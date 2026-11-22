---
title: "La hipótesis de Riemann tiene una prueba que nadie ha leído. Su idea central cabe en una frase"
description: "Un matemático de Anthropic y Claude han publicado una prueba en Lean de la hipótesis de Riemann: 175.187 ficheros, aceptados en horas por verificadores independientes, sin versión legible para humanos. Lo que los titulares se saltan: qué se ha probado exactamente, qué resuelve y qué no una comprobación por máquina, por qué la idea central la reconocería Chebyshev y qué teoremas acaban de cambiar de estatus."
pubDate: 2026-11-24
tags: ["IA", "Matemáticas", "Agentes", "Investigación", "Anthropic"]
lang: es
translationKey: riemann-hypothesis-proof
heroImage: "/blog/riemann-hypothesis-proof.png"
linkedinImage: /blog/riemann-hypothesis-proof-prime-sum.png
---

El viernes 20 de noviembre, Levent Alpöge, un especialista en teoría de números que trabaja en Anthropic, colgó una [nota de cuatro páginas](https://alpo.ge/remark.pdf) en su web personal. El segundo párrafo empieza así: «Creo que he descubierto, trabajando con Claude, una prueba de la hipótesis de Riemann». La prueba no está en la nota. Está en una nota al pie: catorce enlaces a un archivo de código Lean, el lenguaje en el que un programa puede comprobar una demostración matemática paso a paso.

La hipótesis de Riemann es el problema abierto más conocido de las matemáticas. Tiene 167 años, es uno de los siete problemas del Milenio y dice, en una línea, que los números primos están repartidos de la forma más regular posible. Antes de que acabara ese viernes, gente sin ninguna relación con el autor había compilado el archivo y los verificadores lo habían aceptado.

La cobertura ha ido sobre la máquina que gana a los matemáticos y sobre una segunda prueba, hecha solo por humanos, que apareció esa misma tarde. Las dos historias son reales. Es la tercera vez desde septiembre que escribo uno de estos artículos, después de [Navier–Stokes](/es/blog/navier-stokes-blows-up) y de la [hipótesis del tiempo exponencial](/es/blog/exponential-time-hypothesis-falls) en octubre, y como entonces lo que más me interesa no cabe en un titular: qué se ha probado exactamente, qué significa que nadie lo haya leído, por qué la idea central se puede explicar en una pizarra, quién hizo qué y qué teoremas cambiaron de estatus de un día para otro.

<style>
.rh-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.rh-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.rh-fig img{display:block;width:100%;height:auto;margin:0;border:0;border-radius:.6rem}
.rh-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Qué se ha probado, exactamente

**El archivo demuestra cinco enunciados, y el primero es la hipótesis de Riemann palabra por palabra tal como la comunidad de Lean ya la tenía escrita.**

Los primos escasean de una forma regular: cerca de un número grande x, más o menos uno de cada log x números es primo. En 1859 Bernhard Riemann mostró que el detalle fino de ese patrón lo controla una sola función, la función zeta ζ(s), y en concreto los números complejos s en los que vale cero. Algunos de esos ceros no tienen interés (los enteros pares negativos). Todos los demás están en una banda vertical del plano complejo, entre parte real 0 y parte real 1. La hipótesis dice que están todos justo en el centro, sobre la recta de parte real 1/2.

<figure class="rh-fig">
<svg viewBox="0 0 600 330" role="img" aria-label="La banda crítica del plano complejo, entre parte real cero y parte real uno. Los diez primeros ceros no triviales de la función zeta de Riemann, a alturas entre 14,13 y 49,77, están todos sobre la recta central de parte real un medio. Se dibuja un cero hipotético fuera de la recta, en parte real 0,8, con su imagen especular en parte real 0,2: la hipótesis de Riemann dice que no existe ningún par así">
  <rect x="230" y="24" width="140" height="276" fill="rgba(255,255,255,0.04)"/>
  <line x1="230" y1="24" x2="230" y2="300" stroke="rgba(255,255,255,0.22)" stroke-width="1"/>
  <line x1="370" y1="24" x2="370" y2="300" stroke="rgba(255,255,255,0.22)" stroke-width="1"/>
  <line x1="300" y1="18" x2="300" y2="300" stroke="#2dd4bf" stroke-width="2"/>
  <line x1="150" y1="300" x2="450" y2="300" stroke="#64748b" stroke-width="1.5"/>
  <g font-size="10.5" fill="#94a3b8" text-anchor="middle">
    <text x="230" y="316">0</text>
    <text x="300" y="316" fill="#5eead4" font-weight="700">1/2</text>
    <text x="370" y="316">1</text>
    <text x="430" y="316">parte real de s</text>
  </g>
  <g fill="#2dd4bf">
    <circle cx="300" cy="226.5" r="4"/><circle cx="300" cy="190.7" r="4"/><circle cx="300" cy="169.9" r="4"/>
    <circle cx="300" cy="141.8" r="4"/><circle cx="300" cy="128.7" r="4"/><circle cx="300" cy="104.5" r="4"/>
    <circle cx="300" cy="87.2" r="4"/><circle cx="300" cy="74.7" r="4"/><circle cx="300" cy="50.4" r="4"/>
    <circle cx="300" cy="41.2" r="4"/>
  </g>
  <g font-size="9.5" fill="#94a3b8">
    <text x="310" y="230">14,13</text><text x="310" y="194">21,02</text><text x="310" y="173">25,01</text>
  </g>
  <g fill="none" stroke="#f59e0b" stroke-width="1.8" stroke-dasharray="3 2">
    <circle cx="342" cy="154" r="5"/><circle cx="258" cy="154" r="5"/>
  </g>
  <line x1="264" y1="154" x2="336" y2="154" stroke="#f59e0b" stroke-width="1" stroke-dasharray="2 3"/>
  <g font-size="10.5" fill="#e2e8f0">
    <text x="20" y="60" font-weight="700" fill="#5eead4">La recta crítica</text>
    <text x="20" y="76" fill="#94a3b8">Los diez primeros ceros,</text>
    <text x="20" y="90" fill="#94a3b8">calculados. Todos los que se</text>
    <text x="20" y="104" fill="#94a3b8">han calculado están en ella.</text>
    <text x="392" y="140" font-weight="700" fill="#fbbf24">Un cero fuera de la recta</text>
    <text x="392" y="156" fill="#94a3b8">vendría con su imagen</text>
    <text x="392" y="170" fill="#94a3b8">especular y haría los primos</text>
    <text x="392" y="184" fill="#94a3b8">menos regulares.</text>
    <text x="392" y="204" fill="#94a3b8">La hipótesis: no hay ninguno.</text>
  </g>
  <text x="218" y="215" font-size="9.5" fill="#64748b" text-anchor="middle" transform="rotate(-90 218 215)">altura (parte imaginaria de s)</text>
</svg>
<figcaption>Calcular ceros, por muchos que sean, no puede demostrar la hipótesis: una prueba tiene que excluir cualquier cero fuera de la recta, a cualquier altura.</figcaption>
</figure>

Mathlib, la biblioteca comunitaria de matemáticas formalizadas en Lean, ya contenía una definición llamada `RiemannHypothesis`. Nadie la había demostrado; estaba ahí para que otros resultados pudieran decir «suponiendo esto». El primer teorema del archivo es una prueba de esa definición exacta, y eso importa más de lo que parece: el enunciado lo escribieron otras personas antes de que existiera la prueba, así que la prueba no puede haber demostrado a escondidas algo más fácil con el mismo nombre.

Los otros cuatro enunciados van más lejos. Dicen lo mismo de toda una familia de funciones emparentadas, las funciones L de Dirichlet, que controlan los primos dentro de las progresiones aritméticas (los primos que acaban en 7, por ejemplo). Eso es la hipótesis generalizada de Riemann para funciones L de Dirichlet, para todo módulo y todo carácter.

El alcance tiene un borde y conviene saber dónde está. «GRH» se usa para varios enunciados de alcance creciente. Lo que los verificadores aceptaron se refiere solo a funciones L de Dirichlet. Las versiones para las funciones zeta de cuerpos de números y para funciones L automorfas en general no están entre los cinco teoremas. Alpöge escribe que espera que el método llegue más lejos «con más tiempo»; la [página de verificación de Andrew Sutherland](https://math.mit.edu/~drew/grh/), del MIT, dice sin rodeos que eso no se ha comprobado, porque no está.

## Una prueba que nadie ha leído

**La prueba existe solo como código, y fue una decisión.** Los números, tomados de las notas de quienes la comprobaron:

| | |
|---|---|
| Ficheros Lean | 175.187 |
| Líneas | 17,4 millones, sin un solo comentario |
| Teoremas y lemas | 818.755 |
| Tamaño del código | alrededor de 1 GB |
| El mismo argumento escrito para personas | más de 250.000 páginas, según el autor |
| Artículo legible | ninguno todavía |

Para comparar, la prueba de Navier–Stokes de OpenAI en septiembre eran 166 páginas. Alpöge sí generó el documento largo y decidió no publicarlo: habría sido, en sus palabras, una «parodia masiva e ilegible de *slop*», así que optó por «presentar solo Lean». Añade un detalle que deja claro qué tipo de texto es. Su Teorema 1 empieza observando que, como los números reales están ordenados, un número distinto de 1/2 es o mayor o menor que 1/2.

Así que la afirmación descansa sobre el verificador, y lo primero que hizo la comunidad fue atacar la comprobación por todos los flancos que se le ocurrieron. Sutherland tenía el archivo entero compilado a las 16:43 UTC del día del anuncio. En día y medio, su página y el [repositorio de la propia comunidad de Lean](https://github.com/leanprover-community/riemann-hypothesis) recogían lo siguiente.

<figure class="rh-fig">
<svg viewBox="0 0 600 372" role="img" aria-label="Qué se ha comprobado de la prueba en Lean de la hipótesis de Riemann y qué no. Comprobado: los 175.187 módulos compilan; el enunciado es la definición de Mathlib y coincide con un fichero de reto escrito de forma independiente; solo se usan los tres axiomas estándar de Lean; un segundo kernel escrito de forma independiente en Rust acepta la prueba completa; reconstrucciones independientes de otras personas la reproducen. Todavía no: una prueba escrita para humanos, y la revisión y comprensión por parte de matemáticos">
  <g>
    <rect x="20" y="14" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="62" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="110" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="158" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="206" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="268" width="560" height="42" rx="7" fill="rgba(245,158,11,0.07)" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="5 4"/>
    <rect x="20" y="316" width="560" height="42" rx="7" fill="rgba(245,158,11,0.07)" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="5 4"/>
  </g>
  <g font-size="12" font-weight="700" fill="#5eead4">
    <text x="36" y="32">¿Compila?</text>
    <text x="36" y="80">¿El enunciado dice lo que queremos decir?</text>
    <text x="36" y="128">¿Se supone algo?</text>
    <text x="36" y="176">¿Puede estar mal el propio verificador?</text>
    <text x="36" y="224">¿Depende de quién lo ejecute?</text>
  </g>
  <g font-size="12" font-weight="700" fill="#fbbf24">
    <text x="36" y="286">¿Hay una prueba que una persona pueda leer?</text>
    <text x="36" y="334">¿Entienden los matemáticos por qué es cierto?</text>
  </g>
  <g font-size="10.5" fill="#94a3b8">
    <text x="36" y="48">Los 175.187 módulos, cero errores, y cada uno repasado por el kernel de Lean.</text>
    <text x="36" y="96">Es la definición de Mathlib, y los cinco coinciden con un reto escrito aparte.</text>
    <text x="36" y="144">Solo los tres axiomas estándar de Lean. Ninguna hipótesis oculta sobre primos o ceros.</text>
    <text x="36" y="192">Un segundo kernel, escrito aparte en Rust, acepta la prueba completa. Y otros dos.</text>
    <text x="36" y="240">Reconstrucciones independientes; una, aislada, reproduce la exportación byte a byte.</text>
    <text x="36" y="302">Todavía no. El autor dice que piensa «escribirla como es debido».</text>
    <text x="36" y="350">Todavía no. Ningún revisor la ha leído, y los verificadores no explican nada.</text>
  </g>
  <g font-size="11" font-weight="700" text-anchor="end">
    <text x="566" y="32" fill="#5eead4">sí</text><text x="566" y="80" fill="#5eead4">sí</text><text x="566" y="128" fill="#5eead4">no</text>
    <text x="566" y="176" fill="#5eead4">cubierto</text><text x="566" y="224" fill="#5eead4">no</text>
    <text x="566" y="286" fill="#fbbf24">no</text><text x="566" y="334" fill="#fbbf24">no</text>
  </g>
</svg>
<figcaption>Todo lo que una máquina puede zanjar se zanjó en un día, más o menos. Las dos filas de abajo son las que requieren personas, y tiempo.</figcaption>
</figure>

Cada fila cierra una manera en la que el resultado podría estar mal. Una prueba puede compilar y demostrar otro enunciado, así que los enunciados se compararon con unos escritos por otra persona. Un verificador puede tener un fallo, así que la prueba se exportó y se pasó por kernels escritos de forma independiente, en otro lenguaje y por otra gente. Un archivo puede colar una suposición, así que se listaron los axiomas: los mismos tres que usa cualquier prueba en Lean. Hay una comprobación de Sutherland que me convence especialmente porque deja fuera la función zeta por completo. Combinado con una formalización independiente de una equivalencia clásica, el archivo da un enunciado sobre números enteros corrientes: para todo n mayor que 5040, la suma de los divisores de n es menor que e^γ · n · log log n. Es la desigualdad de Robin, que desde 1984 se sabe equivalente a la hipótesis de Riemann. Se puede probar con una calculadora de bolsillo, y ahora es un teorema sin hipótesis.

En esas páginas hay un detalle que dice algo del momento. Sutherland anota que sus comprobaciones se ejecutaron «con Claude Code». El [mapa público más detallado de la arquitectura de la prueba](https://github.com/nasqret/riemann-rev) declara que se hizo con un asistente de IA. La prueba se escribió con un modelo, y las herramientas para auditarla también. Lo que nadie delegó es el kernel: un programa pequeño, revisado por personas durante años, que no hace otra cosa que comprobar que cada paso se sigue de los anteriores.

Lo que todo esto deja abierto es la parte de abajo de la figura. Un kernel certifica que el teorema se sigue de los axiomas. No dice por qué. Hice la misma distinción con Navier–Stokes, donde los borradores del modelo hubo que [convertirlos en algo que una persona pueda leer](/es/blog/writing-a-research-paper-with-ai), pero allí existía un artículo. Aquí la distancia es total: el resultado es correcto, hasta donde una máquina puede decirlo, y la comprensión no ha empezado. Terence Tao, en una [nota breve](https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/) del mismo día, ordenó los anuncios de la jornada según lo «digeridos» que estaban y puso este el último: imagina que la digestión llevará tiempo, aunque en este caso al menos hay un autor humano con quien hablar para ayudar en la tarea.

## La idea, en una frase

**Un número entero divisible por muchos primos no puede ser pequeño.** Ese es el núcleo del argumento, y el resto es el trabajo de hacerlo lo bastante preciso.

Empiezo por qué lo que hace falta es una *cota superior*. La fórmula de Riemann dice que cada cero de ζ aporta una onda al recuento de primos, y que la parte real del cero fija el volumen de la onda. Si todos los ceros tienen parte real 1/2, todas las ondas tienen una amplitud proporcional a √y, donde y es hasta dónde se cuenta en la recta numérica. Un cero fuera de la recta, en parte real 0,8 por ejemplo, sería una onda que crece como y elevado a 0,8, y tarde o temprano taparía a las demás.

Esto se puede ver sin más que una lista de primos. Se toma un recuento ponderado de los primos hasta y, se le resta lo que uno espera y se divide por √y:

<figure class="rh-fig">
<img src="https://www.javieraguilar.ai/blog/riemann-hypothesis-proof-prime-sum.png" alt="El recuento ponderado de primos G(y), restado su valor esperado y dividido por la raíz cuadrada de y, calculado para y entre diez y diez millones. La curva oscila de forma irregular pero nunca supera 0,023 en valor absoluto, bien dentro de la banda de más o menos 0,0462 que predice la hipótesis de Riemann" aria-label="El recuento ponderado de primos G(y), restado su valor esperado y dividido por la raíz cuadrada de y, calculado para y entre diez y diez millones. La curva oscila de forma irregular pero nunca supera 0,023 en valor absoluto, bien dentro de la banda de más o menos 0,0462 que predice la hipótesis de Riemann" />
<figcaption>Calculado con los primos hasta diez millones: la curva nunca pasa de 0,023, la mitad del ancho de la banda que permite la hipótesis. Un dibujo así es un indicio, no una prueba; la prueba tiene que valer para todo y. <a href="https://github.com/JaviMaligno/personal-website/blob/main/scripts/figures/riemann-centred-prime-sum.py">Script</a>.</figcaption>
</figure>

La hipótesis es la afirmación de que esa curva se queda dentro de una banda para siempre. Y aquí está la primera idea de la prueba, una idea clásica afinada: no hacen falta los dos lados de la banda. Una onda sube igual que baja. Si se demuestra que el recuento se queda *por debajo* del techo durante tramos largos, no hay sitio para una onda más fuerte, porque una onda más fuerte habría asomado por encima. La prueba solo necesita esa cota por un lado, y solo en algunos intervalos largos, siempre que las combinaciones que intervienen tengan pesos positivos, para que las ondas de funciones distintas no puedan cancelarse entre sí. Esa pieza es un refinamiento de un teorema de Landau de 1905, y se ha comprobado por máquina por separado, aislada del resto.

Así que todo el problema se convierte en: ¿de dónde puede salir una cota superior para un recuento de primos?

De la divisibilidad. Tómese un entero positivo N. Cada potencia de primo que divide a N contribuye a su tamaño, de modo que si se suma log p sobre todas las potencias de primos que dividen a N, no se puede superar log N. Si se sabe que N es divisible por muchísimos primos, y su tamaño se puede medir por otro camino, se tiene una desigualdad con una suma sobre primos a un lado y una cantidad conocida al otro. Eso es una cota superior para un recuento de primos.

No es un truco nuevo. Es el más viejo. En 1850 Chebyshev lo aplicó al factorial: a! es divisible por cada primo p unas a/p + a/p² + … veces, y su tamaño lo da la fórmula de Stirling. De ahí salió la primera demostración de que el número de primos hasta x tiene el orden de magnitud de x/log x. El factorial no es lo bastante divisible para dar más. La prueba anunciada aplica el mismo principio a un número mucho más divisible. La cronología de Alpöge recoge el punto de partida, fechado el 9 de octubre: una cantidad construida con las derivadas de una función theta sobre una curva elíptica con simetría extra, que es divisible por cada primo adecuado p unas a/p + a/p³ + … veces. Se comporta como un factorial al que solo dividen ciertos primos, y su tamaño se puede calcular exactamente.

Eso, por sí solo, no da la raíz cuadrada. La da la segunda idea, que es la que Alpöge eligió como la única línea que haría que sus colegas matemáticos «se cayeran de la silla».

## De dónde sale la raíz cuadrada

**La prueba desciende de un argumento de 1969 para otro mundo, y la raíz cuadrada aparece al equilibrar dos costes.**

La hipótesis de Riemann tiene una gemela para curvas sobre cuerpos finitos, donde lo análogo a contar primos es contar los puntos de una curva. Esa gemela la demostró André Weil en los años cuarenta con maquinaria pesada, y luego otra vez, a partir de 1969, Serguéi Stepanov casi sin ninguna. La idea de Stepanov: construir un polinomio auxiliar que se anule en todos los puntos de la curva, y que no solo se anule sino que lo haga *con orden alto*, un cero de multiplicidad m en cada punto. Un polinomio no puede tener más ceros, contados con multiplicidad, que su grado. Así que el número de puntos por m es como mucho el grado, y eso es una cota superior para el número de puntos. Como en la sección anterior, con cotas superiores basta.

El obstáculo para copiar esto con los primos de toda la vida es la palabra «multiplicidad». Para que un polinomio se anule con orden m se deriva. En los números enteros no hay nada que derivar. Alpöge lo dice así: la multiplicidad «es difícil de encontrar sobre los enteros, y correspondería a algo así como derivar números enteros».

El sustituto es la divisibilidad, obtenida por iteración. La construcción que produce el número muy divisible se puede encadenar: se aplica una vez y se gana cierta cantidad de divisibilidad, se aplica m veces seguidas y se gana m veces. El nombre técnico de cada eslabón es *theta lift*, una forma clásica de trasladar una función con simetrías de un grupo a otro mayor; no voy a fingir que los detalles sean intuitivos. La contabilidad sí lo es.

<figure class="rh-fig">
<svg viewBox="0 0 600 262" role="img" aria-label="Un diccionario entre la prueba de Stepanov de 1969 de la hipótesis de Riemann para curvas sobre cuerpos finitos y la prueba anunciada sobre los enteros. Anularse con orden m pasa a ser la divisibilidad de una cadena de m theta lifts. Contar ceros frente al grado pasa a ser pesar divisibilidad frente a tamaño. Las extensiones finitas del cuerpo pasan a ser los pisos de una torre de cuerpos de números. En ambas, basta una cota superior">
  <g font-size="11.5" font-weight="700" text-anchor="middle">
    <text x="150" y="24" fill="#94a3b8">Stepanov, 1969</text>
    <text x="150" y="40" font-size="10" font-weight="400" fill="#64748b">puntos de una curva sobre un cuerpo finito</text>
    <text x="450" y="24" fill="#5eead4">La prueba anunciada, 2026</text>
    <text x="450" y="40" font-size="10" font-weight="400" fill="#64748b">números primos</text>
  </g>
  <defs>
    <marker id="rh-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <g>
    <rect x="20" y="54" width="260" height="40" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)"/>
    <rect x="20" y="104" width="260" height="40" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)"/>
    <rect x="20" y="154" width="260" height="40" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)"/>
    <rect x="20" y="204" width="260" height="40" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)"/>
    <rect x="320" y="54" width="260" height="40" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="320" y="104" width="260" height="40" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="320" y="154" width="260" height="40" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="320" y="204" width="260" height="40" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
  </g>
  <g stroke="#64748b" stroke-width="1.5" marker-end="url(#rh-ar)">
    <line x1="284" y1="74" x2="316" y2="74"/><line x1="284" y1="124" x2="316" y2="124"/>
    <line x1="284" y1="174" x2="316" y2="174"/><line x1="284" y1="224" x2="316" y2="224"/>
  </g>
  <g font-size="11" fill="#e2e8f0" text-anchor="middle">
    <text x="150" y="78">un polinomio que se anula con orden m</text>
    <text x="150" y="128">ceros contados frente al grado</text>
    <text x="150" y="178">las extensiones finitas del cuerpo</text>
    <text x="150" y="228">basta una cota superior</text>
    <text x="450" y="78">un número hecho divisible con m lifts</text>
    <text x="450" y="128">divisibilidad pesada frente a tamaño</text>
    <text x="450" y="178">los pisos de una torre de cuerpos</text>
    <text x="450" y="228">basta una cota superior, en tramos largos</text>
  </g>
