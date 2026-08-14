# Fase 0 — Perfilado y selección de repos candidatos

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir una herramienta que perfile repositorios Python candidatos y emitir la ficha de cada uno, para elegir con datos los tres finalistas del experimento de buenas prácticas.

**Architecture:** Paquete Python `acp` con un módulo por dimensión de examen, todos funciones puras sobre un árbol de ficheros salvo la ejecución de la suite, que se aísla en Docker y de la que solo se testea el parseo. Un `cli` orquesta las dimensiones y `report` emite ficha markdown por repo más una tabla comparativa.

**Tech Stack:** Python 3.11+, biblioteca estándar (`ast`, `pathlib`, `dataclasses`, `subprocess`), pytest para los tests, Docker para ejecutar suites de terceros con aislamiento.

**Spec:** [`../specs/2026-08-14-software-practices-for-coding-agents-design.md`](../specs/2026-08-14-software-practices-for-coding-agents-design.md), §3.2.

**Repo de código:** `C:/Users/Usuario/GitHub/agent-code-practices` (nuevo). Este plan vive en `personal-website` junto al spec; el código no.

---

## Por qué esta fase primero

El spec (§3.2) la declara previa a todo: sin saber sobre qué repos se trabaja, ni el transformador ni el harness se pueden diseñar con criterio. Un repo ya plano y sin documentar no deja margen para degradar la familia B; uno hecho de pegamento y utilidades no admite el estrato de fallos de dominio (§3.3.1). Las dos cosas se ven midiendo, no leyendo.

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `pyproject.toml` | Metadatos del paquete y configuración de pytest |
| `.gitignore` | Excluye clones de candidatos, entornos y salidas |
| `src/acp/models.py` | Dataclasses del perfil: una por dimensión, más el agregado |
| `src/acp/metrics/size.py` | Líneas, ficheros, profundidad de jerarquía |
| `src/acp/metrics/readability.py` | Ratio de comentarios y docstrings, cobertura de anotaciones, presencia de README y `docs/` |
| `src/acp/metrics/runtime_typing.py` | Detección de tipado usado en ejecución (criterio de exclusión) |
| `src/acp/metrics/coupling.py` | Grafo de imports internos, fan-in y fan-out |
| `src/acp/metrics/domain.py` | Complejidad ciclomática, proxy de densidad de dominio y muestra de funciones |
| `src/acp/suite.py` | Parseo de la salida de pytest y ejecución en Docker |
| `src/acp/report.py` | Ficha markdown por repo y tabla comparativa |
| `src/acp/cli.py` | Punto de entrada que orquesta las dimensiones |
| `tests/` | Un fichero de test por módulo, con fixtures de árboles mínimos |

## Convenciones

- Todo módulo de `metrics/` expone una única función pública `measure(root: Path) -> <Modelo>`.
- Ninguna función de `metrics/` ejecuta código del repo analizado: solo lo lee y lo parsea con `ast`.
- Ficheros de test en `tests/test_<modulo>.py`.
- Comandos desde la raíz del repo, en PowerShell.

---

## Task 1: Scaffolding del repo

**Files:**
- Create: `C:/Users/Usuario/GitHub/agent-code-practices/pyproject.toml`
- Create: `C:/Users/Usuario/GitHub/agent-code-practices/.gitignore`
- Create: `C:/Users/Usuario/GitHub/agent-code-practices/README.md`
- Create: `C:/Users/Usuario/GitHub/agent-code-practices/src/acp/__init__.py`
- Create: `C:/Users/Usuario/GitHub/agent-code-practices/src/acp/metrics/__init__.py`
- Create: `C:/Users/Usuario/GitHub/agent-code-practices/tests/__init__.py`

- [ ] **Step 1: Crear el repo y la estructura**

```powershell
New-Item -ItemType Directory -Force C:/Users/Usuario/GitHub/agent-code-practices/src/acp/metrics
New-Item -ItemType Directory -Force C:/Users/Usuario/GitHub/agent-code-practices/tests
Set-Location C:/Users/Usuario/GitHub/agent-code-practices
git init
```

- [ ] **Step 2: Escribir `pyproject.toml`**

```toml
[project]
name = "acp"
version = "0.1.0"
description = "Which software practices help a coding agent"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
acp = "acp.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: needs Docker, not run by default"]
addopts = "-m 'not integration'"
```

- [ ] **Step 3: Escribir `.gitignore`**

```gitignore
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
candidates/
out/
```

- [ ] **Step 4: Escribir `README.md`**

```markdown
# agent-code-practices

Experimento: qué buenas prácticas de software ayudan realmente a un coding agent.

Fase 0 — perfilado de repos candidatos. El diseño completo vive en el spec del blog:
`personal-website/docs/superpowers/specs/2026-08-14-software-practices-for-coding-agents-design.md`

## Uso

    python -m acp.cli profile candidates/pint --name pint --out out/

`candidates/` y `out/` están fuera del control de versiones a propósito: los clones ocupan
gigas y se borran al terminar cada bloque.
```

- [ ] **Step 5: Crear los `__init__.py` vacíos**

```powershell
New-Item -ItemType File src/acp/__init__.py
New-Item -ItemType File src/acp/metrics/__init__.py
New-Item -ItemType File tests/__init__.py
```

- [ ] **Step 6: Crear el entorno e instalar**

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```
Esperado: `Successfully installed acp-0.1.0`

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: scaffold the profiling package"
```

---

## Task 2: Modelos de datos

