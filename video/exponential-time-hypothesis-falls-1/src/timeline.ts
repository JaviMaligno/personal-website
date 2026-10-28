// The Exponential Time Hypothesis Fell Twice — part 1 of 2, the problem. Narration from script.md
// (draft, pending approval). The article's dinner party carries 3-SAT: friends are yes/no choices,
// conditions are clauses; checking a list is one pass, finding one doubles with every friend.
import type { Cuts } from './types.ts';
import { L, anim, intro, outro, say, videos } from './narrate.ts';

const build = (): Cuts => ({
  main: [
    intro('hook', [
      say(0.4, 'Your friends send conditions for a dinner. Is there one guest list that works?', 'Tus amigos te mandan condiciones para una cena. ¿Hay una lista de invitados que funcione?'),
    ]),
    anim('dinner', 'DinnerParty', { mode: 'intro' }, [
      say(0.3, '"Ana comes, or Bea doesn\'t."', '"Viene Ana, o no viene Bea."'),
      say(0, '"Carlos or Diego, at least one."', '"Carlos o Diego, al menos uno."'),
      say(0, '"Not Ana, Bea and Carlos together."', '"Ana, Bea y Carlos juntos no."'),
      say(0, 'Each friend is a yes or a no. Each condition names at most three.', 'Cada amigo es un sí o un no. Cada condición nombra como mucho a tres.'),
      say(0, "That's 3-SAT, the reference hard problem of computer science.", 'Eso es 3-SAT, el problema difícil de referencia de la informática.', {
        en: "That's three-SAT, the reference hard problem of computer science.",
        es: 'Eso es tres-SAT, el problema difícil de referencia de la informática.',
      }),
    ]),
    anim('check', 'DinnerParty', { mode: 'check' }, [
      say(0.2, 'Checking a guest list is easy: one pass over the conditions.', 'Comprobar una lista es fácil: una pasada por las condiciones.'),
    ], { min: 4.5 }),
    anim(
      'finding',
      'StatGrid',
      {
        stats: [
          { value: '1,024', label: L('lists with 10 friends', 'listas con 10 amigos') },
          { value: '≈ 1 billion', label: L('with 30 friends', 'con 30 amigos') },
          { value: '31 digits', label: L('with 100 friends', 'con 100 amigos') },
        ],
      },
      [
        say(0.3, 'Finding one is hard: every friend you add doubles the lists to try.', 'Encontrarla es difícil: cada amigo que añades duplica las listas que probar.'),
        say(0, 'About a billion with 30 friends. A 31-digit number with 100.', 'Unos mil millones con 30 amigos. Un número de 31 cifras con 100.'),
      ],
    ),
    anim(
      'bases',
      'BarCompare',
      {
        bars: [
          { label: L('Try every list', 'Probarlas todas'), value: 2, display: '2ⁿ' },
          { label: 'Schöning (1999)', value: 1.334, display: '1.334ⁿ' },
          { label: 'PPSZ + Hertli', value: 1.308, display: '1.308ⁿ', highlight: true },
        ],
        max: 2,
      },
      [say(0.3, 'Forty years of clever ideas lowered that growth rate. Never to one.', 'Cuarenta años de ideas ingeniosas bajaron ese ritmo de crecimiento. Nunca a uno.')],
      { min: 5 },
    ),
    anim(
      'papers',
      'Counter',
      { value: 800, suffix: '+', label: L('papers rest on ETH', 'artículos se apoyan en ETH'), beat: 0 },
      [
        say(0.2, 'In 1999 that became a bet: the Exponential Time Hypothesis.', 'En 1999 eso se convirtió en una apuesta: la hipótesis del tiempo exponencial.'),
        say(0, 'Over 800 papers rest on it.', 'Más de 800 artículos se apoyan en ella.'),
      ],
    ),
    anim(
      'closer',
      'KeyQuote',
      { text: L('This week it fell. Twice.', 'Esta semana cayó. Dos veces.'), emphasis: ['Twice', 'veces'] },
      [
        say(0.3, 'This week, two AI labs proved it false.', 'Esta semana, dos laboratorios de IA demostraron que es falsa.'),
        say(0, 'Part two: how.', 'Segunda parte: cómo.'),
      ],
      { min: 4 },
    ),
    outro('outro', []),
  ],
});

export const VIDEOS = videos(build);
/** The English main cut. */
export const TIMELINE = VIDEOS.en.main;
