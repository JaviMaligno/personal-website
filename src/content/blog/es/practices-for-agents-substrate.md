---
title: "El código malo no daña a un agente. Hasta que el repositorio es grande."
description: "Degradé cuatro repositorios de nueve formas semánticamente equivalentes y medí 2.371 corridas de agente. En código pequeño no pasa nada medible. En código grande e interconectado, degradar cómo está escrito lo tumba: cero de veinticinco."
pubDate: 2026-08-25
tags: ["IA", "Agentes", "Evaluación"]
lang: es
translationKey: practices-for-agents-substrate
heroImage: "/blog/practices-for-agents-substrate.png"
repoUrl: "https://github.com/JaviMaligno/agent-code-practices"
---

Las buenas prácticas de software se justificaron para lectores humanos. Nombres que se entienden,
formato consistente, módulos con una responsabilidad, documentación que dice dónde vive cada cosa.
Hoy una parte creciente de las lecturas de cualquier repositorio las hace un agente, y no he
encontrado una medición de cuáles de esas prácticas le sirven **a él** y cuáles solo nos servían
**a nosotros**.

Mi hipótesis, escrita antes de correr nada, salía de cómo funciona un modelo de lenguaje:

> Un LLM es un procesador de texto excelente. Lo que no tiene es el repositorio en la cabeza. Así
> que debería importarle **más saber dónde mirar** —organización, distribución en ficheros,
> documentación— **que lo bien escrito que esté el fichero** una vez abierto.

El razonamiento parecía sólido y el resultado lo invierte: lo único que produce daño medible es
**cómo está escrito el texto que ya tiene delante**. Saber dónde mirar lo resuelve por su cuenta,
con las herramientas de búsqueda que cualquier agente lleva encima.

## El método: romper el código sin cambiar el programa

Coger un repositorio que funciona y degradarlo de maneras **semánticamente equivalentes** —el
programa hace exactamente lo mismo antes y después, verificado porque la suite del propio repo da un
resultado idéntico—. Así, cualquier diferencia en la tasa de éxito es atribuible a legibilidad o
navegabilidad, y nunca a que la tarea se haya vuelto más difícil.

Nueve degradaciones en dos familias. **Cómo está escrito**: eliminar anotaciones de tipo, renombrar
identificadores a opacos, destruir el formato, quitar comentarios y docstrings. **Dónde mirar**:
romper la cohesión sin tocar el tamaño, aplanar la jerarquía a `m1.py`, `m2.py`, borrar README y
docstrings de módulo, esconder la suite de tests, concatenar módulos para variar el tamaño de
fichero.

Las tareas se **fabrican**, no se buscan: se inyecta un fallo de forma programática y solo cuenta si
hace fallar un conjunto concreto de tests y no otros. Estos fallos no existen en internet, así que
no hay contaminación, y la resolución es objetiva — sin ningún LLM evaluador.

Y una condición que la primera versión de este experimento no tenía: **una tarea solo entra si el
árbol intacto la resuelve con margen**. Si el código limpio ya agota el presupuesto de turnos, no
queda sitio donde una degradación pueda notarse, y la celda saldrá a cero pase lo que pase.

