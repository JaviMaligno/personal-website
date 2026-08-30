# Fase 3 — Familia B: partir y fusionar módulos (B1 y B5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Las dos transformaciones que quedan de la familia B: romper la cohesión repartiendo definiciones entre ficheros (B1) y variar el tamaño de fichero concatenando módulos (B5), con la curva de dosis que el spec pide.

**Architecture:** Las dos mueven **definiciones**, no ficheros, y ahí está todo lo difícil. Una definición arrastra lo que usa —imports, constantes del módulo, otras definiciones— así que moverla exige calcular sus nombres libres y llevárselos o importarlos en el destino. Y al juntar dos módulos en uno, dos nombres iguales colisionan. La pieza nueva del núcleo es el análisis de dependencias de una definición, compartido por las dos; y el mapa de identidad pasa de seguir movimientos de módulo a seguir movimientos de **símbolo**.

**Tech Stack:** Python 3.11+, LibCST, `ast`, pytest, Docker vía `acp.runners`.

**Spec:** [`../specs/2026-08-14-software-practices-for-coding-agents-design.md`](../specs/2026-08-14-software-practices-for-coding-agents-design.md), §4.2 (B1, B5), §5.4.2, §6.3 (curva de tamaño).

**Fase 2:** [`../specs/2026-08-19-fase-2-resultados.md`](../specs/2026-08-19-fase-2-resultados.md). B2, B3 y B4 verificadas; cuatro celdas equivalentes con dosis real.

## Global Constraints

- **El nombre del paquete raíz no se transforma nunca** (§5.6).
- **Alcance repo-wide, tests incluidos** (§4.3.1): `iter_transformable_files`, nunca `iter_source_files`.
- **Reproducible**: B1 reparte "al azar" con **seed fijo**; dos corridas de la misma celda tienen que
  producir el mismo árbol o los seeds del 2×2 no son comparables (§5.4.4).
- **Una copia viva por condición**, borrada al cerrar. El original no se toca.
- **Preferir mover de menos a romper el repo**: una dosis más baja se declara y se mide; un repo roto
  se lee igual que un agente que fracasa (§11). Cuando un caso sea irreducible, sácalo del alcance y
  **decláralo en el código y en las notas**, no lo fuerces.
- **TDD estricto**, commit por paso. Suite hoy en `345 passed`, tiene que quedar en verde.
- **Limpia**: clones borrados, contenedores `acp-*` fuera. Disco vigilado.
- Comentarios en español, explicando **por qué**.

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `src/acp/transforms/base.py` | `TransformResult.symbol_moves` |
| `src/acp/symbols.py` | El mapa sigue movimientos de símbolo, no solo de módulo |
| `src/acp/transforms/dependencies.py` | Qué necesita una definición para vivir en otro fichero |
| `src/acp/transforms/b1_cohesion.py` | Reparte definiciones entre ficheros |
| `src/acp/transforms/b5_size.py` | Concatena módulos hasta un techo de líneas |
| `tests/test_transforms_b1.py`, `tests/test_transforms_b5.py` | Uno por transformación |

---

## Task 1: El mapa sigue símbolos, no solo módulos

`moves` es módulo→módulo, y le vale a B2 porque mueve ficheros enteros. B1 mueve **definiciones
sueltas**: dos símbolos del mismo módulo acaban en ficheros distintos, así que un mapa por módulo no
puede describirlo y todos los símbolos movidos se caerían del manifiesto — que es lo que ya pasó en
la fase 2 y dejó la métrica de localización sin datos, en verde.

**Files:**
- Modify: `src/acp/transforms/base.py`, `src/acp/symbols.py`, `src/acp/cli.py`
- Test: `tests/test_symbols.py`

