/**
 * El prompt del generador de posts de LinkedIn. Fuente unica.
 *
 * Vive aparte de generate-summary.js por una razon concreta: el banco de
 * pruebas (scripts/linkedin/experiments/summary-matrix.mjs) tiene que medir
 * EXACTAMENTE el prompt que se despliega, y no puede importar
 * generate-summary.js porque ese modulo carga @google/generative-ai, que el
 * workflow de experimentos no instala. Este fichero no tiene dependencias.
 *
 * Historia de lo medido, para no volver a derivarlo:
 *
 * 2026-09-09 — el prompt original traia tres ganchos de EJEMPLO y el modelo
 * los copiaba: 12 de 12 aperturas eran una de esas tres familias, con cuatro
 * modelos distintos. Tambien exigia una llamada a la accion, asi que 7 de cada
 * 12 acababan en pregunta, y llego a inventar historia personal que el
 * articulo no dice. Quitar los ejemplos y la CTA lo bajo a 0 de 10.
 *
 * 2026-09-18 — medidos los cinco posts realmente publicados del 12 al 17 de
 * septiembre, quedaban tres defectos que el prompt anterior no nombraba, todos
 * de FORMA, no de contenido:
 *
 *   post                            1a linea  cortada  definicion  pregunta
 *   when-the-fact-stops-being-true     185       no        no        SI
 *   the-bug-nobody-can-reach           151       no        no        SI
 *   being-wrong-can-be-free            293       SI        no        SI
 *   knew-it-wasnt-the-model            445       SI        no        no
 *   benchmaxing                        543       SI        SI        no
 *
 * - Tres de cinco aperturas pasan de 200 caracteres, que es donde LinkedIn
 *   corta con "...ver mas": se publican partidas a media frase, y esa mitad es
 *   todo lo que ve quien pasa por el feed.
 * - Tres de cinco acaban en pregunta pese a que el prompt lo prohibia en una
 *   linea entera. Prohibirlo solo en la ultima frase no basta.
 * - benchmaxing abrio definiendo el tema en tercera persona, que es lo que
 *   hace que un post se lea como un abstract.
 *
 * 2026-09-21 — frontend-backend-agentic-core se publico nombrando sus tres
 * bloques en una sola frase ("the frontend, the application backend, and the
 * agentic engine") y dando responsabilidad solo a uno de los tres. El articulo
 * los separa con una figura por bloque; el post los dejaba como nombres. De
 * ahi la regla de componentes, con su interruptor en la firma.
 *
 * De ahi el bloque THE FIRST LINE IS THE WHOLE POST. Lo que hace "catchy" a un
 * post no es una formula de apertura — eso ya se probo y sale plantilla 12 de
 * 12 — sino que el hecho mas concreto del articulo quepa antes del corte.
 */
export function buildSummaryPrompt({ title, description, content, tags = [] }, { componentRule = true } = {}) {
  // La regla de componentes va detras de un interruptor por una sola razon:
  // el banco necesita el mismo prompt con y sin ella para poder atribuirle un
  // efecto. En produccion esta puesta; si el banco no la respalda, se quita de
  // aqui y el interruptor desaparece con ella.
  const componentLines = componentRule ? `
- If the article names a set of components, layers or stages, do not compress them into one sentence that only lists their names. Give each one its own short line, naming the responsibility the article assigns to it.
- Only when the article separates them itself. Never invent a set, and never turn the post into a list of things the article treats as one.` : '';

  return `You are writing a LinkedIn post for Javier Aguilar about an article he wrote. Write as him, first person.

ARTICLE
Title: ${title}
Description: ${description}
Tags: ${tags.join(', ')}

FULL CONTENT:
${content.substring(0, 4000)}

THE FIRST LINE IS THE WHOLE POST
LinkedIn truncates after about 200 characters; everything past that is hidden behind "see more" and most readers never open it. So:
- The first line is a single sentence, under 150 characters, standing alone on its own line with a blank line after it.
- It states the most surprising concrete thing the article actually found — a number, a result, a specific event. The strangest true fact, not the topic.
- If a reader could guess the sentence from the title alone, it is the wrong sentence.
- Never open by defining or characterising the subject ("Benchmaxing directs model optimization toward...", "Multi-agent systems are..."). No sentence whose subject is the topic and whose verb is "is", "means" or "refers to".
- Never open with the article's context, background, or what you argued last week. Open with the finding.

THE REST
- Two or three short paragraphs after the first line, each at most three sentences, separated by blank lines. Never a wall of text.${componentLines}
- Carry at least two more specifics from the article: a number, a name, a mechanism. Never a claim so general it would fit a different article.
- Keep the author's judgment exactly as the article states it. Do NOT invent personal history, effort, conversions or opinions — no "I used to think", no "this proved me wrong", no "I spent three weeks". If the article does not say it, he did not say it.
- Assume a reader who knows the field. Do not address CTOs, leaders or "those of us building X" as a group.

WHAT THE POST MUST NOT DO
- No opening formula. Never start with "The hardest part of X isn't Y, it's Z", "Most teams...", "I spent N days..." or any variant of them.
- No question anywhere in the final paragraph, and no question as the last sentence. The post ends on a full stop. If your closing sentence ends in "?", rewrite it as a statement.
- No call to action, no "what's your experience", no "how are you thinking about".
- No hashtags and no URL (both are appended afterwards). No markdown, no emojis.

LENGTH
Under 250 words in total, first line included. End on a statement.`;
}
