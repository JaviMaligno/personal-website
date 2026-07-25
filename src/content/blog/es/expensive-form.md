---
title: "Había construido un formulario caro"
description: "Defendí que un journey conversacional aportaba poco sobre un formulario bien diseñado. La decisión fue la contraria, así que lo construí — y el feedback del cliente zanjó la discusión mejor de lo que yo habría podido."
pubDate: 2026-07-28
tags: ["Agentes IA", "Producto", "LangGraph", "UX"]
lang: es
translationKey: expensive-form
heroImage: "/blog/expensive-form.png"
---

Esta discusión la perdí antes de construir nada.

Estábamos sustituyendo un flujo heredado de tickets para presentar informes regulatorios — ese tipo de formulario interno que el personal de primera línea detesta y rellena mal. Mi posición, dicha más de una vez, era que convertir todo el journey en una conversación aportaba poco sobre un formulario bien diseñado. Lo que yo habría construido es un formulario con UX de verdad buena, más un asistente al lado para las dudas que la gente tiene realmente — *¿esto es reportable?*, *¿en qué categoría entra?* — capaz de interactuar con el formulario en lugar de sustituirlo.

La decisión fue la contraria, y era una decisión defendible: un journey conversacional diferencia, funciona en una demo y los clientes lo piden por su nombre. Así que dije *vale, lo hago y vemos qué pasa*.

Vimos qué pasó. Había construido un formulario caro.

## Construir bien lo que no defiendes

Quiero ser preciso aquí, porque «no estaba de acuerdo y lo hice igual» puede leerse como cinismo o como falta de carácter, y no creo que fuera ninguna de las dos.

Una discusión interna sobre si a los usuarios les va a gustar algo no se resuelve discutiendo internamente. Dos personas con modelos plausibles del usuario repiten sus premisas cada vez más alto, y gana quien tiene más autoridad. Eso no es un mal proceso porque ganara la persona equivocada, sino porque **nadie aprende nada**. La salida es poner la cosa delante de un usuario real rápido, construida lo bastante bien como para que su reacción sea sobre la idea y no sobre tu ejecución a medias.

Así que tenía que estar bien hecho. Si hubiera entregado una versión deliberadamente mediocre, cualquier feedback malo habría sido sobre la mediocridad, y no habría demostrado nada.

Tampoco partí de cero: un compañero había hecho el prototipo inicial en LangGraph y yo lo cogí desde ahí. Merece decirse claramente, porque las mejoras que voy a describir se hicieron sobre los cimientos de otra persona.

## Lo que entregamos

La arquitectura no era descuidada. Era un motor de pipelines configurado en YAML: un DAG de fases, unos cuantos tipos de nodo, routers condicionales, triggers globales capaces de redirigir el flujo, puntuación de cumplimiento recalculada tras cada fase.

Cada fase era dueña de una porción del formulario. Hacía su pregunta, validaba la respuesta, la confirmaba, avanzaba. Para un tipo de informe salían unos **siete pasos interactivos**: siete turnos en los que el usuario esperaba a un modelo, leía una pregunta, contestaba una cosa y confirmaba.

Y déjame defender ese diseño, porque sus propiedades son reales.

Una fase por porción te da **validación en el punto de entrada**: cazas una fecha malformada mientras el usuario aún está pensando en fechas. Te da un **modelo de progreso**: como las fases son explícitas, tienes barra de progreso, analítica por fase y un panel de administración que muestra exactamente dónde se atascó un envío. Hace el flujo **legible** — alguien nuevo lee el YAML y sabe qué pasa. Y hace al agente **seguro por construcción**: no puede saltarse un campo obligatorio, porque el grafo no le deja.

No renuncié a nada de eso. Eso importa para lo que viene después.

## El feedback que lo zanjó

El responsable de compliance del cliente lo probó y dijo que *se parecía demasiado al sistema que veníamos a sustituir: lento y complejo*.

