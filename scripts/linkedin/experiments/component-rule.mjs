/**
 * ¿Sirve la regla de componentes? Mismo prompt con y sin ella.
 *
 * Motivo: frontend-backend-agentic-core se publico el 2026-09-21 nombrando sus
 * tres bloques en una sola frase ("the frontend, the application backend, and
 * the agentic engine") y explicando la responsabilidad de uno solo. El
 * articulo dedica una figura a separarlos. La regla nueva pide una linea por
 * componente con su responsabilidad.
 *
 * El riesgo que hay que medir no es solo si la regla funciona donde toca, sino
 * si dispara listas donde NO toca. De ahi los dos articulos de control, que no
 * separan ningun conjunto: si la regla les mete una lista, sale mas cara de lo
 * que vale.
 *
 * Uso (en CI, donde vive GEMINI_API_KEY):
 *   node scripts/linkedin/experiments/component-rule.mjs
 */
import { readFileSync } from 'fs';
import matter from 'gray-matter';
import { generate } from './gemini.mjs';
import { buildSummaryPrompt } from '../prompt.js';
import { SCORES, componentes, listaInventada } from './scores.mjs';

// Los nombres salen del articulo, no de lo que yo llamaria a cada bloque.
const ARTICLES = [
  {
    key: 'tres-bloques', path: 'src/content/blog/en/frontend-backend-agentic-core.md',
    components: [
      { name: 'frontend', re: /frontend/i },
      { name: 'application backend', re: /application backend|app backend|the backend/i },
      { name: 'agentic engine', re: /agentic engine|the engine/i },
    ],
  },
  {
    key: 'cinco-capas', path: 'src/content/blog/en/blaming-the-model.md',
    components: [
      { name: 'input data', re: /input data/i },
      { name: 'prompt & rules', re: /prompt(s)?( ?(&|and) ?rules)?|rules/i },
      { name: 'tools & retrieval', re: /tools|retrieval/i },
      { name: 'harness', re: /harness/i },
      { name: 'model sampling', re: /sampling/i },
    ],
  },
  {
    key: 'tres-componentes', path: 'src/content/blog/en/recursive-language-models-prototype.md',
    components: [
      { name: 'orchestrator', re: /orchestrator/i },
      { name: 'python environment', re: /python (environment|env)/i },
      { name: 'LLM API', re: /LLM API|Azure OpenAI|model API/i },
    ],
  },
  // Control: articulos que no separan ningun conjunto de componentes.
  { key: 'control-mates', path: 'src/content/blog/en/navier-stokes-blows-up.md', components: [] },
  { key: 'control-negocio', path: 'src/content/blog/en/stop-being-the-cable.md', components: [] },
];

const PROMPTS = {
  sin_regla: p => buildSummaryPrompt(p, { componentRule: false }),
  con_regla: p => buildSummaryPrompt(p, { componentRule: true }),
};

const REPS = 2;  // una tirada por celda no distingue la regla del azar del muestreo

// Fijos, y no "los mas nuevos que ofrezca la API": la primera tirada de este
// experimento (2026-09-21) dejo que el script eligiera y cogio gemini-3.8-flash,
// que es exactamente el que el README documenta desde el 2026-09-09 como el que
// NO aguanta un articulo entero — 503 y 429 en todas sus celdas. Estos dos son
// los que usa produccion.
const MODELOS = ['gemini-3-flash-preview', 'gemini-3.5-flash'];

