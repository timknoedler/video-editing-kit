#!/usr/bin/env python3
"""Find the camera moves (and re-takes) inside one long clip: shooters often keep rolling, go back to their start mark and
repeat a push / pan / tilt. This tracks the global camera motion per frame (background features, RANSAC similarity on a
small proxy), smooths it, and splits the clip into HOLD (on a mark), MOVE (a deliberate move) and RESET (a fast move back
toward an earlier start). Each MOVE is reported with its real start (the end of the hold before it), its end, its
direction, how far it went, how even its speed was, and its jitter, so the cleanest attempt can be picked and cut from
its first frame.
Usage: vpy camera_moves.py FILE [--fps 12] [--from 0] [--to END] [--sheet out.jpg]
Speeds are in % of frame width (or zoom %) per second. Run on proxies (fast); times are source seconds."""
import sys, subprocess, numpy as np, cv2
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
f = a[0]; FPS = float(opt("--fps", 12)); t0 = float(opt("--from", 0)); t1 = opt("--to", None); sheet = opt("--sheet", None)
W, H = 480, 270
cmd = ["ffmpeg", "-v", "error", "-ss", str(t0), "-i", f] + (["-t", str(float(t1) - t0)] if t1 else []) + \
      ["-vf", f"fps={FPS},scale={W}:{H}", "-pix_fmt", "gray", "-f", "rawvideo", "-"]
fr = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.uint8).reshape(-1, H, W)
n = len(fr); dx = np.zeros(n); dy = np.zeros(n); dz = np.zeros(n); dr = np.zeros(n)
for i in range(1, n):
    p = cv2.goodFeaturesToTrack(fr[i - 1], 300, 0.01, 8)
    if p is None or len(p) < 12: continue
    q, st, _ = cv2.calcOpticalFlowPyrLK(fr[i - 1], fr[i], p, None); g = st.ravel() == 1
    if g.sum() < 12: continue
    m, _ = cv2.estimateAffinePartial2D(p[g], q[g], method=cv2.RANSAC, ransacReprojThreshold=1.5)
    if m is None: continue
    dx[i] = -m[0, 2] / W * 100; dy[i] = -m[1, 2] / H * 100          # camera motion = opposite of image motion
    dz[i] = (np.hypot(m[0, 0], m[1, 0]) - 1) * 100; dr[i] = np.degrees(np.arctan2(m[1, 0], m[0, 0]))
k = max(3, int(FPS * 0.35)) | 1
sm = lambda v: np.convolve(np.pad(v, k // 2, mode="edge"), np.ones(k) / k, "valid")
vx, vy, vz = sm(dx) * FPS, sm(dy) * FPS, sm(dz) * FPS                  # per second
speed = np.hypot(np.hypot(vx, vy), vz * 1.5)
px, py, pz = np.cumsum(dx), np.cumsum(dy), np.cumsum(dz)               # camera pointing / zoom path
moving = speed > max(4.0, np.percentile(speed, 30) * 1.5)
# clean up flicker: runs shorter than 0.4 s flip to their neighbours
runs, i = [], 0
while i < n:
    j = i
    while j < n and moving[j] == moving[i]: j += 1
    runs.append([i, j, bool(moving[i])]); i = j
minlen = int(FPS * 0.4)
for r in runs:
    if r[1] - r[0] < minlen: r[2] = not r[2]
merged = []
for r in runs:
    if merged and merged[-1][2] == r[2]: merged[-1][1] = r[1]
    else: merged.append(list(r))
def dirname(ddx, ddy, ddz):
    parts = []
    if abs(ddz) > max(abs(ddx), abs(ddy)) * 0.5 and abs(ddz) > 3: parts.append("push in" if ddz > 0 else "pull out")
    if abs(ddx) > 4: parts.append("pan right" if ddx > 0 else "pan left")
    if abs(ddy) > 4: parts.append("tilt down" if ddy > 0 else "tilt up")
    return " + ".join(parts) or "drift"
moves, starts = [], []
print(f"{f.split('/')[-1]}  {t0:.2f}-{t0 + n / FPS:.2f}s  ({n} samples @ {FPS:g} fps)")
for s, e, mv in merged:
    ts, te = t0 + s / FPS, t0 + e / FPS
    if not mv:
        print(f"  HOLD  {ts:7.2f}-{te:7.2f}"); continue
    e1 = min(e, n - 1)
    ddx, ddy, ddz = px[e1] - px[s], py[e1] - py[s], pz[e1] - pz[s]
    sp = speed[s:e]; even = float(np.std(sp) / (np.mean(sp) + 1e-6))
    res = np.hypot(dx[s:e] - sm(dx)[s:e], dy[s:e] - sm(dy)[s:e]); jit = float(np.sqrt(np.mean(res ** 2)))
    # a reset heads back toward where an earlier move started, faster than that move
    back = None
    for (ms, mx, my, mz, mspeed) in starts:
        d_before = np.hypot(np.hypot(px[s] - mx, py[s] - my), pz[s] - mz)
        d_after = np.hypot(np.hypot(px[e1] - mx, py[e1] - my), pz[e1] - mz)
        if d_before > 3 and d_after < d_before * 0.45 and np.mean(sp) > mspeed * 1.3: back = ms
    kind = "RESET" if back is not None else "MOVE"
    note = f" (back to the {back:.2f}s start)" if back is not None else ""
    print(f"  {kind:5s} {ts:7.2f}-{te:7.2f}  {dirname(ddx, ddy, ddz):22s} dist x{ddx:+6.1f} y{ddy:+6.1f} zoom{ddz:+5.1f}%"
          f"  speed {np.mean(sp):5.1f}/s  evenness {even:4.2f}  jitter {jit:4.2f}{note}")
    if kind == "MOVE":
        size = float(np.hypot(np.hypot(ddx, ddy), ddz * 3))
        starts.append((ts, px[s], py[s], pz[s], float(np.mean(sp)))); moves.append((ts, te, even, jit, size))
if moves:
    big = max(m[4] for m in moves)                                      # only compare takes of a similar size
    best = min([m for m in moves if m[4] >= big * 0.5], key=lambda m: m[2] + m[3] * 2)
    print(f"  best take: {best[0]:.2f}-{best[1]:.2f} (evenness {best[2]:.2f}, jitter {best[3]:.2f}; lower is better)")
    if sheet:
        tiles = []
        for ts, te, _, _, _ in moves:
            for tt in (ts, (ts + te) / 2, te - 0.05):
                idx = min(int((tt - t0) * FPS), n - 1); im = cv2.cvtColor(fr[idx], cv2.COLOR_GRAY2BGR)
                cv2.putText(im, f"{tt:.2f}s", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2); tiles.append(im)
        rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
        cv2.imwrite(sheet, np.vstack(rows)); print("  sheet:", sheet, "(each row = one take: start / middle / end)")
