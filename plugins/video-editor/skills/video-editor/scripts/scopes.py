#!/usr/bin/env python3
"""Broadcast-style scopes for graded frames (PNG/JPG exported from the sequence, e.g. export_sequence_clip_review_frames).
For every frame: luma waveform (IRE), RGB parade, vectorscope (Rec.709 Cb/Cr with the skin-tone line and 75% targets) and a
luma histogram, rendered next to a thumbnail, plus a numbers table:
  black/white point in IRE (0.5th / 99.5th pct), % clipped (<= 0 IRE, >= 100 IRE), median IRE,
  neutral balance (R-B and G-M of near-neutral pixels in shadows / mids / highlights, in 8-bit code values; + = warm / green),
  saturation (median and 95th pct, % of the 75% graticule), and the skin-hue offset from the skin line (degrees, + = toward yellow).
Usage: vpy scopes.py OUT_PREFIX FRAME [FRAME ...] [--labels a,b,c] [--cols 4]
Writes OUT_PREFIX_sheet.jpg and OUT_PREFIX.csv. Flags in the table: CLIP-B / CLIP-W (>1% clipped), CAST (|R-B| > 6 or |G-M| > 5
in mids), SAT (95th pct > 100% of the 75% graticule), SKIN (skin hue > 8 deg off the line)."""
import sys, csv, numpy as np
from PIL import Image, ImageDraw
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
out = a[0]; files = [f for f in a[1:] if not f.startswith("--") and f not in (opt("--labels", None), opt("--cols", None))]
labels = opt("--labels", ",".join(f.split("/")[-1].rsplit(".", 1)[0] for f in files)).split(",")
cols = int(opt("--cols", 4))
SK = np.deg2rad(123.0)                       # skin-tone line on a Rec.709 vectorscope (I-line), measured from +Cb axis

