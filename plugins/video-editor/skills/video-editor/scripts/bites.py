#!/usr/bin/env python3
"""Interview bite tools: read whisper.cpp word timings, snap cut points to quiet frames, score bites.
Usage (venv python not required for `words`; `snap`/`score` need numpy -> use scripts/vpy):
  bites.py words  <transcript.json> [from_s to_s]          timestamped lines (or word@time list for a range)
  bites.py snap   <media> t1 t2 ...                        nearest energy minimum within ±0.25 s of each cut (10 ms RMS).
                  Check the result against `words`: a minimum can land after the next speaker has started.
  bites.py score  <media> <transcript.json> in-out[:label] ...   per bite: duration, LUFS, noise floor, SNR, words/s, fillers, text
Tips: check whisper's text for the interviewer's voice at bite edges (e.g. "So..." right after an answer); a bite whose
noise floor is 3+ dB worse than the rest of the interview usually has room noise or crosstalk."""
import json, re, subprocess, sys

def words(p):
    j = json.load(open(p))
    return [(s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"].strip()) for s in j["transcription"]
            if s["text"].strip() and not s["text"].strip().startswith("[_")]

def env(media, a, b):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", str(a), "-t", str(b - a), "-i", media, "-vn", "-ac", "1", "-ar", "48000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768; h = 480
    return 20 * np.log10(np.array([np.sqrt(np.mean(x[i:i + h] ** 2)) + 1e-9 for i in range(0, len(x) - h, h)]))

cmd = sys.argv[1]
if cmd == "words":
    W = words(sys.argv[2])
    if len(sys.argv) > 4:
        a, b = float(sys.argv[3]), float(sys.argv[4]); print(" ".join(f"{t}@{s:.2f}" for s, e, t in W if a <= s <= b))
    else:
        line, st = [], None
        for s, e, t in W:
            st = s if st is None else st; line.append(t)
            if t.endswith((".", "?")) or len(line) >= 16:
                print(f"{int(st // 60)}:{st % 60:05.2f} {' '.join(line)}"); line, st = [], None
elif cmd == "snap":
    import numpy as np
    for t in map(float, sys.argv[3:]):
        e = env(sys.argv[2], t - 0.25, t + 0.25); i = int(np.argmin(e))
        print(f"{t:.2f} -> {t - 0.25 + i / 100:.2f}  ({e[i]:.0f} dB)")
elif cmd == "score":
    import numpy as np
    media, W = sys.argv[2], words(sys.argv[3])
    for arg in sys.argv[4:]:
        rng, _, lab = arg.partition(":"); a, b = map(float, rng.split("-"))
        o = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(a), "-t", str(b - a), "-i", media, "-vn", "-af", "pan=mono|c0=c0,ebur128", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
        L = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1]); e = env(media, a, b)
        fl = np.percentile(e, 5); ws = [t for s, _, t in W if a - 0.05 <= s < b - 0.05]; txt = " ".join(ws)
        fill = sum(t.lower().strip(",.") in ("um", "uh") for t in ws) + txt.lower().count("you know") + txt.lower().count("kind of")
        print(f"{lab or rng:28s} {b - a:5.1f}s {L:6.1f} LUFS floor {fl:6.1f} SNR {np.percentile(e, 50) - fl:4.1f} "
              f"{len(ws) / (b - a):3.1f} w/s fillers {fill} | {txt[:100]}")
