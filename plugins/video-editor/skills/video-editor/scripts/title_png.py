#!/usr/bin/env python3
"""Transparent PNG title card (tracked serif caps, hairline rule, soft shadow) at the sequence frame size,
for a static title that you animate in Premiere (Opacity/Scale keyframes). Lines are separated by '|';
a line that is just '-' draws the hairline rule.
Usage: vpy title_png.py OUT.png "SUMMER FEST|-|THE ESTATE  ·  2026" [--size 2160x3840] [--y 0.50]
       [--pt 190,0,78] [--track 0.32,0,0.30] [--gap 0.55] [--font /System/Library/Fonts/Supplemental/Didot.ttc]
       [--color 250,246,238] [--shadow 0.45] [--maxw 0.82] [--fonts "PATH#IDX;PATH#IDX"] [--scrim 0.35]
  fonts: one font per line (path#face index; last one repeats), overrides --font. Thin-hairline faces (Didot
  Regular) vanish at phone size: use a semibold serif for the name and a demi sans for small lines.
  scrim: peak alpha of a soft dark oval behind the block, so text reads over busy aerials (0 = off).
  y: centre of the block as a fraction of frame height. pt/track: per line point size and letter spacing (x size).
  maxw: the block is scaled down to fit this fraction of the width (keep inside the Reels safe area: x 6-94%,
  y 14-65% of a 9:16 frame)."""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
out, text = a[0], a[1].split("|")
W, H = map(int, opt("--size", "2160x3840").split("x")); yc = float(opt("--y", 0.5))
pts = [float(v) for v in opt("--pt", "190,0,78").split(",")]; trk = [float(v) for v in opt("--track", "0.32,0,0.30").split(",")]
gap = float(opt("--gap", 0.55)); font = opt("--font", "/System/Library/Fonts/Supplemental/Didot.ttc")
col = tuple(int(v) for v in opt("--color", "250,246,238").split(",")); shadow = float(opt("--shadow", 0.45)); maxw = float(opt("--maxw", 0.82))
fonts = [(f.split("#")[0], int(f.split("#")[1]) if "#" in f else 0) for f in opt("--fonts", font).split(";")]
fonts += [fonts[-1]] * (len(text) - len(fonts)); scrim = float(opt("--scrim", 0))
pts += [pts[-1]] * (len(text) - len(pts)); trk += [trk[-1]] * (len(text) - len(trk))

def line_img(s, pt, tr, fnt):                      # one line, letter by letter so tracking is exact
    if s.strip() == "-":
        w = int(W * 0.14); im = Image.new("L", (w, max(3, int(pt or 4))), 0); ImageDraw.Draw(im).rectangle([0, 0, w, 2], fill=255); return im
    f = ImageFont.truetype(fnt[0], int(pt), index=fnt[1]); adv = [f.getlength(c) for c in s]
    w = int(sum(adv) + tr * pt * (len(s) - 1)) + 4; asc, desc = f.getmetrics()
    im = Image.new("L", (w, asc + desc), 0); d = ImageDraw.Draw(im); x = 0
    for c, ad in zip(s, adv): d.text((x, 0), c, font=f, fill=255); x += ad + tr * pt
    return im
lines = [line_img(s, p, t, f) for s, p, t, f in zip(text, pts, trk, fonts)]
sp = [int(gap * max(p, 60)) for p in pts]
bw = max(l.width for l in lines); bh = sum(l.height for l in lines) + sum(sp[:-1])
k = min(1.0, maxw * W / bw)
mask = Image.new("L", (W, H), 0); y = int(yc * H - bh * k / 2)
for l, s in zip(lines, sp):
    l2 = l.resize((max(1, int(l.width * k)), max(1, int(l.height * k))), Image.LANCZOS)
    mask.paste(l2, ((W - l2.width) // 2, y)); y += int((l.height + s) * k)
sh = mask.filter(ImageFilter.GaussianBlur(W / 180)).point(lambda v: int(v * shadow))
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
if scrim > 0:                                  # soft oval behind the block, feathered well past the text
    yy, xx = np.mgrid[0:H, 0:W]; cy = yc * H; ry = bh * k * 1.6 + H * 0.04; rx = W * 0.75
    r = np.sqrt(((xx - W / 2) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    sc = Image.fromarray((np.clip(1 - r, 0, 1) ** 1.6 * 255 * scrim).astype(np.uint8))
    img.paste(Image.new("RGBA", (W, H), (0, 0, 0, 255)), (0, 0), sc)
img.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [sh]), (0, int(W / 400)))
img.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), v) for v in col] + [mask]))
img.save(out); print(out, f"{W}x{H}", f"block {int(bw * k)}x{int(bh * k)} px, scale {k:.2f}")
