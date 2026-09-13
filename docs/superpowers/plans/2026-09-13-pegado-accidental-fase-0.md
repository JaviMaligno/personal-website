# Pegado accidental — Fase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el arnés que genera conversaciones con un pegote accidental inyectado, y correr la Fase 0 (≈30 conversaciones, 3 modelos) cuyo producto es una rúbrica de clasificación derivada de leer las transcripciones a mano.

**Architecture:** Un paquete Python con tres clientes de inferencia detrás de una interfaz única (gateway LiteLLM, Vertex-Anthropic, Vertex-OpenAI-compat), un banco de artefactos independiente de los temas, y un orquestador que para cada conversación: conduce N turnos con un usuario simulado, mide la similaridad coseno de todos los artefactos del banco contra la conversación, muestrea uno de forma estratificada, lo inyecta como turno de usuario y registra todo en JSONL crudo.

**Tech Stack:** Python 3.12, `uv`, `pytest`, `httpx`, `numpy`. Sin SDKs de proveedor: los tres endpoints son HTTP y sus formas son distintas entre sí, así que un cliente propio y fino es más honesto que tres SDKs.

**Spec:** [`docs/superpowers/specs/2026-09-13-pegado-accidental-design.md`](../specs/2026-09-13-pegado-accidental-design.md)

## Global Constraints

- **Repo de código**: nuevo y público, en `~/Documents/repos/llm-wrong-paste`. Este plan vive en el repo del blog; el código NO.
- **Todo sintético.** Ningún tema, artefacto o transcripción sale de trabajo real ni de repos de la empresa.
- **Sin secretos en el repo.** La key del gateway se lee de `~/.acp-blog-paste-key`; las credenciales de GCP, de ADC. Nada de claves en ficheros versionados.
- **Registro en crudo, siempre.** Cada conversación se guarda íntegra en JSONL con: transcripción completa, artefacto usado, similaridad medida, modelo, longitud, semilla, parámetros de muestreo y `usage` devuelto. El análisis se hace después sobre esos ficheros.
- **Muestreo fijo y registrado**: `temperature=1.0` por defecto del proveedor salvo donde se indique; se registra siempre lo enviado.
- **Claude va por `global`**: `https://aiplatform.googleapis.com/v1/projects/{p}/locations/global/publishers/anthropic/models/{m}:rawPredict`. En `us-central1` la cuota está a cero y devuelve 429.
- **Gemini va por OpenAI-compat de `us-central1`**: `https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{p}/locations/us-central1/endpoints/openapi/chat/completions`, modelo `google/{m}`.
- **Proyecto GCP**: `data-science-364702`. Cabecera `x-goog-user-project` obligatoria.
- **Prefill de turno de asistente está eliminado** en la familia Claude 5. El arnés no puede apoyarse en él.
- **En zsh, usar `${M}` y no `$M:verbo`** al construir URLs: `:r` se interpreta como modificador de expansión y manda la URL mutilada (esto ya costó una hora una vez).

---

### Task 1: Esqueleto del repo y registro de modelos

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/pyproject.toml`
- Create: `~/Documents/repos/llm-wrong-paste/.gitignore`
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/__init__.py`
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/config.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_config.py`

**Interfaces:**
- Consumes: nada.
- Produces: `Model(id: str, provider: str, label: str, tier: str)`, `MODELS: dict[str, Model]`, `GCP_PROJECT: str`, `GATEWAY_URL: str`, `gateway_key() -> str`.

- [ ] **Step 1: Crear el repo y el esqueleto**

```bash
mkdir -p ~/Documents/repos/llm-wrong-paste/{src/wrongpaste,tests,data/artifacts,data/topics,runs}
cd ~/Documents/repos/llm-wrong-paste
git init
touch src/wrongpaste/__init__.py
```

`pyproject.toml`:

```toml
[project]
name = "wrongpaste"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27", "numpy>=2.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wrongpaste"]
```

`.gitignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

Nota: `runs/` **no** va en `.gitignore`. Los datos crudos se versionan; son el producto.

- [ ] **Step 2: Escribir el test que falla**

`tests/test_config.py`:

```python
from wrongpaste.config import MODELS, Model


def test_roster_has_nine_models():
    assert len(MODELS) == 9


def test_every_model_has_a_known_provider():
    providers = {m.provider for m in MODELS.values()}
    assert providers == {"gateway", "vertex_anthropic", "vertex_openai"}


def test_claude_models_are_vertex_anthropic():
    assert MODELS["claude-opus-5"].provider == "vertex_anthropic"
    assert MODELS["claude-sonnet-5"].provider == "vertex_anthropic"


def test_size_ladder_tiers_are_distinct():
    ladder = [m for m in MODELS.values() if m.tier in {"large", "medium", "small"}]
    assert len(ladder) >= 3
```

- [ ] **Step 3: Ejecutar el test y comprobar que falla**

```bash
cd ~/Documents/repos/llm-wrong-paste && uv venv && uv pip install -e ".[dev]"
uv run pytest tests/test_config.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.config'`.

- [ ] **Step 4: Implementar `config.py`**

