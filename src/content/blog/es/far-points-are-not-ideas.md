---
title: "Los huecos del mapa no son ideas"
description: "Un tuit proponía sacar ideas nuevas de los puntos vacíos de un espacio de embeddings. Lo probé con Steam, arXiv y patentes: a los puntos lejanos no llega ningún texto coherente, y lo que sale de ellos es un juego normal."
pubDate: 2026-11-26
tags: ["IA", "Embeddings", "LLMs", "Investigación", "Creatividad"]
lang: es
translationKey: far-points-are-not-ideas
heroImage: "/blog/far-points-are-not-ideas.png"
---
Hace unas semanas leí un tuit de @syntheticbeef con una receta para que la IA invente ideas de verdad nuevas: embebes todos los juegos de Steam, eliges un punto del espacio que esté lejos de todos ellos, lo conviertes de vuelta en una descripción y ordenas los resultados por lo distintos que son de lo que ya existe. Si el punto está lejos de todo, la idea que sale de él tiene que ser nueva.

Mi objeción fue inmediata: en un espacio de mil dimensiones casi todo está lejos de todo, y casi todo ese espacio es ruido. Que un punto esté vacío no significa que ahí quepa una idea; puede que ahí no quepa ningún texto con sentido. Un amigo me respondió que la coherencia es otra dimensión más, con sus propios óptimos locales, y que la difusión de imágenes demuestra que existen rincones raros y con sentido: un astronauta a caballo. Le di la razón en que existen, pero la difusión llega a ellos partiendo de un concepto y avanzando por similitud; el tuit busca la disimilitud sin ningún punto de partida.

Era una discusión que se podía medir, así que la medí.

<style>
.lg-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.lg-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.lg-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Cómo lo medí

Tomé los juegos de Steam publicados antes de 2024 (unos 68.000 tras quitar el contenido para adultos) como mapa, y guardé los 41.000 posteriores para comprobar después si el mundo había llenado algún hueco. Cada ficha se convierte en un vector con Qwen3-Embedding-0.6B, un modelo abierto. Luego repetí todo con resúmenes de arXiv y con solicitudes de patente, para no sacar conclusiones de un solo dominio.

Para «decodificar» un punto, un LLM escribe una ficha de juego en bucle. En cada ronda ve los 8 juegos reales más cercanos al punto y, después de escribir, solo recibe una nota: cuánto se parece su ficha al punto (el coseno). Cuatro rondas, tres candidatas por ronda, se queda la mejor.

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

Los puntos no eran todos del mismo tipo, y esa es la clave del experimento:

- **REAL**: el punto de un juego real que escondo. Es el control: si el método no recupera un juego que existe, nada de lo demás significa algo.
- **INTERP**: el punto medio entre dos juegos muy distintos, la versión geométrica de «combina dos ideas lejanas».
- **GAP**: huecos internos, puntos que caen dentro de la zona donde están los juegos pero donde no hay ninguno.
- **FAR**: la receta literal del tuit. De 20.000 direcciones al azar, las 50 más alejadas de cualquier juego.
- **PLAIN**: sin mapa. Solo le pido al modelo «inventa un juego nuevo, distinto de cualquiera que exista».

Las fichas las puntuaron a ciegas cinco modelos como jueces (coherencia, viabilidad, atractivo y novedad frente a los 5 juegos más parecidos), y una muestra la puntué yo también.

## Los puntos lejanos no se dejan escribir

El control funciona: en REAL el decodificador vuelve a caer, con un coseno de alrededor de 0,7–0,75, en la zona del juego escondido, tan cerca como el juego existente más parecido. El método sabe llegar a un sitio cuando en ese sitio hay texto.

En FAR, en cambio, la ficha aterriza a un coseno de 0,03 del punto. Prácticamente cero. Y no es que el LLM lo haga mal: el juego existente más cercano a esos puntos está a 0,046. Lo que sale es un juego normal. Por ejemplo, *Pounce & Pop: Kitten's Block Quest*, un puzle de empujar bloques con una gatita que vuelve a casa (coseno 0,069 con su punto), o *The Museum of Unfinished Things*, un museo que se reordena solo por la noche (0,028). Juegos razonables, incluso agradables, que podrían estar ya en Steam.

