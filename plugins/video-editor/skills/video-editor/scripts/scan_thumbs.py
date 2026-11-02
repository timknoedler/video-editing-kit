# One decode per clip: cam_scan.py-style 6 fps camera motion + sharpness csv AND a 1 fps thumbnail jpg (320x180), for spotting setup/whip/refocus junk without proxies.
# vpy scan_thumbs.py OUT_DIR clip1.mp4 [clip2 ...]   -> OUT_DIR/<clip>.csv, OUT_DIR/thumbs/<clip>_<sec>.jpg (skips clips already done)
import sys, os, subprocess, numpy as np, cv2
out = sys.argv[1]; W, H = 320, 180
os.makedirs(f"{out}/thumbs", exist_ok=True)
win = cv2.createHanningWindow((W, H), cv2.CV_32F)
for f in sys.argv[2:]:
    name = os.path.splitext(os.path.basename(f))[0]
    if os.path.exists(f"{out}/{name}.csv"): continue
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', f, '-vf', f'fps=6,scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
    prev = None; i = 0; rows = []
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        c = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        g = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).astype(np.float32)
        mv = 0.0
        if prev is not None:
            (dx, dy), _ = cv2.phaseCorrelate(prev, g, win); mv = float(np.hypot(dx, dy))
        rows.append((i / 6, mv, cv2.Laplacian(g, cv2.CV_32F).var(), g.mean()))
        if i % 6 == 0: cv2.imwrite(f"{out}/thumbs/{name}_{i // 6:04d}.jpg", c, [cv2.IMWRITE_JPEG_QUALITY, 80])
        prev = g; i += 1
    p.wait()
    np.savetxt(f"{out}/{name}.csv", np.array(rows), fmt='%.3f', delimiter=',', header='t,motion,sharp,luma')
    print(name, len(rows), flush=True)