Esa frase hizo en una reunión lo que yo no había conseguido en varias. Nadie ganó la discusión interna: la terminó el usuario. Y lo útil no es que se confirmara mi premisa, es que pasamos a tener una queja **concreta** en lugar de dos opiniones enfrentadas. «Lento y complejo» es diagnosticable. «Creo que a los usuarios no les va a gustar» no lo es.

Ese feedback me dio carta blanca para reconstruirlo bien. Que es la razón real por la que me alegro de haber entregado la versión que no defendía: mi alternativa también habría sido una suposición. Lo que conseguimos en su lugar fue evidencia, y la evidencia te compra permiso.

## Por qué un formulario gana esa carrera

Este es el mecanismo. Si la interacción es una secuencia fija de preguntas, el formulario es simplemente la mejor interfaz:

- Ves **todos los campos a la vez**, así que sabes cuánto te va a llevar. Un chat esconde la longitud de la cola, y por eso «¿cuántas preguntas más?» es el pensamiento más frecuente frente a un bot guionizado.
- Los rellenas **en cualquier orden**, saltas, vuelves. Un agente secuencial impone un orden que existe por comodidad del motor, no tuya.
- **Tabulas entre campos** en milisegundos. Cada turno conversacional cuesta una ida y vuelta a un modelo: a veces un segundo, a veces diez. Multiplica por siete.
- No cuesta **nada por envío**. Nuestra versión facturaba tokens por el privilegio de ser más lenta.

Así que el chat guionizado pierde en velocidad, en previsibilidad y en coste, y su única compensación es que parece moderno. Una envoltura conversacional alrededor de una secuencia fija es un formulario con peor ergonomía y factura variable.

## El diagnóstico: la secuencialidad, no los widgets

Mi primer instinto fue la presentación — los campos se veían torpes, las confirmaciones eran verbosas, quizá unos widgets mejores dentro del chat lo arreglarían. Ese instinto estaba equivocado, y es la parte interesante.

El coste no estaba en ningún paso concreto. Estaba en **que hubiera pasos**. Siete turnos son siete turnos, sean bonitos o feos.

Y luego el detalle genuinamente humillante. La maquinaria de *«pregunta solo lo que falta»* ya existía. Cada fase podía calcular sus campos ausentes y preguntar solo por ellos. Solo que operaba **dentro del ámbito de la fase** — así que cuando un usuario abría escribiendo un párrafo rico describiendo todo lo ocurrido, la fase uno extraía sus dos campos y el resto de ese párrafo se descartaba. El usuario ya nos había dado la mayoría de las respuestas. Las tirábamos y luego se las pedíamos de una en una.

El sistema no fallaba al entender al usuario. Entendía y luego olvidaba, porque la unidad de extracción era la fase y no la conversación.

## Primera pasada: arreglarlo dentro del grafo

Diagnosticarlo no me dio derecho a una reescritura, y no debía dármelo.

Esta es la parte que la gente se salta al contar estas historias, así que voy a ser explícito. Había un *producto*. Estaba construido, desplegado, delante de clientes, y funcionaba — mal, pero funcionaba. Nadie tira eso a la basura por un comentario y la convicción de un ingeniero. El siguiente paso razonable, y el que quería el negocio, era ver hasta dónde podía llegar lo que ya existía.

Ese instinto acierta más veces de las que a los ingenieros nos gusta admitir. Los arreglos incrementales son baratos, entran esta semana en lugar del trimestre que viene, y si hubieran bastado nos habríamos ahorrado una reescritura entera. La única forma de saber si una reescritura es necesaria es agotar primero lo que no lo es.

Así que: dos añadidos al grafo existente, ambos detrás de un flag opt-in para que otros flujos conservaran su comportamiento y yo tuviera cero riesgo de regresión con los clientes que no pedían esto.

**Un nodo de intake global.** Antes de la primera fase, el agente pide el relato con las palabras del usuario. Después hace una *única* llamada de extracción estructurada contra la unión de todos los campos que el flujo completo puede extraer, y escribe todo lo que encontró con confianza.

```python
# Secuencial: el grafo decide el orden, una pregunta cada vez
START → fase_1 → fase_2 → ... → fase_7 → END

# Conversacional: extrae todo del relato y luego visita
# solo las fases que siguen teniendo huecos
START → intake → primera_fase_no_satisfecha → ... → END
```

