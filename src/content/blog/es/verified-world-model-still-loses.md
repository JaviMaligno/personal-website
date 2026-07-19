---
title: "Un modelo del mundo puede pasar todos los tests y aun así perder"
description: "Quise reproducir un resultado de DeepMind y acabé encontrando una forma limpia en la que la verificación te puede engañar: un modelo del mundo en código que pasa su gate al 100% de precisión, mantiene un 98% de acierto en los estados que visita un planificador, y aun así pierde sistemáticamente al jugar."
pubDate: 2026-07-15
tags: ["IA", "Machine Learning", "Testing", "Investigación", "Agentes"]
lang: es
translationKey: verified-world-model-still-loses
heroImage: "/blog/verified-world-model-still-loses.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
---
Hace un tiempo escribí que la programación se está desplazando de verificar *cómo* funciona el código a verificar *qué* produce — [programación orientada a resultados](/es/blog/results-oriented-programming). Este post es lo que pasó cuando me tomé esa idea lo bastante en serio como para romperla. Quise reproducir un resultado de DeepMind y acabé varias semanas con una pregunta pequeña y testaruda: **si un chequeo de resultado pasa, ¿significa eso de verdad que el resultado es correcto?** La respuesta resulta ser "no necesariamente" — y se puede decir exactamente cuándo falla, y demostrar parte del porqué.

