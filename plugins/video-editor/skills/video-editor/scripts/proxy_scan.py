#!/usr/bin/env python3
"""Per-frame shot data from proxies in any folder: subject action, camera jitter, pan speed, sharpness, luma (12 fps),
plus an 8-frame labeled strip per clip for visual tagging. Run with scripts/vpy.
Usage: vpy proxy_scan.py OUT_DIR proxy1.mov proxy2.mov ... [--jobs 4]
Writes OUT_DIR/<clip>.json {fps, dur, act[], jit[], pan[], sharp[], luma[]} and OUT_DIR/strips/<clip>.jpg.
act = mean residual frame diff after removing camera motion (0-255); jit = shake px at 640 wide (path minus 0.6 s
moving average); pan = smoothed camera speed px/frame (intentional moves); sharp = Laplacian variance / 100."""
import sys, os, json, subprocess, numpy as np, cv2
from concurrent.futures import ProcessPoolExecutor

FPS = 12; W, H = 640, 360

def scan(src, out):
    c = os.path.basename(src).replace("_Proxy.mov", "").rsplit(".", 1)[0]
    if os.path.exists(f"{out}/{c}.json"): return c
    dur = float(subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
    want = {int(dur * FPS * (i + 0.5) / 8): i for i in range(8)}; keep = {}
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    prev = None; act, dx, dy, sharp, luma = [], [], [], [], []
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        col = np.frombuffer(b, np.uint8).reshape(H, W, 3); f = cv2.cvtColor(col, cv2.COLOR_BGR2GRAY)
        if len(act) in want: keep[len(act)] = col.copy()
        a = 0.0; m = None
        if prev is not None:
            pts = cv2.goodFeaturesToTrack(prev, 200, 0.01, 12)
            if pts is not None and len(pts) >= 8:
                nx, st, _ = cv2.calcOpticalFlowPyrLK(prev, f, pts, None); g = st.ravel() == 1
                if g.sum() >= 8: m, _ = cv2.estimateAffinePartial2D(pts[g], nx[g])
            warped = cv2.warpAffine(prev, m, (W, H)) if m is not None else prev
            a = float(np.mean(cv2.absdiff(warped, f)[20:-20, 20:-20]))
        act.append(a); dx.append(float(m[0, 2]) if m is not None else 0.0); dy.append(float(m[1, 2]) if m is not None else 0.0)
        sharp.append(float(cv2.Laplacian(f, cv2.CV_64F).var() / 100)); luma.append(float(f.mean())); prev = f
    p.wait()
    n = len(act)
    if n < 3: return c
    tx, ty = np.cumsum(dx), np.cumsum(dy); k = 7; ker = np.ones(k) / k
    sx = np.convolve(np.pad(tx, 3, mode="edge"), ker, "valid"); sy = np.convolve(np.pad(ty, 3, mode="edge"), ker, "valid")
    jit = np.hypot(tx - sx, ty - sy); pan = np.hypot(np.gradient(sx), np.gradient(sy))
    r = lambda v: [round(float(x), 2) for x in v]
    json.dump(dict(fps=FPS, dur=n / FPS, act=r(act), jit=r(jit), pan=r(pan), sharp=r(sharp), luma=r(luma)), open(f"{out}/{c}.json", "w"))
    tiles = []
    for i in sorted(keep):
        t = cv2.resize(keep[i], (240, 135)); cv2.rectangle(t, (0, 0), (240, 16), (0, 0, 0), -1)
        cv2.putText(t, f"{c} {i / FPS:.1f}s", (3, 12), 0, 0.4, (0, 255, 255), 1); tiles.append(t)
    os.makedirs(f"{out}/strips", exist_ok=True); cv2.imwrite(f"{out}/strips/{c}.jpg", np.hstack(tiles))
    return c

if __name__ == "__main__":
    a = sys.argv[1:]; jobs = int(a[a.index("--jobs") + 1]) if "--jobs" in a else 4
    a = [x for i, x in enumerate(a) if x != "--jobs" and (i == 0 or a[i - 1] != "--jobs")]
    out, srcs = a[0], a[1:]; os.makedirs(out, exist_ok=True)
    with ProcessPoolExecutor(jobs) as ex:
        for c in ex.map(scan, srcs, [out] * len(srcs)): print("scanned", c, flush=True)
