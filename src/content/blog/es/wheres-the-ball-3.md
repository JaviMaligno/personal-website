---
title: "¿Dónde está el balón? Parte 3 — al final era geometría (y el modelo no sabe cuándo se equivoca)"
description: "Abriendo la red diminuta que batió a los modelos frontera: diez números geométricos interpretables recuperan el 92% de lo que hace, la topología elegante no aporta nada, y el modelo resulta ser sobreconfiado justo en los casos que falla."
pubDate: 2026-07-29
tags: ["IA", "Visión por Computador", "Investigación"]
lang: es
translationKey: wheres-the-ball-3
heroImage: "/blog/wheres-the-ball-3.png"
linkedinImage: /blog/wtb3-geometry-recovers.png
repoUrl: https://github.com/JaviMaligno/wheres-the-ball
linkedinLinks:
  - label: "Parte 1 (el benchmark de VLMs)"
    url: https://www.javieraguilar.ai/es/blog/wheres-the-ball/
  - label: "Parte 2 (el modelo de 60 kB y el estudio de transferencia)"
    url: https://www.javieraguilar.ai/es/blog/wheres-the-ball-2/
---

La [Parte 2](https://www.javieraguilar.ai/es/blog/wheres-the-ball-2/) terminaba con una red pequeña —unos 60 kilobytes de pesos— resolviendo los casos del balón oculto que los modelos de visión-lenguaje frontera no podían. Leía las posiciones y velocidades de los jugadores y apuntaba, con precisión decente, a un balón que nunca se le había mostrado.

Lo cual es satisfactorio y un poco molesto, porque una red que funciona sigue siendo una caja negra. Te da una respuesta, no una explicación. Así que la pregunta que abre el último peldaño de esta escalera es: **¿qué está computando de verdad esa cajita?** ¿Hay algún patrón rico y profundo en cómo se colocan diez jugadores, o hace algo que un humano podría anotar en el reverso de un sobre?

Dediqué el Nivel 3 a intentar abrir la caja por tres vías. La versión corta: es sobre todo una única idea geométrica, la matemática sofisticada a la que recurrí no aportó nada, y cuando le pregunté al modelo cuán seguro estaba, resultó estar confiadamente equivocado en un sitio muy concreto.

## Al final era geometría

La prueba es simple. Si la caja negra computa algo interpretable, entonces un puñado de features geométricas escritas a mano —cantidades que un entrenador sabría nombrar— metidas en un árbol de gradient boosting normal debería reproducir casi toda su precisión. Si hace algo genuinamente profundo, no se acercarán.

Escribí unas diez: el centroide de los jugadores, el centroide ponderado por lo rápido que se mueve cada uno, la posición del más veloz, el grupo más denso, la dispersión de cada equipo, el punto medio de la pareja de rivales más cercana, un "punto de convergencia" donde se cruzan las rectas de movimiento de los jugadores. Diez números, un árbol, la misma partición train/test que el modelo profundo.

![La caja negra está (casi toda) leyendo geometría](/blog/wtb3-geometry-recovers.png)

La distancia entre un baseline de centroide ingenuo y la red profunda entrenada es la "habilidad" que la red aprendió. Diez features interpretables recuperan el **92%** de esa distancia en fútbol — y en baloncesto incluso *superan* a la red profunda (112%). La cajita negra, resulta, no esconde gran cosa. Casi todo lo que sabe se puede escribir.

### Un solo número hace casi todo el trabajo

Y casi todo *eso* es una única feature. Cuando mido cuánto aporta cada cantidad geométrica —barajándola y viendo subir el error— una domina al resto en un orden de magnitud:

![Una feature domina: hacia dónde va la masa que corre](/blog/wtb3-which-geometry.png)

El **centroide ponderado por velocidad** —la posición media de los jugadores, pero contando más los que se mueven rápido— sostiene la localización él solo. Todo lo demás es redondeo. Es el mismo hilo que atravesaba la Parte 2: la señal está en el *movimiento*, en hacia dónde va la masa que corre, no en la forma estática de la alineación.

Hay una pequeña ironía. La feature de la que más orgulloso estaba —el "punto de convergencia", un pulcro cruce por mínimos cuadrados de las rectas de movimiento de todos, lo que dibujarías en una pizarra táctica para decir *el balón está donde todos corren*— apenas mueve la aguja. La burda media ponderada de posiciones bate a la elegante construcción geométrica. No sería la última vez que este proyecto humillara a una idea bonita.

## Lo que esperaba que la topología aportara (y no aportó)

Si diez features simples ya recuperan casi todo, ¿queda *alguna* estructura que una descripción más rica pudiera capturar? El candidato natural es la topología —la forma del cloud de jugadores, sus agujeros y componentes conexas, formalizada como [homología persistente](https://es.wikipedia.org/wiki/Homolog%C3%ADa_persistente). Hay una intuición genuinamente atractiva detrás: un balón en juego abierto suele estar dentro de un *agujero* de la configuración —un anillo de jugadores rodeando espacio vacío— y la topología es justo la matemática de los agujeros.

Así que construí las features topológicas: los estadísticos de persistencia del cloud, el centro de su loop más persistente (vía el ciclo representativo — literalmente "dónde está el mayor agujero"), los dos mayores círculos vacíos de la triangulación de Delaunay ("dónde está el mayor hueco"). Fijé una regla antes de ejecutar nada, para mantenerme honesto: **la topología solo cuenta si bate a su contraparte geométrica.** Si no, es decoración.

![La homología persistente no aporta nada sobre la geometría](/blog/wtb3-topology-nothing.png)

No pasa la vara. Las features topológicas por sí solas quedan muy por detrás de la geometría (0.258 vs 0.111 en fútbol — apenas mejor que el baseline ingenuo). Y pegarlas a las features geométricas no cambia nada: geometría-más-topología iguala a la geometría sola, y cuando barajo todo el bloque topológico el error apenas se inmuta — el árbol simplemente lo ignora en cuanto tiene la geometría.

La intuición atractiva es sencillamente falsa. La posición del balón no es una propiedad de la *forma* del cloud de jugadores; es una propiedad de dónde está la masa y hacia dónde se mueve. La homología persistente describe la configuración maravillosamente a todas las escalas, y nada de esa descripción va del balón. Un resultado negativo limpio — y la regla pre-registrada es la única razón por la que puedo llamarlo limpio en vez de dejarlo caer discretamente.

## ¿Sabe el modelo cuándo se equivoca?

La última pregunta es la que más me interesa, porque no va de precisión sino de autoconocimiento. Una predicción de punto no puede decirte cuán segura está. Así que cambié la salida de un solo punto de la red por una cabeza de [densidad de mezcla](https://publications.aston.ac.uk/id/eprint/373/): en vez de una conjetura, predice una distribución de probabilidad completa sobre dónde podría estar el balón. Ahora puede decir "por aquí cerca, y estoy seguro" o "en toda esta región, y no lo estoy".

El primer hallazgo tranquiliza. La incertidumbre que declara *sí* sigue al error que comete — ordena las predicciones de la más segura a la menos, y el error real sube de forma monótona:

![Globalmente calibrado, pero con un punto ciego en los balones sueltos](/blog/wtb3-blind-spot.png)

Eso es el panel izquierdo: el modelo sabe cuándo no sabe. Débilmente (la correlación es un modesto +0.20), pero consistentemente.

El panel derecho es donde se pone interesante — y donde mi hipótesis murió, otra vez. Yo esperaba que el balón fuera *más difícil* de localizar cuando está enredado en un grupo de jugadores, y más fácil cuando está suelto en espacio abierto. Es al revés. El juego trenzado es el caso *fácil*: cuando los jugadores convergen sobre el balón, sus velocidades apuntan a él, y ese centroide ponderado por velocidad cae justo encima. Un balón suelto, con los jugadores a remolque, es de verdad más difícil — un 20% más de error.

Aquí está el punto ciego: en esos balones sueltos más difíciles, el modelo declara *menos* incertidumbre. Su error sube mientras su confianza sube. Está más seguro de sí mismo exactamente donde más se equivoca — y estos son los mismos balones descentrados y rápidos que hicieron fallar a los modelos frontera allá en la Parte 1. El modo de fallo es consistente por toda la escalera: a todo el mundo le cuesta el balón suelto, y el especialista ni siquiera sabe que le está costando.

¿Y qué pinta tiene el mapa del campo? Si dibujas el error mediano por zonas, el balón se determina mejor junto a las bandas y en el medio campo abierto, y peor en la congestión frente a ambas porterías — córners, centros y rechaces de área donde los jugadores se amontonan y el truco de la convergencia se rompe.

![Dónde es inferible el balón a partir de los jugadores](/blog/wtb3-inferability-map-pitch.png)

## Conclusiones

- **La caja negra estaba leyendo geometría.** Diez features interpretables recuperan el 92% de la red profunda en fútbol y la baten en baloncesto. Localizar el balón no es un patrón profundo — es sobre todo un número: el centroide ponderado por velocidad, "hacia dónde va la masa que corre".
- **La topología no aportó nada.** Homología persistente, círculos vacíos, centros de loop — la atractiva intuición del "balón en el agujero" — no baten a la geometría y se ignoran al añadirlos. La posición del balón no es una propiedad de la forma de la configuración. Una regla pre-registrada mantuvo honesto el resultado negativo.
- **El modelo está confiadamente equivocado en un sitio.** Está globalmente calibrado, pero es sobreconfiado en los balones sueltos en espacio abierto — justo los casos duros y descentrados que rompieron a los modelos frontera en la Parte 1. No sabe que no sabe, precisamente donde importa.
- **Mis mejores conjeturas no dejaron de perder contra las simples.** El elegante punto de convergencia perdió contra una media ponderada; la topología perdió contra diez features simples; la hipótesis de "las multitudes confunden" estaba del revés. A lo largo de tres partes, este proyecto hizo un pleno de cuatro sobre cuatro en "la primera versión de la historia era falsa" — que es justo la razón por la que escribo los controles antes que las conclusiones.

Tres peldaños después, la respuesta a la pregunta desde la grada es casi un anticlímax. Inferir un balón oculto a partir de los jugadores es real, es aprendible, y es *geometría* — el instinto de un entrenador para saber hacia dónde va la jugada, escrito como una media ponderada. Los modelos frontera tienen ese instinto de forma tenue y no saben ejecutarlo; una red de 60 kB lo tiene afilado. Y ninguno de los dos, resulta, sabe decirte cuándo el balón se ha escapado suelto al espacio y han perdido el hilo sin enterarse.

---

*Código, definiciones de features, controles y los experimentos de topología y densidad de mezcla en el repo [`wheres-the-ball`](https://github.com/JaviMaligno/wheres-the-ball). Tracking de fútbol de [Metrica Sports](https://github.com/metrica-sports/sample-data) y [SkillCorner](https://github.com/SkillCorner/opendata); baloncesto de los logs NBA SportVU 2015-16 ([mirror](https://github.com/linouk23/NBA-Player-Movements); sin licencia explícita — uso solo para investigación, sin redistribución). Homología persistente vía [ripser](https://github.com/scikit-tda/ripser.py). Antes: [Parte 1](https://www.javieraguilar.ai/es/blog/wheres-the-ball/) y [Parte 2](https://www.javieraguilar.ai/es/blog/wheres-the-ball-2/).*
