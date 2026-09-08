---
title: "Navier–Stokes explota, y la explosión es un vórtice que se puede dibujar"
description: "OpenAI ha publicado una demostración verificada en Lean de que las ecuaciones de Navier–Stokes en 3D pueden desarrollar una singularidad en tiempo finito. Cuatro cosas que los titulares se saltan: el modelo no era Astra, la rotura ocurre justo donde el fluido deja de ser un fluido, la solución es una patinadora girando, y una estantería de teoremas condicionales acaba de cambiar de estado."
pubDate: 2026-09-09
tags: ["IA", "Matemáticas", "Agentes", "Investigación", "OpenAI"]
lang: es
translationKey: navier-stokes-blows-up
heroImage: "/blog/navier-stokes-blows-up.png"
linkedinImage: /blog/navier-stokes-blows-up-vortex.png
linkedinLinks:
  - label: "Anuncio de OpenAI"
    url: "https://openai.com/index/navier-stokes-solution/"
  - label: "El paper"
    url: "https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf"
  - label: "Formalización en Lean"
    url: "https://github.com/openai/NavierStokesAndEuler"
---

El 8 de septiembre OpenAI [publicó una demostración](https://openai.com/index/navier-stokes-solution/) de que las ecuaciones de Navier–Stokes incompresibles en tres dimensiones pueden desarrollar una singularidad en tiempo finito: un fluido suave, que parte del reposo bajo una fuerza externa suave, cuya velocidad crece sin límite mientras su energía total se mantiene finita. La demostración viene como un [paper de 165 páginas](https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf) y una [formalización en Lean](https://github.com/openai/NavierStokesAndEuler). Es la resolución negativa del problema del milenio de Navier–Stokes tal y como lo escribió el Instituto Clay, noventa años después de Leray.

La cobertura ha ido sobre todo del millón de dólares y de quién llegó primero. Importan más cuatro cosas, y ninguna cabe en un titular: qué modelo lo hizo, qué es exactamente lo que "se rompe" y para quién, por qué la solución se puede dibujar en una servilleta, y qué pasa con los teoremas que llevaban décadas esperando esta respuesta.

<style>
.ns-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.ns-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.ns-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## No fue Astra

La demostración no salió de GPT-6 Astra, el modelo que OpenAI había lanzado cinco días antes. Salió de un modelo interno que lleva entrenándose desde el 28 de agosto y que OpenAI describe como "significativamente más capaz que GPT-6 Astra", con "un rendimiento sin precedentes en nuestros benchmarks, incluidas las matemáticas". El entrenamiento sigue en marcha. OpenAI no lo llama un modelo de matemáticas; el salto que reporta es en sus benchmarks en general, con las matemáticas entre ellos. El único papel de Astra en la historia fue el último paso: produjo la formalización y la verificación en Lean en 17 horas.

Lo que corrió encima de ese modelo es más interesante que el modelo, al menos para quien construye sistemas de agentes. Fue un enjambre:

| | |
|---|---|
| Agentes concurrentes en el grupo de Navier–Stokes | del orden de 10.000 |
| Herramientas | una copia cacheada de internet, ejecución de código |
| Tiempo hasta el resultado | unas 88 horas (del 1 al 5 de septiembre) |
| Mensajes intercambiados | 2,7 millones |
| Tokens de salida | unos 130.000 millones |
| Formalización y verificación en Lean | 17 horas, GPT-6 Astra |
| En todos los problemas intentados | 4,9 millones de mensajes, 300.000 millones de tokens |

Destacan tres decisiones de diseño. Primera: no le pidieron al enjambre que *resolviera* Navier–Stokes. Lo dividieron en grupos y a cada uno le dieron uno de los cuatro enunciados del problema oficial: A y B (las soluciones siempre se mantienen suaves) a unos grupos, C y D (pueden romperse) a otros. Nadie apostó por una dirección. Segunda: a grupos aparte les dieron problemas "más fáciles", y uno de ellos cayó primero: las ecuaciones de Euler sin forzamiento, la misma pregunta con la viscosidad quitada, resueltas por unos 100 agentes en unas 50 horas. Esa demostración se pasó entonces como prompt a los grupos de Navier–Stokes, y se retiraron agentes del resto de problemas del milenio para ponerlos en este. Tercera: los grupos solo podían hablar dentro de sí mismos; la polinización cruzada entre grupos la hizo Codex, usado para consolidar las ideas más útiles de cada grupo en prompts de seguimiento. El grupo que encontró la demostración fue guiado así.

<figure class="ns-fig">
<svg viewBox="0 0 600 190" role="img" aria-label="Cronología del esfuerzo de OpenAI en Navier–Stokes: el entrenamiento del modelo interno empieza el 28 de agosto, un enjambre de unos diez mil agentes se lanza el 1 de septiembre sobre todos los problemas del milenio, la cuestión de Euler sin forzamiento cae primero tras unas cincuenta horas, los agentes se desplazan a Navier–Stokes con la demostración de Euler como prompt, el resultado llega el 5 de septiembre tras ochenta y ocho horas, la verificación en Lean con GPT-6 Astra lleva diecisiete horas más, y la demostración se publica el 8 de septiembre">
  <defs>
    <marker id="ns-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#64748b"/>
    </marker>
  </defs>
  <line x1="28" y1="100" x2="572" y2="100" stroke="#64748b" stroke-width="2" marker-end="url(#ns-ar)"/>
  <g fill="#1a1a24" stroke="#94a3b8" stroke-width="2">
    <circle cx="60" cy="100" r="6"/>
    <circle cx="170" cy="100" r="6"/>
    <circle cx="275" cy="100" r="6"/>
    <circle cx="400" cy="100" r="6" stroke="#2dd4bf"/>
    <circle cx="470" cy="100" r="6"/>
    <circle cx="545" cy="100" r="6" stroke="#f59e0b"/>
  </g>
  <g fill="#2dd4bf"><circle cx="400" cy="100" r="3"/></g>
  <g fill="#f59e0b"><circle cx="545" cy="100" r="3"/></g>
  <g text-anchor="middle" font-size="10.5" fill="#e2e8f0">
    <text x="60" y="62" font-weight="700">28 ago</text>
    <text x="60" y="76" fill="#94a3b8">el modelo interno</text>
    <text x="60" y="88" fill="#94a3b8">empieza a entrenar</text>
    <text x="170" y="128" font-weight="700">1 sep</text>
    <text x="170" y="142" fill="#94a3b8">~10.000 agentes sobre</text>
    <text x="170" y="154" fill="#94a3b8">todos los problemas del milenio</text>
    <text x="275" y="62" font-weight="700">~50 h después</text>
    <text x="275" y="76" fill="#94a3b8">cae Euler sin forzamiento</text>
    <text x="275" y="88" fill="#94a3b8">(~100 agentes)</text>
    <text x="400" y="128" font-weight="700" fill="#5eead4">5 sep · 88 h</text>
    <text x="400" y="142" fill="#94a3b8">demostración de Navier–Stokes</text>
    <text x="400" y="154" fill="#94a3b8">2,7 M mensajes · 130.000 M tokens</text>
    <text x="470" y="62" font-weight="700">6 sep</text>
    <text x="470" y="76" fill="#94a3b8">verificado en Lean</text>
    <text x="470" y="88" fill="#94a3b8">17 h, GPT-6 Astra</text>
    <text x="545" y="128" font-weight="700" fill="#fbbf24">8 sep</text>
    <text x="545" y="142" fill="#94a3b8">publicado</text>
  </g>
  <path d="M305,100 C345,100 345,40 362,40 L382,40 C397,40 397,90 400,94" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="4 3"/>
  <rect x="290" y="22" width="150" height="14" fill="#1a1a24"/>
  <text x="365" y="33" text-anchor="middle" font-size="9.5" fill="#fbbf24">la prueba de Euler pasa como prompt; agentes desplazados</text>
</svg>
<figcaption>La cronología que reporta OpenAI. Astra aparece una vez, en el paso de verificación. El resultado de Euler sin forzamiento, aquí un peldaño, habría sido un resultado mayor por sí solo.</figcaption>
</figure>

Ya escribí sobre [lo que se dicen los agentes entre sí](/es/blog/what-agents-say-to-each-other) cuando se les deja hablar; 2,7 millones de mensajes es esa misma pregunta a una escala en la que leer la transcripción no es una opción, y en la que la única capa legible para un humano es el paso de consolidación.

## Qué se ha demostrado, exactamente

El teorema es lo bastante corto como para enunciarlo. Para toda viscosidad positiva existe una fuerza externa suave, de soporte compacto en espacio y tiempo, tal que el fluido que parte del reposo bajo esa fuerza es suave para todo tiempo anterior a 1, tiene energía cinética acotada en todo momento, y tiene una velocidad máxima que tiende a infinito cuando el tiempo se acerca a 1. En consecuencia no existe una solución suave y de energía finita para todo tiempo con esa fuerza y esa condición inicial.

Eso es el enunciado C de la [descripción oficial del problema por Fefferman](https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf), y el soporte compacto regala el enunciado D, la versión periódica. El problema oficial queda resuelto si se demuestra *cualquiera* de cuatro enunciados, y los cuatro no son simétricos:

<figure class="ns-fig">
<svg viewBox="0 0 600 236" role="img" aria-label="Los cuatro enunciados del problema de Navier–Stokes del Instituto Clay como una cuadrícula de dos por dos: las filas son el espacio entero y la caja periódica, las columnas son regularidad con fuerza cero y rotura con una fuerza suave permitida. Los enunciados A y B, regularidad sin fuerza, siguen abiertos. Los enunciados C y D, rotura bajo una fuerza suave, se demostraron en septiembre de 2026">
  <g font-size="11" fill="#94a3b8" text-anchor="middle">
    <text x="245" y="26" font-weight="700" fill="#e2e8f0">Regularidad</text>
    <text x="245" y="40" font-size="10">todo estado inicial suave, sin fuerza (f ≡ 0)</text>
    <text x="455" y="26" font-weight="700" fill="#e2e8f0">Rotura</text>
    <text x="455" y="40" font-size="10">algún estado inicial, alguna fuerza suave f</text>
  </g>
  <g font-size="11" fill="#e2e8f0" text-anchor="end">
    <text x="130" y="96" font-weight="700">espacio entero ℝ³</text>
    <text x="130" y="176" font-weight="700">caja periódica ℝ³/ℤ³</text>
  </g>
  <g>
    <rect x="145" y="60" width="200" height="70" rx="8" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.18)" stroke-width="1.5" stroke-dasharray="5 4"/>
    <rect x="145" y="140" width="200" height="70" rx="8" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.18)" stroke-width="1.5" stroke-dasharray="5 4"/>
    <rect x="355" y="60" width="200" height="70" rx="8" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="2"/>
    <rect x="355" y="140" width="200" height="70" rx="8" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="2"/>
  </g>
  <g text-anchor="middle">
    <text x="245" y="92" font-size="24" font-weight="700" fill="#94a3b8">A</text>
    <text x="245" y="112" font-size="10.5" fill="#94a3b8">sigue abierto</text>
    <text x="245" y="172" font-size="24" font-weight="700" fill="#94a3b8">B</text>
    <text x="245" y="192" font-size="10.5" fill="#94a3b8">sigue abierto</text>
    <text x="455" y="92" font-size="24" font-weight="700" fill="#5eead4">C</text>
    <text x="455" y="112" font-size="10.5" fill="#5eead4">demostrado · sep 2026</text>
    <text x="455" y="172" font-size="24" font-weight="700" fill="#5eead4">D</text>
    <text x="455" y="192" font-size="10.5" fill="#5eead4">demostrado · sep 2026 (se sigue de C)</text>
  </g>
  <text x="300" y="228" text-anchor="middle" font-size="10" fill="#64748b">Demostrar cualquiera de los cuatro resuelve el problema del milenio. A y B habrían sido un sí; C y D son un no.</text>
