# Brighter, moving pad for under a song's quiet intro (an editor's note: the dark chord_pad under the toasts was "too
# mellow and doesn't match the vibe"). Chord-following detuned saws with an 8th-note pulse (sidechain-style dip on every
# 8th), a low-pass that opens over the length, an octave shimmer, a soft sub, and an optional noise riser that ends exactly
# on --riser-end (the downbeat where the song's band comes in). Stereo 48k WAV at a target loudness.
# vpy pulse_pad.py chords.json OUT.wav --dur 25 --bpm 106.96 [--beat0 0.0] [--cents 5] [--lufs -22] [--riser-end 24.9]
#   [--fade-in 3] [--depth 0.45] [--open 1800 6000]
# chords.json: [[t_start, [midi, ...]], ...] in output seconds; beat0 = output time of a downbeat (pulse phase).
import sys, json, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve, lfilter
a = sys.argv[1:]; CH = json.load(open(a[0])); out = a[1]
def opt(k, d, n=1): return (a[a.index(k)+1:a.index(k)+1+n] if n > 1 else a[a.index(k)+1]) if k in a else d
dur = float(opt('--dur', 30)); bpm = float(opt('--bpm', 100)); beat0 = float(opt('--beat0', 0)); cents = float(opt('--cents', 0))
tgt = float(opt('--lufs', -22)); rend = float(opt('--riser-end', -1)); fi = float(opt('--fade-in', 3)); depth = float(opt('--depth', 0.45))
f_open = [float(v) for v in opt('--open', ['1800', '6000'], 2)]
SR = 48000; N = int((dur + 3)*SR); t = np.arange(N)/SR; rng = np.random.default_rng(7)
f_of = lambda m: 440*2**((m-69)/12)*2**(cents/1200)
def saw(f, tt, ph, top=6000):
    w = np.zeros(len(tt))
    for h in range(1, 40):
        if f*h > top: break
        w += np.sin(2*np.pi*f*h*tt + ph*h)/h
    return w
L = np.zeros(N); R = np.zeros(N)
for i, (t0, notes) in enumerate(CH):
    t1 = CH[i+1][0] if i + 1 < len(CH) else dur + 2
    env = np.clip((t - (t0 - 0.08))/0.16, 0, 1)*np.clip(((t1 + 0.08) - t)/0.16, 0, 1); idx = np.nonzero(env)[0]
    if not len(idx): continue
    tt = t[idx]
    layers = [(m, 1.0) for m in notes] + [(m + 12, 0.35) for m in notes[1:]] + [(notes[0] - 12, 0.0)]
    for m, amp in layers:
        f0 = f_of(m)
        if amp == 0.0:                                                      # sub: pure sine on the root
            w = 0.5*np.sin(2*np.pi*f0*tt); L[idx] += w*env[idx]; R[idx] += w*env[idx]; continue
        for v in range(3):
            det = 2**(rng.uniform(-12, 12)/1200); pan = 0.5 + rng.uniform(-0.35, 0.35)
            w = saw(f0*det, tt, rng.uniform(0, 6.28))*amp*env[idx]*(1.0 if m < 60 else 0.7)
            L[idx] += w*np.cos(pan*np.pi/2); R[idx] += w*np.sin(pan*np.pi/2)
x = np.stack([L, R], 1)
# low-pass opening over the length (blend of two filter states), so the pad builds toward the riser
lo = sosfilt(butter(2, f_open[0], 'lp', fs=SR, output='sos'), x, axis=0); hi = sosfilt(butter(2, f_open[1], 'lp', fs=SR, output='sos'), x, axis=0)
m = np.clip(t/dur, 0, 1)[:, None]**1.5; x = lo*(1 - m) + hi*m
x = sosfilt(butter(2, 45, 'hp', fs=SR, output='sos'), x, axis=0)
# 8th-note pulse: dip at each 8th, recovering over the 8th (sidechain feel)
e8 = 60/bpm/2; ph = ((t - beat0) % e8)/e8; pulse = 1 - depth*np.exp(-ph*5.0)
x *= pulse[:, None]
# medium room, 2.2 s
ir_t = np.arange(int(2.2*SR))/SR; ir = rng.standard_normal((len(ir_t), 2))*np.exp(-ir_t/0.55)[:, None]
ir = sosfilt(butter(2, 5000, 'lp', fs=SR, output='sos'), ir, axis=0); ir /= np.sqrt((ir**2).sum(0))
wet = np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1); x = 0.75*x + 0.4*wet
# riser: band-passed noise, rising level and centre frequency over the last 4 s, cut on the downbeat
if rend > 0:
    r0 = max(0, rend - 4.0); k = (t >= r0) & (t < rend); n = rng.standard_normal((N, 2)); ramp = np.zeros(N)
    ramp[k] = ((t[k] - r0)/(rend - r0))**2.2
    nb = sosfilt(butter(2, [1500, 9000], 'bp', fs=SR, output='sos'), n, axis=0)
    x += nb*ramp[:, None]*0.08
    x[t >= rend] *= np.exp(-(t[t >= rend] - rend)/0.25)[:, None]       # the pad gets out of the band's way
fade = np.clip(t/max(fi, 1e-3), 0, 1); x *= (np.sin(fade*np.pi/2)**2)[:, None]
x = x[:int(dur*SR)]
def kw(y):
    b1=[1.53512485958697,-2.69169618940638,1.19839281085285]; a1=[1,-1.69065929318241,0.73248077421585]
    return lfilter([1,-2,1],[1,-1.99004745483398,0.99007225036621],lfilter(b1,a1,y,axis=0),axis=0)
z = (kw(x)**2).sum(1); blk = int(0.4*SR); zz = np.array([z[i:i+blk].mean() for i in range(0, len(z)-blk, SR//10)])
l = -0.691 + 10*np.log10(zz + 1e-12); g = -0.691 + 10*np.log10(zz[l > -70].mean()) - 10; I = -0.691 + 10*np.log10(zz[l > g].mean())
x *= 10**((tgt - I)/20); x *= min(1, 0.7/np.abs(x).max())
sf.write(out, x.astype(np.float32), SR, subtype='PCM_24'); print(f"{out}: {dur:.1f} s, {tgt} LUFS")
