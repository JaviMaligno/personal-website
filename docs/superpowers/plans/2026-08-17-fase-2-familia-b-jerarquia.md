# Fase 2 — Familia B: mover cosas de sitio (B2, B3, B4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la infraestructura que permite mover código de sitio sin perder la identidad de los símbolos, y con ella las tres transformaciones de familia B que no parten módulos: jerarquía (B2), documentación de repo (B3) y tests visibles (B4).

**Architecture:** Dos piezas nuevas de núcleo antes que las transformaciones. La primera: el entorno instala las **dependencias** del repo, no el repo, porque aplanar la jerarquía invalida una instalación editable (§5.6 del spec) — el árbol se pone al alcance de pytest por ruta. La segunda: `TransformResult` gana un mapa de **movimientos** símbolo→módulo destino, y el mapa de identidad lo sigue; hoy `relocate_symbols` empareja por posición **dentro de cada módulo**, y la familia B mueve los símbolos **entre** módulos, así que sin esto el mapa se vacía en cuanto B2 toca el árbol.

**Tech Stack:** Python 3.11+, LibCST, `ast`, pytest, Docker vía `acp.runners`.

**Spec:** [`../specs/2026-08-14-software-practices-for-coding-agents-design.md`](../specs/2026-08-14-software-practices-for-coding-agents-design.md), §4.2 (familia B), §5.4.2 (localización por símbolo), §5.6 (aislamiento y el nombre del paquete raíz).

**Fase 1:** [`../specs/2026-08-17-fase-1-resultados.md`](../specs/2026-08-17-fase-1-resultados.md). Familia A verificada, 12/12 celdas equivalentes.

## Alcance

Este plan cubre **B2, B3 y B4** más la infraestructura que las tres necesitan. **B1 (cohesión) y B5
(tamaño) quedan para un plan aparte**: son las que parten y fusionan módulos, lo que añade colisiones
de nombres entre definiciones que acaban en el mismo espacio, y conviene atacarlas con la
infraestructura de movimientos ya verificada sobre B2.

Al terminar este plan existe la condición T2 parcial y se puede medir el eje que la fase 0 dejó en el
aire: B2 sobre pint, el único finalista con jerarquía profunda.

## Global Constraints

- **El nombre del paquete raíz no se transforma nunca** (§5.6). B2 aplana lo que hay **dentro** del
  paquete; el directorio del paquete sobrevive, porque es lo único que mantiene válidos a la vez los
  imports desde fuera y el comando de test.
- **Alcance repo-wide, tests del repo incluidos** (§4.3.1): usar `iter_transformable_files`, nunca
  `iter_source_files`.
- **Solo símbolos resolubles estáticamente** (§4.3.3).
- **Una copia de repo viva por condición**, borrada al cerrar (§2). El original nunca se transforma.
- **El árbol transformado no lleva `.git`** y por eso puede necesitar
  `SETUPTOOLS_SCM_PRETEND_VERSION` (ya implementado en `acp.suite.needs_pretend_version`).
- **TDD estricto**: test que falla y se ve fallar, implementación mínima, verde, commit por paso.
- **Nada de suites en paralelo.** Los tests que necesiten Docker llevan `integration` y `docker`.
- Comentarios en español, explicando **por qué**.

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `src/acp/suite.py` | Modo "dependencias, no repo" en la preparación del entorno |
| `src/acp/symbols.py` | `relocate_symbols` sigue movimientos entre módulos |
| `src/acp/transforms/base.py` | `TransformResult.moves` |
| `src/acp/transforms/b3_repo_docs.py` | Borra README, `docs/` y docstrings de módulo |
| `src/acp/transforms/b4_tests.py` | Saca la suite del alcance del agente |
| `src/acp/transforms/b2_hierarchy.py` | Aplana directorios y renombra ficheros |
| `tests/test_transforms_b*.py` | Un fichero por transformación |
| `tests/test_equivalence_family_b.py` | Matriz de equivalencia, marcada `docker` |

---

## Task 1: Instalar las dependencias, no el repo

Hoy la preparación hace `pip install -e .`. B2 destruye la estructura que declara el `pyproject`, así
que la instalación editable dejaría de encontrar sus paquetes y **la condición se leería como un
fracaso total del agente cuando es fontanería rota** (§5.6).

**Files:**
- Modify: `src/acp/suite.py`
- Test: `tests/test_suite_env.py`, `tests/test_docker_integration.py`

