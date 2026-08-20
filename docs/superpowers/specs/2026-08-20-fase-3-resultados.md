# Fase 3 — Resultados: B1 y B5, y el criterio de equivalencia corregido

**Fecha:** 2026-08-20
**Plan:** [`../plans/2026-08-19-fase-3-cohesion-y-tamano.md`](../plans/2026-08-19-fase-3-cohesion-y-tamano.md)
**Spec:** [`2026-08-14-software-practices-for-coding-agents-design.md`](2026-08-14-software-practices-for-coding-agents-design.md), §4.2, §6.3, §3.6.3
**Fase 2:** [`2026-08-19-fase-2-resultados.md`](2026-08-19-fase-2-resultados.md)
**Código:** https://github.com/JaviMaligno/agent-code-practices — `439 passed`

---

## 1. Las nueve transformaciones están implementadas

A1, A2, A3, A4, B1, B2, B3, B4 y B5, más los puntos de curva `B5-500`, `B5-2000` y `B5-10000`. Con
esto se pueden construir T1, T2 y T3 (§6.1).

---

## 2. El hallazgo que más importa: la equivalencia era en parte autocumplida

El reescritor de literales de cadena —el que hace que un módulo movido siga siendo alcanzable por su
nombre nuevo— **editaba también las aserciones de la suite del repo**. Reproducido: B5 absorbió un
módulo y reescribió el propio test de `assert who_now() == 'lab7pkg.zzz_named'` al nombre nuevo. El
test pasaba porque se había cambiado el test.

Esto toca el criterio con el que se ha validado todo el proyecto. La línea que se ha implementado:
§4.3.1 obliga a transformar la suite —si no, los tests no compilan y se mide otra cosa—, así que sus
**imports y referencias a módulos** sí se reescriben, pero **lo que la suite afirma** no.

**Las cuatro celdas que ya se daban por buenas se revalidaron con el criterio corregido y siguen
siendo equivalentes.** Ninguna pasaba por esto.

---

## 3. Equivalencia verificada

| Celda | Dosis | Suite original | Suite transformada |
|---|---|---|---|
| pint × B2 | 126 ficheros | 2.024p / 730s | idéntica |
| pint × B4 | suite completa fuera | 2.024p / 730s | idéntica |
| **pint × B1** | 43 ficheros | 2.024p / 730s | idéntica |
| sqlglot × B2 | 229 ficheros | 1.231p | idéntica |
| sqlglot × B4 | suite completa fuera | 1.231p | idéntica |
| **python-stdnum × B1** | 51 ficheros | 413p / 9s | idéntica |

Cada celda aborta si la dosis es cero, en vez de declararse equivalente: una celda que no cambia nada
no prueba nada.

---

## 4. La dosis de B1 y B5, repo por repo

**B1 (cohesión)** — definiciones de nivel de módulo, cuántas son candidatas a moverse y cuántas se
mueven de verdad:

| Repo | Definiciones | Candidatas | Movidas |
|---|---|---|---|
| python-stdnum | 1.232 | 993 | 33 (3,3% de las candidatas) |
| pint | 586 | 275 | 75 (27%) |
| sqlglot | 2.131 | 839 | 221 |
| holidays | 1.546 | 1.118 | 707 |

B1 es la única transformación de familia B con dosis en **los cuatro** repos, incluido python-stdnum,
donde B2 y B5 dan cero. Tiene sentido: reparte definiciones **dentro** de los ficheros que ya
existen, así que no depende de que los módulos se puedan mover de sitio, que es justo lo que allí
está prohibido.

**B5 (tamaño)** — la curva de §6.3 tiene menos puntos de los que el spec supone:

| Repo | Puntos reales |
|---|---|
| sqlglot | **4**: 253 → 220 → 198 → 195 ficheros |
| pint | **3**: 110 → 98 → 90; los techos de 2.000 y 10.000 dan el mismo árbol |
| python-stdnum | **1**: dosis cero en los tres techos |
| holidays | **1**: dosis cero en los tres techos |

La causa de las dosis cero es la misma que deja a B2 sin efecto ahí: esos repos resuelven sus módulos
por nombre construido en ejecución, así que **el árbol de módulos es su tabla de búsqueda** y moverlo
rompería el programa. Y en pint, a partir de 2.000 líneas lo que limita ya no es el techo sino qué
módulos son compatibles entre sí. **El umbral que busca §6.3 solo se puede medir en sqlglot**, y el
artículo tiene que decirlo así.

---

## 5. Decisiones que cambiaron el diseño

**B1 va la primera de todas.** La clave de un movimiento de símbolo es su nombre cualificado
original; si B1 corriera después de A2 solo podría anunciar el nombre opaco, y todos los símbolos
movidos se caerían del manifiesto **en silencio**. Es el mismo fallo en verde de la fase 2, cazado
esta vez con un test que falla con el orden anterior.

**Los ficheros de test quedan fuera del reparto de B1**, aunque sus imports sí se reescriben. En una
suite de pytest, *dónde* vive una definición es semántica: fixtures por módulo, `conftest.py`,
`importorskip` de primer nivel. Medido: repartir dentro de `pint/testsuite/` dejó la colecta en 0
tests de 2.758. Cuesta dosis —pint baja de 558 a 275 candidatas— y se declara.

**Una condición leía la caché que dejó la anterior.** B1 y B5 cambian el `__module__` de las clases,
así que el árbol transformado no puede leer los pickles del original; y la caché `:auto:` de pint
vive en un directorio del **host** compartido entre corridas. Es contaminación entre celdas, contra
§5.4.4, y ya está aislada.

**Dos guardas de B1 estaban muertos**: movía definiciones que leen `__name__` —que cambia de valor al
llegar al destino— y definiciones cuyo propio decorador las registra al importar el módulo de origen.
Este segundo es el modo de fallo más peligroso del experimento: el registro deja de rellenarse, el
programa cambia y **todo sigue verde**.

---

## 6. Lo que queda

El pre-flight del spec §3.6, que es lo único que separa de la campaña:

1. **24 tareas generadas por inyección de fallo**, 12 genéricas y 12 de dominio, con sus
   `fail_to_pass` y `pass_to_pass`.
2. **Validación del estrato de dominio por aislamiento** (§3.6.2b): si el modelo detecta el fallo
   viendo la función sola, no es de dominio.
3. **Oráculos de control** (§5.4.6): el no-op al 0% y el oráculo al 100% en todas las condiciones.
4. **Baseline T0 discriminante**: ni pegado al 0% ni al 100%, o el experimento no se corre (§9).