**2.371 corridas medidas sobre cuatro repositorios**, con diez o quince pasadas por celda.
Todo [en el repo](https://github.com/JaviMaligno/agent-code-practices).

## Dónde no pasa nada

python-stdnum: validadores de números fiscales, ficheros pequeños y autocontenidos.

| Condición | Resuelve | IC 95% | Turnos | Techo antes→después | ¿Se distingue de la base? |
|---|---|---|---|---|---|
| sin tocar (base) | 49/59 — 83% | [72%, 91%] | 10 | 2 | — |
| cómo está escritoᵃ | 42/56 — 75% | [62%, 84%] | 13 | 2→4 | n.s. (≥20% sería visible) |
| dónde mirarᵃ | 46/58 — 79% | [67%, 88%] | 10 | 2→5 | n.s. (≥20% sería visible) |
| las dos cosasᵃ | 48/59 — 81% | [70%, 89%] | 11 | 2→5 | n.s. (≥19% sería visible) |

Las condiciones con la misma marca (ᵃ) **no se distinguen entre sí**, solo de la base.

Nada se separa de la base. Ni siquiera degradarlo todo a la vez. Y la última columna dice lo que
importa para leer esta tabla: con sesenta celdas por condición se habrían visto caídas de veinte
puntos, así que lo que se afirma no es «da igual», es «si hay un efecto, es menor que eso».

Con el modelo capaz pasa lo mismo por otra razón:

| Condición | Resuelve | IC 95% | Turnos | Techo antes→después | ¿Se distingue de la base? |
|---|---|---|---|---|---|
| sin tocar (base) | 59/60 — 98% | [91%, 100%] | 6 | 1 | — |
| cómo está escritoᵃ | 58/60 — 97% | [89%, 99%] | 6 | 1→2 | n.s. (≥7% sería visible) |
| dónde mirarᵃ | 58/60 — 97% | [89%, 99%] | 6 | 1→1 | n.s. (≥7% sería visible) |
| las dos cosasᵃ | 56/60 — 93% | [84%, 97%] | 6 | 1→2 | n.s. (≥7% sería visible) |

Las condiciones con la misma marca (ᵃ) **no se distinguen entre sí**, solo de la base.

Aquí la base resuelve el 98%. No hay hueco del que caer.

## Dónde sí

pint: unidades físicas, código grande e interconectado donde arreglar algo obliga a entender varias
piezas a la vez.

| Condición | Resuelve | IC 95% | Turnos | Techo antes→después | ¿Se distingue de la base? |
|---|---|---|---|---|---|
| sin tocar (base) | 19/35 — 54% | [38%, 70%] | 30 | 12 | — |
| cómo está escritoᵃ | 7/26 — 27% | [14%, 46%] | 40 | 12→14 | **p=0.040** |
| dónde mirarᵃ | 11/30 — 37% | [22%, 54%] | 38 | 12→15 | n.s. (≥36% sería visible) |
| las dos cosas | 0/25 — 0% | [0%, 13%] | 40 | 12→18 | **p=0.000** |

Las condiciones con la misma marca (ᵃ) **no se distinguen entre sí**, solo de la base.

**Cero de veinticinco.** Degradar las dos familias a la vez no baja la tasa: la anula. Y degradar
solo *cómo está escrito* la reduce a la mitad, con la mediana de turnos clavada en el techo.

Esa es la respuesta a la hipótesis, y es la contraria a la que yo había escrito. Esconder *dónde
mirar* no produce un efecto que estos datos distingan del ruido. Ensuciar el texto sí.

La explicación que me parece más plausible tiene que ver justamente con que el agente es un
procesador de texto: **encontrar el fichero es un problema que ya tiene resuelto** —busca, lista,
abre— y aplanar la jerarquía o borrar el README le quita una ayuda que no estaba usando. Leer código
ilegible, en cambio, no lo puede delegar en ninguna herramienta: lo paga entero, línea a línea, y en
un repositorio donde hay que leer mucho eso se acumula hasta agotar el presupuesto.

## Se paga en turnos antes que en fallos

Las tres corridas puestas en fila, comparando el árbol intacto con su peor condición:

| Corrida | Base | Peor condición | Turnos | Corridas en el techo |
|---|---|---|---|---|
| python-stdnum, tier alto | 98% | 93% | 6 → 6 | 1/60 → 2/60 |
| python-stdnum, tier bajo | 83% | 81% | 10 → 11 | 2/59 → 5/59 |
| pint | 54% | 0% | 30 → 40 | 12/35 → 18/25 |

El modelo capaz no absorbe el daño por ser más listo: **empieza con margen**. Resuelve en 6 turnos
de 40, y aunque la degradación le costara el triple seguiría sobrándole presupuesto. pint parte de
30 sobre 40, y cualquier encarecimiento lo saca por el techo.

Eso reformula la pregunta práctica. No es *«¿puede el agente trabajar en este código?»* sino
*«¿cuánto margen le queda?»*. Un repositorio pequeño con un modelo bueno tolera casi cualquier cosa.
Uno grande con un modelo justo no tolera nada.

## Qué práctica se paga: la respuesta está en devolverlas, no en quitarlas

Quitando cada práctica por separado del código limpio, y devolviéndola por separado al código
totalmente degradado. Sesenta celdas por condición:

| Práctica | Se quita del código limpio | Se devuelve al código destruido |
|---|---|---|
| *(base: 49/59 — 83%)* | | |
| anotaciones de tipo | 81% n.s. | 80% n.s. |
| nombres legibles | 81% n.s. | 97% **(p=0.016)** |
| formato | 85% n.s. | 80% n.s. |
| comentarios y docstrings | 87% n.s. | 85% n.s. |
| cohesión | 86% n.s. | 78% n.s. |
| jerarquía | 84% n.s. | 82% n.s. |
| README y docs | 85% n.s. | 86% n.s. |
| tests visibles | 71% n.s. | 86% n.s. |

Quitar cualquier práctica **por separado** no hace nada: las ocho caen dentro del intervalo de la
base. Pero devolver los **nombres legibles** a código por lo demás destruido recupera el 97%, y eso
sí se distingue —de la base y de devolver casi cualquier otra cosa (p=0,002 frente a cohesión,
0,004 frente a formato, 0,007 frente a tipos; tres sobreviven a corrección de Bonferroni)—.

La asimetría es el hallazgo: **los nombres no son necesarios cuando el resto del contexto está
intacto, pero son suficientes cuando no queda nada más**. Con el código formateado, comentado y
organizado, da igual que las funciones se llamen `f1` y `f2`; hay de dónde deducir. Cuando se ha
borrado todo lo demás, los identificadores son el único sitio donde sobrevive la intención del
autor.

Es también una corrección a mí mismo. Una versión anterior de esta sección, con una sola pasada por
celda, decía que quitar los nombres costaba 28 puntos, y tenía preparado un mecanismo redondo para
explicarlo. Con tres pasadas eso desapareció, y con diez resulta que el efecto real está en el otro
lado del experimento.

## El tamaño de fichero: sin efecto visible

| Tamaño de fichero | Resuelve | ¿Se distingue? |
|---|---|---|
| original | 19/35 — 54% | — |
| ~500 líneas | 19/31 — 61% | n.s. (p=0.62) |
| ~2.000 líneas | 13/30 — 43% | n.s. (p=0.46) |

Concatenar los módulos de pint hasta ~500 y ~2.000 líneas por fichero no cambia nada detectable. El
diseño buscaba un umbral; con estas celdas, ni umbral ni pendiente.

## Dónde no se puede medir, y de quién es la culpa

**El estrato de dominio y sqlglot.** La primera versión de este experimento los declaró «no
interpretables» y lo dejó ahí. Es verdad pero es una excusa: eran ininterpretables porque yo elegí
tareas que el árbol *intacto* ya no resolvía, y sin margen no hay caída que medir. Al añadir el
filtro de coste —una tarea solo entra si el código limpio la resuelve en menos de la mitad del
presupuesto— y regenerarlas, **sqlglot no produjo ni una tarea válida en 56 intentos**. Eso ya no es
un error de elección: es un dato sobre el repositorio y este modelo.

**La sonda TypeScript.** Existía para comprobar si el resultado sobre los tipos es un artefacto de
que en Python sean opcionales. Construirla dejó un hallazgo que no depende de ninguna celda: en
TypeScript, **quitar las anotaciones no es una transformación semánticamente equivalente** — bajo
`strict` el programa deja de compilar y el script de test suele ejecutar el compilador, así que las
anotaciones son parte de lo que la suite verifica. Lo que sí funciona es sustituir cada anotación
por `any`: sigue compilando, se borra al emitir, verificado idéntico sobre los 4.968 tests de
runtime de hono. Sus celdas, con la baseline en el suelo, no permiten concluir nada.

## La varianza, que es la razón de casi todo lo anterior

Este experimento ha producido, en tres versiones sucesivas, tres conclusiones distintas sobre los
mismos repositorios:

| Con | Decía |
|---|---|
| 1 pasada por celda | los nombres cuestan 28 puntos |
| 3 pasadas | ninguna práctica hace nada; degradarlo todo baja al 53% |
| 10-15 pasadas | tampoco eso; el efecto está en pint y en devolver los nombres |

Ninguna de las dos primeras era deshonesta y las tres salieron del mismo código. Lo que cambió fue
la potencia. Con dieciocho celdas por condición solo se ven caídas de treinta y ocho puntos o más:
una tabla plana no significaba «da igual», significaba «no lo sabemos», y yo la leí como lo primero.

Por eso cada fila de este artículo lleva su intervalo y, cuando no hay diferencia, la caída que sí
se habría visto. Es la única forma de que un lector distinga las dos cosas sin repetir el
experimento.

## Lo que esto no contesta

**El techo de 40 turnos es una elección de diseño.** Es donde el presupuesto aprieta; con cien, pint
probablemente se parecería a python-stdnum. El hallazgo no es «el código degradado no se puede
arreglar», es «cuesta más, y los presupuestos son finitos».

**Un solo modelo por tier, y un solo par de tiers.** El contraste entre el modelo con margen y el
que no lo tiene es el resultado más robusto del experimento, y descansa en dos modelos.

**Dos repositorios sostienen todo.** python-stdnum dice dónde no pasa nada; pint, dónde sí. Los
otros dos entraron para la curva de tamaño y para la sonda de tipos, y ninguno de los dos llegó a
dar un bloque interpretable.

Prefiero publicar una tabla con sus zonas muertas marcadas que un titular que los datos no
sostienen. Las corridas están [en el repo](https://github.com/JaviMaligno/agent-code-practices/tree/main/results),
incluidas las que no midieron nada.

---

*Código y datos: [agent-code-practices](https://github.com/JaviMaligno/agent-code-practices). Sigue
la línea de [Agentes que programan y trabajo en equipo](/es/blog/coding-agents-structure), que
preguntaba si la estructura vence a la habilidad social en un equipo de agentes; este pregunta lo
mismo un nivel más abajo, sobre la estructura del código.*
