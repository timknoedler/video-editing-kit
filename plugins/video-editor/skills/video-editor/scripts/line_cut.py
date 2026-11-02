#!/usr/bin/env python3
# Cut a dialogue line from its WORDS, not from guessed times (on a wedding film, whisper-guess in/out points were up to
# ~1 s off, so energy snapping within +-0.45 s still clipped first/last words: "the loud ONE", "it was always YOU").
# cut(file, a, b, text): re-transcribes [a-4, b+4] of the file with whisper.cpp (cached), aligns `text` to the words, then
# snaps the in point to the onset before the first word and the out point to the first 120 ms pause after the last word
# (or, when the speaker runs straight on, the quietest point before the next word). Returns (in, out, info).
# verify(file, in, out, text): transcribes just the cut and reports missing / extra words at the edges.
# CLI: line_cut.py MEDIA a b "text of the line"     (prints the cut and the verify result)
# Cache: JSON next to the media's job (pass cache= path), keyed by file + window.
import json, os, re, subprocess, sys, tempfile, shutil, difflib
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
M = os.environ.get("WHISPER_MODEL") or next((p for p in (
    os.path.expanduser("~/Library/Application Support/whisper.cpp/models/ggml-large-v3-turbo.bin"),
    os.path.expanduser("~/whisper.cpp/models/ggml-large-v3-turbo.bin")) if os.path.exists(p)), "")
_C = {}; _CP = [None]
def use_cache(p):
    _CP[0] = p
    if p and os.path.exists(p): _C.update(json.load(open(p)))
def _save():
    if _CP[0]: json.dump(_C, open(_CP[0], "w"))
def norm(w): return re.sub(r"[^a-z0-9]", "", w.lower().replace("’", "'"))
def words(f, a, b):
    """[(word, start, end)] on the file's clock for the window [a, b] (whisper tokens merged into words)."""
    key = f"dtw|{f}|{a:.2f}|{b:.2f}"
    if key in _C: return [tuple(x) for x in _C[key]]
    tmp = tempfile.mkdtemp()
    try:
        w = f"{tmp}/w.wav"
        subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-ss", f"{max(0, a):.3f}", "-t", f"{b - max(0, a):.3f}", "-i", f, "-vn", "-ac", "1", "-ar", "16000", w], check=True)
        subprocess.run(["whisper-cli", "-m", M, "-f", w, "-l", "en", "-nfa", "-dtw", "large.v3.turbo", "-ojf", "-of", f"{tmp}/w", "-np"], capture_output=True, check=True)
        out = []
        for s in json.load(open(f"{tmp}/w.json"))["transcription"]:
            for tk in s.get("tokens", []):
                t = tk["text"]
                if t.startswith("[_") or not t.strip(): continue
                # DTW token time (needs -nfa): plain token offsets drift by 1 s+ inside a window
                t0 = max(0, a) + (tk["t_dtw"]/100 if tk.get("t_dtw", -1) >= 0 else tk["offsets"]["from"]/1000)
                if (t.startswith(" ") or not out) and norm(t): out.append([t.strip(), t0, t0])
                elif out:
                    out[-1][0] += t.strip()
        for i, w in enumerate(out):                       # word end ~ next word's start (energy snapping refines it)
            w[2] = min(out[i+1][1], w[1] + 1.0) if i + 1 < len(out) else w[1] + 0.6
        _C[key] = out; _save(); return [tuple(x) for x in out]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
