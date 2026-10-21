#!/usr/bin/env python3
# Summarize a cam_scan.py csv into flagged seconds (MOVE / SOFT) on a shared clock. vpy cam_flags.py scan.csv clock_offset_s
import sys, numpy as np
d=np.loadtxt(sys.argv[1],delimiter=','); o=float(sys.argv[2])
med=np.median(d[:,2]); out=[]
for s in range(0,int(d[-1,0])):
    m=d[(d[:,0]>=s)&(d[:,0]<s+1)]
    mx=m[:,1].max(); sh=np.median(m[:,2])
    flag=('MOVE' if mx>3 else 'move' if mx>1.2 else '')+(' SOFT' if sh<0.35*med else '')
    if flag: out.append(f'{int((s+o)//60)}:{(s+o)%60:04.1f} m{mx:.1f} s{sh:.0f} {flag}')
print('median sharp',round(med)); print('\n'.join(out))