</svg>
<figcaption>A y B preguntan si un fluido que se deja solo puede romperse; eso nadie lo sabe todavía. C y D preguntan si puede romperse un fluido empujado por una fuerza suave; ahora sí puede.</figcaption>
</figure>

La fuerza es la parte con la que hay que ser honesto. No es la gravedad, y no se eligió primero. El paper lo dice sin rodeos: para cualquier flujo incompresible se puede *definir* la fuerza como el residuo que dejen las ecuaciones, y entonces las ecuaciones se cumplen por construcción. Toda la dificultad está en elegir un flujo que explote mientras ese residuo se mantiene suave, hasta el instante singular incluido, con todas sus derivadas. El vórtice de fondo por sí solo deja un residuo que diverge; el paper lo cancela con pulsos espacialmente oscilatorios y después elimina los errores restantes orden a orden. Para eso son las 165 páginas. Y por eso algunos matemáticos llamarán a esto una resolución del problema tal y como está escrito y otros lo llamarán un resquicio en el problema tal y como está escrito. Los dos tienen razón: el enunciado está cerrado, y la pregunta que la mayoría entiende por él, si un fluido al que nadie empuja puede explotar, está exactamente igual de abierta que la semana pasada. OpenAI dice que no reclamará el premio.

## Donde el fluido deja de ser un fluido

