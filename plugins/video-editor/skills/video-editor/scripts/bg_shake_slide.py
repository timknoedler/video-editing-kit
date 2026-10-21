#!/usr/bin/env python3
"""Sliding-window version of bg_shake.py: decode a clip range once, then score every window of a given length
(background-ring shake, same metric and bar as bg_shake.py: jit <=0.8%, peak <=2%) plus subject action, so you can
pick the steadiest window that still has the action. Run with scripts/vpy.
Usage: vpy bg_shake_slide.py FILE DUR [FROM TO] [--step 0.25] [--top 8]
Prints the best windows: start, jit%, peak%, action (mean frame diff inside the centre, camera motion removed)."""
import sys, subprocess, numpy as np, cv2
a = sys.argv[1:]
step = float(a[a.index("--step") + 1]) if "--step" in a else 0.25
top = int(a[a.index("--top") + 1]) if "--top" in a else 8
a = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
f, dur = a[0], float(a[1]); t0 = float(a[2]) if len(a) > 2 else 0.0; t1 = float(a[3]) if len(a) > 3 else None
W, H, FPS = 640, 360, 24
cmd = ["ffmpeg", "-v", "error", "-ss", str(t0)] + (["-t", str(t1 - t0)] if t1 else []) + ["-i", f, "-vf", f"fps={FPS},scale={W}:{H}", "-pix_fmt", "gray", "-f", "rawvideo", "-"]
fr = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.uint8).reshape(-1, H, W)
mask = np.full((H, W), 255, np.uint8); mask[int(H * .25):int(H * .85), int(W * .25):int(W * .75)] = 0
dx, dy, act = [0.0], [0.0], [0.0]
for p, q in zip(fr[:-1], fr[1:]):
    m = None; pts = cv2.goodFeaturesToTrack(p, 300, 0.01, 8, mask=mask)
    if pts is not None and len(pts) >= 10:
        nx, st, _ = cv2.calcOpticalFlowPyrLK(p, q, pts, None); g = st.ravel() == 1
        if g.sum() >= 10: m, _ = cv2.estimateAffinePartial2D(pts[g], nx[g], ransacReprojThreshold=1.0)
    dx.append(m[0, 2] if m is not None else 0.0); dy.append(m[1, 2] if m is not None else 0.0)
    w = cv2.warpAffine(p, m, (W, H)) if m is not None else p
    act.append(float(np.mean(cv2.absdiff(w, q)[int(H * .2):int(H * .8), int(W * .2):int(W * .8)])))
dx, dy, act = map(np.array, (dx, dy, act)); n = int(round(dur * FPS)); k = FPS; ker = np.ones(k) / k
res = []
for s in range(0, len(fr) - n, max(1, int(step * FPS))):
    tx, ty = np.cumsum(dx[s + 1:s + n]), np.cumsum(dy[s + 1:s + n])
    sx = np.convolve(np.pad(tx, k // 2, mode="edge"), ker, "valid")[:len(tx)]; sy = np.convolve(np.pad(ty, k // 2, mode="edge"), ker, "valid")[:len(ty)]
    r = np.hypot(tx - sx, ty - sy); stp = np.hypot(np.diff(tx - sx), np.diff(ty - sy)) if len(tx) > 1 else np.array([0])
    res.append((100 * np.sqrt(np.mean(r ** 2)) / W, 100 * stp.max() / W, act[s:s + n].mean(), t0 + s / FPS))
ok = [r for r in res if r[0] <= 0.8 and r[1] <= 2.0]
print(f"{len(res)} windows, {len(ok)} pass the bar")
for j, pk, ac, t in sorted(ok, key=lambda r: -r[2])[:top]: print(f"  @{t:6.2f}  jit {j:.2f}%  peak {pk:.2f}%  action {ac:.1f}")
if not ok:
    for j, pk, ac, t in sorted(res, key=lambda r: r[0])[:top]: print(f"  (best shake) @{t:6.2f}  jit {j:.2f}%  peak {pk:.2f}%  action {ac:.1f}")
