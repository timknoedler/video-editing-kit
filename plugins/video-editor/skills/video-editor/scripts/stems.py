#!/usr/bin/env python3
"""Split audio (or a video's audio) into stems with Demucs htdemucs, locally (weights in ~/.cache/torch/hub).
Use it to pull nat sound out from under PA/band music (keep "other"/"vocals" = crowd, drop "drums"/"bass"),
or to get a clean drum stem from the music for beat-exact cuts. Writes WAVs to OUT_DIR, never next to the source.
Usage: vpy stems.py FILE OUT_DIR [--ss 5.0] [--t 3.0] [--two vocals]
  two: two-stem mode (vocals / no_vocals) - faster, and "vocals" is usually where cheers and laughs land.
  Without --two you get drums, bass, other, vocals. Check the result with audio_tags.py before using it."""
import sys, os, subprocess, tempfile
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
f, out = a[0], a[1]; ss = opt("--ss", None); t = opt("--t", None); two = opt("--two", None)
os.makedirs(out, exist_ok=True)
base = os.path.splitext(os.path.basename(f))[0] + (f"_{float(ss):.1f}" if ss else "")
tmp = os.path.join(tempfile.mkdtemp(), base + ".wav")
cmd = ["ffmpeg", "-v", "error", "-y"] + (["-ss", ss] if ss else []) + ["-i", f] + (["-t", t] if t else []) + ["-vn", "-ac", "2", "-ar", "44100", tmp]
subprocess.run(cmd, check=True)
dm = [sys.executable, "-m", "demucs", "-n", "htdemucs", "-o", out, "--filename", "{track}_{stem}.{ext}"] + (["--two-stems", two] if two else []) + [tmp]
subprocess.run(dm, check=True)
d = os.path.join(out, "htdemucs")
for s in sorted(os.listdir(d)):
    if s.startswith(base): print(os.path.join(d, s))
