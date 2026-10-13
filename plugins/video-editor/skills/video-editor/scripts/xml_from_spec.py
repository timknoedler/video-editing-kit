#!/usr/bin/env python3
"""Build an FCP7 XML (xmeml v4) of one or more rough-cut sequences from a JSON edit spec,
for import into Premiere (File > Import, or MCP import_media on the .xml).
Use when the Premiere bridge can't set source in/out points (Premiere 26.x CEP).

Usage: xml_from_spec.py SPEC.json OUT.xml
Spec:
{ "media_root": "/abs/footage/root", "fps": 23.976, "width": 2160, "height": 3840,
  "target_lufs": -19, "max_gain_db": 12,
  "sequences": { "NAME": {
     "dialogue": [ {"clip": "DAY 2/C0021.MP4", "in": 29.44, "out": 38.63, "scale": 100, "at": 0.6} ],
        # V1 + A1/A2; "at" optional (default: butt against previous); per-bite gain auto-set to target_lufs
     "broll": [ {"clip": "DAY 2/C0027.MP4", "in": 16.0, "start": 4.92, "end": 9.19} ],
        # V2 when dialogue exists, else V1 (montage). Video only.
     "vo": [ {"clip": "DAY 2/C0021.MP4", "in": 10.0, "out": 14.4, "at": 22.5} ],
        # audio-only bites (A1/A2) under a montage, gain auto-set to target_lufs
     "graphics": [ {"file": "/abs/logo.png", "start": 36.0, "end": 40.0, "scale": 100} ],
        # stills on the track above the picture (logo end cards)
     "markers": [ {"t": 0, "name": "MUSIC START", "comment": "..."} ],
     "width": 3840, "height": 2160 } } }   # optional per-sequence frame size override
  b-roll/dialogue items also take "scale" (default "broll_scale" at spec level; "auto" = fill the frame: horizontal
  source in a vertical sequence -> 177.78, rotated/vertical-native or matching orientation -> 100).
  Mixed-rate media (29.97 drone, 59.94 FX3) is placed with in/out counted at the sequence rate (what Premiere expects).
Prints a timeline report. Source media is only read (ffprobe/ffmpeg loudness)."""
import json, os, re, subprocess, sys, urllib.parse
from xml.sax.saxutils import escape

spec = json.load(open(sys.argv[1])); OUT = sys.argv[2]
ROOT = (os.environ.get("MEDIA_ROOT") or spec["media_root"]).replace("\\", "/").rstrip("/")  # MEDIA_ROOT: same drive, other machine (e.g. E:/MyDrive)
FPS = 24000 / 1001 if abs(spec.get("fps", 23.976) - 23.976) < 0.01 else spec["fps"]
TB, NTSC = (24, "TRUE") if abs(FPS - 23.976) < 0.01 else (round(FPS), "FALSE")
RATE = f"<rate><timebase>{TB}</timebase><ntsc>{NTSC}</ntsc></rate>"
fr = lambda s: int(round(s * FPS))
_dur = {}; _info = {}

def info(clip):
    """(fps, timebase, ntsc, rotated, w, h) of the clip's video stream."""
    if clip not in _info:
        j = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-select_streams", "v:0", "-show_streams", "-of", "json", f"{ROOT}/{clip}"],
                                      capture_output=True, text=True).stdout)["streams"][0]
        a, b = map(int, j["r_frame_rate"].split("/")); f = a / b
        rot = j.get("tags", {}).get("rotate") or next((sd.get("rotation") for sd in j.get("side_data_list", []) if "rotation" in sd), 0)
        tb = round(f); ntsc = "TRUE" if abs(f - tb) > 0.001 else "FALSE"
        _info[clip] = (f, tb, ntsc, str(rot) in ("90", "-90", "270", "-270"), j["width"], j["height"])
    return _info[clip]

def crate(clip):
    f, tb, ntsc = info(clip)[:3]
    return f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"

def auto_scale(clip, W, H):
    f, tb, ntsc, rot, w, h = info(clip)
    if rot: w, h = h, w
    return round(max(W / w, H / h) * 100, 2)

def duration(clip):
    if clip not in _dur:
        o = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", f"{ROOT}/{clip}"],
                           capture_output=True, text=True).stdout
        _dur[clip] = float(o)
    return _dur[clip]

