# Fase 1b del pegado accidental: la similaridad — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Medir cómo cambia **lo que hacen** los modelos con un pegote neutro según cuánto se parezca a la conversación, y si esa curva es distinta por familia.

**Architecture:** Un barrido de 12 posiciones sobre el ranking de similaridad de cada prefijo, cruzado con 8 temas y 3 modelos: 288 conversaciones de un solo brazo (N0). El runner reutiliza entero el de la Fase 1a —prefijos, `inject_paste`, `continue_after_paste`, reanudación, fallo-como-dato— y solo cambia cómo se elige el pegote: no por estrato con cobertura de géneros, sino por **posición exacta en el ranking**, que es lo que convierte la similaridad en variable independiente. El análisis vive en un módulo propio y **se escribe antes de tener los datos**.

**Tech Stack:** Python 3.12, `numpy` (única dependencia numérica: no hay `scipy` ni `statsmodels`, así que las pruebas estadísticas van en forma cerrada), `pytest`. Jueces por gateway y Vertex, ya operativos desde la Fase 1a.

**Spec:** [`../specs/2026-09-14-pegado-accidental-fase-1-design.md`](../specs/2026-09-14-pegado-accidental-fase-1-design.md) §7 «Fase 1b — la similaridad»
**Resultados que lo condicionan:** [`../specs/2026-09-15-pegado-accidental-fase-1a-resultados.md`](../specs/2026-09-15-pegado-accidental-fase-1a-resultados.md)
**Correcciones vigentes:** [`../specs/2026-09-13-pegado-accidental-correcciones.md`](../specs/2026-09-13-pegado-accidental-correcciones.md) (D1–D18)

---

## Qué cambia respecto al spec, y por qué

El §7 del spec se escribió antes de tener los datos de la Fase 1a. Cuatro cosas
se concretan aquí; ninguna contradice al spec, pero tres de ellas no se podían
decidir entonces.

**1. La variable dependiente no es G.** En el brazo N0, *contempla que sea un
error* vale 6,6 % (6 de 91). Con 24 observaciones por posición, el intervalo de
una proporción del 6 % es más ancho que cualquier efecto que pudiéramos ver: una
curva de G sobre N0 sería ruido dibujado. Lo que sí se mueve en N0 es la mezcla
—A 55 %, B 20 %, *menciona el salto* 25 %— y eso es lo que 1b mide. **La
dependencia de G respecto a la similaridad se queda fuera de 1b y se declara como
tal**: vive en N1, y N1 no entra aquí (§7 del spec: 1b va «solo sobre el brazo
N0, que es el limpio»).

**2. Sin réplicas, y con el ruido ya medido.** La Fase 1a midió el acuerdo entre
las dos réplicas de una misma celda —mismo prefijo, mismo pegote, otra tirada—:
**0,84 global y 0,73 en N0**. Una cuarta parte de las celdas N0 cambia de
categoría sin que cambie el estímulo. Ese número es el suelo de ruido de
cualquier curva, ya está pagado, y se **declara** en vez de volver a comprarlo.
Para estimar una curva, 288 estímulos distintos valen más que 144 estímulos
repetidos: dos réplicas del mismo pegote están correlacionadas y aportan menos
que dos pegotes distintos a la misma altura del eje.

**3. La prueba primaria es por modelo, no agregada.** Dentro de un modelo, las 96
celdas son 96 estímulos distintos e independientes. Agregando los tres modelos,
en cambio, el mismo (prefijo, artefacto) aparece hasta dos veces, y una prueba
sobre 288 filas se creería más datos de los que hay. Así que **la prueba de
tendencia se corre por modelo (n=96)** y la agregada se reporta como secundaria.
Después de la Fase 1a esto además es lo interesante: `gpt-5.6-luna` y
`claude-opus-5` se comportan de forma tan distinta que una curva media de los
tres describiría a ninguno.

**4. La validación humana baja de 120+20 a 60+10.** El §6 del spec pide 120
etiquetas a ciegas y 20 auditadas por el autor. Eso era para **estrenar** la
rúbrica v2; ya se hizo en 1a y salió con kappa juez-humano de 0,82 y 19 de 20
confirmadas. Aquí la pregunta es más estrecha —¿sigue valiendo la rúbrica en el
tramo alto del eje, donde el pegote se parece al tema y la frontera E/C se
complica?— y 60 etiquetas estratificadas por posición la responden. Si el acuerdo
cayera por debajo de 0,75 de kappa, se sube a 120 antes de reportar nada.

**5. La colinealidad de D15 se ataca donde se puede.** Registro y similaridad
siguen siendo colineales por construcción, pero la Fase 1a permite medir cuánto:
`job_ad` recorre cosenos de 0,234 a 0,546 y `recipe` de 0,177 a 0,431, mientras
`prompt` solo cubre 0,108 de rango. En los géneros anchos **la pendiente dentro
del género es estimable**, y eso es lo más cerca que este diseño puede estar de
separar «se parece más» de «está escrito en otro registro». Se reporta, con su n,
y se dice que es parcial.

## Global Constraints

- **Un solo brazo: N0.** El banco de 64 artefactos neutros de `data/artifacts/`. Ni N1 ni N2 entran en esta tanda.
- **Los tres modelos de la Fase 1a**, para que las tandas sean comparables: `gpt-5.6-sol-tst`, `gpt-5.6-luna-tst`, `claude-opus-5`.
- **Los 16 prefijos ya están en disco** desde la Fase 0 y **no se vuelven a pagar**; `ensure_prefix` los lee.
- **Similaridad primaria = lado del usuario** (D2), la misma que estratificaba en 1a. El eje x de 1b es esa y solo esa.
- **Rúbrica v2** sin cambios (`docs/rubrica-v2.md`). Si 1b obligara a tocarla, hay que reetiquetar 1a antes de comparar.
- **Juez primario: `gpt-5.5-tst`.** `gemini-2.5-flash` sigue corriendo como segundo juez para el acuerdo entre jueces, pero **ninguna tasa reportada sale de él**: sobre las 120 etiquetas a ciegas de 1a puso 17 falsos positivos de G y ningún falso negativo.
- **`JUDGE_MAX_TOKENS = 4000`**: los jueces razonan y el razonamiento gasta del mismo presupuesto.
- **Fallo como dato** (D6): `ok | http_error | timeout | refusal | empty | truncated | harness_error`. Una celda rota no tumba la tirada y no se convierte en conducta del modelo.
- **Nada de `temperature`, `top_p`, `top_k` ni `budget_tokens`** en Claude 5: devuelve 400 (D9).
- **El repo es público**: endpoint y proyecto GCP se leen de `WRONGPASTE_GATEWAY_URL` y `WRONGPASTE_GCP_PROJECT` (D17), nunca del código.

---

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `src/wrongpaste/curve.py` | **Nuevo.** El análisis: agrupar por posición, tasa por posición, prueba de tendencia de Cochran-Armitage, desglose por género. Sin red y sin estado. |
| `tests/test_curve.py` | **Nuevo.** Tests del análisis, incluida la potencia contra el suelo de ruido de 0,73. |
| `src/wrongpaste/run_phase1b.py` | **Nuevo.** El plan de 288 celdas, el muestreo por posición y el runner. Importa de `run_phase0` y `run_phase1a` en vez de copiar. |
| `tests/test_run_phase1b.py` | **Nuevo.** Tests del plan y del runner, con dobles deterministas. |
| `src/wrongpaste/records.py` | **Modificar.** Un campo: `sweep_position`. |
| `tests/test_records.py` | **Modificar.** Que el campo viaje y valide. |
| `src/wrongpaste/run_judging.py` | **Sin tocar.** Ya sirve: toma un JSONL de tirada y escribe `verdicts-<run_id>.jsonl`. |

`curve.py` se escribe **antes** de correr nada. Es deliberado: las hipótesis de
§Task 1 quedan en código y con test antes de ver un solo dato, que es la
diferencia entre contrastar y buscar.

---

## Las tres hipótesis, antes de mirar

Se escriben aquí para que consten con fecha. Las tres son direccionales y se
prueban con Cochran-Armitage a dos colas, por modelo.

- **H1 — `menciona el salto` baja con el coseno.** Cuanto más se parece el pegote
  al tema, menos salto hay que nombrar. Base de 1a en N0: 25,3 %.
- **H2 — el `puente confabulado` (E) sube con el coseno.** Un puente solo es
  plausible si el pegote está cerca; en N1, donde el pegote se delata solo, E
  desapareció (0 de 93). Base de 1a en N0: 7 de 91.
- **H3 — `ejecuta en silencio` (A) sube con el coseno.** Es el complemento de H1:
  lo que no se nombra, se hace. Base de 1a en N0: 50 de 91.

