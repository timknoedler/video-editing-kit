#!/usr/bin/env python3
"""Create ProRes Proxy 1080p proxies (matching the <clip>_Proxy.mov convention) for clips that lack one.
Usage: make_proxies.py "<FOOTAGE_ROOT>" "<PROXY_OUT_ROOT>" [--jobs 3] [--dry]
Reads <EDIT_DIR or FOOTAGE_ROOT/_edit>/work/probe.json. A clip counts as covered if <dir>/Proxies/<clip>_Proxy.mov exists
next to it; otherwise a proxy is written to <PROXY_OUT_ROOT>/<dir>/<clip>_Proxy.mov (source folders stay untouched).
Keeps frame rate, orientation (frame 1920x1080 or 1080x1920) and audio; verifies duration within 0.1 s."""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

args = sys.argv[1:]
jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 3
dry = "--dry" in args
root, out = args[0].rstrip("/"), args[1].rstrip("/")
E = os.environ.get("EDIT_DIR") or f"{root}/_edit"
probe = json.load(open(f"{E}/work/probe.json"))

def dur(f):  # video stream duration (DJI containers carry longer data/subtitle tracks)
    r = subprocess.run(["ffprobe", "-v", "quiet", "-select_streams", "v:0", "-show_entries", "stream=duration", "-of", "csv=p=0", f],
                       capture_output=True, text=True).stdout.strip()
    return float(r or 0)

todo = []
for r in probe:
    d, b = os.path.split(r["file"]); n = os.path.splitext(b)[0]
    if os.path.exists(f"{root}/{d}/Proxies/{n}_Proxy.mov"):
        continue
    todo.append((r, f"{root}/{r['file']}", f"{out}/{d}/{n}_Proxy.mov"))
print(len(todo), "clips need proxies")

def run(t):
    r, src, dst = t
    want = dur(src)
    if os.path.exists(dst) and abs(dur(dst) - want) < 0.1:
        return f"skip {dst}"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    size = "1080:1920" if r["orientation"] == "vertical" else "1920:1080"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v:0", "-map", "0:a?", "-c:v", "prores_ks", "-profile:v", "0",
           "-pix_fmt", "yuv422p10le", "-vf", f"scale={size}", "-c:a", "pcm_s16le", dst]
    p = subprocess.run(cmd, capture_output=True, text=True)
    ok = p.returncode == 0 and abs(dur(dst) - want) < 0.1
    return ("ok   " if ok else "FAIL ") + dst + ("" if ok else " " + p.stderr[-300:])

if not dry:
    with ThreadPoolExecutor(jobs) as ex:
        for line in ex.map(run, todo):
            print(line, flush=True)