def lufs(clip, a, b):
    o = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(a), "-t", str(b - a), "-i", f"{ROOT}/{clip}", "-vn",
                        "-af", "pan=mono|c0=c0,ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1])

done_files = set()

def file_url(path):
    """file://localhost URL for Mac (/Volumes/...) or Windows (D:\\... -> /D%3a/...) paths, as Premiere writes them."""
    p = path.replace("\\", "/")
    if not p.startswith("/"): p = "/" + p
    return "file://localhost" + urllib.parse.quote(p).replace("%3A", "%3a")
_ach = {}
def audio_channels(clip):
    if clip not in _ach:
        o = subprocess.run(["ffprobe", "-v", "quiet", "-select_streams", "a", "-show_entries", "stream=channels", "-of", "csv=p=0", f"{ROOT}/{clip}"],
                           capture_output=True, text=True).stdout.split()
        _ach[clip] = sum(int(x) for x in o if x.strip().isdigit())
    return _ach[clip]

def file_xml(clip):
    fid = "file-" + re.sub(r"[^A-Za-z0-9]", "_", clip)
    if fid in done_files:
        return f'<file id="{fid}"/>'
    done_files.add(fid)
    url = file_url(f"{ROOT}/{clip}")
    return (f'<file id="{fid}"><name>{escape(clip.split("/")[-1])}</name><pathurl>{url}</pathurl>{RATE}'
            f'<duration>{fr(duration(clip))}</duration><media><video/>'
            + (f'<audio><channelcount>{min(2, audio_channels(clip))}</channelcount></audio>' if audio_channels(clip) else '')  # silent DJI files go offline if audio is declared
            + '</media></file>')

def still_xml(path, dur_frames):
    fid = "file-" + re.sub(r"[^A-Za-z0-9]", "_", path)
    if fid in done_files:
        return f'<file id="{fid}"/>'
    done_files.add(fid)
    url = file_url(path)
    return (f'<file id="{fid}"><name>{escape(path.split("/")[-1])}</name><pathurl>{url}</pathurl>{RATE}'
            f'<duration>{dur_frames}</duration><media><video><samplecharacteristics><width>828</width><height>828</height></samplecharacteristics></video></media></file>')

def motion(scale):
    if scale == 100: return ""
    return ('<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory>'
            '<effecttype>motion</effecttype><mediatype>video</mediatype><parameter authoringApp="PremierePro">'
            f'<parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax><value>{scale}</value></parameter></effect></filter>')

def levels(lin):
    return ('<filter><effect><name>Audio Levels</name><effectid>audiolevels</effectid><effectcategory>audiolevels</effectcategory>'
            '<effecttype>audiolevels</effecttype><mediatype>audio</mediatype><parameter authoringApp="PremierePro">'
            f'<parameterid>level</parameterid><name>Level</name><valuemin>0</valuemin><valuemax>3.98109</valuemax><value>{lin}</value></parameter></effect></filter>')

n = [0]
def item(clip, st, en, src_in_s, track=None, extra=""):
    """st/en in sequence frames; source in given in seconds. Premiere 26.5 reads clipitem in/out in the
    sequence timebase whatever <rate> says (tested 2026-10-05: 29.97/59.94 media landed 1.25x/2.5x late),
    so source frames are counted at the sequence rate for every clip."""
    n[0] += 1
    si = fr(src_in_s); so = si + en - st
    src = f"<sourcetrack><mediatype>audio</mediatype><trackindex>{track}</trackindex></sourcetrack>" if track else ""
    return (f'<clipitem id="ci-{n[0]}"><name>{escape(clip.split("/")[-1])}</name><enabled>TRUE</enabled><duration>{fr(duration(clip))}</duration>{RATE}'
            f'<start>{st}</start><end>{en}</end><in>{si}</in><out>{so}</out>{file_xml(clip)}{src}{extra}</clipitem>')

def still(path, st, en, scale):
    n[0] += 1
    return (f'<clipitem id="ci-{n[0]}"><name>{escape(path.split("/")[-1])}</name><enabled>TRUE</enabled><duration>{en - st}</duration>{RATE}'
            f'<start>{st}</start><end>{en}</end><in>0</in><out>{en - st}</out>{still_xml(path, en - st)}{motion(scale)}</clipitem>')

