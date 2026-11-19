#!/usr/bin/env python3
"""Reemplaza letreros/logos de un clip por otro logo, siguiendo el movimiento de la cámara.

Objetivos tipo "logo": detecta las letras (claras u oscuras) en un cuadro limpio de referencia,
sigue ese plano con flujo óptico + homografía hacia adelante y atrás, borra las letras
originales (inpainting de la máscara proyectada) y pega el logo nuevo con la misma perspectiva.

Objetivos tipo "alfombra": en cada cuadro detecta un tapete oscuro y borra el texto claro
que tenga encima, excluyendo a la persona (máscara con rembg) para no tocarle las piernas.

Uso: python3 reemplazar_letrero.py config.json
"""
import cv2, glob, json, os, subprocess, sys
import numpy as np

def order_quad(pts):
    pts = np.array(pts, dtype=np.float32)
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], np.float32)  # TL TR BR BL

def scale_quad(q, sx, sy):
    """Escala un cuadrilátero sobre sus propios ejes (ancho TL->TR, alto TL->BL)."""
    c = q.mean(0)
    u = (q[1] - q[0]) + (q[2] - q[3]); u /= np.linalg.norm(u) + 1e-6
    v = (q[3] - q[0]) + (q[2] - q[1]); v /= np.linalg.norm(v) + 1e-6
    return np.array([c + u * ((p - c) @ u) * sx + v * ((p - c) @ v) * sy for p in q], np.float32)

def letters_mask(img, region, polarity, min_area=40):
    """Componentes de letras dentro de la región (descarta las que tocan el borde de la región)."""
    x0, y0, x1, y1 = region
    hsv = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 2] > 200) & (hsv[..., 1] < 70)) if polarity == 'light' else (hsv[..., 2] < 90)
    m = m.astype(np.uint8) * 255
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    H, W = m.shape
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < min_area or x <= 0 or y <= 0 or x + w >= W or y + h >= H:
            continue
        keep[lab == i] = 255
    full = np.zeros(img.shape[:2], np.uint8); full[y0:y1, x0:x1] = keep
    return full

def track(grays, f0, region_mask, step):
    """Homografías acumuladas cuadro f0 -> f, siguiendo los puntos del plano del letrero."""
    Hs, Hc, f, n = {f0: np.eye(3)}, np.eye(3), f0, len(grays)
    h, w = grays[0].shape
    while 0 <= f + step < n:
        prev, cur = grays[f], grays[f + step]
        mask = cv2.warpPerspective(region_mask, Hc, (w, h))
        p0 = cv2.goodFeaturesToTrack(prev, 600, 0.01, 5, mask=mask)
        if p0 is None or len(p0) < 12:
            break
        p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, p0, None, winSize=(31, 31), maxLevel=4)
        g = st.ravel() == 1
        if g.sum() < 12:
            break
        Hs_, _ = cv2.findHomography(p0[g], p1[g], cv2.RANSAC, 2.5)
        if Hs_ is None:
            break
        Hc = Hs_ @ Hc
        f += step
        Hs[f] = Hc.copy()
    return Hs

def render_logo(logo_rgba, quad_w, quad_h, style, color, fill, valign=0.5):
    W = 1000; H = max(40, int(W * quad_h / max(quad_w, 1)))
    lh, lw = logo_rgba.shape[:2]
    sc = min(W * fill / lw, H * fill / lh)
    lw2, lh2 = max(1, int(lw * sc)), max(1, int(lh * sc))
    lg = cv2.resize(logo_rgba, (lw2, lh2), interpolation=cv2.INTER_AREA)
    a = np.zeros((H, W), np.float32)
    x0, y0 = (W - lw2) // 2, int((H - lh2) * valign)
    a[y0:y0 + lh2, x0:x0 + lw2] = lg[..., 3] / 255.0
    col = np.array(color[::-1], np.float32)       # BGR
    img = np.zeros((H, W, 3), np.float32); img[:] = col
    if style == 'neon':
        core = np.clip(col * 0.5 + 255 * 0.5, 0, 255)          # centro más claro: letra iluminada
        k = max(3, int(min(lw2, lh2) * 0.035) | 1)
        inner = cv2.GaussianBlur(cv2.erode(a, np.ones((k, k), np.uint8)), (0, 0), k / 2)
        img = img * (1 - inner[..., None] * 0.65) + core * (inner[..., None] * 0.65)
        glow = cv2.GaussianBlur(a, (0, 0), max(6, lh2 * 0.06))
    else:
        glow = np.zeros_like(a)
    return img, a, glow, col

