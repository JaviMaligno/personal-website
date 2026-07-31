---
title: "¿Dónde está el balón? Parte 4 — cuando nada se mueve"
description: "Un coda de la trilogía: perseguir el punto ciego del especialista me llevó a donde no esperaba. El balón más difícil de localizar no es el que vuela por el aire — es el que está perfectamente quieto."
pubDate: 2026-07-31
tags: ["IA", "Visión por Computador", "Investigación"]
lang: es
translationKey: wheres-the-ball-4
heroImage: "/blog/wheres-the-ball-4.png"
linkedinImage: /blog/wtb4-ball-state.png
repoUrl: https://github.com/JaviMaligno/wheres-the-ball
linkedinLinks:
  - label: "Parte 1 (el benchmark de VLMs)"
    url: https://www.javieraguilar.ai/es/blog/wheres-the-ball/
  - label: "Parte 2 (el modelo de 60 kB y el estudio de transferencia)"
    url: https://www.javieraguilar.ai/es/blog/wheres-the-ball-2/
  - label: "Parte 3 (abriendo la caja negra)"
    url: https://www.javieraguilar.ai/es/blog/wheres-the-ball-3/
---

La [Parte 3](https://www.javieraguilar.ai/es/blog/wheres-the-ball-3/) cerraba la trilogía con un punto ciego: el especialista diminuto es sobreconfiado en los *balones sueltos* — los que están en espacio abierto, lejos de la masa de jugadores. Pensaba parar ahí. Pero una pregunta seguía rondándome, y perseguirla mereció un post más.

La pregunta: ¿no son esos casos duros simplemente **valores parados**? Un córner, una falta — dónde está el balón depende por completo de si el lanzador ya lo ha golpeado o no. Antes del lanzamiento está sobre una marca de cal; después, es un proyectil al que los jugadores todavía están reaccionando. Quizá el error amplio va en realidad de ese momento incómodo intermedio, el balón en vuelo mientras todos se recolocan alrededor de a dónde va.

Es una buena hipótesis. También es falsa — y equivocarme apuntó a algo mejor.

## La premisa no sobrevivió al contacto

Los datos de Metrica traen un registro de eventos — cada pase, tiro y valor parado, con marca de tiempo y las coordenadas de inicio y fin del balón. Así que pude etiquetar cada frame según lo que ocurría y preguntar dónde vive el error de verdad.

Los valores parados apenas aparecen: como fracción del tiempo de juego son un error de redondeo, porque el evento "valor parado" es el instante de ejecución, no una fase en la que pasas minutos. Los balones largos y despejes *sí* eran algo más difíciles que los pases cortos — una pequeña victoria para la versión ampliada de la hipótesis — pero tampoco dominaban. El error amplio estaba repartido por el juego abierto normal.

El corte más nítido no era la etiqueta de evento en absoluto. Era la **velocidad del balón**.

![El modelo necesita movimiento: el balón quieto es el punto ciego](/blog/wtb4-ball-state.png)

Y le da la vuelta a la intuición. El balón *en vuelo* — rápido, por el aire, el caso que yo esperaba que fuera el más difícil — es solo moderadamente difícil. El balón más difícil de localizar es el que apenas se mueve: asentado, por debajo de 2 m/s, un balón muerto o parado a los pies de alguien. La correlación entre velocidad del balón y error es esencialmente nula; toda la estructura está en esa primera barra.

## Sin movimiento, sin señal

Una vez lo ves, es el resultado más fiel al proyecto que podía salir. Cada parte de esta serie ha aterrizado en el mismo hallazgo: la señal que lee un modelo para situar un balón oculto es el **movimiento** — hacia dónde va la masa de jugadores que corre. Entonces, ¿qué pasa cuando nada se mueve?

No hay nada que leer.

![La velocidad es la señal — y es casi inútil cuando nada se mueve](/blog/wtb4-velocity-mechanism.png)

Quita el canal de velocidad del modelo y mira cuánto cuesta, separando según si el balón se mueve o no. Cuando el balón se mueve, la velocidad vale mucho — quitarla infla el error en unos 0.04. Cuando el balón está quieto, la velocidad no vale casi nada: el modelo con velocidad y el modelo sin ella son casi iguales, porque no hay movimiento coherente del que las features de velocidad puedan alimentarse. Toda la ventaja del especialista se evapora justo en el momento en que el campo se queda quieto. (Se mantuvo en ambas direcciones de train/test, y el desplome era aún más marcado al revés — la contribución de la velocidad caía prácticamente a cero en los balones quietos.)

Hay una segunda razón por la que los balones quietos son difíciles, y afila el punto ciego de la Parte 3. Los *peores* balones quietos no son los de junto a una banda, donde un saque de banda junta a los jugadores en un grupo ordenado. Son los que están **en el centro, lejos de todos** — un balón muerto en medio del campo con los jugadores repartidos y nadie convergiendo. Entre los balones quietos, la correlación entre "distancia a la masa de jugadores" y error es fuerte y estable (+0.53 a +0.65 en ambas direcciones). Un balón del que nadie está cerca y hacia el que nadie se mueve está, literalmente, indeterminado: los jugadores han dejado de decirte dónde está.

## Pero en vuelo, aún puedes leer la *dirección*

Queda la otra mitad de la pregunta original. Aunque el balón en vuelo no sea el caso más difícil, la intuición detrás era real: mientras un balón viaja, los jugadores ya están dando forma a lo que viene con sus carreras. Quizá lo recuperable ahí no es la posición exacta del balón, sino a dónde *va*.

Así que le hice al modelo una pregunta distinta sobre los balones rápidos — no "¿dónde está?" sino "¿hacia dónde va?" — y le pedí que predijera la dirección de viaje del balón solo a partir de los jugadores.

![En vuelo, hacia dónde va el balón sí es legible](/blog/wtb4-direction-flight.png)

Puede. Una conjetura aleatoria de una dirección en 2D se equivoca por 90° de media; los jugadores la acotan a unos 45°, con la mitad de los balones rápidos situados dentro de un cono de 45°. No es preciso — pero es inequívocamente real: la configuración del campo codifica hacia dónde viaja el balón, porque los jugadores ya se están inclinando hacia la jugada. Seré honesto en que esto no gana limpiamente a la posición — en vuelo, dirección y posición resultan recuperables en grado parecido, y comparar un ángulo con una distancia es mezclar peras con manzanas. La afirmación honesta es la modesta: la dirección es legible, no que gane.

## Conclusiones

- **El balón más difícil de encontrar es el que está quieto.** No el balón en vuelo — el balón asentado, por debajo de 2 m/s, es donde el error del especialista es mayor. Velocidad del balón y error están por lo demás sin correlacionar; la dificultad se concentra por entero en la quietud.
- **Porque el movimiento es toda la señal.** Las features de velocidad sostienen la localización; cuando el balón está quieto no hay movimiento que leer, y quitar la velocidad no cuesta casi nada. La fuerza del modelo y su punto ciego son el mismo hecho visto por dos caras.
- **Un balón muerto del que nadie está cerca está indeterminado.** Los peores balones quietos son centrales y lejos de la masa de jugadores (correlación acoplamiento-error +0.53 a +0.65) — los jugadores simplemente han dejado de apuntar hacia él.
- **En vuelo, la dirección es legible aunque la posición no sea precisa.** Las carreras de los jugadores acotan el rumbo de un balón rápido a ~45° (el azar es 90°). La corazonada de los valores parados se equivocaba sobre *qué* fase es difícil, pero acertaba en que los jugadores siempre están dando forma a lo que viene.

Cuatro partes después, el hilo conductor es difícil de no ver. Un balón oculto se encuentra a través del movimiento — los modelos frontera no saben ejecutar esa pista, una red de 60 kB la lee con nitidez, y resulta ser geometría pura. Lo que significa que lo único que ninguno de ellos sabe hacer es encontrar un balón que ha dejado de moverse y se ha alejado del grupo. El punto ciego nunca fue un tipo de jugada. Era la quietud.

---

*Código, el análisis del registro de eventos y los experimentos de ablación de velocidad y de dirección en el repo [`wheres-the-ball`](https://github.com/JaviMaligno/wheres-the-ball). Tracking y datos de eventos de fútbol de [Metrica Sports](https://github.com/metrica-sports/sample-data). Antes: [Parte 1](https://www.javieraguilar.ai/es/blog/wheres-the-ball/), [Parte 2](https://www.javieraguilar.ai/es/blog/wheres-the-ball-2/) y [Parte 3](https://www.javieraguilar.ai/es/blog/wheres-the-ball-3/).*
