#!/usr/bin/env python3
"""Synthesized reverse-cymbal swell: a soft, organic lead-in to a cut (the classic high-end alternative to synth whooshes).
Metallic noise (many inharmonic partials 3-14 kHz plus band-passed noise), natural exponential crash decay, then reversed so it
swells into the cut and stops dead on it. Output 48 kHz 24-bit stereo; place it so the file END lands on the cut.
Usage: vpy reverse_cymbal.py OUT.wav [--dur 1.2] [--decay 0.45] [--bright 1.0] [--level -6] [--seed 5]"""
import sys, numpy as np, scipy.signal as ss, soundfile as sf
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
out = a[0]; sr = 48000; dur = float(opt("--dur", 1.2)); dec = float(opt("--decay", 0.45)); bright = float(opt("--bright", 1.0))
level = float(opt("--level", -6)); rng = np.random.default_rng(int(opt("--seed", 5)))
n = int(dur * sr); t = np.arange(n) / sr; ch = []
for c in range(2):
    noise = rng.standard_normal(n)
    b, aa = ss.butter(4, [2500 / (sr / 2), min(15000 * bright, 22000) / (sr / 2)], "band"); x = ss.lfilter(b, aa, noise)
    f = rng.uniform(3000, 14000 * bright, 60); ph = rng.uniform(0, 2 * np.pi, 60)
    part = sum(np.sin(2 * np.pi * fi * t + p) * np.exp(-t / (dec * rng.uniform(0.6, 1.4))) for fi, p in zip(f, ph)) / 25
    x = x * np.exp(-t / dec) + part * 0.6
    x[:int(0.004 * sr)] *= np.linspace(0, 1, int(0.004 * sr))   # soft "strike" (becomes the end after reversing)
    ch.append(x[::-1])
y = np.stack(ch, 1); y *= np.clip(t / 0.15, 0, 1)[:, None]      # fade in the (reversed) tail
y *= 10 ** (level / 20) / np.abs(y).max(); sf.write(out, y, sr, subtype="PCM_24"); print(out, f"{dur}s")