**Interfaces:**
- Produces: `declared_dependencies(repo: Path) -> list[str]`; `install_and_collect(..., install_repo: bool = True)`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_suite_env.py
def test_declared_dependencies_are_read_without_installing_the_project(tmp_path):
    """Aplanar la jerarquía invalida una instalación editable (§5.6), así que
    hace falta poder instalar lo que el repo necesita sin instalarlo a él."""
    from acp.suite import declared_dependencies

    write_pyproject(
        tmp_path,
        '[project]\nname = "demo"\nversion = "0.1.0"\n'
        'dependencies = ["requests>=2", "click"]\n\n'
        '[project.optional-dependencies]\ntest = ["pytest", "hypothesis"]\n',
    )

    assert declared_dependencies(tmp_path) == ["click", "hypothesis", "pytest", "requests>=2"]


def test_only_test_extras_count_as_dependencies(tmp_path):
    from acp.suite import declared_dependencies

    write_pyproject(
        tmp_path,
        '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["click"]\n\n'
        '[project.optional-dependencies]\ndocs = ["sphinx"]\n',
    )

    assert declared_dependencies(tmp_path) == ["click"]


def test_dependency_groups_count_too(tmp_path):
    from acp.suite import declared_dependencies

    write_pyproject(
        tmp_path,
        '[project]\nname = "demo"\nversion = "0.1.0"\n\n'
        '[dependency-groups]\ntest = ["pytest"]\n',
    )

    assert declared_dependencies(tmp_path) == ["pytest"]
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

Run: `.venv/bin/python -m pytest tests/test_suite_env.py -k declared_dependencies -v`
Expected: FAIL con `ImportError: cannot import name 'declared_dependencies'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/suite.py
def declared_dependencies(repo: Path) -> list[str]:
    """Lo que el repo necesita para correr su suite, sin instalarlo a él.

    Se usa cuando la transformación ha destruido la estructura que el
    `pyproject` declara —B2 aplana los directorios— y una instalación editable
    ya no encontraría sus paquetes. El árbol se pone al alcance de pytest por
    ruta, así que ninguna transformación puede invalidar el entorno (§5.6).
    """
    config = _read_pyproject(repo)
    project = config.get("project", {})
    found = set(project.get("dependencies", []))

    extras = project.get("optional-dependencies", {})
    for name in TEST_EXTRAS:
        found.update(extras.get(name, []))

    groups = config.get("dependency-groups", {})
    for name in TEST_EXTRAS:
        found.update(item for item in groups.get(name, []) if isinstance(item, str))

    return sorted(found)
```

- [ ] **Step 4: Ejecutar el test y verlo pasar**

Run: `.venv/bin/python -m pytest tests/test_suite_env.py -k "declared_dependencies or extras_count or groups_count" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/suite.py tests/test_suite_env.py
git commit -m "feat: read what a repo needs without installing the repo"
```

- [ ] **Step 6: Escribir el test de integración que falla**

```python
# tests/test_docker_integration.py
FLATTENED = """\
[project]
name = "demo"
version = "0.1.0"

[project.optional-dependencies]
test = ["pytest"]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["demo", "demo.inner"]
"""


def test_a_repo_whose_declared_layout_no_longer_exists_still_runs(tmp_path: Path):
    """La forma que deja B2: el pyproject declara `demo.inner`, que ya no está
    porque la jerarquía se aplanó. Instalar el repo falla; instalar solo sus
    dependencias y alcanzar el árbol por ruta, no."""
    (tmp_path / "pyproject.toml").write_text(FLATTENED, encoding="utf-8")
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "__init__.py").write_text("VALUE = 42\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_ok.py").write_text(
        "import demo\n\n\ndef test_value():\n    assert demo.VALUE == 42\n", encoding="utf-8"
    )

    result = run_suite_in_docker(tmp_path, timeout=900, install_repo=False)

    assert result.install_ok is True, result.install_error
    assert result.passed == 1
```

- [ ] **Step 7: Ejecutarlo y verlo fallar**

Run: `.venv/bin/python -m pytest -m docker -k no_longer_exists -v`
Expected: FAIL con `TypeError: run_suite_in_docker() got an unexpected keyword argument 'install_repo'`

- [ ] **Step 8: Implementar el modo**

En `install_and_collect`, cuando `install_repo` es falso, sustituir la instalación editable por la de
las dependencias declaradas, y poner el árbol al alcance de pytest por ruta en vez de por
instalación:

```python
    if install_repo:
        code, output, timed_out = _run(runner.wrap(installer(["-e", "."])), repo, timeout)
        if code != 0 or timed_out:
            metrics.install_error = f"install -e .: {output[-800:]}"
            metrics.timed_out = timed_out
            metrics.install_seconds = time.monotonic() - started
            return metrics
    else:
        dependencies = declared_dependencies(repo)
        if dependencies:
            code, output, timed_out = _run(runner.wrap([*pip, *dependencies]), repo, timeout)
            if code != 0 or timed_out:
                metrics.install_error = f"install deps: {output[-800:]}"
                metrics.timed_out = timed_out
                metrics.install_seconds = time.monotonic() - started
                return metrics
    metrics.install_ok = True
```

Y el comando de pytest se lanza con el árbol en `PYTHONPATH`. Como `_run` no acepta entorno, se
envuelve igual que la versión fingida:

```python
def _pytest_command(runner, args: list[str], install_repo: bool) -> list[str]:
    """Con el repo sin instalar, pytest tiene que encontrarlo por ruta."""
    command = [runner.python, "-m", "pytest", *args]
    if install_repo:
        return command
    return [
        "sh", "-lc",
        "PYTHONPATH=. " + " ".join(shlex.quote(part) for part in command),
    ]
```

`run_suite_in_docker`, `run_suite_in_venv` y `run_prepared_suite` propagan `install_repo`, y
`_restore_tree_under_test` se salta la reinstalación editable cuando no se instaló el repo — no hay
editable que restaurar, y el árbol está bajo prueba por ruta.

- [ ] **Step 9: Ejecutar y ver pasar**

Run: `.venv/bin/python -m pytest -m docker -k no_longer_exists -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add src/acp/suite.py tests/test_docker_integration.py
git commit -m "feat: run a repo whose declared layout no longer exists"
```

---

## Task 2: El mapa de símbolos sigue movimientos

`relocate_symbols` empareja las definiciones **dentro de cada módulo**, por posición estructural. La
familia B mueve los símbolos **entre** módulos: en cuanto B2 renombra `stdnum/es/nif.py` a
`stdnum/m17.py`, el módulo original no existe y **todos sus símbolos se caen del mapa**. Sin mapa no
hay métrica de localización, que es la hipótesis medida directamente (§5.4.2).

**Files:**
- Modify: `src/acp/transforms/base.py`, `src/acp/symbols.py`, `src/acp/cli.py`
- Test: `tests/test_symbols.py`

**Interfaces:**
- Consumes: `Location`, `build_symbol_map`, `relocate_symbols`.
- Produces: `TransformResult.moves: dict[str, str]` (módulo original → módulo destino);
  `relocate_symbols(symbols, root, moves: dict[str, str] | None = None)`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_symbols.py
def test_a_symbol_that_changed_module_keeps_its_identity(tmp_path: Path):
    """B2 renombra los ficheros: sin seguir el movimiento, el módulo original no
    existe en el árbol transformado y sus símbolos se caen del mapa entero."""
    original = tmp_path / "before"
    (original / "pkg" / "es").mkdir(parents=True)
    (original / "pkg" / "es" / "nif.py").write_text(
        "def validate(number):\n    return number\n", encoding="utf-8"
    )
    symbols = build_symbol_map(original)

    after = tmp_path / "after"
    (after / "pkg").mkdir(parents=True)
    (after / "pkg" / "m17.py").write_text(
        "def validate(number):\n    return number\n", encoding="utf-8"
    )

    relocated = relocate_symbols(symbols, after, moves={"pkg.es.nif": "pkg.m17"})

    assert relocated["pkg.es.nif.validate"].path == "pkg/m17.py"
    assert relocated["pkg.es.nif.validate"].current_name == "validate"


