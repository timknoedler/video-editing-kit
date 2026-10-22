#!/usr/bin/env python3
"""12-frame contact sheet per clip (ffmpeg only, parallel), plus review stacks of N clips with red dividers.
Usage: contact_sheets.py "<FOOTAGE_ROOT>" [--jobs 6] [--stack 4]
Reads <ROOT>/_edit/work/probe.json (from probe_media.py). Writes <ROOT>/_edit/contact_sheets/<clip>.jpg and
<ROOT>/_edit/work/stacks/<first>-<last>.jpg. Frame i of a sheet is at duration*(i+0.5)/12. Skips existing sheets.
Reads <dir>/Proxies/<clip>_Proxy.mov (or <dir>/<X> Proxies/, or <EDIT_DIR>/proxies/<dir>/ from make_proxies.py) instead of the original when it exists (much faster on long-GOP 4K)."""
import json, os, subprocess, sys, tempfile, shutil, glob
from concurrent.futures import ThreadPoolExecutor

root = sys.argv[1].rstrip("/"); args = sys.argv[2:]
E = os.environ.get("EDIT_DIR") or f"{root}/_edit"  # EDIT_DIR overrides the output folder
jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 6
stack = int(args[args.index("--stack") + 1]) if "--stack" in args else 4
probe = json.load(open(f"{E}/work/probe.json"))
cs = f"{E}/contact_sheets"; st = f"{E}/work/stacks"
os.makedirs(cs, exist_ok=True); os.makedirs(st, exist_ok=True)

_stems = [os.path.splitext(os.path.basename(r["file"]))[0] for r in probe]
def sheet_name(r):  # clip stem; folder-prefixed ("2024-07-16_CamA__C0012") only when stems collide across folders
    stem = os.path.splitext(os.path.basename(r["file"]))[0]
    return stem if _stems.count(stem) == 1 else os.path.splitext(r["file"])[0].replace("/", "__")

def sheet(r):
    name = sheet_name(r); out = f"{cs}/{name}.jpg"
    if os.path.exists(out): return out
    tmp = tempfile.mkdtemp()
    d, b = os.path.split(r["file"]); stem = os.path.splitext(b)[0]
    # proxy in <dir>/Proxies/ or any sibling "* Proxies" folder (e.g. "FX3 Proxies", "Drone Proxies")
    pdirs = [f"{root}/{d}/Proxies"] + sorted(glob.glob(f"{glob.escape(root + '/' + d)}/*Proxies"))
    pdirs.append(f"{E}/proxies/{d}")  # where make_proxies.py writes missing proxies
    px = next((f"{p}/{stem}_Proxy.mov" for p in pdirs if os.path.exists(f"{p}/{stem}_Proxy.mov")), "")
    src = px if os.path.exists(px) else f"{root}/{r['file']}"
    for i in range(12):
        t = r["duration"] * (i + 0.5) / 12
        subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
                        "-vf", "scale=180:-2", f"{tmp}/{i:02d}.png"])
    subprocess.run(["ffmpeg", "-v", "quiet", "-i", f"{tmp}/%02d.png", "-vf", "tile=6x2:padding=4", "-frames:v", "1", "-q:v", "4", out])
    shutil.rmtree(tmp); return out

with ThreadPoolExecutor(jobs) as ex:
    sheets = list(ex.map(sheet, probe))
sheets = [s for s in sheets if os.path.exists(s)]
for k in range(0, len(sheets), stack):
    g = sheets[k:k + stack]
    out = f"{st}/{os.path.basename(g[0])[:-4]}-{os.path.basename(g[-1])[:-4]}.jpg"
    if os.path.exists(out): continue
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for s in g: cmd += ["-i", s]
    fc = "".join(f"[{i}]pad=iw:ih+24:0:0:red[x{i}];" for i in range(len(g))) + "".join(f"[x{i}]" for i in range(len(g)))
    fc += (f"vstack={len(g)}," if len(g) > 1 else "null,") + "scale=iw*0.75:-2"
    subprocess.run(cmd + ["-filter_complex", fc, "-q:v", "5", out])
print(len(sheets), "sheets;", "stacks in", st)
