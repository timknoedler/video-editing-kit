# Apply a .cube 3D LUT (Resolve order: R fastest) to an 8-bit frame at a Lumetri-style intensity (115 = extrapolate 15% past the LUT).
# Offline copy of a LUT adjustment layer, to measure frames in the graded domain without a render.
# vpy lut_apply.py LOOK.cube IN.png OUT.png [intensity]   (also importable: load(), apply())
import numpy as np, cv2, sys
from scipy.ndimage import map_coordinates
def load(p):
    rows=[l.split() for l in open(p) if l.strip() and l.strip()[0] in '0123456789-.']
    n=round(len(rows)**(1/3)); return np.array(rows,float).reshape(n,n,n,3), n   # [b][g][r]
def apply(img_bgr,lut,n,intensity=100):
    rgb=img_bgr[:,:,::-1].astype(float)/255; c=rgb*(n-1)
    coords=[c[:,:,2].ravel(),c[:,:,1].ravel(),c[:,:,0].ravel()]
    out=np.stack([map_coordinates(lut[:,:,:,k],coords,order=1,mode='nearest').reshape(rgb.shape[:2]) for k in range(3)],-1)
    out=rgb+(intensity/100)*(out-rgb); return (np.clip(out,0,1)*255+0.5).astype(np.uint8)[:,:,::-1]
if __name__=='__main__':
    L,n=load(sys.argv[1]); im=cv2.imread(sys.argv[2]); cv2.imwrite(sys.argv[3],apply(im,L,n,float(sys.argv[4]) if len(sys.argv)>4 else 100))
