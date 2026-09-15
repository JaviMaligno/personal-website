---
title: "Contar aros no es freír calamares"
description: "Echas aros de calamar a la sartén y dos objetivos igual de razonables — que quepan cuantos más mejor, o que se dore la mayor superficie posible — resultan ser problemas distintos con respuestas distintas. Salvo que los tamaños cumplan una condición: entonces no solo coinciden, sino que dónde colocas cada aro deja de importar por completo."
pubDate: 2026-09-22
tags: ["Matemáticas", "Geometría", "Optimización", "Investigación"]
lang: es
translationKey: count-the-rings
heroImage: "/blog/count-the-rings.png"
repoUrl: https://github.com/JaviMaligno/calamares
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/2609.15554"
linkedinSummary: |
  Echas aros de calamar a la sartén y ya has tomado una decisión, te hayas dado cuenta o no.

  Puedes hacer que quepan cuantos más aros mejor. O puedes dorar la mayor cantidad posible de calamar, que es lo que de verdad se cocina. Suenan a la misma instrucción dicha dos veces. No lo son, y el caso más pequeño donde se separan es lo bastante pequeño como para dibujarlo.

  Sartén de radio 10, aros de grosor 1, tamaños 9,0, 4,2, 4,2 y 4,2. Coloca los tres pequeños y tienes tres aros y unas 69,7 unidades de superficie tocando la sartén. Usa el grande, con un pequeño dentro de su agujero, y tienes dos aros y unas 76,7. Más aros, menos cena. Lo interesante es que un aro es obstáculo y contenedor a la vez, así que la elección es real.

  Y luego la parte que me sorprendió. Si cada aro es mayor que todos los menores juntos, la discrepancia desaparece: una misma disposición maximiza a la vez todos los objetivos de una clase amplia. Y algo más fuerte: deja de importar dónde pones cada aro. Best fit, worst fit, aleatoria, adversaria — todas idénticas. La demostración no menciona nunca la forma de la sartén, así que vale igual para planchas rectangulares y para cascarones esféricos en tres dimensiones.

  Esa garantía es afilada de una forma que no esperaba: vale hasta tres aros y se rompe en cuatro. Y no hay regla más lista que lo arregle — existen dos instancias idénticas en toda magnitud que una regla pueda observar en el momento decisivo, y que exigen decisiones opuestas.

  La pregunta de debajo me la encuentro a menudo fuera de las matemáticas: ¿qué estoy maximizando de verdad, y el sustituto que optimizo es lo mismo que lo que quiero — o solo dentro de la región en la que resulta que estoy?
---

Echas un puñado de aros de calamar a la sartén y ya has tomado una decisión, te hayas dado cuenta o no.

Puedes colocarlos de forma que quepan todos los aros posibles. O puedes colocarlos de forma que haya la mayor cantidad posible de calamar tocando metal caliente, que es lo que de verdad se cocina. Suenan a la misma instrucción dicha dos veces. No lo son, y el hueco entre ambas da para demostrar teoremas.

Lo que lo convierte en un problema de verdad, y no en un juego de palabras, es que un aro tiene agujero. Un aro suficientemente pequeño cae dentro del agujero de uno mayor y se apoya en la sartén, tocando exactamente el mismo metal que habría tocado por su cuenta. Así que los aros no compiten por el espacio como monedas sobre una mesa: un aro grande es un obstáculo y un contenedor a la vez.

## La idealización, dicha por delante

Los aros de calamar de verdad hacen algo que el modelo prohíbe: se montan unos encima de otros. Un aro apoyado en parte sobre otro no desaparece — sigue dorando en todo lo que queda fuera del solape — y como los aros tienen grosor, esa postura no es un accidente de medida nula. Es lo que pasa de verdad en una sartén llena.

![Dos sartenes vistas desde arriba. A la izquierda, el modelo: dos aros uno junto a otro en tangencia exacta, lo más cerca que las reglas les permiten estar. A la derecha, esos mismos dos aros solapados, uno montado en parte sobre el otro, con las dos regiones de cruce marcadas en rojo — los únicos sitios donde se pierde el contacto con la sartén.](/blog/count-the-rings-fig-6-es.png)

