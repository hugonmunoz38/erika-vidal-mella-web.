#!/usr/bin/env python3
"""Combina prendas entre fotos del mismo personaje en la misma pose: parte de arriba de una foto
(cabeza, polerón/chaqueta) sobre la parte de abajo de otra (pantalón y zapatos), o los pies de otra.

Uso: python3 combinar_prendas.py <carpeta_fotos> <carpeta_salida> <estados.json>
estados.json = [ {"out": "s2.jpg", "top": "2_skulls.jpg", "low": "1_camcorder.jpg"}, {"out": "s1.jpg", "copy": "1_camcorder.jpg"}, ... ]
"""
import cv2, json, numpy as np, os, sys

def hem_curve(img, y0=600, y1=720, x0=150, x1=620):
    """Borde inferior de la parte de arriba por columna = donde empieza el pantalón azul (bermuda)
    de esa misma foto. Incluye el ribete del polerón y las manos en los bolsillos."""
    b, g, r = [img[..., i].astype(int) for i in range(3)]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(int)
    blue = (b > r + 18) & (hsv[..., 1] > 45)
    w = img.shape[1]
    curve = np.full(w, -1)
    for x in range(x0, x1):
        col = blue[y0:y1, x]
        # primer tramo azul de al menos 6 px seguidos
        run = 0
        for i, v in enumerate(col):
            run = run + 1 if v else 0
            if run >= 6:
                curve[x] = y0 + i - 5
                break
    valid = curve > 0
    default = int(np.median(curve[valid])) if valid.any() else 640
    curve[~valid] = default
    pad = np.pad(curve, 6, mode='edge')
    curve = np.array([np.median(pad[i:i + 13]) for i in range(len(curve))])   # filtro mediano de 13 px
    return curve.astype(int), default

def top_mask(img, kind, h, w):
    if kind == 'gris':
        curve, d = hem_curve(img)
        curve = cv2.GaussianBlur(curve.astype(np.float32).reshape(1, -1), (1, 9), 0).ravel()
    else:
        curve = np.full(w, kind if isinstance(kind, int) else 641, np.float32)
    yy = np.arange(h)[:, None]
    m = (yy < curve[None, :]).astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), 1.5)

if __name__ == '__main__':
    src, out, spec = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
    os.makedirs(out, exist_ok=True)
    load = lambda n: cv2.imread(os.path.join(src, n))
    for s in spec:
        if 'copy' in s:
            cv2.imwrite(os.path.join(out, s['out']), load(s['copy']), [cv2.IMWRITE_JPEG_QUALITY, 95]); print('copia', s['out']); continue
        A, B = load(s['top']), load(s['low'])
        h, w = A.shape[:2]
        a = top_mask(A, s.get('kind', 'gris'), h, w)[..., None]
        res = (A * a + B * (1 - a)).astype(np.uint8)
        cv2.imwrite(os.path.join(out, s['out']), res, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print('combinado', s['out'], '=', s['top'], '+', s['low'])
