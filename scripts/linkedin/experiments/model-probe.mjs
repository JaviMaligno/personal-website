/**
 * Por que fallan los flash mas nuevos: 404 (no existe para esta version de API),
 * 403 (permiso/tier), 429 (cupo) o un error de forma de peticion del SDK viejo.
 *
 * Llama al REST directamente, sin SDK, y enseña el cuerpo del error entero.
 */
const KEY = process.env.GEMINI_API_KEY;
const CANDIDATOS = [
  'gemini-3.8-flash',
  'gemini-3.7-flash',
  'gemini-3.6-flash',
  'gemini-3.5-flash',
  'gemini-3-flash-preview',
  'gemini-flash-latest',
];

const body = JSON.stringify({
  contents: [{ role: 'user', parts: [{ text: 'Reply with the single word: ok' }] }],
});

async function probe(version, model) {
  const url = `https://generativelanguage.googleapis.com/${version}/models/${model}:generateContent?key=${KEY}`;
  const t0 = Date.now();
  try {
    const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body });
    const txt = await r.text();
    const secs = ((Date.now() - t0) / 1000).toFixed(1);
    let detail = '';
    try {
      const j = JSON.parse(txt);
      if (j.error) detail = `${j.error.status || ''} ${j.error.message || ''}`.trim();
      else detail = 'OK: ' + (j.candidates?.[0]?.content?.parts?.[0]?.text || '').trim().slice(0, 40);
    } catch { detail = txt.slice(0, 160); }
    return `${version.padEnd(6)} HTTP ${r.status} ${secs}s  ${detail.slice(0, 220)}`;
  } catch (e) {
    return `${version.padEnd(6)} EXCEPCION ${e.message.slice(0, 160)}`;
  }
}

const meta = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${KEY}`)
  .then(r => r.json()).catch(() => ({}));
const byName = Object.fromEntries((meta.models || []).map(m => [m.name.replace('models/', ''), m]));

for (const m of CANDIDATOS) {
  console.log('='.repeat(78));
  const info = byName[m];
  console.log(m, info ? `— listado: si | ${info.displayName || ''} | metodos: ${(info.supportedGenerationMethods || []).join(',')}` : '— listado: NO');
  if (info?.description) console.log('   ', info.description.slice(0, 180));
  console.log('   ', await probe('v1beta', m));
  console.log('   ', await probe('v1', m));
}

console.log('\n' + '='.repeat(78));
console.log("Nota: produccion llama con @google/generative-ai 0.21.0, que oculta el");
console.log("status HTTP. Esta sonda va por REST justo para no perderlo.");