**Interfaces:**
- Produces: `TransformResult.symbol_moves: dict[str, str]` — nombre cualificado original del símbolo
  (la clave del mapa de identidad) → módulo destino; `relocate_symbols(symbols, root, moves=None, symbol_moves=None)`.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_two_symbols_of_the_same_module_can_end_up_in_different_files(tmp_path: Path):
    """Lo que hace B1: `validate` y `compact` viven juntas y acaban separadas.
    Un mapa por módulo no puede describir esto — mandaría las dos al mismo
    sitio— y los símbolos se caerían del manifiesto sin que nada lo diga."""
    original = tmp_path / "before"
    (original / "pkg").mkdir(parents=True)
    (original / "pkg" / "nif.py").write_text(
        "def validate(number):\n"
        "    return number\n"
        "\n"
        "\n"
        "def compact(number):\n"
        "    return number.strip()\n",
        encoding="utf-8",
    )
    symbols = build_symbol_map(original)

    after = tmp_path / "after"
    (after / "pkg").mkdir(parents=True)
    (after / "pkg" / "a.py").write_text("def validate(number):\n    return number\n", encoding="utf-8")
    (after / "pkg" / "b.py").write_text(
        "def compact(number):\n    return number.strip()\n", encoding="utf-8"
    )

    relocated = relocate_symbols(
        symbols, after,
        symbol_moves={"pkg.nif.validate": "pkg.a", "pkg.nif.compact": "pkg.b"},
    )

    assert relocated["pkg.nif.validate"].path == "pkg/a.py"
    assert relocated["pkg.nif.compact"].path == "pkg/b.py"
    assert relocated["pkg.nif.validate"].current_name == "validate"


def test_a_symbol_move_that_lands_nowhere_drops_the_symbol(tmp_path: Path):
    """Antes de mentir, callar: un rango que no se puede verificar contra el
    árbol que ve el agente no es procedencia."""
    original = tmp_path / "before"
    (original / "pkg").mkdir(parents=True)
    (original / "pkg" / "nif.py").write_text("def validate(n):\n    return n\n", encoding="utf-8")
    symbols = build_symbol_map(original)

    after = tmp_path / "after"
    (after / "pkg").mkdir(parents=True)

    relocated = relocate_symbols(symbols, after, symbol_moves={"pkg.nif.validate": "pkg.z"})

    assert relocated == {}
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_symbols.py -k "different_files or lands_nowhere" -v`
Expected: FAIL con `TypeError: relocate_symbols() got an unexpected keyword argument 'symbol_moves'`

- [ ] **Step 3: Implementar**

En `base.py`:

```python
    # Símbolo → módulo destino, para las transformaciones que mueven
    # definiciones sueltas y no ficheros enteros: dos símbolos del mismo módulo
    # pueden acabar en sitios distintos, y `moves` no sabe expresar eso.
    symbol_moves: dict[str, str] = field(default_factory=dict)
```

En `relocate_symbols`, el destino de cada símbolo se decide primero por `symbol_moves` (más
específico), y si no lo nombra, por `moves` del módulo. El emparejamiento posicional dentro del
módulo destino ya no sirve cuando el símbolo viajó solo, así que para esos se busca **por nombre**
dentro del módulo destino y, si el nombre cambió también (A2 corriendo antes), por el nombre que diga
el diccionario de renombrados. Deja escrito en la docstring por qué son dos criterios distintos.

En `cli.py`, acumular `symbol_moves` igual que `renames` y `moves`, y pasarlo a `relocate_symbols`.

- [ ] **Step 4: Verde y commit**

```bash
.venv/bin/python -m pytest tests/test_symbols.py -v
git add src/acp/transforms/base.py src/acp/symbols.py src/acp/cli.py tests/test_symbols.py
git commit -m "feat: follow a symbol that travelled without its module"
```

---

## Task 2: Qué necesita una definición para vivir en otro fichero

Pieza compartida por B1 y B5. Una función no es autónoma: usa imports, constantes del módulo y otras
definiciones. Moverla sin llevarse eso produce un `NameError` en cuanto se ejecuta — y el repo se lee
como un agente que fracasa.

**Files:**
- Create: `src/acp/transforms/dependencies.py`
- Test: `tests/test_transforms_dependencies.py`

**Interfaces:**
- Produces: `free_names(node: ast.AST) -> set[str]`; `module_bindings(tree: ast.Module) -> dict[str, str]` (nombre → qué lo define: `"import"`, `"assign"`, `"def"`).

- [ ] **Step 1: Escribir el test que falla**

```python
from acp.transforms.dependencies import free_names, module_bindings
import ast


def first(source: str) -> ast.AST:
    return ast.parse(source).body[0]


def test_free_names_are_what_the_definition_needs_from_outside():
    node = first(
        "def total(rows):\n"
        "    result = 0\n"
        "    for row in rows:\n"
        "        result += rate(row) * TAX\n"
        "    return result\n"
    )

    assert free_names(node) == {"rate", "TAX"}


def test_parameters_and_locals_are_not_free():
    node = first("def f(a, b=1, *args, **kwargs):\n    c = a + b\n    return c\n")

    assert free_names(node) == set()


def test_a_comprehension_variable_is_not_free():
    node = first("def f(rows):\n    return [x for x in rows if x > LIMIT]\n")

    assert free_names(node) == {"LIMIT"}


