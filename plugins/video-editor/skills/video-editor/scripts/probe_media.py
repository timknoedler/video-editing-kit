#!/usr/bin/env python3
"""Inventory every video file under a footage root: ffprobe specs + Sony XML sidecar (camera model,
capture fps / S&Q slow-mo, creation date) + display orientation from rotation metadata.
Usage: probe_media.py "<FOOTAGE_ROOT>" [OUT.json]   (default OUT: <FOOTAGE_ROOT>/_edit/work/probe.json)
Prints a summary grouped by folder/camera/res/orientation/fps/date. Read-only on media."""
import json, subprocess, glob, os, re, sys
from collections import Counter

root = sys.argv[1].rstrip("/")
E = os.environ.get("EDIT_DIR") or f"{root}/_edit"  # EDIT_DIR overrides the output folder
out = sys.argv[2] if len(sys.argv) > 2 else f"{E}/work/probe.json"
exts = (".mp4", ".mov", ".mxf", ".braw")
files = sorted(f for f in (g.replace("\\", "/") for g in glob.glob(f"{root}/**/*", recursive=True))  # Windows glob returns backslashes
               if f.lower().endswith(exts) and "/_edit/" not in f and "/Proxies/" not in f and not os.path.basename(f).startswith("._"))
rows = []
for f in files:
    j = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", f],
                                  capture_output=True, text=True).stdout or "{}")
    vs = [s for s in j.get("streams", []) if s.get("codec_type") == "video"]
    if not vs:
        continue
    v = vs[0]; a = [s for s in j["streams"] if s.get("codec_type") == "audio"]
    side = os.path.splitext(f)[0] + "M01.XML"
    xml = open(side, errors="ignore").read() if os.path.exists(side) else ""
    g = lambda pat: (re.search(pat, xml) or [None, ""])[1]
    rot = v.get("tags", {}).get("rotate") or next((sd.get("rotation") for sd in v.get("side_data_list", []) if "rotation" in sd), 0)
    w, h = v["width"], v["height"]
    rotated = str(rot) in ("90", "-90", "270", "-270")
    rows.append(dict(file=os.path.relpath(f, root), camera=g(r'modelName="([^"]+)"'), res=f"{w}x{h}",
                     orientation="vertical" if (h > w) != rotated else "horizontal", rotation=rot,
                     fps=v.get("r_frame_rate"), capture_fps=g(r'captureFps="([^"]+)"'), format_fps=g(r'formatFps="([^"]+)"'),
                     duration=round(float(j["format"]["duration"]), 2), codec=f"{v['codec_name']}/{v.get('pix_fmt','')}",
                     audio_ch=sum(int(s.get("channels", 0)) for s in a),
                     created=g(r'<CreationDate value="([^"]+)"') or j["format"].get("tags", {}).get("creation_time", "")))
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(rows, open(out, "w"), indent=1)
print(len(rows), "clips,", round(sum(r["duration"] for r in rows) / 60, 1), "min ->", out)
for k, n in sorted(Counter((os.path.dirname(r["file"]), r["camera"], r["res"], r["orientation"], r["fps"], r["capture_fps"], r["created"][:10]) for r in rows).items()):
    print(n, k)
