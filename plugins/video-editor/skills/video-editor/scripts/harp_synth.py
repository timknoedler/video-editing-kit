# Plucked-harp synth (extended Karplus-Strong at 4x oversampling, gut-string damping, soft pluck, light body + room).
# vpy harp_synth.py notes.json OUT.wav --len 32 [--cents -5] [--lufs -25] [--env "t:db,t:db,..."]
#   notes.json: [[t_seconds, midi, velocity_0_127, decay_seconds], ...]; --env = gain automation points over time
import sys, json, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, lfilter, fftconvolve, resample_poly
a=sys.argv[1:]; notes=json.load(open(a[0])); out=a[1]
def opt(k,d): return a[a.index(k)+1] if k in a else d
L=float(opt('--len',30)); cents=float(opt('--cents',0)); tgt=float(opt('--lufs',-25)); env=opt('--env','')
SR=48000; OS=4; FS=SR*OS; buf=np.zeros((int((L+6)*SR),2)); rng=np.random.default_rng(21)
for t0,midi,vel,dec in notes:
    f0=440*2**((midi-69)/12)*2**(cents/1200); Nd=FS/f0; N=int(Nd); frac=Nd-N
    n=int((dec+0.5)*FS)
    exc=rng.standard_normal(N+2); exc=lfilter([0.5,0.5],[1],exc)                      # soft finger pluck
    p=max(2,int(N*0.18)); exc[:-p]=exc[:-p]-exc[p:]*0.6                              # pluck position comb
    exc*= (vel/90)**1.2
    x=np.zeros(n); x[:len(exc)]=exc
    sb=0.5 if f0<700 else 0.35                                                        # loop low-pass (darker gut tone), lighter up top
    Nd=FS/f0-sb; N=int(Nd); frac=Nd-N
    g=10**(-3/(dec*f0))                                                                # loop gain -> T60 = dec
    taps=np.convolve([1-sb,sb],[1-frac,frac])*g                                        # lags N, N+1, N+2
    aco=np.zeros(N+3); aco[0]=1; aco[N:N+3]=-taps
    y=lfilter([1],aco,x)
    y=resample_poly(y,1,OS)
    y*=np.minimum(1,np.arange(len(y))/(0.002*SR))
    pan=np.clip(0.5+(midi-64)/70,0.25,0.75); j=int(t0*SR); m=min(len(buf)-j,len(y))
    buf[j:j+m,0]+=y[:m]*np.cos(pan*np.pi/2); buf[j:j+m,1]+=y[:m]*np.sin(pan*np.pi/2)
x=sosfilt(butter(2,6000,'lp',fs=SR,output='sos'),buf,axis=0); x=sosfilt(butter(1,110,'hp',fs=SR,output='sos'),x,axis=0)
for fc,q,gdb in ((240,1.2,3.0),(520,1.5,2.0)):                                         # wooden soundboard warmth
    w=2*np.pi*fc/SR; al=np.sin(w)/(2*q); A=10**(gdb/40)
    bb=[1+al*A,-2*np.cos(w),1-al*A]; aa=[1+al/A,-2*np.cos(w),1-al/A]; x=lfilter(bb,aa,x,axis=0)
t=np.arange(int(2.6*SR))/SR; ir=np.stack([rng.standard_normal(len(t)) for _ in range(2)],1)*np.exp(-t/0.45)[:,None]
ir=sosfilt(butter(2,4000,'lp',fs=SR,output='sos'),ir,axis=0); ir/=np.sqrt((ir**2).sum(0))
x=0.7*x+0.3*np.stack([fftconvolve(x[:,c],ir[:,c])[:len(x)] for c in range(2)],1); x=x[:int(L*SR)]
if env:
    pts=[tuple(map(float,p.split(':'))) for p in env.split(',')]; tt=np.arange(len(x))/SR
    x*=10**(np.interp(tt,[p[0] for p in pts],[p[1] for p in pts])/20)[:,None]
k=lfilter([1,-2,1],[1,-1.99004745483398,0.99007225036621],lfilter([1.53512485958697,-2.69169618940638,1.19839281085285],[1,-1.69065929318241,0.73248077421585],x,axis=0),axis=0)
blk=int(0.4*SR); zz=np.array([(k[i:i+blk]**2).mean(0).sum() for i in range(0,len(k)-blk,blk//4)]); zz=zz[zz>1e-12]
zz=zz[10*np.log10(zz)>10*np.log10(zz.mean())-10]; l=-0.691+10*np.log10(zz.mean()); x*=10**((tgt-l)/20)
sf.write(out,x.astype(np.float32),SR,subtype='PCM_24'); print(f'{out}: {len(notes)} notes, {tgt} LUFS, peak {20*np.log10(np.abs(x).max()):.1f} dBFS')
