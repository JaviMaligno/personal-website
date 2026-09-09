/**
 * Matriz modelo x prompt x articulo para el generador de posts de LinkedIn.
 *
 * Motivo: todos los posts automaticos abren igual ("The hardest part of X
 * isn't Y — it's Z"). El prompt actual trae ese gancho como EJEMPLO, asi que
 * hay que separar cuanta culpa es del prompt y cuanta del modelo.
 *
 * Uso (en CI, donde vive GEMINI_API_KEY):
 *   node scripts/linkedin/experiments/summary-matrix.mjs
 */
import { readFileSync } from 'fs';
import matter from 'gray-matter';
import { generate, listFlashModels } from './gemini.mjs';

const ARTICLES = [
  { key: 'matematicas', path: 'src/content/blog/en/navier-stokes-blows-up.md',
    finding: /vortex|smooth force|C[oó]rdoba|Fefferman|Mart[ií]nez-Zoroa|singularit/i },
  { key: 'agentes', path: 'src/content/blog/en/what-agents-say-to-each-other.md',
    finding: /agent|message|transcript|protocol|handoff/i },
  { key: 'negocio', path: 'src/content/blog/en/stop-being-the-cable.md',
    finding: /cable|paste|copy|between|manual|tool/i },
];

const PROMPTS = {
  // P0: el prompt en produccion, copiado literal de generate-summary.js
  P0_actual: ({ title, description, tags, content }) => `You are a LinkedIn content strategist creating engaging posts for AI/tech professionals and CTOs.

BLOG DETAILS:
Title: ${title}
Description: ${description}
Tags: ${tags.join(', ')}

FULL CONTENT:
${content.substring(0, 4000)}

REQUIREMENTS:
- Write 2-3 concise paragraphs (max 400 words)
- Start with a compelling hook that grabs attention (problem, insight, or question)
- Focus on the "why" and key takeaways, not just implementation details
- Speak to technical leaders: CTOs, engineering leads, AI architects
- Use professional but conversational tone
- Include a subtle call-to-action at the end (e.g., "What's your experience with...", "How are you handling...")
- Write in first person (I/my/me) as Javier Aguilar, AI Agent Architect
- DO NOT include hashtags (will be added separately)
- DO NOT include the blog URL (will be added separately)
- DO NOT use emojis (except sparingly if they enhance meaning)

OUTPUT FORMAT:
Plain text only, no markdown formatting.

Example opening hooks:
- "I spent 3 weeks debugging LinkedIn's API before realizing..."
- "Most teams waste hours on manual deployments. Here's why..."
- "The hardest part of AI automation isn't the code—it's..."`,

  // P1: el mismo, sin el bloque de ganchos de ejemplo. Aisla la contaminacion.
  P1_sin_ganchos: ({ title, description, tags, content }) => `You are a LinkedIn content strategist creating engaging posts for AI/tech professionals and CTOs.

BLOG DETAILS:
Title: ${title}
Description: ${description}
Tags: ${tags.join(', ')}

FULL CONTENT:
${content.substring(0, 4000)}

REQUIREMENTS:
- Write 2-3 concise paragraphs (max 400 words)
- Start with a compelling hook that grabs attention (problem, insight, or question)
- Focus on the "why" and key takeaways, not just implementation details
- Speak to technical leaders: CTOs, engineering leads, AI architects
- Use professional but conversational tone
- Include a subtle call-to-action at the end (e.g., "What's your experience with...", "How are you handling...")
- Write in first person (I/my/me) as Javier Aguilar, AI Agent Architect
- DO NOT include hashtags (will be added separately)
- DO NOT include the blog URL (will be added separately)
- DO NOT use emojis (except sparingly if they enhance meaning)

OUTPUT FORMAT:
Plain text only, no markdown formatting.`,

  // P2: reescrito. El articulo manda; nada de audiencia impuesta, formula ni CTA.
  P2_reescrito: ({ title, description, tags, content }) => `You are writing a LinkedIn post for Javier Aguilar about an article he wrote. Write as him, first person.

ARTICLE
Title: ${title}
Description: ${description}
Tags: ${tags.join(', ')}

FULL CONTENT:
${content.substring(0, 4000)}

WHAT THE POST MUST DO
- Lead with the article's own subject and its most concrete finding. If the article is about mathematics, the post is about mathematics; if it is about a measurement, lead with the number.
- Carry at least two specifics from the article: a number, a name, a mechanism. Never a claim so general it would fit a different article.
- Keep the author's judgment exactly as the article states it. Do NOT invent personal history, conversions or opinions — no "I used to think", no "this proved me wrong", no "I spent three weeks". If the article does not say it, he did not say it.
- Assume a reader who knows the field. Do not address CTOs, leaders or "those of us building X" as a group.

WHAT THE POST MUST NOT DO
- No opening formula. Never start with "The hardest part of X isn't Y, it's Z" or any variant of it.
- No closing question, no call to action, no "what's your experience", no "how are you thinking about".
- No hashtags, no URL, no markdown, no emojis.

LENGTH
Two or three short paragraphs, under 300 words. End on a statement.`,
};

