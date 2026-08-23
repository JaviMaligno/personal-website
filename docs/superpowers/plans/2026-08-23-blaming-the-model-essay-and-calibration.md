# Blaming the Model — ensayo y calibración: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** publicar el ensayo de la serie y dejar construido un clasificador de
juguete con cuatro averías reales, cada una como variante de código auténtica,
que produzca registros divergentes de verdad y no delate su propio diseño.

**Architecture:** el sistema bajo análisis vive en `src/btm/system/` y está
limpio: no conoce el experimento. Cada avería es un módulo alternativo real en
`src/btm/variants/<ID>/` que sustituye a su homólogo. El arnés —que nunca se
entrega— vive en `src/btm/harness/`: carga una variante sobre una copia del
sistema, clasifica con ella, compara contra la línea base sana y empaqueta el
escenario. El artículo del ensayo vive en el repo del blog y es independiente
del código.

**Tech Stack:** Python 3.13, pytest, pydantic, Azure OpenAI vía el gateway
privado para el clasificador; Astro y Markdown para el artículo.

**Spec:** `docs/superpowers/specs/2026-08-23-agents-blaming-the-model-design.md`

## Global Constraints

- **Alcance:** este plan termina en el acta de calibración. La rúbrica
  automática, el control sin IA y el run de confirmación son un plan posterior.
- **El paquete no contiene el vocabulario del experimento.** Ni identificadores
  de avería (`A1`…`A4`), ni nombres de flags, ni comentarios que expliquen dónde
  está plantado el fallo, ni metadatos de corrida que lo delaten. Lo que se
  entrega es un sistema averiado y sus registros, como los tendría un ingeniero.
  Un agente que nombra la causa leyendo una etiqueta no ha diagnosticado nada.
- **La divergencia es real:** al agente investigador se le entregan registros de
  corridas ejecutadas de verdad, nunca una descripción textual de la
  variabilidad. Esto descarta cualquier fichero de resumen en prosa.
- **La instrumentación se entrega en dos tiempos:** el paquete inicial lleva
  registros someros —entrada y salida reales por corrida— y el código. La traza
  rica existe, se guarda fuera del paquete, y se entrega **si el agente la
  pide**. Sin ese escalón, "¿propone instrumentar?" es inmedible.
- **Cada avería declara su señal.** A1 diverge entre corridas; A2 y A4 se
  observan contra la línea base sana; A3 corre junto a A1 y muestra las dos. No
  se fabrica dependencia del azar donde la producción no la tiene.
- **Anonimización:** ni dominio, ni taxonomía, ni nombres de repositorio
  internos, ni referencias a tickets del trabajo real. Ambos repos son públicos.
- **Fidelidad, no resultado:** durante la calibración los escenarios se iteran
  por realismo. Un escenario se descarta por poco realista, trivial o mal
  instrumentado; **nunca por dar un resultado incómodo**.
- **El modelo del clasificador no expone `temperature`**, pero el paquete no lo
  dice: el guard vive en el arnés. La indisponibilidad se descubre como en
  producción, por el error de la API.
- **Publicar es merge a `main`.** Ninguna tarea de este plan mergea nada.
- **Tests sin red:** toda la suite corre con un modelo falso.
- **Repo del experimento:** `~/Documents/repos/blaming-the-model`, nuevo y
  público. Crear el directorio requiere confirmación del usuario.

---

## Parte A — El ensayo

### Task 1: Escribir y validar el ensayo

**Files:**
- Create: `src/content/blog/en/blaming-the-model.md`
- Create: `src/content/blog/es/blaming-the-model.md`
- Rama: `blog/agents-blaming-the-model` (ya existe, ya contiene spec y plan)

**Interfaces:**
- Consumes: la sección "Pieza 1 — Ensayo" del spec.
- Produces: nada que consuman tareas posteriores.

- [ ] **Step 1: Invocar la skill de escritura**

Usar la skill `blog-writer`, que ya conoce el formato bilingüe y el frontmatter
de este sitio. No escribir los ficheros a mano saltándose la skill.

- [ ] **Step 2: Redactar las cinco historias**

En este orden: la traza, la estocasticidad, el interruptor, el ground truth, el
determinismo burdo y su motivo. El cierre es que el agente y el sistema
analizado corren el mismo modelo.

Tono: sin rotundidad, sin hombre de paja. Son observaciones de trabajo, no una
ley. Puede decir que esto se puede medir y que es el paso natural —sin fecha,
sin prometer resultados—, y **no** debe anunciar dos partes concretas.

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

Esperado: los seis campos en cada fichero, mismo `translationKey`.

- [ ] **Step 4: Verificar que el sitio compila**

Run: `npm run build`
Esperado: build correcto, sin errores de validación de la colección `blog`.

- [ ] **Step 5: Commit**

```bash
git add src/content/blog/en/blaming-the-model.md src/content/blog/es/blaming-the-model.md
git commit -m "Artículo: culpa al modelo lo que no se culparía a sí mismo"
```

No mergear.

---

## Parte B — El sistema bajo análisis

Todas las rutas de aquí en adelante son relativas a
`~/Documents/repos/blaming-the-model`.

**Ninguno de los módulos de `src/btm/system/` puede mencionar el experimento.**
Sus comentarios describen qué hace el código, nunca por qué está así.

### Task 2: Esqueleto del repo y taxonomía

**Files:**
- Create: `pyproject.toml`, `README.md`
- Create: `src/btm/__init__.py`, `src/btm/system/__init__.py`
- Create: `src/btm/system/taxonomy.py`
- Create: `data/taxonomy.yaml`
- Test: `tests/test_taxonomy.py`

**Interfaces:**
- Produces: `Taxonomy.load(path) -> Taxonomy`, `Taxonomy.get(code) -> TaxonomyNode`,
  `Taxonomy.leaves() -> list[TaxonomyNode]`. `TaxonomyNode` es un pydantic
  `BaseModel` con `code: str`, `name: str`, `description: str`,
  `parent: str | None`.

- [ ] **Step 1: Crear el repo (requiere confirmación del usuario)**

```bash
mkdir -p ~/Documents/repos/blaming-the-model && cd ~/Documents/repos/blaming-the-model && git init
```

- [ ] **Step 2: Escribir la taxonomía**

`data/taxonomy.yaml`. Dos niveles. `business.payments` y `devtools.libraries`
son las que hacen que la ambigüedad de reglas tenga un empate real: un SDK de
pagos satisface las dos.

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

from btm.system.taxonomy import Taxonomy

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


def test_the_colliding_classes_exist(taxonomy: Taxonomy) -> None:
    assert taxonomy.get("business.payments")
    assert taxonomy.get("devtools.libraries")


def test_unknown_code_raises(taxonomy: Taxonomy) -> None:
    with pytest.raises(KeyError):
        taxonomy.get("business.nonexistent")
```

- [ ] **Step 4: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_taxonomy.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.system.taxonomy'`.

- [ ] **Step 5: Implementar**

`src/btm/system/taxonomy.py`:

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
git commit -m "La taxonomía de dominio de aplicación"
```

---

### Task 3: Snapshot del corpus

**Files:**
- Create: `src/btm/system/corpus.py`
- Create: `data/corpus/README.md`
- Test: `tests/test_corpus.py`

**Interfaces:**
- Produces: `Document` (`url: str`, `title: str`, `text: str`, `kind: str`),
  `RepoSnapshot` (`slug: str`, `name: str`, `description: str | None`,
  `documents: list[Document]`), `load_snapshot(slug, root) -> RepoSnapshot`,
  `load_all(root) -> list[RepoSnapshot]`.

`description` es opcional porque en el registro real a veces no está. La avería
A2 no inventa esa ausencia: explota que el clasificador no la compense.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_corpus.py`:

```python
import json
from pathlib import Path

from btm.system.corpus import RepoSnapshot, load_all, load_snapshot


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
    assert load_snapshot("sin-descripcion", tmp_path).description is None


def test_load_all_is_sorted_by_slug(tmp_path: Path) -> None:
    write_snapshot(tmp_path, "zeta", "z")
    write_snapshot(tmp_path, "alfa", "a")
    assert [s.slug for s in load_all(tmp_path)] == ["alfa", "zeta"]
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_corpus.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.system.corpus'`.

- [ ] **Step 3: Implementar**

`src/btm/system/corpus.py`:

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

- [ ] **Step 5: Fijar el criterio de selección antes de recolectar**

`data/corpus/README.md` debe dejar escrito:

- Repositorios de cola larga (baja popularidad), preferentemente recientes, para
  minimizar la memorización.
- **Al menos cinco documentos por snapshot**, para que el truncado de contexto
  siga mordiendo.
- **Repositorios con descripción y sin ella**, en proporción parecida. Sin este
  reparto la avería A2 no tiene dónde manifestarse: su eje es el corpus.
- Fecha de captura y URL de origen en cada snapshot. El corpus se versiona: los
  escenarios congelados dependen de él.

- [ ] **Step 6: Commit**

```bash
git add src/btm/system/corpus.py data/corpus/README.md tests/test_corpus.py
git commit -m "Snapshot local del corpus"
```

---

### Task 4: Tools sobre el snapshot

**Files:**
- Create: `src/btm/system/tools.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Produces: `SearchHit` (`url: str`, `title: str`, `score: float`),
  `ToolBox(snapshot, taxonomy, *, run_id: str = "")` con
  `search(query) -> list[SearchHit]`, `fetch_page(url) -> str`,
  `lookup_taxonomy(code) -> dict`.

`run_id` está en la firma porque el sistema lo recibe en todas partes para sus
registros. El sistema sano **no lo usa** para ordenar: los empates se resuelven
por orden de llegada, de forma estable. La variante A1 sustituye este módulo.

El scoring es un solapamiento de tokens deliberadamente tosco, de modo que los
empates son frecuentes.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_tools.py`:

```python
from pathlib import Path

import pytest

from btm.system.corpus import Document, RepoSnapshot
from btm.system.taxonomy import Taxonomy
from btm.system.tools import ToolBox

TAXONOMY_PATH = Path(__file__).parents[1] / "data" / "taxonomy.yaml"


def tied_snapshot() -> RepoSnapshot:
    # Cinco documentos, los tres primeros con los mismos tokens: empates seguros.
    texts = ["pagos api cliente", "pagos api cliente", "pagos api cliente",
             "guia de instalacion", "notas de version"]
    return RepoSnapshot(
        slug="acme",
        name="acme",
        description=None,
        documents=[
            Document(url=f"https://x.invalid/{i}", title=str(i), text=text, kind="docs")
            for i, text in enumerate(texts)
        ],
    )


@pytest.fixture
def taxonomy() -> Taxonomy:
    return Taxonomy.load(TAXONOMY_PATH)


def test_healthy_search_is_stable_across_run_ids(taxonomy: Taxonomy) -> None:
    orders = {
        tuple(h.url for h in ToolBox(tied_snapshot(), taxonomy, run_id=r).search("pagos api"))
        for r in ("r0", "r1", "r2", "r3")
    }
    assert len(orders) == 1, "el sistema sano no puede depender del run_id"


def test_best_matches_come_first(taxonomy: Taxonomy) -> None:
    hits = ToolBox(tied_snapshot(), taxonomy).search("pagos api")
    assert [h.url for h in hits[:3]] == [f"https://x.invalid/{i}" for i in range(3)]


def test_fetch_page_returns_the_document_text(taxonomy: Taxonomy) -> None:
    assert ToolBox(tied_snapshot(), taxonomy).fetch_page("https://x.invalid/0") == "pagos api cliente"


def test_fetch_page_rejects_unknown_url(taxonomy: Taxonomy) -> None:
    with pytest.raises(KeyError):
        ToolBox(tied_snapshot(), taxonomy).fetch_page("https://x.invalid/nope")


def test_lookup_taxonomy_returns_name_and_description(taxonomy: Taxonomy) -> None:
    assert ToolBox(tied_snapshot(), taxonomy).lookup_taxonomy("business.payments")["name"] == "Pagos"
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_tools.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.system.tools'`.

- [ ] **Step 3: Implementar**

`src/btm/system/tools.py`:

```python
from pydantic import BaseModel

from btm.system.corpus import RepoSnapshot
from btm.system.taxonomy import Taxonomy


class SearchHit(BaseModel):
    url: str
    title: str
    score: float


def tokens(text: str) -> set[str]:
    return {t for t in text.lower().split() if t}


class ToolBox:
    def __init__(self, snapshot: RepoSnapshot, taxonomy: Taxonomy, *, run_id: str = "") -> None:
        self.snapshot = snapshot
        self.taxonomy = taxonomy
        self.run_id = run_id

    def search(self, query: str) -> list[SearchHit]:
        wanted = tokens(query)
        scored: list[tuple[float, int, SearchHit]] = []
        for position, document in enumerate(self.snapshot.documents):
            overlap = len(wanted & tokens(document.text))
            score = overlap / max(len(wanted), 1)
            scored.append(
                (score, position, SearchHit(url=document.url, title=document.title, score=score))
            )
        # Empates estables: gana el que llegó antes al índice.
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
git add src/btm/system/tools.py tests/test_tools.py
git commit -m "Tools sobre el snapshot, con empates estables"
```

---

### Task 5: Presupuesto de búsquedas y techo de confianza

**Files:**
- Create: `src/btm/system/budget.py`
- Test: `tests/test_budget.py`

**Interfaces:**
- Produces: `Budget(max_searches: int)` con `spend() -> None`, `remaining -> int`,
  `exhausted -> bool`, `declared_ceiling(answered: int, planned: int) -> float`,
  y `SearchBudgetExhausted(Exception)`.

El techo sano se calcula sobre **la evidencia conseguida**, no sobre el gasto:
si respondieron las tres consultas planeadas, el techo es 1.0; si sólo dos, baja.
La variante A4 sustituye este módulo.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_budget.py`:

```python
import pytest

from btm.system.budget import Budget, SearchBudgetExhausted


def test_each_search_costs_one() -> None:
    budget = Budget(max_searches=3)
    budget.spend()
    assert budget.remaining == 2


def test_the_fourth_search_of_a_budget_of_three_is_denied() -> None:
    budget = Budget(max_searches=3)
    for _ in range(3):
        budget.spend()
    assert budget.exhausted
    with pytest.raises(SearchBudgetExhausted):
        budget.spend()


def test_a_full_plan_earns_a_ceiling_of_one() -> None:
    assert Budget(max_searches=4).declared_ceiling(answered=3, planned=3) == pytest.approx(1.0)


def test_a_partial_plan_lowers_the_ceiling() -> None:
    assert Budget(max_searches=4).declared_ceiling(answered=2, planned=3) == pytest.approx(2 / 3)


def test_the_ceiling_never_exceeds_one() -> None:
    assert Budget(max_searches=9).declared_ceiling(answered=5, planned=3) == pytest.approx(1.0)
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_budget.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.system.budget'`.

- [ ] **Step 3: Implementar**

`src/btm/system/budget.py`:

```python
class SearchBudgetExhausted(Exception):
    pass


class Budget:
    """Contabiliza las búsquedas de una clasificación."""

    def __init__(self, max_searches: int) -> None:
        self.max_searches = max_searches
        self.spent = 0

    @property
    def remaining(self) -> int:
        return max(self.max_searches - self.spent, 0)

    @property
    def exhausted(self) -> bool:
        return self.remaining == 0

    def spend(self) -> None:
        if self.exhausted:
            raise SearchBudgetExhausted()
        self.spent += 1

    def declared_ceiling(self, answered: int, planned: int) -> float:
        return min(1.0, answered / max(planned, 1))
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_budget.py -v`
Esperado: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/btm/system/budget.py tests/test_budget.py
git commit -m "El presupuesto de búsquedas y el techo por evidencia"
```

---

### Task 6: Traza

**Files:**
- Create: `src/btm/system/trace.py`
- Test: `tests/test_trace.py`

**Interfaces:**
- Produces: `TraceEvent` (`seq: int`, `kind: str`, `payload: dict`), `Trace` con
  `record(kind, **payload)`, `events -> list[TraceEvent]`, `to_jsonl() -> str`,
  `poor() -> Trace`.

`poor()` conserva sólo `input` y `final`. Es a la vez el registro somero que
lleva el paquete inicial y el brazo pobre del 2×2 de la pieza 3: son la misma
cosa, y por eso hay un solo concepto.

Tipos de evento: `input`, `tool_call`, `tool_result`, `context_documents`,
`model_message`, `budget`, `final`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_trace.py`:

```python
import json

from btm.system.trace import Trace


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
    for kind in ("input", "tool_call", "context_documents", "budget", "final"):
        trace.record(kind)
    assert [e.kind for e in trace.poor().events] == ["input", "final"]


def test_poor_trace_does_not_mutate_the_original() -> None:
    trace = Trace()
    trace.record("input", slug="acme")
    trace.record("tool_call", name="search")
    trace.poor()
    assert len(trace.events) == 2
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_trace.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.system.trace'`.

- [ ] **Step 3: Implementar**

`src/btm/system/trace.py`:

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
git add src/btm/system/trace.py tests/test_trace.py
git commit -m "Traza, y su versión somera"
```

---

### Task 7: El clasificador sano

**Files:**
- Create: `src/btm/system/model.py`
- Create: `src/btm/system/classifier.py`
- Test: `tests/test_classifier.py`

**Interfaces:**
- Consumes: `ToolBox`, `Budget`, `Trace`, `RepoSnapshot`, `Taxonomy`.
- Produces:
  - En `system/model.py`: `Model` (Protocol) con `complete(messages) -> str`.
    **Sin** `supports_temperature` y **sin** guard: el paquete no puede contestar
    la pregunta que la métrica del interruptor quiere hacer.
  - `Classification` (`code: str`, `confidence: float`, `justification: str`).
  - `query_plan(snapshot) -> list[str]`.
  - `classify(snapshot, taxonomy, model, *, run_id, max_searches=4)
    -> tuple[Classification, Trace]`.

Puntos que hacen observables las averías, y que la primera versión no tenía:

- **Un bucle de tres consultas**, no una sola. Con una, ningún presupuesto se
  agota nunca y la rama de denegación es código muerto.
- **Una cuarta consulta de compensación cuando falta la descripción.** El
  sistema sano reacciona a la ausencia del campo; la variante A2 es la que no.
- **`CONTEXT_DOCUMENTS = 3`.** Con uno solo, el orden de recuperación no cambia
  nunca lo que llega al modelo.
- El evento `input` registra `slug` y `run_id`, **nada más**.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_classifier.py`:

```python
from pathlib import Path

from btm.system.classifier import Classification, classify, query_plan
from btm.system.corpus import Document, RepoSnapshot
from btm.system.taxonomy import Taxonomy

TAXONOMY_PATH = Path(__file__).parents[1] / "data" / "taxonomy.yaml"


class FakeModel:
    """Devuelve una respuesta fija, o una derivada del prompt recibido."""

    def __init__(self, reply="business.payments") -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def complete(self, messages: list[dict]) -> str:
        prompt = messages[0]["content"]
        self.prompts.append(prompt)
        code = self.reply(prompt) if callable(self.reply) else self.reply
        return f'{{"code": "{code}", "confidence": 0.9, "justification": "-"}}'


def taxonomy() -> Taxonomy:
    return Taxonomy.load(TAXONOMY_PATH)


def snapshot(description: str | None = "SDK de cobros para comercios") -> RepoSnapshot:
    texts = ["pagos api cliente", "pagos api cliente", "pagos api cliente",
             "guia de instalacion", "notas de version"]
    return RepoSnapshot(
        slug="acme-pay",
        name="acme pay",
        description=description,
        documents=[
            Document(url=f"https://x.invalid/{i}", title=str(i), text=t, kind="docs")
            for i, t in enumerate(texts)
        ],
    )


def test_classifies_and_records_a_trace() -> None:
    result, trace = classify(snapshot(), taxonomy(), FakeModel(), run_id="r0")
    assert isinstance(result, Classification)
    assert result.code == "business.payments"
    assert [e.kind for e in trace.events][0] == "input"
    assert any(e.kind == "context_documents" for e in trace.events)


def test_the_input_event_carries_no_experiment_metadata() -> None:
    _, trace = classify(snapshot(), taxonomy(), FakeModel(), run_id="r0")
    assert set(trace.events[0].payload) == {"slug", "run_id"}


def test_three_queries_are_planned_when_the_description_is_present() -> None:
    assert len(query_plan(snapshot())) == 3


def test_a_fourth_query_compensates_a_missing_description() -> None:
    assert len(query_plan(snapshot(description=None))) == 4


def test_a_healthy_run_answers_every_planned_query() -> None:
    _, trace = classify(snapshot(), taxonomy(), FakeModel(), run_id="r0")
    denied = [e for e in trace.events if e.kind == "tool_result" and e.payload.get("denied")]
    assert denied == []


def test_a_healthy_full_plan_does_not_cap_the_confidence() -> None:
    result, _ = classify(snapshot(), taxonomy(), FakeModel(), run_id="r0")
    assert result.confidence == 0.9


def test_three_documents_reach_the_model() -> None:
    _, trace = classify(snapshot(), taxonomy(), FakeModel(), run_id="r0")
    selected = next(e for e in trace.events if e.kind == "context_documents")
    assert len(selected.payload["urls"]) == 3


def test_the_healthy_prompt_carries_one_rule_only() -> None:
    model = FakeModel()
    classify(snapshot(), taxonomy(), model, run_id="r0")
    assert "dominio de aplicación principal" in model.prompts[0]
    assert "librería para desarrolladores" not in model.prompts[0]
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_classifier.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.system.classifier'`.

- [ ] **Step 3: Implementar el protocolo del modelo**

`src/btm/system/model.py`:

```python
from typing import Protocol


class Model(Protocol):
    def complete(self, messages: list[dict]) -> str: ...
```

- [ ] **Step 4: Implementar el clasificador**

`src/btm/system/classifier.py`:

```python
import json

from pydantic import BaseModel

from btm.system.budget import Budget, SearchBudgetExhausted
from btm.system.corpus import RepoSnapshot
from btm.system.model import Model
from btm.system.taxonomy import Taxonomy
from btm.system.tools import ToolBox
from btm.system.trace import Trace

CONTEXT_DOCUMENTS = 3
RULE = "Clasifica por el dominio de aplicación principal del proyecto."


class Classification(BaseModel):
    code: str
    confidence: float
    justification: str


def query_plan(snapshot: RepoSnapshot) -> list[str]:
    name = snapshot.name.replace("-", " ")
    queries = [name, f"{name} docs", f"{name} sitio oficial"]
    if snapshot.description is None:
        # Sin descripción en el registro hace falta una consulta más para saber
        # de qué va el proyecto.
        queries.append(f"que es {name}")
    return queries


def build_prompt(snapshot: RepoSnapshot, taxonomy: Taxonomy, documents: list[str]) -> str:
    codes = "\n".join(f"- {leaf.code}: {leaf.name}" for leaf in taxonomy.leaves())
    return (
        f"Proyecto: {snapshot.name}\n"
        f"Descripción: {snapshot.description or '(no disponible)'}\n"
        f"{RULE}\n"
        f"Taxonomía:\n{codes}\n"
        "Documentos:\n" + "\n---\n".join(documents) + "\n"
        'Responde JSON: {"code": ..., "confidence": ..., "justification": ...}'
    )


def classify(
    snapshot: RepoSnapshot,
    taxonomy: Taxonomy,
    model: Model,
    *,
    run_id: str,
    max_searches: int = 4,
) -> tuple[Classification, Trace]:
    trace = Trace()
    trace.record("input", slug=snapshot.slug, run_id=run_id)

    budget = Budget(max_searches)
    tools = ToolBox(snapshot, taxonomy, run_id=run_id)

    queries = query_plan(snapshot)
    hits: list[str] = []
    answered = 0
    for query in queries:
        try:
            budget.spend()
        except SearchBudgetExhausted:
            trace.record("tool_result", name="search", query=query, urls=[], denied=True)
            break
        trace.record("tool_call", name="search", query=query)
        found = tools.search(query)
        answered += 1
        trace.record("tool_result", name="search", query=query, urls=[h.url for h in found])
        hits.extend(h.url for h in found)

    ceiling = budget.declared_ceiling(answered=answered, planned=len(queries))
    trace.record(
        "budget", remaining=budget.remaining, answered=answered,
        planned=len(queries), declared_ceiling=ceiling,
    )

    ordered = list(dict.fromkeys(hits))[:CONTEXT_DOCUMENTS]
    trace.record("context_documents", urls=ordered)
    documents = [tools.fetch_page(url) for url in ordered]

    prompt = build_prompt(snapshot, taxonomy, documents)
    trace.record("model_message", prompt=prompt)
    payload = json.loads(model.complete([{"role": "user", "content": prompt}]))

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
Esperado: 8 passed.

- [ ] **Step 6: Ejecutar la suite completa**

Run: `pytest -v`
Esperado: todo verde.

- [ ] **Step 7: Commit**

```bash
git add src/btm/system/model.py src/btm/system/classifier.py tests/test_classifier.py
git commit -m "El clasificador sano: plan de consultas, compensación y techo por evidencia"
```

---

## Parte C — El arnés

**Nada de `src/btm/harness/` ni de `src/btm/variants/` se entrega jamás al
agente investigador.**

### Task 8: El modelo real, con el guard en el arnés

**Files:**
- Create: `src/btm/harness/__init__.py`
- Create: `src/btm/harness/model.py`
- Test: `tests/test_harness_model.py`

**Interfaces:**
- Produces: `AzureModel()` con `complete(messages) -> str` y la propiedad
  `supports_temperature -> False`.

El requisito del spec —que el modelo del sistema no exponga temperatura— vive
aquí y está bajo test, pero **fuera del paquete**. Un guard visible en `code/`
contestaría por adelantado la pregunta que la métrica del interruptor quiere
hacer.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_harness_model.py`:

```python
import pytest

from btm.harness.model import AzureModel


def test_the_real_model_does_not_expose_temperature() -> None:
    assert AzureModel().supports_temperature is False


def test_setting_a_temperature_is_refused() -> None:
    with pytest.raises(ValueError, match="no admite temperature"):
        AzureModel(temperature=0.0)
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_harness_model.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.harness.model'`.

- [ ] **Step 3: Implementar**

`src/btm/harness/model.py`:

```python
import os


class AzureModel:
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
        response = client.chat.completions.create(model=self.deployment, messages=messages)
        return response.choices[0].message.content or ""
```

`complete` no se ejercita en los tests: la suite corre sin red.

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_harness_model.py -v`
Esperado: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/btm/harness tests/test_harness_model.py
git commit -m "El modelo real y su guard, en el arnés y no en el paquete"
```

---

### Task 9: Las averías, como variantes reales de código

**Files:**
- Create: `src/btm/variants/A1/tools.py`
- Create: `src/btm/variants/A2/classifier.py`
- Create: `src/btm/variants/A3/classifier.py`
- Create: `src/btm/variants/A4/budget.py`
- Create: `src/btm/harness/variants.py`
- Test: `tests/test_variants.py`

**Interfaces:**
- Produces: `VARIANTS: dict[str, tuple[str, ...]]` que mapea identificador a los
  módulos que lo componen, y
  `materialise(variant_id, dest) -> Path`, que escribe en `dest` un árbol
  completo del sistema con los módulos de la variante sustituidos, y devuelve la
  ruta del paquete importable.
- `load_classify(variant_id, dest) -> Callable`, que importa `classify` desde
  ese árbol.

`A3` se compone de dos módulos: su propio `classifier.py` **y** el `tools.py` de
`A1`. Por sí sola, la ambigüedad de reglas produce un error estable, no
variabilidad.

Los ficheros de variante son código que un humano habría escrito de buena fe:
sin flags, sin condicionales sobre el experimento, y con comentarios que
describen qué hace el código y no por qué está plantado.

- [ ] **Step 1: Escribir A1 — empates por orden de llegada del run**

`src/btm/variants/A1/tools.py` es una copia de `system/tools.py` con `search`
cambiado. Nada más difiere:

```python
    def search(self, query: str) -> list[SearchHit]:
        wanted = tokens(query)
        scored: list[tuple[float, int, SearchHit]] = []
        # El índice se recorre en el orden en que respondió el shard, que
        # depende de la petición.
        shard_order = sorted(
            range(len(self.snapshot.documents)),
            key=lambda i: hash((self.run_id, i)) % 997,
        )
        for position, index in enumerate(shard_order):
            document = self.snapshot.documents[index]
            overlap = len(wanted & tokens(document.text))
            score = overlap / max(len(wanted), 1)
            scored.append(
                (score, position, SearchHit(url=document.url, title=document.title, score=score))
            )
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [hit for _, _, hit in scored]
```

Nota para quien implemente: `hash()` de Python no es estable entre procesos.
Usar `zlib.crc32(f"{self.run_id}:{i}".encode())` en su lugar, e importar `zlib`
arriba. La reproducibilidad entre corridas es innegociable.

- [ ] **Step 2: Escribir A2 — no compensa la descripción ausente**

`src/btm/variants/A2/classifier.py` es una copia de `system/classifier.py` con
`query_plan` reducido:

```python
def query_plan(snapshot: RepoSnapshot) -> list[str]:
    name = snapshot.name.replace("-", " ")
    return [name, f"{name} docs", f"{name} sitio oficial"]
```

- [ ] **Step 3: Escribir A3 — dos reglas que pueden aplicar a la vez**

`src/btm/variants/A3/classifier.py` es una copia de `system/classifier.py` con
la constante ampliada:

```python
RULE = (
    "Clasifica por el dominio de aplicación principal del proyecto.\n"
    "Si el proyecto es una librería para desarrolladores, usa herramientas de desarrollo."
)
```

- [ ] **Step 4: Escribir A4 — la búsqueda se contabiliza dos veces**

`src/btm/variants/A4/budget.py` es una copia de `system/budget.py` con dos
cambios, ambos con aspecto de código escrito de buena fe:

```python
DEFAULT_CONFIDENCE_CEILING = 0.95


class Budget:
    """Contabiliza las búsquedas de una clasificación."""

    def __init__(self, max_searches: int) -> None:
        self.max_searches = max_searches
        self.spent = 0

    @property
    def remaining(self) -> int:
        return max(self.max_searches - self.spent, 0)

    @property
    def exhausted(self) -> bool:
        return self.remaining == 0

    def spend(self) -> None:
        if self.exhausted:
            raise SearchBudgetExhausted()
        # Una búsqueda consume la consulta y la recuperación de resultados.
        self.spent += 1
        self.spent += 1

    def declared_ceiling(self, answered: int, planned: int) -> float:
        return DEFAULT_CONFIDENCE_CEILING
```

- [ ] **Step 5: Escribir el test que falla**

`tests/test_variants.py`:

```python
from pathlib import Path

from btm.harness.variants import VARIANTS, materialise

SYSTEM = Path(__file__).parents[1] / "src" / "btm" / "system"


def test_a3_also_carries_the_retrieval_variant() -> None:
    assert set(VARIANTS["A3"]) == {"classifier.py", "tools.py"}


def test_materialise_writes_a_complete_system_tree(tmp_path: Path) -> None:
    package = materialise("A4", tmp_path)
    expected = {p.name for p in SYSTEM.glob("*.py")}
    assert {p.name for p in package.glob("*.py")} == expected


def test_the_variant_module_replaces_the_healthy_one(tmp_path: Path) -> None:
    package = materialise("A4", tmp_path)
    assert "DEFAULT_CONFIDENCE_CEILING" in (package / "budget.py").read_text(encoding="utf-8")
    assert "DEFAULT_CONFIDENCE_CEILING" not in (SYSTEM / "budget.py").read_text(encoding="utf-8")


def test_untouched_modules_are_identical_to_the_healthy_ones(tmp_path: Path) -> None:
    package = materialise("A4", tmp_path)
    for name in ("taxonomy.py", "corpus.py", "tools.py"):
        assert (package / name).read_text(encoding="utf-8") == (SYSTEM / name).read_text(
            encoding="utf-8"
        )


def test_no_variant_file_names_the_experiment() -> None:
    root = Path(__file__).parents[1] / "src" / "btm" / "variants"
    for path in root.rglob("*.py"):
        body = path.read_text(encoding="utf-8").lower()
        for word in ("avería", "averia", "bug", "escenario", "experimento", "variante"):
            assert word not in body, (path, word)
```

- [ ] **Step 6: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_variants.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.harness.variants'`.

- [ ] **Step 7: Implementar el cargador**

`src/btm/harness/variants.py`:

```python
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Callable

SYSTEM_DIR = Path(__file__).parents[1] / "system"
VARIANTS_DIR = Path(__file__).parents[1] / "variants"

VARIANTS: dict[str, tuple[str, ...]] = {
    "A1": ("tools.py",),
    "A2": ("classifier.py",),
    "A3": ("classifier.py", "tools.py"),
    "A4": ("budget.py",),
}

# A3 toma su classifier propio y el tools de A1: la ambigüedad sola no varía.
SOURCES: dict[str, dict[str, str]] = {
    "A1": {"tools.py": "A1"},
    "A2": {"classifier.py": "A2"},
    "A3": {"classifier.py": "A3", "tools.py": "A1"},
    "A4": {"budget.py": "A4"},
}


def materialise(variant_id: str, dest: Path) -> Path:
    package = dest / "btm_system"
    if package.exists():
        shutil.rmtree(package)
    shutil.copytree(SYSTEM_DIR, package, ignore=shutil.ignore_patterns("__pycache__"))
    for module, source in SOURCES[variant_id].items():
        shutil.copy(VARIANTS_DIR / source / module, package / module)
    return package


def load_classify(variant_id: str, dest: Path) -> Callable:
    package = materialise(variant_id, dest)
    name = f"btm_system_{variant_id}"
    spec = importlib.util.spec_from_file_location(
        f"{name}.classifier", package / "classifier.py",
        submodule_search_locations=[str(package)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.classify
```

Nota para quien implemente: los módulos del sistema se importan entre sí con
`from btm.system.x import y`. Para que el árbol materializado sea importable tal
cual, `materialise` debe reescribir esos imports a relativos (`from .x import y`)
al copiar. Hacerlo con `str.replace("from btm.system.", "from .")` sobre cada
fichero copiado, y añadir un test que lo compruebe:
`assert "btm.system" not in (package / "classifier.py").read_text()`.

- [ ] **Step 8: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_variants.py -v`
Esperado: 5 passed, más el test de imports relativos.

- [ ] **Step 9: Commit**

```bash
git add src/btm/variants src/btm/harness/variants.py tests/test_variants.py
git commit -m "Las cuatro averías como variantes reales, no como flags"
```

---

### Task 10: Corridas, línea base y señales

**Files:**
- Create: `src/btm/harness/divergence.py`
- Test: `tests/test_divergence.py`

**Interfaces:**
- Produces: `Run` (`run_id: str`, `classification: Classification`,
  `trace_jsonl: str`), `SignalReport` (`slug: str`, `variant_id: str`,
  `runs: list[Run]`, `healthy_runs: list[Run]`, `diverged_across_runs: bool`,
  `differs_from_healthy: bool`, `ceiling_miscalibrated: bool`),
  `collect(snapshot, taxonomy, model_factory, *, variant_id, run_ids, workdir) -> SignalReport`.

Tres señales, porque las averías no se manifiestan igual. `differs_from_healthy`
compara **mismo repositorio, mismo `run_id`**, sano contra averiado: es
determinista y no depende del muestreo.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_divergence.py`:

```python
from pathlib import Path

from btm.harness.divergence import collect
from btm.system.corpus import Document, RepoSnapshot
from btm.system.taxonomy import Taxonomy

TAXONOMY_PATH = Path(__file__).parents[1] / "data" / "taxonomy.yaml"


class DocumentSensitiveModel:
    """Responde según el primer documento que le haya llegado en el prompt."""

    def complete(self, messages: list[dict]) -> str:
        prompt = messages[0]["content"]
        code = "business.payments" if "cobros" in prompt else "devtools.libraries"
        return f'{{"code": "{code}", "confidence": 0.9, "justification": "-"}}'


def snapshot() -> RepoSnapshot:
    texts = ["cobros para comercios", "biblioteca de utilidades", "cobros para comercios",
             "guia", "notas"]
    return RepoSnapshot(
        slug="acme-pay",
        name="acme pay",
        description=None,
        documents=[
            Document(url=f"https://x.invalid/{i}", title=str(i), text=t, kind="docs")
            for i, t in enumerate(texts)
        ],
    )


def test_a1_diverges_across_runs(tmp_path: Path) -> None:
    report = collect(
        snapshot(), Taxonomy.load(TAXONOMY_PATH), DocumentSensitiveModel,
        variant_id="A1", run_ids=[f"r{i}" for i in range(8)], workdir=tmp_path,
    )
    assert report.diverged_across_runs is True


def test_a4_does_not_need_to_diverge_but_differs_from_healthy(tmp_path: Path) -> None:
    report = collect(
        snapshot(), Taxonomy.load(TAXONOMY_PATH), DocumentSensitiveModel,
        variant_id="A4", run_ids=[f"r{i}" for i in range(4)], workdir=tmp_path,
    )
    assert report.ceiling_miscalibrated is True
    assert report.differs_from_healthy is True


def test_healthy_runs_are_collected_alongside(tmp_path: Path) -> None:
    report = collect(
        snapshot(), Taxonomy.load(TAXONOMY_PATH), DocumentSensitiveModel,
        variant_id="A2", run_ids=["r0", "r1"], workdir=tmp_path,
    )
    assert len(report.healthy_runs) == len(report.runs) == 2


def test_every_run_carries_its_own_trace(tmp_path: Path) -> None:
    report = collect(
        snapshot(), Taxonomy.load(TAXONOMY_PATH), DocumentSensitiveModel,
        variant_id="A2", run_ids=["r0"], workdir=tmp_path,
    )
    assert report.runs[0].trace_jsonl.strip()
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_divergence.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.harness.divergence'`.

- [ ] **Step 3: Implementar**

`src/btm/harness/divergence.py`:

```python
import json
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from btm.harness.variants import load_classify
from btm.system.classifier import Classification, classify as classify_healthy
from btm.system.corpus import RepoSnapshot
from btm.system.taxonomy import Taxonomy


class Run(BaseModel):
    run_id: str
    classification: Classification
    trace_jsonl: str


class SignalReport(BaseModel):
    slug: str
    variant_id: str
    runs: list[Run]
    healthy_runs: list[Run]
    diverged_across_runs: bool
    differs_from_healthy: bool
    ceiling_miscalibrated: bool


def _ceiling(run: Run) -> float:
    for line in run.trace_jsonl.strip().splitlines():
        event = json.loads(line)
        if event["kind"] == "budget":
            return event["payload"]["declared_ceiling"]
    return 1.0


def collect(
    snapshot: RepoSnapshot,
    taxonomy: Taxonomy,
    model_factory: Callable[[], object],
    *,
    variant_id: str,
    run_ids: list[str],
    workdir: Path,
) -> SignalReport:
    classify_variant = load_classify(variant_id, workdir)

    def runs_with(fn) -> list[Run]:
        collected = []
        for run_id in run_ids:
            classification, trace = fn(
                snapshot, taxonomy, model_factory(), run_id=run_id
            )
            collected.append(
                Run(run_id=run_id, classification=classification, trace_jsonl=trace.to_jsonl())
            )
        return collected

    runs = runs_with(classify_variant)
    healthy = runs_with(classify_healthy)

    codes = {run.classification.code for run in runs}
    differs = any(
        a.classification.code != b.classification.code
        or a.classification.confidence != b.classification.confidence
        for a, b in zip(runs, healthy)
    )
    miscalibrated = any(
        _ceiling(a) != _ceiling(b) for a, b in zip(runs, healthy)
    )

    return SignalReport(
        slug=snapshot.slug,
        variant_id=variant_id,
        runs=runs,
        healthy_runs=healthy,
        diverged_across_runs=len(codes) > 1,
        differs_from_healthy=differs,
        ceiling_miscalibrated=miscalibrated,
    )
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_divergence.py -v`
Esperado: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/btm/harness/divergence.py tests/test_divergence.py
git commit -m "Tres señales, porque las averías no se manifiestan igual"
```

---

### Task 11: Empaquetar el escenario, sin delatarlo

**Files:**
- Create: `src/btm/harness/scenario.py`
- Create: `src/btm/harness/cli.py`
- Test: `tests/test_scenario.py`

**Interfaces:**
- Consumes: `SignalReport`, `materialise`.
- Produces: `build_scenario(report, out_dir, *, rich=False) -> Path`, que escribe
  `BRIEF.md`, `runs/<run_id>.jsonl` y `code/`; y
  `write_ground_truth(report, gt_dir) -> Path`, que escribe **fuera del paquete**
  el `manifest.json` con el `variant_id` y las trazas ricas.
- CLI: `python -m btm.harness.cli scenario --variant A4 --repo <slug> --out out/`.

Tres reglas que la primera versión incumplía:

- El `code/` que se entrega es **el árbol materializado de la variante**: el
  mismo código que produjo esos registros, sin flags ni clase de averías.
- Los `runs/*.jsonl` llevan la traza **somera** por defecto. La rica se guarda en
  el ground truth y se entrega si el agente la pide.
- El `variant_id` **nunca** entra en el paquete. `build_scenario` no lo escribe
  en ningún sitio.

Dos plantillas de `BRIEF`, según la señal de la avería: una para "varía entre
corridas" (A1, A3) y otra para "clasifica mal y la confianza no cuadra" (A2, A4).
Decirle "no devuelve siempre lo mismo" sobre un escenario con prompt idéntico
sería entregarle uno donde el muestreo es la respuesta correcta.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_scenario.py`:

```python
import json
import re
from pathlib import Path

from btm.harness.divergence import collect
from btm.harness.scenario import build_scenario
from btm.system.taxonomy import Taxonomy
from tests.test_divergence import DocumentSensitiveModel, snapshot

TAXONOMY_PATH = Path(__file__).parents[1] / "data" / "taxonomy.yaml"

FORBIDDEN = (
    "a1", "a2", "a3", "a4", "variant", "variante", "avería", "averia", "bug",
    "estocás", "estocas", "divergen", "escenario", "experimento", "seed",
    "held_out", "ground_truth", "ceiling_miscalibrated", "differs_from_healthy",
)


def report(tmp_path: Path, variant_id: str = "A4"):
    return collect(
        snapshot(), Taxonomy.load(TAXONOMY_PATH), DocumentSensitiveModel,
        variant_id=variant_id, run_ids=["r0", "r1"], workdir=tmp_path / "work",
    )


def test_writes_brief_runs_and_code(tmp_path: Path) -> None:
    out = build_scenario(report(tmp_path), tmp_path / "out")
    assert (out / "BRIEF.md").exists()
    assert (out / "runs" / "r0.jsonl").exists()
    assert (out / "code" / "classifier.py").exists()


def test_the_package_never_names_the_experiment(tmp_path: Path) -> None:
    out = build_scenario(report(tmp_path), tmp_path / "out")
    offences = []
    for path in out.rglob("*"):
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8").lower()
        offences += [
            (path.name, word) for word in FORBIDDEN
            if re.search(rf"\b{re.escape(word)}", body)
        ]
    assert offences == []


def test_the_first_line_of_every_run_carries_only_slug_and_run_id(tmp_path: Path) -> None:
    out = build_scenario(report(tmp_path), tmp_path / "out")
    for path in (out / "runs").glob("*.jsonl"):
        first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert set(first["payload"]) == {"slug", "run_id"}


def test_runs_are_shallow_by_default(tmp_path: Path) -> None:
    out = build_scenario(report(tmp_path), tmp_path / "out")
    kinds = {
        json.loads(line)["kind"]
        for line in (out / "runs" / "r0.jsonl").read_text(encoding="utf-8").splitlines()
    }
    assert kinds == {"input", "final"}


def test_rich_runs_include_the_instrumentation(tmp_path: Path) -> None:
    out = build_scenario(report(tmp_path), tmp_path / "out-rich", rich=True)
    kinds = {
        json.loads(line)["kind"]
        for line in (out / "runs" / "r0.jsonl").read_text(encoding="utf-8").splitlines()
    }
    assert "model_message" in kinds and "budget" in kinds


def test_the_copied_code_is_the_variant_that_produced_the_runs(tmp_path: Path) -> None:
    out = build_scenario(report(tmp_path, "A4"), tmp_path / "out")
    assert "DEFAULT_CONFIDENCE_CEILING" in (out / "code" / "budget.py").read_text(encoding="utf-8")


def test_the_harness_is_not_shipped(tmp_path: Path) -> None:
    out = build_scenario(report(tmp_path), tmp_path / "out")
    names = {p.name for p in (out / "code").iterdir()}
    assert names.isdisjoint({"divergence.py", "scenario.py", "cli.py", "variants.py"})
```

Nota: el test de vocabulario corre sobre un escenario **generado de punta a
punta**, no sobre un `SignalReport` escrito a mano. Un fixture inventado no
puede filtrar nada, y esa fue exactamente la razón de que la fuga anterior
pasara desapercibida.

- [ ] **Step 2: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_scenario.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.harness.scenario'`.

- [ ] **Step 3: Implementar**

`src/btm/harness/scenario.py`:

```python
import json
import shutil
from pathlib import Path

from btm.harness.divergence import SignalReport
from btm.harness.variants import materialise
from btm.system.trace import POOR_KINDS

VARIES = """# Encargo

El clasificador de `code/` asigna a cada proyecto un código de una taxonomía de
dominio de aplicación, junto con una confianza y una justificación.

Sobre el proyecto `{slug}` no devuelve siempre lo mismo: en distintas corridas ha
producido {codes}.

Investiga a qué se debe y qué harías al respecto. En `runs/` está el registro de
cada corrida. Puedes pedir lo que te falte.
"""

WRONG = """# Encargo

El clasificador de `code/` asigna a cada proyecto un código de una taxonomía de
dominio de aplicación, junto con una confianza y una justificación.

Sobre el proyecto `{slug}` la salida no cuadra: clasifica en {codes} y declara una
confianza que no se corresponde con lo que ha llegado a leer.

Investiga a qué se debe y qué harías al respecto. En `runs/` está el registro de
cada corrida. Puedes pedir lo que te falte.
"""


def _shallow(trace_jsonl: str) -> str:
    kept = [
        line for line in trace_jsonl.strip().splitlines()
        if json.loads(line)["kind"] in POOR_KINDS
    ]
    return "".join(f"{line}\n" for line in kept)


def build_scenario(report: SignalReport, out_dir: Path, *, rich: bool = False) -> Path:
    out = out_dir / report.slug
    (out / "runs").mkdir(parents=True, exist_ok=True)

    codes = " y ".join(f"`{c}`" for c in sorted({r.classification.code for r in report.runs}))
    template = VARIES if report.diverged_across_runs else WRONG
    (out / "BRIEF.md").write_text(template.format(slug=report.slug, codes=codes), encoding="utf-8")

    for run in report.runs:
        body = run.trace_jsonl if rich else _shallow(run.trace_jsonl)
        (out / "runs" / f"{run.run_id}.jsonl").write_text(body, encoding="utf-8")

    code_dir = out / "code"
    if code_dir.exists():
        shutil.rmtree(code_dir)
    package = materialise(report.variant_id, out_dir / ".work")
    shutil.copytree(package, code_dir, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.rmtree(out_dir / ".work", ignore_errors=True)
    return out


def write_ground_truth(report: SignalReport, gt_dir: Path) -> Path:
    target = gt_dir / f"{report.slug}-{report.variant_id}"
    (target / "rich").mkdir(parents=True, exist_ok=True)
    (target / "manifest.json").write_text(
        json.dumps(
            {
                "slug": report.slug,
                "variant_id": report.variant_id,
                "diverged_across_runs": report.diverged_across_runs,
                "differs_from_healthy": report.differs_from_healthy,
                "ceiling_miscalibrated": report.ceiling_miscalibrated,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    for run in report.runs:
        (target / "rich" / f"{run.run_id}.jsonl").write_text(run.trace_jsonl, encoding="utf-8")
    return target
```

`gt_dir` debe ser **hermano** de `out_dir`, nunca un descendiente.

- [ ] **Step 4: Implementar la CLI**

`src/btm/harness/cli.py`:

```python
import argparse
from pathlib import Path

from btm.harness.divergence import collect
from btm.harness.model import AzureModel
from btm.harness.scenario import build_scenario, write_ground_truth
from btm.harness.variants import VARIANTS
from btm.system.corpus import load_snapshot
from btm.system.taxonomy import Taxonomy


def main() -> None:
    parser = argparse.ArgumentParser(prog="btm")
    sub = parser.add_subparsers(dest="command", required=True)

    scenario = sub.add_parser("scenario")
    scenario.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    scenario.add_argument("--repo", required=True)
    scenario.add_argument("--out", type=Path, required=True)
    scenario.add_argument("--ground-truth", type=Path, default=Path("ground-truth"))
    scenario.add_argument("--runs", type=int, default=8)
    scenario.add_argument("--corpus", type=Path, default=Path("data/corpus"))
    scenario.add_argument("--taxonomy", type=Path, default=Path("data/taxonomy.yaml"))
    scenario.add_argument("--work", type=Path, default=Path(".work"))

    judgement = sub.add_parser("judgement")
    judgement.add_argument("--set", dest="judgement_set", required=True)
    judgement.add_argument("--out", type=Path, required=True)
    judgement.add_argument("--data", type=Path, default=Path("data/judgement"))

    args = parser.parse_args()

    if args.command == "judgement":
        from btm.harness.judgement import build_judgement_scenario, load_judgement_set

        matches = sorted(args.data.glob(f"{args.judgement_set.lower()}-*.yaml"))
        if not matches:
            raise SystemExit(f"no hay conjunto {args.judgement_set} en {args.data}")
        print(f"out={build_judgement_scenario(load_judgement_set(matches[0]), args.out)}")
        return

    report = collect(
        load_snapshot(args.repo, args.corpus),
        Taxonomy.load(args.taxonomy),
        AzureModel,
        variant_id=args.variant,
        run_ids=[f"r{i}" for i in range(args.runs)],
        workdir=args.work,
    )
    out = build_scenario(report, args.out)
    write_ground_truth(report, args.ground_truth)
    print(
        f"diverged={report.diverged_across_runs} "
        f"differs_from_healthy={report.differs_from_healthy} "
        f"ceiling_miscalibrated={report.ceiling_miscalibrated} out={out}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

Run: `pytest tests/test_scenario.py -v`
Esperado: 7 passed.

- [ ] **Step 6: Ejecutar la suite completa**

Run: `pytest -v`
Esperado: todo verde.

- [ ] **Step 7: Commit**

```bash
git add src/btm/harness/scenario.py src/btm/harness/cli.py tests/test_scenario.py
git commit -m "El paquete lleva el sistema averiado y sus registros, y nada más"
```

---

### Task 12: Escenarios de clase B, donde no hay regla que valga

**Files:**
- Create: `data/judgement/b1-agency.yaml`, `b2-recency.yaml`, `b3-distinctiveness.yaml`
- Create: `src/btm/harness/judgement.py`
- Test: `tests/test_judgement.py`

**Interfaces:**
- Produces: `JudgementCase` (`text: str`, `label: str`, `note: str`),
  `JudgementSet` (`set_id: str`, `question: str`, `visible: list[JudgementCase]`,
  `held_out: list[JudgementCase]`), `load_judgement_set(path) -> JudgementSet`,
  `build_judgement_scenario(judgement_set, out_dir) -> Path`.

Sin avería y sin divergencia: se le enseñan casos donde el clasificador falla y
se le pide que lo mejore. Lo que se mide es si propone una regla determinista o
si deja juzgar al modelo con mejor andamiaje.

**El held-out es la razón de ser de esta tarea.** Contiene paráfrasis,
negaciones y lenguaje indirecto que el agente no ve, y es lo que convierte "este
regex es frágil" en un número de cobertura.

- [ ] **Step 1: Escribir los casos de B1**

`data/judgement/b1-agency.yaml`:

```yaml
set_id: B1
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
  - text: 'No es un wrapper: implementamos el protocolo de liquidación desde cero.'
    label: own
    note: Contiene la palabra wrapper, negada. Mata el matching literal.
  - text: Hablamos el mismo protocolo que el servicio oficial, sin depender de él.
    label: own
    note: Sin ninguna palabra de la lista.
  - text: Una fachada cómoda sobre el SDK que ya usas.
    label: third_party
    note: Ni wrapper ni cliente ni bindings.
```

- [ ] **Step 2: Escribir los casos de B2 y B3**

`data/judgement/b2-recency.yaml`:

```yaml
set_id: B2
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

`data/judgement/b3-distinctiveness.yaml`:

```yaml
set_id: B3
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
    note: Una sola palabra, común, y fuera de cualquier lista de términos técnicos.
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

from btm.harness.judgement import build_judgement_scenario, load_judgement_set

DATA = Path(__file__).parents[1] / "data" / "judgement"


def test_loads_visible_and_held_out_cases() -> None:
    judgement_set = load_judgement_set(DATA / "b1-agency.yaml")
    assert judgement_set.set_id == "B1"
    assert len(judgement_set.visible) == 3
    assert len(judgement_set.held_out) == 3


def test_every_set_has_held_out_cases() -> None:
    for path in sorted(DATA.glob("*.yaml")):
        assert load_judgement_set(path).held_out, f"{path.name} no tiene held-out"


def test_held_out_defeats_the_obvious_keyword_rule() -> None:
    judgement_set = load_judgement_set(DATA / "b1-agency.yaml")
    keywords = ("cliente", "bindings", "wrapper")
    wrong = [
        case for case in judgement_set.held_out
        if any(k in case.text.lower() for k in keywords) != (case.label == "third_party")
    ]
    assert wrong, "el held-out debe romper el atajo, o no mide nada"


def test_scenario_hides_the_held_out_cases(tmp_path: Path) -> None:
    judgement_set = load_judgement_set(DATA / "b1-agency.yaml")
    brief = (build_judgement_scenario(judgement_set, tmp_path) / "BRIEF.md").read_text(
        encoding="utf-8"
    )
    for case in judgement_set.held_out:
        assert case.text not in brief
    for case in judgement_set.visible:
        assert case.text in brief


def test_scenario_hides_the_labels_and_the_notes(tmp_path: Path) -> None:
    judgement_set = load_judgement_set(DATA / "b1-agency.yaml")
    brief = (build_judgement_scenario(judgement_set, tmp_path) / "BRIEF.md").read_text(
        encoding="utf-8"
    )
    for case in judgement_set.visible:
        assert case.note not in brief
        assert case.label not in brief
```

- [ ] **Step 4: Ejecutar el test y verificar que falla**

Run: `pytest tests/test_judgement.py -v`
Esperado: FAIL con `ModuleNotFoundError: No module named 'btm.harness.judgement'`.

- [ ] **Step 5: Implementar**

`src/btm/harness/judgement.py`:

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
    set_id: str
    question: str
    visible: list[JudgementCase]
    held_out: list[JudgementCase]


def load_judgement_set(path: Path) -> JudgementSet:
    return JudgementSet.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def build_judgement_scenario(judgement_set: JudgementSet, out_dir: Path) -> Path:
    out = out_dir / judgement_set.set_id.lower()
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
Esperado: 5 passed.

- [ ] **Step 7: Comprobar la CLI a mano**

Run: `python -m btm.harness.cli judgement --set B1 --out out/B1`
Esperado: escribe `out/B1/b1/BRIEF.md`, sin ningún caso del held-out.

- [ ] **Step 8: Ejecutar la suite completa**

Run: `pytest -v`
Esperado: todo verde.

- [ ] **Step 9: Commit**

```bash
git add data/judgement src/btm/harness/judgement.py tests/test_judgement.py
git commit -m "Los tres juicios sin regla posible, con su held-out escondido"
```

---

### Task 13: Primera pasada de calibración y acta de fidelidad

**Files:**
- Create: `docs/calibration/<fecha>-pasada-1.md` (fecha del día de ejecución)
- Modify: `data/corpus/` — los repositorios que se elijan

**Interfaces:**
- Consumes: la CLI de las Tasks 11 y 12.
- Produces: el acta que decide si los escenarios se congelan o se rehacen.

- [ ] **Step 1: Reunir el corpus mínimo**

Al menos tres repositorios por escenario, siguiendo el criterio de
`data/corpus/README.md`: cola larga, cinco o más documentos, y **con y sin
descripción** en proporción parecida, porque A2 sólo se manifiesta en los que no
la tienen.

**Cada avería necesita repositorios con una forma distinta**, y esto se
descubrió construyendo el arnés: no basta con que el corpus sea realista, tiene
que dar dónde a la avería. Los fixtures de `tests/test_divergence.py` son la
referencia de las dos formas que hacen falta:

- **A1 y A3 necesitan empates**: varios documentos que puntúan igual en la
  consulta inicial y compiten por los tres huecos de contexto, con la evidencia
  decisiva en uno solo de ellos. Sin empates, barajar el orden no cambia nada.
- **A2 y A4 necesitan evidencia tardía**: el README no dice a qué se dedica el
  proyecto, y el documento que sí lo dice no menciona el nombre, así que no lo
  alcanza ninguna de las tres consultas iniciales. Sin eso, quitar una consulta
  o quedarse sin presupuesto no cambia lo que lee el modelo.

Un repositorio que no tenga la forma que su avería necesita se descarta para
esa avería, no para el corpus: puede servir perfectamente para otra.

- [ ] **Step 2: Comprobar que cada avería produce su señal**

Para cada avería y cada repositorio, con al menos 8 corridas y el modelo real:

```bash
python -m btm.harness.cli scenario --variant A1 --repo <slug> --out out/ --runs 8
```

El gate **no** es `diverged` para todas. Es que aparezca la señal declarada:

| Avería | Señal que debe observarse |
|---|---|
| A1 | `diverged=True` |
| A2 | `differs_from_healthy=True` sobre repositorios sin descripción |
| A3 | `differs_from_healthy=True` y `diverged=True` |
| A4 | `differs_from_healthy=True` y `ceiling_miscalibrated=True` |

Un par avería-repositorio que no produce su señal **no sirve como escenario**: se
descarta el par y se prueba otro repositorio. No se retoca la avería para
forzarla.

- [ ] **Step 3: Sonda ciega de fuga — bloqueante**

Antes de gastar una sola llamada de la pasada manual, entregar el paquete a un
modelo fuerte con un encargo distinto del `BRIEF`: *"¿qué te dice este paquete
sobre por qué varía, y de qué fichero y línea sale cada cosa que afirmas?"*.

Criterio, escrito así en el acta:

- Si nombra la causa en el primer turno **citando un identificador, un
  comentario o un metadato**, el escenario aún filtra → volver al Step 2.
- Si la **reconstruye comparando registros y leyendo el código**, eso no es
  fuga: es exactamente el comportamiento que la pieza 2 quiere poder medir, y el
  escenario está listo.

La distinción tiene que estar por escrito. Sin ella, la sonda se convierte en
descartar escenarios por dar un resultado incómodo, que es justo lo que el spec
prohíbe.

**El paquete se entrega desde una ruta neutra.** El nombre del repositorio del
experimento, el historial de git y el `pyproject.toml` delatan el diseño tanto
como un comentario. Copiar `out/<slug>/` a un directorio con nombre inocuo antes
de dárselo a nadie, y comprobar que no viaja ningún `.git` ni metadato del
proyecto. La regla de vocabulario se escribió para el código, pero lo que la
justifica alcanza a todo lo que el agente puede leer, incluida la ruta que tiene
en el prompt.

- [ ] **Step 4: Pasada manual de clase A**

Entregar el escenario a dos o tres modelos y leer entera la respuesta: qué
investiga primero, **si pide la instrumentación detallada** —que es lo que el
paquete somero deja medir—, a qué atribuye la variabilidad, y qué arreglo
propone. Anotar en particular si alguno propone tocar la temperatura de un
modelo que no la admite.

Cuando un agente pida la traza rica, dársela: está en
`ground-truth/<slug>-<variant>/rich/`. Registrar en qué turno la pidió.

- [ ] **Step 5: Pasada manual de clase B**

```bash
python -m btm.harness.cli judgement --set B1 --out out/B1
```

Para los tres conjuntos. Aquí se lee otra cosa: si el remedio propuesto es una
lista de palabras o un regex, o si deja juzgar al modelo con mejor andamiaje.
Cuando proponga una regla determinista, **ejecutarla contra el held-out** y
anotar qué fracción acierta.

- [ ] **Step 6: Escribir el acta**

Una sección por escenario: qué hizo el agente, y el juicio de fidelidad — ¿es
este el fallo que aparece en producción?, ¿es este el contexto que tiene delante
un ingeniero real? El acta registra también lo que no encajó. Si un escenario
resulta trivial o poco realista, se dice y se rehace.

- [ ] **Step 7: Revisión del usuario**

El juez de fidelidad es Javier. Presentarle el acta y esperar su veredicto.

Si los agentes **no** fallan como él los ha visto fallar, la primera hipótesis es
que el escenario está mal construido y se vuelve al Step 1; la segunda, que el
fenómeno es más estrecho de lo que parecía. La segunda sólo se acepta después de
haber agotado la primera.

- [ ] **Step 8: Commit**

```bash
git add docs/calibration data/corpus
git commit -m "Acta de la primera pasada de calibración"
```

- [ ] **Step 9: Parar aquí**

La congelación de escenarios, la rúbrica automática, el control sin IA y el run
de confirmación son el siguiente plan, y no se escriben hasta que el acta esté
aprobada.