/** PRNG con semilla: el orden cambia, pero el mismo run se puede repetir. */
function barajar(xs, semilla = 42) {
  let s = semilla;
  const r = () => (s = (s * 1103515245 + 12345) % 2147483648) / 2147483648;
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

async function run() {
  console.log('Modelos:', MODELOS.join(', '));
  // Las celdas van EMPAREJADAS (sin_regla y con_regla seguidas, mismo articulo,
  // modelo y tirada) y en orden barajado. En la primera tirada el orden era
  // secuencial, el cupo se agoto a mitad y se llevo por delante justo los dos
  // articulos de control, que iban al final: el brazo que medía el riesgo de la
  // regla se quedo en n=1. Emparejado, un corte se lleva los dos brazos a la
  // vez y el par entero se descarta, en vez de sesgar la comparacion.
  const pares = [];
  for (const art of ARTICLES)
    for (const modelName of MODELOS)
      for (let rep = 1; rep <= REPS; rep++)
        pares.push({ art, modelName, rep });
  const orden = barajar(pares);
  console.log(`Pares: ${orden.length} (${ARTICLES.length} articulos x ${MODELOS.length} modelos x ${REPS} tiradas), 2 llamadas cada uno\n`);

  const rows = [];
  for (const { art, modelName, rep } of orden) {
    const { data, content } = matter(readFileSync(art.path, 'utf-8'));
    const params = { title: data.title, description: data.description, tags: data.tags || [], content };
    const par = [];

    for (const [pname, build] of Object.entries(PROMPTS)) {
      const r = await generate(modelName, build(params));
      const text = r.text || '';
      const flags = Object.fromEntries(Object.entries(SCORES).map(([k, f]) => [k, text ? f(text) : null]));
      const comp = text ? componentes(text, art.components) : null;
      const lista = text ? listaInventada(text) : null;
      par.push({ art: art.key, prompt: pname, model: modelName, rep, err: r.err || '', flags, comp, lista, text });

      console.log('='.repeat(78));
      console.log(`${art.key} | ${pname} | ${modelName} | rep ${rep} | ${r.secs}s${r.err ? ' | ERROR: ' + r.err : ''}`);
      if (text) {
        console.log('--- apertura:', (text.split('\n')[0] || '').slice(0, 170));
        if (comp) console.log(`--- componentes: atribuidos=${comp.atribuidos}/${comp.total} mencionados=${comp.mencionados}/${comp.total} amontonados_en_una_frase=${comp.amontonados}`);
        console.log(`--- lista=${lista} apertura_cortada=${flags.apertura_cortada} definicion=${flags.apertura_definicion} muro=${flags.muro_de_texto} pregunta_cierre=${flags.pregunta_en_el_cierre}`);
      }
      await new Promise(res => setTimeout(res, 1200));
    }

    // Solo cuentan los pares donde respondieron los dos brazos.
    const completo = par.every(x => x.text);
    if (!completo) console.log(`--- PAR DESCARTADO (${art.key} | ${modelName} | rep ${rep}): falto un brazo`);
    par.forEach(x => rows.push({ ...x, completo }));
  }

  const ok = rows.filter(r => r.text && r.completo);
  const descartados = new Set(rows.filter(r => !r.completo).map(r => `${r.art}|${r.model}|${r.rep}`));
  console.log(`\n\nPares completos: ${ok.length / 2} de ${orden.length}. Descartados por error de la API: ${descartados.size}.`);
  console.log('\n\n' + '#'.repeat(78));
  console.log('RESUMEN — articulos que SI separan componentes');
  console.log('#'.repeat(78));
  for (const pname of Object.keys(PROMPTS)) {
    const r = ok.filter(x => x.prompt === pname && x.comp);
    if (!r.length) continue;
    const atr = r.reduce((a, x) => a + x.comp.atribuidos, 0);
    const tot = r.reduce((a, x) => a + x.comp.total, 0);
    const todos = r.filter(x => x.comp.atribuidos === x.comp.total).length;
    console.log(`${pname.padEnd(10)} responsabilidad propia=${atr}/${tot} (${Math.round(100 * atr / tot)}%)  posts con TODOS atribuidos=${todos}/${r.length}  amontonados=${r.filter(x => x.comp.amontonados).length}/${r.length}`);
  }
  console.log('\nPor articulo:');
  for (const art of ARTICLES.filter(a => a.components.length)) {
    for (const pname of Object.keys(PROMPTS)) {
      const r = ok.filter(x => x.art === art.key && x.prompt === pname);
      if (!r.length) continue;
      console.log(`  ${art.key.padEnd(18)} ${pname.padEnd(10)} atribuidos=${r.map(x => `${x.comp.atribuidos}/${x.comp.total}`).join(' ')}`);
    }
  }

  console.log('\n' + '#'.repeat(78));
  console.log('RESUMEN — controles (la regla no deberia tocarlos)');
  console.log('#'.repeat(78));
  for (const pname of Object.keys(PROMPTS)) {
    const r = ok.filter(x => x.prompt === pname && !x.comp);
    if (!r.length) continue;
    console.log(`${pname.padEnd(10)} lista_inventada=${r.filter(x => x.lista).length}/${r.length}`);
  }

  console.log('\n' + '#'.repeat(78));
  console.log('LO YA GANADO — no se puede perder por meter la regla');
  console.log('#'.repeat(78));
  for (const pname of Object.keys(PROMPTS)) {
    const r = ok.filter(x => x.prompt === pname);
    const pct = k => `${r.filter(x => x.flags[k]).length}/${r.length}`;
    console.log(`${pname.padEnd(10)} apertura_cortada=${pct('apertura_cortada')} definicion=${pct('apertura_definicion')} muro=${pct('muro_de_texto')} pregunta_cierre=${pct('pregunta_en_el_cierre')} formula=${pct('formula_gancho')} yo_inventado=${pct('primera_persona_inventada')}`);
  }

  console.log('\n\nTEXTOS COMPLETOS (la decision se toma leyendo, no contando):');
  for (const row of ok) {
    console.log('\n' + '-'.repeat(78));
    console.log(`${row.art} | ${row.prompt} | ${row.model} | rep ${row.rep}`);
    console.log('-'.repeat(78));
    console.log(row.text);
  }
}

run().catch(e => { console.error('fallo:', e); process.exit(1); });
