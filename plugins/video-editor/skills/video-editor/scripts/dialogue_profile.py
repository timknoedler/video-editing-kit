# Per-speech-region profile of a voice stem (level, noise floor, HF/mid and LF/mid tone) to find inconsistent dialogue: scripts/vpy dialogue_profile.py voice.wav
import numpy as np,subprocess,sys
b=subprocess.run(['ffmpeg','-v','error','-i',sys.argv[1],'-ac','1','-ar','16000','-f','f32le','-'],capture_output=True).stdout
x=np.frombuffer(b,np.float32).astype(np.float64); sr=16000
hop=sr//10; n=len(x)//hop
fr=x[:n*hop].reshape(n,hop); rms=20*np.log10(np.sqrt((fr**2).mean(1))+1e-9)
act=rms>-45
# merge into regions (gap < 1.5 s)
regs=[];s=None;last=-99
for i,a in enumerate(act):
    if a:
        if s is None or i-last>15: 
            if s is not None: regs.append((s,last))
            s=i
        last=i
if s is not None: regs.append((s,last))
from numpy.fft import rfft
for a,bb in regs:
    if bb-a<8: continue
    seg=x[a*hop:(bb+1)*hop]
    lv=20*np.log10(np.sqrt(np.mean(seg**2)))
    # speech-active frames only
    r=rms[a:bb+1]; sp=r[r>np.percentile(r,40)]
    S=np.abs(rfft(seg[:len(seg)//2048*2048].reshape(-1,2048)*np.hanning(2048),axis=1)).mean(0); f=np.fft.rfftfreq(2048,1/sr)
    hf=10*np.log10(S[(f>4000)&(f<7500)].sum()**2/S[(f>300)&(f<3000)].sum()**2)
    lo=10*np.log10(S[(f<200)].sum()**2/S[(f>300)&(f<3000)].sum()**2)
    floor=np.percentile(r,10)
    print(f"{a/10:6.1f}-{(bb+1)/10:6.1f} ({(bb-a)/10:4.1f}s) speechRMS {np.mean(sp):6.1f} floor {floor:6.1f} HF/mid {hf:5.1f} LF/mid {lo:5.1f}")
