#!/usr/bin/env python3
"""Benchmark finished reels: scene cuts, shot-length stats, hook length, tail (end card) length, and a
one-row-per-shot contact strip. Feeds a client STYLE.md.
Usage: style_profile.py OUT_DIR reel1.mp4 reel2.mp4 ... [--thresh 0.28]
Writes OUT_DIR/<reel>.cuts.json, OUT_DIR/<reel>_shots.jpg (venv not required) and prints a summary table.
Scene threshold is a guess on graded social cuts; dissolves/whips can be missed, so eyeball the strips."""
import json, os, re, shutil, subprocess, sys, tempfile, statistics as st

args = sys.argv[1:]
thresh = 0.28
if "--thresh" in args:
    i = args.index("--thresh"); thresh = float(args[i + 1]); del args[i:i + 2]
out, reels = args[0], args[1:]
os.makedirs(out, exist_ok=True)

def dur(f):
    return float(subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True).stdout)

rows = []
for f in reels:
    name = os.path.splitext(os.path.basename(f))[0]
    D = dur(f)
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", f, "-an", "-vf",
                          f"scale=240:-2,select='gt(scene,{thresh})',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    cuts = [round(float(t), 3) for t in re.findall(r"pts_time:([\d.]+)", log)]
    cuts = [c for i, c in enumerate(cuts) if c > 0.2 and (i == 0 or c - cuts[i - 1] > 0.2)]
    edges = [0.0] + cuts + [D]
    shots = [round(b - a, 3) for a, b in zip(edges, edges[1:])]
    json.dump(dict(file=f, duration=D, cuts=cuts, shots=shots), open(f"{out}/{name}.cuts.json", "w"), indent=1)
    # strip: one thumb at the middle of every shot, 10 per row
    mids = [(a + b) / 2 for a, b in zip(edges, edges[1:])]
    tmp = tempfile.mkdtemp()  # local, avoids exFAT ._ sidecars
    for i, m in enumerate(mids):
        subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", f"{m:.3f}", "-i", f, "-frames:v", "1", "-vf", "scale=-2:320",
                        f"{tmp}/{i:03d}.jpg"])
    cols = 10
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-pattern_type", "glob", "-i", f"{tmp}/*.jpg", "-vf",
                    f"tile={cols}x{(len(mids) + cols - 1) // cols}:padding=4:color=white", "-frames:v", "1",
                    f"{out}/{name}_shots.jpg"])
    shutil.rmtree(tmp)
    body = shots[1:-1] or shots
    rows.append((name, D, len(shots), shots[0], st.mean(body), st.median(body), min(shots), max(shots), shots[-1]))

print(f"{'reel':38} {'len':>6} {'shots':>5} {'hook':>5} {'avg':>5} {'med':>5} {'min':>5} {'max':>5} {'tail':>5}")
for r in rows:
    print(f"{r[0][:38]:38} {r[1]:6.1f} {r[2]:5d} {r[3]:5.2f} {r[4]:5.2f} {r[5]:5.2f} {r[6]:5.2f} {r[7]:5.2f} {r[8]:5.2f}")
