#!/usr/bin/env python3
# Re-transcribe short windows of a media file with whisper.cpp and print word times on the FILE's clock (whole-file
# transcripts drift by seconds on sparse speech). Usage: window_words.py MEDIA from_s to_s [from_s to_s ...]
# Writes nothing permanent: temp wav/json live in a temp dir that is cleaned up. Needs whisper-cli + ffmpeg on PATH.
import json, os, subprocess, sys, tempfile, shutil
M = os.environ.get("WHISPER_MODEL") or next((p for p in (
    os.path.expanduser("~/Library/Application Support/whisper.cpp/models/ggml-large-v3-turbo.bin"),
    os.path.expanduser("~/whisper.cpp/models/ggml-large-v3-turbo.bin")) if os.path.exists(p)), "")
media, ts = sys.argv[1], [float(x) for x in sys.argv[2:]]
tmp = tempfile.mkdtemp()
try:
    for a, b in zip(ts[0::2], ts[1::2]):
        w = f"{tmp}/w.wav"
        subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", media, "-vn", "-ac", "1", "-ar", "16000", w], check=True)
        subprocess.run(["whisper-cli", "-m", M, "-f", w, "-l", "en", "-ojf", "-ml", "1", "-sow", "-of", f"{tmp}/w"],
                       capture_output=True, check=True)
        j = json.load(open(f"{tmp}/w.json"))["transcription"]
        out, last = [], None
        for s in j:
            t = s["text"].strip()
            if not t or t.startswith("[_"): continue
            t0, t1 = a + s["offsets"]["from"] / 1000, a + s["offsets"]["to"] / 1000
            if last is not None and t0 - last > 0.6: out.append("|")   # pause marker
            out.append(f"{t}@{t0:.2f}"); last = t1
        print(f"[{a:.1f}-{b:.1f}] " + " ".join(out) + f"  (end {last:.2f})" if last else f"[{a:.1f}-{b:.1f}] (no speech)")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