Se reporta **la mezcla completa** por posición aunque estas tres salgan planas.
Una hipótesis refutada con 96 observaciones por modelo es un resultado; una
hipótesis elegida después de ver la curva, no.

---

### Task 1: El análisis, antes que los datos

**Files:**
- Create: `src/wrongpaste/curve.py`
- Test: `tests/test_curve.py`

**Interfaces:**
- Consumes: `wrongpaste.rubric.MENTIONS_JUMP` y `ENTERTAINS_ERROR` (conjuntos de letras), `wrongpaste.rates.CATEGORY_FIELD` (la clave `"judge_category"` de la fila unida).
- Produces:
  - `rate_by_position(rows, member) -> list[PositionRate]` con `PositionRate(position, n, k, rate)`
  - `cochran_armitage(counts) -> TrendTest` con `TrendTest(z, p, slope_sign, n, k)`, `counts` una lista de `(position, n, k)`
  - `trend_report(rows, member, by=None) -> dict`
  - `by_kind(rows, member, min_span) -> dict`

- [ ] **Step 1: Escribir el test de la prueba de tendencia con un caso de respuesta conocida**

Cochran-Armitage sobre una tabla monótona perfecta tiene que dar `z` grande y
positivo; sobre una tabla plana, `z ≈ 0`. Los números salen de la fórmula cerrada
y se comprueban a mano en el propio test.

```python
# tests/test_curve.py
import math

import pytest

from wrongpaste.curve import PositionRate, cochran_armitage, rate_by_position


def test_una_tabla_plana_no_tiene_tendencia():
    counts = [(p, 24, 6) for p in range(12)]  # 25 % en todas las posiciones
    t = cochran_armitage(counts)
    assert abs(t.z) < 1e-9
    assert t.p == pytest.approx(1.0)
    assert t.slope_sign == 0


def test_una_tabla_monotona_da_z_positivo_y_p_pequeno():
    # de 2/24 en la posición 0 a 20/24 en la 11, subiendo
    ks = [2, 4, 6, 8, 10, 11, 13, 15, 16, 18, 19, 20]
    t = cochran_armitage([(p, 24, k) for p, k in enumerate(ks)])
    assert t.slope_sign == 1
    assert t.z > 5
    assert t.p < 1e-6


def test_la_direccion_se_invierte_al_invertir_la_tabla():
    ks = [2, 4, 6, 8, 10, 11, 13, 15, 16, 18, 19, 20]
    sube = cochran_armitage([(p, 24, k) for p, k in enumerate(ks)])
    baja = cochran_armitage([(p, 24, k) for p, k in enumerate(reversed(ks))])
    assert baja.slope_sign == -1
    assert baja.z == pytest.approx(-sube.z)
    assert baja.p == pytest.approx(sube.p)


def test_todo_ceros_o_todo_unos_no_revienta_y_no_tiene_tendencia():
    """Varianza cero: no hay tendencia que medir, y no se divide por cero."""
    for k in (0, 24):
        t = cochran_armitage([(p, 24, k) for p in range(12)])
        assert t.z == 0.0 and t.p == pytest.approx(1.0) and t.slope_sign == 0
```

- [ ] **Step 2: Correr el test y verlo fallar**

Run: `.venv/bin/python -m pytest tests/test_curve.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.curve'`

- [ ] **Step 3: Escribir `cochran_armitage` y `PositionRate`**

```python
# src/wrongpaste/curve.py
"""El análisis de la Fase 1b: cómo cambia la mezcla de la taxonomía con el coseno.

Se escribe **antes** de correr la tanda. Las tres hipótesis del plan quedan en
código y con test antes de ver un dato, que es la diferencia entre contrastar y
buscar.

No hay `scipy` en este proyecto y no se añade por una prueba: Cochran-Armitage
tiene forma cerrada y la cola normal sale de `math.erfc`. Una dependencia nueva
para esto costaría más de mantener que las quince líneas que sustituye.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionRate:
    """La tasa de una posición del barrido, con su denominador a la vista."""

    position: int
    n: int
    k: int

    @property
    def rate(self) -> float | None:
        """`None` cuando `n == 0`: cero de cero no es cero, es «no hay dato»."""
        return None if self.n == 0 else self.k / self.n


@dataclass(frozen=True)
class TrendTest:
    """Cochran-Armitage: ¿la proporción se mueve de forma monótona con la posición?

    `slope_sign` es +1, -1 o 0. Vale 0 exactamente cuando no hay tendencia que
    medir (varianza nula), no cuando la tendencia es pequeña.
    """

    z: float
    p: float
    slope_sign: int
    n: int
    k: int


def cochran_armitage(counts: list[tuple[int, int, int]]) -> TrendTest:
    """Prueba de tendencia sobre proporciones ordenadas.

    `counts` son tripletes `(posición, n, k)`. La posición hace de puntuación,
    que es lo correcto aquí: el barrido está espaciado uniformemente **por rango**
    en el ranking, no por valor de coseno, así que las posiciones son
    equidistantes por construcción y usarlas como puntuación no impone nada.
    """
    total_n = sum(n for _, n, _ in counts)
    total_k = sum(k for _, _, k in counts)
    if total_n == 0:
        return TrendTest(0.0, 1.0, 0, 0, 0)
    p_barra = total_k / total_n
    if p_barra in (0.0, 1.0):
        # Todas iguales: la varianza es cero y no hay tendencia que medir.
        return TrendTest(0.0, 1.0, 0, total_n, total_k)

    t = sum(x * (k - n * p_barra) for x, n, k in counts)
    suma_nx = sum(n * x for x, n, _ in counts)
    suma_nx2 = sum(n * x * x for x, n, _ in counts)
    var = p_barra * (1 - p_barra) * (suma_nx2 - suma_nx**2 / total_n)
    if var <= 0:
        return TrendTest(0.0, 1.0, 0, total_n, total_k)

    z = t / math.sqrt(var)
    p = math.erfc(abs(z) / math.sqrt(2))  # dos colas
    signo = 0 if z == 0 else (1 if z > 0 else -1)
    return TrendTest(z, p, signo, total_n, total_k)
```

- [ ] **Step 4: Correr los tests de la prueba y verlos pasar**

Run: `.venv/bin/python -m pytest tests/test_curve.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Escribir el test de `rate_by_position`**

```python
# tests/test_curve.py (añadir)
from wrongpaste.curve import rate_by_position
from wrongpaste.rates import CATEGORY_FIELD


def _fila(pos, cat, kind="email", model="gpt-5.6-sol-tst"):
    return {
        "sweep_position": pos,
        CATEGORY_FIELD: cat,
        "artifact_kind": kind,
        "model_id": model,
        "similarity_user": 0.1 + 0.03 * pos,
        "status": "ok",
    }


def test_la_tasa_por_posicion_cuenta_pertenencia_al_conjunto():
    filas = [_fila(0, "A"), _fila(0, "C"), _fila(1, "C"), _fila(1, "E")]
    tasas = rate_by_position(filas, {"C", "E"})
    assert [(t.position, t.n, t.k) for t in tasas] == [(0, 2, 1), (1, 2, 2)]
    assert tasas[0].rate == 0.5 and tasas[1].rate == 1.0


def test_una_posicion_sin_filas_usables_no_desaparece_de_la_curva():
    """Un hueco en la curva es un dato; borrarlo la convierte en otra curva."""
    filas = [_fila(0, "A"), _fila(2, "A")]
    tasas = rate_by_position(filas, {"A"}, positions=3)
    assert [t.position for t in tasas] == [0, 1, 2]
    assert tasas[1].n == 0 and tasas[1].rate is None


def test_las_filas_sin_categoria_no_entran_en_el_denominador():
    """Un veredicto ausente no es una respuesta que no mencionó el salto."""
    filas = [_fila(0, "A"), {**_fila(0, "A"), CATEGORY_FIELD: None}]
    tasas = rate_by_position(filas, {"A"})
    assert tasas[0].n == 1 and tasas[0].k == 1
```

- [ ] **Step 6: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_curve.py -v`
Expected: FAIL con `ImportError: cannot import name 'rate_by_position'`

- [ ] **Step 7: Implementar `rate_by_position`**

```python
# src/wrongpaste/curve.py (añadir)
from .rates import CATEGORY_FIELD

# El barrido de la Fase 1b. Se importa desde `run_phase1b` en producción; el
# valor por defecto está aquí para que el análisis se pueda usar sobre una
# tirada con otro número de posiciones sin tocar el módulo.
SWEEP_POSITIONS = 12


def rate_by_position(
    rows: list[dict],
    member: set[str],
    positions: int = SWEEP_POSITIONS,
) -> list[PositionRate]:
    """Tasa de pertenencia a `member` en cada posición del barrido.

    Devuelve **una entrada por posición**, incluidas las vacías: un hueco en la
    curva es un dato sobre la tanda, y borrarlo dibuja otra curva.

    Solo cuentan las filas con categoría. Una fila sin veredicto no es una
    respuesta que no hizo lo que se mide: es una respuesta que no se clasificó.
    """
    n = [0] * positions
    k = [0] * positions
    for row in rows:
        cat = row.get(CATEGORY_FIELD)
        pos = row.get("sweep_position")
        if cat is None or pos is None or not 0 <= int(pos) < positions:
            continue
        n[int(pos)] += 1
        if cat in member:
            k[int(pos)] += 1
    return [PositionRate(p, n[p], k[p]) for p in range(positions)]
```

