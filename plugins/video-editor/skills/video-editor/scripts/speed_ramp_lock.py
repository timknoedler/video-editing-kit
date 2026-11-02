#!/usr/bin/env python3
"""Target-locked speed ramp (the After Effects "track, then smooth" / Mocha-stabilize idea, offline):
track ONE rigid, distant target (a building facade, a sign) through the whole move instead of the whole frame,
so parallax from close things can't fool it. The target's tracked pose per source frame (centre, size, angle)
is then forced onto a smooth path: centre and angle follow a low-order polynomial, and size grows smoothly.
Everything else in the frame moves naturally around it. Also:
  - travel-equalized timing from the target's own size (log scale = how far the drone has actually flown in),
    blended back to clock time where the ramp is slow (keeps the whole-frame cadence at --vmin);
  - motion blur from a box shutter with fractional frame weights.
Usage: vpy speed_ramp_lock.py SRC OUT.mov S0 S1 DUR --roi x,y,w,h [--vmin 0.8] [--ease 0.35,0.80] [--shutter 1.0]
       [--poly 3] [--lock xyrs] [--zoom auto|1.05] [--eq-full 2.0] [--fps 24000/1001] [--preview track.mp4] [--pin-end]
  --roi   target box in the FIRST frame (S0), in full-res upright pixels. Keep it on rigid, far structure
          (roofline/facade), not on people, tents or trees in front of it.
  --lock  which target components to smooth: x,y = position, r = rotation, s = size (zoom surges).
  --zoom  crop-in that hides the warp edges; auto = the smallest that covers every frame (+0.5 %).
  --pin-end  fade the position correction out over the second half so the landing keeps its original framing
  --preview  writes a small video of the tracked box for checking the track.  Source is only read."""
import sys, subprocess, json, numpy as np, cv2
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
src, out, s0, s1, dur = a[0], a[1], float(a[2]), float(a[3]), float(a[4])
rx, ry, rw, rh = map(float, opt("--roi", "").split(","))
vmin = float(opt("--vmin", 0.8)); ea, eb = map(float, opt("--ease", "0.35,0.80").split(","))
shutter = float(opt("--shutter", 1.0)); poly = int(opt("--poly", 3)); lock = opt("--lock", "xyrs")
zoom_opt = opt("--zoom", "auto"); eqfull = float(opt("--eq-full", 2.0)); preview = opt("--preview", "")
num, den = map(int, opt("--fps", "24000/1001").split("/")); ofps = num / den

p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
    "stream=width,height,r_frame_rate:stream_side_data=rotation", "-of", "json", src], capture_output=True, text=True).stdout)["streams"][0]
W, H = p["width"], p["height"]; rot = abs(int(float((p.get("side_data_list") or [{}])[0].get("rotation", 0))))
if rot in (90, 270): W, H = H, W
n_, d_ = map(int, p["r_frame_rate"].split("/")); sfps = n_ / d_
L = s1 - s0

# ---- pass 1: track the target on a half-res grey proxy; A_k maps frame-0 coords -> frame-k coords ----
sw = W // 2; sh = H // 2; sc = W / sw
dp = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{s0:.4f}", "-i", src, "-t", f"{L + 0.2:.4f}", "-vf",
                       f"scale={sw}:{sh}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
box0 = np.array([[rx, ry], [rx + rw, ry], [rx + rw, ry + rh], [rx, ry + rh]], np.float32) / sc
A = np.eye(3); poses = []; prev = None; frames_dbg = []; lost = 0
while True:
    b = dp.stdout.read(sw * sh)
    if len(b) < sw * sh: break
    g = np.frombuffer(b, np.uint8).reshape(sh, sw)
    if prev is not None:
        box = cv2.perspectiveTransform(box0[None], A)[0]
        mask = np.zeros_like(prev); cv2.fillConvexPoly(mask, box.astype(np.int32), 255)
        pts = cv2.goodFeaturesToTrack(prev, 300, 0.005, 6, mask=mask)
        m = None
        if pts is not None and len(pts) >= 8:
            nx, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None, winSize=(31, 31), maxLevel=4)
            bk, st2, _ = cv2.calcOpticalFlowPyrLK(g, prev, nx, None, winSize=(31, 31), maxLevel=4)
            ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm(bk - pts, axis=2)[:, 0] < 0.5)   # forward-backward check
            if ok.sum() >= 6: m, _ = cv2.estimateAffinePartial2D(pts[ok], nx[ok], method=cv2.RANSAC, ransacReprojThreshold=1.0)
        if m is None: m = np.array([[1, 0, 0], [0, 1, 0]], float); lost += 1
        A = np.vstack([m, [0, 0, 1]]) @ A
    c = (A @ np.array([*(box0.mean(0)), 1.0]))[:2] * sc
    poses.append((c[0], c[1], np.arctan2(A[1, 0], A[0, 0]), np.log(np.hypot(A[0, 0], A[1, 0]))))
    if preview: frames_dbg.append((g[::2, ::2].copy(), (cv2.perspectiveTransform(box0[None], A)[0] / 2).astype(np.int32)))
    prev = g
