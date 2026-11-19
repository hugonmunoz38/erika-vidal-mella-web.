// Renderiza cuadros PNG de escena.html con Playwright.
// Uso: node render.js trabajo.json
// trabajo.json = { "store": "beta", "fmt": "4x5" | "9x16", "frames": [ { "out": "ruta.png", "state": {...} }, ... ] }
// La configuración de la tienda se lee de tiendas/<store>/config.json y se inyecta como window.STORE.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const store = JSON.parse(fs.readFileSync(path.resolve(__dirname, '..', 'tiendas', job.store, 'config.json'), 'utf8'));
  const H = job.fmt === '9x16' ? 1920 : 1350;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: H }, deviceScaleFactor: 1 });
  await page.addInitScript(cfg => { window.STORE = cfg; }, store);
  page.on('pageerror', e => { console.error('Error en la página:', e.message); process.exitCode = 1; });
  await page.goto('file://' + path.resolve(__dirname, 'escena.html') + '?fmt=' + job.fmt);
  await page.evaluate(() => window.ready);
  let n = 0;
  for (const f of job.frames) {
    fs.mkdirSync(path.dirname(f.out), { recursive: true });
    await page.evaluate(s => window.setState(s), f.state);
    await page.locator('#stage').screenshot({ path: f.out, omitBackground: true });
    if (++n % 30 === 0) console.log(`${n}/${job.frames.length}`);
  }
  await browser.close();
  console.log('ok', n);
})();