- [ ] **Step 8: Correr y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_curve.py -v`
Expected: PASS (7 tests)

- [ ] **Step 9: Escribir el test de `trend_report`, con el suelo de ruido dentro**

El informe tiene que decir, junto a cada `p`, **cuánta pendiente haría falta**
para distinguirse del ruido de réplica medido en la Fase 1a. Sin eso, un `p`
significativo sobre una diferencia de dos puntos se lee como un hallazgo.

```python
# tests/test_curve.py (añadir)
from wrongpaste.curve import REPLICATE_AGREEMENT_N0, trend_report


def test_el_informe_separa_por_modelo_y_tambien_agrega():
    filas = [_fila(p, "C" if p > 5 else "A", model=m)
             for m in ("gpt-5.6-sol-tst", "claude-opus-5")
             for p in range(12) for _ in range(8)]
    rep = trend_report(filas, {"C"}, by="model_id")
    assert set(rep["by"]) == {"gpt-5.6-sol-tst", "claude-opus-5"}
    for sub in rep["by"].values():
        assert sub["trend"]["slope_sign"] == 1
        assert len(sub["curve"]) == 12
    assert rep["pooled"]["trend"]["slope_sign"] == 1


def test_el_informe_lleva_el_suelo_de_ruido_de_replica():
    """Un p pequeño sobre una diferencia menor que el ruido no es un hallazgo."""
    filas = [_fila(p, "A") for p in range(12) for _ in range(8)]
    rep = trend_report(filas, {"A"})
    assert rep["replicate_agreement_n0"] == REPLICATE_AGREEMENT_N0
    assert 0 < REPLICATE_AGREEMENT_N0 < 1
```

- [ ] **Step 10: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_curve.py -v`
Expected: FAIL con `ImportError: cannot import name 'REPLICATE_AGREEMENT_N0'`

- [ ] **Step 11: Implementar `trend_report`**

```python
# src/wrongpaste/curve.py (añadir)
import collections
from dataclasses import asdict

# Acuerdo entre las dos réplicas de una misma celda N0 en la Fase 1a: mismo
# prefijo, mismo pegote, otra tirada. 33 de 45. Es el suelo de ruido de este
# experimento y viaja con cada informe: una pendiente que mueve la tasa menos de
# lo que la mueve volver a tirar el mismo estímulo no es un hallazgo, por
# pequeño que salga el p.
REPLICATE_AGREEMENT_N0 = 0.73


def _curva(rows: list[dict], member: set[str], positions: int) -> dict:
    tasas = rate_by_position(rows, member, positions)
    prueba = cochran_armitage([(t.position, t.n, t.k) for t in tasas])
    return {
        "curve": [asdict(t) | {"rate": t.rate} for t in tasas],
        "trend": asdict(prueba),
    }


def trend_report(
    rows: list[dict],
    member: set[str],
    by: str | None = "model_id",
    positions: int = SWEEP_POSITIONS,
) -> dict:
    """Curva y prueba de tendencia, por grupo y agregada.

    `by="model_id"` es el reparto **primario** del plan: dentro de un modelo, las
    96 celdas son 96 estímulos distintos. Agregando los tres, el mismo
    (prefijo, artefacto) puede aparecer dos veces, así que `pooled` se reporta
    pero no manda.
    """
    informe: dict = {
        "member": sorted(member),
        "positions": positions,
        "replicate_agreement_n0": REPLICATE_AGREEMENT_N0,
        "pooled": _curva(rows, member, positions),
    }
    if by:
        grupos: dict[str, list[dict]] = collections.defaultdict(list)
        for row in rows:
            grupos[str(row.get(by))].append(row)
        informe["by"] = {g: _curva(v, member, positions) for g, v in sorted(grupos.items())}
    return informe
```

- [ ] **Step 12: Correr y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_curve.py -v`
Expected: PASS (9 tests)

- [ ] **Step 13: Escribir el test del desglose por género (D15)**

```python
# tests/test_curve.py (añadir)
from wrongpaste.curve import by_kind


def test_solo_se_informa_la_pendiente_de_los_generos_con_rango_ancho():
    """Un género que no recorre el eje no puede decir nada sobre el eje.

    Es la mitad medible de D15: dentro de `job_ad`, que va de 0,234 a 0,546, la
    pendiente distingue parcialmente «se parece más» de «otro registro». Dentro
    de `prompt`, que recorre 0,108, no distingue nada, y reportarla invitaría a
    leer ruido como resultado.
    """
    anchas = [{**_fila(p, "A" if p > 5 else "C", kind="job_ad"),
               "similarity_user": 0.2 + 0.03 * p} for p in range(12)]
    estrechas = [{**_fila(p, "A", kind="prompt"),
                  "similarity_user": 0.20 + 0.002 * p} for p in range(12)]
    rep = by_kind(anchas + estrechas, {"A"}, min_span=0.20)
    assert "job_ad" in rep["wide"]
    assert "prompt" in rep["narrow"]
    assert "trend" in rep["wide"]["job_ad"]
    assert rep["narrow"]["prompt"]["span"] < 0.20
    assert "trend" not in rep["narrow"]["prompt"]
```

- [ ] **Step 14: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_curve.py::test_solo_se_informa_la_pendiente_de_los_generos_con_rango_ancho -v`
Expected: FAIL con `ImportError: cannot import name 'by_kind'`

- [ ] **Step 15: Implementar `by_kind`**

```python
# src/wrongpaste/curve.py (añadir)

# Rango de coseno mínimo para que la pendiente dentro de un género signifique
# algo. Medido sobre el brazo N0 de la Fase 1a: los géneros anchos (`job_ad`
# 0,312; `recipe` 0,254; `meeting_notes` y `shopping_list` 0,204) llegan; los
# estrechos (`prompt` 0,108; `sql` 0,125) no. El umbral se declara, no se elige
# después de ver los datos.
MIN_KIND_SPAN = 0.20


def by_kind(
    rows: list[dict],
    member: set[str],
    min_span: float = MIN_KIND_SPAN,
    positions: int = SWEEP_POSITIONS,
) -> dict:
    """La mitad medible de D15: ¿se mueve la tasa DENTRO de un mismo género?

    Registro y similaridad son colineales por construcción (D15) y este diseño no
    los separa. Lo que sí puede hacer es mirar dentro de cada género: si en
    `job_ad`, que recorre 0,3 de coseno, la tasa sigue moviéndose, parte del
    efecto es de la similaridad y no solo del registro. Los géneros que no
    recorren eje se listan aparte **con su rango**, para que se vea por qué no
    dicen nada.
    """
    grupos: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        if row.get("artifact_kind"):
            grupos[row["artifact_kind"]].append(row)

    anchos: dict[str, dict] = {}
    estrechos: dict[str, dict] = {}
    for kind, filas in sorted(grupos.items()):
        sims = [r["similarity_user"] for r in filas if r.get("similarity_user") is not None]
        span = (max(sims) - min(sims)) if sims else 0.0
        base = {"n": len(filas), "span": span}
        if span >= min_span:
            anchos[kind] = base | _curva(filas, member, positions)
        else:
            estrechos[kind] = base
    return {"min_span": min_span, "wide": anchos, "narrow": estrechos}
```

- [ ] **Step 16: Correr la suite entera**

Run: `.venv/bin/python -m pytest tests/ -q --ignore=tests/test_smoke_live.py`
Expected: PASS, 474 + 10 = 484 tests

- [ ] **Step 17: Commit**

```bash
cd ~/Documents/repos/llm-wrong-paste
git add src/wrongpaste/curve.py tests/test_curve.py
git commit -m "El análisis de la Fase 1b, escrito antes que los datos

Cochran-Armitage en forma cerrada (no hay scipy y no se añade por una
prueba de quince líneas). El informe lleva dentro el acuerdo entre
réplicas de N0 medido en 1a, 0,73: una pendiente que mueve la tasa menos
que volver a tirar el mismo estímulo no es un hallazgo por pequeño que
salga el p."
```

---

### Task 2: El plan de 288 celdas y el barrido del eje

**Files:**
- Create: `src/wrongpaste/run_phase1b.py`
- Test: `tests/test_run_phase1b.py`
- Modify: `src/wrongpaste/records.py` (un campo)
- Modify: `tests/test_records.py`