Las ecuaciones de Navier–Stokes son la segunda ley de Newton aplicada a un continuo. En ellas no hay moléculas; una "parcela de fluido" es un punto matemático con una velocidad, y las ecuaciones describen cómo esas velocidades se empujan unas a otras. Todo aquello para lo que se usan, diseño de aviones, predicción meteorológica, flujo sanguíneo, se apoya en que esa imagen de continuo sea suficientemente buena.

Una singularidad es que las ecuaciones salgan de esa imagen desde dentro. En la construcción, el núcleo del vórtice tiene un radio que se encoge como la raíz cuadrada del tiempo que queda, y una velocidad máxima que crece algo más rápido que uno partido por esa raíz. Mucho antes de que el tiempo restante llegue a cero, el núcleo es más estrecho que el recorrido libre medio de las moléculas del aire, la velocidad ha superado la del sonido, y la incompresibilidad, la hipótesis de que el fluido no se puede comprimir, ya es falsa. En ese punto el continuo no tiene nada que decir. Para seguir modelando el sistema habría que seguir las partículas una a una: teoría cinética, dinámica molecular, el nivel de descripción que todavía no se haya rendido. Las ecuaciones no predicen un fluido infinitamente rápido. Predicen su propia frontera.

¿A quién afecta esto? A casi nadie de los que las usan. La singularidad necesita una fuerza diseñada para cancelar cuatro términos divergentes a todos los órdenes en un único punto del espacio y del tiempo; nada en un ala, en un huracán o en una arteria la proporciona. Los solvers numéricos ya regularizan todo lo que queda por debajo de la escala de la malla. Y la energía cinética del núcleo de hecho *decrece* hasta cero cuando la singularidad se acerca, así que todo el episodio lleva una energía que se desvanece en un volumen que se desvanece. Nadie vuelve a lanzar una simulación mañana. Mi lectura es que la consecuencia práctica para la inmensa mayoría de la mecánica de fluidos es nula, y me sorprendería que algún código de ingeniería cambiase por esto. Lo que ha cambiado es el estado del modelo: creíamos que las ecuaciones eran una descripción cerrada y autoconsistente que simplemente se aplicaba a veces fuera de su rango. Ahora sabemos que las ecuaciones contienen en sí mismas la salida, y que se las puede llevar hasta ella con un empujón suave.

## La parte intuitiva

La construcción es un vórtice que se enrosca hacia dentro mientras se estira a lo largo de su eje. La propia figura del paper son tres bocetos de un núcleo giratorio que se va haciendo más fino y más alto; cualquiera que haya visto el agua irse por un desagüe la puede leer. Aquí está el mecanismo, en los términos del propio paper, redibujado:

<figure class="ns-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Tres instantáneas del vórtice que explota en tiempos sucesivos. El fluido se enrosca hacia un eje vertical y sale a lo largo del eje por encima y por debajo de un plano divisorio. De una instantánea a la siguiente el radio del núcleo se encoge más rápido que su altura, la rotación se acelera, y la velocidad máxima crece sin límite mientras la energía cinética del núcleo tiende a cero">
  <defs>
    <marker id="ns-ab" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#f59e0b"/>
    </marker>
    <marker id="ns-at" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#2dd4bf"/>
    </marker>
  </defs>
  <!-- panel 1 -->
  <g transform="translate(110,160)">
    <line x1="0" y1="-118" x2="0" y2="118" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
    <ellipse cx="0" cy="0" rx="78" ry="32.8" fill="rgba(45,212,191,0.07)" stroke="none"/>
    <path d="M78.0,0.0 L77.4,3.1 L76.1,6.1 L74.1,9.0 L71.5,11.9 L68.3,14.6 L64.5,17.2 L60.1,19.6 L55.3,21.8 L50.0,23.8 L44.2,25.6 L38.2,27.1 L31.8,28.4 L25.2,29.4 L18.4,30.2 L11.6,30.7 L4.6,30.9 L-2.3,30.8 L-9.2,30.5 L-15.9,29.8 L-22.4,29.0 L-28.7,27.9 L-34.7,26.5 L-40.3,24.9 L-45.5,23.1 L-50.3,21.1 L-54.6,19.0 L-58.4,16.7 L-61.7,14.2 L-64.3,11.7 L-66.4,9.1 L-67.9,6.4 L-68.7,3.6 L-69.0,0.9 L-68.6,-1.8 L-67.6,-4.5 L-66.0,-7.1 L-63.9,-9.7 L-61.2,-12.1 L-58.0,-14.4 L-54.3,-16.6 L-50.1,-18.6 L-45.5,-20.4 L-40.6,-22.0 L-35.4,-23.4 L-29.8,-24.6 L-24.1,-25.6 L-18.2,-26.3 L-12.2,-26.8 L-6.1,-27.0 L-0.0,-27.0 L6.0,-26.8 L12.0,-26.3 L17.7,-25.6 L23.3,-24.7 L28.6,-23.6 L33.6,-22.2 L38.3,-20.7 L42.6,-19.0 L46.4,-17.2 L49.9,-15.2 L52.8,-13.1 L55.3,-10.9 L57.2,-8.7 L58.6,-6.3 L59.5,-4.0 L59.9,-1.6 L59.7,0.8 L59.0,3.1 L57.7,5.4 L56.0,7.6 L53.8,9.8 L51.1,11.8 L48.0,13.7 L44.5,15.5 L40.7,17.1 L36.5,18.5 L32.0,19.8 L27.3,20.9 L22.4,21.8 L17.4,22.4 L12.2,22.9 L7.0,23.2 L1.7,23.2 L-3.5,23.1 L-8.6,22.7 L-13.6,22.2 L-18.4,21.4 L-23.0,20.5 L-27.3,19.4 L-31.4,18.2 L-35.2,16.7 L-38.6,15.2 L-41.6,13.5 L-44.2,11.8 L-46.4,9.9 L-48.2,8.0 L-49.5,6.0 L-50.3,4.0 L-50.7,2.0 L-50.7,0.0 L-50.2,-2.0 L-49.3,-3.9 L-47.9,-5.8 L-46.1,-7.7 L-44.0,-9.4 L-41.4,-11.0 L-38.6,-12.6 L-35.4,-13.9 L-31.9,-15.2 L-28.2,-16.3 L-24.3,-17.2 L-20.2,-18.0 L-16.0,-18.6 L-11.7,-19.1 L-7.3,-19.3 L-2.9,-19.4 L1.4,-19.3 L5.7,-19.1 L9.9,-18.7 L14.0,-18.1 L17.9,-17.3 L21.5,-16.4 L25.0,-15.4 L28.1,-14.3 L31.0,-13.0 L33.6,-11.7 L35.8,-10.2 L37.7,-8.7 L39.3,-7.1 L40.4,-5.5 L41.2,-3.9 L41.6,-2.2 L41.7,-0.6 L41.3,1.1 L40.6,2.7 L39.6,4.3 L38.2,5.8 L36.5,7.2 L34.5,8.6 L32.2,9.8 L29.6,11.0 L26.9,12.0 L23.9,12.9 L20.7,13.7 L17.4,14.4 L14.0,14.9 L10.6,15.3 L7.0,15.5 L3.5,15.6 L0.0,15.6 L-3.5,15.4 L-6.8,15.1 L-10.1,14.6 L-13.2,14.0 L-16.2,13.4 L-19.0,12.6 L-21.5,11.7 L-23.9,10.7 L-25.9,9.6 L-27.8,8.5 L-29.3,7.3 L-30.6,6.0 L-31.5,4.8 L-32.2,3.5 L-32.5,2.2 L-32.6,0.9 L-32.4,-0.4 L-31.9,-1.7 L-31.1,-2.9 L-30.0,-4.1 L-28.7,-5.2 L-27.2,-6.3 L-25.5,-7.3 L-23.5,-8.2 L-21.4,-9.0 L-19.1,-9.7 L-16.7,-10.3 L-14.2,-10.8 L-11.6,-11.2 L-8.9,-11.5 L-6.2,-11.7 L-3.5,-11.8 L-0.9,-11.8 L1.7,-11.6 L4.3,-11.4 L6.8,-11.1 L9.1,-10.6 L11.4,-10.1 L13.4,-9.5 L15.4,-8.9 L17.1,-8.1 L18.6,-7.4 L20.0,-6.5 L21.1,-5.6 L22.1,-4.7 L22.8,-3.8 L23.3,-2.8 L23.5,-1.9 L23.6,-0.9 L23.4,-0.0" fill="none" stroke="#2dd4bf" stroke-width="2.0" stroke-linecap="round" marker-end="url(#ns-at)"/>
    <path d="M-14,-38 L-14,-98" fill="none" stroke="#f59e0b" stroke-width="2.2" marker-end="url(#ns-ab)"/>
    <path d="M14,38 L14,98" fill="none" stroke="#f59e0b" stroke-width="2.2" marker-end="url(#ns-ab)"/>
    <line x1="-78" y1="108" x2="78" y2="108" stroke="#64748b" stroke-width="1"/>
    <line x1="-78" y1="104" x2="-78" y2="112" stroke="#64748b" stroke-width="1"/>
    <line x1="78" y1="104" x2="78" y2="112" stroke="#64748b" stroke-width="1"/>
    <text x="0" y="122" text-anchor="middle" font-size="9.5" fill="#94a3b8">radio</text>
    <text x="0" y="140" text-anchor="middle" font-size="11" font-weight="700" fill="#e2e8f0">t₁</text>
  </g>
  <!-- panel 2 -->
  <g transform="translate(300,160)">
    <line x1="0" y1="-118" x2="0" y2="118" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
    <ellipse cx="0" cy="0" rx="50" ry="21.0" fill="rgba(45,212,191,0.07)" stroke="none"/>
    <path d="M50.0,0.0 L49.6,2.0 L48.8,3.9 L47.5,5.8 L45.8,7.6 L43.8,9.4 L41.3,11.0 L38.5,12.6 L35.4,14.0 L32.0,15.3 L28.4,16.4 L24.5,17.4 L20.4,18.2 L16.2,18.9 L11.8,19.3 L7.4,19.7 L3.0,19.8 L-1.5,19.7 L-5.9,19.5 L-10.2,19.1 L-14.4,18.6 L-18.4,17.9 L-22.2,17.0 L-25.8,16.0 L-29.2,14.8 L-32.3,13.5 L-35.0,12.2 L-37.4,10.7 L-39.5,9.1 L-41.2,7.5 L-42.6,5.8 L-43.5,4.1 L-44.0,2.3 L-44.2,0.6 L-44.0,-1.2 L-43.3,-2.9 L-42.3,-4.6 L-41.0,-6.2 L-39.2,-7.8 L-37.2,-9.2 L-34.8,-10.6 L-32.1,-11.9 L-29.2,-13.1 L-26.0,-14.1 L-22.7,-15.0 L-19.1,-15.8 L-15.4,-16.4 L-11.7,-16.8 L-7.8,-17.2 L-3.9,-17.3 L-0.0,-17.3 L3.9,-17.2 L7.7,-16.9 L11.4,-16.4 L14.9,-15.8 L18.3,-15.1 L21.5,-14.3 L24.5,-13.3 L27.3,-12.2 L29.8,-11.0 L32.0,-9.8 L33.8,-8.4 L35.4,-7.0 L36.7,-5.5 L37.6,-4.1 L38.1,-2.5 L38.4,-1.0 L38.3,0.5 L37.8,2.0 L37.0,3.5 L35.9,4.9 L34.5,6.3 L32.8,7.6 L30.8,8.8 L28.5,9.9 L26.1,11.0 L23.4,11.9 L20.5,12.7 L17.5,13.4 L14.4,13.9 L11.1,14.4 L7.8,14.7 L4.5,14.9 L1.1,14.9 L-2.2,14.8 L-5.5,14.6 L-8.7,14.2 L-11.8,13.7 L-14.7,13.1 L-17.5,12.4 L-20.1,11.6 L-22.5,10.7 L-24.7,9.7 L-26.6,8.7 L-28.3,7.6 L-29.7,6.4 L-30.9,5.1 L-31.7,3.9 L-32.3,2.6 L-32.5,1.3 L-32.5,0.0 L-32.2,-1.3 L-31.6,-2.5 L-30.7,-3.7 L-29.6,-4.9 L-28.2,-6.0 L-26.6,-7.1 L-24.7,-8.1 L-22.7,-8.9 L-20.5,-9.7 L-18.1,-10.4 L-15.6,-11.1 L-12.9,-11.6 L-10.2,-11.9 L-7.5,-12.2 L-4.7,-12.4 L-1.9,-12.4 L0.9,-12.4 L3.7,-12.2 L6.4,-12.0 L9.0,-11.6 L11.4,-11.1 L13.8,-10.5 L16.0,-9.9 L18.0,-9.2 L19.9,-8.4 L21.5,-7.5 L23.0,-6.6 L24.2,-5.6 L25.2,-4.6 L25.9,-3.5 L26.4,-2.5 L26.7,-1.4 L26.7,-0.4 L26.5,0.7 L26.1,1.7 L25.4,2.7 L24.5,3.7 L23.4,4.6 L22.1,5.5 L20.6,6.3 L19.0,7.0 L17.2,7.7 L15.3,8.3 L13.3,8.8 L11.2,9.2 L9.0,9.5 L6.8,9.8 L4.5,9.9 L2.3,10.0 L0.0,10.0 L-2.2,9.9 L-4.4,9.7 L-6.5,9.4 L-8.5,9.0 L-10.4,8.6 L-12.2,8.0 L-13.8,7.5 L-15.3,6.8 L-16.6,6.2 L-17.8,5.4 L-18.8,4.7 L-19.6,3.9 L-20.2,3.1 L-20.6,2.2 L-20.9,1.4 L-20.9,0.6 L-20.8,-0.3 L-20.4,-1.1 L-19.9,-1.9 L-19.3,-2.6 L-18.4,-3.3 L-17.4,-4.0 L-16.3,-4.7 L-15.1,-5.2 L-13.7,-5.8 L-12.2,-6.2 L-10.7,-6.6 L-9.1,-6.9 L-7.4,-7.2 L-5.7,-7.4 L-4.0,-7.5 L-2.3,-7.6 L-0.6,-7.5 L1.1,-7.5 L2.8,-7.3 L4.3,-7.1 L5.9,-6.8 L7.3,-6.5 L8.6,-6.1 L9.8,-5.7 L11.0,-5.2 L12.0,-4.7 L12.8,-4.2 L13.6,-3.6 L14.1,-3.0 L14.6,-2.4 L14.9,-1.8 L15.1,-1.2 L15.1,-0.6 L15.0,-0.0" fill="none" stroke="#2dd4bf" stroke-width="1.9" stroke-linecap="round" marker-end="url(#ns-at)"/>
    <path d="M-9,-26 L-9,-86" fill="none" stroke="#f59e0b" stroke-width="2.6" marker-end="url(#ns-ab)"/>
    <path d="M9,26 L9,86" fill="none" stroke="#f59e0b" stroke-width="2.6" marker-end="url(#ns-ab)"/>
    <text x="0" y="140" text-anchor="middle" font-size="11" font-weight="700" fill="#e2e8f0">t₂</text>
  </g>
  <!-- panel 3 -->
  <g transform="translate(490,160)">
    <line x1="0" y1="-118" x2="0" y2="118" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
    <ellipse cx="0" cy="0" rx="27" ry="11.3" fill="rgba(45,212,191,0.07)" stroke="none"/>
    <path d="M27.0,0.0 L26.8,1.1 L26.3,2.1 L25.7,3.1 L24.8,4.1 L23.6,5.1 L22.3,5.9 L20.8,6.8 L19.1,7.5 L17.3,8.2 L15.3,8.9 L13.2,9.4 L11.0,9.8 L8.7,10.2 L6.4,10.4 L4.0,10.6 L1.6,10.7 L-0.8,10.7 L-3.2,10.5 L-5.5,10.3 L-7.8,10.0 L-9.9,9.6 L-12.0,9.2 L-14.0,8.6 L-15.8,8.0 L-17.4,7.3 L-18.9,6.6 L-20.2,5.8 L-21.3,4.9 L-22.3,4.0 L-23.0,3.1 L-23.5,2.2 L-23.8,1.3 L-23.9,0.3 L-23.7,-0.6 L-23.4,-1.6 L-22.9,-2.5 L-22.1,-3.3 L-21.2,-4.2 L-20.1,-5.0 L-18.8,-5.7 L-17.3,-6.4 L-15.8,-7.1 L-14.1,-7.6 L-12.2,-8.1 L-10.3,-8.5 L-8.3,-8.8 L-6.3,-9.1 L-4.2,-9.3 L-2.1,-9.4 L-0.0,-9.4 L2.1,-9.3 L4.1,-9.1 L6.1,-8.9 L8.1,-8.6 L9.9,-8.2 L11.6,-7.7 L13.2,-7.2 L14.7,-6.6 L16.1,-6.0 L17.3,-5.3 L18.3,-4.5 L19.1,-3.8 L19.8,-3.0 L20.3,-2.2 L20.6,-1.4 L20.7,-0.5 L20.7,0.3 L20.4,1.1 L20.0,1.9 L19.4,2.6 L18.6,3.4 L17.7,4.1 L16.6,4.7 L15.4,5.4 L14.1,5.9 L12.6,6.4 L11.1,6.9 L9.5,7.2 L7.8,7.5 L6.0,7.8 L4.2,7.9 L2.4,8.0 L0.6,8.0 L-1.2,8.0 L-3.0,7.9 L-4.7,7.7 L-6.4,7.4 L-8.0,7.1 L-9.5,6.7 L-10.9,6.3 L-12.2,5.8 L-13.3,5.3 L-14.4,4.7 L-15.3,4.1 L-16.1,3.4 L-16.7,2.8 L-17.1,2.1 L-17.4,1.4 L-17.6,0.7 L-17.6,0.0 L-17.4,-0.7 L-17.1,-1.4 L-16.6,-2.0 L-16.0,-2.7 L-15.2,-3.3 L-14.3,-3.8 L-13.3,-4.3 L-12.2,-4.8 L-11.0,-5.3 L-9.8,-5.6 L-8.4,-6.0 L-7.0,-6.2 L-5.5,-6.4 L-4.0,-6.6 L-2.5,-6.7 L-1.0,-6.7 L0.5,-6.7 L2.0,-6.6 L3.4,-6.5 L4.8,-6.3 L6.2,-6.0 L7.5,-5.7 L8.6,-5.3 L9.7,-4.9 L10.7,-4.5 L11.6,-4.0 L12.4,-3.5 L13.1,-3.0 L13.6,-2.5 L14.0,-1.9 L14.3,-1.3 L14.4,-0.8 L14.4,-0.2 L14.3,0.4 L14.1,0.9 L13.7,1.5 L13.2,2.0 L12.6,2.5 L11.9,3.0 L11.1,3.4 L10.3,3.8 L9.3,4.2 L8.3,4.5 L7.2,4.7 L6.0,5.0 L4.9,5.2 L3.7,5.3 L2.4,5.4 L1.2,5.4 L0.0,5.4 L-1.2,5.3 L-2.4,5.2 L-3.5,5.1 L-4.6,4.9 L-5.6,4.6 L-6.6,4.3 L-7.5,4.0 L-8.3,3.7 L-9.0,3.3 L-9.6,2.9 L-10.1,2.5 L-10.6,2.1 L-10.9,1.6 L-11.1,1.2 L-11.3,0.7 L-11.3,0.3 L-11.2,-0.1 L-11.0,-0.6 L-10.8,-1.0 L-10.4,-1.4 L-9.9,-1.8 L-9.4,-2.2 L-8.8,-2.5 L-8.1,-2.8 L-7.4,-3.1 L-6.6,-3.4 L-5.8,-3.6 L-4.9,-3.7 L-4.0,-3.9 L-3.1,-4.0 L-2.2,-4.1 L-1.2,-4.1 L-0.3,-4.1 L0.6,-4.0 L1.5,-3.9 L2.3,-3.8 L3.2,-3.7 L3.9,-3.5 L4.7,-3.3 L5.3,-3.1 L5.9,-2.8 L6.5,-2.5 L6.9,-2.3 L7.3,-2.0 L7.6,-1.6 L7.9,-1.3 L8.1,-1.0 L8.1,-0.7 L8.2,-0.3 L8.1,-0.0" fill="none" stroke="#2dd4bf" stroke-width="1.8" stroke-linecap="round" marker-end="url(#ns-at)"/>
    <path d="M-5,-16 L-5,-74" fill="none" stroke="#f59e0b" stroke-width="3.0" marker-end="url(#ns-ab)"/>
    <path d="M5,16 L5,74" fill="none" stroke="#f59e0b" stroke-width="3.0" marker-end="url(#ns-ab)"/>
    <text x="0" y="140" text-anchor="middle" font-size="11" font-weight="700" fill="#e2e8f0">t₃ → 1</text>
  </g>
  <g font-size="10" fill="#94a3b8">
    <text x="20" y="18"><tspan fill="#5eead4">teal</tspan>: espiral hacia dentro, girando cada vez más rápido</text>
    <text x="20" y="32"><tspan fill="#fbbf24">ámbar</tspan>: salida axial por encima y por debajo del plano medio</text>
    <text x="580" y="18" text-anchor="end">τ = tiempo que queda hasta la singularidad</text>
  </g>
  <g font-size="10" fill="#94a3b8" text-anchor="middle">
    <text x="300" y="318">radio ∝ τ<tspan font-size="7" baseline-shift="super">1/2</tspan>  ·  altura ∝ τ<tspan font-size="7" baseline-shift="super">1/2−h</tspan>  ·  h &lt; 1/100  ·  velocidad máxima ∝ τ<tspan font-size="7" baseline-shift="super">−1/2−h</tspan>  ·  energía del núcleo ∝ τ<tspan font-size="7" baseline-shift="super">1/2−3h</tspan> → 0</text>
  </g>
