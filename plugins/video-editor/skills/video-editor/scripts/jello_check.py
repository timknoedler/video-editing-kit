#!/usr/bin/env python3
"""Detect Warp Stabilizer 'jello' (non-rigid background warping) by comparing two renders of the same cut.
Usage: scripts/vpy jello_check.py before.mp4 after.mp4 cuts.json   (cuts.json: [[start_s, end_s, "name"], ...])
Per frame pair: track features (whole frame), fit a homography (RANSAC), then measure how much the inlier
motion field still bends: residual RMS (px at 360 wide) of local 4x4-cell median flows after removing the
homography. Rigid camera motion -> ~0; jello -> grows. Reports per shot: before, after, ratio. Flag ratio>1.5 and after>0.35."""
import sys, json, subprocess, numpy as np, cv2
W, H = 360, 640
def frames(f, t0, t1):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1-t0:.3f}", "-i", f, "-vf", f"scale={W}:{H}", "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(p, np.uint8).reshape(-1, H, W)
def bend(fr):
    out = []
    for a, b in zip(fr[:-1], fr[1:]):
        pts = cv2.goodFeaturesToTrack(a, 400, 0.01, 6)
        if pts is None or len(pts) < 30: continue
        nx, st, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, None); g = st.ravel() == 1
        p0, p1 = pts[g].reshape(-1, 2), nx[g].reshape(-1, 2)
        if len(p0) < 30: continue
        Hm, inl = cv2.findHomography(p0, p1, cv2.RANSAC, 2.0)
        if Hm is None: continue
        inl = inl.ravel() == 1; p0, p1 = p0[inl], p1[inl]
        pred = cv2.perspectiveTransform(p0.reshape(-1, 1, 2), Hm).reshape(-1, 2); r = p1 - pred
        cells = []
        for i in range(4):
            for j in range(4):
                m = (p0[:, 0] // (W / 4) == i) & (p0[:, 1] // (H / 4) == j)
                if m.sum() >= 4: cells.append(np.median(r[m], axis=0))
        if len(cells) >= 6: out.append(float(np.sqrt(np.mean(np.sum(np.array(cells) ** 2, axis=1)))))
    return float(np.median(out)) if out else float('nan')
bef, aft, cuts = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
for t0, t1, name in cuts:
    t0b, t1b = t0 + 0.05, t1 - 0.05
    b, a = bend(frames(bef, t0b, t1b)), bend(frames(aft, t0b, t1b))
    ratio = a / b if b > 0 else float('nan'); flag = "  <-- JELLO?" if (ratio > 1.5 and a > 0.35) else ""
    print(f"{name:32s} {t0:6.2f}-{t1:6.2f}  before {b:.3f}  after {a:.3f}  x{ratio:.2f}{flag}")