La geometría explica por qué. Los textos no ocupan el espacio entero: viven en un casquete estrecho. Dos direcciones al azar en 1.024 dimensiones tienen un coseno de 0 ± 0,03; dos juegos de Steam, de 0,41. Un punto FAR está fuera de ese casquete, y cualquier ficha que escriba el LLM, por rara que sea, vuelve a caer dentro, con la misma «latitud» que un juego corriente.

<figure class="lg-fig">
<svg viewBox="0 0 600 320" role="img" aria-label="Los textos ocupan un casquete estrecho de la esfera. Un punto lejano queda fuera del casquete y la ficha decodificada vuelve a caer dentro, junto a los vecinos que se le mostraron; un hueco interno sí queda dentro.">
<circle cx="250" cy="170" r="130" fill="none" stroke="rgba(255,255,255,0.18)" stroke-width="1.4"/>
<path d="M140.5,100 A130,130 0 0,1 359.5,100 Z" fill="rgba(45,212,191,0.12)" stroke="#2dd4bf" stroke-width="1.2"/>
<g fill="#94a3b8">
<circle cx="190" cy="88" r="3"/><circle cx="210" cy="72" r="3"/><circle cx="232" cy="90" r="3"/><circle cx="250" cy="60" r="3"/><circle cx="268" cy="84" r="3"/><circle cx="292" cy="68" r="3"/><circle cx="215" cy="95" r="3"/><circle cx="245" cy="78" r="3"/><circle cx="175" cy="96" r="3"/><circle cx="305" cy="92" r="3"/><circle cx="278" cy="56" r="3"/><circle cx="228" cy="62" r="3"/>
</g>
<g fill="#e2e8f0"><circle cx="330" cy="88" r="3.6"/><circle cx="342" cy="96" r="3.6"/><circle cx="322" cy="96" r="3.6"/></g>
<circle cx="262" cy="96" r="5" fill="none" stroke="#fbbf24" stroke-width="1.6"/>
<path d="M342,255 l4,9 10,1 -7.5,6.5 2.5,10 -9,-5.5 -9,5.5 2.5,-10 -7.5,-6.5 10,-1z" fill="#f59e0b"/>
<circle cx="334" cy="84" r="5" fill="#2dd4bf"/>
<path d="M340,252 C380,190 372,130 338,92" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5 4"/>
<g font-size="12">
<text x="250" y="30" fill="#5eead4" text-anchor="middle">el casquete donde viven los textos</text>
<text x="250" y="46" fill="#94a3b8" text-anchor="middle" font-size="10.5">dos juegos: cos 0,41 · dos direcciones al azar: 0 ± 0,03</text>
<text x="398" y="270" fill="#fbbf24">punto FAR</text>
<text x="398" y="286" fill="#94a3b8" font-size="10.5">lejos de todo (máx. cos 0,046)</text>
<text x="398" y="160" fill="#5eead4">la ficha decodificada</text>
<text x="398" y="176" fill="#94a3b8" font-size="10.5">vuelve al casquete, junto a</text>
<text x="398" y="190" fill="#94a3b8" font-size="10.5">los vecinos que vio (blancos)</text>
<text x="160" y="140" fill="#fbbf24" font-size="11">hueco GAP</text>
<path d="M215,135 L257,101" stroke="#fbbf24" stroke-width="1" fill="none"/>
</g>
</svg>
<figcaption>Esquema, no a escala. Los puntos FAR caen fuera de la región donde existe texto; los GAP caen dentro, en un hueco entre juegos.</figcaption>
</figure>

## El texto cae donde están los vecinos, no donde está el punto