</svg>
<figcaption>El flujo a orden principal en las escalas del propio paper: el núcleo se afina más rápido de lo que se acorta, por un exponente menor que una centésima, y ese desajuste minúsculo es todo el mecanismo.</figcaption>
</figure>

Tres ideas, todas viejas:

- **Momento angular.** Una parcela de fluido sobre la que no actúa ningún par conserva su momento angular por unidad de masa, radio por velocidad tangencial. Tira de ella hacia dentro y gira más rápido. Es la patinadora recogiendo los brazos, y es por lo que el agua sobre un desagüe se acelera al acercarse al agujero.
- **Incompresibilidad.** Lo que entra tiene que salir. El fluido que se enrosca hacia el eje se va a lo largo de él, hacia arriba a un lado de un plano divisorio y hacia abajo al otro. El núcleo se estira mientras se afina; la imagen del propio paper son espaguetis.
- **Estiramiento de vórtices.** Estirar un tubo giratorio a lo largo de su eje lo afina y, por el primer punto, lo acelera. Los dinamicistas de fluidos saben desde Helmholtz que este es *el* mecanismo por el que los flujos tridimensionales concentran rotación, y que los bidimensionales no pueden hacerlo, que es por lo que el problema en dos dimensiones se resolvió hace décadas.

La parte que no es intuitiva, y que necesitó la máquina, es el equilibrio. La viscosidad no queda arrollada en esta construcción; el número de Reynolds radial se mantiene de orden uno hasta el final, así que la difusión sigue compitiendo con el flujo entrante y el núcleo evoluciona como una forma autosemejante en vez de colapsar. El radio se encoge como la raíz cuadrada del tiempo restante y la altura como esa misma raíz dividida por una potencia diminuta, de exponente menor que una centésima. Todo en las ecuaciones diverge, y las divergencias tienen que cancelarse con la precisión justa para dejar detrás una fuerza suave. El resultado de Terence Tao de 2016, que una versión promediada de Navier–Stokes explota, se leyó entonces como una pista de que cualquier explosión real tendría que estar diseñada como una máquina construida con fluido. Lo que la demostración enseña es que la máquina es una espiral. Intuitiva de leer; no de demostrar.

