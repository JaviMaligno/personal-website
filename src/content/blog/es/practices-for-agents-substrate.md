---
title: "El código malo no detiene a un agente. Le agota el presupuesto."
description: "Degradé cuatro repositorios de nueve formas semánticamente equivalentes y medí 750 corridas de agente. Las degradaciones no vuelven al agente incapaz de arreglar el fallo — lo vuelven más lento, y con un presupuesto de turnos finito eso acaba siendo lo mismo."
pubDate: 2026-09-08
tags: ["IA", "Agentes", "Evaluación"]
lang: es
translationKey: practices-for-agents-substrate
heroImage: "/blog/practices-for-agents-substrate.png"
repoUrl: "https://github.com/JaviMaligno/agent-code-practices"
---

Las buenas prácticas de software se justificaron para lectores humanos. Nombres que se entienden,
formato consistente, módulos con una responsabilidad, documentación que dice dónde vive cada cosa.
Hoy una fracción creciente de las lecturas de cualquier repositorio las hace un agente, y no he
encontrado una medición de cuáles de esas prácticas le sirven **a él** y cuáles solo nos servían
**a nosotros**.

Mi hipótesis, escrita antes de correr nada:

> Para un coding agent importa **más saber dónde mirar** —organización, distribución en ficheros,
> documentación— **que lo bien escrito que esté el fichero** una vez abierto.

Resultó estar equivocada, y la forma en que lo está es más útil que si hubiera acertado.

## El método: romper el código sin cambiar el programa

Coger un repositorio que funciona y degradarlo de maneras **semánticamente equivalentes** —el
programa hace exactamente lo mismo antes y después, verificado porque la suite del propio repo da un
resultado idéntico—. Así, cualquier diferencia en la tasa de éxito del agente es atribuible a
legibilidad o navegabilidad, y nunca a que la tarea se haya vuelto más difícil.

Nueve degradaciones en dos familias. **Familia A, cómo está escrito**: eliminar anotaciones de tipo
(A1), renombrar identificadores a opacos (A2), destruir el formato (A3), quitar comentarios y
docstrings (A4). **Familia B, dónde mirar**: romper la cohesión sin tocar el tamaño (B1), aplanar la
jerarquía a `m1.py`, `m2.py` (B2), borrar README y docstrings de módulo (B3), esconder la suite
(B4), concatenar módulos para variar el tamaño de fichero (B5).

Las tareas se **fabrican**, no se buscan: se inyecta un fallo de forma programática y solo cuenta si
hace fallar un conjunto concreto de tests y no otros. Estos fallos no existen en internet, así que
no hay contaminación, y la resolución es objetiva — sin ningún LLM evaluador.

