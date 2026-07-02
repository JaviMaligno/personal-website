---
title: "Agentes de código y trabajo en equipo: ¿habilidades sociales o estructura?"
description: "Un benchmark reciente dice que los agentes de código no colaboran porque les falta inteligencia social. Pruebo otra hipótesis: les falta estructura — y encuentro que secuenciar el trabajo recupera la colaboración, mientras que la estructura impuesta solo rinde con un modelo lo bastante capaz."
pubDate: 2026-07-01
tags: ["IA", "Agentes", "Evaluación"]
lang: es
translationKey: coding-agents-structure
heroImage: "/blog/coding-agents-structure.png"
---

> **Estado: preliminar pero completo para dos tiers de modelo.** Los resultados son sobre un subconjunto de 19 tareas que pude correr limpiamente, en dos niveles de capacidad. Direccional, no el benchmark completo — pero el patrón es lo bastante consistente como para reportarlo.

Un benchmark reciente de Stanford, [CooperBench](https://arxiv.org/abs/2601.13295) ("Why Coding Agents Cannot be Your Teammates Yet"), reporta un resultado llamativo: si emparejas dos agentes de código potentes para repartirse una tarea, su tasa de éxito casi se *reduce a la mitad* frente a un solo agente haciendo el mismo trabajo total. Lo llaman la **maldición de la coordinación**, y su lectura es que lo que falta es *inteligencia social* — los agentes no usan el lenguaje para coordinarse de forma fiable, así que, argumentan, esto hay que *entrenarlo*, no arreglarlo con prompts.

Es un paper cuidadoso, y quiero ser justo con él: **deliberadamente** corren los agentes casi sin scaffolding, precisamente para medir la capacidad de coordinación *intrínseca*. Es una elección científica legítima. Pero me dejó con una pregunta de ingeniería que ellos dejan fuera a propósito:

> Los equipos humanos tampoco coordinan bien con *cero* proceso. A un equipo que se pisa constantemente no lo arreglamos con terapia — usamos **estructura**: ownership de código, contratos de interfaz, PRs secuenciales, alguien que integra. Entonces, ¿cuánto de la "coordination gap" es de verdad habilidades sociales, y cuánto es simplemente la ausencia de una estructura que a los agentes nunca se les dio?

## El montaje

Partí del propio benchmark de CooperBench (es open source) y reproduje el baseline: dos agentes, cada uno con una feature de la tarea, en contenedores aislados, y los parches se mergean después. Luego añadí una **escalera de estructuras de coordinación**, ordenada de "advisory" (el agente puede ignorarla) a "impuesta" (el scaffold la garantiza):

- **Handshake (C1):** los agentes deben intercambiar un plan antes de que el scaffold les deje editar código. *(Analogía: una revisión de diseño antes de codear.)*
- **Ownership por fichero (C2):** cada fichero es de un agente; las ediciones al fichero de otro se revierten. *(Analogía: CODEOWNERS.)*
- **Ownership por rangos de línea (C2b):** versión fina — ambos pueden editar el mismo fichero, pero solo en regiones disjuntas. *(Analogía: no pisarse las funciones.)*
- **Pipeline secuencial (seq):** el agente A implementa la feature 1 y commitea; el agente B arranca *desde el código de A* y añade la feature 2. Sin concurrencia. *(Analogía: PRs pequeños y secuenciales sobre trunk.)*
- **Integrador (c4):** A y B trabajan independientes; un tercer agente reconcilia ambos parches. *(Analogía: un ingeniero de integración / revisor de PR.)*

El sentido de la escalera es separar "¿*hablaron*?" de "¿el proceso *les impidió chocar*?" — y encontrar la estructura *mínima* que ayuda.

## Resultados

**Primero las advertencias**, porque importan: son **19 parejas de tareas en 5 repositorios** — un subconjunto que pude correr limpiamente — no el benchmark completo. Pero corrí la escalera entera en **dos tiers de capacidad**: un `gpt-5.4-mini` de gama media y un `gpt-5.4` más fuerte.

| condición | mini | gpt-5.4 |
|---|---|---|
| solo (un agente, ambas features) | 16% | 37% |
| coop (dos agentes, libre) | 0% | 5% |
| handshake (C1) | 0% | 0% |
| ownership por fichero (C2) | 0% | **16%** |
| ownership por línea (C2b) | 0% | 5% |
| integrador (c4) | 0% | 0% |
| **secuencial (seq)** | **21%** | **32%** |

Cuatro cosas destacan:

1. **La coordination gap se reproduce — en ambos tiers.** En solitario resuelve 16% / 37%; en cuanto dos agentes trabajan en concurrencia (coop), se desploma a 0% / 5%. El hallazgo central de CooperBench se sostiene en mi subconjunto.

2. **Secuenciar es lo que la recupera — independientemente de la capacidad.** El **pipeline secuencial** recupera al nivel del solo en ambos modelos (21% vs 16% en mini; 32% vs 37% en el fuerte — estadísticamente indistinguible del solo en ambos casos), mientras que toda condición concurrente queda muy por debajo. Mi lectura: esto no va realmente de "coordinación". Cuando el agente B arranca desde la feature ya *terminada* de A y solo añade una cosa encima, hace una *tarea más pequeña y limpia* que el solo. La palanca es descomponer y secuenciar — no hablar más, no fronteras más estrictas.

3. **La estructura interactúa con la capacidad — la parte interesante.** El **ownership por fichero (C2)** impuesto no recuperó nada en el modelo flojo (0%) pero sí un trozo relevante en el fuerte (0% → **16%**). El modelo más capaz sí sabe *usar* una regla estructural que le das; el flojo no. Esa interacción — *el mismo scaffold ayuda o no según quién lo use* — es justo lo que un piloto ruidoso de 4 tareas no podía mostrar, y es la parte que más merece perseguir. (Con una sola tanda por celda, este contraste concreto es sugerente, no significativo — más abajo.)

4. **Forzar la comunicación no hace nada — porque ya se comunican.** El gate del handshake (C1) ni llegó a dispararse: los agentes *ya* se mandan mensajes antes de tocar código (primer mensaje en el turno 2, primera edición en el turno 6). Hacerles hablar más no cambió nada, en ningún tier. Esto coincide con el propio "la comunicación no ayuda" de CooperBench — y sugiere que el problema no es *si* intercambian información, sino qué **hacen** con ella. El integrador (c4) tampoco ayudó a ninguno.

Una nota menor y algo incómoda: el ownership fino por **rangos de línea** (C2b, 5%) rindió *peor* que el grueso por **fichero** (C2, 16%) en el modelo fuerte — probablemente un artefacto de mi v1, que revierte el fichero entero ante cualquier solape. Los detalles del diseño de enforcement importan, y no los he optimizado.

## Bajo el capó: la colaboración muere en el merge

Mirar *cómo* falla cada condición cambia el cuadro más que las tasas de éxito.

**El coop libre falla en el merge, no en el código.** 14–15 de los 19 fallos de coop (en ambos tiers) son directamente **conflictos de merge** — los parches de los dos agentes ni siquiera se pueden combinar. Y aquí lo llamativo: **el ownership impuesto lleva los conflictos de merge a cero** — 0 de 19 tanto en C2 como en C2b, en ambos tiers. El fallo se desplaza aguas abajo: los parches combinan limpio pero el código integrado no pasa ambas suites. La cadena causal queda así:

> concurrencia sin estructura → ~75% conflictos de merge → el territorio impuesto elimina los conflictos por completo → lo que queda es un problema *semántico* de integración → y la capacidad del modelo decide si ese resto se resuelve (el fuerte en parte sí; el flojo no).

Esto rima con la propia observación de CooperBench de que la comunicación reduce conflictos sin mejorar el éxito — solo que el enforcement no reduce los conflictos: los elimina, y en el tier fuerte eso *sí* empieza a convertirse en passes.

**Las filas de "0%" esconden trabajo a medias.** La métrica exige que pasen *ambas* features. Contando éxito parcial (al menos una feature funcionando), el cuadro del modelo flojo cambia: el coop libre logra 1/19, pero bajo ownership por líneas llega a **10/19**. El enforcement convierte el colapso total en "media tarea bien hecha, de forma fiable" — solo que no basta para superar el listón.

**Ambos tiers chocan con la valla igual de a menudo; solo uno se recupera.** El hook de enforcement disparó un número similar de veces en ambos modelos (≈18–29 violaciones por tanda). El modelo fuerte no es "más ordenado" — viola territorio igual. La diferencia es lo que pasa *después* del revert: el fuerte re-planifica y lo rodea; el flojo sigue dándose contra la valla. Los tres passes de C2 del modelo fuerte tuvieron eventos de enforcement — el mecanismo estuvo activo en todos ellos; no fueron tareas sin conflicto que pasaron de gratis.

**Estadística, con honestidad.** Con una tanda por celda y N=19, los contrastes individuales son frágiles. Lo que sobrevive al test pareado (McNemar): la coordination gap (solo vs coop, agregando ambos tiers, p≈0.004) y la recuperación de secuenciar frente a coop (agregado p≈0.004). Lo que no: seq vs solo es indistinguible (p≈1 — secuenciar *recupera* al solo, no lo supera), y la interacción de C2 con la capacidad (p≈0.5) es una hipótesis para una tanda mayor, no un resultado.

**El trabajo en equipo tiene factura.** Para el modelo fuerte: el solo costó ~$3.60 para un 37%; el secuencial ~$7.10 para un 32%; el integrador ~$9.73 para un 0%. En tareas pequeñas y acopladas, dos agentes cuestan aproximadamente el doble para, como mucho, igualar a uno — si tienes que colaborar, secuencia; si puedes evitarlo, evítalo.

## Lo que dice y lo que no

**No** dice que CooperBench se equivoque — reproduje su gap en ambos tiers. Lo que añade es la pieza que su montaje dejó fuera a propósito: **una vez que das estructura a los agentes, ¿se cierra el gap?** En este subconjunto, en parte — y *qué* estructura funciona depende tanto de la estructura como del modelo.

El titular honesto no es "la estructura le gana a las habilidades sociales". Es más estrecho y, creo, más útil:

- La palanca más fiable no fue la comunicación ni el ownership — fue **reestructurar el trabajo en sí**: descomponer y luego secuenciar. Ayudó a ambos modelos.
- **La estructura impuesta solo rinde con un modelo lo bastante capaz.** Por debajo de cierto umbral, darle a un agente un protocolo de coordinación es como darle un manual de proceso a alguien que aún no sabe hacer la tarea de base.

Así que "todavía no pueden ser compañeros de equipo" se lee, desde aquí, menos como *les falta inteligencia social* y más como *los soltaron en un caos sin estructura que ningún equipo de ingeniería sensato montaría* — y el arreglo que generaliza es proceso (descomponer + secuenciar), no exhortaciones a comunicarse.

## Limitaciones y qué sigue

- **19 parejas, 5 repos, una tanda cada una.** Sin barras de error aún; el pass/fail de una sola ejecución es ruidoso. Trata las diferencias pequeñas (5% vs 16%) como sugerentes, no zanjadas.
- **Los passes se concentran en pocos repos.** Todos los passes, en toda condición y tier, caen en dos repos Python (más una tarea de Pillow); cuatro de las nueve tareas no las resolvió nada, nunca — ni el solo. El conjunto efectivamente discriminativo está más cerca de ~10 parejas que de 19.
- El subconjunto se inclina hacia lo que pude correr de forma nativa; ampliarlo es el siguiente paso obvio.
- El enforcement por rangos de línea merece un revert por-hunk antes de fiarme del número de C2b.

Las condiciones están implementadas sobre el harness abierto de CooperBench — compartiré el código junto a un writeup más completo si el patrón se sostiene en una tanda mayor y repetida.

---

*En respuesta a [CooperBench (Khatua, Zhu, et al., 2026)](https://arxiv.org/abs/2601.13295). Preliminar — los números cambiarán al completarse el experimento.*
