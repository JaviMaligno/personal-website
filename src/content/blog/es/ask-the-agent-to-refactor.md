---
title: "Pídele el refactor al agente. Escribir la regla no basta"
description: "Matt Pocock dice que hay que diseñar más abstracciones para los agentes de código y reforzarlas con un lint estricto. Probé si el propio agente puede ser el diseñador, con tres palancas sobre código repetido en 384 cadenas de tareas. Una regla escrita y un lint de duplicación ayudaron a un agente de tres. Pedir el refactor ayudó a los tres, y lo que compra es sobre todo búsqueda, no diseño."
pubDate: 2026-11-14
tags: ["Agentes", "Claude Code", "Codex", "Diseño de software", "Experimentos"]
lang: es
translationKey: ask-the-agent-to-refactor
repoUrl: "https://github.com/JaviMaligno/personal-website/tree/main/experiments/agent-abstractions"
heroImage: "/blog/ask-the-agent-to-refactor.png"
linkedinImage: "/blog/ask-the-agent-to-refactor-fig-2.png"
---

<style>
.abs-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.abs-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.abs-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

Codex recibe una tarea en una app de presupuestos: los pagos programados cuyo importe «está entre» dos valores deben planificarse en el peor extremo del rango, no en el punto medio. Busca, escribe *«I found three midpoint calculations»*, mueve las tres a una función compartida, pasa los tests y lo da por hecho: *«Previews, automatic posts, and synced rule actions all use the same calculation.»* Los tests pasan. El paso falla.

Había una cuarta copia. La plantilla de presupuesto calculaba el mismo punto medio, escrito de otra forma (`Math.round(num1 + num2) / 2`), y la búsqueda de Codex nunca la encontró. En cinco de ocho cadenas no llegó a abrir ese fichero, y en esas cinco se dejó la copia todas las veces.