def analyze(path, S=256):
    im = Image.open(path).convert("RGB"); w, h = im.size
    sm = im.resize((480, int(480 * h / w))); x = np.asarray(sm).astype(float)
    R, G, B = x[..., 0], x[..., 1], x[..., 2]
    Y = 0.2126 * R + 0.7152 * G + 0.0722 * B; ire = Y / 255 * 100
    Cb = (B - Y) / 1.8556; Cr = (R - Y) / 1.5748; sat = np.hypot(Cb, Cr)
    sat75 = 0.75 * 255 * np.hypot(*(lambda r, g, b: (((b - (0.2126*r+0.7152*g+0.0722*b)) / 1.8556), ((r - (0.2126*r+0.7152*g+0.0722*b)) / 1.5748)))(1, 0, 0))
    res = dict(black=np.percentile(ire, 0.5), white=np.percentile(ire, 99.5), med=np.median(ire),
               clipb=(ire <= 0.5).mean() * 100, clipw=(ire >= 99.5).mean() * 100,
               sat50=np.median(sat) / sat75 * 100, sat95=np.percentile(sat, 95) / sat75 * 100)
    neu = sat < np.percentile(sat, 30)       # least-saturated 30% = reference neutrals
    for name, lo, hi in (("sh", 0, 30), ("mid", 30, 70), ("hi", 70, 101)):
        m = neu & (ire >= lo) & (ire < hi)
        res["rb_" + name] = (R[m] - B[m]).mean() if m.sum() > 200 else np.nan
        res["gm_" + name] = (G[m] - (R[m] + B[m]) / 2).mean() if m.sum() > 200 else np.nan
    ang = np.arctan2(Cr, Cb); sk = (sat > 0.08 * sat75) & (np.abs(ang - SK) < np.deg2rad(25)) & (ire > 25) & (ire < 85)
    res["skin_n"] = sk.mean() * 100
    res["skin_off"] = np.rad2deg(np.median(ang[sk]) - SK) if sk.sum() > 300 else np.nan
    # --- scope images (S x S each) ---
    hh = S
    wf = np.zeros((hh, sm.width)); par = np.zeros((hh, sm.width * 3, 3))
    yi = np.clip((ire / 100 * (hh - 1)).astype(int), 0, hh - 1)
    for c in range(sm.width): np.add.at(wf[:, c], hh - 1 - yi[:, c], 1)
    for k, ch in enumerate((R, G, B)):
        ci = np.clip((ch / 255 * (hh - 1)).astype(int), 0, hh - 1)
        for c in range(sm.width): np.add.at(par[:, k * sm.width + c, k], hh - 1 - ci[:, c], 1)
    wf = np.clip(np.log1p(wf) / np.log1p(wf.max() + 1e-9) * 1.4, 0, 1)
    par = np.clip(np.log1p(par) / np.log1p(par.max() + 1e-9) * 1.4, 0, 1)
    wfi = Image.fromarray((np.stack([wf * 0.6, wf, wf * 0.6], -1) * 255).astype(np.uint8)).resize((S, S))
    pai = Image.fromarray((par * 255).astype(np.uint8)).resize((S, S))
    vs = np.zeros((S, S)); r = S / 2 - 4
    px = (S / 2 + Cb / sat75 * r * 0.75 / 0.75).astype(int); py = (S / 2 - Cr / sat75 * r).astype(int)
    ok = (px >= 0) & (px < S) & (py >= 0) & (py < S); np.add.at(vs, (py[ok], px[ok]), 1)
    vs = np.clip(np.log1p(vs) / np.log1p(vs.max() + 1e-9) * 1.5, 0, 1)
    vsi = Image.fromarray((np.stack([vs, vs, vs * 0.7], -1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(vsi); c0 = S / 2
    d.ellipse([c0 - r, c0 - r, c0 + r, c0 + r], outline=(70, 70, 70))
    d.line([c0, c0, c0 + r * np.cos(SK), c0 - r * np.sin(SK)], fill=(255, 150, 60))
    for (rr, gg, bb), lab in (((1, 0, 0), "R"), ((0, 1, 0), "G"), ((0, 0, 1), "B"), ((0, 1, 1), "C"), ((1, 0, 1), "M"), ((1, 1, 0), "Y")):
        yy = 0.2126 * rr + 0.7152 * gg + 0.0722 * bb; cb = (bb - yy) / 1.8556; cr = (rr - yy) / 1.5748
        tx = c0 + cb * 0.75 * 255 / sat75 * r; ty = c0 - cr * 0.75 * 255 / sat75 * r
        d.rectangle([tx - 3, ty - 3, tx + 3, ty + 3], outline=(120, 120, 120)); d.text((tx + 4, ty - 6), lab, fill=(150, 150, 150))
    hist, _ = np.histogram(ire, bins=S, range=(0, 100)); hist = hist / hist.max()
    hi_ = Image.new("RGB", (S, S), (12, 12, 12)); dh = ImageDraw.Draw(hi_)
    for i, v in enumerate(hist): dh.line([i, S - 1, i, S - 1 - int(v * (S - 4))], fill=(200, 200, 200))
    for img in (wfi, pai):
        dd = ImageDraw.Draw(img)
        for lv in (0, 25, 50, 75, 100): yv = int((1 - lv / 100) * (S - 1)); dd.line([0, yv, S, yv], fill=(60, 60, 60)); dd.text((2, max(0, yv - 10)), str(lv), fill=(120, 120, 120))
    th = im.resize((int(S * w / h), S))
    return res, [th, wfi, pai, vsi, hi_]

rows, tiles = [], []
for f, lab in zip(files, labels):
    r_, t_ = analyze(f); r_["label"] = lab
    flags = []
    if r_["clipb"] > 1: flags.append("CLIP-B")
    if r_["clipw"] > 1: flags.append("CLIP-W")
    if abs(np.nan_to_num(r_["rb_mid"])) > 6 or abs(np.nan_to_num(r_["gm_mid"])) > 5: flags.append("CAST")
    if r_["sat95"] > 100: flags.append("SAT")
    if not np.isnan(r_["skin_off"]) and abs(r_["skin_off"]) > 8: flags.append("SKIN")
    r_["flags"] = " ".join(flags); rows.append(r_); tiles.append((lab, t_))
S = 256; tw = tiles[0][1][0].width + 4 * S + 5 * 4; th = S + 22
sheet = Image.new("RGB", (cols * (tw + 10), ((len(tiles) + cols - 1) // cols) * th), (0, 0, 0)); d = ImageDraw.Draw(sheet)
for k, (lab, t_) in enumerate(tiles):
    X = (k % cols) * (tw + 10); Y = (k // cols) * th; x = X
    r_ = rows[k]
    d.text((X + 2, Y + 4), f"{lab}  B {r_['black']:.0f} W {r_['white']:.0f} IRE  sat95 {r_['sat95']:.0f}%  {r_['flags']}", fill=(255, 220, 120) if r_["flags"] else (220, 220, 220))
    for img in t_: sheet.paste(img, (x, Y + 22)); x += img.width + 4
sheet.save(out + "_sheet.jpg", quality=85)
keys = ["label", "black", "white", "med", "clipb", "clipw", "rb_sh", "rb_mid", "rb_hi", "gm_sh", "gm_mid", "gm_hi", "sat50", "sat95", "skin_n", "skin_off", "flags"]
with open(out + ".csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(keys)
    for r_ in rows: w.writerow([r_[k] if isinstance(r_[k], str) else round(float(r_[k]), 1) for k in keys])
print(f"{'shot':11s} {'blk':>4s} {'wht':>4s} {'med':>4s} {'clB%':>5s} {'clW%':>5s} {'R-B mid':>7s} {'G-M mid':>7s} {'sat50':>5s} {'sat95':>5s} {'skin°':>6s}  flags")
for r_ in rows:
    print(f"{r_['label']:11s} {r_['black']:4.0f} {r_['white']:4.0f} {r_['med']:4.0f} {r_['clipb']:5.1f} {r_['clipw']:5.1f} {r_['rb_mid']:7.1f} {r_['gm_mid']:7.1f} {r_['sat50']:5.0f} {r_['sat95']:5.0f} {r_['skin_off']:6.1f}  {r_['flags']}")
print(out + "_sheet.jpg")
