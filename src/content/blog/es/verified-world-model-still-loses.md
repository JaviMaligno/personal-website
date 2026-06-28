---
title: "Un modelo del mundo puede pasar todos los tests y aun así perder"
description: "Quise reproducir un resultado de DeepMind y acabé encontrando una forma limpia en la que la verificación te puede engañar: un modelo del mundo en código que pasa su gate al 100% de precisión, mantiene un 99% de acierto en los estados que visita un planificador, y aun así pierde sistemáticamente al jugar."
pubDate: 2026-06-28
tags: ["IA", "Machine Learning", "Testing", "Investigación", "Agentes"]
lang: es
translationKey: verified-world-model-still-loses
heroImage: "/blog/verified-world-model-still-loses.png"
publishToDevto: true
---
Hace un tiempo escribí que la programación se está desplazando de verificar *cómo* funciona el código a verificar *qué* produce — [programación orientada a resultados](/es/blog/results-oriented-programming). Este post es lo que pasó cuando me tomé esa idea lo bastante en serio como para romperla. Quise reproducir un resultado de DeepMind y acabé varias semanas con una pregunta pequeña y testaruda: **si un chequeo de resultado pasa, ¿significa eso de verdad que el resultado es correcto?** La respuesta resulta ser "no necesariamente" — y se puede decir exactamente cuándo falla, y demostrar parte del porqué.

Lo escribí todo como un preprint, *When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models*. <!-- TODO: poner la URL real de arXiv cuando esté publicado --> El enlace de arXiv irá aquí cuando esté arriba; el resto de este post es la historia en lenguaje llano.

## El planteamiento: Code World Models

