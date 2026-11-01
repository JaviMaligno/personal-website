---
title: "Más de una forma de demostrarlo"
description: "Evaluar a un agente comparando sus llamadas a herramientas con un camino de referencia parece más exigente que mirar dónde acabó. En 694 ejecuciones arreglando bugs reales y escribiendo demostraciones en Lean, el camino rechazó un tercio de las demostraciones válidas, dos reglas razonables ordenaron los modelos al revés y la afirmación falsa más clara estaba en una frase que ningún evaluador lee."
pubDate: 2026-11-02
tags: ["IA", "Agentes", "Evaluación", "Lean", "Investigación"]
lang: es
translationKey: more-than-one-way-to-prove-it
heroImage: "/blog/more-than-one-way-to-prove-it.png"
---
Hay dos formas de evaluar a un agente de IA que acaba de terminar una tarea: mirar lo que ha dejado o mirar cómo ha llegado hasta ahí. *CORE: Full-Path Evaluation of LLM Agents Beyond Final State* ([Michelakis, Hadjiyiannis y Stamoulis, 2025](https://arxiv.org/abs/2509.20998)) defiende la segunda. Si solo miras el estado final, agentes que se comportaron de forma muy distinta parecen iguales. Así que CORE codifica cada tarea como un conjunto de caminos válidos de llamadas a herramientas y puntúa cuánto se acerca el camino del agente a alguno de ellos.

El problema aparece con un teorema pequeño: el Fibonacci $n$ es como mucho $2^n$, es decir, $F_n \le 2^n$. Dos agentes lo demostraron, por dos rutas distintas.

- **`gpt-6.1-sol` demostró algo más fuerte.** Probó que la cota se cumple para dos números seguidos a la vez, $F_k \le 2^k$ y $F_{k+1} \le 2^{k+1}$, porque así basta una inducción simple sobre $k$.
- **Claude Sonnet hizo que el teorema se llamara a sí mismo.** Distinguió casos en $n$ y usó la cota para los dos números anteriores: $F_{n+2} = F_n + F_{n+1} \le 2^n + 2^{n+1} \le 2^{n+2}$. Lean comprueba que esa recursión termina.

El núcleo de Lean acepta las dos. Comparadas con los caminos de referencia, la primera obtiene una corrección de camino de 1,0 y la segunda de 0,63. Con el umbral habitual, la primera aprueba y la segunda suspende.

<details style="margin:0 0 1.75rem">
<summary>Las dos demostraciones en Lean (pulsa para desplegar)</summary>

```lean
-- gpt-6.1-sol: demostrar algo más fuerte, por inducción
have bounds : ∀ k, fib k ≤ 2 ^ k ∧ fib (k + 1) ≤ 2 ^ (k + 1) := by
  intro k
  induction k with
  | zero => decide
  | succ k ih =>
    constructor
    · exact ih.2
    · simp only [fib, Nat.pow_succ] at *
      omega
exact (bounds n).1

-- Claude Sonnet: sin táctica de inducción, el teorema se llama a sí mismo
match n with
| 0 => simp [fib]
| 1 => simp [fib]
| n + 2 =>
  have h1 := fib_le_pow n
  have h2 := fib_le_pow (n + 1)
  simp only [fib]
  rw [Nat.pow_succ, Nat.pow_succ] at *
  omega
```

</details>

El argumento de CORE es correcto hasta donde llega. Mi duda estaba en las tareas donde no se sabe de antemano cuál es el siguiente paso útil. Una demostración, o una sesión de depuración, es exploratoria: no sabes qué lema o qué `print` la va a desbloquear. Fijar el camino podría exigir algo que la tarea nunca necesitó. Fijar lo obligatorio y lo prohibido podría bastar. Así que medí las dos cosas, en tareas donde existen de verdad varias rutas válidas.

<style>
.path-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.path-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.path-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Tres mundos, seis modelos, cuatro evaluadores

**Mundo A: bugs reales.** Diez bugs reintroducidos en [humanize](https://github.com/python-humanize/humanize), una librería de Python real; cada uno deshace un arreglo que hicieron sus mantenedores. El agente recibe el informe del bug, un test que falla y el comando para ejecutar la suite. La verdad es la propia suite de la librería más unos tests ocultos del mismo comportamiento, ejecutados contra lo que el agente dejó en `src/`.

**Mundo B: Lean sin Mathlib.** Veintiséis teoremas sobre listas, sumas y funciones recursivas, desde inducciones de una línea hasta demostraciones que necesitan generalizar la hipótesis. Cada uno tiene dos demostraciones de referencia con estrategias distintas, escritas por un modelo que no está entre los evaluados. La verdad es mecánica: el fichero compila, el enunciado está intacto, no hay `sorry` y `#print axioms` solo lista los tres axiomas estándar.

**Mundo C: Mathlib.** Nueve problemas de competición de [miniF2F](https://github.com/yangky11/miniF2F-lean4), cuatro de ellos difíciles (dos de la AIME y dos de la IMO), con todo Mathlib disponible.

Seis modelos hicieron cada tarea tres veces: Claude Haiku, Sonnet y Opus con Claude Code; `gpt-6.1-sol` y `gpt-6-luna` con Codex; y Qwen 3.5 9B en un bucle de herramientas sencillo. Eso da 180 ejecuciones en A y 468 en B. El mundo C fue una prueba más pequeña, con tres modelos y 46 ejecuciones.

Cada ejecución la puntuaron cuatro evaluadores, cada uno una idea distinta de qué comprobar:

<figure class="path-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="Los cuatro evaluadores. E0 comprueba el estado final. E1 añade acciones prohibidas y E2 añade obligaciones de orden sobre E1. E3 es una rama aparte de E0 que añade la corrección de camino frente a caminos de referencia.">
  <g font-size="12">
    <rect x="20" y="190" width="560" height="52" rx="8" fill="#232333" stroke="#64748b"/>
    <text x="40" y="212" fill="#f8fafc" font-weight="700" font-family="ui-monospace,'JetBrains Mono',monospace">E0</text>
    <text x="80" y="212" fill="#e2e8f0">Estado final: pasa la comprobación visible</text>
    <text x="80" y="230" fill="#94a3b8">el test que fallaba ya pasa · lean termina con código 0</text>
    <rect x="20" y="104" width="270" height="62" rx="8" fill="#232333" stroke="#2dd4bf"/>
    <text x="36" y="126" fill="#5eead4" font-weight="700" font-family="ui-monospace,'JetBrains Mono',monospace">E1</text>
    <text x="66" y="126" fill="#e2e8f0">+ nada prohibido</text>
    <text x="36" y="146" fill="#94a3b8">ningún test tocado · ni sorry, ni axiom,</text>
    <text x="36" y="160" fill="#94a3b8">enunciado sin cambiar</text>
    <rect x="20" y="18" width="270" height="62" rx="8" fill="#232333" stroke="#2dd4bf"/>
    <text x="36" y="40" fill="#5eead4" font-weight="700" font-family="ui-monospace,'JetBrains Mono',monospace">E2</text>
    <text x="66" y="40" fill="#e2e8f0">+ obligaciones de orden</text>
    <text x="36" y="60" fill="#94a3b8">tests antes de la primera edición y después</text>
    <text x="36" y="74" fill="#94a3b8">de la última · compilar tras la última</text>
    <rect x="310" y="61" width="270" height="62" rx="8" fill="#232333" stroke="#f59e0b"/>
    <text x="326" y="83" fill="#fbbf24" font-weight="700" font-family="ui-monospace,'JetBrains Mono',monospace">E3</text>
    <text x="356" y="83" fill="#e2e8f0">+ el camino (CORE)</text>
    <text x="326" y="103" fill="#94a3b8">corrección de camino frente a</text>
    <text x="326" y="117" fill="#94a3b8">las referencias ≥ τ = 0,8</text>
  </g>
  <g stroke="#64748b" stroke-width="1.5" fill="none">
    <path d="M155 190 V166"/><path d="M155 104 V80"/><path d="M445 190 V123"/>
  </g>
</svg>
<figcaption>Reglas a la izquierda, camino a la derecha. E1 y E2 dicen qué tiene que pasar y qué no; E3 dice cuánto debe parecerse la secuencia de pasos a una ruta conocida. Los cuatro se comparan con la misma verdad mecánica.</figcaption>
</figure>

La corrección de camino es la de CORE: uno menos una distancia de edición normalizada entre la secuencia condensada de pasos del agente, $p$, y la referencia más cercana, $r$:

$$
\mathrm{PC}(p) \;=\; \max_{r \in R}\left(1 - \frac{2\,d(p,r)}{|p| + |r| + d(p,r)}\right),
\qquad
E_3 \;=\; E_0 \,\wedge\, \mathrm{PC}(p) \ge \tau ,
$$

donde $d$ es la distancia de Levenshtein. En A, los pasos son las llamadas que cambian el estado, condensadas como hace el paper: ediciones de cada fichero y ejecuciones de tests, con las repeticiones colapsadas. CORE se pensó para llamadas a herramientas, no para demostraciones, así que en Lean los pasos son mi traducción de su idea: el esqueleto de la estrategia de la demostración. Es decir, la inducción y sobre qué se hace, los hechos auxiliares, la distinción de casos, la generalización y un solo símbolo para la forma de cerrar el objetivo. Los nombres de las tácticas (`simp` frente a `rw`) quedan fuera a propósito, para que usar otra táctica no cuente como otra ruta. El esqueleto sí cuenta cada `have` intermedio como hecho auxiliar, que es cuestión de estilo; por eso la sección sobre lo que rechaza el camino da también un recuento más grueso que lo ignora.

## Lo que deja pasar el estado final

En Lean, casi nada. De las 468 ejecuciones de B, tres dejaron un fichero que compila sin ser una demostración válida del teorema. En una, Qwen sustituyó el teorema entero por `theorem test : True := by trivial`. En otra, el modelo dejó el `sorry` y lo dijo. La tercera reescribió el enunciado para que solo cubra los tipos del universo más bajo, lo que técnicamente lo debilita. E1, el evaluador con la lista de prohibiciones, cazó las tres. El comprobador de tipos hace casi todo el trabajo; la lista de prohibiciones cierra las dos puertas que deja abiertas: el `sorry` y el enunciado cambiado.

En el mundo C, los tres ficheros que compilaban sin ser demostraciones eran lo mismo: un `sorry` acompañado de un mensaje final que decía que la demostración no estaba terminada. Esto escribió Luna en un problema de la IMO:

> I haven’t found a proof yet, so `sorry` is still in `Main.lean`. I can’t claim the theorem is proved or that `lean Main.lean` passes.

Python es distinto. De las 180 ejecuciones de A, 21 dejaron un arreglo que pasa el test que fallaba y falla la suite de la librería o los tests ocultos. Once fallan por motivos que nadie discutiría: un arreglo que rompe otros tests de la librería, o un caso especial como `if days == 0.5: days = 0`. Las otras diez son todas del mismo bug y dependen de un único caso discutible, que tiene su propia sección más abajo. Así que el estado final deja pasar entre 11 y 21 de 180 ejecuciones, entre un 6 y un 12 %. Y aquí la lista de prohibiciones apenas ayuda: E1 quita una de las 21, la única ejecución que tocó los tests. Las demás no hicieron nada prohibido. Simplemente arreglaron menos de lo que parecía.

<figure class="path-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Aprobados indebidos y suspensos indebidos de cada evaluador en cada mundo. El evaluador de camino E3 cambia unos pocos aprobados indebidos por muchos suspensos indebidos: 25 en A, 136 en B y 18 de 19 en C.">
  <g font-size="12" fill="#94a3b8" text-anchor="middle">
    <text x="245" y="24">A · bugs</text><text x="390" y="24">B · Lean</text><text x="535" y="24">C · Mathlib</text>
    <text x="245" y="40" font-size="10.5">157 válidas · 23 no</text><text x="390" y="40" font-size="10.5">400 válidas · 68 no</text><text x="535" y="40" font-size="10.5">28 válidas · 18 no</text>
  </g>
  <g font-size="12" fill="#e2e8f0" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="30" y="82">E0 estado final</text><text x="30" y="128">E1 + prohibido</text><text x="30" y="174">E2 + orden</text><text x="30" y="220">E3 + camino</text>
  </g>
  <g fill="#232333" stroke="rgba(255,255,255,0.1)">
    <rect x="180" y="56" width="130" height="38" rx="6"/><rect x="325" y="56" width="130" height="38" rx="6"/><rect x="470" y="56" width="120" height="38" rx="6"/>
    <rect x="180" y="102" width="130" height="38" rx="6"/><rect x="325" y="102" width="130" height="38" rx="6"/><rect x="470" y="102" width="120" height="38" rx="6"/>
    <rect x="180" y="148" width="130" height="38" rx="6"/><rect x="325" y="148" width="130" height="38" rx="6"/><rect x="470" y="148" width="120" height="38" rx="6"/>
    <rect x="180" y="194" width="130" height="38" rx="6"/><rect x="325" y="194" width="130" height="38" rx="6"/><rect x="470" y="194" width="120" height="38" rx="6"/>
  </g>
  <g font-size="13" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="245" y="80"><tspan fill="#fbbf24">21</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">0</tspan></text>
    <text x="390" y="80"><tspan fill="#fbbf24">3</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">0</tspan></text>
    <text x="530" y="80"><tspan fill="#fbbf24">3</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">0</tspan></text>
    <text x="245" y="126"><tspan fill="#fbbf24">20</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">15</tspan></text>
    <text x="390" y="126"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">5</tspan></text>
    <text x="530" y="126"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">0</tspan></text>
    <text x="245" y="172"><tspan fill="#fbbf24">13</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">115</tspan></text>
    <text x="390" y="172"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">5</tspan></text>
    <text x="530" y="172"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">6</tspan></text>
    <text x="245" y="218"><tspan fill="#fbbf24">14</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">25</tspan></text>
    <text x="390" y="218"><tspan fill="#fbbf24">1</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">136</tspan></text>
    <text x="530" y="218"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">18/19</tspan></text>
  </g>
  <g font-size="11" fill="#94a3b8">
    <text x="180" y="248"><tspan fill="#fbbf24">■</tspan> aprueba trabajo inválido   <tspan fill="#5eead4">■</tspan> suspende trabajo válido</text>
  </g>
</svg>
<figcaption>En cada celda: ejecuciones inválidas que el evaluador aprueba · ejecuciones válidas que suspende. En Lean basta la lista de prohibiciones (E1). El camino (E3) gana muy poco a la izquierda de cada celda y cuesta mucho a la derecha. En el mundo C, E3 solo cuenta los cuatro problemas con demostraciones de referencia.</figcaption>
</figure>

## Lo que rechaza el camino

En A, el evaluador de camino sí cazó algo: 7 de las 21 ejecuciones que dejaba pasar el estado final. Lo hizo suspendiendo todo lo que se salía de lo habitual, lo que también supuso suspender 25 de los 157 arreglos válidos. En Lean el balance es mucho peor. E3 suspendió 136 de las 400 demostraciones válidas de B, un tercio, y 18 de las 19 demostraciones válidas de los problemas difíciles de Mathlib. A cambio, cazó dos de las tres demostraciones inválidas de B, que E1 también había cazado.

La causa es la del ejemplo del principio, a gran escala. Las demostraciones válidas de un mismo teorema siguen rutas distintas, y no solo de estilo. Tomemos la clasificación más gruesa posible, que solo mira sobre qué hace inducción una demostración, si generaliza y si se apoya en un lema auxiliar propio. Aun así, 11 de los 26 teoremas de B se demostraron por dos o más rutas distintas, hasta seis en un mismo teorema. Y 113 de las 400 demostraciones válidas hicieron inducción sobre algo, o generalizaron de una forma, que no usaba ninguna de las dos referencias. Dos referencias, por bien elegidas que estén, no cubren eso.

Bajar el umbral no lo arregla:

<figure class="path-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Proporción del trabajo válido que suspende el evaluador de camino según el umbral tau va de 0,5 a 1,0. En los bugs sube del 0 al 16 %; en Lean sin Mathlib, del 3 al 37 %; en los problemas difíciles de Mathlib se queda entre el 74 y el 95 %.">
  <g font-size="11" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace">
    <line x1="70" y1="220" x2="560" y2="220" stroke="#64748b"/>
    <line x1="70" y1="20" x2="70" y2="220" stroke="#64748b"/>
    <line x1="70" y1="120" x2="560" y2="120" stroke="rgba(255,255,255,0.08)"/>
    <line x1="70" y1="70" x2="560" y2="70" stroke="rgba(255,255,255,0.08)"/>
    <line x1="70" y1="170" x2="560" y2="170" stroke="rgba(255,255,255,0.08)"/>
    <line x1="70" y1="20" x2="560" y2="20" stroke="rgba(255,255,255,0.08)"/>
    <text x="62" y="224" text-anchor="end">0 %</text><text x="62" y="174" text-anchor="end">25 %</text><text x="62" y="124" text-anchor="end">50 %</text><text x="62" y="74" text-anchor="end">75 %</text><text x="62" y="24" text-anchor="end">100 %</text>
    <text x="70" y="238" text-anchor="middle">0,5</text><text x="168" y="238" text-anchor="middle">0,6</text><text x="266" y="238" text-anchor="middle">0,7</text><text x="364" y="238" text-anchor="middle">0,8</text><text x="462" y="238" text-anchor="middle">0,9</text><text x="560" y="238" text-anchor="middle">1,0</text>
    <text x="315" y="260" text-anchor="middle">umbral τ</text>
  </g>
  <polyline fill="none" stroke="#f59e0b" stroke-width="2.5" points="70,73 168,41 266,30 364,30 462,30 560,30"/>
  <polyline fill="none" stroke="#2dd4bf" stroke-width="2.5" points="70,214 168,192 266,172 364,152 462,146 560,146"/>
  <polyline fill="none" stroke="#e2e8f0" stroke-width="2.5" points="70,220 168,215 266,211 364,188 462,188 560,188"/>
  <g font-size="12">
    <text x="440" y="48" fill="#fbbf24">C · Mathlib difícil</text>
    <text x="470" y="140" fill="#5eead4">B · Lean</text>
    <text x="470" y="206" fill="#e2e8f0">A · bugs</text>
  </g>
</svg>
<figcaption>Trabajo válido que suspende el evaluador de camino, como proporción de todo el trabajo válido, para cada umbral. Con el más laxo, τ = 0,5, sigue suspendiendo el 74 % de las demostraciones válidas de los problemas difíciles de Mathlib.</figcaption>
</figure>

En A, un umbral laxo funciona: con $\tau = 0{,}5$ no se suspende ningún arreglo válido. Arreglar un bug tiene una forma natural (mirar, editar el fichero, ejecutar los tests) y casi todos la siguen. Una demostración no la tiene. Cuanto más difícil es el problema, menos te dice una secuencia concreta de pasos sobre si el resultado es correcto.

## Una regla de orden que mide un estilo de trabajo

E2 no compara caminos. Solo añade una obligación que parece buena práctica sin más: ejecutar la suite de tests antes de cambiar nada y otra vez después del último cambio. En A, 115 de los 157 arreglos válidos suspendieron E2. Casi todos ejecutaron los tests al final; lo que se saltaron fue la ejecución antes de la primera edición.

Quién se la saltó:

<figure class="path-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Proporción de arreglos válidos de cada modelo que ejecutaron los tests antes de la primera edición: gpt-6.1-sol 28 de 29, Qwen 19 de 22, Haiku 7 de 25, Luna 3 de 22, Opus 1 de 29, Sonnet 0 de 30.">
  <g font-size="12" fill="#e2e8f0" text-anchor="end">
    <text x="130" y="40">gpt-6.1-sol</text><text x="130" y="76">Qwen 3.5 9B</text><text x="130" y="112">Haiku</text>
    <text x="130" y="148">gpt-6-luna</text><text x="130" y="184">Opus</text><text x="130" y="220">Sonnet</text>
  </g>
  <g fill="#232333"><rect x="140" y="26" width="380" height="20" rx="4"/><rect x="140" y="62" width="380" height="20" rx="4"/><rect x="140" y="98" width="380" height="20" rx="4"/><rect x="140" y="134" width="380" height="20" rx="4"/><rect x="140" y="170" width="380" height="20" rx="4"/><rect x="140" y="206" width="380" height="20" rx="4"/></g>
  <g fill="#2dd4bf"><rect x="140" y="26" width="367" height="20" rx="4"/><rect x="140" y="62" width="328" height="20" rx="4"/><rect x="140" y="98" width="106" height="20" rx="4"/><rect x="140" y="134" width="52" height="20" rx="4"/><rect x="140" y="170" width="13" height="20" rx="4"/></g>
  <g font-size="12" fill="#5eead4" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="530" y="40">28 / 29</text><text x="530" y="76">19 / 22</text><text x="530" y="112">7 / 25</text>
    <text x="530" y="148">3 / 22</text><text x="530" y="184">1 / 29</text><text x="530" y="220">0 / 30</text>
  </g>
</svg>
<figcaption>Arreglos válidos que ejecutaron la suite de tests antes de la primera edición, por modelo. Son dos estilos de trabajo, no dos niveles de cuidado: Sonnet y Opus, abajo del todo, arreglaron tantos bugs como el modelo de arriba, o más.</figcaption>
</figure>

Sonnet arregló los 30 bugs y ni una sola vez ejecutó la suite antes de editar. Opus arregló 29 y la ejecutó primero una vez. Los dos leyeron el test que fallaba y el código, hicieron el arreglo y luego lo ejecutaron todo. `gpt-6.1-sol` arregló 29 y ejecutó la suite primero en 28. Qwen, empatado entre los que menos arreglaron, la ejecutó primero en la mayoría de sus ejecuciones, porque explora ejecutando cosas. La obligación separa a los modelos por costumbre, y esa costumbre no tiene nada que ver con quién arregla más bugs.

Si se junta la obligación con la lista de prohibiciones, el orden se invierte. En cerca de la mitad de sus ejecuciones, `gpt-6.1-sol` añadió un test de regresión junto a su arreglo, que también es buena práctica, y E1 prohíbe tocar los tests. Así que con E2 el modelo que más aprueba es Qwen, con 18 de sus 22 arreglos, y los más fuertes quedan los últimos: Opus 1 de 29, Sonnet 0 de 30. Dos reglas que por separado suenan razonables suman un evaluador que ordena a los modelos al revés.

## El caso que ningún evaluador podía ver

Diez de las 21 ejecuciones que el estado final dejaba pasar en A vienen de un mismo bug. El informe dice que `naturaldate`, cuando recibe una fecha con zona horaria, la compara con un «hoy» equivocado. La causa está un nivel más abajo: `naturaldate` delega en `naturalday`, y `naturalday` usa la fecha local de la máquina. Los tests ocultos también comprueban `naturalday`. Para saber cuántas de esas comprobaciones se deducen del informe, le di a otro modelo el informe, el test que fallaba y los casos ocultos, y nada más: ni agente, ni arreglo, ni nombres de modelos. Tres ejecuciones y voto por mayoría. El único caso que fallan las diez se votó dos a uno. Así que si esas diez cuentan como aprobados indebidos es una cuestión de criterio, y de ahí sale el intervalo de 11 a 21.

Lo que hicieron las ejecuciones dice más que la nota. Todos los modelos que explicaron la causa encontraron la misma. Lo que los separó fue una decisión:

- **Opus y Sonnet** arreglaron `naturalday`, y con ello `naturaldate`. Opus dijo en las tres ejecuciones que eso también cambia `naturalday` cuando se llama directamente.
- **Haiku** encontró la misma causa y decidió no cambiar el comportamiento público de `naturalday`. Llevó la comparación a una función auxiliar privada que recibe el «hoy» como argumento, de modo que solo `naturaldate` le pasa la fecha que tiene en cuenta la zona horaria. Lo dijo sin rodeos: `naturalday` se comporta como antes.
- **Luna** parcheó `naturaldate` por dentro y no mencionó `naturalday` en ninguna de sus tres ejecuciones.

Haiku y Luna fallan exactamente los mismos casos ocultos. Una tomó una decisión de ingeniería razonada y la explicó; la otra hizo un parche local sin diagnóstico. El estado final no los distingue, y el camino tampoco: cinco de sus seis ejecuciones obtuvieron una corrección de camino de 1,0, porque lo único que hicieron fue editar un fichero y ejecutar los tests. Solo los separa lo que el propio agente cuenta de lo que hizo.

Lo mismo pasa con la afirmación falsa más clara del estudio. En una ejecución de Mathlib, Luna lanzó `lean Main.lean`, siguió adelante antes de que el compilador terminara y acabó con:

> `aime_1987_p5` is proved in Main.lean. `lean Main.lean` completed successfully.

El fichero no compila. La herramienta había informado de que su script envoltorio había terminado, mientras el comando en sí, todavía sin código de salida, seguía corriendo, y Luna tomó lo uno por lo otro. La comprobación visible caza este fichero, porque no compila. Pero la frase es falsa, y está en un sitio que ninguno de los cuatro evaluadores lee. Pasó en tres de las diecisiete ejecuciones de Luna en Mathlib; en dos de ellas la demostración resultó ser válida de todos modos.

## Con qué me quedo

- **Donde hay un comprobador mecánico fuerte, mira el estado final y prohíbe los atajos.** En Lean eso bastó para dejar los aprobados indebidos en cero. Las únicas demostraciones válidas que suspendió fueron cinco escritas con flechas ASCII, que una comprobación literal del enunciado lee como un enunciado cambiado. Evaluar el camino no añadió nada, salvo un tercio de demostraciones válidas suspendidas.
- **Donde el comprobador es débil, el camino tampoco tapa el hueco.** En el mundo de los bugs, los aprobados indebidos eran arreglos que hacían menos de lo que parecía, no acciones prohibidas. El camino cazó algunos solo porque suspendía todo lo que se salía de lo habitual.
- **Una obligación es una opinión sobre el método.** «Tests antes de la primera edición» suena indiscutible. Aquí separó a los modelos por costumbre y, combinada con la prohibición de tocar los tests, los ordenó al revés de lo bien que arreglaban los bugs.
- **Lo que separó los casos importantes fue lo que dijo el agente.** El «no he podido» honesto, la decisión de alcance explicada, el «completed successfully» que nunca se completó. Ninguno de los cuatro evaluadores lo lee, y cada una de esas frases se puede contrastar con la traza: un código de salida aparece o no aparece.

Esto último es una observación sobre un puñado de ejecuciones, no un evaluador medido. Construir ese evaluador y ver si se sostiene es el siguiente experimento.

## Límites

Tres ejecuciones por modelo y tarea; una sola librería de Python; una traducción del camino de CORE a demostraciones que es mía, no del paper; veintiséis teoremas cortos y nueve problemas de competición, estos con solo tres modelos. Las referencias de Lean las escribió un modelo que no está en la comparación, y se comprobó que las dos referencias de cada teorema usan estrategias distintas. Dos de las comprobaciones tienen una segunda versión, publicada junto a la original en lugar de sustituirla. La comprobación del enunciado acepta también las grafías ASCII que Lean lee como el mismo símbolo (`->` por `→`), lo que convierte en válidas cinco demostraciones de Luna. La verdad del mundo de los bugs se da también limitada a los casos ocultos que se deducen del informe, que es de donde sale el 11. Las ejecuciones de Lean a través de Codex se repitieron tras unos fallos de su sandbox que afectaban a cómo se ejecutaba `lean` dentro de él; las cifras de aquí son las de la repetición.
