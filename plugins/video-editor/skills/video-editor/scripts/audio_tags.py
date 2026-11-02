#!/usr/bin/env python3
"""Tell what's IN an audio file (or a video's audio) without listening: PANNs sound-event detection (AudioSet, 527 labels)
over time, plus optional CLAP text queries. Runs locally (weights: ~/panns_data/Cnn14_DecisionLevelMax.pth and the
HuggingFace cache for laion/clap-htsat-unfused; panns-inference fetches its weights on first run, needs wget). Use it to pick usable nat sound (laughter vs. PA music bleed), check
that an SFX is what it claims to be, or scan a shoot for moments ("cork pop", "cheering").
Usage: vpy audio_tags.py FILE [--ss 3.5] [--t 1.5] [--top 6] [--hop 0.5] [--clap "cork popping;crowd laughing;music"]
Prints: the top labels for the whole span, a per-hop timeline of the strongest labels, and CLAP similarity per query
(cosine, higher = closer; compare queries against each other, not against a fixed threshold)."""
import sys, subprocess, numpy as np, csv, os
a = sys.argv[1:]
def opt(k, d): return a[a.index(k) + 1] if k in a else d
f = a[0]; ss = float(opt("--ss", 0)); t = opt("--t", None); top = int(opt("--top", 6)); hop = float(opt("--hop", 0.5))
cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-i", f] + (["-t", t] if t else []) + ["-vn", "-ac", "1", "-ar", "32000", "-f", "f32le", "-"]
x = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32).copy()
if len(x) < 3200: sys.exit("no audio")
import torch
from panns_inference import SoundEventDetection
labels = [r["display_name"] for r in csv.DictReader(open(os.path.expanduser("~/panns_data/class_labels_indices.csv")))]
sed = SoundEventDetection(checkpoint_path=os.path.expanduser("~/panns_data/Cnn14_DecisionLevelMax.pth"), device="cpu")
fw = sed.inference(x[None, :])[0]                       # (frames, 527), 100 frames per second
clip = fw.max(0); order = np.argsort(clip)[::-1][:top]
print(f"{os.path.basename(f)} {ss:.2f}s +{len(x)/32000:.2f}s  overall: " + ", ".join(f"{labels[i]} {clip[i]:.2f}" for i in order))
step = max(1, int(hop * 100))
for s0 in range(0, fw.shape[0], step):
    seg = fw[s0:s0 + step].max(0); o = np.argsort(seg)[::-1][:3]
    print(f"  {ss + s0/100:6.2f}s  " + "  ".join(f"{labels[i]} {seg[i]:.2f}" for i in o if seg[i] > 0.05))
q = opt("--clap", None)
if q:
    from transformers import ClapModel, ClapProcessor
    m = ClapModel.from_pretrained("laion/clap-htsat-unfused"); p = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
    x48 = np.frombuffer(subprocess.run(cmd[:-8] + ["-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"], capture_output=True).stdout, np.float32).copy()
    texts = [s.strip() for s in q.split(";")]
    with torch.no_grad():
        ia = p(audios=[x48], sampling_rate=48000, return_tensors="pt"); it = p(text=texts, return_tensors="pt", padding=True)
        ea = m.get_audio_features(**ia); et = m.get_text_features(**it)
        sim = torch.nn.functional.cosine_similarity(ea, et).numpy()
    for s, v in sorted(zip(texts, sim), key=lambda z: -z[1]): print(f"  CLAP {v:+.3f}  {s}")
