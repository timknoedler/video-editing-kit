# Tonal stats of finished films for grade matching: scripts/vpy tone_stats.py film1.mp4 film2.mp4 ... -> median p2/p50/p98 luma, contrast (sd), saturation (frames every 2 s, skips first 5 s / last 15 s)
import subprocess,numpy as np,sys,cv2
def stats(p,step=2.0,skip=(0,0)):
    d=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout)
    W,H=320,180
    b=subprocess.run(['ffmpeg','-v','error','-i',p,'-vf',f'fps=1/{step},scale={W}:{H}','-pix_fmt','bgr24','-f','rawvideo','-'],capture_output=True).stdout
    fr=np.frombuffer(b,np.uint8).reshape(-1,H,W,3)
    t=np.arange(len(fr))*step; keep=(t>skip[0])&(t<d-skip[1]); fr=fr[keep]
    out=[]
    for f in fr:
        y=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY).astype(float); y=y[int(H*0.06):int(H*0.94)]
        if y.mean()<8: continue
        hsv=cv2.cvtColor(f,cv2.COLOR_BGR2HSV)
        out.append([np.percentile(y,2),np.percentile(y,50),np.percentile(y,98),y.std(),hsv[...,1].mean()])
    a=np.array(out); return np.median(a,0)
for p in sys.argv[1:]:
    s=stats(p,skip=(5,15)); print(f"{p.split('/')[-1][:40]:40s} p2 {s[0]:5.1f} p50 {s[1]:5.1f} p98 {s[2]:5.1f} contrast(sd) {s[3]:5.1f} sat {s[4]:5.1f}")