def test_without_a_move_a_vanished_module_still_drops_out(tmp_path: Path):
    """Lo que no se puede verificar contra el árbol que ve el agente no se
    publica: un rango inventado es peor que ningún rango."""
    original = tmp_path / "before"
    (original / "pkg").mkdir(parents=True)
    (original / "pkg" / "core.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    symbols = build_symbol_map(original)

    after = tmp_path / "after"
    (after / "pkg").mkdir(parents=True)

    assert relocate_symbols(symbols, after) == {}
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_symbols.py -k "changed_module or vanished" -v`
Expected: FAIL con `TypeError: relocate_symbols() got an unexpected keyword argument 'moves'`

- [ ] **Step 3: Implementación mínima**

En `base.py`, añadir el campo:

```python
@dataclass
class TransformResult:
    files_changed: int = 0
    renames: dict[str, str] = field(default_factory=dict)
    # Módulo original → módulo destino. Viaja con el resultado por la misma
    # razón que `renames`: el mapa de identidad tiene que poder seguir dónde
    # acabó cada símbolo, y solo la transformación sabe qué movió.
    moves: dict[str, str] = field(default_factory=dict)
```

En `symbols.py`, aplicar el movimiento antes de emparejar:

```python
def relocate_symbols(
    symbols: dict[str, Location],
    root: Path,
    moves: dict[str, str] | None = None,
) -> dict[str, Location]:
    moves = moves or {}
    current = _definitions_by_module(root)
    relocated: dict[str, Location] = {}
    for module, entries in _grouped_by_module(symbols).items():
        # El módulo donde hay que ir a buscar ahora, que puede no ser el suyo.
        found = current.get(moves.get(module, module), {})
        ...
```

El resto del cuerpo no cambia.

Y en `cli.py`, acumular los movimientos igual que los renombrados:

```python
    moves: dict[str, str] = {}
    for name in _application_order(transform_ids):
        result = TRANSFORMS[name](root)
        renames.update(result.renames)
        moves.update(result.moves)

    symbols = relocate_symbols(symbols, root, moves)
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_symbols.py -v`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add src/acp/symbols.py src/acp/transforms/base.py src/acp/cli.py tests/test_symbols.py
git commit -m "feat: follow a symbol that moved to another module"
```

---

## Task 3: B3 — documentación de repo

**Files:**
- Create: `src/acp/transforms/b3_repo_docs.py`
- Modify: `src/acp/transforms/__init__.py`
- Test: `tests/test_transforms_b3.py`

**Interfaces:**
- Produces: `apply(root: Path) -> TransformResult`, registrada como `"B3"`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_transforms_b3.py
from pathlib import Path

from acp.transforms import b3_repo_docs

MODULE = '''\
"""Validación de identificadores españoles."""

import os  # sobrevive: eso es A4


def validate(number):
    """Sobrevive: la docstring de función es A4, no B3."""
    return number
'''


def build(root: Path) -> Path:
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    path = pkg / "core.py"
    path.write_text(MODULE, encoding="utf-8")
    (root / "README.md").write_text("# demo\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "guide.md").write_text("guía\n", encoding="utf-8")
    return path


def test_the_readme_and_the_docs_directory_are_gone(tmp_path: Path):
    build(tmp_path)

    b3_repo_docs.apply(tmp_path)

    assert not (tmp_path / "README.md").exists()
    assert not (tmp_path / "docs").exists()


def test_module_docstrings_are_gone(tmp_path: Path):
    path = build(tmp_path)

    b3_repo_docs.apply(tmp_path)

    assert "Validación de identificadores" not in path.read_text(encoding="utf-8")


def test_function_docstrings_and_comments_survive(tmp_path: Path):
    """El reparto que sostiene el contraste del experimento: lo que te dice qué
    fichero abrir es B3; lo que te explica lo que ya has abierto es A4."""
    path = build(tmp_path)

    b3_repo_docs.apply(tmp_path)

    source = path.read_text(encoding="utf-8")
    assert "Sobrevive: la docstring de función es A4" in source
    assert "# sobrevive: eso es A4" in source


def test_a_module_whose_body_is_only_a_docstring_still_compiles(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir(parents=True)
    path = pkg / "empty.py"
    path.write_text('"""Solo esto."""\n', encoding="utf-8")

    b3_repo_docs.apply(tmp_path)

    compile(path.read_text(encoding="utf-8"), "empty.py", "exec")


def test_a_doctest_in_a_module_docstring_survives(tmp_path: Path):
    """Misma razón que en A4: en python-stdnum los doctests son media suite, y
    borrarlos haría fallar la verificación de equivalencia por construcción."""
    pkg = tmp_path / "pkg"
    pkg.mkdir(parents=True)
    path = pkg / "core.py"
    path.write_text('"""Doc.\n\n>>> 1 + 1\n2\n"""\n', encoding="utf-8")

    b3_repo_docs.apply(tmp_path)

    assert ">>> 1 + 1" in path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_b3.py -v`
Expected: FAIL con `ImportError: cannot import name 'b3_repo_docs'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/transforms/b3_repo_docs.py
from __future__ import annotations

import shutil
from pathlib import Path

import libcst as cst

from acp.metrics.size import read_source
from acp.transforms.a4_docs import docstring_literal, only_doctests
from acp.transforms.base import TransformResult, iter_transformable_files

README_NAMES = ("README.md", "README.rst", "README.txt", "README")
DOCS_DIRS = ("docs", "doc")


class _StripModuleDocstring(cst.CSTTransformer):
    """Quita la docstring de módulo y nada más.

    Es lo que dice qué hay en el fichero, o sea qué fichero abrir: por eso es B3
    y no A4. Conserva los bloques de doctest por la misma razón que A4 — en
    python-stdnum son media suite.
    """

    def leave_Module(self, original: cst.Module, updated: cst.Module) -> cst.Module:
        if not updated.body:
            return updated
        literal = docstring_literal(updated.body[0])
        if literal is None:
            return updated
        kept = only_doctests(literal)
        remaining = list(updated.body[1:])
        if kept is None:
            return updated.with_changes(body=remaining)
        return updated.with_changes(
            body=[literal.with_changes(body=[cst.Expr(value=kept)]), *remaining]
        )


def apply(root: Path) -> TransformResult:
    changed = 0
    for name in README_NAMES:
        path = root / name
        if path.exists():
            path.unlink()
            changed += 1
    for name in DOCS_DIRS:
        directory = root / name
        if directory.is_dir():
            shutil.rmtree(directory)
            changed += 1

    for path in iter_transformable_files(root):
        source = read_source(path)
        try:
            module = cst.parse_module(source)
        except cst.ParserSyntaxError:
            continue
        transformed = module.visit(_StripModuleDocstring()).code
        if transformed != source:
            path.write_text(transformed, encoding="utf-8")
            changed += 1
    return TransformResult(files_changed=changed)
```

**Nota para el implementador:** en `a4_docs.py` esas dos funciones existen pero son privadas y se
llaman `_docstring_literal` y `_only_doctests` (comprobado el 2026-08-17). Tu primer paso es
renombrarlas a `docstring_literal` y `only_doctests` —actualizando sus usos dentro de A4, cuyos tests
tienen que seguir verdes— y usarlas desde aquí en vez de duplicar la lógica: la regla de qué es una
docstring y qué parte se conserva tiene que ser la misma en A4 y en B3, o las dos celdas dejan de ser
comparables. `_only_doctests` devuelve un `cst.SimpleString` o `None` si no había ejemplos.

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_transforms_b3.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/transforms tests/test_transforms_b3.py
git commit -m "feat: B3 removes what tells you which file to open"
```

---

## Task 4: B4 — la suite fuera del alcance del agente

No se mide si el agente escribe tests: se mide si le sirven de documentación ejecutable para entender
cómo se usa una pieza (§4.2). Por eso la suite **se mueve fuera del árbol**, no se borra: los tests
de validación siguen ejecutándose, fuera del alcance del agente, y no se tocan nunca.

**Files:**
- Create: `src/acp/transforms/b4_tests.py`
- Modify: `src/acp/transforms/__init__.py`, `src/acp/suite.py`
- Test: `tests/test_transforms_b4.py`, `tests/test_docker_integration.py`

**Interfaces:**
- Produces: `apply(root: Path) -> TransformResult` registrada como `"B4"`; deja la suite en
  `<árbol>.acp-tests/` (hermano del árbol, nunca dentro); `run_suite_in_docker(..., tests_from: Path | None = None)`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_transforms_b4.py
from pathlib import Path

from acp.transforms import b4_tests


def build(root: Path) -> None:
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "core.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_core.py").write_text(
        "from pkg.core import f\n\n\ndef test_f():\n    assert f() == 1\n", encoding="utf-8"
    )
    (root / "conftest.py").write_text("", encoding="utf-8")


def test_the_suite_leaves_the_tree(tmp_path: Path):
    root = tmp_path / "work"
    build(root)

    b4_tests.apply(root)

    assert not (root / "tests").exists()


def test_the_suite_is_kept_outside_and_intact(tmp_path: Path):
    """Los tests de validación se ejecutan fuera del alcance del agente y no se
    tocan nunca (§4.2): ocultarlos no puede significar perderlos."""
    root = tmp_path / "work"
    build(root)

    b4_tests.apply(root)

    kept = tmp_path / "work.acp-tests" / "tests" / "test_core.py"
    assert kept.exists()
    assert "def test_f()" in kept.read_text(encoding="utf-8")


def test_the_kept_suite_never_lands_inside_the_tree(tmp_path: Path):
    """Dentro del árbol, el agente la encuentra con un `ls` y B4 no mide nada."""
    root = tmp_path / "work"
    build(root)

    b4_tests.apply(root)

    assert not any(path.name.startswith("acp-tests") for path in root.rglob("*"))


def test_the_package_itself_is_not_confused_with_the_suite(tmp_path: Path):
    """Un paquete que se llame `testing` o un módulo `test_utils.py` dentro del
    código fuente no son la suite: llevárselos cambiaría el programa."""
    root = tmp_path / "work"
    build(root)
    (root / "pkg" / "testing").mkdir()
    (root / "pkg" / "testing" / "__init__.py").write_text("HELPER = 1\n", encoding="utf-8")

    b4_tests.apply(root)

    assert (root / "pkg" / "testing" / "__init__.py").exists()
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_b4.py -v`
Expected: FAIL con `ImportError: cannot import name 'b4_tests'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/transforms/b4_tests.py
from __future__ import annotations

import shutil
from pathlib import Path

from acp.transforms.base import TransformResult

# Solo directorios de test de primer nivel y el conftest de la raíz: un paquete
# `testing` dentro del código fuente es parte del programa, no de la suite, y
# llevárselo cambiaría lo que se está midiendo.
SUITE_DIRS = ("tests", "test", "testsuite")
SUITE_FILES = ("conftest.py",)


def kept_suite_path(root: Path) -> Path:
    """Dónde se guarda la suite: hermana del árbol, nunca dentro."""
    return root.parent / f"{root.name}.acp-tests"


def apply(root: Path) -> TransformResult:
    destination = kept_suite_path(root)
    shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True)

    changed = 0
    for name in SUITE_DIRS:
        directory = root / name
        if directory.is_dir():
            shutil.move(str(directory), str(destination / name))
            changed += 1
    for name in SUITE_FILES:
        path = root / name
        if path.exists():
            shutil.move(str(path), str(destination / name))
            changed += 1
    return TransformResult(files_changed=changed)
```

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_transforms_b4.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/transforms tests/test_transforms_b4.py
git commit -m "feat: B4 takes the suite out of the agent's reach without losing it"
```

- [ ] **Step 6: Escribir el test de integración que falla**

```python
# tests/test_docker_integration.py
def test_a_tree_without_its_suite_is_still_verifiable(tmp_path: Path):
    """Si ocultar la suite impidiera verificar la equivalencia, B4 no sería
    medible: los tests salen del árbol pero siguen corriendo."""
    from acp.transforms import b4_tests

    build_repo(tmp_path)
    b4_tests.apply(tmp_path)

    result = run_suite_in_docker(
        tmp_path, timeout=900, tests_from=b4_tests.kept_suite_path(tmp_path)
    )

    assert result.passed == 1
```

- [ ] **Step 7: Ejecutarlo y verlo fallar**

Run: `.venv/bin/python -m pytest -m docker -k still_verifiable -v`
Expected: FAIL con `TypeError: run_suite_in_docker() got an unexpected keyword argument 'tests_from'`

- [ ] **Step 8: Implementar la ejecución con la suite externa**

`run_suite_in_docker` copia la suite guardada dentro del contenedor **después** de que el árbol esté
en su sitio, con un `docker cp` extra:

```python
        if tests_from is not None:
            _run(
                ["docker", "cp", f"{tests_from}/.", f"{runner.container}:{CONTAINER_WORKDIR}"],
                repo, timeout,
            )
```

`CONTAINER_WORKDIR` se importa de `acp.runners`, donde ya está definido como `/repo`.

Va antes de instalar, para que la colecta la encuentre. El árbol del anfitrión no se toca: la suite
solo existe dentro del contenedor, que es donde no hay agente.

- [ ] **Step 9: Ejecutar y ver pasar**

Run: `.venv/bin/python -m pytest -m docker -k still_verifiable -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add src/acp/suite.py tests/test_docker_integration.py
git commit -m "feat: verify a tree whose suite lives outside it"
```

---

## Task 5: B2 — jerarquía

**Files:**
- Create: `src/acp/transforms/b2_hierarchy.py`
- Modify: `src/acp/transforms/__init__.py`
- Test: `tests/test_transforms_b2.py`

**Interfaces:**
- Produces: `apply(root: Path) -> TransformResult` con `moves` relleno, registrada como `"B2"`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_transforms_b2.py
from pathlib import Path

from acp.transforms import b2_hierarchy


def build(root: Path) -> None:
    pkg = root / "pkg"
    (pkg / "es").mkdir(parents=True)
    (pkg / "iso").mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "util.py").write_text("def clean(x):\n    return x.strip()\n", encoding="utf-8")
    (pkg / "es" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "es" / "nif.py").write_text(
        "from pkg.util import clean\n"
        "\n"
        "\n"
        "def validate(number):\n"
        "    return clean(number)\n",
        encoding="utf-8",
    )
    (pkg / "iso" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "iso" / "mod97.py").write_text(
        "from pkg.es.nif import validate\n"
        "\n"
        "\n"
        "def check(number):\n"
        "    return validate(number)\n",
        encoding="utf-8",
    )