def _env(f, lo, hi):
    x = sf.read(f, start=int(max(0, lo)*48000) if sf.info(f).samplerate == 48000 else 0, stop=int(hi*48000), always_2d=True)[0][:, 0]
    x = sosfiltfilt(butter(2, 100, 'hp', fs=48000, output='sos'), x)
    H, W = 480, 960; n = max(0, (len(x) - W)//H)
    e = np.array([20*np.log10(np.sqrt(np.mean(x[i*H:i*H+W]**2)) + 1e-9) for i in range(n)]); t = max(0, lo) + (np.arange(n)*H + W/2)/48000
    return t, e
def align(ws, text):
    """Indices (i0, i1) in ws of the first and last word of text (fuzzy, longest matching run)."""
    tw = [norm(x) for x in text.split() if norm(x)]; ww = [norm(w[0]) for w in ws]
    sm = difflib.SequenceMatcher(None, ww, tw, autojunk=False); blocks = [m for m in sm.get_matching_blocks() if m.size]
    if not blocks: return None
    # first matched word of the text and last matched word, mapped back; require the match to cover the text's ends
    i0 = blocks[0].a - blocks[0].b if blocks[0].b <= 2 else blocks[0].a
    last = blocks[-1]; i1 = last.a + last.size - 1 + (len(tw) - (last.b + last.size)) if len(tw) - (last.b + last.size) <= 2 else last.a + last.size - 1
    return max(0, i0), min(len(ws) - 1, i1)
def cut(f, a, b, text, pad_in=0.06, tail=0.10, slack=2.0):
    """slack: only words starting within [a - slack, b + slack] are matched (small slack picks the right copy of a
    repeated phrase, e.g. a vow repeated after the officiant)."""
    ws = words(f, a - 4, b + 4); sel = [i for i, w in enumerate(ws) if a - slack <= w[1] <= b + slack]
    al = align([ws[i] for i in sel], text) if sel else None
    if al is None: return a, b, {"ok": False, "why": "text not found"}
    i0, i1 = sel[al[0]], sel[al[1]]; w0, w1 = ws[i0], ws[i1]
    prev_end = ws[i0-1][2] if i0 > 0 else w0[1] - 1.0; next_st = ws[i1+1][1] if i1 + 1 < len(ws) else w1[2] + 1.5
    t, e = _env(f, w0[1] - 1.2, w1[2] + 1.6)
    seg = e[(t >= w0[1]) & (t <= w1[2])]
    floor = np.percentile(e, 8); thr = floor + 0.30*(np.percentile(seg, 80) - floor) if len(seg) > 4 else floor + 6
    below = e < thr
    # start: walk back from the first word's start to where the voice begins (max 0.35 s), stay after the previous word
    s = w0[1]; j = np.searchsorted(t, w0[1])
    while j > 0 and t[j] > w0[1] - 0.35 and not below[max(0, j-3):j+1].all(): j -= 1
    s = min(w0[1], t[j] if j < len(t) else w0[1]) - pad_in
    if s < prev_end:                                   # running speech: quietest point between the two words
        m = (t >= prev_end - 0.05) & (t <= w0[1]); s = t[m][np.argmin(e[m])] if m.any() else (prev_end + w0[1])/2
    # end: first 120 ms pause after the last word's start + 0.12 (search to its end + 0.6), before the next word
    nb = None
    for k in np.where((t >= w1[1] + 0.12) & (t <= min(w1[2] + 0.6, next_st)))[0]:
        if below[k:k+12].all(): nb = t[k] + tail; break
    if nb is None:
        m = (t >= w1[2] - 0.05) & (t <= min(next_st + 0.05, w1[2] + 0.6)); nb = t[m][np.argmin(e[m])] + 0.02 if m.any() else w1[2] + 0.1
    nb = min(nb, next_st - 0.02) if next_st > w1[2] else nb
    return round(float(s), 3), round(float(nb), 3), {"ok": True, "first": w0[0], "last": w1[0], "prev": ws[i0-1][0] if i0 > 0 else "", "next": ws[i1+1][0] if i1+1 < len(ws) else ""}
def verify(f, a, b, text):
    ws = words(f, a, b); got = [norm(w[0]) for w in ws]; tw = [norm(x) for x in text.split() if norm(x)]
    sm = difflib.SequenceMatcher(None, got, tw, autojunk=False)
    missing = [tw[j] for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag in ("delete", "replace", "insert") for j in range(j1, j2)]
    head_ok = bool(got[:3]) and any(x in got[:4] for x in tw[:2]); tail_ok = bool(got) and any(x in got[-4:] for x in tw[-2:])
    return {"heard": " ".join(w[0] for w in ws), "missing": missing, "head_ok": head_ok, "tail_ok": tail_ok}
if __name__ == "__main__":
    f, a, b, text = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    i, o, info = cut(f, a, b, text); print(f"cut {i:.3f}-{o:.3f}", info); print(verify(f, i, o, text))
