# Fase 4 — Las tareas y los oráculos de control

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fabricar por inyección de fallo las 24 tareas del experimento, con su conjunto de tests que deben fallar y los que deben seguir pasando, y los dos oráculos de control que demuestran que el circuito de medida no miente.

**Architecture:** Una tarea es un parche que rompe una función concreta, más los tests que ese parche debe poner en rojo (`fail_to_pass`) y los que debe dejar intactos (`pass_to_pass`). Los fallos genéricos se generan con un catálogo de mutaciones sobre el AST; los de dominio no se automatizan —el spec dice que son trabajo de diseño— pero sí se validan igual. Los oráculos son dos agentes falsos que recorren el pipeline entero sin gastar un token: el no-op no edita nada y debe dar 0%, el oráculo aplica el parche de referencia y debe dar 100%.

**Tech Stack:** Python 3.11+, LibCST, `ast`, pytest, Docker vía `acp.runners`.

**Spec:** [`../specs/2026-08-14-software-practices-for-coding-agents-design.md`](../specs/2026-08-14-software-practices-for-coding-agents-design.md), §3.3 (las tareas se generan), §3.3.1 (los dos estratos), §3.6 (pre-flight), §5.4.6 (oráculos), §5.4.7 (ninguna métrica depende de un juez).

**Fase 3:** [`../specs/2026-08-20-fase-3-resultados.md`](../specs/2026-08-20-fase-3-resultados.md). Las nueve transformaciones, verificadas.

## Alcance

Este plan cubre **la generación y validación de tareas y los oráculos**. No cubre el harness de
agente ni el baseline T0, que necesitan modelo y van en un plan aparte: sin ellos igualmente queda
software que funciona y que responde la pregunta más cara del pre-flight —si las tareas discriminan—
antes de gastar un céntimo en cómputo.

## Global Constraints

- **Una tarea es válida solo si falla los tests que debe y no otros** (§3.3). Verificado ejecutando,
  no leyendo.
- **Ninguna métrica depende de un juez** (§5.4.7): el resultado sale de los tests y de la traza.
- **Los tests de validación se ejecutan fuera del alcance del agente y no se tocan nunca** (§4.2).
- **12 genéricas y 12 de dominio**, equilibradas dentro de cada repo (§3.3.1).
- **Cada tarea de dominio lleva anotado cuántos ficheros hay que leer como mínimo** para poder juzgar
  que es un fallo: es la variable que une el estrato con la métrica de localización (§3.3.1).
- **TDD estricto**, commit por paso. Suite hoy en `439 passed`, tiene que quedar en verde.
- **Limpia**: clones borrados, contenedores `acp-*` fuera. Docker tiene ahora un techo de 6 GB.
- Comentarios en español, explicando **por qué**.

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `src/acp/tasks/models.py` | `Task`: el parche, los tests que debe romper y los que no |
| `src/acp/tasks/mutations.py` | Catálogo de fallos genéricos sobre el AST |
| `src/acp/tasks/inject.py` | Aplica una mutación a una función concreta |
| `src/acp/tasks/validate.py` | Comprueba que una tarea rompe lo que debe y nada más |
| `src/acp/oracles.py` | Los dos agentes falsos |
| `tasks/<repo>/*.json` | Las 24 tareas, fuera del código |

---

## Task 1: El modelo de una tarea

**Files:**
- Create: `src/acp/tasks/__init__.py`, `src/acp/tasks/models.py`
- Test: `tests/test_tasks_models.py`

**Interfaces:**
- Produces: `Task(task_id, repo, module, symbol, stratum, patch, fail_to_pass, pass_to_pass, min_files_to_judge)`; `Task.from_json` / `to_json`.

- [ ] **Step 1: Escribir el test que falla**

```python
from acp.tasks.models import Task

RAW = {
    "task_id": "python-stdnum-001",
    "repo": "python-stdnum",
    "module": "stdnum.mx.curp",
    "symbol": "get_gender",
    "stratum": "domain",
    "patch": "--- a\n+++ b\n",
    "fail_to_pass": ["stdnum/mx/curp.py::stdnum.mx.curp.get_gender"],
    "pass_to_pass": ["tests/test_mx_curp.doctest"],
    "min_files_to_judge": 2,
}


def test_a_task_survives_a_round_trip():
    assert Task.from_json(RAW).to_json() == RAW


def test_the_stratum_is_one_of_the_two_the_design_declares():
    """§3.3.1 parte las tareas en genéricas y de dominio, y el corte es lo que
    más probablemente cambie la lectura de la tabla principal. Un tercer valor
    por error tipográfico rompería ese corte sin avisar."""
    import pytest

    with pytest.raises(ValueError):
        Task.from_json({**RAW, "stratum": "generico"})


def test_a_task_without_tests_to_break_is_not_a_task():
    """Sin tests que distingan arreglado de roto no hay medida (§3.2.1)."""
    import pytest

    with pytest.raises(ValueError):
        Task.from_json({**RAW, "fail_to_pass": []})


def test_a_domain_task_must_say_how_many_files_it_takes_to_judge():
    """Es el puente entre el estrato y la métrica de localización (§3.3.1): un
    fallo de dominio que se juzga en una sola línea no sirve, aunque nadie lo
    detecte leyendo la función."""
    import pytest

    with pytest.raises(ValueError):
        Task.from_json({**RAW, "min_files_to_judge": 1})
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_tasks_models.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'acp.tasks'`