def test_the_directories_inside_the_package_are_gone(tmp_path: Path):
    build(tmp_path)

    b2_hierarchy.apply(tmp_path)

    assert not (tmp_path / "pkg" / "es").exists()
    assert not (tmp_path / "pkg" / "iso").exists()


def test_the_root_package_survives(tmp_path: Path):
    """Es lo único que mantiene válidos a la vez los imports desde fuera y el
    comando de test (§5.6). Aplanarlo también dejaría el repo sin punto de
    entrada."""
    build(tmp_path)

    b2_hierarchy.apply(tmp_path)

    assert (tmp_path / "pkg" / "__init__.py").exists()


def test_files_are_renamed_to_opaque_names(tmp_path: Path):
    build(tmp_path)

    b2_hierarchy.apply(tmp_path)

    names = sorted(path.name for path in (tmp_path / "pkg").glob("*.py"))
    assert "__init__.py" in names
    assert any(name.startswith("m") and name[1:-3].isdigit() for name in names)
    assert "nif.py" not in names


def test_the_imports_are_rewritten_so_the_code_runs(tmp_path: Path):
    build(tmp_path)

    b2_hierarchy.apply(tmp_path)

    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c", "import pkg; print('ok')"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    modules = list((tmp_path / "pkg").glob("m*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8") for path in modules)
    assert "pkg.es.nif" not in joined
    assert "pkg.util" not in joined