Lo escribí todo como un preprint, *When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models*, ya en arXiv (**[arXiv:2607.14169](https://arxiv.org/abs/2607.14169)**). El [código y el registro completo de reproducción son abiertos](https://github.com/JaviMaligno/code-world-models); el resto de este post es la historia en lenguaje llano.

<style>
.cwm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.cwm-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.cwm-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
.cwm-table{width:100%;border-collapse:collapse;margin:1.5rem 0;font-size:.92rem}
.cwm-table th,.cwm-table td{padding:.55rem .7rem;border-bottom:1px solid rgba(255,255,255,0.1);text-align:left}
.cwm-table th{color:#94a3b8;font-weight:600}
.cwm-table td.n{font-family:ui-monospace,'JetBrains Mono',monospace;text-align:right;white-space:nowrap}
</style>

## El planteamiento: Code World Models

El paradigma que estaba hurgando viene del paper de DeepMind *Code World Models for General Game Playing* ([Lehrach et al., 2025](https://arxiv.org/abs/2510.04542)). En vez de pedirle a un modelo de lenguaje que *juegue* directamente, le pides que **escriba las reglas del juego como un programa en Python** — un "modelo del mundo" con funciones para movimientos legales, transiciones y resultados. Luego un planificador clásico ([Monte Carlo Tree Search](https://en.wikipedia.org/wiki/Monte_Carlo_tree_search)) juega *contra ese programa sintetizado*. La división del trabajo es elegante: el LLM hace traducción (reglas → código) y la búsqueda clásica hace la anticipación.

Funciona bien, y en juegos conocidos un modelo pequeño + MCTS le gana por mucho al mismo modelo usado como política directa. Eso lo reproduje. Pero un paso me incomodaba: **el paso de verificación.**

Antes de que el planificador confíe en el modelo del mundo sintetizado, el modelo se *refina* hasta alcanzar el 100% de precisión de transición sobre un lote de partidas aleatorias — siguiente estado, movimientos legales, resultado, todo coincidiendo con el juego real. Si lo pasas, "pasas el gate". Parece un chequeo de corrección limpio y automático.

La pregunta que no me podía quitar de encima: **pasar ese gate significa que el modelo coincide con la verdad en juego aleatorio. ¿Significa que el modelo es lo bastante bueno para planificar con él?**

## El nulo honesto

Lo primero, la parte aburrida e importante: en juegos pequeños y completamente especificados, el gate *sí* basta. Tres en raya, una variante de ajedrez generalizado (`army5x5a`, más abajo), [Trike](https://boardgamegeek.com/boardgame/307379/trike) — siempre que un modelo sintetizado pasaba el gate, también era correcto en los estados que el planificador realmente visita. Sin brecha. Lo reporto como resultado nulo, porque marca la frontera: el gate es un filtro fuerte cuando las reglas están completas y el espacio de estados es pequeño.

Así que la pregunta interesante pasa a ser: **¿cuándo se puede engañar al gate?** Y la condición es precisa: necesitas una regla que el juego aleatorio casi nunca dispara pero que el juego competente busca de forma fiable.

## El instrumento: una regla rara que decide partidas

Para hacer real esa condición no inventé un juego desde cero — tomé un juego de ajedrez generalizado *del propio paper de DeepMind* (`army5x5a`, definido en [su Apéndice H.5](https://arxiv.org/abs/2510.04542): un tablero 5×5 con piezas de general, infantería y caballería, se gana capturando al general rival) y le añadí una regla: si la partida llega a un tope alto de jugadas con ambos generales aún vivos, gana quien tenga más material en vez de empatar. Bajo juego *aleatorio*, esa regla decide la partida un 2.5% de las veces — las partidas aleatorias acaban pronto, por error. Bajo juego *competente* decide cerca de la mitad de las partidas, porque el buen juego sobrevive hasta el tope.

<figure class="cwm-fig">
<svg viewBox="0 0 600 200" role="img" aria-label="Con qué frecuencia decide la regla la partida: 2.5% bajo juego aleatorio, cerca del 50% bajo juego competente">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF" text-anchor="middle">
    <line x1="150" y1="30" x2="150" y2="170" stroke="rgba(255,255,255,0.1)"/>
    <line x1="360" y1="30" x2="360" y2="170" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <line x1="570" y1="30" x2="570" y2="170" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <text x="150" y="188">0%</text><text x="360" y="188">50%</text><text x="570" y="188">100%</text>
  </g>
  <text x="140" y="72" text-anchor="end" fill="#f8fafc" font-size="13">Juego aleatorio</text>
  <rect x="150" y="58" width="10.5" height="26" rx="4" fill="#f43f5e"/>
  <text x="168" y="76" fill="#f43f5e" font-size="12" font-family="ui-monospace,monospace">2.5%</text>
  <text x="140" y="132" text-anchor="end" fill="#f8fafc" font-size="13">Juego competente</text>
  <rect x="150" y="118" width="210" height="26" rx="4" fill="#6366f1"/>
  <text x="368" y="136" fill="#818cf8" font-size="12" font-family="ui-monospace,monospace">~50%</text>
</svg>
<figcaption>Con qué frecuencia la regla de material-al-tope decide realmente la partida. El gate muestrea juego <em>aleatorio</em> (2.5%); la partida se decide bajo juego <em>competente</em> (~50%). El gate mira donde la regla casi nunca importa.</figcaption>
</figure>

Ahora omite esa regla de la especificación y sintetiza un modelo del mundo. El resultado es un modelo que:

- pasa el gate al **100% de precisión de transición**,
- es **≥98% preciso** sobre la distribución exacta de estados que visita el planificador,
- y aun así **pierde sistemáticamente al jugar** (tasa de victoria 0.404 vs 0.495 de un baseline justo calibrado — un *coste de juego* de 0.091, con intervalos de confianza al 95% que no se solapan; IC 95% agrupado por semilla [0.065, 0.117] sobre 20 semillas).

En todo el texto, **coste de juego** es simplemente la tasa de victoria que sacrifica el fallo: la tasa del baseline justo menos la del modelo defectuoso, ambos jugando contra el juego real al mismo presupuesto. 0 significa "juega tan bien como la verdad"; cuanto mayor, más partidas te está costando el fallo.

El puñado de estados que falla son exactamente los que deciden partidas. Las medias lo esconden — el error queda *diluido* por todas las posiciones normales que acierta. Precisión de predicción y adecuación para jugar se separan, de forma limpia y reproducible.

<figure class="cwm-fig">
<svg viewBox="0 0 600 195" role="img" aria-label="Tasas de victoria con intervalos de confianza al 95%: baseline justo 0.495, ciego a la regla 0.404, los intervalos no se solapan">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF" text-anchor="middle">
    <line x1="150" y1="40" x2="150" y2="150" stroke="rgba(255,255,255,0.1)"/>
    <line x1="355" y1="40" x2="355" y2="150" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <line x1="560" y1="40" x2="560" y2="150" stroke="rgba(255,255,255,0.1)"/>
    <text x="150" y="168">0.35</text><text x="355" y="168">0.45</text><text x="560" y="168">0.55</text>
    <text x="355" y="186" fill="#94a3b8" font-family="'Inter',sans-serif">tasa de victoria vs el juego real</text>
  </g>
  <text x="138" y="74" text-anchor="end" fill="#f8fafc" font-size="13">Baseline justo</text>
  <line x1="406.25" y1="70" x2="488.25" y2="70" stroke="#6366f1" stroke-width="2"/>
  <line x1="406.25" y1="63" x2="406.25" y2="77" stroke="#6366f1" stroke-width="2"/>
  <line x1="488.25" y1="63" x2="488.25" y2="77" stroke="#6366f1" stroke-width="2"/>
  <circle cx="447.25" cy="70" r="6" fill="#6366f1" stroke="#1a1a24" stroke-width="2"/>
  <text x="447.25" y="52" text-anchor="middle" fill="#818cf8" font-size="12" font-family="ui-monospace,monospace">0.495</text>
  <text x="138" y="124" text-anchor="end" fill="#f8fafc" font-size="13">CWM ciego a la regla</text>
  <line x1="219.7" y1="120" x2="301.7" y2="120" stroke="#f43f5e" stroke-width="2"/>
  <line x1="219.7" y1="113" x2="219.7" y2="127" stroke="#f43f5e" stroke-width="2"/>
  <line x1="301.7" y1="113" x2="301.7" y2="127" stroke="#f43f5e" stroke-width="2"/>
  <circle cx="260.7" cy="120" r="6" fill="#f43f5e" stroke="#1a1a24" stroke-width="2"/>
  <text x="260.7" y="142" text-anchor="middle" fill="#f43f5e" font-size="12" font-family="ui-monospace,monospace">0.404</text>
  <line x1="301.7" y1="95" x2="406.25" y2="95" stroke="#9CA3AF" stroke-width="1" stroke-dasharray="2 3"/>
  <text x="354" y="90" text-anchor="middle" fill="#9CA3AF" font-size="11" font-family="ui-monospace,monospace">brecha 0.091</text>
</svg>
<figcaption>El modelo ciego a la regla (rosa), que pasa el gate y es ≥98% preciso, pierde contra el baseline justo (índigo). Los intervalos al 95% no se solapan — el coste de juego de 0.091 no es un artefacto de muestreo.</figcaption>
</figure>

Para asegurarme de que no era un artefacto de mi sustituto escrito a mano, también lo ejecuté de extremo a extremo a través del pipeline de síntesis real, al mismo presupuesto y con sus propios intervalos de confianza: el modelo sintetizado pasa el gate *solo* cuando la regla rara está ausente de su muestra, y cuando lo hace, pierde al jugar — con un coste al menos tan grande como el de arriba. El mismo efecto, sin un humano dibujando a mano el modelo defectuoso.

<table class="cwm-table">
<thead><tr><th>Brazo (vs el juego real)</th><th style="text-align:right">Tasa de victoria [IC 95%]</th><th style="text-align:right">Coste de juego</th></tr></thead>
<tbody>
<tr><td><span style="color:#6366f1">●</span> Baseline justo (verdad vs verdad)</td><td class="n">0.495 [0.475, 0.515]</td><td class="n">—</td></tr>
<tr><td><span style="color:#f43f5e">●</span> Instrumento ciego a la regla (Panel A)</td><td class="n">0.404 [0.384, 0.424]</td><td class="n"><strong>0.091</strong></td></tr>
<tr><td><span style="color:#f43f5e">●</span> Sintetizado, regla ausente (Panel B)</td><td class="n">0.345 [0.317, 0.374]</td><td class="n"><strong>0.154</strong></td></tr>
</tbody></table>

<p style="color:#94a3b8;font-size:.82rem;margin:-.5rem 0 1.5rem;text-align:center">El coste de juego se mide pareado por semilla contra el baseline justo de cada brazo; el coste mayor del brazo sintetizado refleja imperfecciones más allá de la regla omitida. Números completos e ICs en el <a href="https://arxiv.org/abs/2607.14169">preprint</a>.</p>

## Una ley para cuándo la verificación se queda ciega

Lo bonito es que esto no es una anécdota aislada; tiene forma. El daño esperado sigue

$$\text{daño} = \text{play\_cost} \times (1 - \text{rareza})^N$$

donde `rareza` es cada cuánto una partida aleatoria dispara la regla omitida y $N$ cuántas partidas muestrea el gate. El factor $(1 - \text{rareza})^N$ es exacto — es simplemente la probabilidad de que $N$ partidas aleatorias independientes fallen todas la regla. Así que el daño es despreciable mientras la regla sea lo bastante común como para que la cacen, sube atravesando un umbral según se hace más rara, y se satura en el coste completo de la regla cuando casi siempre escapa al gate.

<figure class="cwm-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="Ley de peligro: daño esperado frente a la rareza de la regla, cerca del coste de juego completo mientras la regla es rara y desplomándose cuando es lo bastante común para cazarla">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF">
    <line x1="70" y1="30" x2="70" y2="210" stroke="rgba(255,255,255,0.1)"/>
    <line x1="70" y1="210" x2="560" y2="210" stroke="rgba(255,255,255,0.1)"/>
    <text x="70" y="228" text-anchor="middle">0</text>
    <text x="233" y="228" text-anchor="middle">5%</text>
    <text x="396" y="228" text-anchor="middle">10%</text>
    <text x="560" y="228" text-anchor="middle">15%</text>
    <text x="315" y="248" text-anchor="middle" fill="#94a3b8" font-family="'Inter',sans-serif">rareza de la regla (fracción de partidas aleatorias que la disparan)</text>
    <text x="58" y="34" text-anchor="end">0.5</text>
    <text x="58" y="214" text-anchor="end">0</text>
    <text x="20" y="120" text-anchor="middle" fill="#94a3b8" font-family="'Inter',sans-serif" transform="rotate(-90 20 120)">daño esperado</text>
  </g>
  <path d="M70,30 L102.7,90 L135.3,129.6 L151.7,144.9 L168,156.7 L200.7,174.7 L233.3,186.9 L266,194.9 L331.3,203.5 L396.7,207.3 L462,208.9 L560,209.7" fill="none" stroke="#6366f1" stroke-width="2.5"/>
  <circle cx="151.7" cy="144.9" r="6" fill="#f43f5e" stroke="#1a1a24" stroke-width="2"/>
  <line x1="151.7" y1="144.9" x2="151.7" y2="210" stroke="#f43f5e" stroke-width="1" stroke-dasharray="2 3"/>
  <text x="160" y="120" fill="#f43f5e" font-size="11" font-family="ui-monospace,monospace">nuestra regla (2.5%)</text>
  <text x="300" y="70" fill="#94a3b8" font-size="12">daño ≈ coste de juego completo mientras</text>
  <text x="300" y="88" fill="#94a3b8" font-size="12">la regla es demasiado rara para un gate de N</text>
</svg>
<figcaption>daño = play_cost × (1 − rareza)<tspan font-size="0.8em">N</tspan>, aquí con N = 40 muestras del gate. El daño se mantiene cerca del coste de juego completo mientras la regla es lo bastante rara para colarse por el gate, y luego se desploma cuando es lo bastante común para cazarla. Nuestra regla diseñada (rosa) cae de lleno en la zona peligrosa.</figcaption>
</figure>

Hay una lectura más afilada de ese factor. Cuando la regla nunca aparece en la muestra, los datos son *literalmente idénticos* esté la regla en el modelo o no. Así que ningún aprendiz de ningún tipo — ni un LLM más grande, ni descenso por gradiente, ni búsqueda exhaustiva — puede recuperar la regla **solo a partir de esa muestra**. No es una debilidad del modelo; es información que falta. Cualquier recuperación tiene que venir de la especificación, no de los datos.

<figure class="cwm-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="Las trayectorias aleatorias muestreadas terminan superficiales; la región profunda que decide las partidas competentes nunca se muestrea">
  <defs>
    <linearGradient id="cwm-deep-es" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f43f5e" stop-opacity="0"/>
      <stop offset="1" stop-color="#f43f5e" stop-opacity="0.18"/>
    </linearGradient>
  </defs>
  <rect x="40" y="180" width="520" height="65" fill="url(#cwm-deep-es)"/>
  <line x1="40" y1="180" x2="560" y2="180" stroke="#f43f5e" stroke-width="1" stroke-dasharray="4 4" opacity="0.6"/>
  <text x="552" y="173" text-anchor="end" fill="#f43f5e" font-size="11" font-family="ui-monospace,monospace">región profunda — decide partidas competentes, nunca muestreada</text>
  <text x="48" y="24" fill="#9CA3AF" font-size="11" font-family="ui-monospace,monospace">inicio</text>
  <circle cx="300" cy="30" r="4" fill="#94a3b8"/>
  <g fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" opacity="0.85">
    <path d="M300,30 L180,90 L120,140"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.2s" repeatCount="indefinite"/></path>
    <path d="M300,30 L250,95 L230,150"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.6s" begin="0.3s" repeatCount="indefinite"/></path>
    <path d="M300,30 L360,92 L410,145"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.4s" begin="0.6s" repeatCount="indefinite"/></path>
    <path d="M300,30 L430,88 L500,150"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.8s" begin="0.15s" repeatCount="indefinite"/></path>
    <path d="M300,30 L300,100 L320,155"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.5s" begin="0.9s" repeatCount="indefinite"/></path>
  </g>
  <g fill="#6366f1">
    <circle cx="120" cy="140" r="3.5"/><circle cx="230" cy="150" r="3.5"/><circle cx="410" cy="145" r="3.5"/><circle cx="500" cy="150" r="3.5"/><circle cx="320" cy="155" r="3.5"/>
  </g>
  <path d="M300,30 L305,110 L300,200 L302,235" fill="none" stroke="#f43f5e" stroke-width="2" stroke-dasharray="3 5" opacity="0.45"/>
  <circle cx="302" cy="235" r="5" fill="none" stroke="#f43f5e" stroke-width="2">
    <animate attributeName="r" values="5;9;5" dur="1.8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.7;0.2;0.7" dur="1.8s" repeatCount="indefinite"/>
  </circle>
</svg>
<figcaption>Lo que ve un gate de muestreo: las partidas aleatorias (índigo) acaban superficiales, por error. La región profunda donde vive el juego competente — y donde la regla rara decide la partida — casi nunca se alcanza, así que el gate nunca la prueba.</figcaption>
</figure>

## Traducción, no inferencia

Eso lleva al hallazgo que me parece más práctico. ¿Se puede *reparar* la brecha dándole al modelo ejemplos de la regla? Lo intenté — en serio: DAgger, estados cosechados on-manifold, decenas de ejemplos discriminantes, dos tamaños de modelo, bucles de refinamiento que sacan datos frescos en cada iteración.

(Para fans del imitation learning: el "DAgger propio" aquí es el bucle de [Ross et al. (2011)](https://arxiv.org/abs/1011.0686) — recoger estados del propio juego del modelo defectuoso y reetiquetarlos con el oráculo — no solo volcar trayectorias competentes.)

No funciona. En todos los casos, el modelo sintetizado sigue ciego a la regla incluso cuando la regla está presente en sus trayectorias casi con certeza (se puede ver: la precisión del gate se queda muy por debajo de 1.0, lo que significa que la regla *está* en los datos, y tras seis pasadas de refinamiento el modelo aún no la ha codificado). El comportamiento es **traducción de reglas, no inferencia de reglas**: el modelo codifica fielmente las reglas que se le *dicen*, y no infiere de forma fiable las reglas que solo se le *muestran*. La versión accionable: completa la especificación antes de sintetizar. Verificar sobre la distribución de juego *detectará* una especificación incompleta; no la *reparará*.

## La misma división en el lado de las creencias

Los juegos con información oculta — póker y similares — añaden una segunda cosa que el modelo tiene que acertar: no solo la dinámica, sino una *función de creencias*, el código que reconstruye lo que un jugador no puede ver a partir de lo que sí ve. Esperaba que la brecha apareciera también aquí. La primera sorpresa fue que no — y la razón es casi graciosa.

En juegos pequeños de póker (Kuhn, Leduc) el gate muestreado es *demostrablemente* suficiente para certificar la función de creencias; puedo escribir la cota. Resulta que el juego aleatorio es un explorador **más** exhaustivo de un árbol de apuestas que el juego hábil, porque rapea y paga indiscriminadamente mientras que el buen juego se retira. Así que los estados de creencia raros nunca se esconden del gate — el juego competente solo visita un subconjunto de lo que el aleatorio ya cubrió. Sin brecha.

Pero eso te dice exactamente qué *necesitaría* una brecha: un juego donde la habilidad te lleve **más profundo** que el azar — donde la profundidad venga de *sobrevivir*, no de dar palos de ciego. Así que construí el juego más pequeño posible con esa forma. Lo llamo Beacon, y es básicamente el dibujo de servilleta: una caminata donde, en cada paso, eliges un movimiento — una opción te deja continuar, la equivocada acaba la partida en el acto. El juego aleatorio se sale del camino casi de inmediato; el juego hábil camina hasta el final. Y justo al final hay una única decisión que depende de un dato oculto sobre tu rival — un dato que podrías haber leído de los movimientos que hizo por el camino.

<figure class="cwm-fig">
<svg viewBox="0 0 600 235" role="img" aria-label="Beacon: una caminata donde un movimiento continúa y el equivocado acaba la partida; la decisión final depende de información oculta que el gate nunca prueba">
  <g stroke="#6366f1" stroke-width="2.5" fill="none" marker-end="url(#cwm-arrow-es)">
    <line x1="72" y1="90" x2="126" y2="90"/><line x1="152" y1="90" x2="206" y2="90"/>
    <line x1="232" y1="90" x2="286" y2="90"/><line x1="312" y1="90" x2="366" y2="90"/>
    <line x1="392" y1="90" x2="446" y2="90"/><line x1="472" y1="90" x2="524" y2="90"/>
  </g>
  <g stroke="#f43f5e" stroke-width="1.5" fill="none" opacity="0.7">
    <line x1="60" y1="104" x2="60" y2="146"/><line x1="140" y1="104" x2="140" y2="146"/>
    <line x1="220" y1="104" x2="220" y2="146"/><line x1="300" y1="104" x2="300" y2="146"/>
  </g>
  <g fill="#f43f5e" opacity="0.75" font-size="10" font-family="ui-monospace,monospace" text-anchor="middle">
    <text x="60" y="162">✕ fin</text><text x="140" y="162">✕ fin</text>
    <text x="220" y="162">✕ fin</text><text x="300" y="162">✕ fin</text>
  </g>
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="10" fill="#f8fafc" text-anchor="middle">
    <circle cx="60" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="60" y="94">s0</text>
    <circle cx="140" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="140" y="94">s1</text>
    <circle cx="220" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="220" y="94">s2</text>
    <circle cx="300" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="300" y="94">s3</text>
    <circle cx="380" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="380" y="94">s4</text>
    <circle cx="460" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="460" y="94">s5</text>
    <circle cx="540" cy="90" r="14" fill="#1a1a24" stroke="#f43f5e" stroke-width="2.5"/><text x="540" y="94">s6</text>
  </g>
  <text x="540" y="60" fill="#f43f5e" font-size="15" text-anchor="middle">?</text>
  <text x="540" y="45" fill="#f43f5e" font-family="'Inter',sans-serif" font-size="10" text-anchor="middle">decisión con info oculta</text>
  <text x="52" y="192" fill="#818cf8" font-family="'Inter',sans-serif" font-size="11">El juego aleatorio se sale del camino en uno o dos pasos…</text>
  <text x="256" y="212" fill="#f43f5e" font-family="'Inter',sans-serif" font-size="11">…así que el gate nunca prueba s5–s6, donde se decide la partida.</text>
  <defs><marker id="cwm-arrow-es" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#6366f1"/></marker></defs>
</svg>
<figcaption>Beacon: un testigo construido a mano donde la habilidad significa <em>sobrevivir</em> más profundo, no explorar más ancho. Un movimiento continúa; el equivocado acaba la partida. La decisión final depende de un dato oculto — así que una función de creencias equivocada solo en s6 pasa un gate de juego aleatorio y aun así pierde todas las partidas.</figcaption>
</figure>

Ahora dale a un modelo una función de creencias correcta en todas partes *excepto* en ese tramo final — el extremo profundo de la caminata al que solo llega el juego hábil. Pasa el gate sin problema (el aleatorio nunca llega lo bastante lejos para probarlo) y luego pierde todas las partidas, porque el único sitio donde sus creencias están mal es el único sitio donde la partida se decide de verdad. La misma forma que la regla rara, ahora en el lado de las creencias: verificada, y aun así equivocada justo donde importa.

Seamos claros: Beacon es un *testigo construido a propósito*, no algo con lo que un modelo se tropezó — una prueba de existencia. Y el emplazamiento profundo no es una trampa, es justo el punto: es el *único* sitio que a la vez es inalcanzable para el gate (que muestrea juego aleatorio, superficial) y decisivo para el resultado (la partida se resuelve en la ronda final). Pon el error en cualquier sitio más superficial y el gate lo caza; ponlo en un sitio que no decida partidas y no cuesta nada. "Equivocada justo donde el gate no puede mirar *y* donde se gana la partida" es exactamente la esquina que la construcción tiene que acertar — y Beacon demuestra que esa esquina no está vacía.

Debajo hay un punto estructural limpio: un gate de precisión de transición es **ciego por construcción** a la función de creencias. Lo que un jugador puede y no puede ver nunca aparece en una transición "este estado pasó a ese estado" — así que ningún chequeo de transiciones puede cazar un modelo de creencias erróneo; necesitas un chequeo *aparte* sobre las creencias. (Estos resultados de información imperfecta usan juegos que instrumenté a mano para aislar el efecto, en vez de modelos totalmente sintetizados — una distinción que mantengo con cuidado en el paper.)

La mitad más esperanzadora de la historia es que ese chequeo aparte a menudo *basta*, y de forma demostrable. En el paper desarrollo una cota de cobertura: un inference gate aleatorio está garantizado que caza los errores de creencias en cuanto muestrea más de aproximadamente `bᵈ` partidas, donde `b` es cuántas opciones enfrenta un jugador en cada paso y `d` es cómo de profundo llegan las decisiones del juego. Los juegos superficiales superan ese listón con holgura — que es exactamente por qué el póker de Kuhn y Leduc *no* muestran brecha de creencias: su gate es demostrablemente suficiente. Para juegos demasiado grandes para enumerar, hay una cota compañera que limita el error no detectado que una función de creencias que pasa el gate puede esconder. Beacon es simplemente el caso diseñado para caer al lado malo de esa cota. Lo que sigue faltando — y lo que marcaría como trabajo futuro — es un chequeo de creencias *adversarial* que muestree deliberadamente la región profunda alcanzable por la habilidad, en vez de esperar a que el juego aleatorio se cuele ahí; ese es el chequeo que cerraría de verdad el hueco con forma de Beacon.

## Lo que me llevo de esto

Una batería de tests que pasa — o un gate basado en muestreo — es un *chequeo de resultado con un punto ciego de cobertura*. Certifica el modelo justo donde caen tus muestras, y el comportamiento competente cae sistemáticamente en otra parte: las zonas raras, decisivas y profundas del espacio. Si verificas un modelo del mundo (o, francamente, cualquier modelo usado para planificar o decidir) por muestreo, mide la adecuación **sobre la distribución en la que realmente se va a usar**, no sobre una aleatoria cómoda. Y cuando la corrección depende de una regla, pon la regla en la especificación — no esperes que el sistema la infiera.

Si quieres la versión formal, con los teoremas y los números, está en el [preprint](https://arxiv.org/abs/2607.14169). El [código también es abierto](https://github.com/JaviMaligno/code-world-models).

---

*Preprint: "When a Verified World Model Still Loses" ([arXiv:2607.14169](https://arxiv.org/abs/2607.14169)) · [código](https://github.com/JaviMaligno/code-world-models). Lecturas relacionadas: [Programación Orientada a Resultados](/es/blog/results-oriented-programming) y [Software Disolviéndose en el Modelo](/es/blog/software-dissolving-into-the-model).*
