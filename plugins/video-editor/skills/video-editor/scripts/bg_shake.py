#!/usr/bin/env python3
# Usage: scripts/vpy bg_shake.py ranges.json   (same format as shake_score.mjs: [{id,file,in,dur}]). Bar: jit <=0.8%, peak <=2%.
# Camera shake from background only: features in the outer border ring (subjects mostly central), RANSAC similarity,
# jitter = RMS of (cumulative path - 1 s moving average) in % of width; peak = max frame-to-frame residual jump.
import sys,json,subprocess,numpy as np,cv2
W,H,FPS=640,360,24
rng=json.load(open(sys.argv[1]))
mask=np.zeros((H,W),np.uint8); mask[:]=255; mask[int(H*.25):int(H*.85),int(W*.25):int(W*.75)]=0
for r in rng:
    p=subprocess.run(["ffmpeg","-v","error","-ss",str(r["in"]),"-t",str(r["dur"]+0.05),"-i",r["file"],"-vf",f"fps={FPS},scale={W}:{H}","-pix_fmt","gray","-f","rawvideo","-"],capture_output=True).stdout
    fr=np.frombuffer(p,np.uint8).reshape(-1,H,W)
    dx=[];dy=[];inl=[]
    for a,b in zip(fr[:-1],fr[1:]):
        pts=cv2.goodFeaturesToTrack(a,300,0.01,8,mask=mask)
        if pts is None or len(pts)<10: dx.append(0);dy.append(0);continue
        nx,st,_=cv2.calcOpticalFlowPyrLK(a,b,pts,None); g=st.ravel()==1
        if g.sum()<10: dx.append(0);dy.append(0);continue
        m,inn=cv2.estimateAffinePartial2D(pts[g],nx[g],ransacReprojThreshold=1.0)
        if m is None: dx.append(0);dy.append(0);continue
        dx.append(m[0,2]);dy.append(m[1,2]); inl.append(inn.mean())
    tx,ty=np.cumsum(dx),np.cumsum(dy); k=FPS; ker=np.ones(k)/k
    sx=np.convolve(np.pad(tx,k//2,mode="edge"),ker,"valid")[:len(tx)]; sy=np.convolve(np.pad(ty,k//2,mode="edge"),ker,"valid")[:len(ty)]
    res=np.hypot(tx-sx,ty-sy); step=np.hypot(np.diff(tx-sx),np.diff(ty-sy)) if len(tx)>1 else np.array([0])
    print(f"{r['id']:20s} jit {100*np.sqrt(np.mean(res**2))/W:5.2f}%  peak {100*step.max()/W:5.2f}%  inliers {np.mean(inl) if inl else 0:.2f}")
