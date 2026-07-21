# Design: "Escribir un paper de investigación con IA" (artículo meta del blog)

Date: 2026-07-19
Branch: `blog/writing-a-paper-with-ai`
Status: approved in brainstorming (spine = proceso/honestidad; modelo-gap como
sección load-bearing; opción "real + anunciar paper 2"; dos sub-hilos honestos)

## Propósito y audiencia

Artículo meta bilingüe (EN + ES) para el blog de javieraguilar.ai que cuenta el
proceso real de escribir un preprint de investigación con IA —
"When a Verified World Model Still Loses" (arXiv:2607.14169, paper 1) — con un
eje nuevo: **dónde se nota de verdad la diferencia de inteligencia entre modelos
al hacer ciencia.**

Audiencia: técnica (los mismos lectores del blog; investigadores, ingenieros de
IA, gente que ya usa LLMs en serio). No es marketing de un modelo concreto.

## Espina (through-line)

**La IA es un multiplicador para un investigador ya capaz; la restricción
vinculante no es escribir prosa, es planear ciencia y revisar como un par.**

Compañero natural del artículo ya publicado
`writing-an-essay-with-ai-codex-vs-claude-code` (prosa = frontera dura para la
IA). Este da el siguiente paso: en investigación, la frontera se mueve al
**diseño experimental riguroso y la revisión peer-grade**, y ahí la *capacidad*
del modelo se vuelve el cuello de botella. Enlazar ambos como serie de "escribir
con IA".

## Restricciones de voz (no negociables)

- Tono **matizado, sin rotundidad ni hype** (ver feedback de voz del blog).
- Sin hombre de paja sobre la trayectoria de Javier.
- **No** presentar nada sintético como real. Todos los ejemplos son reales y
  verificables en git.
- La sección de modelos NO es "modelo X > modelo Y": son dos sub-hilos honestos
  (capacidad en la parte difícil; complementariedad entre pares).
- Para cada afirmación fuerte, separar lo **demostrable** de lo **medido** — la
  misma disciplina que defiende el propio artículo.

## Estructura (5 secciones)

### 1. Gancho — el contraste de credibilidad
Javier ya publicó un preprint antes de la IA (su tesis de matemáticas:
demostración de un teorema, +2 años, con respaldo institucional). Este: ~2
semanas, en solitario. Fija el tono honesto desde la primera línea: no es
incapacidad suplida por IA, es amplificación de alguien ya capaz.

### 2. El proceso real (no "la IA escribió mi paper")
- La idea nació de una **lectura asistida por IA** del paper de DeepMind
  (Code World Models for General Game Playing, arXiv:2510.04542).
- Experimentos **ejecutados por agentes**.
- La disciplina clave: **separar lo demostrable de lo medido** y decir cuál es
  cuál (ir a *ganar* statements fuertes donde se puede: teorema de
  identificabilidad, cota de cobertura; afinar el resto).

### 3. La sección modelo-gap (nueva, load-bearing)
Dónde la capacidad del modelo es el cuello de botella = **planear ciencia +
revisión peer-grade**. Dos sub-hilos:

**(a) Capacidad en la parte difícil — el side-by-side limpio (paper 2, upcoming).**
Ejemplo real y verificable: el spec `curvature-sweep` en el repo del paper 2.
- Anclas git: estado original `3ca6456` → corrección `454a8c2`
  ("spec(rev2): redesign … per expert review — factorization, graph boundaries,
  symmetric metrics, oracle baseline, topology fix"), diff 183+/184−.
- **Anécdota titular — la topología.** Durante la discusión del plan, Javier
  pidió a Opus 4.8 que anotara, como futura línea, el uso pesado de topología en
  ALTAS dimensiones. Opus lo confundió y escribió que unos anillos en 2D
  exigían subir de dimensión. GPT-5.6 lo cazó: *"un anillo vive perfectamente en
  2D y tiene homología no trivial; no requiere aumentar la dimensión del
  estado."* Encuadre honesto: el error fue del **modelo débil malinterpretando
  la intención del humano**, no de Javier; el modelo fuerte lo corrigió.
- **El catch más profundo — el confound.** El plan fijaba la rareza `r` creyendo
  que dejaba "solo geometría" como variable. GPT-5.6 lo factoriza —
  `P(reparación) = P(visible) × P(evidencia suficiente | visible) ×
  P(representable | suficiente)` — y muestra que el plan solo controlaba el
  primer factor: *"con el diseño actual, una curva observada no permitiría
  atribuir el resultado específicamente a curvatura."* Es decir, **el
  experimento no podía responder su propia pregunta.** Planear ciencia en estado
  puro.
- **Micro-catch (opcional, verificable).** El spec decía que las celdas extremas
  "no tienen varianza"; el revisor: *"0/10 no tiene cero varianza — su límite
  superior Wilson ronda 0.28."*
- **Sugerencia original productiva.** El **baseline oráculo** por familia, que
  separa límite-de-información de límite-de-representación del sintetizador; y las
  "notas para paper 3" con citas reales (Federer 1959; Niyogi–Smale–Weinberger;
  Cohen-Steiner–Edelsbrunner–Harer; Mammen–Tsybakov) = las sugerencias de
  continuación que empujan hacia el siguiente paper.
- **Progresión del proceso, honesta:** empezó con Opus 4.8 a base de muchas
  preguntas y rondas de revisión (con GPT-5.5 y propias); con Fable 5 fue más
  fluido, con menos correcciones y sugerencias originales; GPT-5.6 hizo de
  salvavidas cuando Fable topaba con los límites estrictos de la suscripción, con
  revisiones que se asemejan a un peer review real.
- **Anuncio:** presentar el paper 2 como *upcoming* (teaser honesto), sin
  prometer resultados.

**(b) Complementariedad, no solo ranking (paper 1).**
A veces el valor no es "un modelo más listo" sino **un segundo par de ojos
distinto**: dos modelos que ven lo que el otro no. Commits del paper 1 que lo
registran textualmente:
- `cd231e3` — un agente Claude se quejó de que los datos de fallo venían
  truncados; *tenía razón*; el arreglo del confound del canal de feedback
  convirtió un hallazgo débil en uno replicado en dos familias de modelos más.
- `fe6dce7` / `c739a29` — "codex confirm" cazó un overclaim superviviente
  ("reproduces the same play cost" → acotado).
- `0d63099` — el ángulo opuesto a la alucinación de citas: el modelo **se negó a
  fabricar** una URL (`URL to be supplied by the author`).
Enlazar aquí al artículo `writing-an-essay-with-ai-codex-vs-claude-code` en vez
de reexplicar la complementariedad codex↔claude.

### 4. Honestidad — desenredar los confounders
El salto 2 años → 2 semanas tiene varias causas, no solo la IA:
- matemática pura (demostrar un teorema) vs ML empírico — intrínsecamente más
  lento lo primero;
- longitud (el paper de mates es ~el doble o más);
- overhead del proceso institucional.
Reconocerlos evita sobrevender. Aun normalizando, el salto sigue siendo grande;
atribuirlo todo a la IA sería deshonesto. Este eje (pura → aplicada/ML) es
además la **narrativa de la transición de carrera** de Javier, que sirve de hilo.

### 5. Cierre
La IA amplifica la independencia y la velocidad de quien ya es capaz; el
multiplicador **escala con la capacidad del modelo** en la parte difícil (planear
ciencia, revisar como un par) y con la **diversidad** de modelos; el trabajo
humano sigue siendo juicio, disciplina de honestidad y verificación.

## Evidencia y fuentes (todo real, verificable en git)

- Paper 1: repo `code-world-models`, `docs/paper/main.tex`, commits `cd231e3`,
  `da9e60a`, `2e3f2af`, `af934c4`, `c739a29`, `fe6dce7`, `0d63099`.
- Paper 2: repo `cwm-wt-paper2`, rama `claude/continuous-setting-feasibility-wktp6b`,
  spec `docs/superpowers/specs/2026-07-19-curvature-sweep-design.md`, commits
  `3ca6456` → `454a8c2`.
- Feedback de GPT-5.6 en crudo (en mano) — fuente de las citas de la sección 3a;
  usar solo los fragmentos curados, no volcar el texto entero.
- Paper de DeepMind: arXiv:2510.04542. Preprint de Javier: arXiv:2607.14169.

## Integración en el sitio (la ejecuta blog-writer)

- Dos ficheros: `src/content/blog/en/…` y `src/content/blog/es/…`, mismo
  `translationKey`.
- Frontmatter estándar (title, description, pubDate, tags, lang, translationKey,
  heroImage, linkedinImage) siguiendo los artículos existentes.
- `pubDate`: **escalonar** — no coincidir con otras ramas de blog sin mergear
  (ciphers = 2026-07-20). Elegir fecha posterior al publicar; una rama, un
  artículo, publicar de uno en uno.
- Cross-links: al artículo de ensayo codex-vs-claude, a
  `results-oriented-programming`, a `how-much-should-you-still-know`, y al
  artículo/preprint del paper 1.

## Fuera de alcance (YAGNI)

- Volcar el feedback completo de GPT-5.6 — solo fragmentos curados.
- Convertir el artículo en una comparativa/benchmark de modelos.
- Detallar la ciencia del paper 2 más allá del teaser (es upcoming).
- Reexplicar la complementariedad codex↔claude (ya tiene su artículo; enlazar).

## Riesgos

- **Tono hype.** Mitigación: los dos sub-hilos + la sección de confounders +
  citar solo lo verificable.
- **Anunciar paper 2 y que cambie.** Mitigación: teaser sin prometer resultados;
  el ejemplo del spec es sobre *proceso*, no sobre hallazgos.
- **El before/after de curvatura es denso (matemático).** Mitigación: contar la
  topología y el confound en lenguaje llano; el detalle técnico va como cita
  corta, no como exposición completa.
- **Dependencia de material externo** (repos privados). Mitigación: las citas de
  commits/feedback son autocontenidas en el artículo; no requieren que el lector
  acceda a los repos.
