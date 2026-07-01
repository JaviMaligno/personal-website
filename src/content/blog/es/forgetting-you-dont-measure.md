---
title: "El olvido que no mides"
description: "Cuando conviertes un LLM en un 'modelo del mundo' con pre-entrenamiento continuo, olvida conocimiento general en silencio — y un poco de mezcla de datos recupera casi todo. Pero lo que se me quedó grabado es que el método barato y por defecto esconde el olvido por completo. El problema nunca fue el olvido. Fue si podías verlo."
pubDate: 2026-07-01
tags: ["IA", "Machine Learning", "Continual Learning", "LoRA", "Ingeniería"]
lang: es
translationKey: forgetting-you-dont-measure
heroImage: "/blog/forgetting-you-dont-measure.png"
---

Hay un paper reciente del equipo de Qwen — [Qwen-AgentWorld](https://arxiv.org/abs/2606.24597) — que convierte un LLM en un *modelo del mundo*: en vez de responder como asistente, el modelo aprende a predecir lo que un entorno devuelve tras una acción. Ejecuta un comando de shell y predice la salida exacta de la terminal, con código de salida incluido. Lo construyen con pre-entrenamiento continuo (CPT) sobre millones de trayectorias de interacción en siete dominios.

Enterrada en el método hay una decisión de diseño: durante ese CPT también mezclan corpus de conocimiento general — derecho, medicina, actualidad. Su razón declarada es capacidad (no puedes simular un hospital sin saber medicina), pero funciona además como medida anti-olvido: seguir alimentando datos generales para que especializarse en trayectorias estrechas no borre la distribución general. Es una decisión sensata. Lo que nunca hacen es *medirla*. No hay antes/después en benchmarks generales, ni un número de cuánto se olvida o cuánto salva la mezcla.

Así que hice el experimento a escala de juguete. No para superar un modelo de 397B con uno de 0.5B — sería absurdo — sino porque la pregunta es sobre una *dinámica de entrenamiento*, y las dinámicas aparecen también en pequeño. Honestamente, sobre todo quería ver eso a lo que este blog vuelve una y otra vez: no si un sistema se degrada, sino si puedes darte cuenta cuando lo hace.

## El montaje

Cogí `Qwen2.5-0.5B-Instruct`, generé un dataset estrecho de "simulador de terminal" (comandos de shell reales y sus salidas reales), y pre-entrené el modelo de forma continua para predecir esas salidas — enseñándole a ser un modelo del mundo diminuto. Antes y después medí su capacidad general en benchmarks estándar (ARC, HellaSwag, WinoGrande), y medí si de verdad aprendía la tarea nueva (accuracy sobre salidas held-out). Luego barrí el único mando que importa: qué fracción de cada batch de entrenamiento es *replay* — texto general (Wikipedia) — en vez de datos de terminal. Cero, 10%, 25%, 50%, y un control al 100%. Tres semillas cada uno. Todo corrió en una sola T4 spot en Azure por el precio de un par de cafés.

## Resultado uno: sí, olvida, y un poco de mezcla lo recupera

Sin replay, el modelo aprende bien la tarea de terminal (el exact-match sobre salidas held-out sube de ~0.36 a ~0.90) — y olvida. La accuracy general baja en todo, peor en ARC-Easy con −0.15. Luego la curva de mezcla (caída media sobre las cuatro tareas, promediada entre semillas):

| Replay % | Olvido medio | ARC-Easy |
|---|---|---|
| 0%  | **−0.078** | −0.153 |
| 10% | −0.021 | −0.028 |
| 25% | −0.012 | −0.004 |
| 50% | −0.015 | −0.010 |
| 100% (control) | −0.013 | +0.005 |

Un 10% de replay recupera cerca del 73% del olvido medio — y en torno al 82% del peor caso — **sin coste en la tarea nueva** (la accuracy de la tarea se mantiene en ~0.90). El control al 100% confirma el extremo: entrena solo con replay y el modelo nunca aprende a simular nada (la accuracy de la tarea se desploma), mientras la capacidad general queda plana.

Quiero ser claro: esto no es un descubrimiento nuevo. Que una fracción pequeña de replay suprima el olvido catastrófico en pre-entrenamiento continuo está [bien establecido](https://arxiv.org/html/2401.03129v1) — la literatura de continual learning lleva años diciendo "mezcla un 1–5% de la distribución vieja". Lo que hice fue *medir* la afirmación concreta que el paper del modelo del mundo hace por diseño pero deja sin cuantificar. El número dio gusto verlo. No era lo interesante.

## Lo interesante: el método decide si lo ves siquiera

Corrí el mismo barrido de una segunda forma: en vez de fine-tuning completo, usé **LoRA** — el método barato y por defecto, eficiente en parámetros, que entrena un pequeño conjunto de pesos adaptadores y deja el modelo base congelado. Aquí el olvido medio, LoRA frente a fine-tuning completo, en cada fracción de replay:

| Replay % | Fine-tuning completo | LoRA |
|---|---|---|
| 0%  | −0.078 | **+0.002** |
| 10% | −0.021 | +0.005 |
| 25% | −0.012 | +0.009 |
| 50% | −0.015 | +0.009 |

LoRA no muestra **ningún olvido** — ni siquiera a cero replay — mientras aprende la tarea de terminal igual de bien (la misma accuracy ~0.90). Si solo hubieras entrenado así, mirarías tus números, verías la capacidad general perfectamente intacta, y concluirías que convertir tu modelo en modelo del mundo es gratis. Y estarías equivocado. El olvido es real. Tu instrumento simplemente no podía verlo, porque LoRA apenas mueve los pesos que sostienen el conocimiento general — se sabe que [olvida menos](https://arxiv.org/html/2405.09673v2) precisamente *porque* toca tan poco.

Es la misma trampa sobre la que escribo desde ángulos distintos. En [Programación orientada a resultados](/es/blog/results-oriented-programming) era verificar la salida confiando en una señal que no podía fallar en voz alta. En [¿Cuánto deberías seguir sabiendo?](/es/blog/how-much-should-you-still-know) era delegar conocimiento y perder la capacidad de notar cuándo la respuesta recuperada está mal. Aquí es la misma forma a nivel de una corrida de entrenamiento: el peligro no es el olvido, es elegir un método — por razones perfectamente buenas de coste y comodidad — que no puede revelar el olvido aunque esté ocurriendo. El fine-tuning completo "se ve peor" porque es el instrumento honesto. LoRA "se ve seguro" porque es uno más silencioso.

No es un argumento contra LoRA. Que LoRA olvide menos suele ser justo lo que quieres. Es un argumento contra leer "mis benchmarks generales no se movieron" como "no se perdió nada", cuando las dos cosas pueden separarse por completo según cómo entrenaste.

## Dos matices, reportados con honestidad

**Base frente a instruct.** Esperaba que el modelo instruido olvidara más — más que perder. No fue así: base e instruct de 0.5B olvidaron casi idéntico (−0.077 vs −0.078 a cero replay). El matiz honesto es que mi batería son tareas de razonamiento y sentido común; donde un modelo instruct sangraría es en *seguimiento de instrucciones*, que no medí. Así que dice menos de lo que parece.

**Tamaño.** El modelo más grande olvidó algo menos: fine-tuning completo de 1.5B perdió −0.060 de media frente al −0.078 del 0.5B, inclinándose hacia "los modelos pequeños olvidan más". Pero el efecto es suave y no uniforme — claro en ARC-Easy, invertido en ARC-Challenge — y comparable al ruido entre semillas. (Hacer que el fine-tuning completo de 1.5B cupiera en una T4 de 16 GB requirió un optimizador de 8 bits descargado a CPU y batch de uno; en el primer intento se pasó de memoria por 200 MB. Una nota de oficio, no un hallazgo.)

## Para qué sirvió de verdad

Ninguno de los cuatro resultados sobreviviría como preprint — lo comprobé, y todos están ya en la literatura: el replay mitiga el olvido, LoRA olvida menos, los modelos grandes olvidan un poco menos. Fue una reproducción, en un escenario nuevecillo, a una escala que corres de una noche por calderilla.

El valor, para mí, fue el resultado del medio, y no va de modelos del mundo en absoluto. Cuando especializas un modelo y luego compruebas si conservó su capacidad general, *la respuesta que obtienes depende de cómo miraste*. Mismo modelo, mismos datos, misma tarea — un método reporta una pérdida real, el otro no reporta ninguna. Si solo tienes el instrumento silencioso, "sin olvido" no es evidencia de que no hubo olvido. Es solo silencio.

---

*Código y resultados completos: [github.com/JaviMaligno/language-world-model-forgetting](https://github.com/JaviMaligno/language-world-model-forgetting). Este es el tercero de una serie suelta sobre delegar en los modelos y seguir siendo capaz de notar cuándo se equivocan — ver también [¿Cuánto deberías seguir sabiendo?](/es/blog/how-much-should-you-still-know) y [Programación orientada a resultados](/es/blog/results-oriented-programming).*
