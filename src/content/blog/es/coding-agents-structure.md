---
title: "Agentes de código y trabajo en equipo: ¿habilidades sociales o estructura?"
description: "Un benchmark reciente dice que los agentes de código no colaboran porque les falta inteligencia social. Pruebo otra hipótesis: les falta estructura — y encuentro que hacer de la integración el trabajo de un solo agente recupera la colaboración, mientras que los conflictos de merge sobre todo enmascaran fallos semánticos más profundos."
pubDate: 2026-07-01
tags: ["IA", "Agentes", "Evaluación"]
lang: es
translationKey: coding-agents-structure
heroImage: "/blog/coding-agents-structure.png"
---

> **Es un estudio terminado sobre una porción del benchmark, no el adelanto de uno.** Todas las condiciones corrieron hasta el final, las celdas de cabecera tienen tres seeds y audité el propio harness de evaluación — pero sobre un subconjunto de 19 tareas de las 652 de CooperBench, elegido porque podía correrlo limpiamente en dos tiers de modelo. El techo aquí es de *cobertura, no de confianza*: dentro de esta porción el patrón se replica; si se sostiene en el benchmark completo es la pregunta abierta.

Un benchmark reciente de Stanford, [CooperBench](https://arxiv.org/abs/2601.13295) ("Why Coding Agents Cannot be Your Teammates Yet"), reporta un resultado llamativo: si emparejas dos agentes de código potentes para repartirse una tarea, su tasa de éxito casi se *reduce a la mitad* frente a un solo agente haciendo el mismo trabajo total. Lo llaman la **maldición de la coordinación**, y su lectura es que lo que falta es *inteligencia social* — los agentes no usan el lenguaje para coordinarse de forma fiable, así que, argumentan, esto hay que *entrenarlo*, no arreglarlo con prompts.

Es un paper cuidadoso, y quiero ser justo con él: **deliberadamente** corren los agentes casi sin scaffolding, precisamente para medir la capacidad de coordinación *intrínseca*. Es una elección científica legítima. Pero me dejó con una pregunta de ingeniería que ellos dejan fuera a propósito:

> Los equipos humanos tampoco coordinan bien con *cero* proceso. A un equipo que se pisa constantemente no lo arreglamos con terapia — usamos **estructura**: ownership de código, contratos de interfaz, PRs secuenciales, alguien que integra. Entonces, ¿cuánto de la "coordination gap" es de verdad habilidades sociales, y cuánto es simplemente la ausencia de una estructura que a los agentes nunca se les dio?

## El montaje

Partí del [propio benchmark de CooperBench](https://github.com/cooperbench/CooperBench) (es open source) y reproduje el baseline: dos agentes, cada uno con una feature de la tarea, en contenedores separados pero **conectados por un canal de mensajería que pueden usar para coordinarse en cualquier momento** (el benchmark se lo da desde el principio), y sus parches se mergean después. Ese canal importa para todo lo que sigue: los agentes *siempre* pueden hablar — la pregunta abierta es si hablar basta. Luego añadí una **escalera de estructuras de coordinación**, ordenada de "advisory" (el agente puede ignorarla) a "impuesta" (el scaffold la garantiza):

- **Handshake (C1):** los agentes deben intercambiar un plan antes de que el scaffold les deje editar código. *(Analogía: una revisión de diseño antes de codear.)*
- **Ownership por fichero (C2):** cada fichero es de un agente; las ediciones al fichero de otro se revierten. *(Analogía: CODEOWNERS.)*
- **Ownership por rangos de línea (C2b):** versión fina — ambos pueden editar el mismo fichero, pero solo en regiones disjuntas. *(Analogía: no pisarse las funciones.)*
- **Pipeline secuencial (C3):** el agente A implementa la feature 1 y commitea; el agente B arranca *desde el código de A* y añade la feature 2. Sin concurrencia. *(Analogía: PRs pequeños y secuenciales sobre trunk.)*
- **Integrador (C4):** A y B trabajan independientes; un tercer agente reconcilia ambos parches. *(Analogía: un ingeniero de integración / revisor de PR.)*

El sentido de la escalera es separar "¿*hablaron*?" de "¿el proceso *les impidió chocar*?" — y encontrar la estructura *mínima* que ayuda.

## Resultados

**Primero las advertencias**, porque importan: son **19 parejas de tareas en 5 repositorios** — un subconjunto que pude correr limpiamente — no el benchmark completo. Pero corrí la escalera entera en **dos tiers de capacidad** (un `gpt-5.4-mini` de gama media y un `gpt-5.4` más fuerte), y las cuatro condiciones de cabecera las corrí **tres veces cada una**, así que puedo enseñar un rango en vez de un único número ruidoso.

| condición | mini | gpt-5.4 |
|---|---|---|
| solo (un agente, ambas features) | 14% [11–16] | 30% [21–37] |
| coop (dos agentes, libre) | 7% [0–11] | 7% [0–16] |
| coop + resolución justa de conflictos* | 7% [0–11] | 9% [0–16] |
| **secuencial (C3)** | **26% [21–37]** | **35% [32–37]** |
| **integrador (C4)** | **23% [21–26]** | **33% [26–42]** |
| handshake (C1)† | 0% | 0% |
| ownership por fichero (C2)† | 0% | 16% |
| ownership por línea (C2b)† | 0% | 0% |

<sub>Las celdas de cabecera son media [mín–máx] sobre tres seeds; †las condiciones impuestas son una sola tanda cada una (sin réplicas). *La eval del paper resuelve automáticamente los conflictos de merge triviales con un modelo pequeño antes de declarar fallo; la release open-source omite ese paso. Añadí un resolver equivalente (si acaso más potente) y re-puntué las condiciones concurrentes — detalles en "Bajo el capó".</sub>

Cuatro cosas destacan:

1. **La coordination gap se reproduce — y es mayor en el modelo fuerte.** Dos agentes en concurrencia (coop) puntúan por debajo de un agente haciendo la tarea entera (solo): 14%→7% en mini, 30%→7% en gpt-5.4. Agregando tiers y seeds la caída es sólida (McNemar pareado p=0.002); desglosada, es claramente significativa en el fuerte (p=0.002) y no en el flojo (p=0.39) — simplemente porque el solo de mini ya es bajo, así que hay menos que perder. La maldición de la coordinación muerde más fuerte donde un solo agente era de verdad competente.

2. **Dos estructuras la recuperan — y secuenciar hace más que recuperar.** El **pipeline secuencial (C3)** y el **integrador (C4)** superan a coop de forma contundente en ambos tiers (p<0.0001). Comparten mecanismo: **un solo agente acaba siendo dueño del estado final integrado** — B construye sobre el trabajo terminado de A, o un revisor reconcilia ambos parches en un único workspace. Pero no son equivalentes. Secuenciar no solo recupera el nivel del solo — en el modelo *flojo* lo **supera** (mini 26% vs 14%, por delante en las tres seeds, p=0.039), mientras que en el fuerte solo lo iguala (large 35% vs 30%, p=0.45). El integrador recupera sobre coop pero nunca supera al solo de forma significativa (p=0.23). En claro: descomponer la tarea para que el agente B se enfrente a "añade la feature 2 a un código que ya tiene la feature 1" es un problema *más pequeño* que "construye ambas a la vez" — y un problema más pequeño ayuda más a quien peor llevaba el grande.

3. **Así que la estructura interactúa con la capacidad — en los dos sentidos.** Esa es la parte de verdad interesante, y corta por dos lados. **Secuenciar ayuda más al modelo flojo** (lo eleva por encima de su propio solo; en el fuerte solo iguala al solo). **El ownership por fichero (C2) impuesto ayuda más al fuerte** — no recuperó nada en mini pero llegó al 16% en gpt-5.4. Dos interacciones de signo opuesto: aligerar la carga cognitiva rescata al modelo más débil, mientras que una regla estructural que hay que *saber aprovechar* premia al más fuerte. (Ambas son señales de una o pocas tandas sobre un subconjunto pequeño — direccionales, no zanjadas. Y la ventaja de C2 se encoge cuando puntúas los merges de coop de forma justa: ver el asterisco abajo.)

4. **Forzar la comunicación no hace nada — porque ya se comunican.** El gate del handshake (C1) ni llegó a dispararse: los agentes *ya* se mandan mensajes antes de tocar código (primer mensaje en el turno 2, primera edición en el turno 6). Hacerles hablar más no cambió nada, en ningún tier. Esto coincide con el propio "la comunicación no ayuda" de CooperBench — y sugiere que el problema no es *si* intercambian información, sino qué **hacen** con ella.

Una nota menor y algo incómoda: el ownership fino por **rangos de línea** (C2b) rindió *peor* que el grueso por **fichero** (C2, 16%) en el modelo fuerte. Primero sospeché de un artefacto de mi v1 de enforcement, que revertía el fichero entero ante cualquier solape — así que construí una v2 que revierte solo los hunks violadores y re-corrí ambos tiers: **0% en ambos**. La restricción vinculante no es la granularidad del revert. Es que las features de CooperBench solapan *a propósito* en líneas compartidas (la misma lista de imports, la misma firma de función), así que cualquier ownership exclusivo de líneas deja sin sitio al agente que llega segundo.

Una tanda registrada muestra el fallo en miniatura. El agente bloqueado escaló exactamente como lo haría una persona: anunció su plan, luego pidió a su compañero que evitara las regiones compartidas, y — tras más reverts — *delegó*: "¿podrías añadir tú mi línea de export, ya que esa región es tuya?". Comprobé la fontanería por ambos lados: los tres mensajes llegaron al contexto del compañero con turnos de sobra, y su canal de salida funcionaba de forma demostrable (él había enviado el primer mensaje del hilo, nada más empezar). El compañero leyó las peticiones, llegó a escribir en su propio razonamiento "tendré que coordinarme con agent1" — y después no respondió, no añadió la línea de export que poseía, y cerró su tarea. El cuello de botella no es el canal de comunicación; es el **follow-through** — exactamente el fallo de commitment que describe la taxonomía de CooperBench, reproducido aquí con el canal verificado como inocente.

## Bajo el capó: la colaboración muere en el merge

Mirar *cómo* falla cada condición cambia el cuadro más que las tasas de éxito.

**El coop libre falla en el merge, no en el código.** 14–15 de los 19 fallos de coop (en ambos tiers) son directamente **conflictos de merge** — los parches de los dos agentes ni siquiera se pueden combinar. Y aquí lo llamativo: **el ownership impuesto lleva los conflictos de merge a cero** — 0 de 19 tanto en C2 como en C2b, en ambos tiers. El fallo se desplaza aguas abajo: los parches combinan limpio pero el código integrado no pasa ambas suites.

**¿Pero no es morir en un conflicto de merge una muerte demasiado barata?** (¿No está el PR review precisamente para resolver conflictos?) Es una objeción justa — y apuntaba a un hueco real: la eval del propio paper resuelve los conflictos triviales con un modelo pequeño entrenado antes de declarar el fallo, pero la release open-source omite ese paso, así que mi primera tabla puntuaba cada conflicto como fallo instantáneo. Lo comprobé por las dos vías. Primero, clasifiqué los 29 pares conflictivos: **aproximadamente la mitad de los conflictos no son colisiones reales de lógica** — dos agentes añadiendo un import distinto, o un argumento distinto, a la misma línea; git lo marca, al código le daría igual. Después añadí un resolver de conflictos triviales (con un modelo más potente que el del paper, para dar a coop todo el beneficio de la duda) y re-puntué los pares conflictivos en las tres seeds. Rescató un montón de merges — pero **casi ninguno se convirtió en pass**: el coop con merge justo se queda en 7% para mini (sin cambio) y 9% para gpt-5.4 (desde 7%), una única tarea extra. Los conflictos estaban sobre todo *enmascarando* fallos semánticos aguas abajo: en un par rescatado, una feature pasó 71/71 tests y la otra falló una aserción genuinamente rota que el conflicto había estado tapando.

La cadena causal queda así:

> concurrencia sin estructura → ~75% conflictos de merge → la capa *sintáctica* se arregla de dos maneras — prevención (territorio impuesto: cero conflictos) o cura (un resolver de conflictos triviales) → lo que queda es un problema *semántico* de integración → y eso no lo arreglan ni las vallas ni los resolvers. Lo arreglan secuenciar o un integrador.

Esto rima con la propia observación de CooperBench de que la comunicación reduce conflictos sin mejorar el éxito — la capa sintáctica simplemente no es donde se gana la tarea.

**Las filas de "0%" esconden trabajo a medias.** La métrica exige que pasen *ambas* features. Contando éxito parcial (al menos una feature funcionando), el cuadro del modelo flojo se mueve: el coop libre logra apenas un puñado de passes de una-sola-feature, mientras que el ownership impuesto los duplica largamente (mini llega a 5/19 con enforcement por líneas). El enforcement convierte el colapso total en "media tarea hecha" más a menudo — solo que no basta para superar el listón de ambas-features.

**Ambos tiers chocan con la valla igual de a menudo; solo uno se recupera.** El hook de enforcement disparó un número similar de veces en ambos modelos (≈18–29 violaciones por tanda). El modelo fuerte no es "más ordenado" — viola territorio igual. La diferencia es lo que pasa *después* del revert: el fuerte re-planifica y lo rodea; el flojo sigue dándose contra la valla. Los tres passes de C2 del modelo fuerte tuvieron eventos de enforcement — el mecanismo estuvo activo en todos ellos; no fueron tareas sin conflicto que pasaron de gratis.

**Estadística, con honestidad.** Las cuatro condiciones de cabecera tienen tres seeds cada una; las impuestas son tandas únicas. Los tests pareados de McNemar (emparejados por tarea y seed) dan: la coordination gap sólida agregada (p=0.002) y claramente significativa solo en el modelo fuerte (p=0.002); secuenciar y el integrador superan a coop de forma abrumadora (p<0.0001); secuenciar supera al *solo* agregado (p=0.021) y en el modelo flojo por separado (p=0.039, por delante en las tres seeds), mientras que en el fuerte solo lo iguala (p=0.45); el integrador recupera pero nunca supera al solo de forma significativa (p=0.23). Un caveat honesto de método: agregar las parejas discordantes entre seeds trata cada (tarea, seed) como independiente, lo que exagera un poco la significancia — así que me apoyo tanto en la dirección por-seed (mini seq > solo en 3/3) como en el p-value. Con tres seeds sobre un subconjunto de 19 tareas esto sigue siendo direccional; querría una tanda mayor y repetida antes de endurecer cualquier número.

**El trabajo en equipo tiene factura.** Para el modelo fuerte, por tanda: el solo costó ~\$3.60; el secuencial ~\$7.10 y el integrador ~\$9.73. Secuenciar más o menos duplica la factura para superar modestamente al solo; el integrador casi la triplica para igualarlo. En tareas pequeñas y acopladas, si tienes que colaborar, secuencia; si puedes evitarlo, un solo agente capaz es la opción fuerte más barata.

## ¿Se pueden apilar los arreglos?

Si el territorio impuesto mata los conflictos sintácticos y un integrador se hace dueño del merge, ¿combinar ambos no debería superar a cualquiera por separado? Probé tres combinaciones: **territorio + integrador**, **secuencial + revisor** y **handshake + territorio**. Respuesta corta: **ninguna supera de forma robusta a sus propios componentes.**

La instructiva es territorio + integrador. A un seed parecía la estrella del experimento entero — 42% en el modelo fuerte, aparentemente por delante del integrador solo. Luego corrí dos seeds más y se desplomó a 33% [21–42]: el 42% fue una tirada afortunada, y pareado contra el integrador solo en los tres seeds sale p=1.0 — indistinguible. Las réplicas existían justo para cazar ese tipo de sobre-afirmación, y la cazaron.

Pero una medición más limpia rescata algo real. Para cada par re-puntué el árbol *sin* la etapa extra, sobre los mismos dos parches de los agentes — así la única variable es la etapa extra en sí, sin ruido entre tandas. El integrador, medido así, **rescató 8 pares y rompió 0**; el revisor (sobre un pipeline secuencial) rescató 3 y rompió 3, un neto cero. O sea, la contribución del integrador es genuina y va en una sola dirección: solo ayuda. La razón de que territorio + integrador aun así no gane en el marcador: la fase de desarrollo con territorio no le entrega al integrador mejor materia prima que el desarrollo independiente normal, así que un empujón real pero modesto parte de insumos igual de ruidosos y se diluye entre seeds. El revisor da neto cero por un motivo más simple — un pipeline secuencial ya integró el árbol, así que no queda nada que reconciliar, solo código que romper por accidente.

La lección no es "la estructura no se apila". Es más estrecha: **apilar solo compone cuando una etapa mejora los *insumos* de la siguiente.** Secuencial→revisión no pasa esa prueba (nada que mejorar); territorio→integración tampoco (el territorio no produce mejores parches, solo parches que no solapan). La única palanca que sigue funcionando es la misma de las condiciones sueltas — un agente dueño de la integración — y redoblar la apuesta combinándolas no compró más.

## Lo que dice y lo que no

**No** dice que CooperBench se equivoque — reproduje su gap en ambos tiers. Lo que añade es la pieza que su montaje dejó fuera a propósito: **una vez que das estructura a los agentes, ¿se cierra el gap?** En este subconjunto, en parte — y *qué* estructura funciona depende tanto de la estructura como del modelo.

El titular honesto no es "la estructura le gana a las habilidades sociales". Es más estrecho y, creo, más útil:

- La palanca más fiable no fue la comunicación ni el ownership — fue **dar a un solo agente la propiedad de la integración final**: traspaso secuencial, o un integrador/revisor dueño del merge. Ambos recuperan el nivel del solo en ambos tiers, y secuenciar es el que mejor lo hace.
- **La estructura tiene que encajar con el modelo.** Secuenciar — que *encoge* la tarea en lugar de añadir reglas que obedecer — es la única intervención que sube al modelo *flojo* por encima de su propio solo; la colaboración concurrente sigue muerta para él, arregles lo que arregles (merge justo, vallas, handshakes lo dejan plano). El ownership impuesto, una regla que el agente tiene que saber aprovechar, solo rindió en el *fuerte*. Por debajo de cierto umbral de capacidad, darle a un agente un protocolo de coordinación es como darle un manual de proceso a alguien que aún no sabe hacer la tarea de base — pero darle una tarea más pequeña sí ayuda.

Así que "todavía no pueden ser compañeros de equipo" se lee, desde aquí, menos como *les falta inteligencia social* y más como *los soltaron en un caos sin estructura que ningún equipo de ingeniería sensato montaría* — y el arreglo que generaliza es proceso (descomponer + secuenciar, o nombrar un integrador), no exhortaciones a comunicarse.

## ¿De verdad los humanos somos mejores en esto?

Es tentador leer el encuadre del paper como "a los agentes les falta la inteligencia social que los humanos sí tenemos". Pero mira los tres modos de fallo que encontré y pregúntate con honestidad si *nosotros* somos inmunes:

- **Las ediciones concurrentes chocan en el merge.** Dos humanos editando el mismo fichero en paralelo también producen conflictos de merge — constantemente. Eso no lo resolvimos volviéndonos más sociales; lo resolvimos con *proceso*: PRs pequeños, ownership de código, trunk-based, "rebasa antes de pushear".
- **El follow-through falla aunque el mensaje llegue.** El fallo más nítido aquí fue un agente que leyó la petición de su compañero, escribió "tendré que coordinarme con él", y simplemente no lo hizo. Si alguna vez has visto una petición en Slack recibir un 👍 y luego nada, sabes que los humanos también hacemos esto. Nuestro arreglo no es fuerza de voluntad — son tickets, asignados, dailies y "¿quién se encarga de esto?" hecho explícito.
- **Lo que rescató a los agentes es lo que ya hacemos.** Que un solo agente sea dueño de la integración final — traspaso secuencial, o un integrador/revisor designado — no es más que trunk-based development y el rol de release manager. No inventamos eso porque se nos dé mal hablar; lo inventamos porque la concurrencia sin estructura no escala para *nadie*.

Así que la comparación justa no es "humanos vs agentes coordinando". Es "humanos *con décadas de proceso acumulado* vs agentes soltados en un vacío de proceso". Mete a un equipo humano en el montaje exacto de los agentes — sin tickets, sin ownership, sin review, solo un canal de chat y "adelante" — y también se pisaría. La diferencia honesta que queda: cuando falta el proceso, un buen humano lo *improvisa* (le escribe a la persona correcta, gira la silla, convoca cinco minutos); los agentes, con el mismísimo canal, en su mayoría no lo hicieron. Ese hueco — improvisar coordinación cuando no se impuso ninguna — es real, y quizá sea exactamente a lo que apunta la "inteligencia social". Pero es un hueco más pequeño y más específico que "no pueden ser compañeros de equipo", y la lección práctica corta igual para ambas especies: **no cuentes con que nadie, de silicio o de carbono, invente el proceso sobre la marcha — dales el proceso.**

## Limitaciones y qué sigue

- **19 parejas, 5 repos.** Las condiciones de cabecera tienen tres seeds (de ahí los rangos); las impuestas (C1/C2/C2b) siguen siendo tandas únicas, así que trátalas como los números más blandos de aquí.
- **Los passes se concentran en pocos repos.** Todos los passes, en toda condición y tier, caen en dos repos Python (más una tarea de Pillow); cuatro de las nueve tareas no las resolvió nada, nunca — ni el solo. El conjunto efectivamente discriminativo está más cerca de ~10 parejas que de 19.
- El subconjunto se inclina hacia lo que pude correr de forma nativa; ampliarlo es el siguiente paso obvio.
- El número de C2b sobrevivió a una v2 con reverts por-hunk (0% en ambos tiers al re-correrlo) — no es un artefacto de la granularidad del revert.
- Una advertencia de construir esto: dos condiciones puntuaron un 0% falso por bugs de composición del eval (un parche apilado evaluado contra la base equivocada). Después corrí dos auditorías de código adversariales e independientes sobre las cinco condiciones y el ruteo del eval; los números publicados sobrevivieron, y la auditoría es la que destapó el resolver de conflictos ausente detrás de la fila de "merge justo" de arriba. En harnesses de agentes, la fontanería de puntuación merece tantos tests como las condiciones mismas.

Las cinco condiciones, los combos, el resolver LLM de conflictos y los arreglos del eval están implementados sobre el harness abierto de CooperBench — el fork completo es público en [github.com/JaviMaligno/CooperBench](https://github.com/JaviMaligno/CooperBench/tree/experiment/structural-conditions) (rama `experiment/structural-conditions`), así que puedes reproducir o buscarle las cosquillas a todo esto.

---

*En respuesta a [CooperBench (Khatua, Zhu, et al., 2026)](https://arxiv.org/abs/2601.13295). Las celdas de cabecera son medias de tres seeds sobre un subconjunto de 19 tareas; ampliar el conjunto es el siguiente paso.*
