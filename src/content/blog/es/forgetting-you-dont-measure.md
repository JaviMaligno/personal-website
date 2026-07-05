---
title: "El olvido que no mides"
description: "Cuando conviertes un LLM en un 'modelo del mundo' con pre-entrenamiento continuo, olvida conocimiento general en silencio — y un poco de mezcla de datos recupera casi todo. Pero cuánto olvida depende mucho de cómo lo especializas, y el fine-tuning completo paga tres costes que un solo benchmark subestima."
pubDate: 2026-07-06
tags: ["IA", "Machine Learning", "Continual Learning", "LoRA", "Ingeniería"]
lang: es
translationKey: forgetting-you-dont-measure
heroImage: "/blog/forgetting-you-dont-measure.png"
linkedinImage: /blog/forgetting-mixing-curve.png
repoUrl: https://github.com/JaviMaligno/language-world-model-forgetting
---

Hay un paper reciente del equipo de Qwen — [Qwen-AgentWorld](https://arxiv.org/abs/2606.24597) — que convierte un LLM en un *modelo del mundo*: en vez de responder como asistente, el modelo aprende a predecir lo que un entorno devuelve tras una acción. Ejecuta un comando de shell y predice la salida exacta de la terminal, con código de salida incluido. Lo construyen cogiendo un modelo terminado, de propósito general, y entrenándolo un paso más sobre millones de trayectorias de interacción — un paso que se llama **pre-entrenamiento continuo** (sigues pre-entrenando un modelo ya entrenado sobre datos nuevos para enseñarle algo nuevo).

El problema de ese tipo de entrenamiento es de sobra conocido: echa suficientes datos estrechos sobre un modelo y empieza a *olvidar* cosas que sabía — el clásico "olvido catastrófico". La defensa estándar es el **replay** (también llamado mezcla de datos): mientras entrenas con los datos nuevos y estrechos, sigues intercalando una fracción de texto general, para que el modelo repase su conocimiento viejo en vez de dejar que se diluya. El paper de Qwen hace justo esto — durante el pre-entrenamiento continuo mezclan corpus de conocimiento general (derecho, medicina, actualidad). Lo enmarcan como una cuestión de capacidad (no puedes simular un hospital sin saber medicina), pero funciona además como seguro anti-olvido. Es una decisión sensata. Lo que nunca hacen es *medirla*: no hay antes/después en benchmarks generales, ni un número de cuánto se olvida o cuánto salva el replay.

Así que hice el experimento a escala de juguete. No para superar un modelo de 397B con uno de 0.5B — sería absurdo — sino porque la pregunta es sobre una *dinámica de entrenamiento*, y las dinámicas aparecen también en pequeño. Honestamente, sobre todo quería ver eso a lo que este blog vuelve una y otra vez: no si un sistema se degrada, sino si puedes darte cuenta cuando lo hace.

## El montaje

Cogí `Qwen2.5-0.5B-Instruct`, generé un dataset estrecho de "simulador de terminal" (comandos de shell reales y sus salidas reales), y pre-entrené el modelo de forma continua para predecir esas salidas — enseñándole a ser un modelo del mundo diminuto. Antes y después medí su capacidad general en benchmarks estándar (ARC, HellaSwag, WinoGrande), y medí si de verdad aprendía la tarea nueva (accuracy sobre salidas held-out). Luego barrí el único mando que importa: qué fracción de cada batch de entrenamiento es *replay* — texto general (Wikipedia) — en vez de datos de terminal. Cero, 10%, 25%, 50%, y un control al 100%. Tres semillas cada uno. Todo corrió en una sola T4 spot en Azure por el precio de un par de cafés.

## Resultado uno: sí, olvida, y un poco de mezcla lo recupera

Sin replay, el modelo aprende bien la tarea de terminal (el exact-match sobre salidas held-out sube de ~0.36 a ~0.90) — y olvida. La accuracy general baja en todo: −0.078 de media, y −0.15 en el benchmark más golpeado (ARC-Easy). Luego subí el replay. La línea ámbar de abajo es la historia:

![Olvido vs. replay: el fine-tuning completo recupera casi todo con un 10% de mezcla; LoRA apenas olvida](/blog/forgetting-mixing-curve.png)

Un 10% de replay recupera cerca del 73% del olvido medio — y en torno al 82% del peor caso — **sin coste en la tarea nueva** (la accuracy de la tarea se mantiene en ~0.90). Pasado el 25% hay rendimientos decrecientes. Y un control con 100% de replay (no dibujado) confirma el extremo por el otro lado: entrena solo con texto general y el modelo nunca aprende a simular nada (la accuracy de la tarea vuelve a la línea base), mientras la capacidad general queda plana.

Quiero ser claro: esto no es un descubrimiento nuevo. Que una fracción pequeña de replay suprima el olvido catastrófico está [bien establecido](https://arxiv.org/html/2401.03129v1) — la literatura de continual learning lleva años diciendo "mezcla un 1–5% de la distribución vieja". Lo que hice fue ponerle número a la afirmación concreta que el paper del modelo del mundo hace por diseño pero deja sin cuantificar. Esa era la parte fácil. La línea azul — LoRA — es donde se puso interesante.

## Lo más interesante: cuánto olvidas depende de cómo especializas

El replay es una palanca. El *método* de entrenamiento es una mayor. Todo lo de arriba usó **fine-tuning completo** — cualquier peso del modelo puede cambiar. Así que repetí el barrido entero con **LoRA**: el método barato y popular, eficiente en parámetros, que congela el modelo original y solo entrena un pequeño conjunto de pesos adicionales, unos "adaptadores". Esa es la línea azul del gráfico de arriba — plana, cerca de cero, en *todas* las fracciones de replay, incluida la de cero.

LoRA apenas olvida, incluso sin nada de replay, mientras aprende la tarea de terminal igual de bien (la misma accuracy ~0.90). No es un misterio: como los pesos originales están congelados, el conocimiento general que sostienen queda intacto por construcción. Se sabe que LoRA [olvida menos](https://arxiv.org/html/2405.09673v2) precisamente *porque* cambia tan poco. El fine-tuning completo, en cambio, deja que el optimizador sobrescriba cualquier peso — incluidos los que sostienen la capacidad general.

Así que apreté sobre lo que el fine-tuning completo cuesta de verdad, más allá de los benchmarks de razonamiento. Dos sondas más, a cero replay:

| Sonda (a 0% replay) | Fine-tuning completo | LoRA |
|---|---|---|
| Seguimiento de instrucciones (IFEval) | −0.071 | **+0.033** |
| Modelo del mundo en comandos no vistos | **0.00** | **0.15** |

- **Seguimiento de instrucciones.** Mis benchmarks de razonamiento no podían ver esto, así que añadí IFEval — instrucciones que un script puede corregir automáticamente (respetar un formato, una longitud, incluir una palabra dada). El fine-tuning completo lo baja un 37% relativo (0.194 → 0.123); LoRA incluso lo sube un poco. Esto es lo concreto que "los benchmarks generales apenas se movieron" ocultaba del lado de full-FT: un modelo afinado para instrucciones perdiendo en silencio el seguimiento de instrucciones para el que fue afinado.
- **Profundidad de la tarea aprendida.** Aquí esperaba lo contrario — que LoRA, cambiando tan poco, aprendiera un modelo del mundo *más superficial*. Fue al revés. Ambos sacan ~0.90 prediciendo salidas para el tipo de comandos con los que entrenaron, pero en comandos genuinamente desconocidos (cosas como `sed`, `awk`, `grep` y pipes, que el training nunca contenía) el fine-tuning completo se desploma a cero mientras LoRA aún saca 0.15. El fine-tuning completo memorizó las formas exactas de comando que vio; LoRA, apoyado en el base congelado, conservó algo de capacidad de generalizar.

Así que la lectura honesta es más simple que un "te pillé": **el fine-tuning completo paga tres costes — razonamiento general, seguimiento de instrucciones y robustez fuera de distribución — que un solo benchmark subestima, y LoRA en su mayoría no los paga, porque perturba el modelo mucho menos.** No es que LoRA oculte nada; es que LoRA hace menos daño. La versión suave de la lección sigue en pie, y es el hilo de [Programación orientada a resultados](/es/blog/results-oriented-programming) y [¿Cuánto deberías seguir sabiendo?](/es/blog/how-much-should-you-still-know): un solo número ("mi accuracy general aguantó") puede sustituir en silencio a varios que no comprobaste.

El trade-off es el de siempre: LoRA aprende la tarea *nueva* algo menos agresivamente que full-FT. Aquí la tarea de terminal era fácil y ambos llegaron al mismo ~0.90, así que LoRA sale estrictamente mejor — pero en un objetivo más difícil donde necesites cada punto de rendimiento, la disposición de full-FT a sobrescribir es justo lo que estás pagando. No hay comida gratis, solo un dial entre "aprende más, olvida más" y "aprende menos, olvida menos".

## Dos matices, reportados con honestidad

**Base frente a instruct.** Esperaba que el modelo instruido olvidara más — más que perder. En razonamiento no fue así: base e instruct de 0.5B olvidaron casi idéntico (−0.14 vs −0.17 de media a cero replay). Donde el modelo instruct *sí* sangra es en el propio seguimiento de instrucciones (la caída de IFEval de arriba) — un modelo base tiene poco de eso que perder de entrada. Así que "más que perder" es cierto, pero solo en el eje para el que el modelo instruct fue afinado.

**Tamaño.** El modelo más grande olvidó algo menos: fine-tuning completo de 1.5B perdió −0.060 de media frente al −0.078 del 0.5B, inclinándose hacia "los modelos pequeños olvidan más". Pero el efecto es suave y no uniforme — claro en ARC-Easy, invertido en ARC-Challenge — y comparable al ruido entre semillas. (Hacer que el fine-tuning completo de 1.5B cupiera en una T4 de 16 GB requirió un optimizador de 8 bits descargado a CPU y batch de uno; en el primer intento se pasó de memoria por 200 MB. Una nota de oficio, no un hallazgo.)

## La conclusión

Nada de esto es física nueva — que el replay mitigue el olvido, que LoRA olvide menos, y lo demás son cosas que la literatura ya sabe. Fue una reproducción pequeña que corres de una noche por el precio de unos cafés. Lo que me dejó claro es cuánto depende la respuesta a "¿conservó su capacidad general?" de *qué mediste y cómo entrenaste*.

El fine-tuning completo sobre una tarea estrecha se veía bien en razonamiento, hasta que IFEval mostró el seguimiento de instrucciones que había soltado y una sonda de comandos desconocidos mostró lo estrechamente que en realidad había aprendido. Mismo modelo, mismos datos — las pérdidas eran reales, solo que no estaban en el primer sitio donde mirarías. El arreglo no es exótico: cuando especializas un modelo, comprueba más de una capacidad, elige el método de entrenamiento a conciencia (LoRA y fine-tuning completo son trueques genuinamente distintos, no defaults intercambiables), y no leas un solo benchmark plano como prueba de que no se perdió nada.

---

*Código y resultados completos: [github.com/JaviMaligno/language-world-model-forgetting](https://github.com/JaviMaligno/language-world-model-forgetting). Este es el tercero de una serie suelta sobre delegar en los modelos y seguir siendo capaz de notar cuándo se equivocan — ver también [¿Cuánto deberías seguir sabiendo?](/es/blog/how-much-should-you-still-know) y [Programación orientada a resultados](/es/blog/results-oriented-programming).*