track = lambda items: "<track>" + "".join(items) + "<enabled>TRUE</enabled><locked>FALSE</locked></track>" if items else ""
out = ['<?xml version="1.0" encoding="UTF-8"?>', "<!DOCTYPE xmeml>", '<xmeml version="4">']
for name, s in spec["sequences"].items():
    v1, v2, v3, a1, a2, rep = [], [], [], [], [], []
    t = 0
    W, H = s.get("width", spec["width"]), s.get("height", spec["height"])
    def sc(x):
        v = x.get("scale", spec.get("broll_scale", 100))
        return auto_scale(x["clip"], W, H) if v == "auto" else v
    for d in s.get("dialogue", []):
        st = fr(d["at"]) if "at" in d else t
        en = st + fr(d["out"] - d["in"])
        L = lufs(d["clip"], d["in"], d["out"])
        db = min(spec.get("max_gain_db", 12), spec.get("target_lufs", -19) - L)
        lin = round(10 ** (db / 20), 4)
        v1.append(item(d["clip"], st, en, d["in"], extra=motion(sc(d))))
        a1.append(item(d["clip"], st, en, d["in"], 1, levels(lin)))
        a2.append(item(d["clip"], st, en, d["in"], 2, levels(lin)))
        rep.append(f"{st/FPS:6.2f}-{en/FPS:6.2f}  DLG {d['clip'].split('/')[-1]} {d['in']}-{d['out']}  {L:.1f} LUFS -> {db:+.1f} dB  scale {sc(d)}%")
        t = en
    for d in s.get("vo", []):
        st = fr(d["at"]); en = st + fr(d["out"] - d["in"])
        L = lufs(d["clip"], d["in"], d["out"])
        db = min(spec.get("max_gain_db", 12), spec.get("target_lufs", -19) - L); lin = round(10 ** (db / 20), 4)
        a1.append(item(d["clip"], st, en, d["in"], 1, levels(lin))); a2.append(item(d["clip"], st, en, d["in"], 2, levels(lin)))
        rep.append(f"{st/FPS:6.2f}-{en/FPS:6.2f}  VO  {d['clip'].split('/')[-1]} {d['in']}-{d['out']}  {L:.1f} LUFS -> {db:+.1f} dB")
    for b in s.get("broll", []):
        st, en = fr(b["start"]), fr(b["end"])
        (v2 if s.get("dialogue") else v1).append(item(b["clip"], st, en, b["in"], extra=motion(sc(b))))
        rep.append(f"{b['start']:6.2f}-{b['end']:6.2f}  {'V2' if s.get('dialogue') else 'V1'}  {b['clip'].split('/')[-1]} @ {b['in']}  scale {sc(b)}%  ({info(b['clip'])[0]:.3f} fps src)")
    for g in s.get("graphics", []):
        st, en = fr(g["start"]), fr(g["end"])
        (v3 if s.get("dialogue") else v2).append(still(g["file"], st, en, g.get("scale", 100)))
        rep.append(f"{g['start']:6.2f}-{g['end']:6.2f}  GFX {g['file'].split('/')[-1]}")
    total = max([t] + [fr(b["end"]) for b in s.get("broll", [])] + [fr(g["end"]) for g in s.get("graphics", [])])
    mk = "".join(f"<marker><name>{escape(m['name'])}</name><comment>{escape(m.get('comment',''))}</comment><in>{fr(m['t'])}</in><out>-1</out></marker>" for m in s.get("markers", []))
    out.append(f'<sequence id="seq-{escape(name)}"><name>{escape(name)}</name><duration>{total}</duration>{RATE}'
               f'<timecode>{RATE}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>'
               f'<media><video><format><samplecharacteristics>{RATE}<width>{W}</width><height>{H}</height>'
               f'<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></format>'
               f'{track(v1)}{track(v2)}{track(v3)}</video><audio><numOutputChannels>2</numOutputChannels>{track(a1)}{track(a2)}</audio></media>{mk}</sequence>')
    from collections import Counter
    dup = [c for c, n in Counter(b["clip"] for b in s.get("broll", [])).items() if n > 1]
    print(f"== {name}  {total / FPS:.2f}s" + (f"  WARNING repeated b-roll: {dup}" if dup else "")); print("\n".join("   " + r for r in rep))
out.append("</xmeml>")
open(OUT, "w").write("\n".join(out))
print("wrote", OUT)
