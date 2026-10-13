# Final-render QC from the sequence's FCP7 XML + the rendered file: per visible shot tone (p2/p50/p98), tint (Lab a*/b* on near-neutral pixels), chroma, foliage chroma (greens) and Warp Stabilizer "analyzing" banners; plus a whole-film scan for held/duplicated frames. Usage: scripts/vpy render_qc.py seq.xml render.mp4 [out.json]
import xml.etree.ElementTree as ET, sys, subprocess, json
import numpy as np, cv2
from scipy.ndimage import median_filter

TB = 24000 / 1001


def shots_from_xml(path):
    seq = ET.parse(path).getroot().find('.//sequence')
    dur = int(seq.findtext('duration'))
    top = [None] * dur
    for ti, tr in enumerate(seq.find('media/video').findall('track')):
        for c in tr.findall('clipitem'):
            s, e, nm = int(c.findtext('start')), int(c.findtext('end')), c.findtext('name')
            if s < 0 or c.findtext('enabled') == 'FALSE' or 'Adjustment' in nm or nm == 'Graphic':
                continue
            for f in range(s, min(e, dur)):
                top[f] = (nm, s, ti + 1)
    shots, cur = [], None
    for f, t in enumerate(top):
        if t != cur:
            shots.append([t, f, f + 1]); cur = t
        else:
            shots[-1][2] = f + 1
    return shots


def frame(vid, t, w=480):
    b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', vid, '-frames:v', '1', '-vf', f'scale={w}:-2',
                        '-pix_fmt', 'bgr24', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(b, np.uint8).reshape(-1, w, 3)


def shot_stats(f):
    H = f.shape[0]
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)[int(H * .06):int(H * .94)]
    lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB).astype(float)
    L, A, B = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    C = np.hypot(A, B)
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    neutral = (C < np.percentile(C, 40)) & (L > 50) & (L < 220)
    mid = (L > 40) & (L < 230)
    green = (hsv[..., 0] >= 30) & (hsv[..., 0] <= 90) & (hsv[..., 2] > 40) & (C > 6)
    blue = ((f[..., 0] > 200) & (f[..., 1] < 70) & (f[..., 2] < 30)).mean(1)
    return dict(p2=float(np.percentile(g, 2)), p50=float(np.percentile(g, 50)), p98=float(np.percentile(g, 98)),
                a=float(A[neutral].mean()) if neutral.any() else 0, b=float(B[neutral].mean()) if neutral.any() else 0,
                chroma=float(C[mid].mean()), c90=float(np.percentile(C[mid], 90)),
                green=float(C[green].mean()) if green.mean() > 0.03 else None, ws_banner_rows=int((blue > 0.6).sum()))


def held_frames(vid, w=192, h=96):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', vid, '-vf', f'scale={w}:{h}', '-pix_fmt', 'gray', '-f', 'rawvideo', '-'],
                         stdout=subprocess.PIPE)
    prev, d = None, []
    while True:
        b = p.stdout.read(w * h)
        if len(b) < w * h:
            break
        x = np.frombuffer(b, np.uint8).astype(np.int16)
        d.append(np.abs(x - prev).mean() if prev is not None else 99); prev = x
    d = np.array(d); med = median_filter(d, size=9)
    # a frame that barely changes while its neighbours move = held/duplicated frame (slow motion gives false hits; check by eye)
    return [(i, round(i / TB, 2), round(float(d[i]), 2)) for i in range(5, len(d) - 5) if d[i] < 0.4 * med[i] and med[i] > 0.6 and d[i] < 1.0]


def main(xml_path, vid, out=None):
    rows = []
    for t, s, e in shots_from_xml(xml_path):
        if t is None:
            rows.append(dict(name='GAP', s=round(s / TB, 2), e=round(e / TB, 2))); continue
        st = shot_stats(frame(vid, (s + e) / 2 / TB))
        rows.append(dict(name=t[0], track=t[2], s=round(s / TB, 2), e=round(e / TB, 2), **st))
    holds = held_frames(vid)
    print(len(rows), 'shots |', sum(r['name'] == 'GAP' for r in rows), 'gaps | WS banners:',
          [(r['s'], r['name']) for r in rows if r.get('ws_banner_rows', 0) > 0])
    print('possible held frames (frame, s, diff):', holds)
    if out:
        json.dump(dict(shots=rows, held=holds), open(out, 'w'), indent=0)


if __name__ == '__main__':
    main(*sys.argv[1:4])
