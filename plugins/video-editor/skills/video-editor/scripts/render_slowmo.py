#!/usr/bin/env python3
"""Render a slow-motion ProRes 422 HQ clip from a high-frame-rate source window (e.g. 59.94p drone at 40%), conformed to
23.976 with every source frame kept (no frame blending) - the "slow motion without the speed tool" recipe in reference/premiere.md.
Usage: render_slowmo.py SRC OUT.mov IN_S TIMELINE_DUR_S [--speed 0.4] [--extra 0.25]
Reads IN_S .. IN_S + (TIMELINE_DUR_S + extra) * speed seconds of source. Output length = TIMELINE_DUR_S + extra (handle).
Keeps resolution and orientation; full->limited range as in the playbook recipe. Source media is only read."""
import sys, subprocess, os
a = sys.argv[1:]
speed = float(a[a.index("--speed") + 1]) if "--speed" in a else 0.4
extra = float(a[a.index("--extra") + 1]) if "--extra" in a else 0.25
src, out, t_in, dur = a[0], a[1], float(a[2]), float(a[3])
n = int(round((dur + extra) * 24000 / 1001))
os.makedirs(os.path.dirname(out), exist_ok=True)
cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t_in:.4f}", "-i", src, "-an", "-frames:v", str(n),
       "-vf", f"setpts={1 / speed}*(PTS-STARTPTS)", "-r", "24000/1001", "-c:v", "prores_ks", "-profile:v", "3",
       "-pix_fmt", "yuv422p10le", out]
subprocess.run(cmd, check=True)
print(out, n, "frames")
