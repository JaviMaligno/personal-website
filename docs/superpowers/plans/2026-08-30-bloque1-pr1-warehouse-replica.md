# Bloque 1 / PR1 — Warehouse y réplica de la Tabla 1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproducir la Tabla 1 de SKILL.state (arXiv 2608.26263) sobre el entorno Warehouse con los cuatro runtimes originales y Claude Haiku 4.5, en un repositorio nuevo y público.

**Architecture:** Repositorio Python independiente. Tres capas con fronteras explícitas: entornos (generan observaciones y conocen la acción correcta), runtimes (deciden qué contexto ve el modelo en cada paso), y un corredor que los cruza y contabiliza tokens. Los runtimes no saben nada del dominio; los entornos no saben nada de LLMs. Un cliente falso permite testear todos los runtimes sin gastar un token.

**Tech Stack:** Python 3.11+, `anthropic` SDK, pytest, numpy, scipy (t-test), pandas (agregación).

---

## Alcance de este PR

Del spec `docs/superpowers/specs/2026-08-30-relevancia-diferida-design.md`, **solo** esto:

- Andamiaje del repositorio.
- Entorno Warehouse Management (§4).
- Los cuatro runtimes originales: ReAct, Memory, Stateful, SKILL.state (§5, brazos 1–3 y 5 del paper; el nuestro de compaction realista y CWL llegan después).
- Corredor, métricas y réplica de la Tabla 1 a T ∈ {10, 25, 50, 100}, 5 seeds, **solo Haiku 4.5**.

**Fuera de este PR, deliberadamente:** Software Repository, InterCode CTF, τ-Bench, todas las sondas, el brazo de presupuesto igualado, CWL, y el segundo modelo. Cada uno tiene su propio PR tras el checkpoint.

**Sobre temperatura:** ningún modelo de razonamiento admite `temperature`, en ningún
proveedor, así que la determinación bit a bit del paper no está disponible y no se persigue
(spec §8). Haiku 4.5 sí la acepta y se usa a 0 porque sale gratis. PR1 corre solo con Haiku
4.5 por alcance, no por reproducibilidad: el segundo modelo entra en el PR siguiente.

---

## Estructura de ficheros

Repositorio nuevo: `delayed-relevance` (público, cuenta `JaviMaligno`).

| Fichero | Responsabilidad |
|---|---|
| `pyproject.toml` | Dependencias y configuración de pytest |
| `src/dr/types.py` | `Observation`, `Action`, `StepResult` — vocabulario común entre capas |
| `src/dr/envs/base.py` | Protocolo `Environment` |
| `src/dr/envs/warehouse.py` | Warehouse Management: generación por seed, transiciones, acción esperada |
| `src/dr/llm.py` | Cliente Anthropic + contabilidad de tokens + `FakeClient` para tests |
| `src/dr/runtimes/base.py` | Protocolo `Runtime` |
| `src/dr/runtimes/react.py` | ReAct: transcript creciente |
| `src/dr/runtimes/memory.py` | Memory: resumen + ventana de 3 pasos |
| `src/dr/runtimes/stateful.py` | Stateful: bloque de estado **junto al** transcript completo |
| `src/dr/runtimes/skillstate.py` | SKILL.state: `(P, Σ_t, O_t)`, parche JSON, razonamiento descartado |
| `src/dr/runner.py` | Bucle de episodio, seeds, recolección de métricas |
| `src/dr/metrics.py` | Score, agregación media ± SD, paired t-test |
| `experiments/replicate_table1.py` | Script de la réplica |

Los cuatro runtimes comparten protocolo y no comparten código de dominio: cada uno es un fichero pequeño que se entiende solo.

**Concurrencia:** pytest en serie. No instalar `pytest-xdist` ni pasar `-n`. Las corridas contra la API también van en serie.

---

### Task 1: Andamiaje del repositorio

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/dr/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Crear el repositorio y entrar en él**

```bash
gh auth switch --user JaviMaligno
mkdir delayed-relevance && cd delayed-relevance
git init -b main
```

- [ ] **Step 2: Escribir `pyproject.toml`**

```toml
[project]
name = "delayed-relevance"
version = "0.1.0"
description = "Replicacion de SKILL.state y medicion de relevancia diferida en runtimes de agente"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=1.0",
    "numpy>=2.0",
    "scipy>=1.14",
    "pandas>=2.2",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 3: Escribir `.gitignore`**

```
__pycache__/
*.egg-info/
.venv/
results/
.env
```

- [ ] **Step 4: Escribir `README.md`**

```markdown
# delayed-relevance

