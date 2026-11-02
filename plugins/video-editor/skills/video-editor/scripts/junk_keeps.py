# junk_keeps.py SCANDIR OUT.json : keep ranges per clip from scan_thumbs.py csvs, cutting ONLY unusable junk (an editor's raw-selects note:
# "truly only cut something that's not usable"; keep reframes/zooms, people walking through frame, repositioning; nothing under 3 s).
# Junk sample = whip with motion blur (motion > 40 px/frame at 320w AND sharpness < 0.5x local +-5 s median), or motion > 80, or black (luma < 12).
# Mid-take junk is cut only when it lasts >= MIN_MID s (env, default 1.0); at a take's head/tail >= 0.5 s (setup / swing at record stop).
# Pieces under 3 s are merged back into a neighbour across the gap (shake and all) or dropped if isolated. See recipes/raw-selects-delivery.md
import sys, glob, os, json, numpy as np
d, out = sys.argv[1], sys.argv[2]
MIN_MID = float(os.environ.get("MIN_MID", 1.0)); MIN_KEEP = 3.0; FPSS = 6
res = {}
for f in sorted(glob.glob(f"{d}/C*.csv")):
    n = os.path.basename(f)[:-4]; a = np.loadtxt(f, delimiter=',')
    if a.ndim < 2 or len(a) < 2: res[n] = {"dur": 0, "keep": []}; continue
    mv, sh, lu = a[:, 1], a[:, 2], a[:, 3]; N = len(a); dur = N / FPSS
    med = np.array([np.median(sh[max(0, i - 30):i + 31]) for i in range(N)])
    junk = ((mv > 40) & (sh < 0.5 * med)) | (mv > 80) | (lu < 12)
    junk[1:-1] |= junk[:-2] & junk[2:]                      # bridge single-sample holes inside a whip
    runs = []; i = 0                                         # junk runs [i, j) in samples
    while i < N:
        if junk[i]:
            j = i
            while j < N and junk[j]: j += 1
            runs.append([i, j]); i = j
        else: i += 1
    merged = []                                              # join runs separated by < 0.5 s
    for r in runs:
        if merged and r[0] - merged[-1][1] < 3: merged[-1][1] = r[1]
        else: merged.append(r)
    cuts = []
    for s0, e0 in merged:
        edge = s0 <= FPSS or e0 >= N - FPSS                  # touches the first/last second of the take
        if (e0 - s0) / FPSS >= (0.5 if edge else MIN_MID):
            s1, e1 = max(0, s0 - 1), min(N, e0 + 1)          # pad 1 sample
            if s1 <= FPSS: s1 = 0                            # head junk: cut from the start
            if e1 >= N - FPSS: e1 = N                        # tail junk: cut to the end
            cuts.append([s1 / FPSS, e1 / FPSS])
    keeps = []; t = 0.0
    for c0, c1 in cuts:
        if c0 > t: keeps.append([t, c0])
        t = max(t, c1)
    if t < dur: keeps.append([t, dur])
    changed = True                                           # merge pieces under 3 s into a neighbour (restoring the gap)
    while changed:
        changed = False
        for k, (s, e) in enumerate(keeps):
            if e - s >= MIN_KEEP: continue
            gl = s - keeps[k - 1][1] if k > 0 else 1e9; gr = keeps[k + 1][0] - e if k + 1 < len(keeps) else 1e9
            if min(gl, gr) <= 3.0:
                if gl <= gr: keeps[k - 1][1] = e
                else: keeps[k + 1][0] = s
            keeps.pop(k); changed = True; break
    keep = [[round(s, 2), round(min(e, dur - 0.05), 2)] for s, e in keeps if min(e, dur - 0.05) - s >= MIN_KEEP]
    res[n] = {"dur": round(dur, 2), "keep": keep}
json.dump(res, open(out, "w"), indent=0)
tot = sum(r["dur"] for r in res.values()); kept = sum(e - s for r in res.values() for s, e in r["keep"])
pieces = [e - s for r in res.values() for s, e in r["keep"]]
for n, r in res.items():
    print(n, f"{r['dur']:6.1f}", " ".join(f"{s:.1f}-{e:.1f}" for s, e in r["keep"]) or "DROP")
print(f"kept {kept/60:.1f} of {tot/60:.1f} min, {len(pieces)} pieces, shortest {min(pieces):.1f} s")
