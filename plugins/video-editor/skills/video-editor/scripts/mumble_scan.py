#!/usr/bin/env python3
# Find Enhance Speech "mumble" artefacts: the enhanced dialogue stem is loud while the raw lav (speech band) is quiet,
# e.g. private whispers or unscripted chatter that Enhance turns into loud garbled bursts.
# excess = stem dB - raw dB - (median of that over clear speech), per 0.5 s window. Prints windows above --thresh.
# vpy mumble_scan.py RAW_LAV.wav ENHANCED.wav [--raw-offset S] [--thresh 8]
#   both files on one clock; --raw-offset = how many seconds into RAW_LAV the ENHANCED file's first sample falls (default 0).
# Then keep only windows with no words in a word-level transcript of the raw lav, and use the raw lav (HPF only) there.
import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
a=sys.argv[1:]; opt=lambda k,d: float(a[a.index(k)+1]) if k in a else d
ro=opt('--raw-offset',0.0); th=opt('--thresh',8.0)
r,sr=sf.read(a[0],always_2d=True); s,sr2=sf.read(a[1],always_2d=True)
assert sr==sr2, 'resample one file so both share a sample rate'
bp=butter(4,[300,3000],'band',fs=sr,output='sos'); r=sosfiltfilt(bp,r[int(ro*sr):,0]); s=sosfiltfilt(bp,s.mean(1))
W=sr//2; n=min(len(r),len(s))//W
db=lambda x: np.array([10*np.log10(np.mean(x[i*W:(i+1)*W]**2)+1e-14) for i in range(n)])
rd,sd=db(r),db(s); clear=(sd>-30)&(rd>np.percentile(rd,70))
off=np.median(sd[clear]-rd[clear]); ex=sd-rd-off
print(f'chain offset {off:.1f} dB; windows with excess > {th} dB (enhanced-file time):')
i=0
while i<n:
    if ex[i]>th:
        j=i
        while j+1<n and ex[j+1]>th: j+=1
        t=i/2; print(f'  {int(t//60)}:{t%60:04.1f} - {int((j+1)/2//60)}:{(j+1)/2%60:04.1f}  max excess {ex[i:j+1].max():+.1f} dB')
        i=j+1
    else: i+=1