</svg>
<figcaption>La nota llama al argumento «un descendiente del de Stepanov». Cada fila sustituye algo que necesita derivadas por algo que los enteros sí tienen.</figcaption>
</figure>

Cada eslabón de la cadena cuesta algo. Para acotar un recuento de primos de longitud x con una cadena de m eslabones, el error tiene dos partes. Una se reduce al alargar la cadena, como x/m: más multiplicidad, cota más fina. La otra crece con la cadena, como m: cada eslabón añade su propia pérdida. Lo mejor que se puede hacer es igualarlas.

<figure class="rh-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="El error de la cota en función del número m de lifts encadenados, para un recuento de primos de longitud x igual a diez mil. Un coste, x entre m, baja al alargar la cadena; el otro, m, sube. Su suma es mínima cuando m es la raíz cuadrada de x, aquí cien, y el mínimo es del orden de la raíz cuadrada de x">
  <line x1="70" y1="200" x2="566" y2="200" stroke="#64748b" stroke-width="1.5"/>
  <line x1="70" y1="200" x2="70" y2="24" stroke="#64748b" stroke-width="1.5"/>
  <path d="M90.8,33.3 L92.0,42.6 L93.3,50.9 L94.5,58.3 L97.0,71.2 L99.4,81.9 L101.8,91.0 L104.3,98.8 L108.0,108.6 L111.7,116.7 L116.5,125.4 L121.4,132.5 L127.6,139.7 L134.9,146.5 L143.5,152.8 L155.8,159.5 L168.0,164.6 L180.2,168.5 L192.5,171.7 L210.9,175.4 L229.2,178.2 L253.8,181.1 L284.4,183.8 L315.0,185.8 L351.8,187.7 L388.5,189.1 L437.5,190.6 L486.5,191.7 L523.2,192.3 L560.0,192.9" fill="none" stroke="#2dd4bf" stroke-width="1.6" stroke-dasharray="5 4"/>
  <path d="M82.3,197.2 L560,86.7" fill="none" stroke="#f59e0b" stroke-width="1.6" stroke-dasharray="5 4"/>
  <path d="M92.0,37.5 L93.3,45.5 L94.5,52.7 L97.0,65.0 L99.4,75.1 L101.8,83.7 L104.3,90.9 L108.0,99.8 L111.7,107.0 L116.5,114.7 L121.4,120.6 L127.6,126.4 L134.9,131.5 L143.5,135.8 L155.8,139.7 L168.0,141.9 L180.2,143.0 L192.5,143.3 L210.9,142.8 L229.2,141.4 L253.8,138.6 L284.4,134.2 L315.0,129.2 L351.8,122.5 L388.5,115.4 L437.5,105.6 L486.5,95.3 L523.2,87.5 L560.0,79.6" fill="none" stroke="#f8fafc" stroke-width="2.4"/>
  <line x1="192.5" y1="143.3" x2="192.5" y2="200" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3 3"/>
  <circle cx="192.5" cy="143.3" r="4.5" fill="#f8fafc"/>
  <g font-size="10.5" fill="#94a3b8">
    <text x="192.5" y="216" text-anchor="middle" fill="#e2e8f0" font-weight="700">m = √x</text>
    <text x="560" y="216" text-anchor="end">número de lifts encadenados, m</text>
    <text x="64" y="30" text-anchor="end">error</text>
    <text x="112" y="50" fill="#5eead4">x/m: lo que pierde una cadena corta</text>
    <text x="556" y="132" text-anchor="end" fill="#fbbf24">m: lo que cuesta cada eslabón</text>
    <text x="204" y="98" fill="#f8fafc" font-weight="700">error total ≈ 2√x en el mínimo</text>
    <text x="300" y="240" text-anchor="middle">dibujado para x = 10.000: los dos costes se cruzan en m = 100</text>
  </g>
