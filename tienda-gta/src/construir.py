#!/usr/bin/env python3
"""Arma las piezas "tienda en modo GTA" para una tienda.

Uso:  python3 src/construir.py <tienda>        (beta | vans | bold)

Lee tiendas/<tienda>/config.json. Si existen los clips IA (video.walk y video.tryon) arma
el video completo (~19 s):
  1) caminata hacia la tienda + HUD
  2) rueda de productos: el cursor da una vuelta y frena en el producto destacado
  3) fundido -> probador: menú de tienda, compra y descuento de dinero
  4) tarjeta final con la web y el Instagram de la tienda
Si todavía no hay clips IA, arma una VISTA PREVIA (rueda, menú y tarjeta final) sobre
la imagen video.previewBg, para revisar productos y textos antes de generar los clips.
Salidas en tiendas/<tienda>/out/.
"""
import json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
STORE_ID = sys.argv[1] if len(sys.argv) > 1 else 'beta'
T = os.path.join(ROOT, 'tiendas', STORE_ID)
CFG = json.load(open(os.path.join(T, 'config.json')))
VID = CFG.get('video', {})
B, OUT = os.path.join(ROOT, 'build', STORE_ID), os.path.join(T, 'out')
os.makedirs(B, exist_ok=True); os.makedirs(OUT, exist_ok=True)
FPS = 30
P = STORE_ID  # prefijo de archivos de salida

# Corrección de color cálida/saturada estilo trailer (sombras levemente turquesa, luces cálidas)
GRADE = ('eq=contrast=1.06:saturation=1.12:gamma=0.98,'
         'colorbalance=rs=-0.03:gs=0.0:bs=0.04:rh=0.04:gh=0.01:bh=-0.03,'
         'vignette=angle=PI/5')
