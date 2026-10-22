# Warm ambient pad (open root+fifth drone, detuned voices, slow filter motion, long reverb) as a stereo 48k WAV.
# vpy pad_synth.py OUT.wav --root D --dur 34 [--cents -5] [--fade-in 3] [--fade-out 5] [--lufs -30] [--octaves 2,3] [--width 0.35 (0=mono,1=wide)]
import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve
a=sys.argv[1:]; out=a[0]
def opt(k,d): return a[a.index(k)+1] if k in a else d
NOTES=['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B']
root=NOTES.index(opt('--root','D')); dur=float(opt('--dur',30)); cents=float(opt('--cents',0))
fi=float(opt('--fade-in',3)); fo=float(opt('--fade-out',5)); tgt=float(opt('--lufs',-30)); octs=[int(o) for o in opt('--octaves','2,3').split(',')]
SR=48000; N=int((dur+4)*SR); t=np.arange(N)/SR; rng=np.random.default_rng(7)
f_of=lambda midi: 440*2**((midi-69)/12)*2**(cents/1200)
L=np.zeros(N); R=np.zeros(N)
for o in octs:
    for semis,amp in ((0,1.0),(7,0.7),(12,0.45)):   # root, fifth, octave
        f0=f_of(12*(o+1)+root+semis)
        for v in range(4):                           # detuned voices, spread in stereo
            det=2**(rng.uniform(-7,7)/1200); ph=rng.uniform(0,2*np.pi); pan=0.5+(rng.uniform(-1,1))*float(opt('--width',0.35))
            w=np.zeros(N)
            for h in range(1,12):                    # soft band-limited saw-ish tone
                if f0*h>6000: break
                w+=np.sin(2*np.pi*f0*det*h*t+ph*h)/h**1.6
            w*=amp*(0.85+0.15*np.sin(2*np.pi*rng.uniform(0.03,0.08)*t+rng.uniform(0,6)))  # slow swell
            L+=w*np.cos(pan*np.pi/2); R+=w*np.sin(pan*np.pi/2)
x=np.stack([L,R],1)
# slow-moving low-pass (two blended filter states) for warmth
lo=sosfilt(butter(2,700,'lp',fs=SR,output='sos'),x,axis=0); hi=sosfilt(butter(2,1600,'lp',fs=SR,output='sos'),x,axis=0)
m=(0.5+0.5*np.sin(2*np.pi*t/17))[:,None]; x=lo*(1-m*0.6)+hi*(m*0.6)
x=sosfilt(butter(2,70,'hp',fs=SR,output='sos'),x,axis=0)
# reverb: decaying stereo noise impulse, 3.5 s
ir_t=np.arange(int(3.5*SR))/SR; ir=np.stack([rng.standard_normal(len(ir_t)),rng.standard_normal(len(ir_t))],1)*np.exp(-ir_t/1.1)[:,None]
ir=sosfilt(butter(2,3000,'lp',fs=SR,output='sos'),ir,axis=0); ir/=np.sqrt((ir**2).sum(0))
wet=np.stack([fftconvolve(x[:,c],ir[:,c])[:N] for c in range(2)],1); wm=wet.mean(1,keepdims=True); wet=wm+(wet-wm)*float(opt('--width',0.35)); x=0.55*x+0.45*wet
n=int(dur*SR); x=x[:n]; e=np.ones(n)
e[:int(fi*SR)]=np.sin(np.linspace(0,np.pi/2,int(fi*SR)))**2; e[n-int(fo*SR):]=np.cos(np.linspace(0,np.pi/2,int(fo*SR)))**2
x*=e[:,None]
# loudness to target (BS.1770 K-weighting, ungated is fine for a steady pad)
from scipy.signal import lfilter
k=lfilter([1,-2,1],[1,-1.99004745483398,0.99007225036621],lfilter([1.53512485958697,-2.69169618940638,1.19839281085285],[1,-1.69065929318241,0.73248077421585],x,axis=0),axis=0)
s=slice(int(fi*SR),n-int(fo*SR)); l=-0.691+10*np.log10((k[s]**2).mean(0).sum()); x*=10**((tgt-l)/20)
sf.write(out,x.astype(np.float32),SR,subtype='PCM_24'); print(f'{out}: {dur}s, {NOTES[root]} root+fifth, {cents:+.0f} cents, {tgt} LUFS (body), peak {20*np.log10(np.abs(x).max()):.1f} dBFS')
