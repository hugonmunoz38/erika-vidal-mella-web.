"""Composición: cambia la ropa del personaje del clip por la de cada foto de outfit, siguiendo su movimiento."""
import cv2, numpy as np, glob, os, json
import seg
from rembg import remove, new_session
X0, X1 = 700, 1860
import os
EST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tiendas', 'archif', 'personaje', 'estados')
_h = None
def person(bgr):
    global _h
    if _h is None: _h = new_session('u2net_human_seg')
    from PIL import Image
    return np.array(remove(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)), session=_h, only_mask=True)) > 128

def match_lut(src, ref, mask):
    """LUT por canal que lleva el histograma de src al de ref (en la zona mask)."""
    luts = []
    for c in range(3):
        hs = np.bincount(src[..., c][mask], minlength=256).cumsum().astype(np.float64); hs /= hs[-1]
        hr = np.bincount(ref[..., c][mask], minlength=256).cumsum().astype(np.float64); hr /= hr[-1]
        luts.append(np.interp(hs, hr, np.arange(256)).clip(0, 255).astype(np.uint8))
    return luts
def apply_lut(img, luts):
    return np.dstack([cv2.LUT(img[..., c], luts[c]) for c in range(3)])

class Fotos:
    def __init__(self, S, V0):
        A = np.load(S + '/A.npy').copy(); A[0, 2] -= X0
        self.h, self.w = V0.shape[:2]
        self.A = A
        P1 = cv2.imread(EST + '/s1.jpg')
        self.valid = cv2.warpAffine(np.ones(P1.shape[:2], np.uint8), A, (self.w, self.h)) > 0
        self.valid = cv2.erode(self.valid.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        P1a = cv2.warpAffine(P1, A, (self.w, self.h), flags=cv2.INTER_CUBIC)
        self.luts = match_lut(P1a, V0, self.valid)
        self.cache = {}
    def get(self, k):
        if k not in self.cache:
            P = cv2.imread(f'{EST}/{k}.jpg')
            L = seg.labels(P)
            per = person(P)
            pa = apply_lut(cv2.warpAffine(P, self.A, (self.w, self.h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), self.luts)
            La = cv2.warpAffine(L, self.A, (self.w, self.h), flags=cv2.INTER_NEAREST)
            pera = cv2.warpAffine(per.astype(np.uint8), self.A, (self.w, self.h), flags=cv2.INTER_NEAREST) > 0
            top, low, shoes, skin = partes(pa, La, pera)
            yy, xx = np.mgrid[0:self.h, 0:self.w]
            legs = pera & ~top & (yy > 640) & ~(skin & (yy < 850))
            legs = cv2.GaussianBlur(legs.astype(np.float32), (0, 0), 1.2)
            wl = 1 / (1 + np.exp((xx - 563) / 8.0))
            self.cache[k] = (pa, top, low, shoes, (legs * wl).astype(np.float32), (legs * (1 - wl)).astype(np.float32))
        return self.cache[k]

def fill_holes(m):
    m = m.astype(np.uint8)
    h, w = m.shape
    ff = m.copy(); msk = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, msk, (0, 0), 1)
    return (m > 0) | (ff == 0)

def skin_color(bgr):
    """piel con histéresis: semillas fuertes + zona débil conectada"""
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb).astype(np.int16)
    Y, Cr, Cb = ycc[..., 0], ycc[..., 1], ycc[..., 2]
    strong = (Cr > 147) & (Cr < 185) & (Cb < 114) & (Y > 55)
    weak = (Cr > 140) & (Cr < 185) & (Cb < 119) & (Y > 45)
    n, lab = cv2.connectedComponents(weak.astype(np.uint8))
    keep = np.zeros(n, bool); keep[np.unique(lab[strong])] = True; keep[0] = False
    return keep[lab]

