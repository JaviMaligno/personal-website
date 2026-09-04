---
title: "Cuando el dato deja de ser cierto"
description: "Réplica de SKILL.state, un paper de EMNLP que sustituye la historia de conversación de un agente por un estado explícito y mutable. El ahorro en tokens es real y el ahorro en la factura no: 7,5x se queda en 1,4x en cuanto activas la caché. Y donde el estado explícito gana de forma aplastante es justo donde el paper predecía que perdería: 93 correcciones aplicadas de 93, frente a 18 de 82 con el transcript completo."
pubDate: 2026-09-12
tags: ["IA", "Agentes", "Context Engineering", "Evaluación", "Investigación"]
lang: es
translationKey: when-the-fact-stops-being-true
heroImage: "/blog/when-the-fact-stops-being-true.png"
linkedinImage: /blog/when-the-fact-stops-being-true-fig-3.png
---

<style>
.wfs-fig { margin: 2rem 0; }
.wfs-fig svg { width: 100%; height: auto; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.wfs-fig figcaption { margin-top: 0.6rem; font-size: 0.9rem; color: #94a3b8; line-height: 1.5; }
</style>

> **Réplica de *SKILL.state: Scalable Long-Horizon Agent Skills* (Badhe, Tiwari y Chung, aceptado en EMNLP) con dos modelos y más de 500 episodios.** Cada número de este artículo es un recuento de decisiones, no un promedio de episodios.

Un agente lee un evento en el paso 10: *el palé que registraste en el paso 3 nunca llegó a colocarse; esa estantería está vacía*. Veinte pasos después tiene que decidir dónde almacenar el siguiente palé. La respuesta correcta es la estantería que liberó la corrección.

Con el transcript entero en su contexto —el registro original, la corrección, y todo lo que hay en medio— Claude Haiku 4.5 acierta esa decisión **3 veces de 44**. Dándole en su lugar un objeto JSON de 200 caracteres, y ningún transcript, el mismo modelo acierta **44 de 44**.

Es el efecto más fuerte de toda la réplica, y el paper replicado predice lo contrario.

## Qué propone el paper

[*SKILL.state*](https://arxiv.org/abs/2608.26263) sustituye la historia de conversación append-only de un agente estilo ReAct por un estado de ejecución explícito y mutable. En cada paso el modelo recibe el procedimiento `P`, el estado actual `Σ_t` y la última observación `O_t`. Responde con un parche JSON y una acción. El parche se valida y se fusiona, `Σ_{t+1} = Σ_t ⊕ ΔΣ_t`, y el razonamiento que lo produjo se **descarta**. No se acumula nada.

La afirmación tiene dos mitades: más precisión en procedimientos largos, y un prompt que se mantiene O(1) en vez de crecer O(T).

<figure class="wfs-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Los cuatro runtimes comparados por lo que cada uno manda al modelo en el paso t: ReAct manda el transcript entero, Memory un resumen en prosa más una ventana de tres pasos, Stateful un objeto de estado seguido del transcript entero, y SKILL.state solo el objeto de estado y la última observación.">
  <defs>
    <style>
      .wl { fill:#e2e8f0; font:12px ui-sans-serif,system-ui; }
      .wm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .wh { fill:#f8fafc; font:600 12.5px ui-sans-serif,system-ui; }
      .wt { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .wc { font:10px ui-monospace,'JetBrains Mono',monospace; }
    </style>
  </defs>
  <text x="16" y="24" class="wt">Qué manda cada runtime en el paso t</text>
  <text x="16" y="42" class="wm">gris = crece con T · turquesa = acotado</text>

  <g transform="translate(16,58)">
    <text x="0" y="12" class="wh">ReAct</text>
    <rect x="0" y="20" width="120" height="16" rx="3" fill="#334155" stroke="#64748b"/>
    <text x="6" y="32" class="wc" fill="#cbd5e1">procedimiento</text>
    <rect x="0" y="40" width="120" height="42" rx="3" fill="#3f3f46" stroke="#64748b"/>
    <text x="6" y="56" class="wc" fill="#cbd5e1">transcript entero</text>
    <text x="6" y="70" class="wc" fill="#94a3b8">O(T)</text>
    <rect x="0" y="86" width="120" height="16" rx="3" fill="#164e4a" stroke="#2dd4bf"/>
    <text x="6" y="98" class="wc" fill="#5eead4">observación</text>
  </g>

  <g transform="translate(154,58)">
    <text x="0" y="12" class="wh">Memory</text>
    <rect x="0" y="20" width="120" height="16" rx="3" fill="#334155" stroke="#64748b"/>
    <text x="6" y="32" class="wc" fill="#cbd5e1">procedimiento</text>
    <rect x="0" y="40" width="120" height="42" rx="3" fill="#3f3f46" stroke="#64748b"/>
    <text x="6" y="56" class="wc" fill="#cbd5e1">resumen en prosa</text>
    <text x="6" y="70" class="wc" fill="#cbd5e1">+ ventana de 3</text>
    <rect x="0" y="86" width="120" height="16" rx="3" fill="#164e4a" stroke="#2dd4bf"/>
    <text x="6" y="98" class="wc" fill="#5eead4">observación</text>
  </g>

  <g transform="translate(292,58)">
    <text x="0" y="12" class="wh">Stateful</text>
    <rect x="0" y="20" width="120" height="16" rx="3" fill="#334155" stroke="#64748b"/>
    <text x="6" y="32" class="wc" fill="#cbd5e1">procedimiento</text>
    <rect x="0" y="40" width="120" height="16" rx="3" fill="#78350f" stroke="#f59e0b"/>
    <text x="6" y="52" class="wc" fill="#fbbf24">objeto de estado</text>
    <rect x="0" y="60" width="120" height="22" rx="3" fill="#3f3f46" stroke="#64748b"/>
    <text x="6" y="75" class="wc" fill="#cbd5e1">transcript entero</text>
    <rect x="0" y="86" width="120" height="16" rx="3" fill="#164e4a" stroke="#2dd4bf"/>
    <text x="6" y="98" class="wc" fill="#5eead4">observación</text>
  </g>

  <g transform="translate(430,58)">
    <text x="0" y="12" class="wh">SKILL.state</text>
    <rect x="0" y="20" width="120" height="16" rx="3" fill="#334155" stroke="#64748b"/>
    <text x="6" y="32" class="wc" fill="#cbd5e1">procedimiento</text>
    <rect x="0" y="40" width="120" height="16" rx="3" fill="#78350f" stroke="#f59e0b"/>
    <text x="6" y="52" class="wc" fill="#fbbf24">objeto de estado</text>
    <rect x="0" y="86" width="120" height="16" rx="3" fill="#164e4a" stroke="#2dd4bf"/>
    <text x="6" y="98" class="wc" fill="#5eead4">observación</text>
  </g>

  <text x="16" y="188" class="wl">El razonamiento que produjo el parche se descarta. En SKILL.state,</text>
  <text x="16" y="206" class="wl">todo lo que el agente sabrá jamás del paso 3 tiene que estar dentro</text>
  <text x="16" y="224" class="wl">del objeto de estado en el paso 4 — o se ha perdido.</text>
</svg>
<figcaption>Los cuatro brazos solo se diferencian en lo que va entre el procedimiento y la última observación. Stateful y ReAct llevan casi el mismo contenido; el orden en que lo llevan cuesta 5,7 veces más.</figcaption>
</figure>

SkillExecBench no tiene código público, así que el entorno de aquí es una reimplementación a partir de la descripción de su §4.1 —un almacén de 500 estanterías con registros densos de campos separados por barras—, igualada en **densidad de contexto** y no en contenido literal, y corriendo un 1,2–1,5x por encima de la suya en prompt medio.

Una diferencia es deliberada y conviene decirla ya: **su Tabla 1 corre sobre Gemini-3-Flash**, y el resto del paper sobre Gemma-4-31B-it y Qwen-3-8B-it. Esta réplica corre Claude Haiku 4.5 y Claude Sonnet 5. Cuando un resultado de aquí no coincide con el suyo, la primera explicación candidata es la familia de modelo, no el método — y decidir cuál de las dos es resulta ser casi todo el trabajo.

## La mitad que sí se replica

La curva de coste se reproduce exactamente. Prompt medio a T=50, en la misma unidad que reporta el paper —caracteres—: SKILL.state **2.157**, plano desde T=10 (2.136) hasta T=50, frente a sus 1.773. ReAct: **16.437** y creciendo linealmente, frente a sus 11.931. O(1) contra O(T), como anuncian, con un 1,2–1,4x de su densidad.

La mitad de la precisión no, y lo interesante es que no lo hace en ningún horizonte de los que ellos probaron. Su degradación es un efecto de escala —ReAct cae de 0,90 a T=10 hasta 0,74 a T=200—, así que la única forma honesta de comprobarlo es correr su rango entero.

<figure class="wfs-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Score frente al horizonte en los dos modelos. Gemini-3-Flash con transcript completo cae de 0,90 a T=10 hasta 0,74 a T=200, y su brazo de estado explícito de 1,00 a 0,94. Claude Haiku 4.5 se mantiene en 1,00 en los dos brazos en todos los horizontes, acabando en 0,987 el transcript y 1,00 el estado explícito.">
  <defs>
    <style>
      .sm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .st { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .ss { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .sl { fill:#e2e8f0; font:11px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="22" class="st">Su degradación, y la misma medida sobre Claude</text>
  <text x="16" y="40" class="ss">score frente al horizonte · ReAct sólido, SKILL.state discontinuo · 3 seeds cada uno</text>
  <line x1="88" y1="62.0" x2="568" y2="62.0" stroke="rgba(255,255,255,0.09)"/>
  <text x="80" y="66.0" class="sm" text-anchor="end">1.00</text>
  <line x1="88" y1="114.7" x2="568" y2="114.7" stroke="rgba(255,255,255,0.09)"/>
  <text x="80" y="118.7" class="sm" text-anchor="end">0.90</text>
  <line x1="88" y1="167.3" x2="568" y2="167.3" stroke="rgba(255,255,255,0.09)"/>
  <text x="80" y="171.3" class="sm" text-anchor="end">0.80</text>
  <line x1="88" y1="220.0" x2="568" y2="220.0" stroke="rgba(255,255,255,0.09)"/>
  <text x="80" y="224.0" class="sm" text-anchor="end">0.70</text>
  <text x="96" y="240" class="sm" text-anchor="middle">10</text>
  <text x="212" y="240" class="sm" text-anchor="middle">25</text>
  <text x="328" y="240" class="sm" text-anchor="middle">50</text>
  <text x="444" y="240" class="sm" text-anchor="middle">100</text>
  <text x="560" y="240" class="sm" text-anchor="middle">200</text>
  <polyline points="96,114.7 212,104.1 328,125.2 444,146.3 560,198.9" fill="none" stroke="#f59e0b" stroke-width="2.2" stroke-dasharray="none" stroke-linejoin="round"/>
  <circle cx="96" cy="114.7" r="3.4" fill="#f59e0b"/>
  <circle cx="212" cy="104.1" r="3.4" fill="#f59e0b"/>
  <circle cx="328" cy="125.2" r="3.4" fill="#f59e0b"/>
  <circle cx="444" cy="146.3" r="3.4" fill="#f59e0b"/>
  <circle cx="560" cy="198.9" r="3.4" fill="#f59e0b"/>
  <polyline points="96,62.0 212,62.0 328,83.1 444,93.6 560,93.6" fill="none" stroke="#f59e0b" stroke-width="2.2" stroke-dasharray="5 3" stroke-linejoin="round"/>
  <circle cx="96" cy="62.0" r="3.4" fill="#f59e0b"/>
  <circle cx="212" cy="62.0" r="3.4" fill="#f59e0b"/>
  <circle cx="328" cy="83.1" r="3.4" fill="#f59e0b"/>
  <circle cx="444" cy="93.6" r="3.4" fill="#f59e0b"/>
  <circle cx="560" cy="93.6" r="3.4" fill="#f59e0b"/>
  <polyline points="96,62.0 212,62.0 328,62.0 444,62.0 560,68.8" fill="none" stroke="#2dd4bf" stroke-width="2.2" stroke-dasharray="none" stroke-linejoin="round"/>
  <circle cx="96" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="212" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="328" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="444" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="560" cy="68.8" r="3.4" fill="#2dd4bf"/>
  <polyline points="96,62.0 212,62.0 328,62.0 444,62.0 560,62.0" fill="none" stroke="#2dd4bf" stroke-width="2.2" stroke-dasharray="5 3" stroke-linejoin="round"/>
  <circle cx="96" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="212" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="328" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="444" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="560" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <text x="300" y="262" class="sm" text-anchor="middle">horizonte T (pasos)</text>
  <line x1="120" y1="282" x2="150" y2="282" stroke="#f59e0b" stroke-width="2.2"/>
  <text x="156" y="286" class="sl">Gemini-3-Flash (su Tabla 1)</text>
  <line x1="330" y1="282" x2="360" y2="282" stroke="#2dd4bf" stroke-width="2.2"/>
  <text x="366" y="286" class="sl">Claude Haiku 4.5 (esta réplica)</text>
  <text x="120" y="298" class="ss">A T=200 su brazo de transcript está en 0,74. El nuestro en 0,987: falla una decisión de 600.</text>
</svg>
<figcaption>Su brazo de transcript se degrada con el horizonte exactamente como reportan. Sobre otra familia de modelo, en un entorno 1,2–1,4x más denso que el suyo y hasta el mismo T=200, no lo hace.</figcaption>
</figure>

| runtime | T=10 | T=25 | T=50 | T=100 | T=200 |
|---|---|---|---|---|---|
| ReAct | 1,00 | 1,00 | 1,00 | 1,00 | **0,99 ±0,02** |
| SKILL.state | 1,00 | 1,00 | 1,00 | 1,00 | **1,00 ±0,00** |
| Stateful | 1,00 | 1,00 | 1,00 | 0,99 ±0,02 | — |
| Memory | 1,00 | 0,96 | 0,75 | 0,72 | — |

A T=200 el brazo del transcript sostiene un prompt de 48.000 caracteres y 690 eventos accionables, y falla **una decisión de unas 600**. En Gemini-3-Flash ese mismo brazo falla una de cada cuatro. Remedir la celda de SKILL.state a T=50 con 3 seeds × 6 repeticiones da 18/18 exactos a 1,000, desviación cero, así que tampoco es una tirada afortunada.

La fila de Memory parecía al principio un artefacto y no un resultado: su runtime es el único que hace una segunda llamada por paso, y a T=100 perdió 23, 14 y 2 respuestas de 100 por el tope de salida en las tres seeds, puntuando 0,58, 0,67 y 0,91 en ese orden. Así que se remidió con **el doble de presupuesto de salida**:

| Memory | tope 600 | tope 1.200 | respuestas truncadas |
|---|---|---|---|
| T=50 | 0,75 | **0,79** | 3–10 de 50 |
| T=100 | 0,72 | **0,71** | 12–37 de 100 |

Doblar el presupuesto *subió* el truncamiento —23 respuestas cortadas pasaron a 34 en la misma seed— y dejó el score donde estaba. El modelo llena el presupuesto que le den, y el score bajo no es lo que costaban las respuestas cortadas. **Memory se degrada de verdad**, y se degrada más que en el paper.

El motivo por el que los otros tres aguantan merece nombrarse, porque gobierna todo lo que viene después: en esta tarea la información portante nunca está lejos. El hueco liberado que el agente tiene que reutilizar está a **1,9 posiciones del tope de la pila de media**, siete como mucho. Alargar el horizonte añade pasos sin alejar la información de su uso. Si quieres medir si un runtime recuerda, `T` no es la palanca — y de eso va el resto de este artículo.

## El recuento de tokens no es la factura

El paper compara **tokens**. Quien lo pone en producción compara **dinero**, y en cuanto la caché de prompt está activa son cantidades distintas. Un transcript append-only es el prefijo cacheable ideal: cada paso reenvía exactamente lo que envió antes, más un sufijo. Un bloque que muta invalida la caché desde el punto en que muta.

Hay un número que hay que medir antes de que nada de esto signifique algo: **el prefijo mínimo cacheable**. Por debajo de él no cachea nada. En Claude Haiku 4.5 son **4.096 tokens exactos** — un bloque de sistema de 3.984 tokens, enviado dos veces, no lee nada de caché; uno de 4.116 lo lee entero. Así que la respuesta depende de lo largo que sea tu procedimiento, y conviene tener los dos casos.

<figure class="wfs-fig">
<svg viewBox="0 0 600 322" role="img" aria-label="Coste de un episodio de 50 pasos con dos longitudes de procedimiento. Con procedimiento corto a SKILL.state le facturan 109k tokens y a ReAct 152k, una ventaja de 1,39x frente a 7,54x en tokens brutos. Con un procedimiento realista de 5.243 tokens SKILL.state baja a 64k y ReAct sube a 162k, ventaja de 2,51x. A Stateful le facturan unos 850k en las dos, cinco veces ReAct por contenido casi idéntico.">
  <defs>
    <style>
      .cl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .cv { fill:#f8fafc; font:600 11.5px ui-monospace,'JetBrains Mono',monospace; }
      .ct { fill:#fbbf24; font:600 12px ui-sans-serif,system-ui; }
      .cs { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .cm { fill:#94a3b8; font:10px ui-monospace,'JetBrains Mono',monospace; }
      .ch { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="22" class="ch">Lo que cuesta de verdad el mismo episodio de 50 pasos</text>
  <text x="16" y="40" class="cs">Claude Haiku 4.5 · solo entrada · 3 seeds</text>
  <text x="592" y="40" class="cs" text-anchor="end">$ por 1.000 episodios</text>
  <text x="16" y="70" class="ct">Procedimiento corto — 1.491 tokens</text>
  <text x="16" y="85" class="cs">por debajo del umbral de caché de 4.096: solo cachea la historia creciente de ReAct</text>
  <text x="126" y="110" class="cl" text-anchor="end">SKILL.state</text>
  <rect x="132" y="100" width="33.2" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="100" width="33.2" height="13" rx="2" fill="#2dd4bf"/>
  <text x="172.2" y="110" class="cm">109k</text>
  <text x="592" y="110" class="cv" text-anchor="end">$109</text>
  <text x="126" y="130" class="cl" text-anchor="end">ReAct</text>
  <rect x="132" y="120" width="251.9" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="120" width="46.4" height="13" rx="2" fill="#2dd4bf"/>
  <text x="390.9" y="130" class="cm">826k</text>
  <text x="592" y="130" class="cv" text-anchor="end">$152</text>
  <text x="126" y="150" class="cl" text-anchor="end">Memory</text>
  <rect x="132" y="140" width="95.5" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="140" width="95.5" height="13" rx="2" fill="#2dd4bf"/>
  <text x="234.5" y="150" class="cm">313k</text>
  <text x="592" y="150" class="cv" text-anchor="end">$313</text>
  <text x="126" y="170" class="cl" text-anchor="end">Stateful</text>
  <rect x="132" y="160" width="266.3" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="160" width="266.3" height="13" rx="2" fill="#2dd4bf"/>
  <text x="405.3" y="170" class="cm">873k</text>
  <text x="592" y="170" class="cv" text-anchor="end">$873</text>
  <text x="16" y="188" class="ct">Procedimiento realista — 5.243 tokens</text>
  <text x="16" y="203" class="cs">por encima del umbral: ahora cada brazo cachea su mitad estática</text>
  <text x="126" y="228" class="cl" text-anchor="end">SKILL.state</text>
  <rect x="132" y="218" width="91.5" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="218" width="19.5" height="13" rx="2" fill="#2dd4bf"/>
  <text x="230.5" y="228" class="cm">300k</text>
  <text x="592" y="228" class="cv" text-anchor="end">$64</text>
  <text x="126" y="248" class="cl" text-anchor="end">ReAct</text>
  <rect x="132" y="238" width="313.8" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="238" width="49.4" height="13" rx="2" fill="#2dd4bf"/>
  <text x="452.8" y="248" class="cm">1029k</text>
  <text x="592" y="248" class="cv" text-anchor="end">$162</text>
  <text x="126" y="268" class="cl" text-anchor="end">Memory</text>
  <rect x="132" y="258" width="150.7" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="258" width="78.7" height="13" rx="2" fill="#2dd4bf"/>
  <text x="289.7" y="268" class="cm">494k</text>
  <text x="592" y="268" class="cv" text-anchor="end">$258</text>
  <text x="126" y="288" class="cl" text-anchor="end">Stateful</text>
  <rect x="132" y="278" width="330.0" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="278" width="258.9" height="13" rx="2" fill="#2dd4bf"/>
  <text x="469.0" y="288" class="cm">1082k</text>
  <text x="592" y="288" class="cv" text-anchor="end">$849</text>
  <rect x="132" y="306" width="26" height="9" rx="2" fill="#2dd4bf"/>
  <text x="165" y="314" class="cs">lo que te facturan</text>
  <rect x="322" y="306" width="26" height="9" rx="2" fill="none" stroke="#64748b" stroke-dasharray="3 2"/>
  <text x="355" y="314" class="cs">tokens brutos</text>
</svg>
<figcaption>Los tokens brutos son el contorno discontinuo; la barra rellena es lo que te facturan. Todo método que comprime reescribe su prefijo, y reescribir el prefijo mata la caché — hasta que el procedimiento es lo bastante largo para cachear por sí solo.</figcaption>
</figure>

**Procedimiento corto — 1.491 tokens.** Por debajo del umbral, así que el procedimiento no cachea en ningún brazo. Solo cachea ReAct, y solo porque su transcript acumulado empuja el prefijo por encima de 4.096 él solo. **La ventaja de SKILL.state sobre ReAct cae de 7,54x en tokens brutos a 1,39x en dinero.** Y los órdenes tampoco coinciden: por tokens es SKILL.state < Memory < ReAct < Stateful; por dinero, SKILL.state < **ReAct** < Memory < Stateful.

**Procedimiento realista — 5.243 tokens.** Una referencia de los 112 campos que los eventos llevan de verdad, seis reglas de excepción, cinco ejemplos resueltos. Un procedimiento operativo real tiene esta forma. Ahora la mitad estática de cada brazo cachea, y pasan dos cosas:

- **SKILL.state se abarata un 41%: de $109 a $64 por cada mil episodios.** El procedimiento se hizo tres veces y media más largo y la factura bajó, porque cruzó el umbral. Memory pasa de ahorrar 0% a 48%, y Stateful de 0% a 22%.
- **La ventaja en dinero se ensancha a 2,51x mientras la de tokens brutos se estrecha a 3,43x.** En las dos condiciones el recuento bruto es la cifra equivocada para citar: dice 7,54x o 3,43x donde la factura dice 1,39x o 2,51x.

La fila sobre la que hay que actuar es Stateful. Manda casi exactamente lo que manda ReAct. Pone un bloque de estado mutante **delante** del transcript en vez de detrás —que es donde lo coloca la plantilla de su Apéndice A.3— y le facturan **$849 frente a $162 por cada mil episodios**. Mismo contenido, misma tarea, mismo score de 1,00. Una diferencia de 5,2x, y aguanta en las dos condiciones.

En Sonnet 5, con la entrada a 3x, eso son $2.546 frente a $486. Por cada mil episodios, el orden del prompt es una partida de cuatro cifras.

## Dónde gana de verdad el estado explícito

La limitación **L2** que declara el paper predice que el método fallará cuando el objetivo dependa de la procedencia: de *por qué* un dato está en el estado, no solo de qué dice. Así que la sonda natural es el caso en que la procedencia de un dato queda desmentida: el agente registra un palé en el paso `t`; en `t+10` una corrección dice que aquella colocación nunca se completó y la estantería está vacía. Desde ahí esa estantería es la libre más baja, y **todas las decisiones posteriores** dependen de haber aplicado la corrección.

Dos decisiones de diseño hacen que esto sea medible. La primera: la unidad de recuento no es el episodio ni la seed, sino el **paso dependiente** —cada paso posterior al aviso cuya acción correcta cambia por él—. La segunda: las seeds se eligen por rango medido antes de gastar nada. Un agente perfecto pero sordo, que lo ejecuta todo bien y simplemente nunca aplica la corrección, define el suelo, y las seeds difieren enormemente en cuánto sitio dejan por encima:

| seed | suelo del perfecto-pero-sordo | pasos dependientes |
|---|---|---|
| 0 | 0,931 | 2 |
| 1 | 0,893 | 3 |
| 2 | **1,000** | **0** |
| 4 | **0,522** | **11** |
| 6 | 0,846 | 4 |
| 10 | 0,759 | 7 |

Las seeds 4, 10 y 6 aportan 22 pasos dependientes por repetición. Las seeds 0, 1 y 2 aportan cinco entre las tres, y una de ellas no aporta ninguno. Calcular esa tabla cuesta cero llamadas a la API.

<figure class="wfs-fig">
<svg viewBox="0 0 600 218" role="img" aria-label="Cada decisión que dependía de la corrección retroactiva, una celda cada una. Con estado explícito están llenas las 44 celdas de Haiku y las 49 de Sonnet. Con el transcript completo, Haiku llena 3 de 44 y falla episodios enteros de golpe; Sonnet llena 15 de 38, aplicando todas las correcciones en un episodio y ninguna en el siguiente sobre el mismo escenario.">
  <defs>
    <style>
      .dl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .dt { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .dm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .dh { fill:#fbbf24; font:600 11.5px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="24" class="dt">Cada decisión que dependía de la corrección</text>
  <text x="16" y="42" class="dm">una celda = una decisión · los huecos separan episodios · seeds 4, 10 y 6</text>
  <text x="16" y="62" class="dh">Haiku 4.5</text>
  <text x="16" y="130" class="dh">Sonnet 5</text>
    <text x="184" y="80" class="dl" text-anchor="end">ReAct · 3/44</text>
    <rect x="192.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="199.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="206.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="213.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="220.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="227.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="234.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="247.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="254.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="261.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="268.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="275.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="282.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="289.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="302.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="309.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="316.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="323.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="330.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="337.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="344.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="351.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="358.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="365.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="372.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="385.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="392.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="399.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="406.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="413.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="420.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="427.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="434.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="441.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="448.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="455.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="468.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="475.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="482.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="489.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="502.0" y="70" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="509.0" y="70" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="516.0" y="70" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="523.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <text x="184" y="102" class="dl" text-anchor="end">SKILL.state · 44/44</text>
    <rect x="192.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="199.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="206.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="213.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="220.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="227.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="234.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="247.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="254.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="261.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="268.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="275.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="282.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="289.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="302.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="309.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="316.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="323.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="330.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="337.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="344.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="351.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="358.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="365.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="372.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="385.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="392.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="399.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="406.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="413.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="420.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="427.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="434.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="441.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="448.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="455.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="468.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="475.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="482.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="489.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="502.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="509.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="516.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="523.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <text x="184" y="148" class="dl" text-anchor="end">ReAct · 15/38</text>
    <rect x="192.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="199.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="212.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="219.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="226.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="233.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="240.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="247.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="254.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="267.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="274.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="281.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="288.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="295.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="302.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="309.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="322.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="329.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="336.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="343.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="350.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="357.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="364.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="371.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="378.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="385.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="392.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="405.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="412.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="419.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="426.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="433.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="440.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="447.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="454.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="461.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="468.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="475.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <text x="184" y="170" class="dl" text-anchor="end">SKILL.state · 49/49</text>
    <rect x="192.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="199.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="212.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="219.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="226.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="233.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="240.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="247.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="254.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="267.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="274.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="281.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="288.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="295.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="302.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="309.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="322.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="329.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="336.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="349.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="356.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="363.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="370.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="377.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="384.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="391.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="398.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="405.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="412.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="419.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="432.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="439.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="446.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="453.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="460.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="467.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="474.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="481.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="488.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="495.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="502.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="515.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="522.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="529.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="536.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="549.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="556.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="563.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="570.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
  <rect x="192" y="196" width="5.7" height="11" rx="1.4" fill="#2dd4bf"/>
  <text x="205" y="205" class="dm">corrección aplicada</text>
  <rect x="357" y="196" width="5.7" height="11" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
  <text x="370" y="205" class="dm">fallada</text>
</svg>
<figcaption>El estado explícito no falla ni una corrección en 93 pasos dependientes y dos modelos. El transcript completo, que contiene físicamente la corrección, la aplica en 18 de 82.</figcaption>
</figure>

Tres cosas que solo se ven contando decisiones en vez de promediando episodios:

**El brazo del transcript falla todo o nada por escenario.** En Haiku, los errores de cualquier otro tipo son exactamente cero en los seis episodios: sus *únicos* fallos son los pasos de la corrección, y los falla en bloque — 11 de 11, 7 de 7, 4 de 4. No es un agente que se despiste. Es un agente que ejecuta un procedimiento de 50 pasos sin una falta mientras nunca actualiza un dato. En Sonnet aparece el mismo patrón de forma bimodal: un episodio aplica los 11 y la repetición siguiente sobre el mismo escenario falla los 11.

**Más capacidad ayuda y no lo resuelve.** Sonnet con el transcript completo pasa de 6,8% a 39,5%. Reconcilia la contradicción mucho más a menudo, y sigue perdiendo tres decisiones de cada cinco.

**El estado explícito lo compra, y en Sonnet lo cobra en otro sitio.** Sonnet emitió 66 parches fuera de esquema en 8 episodios, agotando los reintentos en 10 pasos que acabaron sin ninguna acción, lo que le costó 21 errores de otros tipos. Haiku emitió cero. El acierto sobre la corrección es del 100% en ambos; la *fiabilidad* del runtime depende del modelo, y eso es una propiedad del método, no de la tarea.

El mecanismo no tiene ningún glamour. El estado explícito tiene exactamente un sitio donde vive el dato, y corregirlo es la operación que el runtime ya ejecuta en cada paso. El transcript no borra nada: sostiene a la vez la afirmación y su desmentido, y cada paso posterior tiene que resolver la contradicción otra vez desde cero.

**Tener un único sitio donde vive la verdad es una ventaja justo cuando la verdad cambia**, que es lo contrario de lo que predice L2, y replica en los dos modelos.

## Dónde el estado explícito no hace nada

La sonda complementaria: en el paso `t` el entorno anuncia que una estantería queda en cuarentena. En `t + k` esa estantería es la libre más baja y la acción correcta es saltársela. El paso dependiente y la estantería son idénticos para todo `k`; lo único que se mueve es la distancia entre la información y su uso. Aquí no se desmiente nada: el dato solo tiene que sobrevivir.

Y aquí el estado explícito, por sí solo, no hace absolutamente nada. Con `k=40`, Haiku con un objeto de estado y sin campo para el aviso: **0 de 24**. Lo que cambia el resultado no es el runtime, sino dónde se le permite vivir al dato:

<figure class="wfs-fig">
<svg viewBox="0 0 600 210" role="img" aria-label="Tres formas de mantener disponible un dato vigente, medidas en Haiku sobre 24 episodios pareados. Sin campo de esquema el agente actúa sobre él 0 veces de 24. Repitiendo el aviso original entero acierta 16 de 24. Repitiendo tres campos destilados acierta 24 de 24. Los tres intervalos de Wilson no se solapan.">
  <defs>
    <style>
      .rl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .rv { fill:#f8fafc; font:600 11.5px ui-monospace,'JetBrains Mono',monospace; }
      .rt { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .rm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="24" class="rt">Actuar sobre un dato vigente 40 pasos después</text>
  <text x="16" y="42" class="rm">Haiku 4.5 · 3 seeds × 8 repeticiones · pareado · barras = intervalo de Wilson al 95%</text>

  <line x1="215" y1="54" x2="215" y2="176" stroke="rgba(255,255,255,0.12)"/>
  <line x1="530" y1="54" x2="530" y2="176" stroke="rgba(255,255,255,0.12)"/>
  <text x="215" y="192" class="rm" text-anchor="middle">0%</text>
  <text x="530" y="192" class="rm" text-anchor="middle">100%</text>

  <g transform="translate(0,66)">
    <text x="196" y="12" class="rl" text-anchor="end">sin campo donde ponerlo</text>
    <line x1="215" y1="8" x2="259" y2="8" stroke="#64748b" stroke-width="3"/>
    <circle cx="215" cy="8" r="5" fill="#64748b"/>
    <text x="272" y="12" class="rv">0/24 — 0%</text>
  </g>
  <g transform="translate(0,106)">
    <text x="196" y="12" class="rl" text-anchor="end">aviso repetido entero</text>
    <line x1="363" y1="8" x2="473" y2="8" stroke="#f59e0b" stroke-width="3"/>
    <circle cx="426" cy="8" r="5" fill="#f59e0b"/>
    <text x="353" y="12" class="rv" style="fill:#fbbf24" text-anchor="end">16/24 — 67%</text>
  </g>
  <g transform="translate(0,146)">
    <text x="196" y="12" class="rl" text-anchor="end">tres campos, destilados</text>
    <line x1="486" y1="8" x2="530" y2="8" stroke="#2dd4bf" stroke-width="3"/>
    <circle cx="530" cy="8" r="5" fill="#2dd4bf"/>
    <text x="476" y="12" class="rv" style="fill:#5eead4" text-anchor="end">24/24 — 100%</text>
  </g>
</svg>
<figcaption>La disponibilidad explica dos tercios del efecto; la destilación explica el resto, y es el tercio que separa «casi siempre» de «siempre».</figcaption>
</figure>

Tres intervenciones, medidas pareadas sobre las mismas seeds:

- **Un campo de esquema que nombra el dato** (`quarantined_shelves`) lleva a Haiku de 0/24 al 100% y a Sonnet del 12% al 75%. Funciona porque quien diseñó el esquema anticipó exactamente ese dato, que es la limitación **L1** del paper, ahora con un número al lado.
- **Un campo genérico de texto libre** (`notes`, sin decir qué poner en él) saca 5/24 = 21% en Sonnet, intervalo 9–40%, estadísticamente indistinguible de no tener campo. En una seed saca 0/8, *peor* que nada.
- **Reinyectar el dato vigente en cada observación** lleva a Haiku de 0/24 a **24/24** y a Sonnet del 12% al 83%, y no exige anticipar nada.

Y lo último se parte todavía más. El aviso reinyectado lleva tres de los quince campos del aviso original, subidos al principio. Repetir el **aviso original entero** verbatim en su lugar, en la misma posición y con la misma cabecera, 981 caracteres en vez de 67, saca **16/24 = 67%**. Los tres intervalos de Wilson son disjuntos, y la versión destilada gana en las tres seeds.

O sea: poner el dato disponible recupera dos tercios del fallo. El tercio que queda es destilación — con el mismo dato presente en cada paso, enterrado entre catorce campos de metadatos operativos, el agente lo pasa por alto una de cada tres veces.

La versión práctica, acotada a lo que se midió (un entorno, `k=40`, la comparación de tres niveles solo en Haiku): **si un dato sigue vigente muchos pasos, reinyecta el campo, no el registro.** Un sistema que vuelca el documento entero al contexto se deja un tercio de los fallos sobre la mesa. Es la misma forma que el hallazgo de [El andamiaje que pagas](/es/blog/the-scaffolding-you-pay-for): la intervención que sobrevive es la que cambia qué está mirando el modelo, no la que le añade estructura alrededor.

## Cuatro comprobaciones que este tipo de experimento necesita

Un experimento sobre agentes produce números esté midiendo algo o no, y cuando sale mal el resultado no es ruido: es un resultado limpio. Dos hallazgos de aquí estaban escritos del todo, con tablas e intervalos que no se solapaban, hasta que estas cuatro los retiraron.

- **Calcula el suelo antes que el efecto.** Simula un agente perfecto salvo que ignora exactamente lo que quieres medir. En las seeds 0, 1 y 2 ese agente saca 0,931, 0,893 y 1,000, así que el efecto máximo posible ahí promedia 0,06 y una seed no aporta información ninguna. Una separación de **+0,199** medida en esas seeds era aritméticamente imposible antes de preguntarse qué la causaba.
- **Cuenta los pasos sin acción aparte de los pasos con acción incorrecta.** Ese +0,199 era truncamiento: el brazo del transcript perdía de 8 a 19 respuestas de 50 por el tope de salida, y una respuesta cortada antes de su línea `Action:` puntúa como error. Subir el tope no lo arregla — 600 tokens dieron 19 truncadas, 1.500 dieron 11 y 4.000 dieron 18. Un presupuesto de salida fijo penaliza al brazo cuyo prompt crece, y el paper reporta que ReAct se degrada al crecer `T` sin reportar truncamiento.
- **Descompón el score por el tipo de paso que promedia.** Un segundo entorno reportó una interacción con cambio de signo entre modelos, con intervalos disjuntos en las dos separaciones. Instrumentado, los cuatro brazos acertaban su regla portante; solo 5 de 34 pasos accionables la probaban, una política ciega sacaba 0,853, y el efecto reportado vivía entero en los pasos rutinarios. La sección se retiró.
- **Conoce tu suelo de ruido.** La misma seed, prompt idéntico byte a byte, ocho repeticiones: una seed alternó acierto y fallo ocho veces seguidas. El acierto de un solo paso arrastra decenas de puntos de ruido de muestreo; un promedio sobre ~170 eventos casi ninguno; la contabilidad de tokens ninguno.
## Lo que me llevo

- **El eje que se anuncia no es el eje.** Cuánto contexto conservas apenas mueve la precisión en una tarea donde la información está cerca. Lo que la mueve es si el dato portante está presente, vigente y destilado en el momento de la decisión.
- **El estado explícito se gana su sitio cuando los datos se invalidan.** Un solo lugar que corregir le gana a un transcript que sostiene una afirmación y su desmentido — 93/93 contra 18/82, en los dos modelos. Si el mundo de tu agente solo acumula, esto te compra mucho menos.
- **Comprimir contexto y cachear contexto están en conflicto.** Todo método que reescribe su prefijo lo paga a precio completo. Mide la factura, no el recuento de tokens, y pon tu bloque mutante *después* de lo que quieras cachear.
- **Un esquema solo protege contra lo que su diseñador anticipó.** Un campo genérico para «ir apuntando cosas» midió indistinguible de no tener campo.

Todo esto está acotado a dos modelos, un entorno que discrimina y un procedimiento lo bastante corto como para quedar por debajo del umbral de caché. Lo que generaliza no es ningún número concreto sino la aritmética: comprueba que tu efecto cabe dentro del rango que tu efecto puede tener.

---

*Réplica de [SKILL.state: Scalable Long-Horizon Agent Skills](https://arxiv.org/abs/2608.26263) (Badhe, Tiwari y Chung, aceptado en EMNLP). Relacionados: [El andamiaje que pagas](/es/blog/the-scaffolding-you-pay-for), sobre intervenciones que cuestan más de lo que compran, y [El olvido que no mides](/es/blog/forgetting-you-dont-measure), sobre lo que esconde un número de benchmark.*
