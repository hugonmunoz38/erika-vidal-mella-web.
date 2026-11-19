"""Quita el fondo de las fotos de producto y recorta al contenido.

Uso: python3 recortar_productos.py '{"origen.jpg": "destino.png", ...}' [--plano]

Por defecto usa rembg (IA local, modelo isnet-general-use), que funciona bien también con
productos blancos o claros. Con --plano usa el método simple: flood-fill del fondo claro
desde los bordes (no requiere rembg, pero se come las partes blancas del producto).
"""
import sys, json
from PIL import Image, ImageFilter
from collections import deque

def remove_bg_plano(im):
    im = im.convert('RGBA'); w, h = im.size; px = im.load()
    if im.getextrema()[3][0] < 10:          # ya tiene transparencia
        return im
    seen = bytearray(w * h); q = deque()
    for x in range(w):
        q.append((x, 0)); q.append((x, h - 1))
    for y in range(h):
        q.append((0, y)); q.append((w - 1, y))
    mask = Image.new('L', (w, h), 255); mp = mask.load()
    while q:
        x, y = q.popleft(); i = y * w + x
        if seen[i]: continue
        seen[i] = 1
        c = px[x, y]
        if min(c[:3]) > 200 and max(c[:3]) - min(c[:3]) < 22:   # fondo = muy claro y poco saturado
            mp[x, y] = 0
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]: q.append((nx, ny))
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    im.putalpha(mask)
    return im

_session = None
def remove_bg_ia(im):
    global _session
    im = im.convert('RGBA')
    if im.getextrema()[3][0] < 10:          # ya tiene transparencia
        return im
    from rembg import remove, new_session
    if _session is None:
        _session = new_session('isnet-general-use')
    return remove(im.convert('RGB'), session=_session, post_process_mask=True)

if __name__ == '__main__':
    plano = '--plano' in sys.argv
    for src, dst in json.loads(sys.argv[1]).items():
        im = (remove_bg_plano if plano else remove_bg_ia)(Image.open(src))
        bb = im.getchannel('A').point(lambda a: 255 if a > 20 else 0).getbbox()
        im = im.crop(bb)
        im.thumbnail((700, 700), Image.LANCZOS)
        im.save(dst); print(dst, im.size)