Tres detalles importaron más que la idea:

- **El conjunto extraíble se calcula, no se escribe a mano.** Es la unión de los campos que escriben las fases que pueden satisfacerse desde prosa. La extracción documental, la subida de ficheros y la firma están *explícitamente excluidas*: ningún relato produce un documento escaneado.
- **Reutiliza las definiciones reales de campo**, para que en el intake corran los mismos validadores que en las fases. Pasar un esquema vacío y «extraer texto sin más» te deja datos sin validar y pasos de más.
- **Nunca adivina.** Si el relato no da un campo con claridad, el intake lo deja vacío. En una lista de opciones, una selección equivocada en un formulario regulatorio es peor que una pregunta más: por un hueco se pregunta, un valor equivocado se envía.

**Saltar las fases satisfechas.** Las fases que exigen interacción real (subida, firma) siempre corren. Las de datos se bifurcan: todos los campos presentes y nada crítico → avanza en silencio; todos presentes pero algo crítico → una confirmación mínima; con huecos → pregunta solo por los huecos.

Resultado: **de unas siete interacciones a tres o cuatro.** Narrar, confirmar lo de alto riesgo, subir, firmar.

Fíjate en lo que sobrevivió. Las fases siguen existiendo, así que la barra de progreso, la analítica, el panel y los validadores siguen funcionando. No desmonté el DAG para volverme conversacional: le puse un nodo delante y dejé que las fases renunciaran a preguntar. La alternativa que rechacé por escrito era colapsarlo todo en un único nodo adaptativo, que da elegancia y cuesta todas las propiedades estructurales de antes.

## Segunda pasada: lo que la reescritura exigió de verdad

La primera pasada trajo una mejora real, y no fue suficiente. Tres o cuatro turnos es mejor que siete, pero la forma de la cosa seguía siendo un grafo desfilando por fases con una puerta de entrada más lista atornillada delante.

Volverse agéntico de verdad significó **un backend completamente nuevo**. No un refactor, sino otra forma de sistema, donde en lugar de un grafo decidiendo el orden de las preguntas hay un agente con herramientas sobre un estado autoritativo en servidor que decide qué hacer a continuación.

Una reescritura de ese tamaño no se gana nunca solo con argumentos técnicos. Hicieron falta dos cosas: el feedback del cliente, que volvió el problema concreto, y después un cambio de rumbo en la empresa que hizo aceptable apostar por algo nuevo. La evidencia construyó el caso; el apetito de riesgo le dio dónde aterrizar. Las dos tenían que ser verdad a la vez.

Esa es la parte que generalizaría. La ventana en la que una organización acepta una reescritura se abre y se cierra por razones que no tienen nada que ver con tu diagrama de arquitectura, y suele ser corta. Lo que controlas es estar listo cuando se abre — que en mi caso significó tener ya especificado el diseño que llevaba defendiendo, porque me había pasado la pasada incremental aprendiendo exactamente qué restricciones importaban.

De esa reconstrucción salieron dos cosas que defendería en cualquier sitio.

**UI generativa dentro del chat, que fue idea mía y la parte a la que más cariño le tengo.** Si el agente tiene que pintar las opciones como texto, has reinventado el desplegable con más latencia. En su lugar, el chat renderiza widgets interactivos reales — chips, selectores, paneles — para que el agente pueda proponer un valor estructurado y el usuario lo ajuste directamente. He escrito aparte sobre [por qué ese patrón importa y el protocolo que lo está estandarizando](/es/blog/ag-ui-third-protocol).

De ahí salió mi regla favorita de todo el sistema. Cuando el agente pregunta por los huecos restantes, los parte en dos: los de texto libre y fecha se preguntan directamente, consolidados en una sola pregunta natural, pero los campos con lista fija de opciones reciben otra instrucción — **infiere tu mejor opción de lo que el usuario ya te ha contado y deja que la ajuste en el panel; no le recites las opciones**. La interceptación vive en la herramienta que calcula los campos ausentes, no en el prompt, porque ese es el punto exacto en que el modelo decide qué preguntar.

