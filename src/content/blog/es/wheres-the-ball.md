---
title: "¿Dónde está el balón? Probando si un VLM tiene intuición de espectador"
description: "Le escondí el balón a varios modelos de visión-lenguaje y les pedí encontrarlo solo a partir de los jugadores. La respuesta fue interesante — pero lo más interesante fue lo cerca que estuve de concluir algo falso."
pubDate: 2026-07-22
tags: ["IA", "Visión por Computador", "Investigación"]
lang: es
translationKey: wheres-the-ball
heroImage: "/blog/wheres-the-ball.png"
linkedinImage: /blog/wheres-the-ball-correlation.png
repoUrl: https://github.com/JaviMaligno/wheres-the-ball
linkedinLinks:
  - label: "Dataset (SoccerNet-Tracking)"
    url: https://github.com/SoccerNet/sn-tracking
  - label: "Trabajo especialista más cercano (TranSPORTmer)"
    url: https://arxiv.org/abs/2410.17785
---

Mira un partido de fútbol desde la última fila del estadio, donde el balón es una mota apenas visible, y pasa algo curioso: normalmente sabes dónde está de todas formas. Te lo dicen los jugadores. Los cuerpos se inclinan, se forma un corro, todos empiezan a desplazarse en la misma dirección — y tu mirada aterriza en el balón un instante antes de verlo de verdad. No es *tracking*. Es una especie de inferencia *social*: conoces el juego, así que las personas te informan sobre la cosa.