El modelo de este artículo es el rígido: los hermanos de un contenedor tienen que ser empaquetables como bolas con interiores disjuntos, así que nada se monta sobre nada. Esa es una idealización real y conviene nombrarla antes de los teoremas y no después, porque todos los resultados de abajo son resultados sobre el modelo rígido.

La versión flexible es una dirección abierta con nombre propio, no un descuido. Sea $\delta$ la anchura de la rampa levantada que forma un aro doblado alrededor de cada solape. Entonces $\delta = 0$ — superficie de contacto igual a la corona menos la región solapada — define una relajación continua en la que las colocaciones parciales cambian contacto por número, y $\delta > 0$ penaliza los solapes con una banda muerta proporcional al perímetro del solape. Ninguna de las dos se resuelve aquí.

Quitado el calamar, el problema rígido es un pariente con sabor a selección del *Recursive Circle Packing Problem*, que introdujeron Pedroso, Cunha y Tavares (*International Transactions in Operational Research*, 2016) para modelar el telescopaje de tubos en contenedores de transporte, y que resolvieron exactamente Gleixner, Maher, Müller y Pedroso. Esa literatura es algorítmica: pregunta cómo empaquetar un conjunto fijo de aros en el menor número de contenedores, y sus métodos son heurísticas — procedimientos que proponen colocaciones sin garantizar que la colocación importara. Yo quería las preguntas estructurales. ¿Qué objetivo optimiza *demostrablemente* el algoritmo voraz obvio? ¿Cuándo es *demostrablemente* irrelevante dónde pongas cada aro? ¿Y qué condición sobre los tamaños decide la respuesta?

