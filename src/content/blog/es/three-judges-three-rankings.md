---
title: "Tres jueces, tres rankings"
description: "Pasé las mismas 45 comparaciones ciegas por un juez GPT, uno Grok y uno Claude. Cada uno produjo un ranking distinto, cada uno favoreció sus propias respuestas, y el efecto crece con lo subjetiva que sea la tarea."
pubDate: 2026-07-30
tags: ["Agentes IA", "Evals", "LLM", "Investigación"]
lang: es
translationKey: three-judges-three-rankings
heroImage: "/blog/three-judges-three-rankings.png"
linkedinImage: /blog/judge-bias-self-preference.png
repoUrl: https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias
linkedinLinks:
  - label: "Parte 1 — LLM-as-Judge son tres decisiones"
    url: https://www.javieraguilar.ai/es/blog/llm-as-judge-three-decisions/
  - label: "Zheng et al., Judging LLM-as-a-Judge (MT-Bench)"
    url: https://arxiv.org/abs/2306.05685
  - label: "Panickssery et al., LLM Evaluators Recognize and Favor Their Own Generations"
    url: https://arxiv.org/abs/2404.13076
---

[Un artículo anterior](https://www.javieraguilar.ai/es/blog/llm-as-judge-three-decisions/) defendía que LLM-as-judge son tres decisiones —contexto, unidad, dimensión— y que las tres se toman antes de escribir el prompt. Aquel iba sobre *qué* puntúas. Este va sobre *quién* lo puntúa.

La pregunta salió de una conversación sobre evaluar dos sistemas, uno construido sobre GPT y otro sobre Claude. Si usas un juez GPT, ¿sigue siendo justa la comparación? El juez nunca ve un nombre de modelo. Pero no lo necesita: cada familia tiene un estilo de casa reconocible, y un juez que aprendió a producir un estilo puede perfectamente premiarlo.

Eso es una afirmación comprobable, y "varios papers han encontrado esto" no es lo mismo que haberlo medido en tus tareas. Así que monté un harness y lo medí. Todo lo que sigue son 378 juicios repartidos entre tres familias de modelos, y cada número es reproducible desde [el repo](https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias).

## El montaje, en un párrafo

Quince tareas repartidas a partes iguales entre tres niveles de subjetividad: objetivas con respuesta comprobable (parsear una duración, arreglar un bug de mediana, fusionar intervalos), medias (resumir, extraer a JSON, clasificar tickets) y subjetivas (el copy de un mensaje de error, el arranque de un postmortem, explicar consistencia eventual a un PM). Tres modelos responden las quince: **GPT-5.5**, **Grok-4.3** y **Claude Sonnet 4.6**. Después cada uno de esos tres modelos juzga todas las parejas de respuestas, a ciegas: ningún nombre de modelo aparece en el prompt, y el harness lo verifica antes de enviarlo. Cada comparación se juzga **dos veces, con las respuestas intercambiadas**, porque la tasa a la que un juez se contradice al intercambiar los huecos *es* el sesgo de posición, medido en vez de asumido. Se permiten empates: forzar una elección binaria entre dos respuestas igual de buenas fabrica caras o cruces que luego se leen como sesgo.

Las tres familias corrieron a través de una única suscripción de Azure AI Foundry, que es el truco barato que hizo esto asequible: una relación de facturación en vez de tres cuentas de proveedor. (También me costó una tarde: los modelos Anthropic en Foundry responden en la Messages API nativa y dan 404 en la ruta compatible con OpenAI, GPT-5.5 rechaza `temperature=0` de plano, y Grok-4.3 gasta ~350 tokens razonando antes de emitir un veredicto de una línea, lo que trunca en silencio la respuesta si presupuestaste 512. El README tiene la lista completa de cicatrices.)

## 1. El ranking depende de quién sostiene el portapapeles

![Tres jueces, tres rankings distintos de las mismas 45 comparaciones](https://www.javieraguilar.ai/blog/judge-bias-ranking.png)

Las mismas respuestas. El mismo prompt ciego. Los dos órdenes de presentación. Lo único que cambia entre esas tres columnas es qué modelo juzga, y el orden cambia con él:

| Generador | Global | por GPT-5.5 | por Grok-4.3 | por Claude Sonnet 4.6 | Palabras (media) |
|---|---|---|---|---|---|
| GPT-5.5 | 66,1% | **85,0%** | 58,3% | 55,0% | 66 |
| Claude Sonnet 4.6 | 45,0% | 35,0% | 38,3% | **61,7%** | 85 |
| Grok-4.3 | 38,9% | 30,0% | **53,3%** | 33,3% | 55 |

Tres jueces, tres ordenaciones distintas. Cada juez se coloca más arriba de donde lo colocan los otros dos. Dos de ellos coronan a GPT-5.5; el tercero se corona a sí mismo. Y los tres discrepan sobre el resto del orden: si hubieras hecho esta evaluación con un solo juez y publicado el ranking, parte de lo que publicabas habría sido el juez.

Eso es el síntoma. El resto es el diagnóstico.

## 2. El self-preference es real, y escala con la subjetividad

La forma ingenua de medir self-preference es contar cuántas veces un juez elige su propia respuesta. Esa medida no sirve: GPT-5.5 elige la suya el 85% de las veces, pero sus respuestas podrían ser simplemente las mejores —y según los otros dos jueces, en buena medida lo son.

Lo que sí demuestra sesgo es el **delta**: cuánto más a menudo un juez elige su propia respuesta *de lo que sus pares eligen esa misma respuesta, en las mismas comparaciones*.

| Juez | Tasa propia | Pares, mismas parejas | Delta | IC 95% | solo vs juez no implicado |
|---|---|---|---|---|---|
| GPT-5.5 | 85,0% | 56,7% | **+28,3pp** | [+16,7, +40,0] | +21,7pp [+8,3, +35,0] |
| Claude Sonnet 4.6 | 61,7% | 36,7% | **+25,0pp** | [+12,5, +36,7] | +15,0pp [+0,0, +28,3] |
| Grok-4.3 | 53,3% | 31,7% | **+21,7pp** | [+9,2, +35,8] | +13,3pp [−1,7, +30,0] |

Los tres positivos, los tres intervalos excluyendo el cero, los tres de tamaño parecido. Esto es justo lo que un piloto dentro de una sola familia no podía mostrar: cuando corrí el mismo harness con tres niveles de *una* familia, los deltas salieron +16,7, −14,6 y +4,2pp — ruido que no apuntaba a ningún lado. Entre familias es una línea recta.

Esa última columna merece una nota, porque es la que yo citaría. Con tres jueces que son a la vez los tres generadores, la línea base de "pares" para una comparación entre A y B incluye a **B**, y el self-preference de B empuja el veredicto en contra de A, inflando el delta medido de A. Restringir la base al juez que no tiene nada en juego en esa pareja se lleva por delante un tercio de cada número. El efecto sobrevive a esa corrección en GPT-5.5, marginalmente en Claude, y se vuelve indistinguible de cero en Grok. Quien mida self-preference con un panel de jueces sacado de los modelos evaluados está sobrecontando si no hace esto.

Y ahora el hallazgo que más me importa:

![El sesgo de un juez hacia sus propias respuestas crece con lo subjetiva que sea la tarea](https://www.javieraguilar.ai/blog/judge-bias-self-preference.png)

| Juez | Objetiva | Media | Subjetiva |
|---|---|---|---|
| GPT-5.5 | +17,5pp | +25,0pp | +42,5pp |
| Grok-4.3 | +7,5pp | +27,5pp | +30,0pp |
| Claude Sonnet 4.6 | −2,5pp | +30,0pp | +47,5pp |

En tareas con respuesta comprobable el self-preference es pequeño o inexistente —Claude Sonnet 4.6 es incluso *más duro* consigo mismo que un juez neutral—. En tareas donde el criterio es el gusto, llega a +30 y +48 puntos porcentuales.

Lo que convierte una advertencia vaga en una regla utilizable: **un juez de la misma familia que uno de los sistemas que comparas es casi inofensivo en trabajo objetivo y casi inservible en trabajo subjetivo.** Si tu rúbrica es "¿la extracción produjo el JSON correcto?", tranquilo. Si es "¿qué mensaje de error se lee mejor?", tu juez es un participante.

## 3. El sesgo de posición no es una ley natural: es una propiedad de un juez concreto

Todo el mundo repite "aleatoriza el orden de presentación". Esto es lo que el orden hizo de verdad:

| Juez | Tasa hueco A | binomial exacto vs 50% | Tasa de vuelco |
|---|---|---|---|
| GPT-5.5 | 52,6% | p = 0,73 | 8,9% |
| Claude Sonnet 4.6 | 51,5% | p = 0,90 | 20,0% |
| Grok-4.3 | **72,4%** | **p < 0,001** | **35,6%** |

Dos de los tres jueces no muestran preferencia de posición alguna. El tercero elige lo que lee primero casi tres de cada cuatro veces, y se contradice en más de un tercio de las comparaciones al intercambiar los huecos. Y empeora justo donde menos te conviene:

| Grok-4.3 | Objetiva | Media | Subjetiva |
|---|---|---|---|
| Tasa hueco A | 64% (p = 0,29) | 75% (p = 0,023) | 77% (p = 0,005) |
| Tasa de vuelco | 13% | 40% | **53%** |

En el tercio subjetivo del conjunto de tareas, Grok-4.3 se contradice en más de la mitad de las comparaciones. A esas alturas no está evaluando las respuestas: está evaluando sus direcciones.

Así que sigue aleatorizando el orden —es gratis—. Pero fíjate en que la justificación habitual ("los jueces LLM prefieren la primera respuesta") no es lo que dicen los datos. Los datos dicen que *algunos jueces lo hacen, de forma catastrófica, y no puedes saber cuál sin medirlo*. Correr cada comparación en los dos órdenes te cuesta un 2× en llamadas de juez y convierte una incógnita en un número.

## 4. El estadístico de longitud que todo el mundo cita es ininterpretable

Este es el número que se suele publicar:

| Juez | Gana la respuesta más larga |
|---|---|
| GPT-5.5 | 48,6% |
| Grok-4.3 | 48,6% |
| Claude Sonnet 4.6 | 64,6% |

Parece que apenas hay sesgo de longitud. En mi piloto dentro de una familia el mismo estadístico marcaba 80–85% y parecía un sesgo de manual. **Ambas lecturas son falsas**, y por la misma razón: en cualquier alineación normal de modelos, longitud y calidad están confundidas. Si tus modelos verbosos son además los buenos, el número se infla; si no lo son, se cancela. Es un accidente de tu alineación, no una propiedad de tu juez.

El control fija el modelo y la tarea y varía **solo** la longitud objetivo: dos variantes de un prompt base idéntico que se diferencian en una frase añadida ("responde en unas N palabras"). Al juez se le enseña el prompt base *sin* esa frase; de lo contrario estaría evaluando el cumplimiento de un límite de palabras del que le han hablado. Las variantes cortas salieron a 46 palabras de media, las largas a 174.

| Juez | Gana la larga (controlado) | Tasa de vuelco |
|---|---|---|
| GPT-5.5 | 77,8% | 11,1% |
| Grok-4.3 | 86,1% | 16,7% |
| Claude Sonnet 4.6 | 88,9% | 5,6% |

O sea que la preferencia no solo es real: es **más fuerte** de lo que sugería el número sin controlar, justo lo contrario de la dirección en la que la gente asume que corre la confusión.

Ahora bien, partido por lo que la tarea premia de verdad, no es una preferencia por la longitud:

| Lo que premia la tarea | Gana la larga | n |
|---|---|---|
| elaboración (explica X) | **100,0%** | 27 |
| concisión (resume, mensaje de commit, copy de error) | 68,5% | 27 |

Veintisiete de veintisiete. Todos los jueces, todos los generadores, los dos órdenes. Sumando las tiradas del piloto son 45 de 45 entre seis jueces de tres familias. Si algo aquí merece llamarse ley, es eso: **en una tarea que invita a elaborar, la respuesta larga gana siempre.**

### Donde me equivoqué

El piloto encontró algo mejor que eso, y lo escribí: en resumen la preferencia *se invertía* —los jueces elegían la versión corta y lo decían explícitamente en sus razones ("forma genuinamente condensada, mientras que B es esencialmente una paráfrasis completa")—. La conclusión redonda era que los jueces infieren el objetivo implícito de la tarea, así que "cuidado con el sesgo de longitud" es la instrucción equivocada.

No replicó. Entre familias, la misma sonda de resumen marca 72,2% a favor de la larga, y la categoría de concisión se queda en 68,5%: por encima del azar, no por debajo. Desglosado por juez, el efecto del piloto era un solo modelo:

| Juez | elaboración | concisión |
|---|---|---|
| GPT-5.5 | 100% | 55,6% |
| Grok-4.3 | 100% | 72,2% |
| Claude Sonnet 4.6 | 100% | 77,8% |
| *piloto:* Opus 5 | 100% | 66,7% |
| *piloto:* Sonnet 5 | 100% | **0,0%** |
| *piloto:* Haiku 4.5 | 100% | 50,0% |

Seis jueces. Uno de ellos prefirió la respuesta corta absolutamente siempre y arrastró un agregado de tres jueces por debajo del 50%, que yo publiqué como hallazgo general. La versión corregida es más estrecha: los jueces premian la elaboración en todas partes, y el premio simplemente *se debilita*, con mucha varianza entre jueces, cuando el criterio implícito de la tarea es comprimir. Uno de cada seis jueces invirtió de verdad.

Mantengo los dos informes en el repo, el piloto primero, porque el modo de fallo es la parte útil: un titular confiado sacado de tres jueces de una familia, retirado en cuanto seis jueces de tres familias tuvieron algo que decir.

## 5. En tareas subjetivas los jueces coinciden al nivel del azar

| Pareja de jueces | Objetiva | Media | Subjetiva |
|---|---|---|---|
| GPT-5.5 vs Grok-4.3 | +0,41 | +0,32 | −0,01 |
| GPT-5.5 vs Claude Sonnet 4.6 | +0,31 | +0,35 | −0,03 |
| Grok-4.3 vs Claude Sonnet 4.6 | +0,20 | +0,02 | +0,05 |

Kappa de Cohen: 1,0 es acuerdo perfecto, 0,0 es azar. En las tareas subjetivas las tres parejas son indistinguibles del azar. Dos jueces frontera evaluando la misma comparación subjetiva coinciden exactamente tanto como dos monedas al aire.

Este es el número que hay que quedarse si solo te quedas con uno. Un panel de jueces se supone que promedia las manías individuales, pero promediar tres jueces que coinciden al azar no te da una señal robusta: te da una señal aleatoria más suave. En dimensiones subjetivas, lo honesto no es meter más jueces. Es dejar de fingir que esa dimensión es medible con un juez y buscar un proxy que sí lo sea: si el usuario volvió, si el ticket se reabrió, si la PR se mergeó.

## Qué haría yo con esto

- **Empareja el juez con la dimensión, no con un leaderboard.** Dimensión objetiva y comprobable → cualquier juez competente, el self-preference es casi cero. Dimensión subjetiva → asume que el juez es un participante.
- **Nunca uses un juez de una familia que estás evaluando en una dimensión subjetiva.** De +30 a +48 puntos porcentuales no es un error de redondeo, y el cegado no lo elimina.
- **Corre los dos órdenes. Siempre.** No porque todos los jueces prefieran lo primero, sino porque uno de cada tres aquí lo hizo, y el intercambio es lo que te dice cuál.
- **Criba al juez antes de fiarte de él.** La tasa de vuelco sobre ~20 comparaciones cuesta casi nada y habría descalificado a Grok-4.3 en diez minutos.
- **Desconfía de cualquier estadístico de longitud sin control** — incluido uno que diga que tu juez no tiene sesgo de longitud.
- **Si tus jueces coinciden al nivel del azar, el problema es la dimensión, no el panel.**

## Qué no demuestra esto

Un modelo por familia, y los niveles no están emparejados: Azure no tenía cuota para un Claude actual en el momento de la tirada, así que el asiento de Anthropic lo ocupa Sonnet 4.6, una generación por detrás de los otros dos. La preocupación evidente es leer una diferencia de capacidad como un efecto de familia. Dos cosas empujan en contra: el modelo más antiguo no es el peor clasificado en el agregado (lo es Grok-4.3), y los tres deltas de self-preference caen a menos de 7pp unos de otros. Pero la versión limpia de este experimento usa modelos del mismo nivel, y esta no lo es.

Además: GPT-5.5 no corrió a temperatura 0, porque se niega. Quince tareas y seis sondas de longitud son 2,5× el piloto y siguen siendo pocas: todos los intervalos de aquí son anchos. Es una sola tirada, sin repeticiones que separen la inestabilidad del juez del ruido de muestreo. Y no se ejecutó nada: incluso las tareas objetivas se evaluaron leyendo, deliberadamente, porque el objetivo era medir al juez. Donde puedas correr los tests en su lugar, corre los tests.

Nada de eso cambia la forma del resultado. Tres jueces miraron las mismas 45 comparaciones y produjeron tres rankings distintos, y la distancia entre ellos era máxima justo donde la respuesta era cuestión de gusto — que es exactamente donde los equipos recurren a un juez LLM para empezar.

---

*Harness, juicios en crudo y los dos informes: [experiments/judge-bias](https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias). Trabajo previo que merece la pena leer: [Zheng et al. sobre sesgo de posición, verbosidad y auto-preferencia](https://arxiv.org/abs/2306.05685), [Wang et al. sobre sesgo de posición](https://aclanthology.org/2024.acl-long.511/), [Panickssery, Bowman y Feng sobre auto-reconocimiento y self-preference](https://arxiv.org/abs/2404.13076), y [Dubois et al. sobre evaluación con control de longitud](https://arxiv.org/abs/2404.04475).*