Quería saber si un modelo de visión-lenguaje generalista tiene esa misma intuición. No un sistema especialista entrenado en trayectorias de balón — existen y son buenos ([Maksai et al.](https://arxiv.org/abs/1511.06181), [Kim et al. 2023](https://arxiv.org/abs/2306.08206), [TranSPORTmer](https://arxiv.org/abs/2410.17785) infieren el balón a partir del movimiento de los jugadores). Me refiero a un modelo que "conoce el juego" como lo conoce alguien en la grada, y que nunca ha sido entrenado para esta tarea en concreto. ¿Puede mirar un fotograma con el balón borrado y señalar dónde tiene que estar?

La respuesta honesta resultó ser *sí, un poco, y solo los modelos más grandes* — pero llegar a una respuesta en la que confío de verdad fue casi todo el trabajo, y es la parte que merece la pena contar.

## El montaje

Usé [SoccerNet-Tracking](https://github.com/SoccerNet/sn-tracking): clips de retransmisión con cajas por fotograma para cada jugador y el balón. En cada fotograma **eliminé el balón** con inpainting LaMa — inpainting profundo que reconstruye un parche coherente de césped, línea o camiseta donde estaba el balón, para que el modelo no pueda hacer trampa detectando el borrón de la edición. (El inpainting clásico dejaba manchas delatoras sobre las líneas del campo; un paso de control de fuga con un VLM confirmó que la versión profunda no deja nada a lo que agarrarse.) Después pedí a varios modelos las coordenadas del balón y medí la distancia a la verdad.

Los modelos: **GPT-5.4**, **Claude Opus 4.8**, **Claude Sonnet 4.6** (todos por API) y **Qwen2.5-VL-7B** como referencia open-source, ejecutado en GPU. Frente a ellos, dos baselines tontos: "el balón está en el centro del fotograma" y "el balón está en el centroide de los jugadores".

## La trampa en la que caí de cabeza

Mi primera ejecución pintaba genial. GPT batía al baseline del centro; en los casos más difíciles — balones lejos del medio del fotograma — parecía ganar el **64%** de las veces. Historia redonda: la IA generalista tiene intuición de espectador. Podría haber escrito *ese* artículo.

Dos problemas, ambos míos.

Primero, un *confound*. Las cámaras de retransmisión *siguen al balón* — lo mantienen cerca del centro del plano. Así que "adivina el centro" no es un baseline tonto en absoluto; es fuerte, y cualquier modelo que tienda al centro parece listo por el motivo equivocado. Segundo, y peor: mi muestra era diminuta. Aquel 64% salía de **14 ítems**. Cuando le puse un intervalo de confianza por bootstrap, el intervalo iba del 36% al 86% — incluyendo cómodamente el 50%, es decir, el azar.

![Cómo una muestra pequeña casi nos engaña](https://www.javieraguilar.ai/blog/wheres-the-ball-sample-trap.png)

Así que reconstruí la prueba para desactivar ambos problemas: balanceé el dataset por la distancia del balón al centro (para que "adivina el centro" sea inútil por construcción) y escalé la muestra. Con más datos, ese mismo porcentaje de victorias en balones descentrados se quedó en **55%**, y su intervalo *seguía* tocando el 50%. El emocionante primer resultado no había sobrevivido al contacto con la estadística. Era un espejismo hecho de una cámara que sigue al balón y catorce puntos de datos.

Lo cuento no por falsa modestia, sino porque es justo el quid: un baseline confundido más una muestra pequeña te entregan una conclusión satisfactoria, publicable y falsa, y *se siente* verdadera. La única defensa es aburrida — de-sesgar, escalar, bootstrap, e intentar tumbar tu propio hallazgo antes de creértelo.

## Lo que sí es verdad

Una vez la muestra fue honesta, dejé de apoyarme en el error sobre un subconjunto difícil (aún con poca potencia) y usé una medida mejor comportada: **¿correlaciona la predicción del modelo con dónde está el balón realmente**, a lo largo de todo el rango de posiciones? A esa pregunta sí pueden responder los datos.

![Correlación de la predicción de cada modelo con la posición real del balón](https://www.javieraguilar.ai/blog/wheres-the-ball-correlation.png)

- **Claude Opus 4.8** tiene la señal más clara — sus predicciones siguen la posición real del balón en ambos ejes, y los intervalos de confianza se mantienen lejos del cero.
- **GPT-5.4** muestra señal parcial (sólida en horizontal, más ruidosa en vertical).
- **Qwen2.5-VL-7B (abierto)** y **Claude Sonnet 4.6** son, estadísticamente, **planos** — sus intervalos cruzan el cero. No es que apunten al centro por pereza (lo comprobé — sus predicciones están repartidas); simplemente no siguen al balón.

Así que la intuición de espectador es real, pero tenue, y es un rasgo de modelo frontera: aparece en los grandes modelos cerrados y no en el abierto pequeño ni en el Claude de gama media. Y una advertencia sobria que sobrevivió a todo el escalado: **desde un solo fotograma, ningún modelo bate de forma fiable el sesgo del centro en balones genuinamente descentrados.** La intuición está ahí en agregado; no es lo bastante fuerte como para clavar los casos difíciles y amplios desde una sola imagen fija.

Un giro más, que me gustó. Le di a cada modelo un prompt "informado" — nombrando el deporte y detallando lo que usa un espectador (los jugadores se orientan hacia el balón, convergen sobre él, el que lo lleva encabeza un corro). Ayudó **mucho a GPT** (su correlación dio un salto), **nada a Sonnet** y apenas movió a Opus. Léelo con cuidado: el problema de Sonnet nunca fue que no supiera de fútbol. Explicarle las reglas no cambió nada, porque su cuello de botella es *ver*, no *saber*. Para GPT, que ya podía razonar sobre la escena, el marco desbloqueó margen — el prompt importó tanto como la gama del modelo.

## El vídeo que no iba de vídeo

Aquí estaba seguro de saber la respuesta de antemano. Un solo fotograma es ambiguo; el truco real del espectador es ver la jugada *desarrollarse*. Así que di a los modelos secuencias cortas — cuatro fotogramas abarcando unos segundos, el balón borrado en todos — esperando que el movimiento desbloqueara los casos difíciles.

Y parecía ayudar a GPT. Pero antes de creérmelo, ejecuté el control que importa: **desordené los fotogramas en orden aleatorio**. Si un modelo lee movimiento, revolver el tiempo debería destruir el beneficio.

![Nadie lee el movimiento — es un efecto multi-vista](https://www.javieraguilar.ai/blog/wheres-the-ball-multiview.png)

Desordenar no cambió nada. El orden de los fotogramas fue el nulo más limpio de todo el experimento. Ningún modelo integra la *trayectoria* de la jugada — no razonan sobre el movimiento en absoluto. Lo que sí cambiaba con varios fotogramas era algo más soso y más raro: **vistas extra de la escena**, en cualquier orden. Y los dos modelos frontera lo manejan de forma opuesta. GPT *agrega* — más miradas al momento, aunque estén revueltas, afinan su predicción. Opus se *diluye* — los fotogramas extra lo alejan de una lectura del fotograma objetivo en la que ya era mejor. El mejor modelo con una sola imagen era el peor usando más imágenes.

Es un hallazgo más interesante que "el vídeo ayuda", y me lo habría perdido si me hubiera fiado de la primera versión, la halagadora.

## Conclusiones

- **Los VLM generalistas sí tienen una tenue intuición de espectador** — sus predicciones correlacionan con el balón oculto — pero es un rasgo de modelo frontera (Opus la más clara, GPT parcial) y es débil: un solo fotograma no resuelve los casos genuinamente difíciles.
- **No razonan sobre el movimiento.** Lo que parece comprensión temporal es en realidad agregación multi-vista, y los modelos difieren en si las vistas extra ayudan o estorban.
- **El cuello de botella no es el conocimiento; es ver.** Explicar el juego ayudó al modelo que ya podía razonar visualmente y no hizo nada por el que no podía.
- **La metodología fue la parte difícil.** Una cámara que sigue al balón y una muestra pequeña produjeron una historia limpia y falsa que se sentía correcta. De-sesgar, escalar, hacer bootstrap y auditar de forma adversarial mis propios resultados cambió la conclusión dos veces.

Hay un Nivel 2 esperando — otros deportes, si la habilidad transfiere, y la geometría que subyace a todo esto — pero eso es para más adelante. Por ahora el titular honesto es más pequeño y mejor que el que estuve a punto de escribir: el modelo en la grada puede intuir dónde está el balón, un poco, si es lo bastante grande; lo que no puede es mirar la jugada para encontrarlo.

---

*El código, el pipeline de datos y la auditoría completa (con IC por bootstrap incluidos) están en el repo [`wheres-the-ball`](https://github.com/JaviMaligno/wheres-the-ball). Construido sobre [SoccerNet-Tracking](https://github.com/SoccerNet/sn-tracking); balón eliminado con [LaMa](https://github.com/advimman/lama) vía [IOPaint](https://github.com/Sanster/IOPaint). Trabajo especialista previo que merece la pena leer: [Maksai et al.](https://arxiv.org/abs/1511.06181), [Kim et al. 2023](https://arxiv.org/abs/2306.08206), [TranSPORTmer](https://arxiv.org/abs/2410.17785).*
