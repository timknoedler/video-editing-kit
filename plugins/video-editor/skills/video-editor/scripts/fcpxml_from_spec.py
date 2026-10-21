#!/usr/bin/env python3
"""Build an FCPXML 1.10 file (one project per sequence) from the same JSON edit spec xml_from_spec.py reads,
for Final Cut Pro (File > Import > XML). Resolve and Premiere should use xml_from_spec.py (FCP7 XML) instead.

Usage: fcpxml_from_spec.py SPEC.json OUT.fcpxml
Spec fields (see xml_from_spec.py / example_spec.json): dialogue, broll, vo, graphics, markers, width/height, fps,
target_lufs, max_gain_db, broll_scale ("auto" = conform Fill, a number = Fit + that scale %).
Layout: dialogue on the primary storyline (gaps between bites); b-roll as connected clips on lane 1 (video only);
VO bites on lane -1 (audio only); graphics on lane 2; markers on whichever storyline item covers their time.
Montage (no dialogue): b-roll forms the primary storyline. Per-bite gain is set to target_lufs like the FCP7 builder.
Status: written from the FCPXML 1.10 spec; check the first import in Final Cut and log anything it rejects."""
import json, os, re, subprocess, sys
from fractions import Fraction
from xml.sax.saxutils import escape, quoteattr
import urllib.parse

spec = json.load(open(sys.argv[1])); OUT = sys.argv[2]
ROOT = (os.environ.get("MEDIA_ROOT") or spec["media_root"]).replace("\\", "/").rstrip("/")
fps_in = spec.get("fps", 23.976)
FD = {23.976: Fraction(1001, 24000), 24: Fraction(1, 24), 25: Fraction(1, 25), 29.97: Fraction(1001, 30000),
      30: Fraction(1, 30), 50: Fraction(1, 50), 59.94: Fraction(1001, 60000), 60: Fraction(1, 60)}
FRAME = next(v for k, v in FD.items() if abs(k - fps_in) < 0.01)
FPS = 1 / FRAME
fr = lambda s: int(round(Fraction(s).limit_denominator(1000000) * FPS))          # seconds -> frames
T = lambda f: f"{(Fraction(f) * FRAME).numerator}/{(Fraction(f) * FRAME).denominator}s" if f else "0s"  # frames -> FCPXML time

_probe = {}
def probe(path):
    if path not in _probe:
        j = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-show_streams", "-show_format", "-of", "json", path],
                                      capture_output=True, text=True).stdout or "{}")
        v = next((s for s in j.get("streams", []) if s["codec_type"] == "video"), None)
        a = [s for s in j.get("streams", []) if s["codec_type"] == "audio"]
        _probe[path] = {"dur": float(j.get("format", {}).get("duration", 0) or 0), "v": v,
                        "ach": sum(int(s.get("channels", 0)) for s in a)}
    return _probe[path]

def lufs(clip, a, b):
    o = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(a), "-t", str(b - a), "-i", f"{ROOT}/{clip}", "-vn",
                        "-af", "pan=mono|c0=c0,ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1])

def url(path):
    p = path.replace("\\", "/")
    if not p.startswith("/"): p = "/" + p                      # Windows drive paths (FCP itself is Mac-only)
    return "file://" + urllib.parse.quote(p)

res, assets, nid = [], {}, [1]
def rid():
    nid[0] += 1; return f"r{nid[0]}"

def asset(path, still=False):
    if path in assets: return assets[path]
    i = rid(); p = probe(path); v = p["v"]
    if still:
        res.append(f'<asset id="{i}" name={quoteattr(os.path.basename(path))} start="0s" duration="0s" hasVideo="1">'
                   f'<media-rep kind="original-media" src={quoteattr(url(path))}/></asset>')
    else:
        a, b = map(int, v["r_frame_rate"].split("/")) if v else (24000, 1001)
        f = rid(); res.append(f'<format id="{f}" frameDuration="{b}/{a}s" width="{v["width"] if v else 0}" height="{v["height"] if v else 0}"/>')
        dur = Fraction(p["dur"]).limit_denominator(a)
        res.append(f'<asset id="{i}" name={quoteattr(os.path.basename(path))} start="0s" duration="{dur.numerator}/{dur.denominator}s" '
                   f'format="{f}" hasVideo="{1 if v else 0}" hasAudio="{1 if p["ach"] else 0}"'
                   + (f' audioSources="1" audioChannels="{min(2, p["ach"])}" audioRate="48000"' if p["ach"] else "")
                   + f'><media-rep kind="original-media" src={quoteattr(url(path))}/></asset>')
    assets[path] = i
    return i