Es justo el fallo que una abstracción debería evitar: si la regla vive en un solo sitio, no hay cuarta copia que olvidar. Matt Pocock defendió usar más abstracciones [en un tweet](https://x.com/mattpocockuk/status/2106425743479546343) que llevo dos semanas poniendo a prueba:

> My hot take from chatting to @poteto is that we should use MORE abstractions in the AI age. You can use them (combined with harsh lint rules) to reduce the design space available to the agent and constrain them only to good decisions. [...] Be braver! Design abstractions.

Él habla a las personas que diseñan el código. Mi pregunta en esta tercera ronda era la siguiente: si el código ya está repetido, ¿puede ser el agente quien diseñe la abstracción? ¿Y qué hace que lo haga: una regla, un lint o pedírselo?

## De dónde venía

Lo hice en tres estudios, todos sobre el mismo código real: `loot-core`, el núcleo de la app de presupuestos de código abierto [Actual](https://github.com/actualbudget/actual), unas 48.000 líneas de TypeScript. Los agentes fueron Claude Code con Sonnet 5.5 y con Haiku 5.5, y Codex con GPT-6 Luna, todos con esfuerzo medio.

El primer estudio probó directamente la mitad del «lint estricto». Con el código tal cual, los agentes tomaron cero malas decisiones de diseño en 240 ejecuciones cada uno, así que ni más abstracción ni más lint tenían nada que corregir. Tampoco ahorraron tokens.

El segundo construyó dos versiones de las mismas cuatro zonas de código: una con la lógica repetida en varios sitios (R) y otra en la que una persona la había factorizado en funciones compartidas (F). Después ejecutó en cada una cadenas de cuatro tareas. Con F los agentes olvidaban menos copias y los jueces ciegos puntuaban mejor el diseño, sobre todo en la cadena completa: las cadenas de Sonnet sacaban 2,94 sobre 5 en R frente a 3,56 en F. El coste en tokens no cambió. La abstracción ayuda, pero en ese estudio la había diseñado una persona.

## El experimento

Todos los brazos parten del código repetido del estudio 2 y ejecutan las mismas cadenas. Cada cadena tiene cuatro pasos, cada uno en una sesión nueva, así que lo que aprenda un agente solo llega al paso siguiente a través del código. T1 cambia una regla de negocio, T2 añade un nuevo consumidor de esa lógica, T3 vuelve a cambiar la regla y T4 construye algo encima. Los brazos solo difieren en una palanca:

<figure class="abs-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Los cuatro brazos. Todos parten del mismo código repetido y ejecutan los mismos cuatro pasos: cambio de regla, nuevo consumidor, cambio de regla y construcción. R no tiene palanca. RG añade una regla a AGENTS.md. RL añade una comprobación de duplicación al lint. RC añade un paso cero, un refactor dirigido que pide que la lógica viva en un solo sitio.">
  <text x="335" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">refactor</text>
  <text x="400" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">regla</text>
  <text x="460" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">consumidor</text>
  <text x="520" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">regla</text>
  <text x="575" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">construir</text>
  <g font-size="12">
    <text x="16" y="56" fill="#e2e8f0" font-weight="600">R</text><text x="52" y="56" fill="#94a3b8">código repetido, sin palanca</text>
    <text x="16" y="106" fill="#e2e8f0" font-weight="600">RG</text><text x="52" y="106" fill="#94a3b8">+ una regla en AGENTS.md</text>
    <text x="16" y="156" fill="#e2e8f0" font-weight="600">RL</text><text x="52" y="156" fill="#94a3b8">+ chequeo de duplicación en el lint</text>
    <text x="16" y="206" fill="#fbbf24" font-weight="600">RC</text><text x="52" y="206" fill="#94a3b8">+ «que viva en un solo sitio»</text>
  </g>
  <g fill="#232334" stroke="#2dd4bf">
    <rect x="375" y="38" width="50" height="28" rx="6"/><rect x="435" y="38" width="50" height="28" rx="6"/><rect x="495" y="38" width="50" height="28" rx="6"/><rect x="552" y="38" width="46" height="28" rx="6"/>
    <rect x="375" y="88" width="50" height="28" rx="6"/><rect x="435" y="88" width="50" height="28" rx="6"/><rect x="495" y="88" width="50" height="28" rx="6"/><rect x="552" y="88" width="46" height="28" rx="6"/>
    <rect x="375" y="138" width="50" height="28" rx="6"/><rect x="435" y="138" width="50" height="28" rx="6"/><rect x="495" y="138" width="50" height="28" rx="6"/><rect x="552" y="138" width="46" height="28" rx="6"/>
    <rect x="375" y="188" width="50" height="28" rx="6"/><rect x="435" y="188" width="50" height="28" rx="6"/><rect x="495" y="188" width="50" height="28" rx="6"/><rect x="552" y="188" width="46" height="28" rx="6"/>
  </g>
  <rect x="310" y="188" width="50" height="28" rx="6" fill="#232334" stroke="#f59e0b"/>
  <g font-size="11" text-anchor="middle" fill="#e2e8f0">
    <text x="400" y="56">T1</text><text x="460" y="56">T2</text><text x="520" y="56">T3</text><text x="575" y="56">T4</text>
    <text x="400" y="106">T1</text><text x="460" y="106">T2</text><text x="520" y="106">T3</text><text x="575" y="106">T4</text>
    <text x="400" y="156">T1</text><text x="460" y="156">T2</text><text x="520" y="156">T3</text><text x="575" y="156">T4</text>
    <text x="400" y="206">T1</text><text x="460" y="206">T2</text><text x="520" y="206">T3</text><text x="575" y="206">T4</text>
    <text x="335" y="206" fill="#fbbf24">T0</text>
  </g>
  <path d="M360 202 L373 202" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="300" y="240" text-anchor="middle" fill="#94a3b8" font-size="11">3 agentes × 4 zonas de código × 8 cadenas por brazo · sesión nueva en cada paso</text>
</svg>
<figcaption>Mismo código de partida, mismas tareas. Solo cambia la palanca: una norma escrita, un chequeo duro o pedir explícitamente el refactor antes de empezar.</figcaption>
</figure>

- **RG**, la regla escrita. Una línea en el `AGENTS.md` raíz, redactada como convención del equipo: *«Do not copy logic: when new code needs behaviour that already exists, extract it into a shared function and reuse it; when a rule changes, change it in one place.»*
- **RL**, el lint estricto. `yarn lint` ejecuta un chequeo de duplicación (jscpd) que falla si algún clon toca líneas añadidas en el paso. Quitar duplicación ajena en otro sitio no da margen.
- **RC**, el refactor dirigido. Antes de T1, un paso T0 que nombra la zona de comportamiento y pide que viva en un solo sitio, sin cambiar el comportamiento. No dice qué ficheros, cuántas copias ni dónde.

En total, 384 cadenas y 1.632 pasos. La corrección la dan tests ocultos. El diseño lo puntúan jueces ciegos (Claude Opus 5.5), que evaluaron 2.206 diffs sin saber el brazo, el agente ni que existieran brazos. Un segundo juez puntuó 340, y calculé la concordancia antes de comparar nada: kappa ponderada entre 0,70 y 0,89 en todas las puntuaciones. El diseño y todos los análisis quedaron registrados antes de las ejecuciones.

## Solo una palanca llega a los tres agentes

La medida principal es la mantenibilidad del diff completo de cada cadena, tal como la puntuaron los jueces de 1 a 5:

<figure class="abs-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Mantenibilidad juzgada del diff de la cadena por agente y brazo. Claude: R 2,59, regla 3,09, lint 3,19, refactor 3,06, factorización humana 3,41. Codex: R 2,19, regla 2,16, lint 2,34, refactor 2,59, factorización humana 2,78. Haiku: R 3,56, regla 3,78, lint 3,69, refactor 3,91, factorización humana 3,91. Pedir el refactor mejora a los tres agentes; la regla y el lint solo mejoran claramente a Claude.">
  <g stroke="rgba(255,255,255,0.08)"><path d="M55 250 H595"/><path d="M55 202.5 H595"/><path d="M55 155 H595"/><path d="M55 107.5 H595"/><path d="M55 60 H595"/></g>
  <g fill="#94a3b8" font-size="10" text-anchor="end"><text x="48" y="253">2,0</text><text x="48" y="205.5">2,5</text><text x="48" y="158">3,0</text><text x="48" y="110.5">3,5</text><text x="48" y="63">4,0</text></g>
  <g font-size="12" font-weight="600" fill="#e2e8f0" text-anchor="middle"><text x="140" y="36">Claude (Sonnet)</text><text x="325" y="36">Codex (Luna)</text><text x="510" y="36">Claude (Haiku)</text></g>
  <rect x="68" y="194" width="30" height="56" fill="#64748b"/><rect x="106" y="146" width="30" height="104" fill="#2dd4bf"/><rect x="144" y="137" width="30" height="113" fill="#2dd4bf"/><rect x="182" y="149" width="30" height="101" fill="#f59e0b"/>
  <path d="M62 116 H220" stroke="#e2e8f0" stroke-width="1.5" stroke-dasharray="5 4"/>
  <rect x="253" y="232" width="30" height="18" fill="#64748b"/><rect x="291" y="235" width="30" height="15" fill="#2dd4bf"/><rect x="329" y="218" width="30" height="32" fill="#2dd4bf"/><rect x="367" y="194" width="30" height="56" fill="#f59e0b"/>
  <path d="M247 176 H405" stroke="#e2e8f0" stroke-width="1.5" stroke-dasharray="5 4"/>
  <rect x="438" y="102" width="30" height="148" fill="#64748b"/><rect x="476" y="81" width="30" height="169" fill="#2dd4bf"/><rect x="514" y="89" width="30" height="161" fill="#2dd4bf"/><rect x="552" y="69" width="30" height="181" fill="#f59e0b"/>
  <path d="M432 69 H590" stroke="#e2e8f0" stroke-width="1.5" stroke-dasharray="5 4"/>
  <text x="436" y="64" fill="#cbd5e1" font-size="10">F humano</text>
  <g font-size="10" text-anchor="middle" fill="#94a3b8">
    <text x="83" y="265">R</text><text x="121" y="265">regla</text><text x="159" y="265">lint</text><text x="197" y="265" fill="#fbbf24">refactor</text>
    <text x="268" y="265">R</text><text x="306" y="265">regla</text><text x="344" y="265">lint</text><text x="382" y="265" fill="#fbbf24">refactor</text>
    <text x="453" y="265">R</text><text x="491" y="265">regla</text><text x="529" y="265">lint</text><text x="567" y="265" fill="#fbbf24">refactor</text>
  </g>
  <g font-size="10" text-anchor="middle" fill="#e2e8f0"><text x="121" y="140">✓</text><text x="159" y="131">✓</text></g>
  <g font-size="10" fill="#cbd5e1"><text x="224" y="119">F humano</text><text x="409" y="179">F humano</text></g>
  <text x="300" y="290" text-anchor="middle" fill="#94a3b8" font-size="10">mantenibilidad (1–5, juez Opus), eje desde 2,0 · ✓ sobrevive a la corrección · discontinua: F humano</text>
</svg>
<figcaption>Pedir el refactor (ámbar) es la única palanca que mejora a los tres agentes, entre 0,35 y 0,47 puntos (p ≈ 0,02 en cada uno, en la misma dirección en 11 de 12 zonas). La regla y el lint solo mueven claramente a Sonnet (el lint se evalúa en las dos zonas donde puede ver las copias).</figcaption>
</figure>

Con Sonnet funcionan las tres palancas, y con el juez registrado la regla y el lint sobreviven a la corrección por comparaciones múltiples. Con Codex y Haiku, la regla y el lint no hacen nada medible. Solo pedir el refactor mueve a los tres. Por separado, el efecto del refactor en cada agente ronda p = 0,02 y no sobreviviría a la corrección, pero va en la misma dirección en 11 de las 12 zonas, y es la única palanca que además mejora la corrección.

Haiku es un caso aparte: parte cerca del techo (3,56 frente a 3,91 del código factorizado por una persona), así que tiene poco margen.

Los jueces son Claude, y también lo son dos de los tres agentes. Para comprobar que no estaban prefiriendo sin más el código de su propia familia, pedí a GPT-6.1 Sol, a través de Codex, que volviera a puntuar a ciegas los 480 diffs de cadena con la misma rúbrica. Los dos jueces coinciden bien en mantenibilidad (kappa ponderada 0,79), y hay un efecto de familia: comparado con Sol, Opus puntúa el código escrito por Claude 0,21 puntos más alto que el escrito por Codex. Todas las comparaciones de arriba son dentro del mismo agente, así que un desfase constante se cancela, y con Sol como juez pedir el refactor sigue mejorando a los tres agentes (+0,34, +0,25 y +0,28 puntos; p = 0,03, 0,09 y 0,04). La regla escrita sigue ayudando a Sonnet (p = 0,02). Lo que encoge es la mejora del lint para Sonnet, de 1,13 a 0,43 puntos en las zonas donde puede ver las copias: la brecha de familia es mayor en los brazos de la regla y del lint.

## Lo que compra el refactor: búsqueda

Vuelvo a la copia olvidada. Con el código repetido y sin palanca, Codex olvida una copia en el 33 % de los cambios de regla y acierta el 59 % de los pasos. Tras su propio refactor, olvida el 12 % y acierta el 70 %. Es mejor que con el código que había factorizado una persona en el estudio 2 (22 % y 66 %).

<figure class="abs-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Codex: las copias olvidadas en los cambios de regla fueron el 33 por ciento sin palanca, 31 con la regla, 31 con el lint, 12 pidiendo el refactor y 22 con el código factorizado por una persona del estudio 2. Los pasos correctos fueron 59, 55, 59, 70 y 66 por ciento.">
  <g stroke="rgba(255,255,255,0.08)"><path d="M55 220 H590"/><path d="M55 175 H590"/><path d="M55 130 H590"/><path d="M55 85 H590"/></g>
  <g fill="#94a3b8" font-size="10" text-anchor="end"><text x="48" y="223">0 %</text><text x="48" y="178">25 %</text><text x="48" y="133">50 %</text><text x="48" y="88">75 %</text></g>
  <g font-size="12" font-weight="600" fill="#e2e8f0" text-anchor="middle"><text x="175" y="36">olvidó una copia (cambios de regla)</text><text x="445" y="36">pasos correctos</text></g>
  <rect x="80" y="161" width="34" height="59" fill="#64748b"/><rect x="122" y="164" width="34" height="56" fill="#2dd4bf"/><rect x="164" y="164" width="34" height="56" fill="#2dd4bf"/><rect x="206" y="198" width="34" height="22" fill="#f59e0b"/><rect x="248" y="180" width="34" height="40" fill="none" stroke="#e2e8f0" stroke-dasharray="4 3"/>
  <rect x="350" y="114" width="34" height="106" fill="#64748b"/><rect x="392" y="121" width="34" height="99" fill="#2dd4bf"/><rect x="434" y="114" width="34" height="106" fill="#2dd4bf"/><rect x="476" y="94" width="34" height="126" fill="#f59e0b"/><rect x="518" y="101" width="34" height="119" fill="none" stroke="#e2e8f0" stroke-dasharray="4 3"/>
  <g font-size="11" text-anchor="middle" fill="#e2e8f0">
    <text x="97" y="155">33</text><text x="139" y="158">31</text><text x="181" y="158">31</text><text x="223" y="192" fill="#fbbf24">12</text><text x="265" y="174">22</text>
    <text x="367" y="108">59</text><text x="409" y="115">55</text><text x="451" y="108">59</text><text x="493" y="88" fill="#fbbf24">70</text><text x="535" y="95">66</text>
  </g>
  <g font-size="10" text-anchor="middle" fill="#94a3b8">
    <text x="97" y="236">R</text><text x="139" y="236">regla</text><text x="181" y="236">lint</text><text x="223" y="236" fill="#fbbf24">refactor</text><text x="265" y="236">F</text>
    <text x="367" y="236">R</text><text x="409" y="236">regla</text><text x="451" y="236">lint</text><text x="493" y="236" fill="#fbbf24">refactor</text><text x="535" y="236">F</text>
  </g>
  <text x="300" y="262" text-anchor="middle" fill="#94a3b8" font-size="10">Codex (GPT-6 Luna), 64 cambios de regla y 128 pasos por brazo · F: factorizado a mano (estudio 2)</text>
</svg>
<figcaption>Con Codex, la regla y el lint dejan las copias olvidadas donde estaban. Tras un refactor hecho por él mismo, olvida una copia tres veces menos que sin palanca.</figcaption>
</figure>

Al leer las trazas, el mecanismo resultó más sencillo que «el agente diseñó una buena abstracción». Con el código repetido, Codex sí consolida en el cambio de regla, pero solo las copias que encuentra. La petición de refactor dice que la lógica está «repetida en vez de definida una vez», y esa frase lo manda a buscar todas las copias. Un cambio de regla no lo hace. Cuando las copias ya están detrás de una función, el siguiente cambio de regla llega a todas con una sola edición, plantilla incluida, sin que el agente llegue a abrir ese fichero.

Las dos copias que aún olvida repiten, con la abstracción del propio Codex, los dos fallos que había visto con la abstracción humana. En una cadena, el refactor no encontró la copia de la plantilla. En la otra, Codex había conservado el redondeo raro de la plantilla como un modo con nombre, y en el paso siguiente lo trató como un requisito protegido: *«Schedule templates explicitly request a separate sum-first rounding mode; I'll preserve that behavior.»* Una abstracción que nombra una excepción invita al siguiente agente a protegerla.

Los tres agentes construyeron el mismo tipo de abstracción en T0: una función de selección de categorías, un único flujo para vincular cuentas bancarias, una función para la regla de fin de semana. Los jueces vieron la mayoría de los refactors completos: la mediana del porcentaje de copias que pasaban por la definición compartida fue del 100 % en los tres agentes. También conservaron el comportamiento: mi chequeo marcó 4 de los 96 refactors, y solo dos eran cambios reales (los dos de Codex). Los otros dos eran un artefacto de lo fino que el chequeo registra las llamadas internas.

## El lint, y cómo lo esquivó Codex

Con Sonnet, el chequeo de duplicación produjo el diseño claramente mejor de todo el estudio. En la zona de sincronización bancaria construyó un único flujo de vinculación para todos los proveedores. Un juez escribió: *«Adding a provider becomes a few lines.»*

Con Codex produjo otra cosa. En cuatro pasos marcó el código para que el chequeo lo ignorase:

```ts
// jscpd:ignore-start -- This provider has the same link lifecycle as the others.
```

con la justificación *«The duplication check is unusually strict here: it flags the same established provider lifecycle even when the implementation is intentionally parallel.»* En otras cadenas reutilizó estirando la función de otro proveedor con flags hasta que servía a los dos. Un juez describió una: *«a SimpleFin handler stretched with an 'orgDomain' in-check to also serve Fintegra.»* En otras dejó copias lo bastante reformuladas como para que el chequeo dejara de reconocerlas. El recuento de duplicación bajó, y las notas de diseño no se movieron.

El lint tiene además un punto ciego estructural: solo ve copias que se parecen. En la zona donde la duplicación son cuatro implementaciones distintas de la misma regla de fin de semana, no salta nunca, y el diseño de Sonnet ahí salió algo peor que sin palanca.

## Lo que no hay que sobrevender

Al leer las justificaciones de los jueces, la mayor parte de la mejora de diseño son menos copias de la misma regla, no una estructura distinta. La queja principal sobre el código repetido, «esta regla vive en varios sitios», sigue ahí en todos los brazos. Lo que cambia es que seis sitios pasan a ser dos. Si descuento el número de bloques duplicados que contó el propio juez, el efecto de las palancas en Sonnet se queda entre una quinta parte y la mitad. El flujo único de vinculación es la excepción.

El refactor no se paga en tokens en cuatro tareas. Con T0 incluido, una cadena con refactor cuesta entre un 16 % y un 23 % más que una sin palanca. Una cadena más larga quizá lo recupere. Esta no.

La regla escrita no se cita nunca. Sonnet la sigue sin mencionarla, y lo hace sobre todo reutilizando funciones auxiliares que él mismo creó en el paso anterior. Codex tiene el fichero en contexto, y sigue otra instrucción de ese fichero (ejecutar los comandos desde la raíz del repositorio) en 541 de 544 pasos. Esta la ignora.

## Qué haría yo

Si quieres una abstracción en un código que mantienen agentes, pídesela al agente como tarea, no como regla. Nombra la zona, di que debe vivir en un solo sitio y di qué diferencias tienen que sobrevivir. Lo último importa: una excepción que no se nombra acaba borrada o envuelta en un modo que el siguiente agente trata como sagrado.

Una regla en `AGENTS.md` no cuesta nada, pero que funcione depende del agente. Un lint de duplicación es una red, no un diseñador: unos agentes lo cumplen construyendo la abstracción y otros esquivando el chequeo. Y ninguna de estas palancas sustituye la búsqueda. Lo que marcó la diferencia fue pedirle al agente que fuera a buscar todas las copias.

Pocock pedía a la gente que fuera más valiente y diseñara abstracciones. Mis datos añaden una cosa: cuando el código ya está repetido, puedes delegar el diseño, siempre que lo pidas explícitamente.

---

*Límites: un solo código, un nivel de esfuerzo, tres agentes. El juez registrado y su segunda pasada son el mismo modelo; el chequeo con Sol, de otra familia, cubre los diffs de cadena, no todas las puntuaciones. Con cuatro zonas, el test de signo por zona nunca puede llegar a significación. Un resultado relacionado: en [un experimento anterior](/es/blog/practices-for-agents-substrate) sobre cómo afecta a los agentes la forma de escribir el código, los efectos solo aparecían en repositorios grandes. El diseño preregistrado, el código, los datos anonimizados y el informe completo están [en el repositorio](https://github.com/JaviMaligno/personal-website/tree/main/experiments/agent-abstractions).*
