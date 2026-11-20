"""Pista de fondo del editor a partir del clip con movimiento: en cada instante, el outfit de la fila
seleccionada (cuadros compuestos) y un recorrido del clip con idas y vueltas suaves.
Uso: python3 fondo_mov.py <dir_cuadros_originales> <dir_compuestos> <editor.json> <9x16|4x5> <salida.mp4>"""
import cv2, numpy as np, glob, json, subprocess, sys
FR, CO, CFG, FMT, OUT = sys.argv[1:6]
FPS, SRC_FPS, X0 = 30, 24, 700
GRADE6 = ('eq=contrast=1.1:saturation=1.22:gamma=0.97,'
          'colorbalance=rs=-0.06:gs=-0.01:bs=0.07:rm=0.03:gm=-0.02:bm=0.03:rh=0.09:gh=0.02:bh=-0.05,'
          'split[ga][gb];[gb]gblur=sigma=14[gbb];[ga][gbb]blend=all_mode=screen:all_opacity=0.2,vignette=angle=PI/4.5')
cfg = json.load(open(CFG)); rows, step, dur = cfg['rows'], cfg['timeline']['step'], cfg['timeline']['dur']
fs = sorted(glob.glob(FR + '/*.jpg')); N = len(fs)

def tiempo_fuente(n, f0, lo, hi, tr=0.6):
    """tiempo del clip (s) para cada cuadro de salida: parte en f0 hacia atrás a velocidad 1x y rebota
    suavemente (giro de tr segundos) entre lo y hi"""
    dt = 1 / FPS / 20; steps = int(n * 20) + 1
    f = np.empty(steps); f[0] = f0; v = -1.0; target = -1.0; acc = 1 / tr * 2      # aceleración para girar en tr s
    for i in range(1, steps):
        if v < 0 and f[i - 1] <= lo + tr / 4: target = 1.0
        if v > 0 and f[i - 1] >= hi - tr / 4: target = -1.0
        v = np.clip(v + np.sign(target - v) * acc * dt, -1, 1) if v != target else v
        f[i] = f[i - 1] + v * dt
    return f[::20][:n]

HOLD = cfg['timeline'].get('hold', 0)
def estado(e):
    k = min(len(rows) - 1, int(max(0, e - HOLD) // step))
    while not rows[k].get('state'): k -= 1
    return rows[k]['state'].split('/')[-1].split('.')[0]

cache = {}
def cuadro(k, t):
    key = (k, t)
    if key not in cache:
        full = cv2.imread(fs[t])
        if k != 's1':
            c = cv2.imread(f'{CO}/{k}/{t:04d}.jpg'); full[:, X0:X0 + c.shape[1]] = c
        if len(cache) > 40: cache.pop(next(iter(cache)))
        cache[key] = full.astype(np.float32)
    return cache[key]

if FMT == '9x16': cx0, cw, W, H = 787, 810, 1080, 1920
else: cx0, cw, W, H = 566, 1152, 1080, 1350
n = int(round(dur * FPS)); ts = tiempo_fuente(n, (N - 1) / SRC_FPS, 0.1, 2.35)
assert ts.min() >= 0 and ts.max() * SRC_FPS <= N - 1, (ts.min(), ts.max())
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                      '-filter_complex', f'[0:v]{GRADE6}[v]', '-map', '[v]', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', OUT], stdin=subprocess.PIPE)
log = []
for i in range(n):
    e = i / FPS; k = estado(e); fsrc = ts[i] * SRC_FPS
    img = cuadro(k, int(round(fsrc)))          # cuadro entero (mezclar dos cuadros duplicaba la figura)
    img = img[:, cx0:cx0 + cw]
    img = cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC if W > cw else cv2.INTER_AREA)
    p.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    if i % 30 == 0: log.append(f'{e:.1f}s {k} f={fsrc:.1f}')
p.stdin.close(); p.wait()
print(' | '.join(log))
