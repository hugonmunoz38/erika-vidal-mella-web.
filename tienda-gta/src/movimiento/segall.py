import cv2, numpy as np, glob, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import seg, comp
S = sys.argv[1]
fs = sorted(glob.glob(S + '/f/*.jpg'))
for i, f in enumerate(fs):
    o = f'{S}/seg/{i:04d}.png'
    if os.path.exists(o): continue
    V = cv2.imread(f)[:, comp.X0:comp.X1]
    L = seg.labels(V); p = comp.person(V)
    cv2.imwrite(o, (L + 10 * p.astype(np.uint8)).astype(np.uint8))
    if i % 20 == 0: print(i, flush=True)
print('fin')
