# Beta Snow en "modo GTA" — carrusel / reel

Recreación del formato "tienda dentro del juego" (caminata en tercera persona con HUD + rueda de selección de accesorios) para **Beta Snow** (betasnow.cl · @betasnowcl).

## Archivos finales (`out/`)
| Archivo | Uso |
|---|---|
| `beta_slide1_video_4x5.mp4` | Slide 1 del carrusel (1080×1350): caminata IA + HUD |
| `beta_slide2_rueda_4x5.png` | Slide 2 del carrusel (1080×1350): rueda de accesorios |
| `beta_video_completo_4x5.mp4` | Todo en un video para el feed (caminata → rueda animada) |
| `beta_reel_9x16.mp4` | Versión vertical para Reels / TikTok (1080×1920) |
| `beta_slide1_video_9x16.mp4`, `beta_rueda_9x16.png` | Variantes verticales sueltas |

Los videos van sin música (pista silenciosa): agrega el audio en Instagram.

## Cómo se hizo
- `assets/ia/escena_inicio.png`: escena generada con GPT Image 2.6 (Higgsfield) usando el logo real como referencia.
- `assets/ia/caminata_kling.mp4`: animación image-to-video con Kling 3.0 (6 s).
- `assets/productos/`: fotos reales del catálogo de betasnow.cl, recortadas con `src/recortar_productos.py`.
- `src/escena.html`: HUD (reloj, dinero, vida, estrellas, puño, minimapa) y rueda de accesorios.
- `src/render.js` + `src/construir.py`: renderizan con Playwright y montan con ffmpeg.

Para cambiar productos/nombres/precios, edita `ITEMS` en `src/escena.html` y corre:

```bash
python3 src/construir.py
```