def test_the_moves_travel_with_the_result(tmp_path: Path):
    """El mapa de identidad los necesita para no perder los símbolos (Task 2)."""
    build(tmp_path)

    result = b2_hierarchy.apply(tmp_path)

    assert result.moves["pkg.es.nif"].startswith("pkg.m")
    assert result.moves["pkg.util"].startswith("pkg.m")
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_b2.py -v`
Expected: FAIL con `ImportError: cannot import name 'b2_hierarchy'`

- [ ] **Step 3: Implementación mínima**

El orden importa: primero se decide el destino de cada módulo, luego se reescriben **todos** los
imports del repo con ese diccionario, y solo al final se mueven los ficheros.

```python
# src/acp/transforms/b2_hierarchy.py
from __future__ import annotations

import shutil
from pathlib import Path

import libcst as cst

from acp.metrics.size import read_source
from acp.transforms.base import TransformResult, iter_transformable_files


def _package_root(root: Path) -> Path | None:
    """El directorio del paquete, que es lo único que no se aplana."""
    candidates = [
        path for path in root.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    ]
    return candidates[0] if len(candidates) == 1 else None


def plan_moves(root: Path) -> dict[str, str]:
    """Módulo original → módulo destino, todos colgando del paquete raíz.

    Determinista y ordenado alfabéticamente: la condición tiene que ser la misma
    en dos corridas distintas, o los resultados no se pueden comparar entre
    seeds (§5.4.4).
    """
    package = _package_root(root)
    if package is None:
        return {}
    moves: dict[str, str] = {}
    index = 0
    for path in sorted(package.rglob("*.py")):
        relative = path.relative_to(root)
        if path.parent == package or path.name == "__init__.py":
            continue
        original = ".".join(relative.with_suffix("").parts)
        moves[original] = f"{package.name}.m{index}"
        index += 1
    # Los módulos que ya cuelgan del paquete también se renombran: si no, la
    # mitad del árbol conserva sus nombres y B2 mide media dosis.
    for path in sorted(package.glob("*.py")):
        if path.name == "__init__.py":
            continue
        original = ".".join(path.relative_to(root).with_suffix("").parts)
        moves[original] = f"{package.name}.m{index}"
        index += 1
    return moves


