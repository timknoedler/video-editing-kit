#!/usr/bin/env python3
"""Usage: vpy xml_audio_mixdown.py SEQ.xml OUT.wav  -- offline audio mixdown of a Premiere FCP XML export (48 kHz float).
Checks what Premiere will actually play: clip positions, in-points and Audio Levels (static + keyframes). Then run ebur128/peak checks on OUT.wav. Assumes stereo pairs on odd/even XML tracks."""
import sys, xml.etree.ElementTree as ET, numpy as np, soundfile as sf, subprocess, urllib.parse
r=ET.parse(sys.argv[1]).getroot(); seq=r.find('.//sequence'); tb=24000/1001; sr=48000
N=int(int(seq.findtext('duration'))/tb*sr)+sr; mix=np.zeros((N,2))
files={}
for f in r.iter('file'):
    p=f.find('pathurl')
    if p is not None and f.get('id'): files[f.get('id')]=urllib.parse.unquote(p.text.replace('file://localhost','').replace('file://',''))
seen=set()
for ti,t in enumerate(seq.findall('./media/audio/track')):
    for c in t.findall('clipitem'):
        s,e,i=int(c.findtext('start')),int(c.findtext('end')),int(c.findtext('in'))
        if s<0: continue
        fid=c.find('file').get('id'); path=files.get(fid)
        key=(c.findtext('name'),s)
        st=c.find('sourcetrack'); ch=int(st.findtext('trackindex')) if st is not None else 1
        d=(e-s)/tb
        raw=subprocess.run(['ffmpeg','-v','error','-ss',str(i/tb),'-i',path,'-t',str(d),'-vn','-ac','2','-ar',str(sr),'-f','f32le','-'],capture_output=True).stdout
        x=np.frombuffer(raw,np.float32).reshape(-1,2).astype(float)
        mono=x[:,ch-1] if x.shape[1]>=ch else x[:,0]
        g=np.ones(len(mono)); cg=1.0
        for p in c.iter('parameter'):
            if p.findtext('parameterid')=='level':
                kf=p.findall('keyframe')
                if kf:
                    w=np.array([int(k.findtext('when')) for k in kf])/tb - i/tb; v=np.array([float(k.findtext('value')) for k in kf])
                    g=np.interp(np.arange(len(mono))/sr, w, v)
                else: g=g*float(p.findtext('value'))
            if p.findtext('parameterid')=='Gain(dB)': cg*=10**(float(p.findtext('value'))/20)   # clip Gain (Audio Gain dialog)
        a=int(s/tb*sr); n=min(len(mono),N-a)
        # each XML audio clipitem is one channel of a stereo pair: route by track parity (odd tracks L, even R)
        mix[a:a+n, ti%2]+= (mono*g*cg)[:n]
mix=mix[:int(int(seq.findtext('duration'))/tb*sr)]
sf.write(sys.argv[2],mix,sr,subtype='FLOAT'); print('wrote',sys.argv[2], 'peak %.2f dBFS'%(20*np.log10(np.abs(mix).max())))
