#!/usr/bin/env python3
# Per-frame (6 fps) camera motion (phase correlation, px/frame at 320 wide) + sharpness of a clip/proxy -> csv; finds whips, focus pulls, blockages. vpy cam_scan.py clip.mov out.csv
import sys, subprocess, numpy as np, cv2
f,out=sys.argv[1],sys.argv[2]; W,H=320,180
p=subprocess.Popen(['ffmpeg','-v','error','-i',f,'-vf',f'fps=6,scale={W}:{H}','-f','rawvideo','-pix_fmt','gray','-'],stdout=subprocess.PIPE)
prev=None; i=0; rows=[]
win=cv2.createHanningWindow((W,H),cv2.CV_32F)
while True:
    b=p.stdout.read(W*H)
    if len(b)<W*H: break
    g=np.frombuffer(b,np.uint8).reshape(H,W).astype(np.float32)
    sh=cv2.Laplacian(g,cv2.CV_32F).var()
    mv=0.0
    if prev is not None:
        (dx,dy),_=cv2.phaseCorrelate(prev,g,win); mv=float(np.hypot(dx,dy))
    rows.append((i/6,mv,sh)); prev=g; i+=1
np.savetxt(out,np.array(rows),fmt='%.3f',delimiter=',',header='t,motion,sharp')
