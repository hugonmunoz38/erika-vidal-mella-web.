#!/usr/bin/env python3
"""Arma las piezas finales del carrusel / reel "Beta Snow en modo GTA".

Entradas : assets/ia/caminata_kling.mp4 (clip IA), assets/productos/*.png, src/escena.html
Salidas  : out/
  beta_slide1_video_4x5.mp4     -> slide 1 del carrusel (caminata + HUD)
  beta_slide2_rueda_4x5.png     -> slide 2 del carrusel (rueda de accesorios)
  beta_video_completo_4x5.mp4   -> caminata + rueda animada en un solo video (feed)
  beta_reel_9x16.mp4            -> lo mismo en vertical para Reels/TikTok
  beta_slide1_video_9x16.mp4, beta_rueda_9x16.png -> variantes verticales
"""
import json, math, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, B, OUT = os.path.join(ROOT, 'src'), os.path.join(ROOT, 'build'), os.path.join(ROOT, 'out')
FPS = 30
CLIP = os.path.join(ROOT, 'assets/ia/caminata_kling.mp4')
os.makedirs(B, exist_ok=True); os.makedirs(OUT, exist_ok=True)

def run(*cmd):
    subprocess.run(cmd, check=True)

def ff(*args):
    run('ffmpeg', '-v', 'error', '-y', *args)

def render(fmt, frames):
    job = os.path.join(B, f'job_{fmt}.json')
    json.dump({'fmt': fmt, 'frames': frames}, open(job, 'w'))
    run('node', os.path.join(SRC, 'render.js'), job)

ENC = ['-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart']
SILENT = ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100']
AUD = ['-c:a', 'aac', '-b:a', '128k', '-shortest']

# --- Animación de la rueda -------------------------------------------------
#  (tiempo_seg, índice seleccionado): el cursor da una vuelta y frena en el jockey
SEL_STEPS = [(0.45, 0), (0.78, 1), (1.06, 2), (1.32, 3), (1.56, 4), (1.80, 5), (2.06, 6),
             (2.36, 7), (2.72, 0), (3.14, 1), (3.66, 2)]
WHEEL_DUR = 5.4
OPEN_AT, OPEN_LEN = 0.05, 0.40
BLUR_LEN = 0.45

def wheel_state(t, bg):
    sel, since = SEL_STEPS[0][1], t - SEL_STEPS[0][0]
    for ts, i in SEL_STEPS:
        if t >= ts:
            sel, since = i, t - ts
    landed = t >= SEL_STEPS[-1][0] + 0.25
    return {
        'mode': 'rueda', 'bg': bg,
        'blur': min(1.0, t / BLUR_LEN),
        'open': max(0.0, min(1.0, (t - OPEN_AT) / OPEN_LEN)),
        'sel': sel, 'pop': min(1.0, max(0.0, since) / 0.16),
        'price': landed, 'buy': landed,
    }

for fmt, H in (('4x5', 1350), ('9x16', 1920)):
    vf = ('crop=720:900:0:140,scale=1080:1350:flags=lanczos' if fmt == '4x5'
          else 'scale=1084:1920:flags=lanczos,crop=1080:1920')
    walk = os.path.join(B, f'walk_{fmt}.mp4')
    ff('-i', CLIP, '-vf', f'{vf},fps={FPS}', '-an', '-c:v', 'libx264', '-crf', '12', '-preset', 'slow', '-pix_fmt', 'yuv420p', walk)
    last, mid = os.path.join(B, f'last_{fmt}.png'), os.path.join(B, f'mid_{fmt}.png')
    ff('-sseof', '-0.05', '-i', walk, '-frames:v', '1', '-update', '1', last)
    ff('-ss', '2.3', '-i', walk, '-frames:v', '1', mid)

    # HUD estático + slide de la rueda + cuadros de la animación
    wdir = os.path.join(B, f'wheel_{fmt}')
    shutil.rmtree(wdir, ignore_errors=True)
    hud = os.path.join(B, f'hud_{fmt}.png')
    rueda_png = os.path.join(OUT, 'beta_slide2_rueda_4x5.png' if fmt == '4x5' else 'beta_rueda_9x16.png')
    frames = [{'out': hud, 'state': {'mode': 'hud'}},
              {'out': rueda_png, 'state': {'mode': 'rueda', 'bg': mid, 'blur': 1, 'open': 1, 'sel': 2}}]
    n = round(WHEEL_DUR * FPS)
    frames += [{'out': os.path.join(wdir, f'w_{k:04d}.png'), 'state': wheel_state(k / FPS, last)} for k in range(n)]
    render(fmt, frames)

    # Slide 1: caminata + HUD
    s1 = os.path.join(OUT, f'beta_slide1_video_{fmt}.mp4')
    ff('-i', walk, '-i', hud, *SILENT, '-filter_complex', '[0:v][1:v]overlay=0:0[v]', '-map', '[v]', '-map', '2:a', *ENC, *AUD, s1)

    # Animación de la rueda como clip
    wclip = os.path.join(B, f'wheelclip_{fmt}.mp4')
    ff('-framerate', str(FPS), '-i', os.path.join(wdir, 'w_%04d.png'), '-c:v', 'libx264', '-crf', '12', '-preset', 'slow', '-pix_fmt', 'yuv420p', wclip)

    # Video completo: caminata con HUD + rueda
    full = os.path.join(OUT, 'beta_video_completo_4x5.mp4' if fmt == '4x5' else 'beta_reel_9x16.mp4')
    ff('-i', walk, '-i', hud, '-i', wclip, *SILENT,
       '-filter_complex', '[0:v][1:v]overlay=0:0,setsar=1[a];[2:v]setsar=1[b];[a][b]concat=n=2:v=1:a=0[v]',
       '-map', '[v]', '-map', '3:a', *ENC, *AUD, full)
    print('listo', fmt)

for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)) // 1024, 'KB')
