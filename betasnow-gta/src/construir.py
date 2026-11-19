#!/usr/bin/env python3
"""Arma las piezas finales "Beta Snow en modo GTA".

Secuencia del video completo (~19 s):
  1) caminata IA hacia la tienda + HUD                    (assets/ia/caminata_kling.mp4)
  2) rueda de accesorios: el cursor frena en el jockey      (cuadros de src/escena.html)
  3) fundido a negro -> probador: se prueba el outfit HUF Sector, menú de tienda,
     compra y descuento de dinero                            (assets/ia/probador_kling.mp4)
  4) tarjeta final "OUTFIT COMPLETADO" + betasnow.cl

Salidas en out/ (4:5 para el feed/carrusel y 9:16 para Reels/TikTok).
"""
import json, os, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, B, OUT = os.path.join(ROOT, 'src'), os.path.join(ROOT, 'build'), os.path.join(ROOT, 'out')
FPS = 30
WALK_SRC = os.path.join(ROOT, 'assets/ia/caminata_kling.mp4')
TRY_SRC = os.path.join(ROOT, 'assets/ia/probador_kling.mp4')
os.makedirs(B, exist_ok=True); os.makedirs(OUT, exist_ok=True)

# Corrección de color cálida/saturada estilo trailer (sombras levemente turquesa, luces cálidas)
GRADE = ('eq=contrast=1.06:saturation=1.12:gamma=0.98,'
         'colorbalance=rs=-0.03:gs=0.0:bs=0.04:rh=0.04:gh=0.01:bh=-0.03,'
         'vignette=angle=PI/5')

def run(*cmd):
    subprocess.run(cmd, check=True)

def ff(*args):
    run('ffmpeg', '-v', 'error', '-y', *args)

def render(fmt, frames, tag):
    job = os.path.join(B, f'job_{tag}_{fmt}.json')
    json.dump({'fmt': fmt, 'frames': frames}, open(job, 'w'))
    run('node', os.path.join(SRC, 'render.js'), job)

def seq(fmt, name):
    d = os.path.join(B, f'{name}_{fmt}')
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    return d

