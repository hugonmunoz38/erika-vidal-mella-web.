#!/usr/bin/env python3
"""Video Archif "GTA 6" con el personaje EN MOVIMIENTO: toma un clip corto del personaje (generado gratis
con Hailuo a partir de la foto del outfit 1) y le cambia la ropa por la de cada foto de outfit siguiendo
su movimiento (flujo óptico + torso rígido + una transformación por pierna). Luego arma el editor de
outfits con la interfaz GTA encima y lo une con la entrada a la tienda.

Requiere haber corrido antes src/archif_gta6.py (usa su caminata y la interfaz ya renderizadas).
Uso: python3 src/archif_gta6_mov.py
Salidas: tiendas/archif/out/archif_gta6_movimiento_9x16.mp4 y _4x5.mp4
"""
import cv2, glob, numpy as np, os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tiendas', 'archif'); SRC = os.path.join(ROOT, 'src'); MOV = os.path.join(SRC, 'movimiento')
B6 = os.path.join(ROOT, 'build', 'archif_gta6'); W = os.path.join(ROOT, 'build', 'archif_mov'); OUT = os.path.join(T, 'out')
CLIP = os.path.join(T, 'ia', 'idle_hailuo.mp4'); FPS = 30
# misma interfaz del editor GTA 6, con una pausa inicial en la primera fila (el personaje hace su gesto)
ED6UI = os.path.join(T, 'editor_gta6_mov_ui.json')
os.makedirs(W, exist_ok=True)

def ff(*a): subprocess.run(['ffmpeg', '-v', 'error', '-y', *a], check=True)
def py(script, *a): subprocess.run(['python3', os.path.join(MOV, script), *a], check=True)

# 1) cuadros del clip
if not os.path.exists(os.path.join(W, 'f', '0124.jpg')):
    os.makedirs(os.path.join(W, 'f'), exist_ok=True)
    ff('-i', CLIP, '-q:v', '2', os.path.join(W, 'f', '%04d.jpg'))

# 2) alinear la foto del outfit 1 con el primer cuadro (el clip salió de esa foto)
if not os.path.exists(os.path.join(W, 'A.npy')):
    P = cv2.imread(os.path.join(T, 'personaje', 'estados', 's1.jpg')); V = cv2.imread(os.path.join(W, 'f', '0001.jpg'))
    sift = cv2.SIFT_create(10000)
    k1, d1 = sift.detectAndCompute(cv2.cvtColor(P, cv2.COLOR_BGR2GRAY), None)
    k2, d2 = sift.detectAndCompute(cv2.cvtColor(V, cv2.COLOR_BGR2GRAY), None)
    g = [a for a, b in cv2.BFMatcher().knnMatch(d1, d2, k=2) if a.distance < .75 * b.distance]
    A, _ = cv2.estimateAffine2D(np.float32([k1[a.queryIdx].pt for a in g]), np.float32([k2[a.trainIdx].pt for a in g]), ransacReprojThreshold=2.5)
    np.save(os.path.join(W, 'A.npy'), A)

# 3) movimiento, segmentación y cuadros compuestos de cada outfit
if not os.path.exists(os.path.join(W, 'maps.npy')): py('flujo.py', W)
os.makedirs(os.path.join(W, 'seg'), exist_ok=True); py('segall.py', W)
if not os.path.exists(os.path.join(W, 'comp', 's9', '0123.jpg')): py('render.py', W, os.path.join(W, 'comp'))

for fmt in ('9x16', '4x5'):
    # 4) pista del personaje (outfit según la fila seleccionada) + interfaz GTA transparente encima
    bgv = os.path.join(W, f'edbg_{fmt}.mp4')
    py('fondo_mov.py', os.path.join(W, 'f'), os.path.join(W, 'comp'), ED6UI, fmt, bgv)
    edd = os.path.join(W, f'ui_{fmt}')
    if not os.path.exists(os.path.join(edd, 'v_0480.png')):
        shutil.rmtree(edd, ignore_errors=True)
        subprocess.run(['node', os.path.join(SRC, 'render_plantilla.js'), 'editor.html', ED6UI, fmt, edd, str(FPS)], check=True)
    edv = os.path.join(W, f'ed_{fmt}.mp4')
    ff('-i', bgv, '-framerate', str(FPS), '-i', os.path.join(edd, 'v_%04d.png'), '-filter_complex',
       '[0:v][1:v]overlay=0:0:shortest=1,fade=t=in:st=0:d=0.35,setsar=1[v]', '-map', '[v]',
       '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', edv)
    # 5) entrada a la tienda + editor, con grano de película
    ff('-i', os.path.join(B6, f'walk2_{fmt}.mp4'), '-i', edv, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
       '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0,noise=alls=3:allf=t[v]', '-map', '[v]', '-map', '2:a',
       '-c:v', 'libx264', '-crf', '20', '-maxrate', '12M', '-bufsize', '24M', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
       '-c:a', 'aac', '-b:a', '128k', '-shortest', os.path.join(OUT, f'archif_gta6_movimiento_{fmt}.mp4'))
    print('listo', fmt)
