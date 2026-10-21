#!/usr/bin/env python3
"""Find which shots of a planned cut already appeared in delivered reels (cross-reel repeat check), by frame matching.
Usage: scripts/vpy reel_repeats.py SPEC.json SEQ_NAME[,SEQ2] OUT.json EXPORT.mp4 [EXPORT2.mp4 ...]
For every b-roll item in the named spec sequences, samples the WHOLE source clip (proxy if one exists) at 2 fps and builds
9:16 crop candidates at 17 horizontal offsets (full frame for vertical/rotated sources), then compares them with every
export frame (4 fps) by normalized correlation of 36x64 grey thumbnails (gain/offset-invariant, so grades don't matter).
Reports, per shot: each export where the clip appears, the export time, the matched source time, and whether that source
time falls inside (or within 1 s of) our window. Match >= 0.90 = same shot (confirm visually); 0.85-0.90 = maybe.
Caches export thumbnails in OUT_DIR/.reel_repeats_cache. Source media is only read."""
import sys, os, json, subprocess, hashlib
import numpy as np, cv2

spec = json.load(open(sys.argv[1])); seqs = sys.argv[2].split(","); OUT = sys.argv[3]; exports = sys.argv[4:]
ROOT = spec["media_root"].rstrip("/")
PROXY_ROOTS = spec.get("proxy_roots", [])
TW, TH = 36, 64
cache = os.path.join(os.path.dirname(os.path.abspath(OUT)), ".reel_repeats_cache"); os.makedirs(cache, exist_ok=True)

def norm(a):
    a = a.astype(np.float32).reshape(len(a), -1); a -= a.mean(1, keepdims=True)
    return a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-6)

def blur(a):
    return np.stack([cv2.GaussianBlur(f, (3, 3), 0) for f in a])

def frames(path, fps, w, h):
    p = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={w}:{h}:flags=area",
                        "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(p, np.uint8).reshape(-1, h, w)

def src_path(clip):
    p = clip if clip.startswith("/") else f"{ROOT}/{clip}"
    d, b = os.path.split(clip); n = os.path.splitext(b)[0]
    if not clip.startswith("/"):
        for c in [f"{ROOT}/{d}/Proxies/{n}_Proxy.mov"] + [f"{r}/{d}/{n}_Proxy.mov" for r in PROXY_ROOTS]:
            if os.path.exists(c): return c, p
    return p, p

def dims(p):
    j = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-select_streams", "v:0", "-show_streams", "-of", "json", p],
                                  capture_output=True, text=True).stdout)["streams"][0]
    rot = abs(int(j.get("tags", {}).get("rotate", 0) or 0))
    for sd in j.get("side_data_list", []):
        if "rotation" in sd: rot = abs(int(sd["rotation"]))
    return int(j["width"]), int(j["height"]), rot

# export thumbnails (cached)
E = []
for ex in exports:
    key = hashlib.md5((ex + str(os.path.getsize(ex))).encode()).hexdigest()[:12]
    cf = f"{cache}/{key}.npy"
    if os.path.exists(cf): fr = np.load(cf)
    else:
        fr = frames(ex, 4, TW, TH); np.save(cf, fr)
    E.append((os.path.basename(ex), norm(blur(fr)) if len(fr) else fr))
    print(f"export {os.path.basename(ex)}: {len(fr)} frames", flush=True)

report = []
for sname in seqs:
    for it in spec["sequences"][sname]["broll"]:
        clip = it["clip"]; use, orig = src_path(clip)
        w, h, rot = dims(use)
        vertical = h > w or rot in (90, 270) or it.get("ignore_rotation")
        if vertical or it.get("vertical"):  # vertical-native (or "vertical": true in the spec item): compare full frame
            fr = frames(use, 2, TW, TH); cands = fr[:, None]; offs = [0]
        else:
            FW, FH = 384, 216; fr = frames(use, 2, FW, FH); cw = int(FH * 9 / 16)
            offs = np.linspace(0, FW - cw, 17).astype(int)
            cands = np.stack([[cv2.resize(f[:, o:o + cw], (TW, TH), interpolation=cv2.INTER_AREA) for o in offs] for f in fr])
        n, k = cands.shape[:2]
        C = cands.reshape(n * k, TH, TW)
        C = norm(blur(C))
        lo, hi = it["in"], it["in"] + (it["end"] - it["start"])
        hits = []
        for name, Ef in E:
            if not len(Ef): continue
            S = Ef @ C.T                       # export frames x candidates
            best = S.max(1); arg = S.argmax(1)
            idx = np.where(best >= 0.85)[0]
            if not len(idx): continue
            # group consecutive export frames into appearances
            groups = np.split(idx, np.where(np.diff(idx) > 2)[0] + 1)
            for g in groups:
                if len(g) < 2: continue       # need >= 0.5 s on screen
                m = g[np.argmax(best[g])]; st = (arg[m] // k) / 2.0
                hits.append({"export": name, "t": round(g[0] / 4, 2), "t_best": round(m / 4, 2), "dur": round(len(g) / 4, 2), "score": round(float(best[m]), 3),
                             "src_t": st, "overlaps_our_window": bool(lo - 1 <= st <= hi + 1)})
        report.append({"seq": sname, "clip": os.path.basename(clip), "in": lo, "out": round(hi, 2), "hits": hits})
        print(f"{sname[:24]:24} {os.path.basename(clip)[:26]:26} {len(hits)} hits " +
              "; ".join(f"{x['export'][:28]}@{x['t']}s src{x['src_t']} {x['score']}{' SAME-WINDOW' if x['overlaps_our_window'] else ''}" for x in hits), flush=True)
json.dump(report, open(OUT, "w"), indent=1)
