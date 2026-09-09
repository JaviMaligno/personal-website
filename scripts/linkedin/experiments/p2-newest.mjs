/**
 * El prompt reescrito contra los modelos mas nuevos, por REST y con reintentos.
 * La matriz anterior los daba por rotos: era el SDK 0.21.0 tapando 503 transitorios.
 */
import { readFileSync } from 'fs';
import matter from 'gray-matter';
import { generate } from './gemini.mjs';

const MODELOS = ['gemini-3.8-flash', 'gemini-3.5-flash', 'gemini-3-flash-preview'];
const ARTICLES = [
  { key: 'matematicas', path: 'src/content/blog/en/navier-stokes-blows-up.md' },
  { key: 'agentes', path: 'src/content/blog/en/what-agents-say-to-each-other.md' },
  { key: 'negocio', path: 'src/content/blog/en/stop-being-the-cable.md' },
];

const N = '(a|one|two|three|four|five|six|seven|\\d+)';
const formula = t => new RegExp(
  "(isn'?t (the|about) [^.]{0,45}(—|-|;|,) ?it'?s|hardest part|most (fascinating|interesting) thing about|real story behind)"
  + "|^I spent " + N + " (day|days|week|weeks|hour|hours)"
  + "|^Most (teams|engineers|engineering leaders|companies|people)"
  + "|^When ", 'i').test(t.split('\n')[0] || '');
const inventado = t => new RegExp("I used to think|proved me wrong|I've always|I was wrong|I spent " + N + " (day|days|week|weeks)", 'i').test(t);

const build = ({ title, description, tags, content }) => `You are writing a LinkedIn post for Javier Aguilar about an article he wrote. Write as him, first person.

ARTICLE
Title: ${title}
Description: ${description}
Tags: ${tags.join(', ')}

FULL CONTENT:
${content.substring(0, 4000)}

WHAT THE POST MUST DO
- Lead with the article's own subject and its most concrete finding. If the article is about mathematics, the post is about mathematics; if it is about a measurement, lead with the number.
- Carry at least two specifics from the article: a number, a name, a mechanism. Never a claim so general it would fit a different article.
- Keep the author's judgment exactly as the article states it. Do NOT invent personal history, effort, conversions or opinions — no "I used to think", no "this proved me wrong", no "I spent three weeks". If the article does not say it, he did not say it.
- Assume a reader who knows the field. Do not address CTOs, leaders or "those of us building X" as a group.

WHAT THE POST MUST NOT DO
- No opening formula. Never start with "The hardest part of X isn't Y, it's Z", "Most teams...", "I spent N days..." or any variant of them.
- No closing question, no call to action, no "what's your experience", no "how are you thinking about".
- No hashtags and no URL (both are appended afterwards). No markdown, no emojis.

LENGTH
Two or three short paragraphs, under 300 words. End on a statement.`;

const gen = (model, prompt) => generate(model, prompt, { intentos: 3 });

const filas = [];
for (const art of ARTICLES) {
  const { data, content } = matter(readFileSync(art.path, 'utf-8'));
  const prompt = build({ title: data.title, description: data.description, tags: data.tags || [], content });
  for (const m of MODELOS) {
    const r = await gen(m, prompt);
    console.log('='.repeat(78));
    console.log(`${art.key} | ${m} | ${r.secs}s | intento ${r.intento}${r.err ? ' | ERROR ' + r.err : ''}`);
    if (r.text) {
      console.log(r.text);
      console.log(`\n[formula=${formula(r.text)} yo_inventado=${inventado(r.text)} pregunta=${/\?\s*$/.test(r.text)} palabras=${r.text.split(/\s+/).length}]`);
      filas.push({ art: art.key, m, t: r.text });
    }
    await new Promise(res => setTimeout(res, 1000));
  }
}

console.log('\n' + '#'.repeat(78));
for (const m of MODELOS) {
  const r = filas.filter(x => x.m === m);
  if (!r.length) { console.log(`${m.padEnd(24)} sin respuestas`); continue; }
  console.log(`${m.padEnd(24)} n=${r.length} formula=${r.filter(x => formula(x.t)).length} inventado=${r.filter(x => inventado(x.t)).length} pregunta=${r.filter(x => /\?\s*$/.test(x.t)).length} palabras_medias=${Math.round(r.reduce((a, x) => a + x.t.split(/\s+/).length, 0) / r.length)}`);
}
