---
title: "Estar equivocado puede ser gratis — hasta que el planificador pueda llegar"
description: "Un modelo del mundo sintetizado puede equivocarse en toda una región, pasar cualquier gate de muestreo y no costar absolutamente nada — con demostración. Después abrí una puerta de 0.1 radianes en esa región y el peligro se derrumbó; escondí la misma puerta detrás del objetivo y siguió a plena potencia. Misma topología, peligro opuesto."
pubDate: 2026-09-02
tags: ["IA", "Machine Learning", "Testing", "Investigación", "Agentes"]
lang: es
translationKey: being-wrong-can-be-free
heroImage: "/blog/being-wrong-can-be-free.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/XXXX.XXXXX"
  - label: "Paper companion"
    url: "https://arxiv.org/abs/2608.17956"
---
La semana pasada escribí sobre [un modelo que infiere la regla que olvidaste, pero solo en una dimensión](/es/blog/infer-the-rule-in-one-dimension). La regla práctica con la que terminaba era que la cobertura de la frontera lo es todo: tu gate de muestreo certifica tu modelo allí donde caen tus muestras, y una regla con forma sigues teniendo que especificarla.

Eso deja una pregunta que no podía responder con los instrumentos de aquel paper. Todos esos modelos equivocados lo estaban *en algún sitio al que un planificador podía llegar*. ¿Qué pasa cuando la parte que el modelo se equivoca encierra algo a lo que nada puede llegar nunca? La respuesta resulta más nítida que "probablemente no pasa nada", y en las dos direcciones: el error se vuelve demostrablemente indetectable **y** demostrablemente gratis — y luego una puerta de 0.1 radianes, en el sitio correcto, deshace la segunda mitad sin tocar la topología. Está escrito como preprint, *An Enclosed Mode Is a Gauge Choice* (**[arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX)**), con el [código, los artefactos de resultados y las demostraciones en Lean abiertos](https://github.com/JaviMaligno/code-world-models).

<style>
.cwm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.cwm-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.cwm-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
.cwm-table{width:100%;border-collapse:collapse;margin:1.5rem 0;font-size:.92rem}
.cwm-table th,.cwm-table td{padding:.55rem .7rem;border-bottom:1px solid rgba(255,255,255,0.1);text-align:left}
.cwm-table th{color:#94a3b8;font-weight:600}
.cwm-table td.n{font-family:ui-monospace,'JetBrains Mono',monospace;text-align:right;white-space:nowrap}
</style>

## Un modo con un dentro

El instrumento es deliberadamente mínimo: un móvil con empuje y rozamiento sobre un plano, y una banda anular — radio interior 3.5, exterior 5.0 — que congela al móvil en el instante en que la toca. Dentro del agujero del anillo hay un "filón" de recompensa alta que el planificador querría visitar. La especificación que recibe el modelo de lenguaje fija la física exactamente y simplemente omite la banda, igual que antes.

La razón para usar un anillo y no otro muro es que esta es la forma que tienen de verdad las omisiones críticas para la seguridad. Vallas, recintos de contención, zonas de exclusión geovalladas: una frontera dibujada alrededor de algo, con un dentro. Y un pipeline que no distingue un vacío vallado de un peligro vallado — ni una valla de un muro macizo — certifica menos de lo que parece.

Tres knobs, todos fijados antes de cualquier ejecución: la anchura $\gamma$ de un canal angular abierto en la banda (con $\gamma = 0$ el anillo está cerrado), si ese canal mira hacia la salida o se esconde detrás del filón, y si el móvil arranca fuera del anillo o dentro de su agujero. Todo lo que afirma el paper se deriva de lo que esos knobs le hacen a un único objeto: el conjunto de pares estado-acción que un rollout puede llegar a consultar.

<figure class="cwm-fig">
<!-- fig:instrument-knobs -->
<svg viewBox="0 0 600 214" role="img" aria-label="Four configurations of the same instrument: a closed band, a channel facing the start, the same channel hidden behind the goal, and a start inside the hole">
<defs><marker id="mk-knobs" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<rect x="6" y="26" width="142" height="150" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="84.0" y="18.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">closed</text>
<circle cx="84.0" cy="108.0" r="28.05" fill="none" stroke="#f43f5e" stroke-width="9.90" stroke-opacity="0.9"/>
<polygon points="84.0,99.4 81.8,104.9 75.8,105.3 80.4,109.2 79.0,114.9 84.0,111.8 89.0,114.9 87.6,109.2 92.2,105.3 86.2,104.9" fill="#fbbf24"/>
<circle cx="21.3" cy="108.0" r="3.0" fill="#f8fafc"/>
<line x1="26.3" y1="108.0" x2="42.8" y2="108.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-knobs)"/>
<path d="M45.6,103.6 L54.4,112.4 M54.4,103.6 L45.6,112.4" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
<text x="77.0" y="194.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">inside unreachable</text>
<rect x="154" y="26" width="142" height="150" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="232.0" y="18.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">facing</text>
<circle cx="232.0" cy="108.0" r="28.05" fill="none" stroke="#6366f1" stroke-width="9.90" stroke-opacity="0.9" stroke-dasharray="159.60 16.65" stroke-dashoffset="79.80"/>
<polygon points="232.0,99.4 229.8,104.9 223.8,105.3 228.4,109.2 227.0,114.9 232.0,111.8 237.0,114.9 235.6,109.2 240.2,105.3 234.2,104.9" fill="#fbbf24"/>
<circle cx="169.3" cy="108.0" r="3.0" fill="#f8fafc"/>
<line x1="174.3" y1="108.0" x2="222.1" y2="108.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-knobs)"/>
<text x="225.0" y="194.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the plan drives through</text>
<rect x="302" y="26" width="142" height="150" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="380.0" y="18.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">hidden</text>
<circle cx="380.0" cy="108.0" r="28.05" fill="none" stroke="#f43f5e" stroke-width="9.90" stroke-opacity="0.9" stroke-dasharray="159.60 16.65" stroke-dashoffset="167.92"/>
<polygon points="380.0,99.4 377.8,104.9 371.8,105.3 376.4,109.2 375.0,114.9 380.0,111.8 385.0,114.9 383.6,109.2 388.2,105.3 382.2,104.9" fill="#fbbf24"/>
<circle cx="317.3" cy="108.0" r="3.0" fill="#f8fafc"/>
<line x1="322.3" y1="108.0" x2="338.8" y2="108.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-knobs)"/>
<path d="M341.6,103.6 L350.4,112.4 M350.4,103.6 L341.6,112.4" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
<text x="373.0" y="194.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">same gap, unreachable</text>
<rect x="450" y="26" width="142" height="150" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="528.0" y="18.0" font-size="11.5" fill="#22d3ee" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">inside</text>
<circle cx="528.0" cy="108.0" r="28.05" fill="none" stroke="#22d3ee" stroke-width="9.90" stroke-opacity="0.9"/>
<polygon points="528.0,99.4 525.8,104.9 519.8,105.3 524.4,109.2 523.0,114.9 528.0,111.8 533.0,114.9 531.6,109.2 536.2,105.3 530.2,104.9" fill="#fbbf24"/>
<circle cx="517.4" cy="121.5" r="3.0" fill="#f8fafc"/>
<circle cx="542.4" cy="89.5" r="2.4" fill="#f8fafc"/>
<circle cx="525.6" cy="84.7" r="2.4" fill="#f8fafc"/>
<circle cx="510.1" cy="92.9" r="2.4" fill="#f8fafc"/>
<circle cx="539.7" cy="128.3" r="2.4" fill="#f8fafc"/>
<circle cx="550.0" cy="116.0" r="2.4" fill="#f8fafc"/>
<text x="521.0" y="194.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the inside is sampled</text>
</svg>
<!-- /fig:instrument-knobs -->
<figcaption>El instrumento, a escala, bajo los knobs que importan. Cerrado: el planificador se detiene en el borde y el interior es inalcanzable. Facing: la misma banda con un canal por el que sí puede conducir. Hidden: el mismo canal, la misma anchura, rotado detrás del filón — topológicamente idéntico al anterior, e inalcanzable. Inside: el móvil arranca dentro del agujero, así que el interior se muestrea y la omisión pasa a ser falsable.</figcaption>
</figure>


## Más allá del alcance, todo es gauge

La teoría en una frase. Si un gate acepta a todo candidato cuyas transiciones muestreadas coinciden, entonces la aceptación-con-certeza determina el modelo exactamente sobre el conjunto alcanzable de consultas — y *todo lo que queda más allá del alcance es gauge*, en el sentido del físico: una elección libre que no cambia ningún observable. Dos modelos que solo difieren ahí fuera son el mismo modelo para cualquier gate de muestreo.

En el anillo cerrado eso tiene un caso límite que cabe en la mano. El artefacto equivocado natural es un **disco relleno**: sin agujero, con todo el interior congelado. Se equivoca en la topología, no solo en los parámetros. Y es:

- **infalsable por cualquier gate de muestreo.** No "difícil de pillar" — hay demostración, y no necesita ningún supuesto sobre tamaño de muestra ni tolerancia. Como la banda congela al móvil al contacto, ningún rollout que empiece fuera puede acabar dentro del agujero, así que ninguna transición posible distingue el disco relleno de la verdad.
- **inofensivo bit a bit al jugar.** El planificador que se fía del disco relleno planifica idénticamente al que conoce la verdad: misma acción en cada paso, mismo retorno, mismo estado final, mismos contactos, semilla por semilla. Los episodios de MPC con semillas emparejadas lo confirman exactamente, no aproximadamente.

<figure class="cwm-fig">
<!-- fig:gauge-unfalsifiable -->
<svg viewBox="0 0 600 250" role="img" aria-label="The truth and the filled-disc artifact differ only inside the hole, where no sampled rollout can ever be">
<defs><marker id="mk-gauge" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<rect x="10" y="24" width="285" height="172" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="148.0" y="16.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">the truth</text>
<circle cx="148.0" cy="110.0" r="63.75" fill="none" stroke="#6366f1" stroke-width="22.50" stroke-opacity="0.9"/>
<polygon points="148.0,95.8 144.3,104.9 134.4,105.6 142.0,111.9 139.6,121.5 148.0,116.3 156.4,121.5 154.0,111.9 161.6,105.6 151.7,104.9" fill="#fbbf24"/>
<line x1="51.9" y1="54.5" x2="76.6" y2="68.8" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="82.8" cy="72.4" r="2.6" fill="#f8fafc"/>
<line x1="39.4" y1="86.9" x2="67.3" y2="92.8" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="74.3" cy="94.3" r="2.6" fill="#f8fafc"/>
<line x1="37.6" y1="121.6" x2="66.0" y2="118.6" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="73.1" cy="117.9" r="2.6" fill="#f8fafc"/>
<line x1="47.4" y1="156.9" x2="73.2" y2="144.9" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="79.8" cy="141.8" r="2.6" fill="#f8fafc"/>
<line x1="68.2" y1="187.1" x2="88.7" y2="167.3" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="93.8" cy="162.3" r="2.6" fill="#f8fafc"/>
<text x="148.0" y="214.0" font-size="10.5" fill="#818cf8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the inside is free</text>
<rect x="305" y="24" width="285" height="172" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="443.0" y="16.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">what the model wrote</text>
<circle cx="443.0" cy="110.0" r="52.50" fill="#f43f5e" fill-opacity="0.3"/>
<circle cx="443.0" cy="110.0" r="63.75" fill="none" stroke="#f43f5e" stroke-width="22.50" stroke-opacity="0.9"/>
<polygon points="443.0,95.8 439.3,104.9 429.4,105.6 437.0,111.9 434.6,121.5 443.0,116.3 451.4,121.5 449.0,111.9 456.6,105.6 446.7,104.9" fill="#fbbf24"/>
<line x1="346.9" y1="54.5" x2="371.6" y2="68.8" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="377.8" cy="72.4" r="2.6" fill="#f8fafc"/>
<line x1="334.4" y1="86.9" x2="362.3" y2="92.8" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="369.3" cy="94.3" r="2.6" fill="#f8fafc"/>
<line x1="332.6" y1="121.6" x2="361.0" y2="118.6" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="368.1" cy="117.9" r="2.6" fill="#f8fafc"/>
<line x1="342.4" y1="156.9" x2="368.2" y2="144.9" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="374.8" cy="141.8" r="2.6" fill="#f8fafc"/>
<line x1="363.2" y1="187.1" x2="383.7" y2="167.3" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#mk-gauge)"/>
<circle cx="388.8" cy="162.3" r="2.6" fill="#f8fafc"/>
<text x="443.0" y="214.0" font-size="10.5" fill="#fb7185" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the whole inside frozen</text>
<text x="300.0" y="236.0" font-size="11" fill="#f8fafc" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">every sample lands on the rim  ·  the two differ only inside it</text>
</svg>
<!-- /fig:gauge-unfalsifiable -->
<figcaption>Por qué ninguna muestra puede separarlos. Todo rollout que empieza fuera se detiene en el borde, así que las transiciones muestreadas son idénticas bajo los dos modelos; los dos solo difieren dentro del agujero, que es justo donde ningún rollout puede estar. Esto es la demostración, no un accidente del muestreo.</figcaption>
</figure>


Así que certificación, corrección y consecuencia se separan por tres, no por dos. Este artefacto está certificado, es incorrecto y es gratis. Mis dos papers anteriores habían mostrado certificado-e-incorrecto-y-costoso, y certificado-e-incorrecto-e-infalsable; el anillo es donde "incorrecto" y "caro" se desacoplan del todo, con un teorema y no con una medida.

## Dos agujeros idénticos, peligro opuesto

Esa es la mitad tranquila. Ahora abre en la banda un canal de anchura angular $\gamma$, y pon ese mismo canal en dos sitios distintos.

**Mirando a la salida**, por donde conduce el planificador: con $\gamma = 0.6$ el coste de juego del artefacto ciego es 0.029. **Escondido detrás del filón**, por donde ningún plan pasa: con la misma $\gamma = 0.6$, el mismo hueco, el mismo primer número de Betti igual a cero, es 1.116 — que es también, con cuatro decimales, lo que marca la banda completamente cerrada. Mismo agujero, misma topología, cuarenta veces el coste.

Conviene ser preciso con lo que cambia y lo que no, porque el eslogan invita a leerlo mal. Abrir el hueco **sí** cambia la topología: una banda cerrada separa el plano y una banda con hueco no. Por eso la comparación que sostiene la afirmación no es cerrado contra abierto, sino estos dos casos abiertos entre sí. Entre ellos no difiere nada topológico — misma $\beta_1$, misma banda no separadora, misma anchura — y lo único que se mueve es si el camino del propio planificador cruza el hueco.

Barrer $\gamma$ enseña dónde está el interruptor. Un barrido denso del modelo ciego programado a mano — 16 episodios de MPC emparejados por punto — pone el `play_cost` (cuánto retorno pierde el planificador por fiarse del modelo equivocado, normalizado contra el planificador con la verdad) en 0.999 con el anillo cerrado, en 0.139 con $\gamma = 0.1$, y en prácticamente cero desde $\gamma = 0.15$. Hay un codo, y está exactamente donde el canal se hace lo bastante ancho para que quepa un paso: con $\gamma = 0.1$ el arco del hueco mide unas 0.35 unidades de mundo, comparable al propio paso del planificador. El brazo de síntesis reproduce el derrumbe con sus propios artefactos ciegos explotados, en los dos tamaños de modelo y en el relevo de Claude: 0.348 en el codo, 0.029 ya en $\gamma = 0.6$.

El canal escondido no hace nada de eso. Con $\gamma = 0.6$ el coste de juego del artefacto ciego es 1.116; con $\gamma = 1.2$ es 1.116 otra vez; con la banda completamente cerrada, 1.116 una vez más. No "parecido al" anillo cerrado: su número con cuatro decimales, porque es el mismo programa ciego frente al mismo mundo alcanzable.

<figure class="cwm-fig">
<svg viewBox="0 0 600 268" role="img" aria-label="Coste de juego frente a anchura del canal: tanto el barrido denso programado como los artefactos ciegos sintetizados se derrumban cuando el canal visible admite el paso del planificador, mientras el canal escondido de la misma anchura mantiene el valor de la banda cerrada, 1.116">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF">
    <line x1="98" y1="38" x2="98" y2="190" stroke="rgba(255,255,255,0.14)"/>
    <line x1="98" y1="190" x2="578" y2="190" stroke="rgba(255,255,255,0.14)"/>
    <text x="88" y="49" text-anchor="end">1.12</text>
    <text x="88" y="194" text-anchor="end">0.00</text>
    <text x="120" y="210" text-anchor="middle">0</text>
    <text x="215" y="210" text-anchor="middle">0.1</text>
    <text x="310" y="210" text-anchor="middle">0.2</text>
    <text x="450" y="210" text-anchor="middle">0.6</text>
    <text x="560" y="210" text-anchor="middle">1.2</text>
    <text x="338" y="230" text-anchor="middle" fill="#64748b">anchura del canal γ (radianes)</text>
  </g>
  <polyline points="120,61 140,120 165,146 215,172 245,190 310,188 450,187 560,189" fill="none" stroke="#6366f1" stroke-width="2.4"/>
  <circle cx="120" cy="61" r="4" fill="#6366f1"/><circle cx="215" cy="172" r="4" fill="#6366f1"/>
  <text x="136" y="78" fill="#818cf8" font-size="11.5" font-family="ui-monospace,monospace">0.999</text>
  <text x="228" y="168" fill="#818cf8" font-size="11.5" font-family="ui-monospace,monospace">0.139</text>
  <circle cx="215" cy="145" r="5" fill="#22d3ee"/><circle cx="450" cy="186" r="5" fill="#22d3ee"/><circle cx="560" cy="187" r="5" fill="#22d3ee"/>
  <text x="228" y="141" fill="#22d3ee" font-size="11.5" font-family="ui-monospace,monospace">0.348</text>
  <circle cx="120" cy="46" r="5.5" fill="#f43f5e" fill-opacity="0.25" stroke="#f43f5e" stroke-width="2"/>
  <circle cx="450" cy="46" r="5.5" fill="#f43f5e"/><circle cx="560" cy="46" r="5.5" fill="#f43f5e"/>
  <line x1="120" y1="46" x2="560" y2="46" stroke="#f43f5e" stroke-width="2.2" stroke-dasharray="5 4"/>
  <text x="470" y="38" fill="#fb7185" font-size="11.5" font-family="ui-monospace,monospace">1.116</text>
  <text x="152" y="33" fill="#fb7185" font-size="11.5">banda cerrada</text>
  <text x="296" y="63" fill="#fb7185" font-size="12">canal escondido, misma γ: no cambia nada</text>
  <text x="300" y="120" fill="#818cf8" font-size="12">canal visible: el peligro se derrumba</text>
  <g font-size="11" font-family="ui-monospace,'JetBrains Mono',monospace">
    <line x1="112" y1="255" x2="138" y2="255" stroke="#6366f1" stroke-width="2.4"/>
    <text x="146" y="259" fill="#9CA3AF">modelo ciego programado, barrido denso</text>
    <circle cx="400" cy="255" r="5" fill="#22d3ee"/>
    <text x="412" y="259" fill="#9CA3AF">artefactos ciegos sintetizados</text>
  </g>
</svg>
<figcaption>Coste de juego del modelo ciego frente a la anchura del canal, 16 episodios de MPC emparejados por punto. Las dos series se derrumban en cuanto el canal visible admite el paso del planificador: el barrido denso programado de 0.999 a 0.139 en γ = 0.1 y a ~0 más allá, y los artefactos sintetizados de 1.116 a 0.348 en el codo y 0.029 ya en γ = 0.6. Rotar ese mismo canal detrás del filón (rosa) mantiene 1.116 en γ = 0.6 y γ = 1.2 — el propio valor de la banda cerrada, con cuatro decimales.</figcaption>
</figure>

Mismo agujero, mismo número de Betti, peligro opuesto. Lo que te dice que la propiedad que hace el trabajo no es topológica en absoluto. **El peligro es topología relativa al alcance.** Y el mecanismo es el cociente del gate apareciendo en el lado del juego: al abrirse el canal justo donde el planificador conduce, el fantasma deja de ser fantasma — el plan ciego (recto hacia el filón) se vuelve *ejecutable en la verdad*, así que el modelo ciego y la verdad coinciden a lo largo del camino operativo, que es el único camino que te puede pasar factura.

Este resultado me gusta porque mata un atajo tentador. Si estás auditando un modelo sintetizado, no puedes mirar la geometría de lo que se equivocó — ni siquiera un invariante tan robusto como "¿hay un agujero?" — y concluir nada sobre la consecuencia. Tienes que preguntar por dónde puede ir lo que planifica contra él.

## ¿Y si simplemente puedes rodearlo?

El anillo es un instrumento bidimensional, y en dos dimensiones una banda envolvente es un muro: si corta el camino, no entra nada. Es razonable desconfiar de eso, porque hace que "el planificador no puede llegar" parezca una propiedad del dibujo y no un hallazgo. Así que el paper corre el caso en el que rodear **sí** es posible: un toro sólido en $\mathbb{R}^3$ colocado entre la salida y el filón, que no separa el espacio en absoluto. Hay un camino explícito que lo rodea y llega al otro lado sin tocarlo nunca.

<figure class="cwm-fig">
<!-- fig:torus-3d -->
<svg viewBox="0 0 600 250" role="img" aria-label="The same solid torus in three dimensions: with the route through its hole it costs 0.019, and moved so the route runs into the tube it costs 0.898 — while a contact-free path around it still exists">
<defs><marker id="t3-mk" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<defs><marker id="t3b-mk" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<defs><marker id="t3b-mk2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#22d3ee"/></marker></defs>
<rect x="10" y="22" width="285" height="176" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="152.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">the route threads the hole</text>
<ellipse cx="152.0" cy="172.0" rx="46" ry="7" fill="#000" fill-opacity="0.30"/>
<defs><clipPath id="t3-far"><rect x="152.0" y="2.0" width="72.0" height="204.0"/></clipPath><clipPath id="t3-near"><rect x="80.0" y="2.0" width="72.0" height="204.0"/></clipPath></defs>
<path d="M120.0,104.0 A32.0,62.0 0 1,0 184.0,104.0 A32.0,62.0 0 1,0 120.0,104.0 Z" fill="none" stroke="#6366f1" stroke-width="20" stroke-opacity="0.55" clip-path="url(#t3-far)"/>
<circle cx="34.0" cy="104.0" r="3.4" fill="#f8fafc"/>
<line x1="40.0" y1="104.0" x2="254.0" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#t3-mk)"/>
<path d="M120.0,104.0 A32.0,62.0 0 1,0 184.0,104.0 A32.0,62.0 0 1,0 120.0,104.0 Z" fill="none" stroke="#6366f1" stroke-width="20" clip-path="url(#t3-near)"/>
<polygon points="268.0,91.0 264.6,99.4 255.6,100.0 262.6,105.8 260.4,114.5 268.0,109.7 275.6,114.5 273.4,105.8 280.4,100.0 271.4,99.4" fill="#fbbf24"/>
<text x="152.0" y="186.0" font-size="15" fill="#6366f1" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  0.019</text>
<text x="152.0" y="214.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">it never touches the object</text>
<rect x="305" y="22" width="285" height="176" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="447.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">the same torus, moved</text>
<ellipse cx="447.0" cy="172.0" rx="86" ry="7" fill="#000" fill-opacity="0.30"/>
<defs><clipPath id="t3b-far"><rect x="323.0" y="34.0" width="248.0" height="70.0"/></clipPath><clipPath id="t3b-near"><rect x="323.0" y="104.0" width="248.0" height="70.0"/></clipPath></defs>
<path d="M363.0,104.0 A84.0,30.0 0 1,0 531.0,104.0 A84.0,30.0 0 1,0 363.0,104.0 Z" fill="none" stroke="#f43f5e" stroke-width="21" stroke-opacity="0.55" clip-path="url(#t3b-far)"/>
<circle cx="329.0" cy="104.0" r="3.4" fill="#f8fafc"/>
<line x1="335.0" y1="104.0" x2="365.0" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#t3b-mk)"/>
<path d="M350.0,99.0 L360.0,109.0 M360.0,99.0 L350.0,109.0" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
<path d="M337.0,104.0 Q447.0,16.0 549.0,104.0" fill="none" stroke="#22d3ee" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#t3b-mk2)"/>
<text x="447.0" y="36.0" font-size="9.5" fill="#22d3ee" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">a way around, contact-free</text>
<path d="M363.0,104.0 A84.0,30.0 0 1,0 531.0,104.0 A84.0,30.0 0 1,0 363.0,104.0 Z" fill="none" stroke="#f43f5e" stroke-width="21" clip-path="url(#t3b-near)"/>
<polygon points="563.0,91.0 559.6,99.4 550.6,100.0 557.6,105.8 555.4,114.5 563.0,109.7 570.6,114.5 568.4,105.8 575.4,100.0 566.4,99.4" fill="#fbbf24"/>
<text x="447.0" y="186.0" font-size="15" fill="#f43f5e" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  0.898</text>
<text x="447.0" y="214.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the route runs into the tube</text>
<text x="300.0" y="238.0" font-size="11" fill="#f8fafc" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">nothing here is sealed off  ·  same object, same contact rarity 0.0033</text>
</svg>
<!-- /fig:torus-3d -->
<figcaption>El control tridimensional, donde rodear sí es posible. Izquierda: la ruta planificada enhebra el agujero del toro y el modelo ciego cuesta 0.019. Derecha: el mismo objeto, movido para que la ruta se meta en el tubo, y cuesta 0.898 — con la misma rareza de contacto, 0.0033, y la misma topología trivial. El camino que lo rodea sin tocarlo es la razón de que aquí nada sea reach-null, y por tanto de que el teorema de infalsabilidad no tenga sobre qué actuar.</figcaption>
</figure>


Ahí se separan dos cosas, y es la descomposición más limpia del paper.

**El gauge desaparece.** Ya nada es reach-null — no hay una región que un planificador competente no pueda consultar por demostración — así que no queda infalsabilidad exacta que tener. En términos de certificación, este modo vuelve a ser meramente raro, que es donde viven los papers anteriores.

**El peligro no.** Lo gobierna una sola cosa: dónde cae el toro respecto al camino óptimo. Pon el *agujero* en el eje salida–filón, de modo que el plan lo enhebre, y el coste de juego del modelo ciego es 0.019. Mueve el *tubo* a ese eje, de modo que el plan lo roce, y es 0.898 — con la misma rareza (0.0033) y la misma topología trivial.

Así que el eslogan se parte en dos, y esta es la versión que yo me llevaría puesta. **El peligro es relativo al camino**: una omisión que está en el camino se explota, encierre algo o no. **La infalsabilidad exacta es relativa a la separación**: solo una frontera envolvente fabrica una región que ningún gate de muestreo podrá consultar jamás. El anillo confunde las dos porque allí la frontera envolvente y el camino bloqueado son el mismo objeto. El toro es lo que las separa.

## ¿Puede el bucle reparar un anillo?

La misma pregunta que la última vez, con una forma más difícil. Tres familias de modelos (GPT-5.x en dos tamaños, Qwen, Claude), el mismo bucle de sintetizar-refinar-aceptar, 903 artefactos en 39 condiciones al final.

**Desde fuera del anillo, nada recupera la región.** Ni un artefacto codifica la banda. Lo que escriben en su lugar son ajustes puntuales supersticiosos: un integrador más un comentario que hipotetiza una trampa diminuta y localizada, congelando por igualdad exacta de flotantes con el único estado de contacto que su muestra contenía. Uno de esos es mi ejemplar favorito de toda la serie — pasó su propio gate a 1.000, y la coordenada hardcodeada está a dos ulps de la misma trayectoria calculada con otra librería matemática. Su certificado era una propiedad del último bit de `sin` en la máquina que lo generó. Un gate independiente lo rechaza en cualquier plataforma.

Eso no es descuido de los modelos; es la teoría cumpliéndose. Desde fuera, la evidencia del anillo y la del disco son *idénticas camino a camino* — no hay observación que las separe — así que un resumen honesto de la evidencia solo puede informar del arco alcanzable.

**Desde dentro del agujero, sí ponen la topología correcta y no pueden fijarla.** Arranca al móvil dentro y el interior pasa a ser alcanzable, así que la omisión ya es falsable. Los artefactos ponen estructuras huecas, lazos, anillos — la forma correcta — y las tasas de aprobación del gate siguen siendo esencialmente cero, porque los radios de la banda no son números redondos y el gate quiere $10^{-9}$. La única recuperación certificada de veinte usó la única forma cuyo único parámetro libre está anclado en la especificación de la recompensa: el *complemento* de un disco cuyo radio es el del propio filón. El mejor reparador de otra familia escribió exactamente la misma forma.

La auditoría held-out es la parte que yo querría ver en el paper de otro. Al re-puntuar cada artefacto sobre un bloque de gate disjunto: la aceptación coincide con "la muestra de ese gate independiente también se perdió la banda" en **156 de 156** casos — una identidad exacta, artefacto a artefacto, cero fuera de la diagonal. Y de 214 aprobaciones en muestra, 121 fallan un gate independiente, y todas y cada una fallan *en un contacto con la banda*. Aprobar en muestra es consistencia con el conjunto de entrenamiento, y lo que omite es exactamente el modo.

## El sensor que guía el bucle tiene un límite de resolución

Para darle a la reparación su mejor oportunidad, alimenté cada intento con un resumen topológico honesto de su propia evidencia — número de clústeres, caja envolvente, y una estimación por homología persistente $\hat\beta_1$ de cuántos agujeros tiene la nube de contactos. Redacción congelada antes de cualquier ejecución, sin nombrar nunca una familia de formas.

Un resumen así es un **sensor**, y los sensores tienen resolución. Este informa $\hat\beta_1 = 1$ — un lazo cerrado — para todo canal más estrecho que unas dos unidades de arco, aunque el $\beta_1$ verdadero es 0 para *todo* $\gamma > 0$: un anillo con un hueco no es un lazo. El cambio ocurre alrededor de $\gamma = 1.8$.

Ese límite es geométrico y no presupuestario, y el paper demuestra la versión de dos lados: por debajo de una escala fijada por el mayor hueco angular de la muestra, el hueco es invisible para el detector, y por encima de otra escala explícita el lazo no puede sobrevivir. Un factorial sobre el presupuesto de puntos del detector (30, 90, 270) y la dosis de evidencia (40 y 160 rollouts) no mueve el cambio en absoluto.

Peor: en la frontera, más evidencia lo vuelve *más* seguro de la topología equivocada. Cuadruplica la dosis y la tasa de lazo falso sube de 1 de 5 semillas a 3 de 5, porque la muestra más densa rellena las capas adyacentes al canal y la persistencia de la barra espuria crece de 0.05 a 0.50 mientras el umbral del propio detector crece solo modestamente. Resolver un canal estrecho pide otra filtración, no una muestra mayor.

Y la topología que ponen los artefactos sigue al *resumen*, no a la verdad: las estructuras cerradas dominan donde el resumen dice "lazo cerrado" y casi desaparecen donde dice honestamente "arco" — 1 cerrada frente a 26 con forma de arco en $\gamma = 2.4$.

Ahora la parte que tengo que reportar contra mí mismo. Ese cruce es entre huecos distintos: el entorno y el resumen cambian juntos, así que no aísla la afirmación del resumen como la causa. Por eso pre-registré una intervención — diseño, script de análisis y regla de decisión comprometidos antes de que existiera ningún resultado — que voltea *solo* la línea de la afirmación: las mismas 60 semillas, evidencia idéntica bit a bit, cada otro byte del prompt fijo, la línea de $\hat\beta_1$ y su única frase interpretativa negadas, puntuado contra un control honesto generado de nuevo.

Resultado: de 11 pares discordantes, 9 se movieron en la dirección que predecía la afirmación y 2 en contra. Binomial exacta a dos colas $p = 0.065$, con el intervalo registrado sobre el efecto conteniendo un medio. Consistente en dirección, y por debajo del nivel al que me había comprometido. Así que el paper reporta la asociación y se niega a la frase causal, y el pre-registro es lo que hace que esa negativa no me cueste nada escribirla.

## La mitigación tiene que igualar la dimensión *y* la dirección

La defensa del paper companion contra este modo de fallo era una valla de desconfianza: cuando la predicción del modelo se contradice en algún estado, marca una bola a su alrededor y haz que el planificador trate como poco fiables los caminos imaginados que la cruzan. En el instrumento del parche, funcionaba.

En el anillo, a su radio calibrado, no hace absolutamente nada — y la razón es un argumento de conteo, no un detalle de implementación. Una valla puntual es un objeto de dimensión cero; la frontera alcanzable del anillo es una curva de dimensión uno de unas 16 unidades de mundo. Sellar una curva con bolas de radio $\varepsilon$ requiere tantas como diga el número de recubrimiento, longitud de frontera entre radio de valla, y el planificador concede entre dos y cuatro contactos por episodio mientras se redirige por el arco sin vallar.

<figure class="cwm-fig">
<!-- fig:fence-covering -->
<svg viewBox="0 0 600 246" role="img" aria-label="Point fences leave gaps along a one-dimensional boundary; a fence built from tangential segments covers it">
<defs><marker id="mk-fence" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<rect x="10" y="24" width="285" height="186" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="162.0" y="16.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">point fences</text>
<circle cx="162.0" cy="116.0" r="63.75" fill="none" stroke="#f43f5e" stroke-width="22.50" stroke-opacity="0.32"/>
<circle cx="122.8" cy="65.8" r="7.5" fill="none" stroke="#22d3ee" stroke-width="1.6" stroke-dasharray="3 2"/>
<circle cx="105.7" cy="86.1" r="7.5" fill="none" stroke="#22d3ee" stroke-width="1.6" stroke-dasharray="3 2"/>
<circle cx="105.7" cy="145.9" r="7.5" fill="none" stroke="#22d3ee" stroke-width="1.6" stroke-dasharray="3 2"/>
<circle cx="122.8" cy="166.2" r="7.5" fill="none" stroke="#22d3ee" stroke-width="1.6" stroke-dasharray="3 2"/>
<line x1="48.0" y1="116.0" x2="144.0" y2="116.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-fence)"/>
<text x="162.0" y="196.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">it re-routes through an unfenced arc</text>
<polygon points="162.0,101.8 158.3,110.9 148.4,111.6 156.0,117.9 153.6,127.5 162.0,122.3 170.4,127.5 168.0,117.9 175.6,111.6 165.7,110.9" fill="#fbbf24"/>
<rect x="305" y="24" width="285" height="186" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="457.0" y="16.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">dimension-matched</text>
<circle cx="457.0" cy="116.0" r="63.75" fill="none" stroke="#f43f5e" stroke-width="22.50" stroke-opacity="0.32"/>
<polyline points="433.1,56.9 429.1,58.7 425.1,60.8 421.4,63.1 417.8,65.8 414.3,68.6 411.1,71.7 408.2,75.0 405.4,78.5 402.9,82.2 400.7,86.1 398.8,90.1 397.1,94.2 395.7,98.4 394.6,102.7 393.9,107.1 393.4,111.6 393.2,116.0 393.4,120.4 393.9,124.9 394.6,129.3 395.7,133.6 397.1,137.8 398.8,141.9 400.7,145.9 402.9,149.8 405.4,153.5 408.2,157.0 411.1,160.3 414.3,163.4 417.8,166.2 421.4,168.9 425.1,171.2 429.1,173.3 433.1,175.1" fill="none" stroke="#22d3ee" stroke-width="14.2" stroke-opacity="0.55" stroke-linecap="round"/>
<line x1="343.0" y1="116.0" x2="361.8" y2="116.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-fence)"/>
<path d="M363.5,111.0 L373.5,121.0 M373.5,111.0 L363.5,121.0" stroke="#22d3ee" stroke-width="2.4" stroke-linecap="round"/>
<text x="457.0" y="196.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">no unfenced arc left to use</text>
<polygon points="457.0,101.8 453.3,110.9 443.4,111.6 451.0,117.9 448.6,127.5 457.0,122.3 465.4,127.5 463.0,117.9 470.6,111.6 460.7,110.9" fill="#fbbf24"/>
<text x="300.0" y="232.0" font-size="11" fill="#f8fafc" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">sealing a curve with balls costs boundary length / fence radius</text>
</svg>
<!-- /fig:fence-covering -->
<figcaption>El argumento de recubrimiento, dibujado. La banda se ve tenue porque el planificador no la ve — solo ve las vallas que le han dado. Las vallas puntuales dejan arcos sin cubrir y el camino imaginado se redirige por uno de ellos; una valla construida a lo largo de la dimensión de la propia frontera no deja ninguno, y por eso funciona tras dos lecciones en vez de nunca.</figcaption>
</figure>


<table class="cwm-table">
<thead><tr><th>Defensa</th><th style="text-align:right">coste de juego</th><th>Por qué</th></tr></thead>
<tbody>
<tr><td>Vallas puntuales, radio calibrado</td><td class="n">0.999 → 1.003</td><td>recubrimiento 0-dimensional de una frontera 1-dimensional</td></tr>
<tr><td>Vallas puntuales, radio 4×</td><td class="n">0.999 → 0.742</td><td>alivio parcial cuando las bolas alcanzan la escala de la geometría</td></tr>
<tr><td>Valla de dimensión igualada, por episodio</td><td class="n">0.999 → 0.957</td><td>forma correcta, olvidada cada episodio</td></tr>
<tr><td><strong>Dimensión igualada, persistida</strong></td><td class="n">0.999 → <strong>0.058</strong></td><td>dos lecciones en total, retornos iguales a la verdad desde el episodio 2</td></tr>
<tr><td>Cualquier valla, modo inventado</td><td class="n">1.769 → 1.769</td><td>salta 18.6 veces por episodio y no cambia nada</td></tr>
<tr><td><strong>Parche de libertad, modo inventado</strong></td><td class="n">1.769 → <strong>0.029</strong></td><td>el certificado dual: descongelar donde el modelo era demasiado pesimista</td></tr>
</tbody></table>

Las dos últimas filas son las que no vi venir. Apunta la misma maquinaria al error *opuesto* — un modelo que alucina un obstáculo donde el mundo está vacío, que cuesta más que el caso de la libertad fantasma, 1.769 — y toda variante de desconfianza es inerte por construcción: salta constantemente, porque al modelo se le contradice en todas partes, y no tiene nada que ofrecer, porque la desconfianza no puede fabricar la libertad que el planificador necesita. La defensa que funciona es la dual: marcar los estados donde el modelo quedó refutado por *demasiado pesimista* y dejar que la imaginación corra libre ahí. Eso lo derrumba de golpe.

Dos formas de estar equivocado, defensas opuestas, y el coste de cada defensa lo fija con qué frecuencia le miente su fallo. Una obstrucción falsa se refuta a sí misma en cada paso, así que un episodio le enseña al planificador todo. Una libertad falsa se refuta solo en la frontera rara, así que hay que pagar la cobertura. La misma geometría que el resto del paper, vista desde el lado del planificador.

## En *n* dimensiones los dos knobs se saturan

Una extensión, porque separa dos cosas que parecen una. Sustituye el anillo por una cáscara envolvente en $n$ dimensiones y barre $n$.

La **rareza** del contacto se derrumba geométricamente — un factor medido de 0.411 por dimensión, con la tasa exponencial demostrada para una interfaz de acción isótropa y una cota explícita para la del propio instrumento. Ese factor sale de un barrido de 10.000 rollouts del evento del cono, porque la calibración más barata se queda sin resolución antes: los contactos caen a 1 de cada 600 rollouts ya en $n = 4$, y a partir de ahí 600 rollouts no distinguen las celdas (0 de 600 en $n = 5$, otra vez 1 de 600 en $n = 6$). En cualquier caso la mis-síntesis se vuelve casi segura: la muestra del gate casi nunca contiene lo que la especificación omitió.

Mientras tanto el **peligro** no decae nada. Un planificador competente con interfaz de acción vectorial es explotado a `play_cost` ≈ 1.0 en todo $n \le 6$: conduce recto hacia el filón y se queda clavado. La rareza vive en el eje de la síntesis, la alcanzabilidad en el del juego, y son knobs independientes. Un modo encerrado en dimensión alta satura los dos — la omisión es casi segura y, cuando ocurre, plenamente explotable.

(Una nota de método que me costó un día: el mismo barrido con el conjunto de candidatos del planificador *escalar* mide peligro cero en todo $n$, y eso es una propiedad del planificador, no de la geometría. A sus candidatos les faltan las secuencias axiales que conducen recto hacia la cáscara. La competencia es una propiedad de la interfaz de acción, y una debilidad incidental del planificador puede esconder un modelo plenamente explotable.)

## Qué me llevo de esto

Un gate de muestreo certifica la restricción alcanzable de tu modelo y nada más. Esa es la serie entera en una frase, y el anillo es donde deja de ser un eslogan: más allá del alcance, el contenido del modelo es una elección libre que ningún test puede fijar y que ningún planificador te puede facturar — un gauge, y el artefacto de topología equivocada que lo aprovecha es a la vez indetectable e inofensivo, por teorema.

Lo que invierte la pregunta que deberías estar haciendo. No "¿es correcto el modelo?" sino **"¿el sitio donde se equivoca corta el alcance operativo de lo que planifica contra él?"** Tres consecuencias que me llevaría a un sistema real:

- **Alcance, no forma — y camino antes que separación.** La geometría e incluso la topología de una omisión no te dicen nada sobre la consecuencia por sí solas. El mismo agujero, movido de delante del objetivo a detrás, pasó de inofensivo a plenamente explotado sin cambiar un solo invariante. El toro lo afina en dos preguntas que conviene hacerse por separado: *¿la cruza algún plan?* decide el coste, y *¿encierra algo?* decide si algún test habría podido pillarlo. Una auditoría que clasifique los errores por tipo, y no por esas dos, está midiendo lo que no importa.
- **Tu resumen de la evidencia es un sensor con resolución.** Si algo en el bucle — un monitor, un informe, un paso de recuperación, un resumen topológico o estadístico — decide *qué forma tiene la evidencia*, su punto ciego se propaga a lo que queda certificado. El nuestro informa de un lazo cerrado para todo hueco más estrecho que dos unidades de arco, y los artefactos siguen al informe. Más datos lo empeoraron, no lo mejoraron.
- **Las vallas pagan dimensión y dirección.** Una defensa hecha de puntos no puede sellar una curva, y una defensa hecha de desconfianza no puede reparar el exceso de pesimismo. Iguala la dimensión de la frontera, persiste lo aprendido entre episodios, y ten claro contra cuál de los dos errores te defiendes — necesitan certificados opuestos.

Si quieres la versión formal — el cociente del gate, el teorema de infalsable-e-inofensivo, el sándwich de resolución de dos lados, la tasa en $n$ dimensiones, y qué partes están verificadas por máquina en Lean — está en el [preprint](https://arxiv.org/abs/XXXX.XXXXX), y el [código y todos los artefactos de resultados están abiertos](https://github.com/JaviMaligno/code-world-models).

---

*Preprint: "An Enclosed Mode Is a Gauge Choice" ([arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX)) · [código](https://github.com/JaviMaligno/code-world-models). Papers companion: [An Omitted Mode Is a Rare Rule](https://arxiv.org/abs/2608.17956) y el post sobre él — [Un LLM puede inferir la regla que olvidaste](/es/blog/infer-the-rule-in-one-dimension) — y [When a Verified World Model Still Loses](https://arxiv.org/abs/2607.14169).*