## Teoremas que cambiaron de estado de un día para otro

Noventa años sin saberlo produjeron una literatura amplia de resultados condicionales, y un teorema condicional no cambia cuando se decide su hipótesis, pero su significado sí. Tres familias, y qué le pasó a cada una:

- **"Si se forma una singularidad, entonces…"** Beale–Kato–Majda: la vorticidad máxima no puede ser integrable en tiempo. Caffarelli–Kohn–Nirenberg: el conjunto singular tiene medida parabólica unidimensional cero. Hasta el lunes eran descripciones de un objeto hipotético. Ahora son una lista de comprobación que el vórtice tiene que cumplir, y la cumple: su conjunto singular es un único punto en el origen en el tiempo 1, como CKN permite, y su vorticidad hace lo que BKM exige. Cada uno de estos es ahora una comprobación cruzada de la demostración, no una restricción sobre un fantasma.
- **"Si las soluciones se mantienen suaves, entonces…"** Comportamiento a largo plazo, convergencia de esquemas numéricos en intervalos arbitrarios, argumentos de unicidad que pasan por la regularidad. Eran teoremas con una hipótesis que todo el mundo esperaba gratis. Siguen siendo teoremas. Pero para el problema forzado la hipótesis ya no está disponible en general; cada resultado tiene ahora un dominio, las fuerzas para las que la regularidad se cumple, y ese dominio excluye al menos una fuerza suave.
- **"Las ecuaciones de Navier–Stokes forzadas en 3D son globalmente regulares."** Una conjetura que sostenía la mayoría. Ahora falsa. Es el único enunciado que ha quedado falsado en vez de reinterpretado.