out_projects = []
for name, s in spec["sequences"].items():
    W, H = s.get("width", spec["width"]), s.get("height", spec["height"])
    def look(x):
        v = x.get("scale", spec.get("broll_scale", 100))
        if v == "auto": return '<adjust-conform type="fill"/>'
        return "" if v == 100 else f'<adjust-transform scale="{v/100:.4f} {v/100:.4f}"/>'
    def gain(clip, a, b):
        L = lufs(clip, a, b); db = min(spec.get("max_gain_db", 12), spec.get("target_lufs", -19) - L)
        return L, db, f'<adjust-volume amount="{db:+.1f}dB"/>'

    # primary storyline: (start_frame, end_frame, kind, payload)
    spine, rep, t = [], [], 0
    base = s.get("dialogue") or []
    if base:
        for d in base:
            st = fr(d["at"]) if "at" in d else t; en = st + fr(d["out"] - d["in"])
            L, db, g = gain(d["clip"], d["in"], d["out"])
            spine.append([st, en, "clip", dict(clip=d["clip"], src=fr(d["in"]), inner=look(d) + g, en="all")])
            rep.append(f"{st/FPS:6.2f}-{en/FPS:6.2f}  DLG {d['clip'].split('/')[-1]} {d['in']}-{d['out']}  {L:.1f} LUFS -> {db:+.1f} dB")
            t = en
        conn_broll = s.get("broll", [])
    else:
        for b in sorted(s.get("broll", []), key=lambda b: b["start"]):
            spine.append([fr(b["start"]), fr(b["end"]), "clip", dict(clip=b["clip"], src=fr(b["in"]), inner=look(b), en="video")])
            rep.append(f"{b['start']:6.2f}-{b['end']:6.2f}  SPINE {b['clip'].split('/')[-1]} @ {b['in']}")
        conn_broll = []
    total = max([e for _, e, _, _ in spine] + [fr(b["end"]) for b in s.get("broll", [])] +
                [fr(g["end"]) for g in s.get("graphics", [])] + [fr(v["at"]) + fr(v["out"] - v["in"]) for v in s.get("vo", [])] + [0])
    # fill holes with gaps so every connected item and marker has a parent
    spine.sort(key=lambda x: x[0]); full, cur = [], 0
    for it in spine:
        if it[0] > cur: full.append([cur, it[0], "gap", {}])
        if it[0] < cur: print(f"   WARNING overlap at {it[0]/FPS:.2f}s, trimmed"); it[0] = cur
        full.append(it); cur = it[1]
    if cur < total: full.append([cur, total, "gap", {}])
    for it in full: it.append([])                               # children
    def parent(f):
        for it in full:
            if it[0] <= f < it[1]: return it
        return full[-1]
    def child_offset(p, f):                                    # connected-clip offset is in the parent's own time
        return (p[3].get("src", 0) if p[2] == "clip" else 0) + (f - p[0])
    for b in conn_broll:
        st, en = fr(b["start"]), fr(b["end"]); p = parent(st); i = asset(f"{ROOT}/{b['clip']}")
        p[4].append(f'<asset-clip ref="{i}" lane="1" name={quoteattr(b["clip"].split("/")[-1])} offset="{T(child_offset(p, st))}" '
                    f'start="{T(fr(b["in"]))}" duration="{T(en - st)}" srcEnable="video">{look(b)}</asset-clip>')
        rep.append(f"{b['start']:6.2f}-{b['end']:6.2f}  B   {b['clip'].split('/')[-1]} @ {b['in']}")
    for v in s.get("vo", []):
        st = fr(v["at"]); en = st + fr(v["out"] - v["in"]); p = parent(st); i = asset(f"{ROOT}/{v['clip']}")
        L, db, g = gain(v["clip"], v["in"], v["out"])
        p[4].append(f'<asset-clip ref="{i}" lane="-1" name={quoteattr(v["clip"].split("/")[-1])} offset="{T(child_offset(p, st))}" '
                    f'start="{T(fr(v["in"]))}" duration="{T(en - st)}" srcEnable="audio">{g}</asset-clip>')
        rep.append(f"{st/FPS:6.2f}-{en/FPS:6.2f}  VO  {v['clip'].split('/')[-1]}  {L:.1f} LUFS -> {db:+.1f} dB")
    for gx in s.get("graphics", []):
        st, en = fr(gx["start"]), fr(gx["end"]); p = parent(st); i = asset(gx["file"], still=True)
        sc = gx.get("scale", 100)
        p[4].append(f'<video ref="{i}" lane="2" name={quoteattr(os.path.basename(gx["file"]))} offset="{T(child_offset(p, st))}" '
                    f'start="0s" duration="{T(en - st)}">' + (f'<adjust-transform scale="{sc/100:.4f} {sc/100:.4f}"/>' if sc != 100 else "") + '</video>')
        rep.append(f"{gx['start']:6.2f}-{gx['end']:6.2f}  GFX {os.path.basename(gx['file'])}")
    for m in s.get("markers", []):
        f = fr(m["t"]); p = parent(f)
        p[4].insert(0, f'<marker start="{T(child_offset(p, f))}" duration="{T(1)}" value={quoteattr(m["name"])}'
                       + (f' note={quoteattr(m["comment"])}' if m.get("comment") else "") + '/>')
    items = []
    for st, en, kind, d, kids in full:
        if kind == "gap":
            mk = [k for k in kids if k.startswith("<marker")]; rest = [k for k in kids if not k.startswith("<marker")]
            items.append(f'<gap name="Gap" offset="{T(st)}" start="0s" duration="{T(en - st)}">{"".join(rest)}{"".join(mk)}</gap>')
        else:
            i = asset(f"{ROOT}/{d['clip']}")
            # DTD order: adjustments, then connected clips, then markers
            adj = d["inner"]; mk = [k for k in kids if k.startswith("<marker")]; rest = [k for k in kids if not k.startswith("<marker")]
            items.append(f'<asset-clip ref="{i}" name={quoteattr(d["clip"].split("/")[-1])} offset="{T(st)}" start="{T(d["src"])}" '
                         f'duration="{T(en - st)}"' + (' srcEnable="video"' if d["en"] == "video" else "") + f'>{adj}{"".join(rest)}{"".join(mk)}</asset-clip>')
    out_projects.append(f'<project name={quoteattr(name)}><sequence format="r1" duration="{T(total)}" tcStart="0s" tcFormat="NDF" '
                        f'audioLayout="stereo" audioRate="48k"><spine>{"".join(items)}</spine></sequence></project>')
    from collections import Counter
    dup = [c for c, n in Counter(b["clip"] for b in s.get("broll", [])).items() if n > 1]
    print(f"== {name}  {total / FPS:.2f}s  {W}x{H}" + (f"  WARNING repeated b-roll: {dup}" if dup else "")); print("\n".join("   " + r for r in rep))
    if (s.get("width"), s.get("height")) not in ((None, None), (spec["width"], spec["height"])):
        print("   NOTE: per-sequence frame sizes share one format in this file; set the project size in Final Cut if it differs")

fmt = f'<format id="r1" frameDuration="{T(1)}" width="{spec["width"]}" height="{spec["height"]}" colorSpace="1-1-1 (Rec. 709)"/>'
xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.10">\n<resources>' + fmt + "".join(res) +
       '</resources>\n<library><event name="Claude Edit">' + "".join(out_projects) + '</event></library>\n</fcpxml>\n')
open(OUT, "w").write(xml)
print("wrote", OUT)
