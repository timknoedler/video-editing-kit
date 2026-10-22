# Warm chord-following pad (not an organ drone): each chord swells in and crossfades into the next, detuned soft voices,
# heavy slowly-breathing low-pass, a little filtered air, long dark reverb. Stereo 48k WAV at a target loudness.
# vpy chord_pad.py chords.json OUT.wav --dur 33 [--cents -5] [--xfade 1.6] [--lufs -23] [--fade-in 4] [--fade-out 3] [--width 0.5]
# chords.json: [[t_start, [midi, midi, ...]], ...]  (voicing per chord; times in output seconds)
import sys, json, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, lfilter
a=sys.argv[1:]; CH=json.load(open(a[0])); out=a[1]
def opt(k,d): return a[a.index(k)+1] if k in a else d
dur=float(opt('--dur',30)); cents=float(opt('--cents',0)); xf=float(opt('--xfade',1.6)); tgt=float(opt('--lufs',-23))
fi=float(opt('--fade-in',4)); fo=float(opt('--fade-out',3)); width=float(opt('--width',0.5))
SR=48000; N=int((dur+5)*SR); t=np.arange(N)/SR; rng=np.random.default_rng(11)
f_of=lambda m: 440*2**((m-69)/12)*2**(cents/1200)
L=np.zeros(N); R=np.zeros(N)
for i,(t0,notes) in enumerate(CH):
    t1=CH[i+1][0] if i+1<len(CH) else dur+4
    # chord envelope: slow swell in (xf), hold, slow release overlapping the next chord's swell
    env=np.clip((t-(t0-xf*0.5))/xf,0,1)*np.clip(((t1+xf*0.5)-t)/xf,0,1); env=np.sin(env*np.pi/2)**2
    idx=np.nonzero(env)[0]
    if not len(idx): continue
    tt=t[idx]
    for m in notes:
        f0=f_of(m); amp=1.0 if m<60 else 0.6
        for v in range(3):
            det=2**(rng.uniform(-9,9)/1200); ph=rng.uniform(0,2*np.pi); pan=0.5+rng.uniform(-1,1)*width*0.5
            w=np.zeros(len(idx))
            for h in range(1,9):
                if f0*h>3500: break
                w+=np.sin(2*np.pi*f0*det*h*tt+ph*h)/h**2.0          # softer than a saw: fewer upper partials = less organ
            w*=amp*env[idx]*(0.8+0.2*np.sin(2*np.pi*rng.uniform(0.05,0.12)*tt+rng.uniform(0,6)))
            L[idx]+=w*np.cos(pan*np.pi/2); R[idx]+=w*np.sin(pan*np.pi/2)
x=np.stack([L,R],1)
# breathing low-pass: blend of 500 Hz and 1300 Hz states, slow cycle; plus a little band-passed air that follows the level
lo=sosfilt(butter(2,500,'lp',fs=SR,output='sos'),x,axis=0); hi=sosfilt(butter(2,1300,'lp',fs=SR,output='sos'),x,axis=0)
m=(0.5+0.5*np.sin(2*np.pi*t/11-1.2))[:,None]; x=lo*(1-0.55*m)+hi*(0.55*m)
lvl=sosfilt(butter(1,2,'lp',fs=SR,output='sos'),np.abs(x).mean(1))
air=sosfilt(butter(2,[2500,7000],'bp',fs=SR,output='sos'),rng.standard_normal((N,2)),axis=0)*lvl[:,None]*0.05
x=sosfilt(butter(2,60,'hp',fs=SR,output='sos'),x+air,axis=0)
# long dark reverb, 5 s
ir_t=np.arange(int(5*SR))/SR; ir=rng.standard_normal((len(ir_t),2))*np.exp(-ir_t/1.6)[:,None]
ir=sosfilt(butter(2,2200,'lp',fs=SR,output='sos'),ir,axis=0); ir/=np.sqrt((ir**2).sum(0))
wet=np.stack([fftconvolve(x[:,c],ir[:,c])[:N] for c in range(2)],1); wm=wet.mean(1,keepdims=True); wet=wm+(wet-wm)*width
x=0.45*x+0.55*wet
n=int(dur*SR); x=x[:n]; e=np.ones(n)
e[:int(fi*SR)]=np.sin(np.linspace(0,np.pi/2,int(fi*SR)))**2; e[n-int(fo*SR):]=np.cos(np.linspace(0,np.pi/2,int(fo*SR)))**2
x*=e[:,None]
k=lfilter([1,-2,1],[1,-1.99004745483398,0.99007225036621],lfilter([1.53512485958697,-2.69169618940638,1.19839281085285],[1,-1.69065929318241,0.73248077421585],x,axis=0),axis=0)
s=slice(int(fi*SR),n-int(fo*SR)); l=-0.691+10*np.log10((k[s]**2).mean(0).sum()); x*=10**((tgt-l)/20)
sf.write(out,x.astype(np.float32),SR,subtype='PCM_24'); print(f'{out}: {dur}s, {len(CH)} chords, {cents:+.0f} cents, {tgt} LUFS (body), peak {20*np.log10(np.abs(x).max()):.1f} dBFS')
