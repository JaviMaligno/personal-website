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

> **Réplica de *SKILL.state: Scalable Long-Horizon Agent Skills* (Badhe, Tiwari y Chung, aceptado en EMNLP) con dos modelos y más de 500 episodios.** Cada número de este artículo es un recuento de decisiones, no un promedio de episodios, y dos resultados que ya estaban escritos con intervalos de confianza limpios los tumbaron las comprobaciones que cuento al final. Esas comprobaciones son la parte transferible.

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

SkillExecBench no tiene código público, así que el entorno de aquí es una reimplementación a partir de la descripción de su §4.1 —un almacén de 500 estanterías con registros densos de campos separados por barras—, igualada en **densidad de contexto** y no en contenido literal, y corriendo un 1,2–1,5x por encima de la suya. Dos modelos: Claude Haiku 4.5 y Claude Sonnet 5.

## La mitad que sí se replica

La curva de coste se reproduce exactamente. Prompt medio a T=50: SKILL.state **2.157 tokens**, plano desde T=10 (2.136) hasta T=50. ReAct: **16.437**, creciendo linealmente. O(1) contra O(T), como anuncian.

La mitad de la precisión no. A T=50, con prompts de 16k tokens y 172 eventos accionables por episodio, tres de los cuatro brazos sacan un 1,00 limpio:

| runtime | T=10 | T=25 | T=50 | paper, T=50 |
|---|---|---|---|---|
| ReAct | 1,00 | 1,00 | **1,00** | 0,88 |
| Memory | 1,00 | 0,96 | **0,75** | 0,93 |
| Stateful | 1,00 | 1,00 | **1,00** | 0,94 |
| SKILL.state | 1,00 | 1,00 | **1,00** | 0,96 |

El único brazo que se degrada es el que resume en prosa, y se degrada más que en el paper. Remedir la celda de SKILL.state con 3 seeds × 6 repeticiones da **18/18 exactos a 1,000, desviación cero**: no es una tirada afortunada.

El motivo merece nombrarse, porque gobierna el resto del trabajo: en esta tarea la información portante nunca está lejos. El hueco liberado que el agente tiene que reutilizar está a **1,9 posiciones del tope de la pila de media**, siete como mucho. Alargar el horizonte añade pasos sin alejar la información de su uso. Si quieres medir si un runtime recuerda, `T` no es la palanca.

## El recuento de tokens no es la factura

El paper compara **tokens**. Quien lo pone en producción compara **dinero**, y son cantidades distintas en cuanto activas la caché de prompt. Un transcript append-only es el prefijo cacheable ideal: cada paso reenvía exactamente lo que envió antes, más un sufijo. Un objeto de estado que muta invalida la caché desde el punto en que muta.

Anthropic cobra las lecturas de caché a 0,1x y las escrituras a 1,25x. Medido sobre episodios de T=50, con el transcript enviado en bloques inmutables por turno para que la caché pueda casar de verdad:

<figure class="wfs-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Tokens brutos frente a tokens facturados en cuatro runtimes. SKILL.state usa los menos tokens brutos, 109k, pero ReAct cae de 826k brutos a 152k facturados porque su transcript append-only cachea, así que la ventaja de 7,5x en tokens se queda en 1,4x en dinero.">
  <defs>
    <style>
      .cl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .cv { fill:#f8fafc; font:600 11px ui-monospace,'JetBrains Mono',monospace; }
      .ct { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .cm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="24" class="ct">Tokens de entrada por episodio, T=50</text>
  <rect x="222" y="32" width="11" height="9" fill="#475569"/><text x="238" y="40" class="cm">brutos</text>
  <rect x="286" y="32" width="11" height="9" fill="#2dd4bf"/><text x="302" y="40" class="cm">facturados</text>

  <g transform="translate(0,52)">
    <text x="126" y="12" class="cl" text-anchor="end">SKILL.state</text>
    <rect x="132" y="2" width="46" height="12" fill="#475569"/><text x="184" y="12" class="cv">109k</text>
    <rect x="132" y="18" width="46" height="12" fill="#2dd4bf"/><text x="184" y="28" class="cv">109k</text>
    <text x="228" y="28" class="cm">la caché ahorra 0%</text>
  </g>
  <g transform="translate(0,100)">
    <text x="126" y="12" class="cl" text-anchor="end">ReAct</text>
    <rect x="132" y="2" width="350" height="12" fill="#475569"/><text x="488" y="12" class="cv">826k</text>
    <rect x="132" y="18" width="64" height="12" fill="#2dd4bf"/><text x="202" y="28" class="cv">152k</text>
    <text x="246" y="28" class="cm">la caché ahorra 82%</text>
  </g>
  <g transform="translate(0,148)">
    <text x="126" y="12" class="cl" text-anchor="end">Memory</text>
    <rect x="132" y="2" width="133" height="12" fill="#475569"/><text x="271" y="12" class="cv">313k</text>
    <rect x="132" y="18" width="133" height="12" fill="#2dd4bf"/><text x="271" y="28" class="cv">313k</text>
    <text x="316" y="28" class="cm">la caché ahorra 0%</text>
  </g>
  <g transform="translate(0,196)">
    <text x="126" y="12" class="cl" text-anchor="end">Stateful</text>
    <rect x="132" y="2" width="370" height="12" fill="#475569"/><text x="508" y="12" class="cv">873k</text>
    <rect x="132" y="18" width="370" height="12" fill="#2dd4bf"/><text x="508" y="28" class="cv">873k</text>
    <text x="132" y="46" class="cm">mismo contenido que ReAct, con el bloque de estado delante — 5,7x la factura</text>
  </g>
</svg>
<figcaption>Todo método que comprime reescribe su prefijo, y reescribir el prefijo mata la caché. El único brazo que cachea es el que nunca toca lo que ya envió.</figcaption>
</figure>

**La ventaja de SKILL.state pasa de 7,54x en tokens brutos a 1,39x en dinero.** Y los dos órdenes no coinciden: por tokens es SKILL.state < Memory < ReAct < Stateful; por dinero es SKILL.state < **ReAct** < Memory < Stateful.

La fila de Stateful es la que hay que retener. Manda casi exactamente lo que manda ReAct. Pone un bloque de estado mutante delante del transcript en vez de detrás —que es donde lo coloca la plantilla del Apéndice A.3 del propio paper— y paga **5,7 veces más** por ello. El orden del prompt es una variable de coste de primer orden.

Dos cosas acotan esto. La caché tiene una longitud mínima de prefijo, y el procedimiento usado aquí (~1.300 tokens) queda por debajo: medido directamente, Haiku 4.5 no cachea un bloque de sistema de ~2.200 tokens y sí cachea uno de ~4.200. Con un procedimiento más largo, los cuatro brazos cachearían su parte estática y el 1,39x se movería. La dirección es aritmética y se sostiene igual; la magnitud pertenece a esta longitud de prompt y a este modelo.

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
<svg viewBox="0 0 600 230" role="img" aria-label="Porcentaje de pasos dependientes en los que se aplicó la corrección retroactiva. Con el transcript completo, Haiku la aplica en 3 de 44 pasos y Sonnet en 15 de 38. Con estado explícito, los dos modelos la aplican en todos: 44 de 44 y 49 de 49.">
  <defs>
    <style>
      .pl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .pv { fill:#f8fafc; font:600 11.5px ui-monospace,'JetBrains Mono',monospace; }
      .pt { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .pm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .ph { fill:#fbbf24; font:600 11.5px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="24" class="pt">Pasos dependientes en los que se aplicó la corrección</text>
  <text x="16" y="42" class="pm">seeds 4, 10 y 6 · 2 repeticiones · excluidos los episodios con &gt;3 respuestas truncadas</text>

  <line x1="150" y1="56" x2="150" y2="196" stroke="rgba(255,255,255,0.12)"/>
  <line x1="530" y1="56" x2="530" y2="196" stroke="rgba(255,255,255,0.12)"/>
  <text x="150" y="212" class="pm" text-anchor="middle">0%</text>
  <text x="530" y="212" class="pm" text-anchor="middle">100%</text>

  <text x="16" y="70" class="ph">Haiku 4.5</text>
  <g transform="translate(0,76)">
    <text x="144" y="11" class="pl" text-anchor="end">ReAct</text>
    <rect x="150" y="1" width="26" height="13" rx="2" fill="#64748b"/>
    <text x="184" y="12" class="pv">3/44 — 6,8%</text>
  </g>
  <g transform="translate(0,96)">
    <text x="144" y="11" class="pl" text-anchor="end">SKILL.state</text>
    <rect x="150" y="1" width="380" height="13" rx="2" fill="#2dd4bf"/>
    <text x="404" y="12" class="pv" style="fill:#0f172a">44/44 — 100%</text>
  </g>

  <text x="16" y="140" class="ph">Sonnet 5</text>
  <g transform="translate(0,146)">
    <text x="144" y="11" class="pl" text-anchor="end">ReAct</text>
    <rect x="150" y="1" width="150" height="13" rx="2" fill="#64748b"/>
    <text x="308" y="12" class="pv">15/38 — 39,5%</text>
  </g>
  <g transform="translate(0,166)">
    <text x="144" y="11" class="pl" text-anchor="end">SKILL.state</text>
    <rect x="150" y="1" width="380" height="13" rx="2" fill="#2dd4bf"/>
    <text x="404" y="12" class="pv" style="fill:#0f172a">49/49 — 100%</text>
  </g>
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

## El instrumento, y dos resultados que se llevó por delante

Un experimento sobre agentes produce números esté midiendo algo o no, y el modo de fallo no es el ruido. Es un resultado limpio.

Dos hallazgos de este proyecto estaban escritos del todo —tablas, intervalos de confianza que no se solapaban, un mecanismo— antes de que los retiraran comprobaciones que no cuestan nada. Las dos hacen falta en cualquier réplica de este tipo:

**Calcula el suelo antes que el efecto.** Simula un agente perfecto salvo que ignora exactamente lo que quieres medir. En la sonda de la corrección, ese agente saca 0,931, 0,893 y 1,000 en las seeds 0, 1 y 2 — así que el efecto máximo posible en esas seeds promedia 0,06, y una seed con suelo 1,000 no aporta información ninguna. Una separación medida de **+0,199** en esas seeds era, por tanto, imposible antes de mirar qué la causaba. La causa era truncamiento: el brazo del transcript perdía de 8 a 19 respuestas de 50 por el tope de salida, y una respuesta cortada antes de su línea `Action:` es un paso sin acción, que puntúa como error.

**Cuenta los pasos sin acción aparte de los pasos con acción incorrecta.** Son sucesos distintos con arreglos distintos, y promediarlos juntos es lo que permitió que un artefacto de presupuesto pareciera uno cognitivo. Subir el tope tampoco lo arregla: en el mismo escenario, 600 tokens dieron 19 respuestas truncadas, 1.500 dieron 11 y 4.000 dieron 18. Un presupuesto de salida fijo penaliza al brazo cuyo prompt crece, porque sus respuestas crecen con el transcript — y el paper original reporta que ReAct se degrada al crecer `T` sin reportar truncamiento.

**Descompón el score por el tipo de paso que promedia.** Un segundo entorno, construido como control de dominio, reportó una interacción con cambio de signo entre modelos y con intervalos disjuntos en las dos separaciones. Instrumentado, los cuatro brazos acertaban la regla portante — 12/12, 14/15, 12/13 y todos. Solo 5 de 34 pasos accionables probaban la regla, una política ciega sacaba 0,853, y el efecto reportado vivía entero en los pasos rutinarios y en los parches fuera de esquema. La sección se retiró completa.

**Y conoce tu suelo de ruido.** La misma seed, prompt idéntico byte a byte, ocho repeticiones: una seed alternó acierto y fallo ocho veces seguidas. El acierto de un solo paso arrastra decenas de puntos de ruido de muestreo; un promedio sobre ~170 eventos casi ninguno; la contabilidad de tokens ninguno. Todo lo que se cayó en este proyecto era de la primera clase, y lo que sobrevivió es de la segunda y la tercera.

## Lo que me llevo

- **El eje que se anuncia no es el eje.** Cuánto contexto conservas apenas mueve la precisión en una tarea donde la información está cerca. Lo que la mueve es si el dato portante está presente, vigente y destilado en el momento de la decisión.
- **El estado explícito se gana su sitio cuando los datos se invalidan.** Un solo lugar que corregir le gana a un transcript que sostiene una afirmación y su desmentido — 93/93 contra 18/82, en los dos modelos. Si el mundo de tu agente solo acumula, esto te compra mucho menos.
- **Comprimir contexto y cachear contexto están en conflicto.** Todo método que reescribe su prefijo lo paga a precio completo. Mide la factura, no el recuento de tokens, y pon tu bloque mutante *después* de lo que quieras cachear.
- **Un esquema solo protege contra lo que su diseñador anticipó.** Un campo genérico para «ir apuntando cosas» midió indistinguible de no tener campo.

Todo esto está acotado a dos modelos, un entorno que discrimina y un procedimiento lo bastante corto como para quedar por debajo del umbral de caché. Lo que generaliza no es ningún número concreto sino la aritmética: comprueba que tu efecto cabe dentro del rango que tu efecto puede tener.

---

*Réplica de [SKILL.state: Scalable Long-Horizon Agent Skills](https://arxiv.org/abs/2608.26263) (Badhe, Tiwari y Chung, aceptado en EMNLP). Relacionados: [El andamiaje que pagas](/es/blog/the-scaffolding-you-pay-for), sobre intervenciones que cuestan más de lo que compran, y [El olvido que no mides](/es/blog/forgetting-you-dont-measure), sobre lo que esconde un número de benchmark.*
