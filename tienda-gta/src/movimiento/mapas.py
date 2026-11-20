"""Refina el mapa denso (cuadro t -> cuadro 0) en: cámara global, torso rígido (homografía suavizada en el
tiempo), piernas suaves y resto denso suavizado. Evita que el 'hervor' del video deforme los estampados."""
import cv2, numpy as np
TORSO = (450, 300, 690, 655)          # caja del torso en el cuadro 0 (x0, y0, x1, y1), sin brazos
CINTURA = 655
SPLIT = 563                           # x que separa pierna izquierda / derecha en el cuadro 0
PIERNAS = ((350, 660, SPLIT, 1330), (SPLIT, 660, 780, 1330))

def hpts(H, X, Y):
    d = H[2, 0] * X + H[2, 1] * Y + H[2, 2]
    return (H[0, 0] * X + H[0, 1] * Y + H[0, 2]) / d, (H[1, 0] * X + H[1, 1] * Y + H[1, 2]) / d

def fit_h(D, mask, step=6, thr=2.5):
    ys, xs = np.where(mask[::step, ::step]); ys *= step; xs *= step
    if len(xs) < 30: return None
    src = np.float32(np.stack([xs, ys], 1)); dst = np.float32(np.stack([D[0][ys, xs], D[1][ys, xs]], 1))
    H, inl = cv2.findHomography(src, dst, cv2.RANSAC, thr, maxIters=3000)
    return H

def masked_blur(F, m, s):
    m = m.astype(np.float32)
    num = cv2.GaussianBlur(F * m, (0, 0), s); den = cv2.GaussianBlur(m, (0, 0), s)
    return num / np.maximum(den, 1e-4), den

def smooth_h(Hs, h, w, sigma=2.0, box=TORSO):
    """suaviza homografías en el tiempo vía trayectorias de 4 esquinas"""
    c = np.float32([[box[0], box[1]], [box[2], box[1]], [box[2], box[3]], [box[0], box[3]]])
    tr = []
    for H in Hs:
        Hi = np.linalg.inv(H)                                   # 0 -> t
        tr.append(cv2.perspectiveTransform(c[None], Hi)[0])
    tr = np.array(tr)                                          # (T, 4, 2)
    k = int(3 * sigma); g = np.exp(-np.arange(-k, k + 1) ** 2 / (2 * sigma ** 2)); g /= g.sum()
    pad = np.pad(tr, ((k, k), (0, 0), (0, 0)), mode='edge')
    sm = np.array([(pad[i:i + 2 * k + 1] * g[:, None, None]).sum(0) for i in range(len(tr))])
    return [cv2.getPerspectiveTransform(np.float32(sm[i]), c) for i in range(len(tr))]   # t -> 0

def piernas_h(D, low_t, shoes_t):
    """afín por pierna (t -> 0), como 3x3"""
    D = D.astype(np.float32); out = []
    for (x0, y0, x1, y1) in PIERNAS:
        inb = (D[0] > x0 + 8) & (D[0] < x1 - 8) & (D[1] > y0 + 120) & (D[1] < y1)
        m = inb & (low_t | shoes_t)
        ys, xs = np.where(m[::4, ::4]); ys *= 4; xs *= 4
        if len(xs) < 30: out.append(None); continue
        A, _ = cv2.estimateAffine2D(np.float32(np.stack([xs, ys], 1)), np.float32(np.stack([D[0][ys, xs], D[1][ys, xs]], 1)),
                                    ransacReprojThreshold=4.0, maxIters=3000)
        out.append(None if A is None else np.vstack([A, [0, 0, 1]]))
    return out

def refinar(D, top_t, low_t, shoes_t, per_t, skin_t, Ht, HL=None, HR=None):
    h, w = D.shape[1:]
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    D = D.astype(np.float32)
    # torso rígido
    tx, ty = hpts(Ht, X, Y)
    bx = np.clip(np.minimum(tx - TORSO[0], TORSO[2] - tx) / 30, 0, 1) * np.clip(np.minimum(ty - TORSO[1], TORSO[3] - ty) / 30 + .5, 0, 1)
    dist = np.hypot(D[0] - tx, D[1] - ty)
    cons = np.clip(1 - (dist - 10) / 12, 0, 1)
    wT = bx * cons * (top_t | skin_t).astype(np.float32)
    wT = cv2.GaussianBlur(wT, (0, 0), 3)
    # piernas: residuo suavizado fuerte
    R = D - np.stack([X, Y])
    lx, ly = hpts(HL, X, Y); rx, ry = hpts(HR, X, Y)
    # peso izquierda/derecha según dónde cae el punto en el cuadro 0 (transición suave entre piernas)
    wl = 1 / (1 + np.exp(((lx + rx) / 2 - SPLIT) / 12))
    Lx, Ly = wl * lx + (1 - wl) * rx, wl * ly + (1 - wl) * ry
    dl = np.hypot(D[0] - Lx, D[1] - Ly)
    wL = np.clip((D[1] - (CINTURA - 30)) / 40, 0, 1) * np.clip(1 - (dl - 10) / 12, 0, 1)
    wL = cv2.GaussianBlur(wL, (0, 0), 3)
    # resto: denso suavizado dentro de la persona
    pm = per_t | cv2.dilate(per_t.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    Rs = np.stack([masked_blur(R[i], pm, 4)[0] for i in range(2)])
    Sx, Sy = X + Rs[0], Y + Rs[1]
    mx = wT * tx + (1 - wT) * (wL * Lx + (1 - wL) * Sx)
    my = wT * ty + (1 - wT) * (wL * Ly + (1 - wL) * Sy)
    return np.stack([mx, my]), wT, wL

def torso_h(D, top_t, skin_t):
    h, w = D.shape[1:]
    D = D.astype(np.float32)
    inb = (D[0] > TORSO[0] + 15) & (D[0] < TORSO[2] - 15) & (D[1] > TORSO[1] + 40) & (D[1] < TORSO[3] - 60)
    return fit_h(D, inb & top_t & ~skin_t, step=5, thr=3.0)
