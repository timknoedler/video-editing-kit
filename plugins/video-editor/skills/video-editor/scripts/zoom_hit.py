#!/usr/bin/env python3
"""Bake a fast "punch / crash zoom" into the head of a shot: N frames from SRC at T0, zooming from --z0 to --z1
(relative to the shot's framing) with a cubic ease-out and zoom blur integrated across each frame interval
(radial smear about the zoom centre). Overwrite it onto the shot's own track at the shot's start (it trims the shot's
head by N frames), then key the shot's Scale to start at z1 x its base scale (x Warp auto-scale if any) so the seam
matches, and let it keep pushing slowly.
Usage: vpy zoom_hit.py SRC OUT.mov T0 [--aspect 9x16|16x9] [--cx 0.5] [--z0 1.0] [--z1 1.2] [--frames 7] [--taps 16] [--src-matrix bt601]
  9x16: base framing = the 9:16 window centred at --cx (fraction of the 16:9 source width), output 2160x3840.
  16x9: base framing = full frame, output 3840x2160.  Output 10-bit 4:2:2 full-range H.264 (.mp4, same as the FX3 files, so Premiere reads its levels the same way), no audio."""
# LEVELS: the FX3 files are full-range 10-bit 4:2:2 H.264. A ProRes overlay (tv or full codes) read ~10 luma brighter
# in Premiere at the seam, so the overlay is written in the camera's own format with the full-range flag.
import sys, subprocess, numpy as np, cv2
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
src, out, t0 = a[0], a[1], float(a[2])
aspect = opt("--aspect", "9x16"); cx = float(opt("--cx", 0.5)); z0 = float(opt("--z0", 1.0)); z1 = float(opt("--z1", 1.2))
N = int(opt("--frames", 7)); taps = int(opt("--taps", 16))
SW, SH = 3840, 2160
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", src, "-frames:v", str(N + 1), "-vf",
                      f"scale={SW}:{SH}:in_color_matrix={opt('--src-matrix', 'bt601')}:in_range=full", "-pix_fmt", "rgb48le", "-f", "rawvideo", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint16).reshape(-1, SH, SW, 3)
if aspect == "9x16":
    OW, OH = 2160, 3840; bw, bh = SH * 9 / 16, SH; ccx = cx * SW
else:
    OW, OH = 3840, 2160; bw, bh = SW, SH; ccx = SW / 2
ccy = SH / 2
def z(t): s = min(max(t / N, 0), 1); return z0 + (z1 - z0) * (1 - (1 - s) ** 3)
def crop(img, zz):                                                    # window of the base framing shrunk by zz
    w, h = bw / zz, bh / zz
    M = np.float32([[OW / w, 0, -(ccx - w / 2) * OW / w], [0, OH / h, -(ccy - h / 2) * OH / h]])
    return cv2.warpAffine(img, M, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{OW}x{OH}",
                      "-r", "24000/1001", "-i", "-", "-vf", "scale=out_range=full:out_color_matrix=bt709", "-color_range", "pc", "-colorspace", "bt709",
                      "-c:v", "libx264", "-profile:v", "high422", "-pix_fmt", "yuv422p10le", "-crf", "8", "-preset", "medium",
                      "-x264-params", "fullrange=on:colormatrix=bt709", out],
                     stdin=subprocess.PIPE)
for k in range(N):
    img = fr[min(k, len(fr) - 1)].astype(np.float32); acc = np.zeros((OH, OW, 3), np.float32)
    for j in range(taps):                                             # 180-degree shutter: first half of the interval
        acc += crop(img, z(k + 0.5 * (j + 0.5) / taps))
    p.stdin.write((acc / taps).clip(0, 65535).astype(np.uint16).tobytes())
p.stdin.close(); p.wait()
print(out, N, "frames", aspect, "zoom", [round(z(k), 3) for k in range(N + 1)])