**Files:**
- Create: `src/acp/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_models.py
from acp.models import RepoProfile, SizeMetrics, ReadabilityMetrics


def test_profile_serialises_to_flat_dict():
    profile = RepoProfile(
        name="demo",
        size=SizeMetrics(python_files=3, code_lines=120, max_depth=2, mean_depth=1.5),
        readability=ReadabilityMetrics(
            comment_ratio=0.1,
            docstring_ratio=0.2,
            annotated_function_ratio=0.5,
            has_readme=True,
            has_docs_dir=False,
        ),
    )
    flat = profile.to_flat_dict()
    assert flat["name"] == "demo"
    assert flat["size.code_lines"] == 120
    assert flat["readability.has_readme"] is True
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'acp.models'`

- [ ] **Step 3: Implementar**

```python
# src/acp/models.py
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from typing import Any


@dataclass
class SizeMetrics:
    python_files: int
    code_lines: int
    max_depth: int
    mean_depth: float


@dataclass
class ReadabilityMetrics:
    comment_ratio: float
    docstring_ratio: float
    annotated_function_ratio: float
    has_readme: bool
    has_docs_dir: bool


@dataclass
class RuntimeTypingMetrics:
    uses_runtime_typing: bool = False
    evidence: list[str] = field(default_factory=list)


@dataclass
class CouplingMetrics:
    internal_modules: int = 0
    internal_edges: int = 0
    mean_fan_out: float = 0.0
    max_fan_in: int = 0


@dataclass
class DomainMetrics:
    complex_functions: int = 0
    domain_candidate_functions: int = 0
    domain_density: float = 0.0
    samples: list[str] = field(default_factory=list)


@dataclass
class SuiteMetrics:
    ran: bool = False
    passed: int = 0
    failed: int = 0
    errors: int = 0
    seconds: float = 0.0


@dataclass
class RepoProfile:
    name: str
    size: SizeMetrics
    readability: ReadabilityMetrics
    runtime_typing: RuntimeTypingMetrics = field(default_factory=RuntimeTypingMetrics)
    coupling: CouplingMetrics = field(default_factory=CouplingMetrics)
    domain: DomainMetrics = field(default_factory=DomainMetrics)
    suite: SuiteMetrics = field(default_factory=SuiteMetrics)

    def to_flat_dict(self) -> dict[str, Any]:
        flat: dict[str, Any] = {"name": self.name}
        for f in fields(self):
            value = getattr(self, f.name)
            if is_dataclass(value):
                for key, inner in asdict(value).items():
                    flat[f"{f.name}.{key}"] = inner
        return flat
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Esperado: PASS

- [ ] **Step 5: Commit**

```bash
git add src/acp/models.py tests/test_models.py
git commit -m "feat: profile data models"
```

---

## Task 3: Métrica de tamaño

Mide el criterio de admisión 2 del spec (§3.2.1) y la profundidad de jerarquía, que es lo que B2 destruye.

**Files:**
- Create: `src/acp/metrics/size.py`
- Test: `tests/test_size.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_size.py
from pathlib import Path

from acp.metrics.size import measure


def build_tree(root: Path) -> None:
    (root / "pkg" / "sub").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "a.py").write_text("x = 1\n\n# comment\ny = 2\n", encoding="utf-8")
    (root / "pkg" / "sub" / "b.py").write_text("z = 3\n", encoding="utf-8")
    (root / "notes.txt").write_text("ignored\n", encoding="utf-8")


def test_counts_python_files_and_code_lines(tmp_path):
    build_tree(tmp_path)
    result = measure(tmp_path)
    assert result.python_files == 3
    assert result.code_lines == 3  # __init__ vacío, dos líneas en a.py, una en b.py


def test_depth_is_measured_relative_to_root(tmp_path):
    build_tree(tmp_path)
    result = measure(tmp_path)
    assert result.max_depth == 2
    assert result.mean_depth == 4 / 3  # profundidades 1, 1 y 2


