---
title: "Un LLM puede inferir la regla que olvidaste — en una dimensión"
description: "Mi preprint anterior concluía que los LLM traducen reglas y no las infieren. En control continuo eso resulta falso para un muro y cierto para un círculo: el modelo repara una regla 1D omitida en 105 de 111 intentos, y no recupera ni una sola vez la versión 2D — a través de ocho intervenciones diseñadas para arreglarlo."
pubDate: 2026-08-20
tags: ["IA", "Machine Learning", "Testing", "Investigación", "Agentes"]
lang: es
translationKey: infer-the-rule-in-one-dimension
heroImage: "/blog/infer-the-rule-in-one-dimension.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/ARXIV_PENDING"
  - label: "Paper companion"
    url: "https://arxiv.org/abs/2607.14169"
---
Hace unas semanas escribí sobre [un modelo del mundo que pasa todos los tests y aun así pierde](/es/blog/verified-world-model-still-loses). De aquel trabajo, la conclusión de la que estaba más seguro era la mitad pesimista: los LLM hacen **traducción de reglas, no inferencia de reglas**. Codifican fielmente las reglas que les *cuentas*, y no infieren de forma fiable las que solo les *enseñas*. Lo intenté a conciencia — DAgger en condiciones, estados cosechados de la propia distribución, dos tamaños de modelo — y el modelo siguió ciego a la regla.

