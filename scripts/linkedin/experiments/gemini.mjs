/**
 * Llamada a Gemini por REST, con reintentos y con el codigo HTTP a la vista.
 *
 * Por que no el SDK: `@google/generative-ai` 0.21.0 (el que usa produccion)
 * envuelve cualquier respuesta no-2xx en un generico "Error fetching from
 * https://...", sin status ni cuerpo. El 2026-09-09 eso hizo creer que
 * gemini-3.8-flash no era llamable con nuestra clave, cuando lo que devolvia
 * era 503 UNAVAILABLE por saturacion y 429 RESOURCE_EXHAUSTED por cupo. Si un
 * experimento no puede distinguir "no tengo permiso" de "vuelve luego", el
 * experimento miente.
 */
const BASE = 'https://generativelanguage.googleapis.com';

/** Modelos flash que la API dice que existen ahora, ordenados de nuevo a viejo. */
export async function listFlashModels({ incluirLite = false } = {}) {
  const r = await fetch(`${BASE}/v1beta/models?key=${process.env.GEMINI_API_KEY}`);
  const j = await r.json().catch(() => ({}));
  const rank = m => parseFloat((m.match(/gemini-(\d+(?:\.\d+)?)/) || [0, 0])[1]) || 0;
  return (j.models || [])
    .filter(m => (m.supportedGenerationMethods || []).includes('generateContent'))
    .map(m => m.name.replace('models/', ''))
    .filter(m => /flash/.test(m) && !/tts|image|live|thinking-exp/.test(m))
    .filter(m => incluirLite || !/lite/.test(m))
    .sort((a, b) => rank(b) - rank(a));
}

/**
 * Genera texto. Devuelve { text, secs, intento } o { err, status, secs, intento }.
 * `err` trae el status HTTP y el codigo de Google, que es lo que permite
 * separar cupo (429) de saturacion (503) de modelo inexistente (404).
 */
export async function generate(model, prompt, { intentos = 3, version = 'v1beta', esperaMs = 4000 } = {}) {
  const url = `${BASE}/${version}/models/${model}:generateContent?key=${process.env.GEMINI_API_KEY}`;
  const body = JSON.stringify({ contents: [{ role: 'user', parts: [{ text: prompt }] }] });
  for (let i = 1; i <= intentos; i++) {
    const t0 = Date.now();
    let r, j;
    try {
      r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body });
      j = await r.json().catch(() => ({}));
    } catch (e) {
      if (i === intentos) return { err: `EXCEPCION ${e.message.slice(0, 120)}`, status: 0, secs: '0.0', intento: i };
      await new Promise(res => setTimeout(res, esperaMs * i));
      continue;
    }
    const secs = ((Date.now() - t0) / 1000).toFixed(1);
    if (r.ok) {
      return { text: (j.candidates?.[0]?.content?.parts?.[0]?.text || '').trim(), secs, intento: i };
    }
    const detalle = `${r.status} ${j.error?.status || ''} ${(j.error?.message || '').slice(0, 100)}`.trim();
    // 429 y 403 no mejoran reintentando en segundos; 503 si.
    if (i === intentos || r.status === 403 || r.status === 404) {
      return { err: detalle, status: r.status, secs, intento: i };
    }
    await new Promise(res => setTimeout(res, esperaMs * i));
  }
}
