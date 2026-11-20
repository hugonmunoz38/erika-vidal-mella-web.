#!/usr/bin/env python3
"""Renderiza el video "vestidor estilo GTA" de una tienda (sin IA: fotos reales de producto).

Uso: python3 src/vestidor.py <tienda>     -> lee tiendas/<tienda>/vestidor.json
Salidas: tiendas/<tienda>/out/<tienda>_vestidor_9x16.mp4 y _4x5.mp4 (+ una imagen por outfit)
"""
import json, os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
st = sys.argv[1] if len(sys.argv) > 1 else 'archif'
T = os.path.join(ROOT, 'tiendas', st); CFG = os.path.join(T, 'vestidor.json'); OUT = os.path.join(T, 'out')
B = os.path.join(ROOT, 'build', st + '_vestidor'); os.makedirs(OUT, exist_ok=True)
cfg = json.load(open(CFG)); FPS = 30
for fmt in ('9x16', '4x5'):
    d = os.path.join(B, fmt); shutil.rmtree(d, ignore_errors=True)
    subprocess.run(['node', os.path.join(ROOT, 'src', 'render_vestidor.js'), CFG, fmt, d, str(FPS)], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(d, 'v_%04d.png'),
                    '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                    '-c:v', 'libx264', '-crf', '17', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    '-c:a', 'aac', '-b:a', '128k', '-shortest', os.path.join(OUT, f'{st}_vestidor_{fmt}.mp4')], check=True)
    # una imagen por outfit (para carrusel)
    ch = cfg['timeline']['changes']
    seen = []
    for t, k in ch:
        if k in seen: continue
        seen.append(k)
        f = os.path.join(d, f'v_{int((t + 0.9) * FPS):04d}.png')
        if fmt == '4x5' and os.path.exists(f):
            shutil.copy(f, os.path.join(OUT, f'{st}_outfit{k + 1}_4x5.png'))
    print('listo', fmt)
for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)) // 1024, 'KB')
