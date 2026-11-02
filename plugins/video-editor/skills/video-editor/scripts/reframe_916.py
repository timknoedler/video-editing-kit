#!/usr/bin/env python3
"""Find the best horizontal slide for a 16:9 clip on a 9:16 timeline (Scale + Position X reframe, no baking).
Samples the source window you actually use, slides the 9:16 crop across the frame and scores every position:
  - subject: SigLIP similarity between each crop and --subject text ("bottles held by hands", "three women posing",
    "DJ hands on the mixer"), the same model as footage_search.py, so you can say what the shot is about;
  - faces: MediaPipe faces found at 1280 px (works on S-Log after a contrast lift); a crop that keeps whole faces scores
    higher and one that slices a face at its edge is penalised;
  - the whole shot counts (mean plus the worst frame), so a subject that drifts stays inside.
Prints the best Premiere Position X (normalised, as the bridge uses) plus clearly different alternatives, and a contact
sheet with the windows (green best, orange/blue alternatives, magenta faces).
Usage: vpy reframe_916.py FILE --from T0 --to T1 [--subject "text"] [--scale 177.78] [--seq 2160x3840] [--frames 5]
                         [--current POSX] [--sheet out.jpg]
Position X convention (Premiere bridge, normalised): p = 0.5 - (cx - 0.5) * k, k = srcW*scale/100/seqW
(UHD source on a 2160x3840 timeline at 177.78: k = 3.1605, visible width = 31.6% of the frame)."""
import sys, os, subprocess, numpy as np, cv2
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
f = a[0]; t0 = float(opt("--from", 0)); t1 = float(opt("--to", t0 + 1)); scale = float(opt("--scale", 177.78))
seqW, seqH = (int(v) for v in opt("--seq", "2160x3840").split("x")); NF = int(opt("--frames", 5))
subject = opt("--subject", "the main subject of the photo, well composed"); cur = opt("--current", None)
sheet = opt("--sheet", None)
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", f], capture_output=True, text=True).stdout.split(",")
srcW, srcH = int(probe[0]), int(probe[1])
k = srcW * scale / 100 / seqW                                         # source-frame widths per sequence width
w = seqW / (srcW * scale / 100)                                       # visible fraction of the source width
hfrac = min(1.0, seqH / (srcH * scale / 100))                         # visible fraction of the source height
W, H = 1280, 720
frames = []
for t in np.linspace(t0, max(t0, t1 - 0.05), NF):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", f, "-frames:v", "1", "-vf", f"scale={W}:{H}",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    if len(b) == W * H * 3: frames.append((t, np.frombuffer(b, np.uint8).reshape(H, W, 3)))
if not frames: sys.exit("no frames decoded")
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
def normalise(bgr):                                                   # lift S-Log so models see contrast and colour
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB); lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR).astype(np.float32) / 255
    m = out.mean(axis=2, keepdims=True); return (np.clip(m + (out - m) * 1.6, 0, 1) * 255).astype(np.uint8)

