#!/usr/bin/env python3
"""Smooth a moving shot (e.g. a drone push) before speed-ramping it: OpenCV feature tracking -> per-frame similarity
transform -> heavily smoothed camera path -> warp each frame onto the smooth path, with a fixed crop-zoom to hide edges.
Works in native YUV (planes warped separately), so there is no colour-matrix round trip. Output: ProRes 422 HQ at the
source frame rate (feed it to speed_ramp.py). Source is only read.
Usage: vpy stabilize.py SRC OUT.mov S0 S1 [--sigma 0.6] [--zoom 1.06]
  sigma  smoothing window in seconds (bigger = smoother glide); zoom  crop-zoom applied to every frame;
  --axes x,a  which components to correct (x, y, a=roll, s=scale; default all). For a forward drone push use
  x,a: y and scale are mostly real parallax flow, and "fixing" them adds fake motion.
  --poly N  fit an order-N polynomial path instead (2-3 = one smooth glide; best before a speed ramp, which
  turns small speed surges into visible jitter). Pick --zoom so the printed max correction fits the crop margin."""
import sys, subprocess, json, numpy as np, cv2
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
src, out, s0, s1 = a[0], a[1], float(a[2]), float(a[3])
sigma_s, zoom = float(opt("--sigma", 0.6)), float(opt("--zoom", 1.06)); poly = int(opt("--poly", 0)); axes = opt("--axes", "x,y,a,s").split(",")
p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
    "stream=width,height,r_frame_rate:stream_side_data=rotation", "-of", "json", src], capture_output=True, text=True).stdout)["streams"][0]
W, H = p["width"], p["height"]; rot = abs(int(float((p.get("side_data_list") or [{}])[0].get("rotation", 0))))
if rot in (90, 270): W, H = H, W
fr = p["r_frame_rate"]; n_, d_ = map(int, fr.split("/")); fps = n_ / d_
def decode(fmt):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{s0:.4f}", "-i", src, "-t", f"{s1 - s0:.4f}",
                             "-f", "rawvideo", "-pix_fmt", fmt, "-"], stdout=subprocess.PIPE)
# pass 1: track on a small grey proxy
sw = 540; sh = int(round(H * sw / W)); sc = W / sw
d = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{s0:.4f}", "-i", src, "-t", f"{s1 - s0:.4f}", "-vf",
                      f"scale={sw}:{sh}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
prev = None; T = []
while True:
    b = d.stdout.read(sw * sh)
    if len(b) < sw * sh: break
    g = np.frombuffer(b, np.uint8).reshape(sh, sw)
    if prev is None: T.append((0.0, 0.0, 0.0, 0.0)); prev = g; continue
    pts = cv2.goodFeaturesToTrack(prev, 400, 0.01, 12)
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None)
    m, _ = cv2.estimateAffinePartial2D(pts[st == 1], nxt[st == 1], method=cv2.RANSAC)
    if m is None: m = np.array([[1, 0, 0], [0, 1, 0]], float)
    T.append((m[0, 2] * sc, m[1, 2] * sc, np.arctan2(m[1, 0], m[0, 0]), np.log(np.hypot(m[0, 0], m[1, 0]))))
    prev = g
T = np.array(T); traj = np.cumsum(T, 0)                       # x, y, angle, log-scale camera path
sig = sigma_s * fps; k = np.arange(-int(3 * sig), int(3 * sig) + 1); ker = np.exp(-k * k / (2 * sig * sig)); ker /= ker.sum()
padded = np.pad(traj, ((len(k) // 2, len(k) // 2), (0, 0)), mode="edge")
smooth = np.stack([np.convolve(padded[:, i], ker, mode="valid") for i in range(4)], 1)
if poly:                                                      # glassy glide: low-order polynomial camera path
    x = np.arange(len(traj)); smooth = np.stack([np.polyval(np.polyfit(x, traj[:, i], poly), x) for i in range(4)], 1)
corr = smooth - traj
for i, ax in enumerate("xyas"):
    if ax not in axes: corr[:, i] = 0                     # forward flights: correct sway (x) and roll (a) only
print(f"{len(T)} frames; max correction x {abs(corr[:, 0]).max():.0f}px y {abs(corr[:, 1]).max():.0f}px "
      f"rot {np.degrees(abs(corr[:, 2]).max()):.2f}deg")
# pass 2: warp full-res YUV planes
dec = decode("yuv420p10le")
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-s", f"{W}x{H}",
    "-r", fr, "-i", "-", "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le", out], stdin=subprocess.PIPE)
ys, cs = W * H, (W // 2) * (H // 2)
for i in range(len(T)):
    b = dec.stdout.read((ys + 2 * cs) * 2)
    if len(b) < (ys + 2 * cs) * 2: break
    f = np.frombuffer(b, np.uint16)
    dx, dy, da, ds = corr[i]; s = zoom * np.exp(ds)
    planes = [(f[:ys].reshape(H, W), 1), (f[ys:ys + cs].reshape(H // 2, W // 2), 2), (f[ys + cs:].reshape(H // 2, W // 2), 2)]
    outp = []
    for pl, div in planes:
        h, w = pl.shape; c = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(c, -np.degrees(da), s)  # OpenCV angle sign is opposite to the tracked transform
        M[0, 2] += dx / div; M[1, 2] += dy / div
        outp.append(cv2.warpAffine(pl, M, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT))
    enc.stdin.write(b"".join(o.astype(np.uint16).tobytes() for o in outp))
enc.stdin.close(); enc.wait(); dec.kill(); print(out)
