// Orden de intentos para generar el resumen del post de LinkedIn, separado del
// SDK para poder probarlo sin red ni dependencias.
//
// Por que existe: entre el 2026-09-14 y el 2026-10-06, 4 de 18 publicaciones se
// quedaron sin post porque Gemini devolvio 503 ("high demand") en los tres
// modelos, uno detras de otro y en segundos. Un pico de demanda dura minutos,
// asi que primero se reintenta el mismo modelo con espera; solo despues se pasa
// al siguiente, y como ultimo recurso a un proveedor de otra familia.

const MIN_SUMMARY_LENGTH = 50;

// 503/429 y fallos de red son transitorios; un 400 o una clave invalida no
// mejoran esperando.
export function isRetryable(error) {
  const msg = String(error?.message ?? error);
  return /\b(503|429|500|502|504)\b|unavailable|overloaded|high demand|resource_exhausted|fetch failed|ECONNRESET|ETIMEDOUT/i.test(msg);
}

async function attempt(name, call) {
  console.log(`🤖 Attempting summary generation with ${name}...`);
  const summary = String((await call()) ?? '').trim();
  if (summary.length < MIN_SUMMARY_LENGTH) {
    throw new Error('Generated summary too short');
  }
  console.log(`✅ Summary generated with ${name}`);
  console.log(`   Length: ${summary.length} characters`);
  console.log(`   Words: ~${summary.split(/\s+/).length} words`);
  return summary;
}

/**
 * @param {object} p
 * @param {string[]} p.models - modelos de Gemini en orden de preferencia
 * @param {(model: string) => Promise<string>} p.callModel
 * @param {{name: string, call: () => Promise<string>}} [p.lastResort]
 * @param {number[]} [p.delaysMs] - espera antes de cada reintento del mismo modelo
 * @param {(ms: number) => Promise<void>} [p.sleep]
 */
export async function generateWithFallback({
  models,
  callModel,
  lastResort,
  delaysMs = [20_000, 60_000],
  sleep = (ms) => new Promise((r) => setTimeout(r, ms)),
}) {
  const failures = [];

  for (const model of models) {
    for (let i = 0; i <= delaysMs.length; i++) {
      try {
        return await attempt(model, () => callModel(model));
      } catch (error) {
        console.warn(`⚠️  ${model} failed: ${error.message}`);
        failures.push(`${model}: ${error.message}`);
        if (i === delaysMs.length || !isRetryable(error)) break;
        console.log(`   Retrying ${model} in ${Math.round(delaysMs[i] / 1000)}s...`);
        await sleep(delaysMs[i]);
      }
    }
  }

  if (lastResort) {
    console.log(`Falling back to ${lastResort.name}...`);
    try {
      return await attempt(lastResort.name, lastResort.call);
    } catch (error) {
      console.warn(`⚠️  ${lastResort.name} failed: ${error.message}`);
      failures.push(`${lastResort.name}: ${error.message}`);
    }
  }

  throw new Error(`All summary providers failed. ${failures.join(' | ')}`);
}
