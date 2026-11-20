#!/usr/bin/env python3
"""Arregla las imágenes del personaje: quita el jockey (pone la cabeza de la imagen de referencia,
alineada) y reemplaza zonas de ropa con la de otra imagen de la misma pose.
Uso: python3 arreglar_personaje.py carpeta_original carpeta_final"""
import cv2, numpy as np, sys, os, glob

def align(src, dst, roi):
    """Alinea src a dst (afín) usando la zona roi=(x0,y0,x1,y1) de dst."""
    x0, y0, x1, y1 = roi
    g1 = cv2.cvtColor(dst, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g2 = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mask = np.zeros(g1.shape, np.uint8); mask[y0:y1, x0:x1] = 255
    warp = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6)
    try:
        _, warp = cv2.findTransformECC(g1, g2, warp, cv2.MOTION_AFFINE, crit, mask, 5)
    except cv2.error:
        pass
    return cv2.warpAffine(src, warp, (dst.shape[1], dst.shape[0]), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)

def blend(dst, src, mask, feather):
    a = cv2.GaussianBlur(mask.astype(np.float32) / 255, (0, 0), feather)[..., None]
    return (dst * (1 - a) + src * a).astype(np.uint8)

def head_mask(shape):
    m = np.zeros(shape[:2], np.uint8)
    cv2.ellipse(m, (368, 148), (84, 74), 0, 0, 360, 255, -1)     # gorra / pelo
    cv2.ellipse(m, (367, 205), (52, 50), 0, 0, 360, 255, -1)     # cara hasta el mentón
    return m

if __name__ == '__main__':
    src_dir, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src_dir, '*.jpg')))
    ref = cv2.imread(files[0])                                   # 1_camcorder: sin jockey
    for f in files:
        img = cv2.imread(f); name = os.path.basename(f)
        if f != files[0]:
            head = align(ref, img, (325, 178, 415, 258))           # alinea por la cara (bajo la visera)
            img = blend(img, head, head_mask(img.shape), 7)
        if 'buddha' in name:                                        # quita el short sobrepuesto
            legs = align(ref, img, (150, 900, 620, 1150))           # alinea por las piernas
            m = np.zeros(img.shape[:2], np.uint8)
            cv2.rectangle(m, (150, 652), (600, 905), 255, -1)
            img = blend(img, legs, m, 9)
        cv2.imwrite(os.path.join(out_dir, name), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print('ok', name)
