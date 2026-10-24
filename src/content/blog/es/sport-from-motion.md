---
title: "¿Qué deporte es? Reconocer un deporte solo por cómo se mueven los jugadores"
description: "Quité el campo, el balón y las camisetas y dejé solo puntos que se mueven. Un clasificador pequeño reconoce el deporte el 83 % de las veces; de cinco modelos frontera, solo uno demuestra que usa el orden de los instantes."
pubDate: 2026-10-24
tags: ["IA", "Visión", "Deporte", "Evaluación", "Claude"]
lang: es
translationKey: sport-from-motion
heroImage: "/blog/sport-from-motion.png"
repoUrl: "https://github.com/JaviMaligno/sport-from-motion"
linkedinImage: "/blog/sport-from-motion-linkedin-es.png"
---

<style>
.sfm-fig{margin:2rem 0;padding:1rem;background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:8px}
.sfm-fig svg{width:100%;height:auto;display:block}
.sfm-fig img{width:100%;height:auto;display:block;margin:0 !important;border-radius:4px}
.sfm-fig figcaption{color:#94a3b8;font-size:.9rem;margin-top:.75rem;line-height:1.5}
.sfm-fig .t{fill:#e2e8f0;font:600 13px ui-sans-serif,system-ui,sans-serif}
.sfm-fig .s{fill:#94a3b8;font:11px ui-sans-serif,system-ui,sans-serif}
.sfm-fig .box{fill:#20202c;stroke:rgba(255,255,255,0.12)}
.sfm-fig .dot{fill:#5eead4}
.sfm-fig .dim{fill:#64748b}
.sfm-fig .arw{stroke:#fbbf24;stroke-width:1.5;fill:none}
.sfm-fig .trk{stroke:#5eead4;stroke-width:1.6;fill:none}
</style>

Cuando vemos deporte, hay algo que hacemos sin pensar: reconocemos lo que estamos viendo antes de saber explicar por qué. Me di cuenta viendo un vídeo en el que apenas se distinguía el campo. Aun así, supe enseguida que era rugby y no fútbol. Lo que lo delataba no era el escenario, sino **cómo se movían los jugadores**.

Me quedé con la pregunta de si eso se puede aislar. Si quito todo lo demás (el campo, el balón, los colores, las camisetas) y dejo a los jugadores convertidos en puntos, ¿sigue ahí el deporte? ¿Y lo ve un modelo?

Para probarlo preparé imágenes como esta, que es exactamente lo que recibieron los modelos:

![Ocho instantes de una misma jugada: diez puntos grises sobre fondo blanco, sin campo ni balón](/blog/sport-from-motion-quiz.png)

Ocho instantes de una jugada, separados unos 0,5 segundos. Diez puntos grises, uno por jugador, vistos desde arriba. Nada más: ni campo, ni balón, ni colores, ni escala. ¿Qué deporte es? Al final lo digo, y también qué contestaron los modelos.

La pregunta es hermana de la de [*¿Dónde está el balón?*](/es/blog/wheres-the-ball), donde escondía el balón y pedía encontrarlo mirando a los jugadores. Aquí escondo **todo** salvo los jugadores y pregunto por el juego entero: **¿basta el movimiento para reconocer un deporte?**

## Puntos que se mueven

La representación viene de un experimento clásico de percepción: los *point-light displays* de [Johansson (1973)](https://en.wikipedia.org/wiki/Biological_motion), en los que una persona con unas pocas luces en las articulaciones, grabada a oscuras, se reconoce al instante como alguien que anda o que baila. Aquí cada punto es un jugador entero, y lo que hay que reconocer es el deporte.

Usé datos reales de *tracking* de cuatro deportes:

- **Fútbol americano**: [NFL Big Data Bowl 2023](https://www.kaggle.com/competitions/nfl-big-data-bowl-2023).
- **Baloncesto**: NBA SportVU 2015-16, 31 partidos.
- **Balonmano**: [EIGD-H](https://data.uni-hannover.de/dataset/eigd) (Bundesliga, sensores Kinexon) y [TeamTrack](https://github.com/AtomScott/TeamTrack).
- **Fútbol**: [SkillCorner](https://github.com/SkillCorner/opendata), [Metrica](https://github.com/metrica-sports/sample-data) y TeamTrack.

El rugby, que era la pregunta original, se queda fuera: no hay datos públicos de *tracking* de rugby con los que hacer esto bien.

Cada clip son 4 segundos, 10 jugadores escogidos al azar (el número de jugadores delataría el deporte), girados y reescalados al azar para que el tamaño del campo tampoco diga nada. A los modelos les di 400 clips, 100 por deporte, de 151 partidos distintos.

Lo interesante no es solo si aciertan, sino **qué parte de la señal usan**. Por eso cada clip se presenta en varias condiciones, siempre con los mismos clips:

<figure class="sfm-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Cinco condiciones del mismo clip: ocho instantes en orden; los mismos ocho desordenados; un solo instante; cada jugador en su casilla, lo que borra la forma del equipo; y cada jugador además girado, lo que borra también la dirección compartida.">
<g transform="translate(6,10)">
<rect class="box" width="110" height="150" rx="6"/>
<circle class="dot" cx="25" cy="40" r="3"/><circle class="dot" cx="45" cy="48" r="3"/><circle class="dot" cx="70" cy="42" r="3"/><circle class="dot" cx="90" cy="55" r="3"/>
<circle class="dot" cx="30" cy="95" r="3"/><circle class="dot" cx="52" cy="102" r="3"/><circle class="dot" cx="76" cy="96" r="3"/><circle class="dot" cx="95" cy="110" r="3"/>
<path class="arw" d="M20 70 H95 M89 66 L95 70 L89 74"/>
<text class="s" x="55" y="135" text-anchor="middle">1 → 8</text>
<text class="t" x="55" y="178" text-anchor="middle">Movimiento</text>
<text class="s" x="55" y="195" text-anchor="middle">8 instantes</text><text class="s" x="55" y="209" text-anchor="middle">en orden</text>
</g>
<g transform="translate(125,10)">
<rect class="box" width="110" height="150" rx="6"/>
<circle class="dot" cx="25" cy="40" r="3"/><circle class="dot" cx="45" cy="48" r="3"/><circle class="dot" cx="70" cy="42" r="3"/><circle class="dot" cx="90" cy="55" r="3"/>
<circle class="dot" cx="30" cy="95" r="3"/><circle class="dot" cx="52" cy="102" r="3"/><circle class="dot" cx="76" cy="96" r="3"/><circle class="dot" cx="95" cy="110" r="3"/>
<text class="s" x="55" y="135" text-anchor="middle">5, 2, 8, 1…</text>
<text class="t" x="55" y="178" text-anchor="middle">Desordenado</text>
<text class="s" x="55" y="195" text-anchor="middle">los mismos 8,</text><text class="s" x="55" y="209" text-anchor="middle">barajados</text>
</g>
<g transform="translate(244,10)">
<rect class="box" width="110" height="150" rx="6"/>
<circle class="dot" cx="35" cy="60" r="3"/><circle class="dot" cx="55" cy="72" r="3"/><circle class="dot" cx="75" cy="58" r="3"/><circle class="dot" cx="48" cy="92" r="3"/><circle class="dot" cx="80" cy="95" r="3"/>
<text class="s" x="55" y="135" text-anchor="middle">1</text>
<text class="t" x="55" y="178" text-anchor="middle">Formación</text>
<text class="s" x="55" y="195" text-anchor="middle">un solo</text><text class="s" x="55" y="209" text-anchor="middle">instante</text>
</g>
<g transform="translate(363,10)">
<rect class="box" width="110" height="150" rx="6"/>
<path class="trk" d="M18 30 q10 -6 20 2"/><path class="trk" d="M62 32 q8 8 22 2"/>
<path class="trk" d="M18 70 q12 4 20 -4"/><path class="trk" d="M62 72 q10 -8 22 -2"/>
<path class="trk" d="M18 108 q10 -4 20 4"/><path class="trk" d="M62 110 q8 6 22 -4"/>
<text class="t" x="55" y="178" text-anchor="middle">Cinemática</text>
<text class="s" x="55" y="195" text-anchor="middle">cada jugador en</text><text class="s" x="55" y="209" text-anchor="middle">su casilla: sin forma</text>
</g>
<g transform="translate(482,10)">
<rect class="box" width="110" height="150" rx="6"/>
<path class="trk" d="M18 32 q2 -10 16 -6"/><path class="trk" d="M84 26 q-10 8 -20 6"/>
<path class="trk" d="M26 64 q10 10 12 0"/><path class="trk" d="M66 78 q10 -10 20 -2"/>
<path class="trk" d="M34 116 q-10 -4 -14 -12"/><path class="trk" d="M62 104 q8 10 22 8"/>
<text class="t" x="55" y="178" text-anchor="middle">Cinemática sola</text>
<text class="s" x="55" y="195" text-anchor="middle">y cada uno girado:</text><text class="s" x="55" y="209" text-anchor="middle">sin dirección común</text>
</g>
<text class="s" x="300" y="242" text-anchor="middle">Mismos clips en todas las condiciones: cada diferencia se mide clip a clip</text>
</svg>
<figcaption>Si un modelo acierta igual con los instantes desordenados que en orden, no está leyendo movimiento: está leyendo formas sueltas. Esa comparación es la que decide todo lo demás.</figcaption>
</figure>

## Primero, comprobar que la señal existe

Antes de preguntar a nadie hacía falta saber si la pregunta tiene respuesta. Entrené dos especialistas pequeños, con validación cruzada por partido para que no pudieran reconocer el partido en vez del deporte: [MiniRocket](https://arxiv.org/abs/2012.08791), que es básicamente miles de filtros aleatorios más una regresión, y un [DeepSets](https://arxiv.org/abs/1703.06114) sobre la trayectoria de cada jugador. Minutos de CPU en un portátil.

Sobre los mismos 400 clips que verían los modelos, **MiniRocket acierta el 83 % y DeepSets el 80 %**, con un azar del 25 %. Y el movimiento es lo que cuenta: si se desordenan los instantes, MiniRocket pierde 12 puntos, y con un solo instante DeepSets baja al 54 %. La información está en cómo se mueven los jugadores, y un modelo muy pequeño la encuentra.

Es el mismo patrón que en la [Parte 2 de *¿Dónde está el balón?*](/es/blog/wheres-the-ball-2): la señal está, y la pregunta interesante es quién la ve.

## Lo difícil fue quitar los atajos

Ese 83 % no salió a la primera, y casi todo el trabajo del experimento fue asegurarse de que no mentía. Un clasificador entrenado aprende cualquier cosa que separe las clases, y en datos de *tracking* hay muchas cosas que separan deportes sin ser el deporte:

- **El número de jugadores.** Baloncesto tiene 10, fútbol 22. Por eso todos los clips tienen exactamente 10, elegidos al azar.
- **El tamaño del campo.** Por eso todo se reescala. Y resultó que quedarse con los 10 jugadores *más centrales* también era un atajo: en fútbol y balonmano ese grupo compacto se parece a una pista de baloncesto. Con 10 al azar, los especialistas suben 7 puntos.
- **El sistema de captura.** Este fue el más instructivo.

<figure class="sfm-fig">
<img src="/blog/sport-from-motion-jitter-es.png" alt="Entrenado con Metrica, SkillCorner y SportVU, MiniRocket acierta el 97 % en esas fuentes pero solo el 17 % en TeamTrack, que no había visto; suavizando igual todas las fuentes, sube al 89 %." aria-label="Entrenado con Metrica, SkillCorner y SportVU, MiniRocket acierta el 97 % en esas fuentes pero solo el 17 % en TeamTrack, que no había visto; suavizando igual todas las fuentes, sube al 89 %." />
<figcaption>Entrenado con tres fuentes y probado en una cuarta que no ha visto, el clasificador se hunde por debajo del azar. No había aprendido a distinguir fútbol de baloncesto: había aprendido a distinguir cámaras.</figcaption>
</figure>

TeamTrack graba con una cámara ojo de pez, y en un campo de fútbol grande sus posiciones tiemblan: unas siete veces más aceleración que el mismo fútbol medido por otros sistemas. Un clasificador que no ha visto TeamTrack lee ese temblor como el para-y-arranca del baloncesto y clasifica casi todo su fútbol como baloncesto. Suavizar todas las fuentes por igual lo arregla, y en el conjunto final llega al 95 % sobre la fuente que no ha visto.

Hubo más, todos del mismo tipo:

- Las jugadas de la NFL empezaban justo antes del *snap*, así que todos los clips eran «quietos y luego todos a la vez». Ahora cada clip empieza en un momento aleatorio de la jugada, al menos un segundo después del *snap*.
- TeamTrack marca los jugadores que no detecta con la coordenada (0, 0), que sin filtrar aparece como un punto quieto en una esquina.
- SportVU a veces registra al mismo jugador con dos identificadores, y el modelo veía 9 puntos en vez de 10.
- Las dos partes de un mismo partido de balonmano contaban como partidos distintos en la validación.

Ninguno de estos atajos es exótico. Son lo que pasa cuando se mezclan datos de seis fuentes con sistemas de captura distintos, y ninguno aparece si solo se mira el número final.

## Los modelos frontera

Con los datos limpios, preparé una corrida con cinco modelos frontera: **GPT-5.6 Sol, GPT-5.6 Terra, Claude Opus 5.5, Claude Sonnet 5 y Gemini 3.1 Pro**. Añadí también [Jev](/es/blog/jev-after-the-hype), un modelo de decisión tipada que solo lee texto y devuelve directamente una probabilidad por opción. Antes de ver una sola respuesta dejé escrito un [pre-registro](https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/preregistration.md): las hipótesis, los cuatro contrastes principales por modelo, la corrección por comparaciones múltiples y la regla exacta para decir que un modelo «lee el movimiento». Con 20 contrastes y datos de este tipo, sin reglas fijadas de antemano es muy fácil encontrar algo.

<figure class="sfm-fig">
<img src="/blog/sport-from-motion-accuracy-es.png" alt="Exactitud con 8 instantes en orden: los modelos frontera quedan entre 0,26 y 0,47 una vez corregido su sesgo de respuesta; MiniRocket llega a 0,83 y DeepSets a 0,80." aria-label="Exactitud con 8 instantes en orden: los modelos frontera quedan entre 0,26 y 0,47 una vez corregido su sesgo de respuesta; MiniRocket llega a 0,83 y DeepSets a 0,80." />
<figcaption>El mejor modelo frontera acierta el 47 %; los especialistas, el 80-83 %. Los círculos huecos son la exactitud bruta; los llenos, la exactitud corregida por el deporte favorito de cada modelo.</figcaption>
</figure>

Lo primero que salta es que los modelos tienen un **deporte favorito** al que recurren cuando dudan. GPT-5.6 Sol contesta fútbol americano en el 62 % de los clips, Gemini en el 66 %, Sonnet contesta fútbol en el 64 %. Eso infla el acierto en su deporte favorito y lo hunde en los demás, así que además de la exactitud bruta calculé una **corregida por ese sesgo**, estimado siempre con partidos distintos al del clip. Con la corrección, Sol, Terra, Opus y Gemini quedan por encima del azar. Sonnet 5 no.

<figure class="sfm-fig">
<img src="/blog/sport-from-motion-recall-es.png" alt="Acierto por deporte: los modelos frontera reconocen bien el fútbol americano o el fútbol según su deporte favorito, pero ninguno pasa de 0,15 en balonmano; MiniRocket acierta entre 0,79 y 0,90 en los cuatro." aria-label="Acierto por deporte: los modelos frontera reconocen bien el fútbol americano o el fútbol según su deporte favorito, pero ninguno pasa de 0,15 en balonmano; MiniRocket acierta entre 0,79 y 0,90 en los cuatro." />
<figcaption>El balonmano no lo reconoce ningún modelo frontera (entre 0,04 y 0,15). El baloncesto y el balonmano acaban leídos como fútbol americano o como fútbol. MiniRocket los reconoce todos por igual.</figcaption>
</figure>

## ¿Importa el orden?

La pregunta que decide si un modelo *ve movimiento* es la de la figura de las condiciones: ¿acierta menos cuando se desordenan los instantes?

<figure class="sfm-fig">
<img src="/blog/sport-from-motion-order-es.png" alt="Puntos de exactitud que se pierden al desordenar los instantes, con intervalos de confianza: Claude Opus 5.5 pierde 0,10 [0,05; 0,16]; los otros cuatro modelos quedan en torno a cero; MiniRocket pierde 0,12. Con clips de 8 s sin fútbol americano, Opus y GPT-5.6 Sol pierden 0,08." aria-label="Puntos de exactitud que se pierden al desordenar los instantes, con intervalos de confianza: Claude Opus 5.5 pierde 0,10 [0,05; 0,16]; los otros cuatro modelos quedan en torno a cero; MiniRocket pierde 0,12. Con clips de 8 s sin fútbol americano, Opus y GPT-5.6 Sol pierden 0,08." />
<figcaption>Solo Claude Opus 5.5 pierde acierto de forma clara al desordenar los instantes (la única diferencia que sobrevive a la corrección por comparaciones múltiples). Los círculos huecos son una prueba exploratoria con clips de 8 segundos y sin fútbol americano.</figcaption>
</figure>

Con la regla fijada de antemano, **Claude Opus 5.5 es el único de los cinco que lee el orden temporal**: desordenar los instantes le quita 10 puntos, con un intervalo de 5 a 16, casi lo mismo que a MiniRocket. Se repite en las réplicas y, de forma exploratoria, con clips de 8 segundos.

Hay matices que importan:

- **El efecto de Opus se concentra en fútbol americano y baloncesto**, y es nulo en balonmano y fútbol. En fútbol americano parte de la señal puede ser la aceleración del arranque de la jugada, que sigue presente aunque los clips empiecen después del *snap*. La prueba de 8 segundos no tiene fútbol americano y el efecto sigue ahí (+0,08), lo que apunta a que no es solo eso.
- **En los otros cuatro no hay evidencia**, que no es lo mismo que evidencia de que no lo lean. Por los intervalos, el orden les aporta como mucho de 3 a 6 puntos. Y hay indicios exploratorios: GPT-5.6 Sol pierde 8 puntos con clips de 8 segundos, y Sol y Gemini leen el orden en el fútbol americano, compensado en el total por otros deportes.
- **Algo sacan de las formas.** Sol, Terra y Gemini aciertan por encima del azar incluso con los instantes desordenados, y Sol incluso con un solo instante. Ven algo de la disposición de los jugadores, pero no hay evidencia de que les sirva cómo cambia.

## Lo que no ayudó

Probé también tres cosas que parecían prometedoras, y ninguna movió los resultados de forma clara:

- **Coordenadas en texto en lugar de imágenes.** Ni empeora ni mejora de forma consistente. Gemini acierta algo más con texto, sin llegar a ser significativo. Jev, que solo puede leer texto, queda en el azar: contesta «fútbol» en el 90-100 % de los clips. Sus probabilidades parecen moverse algo con el orden (corregido su sesgo, 0,34 con los instantes en orden frente a 0,21-0,23 desordenados), pero casi nunca llegan a cambiar su respuesta, y no es una diferencia que pusiera a prueba.
- **Decirle qué mirar.** Un prompt que describe cómo se mueve cada deporte, sin números, sube el acierto entre 0 y 3 puntos. Nada que sobreviva a la corrección.
- **Estelas y vídeo.** Dibujar la estela de cada jugador no ayuda a nadie, y a Sol le quita 7 puntos. Con vídeo, Gemini acierta unos 7 puntos más que con la hoja, pero es exploratorio y no alcanza para afirmarlo.

## Qué me llevo

La información para reconocer un deporte está en el movimiento de los jugadores, y un clasificador que cabe en un portátil la extrae el 83 % de las veces. Los modelos frontera, en esta tarea y con estas representaciones, se quedan entre el azar y el 47 %, y solo uno de los cinco demuestra que usa el orden de los instantes.

No saco de aquí que los otros «no vean el movimiento»: saco que no hay evidencia de que lo usen, y que si lo usan es poco. Tampoco que Opus lea el movimiento en general: lo hace sobre todo en dos deportes. Lo que sí me parece robusto es la distancia con los especialistas, y lo que costó llegar a un número en el que confiar. Cada atajo que quité habría contado una historia distinta.

Y la hoja del principio es **baloncesto**. Tres modelos contestaron fútbol americano (los diez puntos casi en línea recuerdan a una línea de *scrimmage*) y dos contestaron fútbol. Los tres especialistas, MiniRocket, DeepSets y el clasificador de estadísticas de movimiento, acertaron.

---

*Código, pre-registro y resultados completos en [github.com/JaviMaligno/sport-from-motion](https://github.com/JaviMaligno/sport-from-motion). El análisis sigue el [pre-registro](https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/preregistration.md), y los [resultados](https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/results-final.md) incluyen todo lo que no salió. Los datos no se redistribuyen; cada fuente tiene su licencia.*
