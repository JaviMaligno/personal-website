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

La pregunta tiene dos ejes, así que los crucé. Un eje es *quién lee*: un especialista diminuto entrenado exactamente para esto, o un generalista frontera. El otro es *qué se lee*: los píxeles de la retransmisión, o los tracks de jugadores que hay debajo.

En el lado *entrenado*, dos especialistas. Para los tracks: una red [DeepSets](https://arxiv.org/abs/1703.06114) — una arquitectura invariante a permutaciones que traga un conjunto desordenado de jugadores y lo agrega en una única predicción — entrenada con la posición y velocidad de cada jugador durante un segundo, nada más. Ni píxeles, ni césped, ni cuerpos. Unos 14.000 parámetros, ~60 kB de pesos, unos minutos de CPU en mi portátil. Para los píxeles: una red de visión pequeña de estantería (una ResNet-18) afinada sobre siete mil frames de retransmisión con el balón borrado por inpainting — para que no pueda detectarlo, solo inferirlo. Y los modelos frontera corrieron dos veces sobre los mismos ítems emparejados: una con los píxeles (el montaje de la Parte 1) y otra con **exactamente los mismos tracks de un segundo que vio la red diminuta, serializados como coordenadas en texto plano** — la misma información, sin píxeles.

![Los mismos ítems de balón oculto, dos tipos de input: una red diminuta entrenada vs VLMs frontera](/blog/wtb2-david-goliath.png)

El patrón es difícil de no ver. Los dos modelos entrenados baten el sesgo de la cámara en balones descentrados — **82%** desde los tracks, **74%** desde los píxeles. Los modelos frontera no lo hacen desde ninguno de los dos inputs: 53% con píxeles (estadísticamente, una moneda al aire) y 35-38% — por *debajo* del azar — con los propios tracks, donde su correlación con el balón real pasa de débilmente positiva a nula o ligeramente negativa: con las coordenadas crudas en la mano, derivan hacia la mismísima trampa del centroide que la geometría de broadcast castiga (siguiente sección). Dos notas mantienen el cuadro honesto. La columna de tracks usa tracking *ground-truth*, así que es un techo de información. Y en los ítems fáciles y centrados los VLM zero-shot siguen teniendo mejores medianas globales (0.147 vs 0.195-0.210): precisión de píxel donde la cámara ya ha hecho el trabajo.

El cuadro zanja la pregunta que la Parte 1 dejó abierta, descartando las excusas candidatas una a una. ¿Falta información? No — la columna de tracks la extrae. ¿El muro es percibir desde píxeles? Tampoco — una CNN pequeña entrenada llega casi hasta arriba desde los mismos frames enmascarados. Lo que separa las barras de esa gráfica no es el input; es la fila: **entrenado versus zero-shot. El conocimiento general del juego de los modelos frontera, en cualquier representación, no sustituye a la inferencia específica de la tarea** — que es exactamente la pregunta que planteaba la vista desde la grada.

## La cámara miente

Por el camino, una estadística explicó algo que me rondaba desde la Parte 1: ¿por qué la geometría ingenua es tan inútil en frames de retransmisión? El centroide de los jugadores — "el balón está donde está la masa" — no es solo poco informativo en espacio de imagen. Está *anti*-correlacionado con el balón (−0.58): cuando el balón está lejos del centro del encuadre, la masa de jugadores tiende a estar en el *lado contrario*.

![La misma estadística, dos espacios: la cámara le cambia el signo](/blog/wtb2-camera-lies.png)

La razón es el operador de cámara. Cuando un balón está descentrado, suele ser porque se mueve rápido — un pase largo, un despeje — corriendo *por delante* de la jugada mientras los jugadores van detrás. Proyecta eso sobre una cámara que persigue al balón y la geometría se invierte. Quita la cámara — calcula el mismo centroide en coordenadas de campo — y la correlación pasa a +0.83. La misma estadística, los mismos partidos; la cámara le cambia el signo. Todos los sistemas de la Parte 1 que se apoyaban en "el balón está cerca de los jugadores" se apoyaban en una mentira.

## Dos deportes, una pregunta: ¿qué transfiere de verdad?

Con un especialista funcional en la mano, por fin podía hacer la pregunta que motivó todo este proyecto desde la grada: **¿cuánto de esta habilidad es "saber de fútbol" y cuánto es estructura universal de deporte de equipo?** Entrené la misma arquitectura en fútbol (datos de tracking de Metrica y SkillCorner) y en baloncesto (NBA SportVU), y las crucé.

![La transferencia zero-shot entre deportes es asimétrica](/blog/wtb2-asymmetry.png)

En zero-shot — entrenado en un deporte, probado en frío en el otro — el resultado es asimétrico de una forma que no predije. Fútbol→baloncesto falla: peor que un centroide *sin entrenar*. Pero baloncesto→fútbol *funciona*: 0.17 de error mediano, batiendo a los propios baselines geométricos del fútbol sin haber visto nunca un partido de fútbol. Y no, no es que el dataset de baloncesto sea mayor — submuestreándolo al tamaño del de fútbol el resultado se mantiene (0.174).

Costó un par de pasos en falso concretarlo. Mi primera hipótesis — que el balón de baloncesto vive más cerca de la masa de jugadores — salió falsa: las distribuciones de distancia balón-masa son casi idénticas. El verdadero culpable es la **escala de velocidad**. Recorta cada jugador a *solo posiciones*, tirando el canal de velocidad, y la asimetría se desvanece — las posiciones transfieren simétricamente en ambos sentidos; es el *uso de la velocidad* lo que viaja en una sola dirección. Y la razón es un desajuste de unidades que debería haber visto venir: una cancha de baloncesto es una sexta parte del área de un campo de fútbol, así que en las coordenadas normalizadas que lee el modelo, los jugadores se mueven tres o cuatro veces más rápido en baloncesto. El sentido aprendido de "qué es rápido, y qué implica sobre dónde está el balón" está calibrado a la escala del propio deporte y falla al cruzar un salto de 3-4×. Las posiciones no llevan esa escala, así que cruzan sin problema. Esa es toda la asimetría — y una lección pequeña y general: lo que transfiere entre dominios es la estructura sin escala; todo lo que lleva unidades pegadas necesita recalibrarse.

![Al quitar el canal de velocidad, la transferencia entre deportes se vuelve simétrica](/blog/wtb2-asymmetry-velocity.png)

## Fine-tuning, y una hipótesis que murió dos veces

¿Pre-entrenar en un deporte da al menos ventaja para aprender otro? Aquí me quemé con mi propio entusiasmo — dos veces — y las dos veces lo cazó un control.

Primera pasada: con features instantáneas de jugador, pre-entrenar en fútbol no daba *ninguna* ventaja sobre entrenar desde cero con los mismos minutos de baloncesto. Segunda pasada: con trayectorias de un segundo *sí* — y estuve a punto de escribir "lo que transfiere es la dinámica temporal". Entonces un control de targets permutados (pre-entrenar la misma red con posiciones de balón aleatorizadas — mismo calentamiento de optimización, cero conocimiento) mostró que un tercio de esa ventaja era warm-start genérico. Y una ablación de features mostró que el resto no iba de profundidad temporal: la ventaja sigue a las variantes que usan features de *velocidad*, da igual snapshot que trayectoria.

![El pre-entreno real bate al scratch y al control permutado, en ambas direcciones](/blog/wtb2-pretraining-arms.png)

Lo que sobrevive a todos los controles, agregando ambas direcciones de transferencia: el pre-entreno real gana en 12/13 semillas contra scratch (p=0.002) y en 9/10 contra el control permutado (p=0.011), con una ventaja modesta (~5%) que solo aparece cuando tienes ~30 minutos del deporte destino. El cuadro refinado: **las posiciones llevan la señal central, pero su mapping es fácil — media hora de cualquier deporte lo enseña desde cero. Lo que transfiere de verdad es la habilidad, más costosa de adquirir, de explotar las velocidades**, que despista en zero-shot (las escalas de velocidad son específicas de cada deporte) pero rinde en cuanto se recalibra brevemente.

"Conocer el juego", para esta familia de modelos, resulta significar algo estrecho y concreto: saber qué hacer con el movimiento.

## Conclusiones

- **El entrenamiento importa; el input apenas.** Una red de 60 kB sobre tracks (82%) y una CNN pequeña sobre píxeles enmascarados (74%) resuelven ambas los balones descentrados; los modelos frontera zero-shot fallan con los dos inputs — 53% con píxeles, 35-38% (bajo el azar) con los mismísimos tracks en texto. Ni la información ni la percepción son el muro: el conocimiento general del juego no sustituye a la inferencia específica de la tarea.
- **La geometría de broadcast es una trampa.** El centroide de jugadores está anti-correlacionado con el balón en espacio de imagen (−0.58) y fuertemente correlacionado en coordenadas de campo (+0.83). La cámara cambia el signo.
- **La transferencia entre deportes es asimétrica, y la asimetría es un desajuste de escala de velocidad.** El baloncesto exporta su sentido del balón al fútbol; el fútbol no devuelve el favor. Las posiciones transfieren simétricamente en ambos sentidos — lo que se rompe es el *uso de la velocidad*, porque los dos deportes viven a 3-4× de distancia en la escala de velocidad normalizada. La estructura sin escala cruza; la parte con unidades, no.
- **Los controles hicieron el trabajo duro, otra vez.** Un control de pre-entreno permutado y una ablación de features tumbaron sendas conclusiones que estaba listo para publicar. Este proyecto va tres de tres en "la primera versión de la historia era falsa".

Lo siguiente es el Nivel 3 de esta escalera: la geometría y topología de debajo — *cuándo* determinan los jugadores al balón, y si estructura interpretable (células de Voronoi, pitch control, homología persistente) recupera lo que aprendió la cajita negra.

---

*Código, pipelines de datos, controles y auditorías en el repo [`wheres-the-ball`](https://github.com/JaviMaligno/wheres-the-ball). Tracking de jugadores de [SoccerNet-Tracking](https://github.com/SoccerNet/sn-tracking), [Metrica Sports](https://github.com/metrica-sports/sample-data), [SkillCorner](https://github.com/SkillCorner/opendata) y los logs NBA SportVU 2015-16 ([mirror](https://github.com/linouk23/NBA-Player-Movements); sin licencia explícita — uso solo para investigación, sin redistribución). Arquitectura: [DeepSets](https://arxiv.org/abs/1703.06114).*
