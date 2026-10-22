# Sampled-piano renderer from Logic's factory Steinway (EXS zone map + consolidated CAF) -> stereo 48k WAV.
# REQUIRES macOS with Logic Pro and its factory sampler library installed (default paths below; --exs/--caf for others).
# Without Logic, use piano_synth.py (fully synthetic, no samples needed).
# Soft "felt" sound by default: soft velocity layers, pedal-down (No Dampers) samples, low-pass, small room + long tail.
# vpy piano_sampler.py notes.json OUT.wav --len 32 [--cents -5] [--lufs -21] [--felt 2400] [--exs PATH] [--caf PATH]
#   notes.json: [[t_seconds, midi, velocity_0_127, hold_seconds], ...]
import sys, json, struct, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, lfilter, resample_poly
a=sys.argv[1:]; notes=json.load(open(a[0])); out=a[1]
def opt(k,d): return a[a.index(k)+1] if k in a else d
L=float(opt('--len',30)); cents=float(opt('--cents',0)); tgt=float(opt('--lufs',-21)); felt=float(opt('--felt',2400))
EXS=opt('--exs','/Library/Application Support/Logic/Sampler Instruments/01 Acoustic Pianos/Steinway Grand Piano 2.exs')
CAF=opt('--caf','/Library/Application Support/Logic/EXS Factory Samples/01 Acoustic Pianos/Steinway Piano_consolidated.caf')
import os
for _p in (EXS,CAF):
    if not os.path.exists(_p): sys.exit(f'piano_sampler.py needs Logic Pro\'s factory Steinway library (not found: {_p}). Pass --exs/--caf, or use piano_synth.py instead.')
b=open(EXS,'rb').read(); i=0; groups={}; zones=[]
while i+84<=len(b):
    sig,size,cid=struct.unpack('<III',b[i:i+12]); name=b[i+20:i+84].split(b'\0')[0].decode('latin1'); d=b[i+84:i+84+size]
    if sig==0x42000101: groups[cid]=(name,d[5],d[6])
    elif sig==0x41000101:
        g=d[d.find(b'\x80\x4f\x12\x00')+4]
        zones.append(dict(root=d[1],lo=d[6],hi=d[7],start=struct.unpack('<I',d[12:16])[0],end=struct.unpack('<I',d[24:28])[0],g=g))
    i+=84+size
SR=48000; out_buf=np.zeros((int((L+8)*SR),2)); rng=np.random.default_rng(11); cache={}
def sample(z):
    k=(z['start'],z['end'])
    if k not in cache:
        x,sr=sf.read(CAF,start=z['start'],stop=z['end'],dtype='float64',always_2d=True); cache[k]=(x,sr)
    return cache[k]
for t0,midi,vel,hold in notes:
    cand=[z for z in zones if z['lo']<=midi<=z['hi'] and 'No Dampers' in groups[z['g']][0] and groups[z['g']][1]<=vel<=groups[z['g']][2]]
    if not cand: cand=[z for z in zones if z['lo']<=midi<=z['hi'] and groups[z['g']][1]<=vel<=groups[z['g']][2] and not groups[z['g']][0].startswith('p')]
    z=cand[0]; x,sr=sample(z)
    ratio=2**((midi-z['root'])/12+cents/1200)            # pitch shift by resampling (<= 1.5 semitones here)
    from fractions import Fraction; fr_=Fraction(SR/(sr*ratio)).limit_denominator(400)
    y=resample_poly(x[:int((hold+3)*sr*ratio)+sr],fr_.numerator,fr_.denominator,axis=0)   # rational approx (<0.5 cent), only the part we use
    gain=(vel/64)**1.4                                      # within-layer dynamics
    n=min(len(y),int((hold+2.5)*SR)); y=y[:n]*gain
    tt=np.arange(n)/SR; y*=np.where(tt>hold,np.exp(-(tt-hold)/0.6),1.0)[:,None]   # pedal-up release
    j=int(t0*SR); m=min(len(out_buf)-j,n); out_buf[j:j+m]+=y[:m]
x=out_buf
x=sosfilt(butter(2,felt,'lp',fs=SR,output='sos'),x,axis=0)                 # felt: darker, softer hammers
x=sosfilt(butter(1,90,'hp',fs=SR,output='sos'),x,axis=0)
x=np.tanh(x*1.5)/1.5                                                         # a touch of warmth
def ir(sec,lp):
    t=np.arange(int(sec*SR))/SR; r=np.stack([rng.standard_normal(len(t)) for _ in range(2)],1)*np.exp(-t/(sec/6.9*1.0))[:,None]
    r=sosfilt(butter(2,lp,'lp',fs=SR,output='sos'),r,axis=0); return r/np.sqrt((r**2).sum(0))
room=np.stack([fftconvolve(x[:,c],ir(0.7,5000)[:,c])[:len(x)] for c in range(2)],1)
hall=np.stack([fftconvolve(x[:,c],ir(3.2,2500)[:,c])[:len(x)] for c in range(2)],1)
x=0.72*x+0.22*room+0.12*hall; x=x[:int(L*SR)]
k=lfilter([1,-2,1],[1,-1.99004745483398,0.99007225036621],lfilter([1.53512485958697,-2.69169618940638,1.19839281085285],[1,-1.69065929318241,0.73248077421585],x,axis=0),axis=0)
blk=int(0.4*SR); zz=np.array([(k[i:i+blk]**2).mean(0).sum() for i in range(0,len(k)-blk,blk//4)]); zz=zz[zz>1e-10]
zz=zz[10*np.log10(zz)>10*np.log10(zz.mean())-10]; l=-0.691+10*np.log10(zz.mean()); x*=10**((tgt-l)/20)
sf.write(out,x.astype(np.float32),SR,subtype='PCM_24'); print(f'{out}: {len(notes)} notes, {len(zones)} zones/{len(groups)} groups read, {tgt} LUFS, peak {20*np.log10(np.abs(x).max()):.1f} dBFS')
