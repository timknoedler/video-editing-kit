#!/usr/bin/env python3
"""Find b-roll windows that are steady AND contain action (cut-on-action helper). Needs the toolkit venv.
Usage: scripts/vpy action_scan.py "<FOOTAGE_ROOT>" C0001 C0002 ...   (reads <dir>/Proxies/<clip>_Proxy.mov when present)
Per 0.25 s step: action = mean residual frame difference after removing camera motion (subject movement, 0-255 scale),
jitter = camera shake in px at 640 wide (same idea as shot_quality.py). Writes <EDIT_DIR>/work/action/<clip>.json and
prints the best windows for 1.25 s and 2.5 s: high action, jitter < 1.0. Confirm picks visually (vcrop_strip.py / grid)."""
import sys, os, json, subprocess, numpy as np, cv2
root = sys.argv[1].rstrip("/"); E = os.environ.get("EDIT_DIR") or f"{root}/_edit"; OUT = f"{E}/work/action"; os.makedirs(OUT, exist_ok=True)
FPS = 12; W, H = 640, 360
def scan(c):
    px = f"{root}/Proxies/{c}_Proxy.mov"; src = px if os.path.exists(px) else f"{root}/{c}.MP4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={FPS},scale={W}:{H}", "-pix_fmt", "gray", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    prev = None; act = []; dx = []; dy = []
    while True:
        b = p.stdout.read(W * H)
        if len(b) < W * H: break
        f = np.frombuffer(b, np.uint8).reshape(H, W)
        a = 0.0; m = None
        if prev is not None:
            pts = cv2.goodFeaturesToTrack(prev, 200, 0.01, 12)
            if pts is not None and len(pts) >= 8:
                nx, st, _ = cv2.calcOpticalFlowPyrLK(prev, f, pts, None); g = st.ravel() == 1
                if g.sum() >= 8: m, _ = cv2.estimateAffinePartial2D(pts[g], nx[g])
            warped = cv2.warpAffine(prev, m, (W, H)) if m is not None else prev
            d = cv2.absdiff(warped, f)[20:-20, 20:-20]; a = float(np.mean(d))
        act.append(a); dx.append(float(m[0, 2]) if m is not None else 0.0); dy.append(float(m[1, 2]) if m is not None else 0.0); prev = f
    p.wait()
    tx, ty = np.cumsum(dx), np.cumsum(dy); k = 7; ker = np.ones(k) / k
    sx = np.convolve(np.pad(tx, 3, mode="edge"), ker, "valid"); sy = np.convolve(np.pad(ty, 3, mode="edge"), ker, "valid")
    jit = np.hypot(tx - sx, ty - sy); act = np.array(act)
    res = {}
    for win in (1.25, 2.5):
        n = int(win * FPS); rows = []
        for s in range(0, len(act) - n, 3):
            rows.append(dict(t=round(s / FPS, 2), action=round(float(np.mean(act[s:s + n])), 2), jitter=round(float(np.sqrt(np.mean(jit[s:s + n] ** 2))), 2)))
        res[str(win)] = rows
    json.dump(res, open(f"{OUT}/{c}.json", "w"))
    return res
for c in sys.argv[2:]:
    r = scan(c)
    for win in ("1.25", "2.5"):
        ok = [x for x in r[win] if x["jitter"] < 1.5]
        best = sorted(ok, key=lambda x: -x["action"])[:3]
        print(c, win, " ".join(f"@{x['t']}:act{x['action']}/jit{x['jitter']}" for x in best), flush=True)