**750 corridas medidas sobre cuatro repositorios**: un 2×2 (sin tocar, familia A, familia B, las dos)
en dos de ellos y dos tiers de modelo con tres pasadas, más cada una de las ocho prácticas quitada y
devuelta por separado, más una curva de tamaño de fichero, más una sonda TypeScript. Todo
[en el repo](https://github.com/JaviMaligno/agent-code-practices).

## La tabla principal

python-stdnum, tres pasadas por celda.

| Condición | Tier bajo | Mediana turnos | Tier alto | Mediana turnos |
|---|---|---|---|---|
| **T0** sin tocar | 14/18 — **78%** | 11 | 18/18 — **100%** | 6 |
| **T1** familia A | 15/17 — 88% | 10 | 18/18 — 100% | 6 |
| **T2** familia B | 12/15 — 80% | 12 | 14/14 — 100% | 18 |
| **T3** las dos | 8/15 — **53%** | 19 | 13/15 — **87%** | 15 |

Cada condición son seis tareas × tres pasadas = 18 corridas. El denominador baja a 15 en T2 y T3
porque allí tres corridas **no midieron nada**: el fallo inyectado no puso en rojo ningún test, así
que la celda no dice nada del agente y se excluye en vez de puntuarse como fracaso. Por qué pasa eso,
y por qué excluirlas no es hacerle un favor al agente, está [más
abajo](#tres-veces-que-una-transformación-rota-pareció-un-agente-que-fracasa).

Hay que leer las columnas de turnos, no solo los porcentajes. El hallazgo está ahí.

## Qué hacen de verdad las degradaciones

Ninguna familia daña sola: T1 (88%) y T2 (80%) están al nivel del 78% de la base. Las dos juntas la bajan al 53%. Eso es
una interacción, y es lo que habría reportado de haberme parado ahí.

Pero el mismo experimento sobre **pint** —código real, grande e interconectado en vez de validadores
pequeños y autocontenidos— dice algo que los porcentajes por sí solos esconden:

| | Sin tocar | Familia A |
|---|---|---|
| Resueltas | 8/12 | **2/12** |
| Mediana de turnos | 30 | **40 (el techo)** |
| Corridas que tocan el techo | 3/12 | **10/12** |

El agente no se vuelve incapaz con el código degradado. **Se queda sin turnos.** En pint bajo la
familia A, diez de doce corridas agotan el presupuesto de 40 turnos, y tres quedan registradas como
«lo arregló a medias» — un modo de fallo que no aparece ni una vez en el árbol intacto.

Puestos en fila los tres regímenes, el mecanismo es el mismo en todos:

Cada fila compara el árbol intacto con la peor condición de esa corrida: la mediana de turnos antes
y después, cuántas corridas tocaron el techo de 40 y qué hizo la resolución.

| Corrida | Mediana de turnos | Corridas en el techo | Resolución |
|---|---|---|---|
| python-stdnum, tier alto | 6 → 18 | 0 de 15 | 100% → 87% |
| python-stdnum, tier bajo | 11 → 19 | 0 de 15 | 78% → 53% |
| pint, tier bajo | 30 → **40** | **10 de 12** | 67% → 18% |

**El modelo capaz no absorbe el daño por ser más listo: lo absorbe porque empieza con margen.** Paga
el mismo peaje, triplicando sus turnos de 6 a 18, y puede permitírselo. pint parte de 30 sobre 40 y
el mismo peaje lo saca por el techo.

Así que las degradaciones no destruyen la capacidad del agente. Encarecen el trabajo, y con
presupuesto finito lo caro se vuelve imposible. Eso cambia la pregunta práctica: no *«¿puede el
agente trabajar en este codebase?»* sino *«¿cuánto margen le queda?»*.

## Qué práctica se paga: ninguna, por separado

Quitando cada una de las ocho prácticas por su cuenta, tres pasadas, 18 corridas por condición:

| Se quita | Resolución | Mediana turnos |
|---|---|---|
| Base | 78% | 11 |
| Anotaciones de tipo | 83% | 10 |
| Nombres legibles | 67% | 12 |
| Formato | 78% | 10 |
| Comentarios y docstrings | 72% | 10 |
| Cohesión | 72% | 10 |
| Jerarquía | 89% | 9 |
| README y docs de módulo | 83% | 14 |
| Tests visibles | 83% | 12 |

Todo cae entre el 67% y el 89% alrededor de una base del 78%, y todas las
medianas de turnos entre 9 y 14. **Ninguna práctica suelta hace un daño que estos
datos puedan separar del ruido.** Devuelve cualquiera de ellas al código
totalmente degradado y recupera casi todo —del 72% al 94% frente al 53% de T3—,
que es la otra cara de la interacción: no hay una práctica que cargue con el
efecto, es su ausencia conjunta.

Lo cuento así porque la primera versión de esta tabla decía otra cosa. Corrida una
vez en lugar de tres, daba que los nombres costaban 28 puntos y duplicaban los
turnos, y yo tenía un mecanismo redondo preparado: los nombres opacos encarecen
encontrar la función correcta. La evidencia era que A2 rompía una tarea que la
base resuelve siempre. Con tres pasadas esa celda sale 3 de 3 resuelta, en 10, 11
y 7 turnos. Era una corrida con mala suerte.

Que es lo que este mismo artículo dice dos secciones más abajo sobre que la
varianza es del orden de los efectos. Escribí esa frase y publiqué igualmente una
tabla de una pasada.

## Dónde no se puede medir nada, y por qué lo enseño

Cinco bloques de esta campaña son ininterpretables, y se publican con el resto:

- **El desglose del tier alto**: trece de sus dieciséis condiciones al 100% y las otras tres al 83%,
  mediana de 6 turnos, una pasada cada una. Con la baseline en el techo no hay hueco donde quepa una
  caída.
- **El tier alto en general**: 18/18 sin tocar nada.
- **Las tareas de dominio de pint**: 1/6 en la base. Esas dos las escribí a mano y me salieron
  demasiado caras — cinco de sus seis corridas base tocan el techo de turnos sin acabar.
- **Un tercer repositorio, sqlglot**: 0/3 en la base. Lo traje por un motivo concreto: es el único
  de los cuatro candidatos cuyos ficheros se pueden concatenar en cuatro tamaños de verdad
  distintos, que es lo que hace falta para buscar un umbral. Sus tareas resultaron estar fuera del
  alcance de este modelo, así que la curva que venía a aportar no se puede leer: no hay desde dónde
  caer.
- **La sonda TypeScript**: 1/12 en la base, también pegada al suelo. Se construyó para comprobar si el
  resultado sobre los tipos es un artefacto de que en Python sean opcionales; no puede responder a
  eso, y [lo que sí dejó claro](#lo-que-esto-no-contesta) es un hecho sobre la transformación, no
  sobre los agentes.

El primero merece detenerse. Mi plan original era correr el desglose en **un** tier, el que tuviera
la familia A y la familia B más separadas — que es el alto. Haber hecho solo eso habría producido
dieciséis celdas idénticas al 100% y ninguna información. Correr los dos es la única razón de que
haya un desglose que enseñar.

La curva de tamaño sí sobrevive en pint: 67% → 50% con ~500 líneas por fichero → 33% con ~2.000.
Monótona, y con tres puntos y seis corridas cada uno no se ve ningún umbral. El diseño quería
encontrar uno; lo que hay es una pendiente.

## La varianza que convierte en ficción los resultados de una pasada

Cuatro de 22 celdas medibles dieron respuestas distintas en tres pasadas idénticas:

```
sin tocar, genérica (un chequeo de None quitado)  no → OK → OK
familia A, la misma degradada                     no → OK → OK
familia A, dominio (rotación en checksum ISO)     no → no → OK
las dos,   genérica (una condición invertida)     OK → OK → no
```

Misma tarea, misma condición, mismo modelo, mismo enunciado. Una de esas celdas tardó 27 turnos en
fallar, 17 en resolverse y 40 en volver a resolverse.

La versión de una sola pasada de la tabla principal —que tuve, ese mismo día por la mañana— daba la
familia B al 100% y habría sostenido la conclusión contraria.

## Tres veces que una transformación rota pareció un agente que fracasa

Es el modo de fallo del que todo el diseño se defiende, y apareció tres veces, las tres produciendo
números que yo habría publicado.

**La primera vez tuve una tabla completa en la que ni un solo número hablaba de un agente.** Mi
runner inyectaba el fallo de cada tarea en el árbol ya degradado, donde ya no encajaba; dos
condiciones salieron vacías y una tercera salió como seis agentes que «rompieron otra cosa». Nada en
esa tabla tenía aspecto de estar roto. El arreglo fue invertir el orden —el fallo primero, la
degradación encima— y comprobar después, ejecutando el código, que el fallo había sobrevivido.

**La segunda es la razón de que algunas condiciones se puntúen sobre 15 y no sobre 18 en [la tabla
principal](#la-tabla-principal).** Qué tests
rompe un fallo no se puede leer del fichero de la tarea, porque las degradaciones mueven también los
tests. Así que cada celda construye dos árboles degradados, uno sano y otro con el fallo, y le
pregunta a la suite qué cambió. Para una de las tareas bajo la familia B la respuesta fue *nada*: su
único test era un doctest que vivía en la docstring de un módulo, y la familia B borra las docstrings
de módulo. El fallo seguía ahí; ya no quedaba ningún test que se diera cuenta. Puntuar esas tres como
fracasos habría movido T3 del 53% al 44% por culpa de un doctest que ya no estaba.

**Y durante un tiempo el resultado dependió de con qué Python se corriera el experimento.** pint usa
sintaxis que solo 3.12 parsea. Con 3.11 el transformador no podía leer un fichero y se lo saltaba en
silencio, renombrando una clase en todas partes menos donde se la referenciaba — el paquete moría al
importarse y una condición entera se leía como un agente que rompe cosas. Ahora transformar se
detiene y nombra los ficheros que no puede leer: un árbol a medio renombrar no es equivalente, y no
producirlo es la única salida honesta.

Dos de esas tres solo aparecieron al añadir el segundo repositorio.

## Lo que esto no contesta

**El techo de turnos es una decisión de diseño.** Cuarenta turnos es donde el presupuesto aprieta;
con cien, pint probablemente se parecería a python-stdnum. El hallazgo no es «el código degradado no
se puede arreglar», es «cuesta más, y los presupuestos son finitos» — lo cual vale para cualquier
agente real, pero las cifras concretas de aquí están atadas a ese techo.

**Los dos repositorios sobre los que corre el 2×2 son Python, y la sonda que debía arreglarlo no lo
arregló.** En Python los
tipos no los comprueba nadie en ejecución, así que A1 los mide como documentación; en un lenguaje que
sí los comprueba son además contrato. Construir la sonda TypeScript dejó una cosa que vale la pena
guardar: **quitar allí las anotaciones no es una transformación semánticamente equivalente** — bajo
`strict` el programa deja de compilar (`TS7006`), y el script de test de un repo suele ejecutar
también el compilador, así que las anotaciones son parte de lo que la suite verifica. Lo que sí
funciona es sustituir cada anotación por `any`: sigue compilando, se borra al emitir, y verificado
idéntico sobre los 4.968 tests de runtime de hono.

Después las celdas se corrieron, y el bloque se suma a las zonas muertas. Baseline 1/12 —pegada al
suelo—, así que su 5/12 con los tipos borrados dice que la baseline no discriminaba, no que borrar
tipos ayude. Una pasada anterior sobre esas mismas cuatro tareas había dado 2 de 4 y parecía
discriminar; esas dos tareas dan 0/3 y 1/3 con tres pasadas, con los mismos turnos. Así que
la pregunta para la que se construyó esta sonda sigue abierta, y la maquinaria para responderla está
[en el repo](https://github.com/JaviMaligno/agent-code-practices/tree/main/infra/ts).

**El estrato de dominio se apoya en dos tareas de un repositorio.** Las de python-stdnum aguantaron;
las de pint salieron demasiado difíciles para poder leerlas.

Prefiero publicar una tabla con sus zonas muertas señaladas que un titular que los datos no
sostienen. Las 750 corridas están
[en el repo](https://github.com/JaviMaligno/agent-code-practices/tree/main/results), incluidas las
que no midieron nada.

---

*Código y datos: [agent-code-practices](https://github.com/JaviMaligno/agent-code-practices). Esto
continúa la línea de [Coding Agents y trabajo en equipo](/es/blog/coding-agents-structure), que
preguntaba si la estructura le gana a la habilidad social en un equipo de agentes; este lo pregunta
un nivel más abajo, sobre la estructura del código mismo.*