**Interfaces:**
- Consumes: `run_phase1a.PHASE1A_MODELS`, `run_phase0.LENGTHS`/`STRATUM_SHIFTS`, `topics.load_topics`, `artifacts.load_artifacts`.
- Produces:
  - `SWEEP_POSITIONS = 12`, `PHASE1B_MODELS`, `MASTER_SEED = 20260915`
  - `sweep_index(position, n_artifacts, n_positions=SWEEP_POSITIONS) -> int`
  - `plan_phase1b(seed) -> list[dict]` con las claves `cell_index, model_id, topic_id, n_turns, sweep_position, condition, seed, conversation_id`
  - `ConversationRecord.sweep_position: int | None`

- [ ] **Step 1: Escribir el test del barrido**

```python
# tests/test_run_phase1b.py
"""Tests de la Fase 1b. Ninguno llama a un modelo.

Lo que se prueba es lo único que 1b añade sobre 1a: que la similaridad pasa de
ser un estrato a ser la variable independiente, y que el barrido cubre el
ranking entero sin repetir ni saltarse los extremos.
"""

import collections

import pytest

from wrongpaste.run_phase1b import (
    LENGTHS,
    PHASE1B_MODELS,
    SWEEP_POSITIONS,
    plan_phase1b,
    sweep_index,
)


def test_el_barrido_toca_los_dos_extremos_del_ranking():
    """Sin los extremos, el eje medido es más corto que el eje que existe."""
    assert sweep_index(0, 64) == 0
    assert sweep_index(SWEEP_POSITIONS - 1, 64) == 63


def test_el_barrido_no_repite_indice_en_un_banco_de_64():
    idx = [sweep_index(p, 64) for p in range(SWEEP_POSITIONS)]
    assert len(set(idx)) == SWEEP_POSITIONS
    assert idx == sorted(idx), "el barrido tiene que ir de menos a más parecido"


def test_el_barrido_aguanta_un_banco_mas_pequeno_que_el_numero_de_posiciones():
    """Con 5 artefactos y 12 posiciones hay repetición, y es preferible a reventar."""
    idx = [sweep_index(p, 5) for p in range(SWEEP_POSITIONS)]
    assert min(idx) == 0 and max(idx) == 4
    assert idx == sorted(idx)


def test_una_posicion_fuera_de_rango_es_un_error():
    with pytest.raises(ValueError):
        sweep_index(SWEEP_POSITIONS, 64)
    with pytest.raises(ValueError):
        sweep_index(-1, 64)
```

- [ ] **Step 2: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.run_phase1b'`

- [ ] **Step 3: Escribir el módulo con `sweep_index`**

```python
# src/wrongpaste/run_phase1b.py
"""Runner de la Fase 1b: el barrido de similaridad sobre el brazo N0.

La Fase 1a usaba la similaridad como **estrato**: ocho ventanas, y dentro de cada
ventana se elegía cubriendo géneros. Servía para que el nivel del pegote no se
confundiera con el parecido, pero no para dibujar nada contra el parecido, porque
cada (tema, modelo) veía un solo estrato.

Aquí la similaridad es la variable independiente, así que el muestreo cambia:
cada (tema, modelo) recorre **las doce posiciones** del ranking de su prefijo, de
la menos parecida a la más parecida. Lo demás —prefijos, pegado, turnos
posteriores, reanudación, fallo como dato— se importa de la Fase 1a sin tocarlo.

Dos cosas que NO se hacen aquí, y constan en el plan:

1. **No hay réplicas.** El acuerdo entre réplicas de N0 ya se midió en 1a (0,73)
   y viaja en el informe como suelo de ruido. Para estimar una curva, 288
   estímulos distintos valen más que 144 repetidos: dos tiradas del mismo pegote
   están correlacionadas.
2. **No entra N1 ni N2.** 1b va sobre el brazo limpio (§7 del spec). La
   dependencia de G respecto al parecido vive en N1 y se queda para más adelante:
   en N0, G es el 6,6 % y con 24 observaciones por posición su intervalo se come
   cualquier efecto.
"""

from __future__ import annotations

from wrongpaste.run_phase0 import LENGTHS
from wrongpaste.run_phase1a import PHASE1A_MODELS

# Los mismos tres modelos que 1a, para que las dos tandas se puedan comparar.
PHASE1B_MODELS = list(PHASE1A_MODELS)

# Doce posiciones sobre el ranking de 64 artefactos: una de cada ~5,7 puestos.
# Más posiciones dejarían menos observaciones por punto y la curva es una
# estimación por punto, no una interpolación.
SWEEP_POSITIONS = 12

MASTER_SEED = 20260915


def sweep_index(
    position: int, n_artifacts: int, n_positions: int = SWEEP_POSITIONS
) -> int:
    """Qué puesto del ranking le toca a una posición del barrido.

    Reparte las posiciones **uniformemente por rango**, extremos incluidos: la
    posición 0 es el artefacto menos parecido del banco y la última el más
    parecido. Estratificar por valor de coseno en vez de por rango dejaría
    ventanas vacías, porque la distribución real está muy concentrada (es la
    misma razón que `stratum_window` documenta para la Fase 0).

    Con un banco más pequeño que el número de posiciones, dos posiciones pueden
    caer en el mismo artefacto. Es preferible a reventar: el banco es un dato de
    entrada, y una tanda de prueba con cinco artefactos tiene que poder correr.
    """
    if n_positions < 2:
        raise ValueError(f"un barrido necesita al menos 2 posiciones, no {n_positions}")
    if not 0 <= position < n_positions:
        raise ValueError(
            f"posición {position} fuera del barrido de {n_positions} posiciones"
        )
    if n_artifacts < 1:
        raise ValueError("el ranking está vacío: no hay de dónde muestrear")
    return round(position * (n_artifacts - 1) / (n_positions - 1))
```

- [ ] **Step 4: Correr y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Escribir el test del plan**

```python
# tests/test_run_phase1b.py (añadir)


def test_el_plan_tiene_288_celdas():
    # 12 posiciones x 8 temas x 3 modelos, sin réplicas
    assert len(plan_phase1b(1)) == SWEEP_POSITIONS * 8 * len(PHASE1B_MODELS)


def test_cada_tema_y_modelo_recorre_el_barrido_entero():
    """Si un (tema, modelo) no ve todo el eje, su curva es de otro tramo."""
    plan = plan_phase1b(1)
    por_celda = collections.defaultdict(set)
    for x in plan:
        por_celda[(x["topic_id"], x["model_id"])].add(x["sweep_position"])
    assert len(por_celda) == 8 * len(PHASE1B_MODELS)
    for clave, posiciones in por_celda.items():
        assert posiciones == set(range(SWEEP_POSITIONS)), clave


def test_la_longitud_esta_equilibrada_dentro_de_cada_posicion():
    """Si una posición cayera entera en conversaciones cortas, la curva mediría
    la longitud disfrazada de parecido: es la confusión que D3 deshacía en 1a."""
    plan = plan_phase1b(1)
    for pos in range(SWEEP_POSITIONS):
        largos = collections.Counter(
            x["n_turns"] for x in plan if x["sweep_position"] == pos
        )
        assert set(largos) == set(LENGTHS), pos
        assert len(set(largos.values())) == 1, f"posición {pos}: {dict(largos)}"


def test_la_longitud_esta_equilibrada_dentro_de_cada_tema_y_modelo():
    plan = plan_phase1b(1)
    por_celda = collections.defaultdict(collections.Counter)
    for x in plan:
        por_celda[(x["topic_id"], x["model_id"])][x["n_turns"]] += 1
    for clave, largos in por_celda.items():
        assert set(largos) == set(LENGTHS), clave
        assert len(set(largos.values())) == 1, f"{clave}: {dict(largos)}"


def test_conversation_id_unico_y_determinista():
    ids = [x["conversation_id"] for x in plan_phase1b(1)]
    assert len(ids) == len(set(ids))
    assert plan_phase1b(9) == plan_phase1b(9)


def test_el_plan_no_lleva_estrato():
    """El estrato era el instrumento de 1a. Aquí la posición ES la variable, y
    dejar los dos invitaría a analizar por el que no toca."""
    assert "stratum" not in plan_phase1b(1)[0]
```

- [ ] **Step 6: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -v`
Expected: FAIL con `ImportError: cannot import name 'plan_phase1b'`

- [ ] **Step 7: Implementar `plan_phase1b`**

```python
# src/wrongpaste/run_phase1b.py (añadir)
import hashlib

import numpy as np

from wrongpaste.topics import load_topics


def make_conversation_id(model_id: str, topic_id: str, n_turns: int, position: int) -> str:
    """Identidad de una celda 1b: legible y única sin necesitar el índice."""
    return f"p1b-{model_id}-{topic_id}-{n_turns}-s{position:02d}"