def test_skips_test_and_vendor_directories(tmp_path):
    build_tree(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("x = 1\n", encoding="utf-8")
    result = measure(tmp_path)
    assert result.python_files == 3
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv\Scripts\python.exe -m pytest tests/test_size.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'acp.metrics.size'`

- [ ] **Step 3: Implementar**

```python
# src/acp/metrics/size.py
from __future__ import annotations

from pathlib import Path

from acp.models import SizeMetrics

EXCLUDED_DIRS = {
    "tests", "test", "testing", "docs", "doc", "examples", "example",
    "vendor", "third_party", "build", "dist", ".git", ".venv", "venv",
    "__pycache__", "node_modules", "site-packages",
}


def iter_source_files(root: Path) -> list[Path]:
    """Ficheros .py del repo, excluidos tests, vendorizados y artefactos."""
    found: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        parts = set(path.relative_to(root).parts[:-1])
        if parts & EXCLUDED_DIRS:
            continue
        found.append(path)
    return found


def _code_lines(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def measure(root: Path) -> SizeMetrics:
    files = iter_source_files(root)
    if not files:
        return SizeMetrics(python_files=0, code_lines=0, max_depth=0, mean_depth=0.0)
    depths = [len(path.relative_to(root).parts) - 1 for path in files]
    return SizeMetrics(
        python_files=len(files),
        code_lines=sum(_code_lines(path) for path in files),
        max_depth=max(depths),
        mean_depth=sum(depths) / len(depths),
    )
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv\Scripts\python.exe -m pytest tests/test_size.py -v`
Esperado: PASS, 3 tests

- [ ] **Step 5: Commit**

```bash
git add src/acp/metrics/size.py tests/test_size.py
git commit -m "feat: size and hierarchy-depth metric"
```

---

## Task 4: Métrica de legibilidad y margen de degradación

Cuantifica cuánto hay que destruir: un repo sin comentarios ni anotaciones ni README ya parte degradado y no sirve de baseline.

**Files:**
- Create: `src/acp/metrics/readability.py`
- Test: `tests/test_readability.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_readability.py
from acp.metrics.readability import measure

SOURCE = '''\
"""Module docstring."""


def annotated(a: int) -> int:
    """Doc."""
    # a comment
    return a + 1


def bare(a):
    return a
'''


def test_measures_ratios_and_doc_presence(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text(SOURCE, encoding="utf-8")
    (tmp_path / "README.md").write_text("hi\n", encoding="utf-8")

    result = measure(tmp_path)

    assert result.annotated_function_ratio == 0.5
    assert result.has_readme is True
    assert result.has_docs_dir is False
    assert result.comment_ratio > 0
    assert result.docstring_ratio > 0


def test_detects_docs_directory(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()

    result = measure(tmp_path)

    assert result.has_docs_dir is True
    assert result.annotated_function_ratio == 0.0
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv\Scripts\python.exe -m pytest tests/test_readability.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'acp.metrics.readability'`

- [ ] **Step 3: Implementar**

```python
# src/acp/metrics/readability.py
from __future__ import annotations

import ast
from pathlib import Path

from acp.metrics.size import iter_source_files
from acp.models import ReadabilityMetrics

README_NAMES = ("README.md", "README.rst", "README.txt", "README")
DOCS_DIRS = ("docs", "doc")


def _is_annotated(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if node.returns is not None:
        return True
    args = node.args
    every = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    if args.vararg:
        every.append(args.vararg)
    if args.kwarg:
        every.append(args.kwarg)
    return any(arg.annotation is not None for arg in every)


def measure(root: Path) -> ReadabilityMetrics:
    total_lines = 0
    comment_lines = 0
    docstring_lines = 0
    functions = 0
    annotated = 0

    for path in iter_source_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        total_lines += len(lines)
        comment_lines += sum(1 for line in lines if line.strip().startswith("#"))

        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    docstring_lines += len(doc.splitlines())
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
                if _is_annotated(node):
                    annotated += 1

    denominator = total_lines or 1
    return ReadabilityMetrics(
        comment_ratio=comment_lines / denominator,
        docstring_ratio=docstring_lines / denominator,
        annotated_function_ratio=(annotated / functions) if functions else 0.0,
        has_readme=any((root / name).exists() for name in README_NAMES),
        has_docs_dir=any((root / name).is_dir() for name in DOCS_DIRS),
    )
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv\Scripts\python.exe -m pytest tests/test_readability.py -v`
Esperado: PASS, 2 tests

- [ ] **Step 5: Commit**

```bash
git add src/acp/metrics/readability.py tests/test_readability.py
git commit -m "feat: readability and degradation-headroom metric"
```

---

## Task 5: Detección de tipado en ejecución

Criterio de exclusión 4 del spec (§3.2.1): si las anotaciones se usan en ejecución, A1 no es semánticamente equivalente y el repo no sirve.

**Files:**
- Create: `src/acp/metrics/runtime_typing.py`
- Test: `tests/test_runtime_typing.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_runtime_typing.py
from acp.metrics.runtime_typing import measure


def write(tmp_path, source: str):
    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pkg" / "a.py").write_text(source, encoding="utf-8")


def test_flags_pydantic(tmp_path):
    write(tmp_path, "from pydantic import BaseModel\n\n\nclass M(BaseModel):\n    x: int\n")
    result = measure(tmp_path)
    assert result.uses_runtime_typing is True
    assert any("pydantic" in item for item in result.evidence)


def test_flags_get_type_hints(tmp_path):
    write(tmp_path, "import typing\n\n\ndef f(o):\n    return typing.get_type_hints(o)\n")
    result = measure(tmp_path)
    assert result.uses_runtime_typing is True


def test_plain_annotations_are_clean(tmp_path):
    write(tmp_path, "def f(a: int) -> int:\n    return a\n")
    result = measure(tmp_path)
    assert result.uses_runtime_typing is False
    assert result.evidence == []
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv\Scripts\python.exe -m pytest tests/test_runtime_typing.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'acp.metrics.runtime_typing'`

- [ ] **Step 3: Implementar**

```python
# src/acp/metrics/runtime_typing.py
from __future__ import annotations

import ast
from pathlib import Path

from acp.metrics.size import iter_source_files
from acp.models import RuntimeTypingMetrics

# Librerías que convierten las anotaciones en comportamiento en ejecución.
RUNTIME_TYPING_MODULES = {
    "pydantic", "attrs", "attr", "marshmallow", "cattrs", "typeguard",
    "beartype", "trafaret", "schematics", "msgspec", "typedload",
}
RUNTIME_TYPING_CALLS = {"get_type_hints", "validate_arguments", "validate_call"}


def measure(root: Path) -> RuntimeTypingMetrics:
    evidence: list[str] = []

    for path in iter_source_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in RUNTIME_TYPING_MODULES:
                        evidence.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                root_module = (node.module or "").split(".")[0]
                if root_module in RUNTIME_TYPING_MODULES:
                    evidence.append(f"{path.name}: from {node.module} import ...")
            elif isinstance(node, ast.Call):
                name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if name in RUNTIME_TYPING_CALLS:
                    evidence.append(f"{path.name}: {name}()")

    return RuntimeTypingMetrics(uses_runtime_typing=bool(evidence), evidence=evidence[:20])
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv\Scripts\python.exe -m pytest tests/test_runtime_typing.py -v`
Esperado: PASS, 3 tests

- [ ] **Step 5: Commit**

```bash
git add src/acp/metrics/runtime_typing.py tests/test_runtime_typing.py
git commit -m "feat: runtime-typing exclusion check"
```

---

## Task 6: Métrica de acoplamiento

Dimensión de examen del spec (§3.2): interesan repos donde entender un fallo obligue a leer más de un sitio.

**Files:**
- Create: `src/acp/metrics/coupling.py`
- Test: `tests/test_coupling.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_coupling.py
from acp.metrics.coupling import measure


def test_counts_internal_edges_only(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "core.py").write_text("import os\n", encoding="utf-8")
    (pkg / "api.py").write_text("from pkg import core\nimport json\n", encoding="utf-8")
    (pkg / "cli.py").write_text("from pkg import core\n", encoding="utf-8")

    result = measure(tmp_path)

    assert result.internal_modules == 4
    assert result.internal_edges == 2
    assert result.max_fan_in == 2
    assert result.mean_fan_out == 0.5


def test_repo_without_internal_imports_has_no_edges(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("import os\n", encoding="utf-8")
    (pkg / "b.py").write_text("import sys\n", encoding="utf-8")

    result = measure(tmp_path)

    assert result.internal_edges == 0
    assert result.max_fan_in == 0
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coupling.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'acp.metrics.coupling'`

- [ ] **Step 3: Implementar**

```python
# src/acp/metrics/coupling.py
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from acp.metrics.size import iter_source_files
from acp.models import CouplingMetrics


def _module_name(path: Path, root: Path) -> str:
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve(candidate: str, known: set[str]) -> str | None:
    """Módulo conocido más largo que sea prefijo del nombre importado."""
    while candidate:
        if candidate in known:
            return candidate
        candidate = candidate.rpartition(".")[0]
    return None


def _import_targets(tree: ast.AST, known: set[str]) -> set[str]:
    """Módulos internos a los que apunta cada sentencia de import.

    De `from pkg import core` sale `pkg.core`, no `pkg`: se toma siempre el
    destino más específico que exista, y solo se cae al módulo padre si el
    nombre importado es un símbolo y no un submódulo.
    """
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve(alias.name, known)
                if resolved:
                    targets.add(resolved)
        elif isinstance(node, ast.ImportFrom) and node.module:
            specific = {
                resolved
                for alias in node.names
                if (resolved := _resolve(f"{node.module}.{alias.name}", known))
                and resolved != node.module
            }
            if specific:
                targets |= specific
            else:
                parent = _resolve(node.module, known)
                if parent:
                    targets.add(parent)
    return targets


def measure(root: Path) -> CouplingMetrics:
    files = iter_source_files(root)
    modules = {_module_name(path, root): path for path in files}
    known = set(modules)

    fan_out: dict[str, set[str]] = defaultdict(set)
    fan_in: dict[str, int] = defaultdict(int)

    for name, path in modules.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for target in _import_targets(tree, known):
            if target != name:
                fan_out[name].add(target)
                fan_in[target] += 1

    edges = sum(len(targets) for targets in fan_out.values())
    module_count = len(modules) or 1
    return CouplingMetrics(
        internal_modules=len(modules),
        internal_edges=edges,
        mean_fan_out=edges / module_count,
        max_fan_in=max(fan_in.values()) if fan_in else 0,
    )
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv\Scripts\python.exe -m pytest tests/test_coupling.py -v`
Esperado: PASS, 2 tests

- [ ] **Step 5: Commit**

```bash
git add src/acp/metrics/coupling.py tests/test_coupling.py
git commit -m "feat: internal-import coupling metric"
```

---

## Task 7: Proxy de densidad de lógica de dominio

Sin lógica propia no se pueden fabricar fallos del estrato de dominio (§3.3.1). El proxy: funciones con varias ramas cuyo cuerpo llama sobre todo a código del propio repo, no a librerías. Es un proxy y se reporta como tal; la muestra de nombres existe para inspección manual.

**Files:**
- Create: `src/acp/metrics/domain.py`
- Test: `tests/test_domain.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_domain.py
from acp.metrics.domain import cyclomatic_complexity, measure
import ast


def first_function(source: str) -> ast.FunctionDef:
    return ast.parse(source).body[0]


def test_complexity_counts_branches():
    node = first_function(
        "def f(a, b):\n"
        "    if a and b:\n"
        "        for x in a:\n"
        "            pass\n"
        "    return a\n"
    )
    assert cyclomatic_complexity(node) == 4


def test_flat_function_has_complexity_one():
    node = first_function("def f(a):\n    return a + 1\n")
    assert cyclomatic_complexity(node) == 1


def test_domain_candidates_need_branches_and_internal_calls(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "rules.py").write_text("def rate(x):\n    return x\n", encoding="utf-8")
    (pkg / "billing.py").write_text(
        "from pkg import rules\n"
        "import json\n"
        "\n"
        "\n"
        "def total(items, region, premium):\n"
        "    if region == 'eu' and premium:\n"
        "        base = rules.rate(items)\n"
        "    else:\n"
        "        base = rules.rate(items) * 2\n"
        "    return base\n"
        "\n"
        "\n"
        "def dump(data):\n"
        "    return json.dumps(data)\n",
        encoding="utf-8",
    )

    result = measure(tmp_path)

    assert result.domain_candidate_functions == 1
    assert "pkg.billing.total" in result.samples
    assert "pkg.billing.dump" not in result.samples
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv\Scripts\python.exe -m pytest tests/test_domain.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'acp.metrics.domain'`

- [ ] **Step 3: Implementar**

```python
# src/acp/metrics/domain.py
from __future__ import annotations

import ast
from pathlib import Path

from acp.metrics.size import iter_source_files
from acp.models import DomainMetrics

BRANCHING = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.Assert)
MIN_COMPLEXITY = 3
MAX_SAMPLES = 15


def cyclomatic_complexity(node: ast.AST) -> int:
    score = 1
    for child in ast.walk(node):
        if isinstance(child, BRANCHING):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += len(child.values) - 1
        elif isinstance(child, ast.comprehension):
            score += len(child.ifs)
    return score


def _local_names(root: Path, files: list[Path]) -> set[str]:
    """Nombres de módulo de primer nivel que pertenecen al propio repo."""
    return {path.relative_to(root).parts[0].removesuffix(".py") for path in files}


def _calls_internal(node: ast.AST, local: set[str], sibling_defs: set[str]) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name) and func.id in sibling_defs:
            return True
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id in local or func.value.id in sibling_defs:
                return True
    return False


def measure(root: Path) -> DomainMetrics:
    files = iter_source_files(root)
    local = _local_names(root, files)

    complex_count = 0
    candidates: list[str] = []
    total_functions = 0

    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue

        module = ".".join(path.relative_to(root).with_suffix("").parts)
        imported_local = {
            alias.asname or alias.name.split(".")[-1]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in local
            for alias in node.names
        }

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            total_functions += 1
            if cyclomatic_complexity(node) < MIN_COMPLEXITY:
                continue
            complex_count += 1
            if _calls_internal(node, local, imported_local):
                candidates.append(f"{module}.{node.name}")

    return DomainMetrics(
        complex_functions=complex_count,
        domain_candidate_functions=len(candidates),
        domain_density=len(candidates) / (total_functions or 1),
        samples=candidates[:MAX_SAMPLES],
    )
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv\Scripts\python.exe -m pytest tests/test_domain.py -v`
Esperado: PASS, 3 tests

- [ ] **Step 5: Commit**

```bash
git add src/acp/metrics/domain.py tests/test_domain.py
git commit -m "feat: domain-logic density proxy"
```

---

## Task 8: Ejecución y parseo de la suite

Criterio de admisión 1 y 3 del spec: sin suite verde no hay medida, y el tiempo se multiplica por 54 corridas. Se ejecuta en Docker porque muchos repos Python no corren en Windows y porque el aislamiento hará falta igualmente después. Solo se testea el parseo; la ejecución lleva un test de humo marcado como `integration`.

**Files:**
- Create: `src/acp/suite.py`
- Test: `tests/test_suite.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_suite.py
import pytest

from acp.suite import parse_pytest_summary

GREEN = """\
============================= test session starts ==============================
collected 312 items

tests/test_a.py ....                                                     [ 10%]
tests/test_b.py ....                                                     [100%]

======================== 312 passed, 4 skipped in 21.44s =======================
"""

RED = """\
======================== 3 failed, 120 passed, 1 error in 8.10s ================
"""


def test_parses_green_summary():
    result = parse_pytest_summary(GREEN)
    assert result.ran is True
    assert result.passed == 312
    assert result.failed == 0
    assert result.errors == 0
    assert result.seconds == pytest.approx(21.44)


def test_parses_failures_and_errors():
    result = parse_pytest_summary(RED)
    assert result.passed == 120
    assert result.failed == 3
    assert result.errors == 1
    assert result.seconds == pytest.approx(8.10)


def test_unparseable_output_is_not_a_run():
    result = parse_pytest_summary("ImportError while loading conftest")
    assert result.ran is False
    assert result.passed == 0
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv\Scripts\python.exe -m pytest tests/test_suite.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'acp.suite'`

- [ ] **Step 3: Implementar**

```python
# src/acp/suite.py
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from acp.models import SuiteMetrics

COUNT_PATTERN = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped)")
DURATION_PATTERN = re.compile(r"in\s+([\d.]+)s")

DEFAULT_IMAGE = "python:3.12-slim"
INSTALL_AND_TEST = (
    "python -m pip install --quiet --upgrade pip && "
    "python -m pip install --quiet -e '.[test,dev]' || python -m pip install --quiet -e . ; "
    "python -m pip install --quiet pytest && python -m pytest -q"
)


def parse_pytest_summary(output: str) -> SuiteMetrics:
    counts = {"passed": 0, "failed": 0, "errors": 0}
    found = False
    for number, label in COUNT_PATTERN.findall(output):
        found = True
        key = "errors" if label.startswith("error") else label
        if key in counts:
            counts[key] += int(number)

    if not found:
        return SuiteMetrics()

    duration = DURATION_PATTERN.search(output)
    return SuiteMetrics(
        ran=True,
        passed=counts["passed"],
        failed=counts["failed"],
        errors=counts["errors"],
        seconds=float(duration.group(1)) if duration else 0.0,
    )


def run_suite_in_docker(repo: Path, image: str = DEFAULT_IMAGE, timeout: int = 3600) -> SuiteMetrics:
    """Instala el repo y corre su suite dentro de un contenedor desechable."""
    command = [
        "docker", "run", "--rm",
        "-v", f"{repo.resolve()}:/repo",
        "-w", "/repo",
        image, "bash", "-lc", INSTALL_AND_TEST,
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return SuiteMetrics()
    return parse_pytest_summary(completed.stdout + completed.stderr)
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv\Scripts\python.exe -m pytest tests/test_suite.py -v`
Esperado: PASS, 3 tests

- [ ] **Step 5: Añadir el test de humo de Docker**

```python
# tests/test_suite_integration.py
import subprocess
from pathlib import Path

import pytest

from acp.suite import run_suite_in_docker

pytestmark = pytest.mark.integration


def test_runs_a_trivial_repo_in_docker(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n'
        '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n',
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    result = run_suite_in_docker(tmp_path, timeout=600)

    assert result.ran is True
    assert result.passed == 1
```

- [ ] **Step 6: Ejecutar el test de humo**

Run: `.venv\Scripts\python.exe -m pytest tests/test_suite_integration.py -v -m integration`
Esperado: PASS. Si Docker no está disponible, el test falla con error de conexión — resolver antes de seguir, porque toda la campaña depende de ello.

- [ ] **Step 7: Commit**

```bash
git add src/acp/suite.py tests/test_suite.py tests/test_suite_integration.py
git commit -m "feat: containerised suite execution and summary parsing"
```

---

## Task 9: Informe

**Files:**
- Create: `src/acp/report.py`
- Test: `tests/test_report.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_report.py
from acp.models import ReadabilityMetrics, RepoProfile, SizeMetrics, SuiteMetrics
from acp.report import comparison_table, render_profile


def make_profile(name: str = "demo") -> RepoProfile:
    return RepoProfile(
        name=name,
        size=SizeMetrics(python_files=40, code_lines=8000, max_depth=3, mean_depth=1.8),
        readability=ReadabilityMetrics(
            comment_ratio=0.08,
            docstring_ratio=0.12,
            annotated_function_ratio=0.4,
            has_readme=True,
            has_docs_dir=True,
        ),
        suite=SuiteMetrics(ran=True, passed=300, failed=0, errors=0, seconds=44.0),
    )


def test_profile_renders_name_and_key_numbers():
    text = render_profile(make_profile())
    assert "# demo" in text
    assert "8000" in text
    assert "44.0" in text


def test_comparison_table_has_a_row_per_repo():
    text = comparison_table([make_profile("a"), make_profile("b")])
    lines = [line for line in text.splitlines() if line.startswith("| ")]
    assert len(lines) == 3  # cabecera y dos filas; el separador empieza por "|---"


def test_admission_verdict_rejects_red_suite():
    profile = make_profile()
    profile.suite = SuiteMetrics(ran=True, passed=10, failed=2, errors=0, seconds=5.0)
    assert "RECHAZADO" in render_profile(profile)
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv\Scripts\python.exe -m pytest tests/test_report.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'acp.report'`

- [ ] **Step 3: Implementar**

```python
# src/acp/report.py
from __future__ import annotations

from acp.models import RepoProfile

COLUMNS = [
    ("repo", lambda p: p.name),
    ("ficheros", lambda p: str(p.size.python_files)),
    ("líneas", lambda p: str(p.size.code_lines)),
    ("prof. máx", lambda p: str(p.size.max_depth)),
    ("anotadas", lambda p: f"{p.readability.annotated_function_ratio:.0%}"),
    ("docs", lambda p: "sí" if p.readability.has_docs_dir else "no"),
    ("fan-out", lambda p: f"{p.coupling.mean_fan_out:.2f}"),
    ("dominio", lambda p: f"{p.domain.domain_density:.0%}"),
    ("suite", lambda p: f"{p.suite.passed}p/{p.suite.failed}f {p.suite.seconds:.0f}s"),
]


def admission_verdict(profile: RepoProfile) -> tuple[str, list[str]]:
    """Aplica los criterios de admisión del spec §3.2.1."""
    reasons: list[str] = []
    if not profile.suite.ran:
        reasons.append("la suite no llegó a ejecutarse")
    elif profile.suite.failed or profile.suite.errors:
        reasons.append(f"suite en rojo: {profile.suite.failed} fallos, {profile.suite.errors} errores")
    if profile.runtime_typing.uses_runtime_typing:
        reasons.append("usa tipado en ejecución, A1 no sería equivalente")
    if profile.size.code_lines < 2000:
        reasons.append("demasiado pequeño: el agente lo lee entero")
    if profile.size.code_lines > 80000:
        reasons.append("demasiado grande para el presupuesto")
    return ("RECHAZADO" if reasons else "ADMITIDO"), reasons


def render_profile(profile: RepoProfile) -> str:
    verdict, reasons = admission_verdict(profile)
    lines = [
        f"# {profile.name}",
        "",
        f"**Veredicto de admisión:** {verdict}",
        "",
    ]
    if reasons:
        lines += [f"- {reason}" for reason in reasons] + [""]

    lines += [
        "## Tamaño",
        f"- Ficheros Python: {profile.size.python_files}",
        f"- Líneas de código: {profile.size.code_lines}",
        f"- Profundidad de jerarquía: máx {profile.size.max_depth}, media {profile.size.mean_depth:.2f}",
        "",
        "## Margen de degradación",
        f"- Ratio de comentarios: {profile.readability.comment_ratio:.1%}",
        f"- Ratio de docstrings: {profile.readability.docstring_ratio:.1%}",
        f"- Funciones anotadas: {profile.readability.annotated_function_ratio:.1%}",
        f"- README: {'sí' if profile.readability.has_readme else 'no'}",
        f"- Directorio docs/: {'sí' if profile.readability.has_docs_dir else 'no'}",
        "",
        "## Acoplamiento",
        f"- Módulos internos: {profile.coupling.internal_modules}",
        f"- Aristas internas: {profile.coupling.internal_edges}",
        f"- Fan-out medio: {profile.coupling.mean_fan_out:.2f}",
        f"- Fan-in máximo: {profile.coupling.max_fan_in}",
        "",
        "## Densidad de lógica de dominio (proxy)",
        f"- Funciones complejas: {profile.domain.complex_functions}",
        f"- Candidatas a dominio: {profile.domain.domain_candidate_functions}",
        f"- Densidad: {profile.domain.domain_density:.1%}",
        "",
        "### Muestra para inspección manual",
    ]
    lines += [f"- `{sample}`" for sample in profile.domain.samples] or ["- (ninguna)"]
    lines += [
        "",
        "## Suite",
        f"- Ejecutada: {'sí' if profile.suite.ran else 'no'}",
        f"- Pasan: {profile.suite.passed}, fallan: {profile.suite.failed}, errores: {profile.suite.errors}",
        f"- Duración: {profile.suite.seconds} s",
        "",
        "## Tipado en ejecución",
        f"- Detectado: {'sí' if profile.runtime_typing.uses_runtime_typing else 'no'}",
    ]
    lines += [f"  - {item}" for item in profile.runtime_typing.evidence]
    return "\n".join(lines) + "\n"


def comparison_table(profiles: list[RepoProfile]) -> str:
    header = "| " + " | ".join(name for name, _ in COLUMNS) + " |"
    separator = "|" + "|".join("---" for _ in COLUMNS) + "|"
    rows = [
        "| " + " | ".join(getter(profile) for _, getter in COLUMNS) + " |"
        for profile in profiles
    ]
    return "\n".join([header, separator, *rows]) + "\n"
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv\Scripts\python.exe -m pytest tests/test_report.py -v`
Esperado: PASS, 3 tests

- [ ] **Step 5: Commit**

```bash
git add src/acp/report.py tests/test_report.py
git commit -m "feat: candidate profile report and comparison table"
```

---

## Task 10: CLI

**Files:**
- Create: `src/acp/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_cli.py
from pathlib import Path

from acp.cli import profile_repo


def test_profile_repo_produces_a_profile_without_running_the_suite(tmp_path: Path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "core.py").write_text(
        '"""Core."""\n\n\ndef f(a: int) -> int:\n    if a:\n        return 1\n    return 0\n',
        encoding="utf-8",
    )

    profile = profile_repo(tmp_path, name="demo", run_suite=False)

    assert profile.name == "demo"
    assert profile.size.python_files == 2
    assert profile.suite.ran is False
    assert profile.readability.annotated_function_ratio == 1.0
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'acp.cli'`

- [ ] **Step 3: Implementar**

```python
# src/acp/cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from acp.metrics import coupling, domain, readability, runtime_typing, size
from acp.models import RepoProfile
from acp.report import comparison_table, render_profile
from acp.suite import run_suite_in_docker


def profile_repo(root: Path, name: str, run_suite: bool = True) -> RepoProfile:
    profile = RepoProfile(
        name=name,
        size=size.measure(root),
        readability=readability.measure(root),
        runtime_typing=runtime_typing.measure(root),
        coupling=coupling.measure(root),
        domain=domain.measure(root),
    )
    if run_suite:
        profile.suite = run_suite_in_docker(root)
    return profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="acp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    profile_parser = subparsers.add_parser("profile", help="perfila un repo candidato")
    profile_parser.add_argument("path", type=Path)
    profile_parser.add_argument("--name", required=True)
    profile_parser.add_argument("--out", type=Path, default=Path("out"))
    profile_parser.add_argument("--no-suite", action="store_true")

    table_parser = subparsers.add_parser("table", help="tabla comparativa de las fichas existentes")
    table_parser.add_argument("--out", type=Path, default=Path("out"))

    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    if args.command == "profile":
        profile = profile_repo(args.path, name=args.name, run_suite=not args.no_suite)
        destination = args.out / f"{args.name}.md"
        destination.write_text(render_profile(profile), encoding="utf-8")
        import json

        (args.out / f"{args.name}.json").write_text(
            json.dumps(profile.to_flat_dict(), indent=2), encoding="utf-8"
        )
        print(f"escrito {destination}")
        return 0

    if args.command == "table":
        import json

        profiles = []
        for path in sorted(args.out.glob("*.json")):
            flat = json.loads(path.read_text(encoding="utf-8"))
            profiles.append(_profile_from_flat(flat))
        destination = args.out / "comparison.md"
        destination.write_text(comparison_table(profiles), encoding="utf-8")
        print(f"escrito {destination}")
        return 0

    return 1


def _profile_from_flat(flat: dict) -> RepoProfile:
    from acp.models import (
        CouplingMetrics,
        DomainMetrics,
        ReadabilityMetrics,
        RuntimeTypingMetrics,
        SizeMetrics,
        SuiteMetrics,
    )

    def group(prefix: str) -> dict:
        return {
            key.split(".", 1)[1]: value
            for key, value in flat.items()
            if key.startswith(f"{prefix}.")
        }

    return RepoProfile(
        name=flat["name"],
        size=SizeMetrics(**group("size")),
        readability=ReadabilityMetrics(**group("readability")),
        runtime_typing=RuntimeTypingMetrics(**group("runtime_typing")),
        coupling=CouplingMetrics(**group("coupling")),
        domain=DomainMetrics(**group("domain")),
        suite=SuiteMetrics(**group("suite")),
    )


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Esperado: PASS

- [ ] **Step 5: Ejecutar la suite completa**

Run: `.venv\Scripts\python.exe -m pytest -v`
Esperado: PASS, todos los tests salvo los marcados `integration`, que no se ejecutan

- [ ] **Step 6: Commit**

```bash
git add src/acp/cli.py tests/test_cli.py
git commit -m "feat: profiling CLI"
```

---

## Task 11: Perfilar los candidatos y elegir tres finalistas

Esta tarea no escribe código: produce el entregable de la fase 0 (§3.2 del spec).

**Files:**
- Create: `out/*.md` y `out/comparison.md` en el repo de código (fuera de control de versiones)
- Create: `C:/Users/Usuario/GitHub/personal-website/docs/superpowers/specs/2026-08-14-fase-0-resultados.md`

**Candidatos iniciales.** Elegidos por tener lógica de dominio propia y suite real; la lista puede ampliarse si alguno cae:

| Repo | Por qué es candidato |
|---|---|
| `hgrecco/pint` | Unidades y dimensiones: conversiones, precedencias, invariantes. Dominio puro |
| `arthurdejong/python-stdnum` | Validación de identificadores por país: un módulo por regla, muy modular |
| `vacanza/holidays` | Reglas de calendario por jurisdicción, suite grande |
| `python-babel/babel` | Plurales, formatos y zonas: reglas densas y no obvias |
| `tobymao/sqlglot` | Dialectos SQL: transformaciones con reglas propias |
| `dateutil/dateutil` | Recurrencias y husos: dominio clásico de fallos sutiles |
| `py-moneyed/py-moneyed` | Dinero y redondeo: pequeño, quizá por debajo del umbral |
| `python-jsonschema/jsonschema` | Reglas de validación encadenadas |

- [ ] **Step 1: Comprobar espacio en disco antes de clonar**

```powershell
Get-PSDrive C | Select-Object Used, Free
```
Esperado: al menos 10 GB libres. Si no los hay, liberar antes de continuar (§2 del spec).

- [ ] **Step 2: Clonar los candidatos en superficie**

```powershell
New-Item -ItemType Directory -Force candidates
git clone --depth 1 https://github.com/hgrecco/pint candidates/pint
git clone --depth 1 https://github.com/arthurdejong/python-stdnum candidates/python-stdnum
git clone --depth 1 https://github.com/vacanza/holidays candidates/holidays
git clone --depth 1 https://github.com/python-babel/babel candidates/babel
git clone --depth 1 https://github.com/tobymao/sqlglot candidates/sqlglot
git clone --depth 1 https://github.com/dateutil/dateutil candidates/dateutil
git clone --depth 1 https://github.com/py-moneyed/py-moneyed candidates/py-moneyed
git clone --depth 1 https://github.com/python-jsonschema/jsonschema candidates/jsonschema
```

- [ ] **Step 3: Perfilado estático de todos, sin suite**

```powershell
foreach ($name in @("pint","python-stdnum","holidays","babel","sqlglot","dateutil","py-moneyed","jsonschema")) {
  .venv\Scripts\python.exe -m acp.cli profile "candidates/$name" --name $name --out out --no-suite
}
.venv\Scripts\python.exe -m acp.cli table --out out
```
Esperado: ocho ficheros `out/<nombre>.md` y `out/comparison.md`.

- [ ] **Step 4: Descartar por criterios estáticos**

Leer `out/comparison.md` y descartar los que incumplan admisión: tipado en ejecución detectado, menos de 2.000 líneas, más de 80.000. Anotar el descarte y su razón.

- [ ] **Step 5: Ejecutar la suite solo de los supervivientes**

Uno por uno, nunca en paralelo (§2 del spec):

```powershell
.venv\Scripts\python.exe -m acp.cli profile "candidates/<nombre>" --name <nombre> --out out
```
Esperado: `suite.ran = true` y cero fallos. Un repo cuya suite no arranca limpia queda descartado.

- [ ] **Step 6: Anotar el riesgo de contaminación**

Quinta dimensión de examen del spec (§3.2). No se automatiza: se consulta y se apunta en la ficha.

```powershell
foreach ($repo in @("hgrecco/pint","arthurdejong/python-stdnum","vacanza/holidays","python-babel/babel","tobymao/sqlglot","dateutil/dateutil","py-moneyed/py-moneyed","python-jsonschema/jsonschema")) {
  gh api "repos/$repo" --jq '"\(.full_name)\t\(.stargazers_count) estrellas\tcreado \(.created_at)\túltimo push \(.pushed_at)"'
}
```

Entre dos candidatos equivalentes en el resto de dimensiones, gana el menos visto. La popularidad
no es criterio de exclusión — los fallos son inyectados y de dominio, así que la contaminación pesa
mucho menos que en un benchmark de issues reales — pero sí es criterio de desempate, y va escrito
en el artículo.

- [ ] **Step 7: Inspección manual de la muestra de dominio**

Para cada superviviente, abrir cinco funciones de `samples` en su ficha y contestar por escrito: ¿se podría introducir aquí un fallo que **solo** se detecte entendiendo la regla de negocio, y que exija leer más de un fichero para juzgarlo? Es el juicio que el proxy no puede dar, y el que decide la viabilidad del estrato de dominio (§3.3.1).

- [ ] **Step 8: Escribir el documento de resultados**

Crear `personal-website/docs/superpowers/specs/2026-08-14-fase-0-resultados.md` con: la tabla comparativa, un párrafo por candidato descartado con su razón, los tres finalistas con la justificación en las cinco dimensiones de examen del spec, y la respuesta a si el lenguaje sigue siendo el adecuado.

- [ ] **Step 9: Limpiar**

```powershell
Remove-Item -Recurse -Force candidates
Get-PSDrive C | Select-Object Used, Free
```
Obligatorio por §2 del spec. Las fichas quedan en `out/`, que ocupa kilobytes.

- [ ] **Step 10: Commit en los dos repos**

```bash
git -C C:/Users/Usuario/GitHub/agent-code-practices add -A
git -C C:/Users/Usuario/GitHub/agent-code-practices commit -m "chore: phase 0 profiling run"

git -C C:/Users/Usuario/GitHub/personal-website add docs/superpowers/specs/2026-08-14-fase-0-resultados.md
git -C C:/Users/Usuario/GitHub/personal-website commit -m "docs: phase 0 results and the three finalists"
```

---

## Checkpoint

La fase 0 termina aquí. Antes de planificar la fase 1 (transformadores y verificación de equivalencia) hace falta revisar los tres finalistas, porque de ellos dependen decisiones del transformador: si ninguno tiene jerarquía profunda, B2 pierde sentido; si la densidad de dominio es baja en todos, el estrato de dominio hay que replantearlo antes de construir nada más.