```python
from dataclasses import dataclass
from pathlib import Path

GCP_PROJECT = "data-science-364702"
GATEWAY_URL = "https://litellm.infra.skyc.cloud"
GATEWAY_KEY_PATH = Path.home() / ".acp-blog-paste-key"

VERTEX_ANTHROPIC_URL = (
    "https://aiplatform.googleapis.com/v1/projects/{project}"
    "/locations/global/publishers/anthropic/models/{model}:rawPredict"
)
VERTEX_OPENAI_URL = (
    "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{project}"
    "/locations/us-central1/endpoints/openapi/chat/completions"
)

EMBEDDING_MODEL = "text-embedding-3-small-tst"


@dataclass(frozen=True)
class Model:
    id: str
    provider: str
    label: str
    tier: str


_ROSTER = [
    Model("gpt-5.6-sol-tst", "gateway", "GPT-5.6 sol", "large"),
    Model("gpt-5.6-terra-tst", "gateway", "GPT-5.6 terra", "medium"),
    Model("gpt-5.6-luna-tst", "gateway", "GPT-5.6 luna", "small"),
    Model("gpt-5.4-tst", "gateway", "GPT-5.4", "prev_large"),
    Model("gpt-5.4-mini-tst", "gateway", "GPT-5.4 mini", "prev_small"),
    Model("claude-opus-5", "vertex_anthropic", "Claude Opus 5", "large"),
    Model("claude-sonnet-5", "vertex_anthropic", "Claude Sonnet 5", "medium"),
    Model("gemini-2.5-pro", "vertex_openai", "Gemini 2.5 Pro", "large"),
    Model("gemini-2.5-flash", "vertex_openai", "Gemini 2.5 Flash", "small"),
]

MODELS = {m.id: m for m in _ROSTER}


def gateway_key() -> str:
    return GATEWAY_KEY_PATH.read_text().strip()
```

- [ ] **Step 5: Ejecutar el test y comprobar que pasa**

```bash
uv run pytest tests/test_config.py -v
```

Esperado: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore src tests
git commit -m "feat: esqueleto del repo y registro de los nueve modelos"
```

---

### Task 2: Los tres clientes de inferencia

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/clients.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_clients.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_smoke_live.py`

**Interfaces:**
- Consumes: `config.MODELS`, `config.gateway_key`, `config.GCP_PROJECT`, las tres URLs.
- Produces: `Reply(text: str, usage: dict, raw: dict)`, `chat(model_id: str, messages: list[dict], max_tokens: int = 1024) -> Reply`, `embed(texts: list[str]) -> numpy.ndarray`.

`messages` usa siempre la forma OpenAI (`{"role": "user"|"assistant", "content": str}`); la traducción al formato de Anthropic ocurre dentro del cliente. Así el resto del arnés no sabe de proveedores.

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_clients.py` (sin red — comprueba la traducción de formatos):

```python
from wrongpaste.clients import _anthropic_body, _gateway_body, _vertex_openai_body


def test_anthropic_body_moves_system_out_of_messages():
    msgs = [
        {"role": "system", "content": "eres útil"},
        {"role": "user", "content": "hola"},
    ]
    body = _anthropic_body(msgs, max_tokens=16)
    assert body["system"] == "eres útil"
    assert body["messages"] == [{"role": "user", "content": "hola"}]
    assert body["anthropic_version"] == "vertex-2023-10-16"
    assert body["max_tokens"] == 16


def test_anthropic_body_never_ends_on_assistant_turn():
    # El prefill está eliminado en la familia 5: un último turno de
    # assistant daría 400. El cliente debe negarse antes de llamar.
    msgs = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}]
    try:
        _anthropic_body(msgs, max_tokens=16)
    except ValueError as exc:
        assert "prefill" in str(exc).lower()
    else:
        raise AssertionError("debería haber lanzado ValueError")


def test_gateway_body_uses_max_completion_tokens():
    body = _gateway_body("gpt-5.6-sol-tst", [{"role": "user", "content": "x"}], 32)
    assert body["max_completion_tokens"] == 32
    assert "max_tokens" not in body


def test_vertex_openai_body_prefixes_model_with_google():
    body = _vertex_openai_body("gemini-2.5-pro", [{"role": "user", "content": "x"}], 32)
    assert body["model"] == "google/gemini-2.5-pro"
```

`tests/test_smoke_live.py` (con red, marcado para poder excluirlo):

```python
import pytest

from wrongpaste.clients import chat, embed

LIVE = [
    "gpt-5.6-luna-tst",      # gateway, el más barato
    "claude-sonnet-5",       # vertex_anthropic
    "gemini-2.5-flash",      # vertex_openai
]


@pytest.mark.live
@pytest.mark.parametrize("model_id", LIVE)
def test_each_provider_answers(model_id):
    reply = chat(model_id, [{"role": "user", "content": "Responde solo: ok"}], max_tokens=16)
    assert reply.text.strip().lower().startswith("ok")


@pytest.mark.live
def test_embeddings_have_1536_dimensions():
    vecs = embed(["hola", "adiós"])
    assert vecs.shape == (2, 1536)
```

Añadir a `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = ["live: hace llamadas reales a los modelos (cuesta dinero)"]
```

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

```bash
uv run pytest tests/test_clients.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.clients'`.

- [ ] **Step 3: Implementar `clients.py`**

