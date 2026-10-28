// The Exponential Time Hypothesis Fell Twice — part 2 of 2, how it fell. Narration from script.md (draft v1,
// pending approval). The wall (an expander that every cut severs) and the way through it (count,
// so pieces can carry signs; one crossing becomes two cheap pieces) are the two bespoke scenes.
import type { Cuts } from './types.ts';
import { L, anim, intro, outro, say, videos } from './narrate.ts';

const build = (): Cuts => ({
  main: [
    intro('hook', [
      say(0.4, 'Two AI labs just refuted the Exponential Time Hypothesis. Here is how.', 'Dos laboratorios de IA acaban de refutar la hipótesis del tiempo exponencial. Así lo hicieron.'),
    ]),
    anim('wall', 'ExpanderCut', {}, [
      say(0.3, 'Link two conditions when they share a friend.', 'Une dos condiciones cuando comparten un amigo.'),
      say(0, "The wall: hard puzzles can't be split without cutting too many links.", 'El muro: los puzles difíciles no se pueden partir sin cortar demasiados enlaces.'),
    ], { min: 5.5 }),
    anim(
      'count',
      'KeyQuote',
      { text: L("Count, don't decide.", 'Contar, no decidir.'), emphasis: ['Count', 'Contar'] },
      [say(0.3, 'Both labs count the solutions instead, so terms can cancel.', 'Los dos cuentan las soluciones, para que los términos puedan cancelarse.')],
      { min: 4 },
    ),
    anim('octonions', 'CrossingRewrite', {}, [
      say(0.3, "Claude's proof uses an identity from 1818, from the octonions.", 'La prueba de Claude usa una identidad de 1818, de los octoniones.'),
      say(0, 'Two crossing links become pieces that are cheap one way or the other.', 'Dos enlaces cruzados se convierten en piezas baratas en una dirección o en la otra.'),
    ], { min: 9 }),
    anim(
      'levels',
      'BarCompare',
      {
        bars: [
          { label: L('Level 0', 'Nivel 0'), value: 1, display: '1' },
          { label: L('Level 2', 'Nivel 2'), value: 0.94, display: '0.94' },
          { label: L('Level 5', 'Nivel 5'), value: 0.73, display: '0.73' },
          { label: L('Level 10', 'Nivel 10'), value: 0.47, display: '0.47', highlight: true },
        ],
        max: 1,
      },
      [
        say(0.3, 'Each level shrinks the exponent by 11/12, as low as you like.', 'Cada nivel encoge el exponente en 11/12, tan bajo como quieras.', {
          en: 'Each level shrinks the exponent by eleven twelfths, as low as you like.',
          es: 'Cada nivel encoge el exponente en once doceavos, tan bajo como quieras.',
        }),
      ],
      { min: 5 },
    ),
    anim(
      'openai',
      'FlowDiagram',
      {
        layout: 'vertical',
        nodes: [
          { id: 'deform', label: L('Deform: H(T)', 'Deformar: H(T)') },
          { id: 'easy', label: L('Easy points T = 1…Q', 'Puntos fáciles T = 1…Q') },
          { id: 'back', label: L('Interpolate: H(0) = count', 'Interpolar: H(0) = cuenta') },
        ],
        edges: [
          { from: 'deform', to: 'easy' },
          { from: 'easy', to: 'back' },
        ],
      },
      [say(0.3, "OpenAI's proof deforms the problem, solves the easy cases, and interpolates back.", 'La de OpenAI deforma el problema, resuelve los casos fáciles e interpola de vuelta.')],
      { min: 5.5 },
    ),
    anim(
      'sowhat',
      'StatGrid',
      {
        stats: [
          { value: '10^10,000', label: L('variables before it beats brute force', 'variables antes de ganar a la fuerza bruta') },
          { value: 'P vs NP', label: L('untouched', 'intacto') },
        ],
      },
      [
        say(0.3, 'No faster solvers: it only wins past 10^10,000 variables.', 'Sin solvers más rápidos: solo gana pasadas 10^10.000 variables.', {
          en: 'No faster solvers: it only wins past ten to the ten thousand variables.',
          es: 'Sin solvers más rápidos: solo gana pasadas diez elevado a diez mil variables.',
        }),
      ],
      { min: 5 },
    ),
    anim(
      'closer',
      'KeyQuote',
      { text: L('ETH is false. Twice.', 'ETH es falsa. Dos veces.'), emphasis: ['Twice', 'veces'], beat: 1 },
      [
        say(0.3, 'Two labs, the same week, the same bound.', 'Dos laboratorios, la misma semana, la misma cota.'),
        say(0, 'The hypothesis is false.', 'La hipótesis es falsa.'),
      ],
      { min: 5 },
    ),
    outro('outro', []),
  ],
});

export const VIDEOS = videos(build);
/** The English main cut. */
export const TIMELINE = VIDEOS.en.main;
