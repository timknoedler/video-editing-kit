#!/usr/bin/env python3
"""Synthesized whoosh for transitions and speed ramps (no sample library needed).
Filtered noise whose band sweeps from --f0 to --f1 Hz, with a fast swell to --peak seconds and a long tail,
slight stereo movement (L->R by default) and a soft low "air" body. Output: 48 kHz 24-bit stereo WAV.
Usage: vpy whoosh_synth.py OUT.wav [--dur 2.0] [--peak 0.35] [--f0 2400] [--f1 260] [--q 1.4] [--pan -0.4,0.4]
       [--level -6] [--seed 7]
  peak: where the swell tops out (put it on the fastest part of the move). level: peak dBFS of the file;
  set the clip level in Premiere (about -14 to -20 dB under music for a subtle bed)."""
import sys, numpy as np, scipy.signal as ss, soundfile as sf
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
out = a[0]; sr = 48000
dur = float(opt("--dur", 2.0)); peak = float(opt("--peak", 0.35)); f0 = float(opt("--f0", 2400)); f1 = float(opt("--f1", 260))
q = float(opt("--q", 1.4)); p0, p1 = map(float, opt("--pan", "-0.4,0.4").split(",")); level = float(opt("--level", -6))
rng = np.random.default_rng(int(opt("--seed", 7)))
n = int(dur * sr); t = np.arange(n) / sr
noise = rng.standard_normal(n)
# time-varying band-pass: process in short overlapping blocks with a log-swept centre frequency
blk, hop = 2048, 512; win = np.hanning(blk); y = np.zeros(n + blk)
x = np.concatenate([noise, np.zeros(blk)])
for s in range(0, n, hop):
    u = min(1.0, (s + blk / 2) / n); fc = f0 * (f1 / f0) ** (u ** 0.7)
    lo, hi = fc / (2 ** (0.5 / q)), min(fc * (2 ** (0.5 / q)), sr / 2 - 100)
    b, a_ = ss.butter(2, [lo / (sr / 2), hi / (sr / 2)], "band")
    y[s:s + blk] += ss.lfilter(b, a_, x[s:s + blk]) * win
y = y[:n]
body = ss.lfilter(*ss.butter(2, 180 / (sr / 2)), noise) * 0.5          # low "air" under the sweep
sig = y + body
env = np.where(t < peak, (t / peak) ** 2, np.exp(-(t - peak) / max((dur - peak) / 4.0, 1e-3)))
fade = np.clip((dur - t) / 0.05, 0, 1)                                   # click-free end
sig *= env * fade
pan = p0 + (p1 - p0) * np.clip(t / dur, 0, 1)                           # equal-power pan sweep
L = sig * np.cos((pan + 1) * np.pi / 4); R = sig * np.sin((pan + 1) * np.pi / 4)
st = np.stack([L, R], 1); st *= 10 ** (level / 20) / np.abs(st).max()
sf.write(out, st, sr, subtype="PCM_24"); print(out, f"{dur}s peak@{peak}s {f0:.0f}->{f1:.0f} Hz")