Si construyes sobre un canal de mensajería, esto es estructural. Nadie quiere leer ocho opciones numeradas en WhatsApp.

**Libertad para entender, ceremonia para actuar.** El intake puede ser tan abierto como quieras; la escritura no. Cuando el agente va a enviar algo con consecuencias en el mundo real, quiero un paso estrecho, explícito y aburrido. En el backend nuevo ese gate se comprueba en código: un envío se rechaza si no se ofreció en un turno *anterior*, y cualquier corrección posterior anula la aprobación pendiente — porque si el contenido cambió, lo que la persona aprobó ya no es lo que se enviaría. El mismo principio que en los [guardarraíles sobre los que insisto tanto](/es/blog/typescript-ai-agent-guardrails): la restricción tiene que vivir donde el modelo no llega.

## La abstracción que esperé a construir

Aquí es donde esto fue más allá de un cliente. Un backend nuevo por caso de uso no escala, y el movimiento obvio era un **generador**: un backend que toma la configuración de un caso de uso — prompts, los modelos de los formularios, la base de conocimiento — y produce el flujo agéntico a partir de ella.

La disciplina estuvo en el momento. Esperé deliberadamente a tener **dos flujos genuinamente distintos** funcionando antes de generalizar: onboarding de cuentas de empresa en banca y reporte de incidencias regulatorias. Dominios distintos, formularios de otra forma, modos de fallo distintos.

Dos razones, que en realidad son la misma:

- **Dos ejemplos disímiles te dicen qué partes son variables de verdad.** Si abstraes desde uno, construyes una capa de configuración con la forma exacta de tu primer cliente y luego la retuerces dolorosamente para el segundo. Cada palanca que expuse tenía que ser una palanca que los dos flujos giraran de forma distinta.
- **Dos ejemplos también demuestran que la abstracción vale la pena.** Con un solo flujo, «despliega otro backend» es la respuesta más barata y la honesta. El generador solo se gana su complejidad cuando puedes demostrar que la alternativa son N backends.

Ese es el trabajo actual, y existe porque la reescritura ocurrió dos veces con formas distintas, no porque alguien dibujara un diagrama de plataforma al principio.

## No hay que hacer chat de todo

Preferiría no sobrecorregir esto hacia lo conversacional-para-todo, porque mi posición original sigue en pie y la frontera es la parte útil.

Quédate con el formulario cuando los campos son **pocos y conocidos**, cuando el usuario ya tiene el dato **delante**, cuando la entrada es intrínsecamente **no narrativa** (subir un fichero, firmar, elegir en un calendario), o cuando el flujo lo usan **a diario personas entrenadas** que memorizaron el orden de tabulación hace mucho. Un usuario experto le gana en velocidad a una interfaz conversacional siempre.

Ve al agente cuando la entrada llega como **un relato y no como un registro** — una incidencia, una queja, un síntoma, una petición —, cuando el conjunto de campos es **grande pero poco relevante** para cada caso concreto, o cuando quien lo rellena es **ocasional y no entrenado** y el vocabulario del formulario no es el suyo.

Y ojo: la opción intermedia que defendí al principio no se ha ido a ninguna parte. Un buen formulario más un asistente que lo vea y pueda actuar sobre él es a menudo la respuesta correcta, y es la que nadie lleva a una demo.

## La pregunta que me hago primero ahora

Antes de construir cualquier cosa conversacional: *¿qué le permite hacer esto al usuario que el formulario no?*

Si la respuesta es «es más simpático», construyo el formulario. Si la respuesta es «el usuario puede describir su situación como le salga y el sistema averigua a qué campos corresponde», ahí hay algo real — y el trabajo de diseño consiste en extraer una sola vez, preguntar solo lo que falta de verdad y no recitar jamás las opciones en voz alta.

El resto del tiempo estás construyendo un formulario caro. A veces hay que construirlo igual para demostrarlo, y si lo haces, constrúyelo lo bastante bien como para que el feedback sea sobre la idea.