MP = os.path.expanduser("~/mediapipe_models/face_landmarker.task")
faces_by_frame = [[] for _ in frames]
if os.path.exists(MP):
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    lmk = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MP), num_faces=10, min_face_detection_confidence=0.3))
    for i, (_, fr) in enumerate(frames):
        n = normalise(fr)
        for tile_x in (0, W // 3, 2 * W // 3):                          # thirds at 2x so small faces register
            tile = cv2.resize(n[:, max(0, tile_x - 80):min(W, tile_x + W // 3 + 80)], None, fx=2, fy=2)
            r = lmk.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(tile[:, :, ::-1])))
            th, tw = tile.shape[:2]; ox = max(0, tile_x - 80)
            for pts in r.face_landmarks:
                xs = [ox + p.x * tw / 2 for p in pts]; ys = [p.y * th / 2 for p in pts]
                box = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
                if not any(abs(box[0] - b[0]) < box[2] / 2 and abs(box[1] - b[1]) < box[3] / 2 for b in faces_by_frame[i]):
                    faces_by_frame[i].append(box)

import torch
from transformers import AutoModel, AutoProcessor
M = "google/siglip-base-patch16-224"; model = AutoModel.from_pretrained(M).eval(); proc = AutoProcessor.from_pretrained(M)
win = w * W; half = win / 2; top = int(H * (1 - hfrac) / 2)
cands = np.linspace(half, W - half, 25)
crops = []
for _, fr in frames:
    n = normalise(fr)[:, :, ::-1]
    for c in cands:
        crops.append(n[top:H - top, int(c - half):int(c + half)])
with torch.no_grad():
    ti = proc(text=[subject], padding="max_length", return_tensors="pt")
    te = model.get_text_features(**ti); te = te / te.norm(dim=-1, keepdim=True)
    sims = []
    for i in range(0, len(crops), 32):
        ii = proc(images=list(crops[i:i + 32]), return_tensors="pt")
        ie = model.get_image_features(**ii); ie = ie / ie.norm(dim=-1, keepdim=True)
        sims.append((ie @ te.T).squeeze(1).numpy())
sim = np.concatenate(sims).reshape(len(frames), len(cands))
semz = (sim - sim.mean()) / (sim.std() + 1e-6)                       # relative within this shot

face_score = np.zeros_like(semz)
for i, fb in enumerate(faces_by_frame):
    for j, c in enumerate(cands):
        l, r = c - half, c + half
        for x, y, bw, bh in fb:
            frac_in = max(0, min(r, x + bw) - max(l, x)) / max(bw, 1)
            if frac_in > 0.9: face_score[i, j] += 1.0 * min(1, bh / 40)        # whole face kept (small faces count less)
            elif frac_in > 0.1: face_score[i, j] -= 1.5                        # face sliced by the crop edge
nf = max(1, max(len(fb) for fb in faces_by_frame))
per_frame = semz + 1.5 * face_score / nf
S = per_frame.mean(axis=0) + 0.5 * per_frame.min(axis=0)
order = np.argsort(-S); picks = []
for i in order:                                                       # clearly different framings
    if all(abs(cands[i] - cands[j]) > half for j in picks): picks.append(i)
    if len(picks) == 3: break
def pos(cx_frac): return 0.5 - (cx_frac - 0.5) * k
print(f"{f.split('/')[-1]}  {t0:.2f}-{t1:.2f}s  {len(frames)} frames  visible width {w:.3f}  k={k:.4f}  "
      f"faces/frame {[len(x) for x in faces_by_frame]}  subject: {subject!r}")
for rank, i in enumerate(picks):
    cx = cands[i] / W
    print(f"  {'BEST' if rank == 0 else 'alt '}  centre x {cx:.3f}  ->  Position X {pos(cx):.3f}   (score {S[i]:+.2f})")
if cur is not None:
    ccx = 0.5 - (float(cur) - 0.5) / k; j = int(np.argmin(abs(cands / W - ccx)))
    print(f"  current Position X {float(cur):.3f} = centre x {ccx:.3f}, score {S[j]:+.2f}")
if sheet:
    tiles = []
    for fi, (t, fr) in enumerate(frames[:: max(1, len(frames) // 4)][:4]):
        im = cv2.resize(fr, (640, 360)); s = 640 / W
        for rank, i in enumerate(picks):
            col = [(0, 255, 0), (0, 200, 255), (255, 120, 0)][rank]; l = int((cands[i] - half) * s)
            cv2.rectangle(im, (l, int(top * s) + 1), (l + int(win * s), int((H - top) * s) - 2), col, 3 if rank == 0 else 1)
        for x, y, bw, bh in faces_by_frame[frames.index((t, fr)) if False else fi * max(1, len(frames) // 4)]:
            cv2.rectangle(im, (int(x * s), int(y * s)), (int((x + bw) * s), int((y + bh) * s)), (255, 0, 255), 1)
        cv2.putText(im, f"{t:.2f}s", (6, 22), 0, 0.6, (0, 255, 255), 2); tiles.append(im)
    cv2.imwrite(sheet, np.hstack(tiles)); print("  sheet:", sheet)