def test_module_bindings_say_where_each_name_comes_from():
    tree = ast.parse(
        "import os\n"
        "from math import pi\n"
        "\n"
        "TAX = 0.21\n"
        "\n"
        "\n"
        "def rate(x):\n"
        "    return x\n"
    )

    assert module_bindings(tree) == {
        "os": "import",
        "pi": "import",
        "TAX": "assign",
        "rate": "def",
    }
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_dependencies.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'acp.transforms.dependencies'`

- [ ] **Step 3: Implementar**

`free_names` recorre el nodo llevando la cuenta de lo que está ligado localmente —parámetros,
asignaciones, `for`, `with ... as`, `except ... as`, comprehensions, funciones anidadas— y devuelve
los `ast.Name` en contexto de lectura que no estén ligados. Los builtins **no** se filtran aquí: eso
lo decide quien use la función, porque para B1 un builtin no hay que importarlo y para el informe sí
interesa verlo. Si prefieres filtrarlos, hazlo explícito con `builtins.__dict__` y un test.

`module_bindings` recorre el nivel superior del módulo y clasifica cada nombre por lo que lo define.

- [ ] **Step 4: Verde y commit**

```bash
.venv/bin/python -m pytest tests/test_transforms_dependencies.py -v
git add src/acp/transforms/dependencies.py tests/test_transforms_dependencies.py
git commit -m "feat: work out what a definition needs from its module"
```

---

## Task 3: B1 — cohesión

Reparte las definiciones entre los ficheros que ya existen. **Mismo número de ficheros y mismo tamaño
aproximado**: solo se rompe la lógica de qué vive con qué (§4.2). Eso lo distingue de B5, que cambia
el tamaño sin tocar la organización.

**Files:**
- Create: `src/acp/transforms/b1_cohesion.py`
- Modify: `src/acp/transforms/__init__.py`
- Test: `tests/test_transforms_b1.py`

**Interfaces:**
- Produces: `apply(root: Path, seed: int = 0) -> TransformResult` con `symbol_moves` relleno, registrada como `"B1"`.

- [ ] **Step 1: Escribir el test que falla**

```python
from pathlib import Path

from acp.transforms import b1_cohesion


def build(root: Path) -> None:
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "billing.py").write_text(
        "TAX = 0.21\n"
        "\n"
        "\n"
        "def rate(amount):\n"
        "    return amount * TAX\n"
        "\n"
        "\n"
        "def total(rows):\n"
        "    return sum(rate(row) for row in rows)\n",
        encoding="utf-8",
    )
    (pkg / "report.py").write_text(
        "def render(rows):\n"
        "    return ', '.join(str(row) for row in rows)\n"
        "\n"
        "\n"
        "def header():\n"
        "    return 'informe'\n",
        encoding="utf-8",
    )


def test_the_definitions_end_up_somewhere_else(tmp_path: Path):
    build(tmp_path)

    result = b1_cohesion.apply(tmp_path, seed=1)

    assert result.symbol_moves, "no movió ninguna definición"
    origen = {key.rsplit(".", 1)[0] for key in result.symbol_moves}
    destino = set(result.symbol_moves.values())
    assert origen != destino or any(
        key.rsplit(".", 1)[0] != value for key, value in result.symbol_moves.items()
    )


def test_the_number_of_files_does_not_change(tmp_path: Path):
    """B1 rompe la organización SIN tocar el tamaño; el tamaño es B5. Si las dos
    cosas cambian a la vez, ninguna de las dos celdas es atribuible (§4.2)."""
    build(tmp_path)
    antes = sorted(p.name for p in (tmp_path / "pkg").glob("*.py"))

    b1_cohesion.apply(tmp_path, seed=1)

    assert sorted(p.name for p in (tmp_path / "pkg").glob("*.py")) == antes


