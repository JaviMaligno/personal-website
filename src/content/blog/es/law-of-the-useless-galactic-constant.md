---
title: "La ley de la constante galáctica inservible"
description: "Este otoño han caído la hipótesis del tiempo exponencial, Navier–Stokes en su versión forzada y la hipótesis de Riemann, y el mundo funciona exactamente igual. Propongo una ley para explicarlo: un problema abierto durante tiempo suficiente que afecta al mundo real se resuelve de forma coherente con lo observado, o su incoherencia vive donde no se puede observar."
pubDate: 2026-12-23
tags: ["Matemáticas", "Filosofía de la ciencia", "IA"]
lang: es
translationKey: law-of-the-useless-galactic-constant
heroImage: "/blog/law-of-the-useless-galactic-constant.png"
---

<style>
.gal-fig { margin: 2rem 0; padding: 1rem; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }
.gal-fig svg { width: 100%; height: auto; display: block; font-family: system-ui, -apple-system, sans-serif; }
.gal-fig figcaption { margin-top: 0.75rem; font-size: 0.9rem; color: #94a3b8; text-align: center; }
</style>

Este otoño se han resuelto, o se han anunciado resueltos con prueba verificada por máquina, tres problemas que llevaban décadas abiertos: la [hipótesis del tiempo exponencial](/es/blog/exponential-time-hypothesis-falls) es falsa, las [ecuaciones de Navier–Stokes forzadas explotan](/es/blog/navier-stokes-blows-up) en tiempo finito y la [hipótesis de Riemann es cierta](/es/blog/riemann-hypothesis-proof). He escrito un artículo sobre cada uno, y los tres acababan con una sección de "qué cambia" que decía, con distintas palabras, lo mismo: en la práctica, nada.

Lo pensé en serio a raíz de una conversación de WhatsApp. Un amigo escribió, medio en broma, que al final va a resultar que P = NP pero con una constante galáctica inservible. Le contesté esto:

> Podríamos establecer la ley de la constante galáctica inservible: cualquier problema abierto durante tiempo suficiente que afecte al mundo real o bien tiene una resolución coherente con lo observado en el mundo real, o la incoherencia se da en casos inobservables en el mundo real.

Lo escribí como chiste, pero creo que es verdad, y este artículo es el intento de darle forma. No es un teorema. Es una regularidad empírica sobre cómo se resuelven los problemas matemáticos que tocan el mundo, con una explicación de por qué debería cumplirse y una condición concreta que la rompería.

## Los casos de este otoño

**Los tres resultados contradicen lo que mucha gente creía, y ninguno contradice nada que alguien haya medido.**

**La hipótesis del tiempo exponencial.** ETH decía que 3-SAT, el problema de referencia de satisfacer un montón de restricciones lógicas a la vez, no se puede resolver en tiempo subexponencial. OpenAI y Anthropic publicaron en octubre algoritmos que sí lo hacen. Pero el de Anthropic solo mejora a la fuerza bruta cuando el número de variables supera $10^{10\,000}$. En el universo observable hay del orden de $10^{80}$ átomos. Esa es la constante galáctica de la broma, y el nombre no es mío: Dick Lipton y Ken Regan llaman [algoritmos galácticos](https://rjlipton.com/2010/10/23/galactic-algorithms/) a los que son maravillosos asintóticamente y no se usan nunca para calcular nada. Tu resolvedor SAT va igual de rápido que antes. Lo que se observaba, que nadie encontraba un algoritmo práctico, sigue siendo cierto. Lo que se creía, que no existía ninguno, era falso, pero solo en una región que no cabe en el universo.

**Navier–Stokes.** El resultado de septiembre construye un fluido que, empujado por una fuerza suave diseñada a medida, alcanza velocidad infinita en un punto en tiempo finito. No se te va a romper el desagüe porque el agua de repente vaya infinitamente rápido, ni se van a caer los aviones. El núcleo del vórtice se estrecha hasta quedar por debajo del recorrido libre medio de las moléculas del aire, unas decenas de nanómetros, mucho antes de que la velocidad diverja. A esa escala ya no hay fluido: hay moléculas, y las ecuaciones del continuo hace tiempo que dejaron de describir nada. Como escribí entonces, las ecuaciones no predicen un fluido infinitamente rápido; predicen su propio límite.

**La hipótesis de Riemann.** Aquí la resolución es la coherente: es cierta, que es lo que decían los cálculos numéricos de más de un siglo, con billones de ceros comprobados en la recta crítica. La criptografía no se entera. Ningún sistema desplegado dependía de que fuese falsa, y saber que es verdadera no factoriza ningún número más rápido.

## Un caso antiguo: el avión diseñado con Lebesgue

**La ley no es de este otoño; los matemáticos llevan tiempo bromeando con ella.** Richard Hamming, el de los códigos de Hamming, preguntó una vez si alguien creía que la diferencia entre la integral de Lebesgue y la de Riemann podía tener significado físico, y si que un avión volase o no podía depender de esa diferencia. "Si alguien lo afirmase", añadía, "no me gustaría volar en ese avión".

La pregunta tiene respuesta, y Andrew Lewis, de Queen's University, la contestó con un artículo que recuerdo de la carrera y cuyo título lo dice todo: [*Should we fly in the Lebesgue-designed airplane?*](https://mast.queensu.ca/~andrew/notes/abstracts/2007c.html) Lewis defiende la integral de Lebesgue, pero su defensa no es que el avión vuele distinto. Las dos integrales dan lo mismo en toda función que una medida física pueda producir; donde difieren es en funciones tan patológicas que ningún sensor las vería. La ventaja de Lebesgue es otra: hace que los espacios de funciones tengan las propiedades que necesitas para demostrar que existen las soluciones que luego calculas. Es decir, la diferencia importa a los teoremas y no a los aviones, que es exactamente lo que dice la ley.

<figure class="gal-fig">
<svg viewBox="0 0 600 330" role="img" aria-label="Diagrama de la ley: un problema abierto durante tiempo suficiente que toca el mundo real se resuelve por una de dos ramas. Coherente con lo observado: la hipótesis de Riemann y Lebesgue frente a Riemann. Incoherente solo donde no se puede observar: la hipótesis del tiempo exponencial, que solo mejora a la fuerza bruta por encima de 10 elevado a 10.000 variables, y Navier–Stokes forzado, cuya explosión ocurre por debajo del recorrido libre medio del aire. Falta un tercer caso: una resolución que contradiga algo medible.">
  <rect x="150" y="14" width="300" height="50" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.25)" stroke-width="1.5"/>
  <text x="300" y="35" text-anchor="middle" font-size="12.5" font-weight="700" fill="#f8fafc">Problema abierto durante tiempo suficiente</text>
  <text x="300" y="52" text-anchor="middle" font-size="11" fill="#94a3b8">que afecta al mundo real</text>
  <path d="M300 64 L300 82 L155 82 L155 100" fill="none" stroke="#64748b" stroke-width="1.5"/>
  <path d="M300 82 L445 82 L445 100" fill="none" stroke="#64748b" stroke-width="1.5"/>
  <rect x="20" y="100" width="270" height="150" rx="8" fill="rgba(45,212,191,0.08)" stroke="#2dd4bf" stroke-width="2"/>
  <text x="155" y="122" text-anchor="middle" font-size="12.5" font-weight="700" fill="#5eead4">Resolución coherente con lo observado</text>
  <text x="38" y="152" font-size="11.5" font-weight="700" fill="#e2e8f0">Hipótesis de Riemann</text>
  <text x="38" y="168" font-size="10.5" fill="#94a3b8">cierta, como decían los cálculos;</text>
  <text x="38" y="182" font-size="10.5" fill="#94a3b8">la criptografía, intacta</text>
  <text x="38" y="208" font-size="11.5" font-weight="700" fill="#e2e8f0">Lebesgue frente a Riemann</text>
  <text x="38" y="224" font-size="10.5" fill="#94a3b8">misma integral en toda función</text>
  <text x="38" y="238" font-size="10.5" fill="#94a3b8">que pueda salir de una medida</text>
  <rect x="310" y="100" width="270" height="150" rx="8" fill="rgba(245,158,11,0.08)" stroke="#f59e0b" stroke-width="2"/>
  <text x="445" y="122" text-anchor="middle" font-size="12.5" font-weight="700" fill="#fbbf24">Incoherente solo donde no se ve</text>
  <text x="328" y="152" font-size="11.5" font-weight="700" fill="#e2e8f0">Tiempo exponencial (ETH)</text>
  <text x="328" y="168" font-size="10.5" fill="#94a3b8">gana a la fuerza bruta si n &gt; 10^10.000;</text>
  <text x="328" y="182" font-size="10.5" fill="#94a3b8">el universo tiene ~10^80 átomos</text>
  <text x="328" y="208" font-size="11.5" font-weight="700" fill="#e2e8f0">Navier–Stokes forzado</text>
  <text x="328" y="224" font-size="10.5" fill="#94a3b8">explota por debajo del recorrido libre</text>
  <text x="328" y="238" font-size="10.5" fill="#94a3b8">medio del aire, donde no hay fluido</text>
  <rect x="150" y="270" width="300" height="46" rx="8" fill="none" stroke="rgba(255,255,255,0.25)" stroke-width="1.5" stroke-dasharray="5 4"/>
  <text x="300" y="290" text-anchor="middle" font-size="11.5" font-weight="700" fill="#94a3b8">Vacío: una resolución que contradiga</text>
  <text x="300" y="306" text-anchor="middle" font-size="11.5" font-weight="700" fill="#94a3b8">algo que se pueda medir</text>
</svg>
<figcaption>Las dos ramas que permite la ley, con los casos de este otoño y uno antiguo. La casilla vacía es la que la refutaría.</figcaption>
</figure>

## La palabra clave: tiempo suficiente

**Sin "tiempo suficiente", la ley sería o trivial o exagerada, y conviene ver por qué.**

Si quito la condición y la aplico a un problema recién planteado, la segunda rama se vuelve trivial. Cualquier afirmación nueva que no se ha contrastado con la realidad está, obviamente, en lo no observado. Decir que su incoherencia "se da en casos no observados" no dice nada: todavía no se ha observado casi nada.

Y si en lugar de "no observado" digo "inobservable", la ley sin tiempo se vuelve exagerada. No puedo afirmar que algo es imposible de observar solo porque aún no lo ha mirado nadie.

El tiempo es lo que convierte una cosa en la otra. Un problema que lleva décadas abierto y que toca el mundo real ha pasado décadas siendo puesto a prueba, sin que nadie lo pretendiera: millones de ingenieros simulando fluidos, décadas de resolvedores SAT en producción, billones de ceros de la función zeta calculados. Si hubiera una discrepancia en la región que se puede mirar, con tanta gente mirando, ya habría aparecido. Con tiempo suficiente, lo que queda sin observar deja de ser "lo que todavía no hemos mirado" y pasa a ser, con bastante seguridad, "lo que no se puede mirar".

## Por qué debería cumplirse

**La ley es casi un efecto de selección: el mundo ya ha hecho el experimento en toda la región accesible.**

Una resolución matemática no puede contradecir datos que ya existen, porque los datos los produjo el mundo, y el mundo es consistente consigo mismo. Si un problema se resuelve después de tanto tiempo, solo puede discrepar de lo que creíamos en los sitios donde nadie había podido comprobarlo. Y esos sitios, tras décadas de comprobaciones, son los extremos: tamaños mayores que el universo, escalas menores que una molécula, funciones que ningún instrumento produce.

La ETH lo ilustra bien. Que nadie encontrase en 27 años un algoritmo práctico para 3-SAT era una observación sobre el mundo, hecha por miles de personas con incentivos para encontrarlo. Cuando la hipótesis cayó, el algoritmo que la tumbó tenía que respetar esa observación, y la respetó de la única forma posible: siendo inútil en la práctica.

## Qué no dice la ley

**No dice que las matemáticas no importen; dice que una resolución no cambia lo que ya se había medido.** En los tres artículos, la sección de "qué cambia" no estaba vacía. Estanterías enteras de teoremas cambiaron de estatus: lo que se había probado "suponiendo ETH" perdió su hipótesis, lo que empezaba con "suponiendo la hipótesis de Riemann" la ganó, y el estudio de qué ocurre después de una singularidad pasó a tener un objeto concreto. Esos cambios ocurren dentro de las matemáticas, que es donde viven los problemas.

**Y las matemáticas no son solo resultados, ni solo lo que le dan al mundo real.** En el [artículo sobre Riemann](/es/blog/riemann-hypothesis-proof), en la sección «Las matemáticas han muerto», defendía que la disciplina está más viva que nunca. Esta ley llega a lo mismo por otro lado. Si demostrar la conjetura más famosa de la teoría de números no cambia nada fuera de ella, el valor de demostrarla nunca estuvo ahí fuera. Está en entender por qué los primos se reparten como se reparten, en las conexiones entre áreas que la prueba obliga a hacer y en las preguntas que deja abiertas. La utilidad llega a veces, a menudo décadas después y por caminos que nadie planeó: G. H. Hardy presumía en 1940 de que la teoría de números no servía para nada, y hoy sostiene la criptografía de internet. Pero medir las matemáticas por lo que cambian en el mundo es medirlas con la vara equivocada, y la ley explica por qué esa vara marca casi siempre cero justo cuando cae un gran problema.

**Tampoco prohíbe los inventos.** La ley habla de lo que una resolución dice sobre observaciones pasadas, no de las capacidades nuevas que pueda traer. Un algoritmo práctico para factorizar enteros grandes cambiaría el mundo de verdad. Pero fíjate en lo que la ley predice para ese caso: la factorización es un problema abierto desde hace mucho y del que depende medio internet, y décadas de criptoanalistas no han encontrado un algoritmo clásico rápido. Si algún día se demuestra que la factorización es fácil, mi apuesta, según la ley, es que lo será con una constante galáctica. El algoritmo de Shor no es un contraejemplo: corre en otra máquina, un ordenador cuántico, y la pregunta de si se puede construir uno grande es justo de las que todavía están en lo no observado.

**Y se puede refutar.** Basta con un problema abierto durante décadas, con consecuencias en el mundo real, cuya resolución contradiga algo que se pueda medir: la casilla vacía de la figura. Un algoritmo práctico para un problema que llevaba treinta años resistiéndose a los profesionales, o un fluido real que se comporte como la singularidad dice. No conozco ninguno.

## Una ley abierta

**No tengo prisa en cerrarla, porque los casos siguen llegando.** El mismo día que la prueba de Riemann, Terence Tao recogía el anuncio de una explosión en tiempo finito para Navier–Stokes *sin* fuerza externa, el caso que la mayoría de la gente tiene en mente cuando habla del problema. Todavía no lo he leído. Si se confirma, es la siguiente prueba para la ley, y la predicción es concreta: la singularidad volverá a ocurrir por debajo de la escala en la que un fluido es un fluido.

Seguiré añadiendo casos a este artículo a medida que caigan problemas. Si conoces uno que encaje en la casilla vacía, me interesa mucho más que cualquiera de los que confirman la ley.

## Qué me llevo

- **Los problemas abiertos que tocan el mundo se resuelven sin contradecir el mundo.** O la resolución coincide con lo observado (Riemann), o discrepa solo donde no se puede mirar (ETH, Navier–Stokes forzado).
- **"Tiempo suficiente" es lo que da contenido a la ley.** Sin él, "no observado" es trivial e "inobservable" es exagerado; con décadas de pruebas involuntarias, uno se convierte en el otro.
- **Lo que cambia, cambia dentro de las matemáticas**: el estatus de los teoremas condicionales, los métodos, las preguntas nuevas. Y su valor nunca se midió por lo que le dan al mundo real.
- **La ley hace predicciones y se puede refutar.** Una factorización fácil vendría con constante galáctica; la explosión de Navier–Stokes sin fuerza, si se confirma, viviría por debajo de la escala molecular.

---

*Fuentes: mis artículos sobre [la hipótesis del tiempo exponencial](/es/blog/exponential-time-hypothesis-falls), [Navier–Stokes](/es/blog/navier-stokes-blows-up) y [la hipótesis de Riemann](/es/blog/riemann-hypothesis-proof), con sus fuentes primarias; Dick Lipton sobre [algoritmos galácticos](https://rjlipton.com/2010/10/23/galactic-algorithms/); Andrew Lewis, [*Should we fly in the Lebesgue-designed airplane?*](https://mast.queensu.ca/~andrew/notes/abstracts/2007c.html); y la [nota de Terence Tao del 20 de noviembre](https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/).*
