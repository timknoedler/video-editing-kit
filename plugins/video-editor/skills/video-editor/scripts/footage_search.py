#!/usr/bin/env python3
"""Search footage by description ("women laughing under umbrellas", "close-up of a wine pour") with SigLIP, locally
(google/siglip-base-patch16-224 in the HuggingFace cache). Index once per folder, then query as often as you like.
  index: vpy footage_search.py index CACHE.npz FOLDER [FOLDER ...] [--hop 2]
         samples one frame every --hop seconds of every video (videotoolbox decode, 224 px) and stores embeddings.
         Keep CACHE in the job's _edit folder, never on the source card folders. Re-running skips files already indexed.
  query: vpy footage_search.py query CACHE.npz "text" ["text 2" ...] [--top 12] [--sheet OUT.jpg]
         prints file + source time per hit (best first, one hit per 6 s window) and optionally a contact sheet.
Scores are cosine similarity: compare hits against each other, not against a fixed threshold."""
import sys, os, subprocess, numpy as np, torch
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
mode, cache = a[0], a[1]; args = [s for i, s in enumerate(a[2:], 2) if not s.startswith("--") and not a[i - 1].startswith("--")]
from transformers import AutoModel, AutoProcessor
M = "google/siglip-base-patch16-224"; model = AutoModel.from_pretrained(M).eval(); proc = AutoProcessor.from_pretrained(M)
VID = (".mp4", ".mov", ".mxf", ".m4v")

def frames(f, hop):
    cmd = ["ffmpeg", "-v", "error", "-hwaccel", "videotoolbox", "-i", f, "-vf", f"fps=1/{hop},scale=224:224", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 224, 224, 3)

if mode == "index":
    hop = float(opt("--hop", 2)); old = dict(np.load(cache, allow_pickle=True)) if os.path.exists(cache) else {}
    files, times, embs = list(old.get("files", [])), list(old.get("times", [])), list(old.get("embs", np.zeros((0, 768))))
    done = set(files)
    todo = [os.path.join(r, n) for d in args for r, _, ns in os.walk(d) for n in sorted(ns) if n.lower().endswith(VID) and not n.startswith(".")]
    for k, f in enumerate(todo):
        if f in done: continue
        fr = frames(f, hop)
        if not len(fr): continue
        with torch.no_grad():
            e = model.get_image_features(**proc(images=list(fr), return_tensors="pt"))
        e = torch.nn.functional.normalize(e, dim=-1).numpy()
        files += [f] * len(e); times += [i * hop + hop / 2 for i in range(len(e))]; embs += list(e)
        print(f"[{k + 1}/{len(todo)}] {os.path.basename(f)} {len(e)} frames", flush=True)
        np.savez(cache, files=np.array(files), times=np.array(times), embs=np.array(embs))
    print(cache, len(files), "frames")
else:
    z = np.load(cache, allow_pickle=True); files, times, embs = z["files"], z["times"], z["embs"]; top = int(opt("--top", 12))
    with torch.no_grad():
        t = model.get_text_features(**proc(text=args, padding="max_length", return_tensors="pt"))
    t = torch.nn.functional.normalize(t, dim=-1).numpy()
    hits = []
    for q, v in zip(args, t):
        s = embs @ v; picked = []
        for i in np.argsort(s)[::-1]:
            if any(files[i] == files[j] and abs(times[i] - times[j]) < 6 for j in picked): continue
            picked.append(i)
            if len(picked) == top: break
        print(f'"{q}"')
        for i in picked: print(f"  {s[i]:+.3f}  {times[i]:7.1f}s  {files[i]}")
        hits += [(q, files[i], times[i], s[i]) for i in picked]
    sheet = opt("--sheet", None)
    if sheet:
        from PIL import Image, ImageDraw
        W, H, cols = 384, 216, 4; im = Image.new("RGB", (cols * W, ((len(hits) + cols - 1) // cols) * (H + 20)), (0, 0, 0)); d = ImageDraw.Draw(im)
        for k, (q, f, tt, s) in enumerate(hits):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(tt), "-i", f, "-frames:v", "1", "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            x, y = (k % cols) * W, (k // cols) * (H + 20)
            if len(raw) == W * H * 3: im.paste(Image.frombytes("RGB", (W, H), raw), (x, y + 20))
            d.text((x + 3, y + 4), f"{os.path.basename(f)} {tt:.1f}s {s:+.2f}", fill=(230, 230, 230))
        im.save(sheet, quality=85); print(sheet)
