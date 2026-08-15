# Fase 1 — Núcleo de transformación y familia A

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el núcleo que transforma una copia de un repositorio y verifica que la transformación es semánticamente equivalente, más las cuatro transformaciones de la familia A (tipos, nombres, formato, comentarios y docstrings).

**Architecture:** Un paquete `acp.transforms` donde cada transformación es un módulo con una única función `apply(root) -> TransformResult`, aplicada sobre una copia desechable del árbol. Las ediciones se hacen con LibCST, que preserva formato y comentarios: eso es lo que permite que A1 cambie *solo* los tipos y A4 *solo* la documentación, en vez de reescribir el fichero entero. Un mapa de identidad de símbolos, construido sobre el árbol original y actualizado por cada transformación, es lo que hace comparables las métricas de localización entre condiciones. La equivalencia se comprueba ejecutando la suite del repo en las dos versiones con el ejecutor Docker que ya existe.

**Tech Stack:** Python 3.11+, LibCST (transformación preservando formato), `ast` y `tokenize` de la biblioteca estándar, pytest, Docker vía `acp.runners`.

**Spec:** [`../specs/2026-08-14-software-practices-for-coding-agents-design.md`](../specs/2026-08-14-software-practices-for-coding-agents-design.md), §4 (transformaciones), §4.3 (reglas de equivalencia), §5.4.2 (localización por símbolo), §5.6 (aislamiento).

**Fase 0:** [`../specs/2026-08-14-fase-0-resultados.md`](../specs/2026-08-14-fase-0-resultados.md). Finalistas: python-stdnum, sqlglot, holidays; pint solo para B2.

## Alcance

Este plan cubre el **núcleo de transformación y la familia A**. La familia B (B1 cohesión, B2 jerarquía, B3 documentación de repo, B4 tests visibles, B5 tamaño) va en un plan aparte, porque mueve ficheros y eso obliga a que el mapa de símbolos siga reubicaciones, no solo renombrados. Al terminar este plan hay software que funciona por sí solo: se puede producir la condición T1 del 2×2 (§6.1) y verificar que es equivalente.

## Global Constraints

- **LibCST se instala solo desde wheel precompilada**: `pip install --only-binary :all: libcst`. Compilarlo desde fuente falla en la máquina de trabajo (necesita toolchain de Rust). Verificado el 2026-08-15.
- **El nombre del paquete raíz no se transforma nunca** (§5.6 del spec). Todo lo de dentro sí.
- **Alcance repo-wide, tests del repo incluidos** (§4.3.1). Renombrar solo el código fuente deja los tests sin compilar y mide otra cosa.
- **Solo símbolos resolubles estáticamente** (§4.3.3). Nada de lo alcanzable por `getattr`, por cadenas, por reflexión o por API pública consumida desde fuera.
- **Una copia de repo viva por condición**, y se borra al cerrar (§2). Nunca se transforma el clon original.
- **TDD estricto**: test que falla, implementación, test que pasa, commit. Cada paso su commit.
- **Nada de suites en paralelo**: un solo proceso de pytest a la vez.
- Los tests que necesiten Docker llevan `@pytest.mark.integration` y `@pytest.mark.docker`.

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `src/acp/transforms/__init__.py` | Registro de transformaciones por identificador (`A1`…`A4`) |
| `src/acp/transforms/base.py` | `TransformResult`, y la copia desechable del árbol |
| `src/acp/transforms/a1_types.py` | Elimina anotaciones y type hints |
| `src/acp/transforms/a2_names.py` | Renombra identificadores a opacos, con su diccionario |
| `src/acp/transforms/a3_format.py` | Destruye las señales visuales de formato |
| `src/acp/transforms/a4_docs.py` | Elimina comentarios y docstrings de función |
| `src/acp/symbols.py` | Mapa de identidad de símbolos: nombre original → fichero y rango |
| `src/acp/equivalence.py` | Compara el resultado de la suite entre original y transformado |
| `src/acp/cli.py` | Subcomandos `transform` y `verify` |
| `tests/test_transforms_*.py` | Un fichero por transformación |
| `tests/test_symbols.py`, `tests/test_equivalence.py` | Núcleo |
| `tests/test_transforms_integration.py` | Equivalencia contra un repo real, marcado `docker` |

---

## Task 1: Copia desechable y registro de transformaciones

**Files:**
- Create: `src/acp/transforms/__init__.py`
- Create: `src/acp/transforms/base.py`
- Test: `tests/test_transforms_base.py`

**Interfaces:**
- Produces: `TransformResult(files_changed: int, renames: dict[str, str])`; `copy_tree(source: Path, destination: Path) -> Path`; `iter_transformable_files(root: Path) -> list[Path]`; `TRANSFORMS: dict[str, Callable[[Path], TransformResult]]`.

**Ojo con esto**, que es la diferencia entre este paquete y el de métricas: `iter_source_files`
**excluye los tests** porque perfilar el código del repo no debe contar su suite. Transformar es lo
contrario: §4.3.1 exige alcance repo-wide **con los tests incluidos**, porque renombrar solo el
código fuente deja los tests sin compilar y entonces se mide otra cosa. Por eso las transformaciones
usan `iter_transformable_files` y nunca `iter_source_files`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_transforms_base.py
from pathlib import Path

from acp.transforms.base import TransformResult, copy_tree


def test_copy_tree_leaves_the_original_untouched(tmp_path: Path):
    source = tmp_path / "repo"
    (source / "pkg").mkdir(parents=True)
    (source / "pkg" / "core.py").write_text("x = 1\n", encoding="utf-8")

    destination = copy_tree(source, tmp_path / "work")
    (destination / "pkg" / "core.py").write_text("x = 2\n", encoding="utf-8")

    assert (source / "pkg" / "core.py").read_text(encoding="utf-8") == "x = 1\n"