Esa conclusión era correcta para el escenario en el que la medí, y he pasado unas semanas más averiguando dónde deja de serlo. La versión corta: pasa de juegos de tablero a control continuo y un modelo actual **sí** infiere la regla omitida a partir de un puñado de ejemplos — de forma fiable, exacta, escribiendo la regla global verdadera en lugar de un ajuste de curva. Después dale a esa misma regla una dimensión más y la capacidad entera desaparece, a través de todas las intervenciones que supe diseñar en su contra. Está escrito como preprint, *An Omitted Mode Is a Rare Rule* (**[arXiv:PENDING](https://arxiv.org/abs/ARXIV_PENDING)**), con el [código y los artefactos de resultados abiertos](https://github.com/JaviMaligno/code-world-models).

<style>
.cwm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.cwm-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.cwm-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
.cwm-table{width:100%;border-collapse:collapse;margin:1.5rem 0;font-size:.92rem}
.cwm-table th,.cwm-table td{padding:.55rem .7rem;border-bottom:1px solid rgba(255,255,255,0.1);text-align:left}
.cwm-table th{color:#94a3b8;font-weight:600}
.cwm-table td.n{font-family:ui-monospace,'JetBrains Mono',monospace;text-align:right;white-space:nowrap}
</style>

## De los juegos de tablero a un carro con un muro

La razón para rehacer esto en control continuo es que la literatura de ese campo discrepa con la forma de mi resultado. El RL basado en modelos trata el error del modelo del mundo como **omnipresente y acumulativo** — un poco mal en todas partes, y peor según avanzas. Mi resultado discreto era lo contrario: error *localizado y decisivo*, exactamente cero en casi todo el espacio y catastrófico en un conjunto fino. Si esa geometría no sobrevive al salto a espacios de estados continuos, es una rareza de los juegos de tablero.

Así que: un carro sobre una vía, mesetas de recompensa sigmoides en ambos extremos, y un muro en alguna posición que detiene el carro en seco. Un planificador hace MPC de disparo aleatorio contra un modelo de la física sintetizado en Python. La especificación que recibe el LLM fija el integrador exactamente y simplemente **omite la cláusula del muro**. El gate es la misma idea que antes: sintetizar, refinar contra 40 rollouts muestreados, aceptar cuando cada transición coincide hasta $10^{-9}$.

Cuando la muestra de entrenamiento no contiene ningún contacto con el muro, el resultado es el titular del paper discreto reproducido en física, de punta a punta: el artefacto pasa el gate a 1.000, es exacto en todo lo que no sea el muro, está completamente ciego a él en las sondas, y el planificador que se fía conduce hacia la región fantasma, se queda **clavado en el muro en todos los episodios**, y replanifica el mismo plan condenado en cada paso durante el episodio entero — un retorno de unos 0.02 frente a los 17.77 del planificador con la verdad. Las 20 semillas de ese caso, en dos tamaños de modelo sobre bloques de muestra disjuntos, hicieron exactamente eso.

La frecuencia con la que ocurre eso tampoco es un misterio. Si un evento crítico tiene probabilidad $r$ bajo la ley de muestreo del gate y el gate saca $N$ rollouts, la probabilidad de que los $N$ lo pierdan es exactamente $(1-r)^N$ — sin asintóticas, sin más supuestos que rollouts i.i.d. En el knob principal $r = 0.0114$, así que $(1-r)^{40} = 0.63$; medido, 20 de 40 muestras independientes se perdieron el muro. El factor interesante del peligro es el que se calcula en forma cerrada.

## Esta vez, el modelo repara la regla

Aquí es donde se rompe mi conclusión anterior. Cuando el muro **sí** aparece en la muestra de entrenamiento — a menudo con un puñado de transiciones de contacto — GPT-5.x no se queda ciego ni ajusta una curva. Lee las transiciones que fallan y escribe la regla global verdadera:

```python
if x2 >= 8.0:
    return [8.0, 0.0]
```

No un parche local alrededor de los contactos observados. La regla, con la constante correcta, válida en todas partes.

En los dos instrumentos unidimensionales (el tope de posición del carro y el tope angular de un péndulo) lo hizo en **105 de 111 tiradas de síntesis con el modo presente**. Esas tiradas comparten bloques de rollouts muestreados, así que la unidad honesta es el bloque y no la tirada: todos los intentos fueron exactos en **50 de 56 bloques instrumento–stream**, con un intervalo exacto al 95% de [0.781, 0.960]. De las seis que fallaron, el gate cazó dos — parches locales supersticiosos ajustados a los contactos observados, que rechazó.

Eso es una reversión genuina del residuo de "traducción, no inferencia", y conviene decirlo claro en vez de enterrarlo: una discontinuidad manifestada numéricamente **sí** se aprende de los datos de una forma en que una regla simbólica de juego no lo hacía. Un muro se anuncia solo. Cuatro filas de 3.200 inclinan un ajuste lineal doce órdenes de magnitud; el LLM, en cambio, nombra la discontinuidad y la escribe.

## Entonces hice la regla bidimensional

La pregunta obvia es si esa capacidad va de *dimensión* o de *discontinuidad*. Así que construí un instrumento 4D: un móvil en un plano, dos parches circulares, y la regla es que entrar en un parche te congela. Mismo pipeline, mismo gate, misma tolerancia, mismos modelos. Ahora la regla es una región — tres constantes en lugar de una.

La reparación no sobrevive al cambio.

<figure class="cwm-fig">
<svg viewBox="0 0 600 210" role="img" aria-label="Reparación desde datos: 105 de 111 tiradas en reglas unidimensionales, 0 de 156 en regiones bidimensionales">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF" text-anchor="middle">
    <line x1="170" y1="30" x2="170" y2="175" stroke="rgba(255,255,255,0.1)"/>
    <line x1="380" y1="30" x2="380" y2="175" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <line x1="590" y1="30" x2="590" y2="175" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <text x="170" y="193">0%</text><text x="380" y="193">50%</text><text x="590" y="193">100%</text>
  </g>
  <text x="160" y="70" text-anchor="end" fill="#f8fafc" font-size="13">Regla 1D (muro, tope)</text>
  <rect x="170" y="56" width="397" height="26" rx="4" fill="#6366f1"/>
  <text x="360" y="74" fill="#0b0b12" font-size="12" font-weight="700" font-family="ui-monospace,monospace">105 / 111 tiradas</text>
  <text x="160" y="134" text-anchor="end" fill="#f8fafc" font-size="13">Regla 2D (disco, cuadrado)</text>
  <rect x="170" y="120" width="3" height="26" rx="1.5" fill="#f43f5e"/>
  <text x="184" y="138" fill="#f43f5e" font-size="12" font-family="ui-monospace,monospace">0 / 156 tiradas</text>
</svg>
<figcaption>El mismo pipeline, los mismos modelos, el mismo gate. En reglas duras unidimensionales el sintetizador recupera la regla verdadera desde unas pocas transiciones de contacto; en regiones bidimensionales no la recupera en ninguna de las 156 tiradas con el modo presente, repartidas sobre 20 muestras de gate distintas.</figcaption>
</figure>

Un cero es un número que merece desconfianza, así que: esas 156 tiradas se apoyan en 20 bloques de rollouts distintos, lo que acota la probabilidad de reparación por bloque en 0.168 con un 95% de confianza. No es "nunca" — es "ni una vez en la evidencia que tengo, y la evidencia es lo bastante ancha como para que eso signifique algo".

Lo que los artefactos escriben en su lugar es la parte interesante. El fallo dominante es la **reducción dimensional**: el disco se convierte en un semiplano en la posición correcta y con la forma equivocada — un umbral 1D, justo lo que funcionaba en el carro, aplicado a una regla que no lo es. Otros ajustan la envolvente convexa de las posiciones de congelación que observaron, o inventan una zona alrededor de las balizas de recompensa. Ni uno solo de los 76 artefactos que vieron un parche codificó el parche que vio.

## Ocho intervenciones, y qué sobrevive a ellas

Llegado ahí, lo honesto es atacar tu propia explicación. Si es la curvatura, los bordes rectos deberían arreglarlo. Si es el prompt, un prompt mejor debería arreglarlo. Así que lancé ocho intervenciones, cada una apuntando a una causa candidata, informando de lo que cada una cambiaba más allá de su objetivo.

<table class="cwm-table">
<thead><tr><th>Intervención</th><th style="text-align:right">Reparado</th><th>Qué descarta</th></tr></thead>
<tbody>
<tr><td>Prompt centrado en la región, 3× presupuesto</td><td class="n">0/40</td><td>el prompting y el presupuesto probados</td></tr>
<tr><td>Cuadrado alineado a los ejes, bordes rectos</td><td class="n">0/40</td><td>la curvatura del borde</td></tr>
<tr><td>Una segunda familia de modelos</td><td class="n">0/3</td><td>la idiosincrasia de una familia</td></tr>
<tr><td>Una banda en una sola coordenada</td><td class="n">0/40</td><td><em>nada — objetivo no identificable</em></td></tr>
<tr><td>Nombrar la variable que lee el disparador</td><td class="n">0/40</td><td>la ambigüedad de variable</td></tr>
<tr><td>El móvil se para dentro de la región</td><td class="n">0/40</td><td>que el interior sea inobservable</td></tr>
<tr><td>El móvil se proyecta sobre el borde</td><td class="n">0/40</td><td>lo mismo, con evidencia igualada</td></tr>
<tr><td>Mayor cobertura angular de los contactos</td><td class="n">0/40</td><td>la cobertura de la evidencia</td></tr>
</tbody></table>

<p style="color:#94a3b8;font-size:.82rem;margin:-.5rem 0 1.5rem;text-align:center">Cada fila es una campaña completa sobre los mismos 20 bloques muestreados. Ninguna restaura la reparación. La cuarta se registra en vez de contarse: en ese instrumento el objetivo es demostrablemente no identificable, así que un cero ahí no significa nada.</p>

Dos de ellas merecen una frase. El cuadrado era el que esperaba que funcionase — si el modelo sabe escribir `x2 >= 8.0`, una caja son cuatro de esos. Falló como una imagen especular del disco: los artefactos escribieron *discos* sobre evidencia cuadrada. Y la del interior apuntaba a un teorema del paper: como el parche congela al móvil en su posición anterior, ningún rollout ocupa nunca el interior de la región, así que una muestra solo puede atestiguar *entradas*. Esa censura es real, y yo estaba bastante convencido de que era la causa. Dos campañas la levantaron — una de ellas aportando once veces más evidencia del modo — y la reparación siguió en cero. Equivocarte sobre tu propio mecanismo es la parte del proceso que de verdad lo mueve.

## Qué falta realmente: una regla *localizada*

Las intervenciones son todas negativos, y un negativo solo vale lo que valga la garantía de que su objetivo era aprendible. Así que, dos controles positivos.

**Desde fuera del pipeline:** un ajuste algebraico de circunferencia por mínimos cuadrados — tres líneas de álgebra lineal, sin prior y sin modelo de lenguaje — sobre exactamente la evidencia que recibió el sintetizador. Recupera centro y radio con un margen de una décima en 12 de 20 muestras. Y como el instrumento permite ensanchar la apertura angular de los contactos manteniendo fijo su *número*, puedo dosificar la evidencia hasta que ese ajuste acierte en todas y cada una de las muestras.

<figure class="cwm-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Al subir la cobertura de evidencia el ajuste trivial pasa de 12 a 20 de 20 mientras el sintetizador se queda en 0 de 20">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF">
    <line x1="105" y1="40" x2="105" y2="185" stroke="rgba(255,255,255,0.14)"/>
    <line x1="105" y1="185" x2="575" y2="185" stroke="rgba(255,255,255,0.14)"/>
    <text x="95" y="45" text-anchor="end">20/20</text>
    <text x="95" y="189" text-anchor="end">0/20</text>
    <text x="160" y="207" text-anchor="middle">111°</text>
    <text x="340" y="207" text-anchor="middle">129°</text>
    <text x="520" y="207" text-anchor="middle">185°</text>
    <text x="340" y="230" text-anchor="middle" fill="#64748b">cobertura angular de la evidencia de contacto</text>
  </g>
  <polyline points="160,101 340,73 520,45" fill="none" stroke="#6366f1" stroke-width="2.5"/>
  <circle cx="160" cy="101" r="5" fill="#6366f1"/><circle cx="340" cy="73" r="5" fill="#6366f1"/><circle cx="520" cy="45" r="5" fill="#6366f1"/>
  <text x="536" y="42" fill="#818cf8" font-size="12" font-family="ui-monospace,monospace">20</text>
  <text x="160" y="92" fill="#818cf8" font-size="11" text-anchor="middle" font-family="ui-monospace,monospace">12</text>
  <text x="340" y="64" fill="#818cf8" font-size="11" text-anchor="middle" font-family="ui-monospace,monospace">16</text>
  <polyline points="160,185 340,185 520,185" fill="none" stroke="#f43f5e" stroke-width="2.5"/>
  <circle cx="160" cy="185" r="5" fill="#f43f5e"/><circle cx="340" cy="185" r="5" fill="#f43f5e"/><circle cx="520" cy="185" r="5" fill="#f43f5e"/>
  <text x="536" y="189" fill="#f43f5e" font-size="12" font-family="ui-monospace,monospace">0</text>
  <text x="170" y="127" fill="#818cf8" font-size="12">tres líneas de mínimos cuadrados</text>
  <text x="170" y="170" fill="#f43f5e" font-size="12">el sintetizador</text>
</svg>
<figcaption>Manteniendo fijo el número de contactos y ensanchando solo su apertura angular. El estimador trivial mejora hasta recuperar la región en todas las muestras; el sintetizador no la recupera en ninguna, en todas las dosis. El fallo no responde a la evidencia en absoluto.</figcaption>
</figure>

**Desde dentro del pipeline:** sustituir la cláusula que falta por una *parcial* que enuncia la forma y el efecto de la regla pero retiene las constantes. Dos niveles, y se separan por completo:

- Dada la forma de la región **y** sus centros, reteniendo solo el radio — un único número desconocido — el sintetizador lo infiere **exactamente en 20 de 20 semillas**, coincidiendo con la verdad con IoU 1.000 en todos los puntos de la rejilla de sondeo. Un artefacto incluso comenta "radio inferido de las transiciones proporcionadas".
- Dada la forma **sola**, reteniendo los centros: **0 de 20**.

Junto todo, eso sitúa el fallo con precisión, y es más estrecho y más raro que "2D es más difícil". No es la evidencia — tres líneas de álgebra lineal recuperan la región de la misma muestra. No es incapacidad de ajustar constantes — dada la localización, clava el radio con precisión de coma flotante. No es representacional — si le cuentas la regla, todas las variantes escriben el disco a gate 1.000 en cero iteraciones de refinamiento. Lo que el sintetizador no hace es **inducir una regla *localizada***: la forma sola no lo rescata, la forma más su localización sí. Cuando el gate rechaza la plantilla, memoriza los contactos en lugar de ajustarlos.

Y esto tampoco es una historia de código contra redes neuronales. Ejecuté el baseline aprendido más favorable que supe construir — la física verdadera fijada, aprendiendo solo la función de evento. En el carro iguala al código exactamente: recupera el umbral en 8.0 a partir de cuatro contactos, es exacto en coma flotante sobre 3.200 transiciones held-out, y pasa el mismo gate de $10^{-9}$. En el instrumento 2D recupera el parche cercano en 12 de 20 bloques y **ambos** parches en ninguno. El muro es fácil para todo; el círculo es difícil para todo lo que tenga que encontrarlo a partir de datos.

## Verificado, y equivocado de una forma nueva

Un resultado más, porque es el que me cambió la forma de leer un gate que pasa. Entre las reparaciones 1D, cuatro artefactos escribieron el tope correcto **y** un segundo tope inventado en el lado contrario — en un ángulo que sus propios rollouts de entrenamiento nunca alcanzan. Sus muestras no pueden refutar la invención, así que el gate los acepta a 1.000. Volví a puntuar los 1.034 artefactos versionados contra muestras de aceptación nuevas y disjuntas: un gate independiente cazó *uno* de esos cuatro, por suerte del sorteo. A los otros tres los condena una rejilla densa, no un rollout.

Esa es la tesis entera en miniatura, y lleva un teorema pegado. Como el modo congela al móvil, existe una clase completa de reglas equivocadas que coinciden con la verdad en todas las transiciones de todos los rollouts posibles — irrefutables a cualquier tamaño de muestra y cualquier tolerancia. En un instrumento el modelo grande escribe de forma fiable exactamente una regla así: diecinueve de sus veinte artefactos pasan el gate, un gate independiente y la propia sonda del paper, sin codificar la región en absoluto. El consuelo es que el mismo argumento los vuelve inofensivos: un modelo que solo se equivoca donde ningún planificador puede llegar no cuesta nada al jugar.

## Lo que me llevo de esto

La verificación por muestreo certifica tu modelo donde caen tus muestras. Ese era el punto del paper anterior, y sobrevive intacto al salto a control continuo — incluido el factor en forma cerrada de cuántas veces la muestra se pierde lo que importa.

Lo nuevo es la historia de la reparación, y es más estrecha de lo que yo habría supuesto en ambas direcciones. Un sintetizador capaz **sí** recupera una regla que le han enseñado, de forma exacta y global, cuando esa regla es un umbral en una variable. No recupera el mismo tipo de regla cuando encontrarla implica localizar una región, y no mejora con un prompt más fuerte, más presupuesto, geometría más plana ni más evidencia — probé las cuatro. Así que la regla práctica que daría es una cláusula más afilada que la del año pasado: **la cobertura de la frontera lo es todo, y "ya lo deducirá de los datos" es una apuesta que solo puedes hacer en una dimensión.** Todo lo que tenga forma, sigues teniendo que especificarlo.

Si quieres la versión formal — la ley exacta de fallo del gate, el presupuesto de volumen que separa los programas de los modelos Lipschitz, y el teorema de irrefutabilidad — está en el [preprint](https://arxiv.org/abs/ARXIV_PENDING), y el [código y todos los artefactos de resultados son abiertos](https://github.com/JaviMaligno/code-world-models).

---

*Preprint: "An Omitted Mode Is a Rare Rule" ([arXiv:PENDING](https://arxiv.org/abs/ARXIV_PENDING)) · [código](https://github.com/JaviMaligno/code-world-models). Paper companion: [When a Verified World Model Still Loses](https://arxiv.org/abs/2607.14169), y el post sobre él — [Un modelo del mundo puede pasar todos los tests y aun así perder](/es/blog/verified-world-model-still-loses).*
