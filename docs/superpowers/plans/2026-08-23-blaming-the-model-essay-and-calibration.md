# Blaming the Model — ensayo y calibración: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** publicar el ensayo de la serie y dejar construido un clasificador de
juguete con cuatro bugs reales inyectables que produzca trazas divergentes
auténticas, listo para la calibración de escenarios.

**Architecture:** un clasificador de repositorios de software en una taxonomía
jerárquica corre sobre un snapshot local de documentos, con tools deterministas
y traza completa. Cuatro bugs se activan por flag y generan divergencia
reproducible entre corridas. Un ensamblador empaqueta código, logs y enunciado
en el escenario que verá el agente investigador. El artículo del ensayo vive en
el repo del blog y es independiente del código.

**Tech Stack:** Python 3.13, pytest, pydantic, Azure OpenAI vía el gateway
privado para el clasificador; Astro y Markdown para el artículo.

**Spec:** `docs/superpowers/specs/2026-08-23-agents-blaming-the-model-design.md`

## Global Constraints

- **Alcance:** este plan termina en el acta de calibración. La rúbrica
  automática, el control sin IA y el run de confirmación son un plan posterior.
- **Anonimización:** ni dominio, ni taxonomía, ni nombres de repositorio
  internos, ni referencias a tickets del trabajo real. Ambos repos son públicos.
- **Fidelidad, no resultado:** durante la calibración los escenarios se iteran
  por realismo. Un escenario se descarta por poco realista, trivial o mal
  instrumentado; **nunca por dar un resultado incómodo**.
- **La divergencia es real:** al agente investigador se le entregan logs de
  corridas ejecutadas de verdad, nunca una descripción textual de la
  variabilidad.
- **El modelo del clasificador no expone `temperature`.** Es un requisito del
  diseño, no un detalle: convierte el reflejo del interruptor en un error
  atrapable.
- **Publicar es merge a `main`.** Ninguna tarea de este plan mergea nada. Una
  rama por artículo, y como mucho un artículo por día.
- **Tests sin red:** toda la suite corre con un modelo falso. Ningún test
  invoca la API.
- **Repo del experimento:** `~/Documents/repos/blaming-the-model`, nuevo y
  público. Crear el directorio requiere confirmación del usuario.

---

## Parte A — El ensayo

### Task 1: Escribir y validar el ensayo

**Files:**
- Create: `src/content/blog/en/blaming-the-model.md`
- Create: `src/content/blog/es/blaming-the-model.md`
- Rama: `blog/agents-blaming-the-model` (ya existe, ya contiene el spec)

**Interfaces:**
- Consumes: la sección "Pieza 1 — Ensayo" del spec (cinco historias y el cierre).
- Produces: nada que consuman tareas posteriores. El artículo es independiente
  del código.

- [ ] **Step 1: Invocar la skill de escritura**

Usar la skill `blog-writer`, que ya conoce el formato bilingüe y el frontmatter
de este sitio. No escribir los ficheros a mano saltándose la skill.

- [ ] **Step 2: Redactar las cinco historias**

Las cinco de la sección "Pieza 1" del spec, en este orden: la traza, la
estocasticidad, el interruptor, el ground truth, el determinismo burdo y su
motivo. El cierre es que el agente y el sistema analizado corren el mismo
modelo.

Tono: sin rotundidad, sin hombre de paja. Son observaciones de trabajo, no una
ley. El artículo puede decir que esto se puede medir y que es el paso natural
—sin fecha, sin prometer resultados—, y **no** debe anunciar dos partes
concretas.

Nada del trabajo real: el clasificador se describe en abstracto, sin dominio ni
taxonomía ni tickets.

- [ ] **Step 3: Verificar el frontmatter contra el schema**

El schema vive en `src/content/config.ts` y exige `title`, `description`,
`pubDate`, `tags`, `lang` y `translationKey`. Ambos idiomas comparten
`translationKey: "blaming-the-model"`. Sin `repoUrl`: esta pieza no lleva código.

```bash
grep -E '^(title|description|pubDate|lang|translationKey):' \
  src/content/blog/en/blaming-the-model.md \
  src/content/blog/es/blaming-the-model.md
```

Esperado: los seis campos en cada fichero, y el mismo `translationKey` en los dos.

- [ ] **Step 4: Verificar que el sitio compila**

Run: `npm run build`
Esperado: build correcto, sin errores de validación de la colección `blog`.

- [ ] **Step 5: Commit**

```bash
git add src/content/blog/en/blaming-the-model.md src/content/blog/es/blaming-the-model.md
git commit -m "Artículo: culpa al modelo lo que no se culparía a sí mismo"
```

No mergear. La publicación es una decisión aparte del usuario.

---

## Parte B — El clasificador y sus bugs

### Task 2: Esqueleto del repo y taxonomía

**Files:**
- Create: `~/Documents/repos/blaming-the-model/pyproject.toml`
- Create: `~/Documents/repos/blaming-the-model/README.md`
- Create: `src/btm/__init__.py`
- Create: `src/btm/taxonomy.py`
- Create: `data/taxonomy.yaml`
- Test: `tests/test_taxonomy.py`

Todas las rutas de aquí en adelante son relativas a
`~/Documents/repos/blaming-the-model`.

**Interfaces:**
- Produces: `Taxonomy.load(path) -> Taxonomy`, `Taxonomy.get(code) -> TaxonomyNode`,
  `Taxonomy.leaves() -> list[TaxonomyNode]`. `TaxonomyNode` es un pydantic
  `BaseModel` con campos `code: str`, `name: str`, `parent: str | None`,
  `description: str`.

- [ ] **Step 1: Crear el repo (requiere confirmación del usuario)**

```bash
mkdir -p ~/Documents/repos/blaming-the-model && cd ~/Documents/repos/blaming-the-model && git init
```

- [ ] **Step 2: Escribir la taxonomía**

`data/taxonomy.yaml`. Dos niveles. Las clases marcadas son las que hacen falta
para que el escenario A3 tenga un empate real: un SDK de pagos satisface a la
vez "dominio de aplicación principal" y "librería para desarrolladores".

```yaml
infra:
  name: Infraestructura y operaciones
  description: Software que opera o sostiene otros sistemas en ejecución.
  children:
    infra.observability:
      name: Observabilidad
      description: Métricas, trazas, logs y alertas.
    infra.orchestration:
      name: Orquestación y despliegue
      description: Programación de cargas, despliegue y gestión de clústeres.
    infra.networking:
      name: Redes
      description: Proxies, balanceadores, service mesh y transporte.
data:
  name: Datos
  description: Movimiento, almacenamiento y análisis de datos.
  children:
    data.pipelines:
      name: Pipelines y ETL
      description: Ingesta, transformación y orquestación de datos.
    data.storage:
      name: Almacenamiento
      description: Bases de datos, motores de consulta y formatos.
ai:
  name: Inteligencia artificial
  description: Entrenamiento, inferencia y sistemas construidos sobre modelos.
  children:
    ai.training:
      name: Entrenamiento
      description: Bucles de entrenamiento, fine-tuning y datasets.
    ai.serving:
      name: Inferencia
      description: Servido de modelos, batching y aceleración.
    ai.agents:
      name: Agentes
      description: Bucles agénticos, herramientas y orquestación de modelos.
devtools:
  name: Herramientas de desarrollo
  description: Software cuyo usuario final es quien programa.
  children:
    devtools.build:
      name: Build y empaquetado
      description: Compilación, dependencias y distribución.
    devtools.testing:
      name: Testing y calidad
      description: Frameworks de test, linters y análisis estático.
    devtools.libraries:
      name: Librerías y SDK
      description: Bibliotecas de propósito general y SDK de integración.
business:
  name: Dominio de negocio
  description: Software que resuelve un problema de un sector concreto.
  children:
    business.payments:
      name: Pagos
      description: Cobros, facturación, conciliación y cumplimiento financiero.
    business.health:
      name: Salud
      description: Historia clínica, dispositivos y datos sanitarios.
    business.geo:
      name: Geoespacial
      description: Mapas, rutas y datos de localización.
```

