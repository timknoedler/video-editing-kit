#!/usr/bin/env python3
"""Speech regions per shot from a final mix, for timing captions (onsets accurate to ~10 ms; whisper word times drift).
Usage: vpy speech_regions.py MIX.(wav|mp4) t0 t1 t2 ...   (shot cut times in seconds, incl. 0 and end)
Prints [start-end peak] regions per shot: threshold = max(shot floor + 10 dB, shot peak - 30 dB), gaps < 0.25 s merged, min 0.12 s."""
import sys, subprocess, numpy as np
raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", sys.argv[1], "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768; n = len(x) // 160
db = 20 * np.log10(np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(1) + 1e-12))
cuts = [float(c) for c in sys.argv[2:]]
for a, b in zip(cuts, cuts[1:]):
    seg = db[int(a * 100):int(b * 100)]; thr = max(np.percentile(seg, 20) + 10, seg.max() - 30); on = seg > thr; regs = []; i = 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]: j += 1
            if regs and i - regs[-1][1] < 25: regs[-1][1] = j
            else: regs.append([i, j])
            i = j
        else: i += 1
    print(f"{a:7.2f}-{b:7.2f}: " + "  ".join(f"[{a+r[0]/100:.2f}-{a+r[1]/100:.2f} pk{seg[r[0]:r[1]].max():.0f}]" for r in regs if r[1] - r[0] >= 12))
