#!/usr/bin/env python3
"""Match ungraded shots to the editor's hand-corrected ones (Lumetri Basic Correction).

usage: cc_match.py out.json SEQ1.xml:RENDER1.mp4 [SEQ2.xml:RENDER2.mp4 ...]

- SEQ.xml is an FCP XML export of the sequence; RENDER.mp4 a full render of it (same timing).
- Visible shots = V2 clips plus the parts of V1 not covered by V2.
- A clip the editor graded shows up in FCP XML as an effect with an empty <name> (XML drops Lumetri).
- Run it BEFORE adding your own corrections: any clip with Lumetri counts as graded.
- Per shot: luma p5/p50/p95 and R-B / G-M casts (percent), from 5 frames.
- Prints a proposed correction for each ungraded shot, aimed at the graded median, in the editor's
  vocabulary (Highlights, Shadows, small Tint/Temperature; no exposure/contrast/whites/blacks).

Calibration (Lumetri on the clip, before a creative LUT on an adjustment layer, Oct 2026):
  Highlights +20 -> p95 +5;  Shadows +30 -> p50 +9.5 (p5/p95 +4.5).
  Shots that hit +45 and still sit low can go to 55-60. Do not lift shadows when p5 is already
  high (raised blacks read flatter).
"""
import sys, json, subprocess, xml.etree.ElementTree as ET
import numpy as np

FR = 1001 / 24000


def shots(xmlp):
    seq = ET.parse(xmlp).getroot().find('.//sequence')
    tr = seq.findall('media/video/track')
    items = []
    for ti, t in enumerate(tr[:2]):
        for c in t.findall('clipitem'):
            names = [e.findtext('name') for e in c.findall('filter/effect')]
            items.append(dict(tr=ti, st=int(c.findtext('start')), en=int(c.findtext('end')),
                              name=c.findtext('name'), graded=any(not n for n in names)))
    v2 = [i for i in items if i['tr'] == 1]
    out = []
    for s in [i for i in items if i['tr'] == 0]:
        segs = [(s['st'], s['en'])]
        for v in v2:
            ns = []
            for a, b in segs:
                if v['en'] <= a or v['st'] >= b:
                    ns.append((a, b)); continue
                if a < v['st']: ns.append((a, v['st']))
                if v['en'] < b: ns.append((v['en'], b))
            segs = ns
        out += [dict(s, st=a, en=b) for a, b in segs if b - a >= 6]
    return sorted(out + v2, key=lambda x: x['st'])


def stats(mp4, a, b):
    ys, rb, gm = [], [], []
    for k in range(5):
        t = (a + (b - a) * (0.2 + 0.15 * k)) * FR
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', mp4, '-frames:v', '1',
                              '-vf', 'scale=216:384', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                             capture_output=True).stdout
        im = np.frombuffer(raw, np.uint8).reshape(384, 216, 3).astype(float) / 255
        Y = 0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2]
        ys.append(Y.ravel())
        m = (Y > 0.2) & (Y < 0.8)
        rb.append((im[..., 0] - im[..., 2])[m].mean())
        gm.append((im[..., 1] - (im[..., 0] + im[..., 2]) / 2)[m].mean())
    Y = np.concatenate(ys)
    return dict(zip(('p5', 'p50', 'p95'), [round(float(np.percentile(Y, p)) * 100, 1) for p in (5, 50, 95)]),
                rb=round(float(np.mean(rb)) * 100, 1), gm=round(float(np.mean(gm)) * 100, 1))


def r5(x): return int(round(x / 5.0) * 5)


def propose(s, ref):
    H = r5(min(max((ref['p95'] - s['p95']) / 0.25, 0), 45))
    S = 0
    if s['p50'] < ref['p50'] - 10 and s['p5'] < ref['p5'] + 6:
        S = r5(min(max((ref['p50'] - 5 - s['p50'] - 0.2 * H) / 0.3, 0), 35))
    tint = -2 if s['gm'] < ref['gm'] - 5 else (2 if s['gm'] > ref['gm'] + 3 else 0)
    temp = -3 if s['rb'] > ref['rb'] + 15 else (2 if s['rb'] < ref['rb'] - 15 else 0)
    return dict(Highlights=H, Shadows=S, Tint=tint, Temperature=temp)


res = []
for pair in sys.argv[2:]:
    xmlp, mp4 = pair.split(':', 1)
    for s in shots(xmlp):
        res.append(dict(src=mp4.rsplit('/', 1)[-1], t=round(s['st'] * FR, 2), name=s['name'],
                        tr=s['tr'] + 1, graded=s['graded'], **stats(mp4, s['st'], s['en'])))
G = [x for x in res if x['graded']]
if not G:
    sys.exit('no graded shots found (no empty-name effects in the XML)')
ref = {k: float(np.median([x[k] for x in G])) for k in ('p5', 'p50', 'p95', 'rb', 'gm')}
print('graded reference (median of %d):' % len(G), ref)
for x in res:
    p = None if x['graded'] else propose(x, ref)
    x['proposal'] = p
    tag = 'G' if x['graded'] else '.'
    print(f"{tag} {x['src'][:12]:12} V{x['tr']} {x['t']:6.2f} {x['name'][:28]:28} "
          f"p5 {x['p5']:5.1f} p50 {x['p50']:5.1f} p95 {x['p95']:5.1f} R-B {x['rb']:5.1f} G-M {x['gm']:5.1f}  {p or ''}")
json.dump(dict(ref=ref, shots=res), open(sys.argv[1], 'w'), indent=1)