- [ ] **Step 3: Escribir el test que falla**

`tests/test_taxonomy.py`:

```python
from pathlib import Path

import pytest

from btm.taxonomy import Taxonomy

TAXONOMY_PATH = Path(__file__).parents[1] / "data" / "taxonomy.yaml"


@pytest.fixture
def taxonomy() -> Taxonomy:
    return Taxonomy.load(TAXONOMY_PATH)


def test_leaf_knows_its_parent(taxonomy: Taxonomy) -> None:
    node = taxonomy.get("business.payments")
    assert node.name == "Pagos"
    assert node.parent == "business"


def test_every_leaf_code_is_prefixed_by_its_parent(taxonomy: Taxonomy) -> None:
    for leaf in taxonomy.leaves():
        assert leaf.parent is not None
        assert leaf.code.startswith(f"{leaf.parent}.")


def test_a3_collision_classes_exist(taxonomy: Taxonomy) -> None:
    # El escenario A3 necesita estas dos clases para que el empate sea real.
    assert taxonomy.get("business.payments")
    assert taxonomy.get("devtools.libraries")


def test_unknown_code_raises(taxonomy: Taxonomy) -> None:
    with pytest.raises(KeyError):
        taxonomy.get("business.nonexistent")
```

- [ ] **Step 4: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_taxonomy.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.taxonomy'`.

- [ ] **Step 5: Implementar**

`src/btm/taxonomy.py`:

```python
from pathlib import Path

import yaml
from pydantic import BaseModel


class TaxonomyNode(BaseModel):
    code: str
    name: str
    description: str
    parent: str | None = None


class Taxonomy(BaseModel):
    nodes: dict[str, TaxonomyNode]

    @classmethod
    def load(cls, path: Path) -> "Taxonomy":
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        nodes: dict[str, TaxonomyNode] = {}
        for code, division in raw.items():
            nodes[code] = TaxonomyNode(
                code=code, name=division["name"], description=division["description"]
            )
            for child_code, child in division.get("children", {}).items():
                nodes[child_code] = TaxonomyNode(
                    code=child_code,
                    name=child["name"],
                    description=child["description"],
                    parent=code,
                )
        return cls(nodes=nodes)

    def get(self, code: str) -> TaxonomyNode:
        return self.nodes[code]

    def leaves(self) -> list[TaxonomyNode]:
        return [node for node in self.nodes.values() if node.parent is not None]
```

- [ ] **Step 6: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_taxonomy.py -v`
Esperado: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml README.md src/btm data/taxonomy.yaml tests/test_taxonomy.py
git commit -m "La taxonomía de dominio de aplicación, con el empate de A3 dentro"
```

---

### Task 3: Snapshot del corpus

**Files:**
- Create: `src/btm/corpus.py`
- Create: `data/corpus/README.md`
- Test: `tests/test_corpus.py`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `Document` (pydantic: `url: str`, `title: str`, `text: str`,
  `kind: str`), `RepoSnapshot` (pydantic: `slug: str`, `name: str`,
  `description: str | None`, `documents: list[Document]`),
  `load_snapshot(slug, root) -> RepoSnapshot`,
  `load_all(root) -> list[RepoSnapshot]`.

`description` es opcional **a propósito**: el bug A2 explota justamente que a
veces no está.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_corpus.py`:

```python
import json
from pathlib import Path

from btm.corpus import RepoSnapshot, load_all, load_snapshot


def write_snapshot(root: Path, slug: str, description: str | None) -> None:
    payload = {
        "slug": slug,
        "name": slug,
        "description": description,
        "documents": [
            {
                "url": f"https://example.invalid/{slug}/readme",
                "title": "README",
                "text": "Un cliente en Python para la API de un proveedor de pagos.",
                "kind": "readme",
            }
        ],
    }
    path = root / slug
    path.mkdir(parents=True)
    (path / "snapshot.json").write_text(json.dumps(payload), encoding="utf-8")


def test_loads_a_snapshot_with_its_documents(tmp_path: Path) -> None:
    write_snapshot(tmp_path, "acme-pay", "Cliente de pagos")
    snapshot = load_snapshot("acme-pay", tmp_path)
    assert isinstance(snapshot, RepoSnapshot)
    assert snapshot.description == "Cliente de pagos"
    assert snapshot.documents[0].kind == "readme"


def test_description_may_be_absent(tmp_path: Path) -> None:
    write_snapshot(tmp_path, "sin-descripcion", None)
    snapshot = load_snapshot("sin-descripcion", tmp_path)
    assert snapshot.description is None


def test_load_all_is_sorted_by_slug(tmp_path: Path) -> None:
    write_snapshot(tmp_path, "zeta", "z")
    write_snapshot(tmp_path, "alfa", "a")
    assert [s.slug for s in load_all(tmp_path)] == ["alfa", "zeta"]
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_corpus.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.corpus'`.

- [ ] **Step 3: Implementar**

`src/btm/corpus.py`:

```python
import json
from pathlib import Path

from pydantic import BaseModel


class Document(BaseModel):
    url: str
    title: str
    text: str
    kind: str


class RepoSnapshot(BaseModel):
    slug: str
    name: str
    description: str | None = None
    documents: list[Document]


def load_snapshot(slug: str, root: Path) -> RepoSnapshot:
    payload = json.loads((root / slug / "snapshot.json").read_text(encoding="utf-8"))
    return RepoSnapshot.model_validate(payload)


def load_all(root: Path) -> list[RepoSnapshot]:
    slugs = sorted(p.name for p in root.iterdir() if (p / "snapshot.json").exists())
    return [load_snapshot(slug, root) for slug in slugs]
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_corpus.py -v`
Esperado: 3 passed.

- [ ] **Step 5: Documentar el criterio de selección**

`data/corpus/README.md` debe fijar el criterio antes de recolectar nada:
repositorios de cola larga (baja popularidad), preferentemente recientes, para
minimizar la memorización. Cada snapshot se guarda con la fecha de captura y la
URL de origen, y el corpus se versiona: los escenarios congelados dependen de
él.

- [ ] **Step 6: Commit**

```bash
git add src/btm/corpus.py data/corpus/README.md tests/test_corpus.py
git commit -m "Snapshot local del corpus, con la descripción opcional a propósito"
```

---

### Task 4: Tools deterministas sobre el snapshot

**Files:**
- Create: `src/btm/tools.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `Document`, `RepoSnapshot` de `btm.corpus`; `Taxonomy` de
  `btm.taxonomy`.
- Produces: `SearchHit` (pydantic: `url: str`, `title: str`, `score: float`),
  `ToolBox(snapshot, taxonomy, *, tie_seed: int = 0, unstable_ties: bool = False)`
  con métodos `search(query) -> list[SearchHit]`, `fetch_page(url) -> str`,
  `lookup_taxonomy(code) -> dict`.

El scoring es un solapamiento de tokens deliberadamente tosco: **produce empates
con frecuencia**, que es la condición que el bug A1 necesita para existir.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_tools.py`:

```python
import pytest

from btm.corpus import Document, RepoSnapshot
from btm.taxonomy import Taxonomy
from btm.tools import ToolBox

TAXONOMY_PATH = __import__("pathlib").Path(__file__).parents[1] / "data" / "taxonomy.yaml"


def snapshot_with_tied_documents() -> RepoSnapshot:
    # Dos documentos con exactamente los mismos tokens relevantes: empate seguro.
    return RepoSnapshot(
        slug="acme",
        name="acme",
        description=None,
        documents=[
            Document(url="https://x.invalid/a", title="A", text="pagos api cliente", kind="readme"),
            Document(url="https://x.invalid/b", title="B", text="pagos api cliente", kind="docs"),
        ],
    )


@pytest.fixture
def taxonomy() -> Taxonomy:
    return Taxonomy.load(TAXONOMY_PATH)


def test_search_is_stable_when_ties_are_stable(taxonomy: Taxonomy) -> None:
    box = ToolBox(snapshot_with_tied_documents(), taxonomy, tie_seed=1, unstable_ties=False)
    other = ToolBox(snapshot_with_tied_documents(), taxonomy, tie_seed=2, unstable_ties=False)
    assert [h.url for h in box.search("pagos api")] == [h.url for h in other.search("pagos api")]


def test_search_order_changes_with_seed_when_ties_are_unstable(taxonomy: Taxonomy) -> None:
    orders = set()
    for seed in range(8):
        box = ToolBox(snapshot_with_tied_documents(), taxonomy, tie_seed=seed, unstable_ties=True)
        orders.add(tuple(h.url for h in box.search("pagos api")))
    assert len(orders) == 2, "el bug A1 debe poder producir los dos órdenes"


def test_fetch_page_returns_the_document_text(taxonomy: Taxonomy) -> None:
    box = ToolBox(snapshot_with_tied_documents(), taxonomy)
    assert box.fetch_page("https://x.invalid/a") == "pagos api cliente"


def test_fetch_page_rejects_unknown_url(taxonomy: Taxonomy) -> None:
    box = ToolBox(snapshot_with_tied_documents(), taxonomy)
    with pytest.raises(KeyError):
        box.fetch_page("https://x.invalid/nope")


def test_lookup_taxonomy_returns_name_and_description(taxonomy: Taxonomy) -> None:
    box = ToolBox(snapshot_with_tied_documents(), taxonomy)
    assert box.lookup_taxonomy("business.payments")["name"] == "Pagos"
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_tools.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.tools'`.

- [ ] **Step 3: Implementar**

`src/btm/tools.py`:

```python
import random

from pydantic import BaseModel

from btm.corpus import RepoSnapshot
from btm.taxonomy import Taxonomy


class SearchHit(BaseModel):
    url: str
    title: str
    score: float


def _tokens(text: str) -> set[str]:
    return {t for t in text.lower().split() if t}


class ToolBox:
    def __init__(
        self,
        snapshot: RepoSnapshot,
        taxonomy: Taxonomy,
        *,
        tie_seed: int = 0,
        unstable_ties: bool = False,
    ) -> None:
        self.snapshot = snapshot
        self.taxonomy = taxonomy
        self.tie_seed = tie_seed
        self.unstable_ties = unstable_ties

    def _insertion_order(self) -> list[int]:
        order = list(range(len(self.snapshot.documents)))
        if self.unstable_ties:
            random.Random(self.tie_seed).shuffle(order)
        return order

    def search(self, query: str) -> list[SearchHit]:
        query_tokens = _tokens(query)
        scored: list[tuple[float, int, SearchHit]] = []
        for rank, index in enumerate(self._insertion_order()):
            document = self.snapshot.documents[index]
            overlap = len(query_tokens & _tokens(document.text))
            score = overlap / max(len(query_tokens), 1)
            scored.append(
                (score, rank, SearchHit(url=document.url, title=document.title, score=score))
            )
        # Empates resueltos por orden de inserción: el punto donde vive A1.
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [hit for _, _, hit in scored]

    def fetch_page(self, url: str) -> str:
        for document in self.snapshot.documents:
            if document.url == url:
                return document.text
        raise KeyError(url)

    def lookup_taxonomy(self, code: str) -> dict:
        node = self.taxonomy.get(code)
        return {"code": node.code, "name": node.name, "description": node.description}
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_tools.py -v`
Esperado: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/btm/tools.py tests/test_tools.py
git commit -m "Tools sobre el snapshot; los empates se resuelven por orden de inserción"
```

---

### Task 5: Presupuesto de búsquedas y techo de confianza

**Files:**
- Create: `src/btm/budget.py`
- Test: `tests/test_budget.py`

**Interfaces:**
- Produces: `Budget(max_searches: int, *, double_charge: bool = False,
  fixed_ceiling: float | None = None)` con `spend(kind: str) -> None`,
  `remaining -> int`, `exhausted -> bool`, `declared_ceiling() -> float`,
  y `SearchBudgetExhausted(Exception)`.

Aquí vive el bug A4, y tiene dos mitades que se refuerzan: el doble descuento
agota el presupuesto antes de tiempo, y el techo fijo impide que la confianza
declarada refleje que la evidencia se quedó corta. El síntoma parece del
modelo; la causa está en la contabilidad.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_budget.py`:

```python
import pytest

from btm.budget import Budget, SearchBudgetExhausted


def test_healthy_budget_charges_once_per_search() -> None:
    budget = Budget(max_searches=3)
    budget.spend("search")
    assert budget.remaining == 2


def test_double_charge_halves_the_real_budget() -> None:
    budget = Budget(max_searches=4, double_charge=True)
    budget.spend("search")
    assert budget.remaining == 2


def test_exhausted_budget_raises() -> None:
    budget = Budget(max_searches=1)
    budget.spend("search")
    with pytest.raises(SearchBudgetExhausted):
        budget.spend("search")


def test_healthy_ceiling_falls_with_the_evidence_gathered() -> None:
    budget = Budget(max_searches=4)
    budget.spend("search")
    assert budget.declared_ceiling() == pytest.approx(0.25)


def test_fixed_ceiling_ignores_how_little_evidence_there_is() -> None:
    budget = Budget(max_searches=4, fixed_ceiling=0.95)
    assert budget.declared_ceiling() == pytest.approx(0.95)
    budget.spend("search")
    assert budget.declared_ceiling() == pytest.approx(0.95)
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_budget.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.budget'`.

- [ ] **Step 3: Implementar**

`src/btm/budget.py`:

```python
class SearchBudgetExhausted(Exception):
    pass


class Budget:
    def __init__(
        self,
        max_searches: int,
        *,
        double_charge: bool = False,
        fixed_ceiling: float | None = None,
    ) -> None:
        self.max_searches = max_searches
        self.double_charge = double_charge
        self.fixed_ceiling = fixed_ceiling
        self.spent = 0

    @property
    def remaining(self) -> int:
        return max(self.max_searches - self.spent, 0)

    @property
    def exhausted(self) -> bool:
        return self.remaining == 0

    def spend(self, kind: str) -> None:
        if self.exhausted:
            raise SearchBudgetExhausted(kind)
        self.spent += 2 if self.double_charge else 1

    def declared_ceiling(self) -> float:
        if self.fixed_ceiling is not None:
            return self.fixed_ceiling
        return self.spent / self.max_searches
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_budget.py -v`
Esperado: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/btm/budget.py tests/test_budget.py
git commit -m "El presupuesto de búsquedas y el techo de confianza, con sus dos averías"
```

---

### Task 6: Traza completa

**Files:**
- Create: `src/btm/trace.py`
- Test: `tests/test_trace.py`

**Interfaces:**
- Produces: `TraceEvent` (pydantic: `seq: int`, `kind: str`, `payload: dict`),
  `Trace` con `record(kind, **payload) -> None`, `events -> list[TraceEvent]`,
  `to_jsonl() -> str`, y `poor() -> Trace`.

`poor()` devuelve la versión pobre de la traza —sólo entrada y salida final—
y es exactamente el factor 1 del 2×2 de la pieza 3. Se construye ahora porque
el clasificador debe emitir la traza rica desde el principio: recortarla después
es barato, reconstruirla no.

Tipos de evento: `input`, `tool_call`, `tool_result`, `context_documents`,
`model_message`, `budget`, `final`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_trace.py`:

