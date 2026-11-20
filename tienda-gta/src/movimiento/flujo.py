"""Mapa denso de cada cuadro del clip hacia el cuadro 0 (flujo óptico encadenado + refinamiento contra el 0)."""
import cv2, numpy as np, glob, sys, time
S = sys.argv[1]; X0, X1 = 700, 1860
fs = sorted(glob.glob(S + '/f/*.jpg'))
def prep(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    g = np.sqrt(g)                                       # realza detalle en la ropa negra
    return (g * 255).astype(np.uint8)
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
dis.setFinestScale(0); dis.setVariationalRefinementIterations(10)
V = [cv2.imread(f)[:, X0:X1] for f in fs]
h, w = V[0].shape[:2]
Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
mx, my = X.copy(), Y.copy()                              # mapa t -> 0
g0 = prep(V[0]); prev = g0
maps = [np.stack([mx, my]).astype(np.float16)]
t0 = time.time()
for t in range(1, len(V)):
    g = prep(V[t])
    f = dis.calc(g, prev, None)                          # V_t(x) ~ V_{t-1}(x+f)
    mx2 = cv2.remap(mx, X + f[..., 0], Y + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    my2 = cv2.remap(my, X + f[..., 0], Y + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    # refinamiento contra el cuadro 0 para que no se acumule deriva
    Wg = cv2.remap(g0, mx2, my2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    r = dis.calc(g, Wg, None)
    mx = cv2.remap(mx2, X + r[..., 0], Y + r[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    my = cv2.remap(my2, X + r[..., 0], Y + r[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    prev = g
    maps.append(np.stack([mx, my]).astype(np.float16))
    if t % 20 == 0:
        W0 = cv2.remap(V[0], mx, my, cv2.INTER_LINEAR)
        print(t, 'err', np.abs(W0.astype(int) - V[t].astype(int)).mean().round(2), 'time', round(time.time() - t0, 1), flush=True)
np.save(S + '/maps.npy', np.stack(maps))
print('ok', h, w)
