const crypto = require('crypto');

const DB_URL = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const DB_TOKEN = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
const KEY = 'horas-bloqueadas';
const HORAS = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00'];

async function redis(cmd) {
  const r = await fetch(DB_URL, {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + DB_TOKEN },
    body: JSON.stringify(cmd),
  });
  if (!r.ok) throw new Error('redis ' + r.status);
  return (await r.json()).result;
}

const sha = (s) => crypto.createHash('sha256').update(String(s)).digest();
function claveOk(c) {
  const real = process.env.ADMIN_CLAVE;
  return !!real && crypto.timingSafeEqual(sha(c || ''), sha(real));
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  try {
    if (req.method === 'GET') {
      const v = DB_URL && DB_TOKEN ? await redis(['GET', KEY]) : null;
      return res.status(200).json({ blocked: v ? JSON.parse(v) : {} });
    }
    if (req.method !== 'POST') return res.status(405).end();
    const b = req.body || {};
    if (!claveOk(b.clave)) {
      await new Promise((r) => setTimeout(r, 800));
      return res.status(401).json({ error: 'clave' });
    }
    if (b.accion === 'login') return res.status(200).json({ ok: true });
    if (!DB_URL || !DB_TOKEN) return res.status(500).json({ error: 'sin base de datos' });
    const limpio = {};
    for (const [dia, hs] of Object.entries(b.blocked || {})) {
      if (/^\d{4}-\d{2}-\d{2}$/.test(dia) && Array.isArray(hs)) {
        const ok = [...new Set(hs.filter((h) => HORAS.includes(h)))];
        if (ok.length) limpio[dia] = ok;
      }
    }
    await redis(['SET', KEY, JSON.stringify(limpio)]);
    return res.status(200).json({ ok: true });
  } catch (e) {
    return res.status(500).json({ error: 'servidor' });
  }
};