```python
import json

from btm.trace import Trace


def test_events_are_numbered_in_order() -> None:
    trace = Trace()
    trace.record("input", slug="acme")
    trace.record("tool_call", name="search", query="pagos")
    assert [e.seq for e in trace.events] == [0, 1]
    assert trace.events[1].payload["name"] == "search"


def test_jsonl_has_one_line_per_event() -> None:
    trace = Trace()
    trace.record("input", slug="acme")
    trace.record("final", code="business.payments")
    lines = trace.to_jsonl().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["payload"]["code"] == "business.payments"


def test_poor_trace_keeps_only_input_and_final() -> None:
    trace = Trace()
    trace.record("input", slug="acme")
    trace.record("tool_call", name="search", query="pagos")
    trace.record("context_documents", urls=["https://x.invalid/a"])
    trace.record("final", code="business.payments")
    assert [e.kind for e in trace.poor().events] == ["input", "final"]


def test_poor_trace_does_not_mutate_the_original() -> None:
    trace = Trace()
    trace.record("input", slug="acme")
    trace.record("tool_call", name="search", query="pagos")
    trace.poor()
    assert len(trace.events) == 2
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_trace.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.trace'`.

- [ ] **Step 3: Implementar**

`src/btm/trace.py`:

```python
import json

from pydantic import BaseModel

POOR_KINDS = ("input", "final")


class TraceEvent(BaseModel):
    seq: int
    kind: str
    payload: dict


class Trace:
    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    @property
    def events(self) -> list[TraceEvent]:
        return list(self._events)

    def record(self, kind: str, **payload: object) -> None:
        self._events.append(TraceEvent(seq=len(self._events), kind=kind, payload=dict(payload)))

    def to_jsonl(self) -> str:
        return "".join(f"{json.dumps(e.model_dump(), ensure_ascii=False)}\n" for e in self._events)

    def poor(self) -> "Trace":
        stripped = Trace()
        for event in self._events:
            if event.kind in POOR_KINDS:
                stripped.record(event.kind, **event.payload)
        return stripped
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_trace.py -v`
Esperado: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/btm/trace.py tests/test_trace.py
git commit -m "Traza completa, y su versión pobre para el 2x2"
```

---

### Task 7: El clasificador, con sus cuatro averías inyectables

**Files:**
- Create: `src/btm/model.py`
- Create: `src/btm/classifier.py`
- Test: `tests/test_classifier.py`

**Interfaces:**
- Consumes: `ToolBox`, `Budget`, `Trace`, `RepoSnapshot`, `Taxonomy`.
- Produces:
  - `Model` (protocolo) con `complete(messages: list[dict]) -> str` y la
    propiedad `supports_temperature: bool`.
  - `FakeModel(replies: list[str])`, para los tests. `supports_temperature` es
    `False`, igual que el modelo real del escenario.
  - `Bugs` (pydantic: `unstable_ties: bool`, `drop_description: bool`,
    `ambiguous_rules: bool`, `double_charge: bool`), todos `False` por defecto.
  - `Classification` (pydantic: `code: str`, `confidence: float`,
    `justification: str`).
  - `classify(snapshot, taxonomy, model, *, bugs, seed, max_searches=4)
    -> tuple[Classification, Trace]`.

Correspondencia con el spec: `unstable_ties` es A1, `drop_description` es A2,
`ambiguous_rules` es A3, `double_charge` junto al techo fijo es A4.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_classifier.py`:

```python
from pathlib import Path

from btm.classifier import Bugs, classify
from btm.corpus import Document, RepoSnapshot
from btm.model import FakeModel
from btm.taxonomy import Taxonomy

TAXONOMY_PATH = Path(__file__).parents[1] / "data" / "taxonomy.yaml"


def snapshot() -> RepoSnapshot:
    return RepoSnapshot(
        slug="acme-pay",
        name="acme-pay",
        description="SDK de cobros para comercios",
        documents=[
            Document(url="https://x.invalid/a", title="A", text="pagos api cliente", kind="readme"),
            Document(url="https://x.invalid/b", title="B", text="pagos api cliente", kind="docs"),
        ],
    )


def taxonomy() -> Taxonomy:
    return Taxonomy.load(TAXONOMY_PATH)


def reply(code: str) -> str:
    return f'{{"code": "{code}", "confidence": 0.9, "justification": "porque si"}}'


def test_classifies_and_records_a_trace() -> None:
    model = FakeModel([reply("business.payments")])
    result, trace = classify(snapshot(), taxonomy(), model, bugs=Bugs(), seed=0)
    assert result.code == "business.payments"
    assert [e.kind for e in trace.events][0] == "input"
    assert any(e.kind == "context_documents" for e in trace.events)


def test_confidence_is_capped_by_the_evidence_gathered() -> None:
    # Una búsqueda de cuatro posibles: el techo sano baja a 0.25 y recorta el 0.9.
    model = FakeModel([reply("business.payments")])
    result, _ = classify(snapshot(), taxonomy(), model, bugs=Bugs(), seed=0, max_searches=4)
    assert result.confidence == 0.25


def test_a2_hides_the_description_from_the_prompt() -> None:
    model = FakeModel([reply("devtools.libraries")])
    _, trace = classify(snapshot(), taxonomy(), model, bugs=Bugs(drop_description=True), seed=0)
    prompts = [e.payload["prompt"] for e in trace.events if e.kind == "model_message"]
    assert all("SDK de cobros" not in p for p in prompts)


def test_a3_puts_two_colliding_rules_in_the_prompt() -> None:
    model = FakeModel([reply("business.payments")])
    _, trace = classify(snapshot(), taxonomy(), model, bugs=Bugs(ambiguous_rules=True), seed=0)
    prompt = next(e.payload["prompt"] for e in trace.events if e.kind == "model_message")
    assert "dominio de aplicación principal" in prompt
    assert "librería para desarrolladores" in prompt


def test_a4_exhausts_the_budget_early_but_keeps_the_ceiling_high() -> None:
    model = FakeModel([reply("business.payments")])
    _, trace = classify(
        snapshot(), taxonomy(), model, bugs=Bugs(double_charge=True), seed=0, max_searches=2
    )
    budget_events = [e.payload for e in trace.events if e.kind == "budget"]
    assert budget_events[-1]["remaining"] == 0
    assert budget_events[-1]["declared_ceiling"] == 0.95


def test_the_scenario_model_does_not_expose_temperature() -> None:
    assert FakeModel([]).supports_temperature is False
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_classifier.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.classifier'`.

- [ ] **Step 3: Implementar el modelo**

`src/btm/model.py`:

```python
from typing import Protocol


class Model(Protocol):
    @property
    def supports_temperature(self) -> bool: ...

    def complete(self, messages: list[dict]) -> str: ...


class FakeModel:
    """Modelo de test. No expone temperature, igual que el del escenario."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.seen: list[list[dict]] = []

    @property
    def supports_temperature(self) -> bool:
        return False

    def complete(self, messages: list[dict]) -> str:
        self.seen.append(messages)
        return self.replies.pop(0)
```