El paradigma que estaba hurgando viene del paper de DeepMind *Code World Models for General Game Playing* ([Lehrach et al., 2025](https://arxiv.org/abs/2510.04542)). En vez de pedirle a un modelo de lenguaje que *juegue* directamente, le pides que **escriba las reglas del juego como un programa en Python** — un "modelo del mundo" con funciones para movimientos legales, transiciones y resultados. Luego un planificador clásico (Monte Carlo Tree Search) juega *contra ese programa sintetizado*. La división del trabajo es elegante: el LLM hace traducción (reglas → código) y la búsqueda clásica hace la anticipación.

Funciona bien, y en juegos conocidos un modelo pequeño + MCTS le gana por mucho al mismo modelo usado como política directa. Eso lo reproduje. Pero un paso me incomodaba: **el paso de verificación.**

Antes de que el planificador confíe en el modelo del mundo sintetizado, el modelo se *refina* hasta alcanzar el 100% de precisión de transición sobre un lote de partidas aleatorias — siguiente estado, movimientos legales, resultado, todo coincidiendo con el juego real. Si lo pasas, "pasas el gate". Parece un chequeo de corrección limpio y automático.

La pregunta que no me podía quitar de encima: **pasar ese gate significa que el modelo coincide con la verdad en juego aleatorio. ¿Significa que el modelo es lo bastante bueno para planificar con él?**

## El nulo honesto

Lo primero, la parte aburrida e importante: en juegos pequeños y completamente especificados, el gate *sí* basta. Tres en raya, una variante de ajedrez generalizado, Trike — siempre que un modelo sintetizado pasaba el gate, también era correcto en los estados que el planificador realmente visita. Sin brecha. Lo reporto como resultado nulo, porque marca la frontera: el gate es un filtro fuerte cuando las reglas están completas y el espacio de estados es pequeño.

Así que la pregunta interesante pasa a ser: **¿cuándo se puede engañar al gate?** Y la condición es precisa: necesitas una regla que el juego aleatorio casi nunca dispara pero que el juego competente busca de forma fiable.

## El instrumento: una regla rara que decide partidas

Para hacer real esa condición no inventé un juego desde cero — tomé un juego de ajedrez generalizado *del propio paper de DeepMind* (un tablero 5×5 con piezas de general, infantería y caballería, llamado `army5x5a`) y le añadí una regla: si la partida llega a un tope alto de jugadas con ambos generales aún vivos, gana quien tenga más material en vez de empatar. Bajo juego *aleatorio*, esa regla decide la partida un 2.5% de las veces — las partidas aleatorias acaban pronto, por error. Bajo juego *competente* decide cerca de la mitad de las partidas, porque el buen juego sobrevive hasta el tope.

Ahora omite esa regla de la especificación y sintetiza un modelo del mundo. El resultado es un modelo que:

- pasa el gate al **100% de precisión de transición**,
- es **≥99% preciso** sobre la distribución exacta de estados que visita el planificador,
- y aun así **pierde más o menos 2:1 al jugar** (tasa de victoria 0.376 vs un baseline calibrado de 0.493, con intervalos de confianza que no se solapan).

El 1% que falla es exactamente el 1% que decide partidas. Las medias lo esconden — el error queda *diluido* por todas las posiciones normales que acierta. Precisión de predicción y adecuación para jugar se separan, de forma limpia y reproducible.

## Una ley para cuándo la verificación se queda ciega

Lo bonito es que esto no es una anécdota aislada; tiene forma. El daño esperado sigue

$$\text{daño} = \text{play\_cost} \times (1 - \text{rareza})^N$$

donde `rareza` es cada cuánto una partida aleatoria dispara la regla omitida y $N$ cuántas partidas muestrea el gate. El factor $(1 - \text{rareza})^N$ es exacto — es simplemente la probabilidad de que $N$ partidas aleatorias independientes fallen todas la regla. Así que el daño es despreciable mientras la regla sea lo bastante común como para que la cacen, sube atravesando un umbral según se hace más rara, y se satura en el coste completo de la regla cuando casi siempre escapa al gate.

Hay una lectura más afilada de ese factor. Cuando la regla nunca aparece en la muestra, los datos son *literalmente idénticos* esté la regla en el modelo o no. Así que ningún aprendiz de ningún tipo — ni un LLM más grande, ni descenso por gradiente, ni búsqueda exhaustiva — puede recuperar la regla **solo a partir de esa muestra**. No es una debilidad del modelo; es información que falta. Cualquier recuperación tiene que venir de la especificación, no de los datos.

## Traducción, no inferencia

Eso lleva al hallazgo que me parece más práctico. ¿Se puede *reparar* la brecha dándole al modelo ejemplos de la regla? Lo intenté — en serio: DAgger, estados cosechados on-manifold, decenas de ejemplos discriminantes, dos tamaños de modelo, bucles de refinamiento que sacan datos frescos en cada iteración.

(Para fans del imitation learning: el "DAgger propio" aquí es el bucle de [Ross et al. (2011)](https://arxiv.org/abs/1011.0686) — recoger estados del propio juego del modelo defectuoso y reetiquetarlos con el oráculo — no solo volcar trayectorias competentes.)

No funciona. En todos los casos, el modelo sintetizado sigue ciego a la regla incluso cuando la regla está presente en sus trayectorias casi con certeza (se puede ver: la precisión del gate se queda muy por debajo de 1.0, lo que significa que la regla *está* en los datos, y tras seis pasadas de refinamiento el modelo aún no la ha codificado). El comportamiento es **traducción de reglas, no inferencia de reglas**: el modelo codifica fielmente las reglas que se le *dicen*, y no infiere de forma fiable las reglas que solo se le *muestran*. La versión accionable: completa la especificación antes de sintetizar. Verificar sobre la distribución de juego *detectará* una especificación incompleta; no la *reparará*.

## La misma trampa en el lado de las creencias

Los juegos con información oculta (tipo póker) añaden una segunda superficie: la *función de creencias* del modelo — cómo reconstruye lo que no puede ver. Aquí pude demostrar algo limpio: un gate muestreado sobre juego aleatorio es *demostrablemente* suficiente para certificar la función de creencias en juegos pequeños o poco profundos (por eso Kuhn y Leduc poker no muestran brecha). Pero la función de creencias tiene su propio punto ciego, y un gate de precisión de transición es *estructuralmente* ciego a él — la información sobre qué puede y qué no puede ver un jugador no aparece nunca en una transición. Esto lo muestro con testigos construidos a mano, no con modelos sintetizados, y soy explícito sobre esa línea en el paper.

## Lo que me llevo de esto

Dos cosas, una técnica y otra sobre cómo se hizo el trabajo.

**Técnica:** una batería de tests que pasa — o un gate basado en muestreo — es un *chequeo de resultado con un punto ciego de cobertura*. Certifica el modelo justo donde caen tus muestras, y el comportamiento competente cae sistemáticamente en otra parte: las zonas raras, decisivas y profundas del espacio. Si verificas un modelo del mundo (o, francamente, cualquier modelo usado para planificar o decidir) por muestreo, mide la adecuación **sobre la distribución en la que realmente se va a usar**, no sobre una aleatoria cómoda. Y cuando la corrección depende de una regla, pon la regla en la especificación — no esperes que el sistema la infiera.

**Meta:** la disciplina que endureció este paper no fue "afirmar menos". Fue, para cada afirmación grande, separar la parte que de verdad podía *demostrar* de la parte que solo estaba *medida* — y decir cuál era cuál. Es el mismo reflejo orientado a resultados (verifica el resultado, y sé preciso sobre qué cubre ese "verificado"), aplicado a un paper en vez de a un programa.

Si quieres la versión formal, con los teoremas y los números, está en el preprint. <!-- TODO: URL de arXiv --> El código también es abierto.

---

*Preprint: "When a Verified World Model Still Loses" (enlace de arXiv pronto). Lecturas relacionadas: [Programación Orientada a Resultados](/es/blog/results-oriented-programming) y [Software Disolviéndose en el Modelo](/es/blog/software-dissolving-into-the-model).*