def partes(img, L, per):
    """top, low, shoes, skin para una imagen (cuadro o foto)"""
    h, w = img.shape[:2]
    yy = np.arange(h)[:, None]
    low = fill_holes(L == 2)
    skin = per & skin_color(img) & ~low
    skin = cv2.morphologyEx(skin.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    shoes = per & ~low & (L != 1) & (yy > 1000)
    top = fill_holes(L == 1)
    near = cv2.dilate(top.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    top = (top | (per & near & ~skin & ~low & ~shoes & (yy > 400))) & ~skin
    top = fill_holes(top) & ~skin
    return top, low & ~top, shoes, skin

def feather(m, s=2.0):
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), s)[..., None]

CAMBIOS = {   # respecto del video (s1): cambia la parte de arriba / abajo ('pies' = solo zapatos, 'todo')
    's2': (1, None), 's3': (1, 'pies'), 's4': (1, 'todo'), 's5': (1, 'todo'),
    's6': (1, 'pies'), 's7': (1, 'pies'), 's8': (1, 'pies'), 's9': (1, 'pies')}
def cargar_partes(S, t, Vt):
    import os
    p = f'{S}/seg/{t:04d}.png'
    if os.path.exists(p):
        m = cv2.imread(p, cv2.IMREAD_GRAYSCALE); L = m % 10; per = m >= 10
    else:
        import seg; L = seg.labels(Vt); per = person(Vt)
    return partes(Vt, L, per) + (per,)

def componer(Vt, pt, M, foto, top_change, low_mode, legH=None, plate=None):
    top_t, low_t, shoes_t, skin_t, per_t = pt
    pa, ftop, flow_, fshoes, legL, legR = foto
    mx, my = M[0].astype(np.float32), M[1].astype(np.float32)
    Wk = cv2.remap(pa, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    rm = lambda m: cv2.remap(m.astype(np.uint8), mx, my, cv2.INTER_NEAREST) > 0
    h, w = Vt.shape[:2]
    R = Vt.astype(np.float32)
    if low_mode:
        Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
        maps = []
        for H in legH:
            d = H[2, 0] * X + H[2, 1] * Y + H[2, 2]
            maps.append((((H[0, 0] * X + H[0, 1] * Y + H[0, 2]) / d).astype(np.float32), ((H[1, 0] * X + H[1, 1] * Y + H[1, 2]) / d).astype(np.float32)))
        if low_mode == 'todo':
            ramp = np.ones((h, w, 1), np.float32)
        else:
            # solo bajo el ruedo del jeans del video (en coordenadas del cuadro 0, por pierna)
            wl = 1 / (1 + np.exp(((maps[0][0] + maps[1][0]) / 2 - 563) / 10))
            r = wl * np.clip((maps[0][1] - 925) / 70, 0, 1) + (1 - wl) * np.clip((maps[1][1] - 925) / 70, 0, 1)
            ramp = r[..., None]
        # parte de abajo nueva = fondo limpio + cada pierna de la foto movida con su propia transformación
        NL = plate.astype(np.float32); LA = np.zeros((h, w, 1), np.float32)
        for (sx, sy), lm in zip(maps, (legL, legR)):
            col = cv2.remap(pa, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
            al = cv2.remap(lm, sx, sy, cv2.INTER_LINEAR)[..., None]
            NL = NL * (1 - al) + col * al; LA = np.maximum(LA, al)
        # se aplica donde estaba la parte de abajo del video o donde queda la nueva
        cl = cv2.dilate((low_t | shoes_t).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
        a = np.maximum(cv2.GaussianBlur(cl, (0, 0), 2.5)[..., None], LA) * ramp
        R = R * (1 - a) + NL * a
    if top_change:
        # se agranda un poco la zona para tapar el borde oscuro de la prenda original
        grow = cv2.dilate(top_t.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
        reg = grow | (rm(ftop) & per_t & ~skin_t)
        a = feather(reg & ~skin_t); R = R * (1 - a) + Wk * a
    elif low_mode:
        a = feather(top_t); R = R * (1 - a) + Vt * a
    a = feather(skin_t, 1.2)
    R = R * (1 - a) + Vt * a
    return np.clip(R, 0, 255).astype(np.uint8)
