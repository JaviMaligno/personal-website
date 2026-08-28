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

## Más allá del alcance, todo es gauge

La teoría en una frase. Si un gate acepta a todo candidato cuyas transiciones muestreadas coinciden, entonces la aceptación-con-certeza determina el modelo exactamente sobre el conjunto alcanzable de consultas — y *todo lo que queda más allá del alcance es gauge*, en el sentido del físico: una elección libre que no cambia ningún observable. Dos modelos que solo difieren ahí fuera son el mismo modelo para cualquier gate de muestreo.

En el anillo cerrado eso tiene un caso límite que cabe en la mano. El artefacto equivocado natural es un **disco relleno**: sin agujero, con todo el interior congelado. Se equivoca en la topología, no solo en los parámetros. Y es:

- **infalsable por cualquier gate de muestreo.** No "difícil de pillar" — hay demostración, y no necesita ningún supuesto sobre tamaño de muestra ni tolerancia. Como la banda congela al móvil al contacto, ningún rollout que empiece fuera puede acabar dentro del agujero, así que ninguna transición posible distingue el disco relleno de la verdad.
- **inofensivo bit a bit al jugar.** El planificador que se fía del disco relleno planifica idénticamente al que conoce la verdad: misma acción en cada paso, mismo retorno, mismo estado final, mismos contactos, semilla por semilla. Los episodios de MPC con semillas emparejadas lo confirman exactamente, no aproximadamente.

Así que certificación, corrección y consecuencia se separan por tres, no por dos. Este artefacto está certificado, es incorrecto y es gratis. Mis dos papers anteriores habían mostrado certificado-e-incorrecto-y-costoso, y certificado-e-incorrecto-e-infalsable; el anillo es donde "incorrecto" y "caro" se desacoplan del todo, con un teorema y no con una medida.

## Dos agujeros idénticos, peligro opuesto

Esa es la mitad tranquila. Ahora abre un canal en la banda — un hueco de anchura angular $\gamma$, mirando a la salida, para que el planificador pueda conducir por él.

La explotación se derrumba. Un barrido denso del modelo ciego programado a mano — 16 episodios de MPC emparejados por punto — pone el `play_cost` (cuánto retorno pierde el planificador por fiarse del modelo equivocado, normalizado contra el planificador con la verdad) en 0.999 con el anillo cerrado, en 0.139 con $\gamma = 0.1$, y en prácticamente cero desde $\gamma = 0.15$. Hay un codo, y está exactamente donde el canal se hace lo bastante ancho para que quepa un paso: con $\gamma = 0.1$ el arco del hueco mide unas 0.35 unidades de mundo, comparable al propio paso del planificador. El brazo de síntesis reproduce el derrumbe con sus propios artefactos ciegos explotados, en los dos tamaños de modelo y en el relevo de Claude: 0.348 en el codo, 0.029 ya en $\gamma = 0.6$.

Después coge el mismo canal, la misma anchura, el mismo primer número de Betti, y rótalo para que se esconda detrás del filón, donde ningún plan pasa nunca. Con $\gamma = 0.6$ el coste de juego del artefacto ciego es 1.116. Con $\gamma = 1.2$ es 1.116 otra vez — y con la banda completamente cerrada, 1.116 una vez más. No "parecido al" anillo cerrado: su número con cuatro decimales, porque es el mismo programa ciego frente al mismo mundo alcanzable.

<figure class="cwm-fig">
<svg viewBox="0 0 600 268" role="img" aria-label="Coste de juego frente a anchura del canal: tanto el barrido denso programado como los artefactos ciegos sintetizados se derrumban cuando el canal visible admite el paso del planificador, mientras el canal escondido de la misma anchura mantiene el valor de la banda cerrada, 1.116">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF">
    <line x1="98" y1="38" x2="98" y2="190" stroke="rgba(255,255,255,0.14)"/>
    <line x1="98" y1="190" x2="578" y2="190" stroke="rgba(255,255,255,0.14)"/>
    <text x="88" y="49" text-anchor="end">1.12</text>
    <text x="88" y="64" text-anchor="end">1.00</text>
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
  <text x="132" y="55" fill="#818cf8" font-size="11.5" font-family="ui-monospace,monospace">0.999</text>
  <text x="228" y="168" fill="#818cf8" font-size="11.5" font-family="ui-monospace,monospace">0.139</text>
  <circle cx="215" cy="145" r="5" fill="#22d3ee"/><circle cx="450" cy="186" r="5" fill="#22d3ee"/><circle cx="560" cy="187" r="5" fill="#22d3ee"/>
  <text x="228" y="141" fill="#22d3ee" font-size="11.5" font-family="ui-monospace,monospace">0.348</text>
  <circle cx="120" cy="46" r="5.5" fill="#f43f5e" fill-opacity="0.25" stroke="#f43f5e" stroke-width="2"/>
  <circle cx="450" cy="46" r="5.5" fill="#f43f5e"/><circle cx="560" cy="46" r="5.5" fill="#f43f5e"/>
  <line x1="120" y1="46" x2="560" y2="46" stroke="#f43f5e" stroke-width="2.2" stroke-dasharray="5 4"/>
  <text x="470" y="38" fill="#fb7185" font-size="11.5" font-family="ui-monospace,monospace">1.116</text>
  <text x="134" y="38" fill="#fb7185" font-size="11.5">banda cerrada</text>
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

- **Alcance, no forma.** La geometría e incluso la topología de una omisión no te dicen nada sobre la consecuencia por sí solas. El mismo agujero, movido de delante del objetivo a detrás, pasó de inofensivo a plenamente explotado sin cambiar un solo invariante. Así que una auditoría que clasifique los errores del modelo por tipo, y no por si un plan los cruza, está midiendo lo que no importa.
- **Tu resumen de la evidencia es un sensor con resolución.** Si algo en el bucle — un monitor, un informe, un paso de recuperación, un resumen topológico o estadístico — decide *qué forma tiene la evidencia*, su punto ciego se propaga a lo que queda certificado. El nuestro informa de un lazo cerrado para todo hueco más estrecho que dos unidades de arco, y los artefactos siguen al informe. Más datos lo empeoraron, no lo mejoraron.
- **Las vallas pagan dimensión y dirección.** Una defensa hecha de puntos no puede sellar una curva, y una defensa hecha de desconfianza no puede reparar el exceso de pesimismo. Iguala la dimensión de la frontera, persiste lo aprendido entre episodios, y ten claro contra cuál de los dos errores te defiendes — necesitan certificados opuestos.

Si quieres la versión formal — el cociente del gate, el teorema de infalsable-e-inofensivo, el sándwich de resolución de dos lados, la tasa en $n$ dimensiones, y qué partes están verificadas por máquina en Lean — está en el [preprint](https://arxiv.org/abs/XXXX.XXXXX), y el [código y todos los artefactos de resultados están abiertos](https://github.com/JaviMaligno/code-world-models).

---

*Preprint: "An Enclosed Mode Is a Gauge Choice" ([arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX)) · [código](https://github.com/JaviMaligno/code-world-models). Papers companion: [An Omitted Mode Is a Rare Rule](https://arxiv.org/abs/2608.17956) y el post sobre él — [Un LLM puede inferir la regla que olvidaste](/es/blog/infer-the-rule-in-one-dimension) — y [When a Verified World Model Still Loses](https://arxiv.org/abs/2607.14169).*
