#!/usr/bin/env python3
"""Bake a "whip pan up into the shot" overlay: N frames from SRC starting at T0, content starts displaced upward and
settles to rest with an ease-out, with motion blur integrated across each frame (24 taps). Place it on the track above
the shot's first frames; its last frame matches the shot at rest.
Usage: vpy whip_in.py SRC OUT.mov T0 [--aspect 9x16|16x9] [--cx 0.5] [--frames 9] [--amount 0.9]
  9x16: crops the 9:16 window centred at --cx (fraction of source width) and scales to 2160x3840.
  16x9: full frame at 3840x2160.  amount: start offset in frame heights.  Output 10-bit 4:2:2 full-range H.264 (.mp4, same as the FX3 files, so Premiere reads its levels the same way), no audio."""
# LEVELS: the FX3 files are full-range 10-bit 4:2:2 H.264. A ProRes overlay (tv or full codes) read ~10 luma brighter
# in Premiere at the seam, so the overlay is written in the camera's own format with the full-range flag.
import sys, subprocess, numpy as np, cv2
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
src, out, t0 = a[0], a[1], float(a[2])
aspect = opt("--aspect", "9x16"); cx = float(opt("--cx", 0.5)); N = int(opt("--frames", 9)); A = float(opt("--amount", 0.9))
M = opt("--src-matrix", "bt601"); RNG = opt("--range", "pc")
LV = [[float(v) for v in g.split(",")] for g in opt("--levels", "1,0;1,0;1,0").split(";")]  # R;G;B gain,offset (8-bit units)
if aspect == "9x16":
    W, H = 2160, 3840; x0 = int(round(cx * 3840 - 1215 / 2)); vf = f"crop=1215:2160:{x0}:0,scale={W}:{H}:flags=lanczos:in_color_matrix={M}:in_range=full"
else:
    W, H = 3840, 2160; vf = f"scale={W}:{H}:flags=lanczos:in_color_matrix={M}:in_range=full"
cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", src, "-frames:v", str(N + 1), "-vf", vf,
       "-pix_fmt", "rgb48le", "-f", "rawvideo", "-"]
fr = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.uint16).reshape(-1, H, W, 3).astype(np.float32)
fr = fr * np.float32([g for g, _ in LV]) + np.float32([o * 257 for _, o in LV])
if "--lut" in a:                                                      # per-channel 16-bit LUT (3x65536 .npy), e.g. from a Premiere match test
    L = np.load(opt("--lut", "")); q = fr.clip(0, 65535).astype(np.uint16)
    fr = np.stack([L[c][q[..., c]] for c in range(3)], -1).astype(np.float32)
def off(k):
    s = min(k / N, 1.0); return -A * H * (1 - s) ** 3
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W}x{H}",
                      "-r", "24000/1001", "-i", "-", "-vf", f"scale=out_range=full:out_color_matrix={M}", "-color_range", RNG,
                      "-colorspace", {"bt601": "smpte170m"}.get(M, M),
                      "-c:v", "libx264", "-profile:v", "high422", "-pix_fmt", "yuv422p10le", "-crf", "8", "-preset", "medium",
                      "-x264-params", f"fullrange={'on' if RNG == 'pc' else 'off'}:colormatrix={ {'bt601': 'smpte170m'}.get(M, M)}", out],
                     stdin=subprocess.PIPE)
for k in range(N):
    img = fr[min(k, len(fr) - 1)]
    d0, d1 = off(k), off(k + 1)
    taps = 24; acc = np.zeros_like(img)
    for j in range(taps):
        dy = d0 + (d1 - d0) * (j + 0.5) / taps
        acc += cv2.warpAffine(img, np.float32([[1, 0, 0], [0, 1, dy]]), (W, H), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REFLECT)
    p.stdin.write((acc / taps).clip(0, 65535).astype(np.uint16).tobytes())
p.stdin.close(); p.wait(); print(out, N, "frames", aspect)