</svg>
<figcaption>El exponente 1/2 de la hipótesis de Riemann, como el fondo de un compromiso. En la nota, la sugerencia de tomar una cadena de longitud √X se atribuye a Claude.</figcaption>
</figure>

x/m es igual a m cuando m vale √x, y el error es entonces del tamaño de √x. Esa es la raíz cuadrada de la hipótesis de Riemann: la amplitud que se le permite a cada onda. La línea de Alpöge, entera: para la suma de von Mangoldt de longitud X, la longitud de la cadena de theta lifts que sugirió Claude, dado que cada uno imita la multiplicidad, fue √X. «(Y sin embargo, ¿qué otra cosa podía ser?)»

Tengo que dejar claro qué estoy haciendo aquí. Esta es la arquitectura tal como la describen la nota y las guías públicas de lectura, que sí he leído; no he verificado diecisiete millones de líneas, ni lo ha hecho nadie a ojo. El dibujo puede ser correcto y la comprensión seguir siendo superficial. Ese es el estado de todo el mundo esta semana, autor incluido.

## Lo que hizo falta por debajo

**La idea sencilla se apoya en buena parte de la teoría de números moderna, y el archivo también la reconstruye.**

El camino de la idea al teorema, tal como lo exponen las guías de lectura:

<figure class="rh-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="La ruta de la prueba en siete pasos. Suministro aritmético: representaciones de Galois asociadas a formas automorfas, del programa de Langlands, y teoría de Iwasawa para acotar la pérdida de divisibilidad. La estimación: una cadena de unos raíz de x theta lifts, donde se pesa divisibilidad frente a tamaño, y un promedio sobre caracteres con pesos positivos. El motor analítico: una cota superior en tramos largos excluye ceros a la derecha de la recta crítica. El destino: la reflexión por la ecuación funcional da la hipótesis de Riemann y su generalización para funciones L de Dirichlet">
  <defs>
    <marker id="rh-a2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <g font-size="9.5" fill="#64748b" font-weight="700">
    <text x="20" y="20">SUMINISTRO ARITMÉTICO</text>
    <text x="216" y="20">LA ESTIMACIÓN</text>
    <text x="412" y="20">ANÁLISIS Y DESTINO</text>
  </g>
  <g>
    <rect x="20" y="32" width="170" height="74" rx="8" fill="rgba(245,158,11,0.07)" stroke="#f59e0b" stroke-width="1.5"/>
    <rect x="20" y="166" width="170" height="74" rx="8" fill="rgba(245,158,11,0.07)" stroke="#f59e0b" stroke-width="1.5"/>
    <rect x="216" y="32" width="170" height="74" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.25)" stroke-width="1.5"/>
    <rect x="216" y="166" width="170" height="74" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.25)" stroke-width="1.5"/>
    <rect x="412" y="32" width="168" height="74" rx="8" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="412" y="166" width="168" height="74" rx="8" fill="rgba(45,212,191,0.16)" stroke="#2dd4bf" stroke-width="2.2"/>
  </g>
  <g font-size="11" font-weight="700" fill="#e2e8f0" text-anchor="middle">
    <text x="105" y="54" fill="#fbbf24">Representaciones de Galois</text>
    <text x="105" y="188" fill="#fbbf24">Teoría de Iwasawa</text>
    <text x="301" y="54">Cadena de ~√x theta lifts</text>
    <text x="301" y="188">Promedio sobre caracteres</text>
    <text x="496" y="54" fill="#5eead4">Landau, localizado</text>
    <text x="496" y="188" fill="#5eead4">RH y GRH de Dirichlet</text>
  </g>
  <g font-size="9.5" fill="#94a3b8" text-anchor="middle">
    <text x="105" y="72">asociadas a formas</text>
    <text x="105" y="85">automorfas: el programa</text>
    <text x="105" y="98">de Langlands</text>
    <text x="105" y="206">la divisibilidad falla un</text>
    <text x="105" y="219">poco; esto acota cuánto,</text>
    <text x="105" y="232">en todo un tramo</text>
    <text x="301" y="72">un número muy divisible</text>
    <text x="301" y="85">no puede ser pequeño:</text>
    <text x="301" y="98">divisibilidad contra tamaño</text>
    <text x="301" y="206">pesos positivos aíslan la</text>
    <text x="301" y="219">función buscada; las demás</text>
    <text x="301" y="232">se descartan</text>
    <text x="496" y="72">una cota superior en tramos</text>
    <text x="496" y="85">largos no deja sitio a un</text>
    <text x="496" y="98">cero a la derecha de la recta</text>
    <text x="496" y="206">la ecuación funcional refleja</text>
    <text x="496" y="219">la izquierda en la derecha:</text>
    <text x="496" y="232">todos los ceros en la recta</text>
  </g>
  <g stroke="#64748b" stroke-width="1.5" fill="none" marker-end="url(#rh-a2)">
    <line x1="192" y1="69" x2="213" y2="69"/>
    <line x1="105" y1="108" x2="105" y2="163"/>
    <path d="M192,190 L203,190 L203,90 L213,90"/>
    <line x1="301" y1="108" x2="301" y2="163"/>
    <path d="M388,203 L399,203 L399,69 L409,69"/>
    <line x1="496" y1="108" x2="496" y2="163"/>
  </g>
  <text x="300" y="272" text-anchor="middle" font-size="10" fill="#94a3b8">Desde «promedio» en adelante, también comprobado por máquina de forma aislada, a partir de premisas explícitas.</text>
  <text x="300" y="288" text-anchor="middle" font-size="10" fill="#64748b">Reconstruido a partir de la guía pública de lectura; en las cajas ámbar vive la maquinaria pesada.</text>