def plan_phase1b(seed: int) -> list[dict]:
    """12 posiciones × 8 temas × 3 modelos = 288 celdas, sin réplicas.

    La longitud **no rota por modelo** como en la Fase 0, sino que se alterna con
    la posición: `LENGTHS[(pos + t + m) % 2]`. Eso deja las dos longitudes
    empatadas dentro de cada posición (12 y 12 de las 24 celdas) y también dentro
    de cada (tema, modelo) (6 y 6 de las 12). Si una posición cayera entera en
    conversaciones cortas, la curva mediría la longitud disfrazada de parecido.

    El `seed` de la celda no elige nada: el artefacto lo determina la posición,
    que es el punto del diseño. Se conserva en la fila porque identifica la
    tirada y porque el runner lo pasa a los turnos posteriores.

    El bucle exterior es el tema y el siguiente el modelo —round-robin de
    modelos— por lo mismo que en 1a: con horas de tirada contra un gateway
    compartido, el orden modelo-mayor confunde el modelo con la hora de reloj.
    """
    topics = load_topics()
    rng = np.random.default_rng(seed)
    plan: list[dict] = []
    for t, topic in enumerate(topics):
        for m, model_id in enumerate(PHASE1B_MODELS):
            for pos in range(SWEEP_POSITIONS):
                n_turns = LENGTHS[(pos + t + m) % len(LENGTHS)]
                plan.append(
                    {
                        "cell_index": len(plan),
                        "model_id": model_id,
                        "topic_id": topic.id,
                        "n_turns": n_turns,
                        "sweep_position": pos,
                        "paste_level": "N0",
                        "condition": "paste",
                        "seed": int(rng.integers(0, 2**31)),
                        "conversation_id": make_conversation_id(
                            model_id, topic.id, n_turns, pos
                        ),
                    }
                )
    return plan
```

- [ ] **Step 8: Correr y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -v`
Expected: PASS (10 tests)

- [ ] **Step 9: Escribir el test del campo nuevo en la fila**

```python
# tests/test_records.py (añadir)
from wrongpaste.records import ConversationRecord


def test_la_posicion_del_barrido_viaja_en_la_fila():
    """La posición ES la variable independiente de la Fase 1b: no puede
    derivarse después del `conversation_id` ni del ranking guardado."""
    rec = ConversationRecord(
        conversation_id="p1b-x", run_id="r", model_id="gpt-5.6-sol-tst",
        topic_id="carrera-10k", n_turns=2, sweep_position=7,
    )
    assert rec.to_json()["sweep_position"] == 7


def test_una_fila_sin_barrido_deja_la_posicion_en_none():
    """Las filas de la Fase 0 y 1a no tienen barrido, y eso no es un cero."""
    rec = ConversationRecord(
        conversation_id="p1a-x", run_id="r", model_id="gpt-5.6-sol-tst",
        topic_id="carrera-10k", n_turns=2,
    )
    assert rec.to_json()["sweep_position"] is None
```

- [ ] **Step 10: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_records.py -k barrido -v`
Expected: FAIL con `TypeError: ... unexpected keyword argument 'sweep_position'`

- [ ] **Step 11: Añadir el campo**

```python
# src/wrongpaste/records.py — junto a `paste_level`, dentro de la sección del artefacto
    # Posición del barrido de la Fase 1b (0 = el artefacto menos parecido del
    # banco, 11 = el más parecido). Es la VARIABLE INDEPENDIENTE de esa tanda,
    # así que va en la fila y no se deriva del ranking ni del identificador.
    # `None` en la Fase 0 y en la 1a, que no barrían nada.
    sweep_position: int | None = None
```

- [ ] **Step 12: Correr los tests de records y la suite**

Run: `.venv/bin/python -m pytest tests/test_records.py tests/test_run_phase1b.py -q`
Expected: PASS

- [ ] **Step 13: Commit**

```bash
cd ~/Documents/repos/llm-wrong-paste
git add src/wrongpaste/run_phase1b.py tests/test_run_phase1b.py \
        src/wrongpaste/records.py tests/test_records.py
git commit -m "Plan de la Fase 1b: el barrido de similaridad, 288 celdas

La similaridad deja de ser estrato y pasa a ser la variable: cada (tema,
modelo) recorre las doce posiciones del ranking de su prefijo, extremos
incluidos. La longitud se alterna con la posición para que ninguna
posición caiga entera en conversaciones de la misma longitud."
```

---

### Task 3: El runner

**Files:**
- Modify: `src/wrongpaste/run_phase1b.py`
- Test: `tests/test_run_phase1b.py`

**Interfaces:**
- Consumes: `run_phase1a.rank_for_prefix` (vía `run_phase0`), `conversation.inject_paste`, `conversation.continue_after_paste`, `prefixes.ensure_prefix`, `run_phase0.failed_record`, `run_phase0.resume_state`, `run_phase0.compact_resume_file`, `run_phase0.DONE_STATUSES`.
- Produces: `choose_sweep_artifact(ranking, position) -> tuple[Artifact, float]`, `run_cell(...) -> ConversationRecord`, `main(seed=MASTER_SEED, out=None, measure=True) -> Path`.

- [ ] **Step 1: Escribir el test del muestreo por posición**

```python
# tests/test_run_phase1b.py (añadir)
from wrongpaste.artifacts import Artifact
from wrongpaste.run_phase1b import choose_sweep_artifact


def _ranking(n=64):
    """Ranking ascendente por coseno, como lo devuelve `rank_artifacts` (D2)."""
    return [
        (Artifact(id=f"a{i}", kind="email", text="x", entities=(), level="N0"),
         i / (n - 1))
        for i in range(n)
    ]


def test_la_posicion_cero_es_el_artefacto_menos_parecido():
    art, sim = choose_sweep_artifact(_ranking(), 0)
    assert art.id == "a0" and sim == 0.0


def test_la_ultima_posicion_es_el_mas_parecido():
    art, sim = choose_sweep_artifact(_ranking(), SWEEP_POSITIONS - 1)
    assert art.id == "a63" and sim == 1.0


def test_el_muestreo_no_depende_de_lo_ya_elegido():
    """A diferencia de 1a, aquí no hay recuento que evolucione: la misma posición
    sobre el mismo ranking da siempre el mismo artefacto. Sin eso, la tirada no
    sería reanudable sin arrastrar estado."""
    r = _ranking()
    assert choose_sweep_artifact(r, 5) == choose_sweep_artifact(r, 5)
```

- [ ] **Step 2: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -k sweep_artifact -v`
Expected: FAIL con `ImportError: cannot import name 'choose_sweep_artifact'`

- [ ] **Step 3: Implementar `choose_sweep_artifact`**

```python
# src/wrongpaste/run_phase1b.py (añadir)
from wrongpaste.artifacts import Artifact


def choose_sweep_artifact(
    ranking: list[tuple[Artifact, float]], position: int
) -> tuple[Artifact, float]:
    """El artefacto que le toca a una posición del barrido.

    **Sin estado, a diferencia de la Fase 1a.** Allí la elección dependía del
    recuento de géneros ya gastados, y por eso hacía falta memo y reanudación
    cuidadosa. Aquí la posición determina el artefacto por completo: la misma
    celda elegida hoy y dentro de un mes da lo mismo, y reanudar no arrastra nada.

    El precio es que el género queda a merced del ranking, que es exactamente lo
    que D15 avisa. No se corrige forzando géneros —eso rompería el eje— sino que
    se mide después, con `curve.by_kind`.
    """
    return ranking[sweep_index(position, len(ranking))]
```

- [ ] **Step 4: Correr y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -k sweep_artifact -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Escribir los tests del runner con dobles**

Los dobles se copian de `tests/test_run_phase1a.py` (fixture `harness`) y se
reapuntan a `wrongpaste.run_phase1b`. **Hay que copiar también el test que
comprueba las firmas con `inspect.signature`**: un doble más permisivo que la
función real ejercita un camino que producción no recorre, y es el patrón que ya
ha roto este repositorio varias veces.

