#!/usr/bin/env python3
"""Pick the best take/moment: per-sample sharpness (focus) and faces / eyes-open (MediaPipe face landmarker, locally;
model at ~/mediapipe_models/face_landmarker.task; get it once from
https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task). Use it to compare takes ("which pour is in focus?") or to find
the frames in a clip where nobody is blinking or the subject is sharp.
Usage: vpy shot_check.py FILE [FILE ...] [--ss 3.0] [--t 4.0] [--hop 0.25]
Prints per file: a timeline of sharp (Laplacian variance of the centre 60% after a 1-99 pct contrast stretch, /100 at 1080p; higher = sharper,
compare between takes of the same scene), face_sharp (same, on the largest face), faces, and blink (the max
eyeBlink blendshape across faces, > 0.5 = someone's eyes are closed), then the best sample by sharpness with no blink."""
import sys, os, subprocess, numpy as np, cv2
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
files = [s for i, s in enumerate(a) if not s.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
ss = float(opt("--ss", 0)); t = opt("--t", None); hop = float(opt("--hop", 0.25))
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=os.path.expanduser("~/mediapipe_models/face_landmarker.task")),
    output_face_blendshapes=True, num_faces=8))
W, H = 1920, 1080
def lap(g): return cv2.Laplacian(g, cv2.CV_64F).var() / 100 if g.size > 400 else np.nan
def stretch(x):                                # log footage is flat: stretch 1-99 pct per frame so focus and faces read
    lo, hi = np.percentile(x, (1, 99)); return np.clip((x.astype(float) - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
for f in files:
    cmd = ["ffmpeg", "-v", "error", "-hwaccel", "videotoolbox", "-ss", str(ss), "-i", f] + (["-t", t] if t else []) + \
          ["-vf", f"fps=1/{hop},scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:-1:-1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    fr = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.uint8).reshape(-1, H, W, 3)
    print(f"{os.path.basename(f)}  {ss:.2f}s +{len(fr) * hop:.2f}s")
    rows = []
    for k, x in enumerate(fr):
        x = stretch(x)
        g = cv2.cvtColor(x, cv2.COLOR_RGB2GRAY); c = g[int(H * .2):int(H * .8), int(W * .2):int(W * .8)]
        r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(x)))
        fs, blink = np.nan, 0.0
        if r.face_landmarks:
            boxes = [(min(p.x for p in L), min(p.y for p in L), max(p.x for p in L), max(p.y for p in L)) for L in r.face_landmarks]
            x0, y0, x1, y1 = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            fs = lap(g[max(0, int(y0 * H)):int(y1 * H), max(0, int(x0 * W)):int(x1 * W)])
            blink = max(max(b.score for b in bs if b.category_name.startswith("eyeBlink")) for bs in r.face_blendshapes)
        rows.append((ss + k * hop, lap(c), fs, len(r.face_landmarks), blink))
        print(f"  {rows[-1][0]:7.2f}s  sharp {rows[-1][1]:6.2f}  face_sharp {fs:6.2f}  faces {rows[-1][3]}  blink {blink:.2f}" + ("  BLINK" if blink > .5 else ""))
    ok = [r for r in rows if r[4] <= .5] or rows
    if ok:
        b = max(ok, key=lambda r: np.nan_to_num(r[2], nan=r[1]) if r[3] else r[1])
        print(f"  best: {b[0]:.2f}s (sharp {b[1]:.2f}, face_sharp {b[2]:.2f}, faces {b[3]})")