ENC = ['-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
TMP = ['-c:v', 'libx264', '-crf', '12', '-preset', 'medium', '-pix_fmt', 'yuv420p']
SILENT = ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100']
AUD = ['-c:a', 'aac', '-b:a', '128k', '-shortest']

# --- 2) rueda ---------------------------------------------------------------
SEL_STEPS = [(0.45, 0), (0.78, 1), (1.06, 2), (1.32, 3), (1.56, 4), (1.80, 5), (2.06, 6),
             (2.36, 7), (2.72, 0), (3.14, 1), (3.66, 2)]
WHEEL_DUR = 5.4

def wheel_state(t, bg):
    sel, since = SEL_STEPS[0][1], t - SEL_STEPS[0][0]
    for ts, i in SEL_STEPS:
        if t >= ts:
            sel, since = i, t - ts
    landed = t >= SEL_STEPS[-1][0] + 0.25
    return {'mode': 'rueda', 'bg': bg, 'blur': min(1.0, t / 0.45),
            'open': max(0.0, min(1.0, (t - 0.05) / 0.40)),
            'sel': sel, 'pop': min(1.0, max(0.0, since) / 0.16), 'price': landed, 'buy': landed}

# --- 3) probador --------------------------------------------------------------
MONEY0, TOTAL = 9999900, 47990 + 36990 + 49990 + 19990

def try_state(t):
    steps = [(0.0, 0, 1), (0.7, 1, 2), (1.4, 2, 3), (2.1, 3, 4), (2.8, 4, 4)]
    cur, eq = 0, 1
    for ts, c, e in steps:
        if t >= ts:
            cur, eq = c, e
    k = min(1.0, max(0.0, (t - 3.1) / 0.8))                       # descuento del dinero
    pop = 0.0 if t < 3.1 else (1.0 if t < 4.5 else max(0.0, 1 - (t - 4.5) / 0.4))
    return {'mode': 'probador', 'cursor': cur, 'equipped': eq, 'menu': 1,
            'money': MONEY0 - TOTAL * k, 'moneyPop': pop}

FINAL_DUR = 2.6

for fmt, H in (('4x5', 1350), ('9x16', 1920)):
    # 1) caminata con corrección de color
    vf = ('crop=720:900:0:140,scale=1080:1350:flags=lanczos' if fmt == '4x5'
          else 'scale=1084:1920:flags=lanczos,crop=1080:1920')
    walk = os.path.join(B, f'walk_{fmt}.mp4')
    ff('-i', WALK_SRC, '-vf', f'{vf},{GRADE},fps={FPS}', '-an', *TMP, walk)
    last, mid = os.path.join(B, f'last_{fmt}.png'), os.path.join(B, f'mid_{fmt}.png')
    ff('-sseof', '-0.05', '-i', walk, '-frames:v', '1', '-update', '1', last)
    ff('-ss', '2.3', '-i', walk, '-frames:v', '1', mid)

    # 3) probador: 9:16 a pantalla completa; 4:5 con el personaje a la derecha y fondo desenfocado
    tryv = os.path.join(B, f'try_{fmt}.mp4')
    if fmt == '9x16':
        ff('-i', TRY_SRC, '-vf', f'scale=1080:1920:flags=lanczos,{GRADE},fps={FPS}', '-an', *TMP, tryv)
    else:
        ff('-i', TRY_SRC, '-filter_complex',
           '[0:v]split[a][b];'
           '[a]scale=1080:1920,crop=1080:1350,boxblur=24:2,eq=brightness=-0.12:saturation=0.9[bg];'
           '[b]scale=-2:1350:flags=lanczos[fg];'
           f'[bg][fg]overlay=W-w:0,{GRADE},fps={FPS}[v]', '-map', '[v]', '-an', *TMP, tryv)
    try_last = os.path.join(B, f'trylast_{fmt}.png')
    ff('-sseof', '-0.05', '-i', tryv, '-frames:v', '1', '-update', '1', try_last)
    try_dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                             '-of', 'csv=p=0', tryv]).decode())

    # Cuadros HTML: HUD, slide de la rueda, rueda animada, menú del probador, tarjeta final
    hud = os.path.join(B, f'hud_{fmt}.png')
    rueda_png = os.path.join(OUT, 'beta_slide2_rueda_4x5.png' if fmt == '4x5' else 'beta_rueda_9x16.png')
    wdir, tdir, fdir = seq(fmt, 'wheel'), seq(fmt, 'tryov'), seq(fmt, 'final')
    frames = [{'out': hud, 'state': {'mode': 'hud'}},
              {'out': rueda_png, 'state': {'mode': 'rueda', 'bg': mid, 'blur': 1, 'open': 1, 'sel': 2}}]
    frames += [{'out': f'{wdir}/w_{k:04d}.png', 'state': wheel_state(k / FPS, last)} for k in range(round(WHEEL_DUR * FPS))]
    frames += [{'out': f'{tdir}/t_{k:04d}.png', 'state': try_state(k / FPS)} for k in range(round(try_dur * FPS))]
    frames += [{'out': f'{fdir}/f_{k:04d}.png', 'state': {'mode': 'final', 'bg': try_last, 't': k / FPS, 'money': MONEY0 - TOTAL}}
               for k in range(round(FINAL_DUR * FPS))]
    render(fmt, frames, 'all')

    # Clips intermedios
    walk_hud = os.path.join(B, f'walkhud_{fmt}.mp4')
    ff('-i', walk, '-i', hud, '-filter_complex', '[0:v][1:v]overlay=0:0,setsar=1[v]', '-map', '[v]', *TMP, walk_hud)
    wclip = os.path.join(B, f'wheelclip_{fmt}.mp4')
    ff('-framerate', str(FPS), '-i', f'{wdir}/w_%04d.png', '-vf', f'fade=t=out:st={WHEEL_DUR - 0.45}:d=0.45,setsar=1', *TMP, wclip)
    tclip = os.path.join(B, f'tryclip_{fmt}.mp4')
    ff('-i', tryv, '-framerate', str(FPS), '-i', f'{tdir}/t_%04d.png', '-filter_complex',
       '[0:v][1:v]overlay=0:0:shortest=1,fade=t=in:st=0:d=0.35,setsar=1[v]', '-map', '[v]', *TMP, tclip)
    fclip = os.path.join(B, f'finalclip_{fmt}.mp4')
    ff('-framerate', str(FPS), '-i', f'{fdir}/f_%04d.png', '-vf', 'setsar=1', *TMP, fclip)

    def concat(parts, out):
        ins = sum((['-i', p] for p in parts), [])
        n = len(parts)
        fc = ''.join(f'[{i}:v]' for i in range(n)) + f'concat=n={n}:v=1:a=0[v]'
        ff(*ins, *SILENT, '-filter_complex', fc, '-map', '[v]', '-map', f'{n}:a', *ENC, *AUD, out)

    if fmt == '4x5':
        concat([walk_hud, wclip, tclip, fclip], os.path.join(OUT, 'beta_video_completo_4x5.mp4'))
        concat([walk_hud], os.path.join(OUT, 'beta_slide1_video_4x5.mp4'))
        concat([tclip, fclip], os.path.join(OUT, 'beta_slide3_probador_4x5.mp4'))
        ff('-ss', '3.4', '-i', tclip, '-frames:v', '1', os.path.join(OUT, 'beta_slide3_probador_4x5.png'))
    else:
        concat([walk_hud, wclip, tclip, fclip], os.path.join(OUT, 'beta_reel_9x16.mp4'))
        concat([walk_hud], os.path.join(OUT, 'beta_slide1_video_9x16.mp4'))
    print('listo', fmt)

for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)) // 1024, 'KB')
