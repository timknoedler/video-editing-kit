#!/usr/bin/env python3
"""Render a 9:16 (or any) crop window that moves over a 16:9 source: keyframed pans, subject tracking, push-ins.
Premiere's Motion > Position can't be keyframed through the MCP (vector values), so moves are baked to ProRes 422 HQ.
Usage: vpy pan_crop.py SRC OUT.mov IN DUR "t:cx[:zoom],t:cx[:zoom],..." [--out 2160x3840] [--cy 0.5]
  t  seconds from IN; cx  crop-centre x as a fraction of source width; zoom  1.0 = the plain 9:16 crop (default 1.0); ffmpeg's crop evaluates w/h once, so keep zoom constant
  (use Premiere Scale keyframes for push-ins).
  Moves between keys use smoothstep easing. Writes DUR + 2 frames of handle. Source is only read; log footage stays log."""
import sys, subprocess, json
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
src, out, t_in, dur, keys = a[0], a[1], float(a[2]), float(a[3]), a[4]
ow, oh = map(int, opt("--out", "2160x3840").split("x")); cy = float(opt("--cy", 0.5))
K = []
for k in keys.split(","):
    p = k.split(":"); K.append((float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 1.0))
st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                "-of", "json", src], capture_output=True, text=True).stdout)["streams"][0]
W, H = st["width"], st["height"]
base_h = min(H, W * oh / ow); base_w = base_h * ow / oh          # largest crop with the output aspect

def seg(key, idx):                                              # eased value of field idx across the key list
    e = f"{K[-1][idx]}"
    for (t0, *v0), (t1, *v1) in reversed(list(zip(K, K[1:]))):
        a0, a1 = v0[idx - 1], v1[idx - 1]
        u = f"clip((t-{t0})/{max(t1 - t0, 1e-3)},0,1)"
        e = f"if(lt(t,{t1}),{a0}+({a1 - a0})*({u})*({u})*(3-2*({u})),{e})"
    return f"if(lt(t,{K[0][0]}),{K[0][idx]},{e})"
zoom = seg(K, 2); cx = seg(K, 1)
cw = f"({base_w}/({zoom}))"; ch = f"({base_h}/({zoom}))"
vf = (f"format=yuv444p10le,crop=w='{cw}':h='{ch}':x='clip(({cx})*{W}-{cw}/2,0,{W}-{cw})':y='clip({cy}*{H}-{ch}/2,0,{H}-{ch})',"
      f"scale={ow}:{oh}:flags=lanczos")
n = int(round((dur + 2 / 23.976) * 24000 / 1001))
cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t_in:.4f}", "-i", src, "-an", "-frames:v", str(n), "-vf", vf,
       "-r", "24000/1001", "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le", out]
subprocess.run(cmd, check=True); print(out, n, "frames")
