#!/usr/bin/env python3
# Audio-sync recordings to a reference: speech-band log-energy xcorr, refined on raw audio. vpy audio_sync.py ref.wav other.wav ... (16 kHz mono wavs) -> time in ref where each file starts
import sys, numpy as np, wave
from scipy.signal import butter, sosfiltfilt, fftconvolve
def load(p):
    w=wave.open(p); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768; return x, w.getframerate()
sos=butter(4,[300,3000],btype='band',fs=16000,output='sos')
def env(x):
    y=sosfiltfilt(sos,x); n=len(y)//160; e=np.log(np.sqrt((y[:n*160].reshape(n,160)**2).mean(1))+1e-5)
    k=np.ones(200)/200; e=e-np.convolve(e,k,'same'); return (e-e.mean())/(e.std()+1e-9)
ref,sr=load(sys.argv[1]); er=env(ref)
for p in sys.argv[2:]:
    x,_=load(p); ex=env(x)
    c=fftconvolve(er,ex[::-1],'full'); lag=np.argmax(c)-(len(ex)-1)
    pk=c.max(); srt=np.sort(c)[::-1]; second=max(c[np.r_[0:max(0,np.argmax(c)-300), min(len(c),np.argmax(c)+300):len(c)]])
    off=lag/100.0
    # refine on raw audio over up to 60 s of overlap
    a0=max(0,int(off*sr)); b0=a0-int(off*sr)
    mid=min(len(ref)-a0,len(x)-b0)//2
    L=min(int(60*sr), 2*(mid-1600))  # up to 60 s, kept inside the overlap (short clips)
    ra=ref[a0+mid-L//2:a0+mid+L//2]; xb=x[b0+mid-L//2-1600:b0+mid+L//2+1600]
    cc=fftconvolve(xb, ra[::-1],'valid'); fine=(np.argmax(np.abs(cc))-1600)/sr
    print(f"{p.split('/')[-1]}: starts at ref {off-fine:.4f}s (coarse {off:.2f}, peak/2nd {pk/second:.2f})")