ENC = ['-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
TMP = ['-c:v', 'libx264', '-crf', '12', '-preset', 'medium', '-pix_fmt', 'yuv420p']
SILENT = ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100']
AUD = ['-c:a', 'aac', '-b:a', '128k', '-shortest']

def run(*cmd):
    subprocess.run(cmd, check=True)

def ff(*args):
    run('ffmpeg', '-v', 'error', '-y', *args)

def render(fmt, frames):
    job = os.path.join(B, f'job_{fmt}.json')
    json.dump({'store': STORE_ID, 'fmt': fmt, 'frames': frames}, open(job, 'w'))
    run('node', os.path.join(SRC, 'render.js'), job)

def seq(fmt, name):
    d = os.path.join(B, f'{name}_{fmt}')
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    return d

def tpath(rel):
    return os.path.join(T, rel) if rel else None

# --- 2) rueda: una vuelta completa y frena en el producto destacado -------------
N_ITEMS, SEL = len(CFG['items']), CFG['selected']
_order = list(range(N_ITEMS)) + list(range(SEL + 1))
_t, SEL_STEPS = 0.45, []
for j, idx in enumerate(_order):
    SEL_STEPS.append((round(_t, 3), idx))
    _t += 0.26 + 0.26 * (j / max(1, len(_order) - 1)) ** 2
LANDED = SEL_STEPS[-1][0]
WHEEL_DUR = round(LANDED + 1.75, 2)

def wheel_state(t, bg):
    sel, since = SEL_STEPS[0][1], t - SEL_STEPS[0][0]
    for ts, i in SEL_STEPS:
        if t >= ts:
            sel, since = i, t - ts
    landed = t >= LANDED + 0.25
    return {'mode': 'rueda', 'bg': bg, 'blur': min(1.0, t / 0.45),
            'open': max(0.0, min(1.0, (t - 0.05) / 0.40)),
            'sel': sel, 'pop': min(1.0, max(0.0, since) / 0.16), 'price': landed, 'buy': landed}

# --- 3) probador ----------------------------------------------------------------
OUTFIT = CFG['outfit']['items']
MONEY0, TOTAL = 9999900, sum(o['value'] for o in OUTFIT if o.get('buy', True))
STEP = 2.8 / len(OUTFIT)           # el menú recorre las prendas en ~2,8 s
BUY_AT = STEP * len(OUTFIT) + 0.3

def try_state(t):
    cur, eq = 0, 1
    for i in range(len(OUTFIT) + 1):
        if t >= i * STEP:
            cur, eq = i, min(i + 1, len(OUTFIT))
    k = min(1.0, max(0.0, (t - BUY_AT) / 0.8))
    pop = 0.0 if t < BUY_AT else (1.0 if t < BUY_AT + 1.4 else max(0.0, 1 - (t - BUY_AT - 1.4) / 0.4))
    return {'mode': 'probador', 'cursor': cur, 'equipped': eq, 'menu': 1,
            'money': MONEY0 - TOTAL * k, 'moneyPop': pop}

FINAL_DUR = 2.6
WALK, TRY = tpath(VID.get('walk')), tpath(VID.get('tryon'))
FULL = bool(WALK and TRY and os.path.exists(WALK) and os.path.exists(TRY))

def concat(parts, out):
    ins = sum((['-i', p] for p in parts), [])
    n = len(parts)
    fc = ''.join(f'[{i}:v]' for i in range(n)) + f'concat=n={n}:v=1:a=0[v]'
    ff(*ins, *SILENT, '-filter_complex', fc, '-map', '[v]', '-map', f'{n}:a', *ENC, *AUD, out)

for fmt, H in (('4x5', 1350), ('9x16', 1920)):
    fit = ('scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920' if fmt == '9x16'
           else 'scale=1080:1350:force_original_aspect_ratio=increase,crop=1080:1350')
    if not FULL:
        # ---------------- VISTA PREVIA (sin clips IA) ----------------
        bg = os.path.join(B, f'previewbg_{fmt}.png')
        ff('-i', tpath(VID['previewBg']), '-vf', f'{fit},{GRADE}', '-frames:v', '1', bg)
        bgb = os.path.join(B, f'previewbg_blur_{fmt}.png')     # fondo desenfocado para menú y tarjeta final
        ff('-i', bg, '-vf', 'boxblur=18:2,eq=brightness=-0.06', '-frames:v', '1', bgb)
        render(fmt, [
            {'out': os.path.join(OUT, f'{P}_rueda_{fmt}.png'), 'state': {'mode': 'rueda', 'bg': bg, 'blur': 1, 'open': 1, 'sel': SEL}},
            {'out': os.path.join(B, f'menu_{fmt}.png'), 'state': {'mode': 'probador', 'cursor': len(OUTFIT), 'equipped': len(OUTFIT),
                                                                    'menu': 1, 'money': MONEY0 - TOTAL, 'moneyPop': 1}},
            {'out': os.path.join(OUT, f'{P}_final_preview_{fmt}.png'), 'state': {'mode': 'final', 'bg': bgb, 't': 2, 'money': MONEY0 - TOTAL}},
        ])
        ff('-i', bgb, '-i', os.path.join(B, f'menu_{fmt}.png'), '-filter_complex', '[0:v]eq=brightness=-0.04[a];[a][1:v]overlay=0:0',
           '-frames:v', '1', os.path.join(OUT, f'{P}_menu_preview_{fmt}.png'))
        print('vista previa lista', fmt)
        continue

    # ---------------- VIDEO COMPLETO ----------------
    vf = (VID.get('walkCrop4x5', 'crop=720:900:0:140') + ',scale=1080:1350:flags=lanczos' if fmt == '4x5'
          else 'scale=1084:1920:flags=lanczos,crop=1080:1920')
    walk = os.path.join(B, f'walk_{fmt}.mp4')
    ff('-i', WALK, '-vf', f'{vf},{GRADE},fps={FPS}', '-an', *TMP, walk)
    last, mid = os.path.join(B, f'last_{fmt}.png'), os.path.join(B, f'mid_{fmt}.png')
    ff('-sseof', '-0.05', '-i', walk, '-frames:v', '1', '-update', '1', last)
    ff('-ss', str(VID.get('midTime', 2.3)), '-i', walk, '-frames:v', '1', mid)

    tryv = os.path.join(B, f'try_{fmt}.mp4')
    if fmt == '9x16':
        ff('-i', TRY, '-vf', f'scale=1080:1920:flags=lanczos,{GRADE},fps={FPS}', '-an', *TMP, tryv)
    else:
        ff('-i', TRY, '-filter_complex',
           '[0:v]split[a][b];'
           '[a]scale=1080:1920,crop=1080:1350,boxblur=24:2,eq=brightness=-0.12:saturation=0.9[bg];'
           '[b]scale=-2:1350:flags=lanczos[fg];'
           f'[bg][fg]overlay=W-w:0,{GRADE},fps={FPS}[v]', '-map', '[v]', '-an', *TMP, tryv)
    try_last = os.path.join(B, f'trylast_{fmt}.png')
    ff('-sseof', '-0.05', '-i', tryv, '-frames:v', '1', '-update', '1', try_last)
    try_dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                             '-of', 'csv=p=0', tryv]).decode())

    hud = os.path.join(B, f'hud_{fmt}.png')
    rueda_png = os.path.join(OUT, f'{P}_slide2_rueda_{fmt}.png')
    wdir, tdir, fdir = seq(fmt, 'wheel'), seq(fmt, 'tryov'), seq(fmt, 'final')
    frames = [{'out': hud, 'state': {'mode': 'hud'}},
              {'out': rueda_png, 'state': {'mode': 'rueda', 'bg': mid, 'blur': 1, 'open': 1, 'sel': SEL}}]
    frames += [{'out': f'{wdir}/w_{k:04d}.png', 'state': wheel_state(k / FPS, last)} for k in range(round(WHEEL_DUR * FPS))]
    frames += [{'out': f'{tdir}/t_{k:04d}.png', 'state': try_state(k / FPS)} for k in range(round(try_dur * FPS))]
    frames += [{'out': f'{fdir}/f_{k:04d}.png', 'state': {'mode': 'final', 'bg': try_last, 't': k / FPS, 'money': MONEY0 - TOTAL}}
               for k in range(round(FINAL_DUR * FPS))]
    render(fmt, frames)

    walk_hud = os.path.join(B, f'walkhud_{fmt}.mp4')
    ff('-i', walk, '-i', hud, '-filter_complex', '[0:v][1:v]overlay=0:0,setsar=1[v]', '-map', '[v]', *TMP, walk_hud)
    wclip = os.path.join(B, f'wheelclip_{fmt}.mp4')
    ff('-framerate', str(FPS), '-i', f'{wdir}/w_%04d.png', '-vf', f'fade=t=out:st={WHEEL_DUR - 0.45}:d=0.45,setsar=1', *TMP, wclip)
    tclip = os.path.join(B, f'tryclip_{fmt}.mp4')
    ff('-i', tryv, '-framerate', str(FPS), '-i', f'{tdir}/t_%04d.png', '-filter_complex',
       '[0:v][1:v]overlay=0:0:shortest=1,fade=t=in:st=0:d=0.35,setsar=1[v]', '-map', '[v]', *TMP, tclip)
    fclip = os.path.join(B, f'finalclip_{fmt}.mp4')
    ff('-framerate', str(FPS), '-i', f'{fdir}/f_%04d.png', '-vf', 'setsar=1', *TMP, fclip)

    if fmt == '4x5':
        concat([walk_hud, wclip, tclip, fclip], os.path.join(OUT, f'{P}_video_completo_4x5.mp4'))
        concat([walk_hud], os.path.join(OUT, f'{P}_slide1_video_4x5.mp4'))
        concat([tclip, fclip], os.path.join(OUT, f'{P}_slide3_probador_4x5.mp4'))
        ff('-ss', str(BUY_AT + 0.3), '-i', tclip, '-frames:v', '1', os.path.join(OUT, f'{P}_slide3_probador_4x5.png'))
    else:
        concat([walk_hud, wclip, tclip, fclip], os.path.join(OUT, f'{P}_reel_9x16.mp4'))
        concat([walk_hud], os.path.join(OUT, f'{P}_slide1_video_9x16.mp4'))
    print('listo', fmt)

for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)) // 1024, 'KB')
