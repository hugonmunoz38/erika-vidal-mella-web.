# Beta Snow en "modo GTA" — carrusel / reel

Recreación del formato "tienda dentro del juego" para **Beta Snow** (betasnow.cl · @betasnowcl),
ambientada en una Vice City / Leonida estilo GTA 6: calles tipo Miami al atardecer, tonos cálidos con
acentos rosados y turquesa, look fotorrealista.

## Secuencia del video completo (~19 s)
1. **Caminata** (0–6 s): el personaje llega y entra a la tienda BETA, con HUD (reloj, dinero, vida, estrellas, puño, minimapa).
2. **Rueda de accesorios** (6–11 s): 8 accesorios reales de betasnow.cl; el cursor frena en el Jockey HUF Sector ($47.990).
3. **Probador** (11–16 s): fundido a negro y cámara de tienda. Se prueba el outfit HUF Sector
   (jockey, polera, short y calcetines), se acomoda el jockey y gira para mostrar el biohazard de la espalda.
   El menú de la tienda va marcando cada prenda y al "Comprar todo" se descuentan $154.960 del dinero.
4. **Tarjeta final** (16–19 s): "OUTFIT COMPLETADO · ESTILO +" y betasnow.cl · @betasnowcl.

## Archivos finales (`out/`)
| Archivo | Uso |
|---|---|
| `beta_video_completo_4x5.mp4` | Todo en un video para el feed (1080×1350) |
| `beta_reel_9x16.mp4` | Versión vertical para Reels / TikTok (1080×1920) |
| `beta_slide1_video_4x5.mp4` | Carrusel slide 1: caminata + HUD |
| `beta_slide2_rueda_4x5.png` | Carrusel slide 2: rueda de accesorios |
| `beta_slide3_probador_4x5.mp4` / `.png` | Carrusel slide 3: probador + tarjeta final |
| `beta_slide1_video_9x16.mp4`, `beta_rueda_9x16.png` | Variantes verticales sueltas |

Los videos van sin música (pista silenciosa): agrega el audio en Instagram.

## Cómo se hizo
- `assets/ia/escena_inicio.png` → `caminata_kling.mp4`: escena con GPT Image 2.6 (logo real como referencia) animada con Kling 3.0.
- `assets/ia/probador_frente.png` + `probador_espalda.png` → `probador_kling.mp4`: fotos reales de las prendas como referencia,
  y Kling 3.0 con fotograma inicial y final para el giro.
- `assets/productos/`: fotos reales del catálogo de betasnow.cl, recortadas con `src/recortar_productos.py`.
- `src/escena.html`: HUD, rueda, menú de tienda y tarjeta final.
- `src/render.js` + `src/construir.py`: renderizan con Playwright y montan con ffmpeg (incluye la corrección de color).

Para cambiar productos/nombres/precios, edita `ITEMS` y `OUTFIT` en `src/escena.html` y corre:

```bash
python3 src/construir.py
```