</svg>
<figcaption>Una estimación difícil en el centro, análisis clásico a su derecha y, a su izquierda, la parte que hace que a los expertos se les abran los ojos.</figcaption>
</figure>

Dos piezas de ese dibujo merecen una frase cada una. La primera: la divisibilidad no es perfecta. En cada eslabón falla un poco, y el tamaño del fallo lo miden objetos de cohomología de Galois del tipo que aparece en una famosa conjetura sin demostrar, la de Vandiver. La prueba no necesita esa conjetura. Necesita una cota del fallo total a lo largo de todo un tramo, y la obtiene de la teoría de Iwasawa; Alpöge lo llama «un debilitamiento significativo de Vandiver» y añade en una nota al pie: «¡¡esto sigue siendo bastante fuerte!!».

La segunda: tanto los tamaños como esa cohomología los controlan representaciones de Galois asociadas a formas automorfas, los objetos centrales del programa de Langlands y el tema de algunos de los artículos más profundos de los últimos treinta años. Una prueba escrita citaría esos artículos. Una prueba en Lean no puede citar nada que Mathlib no contenga, así que el archivo lleva su propia construcción formal de todo ello. Chris Birkbeck, especialista en teoría de números de la Universidad de East Anglia, describió lo que estaba viendo en el chat de la comunidad, citado por [TechCrunch](https://techcrunch.com/2026/11/20/ai-claimed-a-solution-to-the-167-year-old-riemann-hypothesis-and-a-human-did-too/): el argumento usa de verdad la existencia de representaciones de Galois asociadas a representaciones automorfas cuspidales, polarizadas y algebraicas regulares de GL_n sobre cuerpos CM, junto con una lista de teoremas con nombre propio. La primera impresión de Tao fue que parece usar toda la potencia de los desarrollos modernos del programa de Langlands y de la geometría aritmética.

Esa es buena parte de la razón del tamaño del archivo. Es una prueba de la hipótesis de Riemann, y es también la formalización de una porción considerable de un área de investigación que nunca se había formalizado. La intuición del propio Alpöge «insiste en que se simplificará enormemente, probablemente de inmediato».

## Quién hizo qué

**Un matemático que había planeado toda su carrera alrededor de este problema marcó la dirección y, según cuenta él mismo, el modelo le dejó atrás al final.**

La nota es inusualmente franca sobre el reparto del trabajo. Alpöge escribe que el problema era su plan secreto desde sus años de estudiante y que dedicó años a aprender cada herramienta que algún día pudiera reconocer en él. En este intento, dice, llevó el trabajo a la línea de combinar dos ideas muy distintas presentes en un caso de juguete, lo guio hasta la situación análoga a ese caso, «y entonces Claude empezó a dejarme asombrado». El tramo decisivo usa formas automorfas en grupos grandes, donde él reconoce estar «fuera de mi elemento». Para esas partes avisa de que su propio resumen parafrasea un resumen hecho por la máquina que «puede no tener ningún sentido», y de que «el Lean debería bastar para aclararlo todo».

La cronología de la nota, que según él compiló Claude, tiene veinte entradas:

<figure class="rh-fig">
<svg viewBox="0 0 600 196" role="img" aria-label="Cronología de la prueba según la nota del autor y los registros de verificación. 6 de octubre de 2026: primera entrada, un determinante de tipo Stepanov. 9 de octubre: la cantidad muy divisible sobre una curva con multiplicación compleja. 15 de noviembre: ocho entradas en un día, entre ellas la cadena de theta lifts de longitud en torno a la raíz de X. 16 de noviembre: la hipótesis generalizada de Riemann. 19 de noviembre: salida a bolsa de Anthropic. 20 de noviembre: el anuncio, y la primera compilación independiente termina a las 16:43 UTC. 21 de noviembre: kernels y reconstrucciones independientes aceptan la prueba">
  <defs>
    <marker id="rh-a3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <line x1="24" y1="100" x2="578" y2="100" stroke="#64748b" stroke-width="2" marker-end="url(#rh-a3)"/>
  <g fill="#1a1a24" stroke="#94a3b8" stroke-width="2">
    <circle cx="56" cy="100" r="6"/><circle cx="140" cy="100" r="6"/>
    <circle cx="268" cy="100" r="6" stroke="#2dd4bf"/><circle cx="346" cy="100" r="6" stroke="#2dd4bf"/>
    <circle cx="420" cy="100" r="6"/><circle cx="486" cy="100" r="6" stroke="#f59e0b"/><circle cx="552" cy="100" r="6"/>
  </g>
  <circle cx="268" cy="100" r="3" fill="#2dd4bf"/><circle cx="346" cy="100" r="3" fill="#2dd4bf"/><circle cx="486" cy="100" r="3" fill="#f59e0b"/>
  <g text-anchor="middle" font-size="10.5" fill="#e2e8f0">
    <text x="56" y="62" font-weight="700">6 oct</text>
    <text x="56" y="76" fill="#94a3b8">primera entrada:</text>
    <text x="56" y="88" fill="#94a3b8">una idea de Stepanov</text>
    <text x="140" y="128" font-weight="700">9 oct</text>
    <text x="140" y="142" fill="#94a3b8">el número muy</text>
    <text x="140" y="154" fill="#94a3b8">divisible</text>
    <text x="268" y="62" font-weight="700" fill="#5eead4">15 nov</text>
    <text x="268" y="76" fill="#94a3b8">ocho entradas en un día:</text>
    <text x="268" y="88" fill="#94a3b8">la cadena, m ≈ √X</text>
    <text x="346" y="128" font-weight="700" fill="#5eead4">16 nov</text>
    <text x="346" y="142" fill="#94a3b8">«GRH.»</text>
    <text x="420" y="62" font-weight="700">19 nov</text>
    <text x="420" y="76" fill="#94a3b8">Anthropic sale</text>
    <text x="420" y="88" fill="#94a3b8">a bolsa</text>
    <text x="486" y="128" font-weight="700" fill="#fbbf24">20 nov</text>
    <text x="486" y="142" fill="#94a3b8">anuncio; primera compilación</text>
    <text x="486" y="154" fill="#94a3b8">externa, 16:43 UTC</text>
    <text x="552" y="62" font-weight="700">21 nov</text>
    <text x="552" y="76" fill="#94a3b8">otros kernels,</text>
    <text x="552" y="88" fill="#94a3b8">otras personas</text>
  </g>
  <text x="300" y="184" text-anchor="middle" font-size="10" fill="#64748b">Las fechas hasta el 16 de noviembre son de la cronología de la nota; el resto, de los registros de verificación y la prensa.</text>
</svg>
<figcaption>Seis semanas de la primera entrada a la última, con ocho de las veinte entradas fechadas en un solo domingo.</figcaption>
</figure>

Tres cosas que la nota no dice y que me gustaría saber. No nombra el modelo; Tao lo describe como «un modelo interno de IA», así que, como con OpenAI en septiembre, no es algo que se pueda ejecutar. No da cifras de cómputo, tokens ni agentes, cuando OpenAI las publicó todas para Navier–Stokes. Y no es un anuncio de Anthropic: es una nota en una web personal, y no he encontrado un comunicado de la empresa.

Sí habla del calendario. Anthropic salió a bolsa el jueves 19 de noviembre; la nota apareció a la mañana siguiente. Alpöge escribe que «el momento exacto es horrible», que la prueba cuajó «el domingo por la noche, tarde», que escribió a Dario Amodei, consejero delegado de Anthropic, para preguntar por la posibilidad de anunciarlo, que «había una restricción que respetar», y que es «claramente responsable de forma unilateral» de sentir que no podía vivir si esperaba más. De la lectura cínica dice solo que es falsa. No tengo forma de comprobar nada de eso, y lo recojo como su versión.

Dos piezas de contexto ayudan a situar la velocidad. En agosto, Anthropic [contó](https://www.anthropic.com/research/riemann-zeta) que una versión no publicada de Claude, a la que alguien de la plantilla que no es matemático pidió que intentara en serio la hipótesis, había subido la proporción demostrada de ceros sobre la recta crítica del 41,6 % al 67,2 %, y añadía que no esperaban que las técnicas usadas por Claude llevaran a demostrar la hipótesis de Riemann. Y en octubre, la publicación por parte de OpenAI de varios cientos de manuscritos escritos por máquina incluía la prueba de una [forma mucho más débil de la hipótesis](/es/blog/when-ai-chooses-the-questions): ningún cero con parte real mayor que 7/8. La nota de Alpöge agradece a la gente de OpenAI implicada en varios resultados matemáticos su gusto al elegir problemas, y dice que un argumento que publicaron lo reconoció de inmediato como «Stepanov sin multiplicidad». La publicación de un laboratorio rival fue una de sus pistas.

## La otra prueba, esa misma tarde

**Horas después, el presidente de la American Mathematical Society publicó una prueba humana del mismo teorema, y está en un estado muy distinto.**

Ravi Vakil, de Stanford, publicó un borrador de Alessandro Masullo que afirma demostrar la hipótesis generalizada de Riemann. Es «todo humano, sin IA», escribió; la esperanza era llevar a Masullo a Stanford un año para pulir la redacción, y ahora parecía mejor sacar el borrador actual. Brian Conrad, especialista en teoría de números de Stanford, llevaba meses dándole comentarios. La introducción del propio Masullo, tal como la [cita TechCrunch](https://techcrunch.com/2026/11/20/ai-claimed-a-solution-to-the-167-year-old-riemann-hypothesis-and-a-human-did-too/), dice que el trabajo le llevó doce años y lleva un mensaje para los matemáticos desanimados por el clima actual: seguimos aquí, estamos muy vivos, no nos vamos a ninguna parte.

El estatus no es comparable, y lo dicen quienes están más cerca. Conrad contó a [Scientific American](https://www.scientificamerican.com/article/dueling-claims-of-riemann-hypothesis-proofs-emerge/) que el artículo está en «revisión mayor» y que juzgar el método exige una versión más definitiva. Unas ocho horas después, [según The Decoder](https://the-decoder.com/hours-after-anthropic-claims-a-claude-proof-of-the-riemann-hypothesis-stanford-releases-an-all-human-competing-draft/), Vakil actualizó su entrada: varias personas le habían comunicado problemas en el borrador, encontrados con ayuda de modelos de IA, y él no afirmaba nada sobre la corrección de la estrategia.

Puestas una al lado de la otra dan el hecho más raro de la semana. Una prueba está comprobada por completo y no la entiende nadie. La otra se escribió para ser entendida y no la ha comprobado nadie. Hasta este año esas dos propiedades iban juntas, porque la única forma de comprobar una prueba era entenderla.

## Teoremas que cambiaron de estatus de un día para otro

**Un siglo de resultados empieza con las palabras «suponiendo la hipótesis de Riemann». En los que solo necesitan lo que se ha probado, esa cláusula ya se puede borrar.**

Como con [Navier–Stokes](/es/blog/navier-stokes-blows-up), un teorema condicional no cambia cuando se decide su hipótesis, pero su significado sí. Algunos ejemplos, ordenados según el lado del alcance en el que caen.

- **Ya incondicionales, si la prueba se sostiene.** La forma más fina del teorema de los números primos: para x ≥ 2657, el número de primos hasta x difiere de la estimación de Gauss li(x) en menos de √x · log x / 8π (Schoenfeld, 1976). La desigualdad de Robin sobre sumas de divisores, mencionada arriba. Los primos de cada progresión aritmética están repartidos con la misma regularidad que los primos en general. El test de primalidad de Miller, de 1976, que es rápido y determinista *siempre que* se cumpla la GRH para funciones L de Dirichlet, pasa a ser correcto sin más; en la práctica no cambia nada, porque desde 2002 existe un test rápido incondicional.
- **Teoremas que se habían demostrado dos veces.** Gauss conjeturó que cierto número asociado a los cuerpos cuadráticos, el número de clases, crece sin límite. Hecke lo demostró suponiendo la GRH. En 1934 Heilbronn lo demostró suponiendo que la GRH es *falsa*. Entre los dos, la conjetura quedó convertida en teorema sin que nadie supiera cuál de las dos pruebas era la válida. Ahora se sabe: la de Hecke.
- **Fuera del alcance.** Todo lo que necesita la hipótesis para funciones zeta de cuerpos de números más allá de los más sencillos, o para funciones L de curvas elípticas y formas automorfas. La conjetura de Artin sobre raíces primitivas, que Hooley demostró en 1967 bajo una hipótesis de ese tipo, sigue siendo condicional. Igual que muchos resultados efectivos de teoría algebraica de números.
- **Nada afectado.** La criptografía. Ningún sistema en uso depende de que la hipótesis de Riemann sea falsa, y saber que es cierta no factoriza ningún número más deprisa.

Lo que los matemáticos esperan que importe es el método más que la lista. Carlo Pagano, de la Universidad Concordia, dijo a [Scientific American](https://www.scientificamerican.com/article/anthropic-mathematician-claims-to-prove-riemann-hypothesis-most-famous-problem-in-all-of-math/) que le parece muy plausible que las ideas nuevas abran vías de pensamiento completamente nuevas en teoría de números. Eso depende de que las ideas se extraigan, lo que devuelve a las dos filas ámbar.

Sobre el millón de dólares, la misma respuesta que en septiembre. El Instituto Clay exige publicación en un medio que cumpla sus requisitos, una espera de dos años y aceptación general de la comunidad matemática. Un archivo que nadie ha leído no es, por ahora, ninguna de las tres cosas.

## El mismo día, el otro problema del Milenio

En septiembre acabé el artículo de Navier–Stokes con una escalera cuyo peldaño superior estaba vacío: las ecuaciones sin fuerza, la pregunta que casi todo el mundo tiene en la cabeza. La nota de Tao del 20 de noviembre lista, por encima del punto de Riemann y como mejor digeridos, otros dos anuncios en los que participan Alpöge y Tristan Buckmaster, de la NYU: una prueba legible, con Matei Coiculescu, de la explosión en tiempo finito para las ecuaciones de Euler tridimensionales *sin fuerza*, y una prueba de la explosión en tiempo finito para las ecuaciones de Navier–Stokes tridimensionales *sin fuerza*, ambas con formalización en Lean. De la segunda, Tao dice que la estrategia está clara a grandes rasgos y sigue uno de los caminos esperados, pero que hace falta más trabajo para tener una prueba escrita de forma profesional. No he leído ninguna de las dos y merecen su propio artículo. Lo anoto aquí porque ese peldaño superior tiene ya quien lo reclama, y es la pareja cuya ruta OpenAI terminó primero en septiembre.

## Con qué quedarse

- **Lo que se ha probado es la hipótesis de Riemann y su generalización a funciones L de Dirichlet**, con la redacción de Mathlib. Las versiones más amplias de la GRH no están en el archivo.
- **Correcto y entendido se han separado.** Todo lo que una máquina puede comprobar se comprobó en un día, más o menos, por gente independiente con herramientas independientes. Nada de lo que hace un revisor se ha hecho, y no existe una prueba legible. Ninguno de los dos hechos anula al otro.
- **La idea central es vieja y sencilla.** Un número divisible por muchos primos no puede ser pequeño; Chebyshev la usó en 1850. La raíz cuadrada sale de equilibrar la longitud de una cadena con el coste de cada eslabón.
- **La idea es sencilla; lo que la sostiene, no.** Descansa sobre una reconstrucción formal de una parte grande del programa de Langlands, que es adonde va la mayoría de los diecisiete millones de líneas.
- **Un humano eligió la ruta y el modelo la terminó.** Es la descripción del propio autor. También dice que todavía no sabe explicar el último tramo, y que entenderlo es el trabajo que empieza ahora.
- **El modelo no es uno que se pueda usar, y las cifras de la ejecución no son públicas.**

Para quien construye con agentes, lo que se traslada de todo esto no son las matemáticas. Es que el resultado se aceptó en un día porque existía un verificador pequeño, independiente y bien entendido, y porque el enunciado que había que comprobar lo había escrito otra persona de antemano. Donde tu trabajo tiene las dos cosas, puedes dejar que un modelo vaya muy por delante de ti. Donde no tiene ninguna, lo único que te queda son las 250.000 páginas.

---

*Fuentes: el [anuncio de Alpöge](https://alpo.ge/remark.pdf); los [ficheros de verificación de Andrew Sutherland](https://math.mit.edu/~drew/grh/) en el MIT; el [repositorio de verificación](https://github.com/leanprover-community/riemann-hypothesis) de la comunidad de Lean; el [mapa y guía independientes de la prueba](https://github.com/nasqret/riemann-rev); la [nota de Terence Tao](https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/); Scientific American sobre [el anuncio](https://www.scientificamerican.com/article/anthropic-mathematician-claims-to-prove-riemann-hypothesis-most-famous-problem-in-all-of-math/) y sobre [las dos pruebas](https://www.scientificamerican.com/article/dueling-claims-of-riemann-hypothesis-proofs-emerge/); la [crónica de TechCrunch](https://techcrunch.com/2026/11/20/ai-claimed-a-solution-to-the-167-year-old-riemann-hypothesis-and-a-human-did-too/); y la entrada de Anthropic de agosto sobre [Claude y los ceros de la función zeta](https://www.anthropic.com/research/riemann-zeta).*
