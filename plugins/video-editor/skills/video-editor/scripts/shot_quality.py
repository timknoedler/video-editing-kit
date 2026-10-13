#!/usr/bin/env python3
"""Camera-shake + sharpness tools for picking steady b-roll windows. Needs the toolkit venv (setup_venv.sh).
Usage (run with scripts/vpy):
  shot_quality.py scan "<ROOT>" C0011 C0012 ...      per-second jitter/move/sharpness -> <ROOT>/_edit/work/shake/<clip>.json (~2.5x realtime on 4K)
  shot_quality.py scan "<ROOT>" --all [--skip C0021,C0022]
  shot_quality.py pick "<ROOT>" C0011:31:2.5 ...     score a planned window (clip:in:dur[:lo:hi]) and show the best window of that length
  shot_quality.py grid "<ROOT>" C0011 [start end step]  annotated frame grid -> <ROOT>/_edit/work/grids/<clip>.jpg (red = jitter>1px or sharp<0.6)
Reading the numbers (360px-wide analysis): jitter <0.4 steady, 0.4-1.0 OK handheld, >1 visibly shaky.
CAVEAT: subject motion (spins, swinging boots, close-ups that fill frame) also raises jitter and lowers sharpness;
confirm flagged shots with `grid` before swapping. Requires <ROOT>/_edit/work/probe.json from probe_media.py."""
import sys, json, subprocess, os
import numpy as np, cv2

cmd, root = sys.argv[1], sys.argv[2].rstrip("/")
E = os.environ.get("EDIT_DIR") or f"{root}/_edit"  # EDIT_DIR overrides the output folder
rest = " ".join(sys.argv[3:]).split()
FPS = 24000 / 1001
probe = {os.path.splitext(os.path.basename(r["file"]))[0]: r for r in json.load(open(f"{E}/work/probe.json"))}
SH = f"{E}/work/shake"; GR = f"{E}/work/grids"
os.makedirs(SH, exist_ok=True); os.makedirs(GR, exist_ok=True)

def fps_of(r):
    try:
        a, b = r["fps"].split("/"); return float(a) / float(b)
    except Exception:
        return FPS

