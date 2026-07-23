---
title: "La muerte del prompt engineer"
description: "Una conjetura abierta 30 años cayó con prompts que decían 'haz un breakthrough' y 'sigue'. El oficio de escribir el prompt perfecto se está muriendo, y algo más interesante ocupa su lugar."
pubDate: 2026-07-25
tags: ["IA", "Prompt Engineering", "Agentes", "Tendencias"]
lang: es
translationKey: death-of-prompt-engineering
heroImage: "/blog/death-of-prompt-engineering.png"
---

El mes pasado alguien refutó una conjetura de teoría de grafos que llevaba unos treinta años abierta. La conjetura de Dinitz–Garg–Goemans es falsa: existe un grafo cuyo flujo fraccional cuesta 58, mientras que cualquier flujo no divisible —incluso permitiendo una violación de capacidad de hasta 15— cuesta al menos 60. El contraejemplo salió de una sesión de chat con GPT-5.6 Pro.

Y aquí está la parte que debería frenarte. Los prompts que lo produjeron decían, textualmente (en su inglés original), esto:

> "Construct a counterexample to general (non-planar) case of Dinitz Garg Goemans conjecture. You should do a breakthrough and find a structured counterexample."
>
> "please continue research and find a complete unconditional counterexample"
>
> "Continue the search. Have a clear strategy obtained from deeper understanding of the problem structure."
>
> "it's enough of partial results. let's finish with a complete unconditional counterexample"

Eso es el prompt engineering. *Haz un breakthrough. Simplemente continúa. Basta de parciales, terminemos.* Esa misma semana circuló un meme que lo capturaba a la perfección:

![Meme titulado "Math now" con una fila de caras brainlet cada vez más desquiciadas rotuladas "do a breakthrough", "continue", "just do it" y "find the proof", sobre un tweet que dice "So another long-standing open conjecture was disproved by AI."](https://www.javieraguilar.ai/blog/conjecture-disproved-meme.jpg)

*Fuente: [@Merkaloid](https://x.com/Merkaloid) citando a [@mattshumer_](https://x.com/mattshumer_) en X.*

Es una broma. Y también es la descripción más honesta del estado del arte que he visto este año.

Aquí murió algo en silencio, y no fue la conjetura. Fue el prompt engineering.

## Qué murió exactamente

No el prompting. Prompting —pedirle a un modelo lo que quieres— es más central que nunca. Lo que murió es el prompt engineering como *artesanía del artefacto*: la creencia de que el valor vivía en la redacción.

Durante un par de años esa creencia tuvo toda una economía alrededor. Plantillas. Preámbulos de `Eres un experto…`. Andamios few-shot que ajustabas como hiperparámetros. Trucos de delimitadores y conjuros de "piensa paso a paso". Marketplaces de prompts. Ofertas de "Prompt Engineer" a seis cifras, como si la habilidad fuera una profesión estable y no un artefacto temporal de los modelos débiles. Hace unos meses escribí un artículo que listaba el prompt engineering, sin ironía, como una de las skills clave de cara al futuro. Estaba describiendo un blanco móvil y no lo sabía.

La señal está en el ejemplo matemático. Si el prompting siguiera siendo una artesanía del artefacto, refutar una conjetura de treinta años exigiría el prompt más exquisitamente diseñado jamás escrito. En cambio, bastó "haz un breakthrough". La redacción no aportaba casi ninguna información. Todo vino del modelo y del bucle.

## La versión cotidiana: la divagación

No hace falta una conjetura abierta para verlo. Andrej Karpathy describió la versión ordinaria en un tweet que Carlos Santana amplificó con el marco exacto: que Karpathy no descubría nada, solo ponía en voz alta lo que la práctica ya hacía en silencio.

> "Un patrón que me resulta útil trabajando con LLMs es una buena sesión larga de divagación… me gusta echarme hacia atrás, cambiar a /voice y simplemente divagar durante unos 10 minutos, un caos total, todo vale, flujo de conciencia puro… descubro que los LLMs son de algún modo muy buenos reconstruyendo divagaciones largas e incoherentes, y a menudo su eco de tu propia maraña de pensamientos sale bastante más limpio de lo que empezaste."

Si lo has hecho, conoces la sensación: dejas de componer y empiezas a *gesticular*. Sueltas un caos y el modelo te devuelve algo más coherente de lo que metiste. Este mismo artículo empezó como una divagación de voz de diez minutos, con sus faltas y todo, y por eso puede terminar describiéndose a sí mismo.

Eso es lo contrario del prompt engineering. No estás curando el input. Estás confiando en que el sistema reconstruya la intención a partir del ruido.

## Por qué murió: el harness se comió el trabajo

Dos cosas mataron al artefacto.

La primera es el **harness**. Los agentes modernos de código e investigación no se quedan esperando una petición perfectamente especificada. Buscan en tu entorno, recuperan los archivos relevantes, arrastran memoria entre turnos y ejecutan bucles agénticos que recopilan el contexto que antes le metías a mano. El trabajo que hacía el prompt engineering —ensamblar exactamente los bits correctos en exactamente el orden correcto— quedó absorbido por el tooling. Le das un párrafo mal escrito; el harness va y encuentra el resto.

La segunda es la **capacidad bruta**. Los modelos ya son lo bastante buenos como para reconstruir la intención de un input malo, y para seguir cuando la instrucción es solo "continúa". En el caso de la conjetura apenas queda prompt engineering al que señalar: lo sustituye la *iteración*: repetir "sigue, ahora termina" mientras el agente descompone el problema por su cuenta. La inteligencia se movió de la frase al modelo y al bucle que lo rodea.

## Qué NO murió — y esta es la parte importante

Sería mentira cerrar con "diverga y la máquina hace todo lo demás". Para los problemas de verdad difíciles, el esfuerzo no desapareció; cambió de forma.

Detrás de "haz un breakthrough" sigue habiendo una persona que distingue un resultado real de uno plausible. Cuando [escribí un paper de investigación con IA](/es/blog/writing-a-research-paper-with-ai), la disciplina que importaba no era la redacción: era separar lo que se podía *demostrar* de lo que solo se podía *medir*, y negarse a difuminar los dos. En una sesión de planificación un modelo garabateó mal una nota sobre topología, afirmando que un anillo en el plano necesitaba una dimensión más. Lo pillé porque es mi campo, no porque hubiera escrito un prompt ingenioso. El modelo puede hacer la búsqueda; tú sigues teniendo que saber cuándo la respuesta es real.

Y para el trabajo más difícil cada vez recurres no a un prompt mejor sino a una **estructura** —una skill, un harness— que fuerza al modelo a probar varias estrategias, descomponer el problema en partes más pequeñas o lemas, correr experimentos, escribir tests, revisar su propio output, mantener un estándar de rigor. Ese andamiaje es el sucesor de la plantilla de prompt. No es una frase mágica; es un proceso. La conjetura tampoco cayó por un mensaje afortunado: cayó por un bucle que insistió en el rigor hasta que un resultado parcial se volvió completo.

Así que la habilidad no se esfumó. Se movió — de las *palabras* al *encuadre, la dirección y la verificación*. El término de Karpathy para la meta es el "mind meld": alinear al modelo con lo que realmente quieres decir, para tener que corregirlo menos a partir de ahí. Ese es el oficio ahora. La línea de tendencia es inequívoca: cada generación hace más con menos, y la parte que puedes dejarle al modelo no para de crecer.

## El esfuerzo no desapareció — subió de altitud

Si el prompt engineering se está muriendo, no es porque el engineering se haya ido. Es porque subió por la pila. La palanca solía estar en el nivel de la frase. Ahora está en el nivel del *sistema*: a qué modelo le entregas una tarea, si planeas con uno fuerte y ejecutas con uno barato, qué estructura envuelves alrededor del bucle.

Eso es una disciplina propia —la que yo diría que está reemplazando al prompt engineering, no simplemente sobreviviéndolo— y merece su propio artículo. Por ahora la versión corta es esta: el mejor "prompt" de 2026 es una divagación de diez minutos a un sistema que ya conoce tu código, y la habilidad que vale la pena tener es saber qué construir a su alrededor.

El prompt nunca fue lo importante. Que la máquina te entendiera sí.

---

*Este es el primero de dos artículos sobre cómo el trabajo de "engineering" en IA no para de mudarse de sitio. El segundo va sobre **routing engineering** — elegir qué modelo y cuánto razonamiento gastar en cada tarea. Ver también [El software se está disolviendo en el modelo](/es/blog/software-dissolving-into-the-model).*