class _RewriteImports(cst.CSTTransformer):
    def __init__(self, moves: dict[str, str]) -> None:
        self.moves = moves

    def leave_ImportFrom(self, original, updated):
        if updated.module is None:
            return updated
        dotted = _dotted(updated.module)
        target = self.moves.get(dotted)
        if target is None:
            return updated
        return updated.with_changes(module=cst.parse_expression(target))


def _dotted(node: cst.BaseExpression) -> str:
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return f"{_dotted(node.value)}.{node.attr.value}"
    return ""


def apply(root: Path) -> TransformResult:
    moves = plan_moves(root)
    if not moves:
        return TransformResult()

    changed = 0
    for path in iter_transformable_files(root):
        source = read_source(path)
        try:
            module = cst.parse_module(source)
        except cst.ParserSyntaxError:
            continue
        transformed = module.visit(_RewriteImports(moves)).code
        if transformed != source:
            path.write_text(transformed, encoding="utf-8")
            changed += 1

    package = _package_root(root)
    for original, target in moves.items():
        source_path = root / Path(*original.split(".")).with_suffix(".py")
        destination = root / Path(*target.split(".")).with_suffix(".py")
        if source_path != destination and source_path.exists():
            shutil.move(str(source_path), str(destination))
            changed += 1

    for directory in sorted(package.rglob("*"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()

    return TransformResult(files_changed=changed, moves=moves)
```

**Nota para el implementador:** el `import pkg.es.nif` en forma de `ast.Import` (no `ImportFrom`) no
está cubierto arriba y hay que añadirlo: `import pkg.es.nif as x` se reescribe a
`import pkg.m3 as x`, pero `import pkg.es.nif` sin alias se usa después como `pkg.es.nif.validate(...)`
y hay que reescribir también esos usos, o el repo deja de funcionar. Escribe el test primero y
decide: si el caso resulta irreducible, sácalo del alcance de B2 declarándolo, en vez de romper el
repo.

- [ ] **Step 4: Ejecutar y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_transforms_b2.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/transforms tests/test_transforms_b2.py
git commit -m "feat: B2 flattens the hierarchy inside the package"
```

---

## Task 6: Equivalencia de la familia B sobre repos reales

Es el criterio de cierre, y en la fase 1 fue donde apareció todo lo que los fixtures no veían: A4 y
los doctests, A2 y `getattr`, la versión derivada del repositorio.

**Files:**
- Create: `tests/test_equivalence_family_b.py`

- [ ] **Step 1: Escribir el test**

```python
# tests/test_equivalence_family_b.py
"""Equivalencia de la familia B contra repos reales. Necesita Docker y red."""

import shutil
import subprocess
from pathlib import Path

import pytest

from acp.cli import transform_repo
from acp.equivalence import compare
from acp.suite import run_suite_in_docker

pytestmark = [pytest.mark.integration, pytest.mark.docker]

REPOS = {
    "python-stdnum": "https://github.com/arthurdejong/python-stdnum",
    "pint": "https://github.com/hgrecco/pint",
}


@pytest.fixture(autouse=True)
def require_docker():
    if shutil.which("docker") is None:
        pytest.skip("docker no está instalado")


@pytest.mark.parametrize("transform", ["B2", "B3"])
def test_family_b_keeps_python_stdnum_equivalent(tmp_path: Path, transform: str):
    clone = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", "--depth", "1", REPOS["python-stdnum"], str(clone)],
        check=True, capture_output=True,
    )

    before = run_suite_in_docker(clone, timeout=1800)
    work = transform_repo(clone, [transform], tmp_path / "work")
    # B2 destruye la estructura que declara el pyproject (§5.6).
    after = run_suite_in_docker(work, timeout=1800, install_repo=(transform != "B2"))

    report = compare(before, after)
    assert report.equivalent is True, f"{transform}: {report.differences}"
```

- [ ] **Step 2: Ejecutarlo**

Run: `.venv/bin/python -m pytest tests/test_equivalence_family_b.py -v`
Expected: PASS. Unos 6 minutos: dos transformaciones, cada una con dos corridas de suite.

Si falla, **no relajes el test**: el fallo es la información. Diagnostica si es la transformación o
la fontanería, arréglalo con su test de regresión, y anota en el checkpoint qué apareció.

- [ ] **Step 3: Commit**

```bash
git add tests/test_equivalence_family_b.py
git commit -m "feat: prove family B equivalent on a real repository"
```

---

## Checkpoint

Al terminar existen B2, B3 y B4 verificadas. Antes de planificar B1 y B5 hay que mirar dos cosas:

1. **Cuánto aplana B2 de verdad en cada finalista.** Los tres tienen profundidad 2, así que aplanar
   quizá solo cambie los nombres de fichero sin mover nada de sitio. Si es así, en ellos B2 mide
   sobre todo el renombrado de ficheros, y el efecto de la jerarquía habrá que leerlo en pint —donde
   sí hay profundidad 3— y decirlo en el artículo.
2. **Si `import pkg.sub.mod` sin alias quedó dentro o fuera del alcance de B2.** De eso depende que
   B1 y B5 puedan reescribir imports con la misma maquinaria o necesiten otra.
