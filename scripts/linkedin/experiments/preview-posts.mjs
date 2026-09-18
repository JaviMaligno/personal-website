/**
 * Genera posts de muestra con el prompt QUE ESTA EN PRODUCCION en esta rama,
 * para leerlos antes de desplegarlo.
 *
 * A diferencia de summary-matrix.mjs, esto no compara prompts: elige articulos
 * YA PUBLICADOS, cuyo post real se puede mirar en LinkedIn, y regenera el post
 * con el prompt nuevo. La comparacion antes/despues sale gratis y sobre el
 * mismo material, que es la unica forma de que signifique algo.
 *
 * Dos tiradas por articulo, porque una sola no dice si el prompt aguanta o si
 * tuvo suerte.
 *
 * Uso (en CI, donde vive GEMINI_API_KEY):
 *   node scripts/linkedin/experiments/preview-posts.mjs
 */
import { readFileSync } from 'fs';
import matter from 'gray-matter';
import { generate } from './gemini.mjs';
import { buildSummaryPrompt } from '../prompt.js';

// Los tres posts de septiembre que peor salieron, con la medida del que se
// publico de verdad, para poder comparar sin ir a buscarla.
const ARTICLES = [
  { path: 'src/content/blog/en/benchmaxing.md',
    real: { car1: 543, defecto: 'abrio definiendo el tema en tercera persona, como un abstract' } },
  { path: 'src/content/blog/en/knew-it-wasnt-the-model.md',
    real: { car1: 445, defecto: 'primera linea partida por el corte de "ver mas"' } },
  { path: 'src/content/blog/en/the-bug-nobody-can-reach.md',
    real: { car1: 151, defecto: 'apertura buena, pero cerro con pregunta' } },
];

const TIRADAS = 2;
const MODELO = 'gemini-3-flash-preview';

const medir = (t) => {
  const lineas = t.trim().split('\n');
  const parrafos = t.trim().split(/\n\s*\n/);
  return {
    car1: (lineas[0] || '').length,
    cortada: (lineas[0] || '').length > 200,
    parrafos: parrafos.length,
    palabras: t.trim().split(/\s+/).length,
    pregunta_cierre: /\?/.test(parrafos[parrafos.length - 1] || ''),
    parrafo_mas_largo: Math.max(...parrafos.map(p => p.length)),
  };
};

for (const art of ARTICLES) {
  const { data, content } = matter(readFileSync(art.path, 'utf-8'));
  console.log('\n' + '#'.repeat(78));
  console.log('# ' + art.path);
  console.log(`# El post REAL: primera linea de ${art.real.car1} caracteres — ${art.real.defecto}`);
  console.log('#'.repeat(78));

  for (let i = 1; i <= TIRADAS; i++) {
    const prompt = buildSummaryPrompt({
      title: data.title, description: data.description, content, tags: data.tags || [],
    });
    const r = await generate(MODELO, prompt);
    if (r.err) { console.log(`\n--- tirada ${i}: ERROR ${r.err}`); continue; }
    const m = medir(r.text);
    console.log(`\n--- tirada ${i} (${r.secs}s) | 1a linea ${m.car1} car | cortada=${m.cortada} | ${m.parrafos} parrafos | parrafo mas largo ${m.parrafo_mas_largo} car | ${m.palabras} palabras | pregunta al cierre=${m.pregunta_cierre}`);
    console.log('-'.repeat(78));
    console.log(r.text);
    console.log('-'.repeat(78));
    await new Promise(res => setTimeout(res, 1500));
  }
}
