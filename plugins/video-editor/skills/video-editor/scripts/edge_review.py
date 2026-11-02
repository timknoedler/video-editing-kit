# Cut-point review (for the editor note "some shots are cut weird, cutting too soon or starting too soon").
# For every shot as it is VISIBLE on the timeline (top layer wins), writes:
#   - flags from the proxy's camera motion (phase correlation, 12 fps): IN-MOVE = the in point catches the tail of a
#     reframe/whip that settles inside the shot (start later); OUT-MOVE = the camera starts moving/whipping before the out
#     (end earlier); JUMP = back-to-back pieces of the same clip less than 3 s apart in the source (a jump cut);
#   - edge sheets: one row per shot, 6 frames: in-1 s | IN (green) | in+0.5 | out-0.5 | OUT (red, last frame) | out+1 s.
# Subject motion is NOT flagged automatically (on flat S-Log proxies grain swamps it): judge hugs/kisses/gestures that
# are cut mid-way, foreground walk-ins, people leaving frame and "starts on nothing" by eye on the sheets. Typical finds:
# a hug or kiss cut before it lands/releases, a payoff just after the out (dog reaches the lens), a sound line about
# something not yet in picture, an out on the first frame of a whip, a reaction shot blocked by someone's back.
# usage: vpy edge_review.py spec.json SEQ outdir --proxies DIR [--only changed_vs.json] [--rows 10]
#   (--only: edge json from an earlier run; only shots whose clip/in/out changed are drawn)
import json, sys, os, glob, subprocess, numpy as np, cv2
from concurrent.futures import ThreadPoolExecutor
A = sys.argv[1:]
def opt(k, d=None): return A[A.index(k) + 1] if k in A else d
spec = json.load(open(A[0])); seq = spec["sequences"][A[1]]; OUT = A[2]; PROX = opt("--proxies"); ROWS = int(opt("--rows", 10))
ROOT = spec.get("media_root", ""); fps = spec.get("fps", 23.976); FPS = 24000/1001 if abs(fps - 23.976) < 0.01 else fps
os.makedirs(OUT, exist_ok=True)
_idx = {}
if PROX:
    for p in glob.glob(f"{PROX}/**/*_Proxy.mov", recursive=True): _idx[os.path.basename(p)[:-10]] = p
def media(clip):
    c = os.path.basename(clip).rsplit(".", 1)[0]
    if c in _idx: return _idx[c]
    return clip if clip.startswith("/") else os.path.join(ROOT, clip)
def visible():
    it = [x for x in seq["broll"] if x.get("track", 1) in (1, 2) and x.get("enabled", True)]
    end = max(x["end"] for x in it); n = int(round(end * FPS)); top = [None] * n
    for x in sorted(it, key=lambda x: x.get("track", 1)):
        for f in range(int(round(x["start"] * FPS)), int(round(x["end"] * FPS))):
            if 0 <= f < n: top[f] = x
    out = []
    for f, x in enumerate(top):
        if out and out[-1][0] is x: out[-1][2] = f + 1
        else: out.append([x, f, f + 1])
    return [(x, a / FPS, b / FPS) for x, a, b in out if x is not None]
def gray(p, a, b, W=320, H=180):
    a = max(0.0, a); raw = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", p, "-vf", f"fps=12,scale={W}:{H},format=gray",
                                           "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (W * H); return a, np.frombuffer(raw[:n * W * H], np.uint8).reshape(n, H, W).astype(np.float32)
def cam(fr):
    win = cv2.createHanningWindow((fr.shape[2], fr.shape[1]), cv2.CV_32F); v = [0.0]
    for i in range(1, len(fr)): (dx, dy), _ = cv2.phaseCorrelate(fr[i-1], fr[i], win); v.append(float(np.hypot(dx, dy)))
    return np.convolve(np.array(v), np.ones(3) / 3, "same")
