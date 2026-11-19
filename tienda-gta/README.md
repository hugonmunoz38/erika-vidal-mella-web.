# Tienda en "modo GTA" — carrusel / reel por tienda

Formato "tienda dentro del juego", ambientado en una Vice City / Leonida estilo GTA 6
(calles tipo Miami al atardecer, tonos cálidos con acentos rosados y turquesa, look fotorrealista):

1. **Caminata** hacia la tienda con HUD (reloj, dinero, vida, estrellas, puño, minimapa).
2. **Rueda de productos** reales de la tienda; el cursor da una vuelta y frena en el producto destacado.
3. **Probador**: fundido y cámara de tienda; menú con banner de la marca, prendas y precios reales,
   compra y descuento de dinero; el personaje se prueba el outfit y gira.
4. **Tarjeta final** con la web y el Instagram de la tienda.

## Tiendas
| Tienda | Estado | Productos |
|---|---|---|
| `tiendas/beta` (Beta Snow) | **Listo**: video completo 4:5 y 9:16, slides de carrusel | Accesorios + outfit HUF Sector |
| `tiendas/vans` (Vans Chile) | **Vista previa** (rueda, menú, tarjeta final). Faltan los clips IA | New In: 8 zapatillas + outfit New In |
| `tiendas/bold` (Bold) | **Vista previa** (rueda, menú, tarjeta final). Faltan los clips IA | Nuevas llegadas: 8 zapatillas, prueba de Air Max 95 |

Cada tienda tiene `config.json` (productos, precios, textos, colores, logo y los prompts de IA),
`productos/` (fotos reales recortadas), `marca/` (logo), `ref/` (fotos de referencia), `ia/` (clips IA) y `out/`.

## Uso

```bash
python3 src/construir.py beta     # o vans / bold
```

- Si existen `ia/caminata_kling.mp4` y `ia/probador_kling.mp4`, arma el video completo (~19 s) y las slides.
- Si no, arma la **vista previa** (`<tienda>_rueda_*.png`, `<tienda>_menu_preview_*.png`, `<tienda>_final_preview_*.png`)
  sobre `video.previewBg`.

### Para terminar Vans y Bold (requiere créditos de IA, ~20 por tienda en Higgsfield)
Los prompts y referencias están en `tiendas/<tienda>/kit/` (`PASOS.md` + `referencias/`); se pueden generar gratis en ChatGPT/Gemini (imágenes) y Kling/Flow/Dreamina (videos):
1. `escena` → imagen 9:16 (GPT Image 2.6) con el logo/fachada de `ref/` o `marca/` como referencia.
2. `caminata` → Kling 3.0, 6 s, image-to-video desde la escena → guardar como `ia/caminata_kling.mp4`.
3. `probador_frente` y `probador_espalda` → imágenes con las fotos de `productos/` como referencia.
4. `probador_video` → Kling 3.0, 5 s, con fotograma inicial y final → guardar como `ia/probador_kling.mp4`.
5. `python3 src/construir.py <tienda>`.

## Herramientas
- `src/escena.html`: HUD, rueda, menú de tienda y tarjeta final (lee `window.STORE`).
- `src/render.js`: renderiza cuadros con Playwright e inyecta la config de la tienda.
- `src/construir.py`: monta todo con ffmpeg (incluye la corrección de color).
- `src/recortar_productos.py`: recorta fondos de fotos de producto con rembg (o `--plano`).

Los videos van sin música (pista silenciosa): agrega el audio en Instagram.
