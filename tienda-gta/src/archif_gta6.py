#!/usr/bin/env python3
"""Video Archif "GTA 6": entrada a la tienda (caminata IA con letrero ARCHIF) + editor de outfits.

Uso: python3 src/archif_gta6.py
Salidas: tiendas/archif/out/archif_gta6_9x16.mp4 y archif_gta6_4x5.mp4
"""
import glob, json, os, shutil, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tiendas', 'archif'); SRC = os.path.join(ROOT, 'src')
B = os.path.join(ROOT, 'build', 'archif_gta6'); OUT = os.path.join(T, 'out')
os.makedirs(B, exist_ok=True); FPS = 30
WALK = os.path.join(T, 'ia', 'caminata_archif.mp4')

# Look "Vice City / Leonida": luces cálidas y rosadas, sombras turquesa, bloom suave, viñeta
GRADE6 = ('eq=contrast=1.1:saturation=1.22:gamma=0.97,'
          'colorbalance=rs=-0.06:gs=-0.01:bs=0.07:rm=0.03:gm=-0.02:bm=0.03:rh=0.09:gh=0.02:bh=-0.05,'
          'split[ga][gb];[gb]gblur=sigma=14[gbb];[ga][gbb]blend=all_mode=screen:all_opacity=0.2,vignette=angle=PI/4.5')

def ff(*a): subprocess.run(['ffmpeg', '-v', 'error', '-y', *a], check=True)
def render(tpl, cfg, fmt, d):
    shutil.rmtree(d, ignore_errors=True)
    subprocess.run(['node', os.path.join(SRC, 'render_plantilla.js'), tpl, cfg, fmt, d, str(FPS)], check=True)

# 1) fotos del editor con el mismo look
EST = os.path.join(T, 'personaje', 'estados'); EST6 = os.path.join(T, 'personaje', 'estados_gta6'); os.makedirs(EST6, exist_ok=True)
for f in sorted(glob.glob(os.path.join(EST, 's*.jpg'))):
    ff('-i', f, '-filter_complex', f'[0:v]{GRADE6}[v]', '-map', '[v]', '-q:v', '2', os.path.join(EST6, os.path.basename(f)))
ed = json.load(open(os.path.join(T, 'editor.json')))
for r in ed['rows']:
    if r.get('state'): r['state'] = r['state'].replace('/estados/', '/estados_gta6/')
ED6 = os.path.join(T, 'editor_gta6.json'); json.dump(ed, open(ED6, 'w'), indent=2, ensure_ascii=False)

for fmt in ('9x16', '4x5'):
    vf = 'crop=720:900:0:140,scale=1080:1350:flags=lanczos' if fmt == '4x5' else 'scale=1084:1920:flags=lanczos,crop=1080:1920'
    walk = os.path.join(B, f'walk_{fmt}.mp4')
    ff('-i', WALK, '-filter_complex', f'[0:v]{vf},{GRADE6},fps={FPS}[v]', '-map', '[v]', '-an', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', walk)
    # 2) HUD y título sobre la caminata
    ov = os.path.join(B, f'ov_{fmt}'); render('entrada.html', os.path.join(T, 'entrada.json'), fmt, ov)
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', walk]).decode())
    walk2 = os.path.join(B, f'walk2_{fmt}.mp4')
    ff('-i', walk, '-framerate', str(FPS), '-i', os.path.join(ov, 'v_%04d.png'), '-filter_complex',
       f'[0:v][1:v]overlay=0:0:shortest=1,fade=t=out:st={dur - 0.35:.2f}:d=0.35,setsar=1[v]', '-map', '[v]',
       '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', walk2)
    # 3) editor de outfits
    edd = os.path.join(B, f'ed_{fmt}'); render('editor.html', ED6, fmt, edd)
    edv = os.path.join(B, f'ed_{fmt}.mp4')
    ff('-framerate', str(FPS), '-i', os.path.join(edd, 'v_%04d.png'), '-vf', 'fade=t=in:st=0:d=0.35,setsar=1',
       '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', edv)
    # 4) unir + grano de película en todo
    ff('-i', walk2, '-i', edv, '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
       '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0,noise=alls=3:allf=t[v]', '-map', '[v]', '-map', '2:a',
       '-c:v', 'libx264', '-crf', '20', '-maxrate', '12M', '-bufsize', '24M', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
       '-c:a', 'aac', '-b:a', '128k', '-shortest', os.path.join(OUT, f'archif_gta6_{fmt}.mp4'))
    print('listo', fmt)