- [ ] **Step 3: Implementar**

`Task` como dataclass con validación en `from_json`: el estrato solo admite `"generic"` y `"domain"`;
`fail_to_pass` no puede estar vacío; y una tarea de dominio exige `min_files_to_judge >= 2`, con el
porqué en la docstring.

- [ ] **Step 4: Verde y commit**

```bash
.venv/bin/python -m pytest tests/test_tasks_models.py -v
git add src/acp/tasks tests/test_tasks_models.py
git commit -m "feat: a task is a patch plus the tests it must break"
```

---

## Task 2: El catálogo de fallos genéricos

Un fallo genérico se reconoce por patrón sin entender el código (§3.3.1). Se generan
programáticamente porque su forma es lo que importa, no su contenido.

**Files:**
- Create: `src/acp/tasks/mutations.py`
- Test: `tests/test_tasks_mutations.py`

**Interfaces:**
- Produces: `MUTATIONS: dict[str, Callable]`; `mutate(source: str, symbol: str, kind: str) -> str | None` (None si esa mutación no aplica a esa función).

- [ ] **Step 1: Escribir el test que falla**

```python
from acp.tasks.mutations import MUTATIONS, mutate

SOURCE = '''\
def clasificar(valor, limite):
    if valor > limite:
        return "alto"
    return "bajo"
'''


def test_the_catalogue_covers_the_forms_the_design_names():
    """§3.3.1 los enumera: condición invertida, off-by-one, comprobación de nulo
    que falta, argumento cambiado de orden. Repartir el set entre formas
    distintas es lo que impide que mida una sola habilidad."""
    assert {"invert_condition", "off_by_one", "drop_none_check", "swap_args"} <= set(MUTATIONS)


def test_inverting_a_condition_changes_the_program():
    mutated = mutate(SOURCE, "clasificar", "invert_condition")

    assert mutated is not None
    espacio: dict = {}
    exec(compile(mutated, "m.py", "exec"), espacio)
    assert espacio["clasificar"](10, 5) == "bajo"


def test_a_mutation_that_does_not_apply_returns_none():
    """Una función sin comparaciones no admite off-by-one. Devolver el fuente
    intacto haría creer que hay tarea donde no la hay, y la validación lo
    descubriría más tarde y más caro."""
    assert mutate("def f(x):\n    return x\n", "f", "off_by_one") is None


def test_the_mutation_only_touches_the_named_symbol():
    source = SOURCE + "\n\ndef otra(a, b):\n    if a > b:\n        return 1\n    return 0\n"

    mutated = mutate(source, "clasificar", "invert_condition")

    assert "def otra(a, b):\n    if a > b:" in mutated


def test_the_result_still_compiles():
    for kind in MUTATIONS:
        mutated = mutate(SOURCE, "clasificar", kind)
        if mutated is not None:
            compile(mutated, "m.py", "exec")
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_tasks_mutations.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'acp.tasks.mutations'`

- [ ] **Step 3: Implementar**

Cada mutación es un `cst.CSTTransformer` que actúa **solo dentro de la función nombrada**:
`invert_condition` cambia el operador de comparación por su contrario; `off_by_one` suma o resta 1 a
un literal entero de una comparación; `drop_none_check` elimina una guarda `if x is None: return`;
`swap_args` intercambia dos argumentos posicionales de una llamada. Si el patrón no aparece, devuelve
`None`.

- [ ] **Step 4: Verde y commit**

```bash
.venv/bin/python -m pytest tests/test_tasks_mutations.py -v
git add src/acp/tasks/mutations.py tests/test_tasks_mutations.py
git commit -m "feat: a catalogue of failures you can spot by shape"
```

---

## Task 3: Validar que una tarea discrimina

Es el requisito duro del spec: la tarea tiene que hacer fallar **un conjunto concreto de tests y no
otros** (§3.3). Sin esto, una tarea que no rompe nada se contaría como resuelta siempre, y una que
rompe media suite mediría otra cosa.