P = np.array(poses)[:int(np.floor(L * sfps)) + 1]; K = len(P); tk = np.arange(K) / sfps
print(f"tracked {K} frames ({lost} lost); target grew x{np.exp(P[-1, 3]):.2f}, moved {P[-1, 0] - P[0, 0]:.0f},{P[-1, 1] - P[0, 1]:.0f}px, turned {np.degrees(P[-1, 2]):.2f}deg")
if preview:
    h2, w2 = frames_dbg[0][0].shape
    pv = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w2}x{h2}", "-r", f"{n_}/{d_}",
                           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", preview], stdin=subprocess.PIPE)
    for gg, bx in frames_dbg:
        im = cv2.cvtColor(gg, cv2.COLOR_GRAY2BGR); cv2.polylines(im, [bx], True, (0, 0, 255), 2); pv.stdin.write(im.tobytes())
    pv.stdin.close(); pv.wait()

def gauss(x, sec):
    s = max(sec * sfps, 1e-3); k = np.arange(-int(3 * s), int(3 * s) + 1); ker = np.exp(-k * k / (2 * s * s)); ker /= ker.sum()
    return np.convolve(np.pad(x, (len(k) // 2, len(k) // 2), mode="edge"), ker, mode="valid")

# ---- travel time base from the target's size (smoothed), normalized to clock length ----
# flying straight at a target, its size s ~ 1/distance, so distance flown ~ 1 - 1/s (ground travel, not zoom rate)
ls = gauss(P[:, 3], 0.1); dist = 1 - np.exp(-ls); dist = np.maximum.accumulate(dist + 1e-12 * np.arange(K))
tau = (dist - dist[0]) / (dist[-1] - dist[0]) * tk[-1]
r = np.gradient(tau); r = gauss(r, 0.2)
print(f"flight-speed surge (ground travel rate) +-{100 * (r.max() - r.min()) / 2 / r.mean():.0f}%")

# ---- speed curve, solved to land on S1. Blend RATES (not time maps) between travel-timed and clock-timed, so the
#      hand-over at the slow end has no speed bump: du/dt = v * (w * dtk/dtau(u) + (1 - w)) ----
N = int(round(dur * ofps)); t = np.arange(N + 1) / ofps
dtau = np.maximum(gauss(np.gradient(tau, tk), 0.3), 1e-6)           # travel-seconds per clock-second at u (smoothed: surges are slow)
def speed(vmax):
    x = np.clip((t / dur - ea) / (eb - ea), 0, 1); sm = x * x * (3 - 2 * x); return vmin + (vmax - vmin) * (1 - sm)
def integrate(vmax):
    v = speed(vmax); w = np.clip((v - vmin) / max(eqfull - vmin, 1e-6), 0, 1); w = w * w * (3 - 2 * w)
    u = [0.0]
    for i in range(N):
        J = 1.0 / np.interp(u[-1], tk, dtau); u.append(u[-1] + v[i] / ofps * (w[i] * J + (1 - w[i])))
    return np.array(u), v
lo, hi = vmin, 80.0
for _ in range(60):
    mid = (lo + hi) / 2; u, v = integrate(mid)
    lo, hi = (mid, hi) if u[-1] < tk[-1] else (lo, mid)
S, v = integrate(mid); vmax = mid; S = np.clip(S, 0, tk[-1])
print(f"vmax {vmax:.2f}x -> vmin {vmin}x, {N} frames, source {s0}-{s0 + S[-1]:.2f}")

# ---- smooth target path (fit in travel); per-frame correction = similarity taking actual pose -> smooth pose ----
Ps = np.stack([gauss(P[:, i], float(opt('--denoise', 0.12))) for i in range(4)], 1)   # real bob is slow; tracker noise isn't
F = Ps.copy()
mag = np.exp(Ps[:, 3])                                              # straight push: offset from centre grows ~ with size
for i, ax in enumerate("xyrs"):
    if ax not in lock: continue
    base = mag if ax in "xy" else tau                                 # position fits against size, angle/size against travel
    F[:, i] = np.polyval(np.polyfit(base, Ps[:, i], 2 if ax in "xy" else poly), base)
    if "--pin-end" in a:                                              # keep the landing frame's own composition: fade the
        hold = np.clip((tau - 0.5 * tau[-1]) / (0.5 * tau[-1]), 0, 1)   # correction to zero over the 2nd half of the travel
        hold = hold * hold * (3 - 2 * hold); F[:, i] = F[:, i] + hold * (Ps[:, i] - F[:, i]) * (ax in "xy")
def corr_mat(k, zoom, div=1):
    cx, cy, th, l = Ps[k]; fx, fy, fth, fl = F[k]                    # correct the de-noised pose, never inject tracker noise
    if "x" not in lock: fx = cx
    if "y" not in lock: fy = cy
    if "r" not in lock: fth = th
    if "s" not in lock: fl = l
    d = np.exp(fl - l); ca, sa = np.cos(fth - th), np.sin(fth - th)
    R = d * np.array([[ca, -sa], [sa, ca]])
    C = np.array([W / 2, H / 2]); c = np.array([cx, cy]); f = np.array([fx, fy])
    Am = zoom * R; bv = C + zoom * (f - C) - Am @ c
    return np.hstack([Am, (bv / div)[:, None]])
def need_zoom(k):                                                   # smallest zoom whose output corners map inside the source
    lo_, hi_ = 1.0, 1.5
    for _ in range(30):
        z = (lo_ + hi_) / 2; M = corr_mat(k, z); Mi = cv2.invertAffineTransform(M)
        q = (Mi[:, :2] @ np.array([[0, 0], [W, 0], [W, H], [0, H]], float).T).T + Mi[:, 2]
        inside = (q[:, 0] >= 0).all() and (q[:, 0] <= W).all() and (q[:, 1] >= 0).all() and (q[:, 1] <= H).all()
        lo_, hi_ = (lo_, z) if inside else (z, hi_)
    return hi_
used = sorted(set(np.clip(np.round(S * sfps).astype(int), 0, K - 1)))
zreq = max(need_zoom(k) for k in used)
zoom = zreq + 0.005 if zoom_opt == "auto" else float(zoom_opt)
dev = np.abs(Ps - F)
print(f"path deviation removed: max {dev[:, 0].max():.0f}px x, {dev[:, 1].max():.0f}px y, {np.degrees(dev[:, 2].max()):.2f}deg, "
      f"size {100 * dev[:, 3].max():.1f}%; crop-in needed {100 * (zreq - 1):.1f}% -> using {100 * (zoom - 1):.1f}%")

if "--dump" in a:                                                   # analysis only: track, fit and timing, no render
    json.dump({"sfps": sfps, "P": P.tolist(), "Ps": Ps.tolist(), "F": F.tolist(), "tau": tau.tolist(), "S": S.tolist()}, open(opt("--dump", ""), "w")); sys.exit()
# ---- pass 2: warp each source frame, box-shutter blend with fractional weights ----
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{s0:.4f}", "-i", src, "-t", f"{L + 0.2:.4f}",
                        "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-s", f"{W}x{H}",
    "-r", f"{num}/{den}", "-i", "-", "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le",
    "-color_range", "tv", out], stdin=subprocess.PIPE)
ys, cs = W * H, (W // 2) * (H // 2); fsz = (ys + 2 * cs) * 2
cache = {}; nxt = 0
def frame(k):
    global nxt
    while nxt <= k:
        b = dec.stdout.read(fsz)
        if len(b) < fsz: break
        f = np.frombuffer(b, np.uint16); kk = min(nxt, K - 1); outp = []
        for pl, div in ((f[:ys].reshape(H, W), 1), (f[ys:ys + cs].reshape(H // 2, W // 2), 2), (f[ys + cs:].reshape(H // 2, W // 2), 2)):
            h, w_ = pl.shape
            outp.append(cv2.warpAffine(pl.astype(np.float32), corr_mat(kk, zoom, div), (w_, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT))
        cache[nxt] = outp; nxt += 1
    return cache[min(k, nxt - 1)]
for i in range(N):
    hi_t = S[i + 1]; lo_t = hi_t - shutter * (S[i + 1] - S[i]); a0, a1 = lo_t * sfps, hi_t * sfps
    if a1 - a0 < 1.0: ks, ws = [int(round(a1))], [1.0]
    else:
        ks = list(range(int(np.floor(a0 + 0.5)), int(np.floor(a1 + 0.5)) + 1))
        ws = [max(0.0, min(a1, k + 0.5) - max(a0, k - 0.5)) for k in ks]
    acc = None; tw = 0.0
    for k, wt in zip(ks, ws):
        if wt <= 0: continue
        fr = frame(min(k, K - 1)); acc = [x * wt for x in fr] if acc is None else [A_ + x * wt for A_, x in zip(acc, fr)]; tw += wt
    for k in [k for k in cache if k < min(ks) - 1]: del cache[k]
    enc.stdin.write(b"".join(np.clip(np.round(A_ / tw), 0, 1023).astype(np.uint16).tobytes() for A_ in acc))
enc.stdin.close(); enc.wait(); dec.kill(); print(out)