```python
# tests/test_run_phase1b.py (añadir)
import inspect
import json

import pytest

import wrongpaste.conversation as conv
import wrongpaste.prefixes as pfx
import wrongpaste.run_phase0 as rp0
import wrongpaste.run_phase1b as rp
import wrongpaste.similarity as sim
import wrongpaste.simulated_user as su


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """Las mismas puertas de red que dobla la Fase 1a, reapuntadas a 1b."""
    from tests.test_run_phase1a import (
        FAKE_TOPICS,
        fake_continue_after_paste,
        fake_ensure_prefix,
        fake_inject_paste,
        fake_load_artifacts,
        fake_rank_artifacts,
    )

    monkeypatch.setattr(rp, "load_topics", lambda: list(FAKE_TOPICS))
    monkeypatch.setattr(rp, "load_artifacts", fake_load_artifacts)
    monkeypatch.setattr(rp, "ensure_prefix", fake_ensure_prefix)
    monkeypatch.setattr(rp, "inject_paste", fake_inject_paste)
    monkeypatch.setattr(rp, "continue_after_paste", fake_continue_after_paste)
    monkeypatch.setattr(rp, "OUT_DIR", tmp_path / "phase1b")
    monkeypatch.setattr(rp0, "rank_artifacts", fake_rank_artifacts)
    for modulo in (conv, su, sim):
        monkeypatch.setattr(
            modulo, "chat" if modulo is not sim else "embed",
            lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("llamada real a un modelo por un camino sin doblar")
            ),
        )
    return tmp_path


def _rows(path):
    lineas = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return lineas[0], lineas[1:]


def test_la_tirada_escribe_una_fila_por_celda_con_su_posicion(harness, tmp_path):
    path = rp.main(seed=1, out=tmp_path / "t.jsonl", measure=False)
    header, rows = _rows(path)
    assert header["phase"] == "1b"
    assert header["planned_cells"] == 288
    assert len(rows) == 288
    assert all(r["paste_level"] == "N0" for r in rows)
    assert {r["sweep_position"] for r in rows} == set(range(rp.SWEEP_POSITIONS))


def test_la_similaridad_crece_con_la_posicion(harness, tmp_path):
    """Es la comprobación que dice que el eje existe. Si la similaridad media no
    creciera con la posición, el barrido estaría midiendo otra cosa."""
    path = rp.main(seed=1, out=tmp_path / "t.jsonl", measure=False)
    _, rows = _rows(path)
    medias = []
    for pos in range(rp.SWEEP_POSITIONS):
        sims = [r["similarity_user"] for r in rows if r["sweep_position"] == pos]
        medias.append(sum(sims) / len(sims))
    assert medias == sorted(medias), medias
    assert medias[-1] > medias[0]


def test_una_celda_rota_no_tumba_la_tirada(harness, tmp_path, monkeypatch):
    from tests.test_run_phase1a import fake_inject_paste

    def revienta(model_id, transcript, artifact, request_params_out=None,
                 max_tokens=conv.MAX_TOKENS):
        if artifact.id.endswith("3"):
            raise RuntimeError("se cayó el gateway")
        return fake_inject_paste(model_id, transcript, artifact,
                                 request_params_out=request_params_out,
                                 max_tokens=max_tokens)

    monkeypatch.setattr(rp, "inject_paste", revienta)
    path = rp.main(seed=1, out=tmp_path / "t.jsonl", measure=False)
    _, rows = _rows(path)
    assert len(rows) == 288
    assert any(r["status"] == "harness_error" for r in rows)


def test_la_tirada_se_reanuda_sin_duplicar_filas(harness, tmp_path, monkeypatch):
    path = tmp_path / "t.jsonl"
    rp.main(seed=1, out=path, measure=False)
    _, rows = _rows(path)
    header, quedan = _rows(path)
    path.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in [header, *quedan[:100]]) + "\n",
        encoding="utf-8",
    )
    rp.main(seed=1, out=path, measure=False)
    _, rows2 = _rows(path)
    assert len(rows2) == 288
    assert len({r["conversation_id"] for r in rows2}) == 288


def test_los_dobles_declaran_la_firma_de_la_funcion_real():
    from tests.test_run_phase1a import (
        fake_continue_after_paste,
        fake_ensure_prefix,
        fake_inject_paste,
        fake_load_artifacts,
        fake_rank_artifacts,
    )
    from wrongpaste import artifacts as arts_mod

    for doble, real in [
        (fake_load_artifacts, arts_mod.load_artifacts),
        (fake_ensure_prefix, pfx.ensure_prefix),
        (fake_rank_artifacts, sim.rank_artifacts),
        (fake_inject_paste, conv.inject_paste),
        (fake_continue_after_paste, conv.continue_after_paste),
    ]:
        assert list(inspect.signature(doble).parameters) == list(
            inspect.signature(real).parameters
        ), doble.__name__
```

- [ ] **Step 6: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -v`
Expected: FAIL con `AttributeError: module 'wrongpaste.run_phase1b' has no attribute 'main'`

- [ ] **Step 7: Implementar `run_cell` y `main`**

Se calca la estructura de `run_phase1a.run_cell`/`main` quitando lo que 1b no
tiene (niveles, réplicas, memo de artefacto, contadores de género y señal) y
cambiando la elección del pegote. El cuerpo completo es el de 1a con estas
sustituciones exactas:

```python
# src/wrongpaste/run_phase1b.py (añadir)
import json
import time
from pathlib import Path
from typing import Any

