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
     "music": [ {"file": "/abs/song_edit.wav", "in": 0, "start": 0, "end": 63.4, "gain_db": 0} ],
        # stereo music pair on A1/A2 (A3/A4 when there is dialogue/VO). Premiere 26.5 renders this pair as MONO:
        # check the first review render and re-import the WAV as a normal stereo clip (reference/premiere.md)
     "markers": [ {"t": 0, "name": "MUSIC START", "comment": "..."} ],
     "width": 3840, "height": 2160 } } }   # optional per-sequence frame size override
  b-roll items also take "xoff" (9:16 crop-centre shift in source px, 3840-wide reference, same as vcrop_strip.py),
  "center": [h, v] (raw FCP Basic Motion center), and "track": 1-4 (stacked/split-screen layers; graphics then go on V3 unless they set their own "track"; empty tracks below the top used one are kept, e.g. an empty V2 for an adjustment layer).
  Clip paths may be absolute (e.g. slow-motion renders in _edit/).
  Dialogue items also take "xoff"/"center" (same as b-roll). Spec "fps" may be any NTSC rate (23.976/29.97/59.94).
  b-roll/dialogue items also take "scale" (default "broll_scale" at spec level; "auto" = fill the frame: horizontal
  source in a vertical sequence -> 177.78, rotated/vertical-native or matching orientation -> 100).
  Mixed-rate media (29.97 drone, 59.94 FX3) is placed with in/out counted at the sequence rate (what Premiere expects).
Prints a timeline report. Source media is only read (ffprobe/ffmpeg loudness)."""
import json, os, re, subprocess, sys, urllib.parse
from xml.sax.saxutils import escape

spec = json.load(open(sys.argv[1])); OUT = sys.argv[2]
ROOT = (os.environ.get("MEDIA_ROOT") or spec["media_root"]).replace("\\", "/").rstrip("/")  # MEDIA_ROOT: same drive, other machine (e.g. E:/MyDrive)
_f = spec.get("fps", 23.976)   # NTSC rates (23.976, 29.97, 59.94) -> exact n*1000/1001 and ntsc TRUE
FPS = round(_f) * 1000 / 1001 if abs(_f - round(_f) * 1000 / 1001) < 0.01 else _f
TB, NTSC = round(FPS), ("TRUE" if abs(FPS - round(FPS)) > 0.001 else "FALSE")
RATE = f"<rate><timebase>{TB}</timebase><ntsc>{NTSC}</ntsc></rate>"
fr = lambda s: int(round(s * FPS))
_dur = {}; _info = {}

P = lambda clip: clip if clip.startswith("/") else f"{ROOT}/{clip}"  # absolute paths (renders in _edit/) pass through

def info(clip):
    """(fps, timebase, ntsc, rotated, w, h) of the clip's video stream."""
    if clip not in _info:
        j = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-select_streams", "v:0", "-show_streams", "-of", "json", P(clip)],
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
        o = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", P(clip)],
                           capture_output=True, text=True).stdout
        _dur[clip] = float(o)
    return _dur[clip]

def lufs(clip, a, b):
    o = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(a), "-t", str(b - a), "-i", P(clip), "-vn",
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
        o = subprocess.run(["ffprobe", "-v", "quiet", "-select_streams", "a", "-show_entries", "stream=channels", "-of", "csv=p=0", P(clip)],
                           capture_output=True, text=True).stdout.split()
        _ach[clip] = sum(int(x) for x in o if x.strip().isdigit())
    return _ach[clip]

def has_video(clip):
    return bool(subprocess.run(["ffprobe", "-v", "quiet", "-select_streams", "v", "-show_entries", "stream=index", "-of", "csv=p=0", P(clip)],
                               capture_output=True, text=True).stdout.strip())

