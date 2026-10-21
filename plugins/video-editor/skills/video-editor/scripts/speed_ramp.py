#!/usr/bin/env python3
"""Render a speed-ramped ProRes 422 HQ clip (fast -> eased -> slow) from a high-frame-rate source, with motion blur
in the fast part (frames averaged over a 180-degree shutter). Premiere's Time Remapping can't be scripted, so ramps are baked.
Usage: vpy speed_ramp.py SRC OUT.mov S0 S1 DUR [--vmin 0.6] [--ease 0.40,0.70] [--fps 24000/1001] [--vmax-cap 12]
  S0..S1  source seconds covered; DUR  output seconds; --vmin  speed at the end (1.0 = real time);
  Pick vmin so the source advances a whole number of frames per output frame (59.94 -> 23.976: 0.4x = 1, 0.8x = 2),
  or the slow end judders.
  --shutter 0.5|1.0  motion-blur window as a fraction of each frame's source span (1.0 = smoothest).
  --ease a,b  fraction of DUR where the slow-down starts/ends (smoothstep). vmax is solved so the ramp lands on S1.
Autorotates (DJI vertical files come out upright). Source is only read."""
import sys, subprocess, json, numpy as np
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
src, out, s0, s1, dur = a[0], a[1], float(a[2]), float(a[3]), float(a[4])
vmin = float(opt("--vmin", 0.6)); shutter = float(opt("--shutter", 0.5)); ea, eb = map(float, opt("--ease", "0.40,0.70").split(","))
num, den = map(int, opt("--fps", "24000/1001").split("/")); ofps = num / den

p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
    "stream=width,height,r_frame_rate:stream_side_data=rotation", "-of", "json", src], capture_output=True, text=True).stdout)["streams"][0]
w, h = p["width"], p["height"]; rot = abs(int(float((p.get("side_data_list") or [{}])[0].get("rotation", 0))))
if rot in (90, 270): w, h = h, w
n_, d_ = map(int, p["r_frame_rate"].split("/")); sfps = n_ / d_

N = int(round(dur * ofps)); t = (np.arange(N + 1)) / ofps
def speed(vmax):
    x = np.clip((t / dur - ea) / (eb - ea), 0, 1); sm = x * x * (3 - 2 * x)
    return vmin + (vmax - vmin) * (1 - sm)
lo, hi = vmin, 60.0
for _ in range(80):                                  # solve vmax so the integral of speed == s1 - s0
    mid = (lo + hi) / 2; s = np.concatenate([[0], np.cumsum(speed(mid)[:-1] / ofps)])
    lo, hi = (mid, hi) if s[-1] < s1 - s0 else (lo, mid)
vmax = mid; S = s0 + s                               # source time at each output frame boundary
print(f"vmax {vmax:.2f}x -> vmin {vmin}x, {N} frames, source {s0}-{S[-1]:.2f}")

dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{s0:.4f}", "-i", src, "-t", f"{s1 - s0 + 0.2:.3f}",
    "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-s", f"{w}x{h}",
    "-r", f"{num}/{den}", "-i", "-", "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le",
    "-color_range", "tv", out], stdin=subprocess.PIPE)
fsz = w * h * 3; k = 0; last = None   # yuv420p10le = 1.5 samples/px x 2 bytes; averaged per plane (no colour-matrix round trip)
for i in range(N):
    t_hi = S[i + 1] - s0; t_lo = t_hi - shutter * (S[i + 1] - S[i])  # shutter 0.5 = 180 deg, 1.0 = 360 deg (more blur hides jitter)
    acc = None; c = 0
    while True:
        ft = k / sfps
        if ft > t_hi + 1e-6: break
        buf = dec.stdout.read(fsz)
        if len(buf) < fsz: break
        k += 1; last = buf
        if ft >= t_lo - 1e-6:
            f = np.frombuffer(buf, np.uint16).astype(np.float32); acc = f if acc is None else acc + f; c += 1
    if acc is None: acc, c = np.frombuffer(last, np.uint16).astype(np.float32), 1   # slow part: reuse nearest frame
    enc.stdin.write((acc / c).round().astype(np.uint16).tobytes())
enc.stdin.close(); enc.wait(); dec.kill()
print(out)
