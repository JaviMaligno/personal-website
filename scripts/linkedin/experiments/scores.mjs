/**
 * Los detectores de forma del banco de posts de LinkedIn. Fuente unica.
 *
 * Viven aparte porque los usan dos experimentos (summary-matrix.mjs y
 * component-rule.mjs) y un detector copiado deja de ser el mismo a la segunda
 * edicion, que es justo lo que le paso al prompt antes de prompt.js.
 *
 * Son deliberadamente literales y pueden quedarse cortos: sirven para ordenar,
 * la decision se toma leyendo los textos que el experimento imprime.
 */
export const N = '(a|one|two|three|four|five|six|seven|\d+)';
export const SCORES = {
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
  // Lo que LinkedIn impone y P2 no decia. El corte de "...ver mas" ronda los
  // 200 caracteres en movil: una primera linea mas larga se publica cortada a
  // media frase, y esa mitad es todo lo que ve quien pasa por el feed.
  apertura_cortada: t => (t.trim().split('\n')[0] || '').length > 200,
  // benchmaxing (2026-09-16) abrio definiendo el tema en tercera persona
  // ("Benchmaxing directs model optimization toward...") y el post entero se
  // leyo como un abstract. La firma es el sujeto = tema y un verbo descriptivo
  // en segunda o tercera posicion. Probado contra los cinco posts de
  // septiembre: marca benchmaxing y ninguno de los otros cuatro.
  // Ojo: "sin I/my/me en el primer parrafo" NO sirve — marcaba justo los dos
  // ganchos buenos, cuya primera linea es una escena sin narrador.
  apertura_definicion: t => /^[A-Z][\w-]*( \w+)? (is|are|means|refers to|directs|describes|involves|represents|remains) /
    .test((t.trim().split('\n')[0] || '').trim()),
  // Un parrafo de mas de 600 caracteres es un muro en el feed.
  muro_de_texto: t => t.trim().split(/\n\s*\n/).some(p => p.length > 600),
  pregunta_en_el_cierre: t => /\?/.test(t.trim().split(/\n\s*\n/).pop() || ''),
};

// Ojo con los dos puntos: NO se parte por ellos. La regla de componentes
// induce justamente el formato "Frontend: interaccion, supervision, resultados",
// y partir por ":" dejaba el nombre en una frase y su responsabilidad en otra,
// asi que el detector contaba como no atribuido justo el formato que la regla
// produce. Medido el 2026-09-22: sesgaba el resultado EN CONTRA de la regla.
export const frases = text => text.split(/\n+|(?<=[.;!?])\s+/).map(s => s.trim()).filter(Boolean);

/** Cuantos componentes reciben frase propia, y si el post los amontona en una. */
export function componentes(text, comps) {
  if (!comps.length) return null;
  const sents = frases(text);
  const amontonados = sents.some(s => comps.filter(c => c.re.test(s)).length >= 3);
  const atribuidos = comps.filter(c => sents.some(s =>
    c.re.test(s)
    && comps.filter(o => o !== c && o.re.test(s)).length === 0
    // una mencion suelta no es una responsabilidad: la frase tiene que decir algo
    && s.replace(c.re, ' ').split(/\s+/).filter(Boolean).length >= 4
  )).length;
  const mencionados = comps.filter(c => c.re.test(text)).length;
  return { amontonados, atribuidos, mencionados, total: comps.length };
}

/** Para los controles: ¿la regla ha inventado una lista donde no habia conjunto? */
export const listaInventada = text => text.split('\n').map(l => l.trim()).filter(Boolean)
  // 200 y no 120: la linea de un componente con su responsabilidad pasa de
  // 120 caracteres en cuanto la responsabilidad tiene tres partes, y con el
  // limite corto el detector se dejaba fuera justo la tercera.
  .filter(l => l.length < 200 && /^[A-Z][\w' -]{2,40}\s*(—|-|:)\s+\S/.test(l)).length >= 3;