Dos cosas no se han movido. Los enunciados A y B, la regularidad de las ecuaciones *sin forzamiento*, quedan intactos; todo teorema condicionado a ellos conserva exactamente el estado que tenía. Y no todos los criterios de regularidad se transfieren: el criterio de Escauriaza, Seregin y Šverák, que la norma L³ tiene que explotar, se demostró para el problema de Cauchy sin forzamiento, así que no restringe automáticamente a este vórtice.

Hay además una pregunta que acaba de volverse concreta. Leray demostró en 1934 que las soluciones débiles continúan más allá de cualquier tiempo singular. Si continúan de forma *única* no se sabe, y Albritton, Brué y Colombo demostraron en 2022 que con una fuerza singular en el instante inicial no lo hacen. Hasta ahora, "qué hace el fluido después de la singularidad" era una pregunta sobre una trayectoria que nadie había exhibido. Ahora hay una trayectoria suave desde el reposo hasta un punto singular, y lo que hay al otro lado es una pregunta sobre un objeto concreto.

## El trabajo concurrente

El relato de OpenAI dice que el esfuerzo empezó el 1 de septiembre tras un rumor de que se habían resuelto dos problemas del milenio; el rumor resultó referirse a Levent Alpöge, empleado de Anthropic, y Tristan Buckmaster, de la NYU, que tenían un resultado de explosión para las ecuaciones de *Euler forzadas*. OpenAI dice que contactó con ellos el 6 de septiembre, después de la verificación en Lean, para ofrecerles un anuncio conjunto, que ni sus investigadores ni sus agentes vieron nada de su trabajo antes de que fuera público, y que reconoce su prioridad en Euler forzado. Buckmaster ha planteado dudas sobre los tiempos y sobre borradores que había metido en herramientas de OpenAI; Sébastien Bubeck ha negado cualquier uso de ellos. No tengo manera de dirimir eso desde fuera, y tampoco la tiene nadie que no estuviera en la sala. Lo que sí se puede decir es que el resultado de Euler de OpenAI es para las ecuaciones *sin forzamiento*, que es el enunciado distinto y el que suele considerarse más difícil, y que según se reporta las dos demostraciones difieren sustancialmente.

