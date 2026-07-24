---
title: "Routing engineering"
description: "Cuando el prompt deja de ser lo difícil, ocupa su lugar otra pregunta: qué modelo, con cuánto esfuerzo de razonamiento, para qué parte del trabajo. Elegir bien se está convirtiendo en una disciplina de ingeniería propia."
pubDate: 2026-07-26
tags: ["IA", "Routing", "Agentes", "Coste", "Tendencias"]
lang: es
translationKey: routing-engineering
heroImage: "/blog/routing-engineering.png"
---

En la [primera parte de este par](/es/blog/death-of-prompt-engineering) sostuve que el prompt engineering —el oficio de la redacción— se está muriendo, y que el esfuerzo no desapareció sino que subió por la pila. Aquí es a donde subió.

Esta es la nueva fricción. Me siento a una tarea y, antes de hacer nada, me enfrento a una rejilla. [OpenAI ya ofrece GPT-5.6](https://openai.com/index/gpt-5-6/) en tres tiers —Sol, Terra, Luna—, con varios ajustes de esfuerzo de razonamiento y un nuevo nivel `max`. Suma los modelos 5.x anteriores que siguen en rotación y las variantes Codex, y un solo proveedor ya te da decenas de rutas plausibles (modelo × esfuerzo). [La escalera de esfuerzo de Claude](https://platform.claude.com/docs/en/build-with-claude/effort) abarca `low`, `medium`, `high` y `max`, con `xhigh` en los modelos compatibles. Gemini tiene un presupuesto de pensamiento. La redacción ya no es la decisión. Lo es *la asignación*: qué modelo, con cuánto esfuerzo, para qué parte del trabajo. Acertar con eso es lo que yo llamaría routing engineering, y se ha vuelto en silencio una de las cosas más valiosas en las que ser bueno.

## La matriz que nadie pidió

La parte incómoda es que la rejilla creció más rápido que nuestra capacidad de razonar sobre ella. Cuando un modelo tenía un único ajuste, "usa el mejor" era una estrategia completa. Ahora los mandos se multiplican con cada release, y la mayoría intercambian las mismas tres cosas entre sí: calidad, latencia y coste. Un modelo de vanguardia a esfuerzo `max` machaca casi cualquier cosa, pero es lento y quema tokens. Un modelo barato a esfuerzo `low` es instantáneo y casi gratis, y destrozará con total confianza una tarea que necesitaba un momento de pensamiento.

Nadie optimiza a mano una rejilla de cien celdas por tarea, así que en la práctica todos la colapsamos en un puñado de hábitos. La pregunta interesante —la de ingeniería— es *qué* hábitos pagan de verdad, y cuándo la granularidad merece siquiera la molestia.

## Lo que hago yo

Mi opción por defecto es de una simpleza vergonzosa, y es una decisión de routing. En Claude Code planeo con Fable 5 y luego ejecuto con Opus o algo más ligero. Si dejo que el modelo con nivel de planificación conduzca toda la tarea, el consumo de tokens se dispara; el plan es donde tiene que estar la inteligencia, y la ejecución básicamente tiene que *seguir* el plan. Partir los dos por esa costura es el único cambio que me hizo asequibles las sesiones largas de agente.

Hago lo mismo en investigación. Al [escribir un paper con IA](/es/blog/writing-a-research-paper-with-ai) la división que importaba era Fable 5 para planificar la ciencia y GPT-5.6 como segundo revisor —un modelo fuerte donde vive el criterio, un cambio cuando llego a los límites de uso, y ejecución más barata en medio—. Nada de eso es artesanía de prompts. Es routing: emparejar el modelo con la forma del trabajo.

## Por qué funciona la división

La razón por la que esta costura concreta —planea fuerte, ejecuta barato— no para de aparecer es que casi toda la dificultad de una tarea se concentra en unas pocas decisiones. [Cursor le puso un número hace poco](https://cursor.com/blog/agent-swarm-model-economics). En un estudio sobre "enjambres" de agentes de larga duración, pusieron a una flota a construir SQLite desde cero en Rust, trabajando solo a partir de su manual de 835 páginas, y variaron quién planificaba y quién ejecutaba. Su propio resumen del mecanismo es la formulación más clara del principio que he visto:

> "Hay pocos momentos en una tarea grande que realmente requieran inteligencia de vanguardia, como la descomposición inicial, las decisiones de diseño y ciertas concesiones. Una vez que un planificador de vanguardia ha convertido la ambigüedad en una instrucción detallada y explícita, los modelos menos costosos simplemente tienen que seguirla."

El resultado fue que cada mezcla de modelos alcanzó una *calidad similar*, mientras el coste variaba unas 8× — desde unos \$1.339 para un híbrido Opus 4.8-planea / Composer 2.5-ejecuta, hasta \$10.565 para GPT-5.5 haciéndolo todo él solo. En la parte de ejecución sola la brecha era más cruda: los workers baratos costaron unos \$411 donde los de la ejecución todo-vanguardia costaron \$9.373. Mismo destino, un orden de magnitud de diferencia en el billete.

Y esto no es solo una afirmación de marketing de un vendor. La evidencia académica más antigua ya apuntaba en la misma dirección: [RouteLLM](https://github.com/lm-sys/RouteLLM) reportó hasta un **85% menos de coste manteniendo el 95% de la calidad de GPT-4** enrutando cada consulta a un modelo fuerte o débil; [FrugalGPT](https://arxiv.org/abs/2305.05176), anterior aún, mostró cascadas que igualaban a un modelo top con hasta un 98% menos de coste. Son pruebas útiles de que la asimetría se conoce desde hace años, no mediciones de la frontera actual. La imagen más reciente también es más sobria: [LLMRouterBench](https://arxiv.org/abs/2601.07206), publicado en enero de 2026, reevaluó diez métodos de routing sobre más de 400.000 ejemplos, 21 datasets y 33 modelos. Confirmó que los modelos son complementarios, pero encontró que varios métodos recientes —incluidos routers comerciales— no superaban de forma fiable un baseline sencillo. El ahorro es real; extraerlo de forma fiable sigue sin estar resuelto.

## La parte que lo hace *ingeniería*

Si fuera solo "planea con el listo", sería un truco, no una disciplina. Lo que lo hace ingeniería es que la jugada obvia a menudo está equivocada.

El mismo estudio de Cursor tiene un detalle al que no paro de volver: el híbrido montado sobre el planificador *más fuerte y más nuevo* (Fable 5) acabó siendo **más caro** que el montado sobre Opus 4.8 — aunque la factura propia del planner Fable fuera algo menor. La trampa estaba aguas abajo: sus planes llevaron a los workers baratos a consumir varias veces más tokens, y los workers son donde está el volumen (concentraron al menos el 69% de los tokens en cada ejecución, más del 90% en la mayoría). Un planificador mejor produjo una ejecución más cara.

Ahí está toda la lección en un solo dato. El coste de una ruta es no-lineal y vive sobre todo en efectos de segundo orden — cómo un plan moldea la ejecución, no la etiqueta de precio del planner. No lo lees en una ficha técnica. Tienes que medir la ruta de punta a punta, que es exactamente lo que las disciplinas de ingeniería existen para hacer.

## Manual, o automático

Puedes rutear a mano, como hago yo, o entregarle la decisión a un sistema.

El nivel automático se está llenando rápido. Cursor ya ofrece un **[Router](https://cursor.com/blog/router)** a nivel de request que clasifica cada tarea y la manda a un modelo apropiado, con un modo Auto que puedes sesgar hacia inteligencia, equilibrio o coste — reportan reducciones de coste del 30–50% a calidad de vanguardia en su adopción empresarial inicial. El endpoint `auto` de [OpenRouter](https://openrouter.ai) rutea por prompt (movido por el modelo de NotDiamond) con un dial de coste-frente-a-calidad. Martian y NotDiamond venden la misma idea como servicio. Hay incluso una pequeña literatura de benchmarks intentando responder "cuán bueno es el routing, de verdad", y la lectura honesta es *prometedor pero sin resolver*: algunos routers ahorran dinero real, y otros, bajo escrutinio, simplemente tiran por defecto al modelo caro.

Hay una dificultad más profunda: **a menudo no puedes saber lo difícil que es una tarea hasta que empiezas a hacerla**. Un prompt que parece rutinario puede esconder una dependencia desagradable tres llamadas a herramientas más tarde; otro que asusta puede deshacerse tras la primera inspección. El routing de una sola decisión tiene que predecir esa dificultad latente antes de ver la evidencia que revelará el propio trabajo. La investigación reciente está empezando a meter la decisión dentro del bucle de ejecución. [TwinRouterBench](https://arxiv.org/abs/2605.18859), de mayo de 2026, rutea en cada llamada dentro de trayectorias de agentes de código e investigación y comprueba si la tarea completa sigue teniendo éxito. En uno de sus diagnósticos, ni siquiera Opus 4.6 actuando como router identificó más que 7 de los 147 pasos que la ejecución demostró que realmente necesitaban el tier alto, y fallaron las 40 trayectorias de SWE-bench. [R2R](https://proceedings.neurips.cc/paper_files/paper/2025/file/b39cef2ef90591cffdc9c674cd55bebe-Paper-Conference.pdf), en NeurIPS 2025, baja aún más el nivel: empieza a generar con un modelo destilado de DeepSeek-R1 de 1,5B e invoca el de 32B token a token cuando la trayectoria de razonamiento empieza a desviarse. El router ya no es un recepcionista que elige modelo en la puerta; es un supervisor que observa cómo avanza el trabajo y escala cuando hace falta.

El routing automático mejorará, pero hereda la parte difícil de arriba: para rutear bien tiene que predecir el coste de segundo orden, no solo clasificar la dificultad. Por ahora me fío más de una costura dibujada a mano que he medido que de un router que no.

## Cuándo merece la pena

Aquí está la parte en la que discreparía del hype: la granularidad del routing tiene un coste propio, y no siempre vale la pena pagarlo.

Para una tarea puntual, todo el cálculo suele ser "usa el mejor modelo y sigue" — el tiempo que gastarías ajustando una ruta empequeñece los tokens que ahorrarías. El routing granular se gana el sueldo cuando se cumple una de tres cosas: **volumen** (corres la tarea miles de veces), **presupuestos ajustados de coste o latencia**, o una **asimetría clara plan/ejecución** como las sesiones largas de agente de arriba. Fuera de eso, un router es optimización prematura disfrazada de ingeniería. Saber cuándo *no* rutear es tanto parte de la disciplina como el routing en sí.

## La unidad no para de crecer

Da un paso atrás y hay un hilo con hacia dónde va todo esto. Cursor encuadró su enjambre como una especie de compilador probabilístico —los planificadores descomponen la intención en un árbol, los modelos baratos compilan las hojas— y señaló que "la unidad de trabajo pasa a ser la especificación". Eso rima con [el software disolviéndose en el modelo](/es/blog/software-dissolving-into-the-model): lo que le entregas al sistema no para de hacerse más grande y menos literal, y la habilidad escasa pasa a ser describir bien la intención y decidir qué corre dónde.

Queda un matiz honesto más que vale la pena conservar. En ese mismo estudio, el equipo quería usar GPT-5.6 Sol como planificador de vanguardia y no pudo — el modelo nuevo era tan sensible a la redacción literal y enfática que se descontroló, y recurrieron a GPT-5.5 en vez de reajustar los prompts. Así que incluso en la frontera del routing, un fantasma del prompt engineering sigue en la sala. El oficio no murió tanto como se mudó — de las palabras, al cableado. Elegir el modelo *es* el nuevo oficio.

---

*Este es el segundo de dos artículos sobre cómo el trabajo de "engineering" en IA no para de mudarse hacia arriba en la pila. El primero es [La muerte del prompt engineer](/es/blog/death-of-prompt-engineering).*
