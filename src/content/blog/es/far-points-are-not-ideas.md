---
title: "Los huecos del mapa no son ideas"
description: "Un tuit proponía sacar ideas nuevas de los puntos vacíos de un espacio de embeddings. Lo probé con juegos de Steam, artículos de arXiv y patentes: ningún texto coherente llega a esos puntos, y lo que sale de ellos es un juego normal."
pubDate: 2026-11-02
tags: ["IA", "Embeddings", "LLMs", "Investigación", "Creatividad"]
lang: es
translationKey: far-points-are-not-ideas
heroImage: "/blog/far-points-are-not-ideas.png"
---
Hace poco [@syntheticbeef publicó en X](https://x.com/syntheticbeef/status/2112904858718367750) una receta para que la IA invente ideas de verdad nuevas. Embebes los juegos de Steam, eliges puntos del espacio que estén lejos de todos ellos, conviertes cada punto de vuelta en la descripción de un juego y ordenas el resultado por lo distinto que es de lo que ya existe. Si el punto está lejos de todo, la idea que sale de él debería ser nueva.

Mi objeción fue inmediata. En un espacio de mil dimensiones casi todo está lejos de todo, y casi todo ese espacio es ruido. Que un punto esté vacío no significa que ahí quepa una idea. Puede que ahí no quepa ningún texto con sentido.

Un amigo me respondió que la coherencia es una dimensión más, con sus propios óptimos locales, y que la difusión de imágenes lo demuestra: le pides un astronauta montando a caballo y te lo dibuja, aunque nunca haya visto uno. Le di la razón en que esos rincones raros y con sentido existen. Pero la difusión llega a ellos partiendo de conceptos que conoce («astronauta», «caballo») y combinándolos por similitud. El tuit hace lo contrario: busca la disimilitud, sin ningún concepto del que partir.

Era una discusión que se podía medir, así que la medí.

<style>
.lg-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.lg-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.lg-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Tres mapas

El mapa principal es el del tuit: los 71.939 juegos de Steam publicados antes de 2024, con su descripción, géneros y etiquetas. Guardé aparte los 41.000 publicados después, para comprobar al final si alguna idea se adelantaba a lo que salió más tarde.

Un catálogo de videojuegos es un espacio muy particular, y no quería que la conclusión dependiera de él. Así que repetí todo en otros dos catálogos que no se parecen en nada a Steam:

- **arXiv**: 72.000 artículos de informática anteriores a 2023, cada uno con su título y su resumen.
- **Patentes**: 71.521 solicitudes de patente presentadas en Estados Unidos entre 2012 y 2015.

Cada texto se convierte en un vector con Qwen3-Embedding-0.6B, un modelo abierto de embeddings. Para medir lo cerca que están dos textos uso el coseno entre sus vectores: 1 si apuntan en la misma dirección, 0 si no tienen nada que ver.

Una nota sobre el mapa de Steam. Dejé fuera los 3.717 juegos que Steam etiqueta como contenido sexual o desnudos, porque el filtro de contenido de Azure rechazaba las peticiones que los mostraban como ejemplo. Después comprobé que meterlos no cambia la geometría: el juego más cercano a los puntos lejanos sigue a la misma distancia y el centro del mapa apenas se mueve (coseno 0,9999 entre los dos centros). Eso sí, los juegos explícitos sin etiqueta siguieron dentro, y uno de ellos sale más abajo.

## Cómo se convierte un punto en un juego

Un punto del espacio no se puede leer directamente. Para «decodificarlo», un LLM escribe una ficha de juego en bucle. En cada ronda ve los 8 juegos reales más cercanos al punto y, después de escribir, solo recibe una nota: el coseno entre su ficha y el punto. Son cuatro rondas de tres candidatas, y me quedo con la mejor. En arXiv el LLM escribe un resumen de artículo, y en patentes, una solicitud.

<figure class="lg-fig">
<svg viewBox="0 0 600 190" role="img" aria-label="El bucle de decodificación: el punto objetivo da sus 8 vecinos más cercanos, el LLM escribe una ficha, se embebe, se mide su coseno con el punto y solo esa nota vuelve al LLM durante 4 rondas de 3 candidatas.">
<defs><marker id="lga1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
<g font-size="12" text-anchor="middle">
<rect x="15" y="40" width="100" height="56" rx="8" fill="#0f172a" stroke="#f59e0b"/><text x="65" y="64" fill="#fbbf24" font-weight="600">Punto t</text><text x="65" y="81" fill="#94a3b8" font-size="10.5">del espacio</text>
<rect x="135" y="40" width="100" height="56" rx="8" fill="#0f172a" stroke="rgba(255,255,255,0.18)"/><text x="185" y="64" fill="#e2e8f0">8 vecinos</text><text x="185" y="81" fill="#94a3b8" font-size="10.5">reales + su coseno</text>
<rect x="255" y="40" width="100" height="56" rx="8" fill="#0f172a" stroke="#2dd4bf"/><text x="305" y="64" fill="#5eead4" font-weight="600">LLM</text><text x="305" y="81" fill="#94a3b8" font-size="10.5">escribe una ficha</text>
<rect x="375" y="40" width="100" height="56" rx="8" fill="#0f172a" stroke="rgba(255,255,255,0.18)"/><text x="425" y="64" fill="#e2e8f0">Embedding</text><text x="425" y="81" fill="#94a3b8" font-size="10.5">Qwen3-0.6B</text>
<rect x="495" y="40" width="90" height="56" rx="8" fill="#0f172a" stroke="rgba(255,255,255,0.18)"/><text x="540" y="64" fill="#e2e8f0">cos(ficha, t)</text><text x="540" y="81" fill="#94a3b8" font-size="10.5">la nota</text>
</g>
<g stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#lga1)">
<path d="M115,68 L133,68"/><path d="M235,68 L253,68"/><path d="M355,68 L373,68"/><path d="M475,68 L493,68"/>
<path d="M540,96 L540,135 L305,135 L305,99"/>
</g>
<text x="422" y="153" fill="#94a3b8" font-size="11" text-anchor="middle">solo vuelve la nota · 4 rondas × 3 candidatas · se queda la mejor</text>
</svg>
<figcaption>El decodificador. El LLM nunca ve el punto, solo los juegos que lo rodean y una nota de lo cerca que ha quedado.</figcaption>
</figure>

Probé cinco tipos de punto. Cada tipo es lo que en un experimento se llama un brazo:

- **REAL**: el punto de un juego real que escondo del mapa. Es el control. Si el método no recupera un juego que existe, nada de lo demás significa algo.
- **INTERP**: el punto medio entre dos juegos muy distintos. Es la versión geométrica de «combina dos ideas lejanas».
- **GAP**: huecos internos, puntos que caen en la zona donde hay juegos pero donde no hay ninguno.
- **FAR**: la receta del tuit. De 20.000 direcciones al azar, las 50 más alejadas de cualquier juego.
- **PLAIN**: sin mapa. Solo le pido al modelo «inventa un juego nuevo, distinto de cualquiera que exista».

En Steam usé seis generadores, que son los modelos que escriben las fichas: Claude Opus, Sonnet y Haiku, gpt-6.1-sol, y gpt-6-luna por API y a través de Codex. En arXiv y patentes usé dos, luna vía Codex y Sonnet. Antes de puntuar, otro modelo reescribía cada ficha al mismo formato de 120 palabras, para que el estilo no delatara de dónde venía. Después cuatro modelos distintos las puntuaron a ciegas en coherencia, viabilidad, atractivo y novedad frente a los cinco textos existentes más parecidos. Entre las fichas a puntuar había también juegos reales posteriores a 2024, como referencia. Además, yo puntué 80 a mano.

## Qué sale de cada tipo de punto

**REAL funciona.** Cuando el punto es un juego escondido, el decodificador vuelve a su zona, con un coseno de alrededor de 0,7. Llega tan cerca como el juego existente más parecido, y a veces más. Con *Star Farmer: Warlock of the Universe* escondido, escribió *Voidbloom Run*, un juego de granjero espacial que cultiva semillas en planetas hostiles, a 0,87.

Y reconstruye lo que haya en el mapa, también lo que nadie querría. Uno de los juegos escondidos era *SEX with HITLER: WW2*, y entre los vecinos que vio el modelo estaban sus dos secuelas. Escribió *Hitler: No Future in Berlin*, una novela visual con disparos en la que el Führer, derrotado, intenta sobrevivir entre las ruinas de Berlín y conoce a «cinco heroínas adultas» (coseno 0,69). El método no tiene criterio, solo va adonde hay texto.

**INTERP da combinaciones literales.** Entre un juego de meditación en realidad virtual y uno de estrategia con demonios salió *Ashen Breath: Legions of the Void*, un RPG táctico de fantasía oscura «con un modo opcional de meditación en VR» (0,84). Es lo que se pidió, y se nota la costura.

**FAR no llega a ninguna parte.** La ficha aterriza a un coseno de entre 0,03 y 0,05 del punto, según el generador, es decir, prácticamente a cero. Y no es que el LLM lo haga mal: el juego existente más cercano a esos puntos está a 0,046. Lo que sale es un juego normal. Los vecinos de uno de los puntos eran *Challenge from the Black Cat*, un puzle japonés de hámsteres y *My Furry Stepmom*, y lo que salió fue *Pounce & Pop: Kitten's Block Quest*, una gatita que empuja bloques para volver a casa (0,069). De otro salió *The Museum of Unfinished Things*, un museo que se reordena solo por la noche (0,028). Son juegos razonables, incluso agradables, que podrían estar ya en Steam.

La geometría explica por qué. Los textos no se reparten por todo el espacio. Todos comparten una dirección común, así que ocupan un casquete estrecho de la esfera: dos juegos cualesquiera de Steam tienen un coseno de 0,41, mientras que dos direcciones al azar tienen 0 ± 0,03. Los puntos FAR son direcciones al azar elegidas por estar lejos de todo, así que caen fuera del casquete. En cambio, cualquier ficha que escriba el LLM, por rara que sea, cae dentro.

<figure class="lg-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Los textos ocupan un casquete estrecho de la esfera. Un hueco interno GAP queda dentro del casquete, entre juegos. Un punto FAR queda fuera, en el resto de la esfera, y la ficha que se escribe para él vuelve al casquete, junto a los vecinos que se le mostraron.">
<circle cx="210" cy="190" r="135" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1.4"/>
<path d="M97.8,115 A135,135 0 0,1 322.2,115 Z" fill="rgba(45,212,191,0.12)" stroke="#2dd4bf" stroke-width="1.2"/>
<g fill="#94a3b8"><circle cx="130" cy="108" r="3"/><circle cx="152" cy="100" r="3"/><circle cx="172" cy="90" r="3"/><circle cx="190" cy="104" r="3"/><circle cx="196" cy="74" r="3"/><circle cx="240" cy="72" r="3"/><circle cx="258" cy="92" r="3"/><circle cx="242" cy="106" r="3"/><circle cx="222" cy="64" r="3"/><circle cx="268" cy="108" r="3"/><circle cx="160" cy="80" r="3"/></g>
<g fill="#f8fafc"><circle cx="286" cy="100" r="3.6"/><circle cx="300" cy="108" r="3.6"/><circle cx="302" cy="96" r="3.6"/></g>
<circle cx="292" cy="90" r="5" fill="#2dd4bf"/>
<circle cx="216" cy="88" r="6" fill="none" stroke="#fbbf24" stroke-width="1.6"/>
<defs><marker id="lga2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
<path d="M302,282 C405,245 400,140 310,108" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#lga2)"/>
<path d="M297,286 l4,9 10,1 -7.5,6.5 2.5,10 -9,-5.5 -9,5.5 2.5,-10 -7.5,-6.5 10,-1z" fill="#f59e0b"/>
<line x1="216" y1="96" x2="216" y2="140" stroke="#fbbf24" stroke-width="1"/>
<line x1="392" y1="66" x2="298" y2="88" stroke="#5eead4" stroke-width="1"/>
<g font-size="12">
<text x="210" y="22" fill="#5eead4" text-anchor="middle" font-weight="600">el casquete donde viven los textos</text>
<text x="210" y="40" fill="#94a3b8" text-anchor="middle" font-size="10.5">dos juegos cualesquiera: cos 0,41 · dos direcciones al azar: 0 ± 0,03</text>
<text x="216" y="156" fill="#fbbf24" text-anchor="middle">hueco GAP</text>
<text x="216" y="171" fill="#94a3b8" text-anchor="middle" font-size="10.5">dentro, entre juegos</text>
<text x="210" y="240" fill="#64748b" text-anchor="middle" font-size="10.5">el resto de la esfera:</text>
<text x="210" y="254" fill="#64748b" text-anchor="middle" font-size="10.5">direcciones sin ningún texto</text>
<text x="398" y="62" fill="#5eead4">la ficha que se escribe</text>
<text x="398" y="78" fill="#94a3b8" font-size="10.5">vuelve al casquete, junto a</text>
<text x="398" y="92" fill="#94a3b8" font-size="10.5">los vecinos que vio (blancos)</text>
<text x="398" y="292" fill="#fbbf24">punto FAR</text>
<text x="398" y="308" fill="#94a3b8" font-size="10.5">el juego más cercano está</text>
<text x="398" y="322" fill="#94a3b8" font-size="10.5">a cos 0,046</text>
</g>
</svg>
<figcaption>Esquema, no a escala. Los huecos GAP están dentro de la región donde hay texto; los puntos FAR, fuera. Lo que se escribe para un punto FAR vuelve a caer dentro.</figcaption>
</figure>

En arXiv y en patentes pasa lo mismo. Antes de construir ningún punto de arXiv, calculé solo con las estadísticas del corpus a qué distancia quedaría el artículo más cercano a un punto lejano. Predije 0,062 y salió 0,058. En patentes salió 0,062. En los tres catálogos, lo que se escribe para un punto FAR aterriza a menos de 0,08.

## El texto va adonde están los vecinos

Al mirar dónde caían las fichas FAR vi algo más. Estaban mucho más cerca de los 8 vecinos que se le habían enseñado al LLM que del propio punto: en Steam, a un coseno de 0,63–0,72 de su centroide, frente a 0,03 del punto. Pasaba en el 100 % de las fichas FAR de los tres catálogos. Pero eso era una correlación, y podía tener otra explicación: quizá los vecinos simplemente son lo más parecido al punto que existe.

Así que hice la prueba causal. Mismo punto, misma nota de coseno, y solo cambio una cosa: los vecinos que ve el LLM. Pueden ser los verdaderos, los de otro punto distinto, o ninguno. La hice en Steam y en arXiv, con dos generadores (luna y Sonnet), en REAL, GAP y FAR, con 20 puntos por combinación y las reglas de decisión escritas antes de lanzar nada. Patentes no entró en esta prueba.

<figure class="lg-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Coseno medio entre la ficha y su punto según los vecinos mostrados. Con los vecinos verdaderos, REAL llega a 0,73 en Steam y 0,78 en arXiv; con vecinos de otro punto o sin vecinos baja a 0,3-0,4. En FAR, con los vecinos verdaderos solo llega a 0,03-0,05 y sin ellos queda por debajo de cero.">
<g font-size="11" fill="#94a3b8">
<rect x="150" y="8" width="11" height="11" fill="#2dd4bf"/><text x="166" y="18">vecinos verdaderos</text>
<rect x="292" y="8" width="11" height="11" fill="#f59e0b"/><text x="308" y="18">de otro punto</text>
<rect x="406" y="8" width="11" height="11" fill="#64748b"/><text x="422" y="18">sin vecinos</text>
</g>
<line x1="45" y1="230" x2="300" y2="230" stroke="rgba(255,255,255,0.25)"/><line x1="325" y1="230" x2="580" y2="230" stroke="rgba(255,255,255,0.25)"/>
<g stroke="rgba(255,255,255,0.07)"><line x1="45" y1="105" x2="300" y2="105"/><line x1="325" y1="105" x2="580" y2="105"/><line x1="45" y1="55" x2="300" y2="55"/><line x1="325" y1="55" x2="580" y2="55"/></g>
<g font-size="10" fill="#94a3b8" text-anchor="end"><text x="40" y="233">0</text><text x="40" y="108">0,5</text><text x="40" y="58">0,7</text></g>
<g fill="#2dd4bf"><rect x="60" y="48" width="18" height="182"/><rect x="145" y="105.5" width="18" height="124.5"/><rect x="230" y="223.25" width="18" height="6.75"/>
<rect x="340" y="34" width="18" height="196"/><rect x="425" y="114" width="18" height="116"/><rect x="510" y="217" width="18" height="13"/></g>
<g fill="#f59e0b"><rect x="82" y="120" width="18" height="110"/><rect x="167" y="139.75" width="18" height="90.25"/><rect x="252" y="230" width="18" height="5.25"/>
<rect x="362" y="143.75" width="18" height="86.25"/><rect x="447" y="153" width="18" height="77"/><rect x="532" y="230" width="18" height="4.25"/></g>
<g fill="#64748b"><rect x="104" y="124" width="18" height="106"/><rect x="189" y="142.25" width="18" height="87.75"/><rect x="274" y="230" width="18" height="3.25"/>
<rect x="384" y="137.5" width="18" height="92.5"/><rect x="469" y="156.25" width="18" height="73.75"/><rect x="554" y="230" width="18" height="3.5"/></g>
<g font-size="11.5" fill="#e2e8f0" text-anchor="middle"><text x="91" y="266">REAL</text><text x="176" y="266">GAP</text><text x="261" y="266">FAR</text><text x="371" y="266">REAL</text><text x="456" y="266">GAP</text><text x="541" y="266">FAR</text></g>
<g font-size="10" fill="#5eead4" text-anchor="middle"><text x="239" y="216">0,03</text><text x="519" y="210">0,05</text></g>
<g font-size="9.5" fill="#fbbf24" text-anchor="middle"><text x="268" y="247">−0,02</text><text x="548" y="247">−0,02</text></g>
<g font-size="12.5" fill="#f8fafc" text-anchor="middle" font-weight="600"><text x="172" y="290">Steam</text><text x="452" y="290">arXiv</text></g>
</svg>
<figcaption>Coseno ficha–punto, media de los dos generadores. Quitando o cambiando los vecinos, lo poco que se acercaba a un punto FAR desaparece: la nota de coseno sola no acerca nada.</figcaption>
</figure>

El resultado fue el mismo en las 12 combinaciones: cambiar los vecinos arrastra la ficha hacia los vecinos que ve. En FAR, lo poco que la ficha se acercaba al punto (0,02–0,07 con los vecinos verdaderos) desaparece en cuanto le quitas o le cambias los vecinos, y se queda en −0,02/−0,01. **La nota de coseno por sí sola no acerca el texto a un punto lejano. Lo que el LLM sabe hacer es escribir algo parecido a lo que le enseñas.**

## Lo que sí funciona: pedirlo sin mapa

Los huecos internos sí se alcanzan. Una ficha GAP llega a 0,48–0,55 de su punto en Steam, igual que el mejor juego existente. Pero no son más nuevos. En Steam los jueces les dieron una novedad de 4,9 sobre 10, por debajo de INTERP (5,5), con los seis generadores. En arXiv quedaron empatados con INTERP, y en patentes depende del generador. Un hueco entre juegos se rellena con algo que se parece a los juegos de alrededor.

Para los jueces, lo más novedoso fue lo que no usaba el mapa: PLAIN, simplemente pedir «un juego nuevo». Con todos los generadores, PLAIN superaba al mejor brazo guiado por entre 1,1 y 2,6 puntos de novedad.

Hasta que leí las fichas seguidas. Sonnet llamó a 45 de sus 50 juegos «Tidewright» algo, y luna vía Codex escribió 46 museos de 50. Yo lo vi enseguida («otro museo… cansino»). Los jueces no lo vieron, porque puntuaban cada ficha por separado y nunca vieron dos juntas. Cada idea era nueva frente al catálogo, pero el generador repetía siempre la misma idea. En arXiv pasó igual: Sonnet tituló 43 de sus 50 artículos «Tidal» algo.

<figure class="lg-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Parecido medio entre las 50 ideas de cada generador. PLAIN con Sonnet llega a 0,86 y con luna vía Codex a 0,81, muy por encima de 50 juegos reales al azar (0,40) y de los brazos guiados (0,35-0,49).">
<g font-size="11.5" fill="#e2e8f0" text-anchor="end">
<text x="200" y="45">PLAIN · Sonnet</text><text x="200" y="75">PLAIN · luna vía Codex</text><text x="200" y="105">PLAIN · gpt-6.1-sol</text><text x="200" y="135">PLAIN · luna (API)</text><text x="200" y="165">PLAIN · Haiku</text><text x="200" y="195">PLAIN · Opus</text><text x="200" y="225">50 juegos reales al azar</text><text x="200" y="255">brazos guiados</text>
</g>
<g fill="#f59e0b"><rect x="210" y="34" width="241.9" height="15"/><rect x="210" y="64" width="227.1" height="15"/></g>
<g fill="#b45309"><rect x="210" y="94" width="176.9" height="15"/><rect x="210" y="124" width="160.7" height="15"/><rect x="210" y="154" width="159.3" height="15"/><rect x="210" y="184" width="145.6" height="15"/></g>
<rect x="210" y="214" width="113.1" height="15" fill="#64748b"/>
<rect x="210" y="244" width="137.2" height="15" fill="rgba(45,212,191,0.3)"/><rect x="210" y="244" width="98" height="15" fill="#2dd4bf"/>
<g font-size="10.5" fill="#94a3b8"><text x="457" y="46">0,86 · 45/50 «Tidewright»</text><text x="443" y="76">0,81 · 46/50 museos</text><text x="393" y="106">0,63</text><text x="377" y="136">0,57</text><text x="375" y="166">0,57</text><text x="362" y="196">0,52</text><text x="329" y="226">0,40</text><text x="353" y="256">0,35–0,49</text></g>
<line x1="210" y1="25" x2="210" y2="265" stroke="rgba(255,255,255,0.25)"/>
<text x="300" y="288" fill="#94a3b8" font-size="10.5" text-anchor="middle">coseno mediano entre pares de ideas del mismo generador (más alto = más repetidas)</text>
</svg>
<figcaption>Pedir sin mapa da las ideas más nuevas una a una, pero dos generadores repiten casi siempre la misma. Enseñándole sus ideas anteriores (PLAIND), la repetición baja casi al nivel de los brazos guiados.</figcaption>
</figure>

Lo arreglé con una variante, PLAIND, en la que el modelo ve los títulos que ya ha propuesto. La repetición baja casi al nivel de los brazos guiados y la novedad sigue siendo la más alta en los tres catálogos, entre 1 y 5 puntos por encima de INTERP según el generador.

Mi novedad y la de los jueces no se parecen tanto como esperaba. En patentes les di a todos los brazos entre 1,2 y 3 puntos menos que los jueces. De tres de las cuatro patentes FAR que leí dije «sí, conozco algo que hace esto», y de una GAP escribí que era «un recommendation system de toda la vida». Creo que medimos cosas distintas. Los jueces premian lo específico y poco familiar frente a los cinco textos que se les enseñan, y yo me pregunto si el concepto ya existe.

## ¿Y si buscamos de verdad un texto coherente lejos?

Todo lo anterior dejaba una salida a la tesis del tuit: quizá el LLM no llega a los puntos lejanos porque busca mal, no porque ahí no haya nada. Así que busqué con más fuerza. Una búsqueda en GPU optimiza el coseno directamente, sin enseñar vecinos, y produce textos que se acercan mucho al punto pero son sopa de palabras. Luego Claude o Codex los reescriben para que se puedan leer, con el coseno como única pista. Dos modelos tenían que aceptar el texto como coherente. Antes de mirar los puntos lejanos comprobé que el método funcionaba: recuperaba los 10 juegos y los 10 artículos escondidos de REAL.

En arXiv mi objeción se sostiene: en el 90 % de los puntos FAR, el mejor texto coherente no supera al artículo existente más cercano. En Steam, no del todo. En un 25 % de los puntos, el texto coherente sí queda más de 0,05 por encima del juego más cercano, y en un 15 % si exijo además el visto bueno de un tercer modelo que no había escrito ni filtrado nada de lo que juzgaba. Salir un poco más allá de lo que existe es posible.

<figure class="lg-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Escala del coseno de 0 a 1. El mejor juego existente queda a 0,042 de un punto FAR y el mejor texto coherente a 0,07, como mucho 0,14; un juego real escondido se recupera a 0,84 y el punto está en 1.">
<line x1="40" y1="60" x2="560" y2="60" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>
<g font-size="10" fill="#94a3b8" text-anchor="middle"><text x="40" y="78">0</text><text x="300" y="78">0,5</text><text x="560" y="78">1</text></g>
<rect x="40" y="52" width="104" height="16" fill="none" stroke="#64748b" stroke-dasharray="3 3"/>
<circle cx="477.8" cy="60" r="5" fill="#2dd4bf"/><text x="477.8" y="96" fill="#5eead4" font-size="11" text-anchor="middle">REAL: 0,84</text>
<path d="M560,48 l3,7 8,1 -6,5 2,8 -7,-4 -7,4 2,-8 -6,-5 8,-1z" fill="#f59e0b"/><text x="548" y="35" fill="#fbbf24" font-size="11" text-anchor="end">el punto: 1</text>
<path d="M40,68 L40,138 M144,68 L560,138" stroke="#64748b" stroke-dasharray="3 3" fill="none"/>
<line x1="40" y1="150" x2="560" y2="150" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>
<g font-size="10" fill="#94a3b8" text-anchor="middle"><text x="40" y="168">0</text><text x="300" y="168">0,1</text><text x="560" y="168">0,2</text></g>
<line x1="149" y1="140" x2="149" y2="160" stroke="#94a3b8" stroke-width="2"/>
<text x="149" y="128" fill="#e2e8f0" font-size="11" text-anchor="middle">juego más cercano 0,042 (mediana)</text>
<circle cx="219" cy="150" r="5" fill="#2dd4bf"/>
<text x="219" y="190" fill="#5eead4" font-size="11" text-anchor="middle">mediana coherente 0,07</text>
<rect x="274" y="144" width="130" height="12" rx="3" fill="rgba(45,212,191,0.35)" stroke="#2dd4bf"/>
<text x="339" y="128" fill="#5eead4" font-size="11" text-anchor="middle">las que escapan: 0,09–0,14</text>
<text x="300" y="218" fill="#94a3b8" font-size="10.5" text-anchor="middle">zoom de 0 a 0,2 · Steam, puntos FAR, búsqueda en GPU + reescritura</text>
</svg>
<figcaption>Más allá de cualquier juego existente no es lo mismo que en el punto. Incluso los textos coherentes que escapan se quedan a 0,09–0,14 de un punto que está en 1.</figcaption>
</figure>

Pero hay que mirar la escala. Esos textos que escapan se quedan a un coseno de 0,09–0,14 de su punto. El juego más cercano estaba a 0,04 (mediana de esos 20 puntos), y el punto mismo está en 1. «Más lejos que cualquier juego» no es «en el punto». Esto matiza mi objeción, y creo que la mejora. No es imposible salir del mapa. Lo que pasa es que lo que se alcanza queda muy lejos de lo que se pidió, y lo que se lee sigue siendo un juego normal.

## ¿Se puede demostrar?

Quise ir más allá de los datos y, con ayuda de gpt-6-astra, intenté demostrar una cota: hasta dónde puede acercarse un texto coherente a un punto lejano. Ninguna cota aguantó, porque cada propuesta caía con los datos que ya teníamos. La coherencia no es suave: los jueces dan veredictos opuestos a fichas que solo se diferencian en una palabra. Y ningún umbral de probabilidad de un modelo de lenguaje separa lo que los jueces aceptan de lo que rechazan.

Así que le di la vuelta: ¿se puede demostrar que no hay cota? En sentido estricto no, porque los textos de longitud limitada son un conjunto finito y siempre tienen un máximo. Lo que sí quedó demostrado, y comprobado en Lean, es otra cosa. Sin una regla que diga qué cuenta como coherente, nadie puede certificar un techo mejor que el trivial, por muchas pruebas que haga. Y en general, el problema es computacionalmente difícil.

## ¿Se adelantó alguna idea al futuro?

Quedaba la comprobación con los juegos y artículos posteriores. En Steam no sirve: una vez reescritas todas las fichas al mismo formato, los juegos reales anteriores y posteriores a 2024 apenas se distinguen. En arXiv sí funciona, y las ideas FAR no se acercan a lo publicado después de 2023 más que un artículo antiguo cualquiera. Las de PLAIND sí se acercan. Pero los generadores se entrenaron después de 2023, así que eso muestra que saben lo que vino, no que lo anticipen. El único generador que no podía conocer esos artículos, gpt-4o, no se adelanta a nada una vez quitado el estilo.

## En resumen

- **Los huecos internos se alcanzan, pero no son nuevos.** Se rellenan con algo parecido a lo que los rodea.
- **Los puntos lejanos no se alcanzan.** El texto vuelve al casquete donde están los textos, junto a los vecinos que se le enseñan, y la prueba causal muestra que lo arrastran los vecinos.
- **La novedad vino de pedirla**, no de la geometría vacía, siempre que el modelo vea lo que ya ha propuesto.

El tuit acierta en algo: hay rincones del mapa sin explorar a los que se puede llegar. Pero un punto lejos de todo no es una idea esperando a que alguien la escriba. Casi siempre es un sitio donde no cabe ningún texto.

Me queda la otra mitad de la pregunta, la que el resultado de arXiv deja abierta: ¿puede un modelo llegar a una idea que de verdad no existía cuando se entrenó? Es la prueba de Einstein que propuso Demis Hassabis: entrenar un modelo solo con lo que se sabía antes de 1911 y ver si llega a la relatividad general. Esa será la segunda parte, con un generador cuya fecha de corte controlo yo.
