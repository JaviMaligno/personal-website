---
title: "La hipótesis del tiempo exponencial ha caído dos veces. El camino era un signo menos"
description: "OpenAI y Anthropic han publicado, cada una por su lado, un algoritmo verificado en Lean que resuelve 3-SAT en tiempo subexponencial y refuta una hipótesis de 27 años sobre la que descansaban cientos de artículos. He leído los dos papers. Chocan con el mismo muro, lo atraviesan de la misma manera, y uno de ellos lo hace con una identidad de hace 200 años sacada de los octoniones."
pubDate: 2026-10-28
tags: ["IA", "Matemáticas", "Complejidad Computacional", "Investigación", "Anthropic", "OpenAI"]
lang: es
translationKey: exponential-time-hypothesis-falls
heroImage: "/blog/exponential-time-hypothesis-falls.png"
linkedinImage: /blog/exponential-time-hypothesis-falls-fig-3.png
linkedinLinks:
  - label: "El paper de Anthropic y la prueba en Lean"
    url: "https://github.com/anthropics/formal-math/tree/main/eth"
  - label: "El paper de OpenAI y la prueba en Lean"
    url: "https://github.com/openai/math/blob/main/lean/docs/378.md"
---

El 26 de octubre aparecieron dos papers con pocas horas de diferencia. Uno, de OpenAI, se titula [*The Exponential Time Hypothesis is False*](https://github.com/openai/math/blob/main/lean/docs/378.md). El otro, de Anthropic, firmado por "Claude", se titula [*A 2^o(n) Time Algorithm for 3-SAT*](https://github.com/anthropics/formal-math/tree/main/eth). Los dos dicen lo mismo: el problema difícil canónico de la informática, decidir si una fórmula booleana se puede satisfacer, no necesita tiempo exponencial. Los dos vienen con una formalización en Lean. Los dos los encontró un modelo interno. El paper de Anthropic fecha el hallazgo el 16 de octubre, "con 14M de tokens de salida y sin intervención humana"; el manuscrito de OpenAI está fechado el 17 de octubre.

Los titulares se quedaron en lo de "la IA resuelve un enigma de hace décadas". Eso deja fuera lo que a mí me parece más interesante, que es el *cómo*. He leído los dos papers, y la respuesta no son dos trucos sin relación. Los dos algoritmos chocan con el mismo muro con el que ha chocado todo algoritmo de SAT desde los años ochenta, y los dos lo atraviesan de la misma manera: resolviendo un problema más difícil que el que se pedía y dejando que los números negativos se cancelen. Uno de ellos lo hace con una identidad que un matemático danés escribió en 1818.

Nada de esto hace más rápidos los SAT solvers, y nada de esto toca P vs NP. Llegaré a por qué. Primero, qué es lo que ha caído.

<style>
.eth-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.eth-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.eth-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Qué decía la hipótesis

Una instancia de 3-SAT es una lista de cláusulas como $(x_1 \lor \lnot x_2 \lor x_5)$ sobre $n$ variables verdadero/falso, y la pregunta es si alguna asignación hace verdaderas todas las cláusulas. Probar las $2^n$ asignaciones siempre funciona. El juego desde los años ochenta ha sido ganarle a eso, y se ha jugado sobre la *base* de la exponencial: el paseo aleatorio de Schöning consiguió $1.334^n$ en 1999, PPSZ con el análisis de Hertli $1.308^n$, el algoritmo determinista de Liu $1.328^n$. Cuarenta años de trabajo muy ingenioso, y la base nunca se acercó a 1.

En 1999 Russell Impagliazzo y Ramamohan Paturi convirtieron esa experiencia en una hipótesis: existe una constante $\delta > 0$ tal que 3-SAT necesita tiempo $2^{\delta n}$. Puedes rebajar la base, dice la **hipótesis del tiempo exponencial** (ETH, por sus siglas en inglés), pero no puedes llevarla a 1. Su hermana más fuerte, SETH, dice que con cláusulas lo bastante largas ni siquiera se puede rebajar mucho.

<figure class="eth-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Gráfico de barras del mejor tiempo conocido para 3-SAT escrito como base elevada a n: fuerza bruta 2, Schöning 1999 1,334, Liu 2018 determinista 1,328, PPSZ con Hertli 2014 aleatorizado 1,308. Los algoritmos de 2026 tienen una base efectiva que tiende a 1 al crecer n, que es lo que refuta la hipótesis del tiempo exponencial.">
  <g font-size="11" fill="#94a3b8">
    <text x="170" y="250" text-anchor="middle">1.0</text>
    <text x="300" y="250" text-anchor="middle">1.25</text>
    <text x="430" y="250" text-anchor="middle">1.5</text>
    <text x="560" y="250" text-anchor="middle">2.0</text>
  </g>
  <g stroke="rgba(255,255,255,0.08)">
    <line x1="170" y1="20" x2="170" y2="236"/><line x1="300" y1="20" x2="300" y2="236"/><line x1="430" y1="20" x2="430" y2="236"/><line x1="560" y1="20" x2="560" y2="236"/>
  </g>
  <g font-size="12" fill="#e2e8f0">
    <text x="160" y="44" text-anchor="end">Fuerza bruta</text>
    <text x="160" y="88" text-anchor="end">Schöning (1999)</text>
    <text x="160" y="132" text-anchor="end">Liu (2018, determ.)</text>
    <text x="160" y="176" text-anchor="end">PPSZ + Hertli (2014)</text>
    <text x="160" y="220" text-anchor="end" fill="#fbbf24" font-weight="700">2026, ambos labs</text>
  </g>
  <!-- scale: base 1 -> x=170, base 2 -> x=560 is not linear for 1.5; use piecewise: 1..1.5 -> 170..430 (520 px per unit), 1.5..2 -> 430..560 -->
  <rect x="170" y="30" width="390" height="22" rx="4" fill="#64748b"/>
  <rect x="170" y="74" width="174" height="22" rx="4" fill="#2dd4bf" opacity=".75"/>
  <rect x="170" y="118" width="171" height="22" rx="4" fill="#2dd4bf" opacity=".75"/>
  <rect x="170" y="162" width="160" height="22" rx="4" fill="#2dd4bf"/>
  <rect x="170" y="206" width="6" height="22" rx="2" fill="#f59e0b"/>
  <g font-size="12" font-family="ui-monospace,'JetBrains Mono',monospace" fill="#f8fafc">
    <text x="548" y="46" text-anchor="end">2ⁿ</text>
    <text x="352" y="90">1.334ⁿ</text>
    <text x="349" y="134">1.328ⁿ</text>
    <text x="338" y="178">1.308ⁿ</text>
    <text x="186" y="222" fill="#fbbf24">2^o(n): la base tiende a 1</text>
  </g>
</svg>
<figcaption>Cuarenta años de avances en 3-SAT bajaron la base de la exponencial. ETH apostaba a que nunca llegaría a 1. Los nuevos algoritmos tardan 2^o(n): su base efectiva se desliza hacia 1 al crecer n. (El eje está comprimido entre 1,5 y 2.)</figcaption>
</figure>

No era una apuesta cualquiera. El paper de Anthropic cuenta una búsqueda bibliográfica, hecha por Claude, que encontró más de 800 artículos que demuestran al menos un resultado propio solo bajo ETH o bajo algo que la implica. ETH es la razón por la que "sabemos" que k-Clique no tiene un algoritmo $n^{o(k)}$, que muchos algoritmos parametrizados son óptimos, que la programación dinámica sobre descomposiciones en árbol no se puede mejorar. En 2019 Ryan Williams estimaba en un 70% la probabilidad de que ETH fuera cierta, y en un 25% la de SETH. La mayor parte del campo habría dado cifras más altas.

Los dos papers dan ahora un algoritmo determinista que corre en $2^{o(n)}$: para todo $\delta > 0$, acaba siendo más rápido que $2^{\delta n}$. Eso refuta de una vez ETH, SETH, Gap-ETH y la versión de conteo, #ETH.

## El muro

Esta es la intuición de por qué la base nunca llegó a 1, y es el mismo dibujo en los dos papers.

Dibuja la fórmula como un grafo: las cláusulas son nodos, y dos cláusulas se unen si comparten variables. El paper de Anthropic dice que cada arista "lleva bits", uno por variable compartida. El algoritmo rápido natural es divide y vencerás: corta el grafo en dos mitades, enumera todos los valores posibles de los bits que cruzan el corte y, para cada valor, resuelve las dos mitades por separado. Si cruzan pocos bits, eso es muchísimo más rápido que la fuerza bruta.

El problema es que la fórmula no la eliges tú. Las fórmulas aleatorias, y en general las instancias difíciles, parecen **grafos expansores**, en los que cualquier forma de partir los nodos en dos mitades de tamaño comparable la cruza una fracción constante de todas las aristas. En palabras del paper, "cualquier algoritmo que fije de antemano un árbol de cortes y enumere los bits que cruzan cada corte tarda $2^{\Omega(n)}$. Por eso las ideas anteriores de divide y vencerás solo mejoraban la constante del exponente."

<figure class="eth-fig">
<svg viewBox="0 0 600 262" role="img" aria-label="Dos grafos lado a lado. A la izquierda, una fórmula cuyo grafo de cláusulas tiene dos grupos poco conectados: un corte entre ellos lo cruzan solo dos aristas, así que divide y vencerás sale barato. A la derecha, un grafo tipo expansor en el que cualquier corte equilibrado lo cruzan muchas aristas, así que enumerar los bits que cruzan cuesta tiempo exponencial elija el corte que elija.">
  <text x="150" y="22" text-anchor="middle" font-size="13" fill="#e2e8f0" font-weight="700">Fórmula agrupada</text>
  <text x="450" y="22" text-anchor="middle" font-size="13" fill="#e2e8f0" font-weight="700">Fórmula tipo expansor</text>
  <g stroke="#64748b" stroke-width="1.6">
    <line x1="60" y1="70" x2="100" y2="110"/><line x1="60" y1="70" x2="50" y2="140"/><line x1="100" y1="110" x2="50" y2="140"/><line x1="100" y1="110" x2="80" y2="185"/><line x1="50" y1="140" x2="80" y2="185"/><line x1="60" y1="70" x2="110" y2="60"/><line x1="110" y1="60" x2="100" y2="110"/>
    <line x1="200" y1="70" x2="240" y2="110"/><line x1="200" y1="70" x2="250" y2="150"/><line x1="240" y1="110" x2="250" y2="150"/><line x1="250" y1="150" x2="215" y2="190"/><line x1="240" y1="110" x2="215" y2="190"/><line x1="200" y1="70" x2="190" y2="130"/><line x1="190" y1="130" x2="215" y2="190"/>
  </g>
  <g stroke="#f59e0b" stroke-width="2.2">
    <line x1="110" y1="60" x2="200" y2="70"/><line x1="80" y1="185" x2="190" y2="130"/>
  </g>
  <line x1="150" y1="40" x2="150" y2="210" stroke="#fbbf24" stroke-width="1.5" stroke-dasharray="5 4"/>
  <g fill="#1a1a24" stroke="#2dd4bf" stroke-width="2">
    <circle cx="60" cy="70" r="7"/><circle cx="100" cy="110" r="7"/><circle cx="50" cy="140" r="7"/><circle cx="80" cy="185" r="7"/><circle cx="110" cy="60" r="7"/>
    <circle cx="200" cy="70" r="7"/><circle cx="240" cy="110" r="7"/><circle cx="250" cy="150" r="7"/><circle cx="215" cy="190" r="7"/><circle cx="190" cy="130" r="7"/>
  </g>
  <text x="150" y="250" text-anchor="middle" font-size="12" fill="#fbbf24">cruzan 2 aristas: enumerar 2 bits</text>
  <g transform="translate(450,132)">
    <g stroke="#64748b" stroke-width="1.4">
      <line x1="0" y1="-85" x2="74" y2="42"/><line x1="0" y1="-85" x2="-74" y2="42"/><line x1="0" y1="-85" x2="42" y2="74"/>
      <line x1="42" y1="-74" x2="-42" y2="74"/><line x1="42" y1="-74" x2="-85" y2="0"/><line x1="42" y1="-74" x2="0" y2="85"/>
      <line x1="74" y1="-42" x2="-74" y2="-42"/><line x1="74" y1="-42" x2="-42" y2="74"/><line x1="74" y1="-42" x2="-42" y2="-74"/>
      <line x1="85" y1="0" x2="-85" y2="0"/><line x1="85" y1="0" x2="-42" y2="-74"/><line x1="85" y1="0" x2="0" y2="85"/>
      <line x1="74" y1="42" x2="-74" y2="-42"/><line x1="42" y1="74" x2="-74" y2="42"/><line x1="0" y1="85" x2="-74" y2="-42"/><line x1="-42" y1="74" x2="-85" y2="0"/>
      <line x1="0" y1="-85" x2="42" y2="-74"/><line x1="74" y1="42" x2="85" y2="0"/><line x1="-74" y1="42" x2="-42" y2="74"/><line x1="-42" y1="-74" x2="-74" y2="-42"/>
    </g>
    <line x1="-15" y1="-100" x2="15" y2="100" stroke="#fbbf24" stroke-width="1.5" stroke-dasharray="5 4"/>
    <g fill="#1a1a24" stroke="#2dd4bf" stroke-width="2">
      <circle cx="0" cy="-85" r="7"/><circle cx="42" cy="-74" r="7"/><circle cx="74" cy="-42" r="7"/><circle cx="85" cy="0" r="7"/><circle cx="74" cy="42" r="7"/><circle cx="42" cy="74" r="7"/><circle cx="0" cy="85" r="7"/><circle cx="-42" cy="74" r="7"/><circle cx="-74" cy="42" r="7"/><circle cx="-85" cy="0" r="7"/><circle cx="-74" cy="-42" r="7"/><circle cx="-42" cy="-74" r="7"/>
    </g>
  </g>
  <text x="450" y="250" text-anchor="middle" font-size="12" fill="#fbbf24">cualquier corte equilibrado: muchos bits</text>
</svg>
<figcaption>Divide y vencerás paga por los bits que cruzan el corte. En las fórmulas difíciles cualquier corte equilibrado lo cruza una fracción constante de los bits, así que cualquier plan fijo de cortes cuesta 2^Ω(n). Este es el muro.</figcaption>
</figure>

Para atravesar el muro hay que dejar de pagar por cada bit que cruza. Y no hay manera de hacerlo si cada cantidad que manejas significa "número de soluciones de algo", porque los recuentos de soluciones no son negativos y no se pueden cancelar.

## Contar, no decidir

Así que los dos papers hacen algo que suena al revés. No deciden si existe una asignación que satisface la fórmula. Las **cuentan**, exactamente, que es el problema #3-SAT y en principio es mucho más difícil (lo mejor que había para contar rondaba $1.64^n$, peor que para decidir). Comprobar si la cuenta es cero decide la satisfacibilidad gratis.

¿Por qué complicarse la vida? Porque una cuenta es una suma, y una suma es álgebra. El número de asignaciones que satisfacen la fórmula es

$$\#F = \sum_{x \in \{0,1\}^n} \prod_{\text{cláusulas } e} \Phi_e(x)$$

donde cada $\Phi_e$ vale 1 si la cláusula $e$ se cumple y 0 si no. Una suma de productos se puede reordenar, reescribir, expandir y reagrupar, y nada obliga a que los términos intermedios valgan 0 o 1, ni siquiera a que sean positivos. En cuanto se admiten números negativos a mitad del cálculo, dos piezas caras pueden cancelarse en una barata. Los algoritmos de ramificación, que preguntan "¿y si $x_1$ es verdadera?", no pueden hacer esto: cada rama es una subpregunta real con una respuesta real no negativa.

Ese es el movimiento común. A partir de ahí los dos papers lo implementan de maneras completamente distintas.

## La ruta de Claude: una identidad de 1818

El algoritmo de Anthropic se queda con el dibujo del grafo y ataca los bits que cruzan.

Toma el grafo de cláusulas y agrupa las cláusulas en un número modesto $K$ de nodos grandes, de forma que cada par de nodos grandes esté unido por una arista que lleva el mismo número $\lambda$ de bits. La cantidad a batir es el total de bits que cruzan, $S$. Ahora coloca los nodos en una cuadrícula de $g \times g$. La mayoría de las aristas son *diagonales*: unen dos nodos en filas distintas y columnas distintas. Cada diagonal pertenece exactamente a un rectángulo, y cada rectángulo tiene dos diagonales: la esquina superior izquierda guarda una cadena $x$ que tiene que coincidir con la $v$ de la inferior derecha, y la superior derecha guarda $y$, que tiene que coincidir con la $u$ de la inferior izquierda. Ese par de comprobaciones de igualdad, $[x = v]\,[y = u]$, es lo que el paper llama un cruce.

Si fusionas cada fila en un solo nodo, un cruce cuesta 6 bits por cada bloque de 3: la fila de arriba tiene que contarle a la de abajo tanto $x$ como $y$. Aquí entra la identidad. Para bloques de 3 bits existe una función de signos $\sigma$ tal que

$$2\,[x = v]\,[y = u] = [x \oplus y \oplus u \oplus v = 0]\,\big(\sigma(x,y)\,\sigma(v,u) + \sigma(x,u)\,\sigma(v,y)\big)$$

y se puede comprobar por fuerza bruta en los 4.096 valores posibles de los 12 bits. Lee el lado derecho como dos términos. En el primero, la **elección por filas**, cada $\sigma$ depende de una sola fila, y las dos filas solo tienen que ponerse de acuerdo en una cadena de 3 bits, $x \oplus y = u \oplus v$. Eso cuesta 3 bits, la mitad de 6. El segundo término, la **elección por columnas**, sigue siendo caro si fusionaste filas, pero cuesta solo 3 bits si en vez de eso fusionas columnas. Ninguno de los dos términos significa nada combinatoriamente, toman valores negativos, y solo su suma es una cuenta. Pero cada término es barato en una dirección.

<figure class="eth-fig">
<svg viewBox="0 0 640 280" role="img" aria-label="Un rectángulo de la cuadrícula con las cadenas x, y arriba y u, v abajo. Sus dos diagonales comprueban que x es igual a v y que y es igual a u, lo que cuesta seis bits por bloque si se fusionan las filas. La identidad de los ocho cuadrados reescribe el doble de este cruce como una comprobación de paridad sobre las cuatro esquinas por la suma de una elección por filas, cuyas funciones de signo viven cada una en una fila y cuestan tres bits, y una elección por columnas, que cuesta seis bits con las filas fusionadas pero tres con las columnas fusionadas.">
  <defs>
    <marker id="eth-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <g font-size="12.5" text-anchor="middle" fill="#e2e8f0" font-weight="700">
    <text x="100" y="24">2 × cruce</text>
    <text x="300" y="24" fill="#5eead4">elección por filas</text>
    <text x="520" y="24" fill="#fbbf24">elección por columnas</text>
  </g>
  <text x="200" y="118" font-size="22" fill="#94a3b8" text-anchor="middle">=</text>
  <text x="400" y="118" font-size="22" fill="#94a3b8" text-anchor="middle">+</text>
  <!-- panel 1 -->
  <g stroke="#e2e8f0" stroke-width="2">
    <line x1="50" y1="60" x2="150" y2="170"/><line x1="150" y1="60" x2="50" y2="170"/>
  </g>
  <!-- panel 2: hyperedge + row edges -->
  <g stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="3 3">
    <line x1="250" y1="60" x2="300" y2="115"/><line x1="350" y1="60" x2="300" y2="115"/><line x1="250" y1="170" x2="300" y2="115"/><line x1="350" y1="170" x2="300" y2="115"/>
    <line x1="470" y1="60" x2="520" y2="115"/><line x1="570" y1="60" x2="520" y2="115"/><line x1="470" y1="170" x2="520" y2="115"/><line x1="570" y1="170" x2="520" y2="115"/>
  </g>
  <circle cx="300" cy="115" r="4" fill="#94a3b8"/><circle cx="520" cy="115" r="4" fill="#94a3b8"/>
  <g stroke="#2dd4bf" stroke-width="3"><line x1="250" y1="60" x2="350" y2="60"/><line x1="250" y1="170" x2="350" y2="170"/></g>
  <g stroke="#f59e0b" stroke-width="3"><line x1="470" y1="60" x2="470" y2="170"/><line x1="570" y1="60" x2="570" y2="170"/></g>
  <g fill="#1a1a24" stroke="#2dd4bf" stroke-width="2">
    <circle cx="50" cy="60" r="15"/><circle cx="150" cy="60" r="15"/><circle cx="50" cy="170" r="15"/><circle cx="150" cy="170" r="15"/>
    <circle cx="250" cy="60" r="15"/><circle cx="350" cy="60" r="15"/><circle cx="250" cy="170" r="15"/><circle cx="350" cy="170" r="15"/>
    <circle cx="470" cy="60" r="15"/><circle cx="570" cy="60" r="15"/><circle cx="470" cy="170" r="15"/><circle cx="570" cy="170" r="15"/>
  </g>
  <g font-size="13" text-anchor="middle" fill="#f8fafc" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="50" y="65">x</text><text x="150" y="65">y</text><text x="50" y="175">u</text><text x="150" y="175">v</text>
    <text x="250" y="65">x</text><text x="350" y="65">y</text><text x="250" y="175">u</text><text x="350" y="175">v</text>
    <text x="470" y="65">x</text><text x="570" y="65">y</text><text x="470" y="175">u</text><text x="570" y="175">v</text>
  </g>
  <g font-size="10.5" text-anchor="middle" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="100" y="204">x=v · y=u</text>
    <text x="300" y="50">σ(x,y)</text><text x="300" y="192">σ(v,u)</text>
    <rect x="264" y="131" width="72" height="13" fill="#1a1a24"/><text x="300" y="141">x⊕y⊕u⊕v=0</text>
    <text x="460" y="119" text-anchor="end">σ(x,u)</text><text x="580" y="119" text-anchor="start">σ(v,y)</text>
    <rect x="484" y="131" width="72" height="13" fill="#1a1a24"/><text x="520" y="141">x⊕y⊕u⊕v=0</text>
  </g>
  <line x1="20" y1="218" x2="620" y2="218" stroke="rgba(255,255,255,0.1)"/>
  <text x="20" y="236" font-size="11.5" fill="#94a3b8">con las filas fusionadas, bits por bloque de 3:</text>
  <g font-size="14" text-anchor="middle" font-weight="700">
    <text x="100" y="264" fill="#e2e8f0">6 bits</text>
    <text x="300" y="264" fill="#5eead4">3 bits</text>
    <text x="520" y="264" fill="#fbbf24">6 bits (3 con columnas)</text>
  </g>
</svg>
<figcaption>La identidad de los ocho cuadrados para un rectángulo. Dos comprobaciones en diagonal se convierten en una comprobación de paridad sobre las cuatro esquinas por una suma con signos de dos términos. Cada término es barato en una dirección de la cuadrícula, así que fusiones en la dirección que fusiones, una parte de los bits desaparece.</figcaption>
</figure>

El resto es contabilidad, hecha con cuidado. Las cadenas se parten en bloques de 3, y la expansión se agrupa según cuántos bloques tomaron la elección por columnas, lo que mantiene polinómico el número de términos. Para cada término el algoritmo fusiona filas o columnas, lo que salga más barato. Por bloque, las dos direcciones juntas cuestan $3 + 6 + 1 + 1 = 11$ bits frente a los $12$ de dos cruces, así que la dirección más barata paga como mucho $11/12$ de lo que había antes. Después agrupa las filas fusionadas en $K$ supernodos equilibrados y se llama a sí mismo.

Un nivel encoge el exponente en un factor $11/12$. Repítelo y el exponente tiende a cero: la cota del paper es $e_\ell \le 1.12\,(11/12)^\ell$. El precio es que cada nivel necesita muchísimos más nodos, $K_\ell = 9K_{\ell-1}^{16}$ empezando en 64, y por eso todo esto solo importa para fórmulas astronómicamente grandes.

<figure class="eth-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Gráfico del exponente del tiempo de ejecución en cada nivel de la recursión del algoritmo de Anthropic. El nivel 0 es la fuerza bruta, con exponente 1. El nivel 1 es algo peor, unos 1,03, porque la primera cuadrícula es pequeña. A partir del nivel 2 el exponente baja un factor de once doceavos por nivel, acotado por 1,12 por once doceavos elevado al nivel, queda por debajo de 0,47 en el nivel 10 y tiende a cero.">
  <g stroke="rgba(255,255,255,0.08)"><line x1="60" y1="30" x2="580" y2="30"/><line x1="60" y1="105" x2="580" y2="105"/><line x1="60" y1="180" x2="580" y2="180"/></g>
  <g font-size="11" fill="#94a3b8" text-anchor="end"><text x="52" y="34">1.0</text><text x="52" y="109">0.5</text><text x="52" y="184">0</text></g>
  <g fill="#2dd4bf">
    <rect x="72" y="30" width="30" height="150" fill="#64748b"/>
    <rect x="119" y="25.5" width="30" height="154.5" fill="#64748b"/>
    <rect x="166" y="38.8" width="30" height="141.2"/>
    <rect x="213" y="50.6" width="30" height="129.4"/>
    <rect x="260" y="61.4" width="30" height="118.6"/>
    <rect x="307" y="71.3" width="30" height="108.7"/>
    <rect x="354" y="80.3" width="30" height="99.7"/>
    <rect x="401" y="88.6" width="30" height="91.4"/>
    <rect x="448" y="96.2" width="30" height="83.8"/>
    <rect x="495" y="103.2" width="30" height="76.8"/>
    <rect x="542" y="109.6" width="30" height="70.4"/>
  </g>
  <g font-size="11" fill="#e2e8f0" text-anchor="middle">
    <text x="87" y="198">0</text><text x="134" y="198">1</text><text x="181" y="198">2</text><text x="228" y="198">3</text><text x="275" y="198">4</text><text x="322" y="198">5</text><text x="369" y="198">6</text><text x="416" y="198">7</text><text x="463" y="198">8</text><text x="510" y="198">9</text><text x="557" y="198">10</text>
  </g>
  <text x="320" y="222" font-size="11.5" fill="#94a3b8" text-anchor="middle">nivel de recursión ℓ (cota e_ℓ ≤ 1.12 · (11/12)^ℓ desde el nivel 2)</text>
  <text x="87" y="22" font-size="10.5" fill="#94a3b8" text-anchor="middle">bruta</text>
</svg>
<figcaption>Cada nivel de la recursión multiplica el exponente por unos 11/12. No llega a cero en ningún nivel fijo, pero baja de cualquier δ que digas, que es exactamente lo que hace falta para refutar ETH.</figcaption>
</figure>

La identidad es la parte bonita. En su forma clásica dice que el producto de dos sumas de ocho cuadrados vuelve a ser una suma de ocho cuadrados. Ferdinand Degen la encontró en 1818, y John Graves la volvió a encontrar en 1843 al demostrar que la norma de los octoniones, los primos de ocho dimensiones de los números complejos, es multiplicativa. La función de signos $\sigma$ del algoritmo es, en palabras del paper, "la tabla de signos de la multiplicación de los octoniones, con los elementos de la base renombrados". Hurwitz demostró en 1898 que identidades así solo existen para 1, 2, 4 y 8 cuadrados. El paper tiene un apéndice que explica por qué buscar una descomposición más barata de un cruce lleva directamente al problema de Hurwitz, y por qué, con el recuento sencillo de bits que usa, solo la de ocho deja ganancia: la de dos cuadrados se queda igual, la de cuatro se queda igual, la de ocho da 11 de cada 12.

O sea, lo que ha tumbado ETH es la tabla de multiplicar de los octoniones, usada para recortar bits en una cuadrícula.

## La ruta de OpenAI: deformar el problema y volver interpolando

El algoritmo de OpenAI usa la misma idea, "contar y dejar que los términos se cancelen", pero entra por otra puerta: la interpolación.

Parte de la misma fórmula para $\#F$. Ahora introduce un parámetro $T$ y sustituye cada aparición de una variable dentro de cada cláusula por una combinación lineal de variables cuyos coeficientes son polinomios en $T$. En $T = 0$ cada sustitución es la variable original, así que la suma deformada $H(T)$ cumple $H(0) = \#F$. En los puntos $T = 1, \dots, Q$, las sustituciones están diseñadas para que las variables se separen en grupos pequeños que solo interactúan a través de unas pocas "medidas" compartidas, combinaciones lineales enteras y pequeñas de los bits de cada grupo. Fija los valores de esas medidas y la suma se factoriza grupo a grupo, exactamente como lo haría la fórmula agrupada de la figura anterior. En esos puntos el problema caro se vuelve barato.

<figure class="eth-fig">
<svg viewBox="0 0 600 240" role="img" aria-label="Esquema de la estrategia de interpolación de OpenAI. Un polinomio H de T dibujado como curva. En T igual a cero, su valor es el número exacto de asignaciones que satisfacen la fórmula, difícil de calcular directamente. En los puntos T igual a uno hasta Q, el problema se separa en grupos y es barato, así que el algoritmo calcula ahí el valor y unos pocos coeficientes de Taylor, dibujados como trazos tangentes cortos. Como el grado de H es conocido, eso determina H, y por tanto H de cero.">
  <line x1="50" y1="200" x2="580" y2="200" stroke="#64748b" stroke-width="1.5"/>
  <line x1="80" y1="30" x2="80" y2="210" stroke="#64748b" stroke-width="1.5"/>
  <path d="M80,70 C140,170 190,40 250,110 S350,180 410,95 S520,60 570,140" fill="none" stroke="#e2e8f0" stroke-width="2"/>
  <circle cx="80" cy="70" r="8" fill="#1a1a24" stroke="#f59e0b" stroke-width="3"/>
  <text x="98" y="48" font-size="12" fill="#fbbf24" font-weight="700">H(0) = #F</text>
  <text x="98" y="63" font-size="11" fill="#94a3b8">la cuenta que buscamos: difícil aquí</text>
  <g stroke="#2dd4bf" stroke-width="3">
    <line x1="182" y1="85" x2="214" y2="61"/>
    <line x1="272" y1="124" x2="308" y2="148"/>
    <line x1="342" y1="166" x2="378" y2="146"/>
    <line x1="432" y1="80" x2="468" y2="72"/>
    <line x1="508" y1="74" x2="540" y2="96"/>
  </g>
  <g fill="#2dd4bf"><circle cx="198" cy="73" r="5"/><circle cx="290" cy="136" r="5"/><circle cx="360" cy="156" r="5"/><circle cx="450" cy="76" r="5"/><circle cx="524" cy="85" r="5"/></g>
  <g font-size="11" fill="#e2e8f0" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="80" y="218">0</text><text x="198" y="218">1</text><text x="290" y="218">2</text><text x="360" y="218">3</text><text x="450" y="218">…</text><text x="524" y="218">Q</text>
  </g>
  <text x="360" y="236" font-size="11.5" fill="#5eead4" text-anchor="middle">puntos fáciles: los grupos se separan; valor + unos coeficientes de Taylor</text>
  <path d="M175,95 C140,110 115,95 92,78" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#eth-ar2)"/>
  <defs><marker id="eth-ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
  <text x="128" y="128" font-size="10.5" fill="#94a3b8" text-anchor="middle">interpolar</text>
  <text x="128" y="141" font-size="10.5" fill="#94a3b8" text-anchor="middle">de vuelta (exacto)</text>
</svg>
<figcaption>La estrategia de OpenAI: deformar el problema de contar en un polinomio H(T) de grado conocido. En T = 0 es la cuenta; en T = 1…Q se separa en grupos independientes. Unos pocos coeficientes de Taylor en cada punto fácil fijan el polinomio, y con él la cuenta.</figcaption>
</figure>

Como $H$ es un polinomio de grado conocido, sus valores y unas pocas derivadas en los puntos fáciles lo determinan por completo, y de ahí se lee $H(0)$. Aquí interpolar no es aproximar: es aritmética racional exacta. Toda la dificultad está en la tensión entre dos costes. Las sustituciones tienen que tener grado bajo en $T$, o necesitas demasiados coeficientes de Taylor por punto. Y tienen que respetar una agrupación *distinta* en cada uno de los $Q$ puntos, lo que, hecho a lo ingenuo, cuesta grado $Q$.

La construcción que lo resuelve es donde vuelve el signo menos. Está hecha de **intercambios** (*swaps*): matrices de permutación $\Pi_s$ que intercambian dos etiquetas de grupo en la posición $s$, cada una con autovalores $+1$ y $-1$. Un vector de la base con $j$ de sus posiciones en el autoespacio $-1$ queda multiplicado por $(-1)^j$ bajo el intercambio completo. OpenAI elige un polinomio $f$ que interpola $(-1)^j$ solo en una ventana corta de valores de $j$, centrada donde una distribución binomial concentra casi toda su masa. Dentro de la ventana la construcción es exacta; las pocas direcciones que quedan fuera se pagan con medidas explícitas. La ventana solo necesita ser tan ancha como la desviación típica de la binomial, $\sqrt{Q}$, y con $Q \approx \log n$ de ahí sale el $\sqrt{\log n}$ de la cota final.

Multiplica los tres costes (datos de Taylor, medidas, un grupo cada vez) y cada uno es $2^{o(n)}$. Además el algoritmo usa espacio polinómico, cosa que el de Anthropic no afirma.

## El mismo muro, el mismo signo menos

Uno al lado del otro:

| | OpenAI | Anthropic (Claude) |
|---|---|---|
| Fecha del paper | 17 de octubre, revisado el 25 | 26 de octubre; núcleo encontrado el 16 |
| Extensión | 67 páginas | 49 páginas |
| Qué calcula | #k-SAT exacto, determinista | #k-SAT exacto, determinista |
| Cota, fórmulas dispersas | $2^{O(n/\sqrt{\log n})}$ | $2^{O(m/\sqrt{\log m})}$ en el número de cláusulas |
| Cota, cualquier fórmula | $2^{O(n \log\log n/\sqrt{\log n})}$ | $2^{O(k^2 n \log\log n/\sqrt{\log n})}$ |
| Cota demostrada en Lean | más débil: $(\log\log n)^2$ en lugar de $\log\log n$ | el teorema principal tal como se enuncia |
| Pieza clave | deformación + interpolación de Hermite; matrices de intercambio, $f(j) = (-1)^j$ | cuadrícula + identidad de los ocho cuadrados; recursión con factor 11/12 |
| Espacio | polinómico | no se afirma |

Las cotas caen en el mismo sitio, lo que o es una coincidencia o es una pista de dónde está la barrera natural de esta familia de técnicas. Ninguno de los dos papers sabe quitar el $\log\log n$ para fórmulas generales.

Y los mecanismos riman más de lo que parece. La construcción de OpenAI está hecha literalmente de operadores de intercambio con autovalores $\pm 1$. El README de Anthropic condensa su propia idea clave en un párrafo que incluye "Per bit, SWAP = I − 2·singlet", la forma de físico de escribir un intercambio como la identidad menos una corrección con signo. Los dos papers resuelven un problema más difícil para poder trabajar con cantidades con signo, y los dos sacan su ahorro de escribir el intercambio de dos cosas como una combinación de cosas más baratas con signos. El mundo no negativo, donde cada número intermedio cuenta soluciones de algo, es exactamente donde ETH era cierta.

## Qué cambia y qué no

**En la práctica no cambia nada.** El paper de Anthropic es inusualmente directo al respecto. Para una 3-CNF con $m = 5n$ cláusulas, su cota solo mejora los $2^n$ de la fuerza bruta cuando $n > 10^{10\,000}$, y la cota solo en $n$, cuando $n > 10^{10^8}$. Los autores añaden que su enfoque general "parece poco probable que dé ninguna mejora general salvo que $n > 10^7$, se instancie como se instancie", mientras que la fuerza bruta ya es imposible con $n = 100$. Tu SAT solver, tu planificador, tu herramienta de verificación van exactamente igual de rápido que la semana pasada.

**P vs NP sigue intacto.** Una cota $2^{o(n)}$ para 3-SAT no se traslada a todos los problemas NP, porque las reducciones en tiempo polinómico pueden inflar polinómicamente el número de variables, y $2^{o(n)}$ compuesto con un polinomio ya no es subexponencial. Para problemas con reducciones que mantienen el tamaño lineal, sí se traslada: OpenAI obtiene conteo subexponencial de conjuntos independientes, coloraciones propias y emparejamientos perfectos; Anthropic lista Independent Set, Clique, Vertex Cover y Dominating Set en $O(2^{\delta n})$ para todo $\delta > 0$.

**Una estantería de teoremas ha cambiado de estado.** Todo lo demostrado "bajo ETH" o "bajo SETH" ha perdido su hipótesis. Parte sobrevive sobre cimientos más débiles: las cotas inferiores cuadráticas para la distancia de edición y la subsecuencia común más larga también se siguen de la conjetura de Orthogonal Vectors, que ninguno de los dos papers refuta. Mucho de lo demás, el equivalente a unos 800 artículos, necesita ahora otra razón para ser cierto o resulta ser falso.

**Y hay una ganancia de verdad incondicional.** Gracias al programa de Ryan Williams, que convierte algoritmos de SAT un poco más rápidos que la fuerza bruta en cotas inferiores de circuitos, los dos papers obtienen que la clase $E^{NP}$ no tiene circuitos booleanos de tamaño lineal. La versión de OpenAI da una cota inferior del orden de $n\sqrt{\log n}$. Lo mejor que se conocía antes, sobre la base binaria completa, era $3.1n$. Las cotas inferiores de circuitos son una de las áreas más atascadas de la teoría de la complejidad, y esta ha salido como efecto secundario.

## Qué comprueba Lean y qué no

Los dos resultados están formalizados, y los dos equipos tienen cuidado con lo que eso significa. El README de Anthropic lo dice en una frase que me gustaría ver en toda formalización: "Lean comprueba las demostraciones, pero ninguna máquina comprueba que este fichero dice lo que dice el paper; el fichero se mantiene corto para que un lector pueda comprobarlo." La nota de alcance de OpenAI en Lean es igual de precisa: la cota comprobada por la máquina es la más débil, con $(\log\log n)^2$; la cota más fina del paper no lo está.

Ese es el hueco del que escribí en [Demostrado, certificado, barrido, muestreado](/es/blog/proved-certified-swept-sampled): un check en verde es una afirmación sobre una afirmación concreta, y el trabajo está en saber cuál. Aquí está bien resuelto. Los enunciados son cortos, están impresos en los papers y las diferencias con la prosa están listadas. Mientras escribo esto, la revisión humana sigue en marcha: según la cobertura, OpenAI ha entregado su resultado a revisores externos entre los que están el propio Impagliazzo y Paturi. Una prueba en Lean de un teorema bien enunciado les deja muy poco que encontrar, pero "bien enunciado" es justo la parte para la que están.

## La demostración que cabe en un prompt

Un detalle más, y para alguien que construye con estos modelos es el que se me queda. Al final del README de Anthropic hay una sección titulada "The key idea, in condensed form interpretable by AI models". Es un solo párrafo. Empieza con "The exponential time hypothesis is false!", enuncia una recursión para el coste de contraer redes de tensores sobre un grafo completo, menciona la cuadrícula, el intercambio, la agrupación por número de singletes, y termina con "Prove it." El README dice que Claude Opus 5.5 con esfuerzo alto puede volver a derivar la refutación, en su forma más débil $O(2^{\delta n})$, solo a partir de ese párrafo.

Eso es un tipo nuevo de objeto matemático. Durante siglos una demostración se ha escrito para un lector humano, con el nivel de detalle que ese lector necesite. Aquí hay tres capas: un paper de 49 páginas para personas, un desarrollo en Lean para el kernel y una pista de un párrafo para un modelo, que basta porque el modelo rellena el resto. Cuando escribí sobre [la explosión de Navier–Stokes](/es/blog/navier-stokes-blows-up), el cuello de botella era el contrario: los borradores de la máquina eran casi ilegibles, y convertirlos en un paper que una persona pudiera seguir fueron semanas de trabajo. Siete semanas después, la descripción más comprimida de un resultado importante es la que está escrita para una máquina.

## Qué me llevo

- **ETH es falsa, dos veces, de forma independiente, con demostraciones formales**, a falta de la revisión humana que está en marcha. SETH, Gap-ETH y #ETH caen con ella.
- **El muro era el expansor, y el camino era un signo menos.** Los dos algoritmos cuentan en vez de decidir, para que los términos puedan ser negativos y cancelarse. Esa es la intuición en una frase, y es la misma para los dos.
- **La versión de Claude funciona con octoniones.** Una identidad de 1818 sobre sumas de ocho cuadrados convierte dos comprobaciones de igualdad cruzadas en términos que son baratos cada uno en una dirección, y una recursión multiplica el exponente por 11/12 en cada nivel hasta dejarlo tan pequeño como quieras.
- **La versión de OpenAI deforma e interpola.** Un polinomio que vale la cuenta en 0 y se separa en grupos independientes en $1, \dots, Q$, sostenido por matrices de intercambio y por un polinomio que imita $(-1)^j$ en una ventana bajo una campana de Gauss.
- **Ninguna consecuencia práctica.** El punto de cruce está más allá de $10^{10\,000}$ variables. Las consecuencias son para la teoría: cientos de cotas inferiores condicionales pierden su hipótesis, y una cota inferior de circuitos se ha movido gratis.
- **Dos laboratorios, la misma semana, la misma cota.** Diga lo que diga esto sobre el problema, dice algo sobre los modelos: la frontera de lo que pueden encontrar incluye ya un resultado al que uno de los mayores expertos del campo, en 2019, daba un 70 a 30 en contra.

---

*Fuentes: el [paper y la formalización en Lean](https://github.com/anthropics/formal-math/tree/main/eth) de Anthropic (A 2^o(n) Time Algorithm for 3-SAT, por Claude), y la [nota de alcance en Lean](https://github.com/openai/math/blob/main/lean/docs/378.md) y el [paper](https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/paper.pdf) de OpenAI (The Exponential Time Hypothesis is False).*
