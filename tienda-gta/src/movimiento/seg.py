"""Segmentación de ropa (u2net_cloth_seg de rembg) como mapa de clases."""
import cv2, numpy as np
from rembg import new_session
from PIL import Image
_s = None
def labels(bgr):
    """0 fondo, 1 parte de arriba, 2 parte de abajo, 3 prenda completa"""
    global _s
    if _s is None: _s = new_session('u2net_cloth_seg')
    img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    out = _s.inner_session.run(None, _s.normalize(img, (0.485, 0.456, 0.406), (0.229, 0.224, 0.225), (768, 768)))
    logits = out[0][0]                              # (4, 768, 768)
    up = np.stack([cv2.resize(l, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_LINEAR) for l in logits])
    return np.argmax(up, 0).astype(np.uint8)
