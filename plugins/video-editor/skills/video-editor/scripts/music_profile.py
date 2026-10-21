#!/usr/bin/env python3
# Profile music files (length, BPM, onsets/s, quiet->loud build, brightness) to describe a client's music taste. Usage: scripts/vpy music_profile.py a.wav b.mp3 ...
import sys, glob, os, warnings, numpy as np, librosa
warnings.filterwarnings("ignore")
files = [f for f in sys.argv[1:] if not os.path.basename(f).startswith("._")]
print(f"{'track':58} {'len':>5} {'bpm':>6} {'onset/s':>7} {'quiet->loud dB':>14} {'bright':>6}")
for f in files:
    y, sr = librosa.load(f, sr=22050, mono=True, duration=150)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    on = librosa.onset.onset_detect(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)[0]; db = 20*np.log10(rms+1e-9)
    seg = np.array_split(db, 10); lv = [np.median(s) for s in seg]
    cent = np.median(librosa.feature.spectral_centroid(y=y, sr=sr))
    d = librosa.get_duration(path=f)
    name = os.path.basename(f).replace(".wav","").replace(".mp3","")[:58]
    print(f"{name:58} {d:5.0f} {float(np.atleast_1d(tempo)[0]):6.1f} {len(on)/min(d,150):7.2f} {min(lv[:3]):6.1f}->{max(lv):5.1f} {cent:6.0f}")