Replicacion de [SKILL.state](https://arxiv.org/abs/2608.26263) y medicion de la frontera
que el paper declara y no mide: que pasa cuando una observacion se vuelve relevante `k`
pasos despues de haber sido observada.

Diseno completo: ver el spec enlazado desde el articulo.

## Uso

    pip install -e ".[dev]"
    export ANTHROPIC_API_KEY=...
    pytest
    python experiments/replicate_table1.py --horizon 10 --seeds 1 --model claude-haiku-4-5
```

- [ ] **Step 5: Crear paquetes vacíos**

```bash
mkdir -p src/dr/envs src/dr/runtimes tests experiments
touch src/dr/__init__.py src/dr/envs/__init__.py src/dr/runtimes/__init__.py tests/__init__.py
```

- [ ] **Step 6: Instalar y verificar que pytest arranca**

Run: `pip install -e ".[dev]" && pytest`
Expected: `no tests ran` (exit code 5), sin errores de import.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: andamiaje del repositorio"
```

---

### Task 2: Vocabulario común

**Files:**
- Create: `src/dr/types.py`
- Test: `tests/test_types.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_types.py
from dr.types import Observation, Action, StepResult


def test_observation_renders_as_text():
    obs = Observation(step=3, text="incoming pallet of 12 units of SKU-A", actionable=True)
    assert obs.render() == "[step 3] incoming pallet of 12 units of SKU-A"


def test_action_roundtrips_through_string():
    action = Action(name="Store", args={"shelf": 17, "sku": "SKU-A", "qty": 12})
    assert Action.parse(action.render()) == action


def test_action_parse_returns_none_on_garbage():
    assert Action.parse("no soy una accion") is None


def test_step_result_records_correctness():
    result = StepResult(step=1, actionable=True, correct=True, prompt_tokens=100, output_tokens=20)
    assert result.correct is True
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_types.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.types'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/types.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Observation:
    step: int
    text: str
    actionable: bool

    def render(self) -> str:
        return f"[step {self.step}] {self.text}"


@dataclass(frozen=True)
class Action:
    name: str
    args: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        return f"{self.name}({json.dumps(self.args, sort_keys=True)})"

    @classmethod
    def parse(cls, text: str) -> Action | None:
        match = re.search(r"([A-Za-z]+)\((\{.*\})\)", text, re.DOTALL)
        if match is None:
            return None
        try:
            args = json.loads(match.group(2))
        except json.JSONDecodeError:
            return None
        if not isinstance(args, dict):
            return None
        return cls(name=match.group(1), args=args)


@dataclass(frozen=True)
class StepResult:
    step: int
    actionable: bool
    correct: bool
    prompt_tokens: int
    output_tokens: int
    state_size: int = 0
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_types.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/types.py tests/test_types.py
git commit -m "feat: vocabulario comun de observaciones, acciones y resultados"
```

---

### Task 3: Protocolo de entorno

**Files:**
- Create: `src/dr/envs/base.py`
- Test: `tests/test_env_protocol.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_env_protocol.py
from dr.envs.base import Environment
from dr.types import Action, Observation


class DummyEnv:
    def __init__(self) -> None:
        self.steps = 0

    def reset(self) -> Observation:
        return Observation(step=0, text="hola", actionable=False)

    def observe(self) -> Observation:
        return Observation(step=self.steps, text="hola", actionable=False)

    def expected_action(self) -> Action:
        return Action(name="Wait")

    def apply(self, action: Action) -> None:
        self.steps += 1

    @property
    def done(self) -> bool:
        return self.steps >= 1

    def spec(self) -> str:
        return "dummy"

    def schema_fields(self) -> list[str]:
        return []


def test_dummy_satisfies_protocol():
    assert isinstance(DummyEnv(), Environment)
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_env_protocol.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.envs.base'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/envs/base.py
from __future__ import annotations

from typing import Protocol, runtime_checkable

from dr.types import Action, Observation


@runtime_checkable
class Environment(Protocol):
    """Un entorno genera observaciones y sabe cual era la accion correcta.

    No sabe nada de LLMs ni de runtimes: solo de su propio dominio.
    """

    def reset(self) -> Observation:
        """Estado inicial. Devuelve la primera observacion."""

    def observe(self) -> Observation:
        """Observacion del paso actual, sin avanzar."""

    def expected_action(self) -> Action:
        """Accion correcta para la observacion actual, segun el estado verdadero."""

    def apply(self, action: Action) -> None:
        """Aplica la accion del agente y avanza un paso."""

    @property
    def done(self) -> bool:
        """True cuando se agoto el horizonte."""

    def spec(self) -> str:
        """Especificacion procedimental inmutable P que se pasa al modelo."""

    def schema_fields(self) -> list[str]:
        """Campos del esquema de estado para los runtimes que lo usen."""
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_env_protocol.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/envs/base.py tests/test_env_protocol.py
git commit -m "feat: protocolo de entorno"
```

---

### Task 4: Warehouse — generación determinista por seed

**Files:**
- Create: `src/dr/envs/warehouse.py`
- Test: `tests/test_warehouse_generation.py`

El entorno sigue la descripción de su §4.1: 500 estanterías independientes, acciones
`Store`, `Move`, `Ship`, `Wait`. Cada paso emite un evento. Los eventos accionables exigen
recordar dónde puso el agente cada SKU en pasos anteriores — esa es la demanda de memoria a
horizonte largo que el entorno mide.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_warehouse_generation.py
from dr.envs.warehouse import Warehouse


def test_same_seed_gives_same_event_sequence():
    a = [Warehouse(horizon=10, seed=7).script[i].text for i in range(10)]
    b = [Warehouse(horizon=10, seed=7).script[i].text for i in range(10)]
    assert a == b


def test_different_seed_gives_different_sequence():
    a = [Warehouse(horizon=10, seed=7).script[i].text for i in range(10)]
    b = [Warehouse(horizon=10, seed=8).script[i].text for i in range(10)]
    assert a != b


def test_script_has_exactly_horizon_events():
    assert len(Warehouse(horizon=25, seed=1).script) == 25


def test_first_event_is_always_a_store():
    # No se puede pedir un envio antes de haber almacenado nada.
    assert Warehouse(horizon=10, seed=3).script[0].text.startswith("incoming pallet")


def test_shelf_count_is_500():
    assert len(Warehouse(horizon=10, seed=1).shelves) == 500
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_warehouse_generation.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.envs.warehouse'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/envs/warehouse.py
from __future__ import annotations

import random

from dr.types import Action, Observation

SKUS = [f"SKU-{chr(ord('A') + i)}" for i in range(12)]
SHELF_COUNT = 500


class Warehouse:
    """Inventario discreto y determinista sobre 500 estanterias independientes."""

    def __init__(self, horizon: int, seed: int) -> None:
        self.horizon = horizon
        self.seed = seed
        self.rng = random.Random(seed)
        self.shelves: dict[int, tuple[str, int] | None] = {i: None for i in range(SHELF_COUNT)}
        self.step_index = 0
        self.script: list[Observation] = self._build_script()

    def _build_script(self) -> list[Observation]:
        rng = random.Random(self.seed)
        script: list[Observation] = []
        stored: list[str] = []
        for step in range(self.horizon):
            force_store = step == 0 or not stored
            kind = "store" if force_store else rng.choice(["store", "ship", "telemetry"])
            if kind == "store":
                sku = rng.choice(SKUS)
                qty = rng.randint(1, 20)
                stored.append(sku)
                text = f"incoming pallet of {qty} units of {sku}"
                script.append(Observation(step=step, text=text, actionable=True))
            elif kind == "ship":
                sku = rng.choice(stored)
                text = f"order received for {sku}"
                script.append(Observation(step=step, text=text, actionable=True))
            else:
                text = rng.choice(
                    [
                        "conveyor belt 3 reports nominal throughput",
                        "night shift roster updated",
                        "humidity sensor calibration completed",
                    ]
                )
                script.append(Observation(step=step, text=text, actionable=False))
        return script
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_warehouse_generation.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/envs/warehouse.py tests/test_warehouse_generation.py
git commit -m "feat: generacion determinista del entorno Warehouse"
```

---

### Task 5: Warehouse — transiciones y acción esperada

**Files:**
- Modify: `src/dr/envs/warehouse.py`
- Test: `tests/test_warehouse_transitions.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_warehouse_transitions.py
from dr.envs.warehouse import Warehouse
from dr.types import Action


def test_store_expects_first_empty_shelf():
    env = Warehouse(horizon=5, seed=3)
    env.reset()
    expected = env.expected_action()
    assert expected.name == "Store"
    assert expected.args["shelf"] == 0


def test_store_places_stock_on_the_shelf_the_agent_chose():
    env = Warehouse(horizon=5, seed=3)
    env.reset()
    sku = env.observe().text.split()[-1]
    env.apply(Action(name="Store", args={"shelf": 42, "sku": sku, "qty": 5}))
    assert env.shelves[42] == (sku, 5)


def test_ship_expects_a_shelf_that_actually_holds_the_sku():
    # La accion correcta de Ship depende de donde puso el agente la mercancia,
    # no de una posicion fija: esa es la demanda de memoria que mide el entorno.
    env = Warehouse(horizon=30, seed=11)
    env.reset()
    sku = env.observe().text.split()[-1]
    env.apply(Action(name="Store", args={"shelf": 99, "sku": sku, "qty": 5}))
    assert env.shelves[99] == (sku, 5)
    while not env.done and not env.observe().text.startswith("order received"):
        env.apply(env.expected_action())
    if not env.done:
        expected = env.expected_action()
        ordered_sku = env.observe().text.split()[-1]
        assert env.shelves[expected.args["shelf"]][0] == ordered_sku


def test_non_actionable_event_expects_wait():
    env = Warehouse(horizon=40, seed=5)
    env.reset()
    while not env.done and env.observe().actionable:
        env.apply(env.expected_action())
    if not env.done:
        assert env.expected_action().name == "Wait"


def test_done_after_horizon():
    env = Warehouse(horizon=3, seed=1)
    env.reset()
    for _ in range(3):
        env.apply(env.expected_action())
    assert env.done is True
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_warehouse_transitions.py -v`
Expected: FAIL con `AttributeError: 'Warehouse' object has no attribute 'reset'`

- [ ] **Step 3: Añadir los métodos a `Warehouse`**

```python
    # src/dr/envs/warehouse.py  (añadir dentro de la clase Warehouse)

    def reset(self) -> Observation:
        self.shelves = {i: None for i in range(SHELF_COUNT)}
        self.step_index = 0
        return self.script[0]

    def observe(self) -> Observation:
        return self.script[self.step_index]

    @property
    def done(self) -> bool:
        return self.step_index >= self.horizon

    def _first_empty_shelf(self) -> int:
        for index in range(SHELF_COUNT):
            if self.shelves[index] is None:
                return index
        raise RuntimeError("almacen lleno")

    def _shelf_holding(self, sku: str) -> int | None:
        for index, content in self.shelves.items():
            if content is not None and content[0] == sku:
                return index
        return None

    def expected_action(self) -> Action:
        obs = self.observe()
        if not obs.actionable:
            return Action(name="Wait")
        words = obs.text.split()
        if obs.text.startswith("incoming pallet"):
            qty, sku = int(words[3]), words[-1]
            return Action(
                name="Store",
                args={"shelf": self._first_empty_shelf(), "sku": sku, "qty": qty},
            )
        sku = words[-1]
        shelf = self._shelf_holding(sku)
        if shelf is None:
            return Action(name="Wait")
        return Action(name="Ship", args={"shelf": shelf, "sku": sku})

    def apply(self, action: Action) -> None:
        if action.name == "Store":
            shelf = action.args.get("shelf")
            sku = action.args.get("sku")
            qty = action.args.get("qty")
            if isinstance(shelf, int) and 0 <= shelf < SHELF_COUNT:
                self.shelves[shelf] = (str(sku), int(qty or 0))
        elif action.name == "Ship":
            shelf = action.args.get("shelf")
            if isinstance(shelf, int) and 0 <= shelf < SHELF_COUNT:
                self.shelves[shelf] = None
        elif action.name == "Move":
            source, target = action.args.get("from"), action.args.get("to")
            if isinstance(source, int) and isinstance(target, int):
                self.shelves[target] = self.shelves.get(source)
                self.shelves[source] = None
        self.step_index += 1

    def spec(self) -> str:
        return (
            "You operate a warehouse with 500 shelves numbered 0-499.\n"
            "At each step you receive one event and must reply with exactly one action.\n"
            "Actions:\n"
            '  Store({"shelf": <int>, "sku": "<str>", "qty": <int>}) '
            "- put an incoming pallet on the lowest-numbered empty shelf.\n"
            '  Ship({"shelf": <int>, "sku": "<str>"}) '
            "- fulfil an order from the shelf where that SKU is currently stored.\n"
            '  Move({"from": <int>, "to": <int>}) - relocate stock.\n'
            '  Wait({}) - the event needs no action.\n'
        )

    def schema_fields(self) -> list[str]:
        return ["shelf_contents", "last_event"]
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_warehouse_transitions.py -v`
Expected: 5 passed

- [ ] **Step 5: Ejecutar la suite completa**

Run: `pytest`
Expected: todos pasan

- [ ] **Step 6: Commit**

```bash
git add src/dr/envs/warehouse.py tests/test_warehouse_transitions.py
git commit -m "feat: transiciones y accion esperada del entorno Warehouse"
```

---

### Task 6: Cliente de modelo con contabilidad de tokens

**Files:**
- Create: `src/dr/llm.py`
- Test: `tests/test_llm.py`

`FakeClient` es lo que permite testear los cuatro runtimes sin gastar un token. Devuelve
respuestas de una cola y registra los prompts que recibió, que es justo lo que hay que
inspeccionar para comprobar que cada runtime construye el contexto que dice construir.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_llm.py
from dr.llm import FakeClient, Completion


def test_fake_client_returns_queued_responses_in_order():
    client = FakeClient(responses=["primera", "segunda"])
    assert client.complete(system="s", user="u").text == "primera"
    assert client.complete(system="s", user="u").text == "segunda"


def test_fake_client_records_prompts_it_received():
    client = FakeClient(responses=["x"])
    client.complete(system="spec", user="observacion")
    assert client.calls == [("spec", "observacion")]


def test_fake_client_reports_token_counts():
    client = FakeClient(responses=["hola"])
    completion = client.complete(system="a b c", user="d e")
    assert completion.prompt_tokens == 5
    assert completion.output_tokens == 1


def test_fake_client_raises_when_exhausted():
    client = FakeClient(responses=[])
    try:
        client.complete(system="s", user="u")
    except IndexError:
        return
    raise AssertionError("deberia haber lanzado IndexError")
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_llm.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.llm'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/llm.py
from __future__ import annotations

from dataclasses import dataclass, field

import anthropic


@dataclass(frozen=True)
class Completion:
    text: str
    prompt_tokens: int
    output_tokens: int


@dataclass
class FakeClient:
    """Cliente determinista para tests. Cuenta tokens como palabras."""

    responses: list[str]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str) -> Completion:
        self.calls.append((system, user))
        text = self.responses.pop(0)
        return Completion(
            text=text,
            prompt_tokens=len(system.split()) + len(user.split()),
            output_tokens=len(text.split()),
        )


class AnthropicClient:
    """Cliente real. Temperatura 0 para reproducibilidad; solo valido en Haiku 4.5."""

    def __init__(self, model: str = "claude-haiku-4-5", max_tokens: int = 2048) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic()

    def complete(self, system: str, user: str) -> Completion:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return Completion(
            text=text,
            prompt_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_llm.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/llm.py tests/test_llm.py
git commit -m "feat: cliente de modelo con contabilidad de tokens y doble falso"
```

---

### Task 7: Protocolo de runtime y runtime ReAct

**Files:**
- Create: `src/dr/runtimes/base.py`
- Create: `src/dr/runtimes/react.py`
- Test: `tests/test_react.py`

Plantilla tomada de su Apéndice A.1.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_react.py
from dr.envs.warehouse import Warehouse
from dr.llm import FakeClient
from dr.runtimes.react import ReActRuntime
from dr.types import Observation


def test_first_prompt_contains_the_spec_and_the_observation():
    client = FakeClient(responses=['Action: Store({"shelf": 0, "sku": "SKU-A", "qty": 1})'])
    runtime = ReActRuntime(client=client, spec="ESPEC")
    runtime.act(Observation(step=0, text="evento uno", actionable=True))
    system, user = client.calls[0]
    assert "ESPEC" in system
    assert "evento uno" in user


def test_second_prompt_still_contains_the_first_observation():
    client = FakeClient(responses=["Action: Wait({})", "Action: Wait({})"])
    runtime = ReActRuntime(client=client, spec="ESPEC")
    runtime.act(Observation(step=0, text="evento uno", actionable=False))
    runtime.act(Observation(step=1, text="evento dos", actionable=False))
    _, user = client.calls[1]
    assert "evento uno" in user
    assert "evento dos" in user


def test_prompt_grows_with_history():
    client = FakeClient(responses=["Action: Wait({})"] * 3)
    runtime = ReActRuntime(client=client, spec="ESPEC")
    sizes = []
    for step in range(3):
        runtime.act(Observation(step=step, text=f"evento {step}", actionable=False))
        sizes.append(len(client.calls[-1][1]))
    assert sizes[0] < sizes[1] < sizes[2]


def test_returns_the_parsed_action():
    client = FakeClient(responses=['Action: Store({"shelf": 4, "sku": "SKU-B", "qty": 2})'])
    runtime = ReActRuntime(client=client, spec="ESPEC")
    action, _ = runtime.act(Observation(step=0, text="evento", actionable=True))
    assert action.name == "Store"
    assert action.args["shelf"] == 4
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_react.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.runtimes.react'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/runtimes/base.py
from __future__ import annotations

from typing import Protocol, runtime_checkable

from dr.llm import Completion
from dr.types import Action, Observation


@runtime_checkable
class Runtime(Protocol):
    """Un runtime decide que contexto ve el modelo en cada paso.

    No sabe nada del dominio: recibe observaciones y devuelve acciones.
    """

    def act(self, observation: Observation) -> tuple[Action | None, Completion]:
        """Consulta al modelo y devuelve la accion elegida y el consumo del paso."""

    def state_size(self) -> int:
        """Tamano del estado explicito en caracteres. Cero si el runtime no tiene."""
```

```python
# src/dr/runtimes/react.py
from __future__ import annotations

from dr.llm import Completion
from dr.types import Action, Observation


class ReActRuntime:
    """Transcript creciente: anade cada observacion, razonamiento y accion."""

    def __init__(self, client, spec: str) -> None:
        self.client = client
        self.spec = spec
        self.history: list[str] = []

    def act(self, observation: Observation) -> tuple[Action | None, Completion]:
        history_block = "\n".join(self.history)
        user = (
            f"History:\n{history_block}\n\n"
            f"Latest Observation: {observation.render()}\n"
            "Generate your next reasoning and action (format 'Action: <cmd>'):"
        )
        completion = self.client.complete(system=f"Instructions:\n{self.spec}", user=user)
        self.history.append(f"Observation: {observation.render()}")
        self.history.append(f"Reasoning & Action: {completion.text}")
        return Action.parse(completion.text), completion

    def state_size(self) -> int:
        return 0
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_react.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/runtimes/base.py src/dr/runtimes/react.py tests/test_react.py
git commit -m "feat: protocolo de runtime y runtime ReAct"
```

---

### Task 8: Runtime Memory

**Files:**
- Create: `src/dr/runtimes/memory.py`
- Test: `tests/test_memory.py`

Plantilla de su Apéndice A.2: resumen acumulado más los 3 pasos más recientes.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_memory.py
from dr.llm import FakeClient
from dr.runtimes.memory import MemoryRuntime
from dr.types import Observation


def _run(runtime, count):
    for step in range(count):
        runtime.act(Observation(step=step, text=f"evento {step}", actionable=False))


def test_keeps_only_the_three_most_recent_turns():
    client = FakeClient(responses=["Action: Wait({})"] * 6 + ["resumen"] * 6)
    runtime = MemoryRuntime(client=client, spec="ESPEC")
    _run(runtime, 6)
    _, user = client.calls[-1]
    assert "evento 5" in user
    assert "evento 1" not in user


def test_older_turns_survive_only_inside_the_summary():
    client = FakeClient(responses=["Action: Wait({})"] * 6 + ["RESUMEN-ACUMULADO"] * 6)
    runtime = MemoryRuntime(client=client, spec="ESPEC")
    _run(runtime, 6)
    _, user = client.calls[-1]
    assert "RESUMEN-ACUMULADO" in user


def test_summary_is_refreshed_with_a_separate_call():
    client = FakeClient(responses=["Action: Wait({})"] * 5 + ["resumen"] * 5)
    runtime = MemoryRuntime(client=client, spec="ESPEC")
    _run(runtime, 5)
    summarising_calls = [call for call in client.calls if "Summarise" in call[0]]
    assert len(summarising_calls) >= 1
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_memory.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.runtimes.memory'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/runtimes/memory.py
from __future__ import annotations

from dr.llm import Completion
from dr.types import Action, Observation

WINDOW = 3


class MemoryRuntime:
    """Resumen acumulado en lenguaje natural mas una ventana de 3 pasos."""

    def __init__(self, client, spec: str) -> None:
        self.client = client
        self.spec = spec
        self.summary = "(empty)"
        self.recent: list[str] = []

    def act(self, observation: Observation) -> tuple[Action | None, Completion]:
        recent_block = "\n".join(self.recent[-WINDOW * 2 :])
        user = (
            f"Summarized History:\n{self.summary}\n\n"
            f"Recent History:\n{recent_block}\n\n"
            f"Latest Observation: {observation.render()}\n"
            "Generate your next reasoning and action (format 'Action: <cmd>'):"
        )
        completion = self.client.complete(system=f"Instructions:\n{self.spec}", user=user)
        self.recent.append(f"Observation: {observation.render()}")
        self.recent.append(f"Response: {completion.text}")
        self._refresh_summary()
        return Action.parse(completion.text), completion

    def _refresh_summary(self) -> None:
        dropped = self.recent[: -WINDOW * 2]
        if not dropped:
            return
        summary_completion = self.client.complete(
            system="Summarise the warehouse execution so far. Be terse and factual.",
            user=f"Previous summary:\n{self.summary}\n\nNewly dropped turns:\n" + "\n".join(dropped),
        )
        self.summary = summary_completion.text
        self.recent = self.recent[-WINDOW * 2 :]

    def state_size(self) -> int:
        return 0
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_memory.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/runtimes/memory.py tests/test_memory.py
git commit -m "feat: runtime Memory con resumen y ventana de tres pasos"
```

---

### Task 9: Runtime Stateful

**Files:**
- Create: `src/dr/runtimes/stateful.py`
- Test: `tests/test_stateful.py`

Plantilla de su Apéndice A.3: bloque de estado estructurado **junto al** transcript
completo. Es el baseline que gasta más tokens de todos.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_stateful.py
import json

from dr.llm import FakeClient
from dr.runtimes.stateful import StatefulRuntime
from dr.types import Observation


def test_prompt_contains_both_state_and_full_history():
    client = FakeClient(
        responses=[
            'StateUpdate: {"shelf_contents": "0:SKU-A"} Action: Wait({})',
            "Action: Wait({})",
        ]
    )
    runtime = StatefulRuntime(client=client, spec="ESPEC", schema_fields=["shelf_contents"])
    runtime.act(Observation(step=0, text="evento uno", actionable=False))
    runtime.act(Observation(step=1, text="evento dos", actionable=False))
    _, user = client.calls[1]
    assert "evento uno" in user
    assert "0:SKU-A" in user


def test_state_update_is_applied():
    client = FakeClient(responses=['StateUpdate: {"shelf_contents": "7:SKU-C"} Action: Wait({})'])
    runtime = StatefulRuntime(client=client, spec="ESPEC", schema_fields=["shelf_contents"])
    runtime.act(Observation(step=0, text="evento", actionable=False))
    assert runtime.state["shelf_contents"] == "7:SKU-C"


def test_malformed_state_update_leaves_state_untouched():
    client = FakeClient(responses=["StateUpdate: {roto Action: Wait({})"])
    runtime = StatefulRuntime(client=client, spec="ESPEC", schema_fields=["shelf_contents"])
    runtime.act(Observation(step=0, text="evento", actionable=False))
    assert runtime.state == {}
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_stateful.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.runtimes.stateful'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/runtimes/stateful.py
from __future__ import annotations

import json
import re
from typing import Any

from dr.llm import Completion
from dr.types import Action, Observation


class StatefulRuntime:
    """Estado estructurado junto al transcript completo (estilo LangGraph)."""

    def __init__(self, client, spec: str, schema_fields: list[str]) -> None:
        self.client = client
        self.spec = spec
        self.schema_fields = schema_fields
        self.state: dict[str, Any] = {}
        self.history: list[str] = []

    def act(self, observation: Observation) -> tuple[Action | None, Completion]:
        history_block = "\n".join(self.history)
        user = (
            f"Current State:\n{json.dumps(self.state, indent=2)}\n\n"
            f"History:\n{history_block}\n\n"
            f"Latest Observation: {observation.render()}\n"
            "Update the state if necessary, provide reasoning, and output 'Action: <cmd>'.\n"
            'To update state, use the format: StateUpdate: {"key": "value"}'
        )
        completion = self.client.complete(system=f"Instructions:\n{self.spec}", user=user)
        self._apply_state_update(completion.text)
        self.history.append(f"Observation: {observation.render()}")
        self.history.append(f"Response: {completion.text}")
        return Action.parse(completion.text), completion

    def _apply_state_update(self, text: str) -> None:
        match = re.search(r"StateUpdate:\s*(\{.*?\})", text, re.DOTALL)
        if match is None:
            return
        try:
            update = json.loads(match.group(1))
        except json.JSONDecodeError:
            return
        if isinstance(update, dict):
            self.state.update(update)

    def state_size(self) -> int:
        return len(json.dumps(self.state))
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_stateful.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/runtimes/stateful.py tests/test_stateful.py
git commit -m "feat: runtime Stateful con estado junto al transcript"
```

---

### Task 10: Runtime SKILL.state

**Files:**
- Create: `src/dr/runtimes/skillstate.py`
- Test: `tests/test_skillstate.py`

El del paper. Plantilla de su Apéndice A.4. Tres propiedades que los tests deben fijar,
porque son la tesis entera: el prompt **nunca** contiene observaciones anteriores, el parche
se mergea con semántica de borrado por `null`, y un parche inválido dispara reintento sin
corromper el estado.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_skillstate.py
import json

from dr.llm import FakeClient
from dr.runtimes.skillstate import SkillStateRuntime
from dr.types import Observation


def _patch(patch: dict, action: str = 'Wait({})') -> str:
    body = json.dumps({"state_patch": patch, "action": action})
    return f"razonamiento intermedio\n```json\n{body}\n```"


def test_prompt_never_contains_previous_observations():
    client = FakeClient(responses=[_patch({"a": 1}), _patch({"b": 2})])
    runtime = SkillStateRuntime(client=client, spec="ESPEC", schema_fields=["a", "b"])
    runtime.act(Observation(step=0, text="evento uno", actionable=False))
    runtime.act(Observation(step=1, text="evento dos", actionable=False))
    _, user = client.calls[1]
    assert "evento dos" in user
    assert "evento uno" not in user


def test_prompt_never_contains_previous_reasoning():
    client = FakeClient(responses=[_patch({"a": 1}), _patch({"b": 2})])
    runtime = SkillStateRuntime(client=client, spec="ESPEC", schema_fields=["a", "b"])
    runtime.act(Observation(step=0, text="evento uno", actionable=False))
    runtime.act(Observation(step=1, text="evento dos", actionable=False))
    _, user = client.calls[1]
    assert "razonamiento intermedio" not in user


def test_patch_merges_into_state():
    client = FakeClient(responses=[_patch({"a": 1}), _patch({"b": 2})])
    runtime = SkillStateRuntime(client=client, spec="ESPEC", schema_fields=["a", "b"])
    runtime.act(Observation(step=0, text="uno", actionable=False))
    runtime.act(Observation(step=1, text="dos", actionable=False))
    assert runtime.state == {"a": 1, "b": 2}


def test_null_deletes_the_key():
    client = FakeClient(responses=[_patch({"a": 1}), _patch({"a": None})])
    runtime = SkillStateRuntime(client=client, spec="ESPEC", schema_fields=["a"])
    runtime.act(Observation(step=0, text="uno", actionable=False))
    runtime.act(Observation(step=1, text="dos", actionable=False))
    assert runtime.state == {}


def test_invalid_patch_triggers_retry_without_corrupting_state():
    client = FakeClient(responses=["esto no es json", _patch({"a": 1})])
    runtime = SkillStateRuntime(client=client, spec="ESPEC", schema_fields=["a"])
    runtime.act(Observation(step=0, text="uno", actionable=False))
    assert runtime.state == {"a": 1}
    assert runtime.invalid_patches == 1


def test_prompt_size_is_flat_across_steps():
    client = FakeClient(responses=[_patch({"a": 1})] * 5)
    runtime = SkillStateRuntime(client=client, spec="ESPEC", schema_fields=["a"])
    for step in range(5):
        runtime.act(Observation(step=step, text="evento", actionable=False))
    sizes = [len(call[1]) for call in client.calls]
    assert max(sizes) - min(sizes) < 40
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_skillstate.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.runtimes.skillstate'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/runtimes/skillstate.py
from __future__ import annotations

import json
import re
from typing import Any

from dr.llm import Completion
from dr.types import Action, Observation

MAX_RETRIES = 2


class SkillStateRuntime:
    """(P, Sigma_t, O_t). El razonamiento se descarta tras validar el parche."""

    def __init__(self, client, spec: str, schema_fields: list[str]) -> None:
        self.client = client
        self.spec = spec
        self.schema_fields = schema_fields
        self.state: dict[str, Any] = {}
        self.invalid_patches = 0

    def _prompt(self, observation: Observation) -> str:
        return (
            "Skill Execution State:\n"
            f"```json\n{json.dumps(self.state, separators=(',', ':'))}\n```\n"
            f"Latest Observation: {observation.render()}\n\n"
            "Provide your response with:\n"
            "1. Step-by-step reasoning (will be discarded after execution)\n"
            "2. A JSON block fenced with ```json ... ``` containing both your State Patch "
            'and your Action. The JSON block MUST have exactly these two keys: '
            '{ "state_patch": { <dict: your state updates, set keys to null to delete> }, '
            '"action": "<string: the exact command you want to execute>" }'
        )

    def act(self, observation: Observation) -> tuple[Action | None, Completion]:
        completion = None
        for _ in range(MAX_RETRIES + 1):
            completion = self.client.complete(
                system=f"Instructions:\n{self.spec}", user=self._prompt(observation)
            )
            parsed = self._parse(completion.text)
            if parsed is not None:
                patch, action_text = parsed
                self._merge(patch)
                return Action.parse(action_text), completion
            self.invalid_patches += 1
        return None, completion

    @staticmethod
    def _parse(text: str) -> tuple[dict[str, Any], str] | None:
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match is None:
            return None
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
        patch = payload.get("state_patch")
        action = payload.get("action")
        if not isinstance(patch, dict) or not isinstance(action, str):
            return None
        return patch, action

    def _merge(self, patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if value is None:
                self.state.pop(key, None)
            else:
                self.state[key] = value

    def state_size(self) -> int:
        return len(json.dumps(self.state))
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_skillstate.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/runtimes/skillstate.py tests/test_skillstate.py
git commit -m "feat: runtime SKILL.state con parche validado y razonamiento descartado"
```

---

### Task 11: Corredor de episodios

**Files:**
- Create: `src/dr/runner.py`
- Test: `tests/test_runner.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_runner.py
import json

from dr.envs.warehouse import Warehouse
from dr.llm import FakeClient
from dr.runner import run_episode
from dr.runtimes.skillstate import SkillStateRuntime


def _patch_response(action_text: str) -> str:
    body = json.dumps({"state_patch": {}, "action": action_text})
    return f"pienso\n```json\n{body}\n```"


def test_runner_produces_one_result_per_step():
    env = Warehouse(horizon=4, seed=2)
    client = FakeClient(responses=[_patch_response("Wait({})")] * 4)
    runtime = SkillStateRuntime(client=client, spec=env.spec(), schema_fields=env.schema_fields())
    results = run_episode(env, runtime)
    assert len(results) == 4


def test_runner_marks_correct_actions():
    env = Warehouse(horizon=4, seed=2)
    correct = []
    probe = Warehouse(horizon=4, seed=2)
    probe.reset()
    for _ in range(4):
        correct.append(probe.expected_action().render())
        probe.apply(probe.expected_action())
    client = FakeClient(responses=[_patch_response(text) for text in correct])
    runtime = SkillStateRuntime(client=client, spec=env.spec(), schema_fields=env.schema_fields())
    results = run_episode(env, runtime)
    assert all(result.correct for result in results)


def test_runner_marks_wrong_actions():
    env = Warehouse(horizon=3, seed=2)
    client = FakeClient(responses=[_patch_response('Ship({"shelf": 499, "sku": "SKU-Z"})')] * 3)
    runtime = SkillStateRuntime(client=client, spec=env.spec(), schema_fields=env.schema_fields())
    results = run_episode(env, runtime)
    assert results[0].correct is False


def test_runner_records_token_usage():
    env = Warehouse(horizon=2, seed=2)
    client = FakeClient(responses=[_patch_response("Wait({})")] * 2)
    runtime = SkillStateRuntime(client=client, spec=env.spec(), schema_fields=env.schema_fields())
    results = run_episode(env, runtime)
    assert all(result.prompt_tokens > 0 for result in results)
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_runner.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.runner'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/runner.py
from __future__ import annotations

from dr.types import StepResult


def run_episode(env, runtime) -> list[StepResult]:
    """Cruza un entorno con un runtime y devuelve un resultado por paso."""
    env.reset()
    results: list[StepResult] = []
    while not env.done:
        observation = env.observe()
        expected = env.expected_action()
        action, completion = runtime.act(observation)
        correct = action is not None and action.render() == expected.render()
        results.append(
            StepResult(
                step=observation.step,
                actionable=observation.actionable,
                correct=correct,
                prompt_tokens=completion.prompt_tokens if completion else 0,
                output_tokens=completion.output_tokens if completion else 0,
                state_size=runtime.state_size(),
            )
        )
        env.apply(action if action is not None else expected)
    return results
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_runner.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/runner.py tests/test_runner.py
git commit -m "feat: corredor de episodios"
```

---

### Task 12: Métricas y agregación

**Files:**
- Create: `src/dr/metrics.py`
- Test: `tests/test_metrics.py`

El score es el suyo: acciones correctas sobre eventos accionables.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_metrics.py
from dr.metrics import score, aggregate, paired_ttest
from dr.types import StepResult


def _result(actionable: bool, correct: bool) -> StepResult:
    return StepResult(step=0, actionable=actionable, correct=correct, prompt_tokens=10, output_tokens=2)


def test_score_counts_only_actionable_events():
    results = [_result(True, True), _result(True, False), _result(False, False)]
    assert score(results) == 0.5


def test_score_is_one_when_all_actionable_are_correct():
    assert score([_result(True, True), _result(False, False)]) == 1.0


def test_score_is_zero_when_there_are_no_actionable_events():
    assert score([_result(False, False)]) == 0.0


def test_aggregate_returns_mean_and_sd():
    summary = aggregate([1.0, 0.8, 0.9])
    assert round(summary.mean, 3) == 0.9
    assert summary.sd > 0


def test_paired_ttest_detects_a_real_difference():
    p = paired_ttest([0.9, 0.91, 0.92, 0.89, 0.90], [0.5, 0.51, 0.49, 0.52, 0.50])
    assert p < 0.01
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `pytest tests/test_metrics.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dr.metrics'`

- [ ] **Step 3: Implementación mínima**

```python
# src/dr/metrics.py
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

from dr.types import StepResult


@dataclass(frozen=True)
class Summary:
    mean: float
    sd: float


def score(results: list[StepResult]) -> float:
    actionable = [result for result in results if result.actionable]
    if not actionable:
        return 0.0
    return sum(1 for result in actionable if result.correct) / len(actionable)


def aggregate(scores: list[float]) -> Summary:
    array = np.asarray(scores, dtype=float)
    return Summary(mean=float(array.mean()), sd=float(array.std(ddof=1)))


def paired_ttest(left: list[float], right: list[float]) -> float:
    _, p_value = stats.ttest_rel(left, right)
    return float(p_value)
```

- [ ] **Step 4: Ejecutar para verificar que pasa**

Run: `pytest tests/test_metrics.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/dr/metrics.py tests/test_metrics.py
git commit -m "feat: score, agregacion y test pareado"
```

---

### Task 13: Script de réplica y humo contra la API real

**Files:**
- Create: `experiments/replicate_table1.py`

- [ ] **Step 1: Escribir el script**

```python
# experiments/replicate_table1.py
"""Replica la Tabla 1 de SKILL.state sobre Warehouse. Corridas en serie, a proposito."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dr.envs.warehouse import Warehouse
from dr.llm import AnthropicClient
from dr.metrics import aggregate, score
from dr.runner import run_episode
from dr.runtimes.memory import MemoryRuntime
from dr.runtimes.react import ReActRuntime
from dr.runtimes.skillstate import SkillStateRuntime
from dr.runtimes.stateful import StatefulRuntime

RUNTIMES = {
    "react": lambda client, env: ReActRuntime(client, env.spec()),
    "memory": lambda client, env: MemoryRuntime(client, env.spec()),
    "stateful": lambda client, env: StatefulRuntime(client, env.spec(), env.schema_fields()),
    "skillstate": lambda client, env: SkillStateRuntime(client, env.spec(), env.schema_fields()),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, required=True)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--out", default="results")
    args = parser.parse_args()

    client = AnthropicClient(model=args.model)
    Path(args.out).mkdir(exist_ok=True)
    table: dict[str, dict[str, float]] = {}

    for name, build in RUNTIMES.items():
        scores, prompts, totals = [], [], []
        for seed in range(args.seeds):
            env = Warehouse(horizon=args.horizon, seed=seed)
            results = run_episode(env, build(client, env))
            scores.append(score(results))
            prompts.append(sum(r.prompt_tokens for r in results) / len(results))
            totals.append(sum(r.prompt_tokens + r.output_tokens for r in results))
            print(f"{name} seed={seed} score={scores[-1]:.2f} tokens={totals[-1]}")
        table[name] = {
            "score_mean": aggregate(scores).mean,
            "score_sd": aggregate(scores).sd,
            "avg_prompt_tokens": aggregate(prompts).mean,
            "total_tokens": aggregate(totals).mean,
        }

    path = Path(args.out) / f"table1_T{args.horizon}_{args.model}.json"
    path.write_text(json.dumps(table, indent=2))
    print(f"escrito {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Corrida de humo, la más barata posible**

Run: `python experiments/replicate_table1.py --horizon 10 --seeds 1 --model claude-haiku-4-5`
Expected: cuatro líneas de score (una por runtime) y un fichero en `results/`. Coste estimado por debajo de $0.10.

**Comprobación que decide si seguir:** `skillstate` debe tener `avg_prompt_tokens` claramente menor que `react`, y ese número **no debe crecer** con el horizonte. Si crece, el runtime está mal implementado y no tiene sentido gastar en la rejilla completa.

- [ ] **Step 3: Commit**

```bash
git add experiments/replicate_table1.py
git commit -m "feat: script de replica de la Tabla 1"
```

- [ ] **Step 4: Publicar el repositorio**

```bash
gh repo create delayed-relevance --public --source=. --remote=origin --push
```

- [ ] **Step 5: Manejar el desbordamiento de contexto en vez de estrellarse**

Riesgo R2 del spec: Haiku 4.5 tiene 200K de ventana, y `react` a T=100 puede no caber. Que
no quepa **es un hallazgo, no un bug** — es la razón de existir de la compactación — así que
se registra en lugar de recortar el baseline.

Modificar `experiments/replicate_table1.py`: envolver la llamada a `run_episode` y anotar el
episodio como desbordado.

```python
import anthropic  # anadir a los imports

# ... dentro del bucle de seeds, sustituir la llamada directa:
            try:
                results = run_episode(env, build(client, env))
            except anthropic.BadRequestError as error:
                if "prompt is too long" not in str(error).lower():
                    raise
                print(f"{name} seed={seed} DESBORDA la ventana de contexto")
                overflowed.append(seed)
                continue
```

Declarar `overflowed: list[int] = []` junto a `scores, prompts, totals`, y añadir
`"overflowed_seeds": overflowed` al diccionario de cada runtime en `table[name]`. Si todas
las seeds de un runtime desbordan, sus métricas quedan vacías y eso es exactamente lo que
hay que reportar en la tabla del artículo.

- [ ] **Step 6: Rejilla completa**

```bash
for T in 10 25 50 100; do
  python experiments/replicate_table1.py --horizon $T --seeds 5 --model claude-haiku-4-5
done
```

Expected: cuatro ficheros en `results/`. Coste estimado ~$25. En serie: no lanzar los cuatro horizontes en paralelo.

- [ ] **Step 7: Commit de resultados**

```bash
git add -f results/
git commit -m "data: replica de la Tabla 1 con Haiku 4.5"
git push
```

---

## Checkpoint — parar aquí

Con `results/` delante, comparar contra su Tabla 1 y responder tres preguntas antes de
escribir una línea más:

1. **¿Reproduce la dirección?** `skillstate` ≥ baselines en score, y muy por debajo en
   tokens acumulados. Si no, aplicar la fila correspondiente de la tabla de criterios de
   parada del spec (§8.1) — con la sospecha primera puesta en nuestra reimplementación, no
   en el paper.
2. **¿El prompt de `skillstate` es plano?** Debe rondar los ~1.800 tokens a todos los
   horizontes. Si crece con T, hay un fallo.
3. **¿Cuánta varianza hay entre seeds?** Es el dato que decide el presupuesto de repeticiones
   de todo lo que viene después. Si la SD entre seeds es del orden del efecto que buscan las
   sondas, hay que subir repeticiones antes de gastar en la rejilla grande. Aquí se ejecuta
   también la medición del ruido de muestreo del spec §8: una celda, misma seed, N repeticiones.

Los siguientes PRs son Software Repository, luego InterCode CTF y τ-Bench, luego las sondas.