**Files:**
- Create: `src/acp/tasks/validate.py`
- Test: `tests/test_tasks_validate.py`, `tests/test_tasks_integration.py`

**Interfaces:**
- Consumes: `run_suite_in_docker`, `Task`.
- Produces: `ValidationReport(valid, fail_to_pass_ok, pass_to_pass_ok, unexpected_failures)`;
  `validate_task(repo: Path, task: Task, timeout: int) -> ValidationReport`.

- [ ] **Step 1: Escribir el test de la parte pura**

```python
from acp.tasks.validate import compare_runs


def test_a_task_is_valid_when_it_breaks_exactly_what_it_should():
    report = compare_runs(
        before={"t_a": "passed", "t_b": "passed", "t_c": "passed"},
        after={"t_a": "failed", "t_b": "passed", "t_c": "passed"},
        fail_to_pass=["t_a"],
    )

    assert report.valid is True


def test_a_task_that_breaks_more_than_it_declares_is_not_valid():
    """Una tarea que tumba media suite no mide si el agente arregló el fallo:
    mide si sobrevivió al desastre."""
    report = compare_runs(
        before={"t_a": "passed", "t_b": "passed"},
        after={"t_a": "failed", "t_b": "failed"},
        fail_to_pass=["t_a"],
    )

    assert report.valid is False
    assert report.unexpected_failures == ["t_b"]


def test_a_task_that_breaks_nothing_is_not_a_task():
    report = compare_runs(
        before={"t_a": "passed"},
        after={"t_a": "passed"},
        fail_to_pass=["t_a"],
    )

    assert report.valid is False


def test_the_tests_that_already_failed_are_not_held_against_the_task():
    """Un test roto en el repo original no lo rompió la tarea, y exigir que
    pase dejaría fuera tareas buenas por un defecto ajeno."""
    report = compare_runs(
        before={"t_a": "passed", "t_flaky": "failed"},
        after={"t_a": "failed", "t_flaky": "failed"},
        fail_to_pass=["t_a"],
    )

    assert report.valid is True
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_tasks_validate.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'acp.tasks.validate'`

- [ ] **Step 3: Implementar la parte pura**

`compare_runs` compara los dos diccionarios de resultado por test: los de `fail_to_pass` tienen que
pasar de `passed` a `failed`; cualquier otro que pase de `passed` a `failed` es una
`unexpected_failure`; los que ya fallaban antes se ignoran.

Hace falta además leer el resultado **por test** de pytest, no solo el resumen: usa
`--report-log` o `-v` con parseo, decide y déjalo escrito. El resumen actual (`parse_pytest_summary`)
da totales, y aquí se necesita el detalle.

- [ ] **Step 4: Escribir el test de integración**

```python
# tests/test_tasks_integration.py
"""Valida una tarea contra un repo real. Necesita Docker y red."""
pytestmark = [pytest.mark.integration, pytest.mark.docker]


def test_an_injected_failure_breaks_exactly_its_own_tests(tmp_path):
    """python-stdnum es el más barato del sustrato (96 s por corrida), que es lo
    que hace viable validar 24 tareas."""
    clone = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", "--depth", "1",
         "https://github.com/arthurdejong/python-stdnum", str(clone)],
        check=True, capture_output=True,
    )

    task = inject(clone, module="stdnum.iso7064.mod_97_10", symbol="checksum",
                  kind="off_by_one")
    report = validate_task(clone, task, timeout=1800)

    assert report.valid is True, report.unexpected_failures
```

- [ ] **Step 5: Ejecutar, ver pasar y commit**

Run: `.venv/bin/python -m pytest tests/test_tasks_integration.py -v`
Expected: PASS, unos 4 minutos (dos corridas de suite).

```bash
git add src/acp/tasks/validate.py tests/test_tasks_validate.py tests/test_tasks_integration.py
git commit -m "feat: a task that breaks more than it declares is not a task"
```

---

## Task 4: Los oráculos de control

Dos agentes falsos que recorren el pipeline entero sin gastar un token (§5.4.6). Es la comprobación
más barata del diseño y la que atrapa los errores más caros: los que hacen que una transformación
rota se lea exactamente igual que un agente que fracasa.

**Files:**
- Create: `src/acp/oracles.py`
- Test: `tests/test_oracles.py`, `tests/test_oracles_integration.py`

**Interfaces:**
- Produces: `no_op(repo: Path, task: Task) -> None`; `oracle(repo: Path, task: Task) -> None` (aplica el parche de referencia traducido a la condición); `run_oracle(kind, repo, task, timeout) -> SuiteMetrics`.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_the_no_op_changes_nothing(tmp_path):
    """Debe dar 0% en todas las condiciones. Si da más, hay tareas cuyos tests
    no discriminan (§5.4.6)."""
    ...
    antes = snapshot(tmp_path)
    no_op(tmp_path, task)
    assert snapshot(tmp_path) == antes


