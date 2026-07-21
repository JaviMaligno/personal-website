---
title: "Escribir un paper de investigación con IA: dónde se nota de verdad la inteligencia del modelo"
description: "El proceso real detrás de un preprint asistido por IA — y por qué la frontera más difícil no es la prosa, sino planear la ciencia, donde un modelo más capaz deja de ser una comodidad y pasa a ser lo que permite que el trabajo llegue más lejos."
pubDate: 2026-07-21
tags: ["IA", "Investigación", "Escritura", "Claude", "GPT"]
lang: es
translationKey: writing-a-research-paper-with-ai
heroImage: "/blog/writing-a-research-paper-with-ai.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/2607.14169"
  - label: "My earlier maths preprint"
    url: "https://arxiv.org/abs/2307.11414"
---

Este año publiqué un preprint — [*When a Verified World Model Still Loses*](https://arxiv.org/abs/2607.14169). Me llevó unas dos semanas, en solitario. Años antes de usar IA, publiqué el primero — mi [tesis de matemáticas](https://arxiv.org/abs/2307.11414): un teorema, una demostración y más de dos años de trabajo con una universidad y un proyecto financiado detrás.

Ese contraste es el punto de partida honesto. Es tentador leerlo como "la IA me hizo 50× más rápido". No fue así, y la última sección de este artículo va precisamente de desenredar por qué. Pero algo real sí cambió — y lo interesante no es la escritura. Es *dónde* resultó importar la inteligencia del modelo.

Un apunte previo: ya escribí sobre [escribir un ensayo con IA](/es/blog/writing-an-essay-with-ai-codex-vs-claude-code), donde la frontera dura era la prosa — el tono, el ritmo, el filo retórico. La investigación es distinta. La prosa es la parte fácil. La difícil es planear la ciencia y revisarla como un par, y ahí es exactamente donde un modelo más capaz deja de ser una comodidad y pasa a ser lo que permite que el trabajo llegue más lejos.

## El reparto real del trabajo

Voy a ser honesto sobre quién hizo qué. La prosa del paper es en gran parte de la IA; apenas toqué la redacción. Esa no es la parte interesante, sin embargo, y no es donde estuvo el trabajo.

El trabajo estaba aguas arriba de la escritura:

- **La idea vino de leer**, no de un prompt que dijera "dame un paper" — en concreto, de una lectura asistida por IA del paper de DeepMind *Code World Models for General Game Playing*. Trabajar un paper denso con un modelo que puede responder "¿por qué se sigue este paso?" cuando lo necesitas es una actividad distinta a leer en solitario; ahí fue donde tomó forma la pregunta que acabó siendo mi preprint.
- **Experimentos ejecutados por agentes.** Los pipelines de síntesis, los barridos, las arenas — montados y ejecutados por agentes, conmigo llevando el timón.
- **Una disciplina que mantuve en cada afirmación fuerte: separar lo *demostrable* de lo *medido*, y decir cuál es cuál.** Donde un enunciado podía *ganarse* — un teorema de identificabilidad, una cota de cobertura — fui a ganarlo. Donde solo podía medirse, lo reporté como medido, con intervalos, y me detuve ahí.

Así que sí, la IA escribió el paper. Pero la escritura nunca fue el cuello de botella. Se parece más a llevar un laboratorio pequeño donde los técnicos son rápidos, incansables y, de vez en cuando, se equivocan de formas interesantes — y el valor que aporto no es teclear.

## Dónde se nota la inteligencia del modelo

El ejemplo más nítido que tengo viene de un **segundo paper, todavía sin publicar** — un setting de control continuo — así que lo que sigue es una nota sobre el proceso, no sobre los resultados.

Los modelos fueron cambiando mientras trabajaba, y el orden importa. Empecé con **Opus 4.8** para planificar y **GPT-5.5** como segundo lector; funcionaba, pero costaba muchas rondas de preguntas y correcciones mías. En cuanto salió **Fable 5** me cambié, y se convirtió rápido en mi opción por defecto — la planificación del día a día fue más fluida, con menos correcciones, y ofrecía direcciones genuinamente útiles en vez de solo ejecutar las mías. El único muro que sigo encontrando son los límites de suscripción de Fable. Luego llegó **GPT-5.6** y se convirtió en un segundo revisor aún mejor — el que me salva precisamente cuando me quedo sin Fable, porque en la práctica puedo sustituir uno por otro. Sus revisiones se leen como un peer review de verdad.

Una de esas pasadas de revisión de GPT-5.6 es el ejemplo más claro que tengo de lo que significa "planear ciencia" como capacidad. Dos hallazgos de ella.

### Un modelo corrigiendo el error de otro modelo

Durante la planificación, le pedí a mi agente Opus 4.8 que dejara anotada una línea futura — un uso más intenso de topología en dimensiones altas — para no olvidarla. Lo confundió: escribió que ciertas formas en 2D (anillos — regiones con un agujero) exigirían pasar a un estado de dimensión mayor. Eso es falso. Un anillo vive perfectamente en el plano y ya tiene topología no trivial. Yo lo sé; es mi campo. Pero no fui yo quien lo escribió — fue el modelo, y coló el error al malinterpretar lo que le había pedido.

La corrección vino de un modelo distinto. Cuando GPT-5.6 revisó el plan, lo primero que señaló fue justo esto:

> Un anillo vive perfectamente en 2D y tiene homología no trivial; no requiere aumentar la dimensión del estado.

Un modelo más débil introdujo un error conceptual al malinterpretar mi intención; uno más fuerte lo cazó de una lectura. Esa es la versión pequeña y legible. La siguiente importa más.

### Un experimento que no podía responder su propia pregunta

Todo el objetivo del experimento era aislar una variable — la curvatura de una frontera — y medir cómo de bien podía un modelo reconstruirla a partir de datos muestreados. El plan fijaba una cantidad (con qué frecuencia los datos aleatorios tocan la región) y declaraba que eso dejaba "solo la geometría" como variable libre. La revisión de GPT-5.6 lo desmontó:

> Fijar *r* no deja "solo geometría" como variable. [...] Con el diseño actual, una curva observada no permitiría atribuir el resultado específicamente a la curvatura.

Y reescribió el objetivo como una factorización —

> P(reparación) = P(el modo es visible) × P(la evidencia es geométricamente suficiente | visible) × P(el sintetizador lo representa | suficiente)

— y señaló que el plan solo controlaba el primer factor. En cristiano: **el experimento, tal como estaba diseñado, no podía responder su propia pregunta.** Eso no es editar prosa. Eso es planear ciencia — y es la capacidad que un salto de calidad de modelo realmente te compra.

Hasta propuso un experimento que yo no había planeado: un *baseline oráculo* que separa limpiamente "los datos no contienen suficiente información" de "el modelo no sabe representarlo". Un tercer paper ya estaba en mi hoja de ruta — idea mía, documentada antes de todo esto — y le había pedido al modelo que archivara ahí cualquier feedback digno de esa dirección en vez de embutirlo en el plan actual. Lo hizo, y lo hizo con citas reales. Un revisor que aparca sus buenas ideas en tu trabajo futuro en lugar de descarrilar la tarea que tienes delante está haciendo algo bien.

El antes/después está en git. El mensaje del commit de la revisión es, textual: *"redesign repair-vs-geometry per expert review — factorization, graph boundaries, symmetric metrics, oracle baseline, topology fix."* Casi la mitad del documento reescrita.

## No siempre es el modelo más listo — a veces es un segundo par de ojos

No todo avance es capacidad bruta. A veces el valor es simplemente un segundo par de ojos *distinto* — el otro modelo, o yo — cazando lo que la primera pasada se dejó. De vuelta en el **primer** paper, el historial de git está lleno de esto, registrado en los propios mensajes de commit:

- Un agente Claude que retransmitía la salida del pipeline se quejó de que los datos de fallo parecían truncados. Tenía razón — un paso de logging estaba cortando justo los números que el modelo necesitaba ver. Esa única queja destapó un confound que, una vez arreglado, convirtió un hallazgo endeble en uno que pude replicar en dos familias de modelos más.
- Una pasada de Codex cazó un overclaim que había sobrevivido a ediciones previas: una frase que decía que el pipeline "reproduce el mismo coste de juego" cuando los intervalos de confianza justo a continuación decían lo contrario.
- Y lo contrario del problema de las citas alucinadas que a todos preocupa: al pedirle una referencia que no tenía, el modelo se negó a fabricar una URL y dejó *"URL a proporcionar por el autor"* en su lugar.

Muchos de los hallazgos también fueron míos — la cuestión no es que los modelos sustituyan al revisor, sino que multiplican el número de pasadas independientes que una afirmación sobrevive antes de publicarse. Escribí más sobre esta complementariedad — cómo dos herramientas de IA discrepan de forma productiva — en [Escribir un ensayo con IA: Codex vs Claude Code](/es/blog/writing-an-essay-with-ai-codex-vs-claude-code).

## La parte honesta: no fue solo la IA

Volvamos a ese contraste de dos años a dos semanas. Varias cosas ajenas a la IA explican la mayor parte de ese salto, y sería deshonesto embolsármelo todo como multiplicador de la IA:

- **Matemática pura vs ML empírico.** Demostrar un teorema es intrínsecamente más lento y difícil que escribir un preprint empírico de ML. Son tipos de trabajo distintos.
- **Abstracción e inmersión.** El objeto de la matemática pura es más abstracto; empaparse de él lleva sencillamente más tiempo — y entonces tampoco tenía IA para acelerar esa inmersión, lo cual es un lugar más donde el proceso multiplica hoy.
- **Extensión.** Mi paper de matemáticas es aproximadamente el doble de largo.
- **Overhead institucional.** Un proyecto universitario financiado arrastra proceso — reuniones, coordinación, ciclos de revisión — que un preprint en solitario simplemente no tiene.

Normaliza por todo eso y el salto sigue siendo real, pero es un multiplicador sobre alguien que ya era capaz de hacer el trabajo, no un sustituto de la capacidad. Ese eje — de la matemática pura hacia el ML aplicado — es además, sencillamente, la historia de mi propio giro profesional, y este proyecto se sitúa justo encima.

## Lo que me llevo de verdad

- **La IA no eliminó la parte difícil; movió dónde vive la parte difícil.** Para mí dejó de ser "¿sé escribir y ejecutar esto?" y pasó a ser "¿es este el experimento correcto, y sobrevive esta afirmación al escrutinio?".
- **En esa parte difícil, la capacidad del modelo es la restricción vinculante.** La distancia entre un modelo que sabe planear ciencia — diseñar un experimento que responde su propia pregunta, revisar una afirmación como un par — y uno que no, es la distancia entre un paper que se atasca y uno que llega más lejos. Por eso Fable 5 es mi opción por defecto y GPT-5.6 mi revisor preferido.
- **La capacidad no es la única palanca.** Un segundo par de ojos, distinto — otro modelo, o yo — caza lo que la primera pasada no vio. La diversidad es su propia clase de inteligencia.
- **Lo que no se automatiza es el juicio del investigador.** Haber sido investigador es la parte que aquí soporta el peso: el rigor, el escrutinio, el reflejo de desconfiar de un resultado limpio, la costumbre de revisar una afirmación hasta que aguanta o se rompe, saber cuándo algo puede *demostrarse* frente a solo *medirse*. Esa es la misma función que da una institución de investigación — el peer review, un supervisor crítico, un laboratorio que discute contigo — pero funcionando con menos intermediarios y menos administración, y más ágil en cada paso útil.

---

*El primer paper, "When a Verified World Model Still Loses", está en [arXiv](https://arxiv.org/abs/2607.14169); mi preprint anterior de matemáticas está [aquí](https://arxiv.org/abs/2307.11414). Sobre separar lo que puedes verificar de lo que no: [Programación orientada a resultados](/es/blog/results-oriented-programming) y [¿Cuánto deberías seguir sabiendo?](/es/blog/how-much-should-you-still-know).*

*¿Te interesan las arquitecturas de agentes de IA? [Hablemos](/es/#contact).*