def scan(c):
    out = f"{SH}/{c}.json"
    if os.path.exists(out): return
    r = probe[c]; w, h = (360, 640) if r["orientation"] == "vertical" else (640, 360); fps = fps_of(r)
    d, b = os.path.split(r["file"]); px = f"{root}/{d}/Proxies/{os.path.splitext(b)[0]}_Proxy.mov"
    src = px if os.path.exists(px) else f"{root}/{r['file']}"  # proxies decode much faster; metrics run at 640x360 anyway
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={w}:{h}", "-pix_fmt", "gray",
                          "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    prev = None; dx = []; dy = []; sharp = []
    while True:
        buf = p.stdout.read(w * h)
        if len(buf) < w * h: break
        f = np.frombuffer(buf, np.uint8).reshape(h, w)
        sharp.append(float(cv2.Laplacian(f, cv2.CV_64F).var()))
        m = None
        if prev is not None:
            pts = cv2.goodFeaturesToTrack(prev, 200, 0.01, 12)
            if pts is not None and len(pts) >= 8:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, f, pts, None); g = st.ravel() == 1
                if g.sum() >= 8: m, _ = cv2.estimateAffinePartial2D(pts[g], nxt[g])
        dx.append(float(m[0, 2]) if m is not None else 0.0); dy.append(float(m[1, 2]) if m is not None else 0.0)
        prev = f
    p.wait()
    tx, ty = np.cumsum(dx), np.cumsum(dy); k = max(3, int(fps / 2) | 1); ker = np.ones(k) / k
    sx = np.convolve(np.pad(tx, k // 2, mode="edge"), ker, "valid"); sy = np.convolve(np.pad(ty, k // 2, mode="edge"), ker, "valid")
    jit = np.hypot(tx - sx, ty - sy); mv = np.hypot(np.gradient(sx), np.gradient(sy)); n = len(sharp); sharp = np.array(sharp)
    secs = [dict(t=s, jitter_px=round(float(np.sqrt(np.mean(jit[int(s * fps):int((s + 1) * fps)] ** 2))), 2),
                 move_px=round(float(np.mean(mv[int(s * fps):int((s + 1) * fps)])), 2),
                 sharp=round(float(np.median(sharp[int(s * fps):int((s + 1) * fps)])), 1)) for s in range(int(n / fps))]
    json.dump(dict(clip=c, frames=n, sharp_p90=round(float(np.percentile(sharp, 90)), 1), seconds=secs), open(out, "w"))
    print(c, n, "frames", flush=True)

def window(d, a, n):
    s = d["seconds"][int(a):int(a) + int(round(n + 0.49))]
    if not s: return None
    sh = sum(x["sharp"] for x in s) / len(s) / d["sharp_p90"]; jit = max(x["jitter_px"] for x in s)
    return dict(sharp=round(sh, 2), max_jitter=round(jit, 2), move=round(sum(x["move_px"] for x in s) / len(s), 2), score=round(sh - 0.35 * jit, 2))

def pick(arg):
    p = arg.split(":"); c, a, n = p[0], float(p[1]), float(p[2])
    if not os.path.exists(f"{SH}/{c}.json"): print(c, "not scanned"); return
    d = json.load(open(f"{SH}/{c}.json")); lo = float(p[3]) if len(p) > 3 else 0; hi = float(p[4]) if len(p) > 4 else len(d["seconds"])
    cur = window(d, a, n)
    best = max(((t, window(d, t, n)) for t in range(int(lo), int(hi - n) + 1) if window(d, t, n)), key=lambda x: x[1]["score"])
    flag = "SHAKY" if cur and cur["max_jitter"] > 1 else ("soft" if cur and cur["sharp"] < 0.6 else "ok")
    print(f"{c} @{a:>7.1f} {flag:5s} {cur} | best @{best[0]}s {best[1]}")

def grid(c, a=None, b=None, step=0.5, cols=12, tw=110):
    r = probe[c]; a = a or 0; b = min(b or r["duration"], r["duration"])
    d = json.load(open(f"{SH}/{c}.json")) if os.path.exists(f"{SH}/{c}.json") else None
    th = int(tw * 16 / 9) if r["orientation"] == "vertical" else int(tw * 9 / 16)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", f"{root}/{r['file']}",
                          "-vf", f"fps={1/step},scale={tw}:{th}", "-pix_fmt", "bgr24", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    tiles = []; t = a
    while True:
        buf = p.stdout.read(tw * th * 3)
        if len(buf) < tw * th * 3: break
        im = np.frombuffer(buf, np.uint8).reshape(th, tw, 3).copy(); bad = False; lab = ""
        if d and int(t) < len(d["seconds"]):
            x = d["seconds"][int(t)]; ratio = x["sharp"] / d["sharp_p90"]; bad = x["jitter_px"] > 1 or ratio < 0.6
            lab = f"j{x['jitter_px']:.1f} s{ratio:.1f}"
        cv2.rectangle(im, (0, 0), (tw, 26), (0, 0, 0), -1)
        cv2.putText(im, f"{t:.1f}", (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1)
        cv2.putText(im, lab, (2, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (255, 255, 255), 1)
        if bad: cv2.rectangle(im, (0, 0), (tw - 1, th - 1), (0, 0, 255), 3)
        tiles.append(im); t += step
    p.wait()
    while len(tiles) % cols: tiles.append(np.zeros((th, tw, 3), np.uint8))
    out = f"{GR}/{c}.jpg"
    cv2.imwrite(out, np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]), [cv2.IMWRITE_JPEG_QUALITY, 70])
    print(out)

if cmd == "scan":
    skip = set(rest[rest.index("--skip") + 1].split(",")) if "--skip" in rest else set()
    clips = sorted(probe) if "--all" in rest else [x for x in rest if not x.startswith("--") and x not in skip]
    for c in clips:
        if c not in skip: scan(c)
elif cmd == "pick":
    for a in rest: pick(a)
elif cmd == "grid":
    grid(rest[0], *(float(x) for x in rest[1:4]))
