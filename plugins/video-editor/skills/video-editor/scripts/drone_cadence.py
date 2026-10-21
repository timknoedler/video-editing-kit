#!/usr/bin/env python3
# Detect judder/stutter in a rendered range (e.g. DJI 29.97 drones in a 23.976 timeline): per-frame mean abs difference,
# duplicate frames (diff ~0) and the strength of an every-Nth-frame spike pattern. Usage: drone_cadence.py render.mp4 start end [label]
import subprocess, sys, re, statistics as st
f, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]); lab = sys.argv[4] if len(sys.argv) > 4 else ""
o = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-ss", f"{a+0.05:.3f}", "-to", f"{b-0.05:.3f}", "-i", f, "-vf",
                    "scale=480:-2,format=gray,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
d = [float(x) for x in re.findall(r"YAVG=([\d.]+)", o)][1:]
if not d: print(lab, "no frames"); sys.exit()
med = st.median(d); p90 = sorted(d)[int(len(d) * 0.9)]; dup = sum(1 for x in d if x < 0.15 * p90)  # vs p90: a mostly-frozen shot has a ~0 median
best = max(((p, k) for p in (2, 3, 4, 5) for k in range(p)), key=lambda pk: st.mean(d[pk[1]::pk[0]]) / (st.mean([x for i, x in enumerate(d) if i % pk[0] != pk[1]]) or 1))
p, k = best; ratio = st.mean(d[k::p]) / (st.mean([x for i, x in enumerate(d) if i % p != k]) or 1)
verdict = "STUTTER (duplicate frames)" if dup > len(d) * 0.15 else ("judder (every-%dth spike x%.2f)" % (p, ratio) if ratio > 1.6 else "smooth")
print(f"{lab:28} frames {len(d):3}  median diff {med:5.2f}  duplicates {dup:2}  strongest period {p} x{ratio:.2f}  -> {verdict}")
print("   ", " ".join(f"{x:.1f}" for x in d[:32]))