- [ ] **Step 4: Implementar el clasificador**

`src/btm/classifier.py`:

```python
import json

from pydantic import BaseModel

from btm.budget import Budget, SearchBudgetExhausted
from btm.corpus import RepoSnapshot
from btm.model import Model
from btm.taxonomy import Taxonomy
from btm.tools import ToolBox
from btm.trace import Trace

FIXED_CEILING = 0.95
CONTEXT_DOCUMENTS = 1  # el truncado que hace que el orden de A1 importe

BASE_RULE = "Clasifica por el dominio de aplicación principal del proyecto."
COLLIDING_RULE = (
    "Si el proyecto es una librería para desarrolladores, usa herramientas de desarrollo."
)


class Bugs(BaseModel):
    unstable_ties: bool = False
    drop_description: bool = False
    ambiguous_rules: bool = False
    double_charge: bool = False


class Classification(BaseModel):
    code: str
    confidence: float
    justification: str


def _build_prompt(
    snapshot: RepoSnapshot, taxonomy: Taxonomy, documents: list[str], bugs: Bugs
) -> str:
    rules = BASE_RULE
    if bugs.ambiguous_rules:
        # Dos reglas que pueden aplicar a la vez, y nadie declaró cuál gana.
        rules = f"{BASE_RULE}\n{COLLIDING_RULE}"
    description = None if bugs.drop_description else snapshot.description
    codes = "\n".join(f"- {leaf.code}: {leaf.name}" for leaf in taxonomy.leaves())
    return (
        f"Proyecto: {snapshot.name}\n"
        f"Descripción: {description or '(no disponible)'}\n"
        f"{rules}\n"
        f"Taxonomía:\n{codes}\n"
        f"Documentos:\n" + "\n---\n".join(documents) + "\n"
        'Responde JSON: {"code": ..., "confidence": ..., "justification": ...}'
    )


def classify(
    snapshot: RepoSnapshot,
    taxonomy: Taxonomy,
    model: Model,
    *,
    bugs: Bugs,
    seed: int,
    max_searches: int = 4,
) -> tuple[Classification, Trace]:
    trace = Trace()
    trace.record("input", slug=snapshot.slug, seed=seed, bugs=bugs.model_dump())

    budget = Budget(
        max_searches,
        double_charge=bugs.double_charge,
        fixed_ceiling=FIXED_CEILING if bugs.double_charge else None,
    )
    tools = ToolBox(snapshot, taxonomy, tie_seed=seed, unstable_ties=bugs.unstable_ties)

    query = snapshot.name.replace("-", " ")
    hits = []
    try:
        budget.spend("search")
        trace.record("tool_call", name="search", query=query)
        hits = tools.search(query)
        trace.record("tool_result", name="search", urls=[h.url for h in hits])
    except SearchBudgetExhausted:
        trace.record("tool_result", name="search", urls=[], exhausted=True)
    trace.record(
        "budget", remaining=budget.remaining, declared_ceiling=budget.declared_ceiling()
    )

    # El truncado: sólo los primeros documentos llegan al modelo.
    selected = [h.url for h in hits][:CONTEXT_DOCUMENTS]
    trace.record("context_documents", urls=selected)
    documents = [tools.fetch_page(url) for url in selected]

    prompt = _build_prompt(snapshot, taxonomy, documents, bugs)
    trace.record("model_message", prompt=prompt)
    raw = model.complete([{"role": "user", "content": prompt}])

    payload = json.loads(raw)
    ceiling = budget.declared_ceiling()
    result = Classification(
        code=payload["code"],
        confidence=min(float(payload["confidence"]), ceiling),
        justification=payload["justification"],
    )
    trace.record("final", code=result.code, confidence=result.confidence)
    return result, trace
```

- [ ] **Step 5: Ejecutar los tests y verificar que pasan**

Run: `pytest tests/test_classifier.py -v`
Esperado: 6 passed.

- [ ] **Step 6: Ejecutar la suite completa**

Run: `pytest -v`
Esperado: todo verde.

- [ ] **Step 7: Commit**

```bash
git add src/btm/model.py src/btm/classifier.py tests/test_classifier.py
git commit -m "El clasificador y sus cuatro averías, cada una activable por separado"
```

---

### Task 8: Generador de corridas divergentes

**Files:**
- Create: `src/btm/divergence.py`
- Test: `tests/test_divergence.py`

**Interfaces:**
- Consumes: `classify`, `Bugs`, `Classification`, `Trace`.
- Produces: `Run` (pydantic: `seed: int`, `classification: Classification`,
  `trace_jsonl: str`), `DivergenceReport` (pydantic: `slug: str`,
  `runs: list[Run]`, `distinct_codes: list[str]`, `diverged: bool`),
  `collect_runs(snapshot, taxonomy, model_factory, *, bugs, seeds) -> DivergenceReport`.

Esta tarea es la que hace honor a la restricción global: la divergencia se
**produce**, no se describe. Si un bug no diverge sobre un repositorio, ese par
bug-repositorio no sirve como escenario y hay que buscar otro. El informe lo
dice explícitamente en vez de dejarlo a la interpretación.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_divergence.py`:

```python
from pathlib import Path

from btm.classifier import Bugs
from btm.corpus import Document, RepoSnapshot
from btm.divergence import collect_runs
from btm.model import FakeModel
from btm.taxonomy import Taxonomy

TAXONOMY_PATH = Path(__file__).parents[1] / "data" / "taxonomy.yaml"


def snapshot() -> RepoSnapshot:
    return RepoSnapshot(
        slug="acme-pay",
        name="acme pay",
        description=None,
        documents=[
            Document(url="https://x.invalid/a", title="A", text="pagos api", kind="readme"),
            Document(url="https://x.invalid/b", title="B", text="pagos api", kind="docs"),
        ],
    )


def code_for_document(text: str) -> str:
    # El modelo falso responde según el documento que le haya llegado.
    code = "business.payments" if "pagos" in text else "devtools.libraries"
    return f'{{"code": "{code}", "confidence": 0.9, "justification": "-"}}'


def test_reports_no_divergence_when_the_bug_is_off() -> None:
    report = collect_runs(
        snapshot(),
        Taxonomy.load(TAXONOMY_PATH),
        lambda: FakeModel([code_for_document("pagos")] * 1),
        bugs=Bugs(),
        seeds=[0, 1, 2],
    )
    assert report.diverged is False
    assert len(report.runs) == 3


def test_every_run_carries_its_own_trace() -> None:
    report = collect_runs(
        snapshot(),
        Taxonomy.load(TAXONOMY_PATH),
        lambda: FakeModel([code_for_document("pagos")]),
        bugs=Bugs(),
        seeds=[0, 1],
    )
    assert all(run.trace_jsonl.strip() for run in report.runs)
    assert [run.seed for run in report.runs] == [0, 1]
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_divergence.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.divergence'`.

- [ ] **Step 3: Implementar**

`src/btm/divergence.py`:

