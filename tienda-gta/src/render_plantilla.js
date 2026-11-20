// Renderiza cuadro a cuadro una plantilla HTML con window.setT(t).
// Uso: node render_plantilla.js <plantilla.html> <config.json> <9x16|4x5> <carpeta_salida> [fps] [solo_t]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const [tpl, cfgPath, fmt, outDir, fpsArg, onlyT] = process.argv.slice(2);
  const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const fps = Number(fpsArg || 30), H = fmt === '9x16' ? 1920 : 1350;
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: H }, deviceScaleFactor: 1 });
  await page.addInitScript(c => { window.CFG = c; }, cfg);
  page.on('pageerror', e => { console.error('Error en la página:', e.message); process.exitCode = 1; });
  await page.goto('file://' + path.resolve(__dirname, tpl) + '?fmt=' + fmt);
  await page.evaluate(() => window.ready);
  const times = onlyT ? onlyT.split(',').map(Number) : Array.from({ length: Math.round(cfg.timeline.dur * fps) }, (_, k) => k / fps);
  for (let k = 0; k < times.length; k++) {
    await page.evaluate(t => window.setT(t), times[k]);
    await page.locator('#stage').screenshot({ path: path.join(outDir, `v_${String(k).padStart(4, '0')}.png`) });
    if ((k + 1) % 60 === 0) console.log(`${k + 1}/${times.length}`);
  }
  await browser.close();
  console.log('ok', times.length);
})();
