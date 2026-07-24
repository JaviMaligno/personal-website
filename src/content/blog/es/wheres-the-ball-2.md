---
title: "¿Dónde está el balón? Parte 2 — un modelo de 60 kilobytes, dos deportes y la señal que los VLM no ven"
description: "Una red diminuta entrenada en mi portátil resuelve los casos del balón oculto que los VLM frontera no pueden — y un estudio de transferencia entre dos deportes revela qué aprende exactamente un modelo sobre un juego."
pubDate: 2026-07-27
tags: ["IA", "Visión por Computador", "Investigación"]
lang: es
translationKey: wheres-the-ball-2
heroImage: "/blog/wheres-the-ball-2.png"
linkedinImage: /blog/wtb2-david-goliath.png
repoUrl: https://github.com/JaviMaligno/wheres-the-ball
linkedinLinks:
  - label: "Parte 1 (el benchmark de VLMs)"
    url: https://www.javieraguilar.ai/es/blog/wheres-the-ball/
  - label: "Datos de tracking NBA SportVU"
    url: https://github.com/linouk23/NBA-Player-Movements
---

La [Parte 1](https://www.javieraguilar.ai/es/blog/wheres-the-ball/) terminaba con una nota sobria. Los modelos de visión-lenguaje frontera tienen una tenue intuición de espectador — sus predicciones sobre un balón oculto correlacionan con dónde está de verdad — pero en los casos que importan, balones genuinamente lejos del centro del encuadre, ninguno batía de forma fiable la estrategia más tonta posible: apuntar al medio y confiar en el operador de cámara.

Eso dejaba una pregunta incómoda en el aire. Quizá los casos difíciles son simplemente *difíciles* — quizá las posiciones de los jugadores no contienen información suficiente para encontrar un balón descentrado, y les estaba pidiendo a los modelos un imposible.

Así que lo probé directamente. La respuesta es no: la información está ahí, y puede extraerla un modelo tan pequeño que cabe en un correo.

## David, te presento a Goliat

Entrené una red [DeepSets](https://arxiv.org/abs/1703.06114) — una arquitectura invariante a permutaciones que traga un conjunto desordenado de jugadores y lo agrega en una única predicción — sobre los *tracks* de jugadores de los clips de entrenamiento de SoccerNet: la posición y velocidad de cada jugador durante un segundo, y nada más. Ni píxeles, ni césped, ni cuerpos. Unos 14.000 parámetros, ~60 kB de pesos, unos minutos de CPU en mi portátil, cero llamadas a APIs.

Después la evalué sobre los mismos ítems de balón oculto de la Parte 1, emparejada con los mismos modelos.

![Una red diminuta alimentada con tracks bate el sesgo de cámara donde los VLM frontera se quedan en el azar](/blog/wtb2-david-goliath.png)

En balones descentrados, la red diminuta bate el sesgo de la cámara el **82% de las veces**; GPT-5.4 y Claude Opus 4.8 se quedan en el 53% — estadísticamente, una moneda al aire. Dos notas honestas antes de que esto se le suba a nadie a la cabeza. Primera: el modelito lee tracks de jugadores *ground-truth*, así que esto es un techo de información — responde a "¿está la señal ahí?", no a "¿puedes percibirla desde píxeles?". Segunda: los VLM siguen teniendo mejores medianas globales (0.147 vs 0.195), porque son precisos al píxel en los ítems fáciles y centrados donde la cámara ya ha hecho el trabajo. Ítem a ítem contra cada VLM en el subconjunto difícil, la redecita gana el 59-62% — favorable en dirección, no significativo individualmente con n=34.

Pero la afirmación central sobrevive a los matices, y reencuadra la Parte 1: **la posición del balón está escrita en los movimientos de los jugadores — con la claridad suficiente para un modelo de juguete — y los VLM de hoy no saben leerla de los píxeles.** Su fallo no es que la tarea sea imposible. Es un problema de lectura.

## La cámara miente

Por el camino, una estadística explicó algo que me rondaba desde la Parte 1: ¿por qué la geometría ingenua es tan inútil en frames de retransmisión? El centroide de los jugadores — "el balón está donde está la masa" — no es solo poco informativo en espacio de imagen. Está *anti*-correlacionado con el balón (−0.58): cuando el balón está lejos del centro del encuadre, la masa de jugadores tiende a estar en el *lado contrario*.

![La misma estadística, dos espacios: la cámara le cambia el signo](/blog/wtb2-camera-lies.png)

La razón es el operador de cámara. Cuando un balón está descentrado, suele ser porque se mueve rápido — un pase largo, un despeje — corriendo *por delante* de la jugada mientras los jugadores van detrás. Proyecta eso sobre una cámara que persigue al balón y la geometría se invierte. Quita la cámara — calcula el mismo centroide en coordenadas de campo — y la correlación pasa a +0.83. La misma estadística, los mismos partidos; la cámara le cambia el signo. Todos los sistemas de la Parte 1 que se apoyaban en "el balón está cerca de los jugadores" se apoyaban en una mentira.

## Dos deportes, una pregunta: ¿qué transfiere de verdad?

Con un especialista funcional en la mano, por fin podía hacer la pregunta que motivó todo este proyecto desde la grada: **¿cuánto de esta habilidad es "saber de fútbol" y cuánto es estructura universal de deporte de equipo?** Entrené la misma arquitectura en fútbol (datos de tracking de Metrica y SkillCorner) y en baloncesto (NBA SportVU), y las crucé.

![La transferencia zero-shot entre deportes es asimétrica](/blog/wtb2-asymmetry.png)

En zero-shot — entrenado en un deporte, probado en frío en el otro — el resultado es asimétrico de una forma que no predije. Fútbol→baloncesto falla: peor que un centroide *sin entrenar*. Pero baloncesto→fútbol *funciona*: 0.17 de error mediano, batiendo a los propios baselines geométricos del fútbol sin haber visto nunca un partido de fútbol. Y no, no es que el dataset de baloncesto sea mayor — submuestreándolo al tamaño del de fútbol el resultado se mantiene (0.174).

Mi interpretación de trabajo: en baloncesto el balón está casi siempre estrechamente acoplado a la masa de jugadores — botes, bloqueos, pases cortos — así que el modelo aprende un acoplamiento fuerte que resulta ser un prior universal decente. El fútbol, con sus pelotazos y su juego suelto, enseña un acoplamiento débil que no se exporta. Si quieres un modelo con instinto de lectura de juego portable, entrénalo en el deporte donde el balón nunca abandona a la masa.

## Fine-tuning, y una hipótesis que murió dos veces

¿Pre-entrenar en un deporte da al menos ventaja para aprender otro? Aquí me quemé con mi propio entusiasmo — dos veces — y las dos veces lo cazó un control.

Primera pasada: con features instantáneas de jugador, pre-entrenar en fútbol no daba *ninguna* ventaja sobre entrenar desde cero con los mismos minutos de baloncesto. Segunda pasada: con trayectorias de un segundo *sí* — y estuve a punto de escribir "lo que transfiere es la dinámica temporal". Entonces un control de targets permutados (pre-entrenar la misma red con posiciones de balón aleatorizadas — mismo calentamiento de optimización, cero conocimiento) mostró que un tercio de esa ventaja era warm-start genérico. Y una ablación de features mostró que el resto no iba de profundidad temporal: la ventaja sigue a las variantes que usan features de *velocidad*, da igual snapshot que trayectoria.

![El pre-entreno real bate al scratch y al control permutado, en ambas direcciones](/blog/wtb2-pretraining-arms.png)

Lo que sobrevive a todos los controles, agregando ambas direcciones de transferencia: el pre-entreno real gana en 12/13 semillas contra scratch (p=0.002) y en 9/10 contra el control permutado (p=0.011), con una ventaja modesta (~5%) que solo aparece cuando tienes ~30 minutos del deporte destino. El cuadro refinado: **las posiciones llevan la señal central, pero su mapping es fácil — media hora de cualquier deporte lo enseña desde cero. Lo que transfiere de verdad es la habilidad, más costosa de adquirir, de explotar las velocidades**, que despista en zero-shot (las escalas de velocidad son específicas de cada deporte) pero rinde en cuanto se recalibra brevemente.

"Conocer el juego", para esta familia de modelos, resulta significar algo estrecho y concreto: saber qué hacer con el movimiento.

## Conclusiones

- **La señal está en los tracks.** Una red de 60 kB sobre tracks de jugadores resuelve los balones descentrados que los VLM frontera no pueden, batiendo el sesgo de cámara el 82% de las veces donde ellos están en el azar. El fallo de los VLM en la Parte 1 es un problema de lectura de píxeles, no de información.
- **La geometría de broadcast es una trampa.** El centroide de jugadores está anti-correlacionado con el balón en espacio de imagen (−0.58) y fuertemente correlacionado en coordenadas de campo (+0.83). La cámara cambia el signo.
- **La transferencia entre deportes es real, pequeña y asimétrica.** El baloncesto exporta su sentido del balón al fútbol; el fútbol no devuelve el favor. Lo que transfiere no son reglas ni formaciones — es el uso de las velocidades, que vale ~5% tras calibrar.
- **Los controles hicieron el trabajo duro, otra vez.** Un control de pre-entreno permutado y una ablación de features tumbaron sendas conclusiones que estaba listo para publicar. Este proyecto va tres de tres en "la primera versión de la historia era falsa".

Lo siguiente es el Nivel 3 de esta escalera: la geometría y topología de debajo — *cuándo* determinan los jugadores al balón, y si estructura interpretable (células de Voronoi, pitch control, homología persistente) recupera lo que aprendió la cajita negra. También está en preparación un paper de workshop con el estudio de transferencia completo.

---

*Código, pipelines de datos, controles y auditorías en el repo [`wheres-the-ball`](https://github.com/JaviMaligno/wheres-the-ball). Tracking de jugadores de [SoccerNet-Tracking](https://github.com/SoccerNet/sn-tracking), [Metrica Sports](https://github.com/metrica-sports/sample-data), [SkillCorner](https://github.com/SkillCorner/opendata) y los logs NBA SportVU 2015-16 ([mirror](https://github.com/linouk23/NBA-Player-Movements); sin licencia explícita — uso solo para investigación, sin redistribución). Arquitectura: [DeepSets](https://arxiv.org/abs/1703.06114).*