```python
from typing import Callable

from pydantic import BaseModel

from btm.classifier import Bugs, Classification, classify
from btm.corpus import RepoSnapshot
from btm.model import Model
from btm.taxonomy import Taxonomy


class Run(BaseModel):
    seed: int
    classification: Classification
    trace_jsonl: str


class DivergenceReport(BaseModel):
    slug: str
    runs: list[Run]
    distinct_codes: list[str]
    diverged: bool


def collect_runs(
    snapshot: RepoSnapshot,
    taxonomy: Taxonomy,
    model_factory: Callable[[], Model],
    *,
    bugs: Bugs,
    seeds: list[int],
) -> DivergenceReport:
    runs: list[Run] = []
    for seed in seeds:
        classification, trace = classify(
            snapshot, taxonomy, model_factory(), bugs=bugs, seed=seed
        )
        runs.append(
            Run(seed=seed, classification=classification, trace_jsonl=trace.to_jsonl())
        )
    codes = sorted({run.classification.code for run in runs})
    return DivergenceReport(
        slug=snapshot.slug, runs=runs, distinct_codes=codes, diverged=len(codes) > 1
    )
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_divergence.py -v`
Esperado: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/btm/divergence.py tests/test_divergence.py
git commit -m "La divergencia se produce y se comprueba, no se describe"
```

---

### Task 9: Ensamblar el escenario que verá el agente investigador

**Files:**
- Create: `src/btm/scenario.py`
- Create: `src/btm/cli.py`
- Test: `tests/test_scenario.py`

**Interfaces:**
- Consumes: `DivergenceReport`.
- Produces: `build_scenario(report, out_dir, *, bug_id, include_trace) -> Path`,
  que escribe un directorio con `BRIEF.md`, `runs/seed-<n>.jsonl` y `code/`
  (copia del paquete `btm`).
- CLI: `python -m btm.cli scenario --bug A4 --repo <slug> --out out/A4`.

La CLI importa `AzureModel`, que se implementa en la Task 10. Los tests de esta
tarea no importan `cli.py`, así que pasan igualmente; la CLI no se ejecuta hasta
después de la Task 10.

El `BRIEF.md` es el encargo con framing neutro que exige el spec: pide
**investigar**, no explicar, y no menciona ni el bug ni la palabra
"estocasticidad". `include_trace=False` produce la variante de traza pobre para
la pieza 3.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_scenario.py`:

```python
from pathlib import Path

from btm.classifier import Classification
from btm.divergence import DivergenceReport, Run
from btm.scenario import build_scenario


def report() -> DivergenceReport:
    runs = [
        Run(
            seed=seed,
            classification=Classification(code=code, confidence=0.9, justification="-"),
            trace_jsonl='{"seq": 0, "kind": "input", "payload": {}}\n',
        )
        for seed, code in [(0, "business.payments"), (1, "devtools.libraries")]
    ]
    return DivergenceReport(
        slug="acme-pay",
        runs=runs,
        distinct_codes=["business.payments", "devtools.libraries"],
        diverged=True,
    )


def test_writes_brief_runs_and_code(tmp_path: Path) -> None:
    out = build_scenario(report(), tmp_path, bug_id="A4", include_trace=True)
    assert (out / "BRIEF.md").exists()
    assert (out / "runs" / "seed-0.jsonl").exists()
    assert (out / "runs" / "seed-1.jsonl").exists()
    assert (out / "code" / "classifier.py").exists()


def test_brief_does_not_leak_the_bug_or_the_word_stochastic(tmp_path: Path) -> None:
    out = build_scenario(report(), tmp_path, bug_id="A4", include_trace=True)
    brief = (out / "BRIEF.md").read_text(encoding="utf-8").lower()
    assert "a4" not in brief
    assert "presupuesto" not in brief
    assert "estocás" not in brief


def test_poor_variant_omits_the_runs_directory(tmp_path: Path) -> None:
    out = build_scenario(report(), tmp_path, bug_id="A4", include_trace=False)
    assert not (out / "runs").exists()
    assert (out / "OUTPUTS.md").exists()


def test_code_does_not_leak_the_experiment_machinery(tmp_path: Path) -> None:
    # divergence.py y scenario.py revelan el diseño del experimento: no se copian.
    out = build_scenario(report(), tmp_path, bug_id="A4", include_trace=True)
    copied = {p.name for p in (out / "code").iterdir()}
    assert "divergence.py" not in copied
    assert "scenario.py" not in copied
    assert "cli.py" not in copied
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_scenario.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.scenario'`.

- [ ] **Step 3: Implementar**

`src/btm/scenario.py`:

```python
import shutil
from pathlib import Path

from btm.divergence import DivergenceReport

BRIEF = """# Encargo

El clasificador de `code/` asigna a cada proyecto un código de una taxonomía de
dominio de aplicación, junto con una confianza y una justificación.

Sobre el proyecto `{slug}` no devuelve siempre lo mismo: en distintas corridas ha
producido {codes}.

Investiga a qué se debe y qué harías al respecto. Tienes el código del sistema
{evidence}. Puedes pedir lo que te falte.
"""

WITH_RUNS = "en `code/` y los registros de cada corrida en `runs/`"
WITHOUT_RUNS = "en `code/` y las entradas y salidas de cada corrida en `OUTPUTS.md`"


def build_scenario(
    report: DivergenceReport, out_dir: Path, *, bug_id: str, include_trace: bool
) -> Path:
    out = out_dir / report.slug
    out.mkdir(parents=True, exist_ok=True)

    codes = " y ".join(f"`{code}`" for code in report.distinct_codes)
    evidence = WITH_RUNS if include_trace else WITHOUT_RUNS
    (out / "BRIEF.md").write_text(
        BRIEF.format(slug=report.slug, codes=codes, evidence=evidence), encoding="utf-8"
    )

    if include_trace:
        runs_dir = out / "runs"
        runs_dir.mkdir(exist_ok=True)
        for run in report.runs:
            (runs_dir / f"seed-{run.seed}.jsonl").write_text(run.trace_jsonl, encoding="utf-8")
    else:
        lines = [
            f"- corrida {run.seed}: `{run.classification.code}`"
            f" (confianza {run.classification.confidence})"
            for run in report.runs
        ]
        (out / "OUTPUTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    code_dir = out / "code"
    if code_dir.exists():
        shutil.rmtree(code_dir)
    code_dir.mkdir()
    # Sólo el sistema bajo análisis. divergence.py, scenario.py y cli.py
    # revelarían el diseño del experimento al agente investigador.
    for name in SYSTEM_MODULES:
        shutil.copy(Path(__file__).parent / name, code_dir / name)
    return out
```

Y la lista, junto a las constantes del principio del módulo:

```python
SYSTEM_MODULES = (
    "__init__.py",
    "classifier.py",
    "tools.py",
    "budget.py",
    "trace.py",
    "taxonomy.py",
    "corpus.py",
    "model.py",
)
```

- [ ] **Step 4: Implementar la CLI**

`src/btm/cli.py`:

```python
import argparse
from pathlib import Path

from btm.classifier import Bugs
from btm.corpus import load_snapshot
from btm.divergence import collect_runs
from btm.model import AzureModel
from btm.scenario import build_scenario
from btm.taxonomy import Taxonomy

BUGS = {
    "A1": Bugs(unstable_ties=True),
    "A2": Bugs(drop_description=True),
    "A3": Bugs(ambiguous_rules=True),
    "A4": Bugs(double_charge=True),
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="btm")
    sub = parser.add_subparsers(dest="command", required=True)

    scenario = sub.add_parser("scenario")
    scenario.add_argument("--bug", choices=sorted(BUGS), required=True)
    scenario.add_argument("--repo", required=True)
    scenario.add_argument("--out", type=Path, required=True)
    scenario.add_argument("--seeds", type=int, default=8)
    scenario.add_argument("--corpus", type=Path, default=Path("data/corpus"))
    scenario.add_argument("--taxonomy", type=Path, default=Path("data/taxonomy.yaml"))
    scenario.add_argument("--poor-trace", action="store_true")

    args = parser.parse_args()
    snapshot = load_snapshot(args.repo, args.corpus)
    taxonomy = Taxonomy.load(args.taxonomy)
    report = collect_runs(
        snapshot,
        taxonomy,
        AzureModel,
        bugs=BUGS[args.bug],
        seeds=list(range(args.seeds)),
    )
    out = build_scenario(
        report, args.out, bug_id=args.bug, include_trace=not args.poor_trace
    )
    print(f"diverged={report.diverged} codes={report.distinct_codes} out={out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_scenario.py -v`
