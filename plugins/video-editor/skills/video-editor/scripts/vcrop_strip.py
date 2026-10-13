#!/usr/bin/env python3
"""Preview how a horizontal clip reads as a centered 9:16 crop: one strip of frames per window, labeled with the time.
Usage: vcrop_strip.py "<FOOTAGE_ROOT>" OUT_DIR CLIP:start-end[:xoff] ...   (xoff = crop centre shift in px, e.g. -400 = left)
Needs <EDIT_DIR or ROOT/_edit>/work/probe.json. Vertical-native clips are shown uncropped. Writes OUT_DIR/<CLIP>_<start>.jpg (venv: cv2)."""
import json, os, subprocess, sys
import numpy as np, cv2

root, out = sys.argv[1].rstrip("/"), sys.argv[2]
E = os.environ.get("EDIT_DIR") or f"{root}/_edit"
probe = {os.path.splitext(os.path.basename(r["file"]))[0]: r for r in json.load(open(f"{E}/work/probe.json"))}
os.makedirs(out, exist_ok=True)
for spec in sys.argv[3:]:
    parts = spec.split(":"); c = parts[0]; a, b = map(float, parts[1].split("-")); xoff = int(parts[2]) if len(parts) > 2 else 0
    r = probe[c]; n = 8; th = 360
    vert = r["orientation"] == "vertical"
    tiles = []
    for i in range(n):
        t = a + (b - a) * i / (n - 1)
        raw = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{t:.3f}", "-i", f"{root}/{r['file']}", "-frames:v", "1",
                              "-vf", "scale=-2:720", "-pix_fmt", "rgb24", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR) if raw else None
        if img is None: continue
        h, w = img.shape[:2]
        if not vert and w > h:
            cw = int(h * 9 / 16); cx = w // 2 + int(xoff * w / 3840)
            x0 = max(0, min(w - cw, cx - cw // 2)); img = img[:, x0:x0 + cw]
        img = cv2.resize(img, (int(img.shape[1] * th / img.shape[0]), th))
        cv2.putText(img, f"{t:.1f}", (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        tiles.append(cv2.copyMakeBorder(img, 0, 0, 0, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    if tiles:
        p = f"{out}/{c}_{a:g}.jpg"; cv2.imwrite(p, np.hstack(tiles)); print(p)
