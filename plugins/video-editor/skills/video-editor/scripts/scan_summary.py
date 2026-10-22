# One line per clip: per-second act/jit (rounded) so taggers can pick steady action windows. Usage: python3 scan_summary.py SCAN_DIR > summary.txt
import json,glob,os,sys
for f in sorted(glob.glob(sys.argv[1]+"/*.json")):
    d=json.load(open(f)); c=os.path.basename(f)[:-5]; n=len(d['act']); F=d['fps']
    secs=[]
    for s in range(0,n,F):
        a=sum(d['act'][s:s+F])/len(d['act'][s:s+F]); w=d['jit'][s:s+F]; j=(sum(x*x for x in w)/len(w))**0.5; sh=sum(d['sharp'][s:s+F])/len(d['sharp'][s:s+F])
        secs.append(f"{s//F}:{a:.0f}/{j:.1f}/{sh:.0f}")
    print(f"{c} dur {d['dur']:.1f}s  [sec:act/rmsjit/sharp]  "+" ".join(secs))
