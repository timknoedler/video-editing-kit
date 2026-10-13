# Compare two FCP7 XML exports of the same sequence frame by frame: the full enabled video layer stack (clip name + source frame, bottom to top) and each clip's effect parameters. Use it to prove a track reorg / clip move changed nothing on screen. Usage: scripts/vpy xml_stack_diff.py before.xml after.xml
import xml.etree.ElementTree as ET, sys, itertools

TB = 24000 / 1001


def load(path):
    seq = ET.parse(path).getroot().find('.//sequence')
    dur = int(seq.findtext('duration'))
    stack = [[] for _ in range(dur)]
    fx = {}
    trans = []
    for ti, tr in enumerate(seq.find('media/video').findall('track')):
        for t in tr.findall('transitionitem'):
            trans.append((t.findtext('effect/name'), t.findtext('start'), t.findtext('end'), t.findtext('alignment')))
        for c in tr.findall('clipitem'):
            s, e = int(c.findtext('start')), int(c.findtext('end'))
            name = c.findtext('name')
            if c.findtext('enabled') == 'FALSE' or s < 0:
                continue
            i = int(c.findtext('in') or 0)
            for f in range(s, min(e, dur)):
                stack[f].append((name, i + f - s))
            fx[(name, s)] = tuple(sorted(
                (fl.findtext('effect/name') or '') + str([(p.findtext('name'), p.findtext('value'), len(p.findall('keyframe')))
                                                          for p in fl.findall('effect/parameter')])
                for fl in c.findall('filter')))
    return dur, stack, fx, sorted(trans, key=str)


def main(a_path, b_path):
    da, a, fa, ta = load(a_path)
    db, b, fb, tb = load(b_path)
    print('duration', da, db)
    bad = [f for f in range(min(da, db)) if a[f] != b[f]]
    print('frames whose layer stack differs:', len(bad))
    for _, g in itertools.groupby(enumerate(bad), lambda t: t[1] - t[0]):
        g = list(g)
        s, e = g[0][1], g[-1][1]
        print(f'  {s/TB:8.2f}-{(e+1)/TB:8.2f}s ({e-s+1} fr)', set(a[s]) ^ set(b[s]))
    common = [k for k in fa if k in fb]
    diff = [k for k in common if fa[k] != fb[k]]
    print('clips', len(fa), len(fb), '| effect differences on', len(diff), 'clips:', diff[:10])
    print('note: Lumetri sometimes re-serializes empty curves/LUT fields between exports; confirm real changes with a render')
    if ta != tb:
        print('TRANSITIONS differ:\n  before', ta, '\n  after ', tb)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
