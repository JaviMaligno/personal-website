---
title: "Los huecos del mapa no son ideas"
description: "Un tuit proponía sacar ideas nuevas de los puntos vacíos de un espacio de embeddings. Lo probé con juegos de Steam, artículos de arXiv y patentes: ningún texto coherente llega a esos puntos, y lo que sale de ellos es un juego normal."
pubDate: 2026-11-02
tags: ["IA", "Embeddings", "LLMs", "Investigación", "Creatividad"]
lang: es
translationKey: far-points-are-not-ideas
heroImage: "/blog/far-points-are-not-ideas.png"
linkedinImage: "/blog/far-points-are-not-ideas-linkedin.png"
repoUrl: "https://github.com/JaviMaligno/latent-gap-ideas"
---
Hace poco [@syntheticbeef publicó en X](https://x.com/syntheticbeef/status/2112904858718367750) una receta para que la IA invente ideas de verdad nuevas. Embebes los juegos de Steam, eliges puntos del espacio que estén lejos de todos ellos, conviertes cada punto de vuelta en la descripción de un juego y ordenas el resultado por lo distinto que es de lo que ya existe. Si el punto está lejos de todo, la idea que sale de él debería ser nueva.

Mi objeción fue inmediata: en un espacio de mil dimensiones casi todo está lejos de todo, y casi todo ese espacio es ruido. Que un punto esté vacío no significa que ahí quepa una idea; puede que ahí no quepa ningún texto con sentido. Un amigo me respondió que la coherencia es otra dimensión más, con sus propios óptimos locales, y que la difusión de imágenes demuestra que existen rincones raros y con sentido: un astronauta a caballo. Le di la razón en que existen, pero la difusión llega a ellos partiendo de un concepto y avanzando por similitud; el tuit busca la disimilitud sin ningún punto de partida.

Era una discusión que se podía medir, así que la medí.

<style>
.lg-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.lg-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.lg-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Tres mapas

Repetí todo en tres catálogos que no se parecen en nada entre sí, para que la conclusión no dependiera de uno:

- **Steam**, el mapa del tuit: unos 68.000 juegos publicados antes de 2024, con su descripción, géneros y etiquetas. Guardé aparte los 41.000 publicados después, para comprobar al final si alguna idea se adelantaba a lo que salió más tarde.
- **arXiv**: 72.000 artículos de informática anteriores a 2023, cada uno con su título y su resumen.
- **Patentes**: 71.521 solicitudes de patente presentadas en Estados Unidos entre 2012 y 2015.

Steam es el hilo del artículo. arXiv y patentes sirven para comprobar que lo que pasa no es una rareza de los videojuegos.

Cada texto se convierte en un vector con Qwen3-Embedding-0.6B, un modelo abierto de embeddings. Para medir lo cerca que están dos textos uso el coseno entre sus vectores: 1 si apuntan en la misma dirección, 0 si no tienen nada que ver.

## Dos formas de convertir un punto en texto

Un punto del espacio es una lista de 1.024 números. Ningún modelo de lenguaje puede leerlo, así que el tuit da por hecho un paso que no es trivial: convertir el punto de vuelta en texto. Hay dos formas de hacerlo.

**La primera es enseñarle los vecinos**, la que se le ocurre a cualquiera. Le enseñas al LLM los 8 juegos reales más cercanos al punto, le pides una ficha de juego y le dices lo cerca que ha quedado: el coseno entre su ficha y el punto. Con esa nota vuelve a intentarlo, como en el juego de frío o caliente. Cuatro rondas de tres candidatas, y me quedo con la mejor. En arXiv el LLM escribe un resumen de artículo, y en patentes, una solicitud.

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

Esta forma tiene un problema evidente. **Si le das 8 juegos, lo normal es que escriba algo parecido a esos 8**, y entonces el punto sobra: es lo mismo que pedirle «hazme un juego a partir de estos». Lo único que podría hacer que el punto importara es la nota de coseno. Si el frío o caliente funcionara, el LLM se iría acercando al punto más allá de lo que le dan los vecinos. Eso se puede medir, y lo medí.

**La segunda forma es buscar sin enseñar nada.** Una búsqueda en GPU genera textos que maximizan directamente el coseno con el punto. Esos textos se acercan mucho, pero son sopa de palabras, así que luego Claude o Codex los reescriben para que se puedan leer, con el coseno como única pista. Dos modelos tienen que aceptar el resultado como coherente. Esta es la prueba de verdad de la idea del tuit: si hay un texto coherente cerca del punto, es la forma que tiene más opciones de encontrarlo.

## Cinco tipos de punto

Probé cinco tipos de punto. Cada tipo es lo que en un experimento se llama un brazo:

- **REAL**: el punto de un juego real que escondo del mapa. Es el control. Si el método no recupera un juego que existe, nada de lo demás significa algo.
- **INTERP**: el punto medio entre dos juegos muy distintos. Es la versión geométrica de «combina dos ideas lejanas».
- **GAP**: huecos internos, puntos que caen en la zona donde hay juegos pero donde no hay ninguno.
- **FAR**: la receta del tuit. De 20.000 direcciones al azar, las 50 más alejadas de cualquier juego.
- **PLAIN**: sin mapa. Solo le pido al modelo «inventa un juego nuevo, distinto de cualquiera que exista».

En Steam usé seis generadores, que son los modelos que escriben las fichas: Claude Opus, Sonnet y Haiku, gpt-6.1-sol, y gpt-6-luna por API y a través de Codex. En arXiv y patentes usé dos, luna vía Codex y Sonnet. Antes de puntuar, otro modelo reescribía cada ficha al mismo formato de 120 palabras, para que el estilo no delatara de dónde venía. Después cuatro modelos distintos las puntuaron a ciegas en coherencia, viabilidad, atractivo y novedad frente a los cinco textos existentes más parecidos. Entre las fichas a puntuar había también juegos reales posteriores a 2024, como referencia. Además, yo puntué 64 de las mismas fichas a mano.

## Qué sale enseñando los vecinos

**REAL funciona.** Cuando el punto es un juego escondido, el decodificador vuelve a su zona, con un coseno de alrededor de 0,7. Con [*Star Farmer: Warlock of the Universe*](https://store.steampowered.com/app/2398900/) escondido, escribió *Voidbloom Run*, un juego de granjero espacial que cultiva semillas en planetas hostiles, a 0,87.

Y reconstruye lo que haya en el mapa, también lo que nadie querría. Uno de los juegos escondidos era [*SEX with HITLER: WW2*](https://store.steampowered.com/app/2298590/), y entre los vecinos que vio el modelo estaban los dos anteriores de la serie, [*SEX with HITLER*](https://store.steampowered.com/app/1849000/) y [*SEX with HITLER 2*](https://store.steampowered.com/app/2194810/). Escribió *Hitler: No Future in Berlin*, una novela visual con disparos en la que el Führer, derrotado, intenta sobrevivir entre las ruinas de Berlín y conoce a «cinco heroínas adultas» (coseno 0,69).

**INTERP da combinaciones literales.** Entre [*Skill Master VR -- Learn Meditation*](https://store.steampowered.com/app/553430/), un juego de meditación en realidad virtual, y [*Demon's Rise - Lords of Chaos*](https://store.steampowered.com/app/844420/), uno de estrategia con demonios, salió *Ashen Breath: Legions of the Void*, un RPG táctico de fantasía oscura «con un modo opcional de meditación en VR» (0,84). Es lo que se pidió, y se nota la costura.

**FAR no llega a ninguna parte.** La ficha aterriza a un coseno de entre 0,03 y 0,05 del punto, según el generador, es decir, prácticamente a cero. El juego existente más cercano a esos puntos está a 0,046, así que tampoco hay nada mejor. Lo que sale es un juego normal, parecido a los vecinos que se le enseñaron. Los de uno de los puntos eran [*Challenge from the Black Cat*](https://store.steampowered.com/app/2517090/), [un puzle japonés de hámsteres](https://store.steampowered.com/app/1714200/) y [*My Furry Stepmom*](https://store.steampowered.com/app/2082060/), y salió *Pounce & Pop: Kitten's Block Quest*, una gatita que empuja bloques para volver a casa (0,069). De otro salió *The Museum of Unfinished Things*, un museo que se reordena solo por la noche (0,028). Son juegos razonables, incluso agradables, que podrían estar ya en Steam.

En arXiv y en patentes pasa lo mismo: lo que se escribe para un punto FAR aterriza a menos de 0,08.

## ¿Es solo copiar a los vecinos?

Las fichas FAR estaban mucho más cerca de sus 8 vecinos que del propio punto: en Steam, a un coseno de 0,63–0,72 de su centroide, frente a 0,03 del punto. Pasaba en el 100 % de las fichas FAR de los tres catálogos. La pregunta del apartado anterior seguía abierta: ¿la nota de coseno aporta algo, o todo lo hacen los vecinos?

Para separarlo hice una prueba causal. Mismo punto, misma nota de coseno, y solo cambio una cosa: los vecinos que ve el LLM. Pueden ser los verdaderos, los de otro punto distinto, o ninguno. La hice en Steam y en arXiv, con dos generadores (luna y Sonnet), en REAL, GAP y FAR, con 20 puntos por combinación y las reglas de decisión escritas antes de lanzar nada.

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
<figcaption>Coseno ficha–punto, media de los dos generadores. Sin los vecinos verdaderos, hasta un juego o artículo escondido se queda a 0,3–0,4, apenas más cerca que de otro punto cualquiera. La nota de coseno sola casi no acerca nada.</figcaption>
</figure>

**Lo hacen los vecinos, en las 12 combinaciones.** Con los vecinos de otro punto, la ficha se va hacia ese otro punto. Sin vecinos, jugando solo a frío o caliente, la ficha acaba entre 0,04 y 0,07 más cerca de su punto que de otro punto cualquiera del mismo tipo. Hasta con un juego escondido, sin vecinos se queda en 0,36–0,47, cuando con ellos llega a 0,7–0,8.

Visto ahora parece obvio, y en parte lo es: si a un LLM le das 8 juegos, escribe algo que depende de esos 8, no de un punto del que no sabe nada. Pero eso es lo que hace cualquier decodificador que use un LLM de esta manera, así que cualquier «idea» que salga de un punto por este camino es una mezcla de sus vecinos. **Para saber si en el punto hay algo, hay que buscar sin vecinos.**

## Buscar sin vecinos

Antes de mirar los puntos lejanos comprobé que la búsqueda funcionaba. Con los juegos y artículos escondidos de REAL, el mejor texto coherente quedó más cerca del punto que cualquier texto existente en los 10 casos de cada catálogo. En la mayoría de los huecos GAP llegó a la altura de lo existente o algo más allá.

<figure class="lg-fig">
<svg viewBox="0 0 600 328" role="img" aria-label="Cada punto es un punto del espacio. En horizontal, el coseno del texto existente más cercano; en vertical, el del mejor texto coherente que encontró la búsqueda sin vecinos. En REAL y GAP la búsqueda llega tan cerca como lo existente o más. En FAR todo se queda en la esquina de abajo: en Steam 5 de 20 puntos superan lo existente por más de 0,05, pero ninguno pasa de 0,14.">
<text x="160" y="22" fill="#e2e8f0" font-size="12" text-anchor="middle" font-weight="600">todos los puntos (Steam)</text>
<rect x="60" y="50" width="200" height="200" fill="none" stroke="rgba(255,255,255,0.12)"/>
<line x1="60" y1="250" x2="260" y2="50" stroke="#64748b" stroke-dasharray="4 4"/>
<text x="60" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0</text>
<text x="54" y="253.5" fill="#94a3b8" font-size="10" text-anchor="end">0</text>
<text x="160.0" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0,5</text>
<text x="54" y="153.5" fill="#94a3b8" font-size="10" text-anchor="end">0,5</text>
<text x="260" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">1</text>
<text x="54" y="53.5" fill="#94a3b8" font-size="10" text-anchor="end">1</text>
<circle cx="71.4" cy="240.8" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="66.6" cy="238.8" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="69.4" cy="251.6" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="67.5" cy="236.7" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="67.7" cy="234.8" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="67.3" cy="243.4" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.2" cy="240.0" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.0" cy="225.7" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.1" cy="248.4" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="73.8" cy="240.7" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.4" cy="235.6" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.5" cy="222.4" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.5" cy="231.4" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.5" cy="234.7" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="69.2" cy="233.2" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.8" cy="238.8" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="70.7" cy="234.9" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="69.9" cy="228.2" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="70.3" cy="229.0" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="71.1" cy="241.1" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="164.0" cy="154.4" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="165.1" cy="145.0" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="164.4" cy="120.7" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="164.0" cy="144.2" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="169.0" cy="131.5" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="167.7" cy="132.0" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="169.2" cy="138.3" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="169.7" cy="142.0" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="166.3" cy="141.2" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="166.9" cy="128.5" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="166.7" cy="144.3" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="174.5" cy="154.7" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="171.2" cy="158.6" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="167.1" cy="145.1" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="170.7" cy="132.1" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="168.0" cy="134.8" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="171.0" cy="134.3" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="168.3" cy="121.6" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="167.7" cy="130.3" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="171.2" cy="133.9" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="202.0" cy="96.9" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="206.0" cy="78.9" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="226.2" cy="72.8" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="208.6" cy="72.4" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="200.2" cy="84.2" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="215.7" cy="79.1" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="206.1" cy="95.7" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="204.9" cy="88.2" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="213.7" cy="78.8" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="204.6" cy="86.5" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<text x="202.0" y="60.0" fill="#5eead4" font-size="11" text-anchor="end">REAL</text>
<text x="166.0" y="110.0" fill="#fbbf24" font-size="11" text-anchor="middle">GAP</text>
<text x="78.0" y="216.0" fill="#f8fafc" font-size="11">FAR</text>
<rect x="58.0" y="220.0" width="34.0" height="32.0" fill="none" stroke="#94a3b8" stroke-dasharray="2 2"/>
<text x="98.0" y="246.0" fill="#94a3b8" font-size="10">zoom →</text>
<text x="440" y="22" fill="#e2e8f0" font-size="12" text-anchor="middle" font-weight="600">zoom: puntos FAR</text>
<rect x="340" y="50" width="200" height="200" fill="none" stroke="rgba(255,255,255,0.12)"/>
<polygon points="340.0,191.1764705882353 481.1764705882353,50.0 340.0,50.0" fill="rgba(45,212,191,0.10)"/>
<line x1="340.0" y1="191.1764705882353" x2="481.1764705882353" y2="50.0" stroke="#2dd4bf" stroke-width="0.8" stroke-dasharray="3 3"/>
<line x1="340.0" y1="250.0" x2="540.0" y2="50.0" stroke="#64748b" stroke-dasharray="4 4"/>
<text x="363.52941176470586" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0</text>
<text x="546" y="229.97058823529412" fill="#94a3b8" font-size="10">0</text>
<text x="422.3529411764706" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0,05</text>
<text x="546" y="171.1470588235294" fill="#94a3b8" font-size="10">0,05</text>
<text x="481.1764705882353" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0,1</text>
<text x="546" y="112.3235294117647" fill="#94a3b8" font-size="10">0,1</text>
<text x="540.0" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0,15</text>
<text x="546" y="53.5" fill="#94a3b8" font-size="10">0,15</text>
<circle cx="430.9" cy="172.4" r="3.4" fill="#f8fafc"/>
<circle cx="402.6" cy="160.4" r="3.4" fill="#f8fafc"/>
<circle cx="418.9" cy="235.8" r="3.4" fill="#f8fafc"/>
<circle cx="407.9" cy="148.1" r="3.4" fill="#f8fafc"/>
<circle cx="409.1" cy="137.3" r="3.4" fill="#f8fafc"/>
<circle cx="406.6" cy="187.9" r="3.4" fill="#f8fafc"/>
<circle cx="411.8" cy="167.8" r="3.4" fill="#f8fafc"/>
<circle cx="410.4" cy="83.7" r="3.4" fill="#f8fafc"/>
<circle cx="411.1" cy="217.1" r="3.4" fill="#f8fafc"/>
<circle cx="444.7" cy="171.9" r="3.4" fill="#f8fafc"/>
<circle cx="413.2" cy="141.9" r="3.4" fill="#f8fafc"/>
<circle cx="413.4" cy="64.4" r="3.4" fill="#f8fafc"/>
<circle cx="413.6" cy="116.8" r="3.4" fill="#f8fafc"/>
<circle cx="413.8" cy="136.4" r="3.4" fill="#f8fafc"/>
<circle cx="417.5" cy="127.8" r="3.4" fill="#f8fafc"/>
<circle cx="415.6" cy="160.7" r="3.4" fill="#f8fafc"/>
<circle cx="426.4" cy="137.6" r="3.4" fill="#f8fafc"/>
<circle cx="421.5" cy="98.1" r="3.4" fill="#f8fafc"/>
<circle cx="424.1" cy="103.2" r="3.4" fill="#f8fafc"/>
<circle cx="428.8" cy="174.2" r="3.4" fill="#f8fafc"/>
<circle cx="432.1" cy="153.9" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="439.1" cy="165.4" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="421.0" cy="241.5" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="423.6" cy="147.8" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="441.0" cy="167.0" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="430.5" cy="190.4" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="444.5" cy="168.0" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="428.2" cy="167.1" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="454.0" cy="153.6" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="441.5" cy="186.5" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="440.0" cy="197.3" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="428.7" cy="138.9" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="453.7" cy="135.4" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="462.0" cy="98.6" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="453.3" cy="149.3" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="434.7" cy="110.2" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="429.9" cy="189.9" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="436.4" cy="233.0" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="436.0" cy="136.4" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="453.0" cy="100.9" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<text x="160" y="282" fill="#94a3b8" font-size="10.5" text-anchor="middle">texto existente más cercano →</text>
<text x="440" y="282" fill="#94a3b8" font-size="10.5" text-anchor="middle">texto existente más cercano →</text>
<text x="22" y="150" fill="#94a3b8" font-size="10.5" text-anchor="middle" transform="rotate(-90 22 150)">mejor texto coherente encontrado →</text>
<circle cx="150" cy="310" r="3.4" fill="#f8fafc"/><text x="158" y="313.5" fill="#e2e8f0" font-size="10.5">FAR Steam</text>
<circle cx="240" cy="310" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/><text x="248" y="313.5" fill="#e2e8f0" font-size="10.5">FAR arXiv</text>
<line x1="325" y1="310" x2="345" y2="310" stroke="#64748b" stroke-dasharray="4 4"/><text x="351" y="313.5" fill="#e2e8f0" font-size="10.5">igual que lo existente</text>
<rect x="478" y="304" width="14" height="12" fill="rgba(45,212,191,0.25)" stroke="#2dd4bf" stroke-width="0.8" stroke-dasharray="3 3"/><text x="498" y="313.5" fill="#e2e8f0" font-size="10.5">+0,05: escapa</text>
</svg>
<figcaption>La búsqueda sin vecinos llega adonde ya hay texto, y algo más allá. En los puntos FAR se queda pegada a cero: en Steam, 5 de 20 superan lo existente por más de 0,05, y el mejor llega a 0,14.</figcaption>
</figure>

En los puntos FAR la cosa cambia. **En arXiv mi objeción se sostiene:** en el 90 % de los puntos, el mejor texto coherente no supera al artículo existente más cercano. **En Steam, no del todo.** En un 25 % de los puntos el texto coherente sí queda más de 0,05 por encima del juego más cercano, y en un 15 % si exijo además el visto bueno de un tercer modelo que no había escrito ni filtrado nada de lo que juzgaba. Salir un poco más allá de lo que existe es posible.

Pero hay que mirar la escala. **Esos textos que escapan se quedan a un coseno de 0,09–0,14 de su punto, cuando el punto mismo está en 1.** «Más lejos que cualquier juego» no es «en el punto». Esto matiza mi objeción, y creo que la mejora. No es imposible salir del mapa. Lo que pasa es que lo que se alcanza queda muy lejos de lo que se pidió, y lo que se lee sigue siendo un juego normal.

## Por qué: el casquete

La geometría explica por qué los puntos lejanos son inalcanzables. Los textos no se reparten por todo el espacio. Todos comparten una dirección común, así que **ocupan un casquete estrecho de la esfera**: dos juegos cualesquiera de Steam tienen un coseno de 0,41, mientras que dos direcciones al azar tienen 0 ± 0,03. Los puntos FAR son direcciones al azar elegidas por estar lejos de todo, así que caen fuera del casquete. Cualquier texto, por raro que sea, cae dentro.

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

Con esta geometría se puede predecir la distancia antes de mirar. Antes de construir ningún punto de arXiv, calculé solo con las estadísticas del corpus a qué distancia quedaría el artículo más cercano a un punto lejano. Predije 0,062 y salió 0,058. En patentes salió 0,062.

## Lo que sí funciona: pedirlo sin mapa

**Los huecos internos sí se alcanzan, pero no son más nuevos.** En Steam los jueces les dieron una novedad de 4,9 sobre 10, por debajo de INTERP (5,5), con los seis generadores. En arXiv quedaron empatados con INTERP, y en patentes depende del generador. Un hueco entre juegos se rellena con algo que se parece a los juegos de alrededor.

**Para los jueces, lo más novedoso fue lo que no usaba el mapa:** PLAIN, simplemente pedir «un juego nuevo». Con todos los generadores, PLAIN superaba al mejor brazo guiado por entre 1,1 y 2,6 puntos de novedad.

**Hasta que leí las fichas seguidas.** Sonnet llamó a 45 de sus 50 juegos «Tidewright» algo, y luna vía Codex escribió 46 museos de 50. Yo lo vi enseguida («otro museo… cansino»). Los jueces no lo vieron, porque puntuaban cada ficha por separado y nunca vieron dos juntas. Cada idea era nueva frente al catálogo, pero el generador repetía siempre la misma idea. En arXiv pasó igual: Sonnet tituló 43 de sus 50 artículos «Tidal» algo.

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

**Lo arreglé con una variante, PLAIND**, en la que el modelo ve los títulos que ya ha propuesto. La repetición baja casi al nivel de los brazos guiados y la novedad sigue siendo la más alta en los tres catálogos, entre 1 y 5 puntos por encima de INTERP según el generador.

Mi novedad y la de los jueces no se parecen tanto como esperaba.

<figure class="lg-fig">
<svg viewBox="0 0 600 420" role="img" aria-label="Novedad media que doy yo frente a la de los jueces, por catálogo y brazo. En Steam coincidimos salvo en PLAIN, donde los jueces dan 7,6 y yo 5,2. En arXiv coincidimos bastante. En patentes doy entre 1,2 y 3 puntos menos en todos los brazos.">
<rect x="230" y="8" width="10" height="10" rx="5" fill="#f59e0b"/><text x="246" y="17" fill="#e2e8f0" font-size="11">yo</text>
<rect x="300" y="8" width="10" height="10" rx="5" fill="#2dd4bf"/><text x="316" y="17" fill="#e2e8f0" font-size="11">jueces</text>
<text x="20" y="48" fill="#f8fafc" font-size="12" font-weight="600">Steam</text>
<text x="218" y="48" fill="#e2e8f0" font-size="11" text-anchor="end">INTERP <tspan fill="#64748b" font-size="9.5">n=13</tspan></text>
<line x1="230" y1="44" x2="554" y2="44" stroke="rgba(255,255,255,0.06)"/>
<line x1="418.3" y1="44" x2="410.0" y2="44" stroke="#64748b" stroke-width="2"/>
<circle cx="418.3" cy="44" r="5" fill="#f59e0b"/><circle cx="410.0" cy="44" r="5" fill="#2dd4bf"/>
<text x="218" y="75" fill="#e2e8f0" font-size="11" text-anchor="end">GAP <tspan fill="#64748b" font-size="9.5">n=6</tspan></text>
<line x1="230" y1="71" x2="554" y2="71" stroke="rgba(255,255,255,0.06)"/>
<line x1="416.1" y1="71" x2="402.4" y2="71" stroke="#64748b" stroke-width="2"/>
<circle cx="416.1" cy="71" r="5" fill="#f59e0b"/><circle cx="402.4" cy="71" r="5" fill="#2dd4bf"/>
<text x="218" y="102" fill="#e2e8f0" font-size="11" text-anchor="end">PLAIN <tspan fill="#64748b" font-size="9.5">n=5</tspan></text>
<line x1="230" y1="98" x2="554" y2="98" stroke="rgba(255,255,255,0.06)"/>
<line x1="381.2" y1="98" x2="467.6" y2="98" stroke="#64748b" stroke-width="2"/>
<circle cx="381.2" cy="98" r="5" fill="#f59e0b"/><circle cx="467.6" cy="98" r="5" fill="#2dd4bf"/>
<text x="218" y="129" fill="#e2e8f0" font-size="11" text-anchor="end">PLAIND <tspan fill="#64748b" font-size="9.5">n=8</tspan></text>
<line x1="230" y1="125" x2="554" y2="125" stroke="rgba(255,255,255,0.06)"/>
<line x1="446.0" y1="125" x2="455.0" y2="125" stroke="#64748b" stroke-width="2"/>
<circle cx="446.0" cy="125" r="5" fill="#f59e0b"/><circle cx="455.0" cy="125" r="5" fill="#2dd4bf"/>
<text x="20" y="166" fill="#f8fafc" font-size="12" font-weight="600">arXiv</text>
<text x="218" y="166" fill="#e2e8f0" font-size="11" text-anchor="end">GAP <tspan fill="#64748b" font-size="9.5">n=3</tspan></text>
<line x1="230" y1="162" x2="554" y2="162" stroke="rgba(255,255,255,0.06)"/>
<line x1="398.1" y1="162" x2="403.9" y2="162" stroke="#64748b" stroke-width="2"/>
<circle cx="398.1" cy="162" r="5" fill="#f59e0b"/><circle cx="403.9" cy="162" r="5" fill="#2dd4bf"/>
<text x="218" y="193" fill="#e2e8f0" font-size="11" text-anchor="end">FAR <tspan fill="#64748b" font-size="9.5">n=4</tspan></text>
<line x1="230" y1="189" x2="554" y2="189" stroke="rgba(255,255,255,0.06)"/>
<line x1="410.0" y1="189" x2="412.2" y2="189" stroke="#64748b" stroke-width="2"/>
<circle cx="410.0" cy="189" r="5" fill="#f59e0b"/><circle cx="412.2" cy="189" r="5" fill="#2dd4bf"/>
<text x="218" y="220" fill="#e2e8f0" font-size="11" text-anchor="end">PLAIND <tspan fill="#64748b" font-size="9.5">n=5</tspan></text>
<line x1="230" y1="216" x2="554" y2="216" stroke="rgba(255,255,255,0.06)"/>
<line x1="431.6" y1="216" x2="465.8" y2="216" stroke="#64748b" stroke-width="2"/>
<circle cx="431.6" cy="216" r="5" fill="#f59e0b"/><circle cx="465.8" cy="216" r="5" fill="#2dd4bf"/>
<text x="218" y="247" fill="#e2e8f0" font-size="11" text-anchor="end">reales posteriores <tspan fill="#64748b" font-size="9.5">n=4</tspan></text>
<line x1="230" y1="243" x2="554" y2="243" stroke="rgba(255,255,255,0.06)"/>
<line x1="437.0" y1="243" x2="376.2" y2="243" stroke="#64748b" stroke-width="2"/>
<circle cx="437.0" cy="243" r="5" fill="#f59e0b"/><circle cx="376.2" cy="243" r="5" fill="#2dd4bf"/>
<text x="20" y="284" fill="#f8fafc" font-size="12" font-weight="600">Patentes</text>
<text x="218" y="284" fill="#e2e8f0" font-size="11" text-anchor="end">GAP <tspan fill="#64748b" font-size="9.5">n=3</tspan></text>
<line x1="230" y1="280" x2="554" y2="280" stroke="rgba(255,255,255,0.06)"/>
<line x1="349.9" y1="280" x2="419.0" y2="280" stroke="#64748b" stroke-width="2"/>
<circle cx="349.9" cy="280" r="5" fill="#f59e0b"/><circle cx="419.0" cy="280" r="5" fill="#2dd4bf"/>
<text x="218" y="311" fill="#e2e8f0" font-size="11" text-anchor="end">FAR <tspan fill="#64748b" font-size="9.5">n=4</tspan></text>
<line x1="230" y1="307" x2="554" y2="307" stroke="rgba(255,255,255,0.06)"/>
<line x1="338.0" y1="307" x2="446.0" y2="307" stroke="#64748b" stroke-width="2"/>
<circle cx="338.0" cy="307" r="5" fill="#f59e0b"/><circle cx="446.0" cy="307" r="5" fill="#2dd4bf"/>
<text x="218" y="338" fill="#e2e8f0" font-size="11" text-anchor="end">PLAIND <tspan fill="#64748b" font-size="9.5">n=5</tspan></text>
<line x1="230" y1="334" x2="554" y2="334" stroke="rgba(255,255,255,0.06)"/>
<line x1="402.8" y1="334" x2="480.2" y2="334" stroke="#64748b" stroke-width="2"/>
<circle cx="402.8" cy="334" r="5" fill="#f59e0b"/><circle cx="480.2" cy="334" r="5" fill="#2dd4bf"/>
<text x="218" y="365" fill="#e2e8f0" font-size="11" text-anchor="end">reales posteriores <tspan fill="#64748b" font-size="9.5">n=4</tspan></text>
<line x1="230" y1="361" x2="554" y2="361" stroke="rgba(255,255,255,0.06)"/>
<line x1="356.0" y1="361" x2="398.8" y2="361" stroke="#64748b" stroke-width="2"/>
<circle cx="356.0" cy="361" r="5" fill="#f59e0b"/><circle cx="398.8" cy="361" r="5" fill="#2dd4bf"/>
<text x="230" y="394" fill="#94a3b8" font-size="10" text-anchor="middle">1</text>
<text x="338" y="394" fill="#94a3b8" font-size="10" text-anchor="middle">4</text>
<text x="446" y="394" fill="#94a3b8" font-size="10" text-anchor="middle">7</text>
<text x="554" y="394" fill="#94a3b8" font-size="10" text-anchor="middle">10</text>
<text x="392.0" y="410" fill="#94a3b8" font-size="10.5" text-anchor="middle">novedad media (1–10)</text>
</svg>
<figcaption>Mi novedad frente a la de los jueces (64 fichas puntuadas por los dos). En patentes, donde reconocía casi todo, soy mucho más duro; en Steam solo me separo en PLAIN, el de los museos repetidos.</figcaption>
</figure>

En Steam coincidimos salvo en PLAIN, por los museos repetidos. En patentes soy mucho más duro en todos los brazos. De tres de las cuatro patentes FAR que leí dije «sí, conozco algo que hace esto», y de una GAP escribí que era «un recommendation system de toda la vida». Creo que medimos cosas distintas. Los jueces premian lo específico y poco familiar frente a los cinco textos que se les enseñan, y yo me pregunto si el concepto ya existe.

## ¿Se puede demostrar?

Quise ir más allá de los datos y, con ayuda de gpt-6-astra, intenté demostrar una cota: hasta dónde puede acercarse un texto coherente a un punto lejano. **Ninguna cota aguantó**, porque cada propuesta caía con los datos que ya teníamos. La coherencia no es suave: los jueces dan veredictos opuestos a fichas que solo se diferencian en una palabra. Y ningún umbral de probabilidad de un modelo de lenguaje separa lo que los jueces aceptan de lo que rechazan.

Así que le di la vuelta: ¿se puede demostrar que no hay cota? En sentido estricto no, porque los textos de longitud limitada son un conjunto finito y siempre tienen un máximo. Lo que sí quedó demostrado, y [comprobado en Lean](https://github.com/JaviMaligno/latent-gap-ideas/tree/main/lean), es otra cosa. **Sin una regla que diga qué cuenta como coherente, nadie puede certificar un techo mejor que el trivial**, por muchas pruebas que haga. Y en general, el problema es computacionalmente difícil.

## ¿Se adelantó alguna idea al futuro?

Quedaba la comprobación con los juegos y artículos posteriores. En Steam no sirve: una vez reescritas todas las fichas al mismo formato, los juegos reales anteriores y posteriores a 2024 apenas se distinguen. En arXiv sí funciona, y **las ideas FAR no se acercan a lo publicado después de 2023 más que un artículo antiguo cualquiera.** Las de PLAIND sí se acercan. Pero los generadores se entrenaron después de 2023, así que eso muestra que saben lo que vino, no que lo anticipen. El único generador que no podía conocer esos artículos, gpt-4o, no se adelanta a nada una vez quitado el estilo.

## En resumen

- **Decodificar un punto con un LLM es mezclar sus vecinos.** La nota de coseno casi no aporta nada; lo que sale depende de lo que se le enseña.
- **Buscando sin vecinos, los puntos lejanos siguen sin alcanzarse.** Lo mejor que encontré se queda a 0,14 de un punto que está en 1, porque los textos viven en un casquete y esos puntos están fuera.
- **Los huecos internos se alcanzan, pero no son nuevos.** Se rellenan con algo parecido a lo que los rodea.
- **La novedad vino de pedirla**, no de la geometría vacía, siempre que el modelo vea lo que ya ha propuesto.

El tuit acierta en algo: hay rincones del mapa sin explorar a los que se puede llegar. Pero un punto lejos de todo no es una idea esperando a que alguien la escriba. Casi siempre es un sitio donde no cabe ningún texto.

Me queda la otra mitad de la pregunta, la que el resultado de arXiv deja abierta: ¿puede un modelo llegar a una idea que de verdad no existía cuando se entrenó? Es la prueba de Einstein que propuso Demis Hassabis: entrenar un modelo solo con lo que se sabía antes de 1911 y ver si llega a la relatividad general. Esa será la segunda parte, con un generador cuya fecha de corte controlo yo.

---

*El código, los preregistros y las demostraciones en Lean están en [github.com/JaviMaligno/latent-gap-ideas]($R).*
