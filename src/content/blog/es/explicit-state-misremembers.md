---
title: "El estado explícito no olvida. Recuerda mal."
description: "La segunda mitad de mi réplica de SKILL.state, con el modelo del propio paper y un segundo modelo, y cada celda repetida. El estado explícito aguanta justo donde el paper dice. Donde falla, falla escribiendo mal el estado, y el runtime que conserva la historia al lado apenas lo nota."
pubDate: 2026-10-21
tags: ["IA", "Agentes", "Context Engineering", "Evaluación", "Investigación"]
lang: es
translationKey: explicit-state-misremembers
heroImage: "/blog/explicit-state-misremembers.png"
repoUrl: https://github.com/JaviMaligno/delayed-relevance
linkedinLinks:
  - label: "El paper (SKILL.state)"
    url: "https://arxiv.org/abs/2608.26263"
---

<style>
.esm-fig { margin: 2rem 0; }
.esm-fig svg { width: 100%; height: auto; display: block; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.esm-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
.esm-fig .t { fill: #e2e8f0; font: 13px system-ui, sans-serif; }
.esm-fig .m { fill: #94a3b8; font: 12px system-ui, sans-serif; }
.esm-fig .mono { fill: #e2e8f0; font: 12px ui-monospace, 'JetBrains Mono', monospace; }
.esm-fig .h { fill: #f8fafc; font: 600 14px system-ui, sans-serif; }
</style>

En la [primera mitad de esta réplica](/es/blog/when-the-fact-stops-being-true) corrí
[SKILL.state](https://arxiv.org/abs/2608.26263) sobre Claude y la degradación que el paper
pone en titulares no aparecía. La objeción obvia es que el paper usa Gemini-3-Flash, no
Claude. Así que esta mitad corre sobre el suyo —`gemini-3-flash-preview` por Vertex, en un
entorno reconstruido para ajustarse a su Apéndice B— y además sobre Claude Haiku 4.5 con
el mismo entorno y el mismo tope de salida, con **cada celda repetida** y cada episodio
guardado como traza paso a paso.

La versión corta: la tesis central del paper se sostiene con su propio modelo, y de forma
más limpia de lo que el paper la reporta. Con un segundo modelo no, y lo interesante es
cómo falla. El estado explícito no pierde el hilo del procedimiento. **Escribe mal el
estado**, y nada comprueba lo que escribe.

## Repetir cada celda, incluso a temperatura cero

El protocolo partía de un supuesto que suena seguro: con decodificación greedy, una seed es
una instancia del entorno y basta con una tirada por celda. No basta. La misma celda,
repetida cinco veces a `temperature=0`, sacó entre **0,830 y 0,960**. La distribución
tiene una cola izquierda larga porque los fallos encadenan: el agente guarda un palé en la
estantería equivocada y cada decisión posterior que toca esa estantería hereda el error.

Tres conclusiones redactadas a partir de tiradas sueltas —un efecto del entorno, una curva
de ruido monótona, una estimación del ruido— no sobrevivieron a la repetición. Todas las
cifras de abajo son medias sobre 15 a 24 tiradas, con la dispersión calculada sobre las
tiradas, no sobre las medias por seed.

## Con su modelo, la tesis se sostiene

Su Tabla 1 tiene cuatro runtimes: ReAct (historia completa), Memory (resumen móvil),
Stateful (bloque de estado más historia) y SKILL.state (solo bloque de estado). Estos son
los dos que cargan con el argumento, los nuestros frente a los suyos:

<figure class="esm-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Con Gemini-3-Flash, SKILL.state saca 1,000 en todos los horizontes de 10 a 200 pasos, y ReAct solo baja a 0,913 en T=200, frente a 0,74 en el paper.">
  <text x="20" y="24" class="h">Score frente al horizonte, gemini-3-flash-preview (15 tiradas por celda)</text>
  <line x1="80" y1="40" x2="80" y2="250" stroke="#64748b"/>
  <line x1="80" y1="250" x2="580" y2="250" stroke="#64748b"/>
  <text x="72" y="44" class="m" text-anchor="end">1,00</text>
  <text x="72" y="114" class="m" text-anchor="end">0,90</text>
  <text x="72" y="184" class="m" text-anchor="end">0,80</text>
  <text x="72" y="254" class="m" text-anchor="end">0,70</text>
  <line x1="80" y1="110" x2="580" y2="110" stroke="rgba(255,255,255,0.06)"/>
  <line x1="80" y1="180" x2="580" y2="180" stroke="rgba(255,255,255,0.06)"/>
  <text x="110" y="270" class="m" text-anchor="middle">10</text>
  <text x="220" y="270" class="m" text-anchor="middle">25</text>
  <text x="330" y="270" class="m" text-anchor="middle">50</text>
  <text x="440" y="270" class="m" text-anchor="middle">100</text>
  <text x="550" y="270" class="m" text-anchor="middle">200</text>
  <text x="330" y="290" class="m" text-anchor="middle">horizonte T (pasos)</text>
  <polyline points="110,40 220,40 330,68 440,82 550,82" fill="none" stroke="#2dd4bf" stroke-width="2" stroke-dasharray="6 4" opacity="0.7"/>
  <polyline points="110,110 220,96 330,124 440,152 550,222" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="6 4" opacity="0.7"/>
  <polyline points="110,40 220,40 330,40 440,40 550,40" fill="none" stroke="#2dd4bf" stroke-width="2.6"/>
  <polyline points="110,44.9 220,71.5 330,84.8 440,68 550,100.9" fill="none" stroke="#f59e0b" stroke-width="2.6"/>
  <circle cx="550" cy="40" r="3.5" fill="#2dd4bf"/>
  <circle cx="550" cy="100.9" r="3.5" fill="#f59e0b"/>
  <circle cx="550" cy="222" r="3.5" fill="#f59e0b" opacity="0.7"/>
  <text x="545" y="122" class="t" text-anchor="end">ReAct, nuestro 0,913</text>
  <text x="558" y="86" class="m" style="fill:#5eead4">0,94</text>
  <text x="545" y="218" class="t" text-anchor="end">ReAct, suyo 0,74</text>
  <text x="545" y="58" class="t" text-anchor="end">SKILL.state, nuestro 1,000</text>
  <rect x="96" y="194" width="208" height="42" fill="#1a1a24"/>
  <line x1="104" y1="206" x2="128" y2="206" stroke="#94a3b8" stroke-width="2.6"/>
  <text x="134" y="210" class="m">esta réplica</text>
  <line x1="104" y1="226" x2="128" y2="226" stroke="#94a3b8" stroke-width="2" stroke-dasharray="6 4"/>
  <text x="134" y="230" class="m">su Tabla 1</text>
</svg>
<figcaption>Las líneas continuas son esta réplica y las discontinuas su Tabla 1. SKILL.state (verde azulado) no falla ni una vez en 75 episodios. El brazo de historia completa (ámbar) degrada mucho menos de lo que ellos reportan, y la distancia crece con el horizonte.</figcaption>
</figure>

**SKILL.state no falla ni una vez en 75 episodios de hasta 200 pasos**, donde el suyo
pierde seis puntos. La dirección de su tesis se reproduce con margen. La magnitud no:
nuestro ReAct pierde 0,080 entre 10 y 200 pasos donde el suyo pierde 0,160, y queda
**17 puntos por encima** del suyo en T=200. Variar el presupuesto de razonamiento, el tope
de salida y las tres diferencias de entorno que encontré frente a su apéndice no lo mueve.
El nombre del modelo es el suyo, pero `gemini-3-flash-preview` puede no ser exactamente el
checkpoint que hay detrás de su `Gemini-3-Flash`, así que no puedo descartar el modelo:
solo decir que no lo cambié.

Un brazo no cuadra con el suyo por una razón mía: en T=200 el prompt medio de nuestro
Memory es catorce veces más pequeño que el suyo, y en T=100 y T=200 queda el último. Eso
mide nuestra política de resumen, no el resumen como categoría.

## Con un segundo modelo, el estado explícito escribe mal el estado

El mismo entorno, el mismo tope de salida, Claude Haiku 4.5 por Microsoft Foundry, 24
tiradas por celda en los dos extremos del horizonte:

| T=200 | ReAct | Stateful | SKILL.state |
|---|---|---|---|
| Gemini-3-Flash | 0,913 | 0,930 | **1,000** |
| Claude Haiku 4.5 | 0,974 | **0,999** | 0,958 |

En Haiku el orden se da la vuelta. El brazo de historia completa está casi plano (−0,005
de T=50 a T=200) y el que cae es SKILL.state. Para saber por qué, reproduje cada episodio
contra el entorno real y comparé, paso a paso, el inventario que el modelo *cree* —el de su
objeto de estado— con el que hay de verdad en las estanterías.

Todos los fallos del estado explícito tienen el mismo origen. En los 17 episodios en que la
creencia se apartó de la realidad, el paso que la corrompió fue un **`Move` ejecutado
correctamente con el parche de estado mal escrito**. `Move` es la única transición que
obliga al modelo a copiar el contenido de una estantería en otra clave de su propio estado,
y es en esa copia donde se equivoca.

<figure class="esm-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="En el paso 132 el modelo ejecuta un Move correcto de la estantería 7 a la 3, pero escribe en su estado el contenido de la estantería 6 en lugar del de la 7. Cinco pasos después envía desde la estantería 3 por esa creencia y el entorno rechaza la acción.">
  <text x="20" y="24" class="h">Haiku 4.5, seed 2: la acción está bien, el parche no</text>
  <rect x="20" y="40" width="170" height="190" rx="6" fill="none" stroke="rgba(255,255,255,0.1)"/>
  <text x="105" y="62" class="t" text-anchor="middle">paso 132</text>
  <text x="105" y="84" class="mono" text-anchor="middle">Move 7 → 3</text>
  <text x="105" y="106" class="m" text-anchor="middle">acción: correcta ✓</text>
  <text x="34" y="140" class="m">realidad, estantería 3</text>
  <text x="34" y="158" class="mono" style="fill:#5eead4">SKU-K · L-8558</text>
  <text x="34" y="190" class="m">parche, estantería 3</text>
  <text x="34" y="208" class="mono" style="fill:#fbbf24">SKU-J · L-5231</text>
  <text x="34" y="222" class="m">(copiado de la 6)</text>
  <line x1="190" y1="135" x2="228" y2="135" stroke="#64748b" stroke-width="1.6"/>
  <polygon points="228,130 238,135 228,140" fill="#64748b"/>
  <rect x="240" y="40" width="170" height="190" rx="6" fill="none" stroke="rgba(255,255,255,0.1)"/>
  <text x="325" y="62" class="t" text-anchor="middle">paso 137</text>
  <text x="325" y="84" class="mono" text-anchor="middle">pedido: SKU-J</text>
  <text x="325" y="118" class="m" text-anchor="middle">creencia: SKU-J en</text>
  <text x="325" y="134" class="m" text-anchor="middle">las estanterías 3 y 6</text>
  <text x="325" y="166" class="mono" text-anchor="middle" style="fill:#fbbf24">Ship estantería 3 ✗</text>
  <text x="325" y="190" class="m" text-anchor="middle">correcta: la 6</text>
  <line x1="410" y1="135" x2="448" y2="135" stroke="#64748b" stroke-width="1.6"/>
  <polygon points="448,130 458,135 448,140" fill="#64748b"/>
  <rect x="460" y="40" width="120" height="190" rx="6" fill="none" stroke="rgba(255,255,255,0.1)"/>
  <text x="520" y="62" class="t" text-anchor="middle">paso 138 →</text>
  <text x="520" y="92" class="m" text-anchor="middle">ACCIÓN</text>
  <text x="520" y="108" class="m" text-anchor="middle">RECHAZADA</text>
  <text x="520" y="140" class="m" text-anchor="middle">el estado no</text>
  <text x="520" y="156" class="m" text-anchor="middle">se corrige</text>
  <text x="520" y="190" class="t" text-anchor="middle" style="fill:#fbbf24">~25 fallos</text>
  <text x="520" y="208" class="m" text-anchor="middle">después</text>
</svg>
<figcaption>El fallo que SKILL.state se diseñó para evitar es perder el hilo del procedimiento. El que tiene es escribir un dato falso en el único sitio donde mira el agente, y ni siquiera un rechazo explícito del entorno hace que vuelva a leerlo.</figcaption>
</figure>

Es sistemático, no ruido: en 6 de las 8 tiradas de la seed 2 la corrupción ocurre en ese
mismo paso, y a partir de ahí el agente encadena unos 25 fallos. No todo parche mal escrito
importa —en la seed 0 el modelo copia mal el *número de lote*, que ninguna decisión
posterior lee, y esas tiradas no pierden nada—, pero lo que se escribe nunca se contrasta
con lo que hizo la acción. Gemini no cometió este error en 75 episodios; Haiku escribió al
menos un parche erróneo en 17 de 24 en T=200.

El paper sí estudia actualizaciones de estado erróneas: sobrescrituras prematuras, errores
de esquema y de tipo. Esto es algo más estrecho: un parche válido según el esquema con un
valor equivocado dentro, que pasa todas las comprobaciones que hace el runtime.

## Conservar la historia lo absorbe

El brazo Stateful es el control que lo hace legible. Mantiene el mismo tipo de bloque de
estado y además conserva la historia completa. En Haiku comete **el mismo tipo de error de
escritura** —su creencia se aparta de la realidad en 8 de 15 episodios en T=200, siempre
con la acción correcta y el parche mal escrito— y no le cuesta nada: el estado erróneo
prescribe otra acción en solo 4 pasos, y en los 4 el modelo hace lo que exige la realidad.
Ninguno de sus fallos viene de su estado.

En Gemini el mismo brazo se comporta al revés: su estado se desvía en 11 de 15 episodios,
cuando SKILL.state con el mismo modelo no se desvió nunca, y 77 de sus 211 fallos ocurren
con el estado correcto delante. Stateful y SKILL.state también difieren en el formato de
respuesta, el parser y los reintentos, así que esto describe el efecto de la historia, no lo
aísla. Pero la lectura práctica cuesta evitarla: con el modelo que recuerda mal, la copia
redundante de la historia es lo que lo recoge.

## Donde gana el estado explícito, medido por la decisión

El experimento de recuperación del paper pregunta qué pasa cuando un hecho que le dijeron
al agente deja de ser cierto. Lo mido por episodio: en una trayectoria correcta, la
corrección decide exactamente un paso en cada uno de los tres escenarios usados, así que la
pregunta es si el agente acierta ese paso. Ahora con tres modelos y el mismo diseño en cada
uno:

<figure class="esm-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Corrección retroactiva aplicada: SKILL.state 24 de 24 en Haiku, 22 de 24 en Sonnet y 24 de 24 en Gemini; ReAct 1 de 24, 9 de 24 y 0 de 24.">
  <text x="20" y="24" class="h">Se retira un hecho: ¿actúa el agente según la retirada?</text>
  <text x="20" y="44" class="m">episodios con el paso decisivo acertado, de 24 (seeds 4, 10, 6 × 8)</text>
  <text x="130" y="82" class="t" text-anchor="end">Haiku 4.5</text>
  <rect x="140" y="66" width="360" height="12" fill="#2dd4bf"/><text x="508" y="77" class="t">24</text>
  <rect x="140" y="82" width="15" height="12" fill="#f59e0b"/><text x="162" y="93" class="t">1</text>
  <text x="130" y="132" class="t" text-anchor="end">Sonnet 5</text>
  <rect x="140" y="116" width="330" height="12" fill="#2dd4bf"/><text x="478" y="127" class="t">22</text>
  <rect x="140" y="132" width="135" height="12" fill="#f59e0b"/><text x="282" y="143" class="t">9</text>
  <text x="130" y="182" class="t" text-anchor="end">Gemini-3-Flash</text>
  <rect x="140" y="166" width="360" height="12" fill="#2dd4bf"/><text x="508" y="177" class="t">24</text>
  <rect x="140" y="182" width="2" height="12" fill="#f59e0b"/><text x="150" y="193" class="t">0</text>
  <rect x="140" y="206" width="12" height="10" fill="#2dd4bf"/><text x="158" y="215" class="m">SKILL.state</text>
  <rect x="250" y="206" width="12" height="10" fill="#f59e0b"/><text x="268" y="215" class="m">ReAct (historia completa)</text>
</svg>
<figcaption>70 de 72 episodios con estado explícito, 10 de 72 con la historia completa. Cada paso decisivo fallado es exactamente lo que haría un agente que nunca oyó la corrección.</figcaption>
</figure>

**El estado explícito aplica la corrección en 70 de 72 episodios (intervalo de Wilson al
95 %, 90–99 %); la historia completa, en 10 de 72 (8–24 %).** Es la tesis del propio paper
y se reproduce limpia. También es menos que el «93 de 93» que di en la primera mitad: aquel
recuento leía los pasos dependientes de una trayectoria simulada en lugar de la trayectoria
real del agente, y no podía registrar un fallo que viniera de que el agente no hiciera
nada. Medido sobre la trayectoria real, la dirección se sostiene y la perfección no.

La otra sonda pone a prueba la limitación que el paper declara: el estado explícito solo
protege lo que su esquema previó. Un hecho anunciado en el paso `t` se vuelve relevante por
primera vez en el paso `t+40`, y el agente lo guardó en algún sitio o no.

| SKILL.state, el hecho hace falta 40 pasos después | Haiku 4.5 | Gemini-3-Flash |
|---|---|---|
| Sin campo dedicado | 0/24 | 0/24 |
| Campo libre `notes` | 10/24 | 1/24 |
| Campo del esquema que nombra el hecho | **24/24** | **16/24** |

Sonnet 5 no está en esta tabla porque una cuarta parte de sus episodios nunca llega a la
prueba —su trayectoria ya ha divergido en el paso `t+40`— y sus celdas necesitan dos tasas
para leerse con honestidad; están en el paper.

Tener un sitio donde ponerlo no basta: el sitio tiene que decir qué va ahí. «Sin campo
dedicado» no significa sin dónde guardarlo —los pocos aciertos de Sonnet en ese brazo
escribieron la cuarentena directamente dentro del objeto de inventario—, pero el campo con
nombre es lo que funciona de forma fiable, y estos experimentos no separan el hueco extra
de la pista que da su nombre. Para el runtime sin esquema alguno, un recordatorio pegado a
la observación hace el trabajo: ReAct pasa del 0–34 % al 71–96 % en los tres modelos.

## La factura

La mitad de costes del primer artículo se mantiene. Con un procedimiento corto, la caché
reduce la ventaja de SKILL.state sobre la historia en coste de entrada de **7,5x a 1,4x**
en Anthropic, porque una historia que solo crece es el prefijo cacheable ideal y un bloque
de estado que muta no lo es. En Vertex la misma cuenta apenas mueve la proporción —7,5x en
tokens son 7,2x en entrada efectiva— porque allí la caché implícita le ahorró a ReAct un
6,8 % de su entrada, frente al 82 % en Anthropic.

Y el orden del prompt, aislado esta vez, es una variable de coste de primer orden. El mismo
runtime Stateful, mandando el mismo contenido y con la historia marcada como prefijo
cacheable en los dos brazos, cuesta **5,2x más** cuando su bloque de estado va delante de la
historia que cuando va detrás —869k frente a 168k tokens de entrada efectiva por episodio
de 50 pasos— con el mismo score. La plantilla de prompt del propio paper pone el bloque de
estado delante.

## Lo que me llevo

- **El estado explícito hace lo que el paper dice con el modelo del paper.** En Gemini no
  pierde un paso, y aplica las retiradas casi siempre en los tres modelos.
- **Su modo de fallo es escribir, no recordar.** Un esquema puede validar la forma de un
  parche; nada en el runtime comprueba que el valor coincida con lo que hizo la acción. Si
  construyes sobre estado explícito, esa comprobación es lo que hay que añadir.
- **Conservar la historia junto al estado es un seguro barato con algunos modelos.** A
  Stateful no le costó nada en Haiku y recogió todas las escrituras erróneas que habrían
  importado.
- **Pon lo que muta al final.** Es un cambio de una línea y, medido aislado, una diferencia
  de 5,2x en la factura.
- **Repite la celda.** La temperatura cero no garantiza reproducibilidad, y una tirada suelta
  esconde justo la cola donde viven los fallos.

Cada número de aquí lo recalculó a partir de las trazas paso a paso un revisor adversarial
independiente —nueve rondas, con acceso a los datos crudos y a nada de la prosa—, y el
paper, las trazas y el código son públicos.

---

*Código, trazas paso a paso y el borrador completo del paper: [JaviMaligno/delayed-relevance](https://github.com/JaviMaligno/delayed-relevance). El paper original: [SKILL.state (arXiv 2608.26263)](https://arxiv.org/abs/2608.26263). La primera mitad de la réplica: [Cuando el dato deja de ser cierto](/es/blog/when-the-fact-stops-being-true).*
