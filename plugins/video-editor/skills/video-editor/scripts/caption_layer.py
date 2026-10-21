#!/usr/bin/env python3
"""Burned-in caption layer: cues JSON -> PNG per cue -> one frame-exact ProRes 4444 alpha .mov for the top video track.
Usage: vpy caption_layer.py CUES.json OUT_DIR --size 2160x3840 --fps 29.97 --dur 60.1267 [--font PATH] [--px 175] [--cy 0.60] [--lead 0.1]
CUES.json: [["TEXT (| = line break)", start_s, end_s], ...] in sequence time. Time cues from speech onsets in the final mix
(see speech_regions.py), not raw whisper word times (they drift up to ~1 s). --lead shows each cue that much early
(never overlapping the previous cue). Default style: Arial Black, white, black stroke, soft shadow, centred at 60% height. House style for Reels: --px 135 --stroke 0 --shadow 0
--cy 0.5 --maxw 0.70 (no outline, no punctuation in the cue text). Default font path is macOS; pass --font elsewhere."""
import json, os, sys, subprocess, argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ap = argparse.ArgumentParser(); ap.add_argument("cues"); ap.add_argument("out")
ap.add_argument("--size", default="2160x3840"); ap.add_argument("--fps", type=float, default=29.97); ap.add_argument("--dur", type=float, required=True)
ap.add_argument("--font", default="/System/Library/Fonts/Supplemental/Arial Black.ttf"); ap.add_argument("--px", type=int, default=175)
ap.add_argument("--cy", type=float, default=0.60); ap.add_argument("--lead", type=float, default=0.1); ap.add_argument("--stroke", type=int, default=16); ap.add_argument("--maxw", type=float, default=0.78); ap.add_argument("--shadow", type=int, default=150)
a = ap.parse_args(); W, H = map(int, a.size.split("x")); s = a.px / 175
F = ImageFont.truetype(a.font, a.px); MAXW = int(W * a.maxw); LH = int(205 * s)
fps = round(a.fps) * 1000 / 1001 if abs(a.fps - round(a.fps) * 1000 / 1001) < 0.01 else a.fps
rate = f"{round(a.fps)*1000}/1001" if fps != a.fps else str(a.fps)
cues = json.load(open(a.cues)); os.makedirs(f"{a.out}/png", exist_ok=True)
def wrap(t):
    if "|" in t: return t.split("|")
    out = [""]
    for w in t.split():
        test = (out[-1] + " " + w).strip()
        if F.getlength(test) <= MAXW: out[-1] = test
        else: out.append(w)
    return out
Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(f"{a.out}/png/blank.png")
for i, (t, *_rest) in enumerate(cues):
    L = wrap(t); y0 = int(H * a.cy) - LH * len(L) // 2
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(im), ImageDraw.Draw(sh)
    for k, l in enumerate(L):
        x = (W - F.getlength(l)) / 2; y = y0 + k * LH
        ds.text((x + 10 * s, y + 14 * s), l, font=F, fill=(0, 0, 0, a.shadow))
        d.text((x, y), l, font=F, fill=(255, 255, 255, 255), stroke_width=int(a.stroke * s), stroke_fill=(0, 0, 0, 255))
    Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10 * s)), im).save(f"{a.out}/png/cap_{i:02d}.png")
    if len(L) > 2: print(f"warning: cue {i} wraps to {len(L)} lines: {L}")
fr = lambda t: int(round(t * fps)); END = fr(a.dur); seg = []; cur = 0
for i, (t, st, en) in enumerate(cues):
    A, B = max(cur, fr(st - a.lead)), fr(en)
    if A > cur: seg.append(("blank.png", A - cur))
    seg.append((f"cap_{i:02d}.png", B - A)); cur = B
if END > cur: seg.append(("blank.png", END - cur))
with open(f"{a.out}/concat.txt", "w") as f:
    for p, n in seg: f.write(f"file 'png/{p}'\nduration {n/fps:.6f}\n")
    f.write(f"file 'png/{seg[-1][0]}'\n")
mov = f"{a.out}/captions.mov"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{a.out}/concat.txt", "-vf", f"fps={rate},format=yuva444p10le",
                "-frames:v", str(END), "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", mov], check=True)
print(mov, END, "frames")