const N = '(a|one|two|three|four|five|six|seven|\d+)';
const SCORES = {
  // las tres familias de gancho que el prompt actual da como EJEMPLO
  formula_gancho: t => new RegExp(
    "(isn'?t (the|about) [^.]{0,45}(—|-|;|,) ?it'?s|hardest part|most (fascinating|interesting) thing about|real story behind)"
    + "|^I spent " + N + " (day|days|week|weeks|hour|hours)"
    + "|^Most (teams|engineers|engineering leaders|companies|people)", 'i'
  ).test(t.split('\n')[0] || ''),
  primera_persona_inventada: t => new RegExp(
    "I used to think|proved me wrong|I've always|I was wrong|my first question wasn'?t"
    + "|I spent " + N + " (day|days|week|weeks)", 'i'
  ).test(t),
  acaba_en_pregunta: t => /\?\s*$/.test(t.trim()),
  llamada_a_la_accion: t => /what'?s your experience|how are you (thinking|handling|approaching)|what do you think|curious how/i.test(t),
};

async function run() {
  const flash = await listFlashModels();
  console.log('Modelos flash (sin lite), de nuevo a viejo:', flash.join(', ') || '(ninguno)');

  // el de produccion + los tres mas nuevos que ofrezca la API
  const wanted = ['gemini-3-flash-preview'];
  wanted.push(...flash.filter(m => !wanted.includes(m)).slice(0, 3));
  console.log('Modelos a probar:', wanted.join(', '), '\n');

  const rows = [];
  for (const art of ARTICLES) {
    const raw = readFileSync(art.path, 'utf-8');
    const { data, content } = matter(raw);
    const params = { title: data.title, description: data.description, tags: data.tags || [], content };

    for (const [pname, build] of Object.entries(PROMPTS).filter(([k]) => !k.startsWith('_'))) {
      for (const modelName of wanted) {
        const r = await generate(modelName, build(params));
        const text = r.text || '';
        const err = r.err || '';
        const secs = r.secs;
        const flags = Object.fromEntries(Object.entries(SCORES).map(([k, f]) => [k, text ? f(text) : null]));
        const specific = text ? art.finding.test(text) : null;
        rows.push({ art: art.key, prompt: pname, model: modelName, err, secs, flags, specific, text });

        console.log('='.repeat(78));
        console.log(`${art.key} | ${pname} | ${modelName} | ${secs}s${err ? ' | ERROR: ' + err : ''}`);
        if (text) {
          console.log('--- apertura:', (text.split('\n')[0] || '').slice(0, 160));
          console.log('--- cierre  :', (text.trim().split('\n').filter(Boolean).pop() || '').slice(0, 160));
          console.log(`--- formula=${flags.formula_gancho} yo_inventado=${flags.primera_persona_inventada} pregunta=${flags.acaba_en_pregunta} cta=${flags.llamada_a_la_accion} concreto=${specific}`);
        }
        await new Promise(r => setTimeout(r, 1200));
      }
    }
  }

  console.log('\n\n' + '#'.repeat(78));
  console.log('RESUMEN (de 9 combinaciones por prompt: 3 articulos x 3-4 modelos)');
  console.log('#'.repeat(78));
  for (const pname of Object.keys(PROMPTS).filter(k => !k.startsWith('_'))) {
    const r = rows.filter(x => x.prompt === pname && !x.err);
    const pct = k => `${r.filter(x => x.flags[k]).length}/${r.length}`;
    console.log(`${pname.padEnd(16)} formula=${pct('formula_gancho')} yo_inventado=${pct('primera_persona_inventada')} pregunta=${pct('acaba_en_pregunta')} cta=${pct('llamada_a_la_accion')} concreto=${r.filter(x => x.specific).length}/${r.length}`);
  }
  console.log('\nPor modelo (solo con el prompt actual P0):');
  for (const m of wanted) {
    const r = rows.filter(x => x.model === m && x.prompt === 'P0_actual' && !x.err);
    if (!r.length) continue;
    console.log(`  ${m.padEnd(26)} formula=${r.filter(x => x.flags.formula_gancho).length}/${r.length} cta=${r.filter(x => x.flags.llamada_a_la_accion).length}/${r.length}`);
  }

  console.log('\n\nTEXTOS COMPLETOS DEL PROMPT REESCRITO (P2), para leerlos:');
  for (const row of rows.filter(x => x.prompt === 'P2_reescrito' && x.text)) {
    console.log('\n' + '-'.repeat(78));
    console.log(`${row.art} | ${row.model}`);
    console.log('-'.repeat(78));
    console.log(row.text);
  }
}

run().catch(e => { console.error('fallo:', e); process.exit(1); });
