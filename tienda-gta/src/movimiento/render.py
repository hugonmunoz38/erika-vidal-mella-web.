"""Genera los cuadros compuestos de cada outfit (s2..s9) para todo el clip.
Uso: python3 render.py <dir_trabajo> <dir_salida> [cuadros,separados,por,coma]"""
import cv2, numpy as np, glob, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comp, mapas
S, OUT = sys.argv[1], sys.argv[2]
solo = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None
fs = sorted(glob.glob(S + '/f/*.jpg'))
maps = np.load(S + '/maps.npy', mmap_mode='r')
V = lambda t: cv2.imread(fs[t])[:, comp.X0:comp.X1]
F = comp.Fotos(S, V(0))
T = len(fs)
# paso 1: homografía del torso por cuadro (suavizada en el tiempo)
hp = S + '/homos.npy'
if os.path.exists(hp):
    Hs, HLs, HRs = [list(a) for a in np.load(hp)]
else:
    Hs, HLs, HRs = [], [], []; last = [np.eye(3)] * 3
    for t in range(T):
        pt = comp.cargar_partes(S, t, V(t))
        hs = [mapas.torso_h(maps[t], pt[0], pt[3])] + mapas.piernas_h(maps[t], pt[1], pt[2])
        hs = [h if h is not None else l for h, l in zip(hs, last)]; last = hs
        Hs.append(hs[0]); HLs.append(hs[1]); HRs.append(hs[2])
    Hs = mapas.smooth_h(Hs, 1440, 1160, sigma=2.0)
    HLs = mapas.smooth_h(HLs, 1440, 1160, sigma=2.5, box=mapas.PIERNAS[0])
    HRs = mapas.smooth_h(HRs, 1440, 1160, sigma=2.5, box=mapas.PIERNAS[1])
    np.save(hp, np.array([Hs, HLs, HRs]))
# fondo limpio (sin persona) para la zona de piernas: mediana de lo que se ve detrás en todo el clip
pp = S + '/plate.png'
if os.path.exists(pp):
    plate = cv2.imread(pp)
else:
    acc = []; msk = []
    for t in range(0, T, 3):
        m = cv2.imread(f'{S}/seg/{t:04d}.png', cv2.IMREAD_GRAYSCALE) >= 10
        m = cv2.dilate(m.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
        acc.append(V(t)); msk.append(m)
    acc = np.array(acc).astype(np.float32); msk = np.array(msk)
    acc[msk] = np.nan
    plate = np.nanmedian(acc, 0)
    hole = np.isnan(plate[..., 0])
    plate = np.nan_to_num(plate).astype(np.uint8)
    plate = cv2.inpaint(plate, hole.astype(np.uint8), 9, cv2.INPAINT_TELEA)
    cv2.imwrite(pp, plate)
for k in comp.CAMBIOS: os.makedirs(f'{OUT}/{k}', exist_ok=True)
for t in (solo or range(T)):
    Vt = V(t); pt = comp.cargar_partes(S, t, Vt)
    M, wT, wL = mapas.refinar(maps[t], pt[0], pt[1], pt[2], pt[4], pt[3], Hs[t], HLs[t], HRs[t])
    for k, (tc, lm) in comp.CAMBIOS.items():
        R = comp.componer(Vt, pt, M, F.get(k), tc, lm, (HLs[t], HRs[t]), plate)
        cv2.imwrite(f'{OUT}/{k}/{t:04d}.jpg', R, [cv2.IMWRITE_JPEG_QUALITY, 94])
    if solo and len(solo) <= 5: cv2.imwrite(f'{OUT}/w_{t:04d}.jpg', np.dstack([wT * 255, wL * 255, np.zeros_like(wT)]).astype(np.uint8))
    if t % 10 == 0: print(t, flush=True)
print('fin')