```python
import subprocess
from dataclasses import dataclass

import httpx
import numpy as np

from wrongpaste import config

_TIMEOUT = httpx.Timeout(300.0)


@dataclass
class Reply:
    text: str
    usage: dict
    raw: dict


def _gcp_token() -> str:
    out = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def _gateway_body(model_id: str, messages: list[dict], max_tokens: int) -> dict:
    return {
        "model": model_id,
        "messages": messages,
        "max_completion_tokens": max_tokens,
    }


def _vertex_openai_body(model_id: str, messages: list[dict], max_tokens: int) -> dict:
    return {
        "model": f"google/{model_id}",
        "messages": messages,
        "max_tokens": max_tokens,
    }


def _anthropic_body(messages: list[dict], max_tokens: int) -> dict:
    if messages and messages[-1]["role"] == "assistant":
        raise ValueError(
            "prefill de turno de asistente eliminado en la familia Claude 5"
        )
    system = " ".join(m["content"] for m in messages if m["role"] == "system")
    convo = [m for m in messages if m["role"] != "system"]
    body = {
        "anthropic_version": "vertex-2023-10-16",
        "messages": convo,
        "max_tokens": max_tokens,
    }
    if system:
        body["system"] = system
    return body


def chat(model_id: str, messages: list[dict], max_tokens: int = 1024) -> Reply:
    model = config.MODELS[model_id]

    if model.provider == "gateway":
        resp = httpx.post(
            f"{config.GATEWAY_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.gateway_key()}"},
            json=_gateway_body(model_id, messages, max_tokens),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return Reply(data["choices"][0]["message"]["content"] or "", data.get("usage", {}), data)

    if model.provider == "vertex_openai":
        resp = httpx.post(
            config.VERTEX_OPENAI_URL.format(project=config.GCP_PROJECT),
            headers={"Authorization": f"Bearer {_gcp_token()}"},
            json=_vertex_openai_body(model_id, messages, max_tokens),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return Reply(data["choices"][0]["message"]["content"] or "", data.get("usage", {}), data)

    if model.provider == "vertex_anthropic":
        url = config.VERTEX_ANTHROPIC_URL.format(
            project=config.GCP_PROJECT, model=model_id
        )
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {_gcp_token()}",
                "x-goog-user-project": config.GCP_PROJECT,
            },
            json=_anthropic_body(messages, max_tokens),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
        return Reply(text, data.get("usage", {}), data)

    raise ValueError(f"proveedor desconocido: {model.provider}")


def embed(texts: list[str]) -> np.ndarray:
    resp = httpx.post(
        f"{config.GATEWAY_URL}/v1/embeddings",
        headers={"Authorization": f"Bearer {config.gateway_key()}"},
        json={"model": config.EMBEDDING_MODEL, "input": texts},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    rows = sorted(resp.json()["data"], key=lambda d: d["index"])
    return np.array([r["embedding"] for r in rows], dtype=np.float32)
```

- [ ] **Step 4: Ejecutar los tests sin red y comprobar que pasan**

```bash
uv run pytest tests/test_clients.py -v
```

Esperado: 4 passed.

- [ ] **Step 5: Ejecutar el smoke test con red**

Requiere VPN activa (el gateway resuelve a IP privada) y `gcloud auth login` vigente.

```bash
uv run pytest tests/test_smoke_live.py -v -m live
```

Esperado: 4 passed. Coste: céntimos.

- [ ] **Step 6: Commit**

```bash
git add src/wrongpaste/clients.py tests/test_clients.py tests/test_smoke_live.py pyproject.toml
git commit -m "feat: clientes de los tres proveedores tras una interfaz única"
```

---