Esperado: 4 passed.

- [ ] **Step 6: Ejecutar la suite completa**

Run: `pytest -v`
Esperado: todo verde.

- [ ] **Step 7: Commit**

```bash
git add src/btm/scenario.py src/btm/cli.py tests/test_scenario.py
git commit -m "El escenario que ve el investigador: encargo neutro, logs reales y el código"
```

---

### Task 10: Cliente del modelo real, sin temperatura

**Files:**
- Modify: `src/btm/model.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Produces: `AzureModel()`, que satisface el protocolo `Model` y cuya propiedad
  `supports_temperature` es `False`.

El spec exige que el sistema de los escenarios use un modelo de razonamiento sin
parámetro de temperatura. Esa exigencia tiene que estar en el código y bajo test,
no sólo en la prosa: es lo que convierte el reflejo del interruptor en un error
atrapable.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_model.py`:

```python
import pytest

from btm.model import AzureModel


def test_the_real_model_does_not_expose_temperature() -> None:
    assert AzureModel().supports_temperature is False


def test_setting_a_temperature_is_refused() -> None:
    with pytest.raises(ValueError, match="no admite temperature"):
        AzureModel(temperature=0.0)
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_model.py -v`
Esperado: FAIL con `ImportError: cannot import name 'AzureModel'`.

- [ ] **Step 3: Implementar**

Añadir a `src/btm/model.py`:

```python
import os


class AzureModel:
    """Modelo de razonamiento del sistema bajo análisis. No admite temperature."""

    def __init__(self, *, deployment: str | None = None, temperature: float | None = None) -> None:
        if temperature is not None:
            raise ValueError("este despliegue no admite temperature")
        self.deployment = deployment or os.environ.get("BTM_DEPLOYMENT", "")

    @property
    def supports_temperature(self) -> bool:
        return False

    def complete(self, messages: list[dict]) -> str:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=os.environ["BTM_AZURE_ENDPOINT"],
            api_key=os.environ["BTM_AZURE_KEY"],
            api_version=os.environ.get("BTM_API_VERSION", "2026-01-01"),
        )
        response = client.chat.completions.create(
            model=self.deployment, messages=messages
        )
        return response.choices[0].message.content or ""
```

`complete` no se ejercita en los tests: la suite entera corre con `FakeModel` y
sin red, como exige la restricción global.

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_model.py -v`
Esperado: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/btm/model.py tests/test_model.py
git commit -m "El modelo del escenario no admite temperature, y hay un test que lo dice"
```

---

### Task 11: Escenarios de clase B, donde no hay regla que valga

**Files:**
- Create: `data/judgement/b1-agency.yaml`
- Create: `data/judgement/b2-recency.yaml`
- Create: `data/judgement/b3-distinctiveness.yaml`
- Create: `src/btm/judgement.py`
- Test: `tests/test_judgement.py`

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `JudgementCase` (pydantic: `text: str`, `label: str`,
  `note: str`), `JudgementSet` (pydantic: `bug_id: str`, `question: str`,
  `visible: list[JudgementCase]`, `held_out: list[JudgementCase]`),
  `load_judgement_set(path) -> JudgementSet`,
  `build_judgement_scenario(judgement_set, out_dir) -> Path`.

Estos escenarios no tienen bug ni divergencia: se le enseña al agente un puñado
de casos donde el clasificador falla y se le pide que lo mejore. Lo que se mide
es si propone una regla determinista o si deja juzgar al modelo con mejor
andamiaje.

**El held-out es la razón de ser de esta tarea** y por eso vive en el mismo
fichero pero en una clave aparte: contiene paráfrasis, negaciones y lenguaje
indirecto que el agente no ve. Es lo que después convierte "este regex es
frágil" en un número de cobertura.

- [ ] **Step 1: Escribir los casos de B1**

`data/judgement/b1-agency.yaml`. `label` es `own` si la actividad la hace el
propio proyecto y `third_party` si es un cliente o envoltorio de otro.

```yaml
bug_id: B1
question: ¿El proyecto realiza esta actividad o se limita a integrarse con quien la realiza?
visible:
  - text: Cliente en Python para la API de un proveedor de cobros.
    label: third_party
    note: Envoltorio explícito.
  - text: Motor de conciliación de cobros con soporte para varios adquirentes.
    label: own
    note: La actividad es propia aunque nombre a terceros.
  - text: Bindings de bajo nivel para la librería de cifrado del sistema.
    label: third_party
    note: La palabra bindings lo delata, y por eso invita al atajo.
held_out:
  - text: No es un wrapper: implementamos el protocolo de liquidación desde cero.
    label: own
    note: Contiene la palabra wrapper, negada. Mata el matching literal.
  - text: Hablamos el mismo protocolo que el servicio oficial, sin depender de él.
    label: own
    note: Sin ninguna palabra de la lista.
  - text: Una fachada cómoda sobre el SDK que ya usas.
    label: third_party
    note: Ni wrapper ni client ni bindings.
```

- [ ] **Step 2: Escribir los casos de B2 y B3**

`data/judgement/b2-recency.yaml`, con `label` `current` o `historical`:

```yaml
bug_id: B2
question: ¿Cuál es la actividad vigente del proyecto?
visible:
  - text: Originalmente un fork del planificador de tareas; hoy es una librería de trazas.
    label: current
    note: Lo vigente va después del punto y coma.
  - text: Hasta la v2 servíamos modelos; la v3 es un framework de agentes.
    label: current
    note: Dos actividades, una caducada.
  - text: Proyecto de observabilidad, ahora deprecado en favor del estándar del ecosistema.
    label: historical
    note: Deprecado, pero la actividad descrita sigue siendo la suya.
held_out:
  - text: Empezamos midiendo latencia y seguimos en ello cinco años después.
    label: current
    note: Menciona el pasado sin cambiar de actividad.
  - text: El README lleva sin tocarse desde el rediseño, que lo convirtió en un cliente HTTP.
    label: current
    note: La pista temporal apunta al revés de lo que sugiere el verbo.
```

`data/judgement/b3-distinctiveness.yaml`, con `label` `distinctive` o `generic`:

```yaml
bug_id: B3
question: ¿Basta este nombre para identificar el proyecto en una búsqueda?
visible:
  - text: core
    label: generic
    note: Homónimos por millares.
  - text: quipuswap-indexer
    label: distinctive
    note: Compuesto y raro.
  - text: platform-utils
    label: generic
    note: Dos palabras genéricas no suman distintividad.
held_out:
  - text: mercury
    label: generic
    note: Una sola palabra, común, pero no está en ninguna lista de términos técnicos.
  - text: k9s-mirror-ng
    label: distinctive
    note: Corto, pero inequívoco.
  - text: data-platform-core-utils
    label: generic
    note: Largo y aun así genérico: mata la heurística de longitud.
```

- [ ] **Step 3: Escribir el test que falla**

`tests/test_judgement.py`:

```python
from pathlib import Path

from btm.judgement import build_judgement_scenario, load_judgement_set

DATA = Path(__file__).parents[1] / "data" / "judgement"


def test_loads_visible_and_held_out_cases() -> None:
    judgement_set = load_judgement_set(DATA / "b1-agency.yaml")
    assert judgement_set.bug_id == "B1"
    assert len(judgement_set.visible) == 3
    assert len(judgement_set.held_out) == 3


def test_every_set_has_held_out_cases() -> None:
    for path in sorted(DATA.glob("*.yaml")):
        judgement_set = load_judgement_set(path)
        assert judgement_set.held_out, f"{path.name} no tiene held-out"


def test_held_out_defeats_the_obvious_keyword_rule() -> None:
    # Una lista de palabras sobre los casos visibles no puede acertar el held-out.
    judgement_set = load_judgement_set(DATA / "b1-agency.yaml")
    keywords = ("cliente", "bindings", "wrapper")
    wrong = [
        case
        for case in judgement_set.held_out
        if (any(k in case.text.lower() for k in keywords)) != (case.label == "third_party")
    ]
    assert wrong, "el held-out debe romper el atajo, o no mide nada"


def test_scenario_hides_the_held_out_cases(tmp_path: Path) -> None:
    judgement_set = load_judgement_set(DATA / "b1-agency.yaml")
    out = build_judgement_scenario(judgement_set, tmp_path)
    brief = (out / "BRIEF.md").read_text(encoding="utf-8")
    for case in judgement_set.held_out:
        assert case.text not in brief
    for case in judgement_set.visible:
        assert case.text in brief
```

- [ ] **Step 4: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_judgement.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.judgement'`.

- [ ] **Step 5: Implementar**

`src/btm/judgement.py`:

```python
from pathlib import Path

import yaml
from pydantic import BaseModel

BRIEF = """# Encargo

El clasificador falla al responder a esta pregunta sobre los documentos que lee:

> {question}

Estos son casos donde se equivoca:

{cases}

Propón cómo mejorarlo. Puedes cambiar lo que haga falta del sistema.
"""


class JudgementCase(BaseModel):
    text: str
    label: str
    note: str


class JudgementSet(BaseModel):
    bug_id: str
    question: str
    visible: list[JudgementCase]
    held_out: list[JudgementCase]


def load_judgement_set(path: Path) -> JudgementSet:
    return JudgementSet.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def build_judgement_scenario(judgement_set: JudgementSet, out_dir: Path) -> Path:
    out = out_dir / judgement_set.bug_id.lower()
    out.mkdir(parents=True, exist_ok=True)
    # Sin label y sin note: el agente ve el caso, no la respuesta ni el porqué.
    cases = "\n".join(f"- {case.text}" for case in judgement_set.visible)
    (out / "BRIEF.md").write_text(
        BRIEF.format(question=judgement_set.question, cases=cases), encoding="utf-8"
    )
    return out
```

- [ ] **Step 6: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_judgement.py -v`
Esperado: 4 passed.

- [ ] **Step 7: Añadir el subcomando a la CLI**

En `src/btm/cli.py`, junto al parser de `scenario`:

```python
    judgement = sub.add_parser("judgement")
    judgement.add_argument("--set", dest="judgement_set", required=True)
    judgement.add_argument("--out", type=Path, required=True)
    judgement.add_argument("--data", type=Path, default=Path("data/judgement"))
```

Y en `main`, antes de la rama de `scenario`:

```python
    if args.command == "judgement":
        from btm.judgement import build_judgement_scenario, load_judgement_set

        matches = sorted(args.data.glob(f"{args.judgement_set.lower()}-*.yaml"))
        if not matches:
            raise SystemExit(f"no hay conjunto {args.judgement_set} en {args.data}")
        out = build_judgement_scenario(load_judgement_set(matches[0]), args.out)
        print(f"out={out}")
        return
```

- [ ] **Step 8: Comprobar la CLI a mano**

Run: `python -m btm.cli judgement --set B1 --out out/B1`
Esperado: escribe `out/B1/b1/BRIEF.md`, y el fichero no contiene ningún caso del
held-out.

- [ ] **Step 9: Ejecutar la suite completa**

Run: `pytest -v`
Esperado: todo verde.

- [ ] **Step 10: Commit**

```bash
git add data/judgement src/btm/judgement.py src/btm/cli.py tests/test_judgement.py
git commit -m "Los tres juicios sin regla posible, con su held-out escondido"
```

---

### Task 12: Primera pasada de calibración y acta de fidelidad

**Files:**
- Create: `docs/calibration/2026-XX-XX-pasada-1.md` (en el repo del experimento;
  la fecha es la del día en que se ejecute)
- Modify: `data/corpus/` — los repositorios que se elijan

**Interfaces:**
- Consumes: la CLI de la Task 9.
- Produces: el acta que decide si los escenarios se congelan o se rehacen.

- [ ] **Step 1: Reunir el corpus mínimo**

Al menos tres repositorios de cola larga por escenario, siguiendo el criterio ya
escrito en `data/corpus/README.md`. Guardar fecha de captura y URL de origen.

- [ ] **Step 2: Comprobar que cada bug diverge de verdad**

Para cada bug y cada repositorio, ejecutar el generador con al menos 8 seeds y
el modelo real.

Run: `python -m btm.cli scenario --bug A1 --repo <slug> --out out/A1`
Esperado: el informe marca `diverged: true`. Un par bug-repositorio que no
diverge **no sirve como escenario**: se descarta el par y se prueba otro
repositorio, no se retoca el bug para forzarlo.

- [ ] **Step 3: Pasada manual de clase A con dos o tres modelos**

Entregar el escenario a dos o tres modelos y leer entera la respuesta: qué
investiga primero, si pide instrumentación, a qué atribuye la variabilidad y qué
arreglo propone. Anotar en particular si alguno propone tocar la temperatura de
un modelo que no la admite.

- [ ] **Step 3b: Pasada manual de clase B**

Run: `python -m btm.cli judgement --set B1 --out out/B1` para cada uno de los
tres conjuntos, y entregar el `BRIEF.md` a los mismos modelos.

Lo que se lee aquí es otra cosa: si el remedio propuesto es una lista de
palabras o un regex, o si deja juzgar al modelo con mejor andamiaje. Cuando
proponga una regla determinista, **ejecutarla contra el held-out** y anotar qué
fracción acierta. Ese número es el que hace falta para que el artículo no
dependa de una opinión sobre estilo.

- [ ] **Step 4: Escribir el acta**

Una sección por escenario, y en cada una: qué hizo el agente, y el juicio de
fidelidad —¿es este el bug que aparece en producción?, ¿es este el contexto que
tiene delante un ingeniero real?

El acta debe registrar también lo que no encajó. Si un escenario resulta trivial
o poco realista, se dice y se rehace.

- [ ] **Step 5: Revisión del usuario**

El juez de fidelidad es Javier. Presentarle el acta y esperar su veredicto antes
de tocar nada más.

Si los agentes **no** fallan como él los ha visto fallar, la primera hipótesis es
que el escenario está mal construido y se vuelve a la Task 12 Step 1; la segunda,
que el fenómeno es más estrecho de lo que parecía. La segunda sólo se acepta
después de haber agotado la primera.

- [ ] **Step 6: Commit**

```bash
git add docs/calibration data/corpus
git commit -m "Acta de la primera pasada de calibración"
```

- [ ] **Step 7: Parar aquí**

La congelación de escenarios, la rúbrica automática, el control sin IA y el run
de confirmación son el siguiente plan, y no se escriben hasta que el acta esté
aprobada.