El preprint es [*Greedy Packing of Nested Rings*](https://arxiv.org/abs/2609.15554); el [código, las figuras y los certificados en Lean están abiertos](https://github.com/JaviMaligno/calamares). Esta es la versión legible de lo que hay dentro.

## Dos objetivos que suenan a uno solo

Fija un grosor $w$ — lo gruesa que es la pared del calamar — y di que un aro de radio exterior $r$ tiene un agujero de radio $r - w$. La superficie que toca la sartén es la corona:

$$
a(r) = \pi\left(r^2 - \max(0,\ r-w)^2\right)
$$

que para aros finos se parece mucho a $2\pi w r$. Así que *dorar* — superficie total de contacto — se comporta casi como la suma de los radios, menos una penalización fija $\pi w^2$ por cada aro que uses. *Contar* es simplemente el número de aros.

Esa penalización por aro es la semilla de toda la discrepancia. Añadir un aro siempre suma al recuento. No siempre suma bastante superficie como para compensar el sitio que ocupa, porque ese sitio podría haber ido a algo más grande.

Diremos que los dos objetivos **divergen** en una instancia cuando la disposición óptima en área usa estrictamente menos aros que la óptima en número. Resulta que hace falta una cantidad sorprendente de estructura para que eso pueda ocurrir siquiera.

Con dos aros, nunca. Si caben juntos, cógelos: el área crece estrictamente al añadir un aro, así que el conjunto completo gana en las dos cuentas. Si no caben juntos, toda disposición factible tiene como mucho un aro, y el óptimo de área ya alcanza ese número. Dos aros no pueden discrepar consigo mismos.

## Tres aros pueden discrepar, por el motivo equivocado

Con tres puede pasar, pero solo de forma degenerada. Toma una sartén de radio $R = 10$ con aros muy gruesos, $w = 9/2 = 4{,}5$, y radios

$$
\left\{8,\ \tfrac{101}{20},\ \tfrac{99}{20}\right\} = \{8,\ 5{,}05,\ 4{,}95\}
$$

Los dos pequeños son exactamente diametrales — $5{,}05 + 4{,}95 = 10$ —, así que caben uno al lado del otro cruzando la sartén y ya no cabe nada más. El agujero del grande tiene radio $8 - 4{,}5 = 3{,}5$, demasiado pequeño para cualquiera de ellos, así que no anida nada. Y las superficies comparan:

$$
a(8) = \tfrac{207}{4}\pi \;>\; \tfrac{198}{4}\pi = a(5{,}05) + a(4{,}95)
$$

![Dos sartenes de radio 10 con aros de grosor 4,5. A la izquierda, un único aro de radio 8, cuya superficie de contacto es 207π/4, unas 162,6 unidades. A la derecha, dos aros de radios 5,05 y 4,95 tocándose exactamente entre sí y con la pared de la sartén: dos aros, pero solo 198π/4 de superficie, unas 155,5.](/blog/count-the-rings-fig-0-es.png)

El aro grande solo dora más que los dos pequeños juntos: el número dice dos, el área dice uno. Pero fíjate en el motivo. Los aros son tan gruesos que ningún agujero puede alojar nada, y el problema ha degenerado silenciosamente en empaquetamiento de círculos. El anidamiento — lo que hace que esto sea calamar y no monedas — está apagado.

## La discrepancia más pequeña que va de verdad sobre aros

Baja otra vez el grosor para que el anidamiento vuelva a estar vivo y la discrepancia casi desaparece. Casi. La instancia más pequeña en la que sobrevive *con los agujeros trabajando* necesita cuatro aros: una sartén de radio $10$, grosor $1$, y radios $\{9{,}0;\ 4{,}2;\ 4{,}2;\ 4{,}2\}$.

Juégala de las dos maneras. Si quieres aros en la sartén, coge los tres de 4,2: caben uno al lado del otro, $N = 3$, y doran unos $69{,}7$. Si quieres calamar hecho, coge el de 9,0 y deja caer un 4,2 en su agujero: solo $N = 2$, pero unos $76{,}7$ de superficie de contacto.

![La instancia mínima de divergencia: una sartén de radio 10 con aros de grosor 1. A la izquierda, el óptimo de área — el aro de radio 9 con un aro de 4,2 anidado en su agujero, dos aros y unas 76,7 unidades de superficie de contacto. A la derecha, el óptimo de número — tres aros de 4,2 sueltos uno junto a otro en la sartén, tres aros pero solo unas 69,7 unidades de superficie.](/blog/count-the-rings-fig-1-es.png)

Tres aros o más cena. Las dos cosas no.

Merece la pena nombrar el mecanismo, porque es estrecho. Necesita aros pequeños que quepan $k$ veces en la sartén pero como mucho $k-2$ veces en el agujero del grande. Si caben $k-1$ veces en el agujero, los dos objetivos empatan y no hay nada que discutir. Ese desfase de uno es toda la divergencia en el régimen de anidamiento, y por eso la instancia mínima tiene cuatro aros y no tres.

## Dónde vive la discrepancia

Una vez sabes que existe, puedes cartografiarla. Fija el grosor en $1$ y la sartén en radio $10$, toma la familia "un aro grande de radio $b$ más tantos aros pequeños iguales de radio $s$ como quieras", y barre.

![Diagrama de fases de la banda de divergencia para un aro grande más aros pequeños iguales de radio s, con grosor 1 en una sartén de radio 10. La banda forma una escalera: cada escalón lo fija el umbral óptimo demostrado para empaquetar n círculos iguales en un disco, y el borde superior de la banda es exactamente el umbral de tres círculos, 0,4641 veces el radio de la sartén. El ejemplo trabajado, con b = 9,0 y s = 4,2, aparece marcado con una estrella dentro de la banda.](/blog/count-the-rings-fig-2-es.png)

La región de divergencia es una escalera, y los escalones no son arbitrarios: cada uno se apoya en un umbral óptimo demostrado para empaquetar $n$ círculos iguales en un disco, resultados que se remontan a Pirl y Melissen. El borde superior de la banda es exactamente el umbral de tres círculos, $0{,}4641\,R$. Por encima de ahí, los aros pequeños son ya lo bastante grandes como para que no quepan tres, y la aritmética deja de funcionar.

Una nota honesta, en la misma frase que la afirmación: para la familia de aros gruesos de la sección anterior, el inicio de la divergencia de tres aros está cerca de $w/R \approx 0{,}26$. Ese número está **barrido, no demostrado**. Lo muestreé; no lo establecí. El paper lo dice justo ahí y no en una nota al pie, porque "barrí una malla y aquí es donde cambia" y "he demostrado que aquí es donde cambia" no son la misma moneda, y un lector que no pueda distinguirlas se apoyará en la equivocada.

## Una condición, y el problema deja de ser interesante

Ahora la otra mitad, que me sorprendió más que la divergencia.

Llamemos **superincrecientes** a los radios cuando cada aro es mayor que todos los menores juntos: $r_i > \sum_{j>i} r_j$ para todo $i$. Es una condición fuerte — los tamaños tienen que caer deprisa, cada uno dominando toda la cola — pero no es exótica. Es la misma condición que hace funcionar al voraz en los sistemas monetarios, y el antepasado unidimensional de este resultado es un teorema de 1987 de Coffman, Garey y Johnson: para *bin packing* con tamaños divisibles, First Fit Decreasing es óptimo.

Con radios superincrecientes, el voraz descendente — coge el aro más grande, colócalo, sigue — produce el conjunto factible **lexicográficamente máximo**. Y eso tiene una consecuencia mayor de lo que parece: ser lex-máximo significa que maximiza simultáneamente

$$
\sum_{i \in S} v(r_i)
$$

para *toda* $v$ positiva, estrictamente creciente y superaditiva. La superficie de contacto es una de esas $v$. También lo son la suma de radios y la suma de perímetros. Todas a la vez, con la misma disposición. En este régimen, la discrepancia que he dedicado media artículo a construir simplemente desaparece.

El número en sí *no* se salva, y la razón es precisa: la cardinalidad es $v \equiv 1$, que no es superaditiva, así que el argumento de dominancia no le aplica en absoluto.

![Una sartén de radio 10 con aros de grosor 4,8 y radios superincrecientes 9,95, 5,0, 4,3 y 0,6. A la izquierda, lo que hace el voraz: el 9,95 con el 5,0 anidado en su agujero, dos aros, que es la mejor área posible. A la derecha, tres aros que sí caben — el 5,0, el 4,3 y el 0,6 en fila cruzando la sartén — mostrando que el voraz pierde en número aunque los radios sean superincrecientes.](/blog/count-the-rings-fig-5-es.png)

El contraejemplo es una sartén de radio $10$, grosor $4{,}8$, radios $\{9{,}95;\ 5{,}0;\ 4{,}3;\ 0{,}6\}$. El voraz coge $\{9{,}95;\ 5{,}0\}$: dos aros, área óptima, y ningún paso ofrece siquiera elección de contenedor, así que todas las reglas de colocación coinciden. Mientras tanto $\{5{,}0;\ 4{,}3;\ 0{,}6\}$ se empaqueta en fila en la sartén y da tres. La frontera es exactamente la superaditividad, y la cardinalidad cae del lado malo.

## Y entonces deja de importar dónde pones las cosas

Esta es la parte que no esperaba cuando empecé.

Bajo la misma condición no tienes *un* voraz óptimo. Todo voraz descendente es óptimo, con una regla **arbitraria** para elegir en qué contenedor dejas caer cada aro. Best fit — el contenedor más justo que lo admita. Worst fit — el más holgado. Aleatoria. Adversaria. Todas colocan exactamente el mismo conjunto lex-máximo.

La intuición que conviene quedarse no es "el algoritmo es listo". Es que con radios superincrecientes la decisión que te angustia no tiene consecuencia aguas abajo: hagas lo que hagas con el aro actual, los aros que quedan por venir son, todos juntos, más pequeños que él, y el argumento de intercambio siempre puede recolocarlos alrededor de tu elección.

Y como ese argumento solo mira dentro de la bola que deja vacante un aro movido, nunca menciona qué forma tiene la sartén. El teorema está enunciado y demostrado para un contenedor compacto arbitrario $K \subset \mathbb{R}^d$, leyendo los aros como cascarones esféricos. Una sartén redonda, una plancha rectangular, tubos y cascarones esféricos anidados en tres dimensiones — el escenario original de los contenedores de transporte — quedan cubiertos literalmente, no por extensión. No conozco ninguna garantía comparable de independencia de la colocación en la literatura de empaquetamiento de círculos.

La corroboración computacional es del tipo que me gusta, porque es un intento genuino de romper la afirmación: 100 instancias superincrecientes aleatorias, ejecutadas con best fit, worst fit y colocación aleatoria. Las tres produjeron resultados óptimos — y por tanto idénticos — sin una sola excepción.

## Tres aros, y luego cuatro

Un teorema vale lo que valga su filo, así que: ¿cuánto de esto sobrevive sin la condición?

Con radios *arbitrarios* y sin ninguna hipótesis de superincrecencia, todo voraz descendente sobre **como mucho tres aros** sigue aterrizando en el conjunto lex-máximo. Tres aros no dan sitio suficiente para equivocarse.

Cuatro sí.

![El contraejemplo de cuatro aros: una sartén de radio 15 con aros de grosor 0,3 y radios 10, 5, 4,9 y 4,8. A la derecha, worst fit coloca los cuatro — el 10 y el 5 exactamente tangentes en la sartén, el 4,9 y el 4,8 llenando exactamente el agujero del 10. A la izquierda, best fit anida el 5 dentro del 10, lo que empuja el 4,9 a la sartén y deja al 4,8 sin ningún sitio donde ir, marcado con una cruz roja fuera de la sartén.](/blog/count-the-rings-fig-3-es.png)

Sartén de radio $15$, grosor $0{,}3$, radios $\{10;\ 5;\ 4{,}9;\ 4{,}8\}$. Los cuatro aros caben, y la disposición que lo consigue está ajustada en los dos sitios a la vez: el 10 y el 5 son exactamente tangentes en la sartén ($10 + 5 = 15$), y el 4,9 y el 4,8 llenan exactamente el agujero del 10 ($4{,}9 + 4{,}8 = 9{,}7$, el radio del agujero).

Ahora ejecuta best fit. Ante el 5, prefiere el contenedor justo — el agujero del 10 — y lo anida. Esa única decisión de aspecto razonable empuja al 4,9 a la sartén, y una vez el 4,9 está en la sartén, el 4,8 ya no tiene dónde. Best fit consigue tres aros. Worst fit consigue cuatro.

Así que la irrelevancia de la colocación es afilada. Vale incondicionalmente en tres y falla en cuatro.

## Las gemelas

Podrías concluir, razonablemente, que la solución es una regla mejor. Que best fit es ingenuo y basta con escribir una más lista.

No se puede, y la razón es el resultado más afilado del paper.

Toma una sartén de radio $15$, un aro de 10 y otro de 5, grosor $w = 0{,}505$ — con lo que el agujero del 10 tiene radio $9{,}495$ — y estas dos instancias:

$$
I_1 = \{10;\ 5;\ 4{,}99;\ 4{,}50\}, \qquad I_2 = \{10;\ 5;\ 4{,}76;\ 4{,}74\}
$$

En $I_1$ los dos aros pequeños suman $9{,}49$, que cabe en el agujero. Así que el 5 pertenece a la sartén, y worst fit acierta mientras best fit falla. En $I_2$ suman $9{,}50$, que *no* cabe en el agujero. Así que el 5 pertenece al agujero, y ahora es best fit quien acierta y worst fit quien falla.

![Las instancias gemelas. Dos imágenes idénticas de una sartén de radio 15 con el aro de radio 10 ya colocado y el aro de radio 5 esperando en el borde a ser colocado. En la primera, los aros restantes suman 9,49, que cabe en el agujero de 9,495, así que el 5 va a la sartén. En la segunda suman 9,50, que no cabe, así que el 5 va al agujero. En el momento de decidir, las dos imágenes son la misma.](/blog/count-the-rings-fig-4-es.png)

Decisiones opuestas. Y aquí está el asunto: **en el momento de decidir, las dos instancias son indistinguibles.** Los contenedores son los mismos, sus capacidades son las mismas, los ocupantes son los mismos, el aro entrante es el mismo, $R$ y $w$ son los mismos. Toda magnitud que una regla de colocación pudiera mirar, leyendo el estado que tiene delante, es idéntica — y la jugada correcta es distinta.

La consecuencia no es "best fit es mala". Es que ninguna regla determinista que sea función del estado observable puede ser óptima en todas las instancias, y toda regla aleatorizada falla alguna instancia con probabilidad al menos $1/2$. La información necesaria para decidir no está en el estado. Está en los aros que todavía no has mirado.

## La constante que no era

Queda un hilo más, y termina en la equivocación más bonita que he tenido en bastante tiempo.

Si los radios superincrecientes te dan todo esto y violarlos te lo quita todo, debería haber un umbral en medio. Mide la violación por lo mal que el peor aro es batido por su propia cola:

$$
\rho = \max_i \frac{\sum_{j>i} r_j}{r_i}
$$

de modo que $\rho \le 1$ es exactamente la condición de superincrecencia. En la relajación *aditiva* — donde los hermanos son factibles justo cuando sus radios suman como mucho la capacidad, con la geometría retirada — el umbral es exactamente $\rho = 1$. Limpio, universal, y la razón por la que el modelo aditivo es el sitio adecuado para aislar la mitad combinatoria de la dificultad.

El modelo geométrico es donde se pone interesante. La familia rígida de contraejemplos de cuatro aros tiene un ínfimo, y ese ínfimo es exactamente la [constante de Tribonacci](https://oeis.org/A058265) $T \approx 1{,}83929$ — el análogo del número áureo para la recurrencia que suma los *tres* términos anteriores. Está demostrado, sin colar ninguna idealización de tangencia. Dada esa estructura de tres términos y un problema sobre aros dentro de aros dentro de aros, la conjetura natural se escribe sola: $T$ es el umbral global.

No lo es. Hay una familia explícita — sartén de radio $\varphi + 1$, radios $\{\varphi;\ 1;\ \varphi/2 + 2\varepsilon;\ \varphi/2 + \varepsilon\}$ — que rompe la irrelevancia de la colocación en $\rho = \varphi + 3\varepsilon$, para todo $\varepsilon > 0$ pequeño. Como $\varphi \approx 1{,}618 < 1{,}839 \approx T$, eso demuestra que el umbral geométrico $\tau$ cumple

$$
\tau \le \varphi < T
$$

y la conjetura de Tribonacci está muerta. El número áureo llega antes.

Lo que me encantaría contarte es que $\tau = \varphi$. No puedo, y quiero ser exacto sobre dónde está el hueco, porque es lo primero que uno da por hecho al ver la cota superior. La cota inferior correspondiente $\tau \ge \varphi$ está demostrada para perfiles de pares, y demostrada fuera de una región pesada explícita — pero no en general. Así que el valor áureo es teorema en una dirección y problema abierto en la otra, y Tribonacci queda degradado de "el umbral" a "el suelo exacto de la familia rígida anidada": sigue siendo una constante afilada, solo que no la que yo esperaba.

## Qué aspecto tiene el filo fuera de la sartén

Todo lo anterior sobre el *filo* — la transición en cuatro, las gemelas, el suelo, la familia áurea — era en origen una afirmación sobre una sartén redonda en el plano. La mitad positiva nunca necesitó la forma; la mitad afilada solo se había medido ahí. A cuál de las dos pertenece de verdad esa frontera es una pregunta que no sabía responder cuando salió el preprint, así que fui a hacérsela.

Lo que sigue está escrito y comprobado, pero **todavía no es público**: va en la segunda versión del preprint y no ha pasado por revisión adversaria independiente como sí pasaron los resultados de la v1. Léelo como un conjunto de afirmaciones con demostración adjunta, no como literatura asentada.

En bolas de cualquier dimensión no se mueve nada. La garantía de tres aros vale para un contenedor compacto arbitrario en cualquier dimensión — la demostración de la v1 se apoyaba en $r_1 + r_2 \le R$, pero lo que de verdad necesita es que encoger una bola manteniendo su centro preserve la factibilidad, cosa cierta para cualquier contenedor, cuadrado incluido. El fallo en cuatro también sobrevive, con la *misma* instancia $\{10;\ 5;\ 4{,}9;\ 4{,}8\}$, y también sobreviven las gemelas, y también el suelo de Tribonacci. La razón es un lema de reducción que merece enunciarse aparte: unas bolas de radios $a_1, \dots, a_k$ caben como hermanos dentro de una bola de radio $R$ en $\mathbb{R}^d$ si y solo si caben en $\mathbb{R}^{k-1}$. Las consultas de tres o menos hermanos tienen por tanto respuestas idénticas en toda dimensión $d \ge 2$, y todo resultado cuya demostración solo haga preguntas de ese tamaño viene incluido de regalo.

La primera consulta capaz de distinguir la dimensión 2 de la 3 necesita **cuatro** piezas, y hay una explícita: radios $\{441;\ 440;\ 439;\ 438\}/1000$ en una bola de radio $1$, que cabe en 3D con los centros en los cuatro puntos $(\pm a, \pm a, \pm a)$ de signo par, con $a = 8/25$ — los márgenes son racionales exactos — y no cabe en el plano.

Donde la constante cambia de verdad es en la sartén cuadrada. Ya hay un contraejemplo explícito de cuatro aros en un cuadrado con $\rho = 337/200 = 1{,}685$, con la exclusión geométrica del trío culpable comprobada por el kernel de Lean para todas las coordenadas en vez de muestreada; hay instancias gemelas en cuadrado, que matan también allí las reglas basadas en el estado; y la cota ha bajado a

$$
1 \le \tau_{\square} \le Y \approx 1{,}684487745872346
$$

donde $Y$ es la raíz positiva de $(17 + 10\sqrt2)Y^2 + (72 + 16\sqrt2)Y - (112 + 96\sqrt2) = 0$. Así que el disco y el cuadrado no comparten umbral: $\varphi \approx 1{,}618$ frente a algo cercano a $1{,}684$. La forma de la sartén cambia la constante, y lo que la cambia es la esquina.

Para bolas, la afirmación honesta es más débil de lo que me gustaría: $1 \le \tau_d \le \varphi$ para todo $d \ge 2$, y nada más. No se deduce que $\tau_d = \tau_2$, ni que $\tau_d = \varphi$ — los contraejemplos con cuatro o más hermanos no tienen por qué reducirse a un plano.

## Qué me llevo de esto

Dos cosas, y ninguna va de calamares.

La primera es que "¿qué estoy maximizando de verdad?" no es una pregunta de calentamiento filosófico. Es la pregunta que decide la respuesta. Contar y dorar parecen intercambiables hasta que los escribes, y entonces se separan en una región que puedes dibujar. Cuando un sistema optimiza el sustituto que le diste en vez de lo que querías, el fallo muchas veces no es que el optimizador sea malo: es que le entregaste la $v$ equivocada, y las dos solo coinciden fuera de la banda en la que resulta que estás.

La segunda es más alegre. Existen regímenes donde la parte difícil se evapora: donde todos los objetivos de una clase amplia coinciden, donde el algoritmo obvio es demostrablemente correcto, y donde la decisión en la que habrías invertido tu tiempo no tiene ninguna consecuencia. Saber si estás dentro de uno de ellos vale más que cualquier cantidad de ingenio gastado en la decisión. Aquí el test cabe en una línea — ¿es cada aro mayor que la suma de los demás? — y el premio por pasarlo es que puedes dejar de pensar.

Esto queda muy lejos del álgebra a la que dediqué [mi doctorado](/es/publications), y empezó, de verdad, en una sartén. El [preprint](https://arxiv.org/abs/2609.15554) tiene las demostraciones; el [repositorio](https://github.com/JaviMaligno/calamares) tiene el código, las figuras y los certificados en Lean de las identidades exactas.