### Task 3: Banco de artefactos

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/data/artifacts/*.md` (60-80 ficheros)
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/artifacts.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_artifacts.py`

**Interfaces:**
- Consumes: nada.
- Produces: `Artifact(id: str, kind: str, text: str, entities: list[str])`, `load_artifacts() -> list[Artifact]`.

El campo `entities` es la lista de términos distintivos del artefacto (nombres propios, identificadores, números raros). Se escribe **a mano** en el frontmatter de cada fichero, porque de ahí sale la métrica de fuga de la Fase 2 y una extracción automática sería ruido. Escribirlo ahora es barato; reconstruirlo después, no.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_artifacts.py`:

```python
from wrongpaste.artifacts import load_artifacts

MIN_ARTIFACTS = 60


def test_bank_is_big_enough():
    assert len(load_artifacts()) >= MIN_ARTIFACTS


def test_every_artifact_declares_entities():
    for art in load_artifacts():
        assert art.entities, f"{art.id} no declara entities"


def test_kinds_are_varied():
    kinds = {a.kind for a in load_artifacts()}
    assert len(kinds) >= 8


def test_ids_are_unique():
    ids = [a.id for a in load_artifacts()]
    assert len(ids) == len(set(ids))
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

```bash
uv run pytest tests/test_artifacts.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.artifacts'`.

- [ ] **Step 3: Escribir el formato y un artefacto de ejemplo**

`data/artifacts/recipe-lentejas.md`:

```markdown
---
id: recipe-lentejas
kind: recipe
entities: ["lentejas pardinas", "chorizo", "pimentón de la Vera", "45 minutos"]
---
300 g de lentejas pardinas, remojadas la noche anterior.
Sofreír cebolla, zanahoria y un diente de ajo. Añadir un chorizo en rodajas
y una cucharadita de pimentón de la Vera fuera del fuego, que si no se quema.
Cubrir con caldo, llevar a ebullición y bajar a fuego lento 45 minutos.
Sal al final.
```

Escribir 60-80 así, repartidos en al menos ocho `kind` distintos: `recipe`, `config`, `email`, `stacktrace`, `meeting_notes`, `sql`, `shopping_list`, `prompt`, `changelog`, `job_ad`. **Ninguno se escribe pensando en los temas de conversación** (§4.1 del spec): son artefactos de portapapeles, no distractores.

- [ ] **Step 4: Implementar `artifacts.py`**

```python
import json
from dataclasses import dataclass
from pathlib import Path

ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "data" / "artifacts"


@dataclass(frozen=True)
class Artifact:
    id: str
    kind: str
    text: str
    entities: tuple[str, ...]


def _parse(path: Path) -> Artifact:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise ValueError(f"{path.name}: falta el frontmatter")
    _, front, body = raw.split("---\n", 2)
    meta = {}
    for line in front.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return Artifact(
        id=meta["id"],
        kind=meta["kind"],
        text=body.strip(),
        entities=tuple(json.loads(meta["entities"])),
    )


def load_artifacts() -> list[Artifact]:
    return sorted(
        (_parse(p) for p in ARTIFACT_DIR.glob("*.md")),
        key=lambda a: a.id,
    )
```

- [ ] **Step 5: Ejecutar el test y comprobar que pasa**

```bash
uv run pytest tests/test_artifacts.py -v
```

Esperado: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add data/artifacts src/wrongpaste/artifacts.py tests/test_artifacts.py
git commit -m "feat: banco de artefactos de portapapeles, independiente de los temas"
```

---

### Task 4: Similaridad y muestreo estratificado

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/similarity.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_similarity.py`

**Interfaces:**
- Consumes: `clients.embed`, `artifacts.Artifact`.
- Produces: `cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray`, `rank_artifacts(conversation_text: str, arts: list[Artifact]) -> list[tuple[Artifact, float]]`, `stratified_pick(ranked, k: int, rng) -> list[tuple[Artifact, float]]`.

`stratified_pick` con `k=12` es lo que consumirá la **Fase 1** (12 pegotes por tema
cubriendo el rango). La Fase 0 no lo usa: con 24 celdas y un solo pegote por
conversación, el runner recorre un estrato distinto en cada celda (Task 7). Se
construye y se prueba ahora porque es donde vive la lógica y porque probarlo
aislado es trivial; dejarlo para la Fase 1 significaría escribirlo con prisa.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_similarity.py`:

```python
import numpy as np

from wrongpaste.artifacts import Artifact
from wrongpaste.similarity import cosine, stratified_pick


def test_cosine_of_identical_vectors_is_one():
    v = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
    assert np.isclose(cosine(v, v)[0][0], 1.0)


def test_cosine_of_orthogonal_vectors_is_zero():
    a = np.array([[1.0, 0.0]], dtype=np.float32)
    b = np.array([[0.0, 1.0]], dtype=np.float32)
    assert np.isclose(cosine(a, b)[0][0], 0.0)


def _fake_ranked(n):
    arts = [Artifact(f"a{i}", "k", "t", ("e",)) for i in range(n)]
    return [(a, i / (n - 1)) for i, a in enumerate(arts)]


def test_stratified_pick_covers_the_range():
    ranked = _fake_ranked(100)
    rng = np.random.default_rng(0)
    picked = stratified_pick(ranked, k=12, rng=rng)
    sims = sorted(s for _, s in picked)
    assert len(picked) == 12
    assert sims[0] < 0.2, "el estrato bajo no está representado"
    assert sims[-1] > 0.8, "el estrato alto no está representado"


def test_stratified_pick_is_deterministic_for_a_seed():
    ranked = _fake_ranked(100)
    one = stratified_pick(ranked, k=12, rng=np.random.default_rng(7))
    two = stratified_pick(ranked, k=12, rng=np.random.default_rng(7))
    assert [a.id for a, _ in one] == [a.id for a, _ in two]
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

```bash
uv run pytest tests/test_similarity.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.similarity'`.

- [ ] **Step 3: Implementar `similarity.py`**

```python
import numpy as np

from wrongpaste.artifacts import Artifact
from wrongpaste.clients import embed


def cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)
    return a_norm @ b_norm.T


def rank_artifacts(
    conversation_text: str, arts: list[Artifact]
) -> list[tuple[Artifact, float]]:
    vecs = embed([conversation_text] + [a.text for a in arts])
    sims = cosine(vecs[:1], vecs[1:])[0]
    return sorted(zip(arts, (float(s) for s in sims)), key=lambda p: p[1])


def stratified_pick(
    ranked: list[tuple[Artifact, float]], k: int, rng: np.random.Generator
) -> list[tuple[Artifact, float]]:
    """Un artefacto por estrato de igual anchura sobre el rango observado.

    Estratifica por posición en el ranking, no por valor de similaridad: la
    distribución real está muy concentrada y estratificar por valor dejaría
    estratos vacíos.
    """
    if len(ranked) < k:
        raise ValueError(f"el banco tiene {len(ranked)} artefactos, se piden {k}")
    edges = np.linspace(0, len(ranked), k + 1).astype(int)
    picked = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        idx = int(rng.integers(lo, max(hi, lo + 1)))
        picked.append(ranked[idx])
    return picked
```

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

```bash
uv run pytest tests/test_similarity.py -v
```

Esperado: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/similarity.py tests/test_similarity.py
git commit -m "feat: similaridad coseno y muestreo estratificado por ranking"
```

---

### Task 5: Temas y usuario simulado

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/data/topics/*.md` (8 ficheros)
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/topics.py`
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/simulated_user.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_topics.py`

**Interfaces:**
- Consumes: `clients.chat`.
- Produces: `Topic(id: str, opening: str, goals: tuple[str, ...])`, `load_topics() -> list[Topic]`, `USER_MODEL: str`, `next_user_turn(topic: Topic, history: list[dict]) -> str`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_topics.py`:

```python
from wrongpaste.topics import load_topics


def test_there_are_eight_topics():
    assert len(load_topics()) == 8


def test_every_topic_has_an_opening_and_goals():
    for topic in load_topics():
        assert topic.opening.strip()
        assert len(topic.goals) >= 4, f"{topic.id} tiene pocos objetivos"


def test_topic_ids_are_unique():
    ids = [t.id for t in load_topics()]
    assert len(ids) == len(set(ids))
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

```bash
uv run pytest tests/test_topics.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.topics'`.

- [ ] **Step 3: Escribir los ocho temas**

`data/topics/mudanza.md`:

```markdown
---
id: mudanza
---
opening: Me mudo de piso el mes que viene y no sé por dónde empezar a organizarme.
goals:
- Saber con cuánta antelación contratar la empresa de mudanzas
- Entender qué conviene tirar antes de empaquetar
- Decidir si merece la pena contratar seguro
- Hacer una lista de trámites de cambio de domicilio
- Saber cómo empaquetar cosas frágiles
```

Los ocho temas deben ser **deliberadamente dispares** y ninguno técnico de forma que se parezca a los artefactos de tipo `config`, `sql` o `stacktrace`: mudanza, entrenamiento para una carrera de 10 km, elegir colegio, aprender a hacer pan, planificar un viaje a Japón, montar un huerto en balcón, entender una factura de la luz, elegir cámara de fotos.

- [ ] **Step 4: Implementar `topics.py` y `simulated_user.py`**

`topics.py`:

```python
from dataclasses import dataclass
from pathlib import Path

TOPIC_DIR = Path(__file__).resolve().parents[2] / "data" / "topics"


@dataclass(frozen=True)
class Topic:
    id: str
    opening: str
    goals: tuple[str, ...]


def _parse(path: Path) -> Topic:
    raw = path.read_text(encoding="utf-8")
    _, front, body = raw.split("---\n", 2)
    topic_id = front.strip().split(":", 1)[1].strip()
    opening = ""
    goals = []
    for line in body.strip().splitlines():
        if line.startswith("opening:"):
            opening = line.split(":", 1)[1].strip()
        elif line.startswith("- "):
            goals.append(line[2:].strip())
    return Topic(id=topic_id, opening=opening, goals=tuple(goals))


def load_topics() -> list[Topic]:
    return sorted((_parse(p) for p in TOPIC_DIR.glob("*.md")), key=lambda t: t.id)
```

`simulated_user.py`:

```python
from wrongpaste.clients import chat
from wrongpaste.topics import Topic

USER_MODEL = "gpt-5.6-terra-tst"

_SYSTEM = """Eres una persona normal conversando con un asistente.
Escribe UN único mensaje breve (una o dos frases), en primera persona, en español.
No eres un asistente: no ofrezcas ayuda, no resumas, no hagas listas.
Avanza hacia el siguiente objetivo pendiente de forma natural, reaccionando a
lo que te acaban de decir. No menciones nunca que tienes objetivos."""


def next_user_turn(topic: Topic, history: list[dict]) -> str:
    pending = "\n".join(f"- {g}" for g in topic.goals)
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    prompt = (
        f"Tema de la conversación: {topic.opening}\n\n"
        f"Cosas que quieres acabar sabiendo:\n{pending}\n\n"
        f"Conversación hasta ahora:\n{transcript}\n\n"
        f"Escribe tu siguiente mensaje."
    )
    reply = chat(
        USER_MODEL,
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}],
        max_tokens=400,
    )
    return reply.text.strip()
```

`USER_MODEL` se fija aquí y **no se cambia durante toda la campaña** (§4 del spec). Es `terra` y no `sol` por coste: el usuario simulado genera un turno por vuelta en las 2.688 conversaciones de la Fase 1.

- [ ] **Step 5: Ejecutar el test y comprobar que pasa**

```bash
uv run pytest tests/test_topics.py -v
```

Esperado: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add data/topics src/wrongpaste/topics.py src/wrongpaste/simulated_user.py tests/test_topics.py
git commit -m "feat: ocho temas dispares y usuario simulado con guion de objetivos"
```

---

### Task 6: Motor de conversación con inyección del pegote

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/records.py`
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/conversation.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_conversation.py`

**Interfaces:**
- Consumes: `clients.chat`, `simulated_user.next_user_turn`, `topics.Topic`, `artifacts.Artifact`.
- Produces: `ConversationRecord` (dataclass serializable a JSON), `build_prefix(model_id, topic, n_turns) -> tuple[list[dict], list[dict]]`, `inject_paste(model_id, transcript, artifact) -> tuple[str, dict]`.

**Por qué dos funciones y no una.** La similaridad se mide contra *la conversación
hasta el turno del pegote* (spec §4.1), así que el prefijo tiene que existir antes
de poder elegir el artefacto. Una única `run_conversation(artifact=...)` obligaría
a elegir el artefacto a ciegas y medir la similaridad contra el arranque del tema,
que en las conversaciones de 10 turnos es un proxy malo. El runner (Task 7) hace
prefijo → medir → muestrear → inyectar.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_conversation.py` (con dobles, sin red):

```python
import wrongpaste.conversation as conv
from wrongpaste.artifacts import Artifact
from wrongpaste.clients import Reply
from wrongpaste.topics import Topic

TOPIC = Topic("t", "quiero mudarme", ("a", "b", "c", "d"))
ART = Artifact("art1", "recipe", "300 g de lentejas", ("lentejas",))


def _stub(monkeypatch, replies=None):
    seq = iter(replies or [Reply(f"r{i}", {}, {}) for i in range(20)])
    monkeypatch.setattr(conv, "chat", lambda *a, **k: next(seq))
    monkeypatch.setattr(conv, "next_user_turn", lambda *a, **k: "turno de usuario")


def test_prefix_alternates_roles_and_ends_on_assistant(monkeypatch):
    _stub(monkeypatch)
    transcript, usages = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=3)

    assert transcript[0]["role"] == "user"
    assert transcript[-1]["role"] == "assistant"
    assert [m["role"] for m in transcript] == ["user", "assistant"] * 3
    assert len(usages) == 3


def test_prefix_never_ends_on_user_so_claude_accepts_it(monkeypatch):
    _stub(monkeypatch)
    transcript, _ = conv.build_prefix("claude-opus-5", TOPIC, n_turns=2)
    assert transcript[-1]["role"] == "assistant"


def test_inject_paste_appends_artifact_verbatim(monkeypatch):
    _stub(monkeypatch)
    transcript, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=2)
    before = len(transcript)

    reaction, usage = conv.inject_paste("gpt-5.6-luna-tst", transcript, ART)

    assert transcript[before]["role"] == "user"
    assert transcript[before]["content"] == ART.text
    assert transcript[-1]["role"] == "assistant"
    assert reaction == transcript[-1]["content"]


def test_inject_paste_adds_no_preamble(monkeypatch):
    _stub(monkeypatch)
    transcript, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=2)
    conv.inject_paste("gpt-5.6-luna-tst", transcript, ART)

    pasted = [m for m in transcript if m["content"] == ART.text]
    assert len(pasted) == 1, "el pegote debe ir tal cual, sin envoltorio"
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

```bash
uv run pytest tests/test_conversation.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.conversation'`.

- [ ] **Step 3: Implementar `records.py` y `conversation.py`**

`records.py`:

```python
from dataclasses import asdict, dataclass, field


@dataclass
class ConversationRecord:
    model_id: str
    topic_id: str
    artifact_id: str
    artifact_kind: str
    artifact_entities: list[str]
    similarity: float
    n_turns: int
    seed: int
    user_model: str
    max_tokens: int
    transcript: list[dict]
    reaction: str
    usages: list[dict] = field(default_factory=list)

    def to_json(self) -> dict:
        return asdict(self)
```

`artifact_entities` se copia dentro del registro aunque esté también en el banco:
el análisis de fuga de la Fase 2 se hace sobre estos ficheros y no debe depender de
que el banco no haya cambiado entre tanto. `user_model` y `max_tokens` se guardan
para cumplir el requisito de §4.2 del spec de registrar lo que se envió.

`conversation.py`:

```python
from wrongpaste.artifacts import Artifact
from wrongpaste.clients import chat
from wrongpaste.simulated_user import next_user_turn
from wrongpaste.topics import Topic

MAX_TOKENS = 1024


def build_prefix(
    model_id: str, topic: Topic, n_turns: int
) -> tuple[list[dict], list[dict]]:
    """Conduce n_turns de conversación normal sobre el tema.

    Devuelve la transcripción (siempre terminada en assistant, que es lo que
    Claude exige para poder continuar) y los `usage` de cada llamada.
    """
    transcript: list[dict] = [{"role": "user", "content": topic.opening}]
    usages: list[dict] = []

    reply = chat(model_id, transcript, max_tokens=MAX_TOKENS)
    transcript.append({"role": "assistant", "content": reply.text})
    usages.append(reply.usage)

    for _ in range(n_turns - 1):
        transcript.append({"role": "user", "content": next_user_turn(topic, transcript)})
        reply = chat(model_id, transcript, max_tokens=MAX_TOKENS)
        transcript.append({"role": "assistant", "content": reply.text})
        usages.append(reply.usage)

    return transcript, usages


def conversation_text(transcript: list[dict]) -> str:
    """El texto contra el que se mide la similaridad del banco."""
    return "\n".join(m["content"] for m in transcript)


def inject_paste(
    model_id: str, transcript: list[dict], artifact: Artifact
) -> tuple[str, dict]:
    """Añade el pegote TAL CUAL, sin preámbulo ni envoltorio, y pide respuesta.

    Muta `transcript` in place: el registro guarda la conversación completa.
    """
    transcript.append({"role": "user", "content": artifact.text})
    reply = chat(model_id, transcript, max_tokens=MAX_TOKENS)
    transcript.append({"role": "assistant", "content": reply.text})
    return reply.text, reply.usage
```

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

```bash
uv run pytest tests/test_conversation.py -v
```

Esperado: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/records.py src/wrongpaste/conversation.py tests/test_conversation.py
git commit -m "feat: motor de conversación con inyección literal del pegote"
```

---

### Task 7: Runner de la Fase 0

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/run_phase0.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_run_phase0.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: `plan_phase0(seed: int) -> list[dict]`, `main()` que escribe `runs/phase0/<timestamp>.jsonl`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_run_phase0.py`:

```python
from wrongpaste.run_phase0 import PHASE0_MODELS, plan_phase0


def test_plan_uses_the_three_phase0_models():
    plan = plan_phase0(seed=1)
    assert {c["model_id"] for c in plan} == set(PHASE0_MODELS)


def test_plan_is_about_thirty_conversations():
    plan = plan_phase0(seed=1)
    assert 24 <= len(plan) <= 36


def test_plan_covers_both_lengths():
    plan = plan_phase0(seed=1)
    assert {c["n_turns"] for c in plan} == {2, 10}


def test_plan_is_deterministic_for_a_seed():
    a = [(c["model_id"], c["topic_id"], c["n_turns"]) for c in plan_phase0(seed=3)]
    b = [(c["model_id"], c["topic_id"], c["n_turns"]) for c in plan_phase0(seed=3)]
    assert a == b
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

```bash
uv run pytest tests/test_run_phase0.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.run_phase0'`.

- [ ] **Step 3: Implementar `run_phase0.py`**

```python
import json
import time
from pathlib import Path

import numpy as np

from wrongpaste.artifacts import load_artifacts
from wrongpaste.conversation import (
    MAX_TOKENS,
    build_prefix,
    conversation_text,
    inject_paste,
)
from wrongpaste.records import ConversationRecord
from wrongpaste.similarity import rank_artifacts
from wrongpaste.simulated_user import USER_MODEL
from wrongpaste.topics import load_topics

PHASE0_MODELS = ["gpt-5.6-sol-tst", "gpt-5.6-luna-tst", "claude-opus-5"]
LENGTHS = [2, 10]
STRATA = 8
OUT_DIR = Path(__file__).resolve().parents[2] / "runs" / "phase0"


def plan_phase0(seed: int) -> list[dict]:
    """Cada modelo recorre los 8 temas; la longitud alterna por tema.

    No es un factorial completo a propósito: la Fase 0 es para leer, no para
    contar, y 30 transcripciones es lo que se puede leer de una sentada.
    """
    topics = load_topics()
    rng = np.random.default_rng(seed)
    plan = []
    for model_id in PHASE0_MODELS:
        for i, topic in enumerate(topics):
            plan.append(
                {
                    "model_id": model_id,
                    "topic_id": topic.id,
                    "n_turns": LENGTHS[i % 2],
                    "seed": int(rng.integers(0, 2**31)),
                }
            )
    return plan


def main(seed: int = 20260913) -> Path:
    topics = {t.id: t for t in load_topics()}
    arts = load_artifacts()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{time.strftime('%Y%m%dT%H%M%S')}.jsonl"

    with out.open("w", encoding="utf-8") as fh:
        for i, cell in enumerate(plan_phase0(seed)):
            topic = topics[cell["topic_id"]]
            rng = np.random.default_rng(cell["seed"])

            # 1. Prefijo primero: la similaridad se mide contra la conversación
            #    hasta el turno del pegote (spec §4.1), no contra el tema.
            transcript, usages = build_prefix(
                cell["model_id"], topic, cell["n_turns"]
            )

            # 2. Medir el banco entero contra ese prefijo y muestrear.
            #    En Fase 0 se recorre el estrato i para que las 24 celdas
            #    cubran el rango de similaridad entre todas.
            ranked = rank_artifacts(conversation_text(transcript), arts)
            stratum = i % STRATA
            lo = len(ranked) * stratum // STRATA
            hi = len(ranked) * (stratum + 1) // STRATA
            artifact, sim = ranked[int(rng.integers(lo, max(hi, lo + 1)))]

            # 3. Inyectar y registrar.
            reaction, paste_usage = inject_paste(
                cell["model_id"], transcript, artifact
            )
            usages.append(paste_usage)

            rec = ConversationRecord(
                model_id=cell["model_id"],
                topic_id=topic.id,
                artifact_id=artifact.id,
                artifact_kind=artifact.kind,
                artifact_entities=list(artifact.entities),
                similarity=sim,
                n_turns=cell["n_turns"],
                seed=cell["seed"],
                user_model=USER_MODEL,
                max_tokens=MAX_TOKENS,
                transcript=transcript,
                reaction=reaction,
                usages=usages,
            )
            fh.write(json.dumps(rec.to_json(), ensure_ascii=False) + "\n")
            fh.flush()
            print(f"{rec.model_id} / {rec.topic_id} / sim={sim:.3f}")

    return out


if __name__ == "__main__":
    print(main())
```

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

```bash
uv run pytest tests/test_run_phase0.py -v
```

Esperado: 4 passed.

- [ ] **Step 5: Ejecutar la suite entera sin red**

```bash
uv run pytest -v -m "not live"
```

Esperado: todo passed.

- [ ] **Step 6: Commit**

```bash
git add src/wrongpaste/run_phase0.py tests/test_run_phase0.py
git commit -m "feat: runner de la Fase 0 con plan determinista y registro JSONL"
```

---

### Task 8: Correr la Fase 0 y derivar la rúbrica

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/<timestamp>.jsonl` (el timestamp lo pone el runner)
- Create: `~/Documents/repos/llm-wrong-paste/docs/rubrica-v1.md`
- Create: `~/Documents/repos/personal-website/docs/superpowers/specs/<fecha-de-la-tirada>-pegado-accidental-fase-0-resultados.md`

**Interfaces:**
- Consumes: `run_phase0.main`.
- Produces: la rúbrica que la Fase 1 necesita como entrada. **Sin esto, la Fase 1 no se puede planificar.**

- [ ] **Step 1: Estimar antes de gastar**

Contar celdas (24), multiplicar por turnos y por el precio del modelo, y **decir en voz alta el tiempo y el coste partidos por proveedor** antes de lanzar. Referencia del spec: ≈4 $ y unas 2 h. Si la estimación se dispara por encima de 10 $, parar y revisar.

- [ ] **Step 2: Lanzar la Fase 0**

Requiere VPN activa y `gcloud auth login` vigente.

```bash
cd ~/Documents/repos/llm-wrong-paste
uv run python -m wrongpaste.run_phase0
```

- [ ] **Step 3: Comprobar que el caché de prefijo funciona**

```bash
uv run python -c "
import json, pathlib
p = sorted(pathlib.Path('runs/phase0').glob('*.jsonl'))[-1]
reads = [u.get('cache_read_input_tokens') or u.get('prompt_tokens_details', {}).get('cached_tokens', 0)
         for line in p.read_text().splitlines() for u in json.loads(line)['usages']]
print('llamadas:', len(reads), '| con lectura de caché:', sum(1 for r in reads if r))
"
```

Si sale cero de forma sistemática hay un invalidador silencioso y hay que encontrarlo **antes** de la Fase 1, donde el caché es la diferencia entre 20 $ y bastante más.

- [ ] **Step 4: Leer las 24 transcripciones a mano**

Enteras, no en diagonal. Para cada una, anotar en un fichero de trabajo: qué hizo el modelo con el pegote, con qué palabras, y si encaja en alguna de las cinco categorías previas del spec §5.

Preguntas que la lectura debe contestar:
- ¿Aparecen conductas que no están en las cinco categorías?
- ¿Alguna categoría no aparece nunca, o hay que partirla en dos?
- ¿El usuario simulado suena a persona? (riesgo declarado en §12 del spec)
- ¿Hay ya señal visible de que la similaridad importe?

- [ ] **Step 5: Escribir la rúbrica v1**

`docs/rubrica-v1.md`: las categorías finales, cada una con definición, **dos ejemplos literales de las transcripciones** y el criterio de desempate frente a la categoría vecina. Esto es lo que se le pasa al juez-LLM en la Fase 1.

- [ ] **Step 6: Escribir el documento de resultados de Fase 0**

En el repo del blog, siguiendo el formato de `2026-08-14-fase-0-resultados.md`: qué se corrió, qué se leyó, qué categorías sobrevivieron, coste real frente a estimado, y **decisión GO/NO-GO explícita** sobre seguir a la Fase 1.

- [ ] **Step 7: Commit en los dos repos**

```bash
cd ~/Documents/repos/llm-wrong-paste
git add runs/phase0 docs/rubrica-v1.md
git commit -m "data: Fase 0 — 24 conversaciones y rúbrica v1 derivada de leerlas"

cd ~/Documents/repos/personal-website
git add docs/superpowers/specs/*fase-0-resultados.md
git commit -m "docs: resultados de la Fase 0 y decisión GO/NO-GO"
```

---

## Lo que este plan NO cubre, y por qué

- **Fase 1 y Fase 2 no tienen tareas aquí.** Su diseño depende de la rúbrica que produce la Task 8. Escribirlas ahora sería inventarse nombres de categorías que van a cambiar. Se planifican en un documento aparte cuando exista `rubrica-v1.md`.
- **Fase 3 no existe todavía**, por decisión del spec §8.

## Prerrequisito pendiente para la Fase 1

El spec §4.2 exige que el juez **no** esté entre los modelos evaluados, y ahora mismo la key `blog-paste-experiment` da acceso exactamente al conjunto evaluado. Hay que resolverlo antes de la Fase 1, no durante:

- **Opción recomendada**: añadir `gpt-5.5-tst` a la key. Ya está registrado en el gateway y no forma parte del plantel, así que sirve de juez sin tocar el diseño.
- Alternativa: usar `claude-sonnet-5` como juez y sacarlo del conjunto evaluado, a costa de perder el segundo Claude.