def person_masks(frames, idxs, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    out, sess = {}, None
    for f in idxs:
        cp = os.path.join(cache_dir, f'{f + 1:04d}.png')
        if os.path.exists(cp):
            m = cv2.imread(cp, cv2.IMREAD_GRAYSCALE)
        else:
            if sess is None:
                from rembg import new_session
                sess = new_session('u2net_human_seg')
            from rembg import remove
            m = np.array(remove(cv2.cvtColor(frames[f], cv2.COLOR_BGR2RGB), session=sess, only_mask=True))
            cv2.imwrite(cp, m)
        out[f] = cv2.dilate((m > 90).astype(np.uint8) * 255, np.ones((9, 9), np.uint8))
    return out

def main(cfg_path):
    cfg = json.load(open(cfg_path))
    fd = cfg['frames_dir']; os.makedirs(fd, exist_ok=True)
    if not glob.glob(os.path.join(fd, '*.png')):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', cfg['input'], os.path.join(fd, '%04d.png')], check=True)
    paths = sorted(glob.glob(os.path.join(fd, '*.png')))
    frames = [cv2.imread(p) for p in paths]
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    out = [f.copy() for f in frames]
    h, w = frames[0].shape[:2]
    dbg_dir = cfg.get('debug_dir')

    for t in cfg['targets']:
        if t['type'] == 'alfombra':
            a, b = t['frames'][0] - 1, t['frames'][1] - 1
            pm = person_masks(frames, range(a, b + 1), fd.rstrip('/') + '_persona')
            y_min = int(h * t.get('y_min', 0.55))
            for f in range(a, b + 1):
                hsv = cv2.cvtColor(frames[f], cv2.COLOR_BGR2HSV)
                dark = ((hsv[..., 2] < 95).astype(np.uint8) * 255)
                dark[:y_min] = 0
                enc = cv2.bitwise_or(dark, pm[f]); enc[:y_min] = 0
                enc = cv2.morphologyEx(enc, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
                # el borde inferior cuenta como tapete (el tapete sale de cuadro por abajo)
                pad = cv2.copyMakeBorder(enc, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
                pad[-1, :] = 255
                ff = pad.copy(); msk = np.zeros((pad.shape[0] + 2, pad.shape[1] + 2), np.uint8)
                cv2.floodFill(ff, msk, (0, 0), 128)
                holes = ((ff[1:-1, 1:-1] == 0)).astype(np.uint8) * 255          # no alcanzado desde afuera y no tapete
                light = (hsv[..., 2] > 100).astype(np.uint8) * 255
                m = cv2.bitwise_and(cv2.bitwise_and(holes, light), cv2.bitwise_not(pm[f]))
                n, lab, st, _ = cv2.connectedComponentsWithStats(m)
                keep = np.zeros_like(m)
                for i in range(1, n):
                    if 15 <= st[i, cv2.CC_STAT_AREA] <= t.get('max_letter', 9000):
                        keep[lab == i] = 255
                m = cv2.dilate(keep, np.ones((3, 3), np.uint8), iterations=2)
                m = cv2.bitwise_and(m, cv2.bitwise_not(pm[f]))
                out[f] = cv2.inpaint(out[f], m, 5, cv2.INPAINT_TELEA)
            print(t['name'], 'texto de alfombra borrado en cuadros', a + 1, '-', b + 1)
            continue

        # ---- tipo logo ----
        f0 = t['ref_frame'] - 1
        lm = letters_mask(frames[f0], t['region'], t['polarity'], t.get('min_area', 40))
        pts = cv2.findNonZero(lm)
        q0 = order_quad(cv2.boxPoints(cv2.minAreaRect(pts)))
        if t.get('quad'):                                   # cuadrilátero manual opcional
            q0 = np.array(t['quad'], np.float32)
        reg = np.zeros((h, w), np.uint8)
        cv2.fillPoly(reg, [np.array(t.get('track_poly', q0), np.int32)], 255)
        Hs = {**track(grays, f0, reg, -1), **track(grays, f0, reg, +1)}
        print(t['name'], 'seguido en cuadros', min(Hs) + 1, '-', max(Hs) + 1)
        logo = cv2.imread(t['logo'], cv2.IMREAD_UNCHANGED)
        ql = scale_quad(q0, *t.get('logo_scale', [1.0, 1.0]))          # zona donde va el logo nuevo
        qw = np.linalg.norm(ql[1] - ql[0]); qh = np.linalg.norm(ql[3] - ql[0])
        limg, la, glow, col = render_logo(logo, qw, qh, t.get('style', 'neon'), t.get('color', [229, 0, 16]),
                                          t.get('logo_fill', 0.95), t.get('valign', 0.5))
        Hc_, Wc_ = la.shape
        src = np.array([[0, 0], [Wc_, 0], [Wc_, Hc_], [0, Hc_]], np.float32)
        Hlogo = cv2.getPerspectiveTransform(src, ql)
        lm_d = cv2.dilate(lm, np.ones((3, 3), np.uint8), iterations=t.get('erase_dilate', 3))
        for f, Hf in sorted(Hs.items()):
            m = cv2.warpPerspective(lm_d, Hf, (w, h))
            m = (m > 40).astype(np.uint8) * 255
            if t.get('fill') == 'median':
                # rellena las letras con el color típico del fondo que las rodea (toldo/pared) y suaviza el borde
                ring = cv2.subtract(cv2.dilate(m, np.ones((15, 15), np.uint8)), m)
                pix = out[f][ring > 0]
                if t['polarity'] == 'light':
                    v = pix.max(1); pix = pix[v < np.percentile(v, 60)]
                col_bg = np.median(pix, 0) if len(pix) else np.array([20, 20, 20])
                filled = out[f].copy(); filled[m > 0] = col_bg
                filled = cv2.inpaint(filled, cv2.subtract(cv2.dilate(m, np.ones((3, 3), np.uint8)), cv2.erode(m, np.ones((5, 5), np.uint8))), 3, cv2.INPAINT_TELEA)
                feather = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 2.0)[..., None]
                noise = np.random.default_rng(f).normal(0, 2.5, filled.shape)
                img = np.clip(out[f] * (1 - feather) + (filled + noise) * feather, 0, 255).astype(np.uint8)
            else:
                img = cv2.inpaint(out[f], m, 7, cv2.INPAINT_TELEA)
            Hm = Hf @ Hlogo
            wa = cv2.GaussianBlur(cv2.warpPerspective(la, Hm, (w, h)), (0, 0), 0.6)
            wg = cv2.warpPerspective(glow, Hm, (w, h))
            wi = cv2.GaussianBlur(cv2.warpPerspective(limg, Hm, (w, h)), (0, 0), 0.6)
            base = img.astype(np.float32) + wg[..., None] * col * t.get('glow', 0.5)
            op = t.get('opacity', 1.0)
            base = base * (1 - wa[..., None] * op) + wi * (wa[..., None] * op)
            out[f] = np.clip(base, 0, 255).astype(np.uint8)
            if dbg_dir and f in (f0, max(Hs), (f0 + max(Hs)) // 2):
                d = out[f].copy()
                pass
                os.makedirs(dbg_dir, exist_ok=True); cv2.imwrite(os.path.join(dbg_dir, f'{t["name"]}_{f + 1:04d}.png'), d)

    od = fd.rstrip('/') + '_out'; os.makedirs(od, exist_ok=True)
    for i, f in enumerate(out):
        cv2.imwrite(os.path.join(od, f'{i + 1:04d}.png'), f)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(cfg.get('fps', 24)), '-i', os.path.join(od, '%04d.png'),
                    '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', cfg['output']], check=True)
    print('listo', cfg['output'])

if __name__ == '__main__':
    main(sys.argv[1])
