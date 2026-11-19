// Renderiza cuadros PNG de escena.html con Playwright.
// Uso: node render.js trabajo.json
// trabajo.json = { "fmt": "4x5" | "9x16", "frames": [ { "out": "ruta.png", "state": {...} }, ... ] }
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const H = job.fmt === '9x16' ? 1920 : 1350;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: H }, deviceScaleFactor: 1 });
  const url = 'file://' + path.resolve(__dirname, 'escena.html') + '?fmt=' + job.fmt;
  await page.goto(url);
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
