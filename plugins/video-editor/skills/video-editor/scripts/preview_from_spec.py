#!/usr/bin/env python3
"""Render a low-res review MP4 of one sequence straight from an xml_from_spec.py JSON spec (no Premiere needed):
cuts each b-roll shot at its source in-point, fills the frame like the XML does (centre crop; per-shot "xoff" px shifts
the crop), overlays graphics and mixes VO bites (no markers, captions or music).
Usage: preview_from_spec.py SPEC.json SEQUENCE_NAME OUT.mp4 [--h 960]
Review-only output (ungraded log footage, real-time 60p, no music). Source media is only read."""
import json, os, subprocess, sys, tempfile, shutil

args = sys.argv[1:]
H = int(args[args.index("--h") + 1]) if "--h" in args else 960
spec = json.load(open(args[0])); name, out = args[1], args[2]
s = spec["sequences"][name]; ROOT = (os.environ.get("MEDIA_ROOT") or spec["media_root"]).replace("\\", "/").rstrip("/")  # MEDIA_ROOT: same drive, other machine (e.g. E:/MyDrive)
W0, H0 = s.get("width", spec["width"]), s.get("height", spec["height"])
Wp = int(round(H * W0 / H0 / 2)) * 2
PROXY_ROOTS = [r for r in spec.get("proxy_roots", [])]  # extra folders mirroring media_root for proxies made elsewhere

def src_of(clip):
    """Prefer a ProRes proxy (<dir>/Proxies/<clip>_Proxy.mov, or under a proxy_roots mirror): 4K long-GOP decode is very slow."""
    d, b = os.path.split(clip); n = os.path.splitext(b)[0]
    for c in [f"{ROOT}/{d}/Proxies/{n}_Proxy.mov"] + [f"{p.rstrip('/')}/{d}/{n}_Proxy.mov" for p in PROXY_ROOTS]:
        if os.path.exists(c): return c
    return f"{ROOT}/{clip}"

tmp = tempfile.mkdtemp(); parts = []
for i, b in enumerate(sorted(s.get("broll", []) + s.get("dialogue", []), key=lambda x: x.get("start", x.get("at", 0)))):
    dur = b["end"] - b["start"] if "end" in b else b["out"] - b["in"]
    xoff = b.get("xoff", 0)
    # scale to cover, then crop centred (+xoff in source pixels, scaled)
    vf = (f"scale={Wp}:{H}:force_original_aspect_ratio=increase,"
          f"crop={Wp}:{H}:(iw-{Wp})/2+{xoff}*iw/3840:(ih-{H})/2,fps=24000/1001,setsar=1,format=yuv420p")
    p = f"{tmp}/{i:03d}.mp4"
    rot = ["-noautorotate"] if b.get("ignore_rotation") else []  # wrong rotation metadata (shot horizontal); its proxy has the bad rotation baked in, so use the original
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + rot + ["-ss", str(b["in"]), "-i", f"{ROOT}/{b['clip']}" if rot else src_of(b["clip"]), "-t", f"{dur:.3f}",
                    "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", p], check=True)
    parts.append(p)
open(f"{tmp}/list.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
cat = f"{tmp}/cat.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/list.txt", "-c", "copy", cat], check=True)
cmd = ["ffmpeg", "-v", "error", "-y", "-i", cat]; fc = []; last = "0:v"; k = 1
for g in s.get("graphics", []):
    cmd += ["-loop", "1", "-t", str(g["end"]), "-i", g["file"]]  # still runs the whole timeline; overlay is time-gated
    gw = int(828 * g.get("scale", 100) / 100 * Wp / W0)
    fc.append(f"[{k}:v]scale={gw}:-1[g{k}];[{last}][g{k}]overlay=(W-w)/2:(H-h)/2:enable='between(t,{g['start']},{g['end']})'[v{k}]")
    last = f"v{k}"; k += 1
total = max([b.get("end", 0) for b in s.get("broll", [])])
vos = []
for j, v in enumerate(s.get("vo", [])):  # each VO bite -> its own full-length WAV (a single amix of delayed+padded streams hung)
    w = f"{tmp}/vo{j}.wav"; d = int(v["at"] * 1000); L = v["out"] - v["in"]
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(v["in"]), "-t", f"{L:.3f}", "-i", src_of(v["clip"]), "-vn",
                    "-af", f"pan=mono|c0=c0,loudnorm=I=-19,afade=t=out:st={L - 0.08:.3f}:d=0.08,adelay={d},apad=whole_dur={total}",
                    "-ar", "48000", "-ac", "1", w], check=True)
    cmd += ["-i", w]; vos.append(f"[{k}:a]"); k += 1
if len(vos) > 1:
    fc.append(f"{''.join(vos)}amix=inputs={len(vos)}:duration=first:normalize=0[aout]")
maps = ["-map", f"[{last}]" if last != "0:v" else "0:v"]
if len(vos) > 1: maps += ["-map", "[aout]"]
elif vos: maps += ["-map", vos[0][1:-1]]
if fc: cmd += ["-filter_complex", ";".join(fc)]
cmd = cmd[:1] + ["-nostdin"] + cmd[1:]
cmd += maps + ["-t", str(total), "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", out]
subprocess.run(cmd, check=True)
shutil.rmtree(tmp)
print("wrote", out)