## Qué sacar de esto

- **El problema tal y como está escrito está cerrado, en negativo.** La pregunta que la mayoría entiende por él, si un fluido sin empujón externo puede explotar, sigue abierta, y la propia estructura de la demostración dice lo lejos que está de responderla: la fuerza se define como el residuo que haga funcionar la construcción.
- **No cambia nada para quienes usan las ecuaciones.** La rotura ocurre a escalas donde el continuo nunca fue una descripción válida, con energía que se desvanece, bajo una fuerza que nada en la naturaleza proporciona. Las ecuaciones ya eran un modelo con un rango; ahora sabemos que el rango tiene un borde alcanzable desde dentro.
- **El modelo no es uno que se pueda usar**, y el sistema a su alrededor es un enjambre de diez mil agentes con un agente de código como editor. El paso de Lean, la única parte que alguien de fuera puede comprobar, es la que hizo Astra.
- **La forma siempre estuvo ahí.** Una patinadora recogiendo los brazos, estirada a lo largo del eje de giro, equilibrada contra la viscosidad por un exponente menor que el uno por ciento. Hicieron falta noventa años y una máquina para escribirla, y hace falta un minuto para explicarla.

---

*Fuentes: el [anuncio de OpenAI](https://openai.com/index/navier-stokes-solution/), el [paper](https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf), la [formalización en Lean](https://github.com/openai/NavierStokesAndEuler) y el [enunciado oficial del problema por Fefferman](https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf) para el Instituto Clay.*