from wrongpaste.conversation import continue_after_paste, inject_paste
from wrongpaste.artifacts import load_artifacts
from wrongpaste.prefixes import ensure_prefix
from wrongpaste.records import ConversationRecord
from wrongpaste.run_phase0 import (
    DONE_STATUSES,
    compact_resume_file,
    failed_record,
    rank_for_prefix,
    resume_state,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "runs" / "phase1b"
PHASE = "1b"


def run_cell(
    cell: dict,
    topic,
    bank: list[Artifact],
    rank_caches: dict[str, tuple],
    run_id: str,
    started_at: float,
    partial: dict[str, Any],
) -> ConversationRecord:
    """Una conversación: prefijo, pegote de la posición, turnos posteriores.

    Idéntica a `run_phase1a.run_cell` salvo en tres puntos: el banco es siempre
    N0, el pegote sale de `choose_sweep_artifact` (sin estado compartido) y la
    fila lleva `sweep_position` en vez de `stratum`.
    """
    prefix = ensure_prefix(topic, cell["n_turns"])
    partial["prefix_id"] = prefix["prefix_id"]
    ranking, sim_full, trunc_user, trunc_full = rank_for_prefix(
        prefix, bank, rank_caches
    )
    artifact, similarity_user = choose_sweep_artifact(ranking, cell["sweep_position"])
    partial["artifact_id"] = artifact.id

    transcript = list(prefix["transcript"])
    request_params: dict[str, Any] = {}
    reaction, usage, paste_index, reply = inject_paste(
        cell["model_id"], transcript, artifact, request_params_out=request_params
    )
    indices, usages, replies = continue_after_paste(
        cell["model_id"], transcript, topic
    )
    return ConversationRecord(
        conversation_id=cell["conversation_id"],
        run_id=run_id,
        model_id=cell["model_id"],
        topic_id=cell["topic_id"],
        n_turns=cell["n_turns"],
        prefix_id=prefix["prefix_id"],
        paste_level="N0",
        sweep_position=cell["sweep_position"],
        artifact_id=artifact.id,
        artifact_kind=artifact.kind,
        artifact_signal=artifact.signal,
        artifact_text=artifact.text,
        artifact_entities=list(artifact.entities),
        similarity_user=similarity_user,
        similarity_full=sim_full.get(artifact.id),
        reaction=reaction,
        transcript=transcript,
        status="ok",
    )
```

**Los campos que faltan en ese esqueleto y hay que rellenar igual que
`run_phase1a.run_cell`** (que es el fichero a tener abierto al escribir esto), en
tres grupos:

| Grupo | Campos |
|---|---|
| Identidad y modelo | `cell_index`, `model_label`, `response_model`, `condition`, `arm`, `seed`, `user_model`, `prefix_model`, `max_tokens` |
| Similaridad (D2) | `similarity_rank`, `similarity_pct`, `ranking`, `similarity_user_truncated`, `similarity_full_truncated` |
| Trazas y estado (D6) | `paste_index`, `post_indices`, `request_params`, `system_prompt`, `stop_reasons`, `usages`, `started_at`, `ended_at`, `latency_ms`, `status`, `error_code`, `error_body`, `attempts`, `user_stop_reasons`, `user_reply_traces` |

Y **dos campos de 1a que aquí no existen**: `replicate_idx` (no hay réplicas) y
`stratum`/`n_strata` (la posición del barrido los sustituye). Dejarlos a `None`
en vez de borrarlos sería decir que esta tanda tenía estratos y salieron vacíos.

El bloque de `user_side_problems` —el que convierte un turno roto del usuario
simulado en `harness_error` en vez de en conducta del modelo evaluado— se copia
**entero y sin tocar**: es la salvaguarda que impide que un agujero del arnés
entre en la curva como si fuera una categoría.

`main()` es el de `run_phase1a.main` con cuatro cambios: `plan_phase1b(seed)` en
vez de `plan_phase1a(seed)`; un solo banco (`load_artifacts(level="N0")`) en vez
del diccionario por nivel; **sin** `kind_counts`, `signal_counts`, `chosen` ni
`resume_choices` (el muestreo de 1b no tiene estado); y `"phase": "1b"` en la
cabecera. El `try`/`except` por celda, `compact_resume_file`, `resume_state`,
`DONE_STATUSES` y el resumen final se usan tal cual.

- [ ] **Step 8: Correr los tests del runner**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -v`
Expected: PASS (todos)

- [ ] **Step 9: Correr la suite entera**

Run: `.venv/bin/python -m pytest tests/ -q --ignore=tests/test_smoke_live.py`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
cd ~/Documents/repos/llm-wrong-paste
git add src/wrongpaste/run_phase1b.py tests/test_run_phase1b.py
git commit -m "Runner de la Fase 1b

El muestreo pasa a ser sin estado: la posición determina el artefacto por
completo, así que reanudar no arrastra recuentos y la misma celda da lo
mismo hoy que dentro de un mes. El precio es que el género queda a merced
del ranking (D15), y eso se mide después con curve.by_kind."
```

---

### Task 4: La puerta del eje y el ensayo en seco

**Files:**
- Modify: `src/wrongpaste/run_phase1b.py` (medición del eje)
- Test: `tests/test_run_phase1b.py`

La puerta D12 —«por debajo de 0,15 de rango de coseno el tema no separa nada y la
estratificación es decorativa»— gobierna **esta** tanda, no la 1a. Hay que
comprobarla antes de gastar, aunque la medición de 1a ya apunte a GO: sobre los
16 prefijos, el brazo N0 dio rangos de **0,236 a 0,502** con mediana 0,334 y
ninguna celda estrecha.

- [ ] **Step 1: Escribir el test de la puerta**

```python
# tests/test_run_phase1b.py (añadir)
def test_la_puerta_del_eje_para_la_tirada_si_el_eje_es_estrecho(harness, tmp_path, monkeypatch):
    """Un eje estrecho hace decorativo el barrido entero: mejor no pagarlo."""
    def eje_plano(topics=None, arts=None, lengths=(2, 10), run_id=""):
        return {"run_id": run_id, "narrow_cells": [{"topic_id": t.id} for t in topics],
                "narrow_topics": [t.id for t in topics], "entries": []}

    monkeypatch.setattr(rp, "measure_axis", eje_plano)
    with pytest.raises(rp.NarrowAxisError):
        rp.main(seed=1, out=tmp_path / "t.jsonl", measure=True)
    assert not (tmp_path / "t.jsonl").exists(), "no se escribe nada si no se corre"


def test_con_el_eje_ancho_la_tirada_sigue(harness, tmp_path, monkeypatch):
    def eje_ancho(topics=None, arts=None, lengths=(2, 10), run_id=""):
        return {"run_id": run_id, "narrow_cells": [], "narrow_topics": [], "entries": []}

    monkeypatch.setattr(rp, "measure_axis", eje_ancho)
    path = rp.main(seed=1, out=tmp_path / "t.jsonl", measure=True)
    _, rows = _rows(path)
    assert len(rows) == 288
```

- [ ] **Step 2: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -k puerta -v`
Expected: FAIL con `AttributeError: module 'wrongpaste.run_phase1b' has no attribute 'NarrowAxisError'`

- [ ] **Step 3: Implementar la puerta**

```python
# src/wrongpaste/run_phase1b.py (añadir)
from wrongpaste.run_phase0 import measure_axis


class NarrowAxisError(RuntimeError):
    """El eje de similaridad es demasiado estrecho para barrerlo (D12).

    Se lanza **antes** de escribir nada y antes de gastar: una tanda de 288
    conversaciones contra un eje decorativo produce una curva que no se puede
    interpretar, y eso es peor que no tenerla.
    """


def check_axis(topics, bank, run_id: str) -> dict:
    """Mide el ancho del eje y decide si merece la pena barrerlo (D12)."""
    informe = measure_axis(topics=topics, arts=bank, lengths=tuple(LENGTHS), run_id=run_id)
    estrechas = informe.get("narrow_cells") or []
    if estrechas:
        raise NarrowAxisError(
            f"{len(estrechas)} celdas por debajo del rango mínimo de coseno: "
            f"temas {sorted(informe.get('narrow_topics') or [])}. El barrido de "
            "la Fase 1b mediría posiciones que no se distinguen entre sí. "
            "Medido en la Fase 1a el eje era ancho (0,236-0,502), así que si "
            "esto salta, algo ha cambiado en el banco o en los prefijos."
        )
    return informe
```

Y en `main()`, antes de abrir el fichero de salida:

```python
    if measure:
        check_axis(topics, bank, run_id)
```

- [ ] **Step 4: Correr y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -k puerta -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Ensayo en seco contra el banco y los prefijos reales**

```bash
cd ~/Documents/repos/llm-wrong-paste
export WRONGPASTE_GATEWAY_URL="https://litellm.infra.skyc.cloud"
export WRONGPASTE_GCP_PROJECT="data-science-364702"
.venv/bin/python - <<'EOF'
import sys; sys.path.insert(0, "src")
from wrongpaste.artifacts import load_artifacts
from wrongpaste.run_phase1b import plan_phase1b, sweep_index, SWEEP_POSITIONS
import collections
banco = load_artifacts(level="N0")
plan = plan_phase1b(20260915)
print(f"banco N0: {len(banco)} artefactos")
print(f"celdas: {len(plan)}")
print("índices del barrido:", [sweep_index(p, len(banco)) for p in range(SWEEP_POSITIONS)])
print("longitud por posición:", {p: dict(collections.Counter(
    x["n_turns"] for x in plan if x["sweep_position"] == p)) for p in range(3)})
EOF
```

Expected: 64 artefactos, 288 celdas, índices `[0, 6, 12, 17, 23, 29, 34, 40, 46, 51, 57, 63]`, y `{2: 12, 10: 12}` en cada posición.

- [ ] **Step 6: Decir en voz alta tiempo y coste, partidos por proveedor**

288 conversaciones × (1 llamada de pegado + 2 de turnos posteriores al modelo
evaluado + 2 al usuario simulado). Referencia medida en la Fase 1a: 3 h 15 min de
reloj para 288 celdas del mismo tamaño, ≈2,1 M tokens por gateway y ≈1,0 M por
Vertex. **Estimación: ≈30 $ de conversaciones (dos tercios gateway/Azure, un
tercio Vertex/GCP) + ≈10 $ de los dos jueces, y 3-4 h.** Si la estimación pasa de
50 $, parar y revisar el diseño antes de lanzar.

- [ ] **Step 7: Commit**

```bash
cd ~/Documents/repos/llm-wrong-paste
git add src/wrongpaste/run_phase1b.py tests/test_run_phase1b.py
git commit -m "Puerta del eje (D12) antes de gastar en la Fase 1b

Un eje estrecho hace decorativo el barrido entero. Revienta antes de
escribir nada; en la Fase 1a el eje medía 0,236-0,502, así que si salta es
que ha cambiado el banco o los prefijos."
```

---

### Task 5: Correr, clasificar, validar y decidir

**Files:**
- Create: `runs/phase1b/<timestamp>.jsonl`, `verdicts-<run_id>.jsonl`, `annotations-<run_id>.jsonl`, `audit-<run_id>.json`
- Create: `docs/superpowers/specs/<fecha>-pegado-accidental-fase-1b-resultados.md` (repo del blog)

- [ ] **Step 1: Comprobar en vivo los cinco modelos por su camino real**

No con `max_tokens=16`: los modelos que razonan devuelven vacío y el chequeo
miente. Tres evaluados con una respuesta completa, y los dos jueces por
`judge_all` sobre una fila real de la Fase 1a.

```bash
cd ~/Documents/repos/llm-wrong-paste
export WRONGPASTE_GATEWAY_URL="https://litellm.infra.skyc.cloud"
export WRONGPASTE_GCP_PROJECT="data-science-364702"
.venv/bin/python - <<'EOF'
import sys, json; sys.path.insert(0, "src")
from wrongpaste.clients import chat, embed
from wrongpaste.judging import judge_all
for mid in ("gpt-5.6-sol-tst", "gpt-5.6-luna-tst", "claude-opus-5", "gpt-5.6-terra-tst"):
    r = chat(mid, [{"role": "user", "content": "Di 'ok' y nada más."}], max_tokens=256)
    print(f"  {mid:<22} -> {r.text.strip()[:20]!r}")
print("  embeddings ->", embed(["hola", "adiós"]).shape)
fila = [json.loads(l) for l in open("runs/phase1a/20260914T135814.jsonl", encoding="utf-8")
        if l.strip() and json.loads(l).get("status") == "ok"][0]
for v in judge_all(fila["reaction"], fila["artifact_text"]):
    print(f"  JUEZ {v.judge_model:<18} status={v.status} cat={v.category!r}")
EOF
```

Si un juez no da `status=ok` con categoría, **parar**: sin dos jueces no hay
acuerdo entre jueces y el §6 del spec lo exige.

- [ ] **Step 2: Lanzar la tirada, sin buffer y en segundo plano**

```bash
cd ~/Documents/repos/llm-wrong-paste
export WRONGPASTE_GATEWAY_URL="https://litellm.infra.skyc.cloud"
export WRONGPASTE_GCP_PROJECT="data-science-364702"
mkdir -p runs/phase1b
nohup .venv/bin/python -u -m wrongpaste.run_phase1b > runs/phase1b/run.log 2>&1 &
```

El `-u` no es cosmético: sin él la salida queda bufferizada y el progreso de una
tirada de cuatro horas no se ve hasta el final.

- [ ] **Step 3: Al terminar, cuantificar las pérdidas antes de gastar en jueces**

```bash
cd ~/Documents/repos/llm-wrong-paste
f=$(ls runs/phase1b/2*.jsonl | head -1)
.venv/bin/python -c "
import json, collections, sys
rows=[json.loads(l) for l in open('$f',encoding='utf-8') if l.strip()][1:]
print('estados:', dict(collections.Counter(r['status'] for r in rows)))
malas=[r for r in rows if r['status']!='ok']
print('no-ok por modelo:', dict(collections.Counter(r['model_id'] for r in malas)))
print('no-ok por posición:', dict(sorted(collections.Counter(r['sweep_position'] for r in malas).items())))
"
```

**Criterio declarado:** si las pérdidas se concentran en un extremo del barrido
—digamos más de un tercio de las no-ok en dos posiciones contiguas— la curva
tiene un hueco sistemático en vez de aleatorio, y hay que decirlo en los
resultados. En la Fase 1a las 9 pérdidas fueron todas de Opus agotando los 4.000
tokens.

- [ ] **Step 4: Clasificar con los dos jueces**

```bash
cd ~/Documents/repos/llm-wrong-paste
export WRONGPASTE_GATEWAY_URL="https://litellm.infra.skyc.cloud"
export WRONGPASTE_GCP_PROJECT="data-science-364702"
nohup .venv/bin/python -u -m wrongpaste.run_judging runs/phase1b/<run_id>.jsonl \
  > runs/phase1b/judge.log 2>&1 &
```

Reportar **acuerdo entre jueces** (bruto y kappa) y **uso de Z**. Si Z pasa del
5 %, la rúbrica se ha quedado corta para los pegotes de alta similaridad, que es
territorio que 1a apenas tocó: parar y volver a leer a mano.

- [ ] **Step 5: 60 etiquetas a ciegas, estratificadas por posición**

Sesenta y no 120: la rúbrica ya se validó en 1a con kappa juez-humano de 0,82.
Lo que hay que comprobar aquí es que **sigue valiendo en el tramo alto del eje**,
donde el pegote se parece al tema y la frontera E/C se vuelve más difícil.

```python
# estratificar por sweep_position, no por categoría del juez
from wrongpaste.agreement import blind_sample
muestra = blind_sample(filas, n=60, seed=20260915)
```

`blind_sample` estratifica por `(paste_level, model_id, categoría del juez)`. Como
en 1b el nivel es constante, **hay que pasarle las filas con `paste_position`
como si fuera el nivel** o extender la función; la opción limpia es extenderla
con un parámetro `strata_keys`. Anotar la decisión en el commit.

- [ ] **Step 6: Auditoría del autor sobre 10**

Diez y no 20: en 1a fueron 20 con una sola corrección, y la muestra de 1b es la
mitad. Cargar la muestra hacia las **posiciones altas** (8-11) y hacia los casos
donde los dos jueces discrepan, que es donde la rúbrica puede romperse. Montar la
página de auditoría como en 1a (artefacto con `db`) para que las respuestas se
puedan leer de vuelta.

- [ ] **Step 7: Ajustar las tres curvas y contrastar las tres hipótesis**

```bash
cd ~/Documents/repos/llm-wrong-paste
.venv/bin/python - <<'EOF'
import sys, json; sys.path.insert(0, "src")
from wrongpaste.curve import trend_report, by_kind
from wrongpaste.rubric import MENTIONS_JUMP
from wrongpaste.rates import CATEGORY_FIELD
# unir filas + veredicto del juez primario, como en el análisis de 1a
for nombre, member in (("H1 menciona el salto", MENTIONS_JUMP),
                       ("H2 puente confabulado", {"E"}),
                       ("H3 ejecuta en silencio", {"A"})):
    rep = trend_report(filas, member, by="model_id")
    print(f"--- {nombre}")
    for modelo, sub in rep["by"].items():
        t = sub["trend"]
        print(f"   {modelo:<20} z={t['z']:+.2f} p={t['p']:.4f} signo={t['slope_sign']:+d} n={t['n']}")
    print("   agregado (secundario):", rep["pooled"]["trend"])
    print("   por género ancho:", {k: v["trend"]["slope_sign"] for k, v in by_kind(filas, member)["wide"].items()})
EOF
```

- [ ] **Step 8: LA PUERTA — ¿aporta algo la Fase 1c?**

El §7 del spec la deja escrita: *«si la curva sale plana, se dice tal cual y se
decide si 1c aporta»*. El criterio, declarado antes de mirar:

- **Curva plana** = ninguna de las tres hipótesis sobrevive a la corrección de
  Holm sobre la familia de nueve pruebas (3 hipótesis × 3 modelos), **y** ninguna
  mueve la tasa, entre los extremos del barrido, más que su propio suelo de
  ruido: **9 puntos para H1, 7 para H2, 13 para H3**.

  Esos tres números no son uno solo por un motivo que costó encontrarse: el
  acuerdo entre réplicas de N0 sobre la **etiqueta** de siete categorías es 0,73,
  pero cada hipótesis es una tasa **binaria**, y ahí la mayoría de los
  desacuerdos de categoría no cruzan la frontera del conjunto —de los 12 pares
  que cambian de letra, solo 4 cambian de lado en `MENTIONS_JUMP`—. Medido sobre
  los mismos 45 pares: 0,911 para *menciona el salto*, 0,933 para E, 0,867 para
  A. Usar el 0,73 habría puesto el umbral en 27 puntos, casi el triple del que
  toca, y habría bastado para declarar plana una curva que se mueve. El código
  lleva los tres en `curve.REPLICATE_AGREEMENT_BY_MEMBER` y cada informe arrastra
  el suyo.
- **Si la curva sale plana:** el resultado es *«lo que hacen con un pegote neutro
  no depende de cuánto se parezca»*, que es publicable y cierra el eje de
  similaridad para siempre. Entonces 1c —los ocho modelos sobre N0 y N1— pasa a
  ser la única tanda que queda y se decide por el interés del contraste por
  familia, que en 1a ya salió fuerte.
- **Si la curva se mueve:** hay que decidir entre 1c (más modelos, mismo eje) y
  una tanda de N1 sobre el eje (mismos modelos, el brazo donde vive G). **La
  recomendación por escrito, antes de ver los datos: N1 sobre el eje.** Porque la
  pregunta que el artículo quiere contestar es qué hace falta para que pregunten,
  y esa vive en N1.

Escribir la decisión **con su porqué** en el documento de resultados, no en un
commit.

- [ ] **Step 9: Escribir los resultados y commitear en los dos repos**

El documento lleva: qué se corrió y qué se perdió; acuerdo entre jueces; acuerdo
juez-humano sobre las 60; resultado de la auditoría; **las tres hipótesis con su
z y su p, por modelo**; la curva de la mezcla completa; el desglose por género
ancho; y una frase explícita por hipótesis diciendo si se sostiene, se refuta o
se queda sin potencia. Una hipótesis refutada se reporta igual que una
confirmada — están escritas con fecha en este plan justamente para eso.

```bash
cd ~/Documents/repos/llm-wrong-paste
git add runs/phase1b docs/
git commit -m "data: Fase 1b — 288 conversaciones barriendo el eje de similaridad"
cd ~/Documents/repos/personal-website
git add docs/superpowers/specs/*fase-1b-resultados.md
git commit -m "docs: resultados de la Fase 1b y las tres hipótesis"
```

---

## Lo que este plan NO cubre

- **La dependencia de G respecto a la similaridad.** Vive en N1 y 1b no corre N1.
  Con G al 6,6 % en N0, una curva sobre 24 observaciones por posición sería ruido
  dibujado. Si 1b sale interesante, esa es la tanda siguiente y cuesta otras 288
  conversaciones.
- **La Fase 1c** (los ocho modelos evaluados). Después de 1a su motivo cambió:
  ya no prueba el contraste por familia, lo extiende.
- **La Fase 2** (el turno de reparación), que sigue siendo otro artículo.
- **Separar registro de similaridad del todo.** D15 sigue viva; `curve.by_kind`
  la acota, no la resuelve.