def file_xml(clip):
    fid = "file-" + re.sub(r"[^A-Za-z0-9]", "_", clip)
    if fid in done_files:
        return f'<file id="{fid}"/>'
    done_files.add(fid)
    url = file_url(P(clip))
    return (f'<file id="{fid}"><name>{escape(clip.split("/")[-1])}</name><pathurl>{url}</pathurl>{RATE}'
            f'<duration>{fr(duration(clip))}</duration><media>' + ('<video/>' if has_video(clip) else '')
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

def motion(scale, center=None):
    """center: (h, v) offsets as FCP7 Basic Motion center (0,0 = centred; Premiere position x = 0.5 + h*media_w/seq_w)."""
    if scale == 100 and not center: return ""
    cen = ('<parameter authoringApp="PremierePro"><parameterid>center</parameterid><name>Center</name>'
           f'<value><horiz>{center[0]}</horiz><vert>{center[1]}</vert></value></parameter>') if center else ""
    return ('<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion</effectcategory>'
            '<effecttype>motion</effecttype><mediatype>video</mediatype><parameter authoringApp="PremierePro">'
            f'<parameterid>scale</parameterid><name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax><value>{scale}</value></parameter>{cen}</effect></filter>')

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
def vtracks(ts):   # keep empty tracks below the highest used one (e.g. an empty V2 reserved for an adjustment layer)
    top = max([i for i, t in enumerate(ts) if t] or [0])
    return "".join("<track>" + "".join(t) + "<enabled>TRUE</enabled><locked>FALSE</locked></track>" for t in ts[:top + 1])
out = ['<?xml version="1.0" encoding="UTF-8"?>', "<!DOCTYPE xmeml>", '<xmeml version="4">']
for name, s in spec["sequences"].items():
    v1, v2, v3, v4, a1, a2, a3, a4, rep = [], [], [], [], [], [], [], [], []
    t = 0
    W, H = s.get("width", spec["width"]), s.get("height", spec["height"])
    def sc(x):
        v = x.get("scale", spec.get("broll_scale", 100))
        return auto_scale(x["clip"], W, H) if v == "auto" else v
    def xcen(x, S):   # "xoff" crop-centre shift -> FCP center (see b-roll note below); "center" wins
        if x.get("center") is not None or not x.get("xoff"): return x.get("center")
        mw = info(x["clip"])[4]; X = 0.5 - x["xoff"] * (mw / 3840) * (S / 100) / W; return (round((X - 0.5) * 3, 4), 0)
    for d in s.get("dialogue", []):
        st = fr(d["at"]) if "at" in d else t
        en = st + fr(d["out"] - d["in"])
        L = lufs(d["clip"], d["in"], d["out"])
        db = min(spec.get("max_gain_db", 12), spec.get("target_lufs", -19) - L)
        lin = round(10 ** (db / 20), 4)
        v1.append(item(d["clip"], st, en, d["in"], extra=motion(sc(d), xcen(d, sc(d)))))
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
    vt = {1: v1, 2: v2, 3: v3, 4: v4}
    for b in s.get("broll", []):
        st, en = fr(b["start"]), fr(b["end"])
        S = sc(b); cen = b.get("center")
        if cen is None and b.get("xoff"):   # crop-centre shift in source px (3840-wide reference), as vcrop_strip/preview_from_spec
            # Wanted Premiere Position X = 0.5 - xoff*(media_w/3840)*(S/100)/seq_w. Premiere 26.5 maps FCP center h to
            # Position X = 0.5 + h/3 (measured 2026-10-13: 3840 media at 177.78% in 2160x3840; h -0.1157 -> X 0.4614). Verify by frame.
            mw = info(b["clip"])[4]; X = 0.5 - b["xoff"] * (mw / 3840) * (S / 100) / W; cen = (round((X - 0.5) * 3, 4), 0)
        tr = b.get("track") or (2 if s.get("dialogue") else 1)   # "track": put stacked layers on V1-V3
        vt[tr].append(item(b["clip"], st, en, b["in"], extra=motion(S, cen)))
        rep.append(f"{b['start']:6.2f}-{b['end']:6.2f}  V{tr}  {b['clip'].split('/')[-1]} @ {b['in']}  scale {S}%" + (f" center {cen}" if cen else "") + f"  ({info(b['clip'])[0]:.3f} fps src)")
    for m in s.get("music", []):   # {"file": abs path, "in": src s, "start": t, "end": t, "gain_db": 0} -> stereo pair on A3/A4 (A1/A2 if no dialogue/VO)
        st, en = fr(m["start"]), fr(m["end"]); lin = round(10 ** (m.get("gain_db", 0) / 20), 4)
        ta, tb = (a3, a4) if (s.get("dialogue") or s.get("vo")) else (a1, a2)
        ta.append(item(m["file"], st, en, m.get("in", 0), 1, levels(lin))); tb.append(item(m["file"], st, en, m.get("in", 0), 2, levels(lin)))
        rep.append(f"{m['start']:6.2f}-{m['end']:6.2f}  MUSIC {m['file'].split('/')[-1]} @ {m.get('in', 0)}  {m.get('gain_db', 0):+.1f} dB")
    for g in s.get("graphics", []):
        st, en = fr(g["start"]), fr(g["end"])
        gt = g.get("track") or (3 if (s.get("dialogue") or any(b.get("track") for b in s.get("broll", []))) else 2)   # "track": 1-4 for the still
        vt[gt].append(still(g["file"], st, en, g.get("scale", 100)))
        rep.append(f"{g['start']:6.2f}-{g['end']:6.2f}  GFX {g['file'].split('/')[-1]}")
    total = max([t] + [fr(b["end"]) for b in s.get("broll", [])] + [fr(g["end"]) for g in s.get("graphics", [])] + [fr(m["end"]) for m in s.get("music", [])])
    mk = "".join(f"<marker><name>{escape(m['name'])}</name><comment>{escape(m.get('comment',''))}</comment><in>{fr(m['t'])}</in><out>-1</out></marker>" for m in s.get("markers", []))
    out.append(f'<sequence id="seq-{escape(name)}"><name>{escape(name)}</name><duration>{total}</duration>{RATE}'
               f'<timecode>{RATE}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>'
               f'<media><video><format><samplecharacteristics>{RATE}<width>{W}</width><height>{H}</height>'
               f'<anamorphic>FALSE</anamorphic><pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance></samplecharacteristics></format>'
               f'{vtracks([v1, v2, v3, v4])}</video><audio><numOutputChannels>2</numOutputChannels>{track(a1)}{track(a2)}{track(a3)}{track(a4)}</audio></media>{mk}</sequence>')
    from collections import Counter
    dup = [c for c, n in Counter(b["clip"] for b in s.get("broll", [])).items() if n > 1]
    print(f"== {name}  {total / FPS:.2f}s" + (f"  WARNING repeated b-roll: {dup}" if dup else "")); print("\n".join("   " + r for r in rep))
out.append("</xmeml>")
open(OUT, "w").write("\n".join(out))
print("wrote", OUT)