Al mirar dónde caían las fichas FAR vi algo más: estaban mucho más cerca de los 8 vecinos que se le enseñaban al LLM (coseno 0,63–0,72 con su centroide) que del propio punto. En patentes pasó en el 100 % de los casos. Pero eso era una correlación, y podía tener otra explicación: quizá los vecinos simplemente son lo más parecido al punto que hay.

Así que hice la prueba causal. Mismo punto, misma nota de coseno, y solo cambio una cosa: los vecinos que ve el LLM. Pueden ser los verdaderos, los de otro punto distinto, o ninguno. Lo repetí en Steam y arXiv, con dos generadores (gpt-6-luna y Claude Sonnet) y en REAL, GAP y FAR, 20 puntos por condición, con las reglas de decisión escritas antes de lanzar nada.

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

El resultado fue el mismo en las 12 combinaciones. Cambiar los vecinos arrastra la ficha hacia los vecinos que ve. Y en FAR, lo poco que la ficha se acercaba al punto (0,02–0,07 con los vecinos verdaderos) desaparece en cuanto le quitas o le cambias los vecinos: se queda en −0,02/−0,01. **La nota de coseno por sí sola no acerca el texto a un punto lejano. Lo que el LLM sabe hacer es escribir algo parecido a lo que le enseñas.** La fórmula sencilla con la que yo lo describía (aterrizaje proporcional al centroide de los vecinos) solo se cumple con precisión en REAL; en FAR y en la mayoría de GAP es aproximada. El efecto es causal; la ley, solo aproximada.

## Lo que sí funciona: pedirlo sin mapa

Los huecos internos (GAP) sí se alcanzan: la ficha llega a 0,48–0,55 del punto, lo mismo que el mejor juego existente. Pero no son más nuevos. Los jueces les dieron una novedad de 4,9, por debajo de INTERP (5,5) con los seis generadores. Un hueco entre juegos se rellena con algo que se parece a los juegos de alrededor.

Lo más novedoso para los jueces fue lo que no usaba el mapa: PLAIN, simplemente pedir «un juego nuevo», con una novedad de 7,8. En todos los generadores PLAIN superaba al mejor brazo guiado por entre 1,1 y 2,6 puntos.

Hasta que leí las fichas seguidas. Claude Sonnet llamó a 45 de sus 50 juegos «Tidewright» algo. Luna, a través de Codex, escribió 46 museos de 50. Yo lo vi enseguida («otro museo… cansino»); los jueces no, porque puntuaban cada ficha por separado y nunca vieron dos juntas. Cada idea era nueva frente al catálogo, pero el generador repetía siempre la misma idea.

<figure class="lg-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Parecido medio entre las 50 ideas de cada generador. PLAIN con Sonnet llega a 0,86 y con luna vía Codex a 0,81, muy por encima de 50 juegos reales al azar (0,40) y de los brazos guiados (0,35-0,49).">
<g font-size="11.5" fill="#e2e8f0" text-anchor="end">
<text x="200" y="45">PLAIN · Sonnet</text><text x="200" y="75">PLAIN · luna vía Codex</text><text x="200" y="105">PLAIN · gpt-6.1-sol</text><text x="200" y="135">PLAIN · luna (API)</text><text x="200" y="165">PLAIN · Haiku</text><text x="200" y="195">PLAIN · Opus</text><text x="200" y="225">50 juegos reales al azar</text><text x="200" y="255">brazos guiados</text>
</g>
<g fill="#f59e0b"><rect x="210" y="34" width="241.9" height="15"/><rect x="210" y="64" width="227.1" height="15"/></g>
<g fill="#b45309"><rect x="210" y="94" width="176.9" height="15"/><rect x="210" y="124" width="160.7" height="15"/><rect x="210" y="154" width="159.3" height="15"/><rect x="210" y="184" width="145.6" height="15"/></g>
<rect x="210" y="214" width="113.1" height="15" fill="#64748b"/>
<rect x="308" y="244" width="39.2" height="15" fill="#2dd4bf"/>
<g font-size="10.5" fill="#94a3b8"><text x="457" y="46">0,86 · 45/50 «Tidewright»</text><text x="443" y="76">0,81 · 46/50 museos</text><text x="393" y="106">0,63</text><text x="377" y="136">0,57</text><text x="375" y="166">0,57</text><text x="362" y="196">0,52</text><text x="329" y="226">0,40</text><text x="353" y="256">0,35–0,49</text></g>
<line x1="210" y1="25" x2="210" y2="265" stroke="rgba(255,255,255,0.25)"/>
<text x="300" y="288" fill="#94a3b8" font-size="10.5" text-anchor="middle">coseno mediano entre pares de ideas del mismo generador (más alto = más repetidas)</text>
</svg>
<figcaption>Pedir sin mapa da las ideas más nuevas una a una, pero dos generadores repiten casi siempre la misma. Enseñándole sus ideas anteriores (PLAIND) la repetición desaparece.</figcaption>
</figure>

