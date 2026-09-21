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
import { generate, listFlashModels } from './gemini.mjs';
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

async function run() {
  const flash = await listFlashModels();
  const wanted = ['gemini-3-flash-preview'];
  wanted.push(...flash.filter(m => !wanted.includes(m)).slice(0, 1));
  console.log('Modelos a probar:', wanted.join(', '));
  console.log(`Celdas: ${ARTICLES.length} articulos x ${Object.keys(PROMPTS).length} prompts x ${wanted.length} modelos x ${REPS} tiradas\n`);

  const rows = [];
  for (const art of ARTICLES) {
    const { data, content } = matter(readFileSync(art.path, 'utf-8'));
    const params = { title: data.title, description: data.description, tags: data.tags || [], content };

    for (const [pname, build] of Object.entries(PROMPTS)) {
      for (const modelName of wanted) {
        for (let rep = 1; rep <= REPS; rep++) {
          const r = await generate(modelName, build(params));
          const text = r.text || '';
          const flags = Object.fromEntries(Object.entries(SCORES).map(([k, f]) => [k, text ? f(text) : null]));
          const comp = text ? componentes(text, art.components) : null;
          const lista = text ? listaInventada(text) : null;
          rows.push({ art: art.key, prompt: pname, model: modelName, rep, err: r.err || '', flags, comp, lista, text });

          console.log('='.repeat(78));
          console.log(`${art.key} | ${pname} | ${modelName} | rep ${rep} | ${r.secs}s${r.err ? ' | ERROR: ' + r.err : ''}`);
          if (text) {
            console.log('--- apertura:', (text.split('\n')[0] || '').slice(0, 170));
            if (comp) console.log(`--- componentes: atribuidos=${comp.atribuidos}/${comp.total} mencionados=${comp.mencionados}/${comp.total} amontonados_en_una_frase=${comp.amontonados}`);
            console.log(`--- lista=${lista} apertura_cortada=${flags.apertura_cortada} definicion=${flags.apertura_definicion} muro=${flags.muro_de_texto} pregunta_cierre=${flags.pregunta_en_el_cierre}`);
          }
          await new Promise(res => setTimeout(res, 1200));
        }
      }
    }
  }

  const ok = rows.filter(r => r.text);
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