def test_the_oracle_restores_what_the_task_broke(tmp_path):
    """Debe dar 100% en todas. Si da menos, o la transformación rompió el repo,
    o el mapa de identidad de símbolos está mal."""
    ...
    inject_into(tmp_path, task)
    oracle(tmp_path, task)
    assert (tmp_path / "pkg" / "core.py").read_text(encoding="utf-8") == original


def test_the_oracle_finds_the_symbol_even_after_a_rename(tmp_path):
    """Con A2 el símbolo se llama distinto y con B1 vive en otro fichero: el
    oráculo tiene que localizarlo por el mapa de identidad, no por su nombre."""
    ...
```

Complétalos con el andamiaje real; el patrón de fixtures ya existe en `tests/test_transforms_*.py`.

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_oracles.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'acp.oracles'`

- [ ] **Step 3: Implementar**

El no-op es trivial pero **no es inútil**: recorre el pipeline entero, así que detecta que una tarea
tiene tests que no discriminan.

El oráculo es el difícil: aplica el parche de referencia **traducido a la condición**. En T0 basta
con el parche; con A2 el símbolo tiene otro nombre y con B1/B2/B5 vive en otro fichero, así que hay
que localizarlo con el manifiesto de procedencia —que para eso guarda la identidad original— y
aplicar el cambio ahí. Si el manifiesto no encuentra el símbolo, el oráculo **falla ruidosamente**:
significa que la condición no es medible, y es mejor saberlo aquí que a mitad de campaña.

- [ ] **Step 4: Test de integración sobre una condición transformada**

```python
def test_the_oracle_scores_a_hundred_percent_on_a_transformed_tree(tmp_path):
    """Se corre antes de cada bloque, no una sola vez al principio (§5.4.6)."""
    # clonar python-stdnum, inyectar la tarea, transformar con A2, y comprobar
    # que el oráculo localiza el símbolo renombrado y deja la suite verde.
```

- [ ] **Step 5: Verde y commit**

```bash
.venv/bin/python -m pytest tests/test_oracles.py tests/test_oracles_integration.py -v
git add src/acp/oracles.py tests/test_oracles*.py
git commit -m "feat: two fake agents that prove the circuit does not lie"
```

---

## Task 5: Generar y validar las 24 tareas

No escribe código nuevo: produce el entregable.

**Files:**
- Create: `tasks/<repo>/*.json`
- Create: `docs/superpowers/specs/2026-08-XX-fase-4-resultados.md` en `personal-website`

- [ ] **Step 1: Generar las 12 genéricas**

Cuatro por repo sobre los tres finalistas, repartidas entre las formas del catálogo para que el set
no mida una sola habilidad. Validar cada una: si no discrimina, se descarta y se genera otra.

- [ ] **Step 2: Escribir las 12 de dominio**

Es trabajo de diseño y no se automatiza (§3.3.1). El material está en la inspección de la fase 0
(§6 de `2026-08-14-fase-0-resultados.md`): `curp.get_gender` con el mapeo H→M invertido,
`iso11649.validate` con la rotación cambiada, `_parse_generated_as_identity` con STORED/VIRTUAL al
revés, `burmese._get_start_date` con los días de watat intercambiados. Cada una con su
`min_files_to_judge` anotado.

- [ ] **Step 3: Validar el estrato de dominio por aislamiento** (§3.6.2b)

A cada tarea de dominio se le pasa al modelo **solo la función modificada, fuera de contexto**,
preguntando si contiene un fallo. Si lo detecta, no es de dominio: se descarta o se reclasifica. Es
el filtro que impide que el estrato se llene de bugs genéricos disfrazados, que es el modo de fallo
más probable al fabricarlos.

- [ ] **Step 4: Correr los dos oráculos sobre las 24**

El no-op tiene que dar 0% y el oráculo 100%. Cualquier desviación es un defecto del circuito de
medida, no de las tareas.

- [ ] **Step 5: Escribir el documento de resultados**

Con la tabla de las 24, el reparto por repo y estrato, cuántas se descartaron y por qué, y el
resultado de los oráculos.

---

## Checkpoint

Con esto, del pre-flight §3.6 quedan los puntos 5 y 6: que el baseline T0 sea discriminante y que los
modelos estén disponibles en Azure. Los dos necesitan el harness de agente, que va en el plan
siguiente.

Y una pregunta que solo se puede contestar aquí: **si el filtro de aislamiento descarta muchas de las
12 tareas de dominio**, el estrato es más difícil de fabricar de lo que el spec supone, y hay que
decidir si se rebaja el número o se acepta un set desequilibrado — antes de construir el harness, no
después.