Lo arreglé con una variante, PLAIND, en la que el modelo ve los títulos que ya ha propuesto. La diversidad se acerca a la de los brazos guiados y la novedad sigue siendo la más alta: en patentes, PLAIND supera a INTERP por entre 2 y casi 5 puntos.

También puntué yo una muestra, y mi novedad y la de los jueces no se parecen tanto como esperaba. En patentes les doy a todos los brazos entre 1,2 y 3 puntos menos que los jueces, y a FAR 3 menos. A 3 de las 4 patentes FAR que puntué les respondí «sí, conozco algo que hace esto»; de una GAP escribí que era «un recommendation system de toda la vida». Creo que medimos cosas distintas: los jueces premian lo específico y poco familiar frente a los cinco vecinos que ven, y yo me pregunto si el concepto ya existe.

## ¿Y si buscamos de verdad un texto coherente lejos?

Todo lo anterior podía tener una salida: quizá el LLM no llega a los puntos lejanos porque no busca bien, no porque no haya nada. Así que busqué con más fuerza: una búsqueda en GPU que optimiza el coseno directamente, sin vecinos, cuyos textos luego reescribían Claude o Codex para hacerlos legibles, con solo el coseno como pista. Dos jueces tenían que aceptar el texto como coherente. Antes de mirar los puntos lejanos comprobé que el método funcionaba: recuperaba los 10 juegos (y los 10 artículos) escondidos de REAL, en el 1 % más parecido del corpus.

En arXiv mi objeción se sostiene: en el 90 % de los puntos FAR el mejor texto coherente no pasa del artículo existente más cercano. En Steam no del todo: en un 25 % de los puntos el texto coherente sí supera al juego más cercano por más de 0,05 (un 15 % si exijo además el visto bueno de un tercer juez que no escribió ni filtró nada de lo que juzgaba). Así que salir un poco más allá de lo que existe es posible.