def test_copy_tree_keeps_the_git_directory_out(tmp_path: Path):
    """El .git de un clon pesa más que el código y no se transforma nunca."""
    source = tmp_path / "repo"
    (source / ".git").mkdir(parents=True)
    (source / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    (source / "pkg").mkdir()
    (source / "pkg" / "core.py").write_text("x = 1\n", encoding="utf-8")

    destination = copy_tree(source, tmp_path / "work")

    assert (destination / "pkg" / "core.py").exists()
    assert not (destination / ".git").exists()


def test_a_result_reports_nothing_changed_by_default():
    assert TransformResult().files_changed == 0
    assert TransformResult().renames == {}


def test_transformable_files_include_the_repo_tests(tmp_path: Path):
    """§4.3.1: renombrar solo el código fuente deja los tests sin compilar, y
    entonces la condición mide otra cosa. Es justo lo contrario de lo que hace
    `iter_source_files`, que los excluye para no perfilarlos."""
    from acp.transforms.base import iter_transformable_files

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "core.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_core.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "generated.py").write_text("x = 1\n", encoding="utf-8")

    found = {path.relative_to(tmp_path).as_posix() for path in iter_transformable_files(tmp_path)}

    assert found == {"pkg/core.py", "tests/test_core.py"}
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_base.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'acp.transforms'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/transforms/base.py
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TransformResult:
    """Lo que una transformación cambió.

    `renames` viaja con el resultado porque el enunciado de la tarea se
    transforma con el mismo diccionario (§4.3.2 del spec): un enunciado que
    habla de `get_queryset` sobre un código donde eso se llama `f7` mide otra
    cosa.
    """

    files_changed: int = 0
    renames: dict[str, str] = field(default_factory=dict)


def copy_tree(source: Path, destination: Path) -> Path:
    """Copia desechable sobre la que se transforma.

    El original nunca se toca: es el árbol de referencia contra el que se
    verifica la equivalencia, y la campaña reutiliza el mismo clon entre
    condiciones.
    """
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git"))
    return destination


# Artefactos y dependencias ajenas. No incluye los directorios de test: esos sí
# se transforman (§4.3.1), al revés que en las métricas de la fase 0.
NOT_TRANSFORMABLE = {
    "build", "dist", ".git", ".venv", "venv", "__pycache__", "node_modules", "site-packages",
    "vendor", "third_party",
}


def iter_transformable_files(root: Path) -> list[Path]:
    """Ficheros .py que una transformación puede tocar, tests del repo incluidos.

    Es deliberadamente distinta de `acp.metrics.size.iter_source_files`, que
    excluye los tests: perfilar y transformar quieren conjuntos opuestos.
    """
    found: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        parts = path.relative_to(root).parts[:-1]
        if any(part in NOT_TRANSFORMABLE or part.startswith(".") for part in parts):
            continue
        found.append(path)
    return found
```

```python
# src/acp/transforms/__init__.py
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from acp.transforms.base import TransformResult

TRANSFORMS: dict[str, Callable[[Path], TransformResult]] = {}
```

- [ ] **Step 4: Ejecutar el test y verlo pasar**

Run: `.venv/bin/python -m pytest tests/test_transforms_base.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/transforms tests/test_transforms_base.py
git commit -m "feat: a disposable copy to transform, leaving the clone alone"
```

---

## Task 2: Mapa de identidad de símbolos

Es la pieza de la que depende la métrica de localización (§5.4.2). La identidad de un símbolo es su
**nombre en el árbol original**: con A2 el nombre visible cambia, y sin una identidad estable las
lecturas del agente no se pueden proyectar sobre el objetivo de la tarea.

**Files:**
- Create: `src/acp/symbols.py`
- Test: `tests/test_symbols.py`

**Interfaces:**
- Consumes: `acp.metrics.size.iter_source_files`, `acp.metrics.size.parse_source`.
- Produces: `Location(module: str, path: str, start: int, end: int)`; `build_symbol_map(root: Path) -> dict[str, Location]`; `apply_renames(symbols: dict[str, Location], renames: dict[str, str]) -> dict[str, Location]`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_symbols.py
from pathlib import Path

from acp.symbols import apply_renames, build_symbol_map


def test_every_function_and_class_gets_a_location(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "billing.py").write_text(
        "def total(rows):\n"
        "    return sum(rows)\n"
        "\n"
        "\n"
        "class Invoice:\n"
        "    def render(self):\n"
        "        return ''\n",
        encoding="utf-8",
    )

    symbols = build_symbol_map(tmp_path)

    assert symbols["pkg.billing.total"].start == 1
    assert symbols["pkg.billing.total"].end == 2
    assert symbols["pkg.billing.Invoice"].start == 5
    assert symbols["pkg.billing.Invoice.render"].start == 6
    assert symbols["pkg.billing.total"].path == "pkg/billing.py"


def test_the_map_keeps_the_original_name_as_identity(tmp_path: Path):
    """Con A2 el nombre visible cambia. Si la clave cambiara con él, no habría
    forma de decir que el agente miró la región objetivo."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "billing.py").write_text("def total(rows):\n    return rows\n", encoding="utf-8")
    symbols = build_symbol_map(tmp_path)

    renamed = apply_renames(symbols, {"total": "f7"})

    assert renamed["pkg.billing.total"].current_name == "f7"
    assert "pkg.billing.f7" not in renamed


def test_a_symbol_nobody_renamed_keeps_its_name(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "billing.py").write_text("def total(rows):\n    return rows\n", encoding="utf-8")
    symbols = build_symbol_map(tmp_path)

    renamed = apply_renames(symbols, {"otra_cosa": "f9"})

    assert renamed["pkg.billing.total"].current_name == "total"
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

Run: `.venv/bin/python -m pytest tests/test_symbols.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'acp.symbols'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/symbols.py
from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from pathlib import Path

from acp.metrics.size import iter_source_files, parse_source


@dataclass(frozen=True)
class Location:
    """Dónde vive un símbolo y cómo se llama ahora.

    `module` y el nombre original forman la clave; `current_name` es lo que el
    agente ve después de transformar. Separar las dos cosas es lo que permite
    medir localización en todas las condiciones con la misma vara.
    """

    module: str
    path: str
    start: int
    end: int
    current_name: str


def build_symbol_map(root: Path) -> dict[str, Location]:
    """Funciones, clases y métodos del árbol, con su fichero y rango de líneas."""
    symbols: dict[str, Location] = {}
    for path in iter_source_files(root):
        tree = parse_source(path)
        if tree is None:
            continue
        module = ".".join(path.relative_to(root).with_suffix("").parts)
        relative = path.relative_to(root).as_posix()
        for node, qualified in _walk_definitions(tree):
            symbols[f"{module}.{qualified}"] = Location(
                module=module,
                path=relative,
                start=node.lineno,
                end=node.end_lineno or node.lineno,
                current_name=node.name,
            )
    return symbols


def _walk_definitions(tree: ast.Module) -> list[tuple[ast.AST, str]]:
    """Definiciones con su nombre cualificado dentro del módulo."""
    found: list[tuple[ast.AST, str]] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualified = f"{prefix}{child.name}"
                found.append((child, qualified))
                visit(child, f"{qualified}.")

    visit(tree, "")
    return found


def apply_renames(
    symbols: dict[str, Location], renames: dict[str, str]
) -> dict[str, Location]:
    """Actualiza el nombre visible sin tocar la identidad."""
    return {
        key: replace(location, current_name=renames.get(location.current_name, location.current_name))
        for key, location in symbols.items()
    }
```

- [ ] **Step 4: Ejecutar el test y verlo pasar**

Run: `.venv/bin/python -m pytest tests/test_symbols.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/symbols.py tests/test_symbols.py
git commit -m "feat: symbol identity that survives renaming"
```

---

## Task 3: A4 — comentarios y docstrings

Se hace antes que A1 porque es la transformación más simple con LibCST y sirve de banco de pruebas
para el resto. Ojo con el detalle que la hace no trivial: quitar la docstring de una función cuyo
cuerpo es **solo** la docstring deja un cuerpo vacío, que es un `SyntaxError`.

**Files:**
- Create: `src/acp/transforms/a4_docs.py`
- Modify: `src/acp/transforms/__init__.py`
- Test: `tests/test_transforms_a4.py`

**Interfaces:**
- Consumes: `TransformResult`, `iter_transformable_files`, `read_source`.
- Produces: `apply(root: Path) -> TransformResult`, registrada como `"A4"`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_transforms_a4.py
from pathlib import Path

from acp.transforms import a4_docs

SOURCE = '''\
"""Módulo."""
import os  # de la biblioteca estándar


def rate(value):
    """Calcula la tarifa."""
    # la regla viene de la norma
    return value * 2
'''


def write(root: Path, source: str = SOURCE) -> Path:
    pkg = root / "pkg"
    pkg.mkdir(exist_ok=True)
    path = pkg / "core.py"
    path.write_text(source, encoding="utf-8")
    return path


def test_comments_and_function_docstrings_are_gone(tmp_path: Path):
    path = write(tmp_path)

    a4_docs.apply(tmp_path)

    result = path.read_text(encoding="utf-8")
    assert "# de la biblioteca estándar" not in result
    assert "# la regla viene de la norma" not in result
    assert "Calcula la tarifa" not in result


def test_the_module_docstring_survives(tmp_path: Path):
    """El docstring de módulo es B3, no A4: dice qué hay en el fichero, no cómo
    funciona una función. Mezclarlos borraría el contraste que busca el spec."""
    path = write(tmp_path)

    a4_docs.apply(tmp_path)

    assert '"""Módulo."""' in path.read_text(encoding="utf-8")


def test_the_code_still_runs(tmp_path: Path):
    path = write(tmp_path)

    a4_docs.apply(tmp_path)

    namespace: dict = {}
    exec(compile(path.read_text(encoding="utf-8"), "core.py", "exec"), namespace)
    assert namespace["rate"](21) == 42


def test_a_function_whose_body_is_only_a_docstring_keeps_a_body(tmp_path: Path):
    """Sin esto queda `def f():` sin cuerpo, que no compila: la condición se
    leería como un fracaso total del agente cuando es fontanería rota."""
    path = write(tmp_path, 'def noop():\n    """Nada."""\n')

    a4_docs.apply(tmp_path)

    source = path.read_text(encoding="utf-8")
    compile(source, "core.py", "exec")
    assert "pass" in source


def test_it_reports_how_many_files_changed(tmp_path: Path):
    write(tmp_path)
    (tmp_path / "pkg" / "sin_docs.py").write_text("x = 1\n", encoding="utf-8")

    result = a4_docs.apply(tmp_path)

    assert result.files_changed == 1
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_a4.py -v`
Expected: FAIL con `ImportError: cannot import name 'a4_docs'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/transforms/a4_docs.py
from __future__ import annotations

from pathlib import Path

import libcst as cst

from acp.metrics.size import read_source
from acp.transforms.base import TransformResult, iter_transformable_files


class _StripDocs(cst.CSTTransformer):
    """Quita comentarios y docstrings de función y de clase.

    La docstring de módulo se conserva a propósito: es B3 (dice qué hay en el
    fichero) y no A4 (dice cómo funciona lo que ya has abierto).
    """

    def leave_Comment(self, original: cst.Comment, updated: cst.Comment) -> cst.RemovalSentinel:
        return cst.RemoveFromParent()

    def leave_FunctionDef(self, original, updated):
        return updated.with_changes(body=_without_docstring(updated.body))

    def leave_ClassDef(self, original, updated):
        return updated.with_changes(body=_without_docstring(updated.body))


def _without_docstring(body: cst.BaseSuite) -> cst.BaseSuite:
    if not isinstance(body, cst.IndentedBlock) or not body.body:
        return body
    first = body.body[0]
    if not _is_docstring(first):
        return body
    remaining = list(body.body[1:])
    # Un cuerpo vacío no compila: si la docstring era todo, hace falta un `pass`.
    if not remaining:
        remaining = [cst.SimpleStatementLine(body=[cst.Pass()])]
    return body.with_changes(body=remaining)


def _is_docstring(statement: cst.BaseStatement) -> bool:
    return (
        isinstance(statement, cst.SimpleStatementLine)
        and len(statement.body) == 1
        and isinstance(statement.body[0], cst.Expr)
        and isinstance(statement.body[0].value, cst.SimpleString)
    )


def apply(root: Path) -> TransformResult:
    changed = 0
    for path in iter_transformable_files(root):
        source = read_source(path)
        try:
            module = cst.parse_module(source)
        except cst.ParserSyntaxError:
            continue
        transformed = module.visit(_StripDocs()).code
        if transformed != source:
            path.write_text(transformed, encoding="utf-8")
            changed += 1
    return TransformResult(files_changed=changed)
```

```python
# src/acp/transforms/__init__.py  (añadir)
from acp.transforms import a4_docs

TRANSFORMS: dict[str, Callable[[Path], TransformResult]] = {
    "A4": a4_docs.apply,
}
```

- [ ] **Step 4: Ejecutar el test y verlo pasar**

Run: `.venv/bin/python -m pytest tests/test_transforms_a4.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/transforms tests/test_transforms_a4.py
git commit -m "feat: A4 strips comments and function docstrings"
```

---

## Task 4: A1 — tipos

**Files:**
- Create: `src/acp/transforms/a1_types.py`
- Modify: `src/acp/transforms/__init__.py`
- Test: `tests/test_transforms_a1.py`

**Interfaces:**
- Produces: `apply(root: Path) -> TransformResult`, registrada como `"A1"`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_transforms_a1.py
from pathlib import Path

from acp.transforms import a1_types

SOURCE = '''\
from __future__ import annotations

import os  # comentario que debe sobrevivir

TOTAL: int = 0


def rate(value: int, factor: float = 1.0) -> float:
    """Sobrevive: esto es A4, no A1."""
    partial: float = value * factor
    return partial
'''


def write(root: Path, source: str = SOURCE) -> Path:
    pkg = root / "pkg"
    pkg.mkdir(exist_ok=True)
    path = pkg / "core.py"
    path.write_text(source, encoding="utf-8")
    return path


def test_annotations_are_gone(tmp_path: Path):
    path = write(tmp_path)

    a1_types.apply(tmp_path)

    result = path.read_text(encoding="utf-8")
    assert "value: int" not in result
    assert "-> float" not in result
    assert "partial: float" not in result
    assert "TOTAL: int" not in result


def test_only_the_types_change(tmp_path: Path):
    """A1 mide el valor de los tipos. Si de paso se lleva un comentario o una
    docstring, mide A4 y el resultado no es atribuible."""
    path = write(tmp_path)

    a1_types.apply(tmp_path)

    result = path.read_text(encoding="utf-8")
    assert "# comentario que debe sobrevivir" in result
    assert "Sobrevive: esto es A4, no A1." in result


def test_defaults_keep_their_spacing(tmp_path: Path):
    """Quitar la anotación deja `factor = 1.0`, y ese espaciado es un cambio de
    formato: sería A3 colándose dentro de A1."""
    path = write(tmp_path)

    a1_types.apply(tmp_path)

    assert "factor=1.0" in path.read_text(encoding="utf-8")


def test_an_annotated_assignment_without_value_becomes_nothing(tmp_path: Path):
    """`x: int` sin valor no declara nada en ejecución: al quitar el tipo no
    puede quedar `x`, que sería un NameError."""
    path = write(tmp_path, "def f():\n    x: int\n    x = 1\n    return x\n")

    a1_types.apply(tmp_path)

    source = path.read_text(encoding="utf-8")
    compile(source, "core.py", "exec")
    assert "x: int" not in source


def test_the_code_still_runs(tmp_path: Path):
    path = write(tmp_path)

    a1_types.apply(tmp_path)

    namespace: dict = {}
    exec(compile(path.read_text(encoding="utf-8"), "core.py", "exec"), namespace)
    assert namespace["rate"](21, 2.0) == 42.0
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_a1.py -v`
Expected: FAIL con `ImportError: cannot import name 'a1_types'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/transforms/a1_types.py
from __future__ import annotations

from pathlib import Path

import libcst as cst

from acp.metrics.size import read_source
from acp.transforms.base import TransformResult, iter_transformable_files


class _StripTypes(cst.CSTTransformer):
    def leave_Param(self, original: cst.Param, updated: cst.Param) -> cst.Param:
        if updated.annotation is None:
            return updated
        # Sin anotación, PEP 8 escribe `factor=1.0`: dejar los espacios sería
        # meter un cambio de formato (A3) dentro de A1.
        equal = updated.equal
        if isinstance(equal, cst.AssignEqual):
            equal = equal.with_changes(
                whitespace_before=cst.SimpleWhitespace(""),
                whitespace_after=cst.SimpleWhitespace(""),
            )
        return updated.with_changes(annotation=None, equal=equal)

    def leave_FunctionDef(self, original, updated):
        return updated.with_changes(returns=None)

    def leave_AnnAssign(self, original: cst.AnnAssign, updated: cst.AnnAssign):
        if updated.value is None:
            # `x: int` sin valor no crea nombre en ejecución: quitarlo entero es
            # lo único equivalente. Dejar `x` daría NameError.
            return cst.RemoveFromParent()
        return cst.Assign(
            targets=[cst.AssignTarget(target=updated.target)],
            value=updated.value,
        )


def apply(root: Path) -> TransformResult:
    changed = 0
    for path in iter_transformable_files(root):
        source = read_source(path)
        try:
            module = cst.parse_module(source)
        except cst.ParserSyntaxError:
            continue
        transformed = module.visit(_StripTypes()).code
        if transformed != source:
            path.write_text(transformed, encoding="utf-8")
            changed += 1
    return TransformResult(files_changed=changed)
```

```python
# src/acp/transforms/__init__.py  (añadir "A1": a1_types.apply)
```

- [ ] **Step 4: Ejecutar el test y verlo pasar**

Run: `.venv/bin/python -m pytest tests/test_transforms_a1.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/transforms tests/test_transforms_a1.py
git commit -m "feat: A1 removes annotations without touching anything else"
```

---

## Task 5: A3 — formato

En Python la sangría es sintaxis, así que A3 no puede destruirla (§4.1). Lo que sí puede es eliminar
todas las demás señales visuales: líneas en blanco, espaciado alrededor de operadores y separación
entre bloques.

**Files:**
- Create: `src/acp/transforms/a3_format.py`
- Modify: `src/acp/transforms/__init__.py`
- Test: `tests/test_transforms_a3.py`

**Interfaces:**
- Produces: `apply(root: Path) -> TransformResult`, registrada como `"A3"`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_transforms_a3.py
from pathlib import Path

from acp.transforms import a3_format

SOURCE = '''\
import os


def rate(value, factor):
    total = value * factor + 1

    return total


def other(x):
    return x
'''


def write(root: Path, source: str = SOURCE) -> Path:
    pkg = root / "pkg"
    pkg.mkdir(exist_ok=True)
    path = pkg / "core.py"
    path.write_text(source, encoding="utf-8")
    return path


def test_blank_lines_are_gone(tmp_path: Path):
    path = write(tmp_path)

    a3_format.apply(tmp_path)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert all(line.strip() for line in lines)


def test_operator_spacing_is_gone(tmp_path: Path):
    path = write(tmp_path)

    a3_format.apply(tmp_path)

    assert "value*factor+1" in path.read_text(encoding="utf-8")


def test_indentation_survives_because_it_is_syntax(tmp_path: Path):
    path = write(tmp_path)

    a3_format.apply(tmp_path)

    source = path.read_text(encoding="utf-8")
    compile(source, "core.py", "exec")
    assert any(line.startswith("    ") for line in source.splitlines())


def test_the_code_still_runs(tmp_path: Path):
    path = write(tmp_path)

    a3_format.apply(tmp_path)

    namespace: dict = {}
    exec(compile(path.read_text(encoding="utf-8"), "core.py", "exec"), namespace)
    assert namespace["rate"](6, 6) == 37


def test_strings_are_not_touched(tmp_path: Path):
    """Colapsar espacios dentro de una cadena cambia el programa, y varios
    finalistas comparan mensajes de error literales en sus tests."""
    path = write(tmp_path, 'MESSAGE = "a + b  se queda igual"\n')

    a3_format.apply(tmp_path)

    assert '"a + b  se queda igual"' in path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_a3.py -v`
Expected: FAIL con `ImportError: cannot import name 'a3_format'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/transforms/a3_format.py
from __future__ import annotations

from pathlib import Path

import libcst as cst

from acp.metrics.size import read_source
from acp.transforms.base import TransformResult, iter_transformable_files

_EMPTY = cst.SimpleWhitespace("")


class _CrushFormatting(cst.CSTTransformer):
    """Quita el espaciado que no es sintaxis.

    Se hace sobre el árbol y no con expresiones regulares porque el espaciado
    dentro de una cadena sí es significativo: varios finalistas comparan
    mensajes literales en sus tests.
    """

    def leave_BinaryOperation(self, original, updated):
        return updated.with_changes(
            operator=updated.operator.with_changes(
                whitespace_before=_EMPTY, whitespace_after=_EMPTY
            )
        )

    def leave_Comparison(self, original, updated):
        return updated.with_changes(
            comparisons=[
                target.with_changes(
                    operator=target.operator.with_changes(
                        whitespace_before=_EMPTY, whitespace_after=_EMPTY
                    )
                )
                for target in updated.comparisons
            ]
        )

    def leave_EmptyLine(self, original, updated) -> cst.RemovalSentinel:
        return cst.RemoveFromParent()


def apply(root: Path) -> TransformResult:
    changed = 0
    for path in iter_transformable_files(root):
        source = read_source(path)
        try:
            module = cst.parse_module(source)
        except cst.ParserSyntaxError:
            continue
        transformed = module.visit(_CrushFormatting()).code
        if transformed != source:
            path.write_text(transformed, encoding="utf-8")
            changed += 1
    return TransformResult(files_changed=changed)
```

- [ ] **Step 4: Ejecutar el test y verlo pasar**

Run: `.venv/bin/python -m pytest tests/test_transforms_a3.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/transforms tests/test_transforms_a3.py
git commit -m "feat: A3 destroys the visual cues that are not syntax"
```

---

## Task 6: A2 — nombres

La más delicada de las cuatro, y la que el spec señala como el punto donde la partición entre
familias se rompe (§4.4). Dos restricciones vinculantes: solo símbolos resolubles estáticamente
(§4.3.3) y el nombre del paquete raíz nunca se transforma (§5.6).

**Files:**
- Create: `src/acp/transforms/a2_names.py`
- Modify: `src/acp/transforms/__init__.py`
- Test: `tests/test_transforms_a2.py`

**Interfaces:**
- Produces: `apply(root: Path) -> TransformResult` con `renames` relleno, registrada como `"A2"`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_transforms_a2.py
from pathlib import Path

from acp.transforms import a2_names


def build(root: Path) -> Path:
    pkg = root / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    path = pkg / "billing.py"
    path.write_text(
        "TAX_RATE = 0.21\n"
        "\n"
        "\n"
        "def apply_tax(amount):\n"
        "    return amount * (1 + TAX_RATE)\n"
        "\n"
        "\n"
        "def total(amount):\n"
        "    return apply_tax(amount)\n",
        encoding="utf-8",
    )
    return path


def test_definitions_and_their_uses_are_renamed_together(tmp_path: Path):
    path = build(tmp_path)

    a2_names.apply(tmp_path)

    source = path.read_text(encoding="utf-8")
    assert "def apply_tax" not in source
    assert "apply_tax(" not in source
    compile(source, "billing.py", "exec")


def test_the_dictionary_travels_with_the_result(tmp_path: Path):
    """El enunciado de la tarea se transforma con el mismo diccionario
    (§4.3.2): si no viaja, el enunciado habla de un código que ya no existe."""
    build(tmp_path)

    result = a2_names.apply(tmp_path)

    assert result.renames["apply_tax"].startswith("f")
    assert result.renames["TAX_RATE"].startswith("C")


def test_the_root_package_name_is_never_touched(tmp_path: Path):
    """Es lo único que mantiene válidos a la vez la instalación, los imports
    desde fuera y el comando de test (§5.6)."""
    build(tmp_path)

    result = a2_names.apply(tmp_path)

    assert "pkg" not in result.renames


def test_dunder_and_stdlib_names_are_left_alone(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    path = pkg / "core.py"
    path.write_text(
        "import os\n"
        "\n"
        "\n"
        "class Thing:\n"
        "    def __init__(self, value):\n"
        "        self.value = value\n"
        "\n"
        "    def path(self):\n"
        "        return os.path.join('a', 'b')\n",
        encoding="utf-8",
    )

    result = a2_names.apply(tmp_path)

    source = path.read_text(encoding="utf-8")
    assert "__init__" in source
    assert "os.path.join" in source
    assert "os" not in result.renames


def test_the_repo_tests_are_updated_but_not_renamed(tmp_path: Path):
    """Los tests se transforman (§4.3.1) pero sus propios nombres no: pytest los
    colecta por nombre, y renombrarlos dejaría la suite sin encontrar nada."""
    build(tmp_path)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_billing.py").write_text(
        "from pkg.billing import apply_tax\n"
        "\n"
        "\n"
        "def test_apply_tax():\n"
        "    assert apply_tax(100) > 100\n",
        encoding="utf-8",
    )

    result = a2_names.apply(tmp_path)

    source = (tests / "test_billing.py").read_text(encoding="utf-8")
    assert "def test_apply_tax" in source
    assert "apply_tax(100)" not in source
    assert result.renames["apply_tax"] in source


def test_names_reachable_by_string_are_left_alone(tmp_path: Path):
    """Renombrar lo que se alcanza por getattr rompe el programa, y el fallo se
    leería como un agente que fracasa (§4.3.3)."""
    pkg = tmp_path / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    path = pkg / "core.py"
    path.write_text(
        "def handler(x):\n"
        "    return x\n"
        "\n"
        "\n"
        "def dispatch(name, x):\n"
        "    return globals()[name](x)\n",
        encoding="utf-8",
    )

    result = a2_names.apply(tmp_path)

    assert "handler" not in result.renames
    assert "def handler" in path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_a2.py -v`
Expected: FAIL con `ImportError: cannot import name 'a2_names'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/transforms/a2_names.py
from __future__ import annotations

import ast
from pathlib import Path

import libcst as cst

from acp.metrics.size import iter_source_files, parse_source, read_source
from acp.transforms.base import TransformResult, iter_transformable_files

# Un módulo que use cualquiera de estas queda fuera del renombrado entero: sus
# nombres se alcanzan por cadena y renombrarlos rompe el programa (§4.3.3).
DYNAMIC_ACCESS = {"getattr", "setattr", "hasattr", "globals", "locals", "vars", "eval", "exec"}


def _opaque(name: str, index: int) -> str:
    if name.isupper():
        return f"C{index}"
    if name[:1].isupper():
        return f"K{index}"
    return f"f{index}"


def _uses_dynamic_access(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in DYNAMIC_ACCESS
        for node in ast.walk(tree)
    )


def collect_renames(root: Path) -> dict[str, str]:
    """Diccionario de renombrado de los símbolos que define el propio repo.

    Solo entran definiciones de nivel de módulo —funciones, clases y constantes—
    porque son las que se pueden resolver estáticamente. Los métodos se dejan:
    una llamada `obj.metodo()` no se puede atribuir a una clase sin inferencia
    de tipos, y equivocarse rompe el repo en silencio.
    """
    names: set[str] = set()
    # El diccionario sale solo del código fuente: incluir los ficheros de test
    # metería `test_algo` en el renombrado, y pytest colecta por nombre — la
    # suite dejaría de encontrar sus propios tests. Aplicarlo, en cambio, se
    # aplica a todo (§4.3.1).
    for path in iter_source_files(root):
        tree = parse_source(path)
        if tree is None or _uses_dynamic_access(tree):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith("__"):
                    names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("__"):
                        names.add(target.id)
    return {name: _opaque(name, index) for index, name in enumerate(sorted(names))}


class _Rename(cst.CSTTransformer):
    def __init__(self, renames: dict[str, str]) -> None:
        self.renames = renames

    def leave_Name(self, original: cst.Name, updated: cst.Name) -> cst.Name:
        new = self.renames.get(updated.value)
        return updated.with_changes(value=new) if new else updated


def apply(root: Path) -> TransformResult:
    renames = collect_renames(root)
    changed = 0
    for path in iter_transformable_files(root):
        source = read_source(path)
        try:
            module = cst.parse_module(source)
        except cst.ParserSyntaxError:
            continue
        transformed = module.visit(_Rename(renames)).code
        if transformed != source:
            path.write_text(transformed, encoding="utf-8")
            changed += 1
    return TransformResult(files_changed=changed, renames=renames)
```

- [ ] **Step 4: Ejecutar el test y verlo pasar**

Run: `.venv/bin/python -m pytest tests/test_transforms_a2.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/transforms tests/test_transforms_a2.py
git commit -m "feat: A2 renames what can be resolved statically, and nothing else"
```

---

## Task 7: Verificación de equivalencia

El riesgo número uno de la tabla de §11 del spec: una transformación rompe el repo y se lee
exactamente igual que un agente que fracasa. Esta tarea es la que lo evita.

**Files:**
- Create: `src/acp/equivalence.py`
- Test: `tests/test_equivalence.py`

**Interfaces:**
- Consumes: `acp.models.SuiteMetrics`.
- Produces: `EquivalenceReport(equivalent: bool, differences: list[str])`; `compare(before: SuiteMetrics, after: SuiteMetrics) -> EquivalenceReport`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_equivalence.py
from acp.equivalence import compare
from acp.models import SuiteMetrics


def suite(**overrides) -> SuiteMetrics:
    defaults = dict(
        ran=True, passed=413, failed=0, errors=0, skipped=9,
        attempted=True, install_ok=True, collect_ok=True, tree_under_test=True,
    )
    return SuiteMetrics(**{**defaults, **overrides})


def test_the_same_result_is_equivalent():
    assert compare(suite(), suite()).equivalent is True


def test_one_test_less_is_not_equivalent():
    """Que el total baje suele significar que la transformación se llevó por
    delante un módulo entero, no que el repo cambiara de opinión."""
    report = compare(suite(), suite(passed=412))

    assert report.equivalent is False
    assert any("passed" in difference for difference in report.differences)


def test_a_suite_that_did_not_run_afterwards_is_not_equivalent():
    report = compare(suite(), suite(ran=False, passed=0))

    assert report.equivalent is False


def test_duration_does_not_count_as_a_difference():
    """El tiempo varía entre corridas de la misma máquina: exigirlo igual haría
    fallar la verificación por ruido."""
    assert compare(suite(seconds=20.0), suite(seconds=31.5)).equivalent is True
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

Run: `.venv/bin/python -m pytest tests/test_equivalence.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'acp.equivalence'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/equivalence.py
from __future__ import annotations

from dataclasses import dataclass, field

from acp.models import SuiteMetrics

# El tiempo queda fuera a propósito: varía entre corridas de la misma máquina.
COMPARED = ("ran", "passed", "failed", "errors", "skipped")


@dataclass
class EquivalenceReport:
    equivalent: bool
    differences: list[str] = field(default_factory=list)


def compare(before: SuiteMetrics, after: SuiteMetrics) -> EquivalenceReport:
    """La suite del árbol transformado tiene que dar el mismo resultado (§3.6.3).

    Una transformación que rompe el repo produce exactamente la misma señal que
    un agente incapaz de arreglarlo, y es el error más caro de descubrir tarde.
    """
    differences = [
        f"{field_name}: {getattr(before, field_name)} -> {getattr(after, field_name)}"
        for field_name in COMPARED
        if getattr(before, field_name) != getattr(after, field_name)
    ]
    return EquivalenceReport(equivalent=not differences, differences=differences)
```

- [ ] **Step 4: Ejecutar el test y verlo pasar**

Run: `.venv/bin/python -m pytest tests/test_equivalence.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/acp/equivalence.py tests/test_equivalence.py
git commit -m "feat: a broken transform must not look like a failing agent"
```

---

## Task 8: CLI `transform` y equivalencia contra un repo real

Cierra el plan: produce la condición T1 sobre un finalista de verdad y comprueba que su suite da
exactamente el mismo resultado que el original.

**Files:**
- Modify: `src/acp/cli.py`
- Test: `tests/test_cli_transform.py`
- Test: `tests/test_transforms_integration.py`

**Interfaces:**
- Consumes: `TRANSFORMS`, `copy_tree`, `compare`, `run_suite_in_docker`, `build_symbol_map`, `apply_renames`.
- Produces: subcomando `acp transform <ruta> --apply A1,A2,A3,A4 --out <dir>`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_cli_transform.py
import json
from pathlib import Path

from acp.cli import transform_repo


def build(root: Path) -> Path:
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "core.py").write_text(
        'def rate(value: int) -> int:\n    """Doc."""\n    return value * 2\n',
        encoding="utf-8",
    )
    return root


def test_it_transforms_a_copy_and_leaves_the_original(tmp_path: Path):
    source = build(tmp_path / "repo")

    destination = transform_repo(source, ["A1"], tmp_path / "work")

    assert "value: int" in (source / "pkg" / "core.py").read_text(encoding="utf-8")
    assert "value: int" not in (destination / "pkg" / "core.py").read_text(encoding="utf-8")


def test_the_manifest_records_what_was_applied(tmp_path: Path):
    """Sin procedencia registrada, un cambio a mitad de campaña deja el conjunto
    de datos sin interpretación posible (§5.4.1)."""
    source = build(tmp_path / "repo")

    destination = transform_repo(source, ["A1", "A4"], tmp_path / "work")

    manifest = json.loads((destination / "acp-manifest.json").read_text(encoding="utf-8"))
    assert manifest["applied"] == ["A1", "A4"]
    assert manifest["symbols"]["pkg.core.rate"]["current_name"] == "rate"


def test_an_unknown_transform_is_rejected(tmp_path: Path):
    source = build(tmp_path / "repo")

    try:
        transform_repo(source, ["Z9"], tmp_path / "work")
    except ValueError as error:
        assert "Z9" in str(error)
    else:
        raise AssertionError("debería haber fallado")
```

```python
# tests/test_transforms_integration.py
import shutil
import subprocess
from pathlib import Path

import pytest

from acp.cli import transform_repo
from acp.equivalence import compare
from acp.suite import run_suite_in_docker

pytestmark = [pytest.mark.integration, pytest.mark.docker]


@pytest.fixture(autouse=True)
def require_docker():
    if shutil.which("docker") is None:
        pytest.skip("docker no está instalado")


def test_a1_keeps_python_stdnum_equivalent(tmp_path: Path):
    """El finalista más barato (96 s por corrida), que es el que hace viable
    correr esta comprobación antes de cada bloque (§5.4.6)."""
    clone = tmp_path / "python-stdnum"
    subprocess.run(
        ["git", "clone", "--depth", "1",
         "https://github.com/arthurdejong/python-stdnum", str(clone)],
        check=True, capture_output=True,
    )

    before = run_suite_in_docker(clone, timeout=1800)
    transformed = transform_repo(clone, ["A1"], tmp_path / "work")
    after = run_suite_in_docker(transformed, timeout=1800)

    report = compare(before, after)
    assert report.equivalent is True, report.differences
```

- [ ] **Step 2: Ejecutar los tests y verlos fallar**

Run: `.venv/bin/python -m pytest tests/test_cli_transform.py -v`
Expected: FAIL con `ImportError: cannot import name 'transform_repo'`

- [ ] **Step 3: Implementación mínima**

```python
# src/acp/cli.py  (añadir)
import json
from dataclasses import asdict

from acp.symbols import apply_renames, build_symbol_map
from acp.transforms import TRANSFORMS
from acp.transforms.base import copy_tree


def transform_repo(source: Path, transform_ids: list[str], destination: Path) -> Path:
    """Aplica transformaciones sobre una copia y deja constancia de qué se hizo.

    El manifiesto no es decoración: sin procedencia registrada —qué se aplicó y
    dónde acabó cada símbolo— las métricas de localización de la campaña no se
    pueden interpretar (§5.4.1, §5.4.2).
    """
    unknown = [name for name in transform_ids if name not in TRANSFORMS]
    if unknown:
        raise ValueError(f"transformación desconocida: {', '.join(unknown)}")

    symbols = build_symbol_map(source)
    root = copy_tree(source, destination)

    renames: dict[str, str] = {}
    for name in transform_ids:
        result = TRANSFORMS[name](root)
        renames.update(result.renames)

    symbols = apply_renames(symbols, renames)
    manifest = {
        "applied": transform_ids,
        "renames": renames,
        "symbols": {key: asdict(location) for key, location in symbols.items()},
    }
    (root / "acp-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return root
```

Y en `main()`, junto a los subcomandos existentes:

```python
    transform_parser = subparsers.add_parser("transform", help="transforma una copia del repo")
    transform_parser.add_argument("path", type=Path)
    transform_parser.add_argument("--apply", required=True, help="p. ej. A1,A4")
    transform_parser.add_argument("--out", type=Path, required=True)
```

```python
    if args.command == "transform":
        destination = transform_repo(args.path, args.apply.split(","), args.out)
        print(f"escrito {destination}")
        return 0
```

- [ ] **Step 4: Ejecutar los tests y verlos pasar**

Run: `.venv/bin/python -m pytest tests/test_cli_transform.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Ejecutar la verificación contra el repo real**

Run: `.venv/bin/python -m pytest tests/test_transforms_integration.py -v`
Expected: PASS, unos 4 minutos (dos corridas de suite más la transformación)

- [ ] **Step 6: Commit**

```bash
git add src/acp/cli.py tests/test_cli_transform.py tests/test_transforms_integration.py
git commit -m "feat: produce a transformed tree and prove it is equivalent"
```

---

## Checkpoint

Al terminar este plan existe T1 (§6.1 del spec) y la maquinaria para verificarla. Antes de planificar
la familia B hay que revisar dos cosas que solo se ven con las transformaciones corriendo sobre los
tres finalistas:

1. **Qué tan lejos llega A2 en la práctica.** La implementación renombra definiciones de nivel de
   módulo y deja los métodos fuera, porque atribuir `obj.metodo()` a una clase exige inferencia de
   tipos. Si en los finalistas eso deja la mayor parte del código con sus nombres intactos, A2 estará
   midiendo menos degradación de la que el spec supone, y hay que decirlo o ampliarlo con cuidado.
2. **Cuántos módulos quedan excluidos por acceso dinámico.** Un repo donde media docena de módulos
   usen `getattr` pierde esos módulos del renombrado. Hay que contar cuántos son en cada finalista y
   registrarlo, porque es una dosis de A2 más baja de la nominal.