def test_the_code_still_runs(tmp_path: Path):
    """Lo que una definición necesita —una constante del módulo, otra función—
    tiene que viajar con ella o importarse en el destino, o el primer uso da
    NameError."""
    build(tmp_path)

    b1_cohesion.apply(tmp_path, seed=1)

    import subprocess
    import sys

    proceso = subprocess.run(
        [sys.executable, "-c",
         "import pkg.billing, pkg.report; "
         "mods = [pkg.billing, pkg.report]; "
         "f = [getattr(m, 'total') for m in mods if hasattr(m, 'total')][0]; "
         "print(f([100]))"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert proceso.returncode == 0, proceso.stderr


def test_the_same_seed_produces_the_same_tree(tmp_path: Path):
    """Sin esto, dos corridas de la misma celda no son la misma condición y los
    seeds del 2×2 dejan de ser comparables (§5.4.4)."""
    build(tmp_path / "una")
    build(tmp_path / "otra")

    primera = b1_cohesion.apply(tmp_path / "una", seed=7)
    segunda = b1_cohesion.apply(tmp_path / "otra", seed=7)

    assert primera.symbol_moves == segunda.symbol_moves


def test_a_different_seed_produces_a_different_tree(tmp_path: Path):
    build(tmp_path / "una")
    build(tmp_path / "otra")

    primera = b1_cohesion.apply(tmp_path / "una", seed=1)
    segunda = b1_cohesion.apply(tmp_path / "otra", seed=2)

    assert primera.symbol_moves != segunda.symbol_moves
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_b1.py -v`
Expected: FAIL con `ImportError: cannot import name 'b1_cohesion'`

- [ ] **Step 3: Implementar**

El orden que funciona:

1. Recoger todas las definiciones de nivel de módulo de los ficheros del paquete, con su código
   fuente exacto (LibCST) y sus nombres libres (Task 2).
2. Barajar con `random.Random(seed)` —nunca el `random` global— y repartirlas entre los mismos
   ficheros, procurando que cada uno reciba un número parecido de líneas.
3. Para cada definición en su destino, resolver sus nombres libres: si el nombre lo define otro
   módulo del repo, añadir el import correspondiente; si lo definía su módulo original y sigue ahí,
   importarlo de donde haya quedado; si es un builtin, no hacer nada.
4. Reescribir los imports de todo el repo que apunten a un símbolo movido: `from pkg.billing import
   total` pasa a apuntar al módulo donde `total` haya caído.
5. Devolver `symbol_moves`.

**Lo que probablemente tengas que dejar fuera, y hay que declarar**: definiciones cuyo movimiento no
se puede resolver sin ejecutar el programa —las que dependen de estado de módulo mutado en tiempo de
import, las que usan `global`, las que un decorador registra por módulo—. Sácalas del reparto y anota
cuántas son sobre cada finalista: es dosis que se pierde y va al artículo.

- [ ] **Step 4: Verde y commit**

```bash
.venv/bin/python -m pytest tests/test_transforms_b1.py -v
git add src/acp/transforms tests/test_transforms_b1.py
git commit -m "feat: B1 breaks what lives with what, and nothing else"
```

---

## Task 4: B5 — tamaño

Concatena módulos hasta un techo de líneas por fichero. Es el único eje que busca un **umbral** en
lugar de una diferencia, así que necesita varios puntos: original, ~500, ~2.000 y ~10.000 líneas
(§6.3).

**Files:**
- Create: `src/acp/transforms/b5_size.py`
- Modify: `src/acp/transforms/__init__.py`
- Test: `tests/test_transforms_b5.py`

**Interfaces:**
- Produces: `apply(root: Path, target_lines: int = 2000) -> TransformResult` con `moves` y
  `symbol_moves`, registrada como `"B5"` (y `B5-500`, `B5-2000`, `B5-10000` como puntos de la curva,
  o el mecanismo que decidas para parametrizarla desde el CLI — déjalo escrito).

- [ ] **Step 1: Escribir el test que falla**

```python
from pathlib import Path

from acp.transforms import b5_size


def build(root: Path, modules: int = 6) -> None:
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for index in range(modules):
        (pkg / f"m{index}.py").write_text(
            f"CONST_{index} = {index}\n"
            "\n"
            "\n"
            f"def f{index}(value):\n"
            f"    return value + CONST_{index}\n",
            encoding="utf-8",
        )


def test_the_modules_end_up_in_fewer_files(tmp_path: Path):
    build(tmp_path)
    antes = len(list((tmp_path / "pkg").glob("*.py")))

    b5_size.apply(tmp_path, target_lines=2000)

    assert len(list((tmp_path / "pkg").glob("*.py"))) < antes


def test_a_smaller_target_leaves_more_files(tmp_path: Path):
    """La curva necesita puntos distintos: si 500 y 10.000 producen el mismo
    árbol, no hay curva que medir (§6.3)."""
    build(tmp_path / "pequeno", modules=12)
    build(tmp_path / "grande", modules=12)

    b5_size.apply(tmp_path / "pequeno", target_lines=8)
    b5_size.apply(tmp_path / "grande", target_lines=10000)

    pequeno = len(list((tmp_path / "pequeno" / "pkg").glob("*.py")))
    grande = len(list((tmp_path / "grande" / "pkg").glob("*.py")))
    assert pequeno > grande


def test_the_code_still_runs(tmp_path: Path):
    build(tmp_path)

    b5_size.apply(tmp_path, target_lines=2000)

    import subprocess
    import sys

    proceso = subprocess.run(
        [sys.executable, "-c", "import pkg; print('ok')"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert proceso.returncode == 0, proceso.stderr


def test_two_modules_that_define_the_same_name_are_not_merged(tmp_path: Path):
    """Al juntarlos en un fichero, la segunda definición pisa a la primera y el
    programa cambia en silencio. Preferimos concatenar de menos: la dosis baja se
    declara, un repo roto se lee como un agente que fracasa."""
    pkg = tmp_path / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text("def validate(x):\n    return x\n", encoding="utf-8")
    (pkg / "b.py").write_text("def validate(x):\n    return x * 2\n", encoding="utf-8")

    b5_size.apply(tmp_path, target_lines=10000)

    fuentes = [p.read_text(encoding="utf-8") for p in (tmp_path / "pkg").glob("*.py")]
    assert not any(fuente.count("def validate") > 1 for fuente in fuentes)
```

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_transforms_b5.py -v`
Expected: FAIL con `ImportError: cannot import name 'b5_size'`

- [ ] **Step 3: Implementar**

1. Agrupar módulos hasta llenar el techo de líneas, en orden determinista.
2. **No agrupar dos módulos que definan el mismo nombre de nivel superior**: la segunda definición
   pisaría a la primera. El test de arriba lo fija.
3. Al concatenar, los imports internos **entre los módulos del grupo** sobran y hay que quitarlos: el
   símbolo ya está en el mismo fichero. Los demás imports se unen sin duplicar.
4. El módulo resultante conserva el nombre de uno de los del grupo; los demás desaparecen, así que
   hay que reescribir en todo el repo los imports que los nombraban, igual que hace B2.
5. Devolver `moves` (los módulos absorbidos) y `symbol_moves`.

- [ ] **Step 4: Verde y commit**

```bash
.venv/bin/python -m pytest tests/test_transforms_b5.py -v
git add src/acp/transforms tests/test_transforms_b5.py
git commit -m "feat: B5 varies file size without touching the organisation"
```

---

## Task 5: Equivalencia sobre repos reales

Donde aparece todo lo que los fixtures no ven — cuatro veces en las dos fases anteriores.

**Files:**
- Modify: `tests/test_equivalence_family_b.py`

- [ ] **Step 1: Añadir las celdas**

Añade B1 y B5 a la matriz existente, sobre python-stdnum (el más barato, 96 s por corrida) y pint.
Cada celda tiene que **exigir dosis**: que falle si la transformación no cambió nada, como ya hacen
las de B2 y B4.

B1 y B5 destruyen la estructura que declara el `pyproject`, igual que B2, así que van con el modo que
instala dependencias y no el repo.

- [ ] **Step 2: Ejecutar**

Run: `.venv/bin/python -m pytest tests/test_equivalence_family_b.py -v`
Expected: PASS. Varios minutos: cada celda son dos corridas de suite en contenedor.

Si falla, **no relajes el test**: diagnostica si es la transformación o la fontanería, arréglalo con
su test de regresión, y anótalo.

- [ ] **Step 3: Commit**

```bash
git add tests/test_equivalence_family_b.py
git commit -m "feat: prove B1 and B5 equivalent on real repositories"
```

---

## Checkpoint

Con esto están las nueve transformaciones y se pueden construir T1, T2 y T3 completas (§6.1). Antes
de la campaña quedan, del pre-flight §3.6: generar las 24 tareas por inyección de fallo, validar el
estrato de dominio por aislamiento, los oráculos de control, y comprobar que el baseline T0 es
discriminante.

Dos cosas que solo se ven al terminar esta fase y hay que medir antes de seguir:

1. **Cuánta dosis pierde B1** por las definiciones que no se pueden mover sin ejecutar el programa.
   Si en los finalistas resulta que la mayoría no se mueve, B1 mide mucho menos de lo que el spec
   supone y hay que decirlo.
2. **Si la curva de B5 tiene puntos distintos de verdad** en los finalistas: con módulos que ya son
   pequeños, ~2.000 y ~10.000 pueden producir el mismo árbol, y entonces la curva tiene menos puntos
   de los que dice §6.3.