<figure class="lg-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Escala del coseno de 0 a 1. El mejor juego existente queda a 0,042 de un punto FAR y el mejor texto coherente a 0,07, como mucho 0,14; un juego real escondido se recupera a 0,84 y el punto está en 1.">
<line x1="40" y1="60" x2="560" y2="60" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>
<g font-size="10" fill="#94a3b8" text-anchor="middle"><text x="40" y="78">0</text><text x="300" y="78">0,5</text><text x="560" y="78">1</text></g>
<rect x="40" y="52" width="104" height="16" fill="none" stroke="#64748b" stroke-dasharray="3 3"/>
<circle cx="477.8" cy="60" r="5" fill="#2dd4bf"/><text x="477.8" y="96" fill="#5eead4" font-size="11" text-anchor="middle">REAL: 0,84</text>
<path d="M560,48 l3,7 8,1 -6,5 2,8 -7,-4 -7,4 2,-8 -6,-5 8,-1z" fill="#f59e0b"/><text x="548" y="35" fill="#fbbf24" font-size="11" text-anchor="end">el punto: 1</text>
<path d="M92,68 L40,132 M144,68 L560,132" stroke="#64748b" stroke-dasharray="3 3" fill="none"/>
<line x1="40" y1="150" x2="560" y2="150" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>
<g font-size="10" fill="#94a3b8" text-anchor="middle"><text x="40" y="168">0</text><text x="300" y="168">0,1</text><text x="560" y="168">0,2</text></g>
<line x1="149" y1="140" x2="149" y2="160" stroke="#94a3b8" stroke-width="2"/>
<text x="149" y="128" fill="#e2e8f0" font-size="11" text-anchor="middle">mejor juego existente 0,042</text>
<circle cx="219" cy="150" r="5" fill="#2dd4bf"/>
<text x="219" y="190" fill="#5eead4" font-size="11" text-anchor="middle">mediana coherente 0,07</text>
<rect x="274" y="144" width="130" height="12" rx="3" fill="rgba(45,212,191,0.35)" stroke="#2dd4bf"/>
<text x="339" y="128" fill="#5eead4" font-size="11" text-anchor="middle">las que escapan: 0,09–0,14</text>
<text x="300" y="218" fill="#94a3b8" font-size="10.5" text-anchor="middle">zoom de 0 a 0,2 · Steam, puntos FAR, búsqueda en GPU + reescritura</text>
</svg>
<figcaption>Más allá de cualquier juego existente no es lo mismo que en el punto. Incluso los textos coherentes que escapan se quedan a 0,09–0,14 de un punto que está en 1.</figcaption>
</figure>

Pero hay que mirar la escala. Esos textos que escapan se quedan a un coseno de 0,09–0,14 de su punto, cuando el juego más cercano estaba a 0,04 y el punto mismo está en 1. «Más lejos que cualquier juego» no es «en el punto». Esto matiza mi objeción, y creo que la mejora: no es que sea imposible salir del mapa, es que lo que se alcanza está muy lejos de lo que se pidió, y lo que se lee sigue siendo un juego normal.

## ¿Se puede demostrar?

Quise ir más allá de los datos y, con ayuda de gpt-6-astra, intenté demostrar una cota: hasta dónde puede acercarse un texto coherente a un punto lejano. Ninguna cota aguantó. Cada propuesta caía con los datos que ya teníamos: la coherencia no es suave (los jueces dan veredictos opuestos a fichas que solo cambian en una palabra), y ningún umbral de probabilidad de un modelo de lenguaje separa lo que los jueces aceptan de lo que rechazan.

Así que le di la vuelta: ¿se puede demostrar que no hay cota? En sentido estricto no, porque con textos de longitud limitada el conjunto es finito y siempre hay un máximo. Lo que sí quedó demostrado, y comprobado en Lean, es que sin una regla que diga qué cuenta como coherente nadie puede certificar un techo más ajustado que el trivial, por muchas consultas que haga, y que en general el problema es computacionalmente difícil. Todas las reglas candidatas que probamos cayeron con los datos.

## En resumen

- **Los huecos internos se alcanzan, pero no son nuevos**: se rellenan con algo parecido a lo que los rodea.
- **Los puntos lejanos no se alcanzan**: el texto vuelve al casquete donde están los textos, junto a los vecinos que se le enseñan. Y eso es causal.
- **La novedad vino de pedirla**, no de la geometría vacía, siempre que el modelo vea lo que ya ha propuesto.

El tuit acierta en algo: hay rincones del mapa sin explorar a los que se puede llegar. Pero un punto lejos de todo no es una idea esperando a ser escrita; casi siempre es un sitio donde no cabe ningún texto.

Me queda la otra mitad de la pregunta, la que no se puede medir con un catálogo: ¿puede un modelo llegar a una idea que de verdad no existía? Es la prueba de Einstein que propuso Demis Hassabis: entrenar un modelo solo con lo que se sabía antes de 1911 y ver si llega a la relatividad general. Esa será la segunda parte, con un generador con fecha de corte controlada.
