#!/usr/bin/env python3
# Best musical splice for trimming inside live music: out at a, in at b, chosen by chroma + mel similarity of the
# 3 s before each side (and similar level). Crossfade the join ~1 s equal-power.
# vpy splice_find.py ROOM.wav OUT_FROM OUT_TO IN_FROM IN_TO [--offset S]
#   times in timeline seconds; --offset = timeline time of the audio file's first sample (default 0). Needs IN_TO > OUT_FROM.
import sys, numpy as np, librosa
a=sys.argv[1:]; f=a[0]; o0,o1,i0,i1=map(float,a[1:5]); off=float(a[a.index('--offset')+1]) if '--offset' in a else 0.0
y,sr=librosa.load(f,sr=22050,offset=max(0,o0-off-4),duration=i1-o0+8); t0=max(off,o0-4); hop=512; fps=sr/hop
C=librosa.feature.chroma_cqt(y=y,sr=sr,hop_length=hop); Mm=librosa.power_to_db(librosa.feature.melspectrogram(y=y,sr=sr,hop_length=hop,n_mels=40))
F=np.vstack([C*3,(Mm-Mm.mean())/Mm.std()]); rms=librosa.feature.rms(y=y,hop_length=hop)[0]
fr=lambda t:int((t-t0)*fps); W=int(3*fps)
def vec(t): i=fr(t); return F[:,max(0,i-W):i].flatten()
best=[]
for ta in np.arange(o0,o1,0.1):
    va=vec(ta)
    for tb in np.arange(i0,i1,0.1):
        vb=vec(tb)
        if len(va)!=len(vb): continue
        r=np.corrcoef(va,vb)[0,1]; la=20*np.log10(rms[fr(ta)]+1e-9); lb=20*np.log10(rms[fr(tb)]+1e-9)
        best.append((r-0.02*abs(la-lb),ta,tb,r,la,lb))
best.sort(reverse=True)
for s,ta,tb,r,la,lb in best[:5]: print(f'out {int(ta//60)}:{ta%60:05.2f} -> in {int(tb//60)}:{tb%60:05.2f}  r={r:.3f}  level {la:.1f}/{lb:.1f} dB')
print('Use r > 0.8 with similar levels; listen to the join.')
