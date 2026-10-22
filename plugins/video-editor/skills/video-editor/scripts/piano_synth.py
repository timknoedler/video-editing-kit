# Soft felt-piano part from a notes JSON [[t, midi, vel(0-1), dur], ...] -> stereo 48k WAV with room reverb.
# vpy piano_synth.py notes.json OUT.wav --len 34 [--cents -5] [--lufs -26]
import sys, json, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, lfilter
a=sys.argv[1:]; notes=json.load(open(a[0])); out=a[1]
def opt(k,d): return a[a.index(k)+1] if k in a else d
L=float(opt('--len',30)); cents=float(opt('--cents',0)); tgt=float(opt('--lufs',-26))
SR=48000; N=int((L+4)*SR); x=np.zeros((N,2)); rng=np.random.default_rng(3)
for t0,midi,vel,dur in notes:
    f0=440*2**((midi-69)/12)*2**(cents/1200); n=int((dur+3.0)*SR); t=np.arange(n)/SR; s=np.zeros(n)
    B=0.00025; pan=np.clip(0.5+(midi-62)/60,0.3,0.7)
    for h in range(1,16):
        fh=h*f0*np.sqrt(1+B*h*h)
        if fh>9000: break
        amp=vel**(0.6+0.12*h)/h**1.15*np.exp(-0.05*h)
        tau=2.8/(1+0.35*h)*(220/f0)**0.3
        for det in (-0.6,0.6):  # two strings, slow beating
            s+=0.5*amp*np.sin(2*np.pi*fh*2**(det/1200)*t+rng.uniform(0,6.28))*(0.7*np.exp(-t/tau)+0.3*np.exp(-t/(tau*4)))
    att=np.minimum(1,t/0.006); rel=np.where(t>dur,np.exp(-(t-dur)/0.35),1.0); s*=att*rel
    i=int(t0*SR); j=min(N,i+n); x[i:j,0]+=s[:j-i]*np.cos(pan*np.pi/2); x[i:j,1]+=s[:j-i]*np.sin(pan*np.pi/2)
x=sosfilt(butter(2,5000,'lp',fs=SR,output='sos'),x,axis=0)   # felt / soft
ir_t=np.arange(int(3.0*SR))/SR; ir=np.stack([rng.standard_normal(len(ir_t)) for _ in range(2)],1)*np.exp(-ir_t/0.9)[:,None]
ir=sosfilt(butter(2,3500,'lp',fs=SR,output='sos'),ir,axis=0); ir/=np.sqrt((ir**2).sum(0))
wet=np.stack([fftconvolve(x[:,c],ir[:,c])[:N] for c in range(2)],1); x=0.6*x+0.4*wet; x=x[:int(L*SR)]
k=lfilter([1,-2,1],[1,-1.99004745483398,0.99007225036621],lfilter([1.53512485958697,-2.69169618940638,1.19839281085285],[1,-1.69065929318241,0.73248077421585],x,axis=0),axis=0)
blk=int(0.4*SR); z=np.array([(k[i:i+blk]**2).mean(0).sum() for i in range(0,len(k)-blk,blk//4)]); z=z[z>1e-9]
g=z[10*np.log10(z)>10*np.log10(z.mean())-10]; l=-0.691+10*np.log10(g.mean()); x*=10**((tgt-l)/20)
sf.write(out,x.astype(np.float32),SR,subtype='PCM_24'); print(f'{out}: {len(notes)} notes, {tgt} LUFS, peak {20*np.log10(np.abs(x).max()):.1f} dBFS')