def analyse(xab):
    x, a, b = xab; p = media(x["clip"]); s_in = x["in"] + (a - x["start"]); s_out = s_in + (b - a)
    r = {"t": round(a, 2), "dur": round(b - a, 2), "clip": os.path.basename(x["clip"]).rsplit(".", 1)[0], "track": x.get("track", 1),
         "in": round(s_in, 2), "out": round(s_out, 2), "path": p, "flags": []}
    if not os.path.exists(p) or p.endswith(".png"): return r
    t0, fr = gray(p, s_in - 1.5, s_out + 1.5)
    if len(fr) < 6: return r
    c = cam(fr); t = t0 + np.arange(len(fr)) / 12.0
    m = lambda lo, hi: float(c[(t >= lo) & (t < hi)].mean()) if ((t >= lo) & (t < hi)).any() else 0.0
    ins = (t >= s_in) & (t < s_out); mid = float(np.median(c[ins])) if ins.any() else 0.0; hi = max(3.0, 2.5 * mid + 1.0); calm = max(1.5, 1.5 * mid + 0.5)
    if m(s_in, s_in + 0.35) > hi:
        st = next((tt for tt in t[ins] if m(tt, tt + 0.35) < calm), None)
        if st is not None and st - s_in < (s_out - s_in) * 0.6: r["flags"].append(["IN-MOVE", round(st - s_in, 2)])
    if m(s_out - 0.35, s_out) > hi:
        st = next((tt for tt in t[ins][::-1] if m(tt - 0.35, tt) < calm), None)
        if st is not None: r["flags"].append(["OUT-MOVE", round(s_out - st, 2)])
    return r
with ThreadPoolExecutor(6) as ex: R = list(ex.map(analyse, visible()))
for a, b in zip(R, R[1:]):
    if a["clip"] == b["clip"] and 0 < b["in"] - a["out"] < 3.0: b["flags"].append(["JUMP", round(b["in"] - a["out"], 2)])
for r in R:
    if r["flags"]: print(f"{int(r['t']//60)}:{r['t']%60:05.2f} {r['dur']:5.2f}s V{r['track']} {r['clip']:16s} {r['in']:8.2f}-{r['out']:8.2f}  " + " ".join(f"{k}({v})" for k, v in r["flags"]))
json.dump(R, open(f"{OUT}/edges.json", "w"), indent=1)
draw = R
if opt("--only"):
    old = [(o["clip"], o["in"], o["out"]) for o in json.load(open(opt("--only")))]
    draw = [r for r in R if not any(c == r["clip"] and abs(i - r["in"]) < 0.15 and abs(o - r["out"]) < 0.15 for c, i, o in old)]
W, H = 240, 119
def grab(p, t):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{max(0, t):.3f}", "-i", p, "-frames:v", "1", "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(raw[:W*H*3], np.uint8).reshape(H, W, 3).copy() if len(raw) >= W*H*3 else np.zeros((H, W, 3), np.uint8)
def row(ir):
    i, r = ir; a, b = r["in"], r["out"]; fr = []
    for t, k in ((a - 1.0, 0), (a, 1), (a + min(0.5, (b - a) / 3), 2), (b - min(0.5, (b - a) / 3), 2), (b - 1 / FPS, 3), (b + 1.0, 0)):
        im = grab(r["path"], t) if os.path.exists(r["path"]) else np.zeros((H, W, 3), np.uint8)
        if k == 0: im = (im * 0.45).astype(np.uint8)
        if k in (1, 3): cv2.rectangle(im, (0, 0), (W - 1, H - 1), (0, 220, 0) if k == 1 else (0, 0, 230), 3)
        cv2.putText(im, f"{t:.1f}", (4, H - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1); fr.append(im)
    lab = np.zeros((18, W * 6, 3), np.uint8); t = r["t"]
    cv2.putText(lab, f"#{i}  {int(t//60)}:{t%60:05.2f}  {r['dur']:.2f}s  V{r['track']}  {r['clip']}  src {a:.2f}-{b:.2f}  " + " ".join(k for k, _ in r["flags"]), (4, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
    return np.vstack([lab, np.hstack(fr)])
with ThreadPoolExecutor(8) as ex: rows = list(ex.map(row, enumerate(draw)))
for k in range(0, len(rows), ROWS): cv2.imwrite(f"{OUT}/edges_{k//ROWS:02d}.jpg", np.vstack(rows[k:k+ROWS]), [cv2.IMWRITE_JPEG_QUALITY, 82])
print(f"{len(R)} shots, {sum(1 for r in R if r['flags'])} flagged; {len(rows)} rows drawn -> {OUT}/edges_*.jpg")
