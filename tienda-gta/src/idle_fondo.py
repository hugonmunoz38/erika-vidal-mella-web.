#!/usr/bin/env python3
"""Anima fotos fijas del personaje con un "idle" sutil (respiración, balanceo de peso, cabeza)
deformando solo al personaje y su entorno inmediato, con los pies fijos. Arma la pista de fondo del
editor de outfits: en cada instante usa la foto del estado vigente y una fase de movimiento continua.

Uso: python3 idle_fondo.py <editor.json> <9x16|4x5> <salida.mp4> [fps]
"""
import cv2, json, numpy as np, os, subprocess, sys

def person_mask(img, cache):
    if os.path.exists(cache):
        return cv2.imread(cache, cv2.IMREAD_GRAYSCALE)
    from rembg import remove, new_session
    m = np.array(remove(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), session=new_session('u2net_human_seg'), only_mask=True))
    cv2.imwrite(cache, m)
    return m

def idle_field(mask, t, h, w):
    """Campo de desplazamiento (dx, dy) en píxeles para el tiempo t."""
    ys, xs = np.where(mask > 128)
    y_head, y_feet = ys.min(), ys.max()
    cx = float(np.median(xs))
    # peso: personaje + un margen suave alrededor (para que no queden bordes)
    wgt = cv2.GaussianBlur((mask > 128).astype(np.float32), (0, 0), 18)
    wgt = np.clip(wgt * 1.6, 0, 1)
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    up = np.clip((y_feet - Y) / max(1, y_feet - y_head), 0, 1)             # 0 en los pies, 1 en la cabeza
    sway = np.sin(2 * np.pi * t / 3.4) * 4.0 * up ** 1.4                   # traspaso de peso
    breath = 0.5 - 0.5 * np.cos(2 * np.pi * t / 2.7)                        # 0..1
    chest = np.exp(-((Y - (y_head + 0.28 * (y_feet - y_head))) / (0.16 * (y_feet - y_head))) ** 2)
    dx = sway + (X - cx) * 0.010 * breath * chest
    dy = -2.2 * breath * up ** 1.2 + 1.2 * np.sin(2 * np.pi * t / 1.9 + 1.0) * np.clip((up - .82) / .18, 0, 1)
    return dx * wgt, dy * wgt

def warp(img, mask, t):
    h, w = img.shape[:2]
    dx, dy = idle_field(mask, t, h, w)
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    return cv2.remap(img, (X - dx).astype(np.float32), (Y - dy).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

if __name__ == '__main__':
    cfg_path, fmt, out = sys.argv[1], sys.argv[2], sys.argv[3]
    fps = int(sys.argv[4]) if len(sys.argv) > 4 else 30
    cfg = json.load(open(cfg_path)); base = os.path.dirname(cfg_path)
    rows, step, dur = cfg['rows'], cfg['timeline']['step'], cfg['timeline']['dur']
    states = {}
    for r in rows:
        if r.get('state') and r['state'] not in states:
            p = os.path.join(base, r['state']); img = cv2.imread(p)
            states[r['state']] = (img, person_mask(img, p + '.mask.png'))
    W, H = 1080, (1920 if fmt == '9x16' else 1350)
    iw, ih = cfg['photoSize']
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                           '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    n = int(round(dur * fps))
    for f in range(n):
        t = f / fps
        k = min(len(rows) - 1, int(t // step))
        while not rows[k].get('state'):
            k -= 1
        img, m = states[rows[k]['state']]
        fr = warp(img, m, t)
        z = 1 + .02 * t / dur                                              # empuje lento de cámara
        if fmt == '9x16':
            sc = max(W / iw, H / ih) * z
            fr2 = cv2.resize(fr, (int(iw * sc), int(ih * sc)), interpolation=cv2.INTER_LINEAR)
            y0 = (fr2.shape[0] - H) // 2; x0 = (fr2.shape[1] - W) // 2
            frame = fr2[y0:y0 + H, x0:x0 + W]
        else:
            ph = cv2.resize(fr, (int(iw * H / ih * z), int(H * z)), interpolation=cv2.INTER_LINEAR)
            ph = ph[(ph.shape[0] - H) // 2:(ph.shape[0] - H) // 2 + H]
            bg = cv2.resize(fr, (W, int(ih * W / iw)))[:H] if ih * W / iw >= H else cv2.resize(fr, (W, H))
            bg = cv2.GaussianBlur(bg, (0, 0), 24); bg = (bg * .45).astype(np.uint8)
            frame = bg.copy(); x0 = W - ph.shape[1] - 10
            frame[:, x0:x0 + ph.shape[1]] = ph[:, :min(ph.shape[1], W - x0)]
        ff.stdin.write(np.ascontiguousarray(frame).tobytes())
    ff.stdin.close(); ff.wait()
    print('listo', out)
