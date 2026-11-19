#!/usr/bin/env python3
"""Genera imágenes y clips con Spaces gratuitos de Hugging Face (ZeroGPU), sin créditos de pago.

  imagen  : akhaliq/Qwen-Image-Edit-2509        (Qwen Image Edit Plus, 8 pasos, 2 imágenes de referencia)
  video   : zerogpu-aoti/wan2-2-fp8da-aoti-faster (Wan 2.2 14B, imagen a video)
  giro    : multimodalart/wan-2-2-first-last-frame (Wan 2.2, fotograma inicial y final)

Uso:
  python3 ia_gratis.py imagen  salida.png "prompt" ref1.png ref2.png [--steps 8]
            (la imagen de salida toma el formato de ref1: usa una ref1 vertical 9:16)
  python3 ia_gratis.py video   salida.mp4 inicio.png "prompt" [--dur 5]
  python3 ia_gratis.py giro    salida.mp4 inicio.png fin.png "prompt" [--dur 5]

Las cuotas de GPU gratis son diarias (cuenta gratis ~5 min/día). El token gratuito de Hugging Face
lo inyecta el proxy del entorno en el encabezado x-hf-authorization; el script no lo maneja.
"""
import os, shutil, sys, time
from gradio_client import Client, handle_file


def _opt(args, name, default, cast=float):
    if name in args:
        i = args.index(name); v = cast(args[i + 1]); del args[i:i + 2]; return v
    return default

def _client(space):
    # marcador: el proxy del entorno lo reemplaza por el token real de Hugging Face
    return Client(space, verbose=False, headers={"x-hf-authorization": "Bearer proxy-injected"})

def _save(res, out):
    # gradio devuelve una ruta, un dict con 'video'/'path', o una lista/tupla
    if isinstance(res, (list, tuple)):
        res = res[0]
    if isinstance(res, dict):
        res = res.get('video') or res.get('path') or res.get('image') or res.get('value')
        if isinstance(res, dict):
            res = res.get('path')
    shutil.copy(res, out)
    return out

def imagen(out, prompt, refs, steps=8, seed=None):
    c = _client('akhaliq/Qwen-Image-Edit-2509')
    a, b = refs[0], (refs[1] if len(refs) > 1 else refs[0])
    res = c.predict(image1=handle_file(a), image2=handle_file(b), prompt=prompt,
                    seed=int(seed if seed is not None else time.time()) % 2**31, true_cfg_scale=1.0,
                    negative_prompt=' ', num_steps=steps, guidance_scale=1.0, api_name='/edit_images')
    return _save(res, out)

def video(out, img, prompt, dur=5.0):
    c = _client('zerogpu-aoti/wan2-2-fp8da-aoti-faster')
    res = c.predict(input_image=handle_file(img), prompt=prompt, steps=6, duration_seconds=dur,
                    guidance_scale=1, guidance_scale_2=1, seed=42, randomize_seed=True, api_name='/generate_video')
    return _save(res, out)

def giro(out, a, b, prompt, dur=5.0):
    c = _client('multimodalart/wan-2-2-first-last-frame')
    res = c.predict(start_image_pil=handle_file(a), end_image_pil=handle_file(b), prompt=prompt,
                    duration_seconds=dur, steps=8, guidance_scale=1.0, guidance_scale_2=1.0, seed=42,
                    randomize_seed=True, api_name='/generate_video')
    return _save(res, out)

if __name__ == '__main__':
    a = sys.argv[1:]
    mode = a.pop(0)
    t0 = time.time()
    if mode == 'imagen':
        st = _opt(a, '--steps', 8, int)
        out, prompt, refs = a[0], a[1], a[2:]
        print(imagen(out, prompt, refs, st))
    elif mode == 'video':
        d = _opt(a, '--dur', 5.0)
        print(video(a[0], a[1], a[2], d))
    elif mode == 'giro':
        d = _opt(a, '--dur', 5.0)
        print(giro(a[0], a[1], a[2], a[3], d))
    print(f'{time.time() - t0:.0f} s')
