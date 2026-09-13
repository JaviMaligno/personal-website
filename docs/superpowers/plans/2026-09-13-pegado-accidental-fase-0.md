# Pegado accidental — Fase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el arnés que genera conversaciones con un pegote accidental inyectado, y correr la Fase 0 (27 conversaciones: 24 con pegote y 3 de control sin pegote, sobre 3 modelos) cuyo producto es una rúbrica de clasificación derivada de leer las transcripciones a mano.

**Architecture:** Un paquete Python con tres clientes de inferencia detrás de una interfaz única (gateway LiteLLM, Vertex-Anthropic, Vertex-OpenAI-compat), un banco de artefactos independiente de los temas, un almacén de prefijos compartidos, y un orquestador que para cada celda: recupera el prefijo compartido de ese (tema, longitud), mide la similaridad coseno de los 64 artefactos del banco contra el lado del usuario de ese prefijo, muestrea uno dentro del estrato que le asigna el plan, lo inyecta como turno de usuario, sigue dos turnos más sin reparación y registra todo en JSONL crudo.

**Tech Stack:** Python 3.12, `uv`, `pytest`, `httpx`, `numpy`. Sin SDKs de proveedor: los tres endpoints son HTTP y sus formas son distintas entre sí, así que un cliente propio y fino es más honesto que tres SDKs.

**Spec:** [`docs/superpowers/specs/2026-09-13-pegado-accidental-design.md`](../specs/2026-09-13-pegado-accidental-design.md)

**Decisiones de diseño (mandan sobre este plan):** [`docs/superpowers/specs/2026-09-13-pegado-accidental-correcciones.md`](../specs/2026-09-13-pegado-accidental-correcciones.md) — D1..D17, salidas de la auditoría adversarial. Donde este plan y ese documento se contradigan, gana el documento.

## Global Constraints

- **Repo de código**: nuevo y público, en `~/Documents/repos/llm-wrong-paste`. Este plan vive en el repo del blog; el código NO.
- **Todo sintético.** Ningún tema, artefacto o transcripción sale de trabajo real ni de repos de la empresa.
- **Sin secretos en el repo.** La key del gateway se lee de `~/.acp-blog-paste-key`; las credenciales de GCP, de ADC. Nada de claves en ficheros versionados.
- **Registro en crudo, siempre.** Cada conversación se guarda íntegra en JSONL con: transcripción completa con etiquetas, artefacto usado, las dos similaridades, ranking completo, modelo, longitud, semilla, parámetros enviados y `usage` devuelto. El análisis se hace después sobre esos ficheros.
- **Prefijo compartido y autoría fija (D1).** El prefijo se genera **una vez por (tema, longitud)** con el usuario simulado y un modelo de asistente fijo (`PREFIX_MODEL = gpt-5.6-terra-tst`, el mismo que hace de usuario), se persiste en `runs/prefixes/<prefix_id>.json` y se le sirve **idéntico** a los tres modelos evaluados. Si cada modelo se fabricara su prefijo, el eje x dependería de quién contesta —Opus diluye el embedding con mil tokens de prosa y `luna` no— y las curvas dejarían de ser comparables entre modelos, que es justo lo que el spec §9 quiere comparar. El coste de esta decisión se declara en la sección *Limitaciones declaradas*.
- **La similaridad se mide sobre el lado del usuario (D2).** La primaria, `similarity_user`, se calcula contra la concatenación de apertura + turnos del usuario simulado: es corta, es independiente del modelo evaluado y es la definición correcta de "de qué va esta conversación". Se registra además `similarity_full` sobre la conversación entera, como secundaria, para poder ver si divergen. Guarda obligatoria antes de embeber: por encima de `MAX_EMBED_CHARS = 24_000` (≈6.000 tokens estimados, holgado frente a los 8.191 del embedder) se recorta **por el principio** conservando el final y se marca `similarity_text_truncated`.
- **Muestreo explícito (D9).** `temperature = 1.0` va escrita en los tres cuerpos; no se hereda el default de cada proveedor, que ni coincide entre ellos ni está congelado. Los modelos Claude llevan `thinking: {"type": "adaptive"}` siempre, porque si no Sonnet 5 correría sin razonamiento mientras Opus 5 lo lleva por defecto y los dos Claude dejarían de ser comparables. **`budget_tokens` está prohibido: devuelve 400 en Opus 5 y en Sonnet 5.** El cuerpo enviado, sin `messages`, se guarda en cada fila como `request_params`.
- **Los fallos son datos, no una caída (D6).** `chat()` reintenta 429 y 5xx tres veces con backoff exponencial; `main()` envuelve cada celda en `try/except` y **siempre** escribe fila, con `status ∈ ok | http_error | timeout | refusal | empty` más `error_code`, `error_body` y `attempts`; la tirada se reanuda sobre un fichero a medias saltando los `conversation_id` que ya están. Un JSONL de 19 filas sin marcas es indistinguible de uno completo, y el sesgo de las que faltan es predecible: fallan más las conversaciones largas y los pegotes de coseno alto, justo la zona interesante. **Que un modelo se niegue a responder al pegote es un resultado**, no un error.
- **Claude va por `global`**: `https://aiplatform.googleapis.com/v1/projects/{p}/locations/global/publishers/anthropic/models/{m}:rawPredict`. En `us-central1` la cuota está a cero y devuelve 429.
- **Gemini va por OpenAI-compat de `us-central1`**: `https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{p}/locations/us-central1/endpoints/openapi/chat/completions`, modelo `google/{m}`.
- **Proyecto GCP**: `data-science-364702`. Cabecera `x-goog-user-project` obligatoria.
- **Prefill de turno de asistente está eliminado** en la familia Claude 5. El arnés no puede apoyarse en él.
- **Repo público (D17).** `runs/` se versiona. Cada fila lleva el alias interno (`model_id`) y la etiqueta pública (`model_label`), y `config.py` versiona el endpoint del gateway y el proyecto GCP. No es secreto, pero es material de trabajo interno: antes de la primera tirada hay que decidir si endpoint y proyecto pasan a variables de entorno (Task 8, Step 1).
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
- Produces: `Model(id: str, provider: str, label: str, tier: str)`, `MODELS: dict[str, Model]`, `GCP_PROJECT: str`, `GATEWAY_URL: str`, `EMBEDDING_MODEL: str`, `gateway_key() -> str`.

- [ ] **Step 1: Crear el repo y el esqueleto**

```bash
mkdir -p ~/Documents/repos/llm-wrong-paste/{src/wrongpaste,tests,data/artifacts,data/topics,docs,runs}
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

[tool.pytest.ini_options]
markers = ["live: hace llamadas reales a los modelos (cuesta dinero)"]
```

`.gitignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

Nota: `runs/` **no** va en `.gitignore`. Los datos crudos se versionan; son el producto (D17).

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

El plantel son **nueve** modelos verificados. El §6 del spec presupuesta sobre siete y el prerrequisito del juez propone sacar a `claude-sonnet-5`: esa incoherencia es D16 y **se resuelve al planificar la Fase 1**, no aquí (ver *Prerrequisitos pendientes para la Fase 1*).

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

`Model.label` no es decorativo: viaja a cada fila del JSONL como `model_label` junto al alias interno `model_id` (D17).

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
- Produces: `Reply(text, usage, raw, stop_reason, response_model, attempts, latency_ms)`, `chat(model_id, messages, max_tokens=1024, request_params_out=None) -> Reply`, `embed(texts) -> numpy.ndarray`, y las constantes `TEMPERATURE`, `MAX_ATTEMPTS`, `BACKOFF_BASE_SECONDS`.

`messages` usa siempre la forma OpenAI (`{"role": "user"|"assistant", "content": str}`); la traducción al formato de Anthropic ocurre dentro del cliente. Así el resto del arnés no sabe de proveedores.

Este fichero carga con cuatro decisiones a la vez: **D9** (temperature explícita, thinking adaptive, nada de `budget_tokens`), **D10** (`cache_control` al final del prefijo), **D6** (reintentos, `stop_reason`, `attempts`) y **D5** (`response_model`, `request_params`).

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_clients.py` (sin red — comprueba la traducción de formatos y las cuatro decisiones). Forma de los cuerpos:

```python
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

Muestreo y razonamiento (D9):

```python
def test_los_tres_cuerpos_mandan_temperature_explicita():
    # D9: nada de heredar el default de cada proveedor, que ni coincide entre
    # ellos ni está congelado.
    msgs = [{"role": "user", "content": "x"}]
    assert _gateway_body("gpt-5.6-sol-tst", msgs, 32)["temperature"] == TEMPERATURE
    assert _vertex_openai_body("gemini-2.5-pro", msgs, 32)["temperature"] == TEMPERATURE
    assert _anthropic_body(msgs, max_tokens=32)["temperature"] == TEMPERATURE
    assert TEMPERATURE == 1.0


def test_anthropic_body_manda_thinking_adaptive_siempre():
    # Sin esto, Sonnet 5 correría sin razonamiento mientras Opus 5 lo lleva por
    # defecto, y los dos Claude dejarían de ser comparables.
    body = _anthropic_body([{"role": "user", "content": "x"}], max_tokens=32)
    assert body["thinking"] == {"type": "adaptive"}


def test_anthropic_body_nunca_manda_budget_tokens():
    # `budget_tokens` devuelve 400 en Opus 5 y Sonnet 5: tumbaría la tirada.
    msgs = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "x"},
        {"role": "assistant", "content": "y"},
        {"role": "user", "content": "pegote"},
    ]
    body = _anthropic_body(msgs, max_tokens=32)
    assert "budget_tokens" not in body
    assert "budget_tokens" not in body["thinking"]
```

Caché (D10) — el breakpoint va al final del **prefijo**, no en el pegote, que es lo único que mide el ahorro que la Fase 1 necesita:

```python
def _cache_control_of(message: dict):
    content = message["content"]
    if isinstance(content, str):
        return None
    return content[-1].get("cache_control")


def test_cache_control_marca_el_final_del_prefijo_no_el_pegote():
    msgs = [
        {"role": "user", "content": "apertura"},
        {"role": "assistant", "content": "respuesta"},
        {"role": "user", "content": "PEGOTE"},
    ]
    body = _anthropic_body(msgs, max_tokens=32)
    enviados = body["messages"]
    assert _cache_control_of(enviados[-2]) == {"type": "ephemeral"}
    assert _cache_control_of(enviados[-1]) is None
    assert enviados[-1]["content"] == "PEGOTE"


def test_cache_control_no_muta_la_transcripcion_del_llamante():
    # La transcripción se guarda tal cual en el JSONL: el cuerpo de la llamada
    # no puede ensuciarla con bloques ni con cache_control.
    msgs = [
        {"role": "user", "content": "apertura"},
        {"role": "assistant", "content": "respuesta"},
        {"role": "user", "content": "PEGOTE"},
    ]
    _anthropic_body(msgs, max_tokens=32)
    assert msgs[1]["content"] == "respuesta"


def test_sin_prefijo_no_hay_cache_control():
    # Un único mensaje no tiene delante nada estable que cachear.
    body = _anthropic_body([{"role": "user", "content": "x"}], max_tokens=32)
    assert body["messages"] == [{"role": "user", "content": "x"}]
```

Reintentos y trazas (D6), contra un `httpx.post` doblado por `monkeypatch`:

```python
def test_backoff_es_exponencial_de_un_segundo():
    assert [_backoff_seconds(i) for i in (1, 2, 3)] == [1.0, 2.0, 4.0]
```

Más: `test_chat_devuelve_stop_reason_modelo_y_trazas_en_gateway`,
`test_chat_devuelve_stop_reason_de_anthropic`,
`test_chat_reintenta_el_429_y_cuenta_los_intentos`,
`test_chat_reintenta_los_5xx_y_se_rinde_al_tercero`,
`test_chat_no_reintenta_un_400`,
`test_chat_rellena_request_params_out_sin_los_mensajes`,
`test_chat_rellena_request_params_out_aunque_la_llamada_falle` y
`test_chat_devuelve_texto_vacio_sin_reventar`.

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

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

```bash
uv run pytest tests/test_clients.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.clients'`.

- [ ] **Step 3: Implementar `clients.py`**

Constantes y `Reply`:

```python
import subprocess
import time
from dataclasses import dataclass

import httpx
import numpy as np

from wrongpaste import config

_TIMEOUT = httpx.Timeout(300.0)

# D9: muestreo explícito. No se delega en el default de cada proveedor, que
# puede cambiar sin avisar y que no es el mismo en los tres.
TEMPERATURE = 1.0

# D6: los fallos son datos, no caída. Tres intentos con backoff exponencial
# (1 s / 2 s / 4 s) para 429 y 5xx; el resto de 4xx son errores nuestros y no
# mejoran esperando, así que se propagan al primer intento.
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0
_RETRIABLE_STATUS = {429}


@dataclass
class Reply:
    text: str
    usage: dict
    raw: dict
    stop_reason: str | None = None
    response_model: str | None = None
    attempts: int = 1
    latency_ms: float | None = None
```

Los tres cuerpos, con `temperature` en todos (D9) y el breakpoint de caché en el de Anthropic (D10):

```python
def _gateway_body(model_id: str, messages: list[dict], max_tokens: int) -> dict:
    return {
        "model": model_id,
        "messages": messages,
        "max_completion_tokens": max_tokens,
        "temperature": TEMPERATURE,
    }


def _vertex_openai_body(model_id: str, messages: list[dict], max_tokens: int) -> dict:
    return {
        "model": f"google/{model_id}",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": TEMPERATURE,
    }


def _as_blocks(content) -> list[dict]:
    """Normaliza el contenido de un mensaje a lista de bloques.

    Claude acepta `content` como cadena o como lista de bloques, pero
    `cache_control` solo se puede colgar de un bloque.
    """
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [dict(block) for block in content]


def _mark_cacheable_prefix(convo: list[dict]) -> list[dict]:
    """Pone el breakpoint de caché al final del prefijo (D10).

    El pegote es siempre el último mensaje de la lista, así que el breakpoint
    va en el último bloque del **penúltimo** mensaje: de ese modo el prefijo
    entero —idéntico entre las celdas que comparten `prefix_id`— se sirve de
    caché en la llamada del pegote, que es justo el ahorro que la Fase 1
    necesita medir.

    Devuelve una lista nueva: no muta la transcripción del llamante.
    """
    marked = [dict(m) for m in convo]
    if len(marked) < 2:
        # Un solo mensaje: no hay prefijo estable que cachear delante de él.
        return marked
    target = marked[-2]
    blocks = _as_blocks(target["content"])
    blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}
    target["content"] = blocks
    return marked


def _anthropic_body(messages: list[dict], max_tokens: int) -> dict:
    if messages and messages[-1]["role"] == "assistant":
        raise ValueError(
            "prefill de turno de asistente eliminado en la familia Claude 5"
        )
    system = " ".join(m["content"] for m in messages if m["role"] == "system")
    convo = [m for m in messages if m["role"] != "system"]
    body = {
        "anthropic_version": "vertex-2023-10-16",
        "messages": _mark_cacheable_prefix(convo),
        "max_tokens": max_tokens,
        # OJO (D9): `budget_tokens` devuelve 400 en Opus 5 y Sonnet 5. El modo
        # adaptativo es la única forma de razonamiento en la familia 5, y hay
        # que mandarlo siempre para que Sonnet 5 y Opus 5 sean comparables.
        "thinking": {"type": "adaptive"},
        # OJO: D9 exige `temperature` explícita en los tres cuerpos. Verificar
        # contra el proveedor antes de la tirada: si la familia Claude 5
        # rechaza el muestreo explícito con 400, esta línea la tumba entera.
        "temperature": TEMPERATURE,
    }
    if system:
        body["system"] = system
    return body
```

Los reintentos (D6):

```python
def _backoff_seconds(attempt: int) -> float:
    """Espera antes del intento `attempt + 1`: 1 s, 2 s, 4 s."""
    return BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))


def _is_retriable(status_code: int) -> bool:
    return status_code in _RETRIABLE_STATUS or status_code >= 500


def _post_with_retries(url: str, headers: dict, body: dict) -> tuple[httpx.Response, int, float]:
    """POST con reintentos de 429 y 5xx (D6).

    Devuelve la respuesta, el número de intentos consumidos y la latencia
    total en milisegundos (sueltas de backoff incluidas). Si se agotan los
    intentos, propaga el `HTTPStatusError` con el recuento de intentos
    colgado en el atributo `attempts`, para que el runner pueda registrarlo.
    """
    started = time.perf_counter()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        resp = httpx.post(url, headers=headers, json=body, timeout=_TIMEOUT)
        if resp.status_code < 400:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return resp, attempt, latency_ms
        if attempt < MAX_ATTEMPTS and _is_retriable(resp.status_code):
            time.sleep(_backoff_seconds(attempt))
            continue
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            exc.attempts = attempt
            raise
    raise AssertionError("inalcanzable")  # pragma: no cover
```

Y la puerta única, que elige proveedor, rellena `request_params_out` **antes** de llamar (para que también exista si la llamada revienta) y devuelve `stop_reason` y `response_model`:

```python
def chat(
    model_id: str,
    messages: list[dict],
    max_tokens: int = 1024,
    request_params_out: dict | None = None,
) -> Reply:
    """Una llamada al modelo, con reintentos y trazabilidad."""
    model = config.MODELS[model_id]

    if model.provider == "gateway":
        url = f"{config.GATEWAY_URL}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {config.gateway_key()}"}
        body = _gateway_body(model_id, messages, max_tokens)
    elif model.provider == "vertex_openai":
        url = config.VERTEX_OPENAI_URL.format(project=config.GCP_PROJECT)
        headers = {"Authorization": f"Bearer {_gcp_token()}"}
        body = _vertex_openai_body(model_id, messages, max_tokens)
    elif model.provider == "vertex_anthropic":
        url = config.VERTEX_ANTHROPIC_URL.format(
            project=config.GCP_PROJECT, model=model_id
        )
        headers = {
            "Authorization": f"Bearer {_gcp_token()}",
            "x-goog-user-project": config.GCP_PROJECT,
        }
        body = _anthropic_body(messages, max_tokens)
    else:
        raise ValueError(f"proveedor desconocido: {model.provider}")

    if request_params_out is not None:
        request_params_out.clear()
        request_params_out.update({k: v for k, v in body.items() if k != "messages"})

    resp, attempts, latency_ms = _post_with_retries(url, headers, body)
    data = resp.json()

    if model.provider in ("gateway", "vertex_openai"):
        return _openai_reply(data, attempts, latency_ms)

    text = "".join(b["text"] for b in data.get("content", []) if b["type"] == "text")
    return Reply(
        text=text,
        usage=data.get("usage", {}),
        raw=data,
        stop_reason=data.get("stop_reason"),
        response_model=data.get("model"),
        attempts=attempts,
        latency_ms=latency_ms,
    )
```

Completan el fichero `_gcp_token()` (`gcloud auth print-access-token`), `_openai_reply()` (que saca `finish_reason` y `model` de la respuesta OpenAI-compat, tolerando `content: null`) y `embed()`, que sigue siendo una llamada simple al gateway sin reintentos: si el embedder falla, la celda entera falla y D6 la registra.

- [ ] **Step 4: Ejecutar los tests sin red y comprobar que pasan**

```bash
uv run pytest tests/test_clients.py -v
```

Esperado: 21 passed.

- [ ] **Step 5: Ejecutar el smoke test con red**

Requiere VPN activa (el gateway resuelve a IP privada) y `gcloud auth login` vigente.

```bash
uv run pytest tests/test_smoke_live.py -v -m live
```

Esperado: 4 passed. Coste: céntimos. **Este es el momento de verificar que la familia Claude 5 acepta `temperature` explícita junto a `thinking: adaptive`**: si devolviera 400, hay que decidirlo aquí y no a mitad de una tirada de dos horas.

- [ ] **Step 6: Commit**

```bash
git add src/wrongpaste/clients.py tests/test_clients.py tests/test_smoke_live.py pyproject.toml
git commit -m "feat: clientes de los tres proveedores tras una interfaz única"
```

---

### Task 3: Banco de artefactos y casado de entidades

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/data/artifacts/*.md` (64 ficheros)
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/artifacts.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_artifacts.py`

**Interfaces:**
- Consumes: nada.
- Produces: `Artifact(id: str, kind: str, text: str, entities: tuple[str, ...])`, `load_artifacts() -> list[Artifact]`, `normalise(text) -> str`, `entity_hits(text, entities) -> list[str]`.

El campo `entities` es la lista de términos distintivos del artefacto (nombres propios, identificadores, números raros). Se escribe **a mano** en el frontmatter de cada fichero, porque de ahí sale la métrica de fuga de la Fase 2 y una extracción automática sería ruido.

`entity_hits` es D8: toda la métrica automática de fuga se apoya en esas entidades y no había ni función ni especificación de casado. Sin ella, "el modelo mencionó el chorizo tres turnos después" es una impresión, no un dato.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_artifacts.py`, banco:

```python
from wrongpaste.artifacts import entity_hits, load_artifacts

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

Casado de entidades (D8):

```python
def test_entity_hits_ignora_acentos_y_mayusculas():
    texto = "Compré pimenton de la vera en el mercado."
    assert entity_hits(texto, ["Pimentón de la Vera"]) == ["Pimentón de la Vera"]
    # y en el sentido contrario: el acento está en el texto y no en la entity
    assert entity_hits("Lleva Pimentón de la Vera.", ["pimenton de la vera"]) == [
        "pimenton de la vera"
    ]


def test_entity_hits_no_casa_dentro_de_otra_palabra():
    assert entity_hits("Miro la pantalla del horno.", ["pan"]) == []
    assert entity_hits("Se llama Trufalandia, no es el perro.", ["Trufa"]) == []
    # la misma entity sí casa cuando es una palabra suelta
    assert entity_hits("Horneé un pan de centeno.", ["pan"]) == ["pan"]


def test_entity_hits_casa_entidades_multipalabra():
    texto = "Formar, cesto enharinado y 12 horas de fermentación en frío."
    assert entity_hits(texto, ["12 horas de fermentación en frío"]) == [
        "12 horas de fermentación en frío"
    ]
    # la puntuación intermedia actúa como separador, no como obstáculo
    assert entity_hits("Factura F-2026/118, pendiente.", ["F-2026/118"]) == [
        "F-2026/118"
    ]


def test_entity_hits_no_duplica():
    texto = "Masa madre, y otra vez masa madre para la segunda hornada."
    entities = ["masa madre", "masa madre", "Masa Madre"]
    assert entity_hits(texto, entities) == ["masa madre"]


def test_todas_las_entities_aparecen_en_su_propio_artefacto():
    """Cada entity del banco debe estar literalmente en el cuerpo del artefacto.

    Si falla, la métrica de fuga de la Fase 2 estaría contando entidades que
    nunca se pegaron: hay que arreglar el fichero del banco, no el test.
    """
```

Más: `test_entity_hits_respeta_el_orden_de_entrada` y `test_entity_hits_devuelve_vacio_si_no_hay_ninguna`.

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

```bash
uv run pytest tests/test_artifacts.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.artifacts'`.

- [ ] **Step 3: Escribir el formato y los 64 artefactos**

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

Se escriben 64, repartidos en once `kind`: `changelog` (5), `config` (5), `email` (8), `job_ad` (5), `meeting_notes` (8), `note_to_self` (5), `prompt` (5), `recipe` (5), `shopping_list` (5), `sql` (5), `stacktrace` (8). **Ninguno se escribe pensando en los temas de conversación** (§4.1 del spec): son artefactos de portapapeles, no distractores.

Los cinco `prompt` son el caso delicado: ahí el pegote es literalmente una instrucción ejecutable, y **ejecutarla es una sexta conducta que no está en las cinco categorías del spec §5**. Por eso D4 obliga a que aparezcan en la tirada (Task 7) en vez de dejarlo a suerte.

- [ ] **Step 4: Implementar `artifacts.py`**

```python
import json
import unicodedata
from collections.abc import Iterable
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


def normalise(text: str) -> str:
    """Normaliza un texto para el casado de entidades (D8).

    Pasa a minúsculas, descompone en NFKD y descarta las marcas combinantes
    (así «pimentón» y «Pimenton» acaban igual), convierte en separador todo
    carácter que no sea alfanumérico —puntuación, símbolos, guiones, el signo
    de euro— y colapsa los espacios. El resultado es una secuencia de palabras
    separadas por un único espacio, lo que permite comprobar fronteras de
    palabra con una simple búsqueda de subcadena.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    chars = [
        char if char.isalnum() else " "
        for char in decomposed
        if not unicodedata.combining(char)
    ]
    return " ".join("".join(chars).split())


def entity_hits(text: str, entities: Iterable[str]) -> list[str]:
    """Devuelve las `entities` que aparecen en `text` (D8).

    Ambos lados se normalizan con `normalise`: minúsculas, sin acentos,
    puntuación tratada como separador y espacios colapsados. Una entity cuenta
    como presente si aparece como subcadena **con fronteras de palabra** en el
    texto normalizado, de modo que «pan» no casa dentro de «pantalla».

    La lista se devuelve en el orden en que se pasaron las entities, con su
    grafía original y sin duplicados (dos entities que se normalizan igual
    cuentan como una sola).
    """
    haystack = f" {normalise(text)} "
    hits: list[str] = []
    seen: set[str] = set()
    for entity in entities:
        needle = normalise(entity)
        if not needle or needle in seen:
            continue
        seen.add(needle)
        if f" {needle} " in haystack:
            hits.append(entity)
    return hits
```

- [ ] **Step 5: Ejecutar el test y comprobar que pasa**

```bash
uv run pytest tests/test_artifacts.py -v
```

Esperado: 11 passed.

- [ ] **Step 6: Commit**

```bash
git add data/artifacts src/wrongpaste/artifacts.py tests/test_artifacts.py
git commit -m "feat: banco de artefactos de portapapeles y casado de entidades"
```

---

### Task 4: Similaridad, guarda de longitud y muestreo estratificado

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/similarity.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_similarity.py`

**Interfaces:**
- Consumes: `clients.embed`, `artifacts.Artifact`.
- Produces: `cosine(a, b)`, `user_text(transcript) -> str`, `truncate_for_embedding(text, max_chars) -> tuple[str, bool]`, `rank_artifacts(text, arts, max_chars) -> tuple[list[tuple[Artifact, float]], bool]`, `rank_stats(ranking) -> dict`, `stratified_pick(ranked, k, rng)`, y las constantes `MAX_EMBED_CHARS`, `USER_TAGS`.

Este es el fichero de **D2** (qué texto se embebe) y de **D12** (cómo se mide el ancho del eje).

`rank_artifacts` ya no devuelve solo el ranking: devuelve también si hubo que recortar, porque el runner copia esa bandera a la fila (`similarity_text_truncated`). Un truncado silencioso en el brazo de 10 turnos sería exactamente el fallo que D2 vino a cerrar.

`stratified_pick` con `k=12` es lo que consumirá la **Fase 1** (12 pegotes por tema cubriendo el rango). La Fase 0 **no** lo usa: `run_phase0.main()` inlinea su propia lógica porque tiene que garantizar además la cobertura de `kind` de D4. Se construye y se prueba ahora porque es donde vive la lógica y porque probarlo aislado es trivial.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_similarity.py` no llama al endpoint de embeddings: donde hace falta embeber se monkeypatchea `wrongpaste.similarity.embed` por una función determinista. Lo que se prueba es la selección de texto, la guarda y el orden del ranking, no el embedder.

```python
def test_cosine_of_identical_vectors_is_one():
    v = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
    assert np.isclose(cosine(v, v)[0][0], 1.0)


def test_cosine_of_orthogonal_vectors_is_zero():
    a = np.array([[1.0, 0.0]], dtype=np.float32)
    b = np.array([[0.0, 1.0]], dtype=np.float32)
    assert np.isclose(cosine(a, b)[0][0], 0.0)
```

El lado del usuario (D2):

```python
def test_user_text_ignores_assistant_turns():
    transcript = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "PROSA DEL MODELO"},
        {"role": "user", "content": "y el horno?"},
        {"role": "assistant", "content": "MÁS PROSA"},
    ]
    assert user_text(transcript) == "hola\ny el horno?"


def test_user_text_selects_opening_and_user_sim_by_tag():
    transcript = [
        {"role": "user", "content": "apertura", "tag": "opening"},
        {"role": "assistant", "content": "prosa", "tag": "assistant"},
        {"role": "user", "content": "seguimiento", "tag": "user_sim"},
    ]
    assert user_text(transcript) == "apertura\nseguimiento"


def test_user_text_excludes_the_paste_and_the_repair():
    # `paste` y `repair` son role=user pero posteriores al pegote: no definen
    # de qué va la conversación, así que no entran en la similaridad.
    transcript = [
        {"role": "user", "content": "apertura", "tag": "opening"},
        {"role": "assistant", "content": "prosa", "tag": "assistant"},
        {"role": "user", "content": "STACKTRACE", "tag": "paste"},
        {"role": "assistant", "content": "reacción", "tag": "assistant"},
        {"role": "user", "content": "perdón, pegote", "tag": "repair"},
    ]
    assert user_text(transcript) == "apertura"
```

La guarda de longitud (D2):

```python
def test_truncate_for_embedding_keeps_the_end():
    text = "INICIO" + "x" * 100 + "FINAL"
    clipped, truncated = truncate_for_embedding(text, max_chars=10)
    assert truncated is True
    assert len(clipped) == 10
    assert clipped.endswith("FINAL")
    assert "INICIO" not in clipped
    assert text.endswith(clipped)


def test_truncate_for_embedding_default_is_the_documented_guard():
    text = "b" * (MAX_EMBED_CHARS + 500)
    clipped, truncated = truncate_for_embedding(text)
    assert truncated is True
    assert len(clipped) == MAX_EMBED_CHARS == 24_000


def test_truncate_for_embedding_rejects_a_non_positive_limit():
    # Sin la guarda, `text[-0:]` devolvería el texto entero sin avisar.
    with pytest.raises(ValueError):
        truncate_for_embedding("hola", max_chars=0)
```

El ancho del eje (D12):

```python
def test_rank_stats_computes_min_median_and_max():
    ...


def test_rank_stats_measures_the_width_of_the_axis(monkeypatch):
    ...


def test_rank_stats_rejects_an_empty_ranking():
    with pytest.raises(ValueError):
        rank_stats([])
```

Y los dos de `stratified_pick`, que no cambian:

```python
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

# Tope de caracteres antes de embeber (D2): ≈6.000 tokens estimados, holgado
# frente a los 8.191 del embedder incluso con texto denso en símbolos.
MAX_EMBED_CHARS = 24_000

# Etiquetas de mensaje que cuentan como "lado del usuario" a efectos de
# similaridad. `paste` y `repair` también son role=user, pero son posteriores
# al pegote: entran en la conversación, no en la definición del tema.
USER_TAGS: frozenset[str] = frozenset({"opening", "user_sim"})


def cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)
    return a_norm @ b_norm.T


def user_text(transcript: list[dict]) -> str:
    """Concatena, en orden, solo los turnos del lado del usuario (D2).

    Un mensaje cuenta si lleva `tag` en `USER_TAGS` (apertura o usuario
    simulado); los mensajes sin `tag` —transcripciones crudas, anteriores a
    D5— se seleccionan por `role == "user"`. Así el pegote y la reparación,
    que van etiquetados, quedan fuera aunque su role sea `user`.
    """
    parts = []
    for message in transcript:
        tag = message.get("tag")
        if tag is None:
            if message.get("role") == "user":
                parts.append(message["content"])
        elif tag in USER_TAGS:
            parts.append(message["content"])
    return "\n".join(parts)


def truncate_for_embedding(
    text: str, max_chars: int = MAX_EMBED_CHARS
) -> tuple[str, bool]:
    """Recorta **por el principio** conservando el final (guarda de D2).

    Devuelve `(texto, truncado)`. Se conserva el final porque es lo que fija de
    qué se está hablando ahora: recortar la cola dejaría la similaridad anclada
    a una apertura que la conversación ya ha abandonado.
    """
    if max_chars <= 0:
        raise ValueError(f"max_chars tiene que ser positivo, recibí {max_chars}")
    if len(text) <= max_chars:
        return text, False
    return text[-max_chars:], True


def rank_artifacts(
    text: str, arts: list[Artifact], max_chars: int = MAX_EMBED_CHARS
) -> tuple[list[tuple[Artifact, float]], bool]:
    """Ordena el banco por coseno ascendente contra `text`.

    Aplica la guarda de longitud antes de embeber. Devuelve el ranking (lista
    de `(Artifact, coseno)` de menor a mayor) y un booleano de si hubo que
    recortar el texto, que el runner copia a la fila del JSONL.
    """
    clipped, truncated = truncate_for_embedding(text, max_chars=max_chars)
    vecs = embed([clipped] + [a.text for a in arts])
    sims = cosine(vecs[:1], vecs[1:])[0]
    ranking = sorted(zip(arts, (float(s) for s in sims)), key=lambda p: p[1])
    return ranking, truncated


def rank_stats(ranking: list[tuple[Artifact, float]]) -> dict:
    """Mínimo, mediana y máximo del coseno observado en un ranking (D12).

    Es la medida del **ancho del eje**: si un tema tiene un rango estrecho, la
    estratificación por similaridad no separa nada y el GO/NO-GO tiene que
    verlo antes de gastar el presupuesto.
    """
    if not ranking:
        raise ValueError("el ranking está vacío: no hay estadísticos que dar")
    sims = np.array([s for _, s in ranking], dtype=float)
    return {
        "min": float(sims.min()),
        "median": float(np.median(sims)),
        "max": float(sims.max()),
    }


def stratified_pick(
    ranked: list[tuple[Artifact, float]], k: int, rng: np.random.Generator
) -> list[tuple[Artifact, float]]:
    """Un artefacto por estrato de igual anchura sobre el rango observado.

    Estratifica por posición en el ranking, no por valor de similaridad: la
    distribución real está muy concentrada y estratificar por valor dejaría
    estratos vacíos.

    La Fase 0 **no** la usa (`run_phase0.main()` inlinea su propia lógica para
    garantizar la cobertura de `kind` de D4); queda para la Fase 1.
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

Esperado: 22 passed.

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/similarity.py tests/test_similarity.py
git commit -m "feat: similaridad sobre el lado del usuario, guarda de longitud y ancho del eje"
```

---

### Task 5: Temas con hueco de tarea verificable, y usuario simulado

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/data/topics/*.md` (8 ficheros)
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/topics.py`
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/simulated_user.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_topics.py`

**Interfaces:**
- Consumes: `clients.chat`.
- Produces: `Topic(id, opening, goals, task=None, expected=None, verifier=None)`, `load_topics() -> list[Topic]`, `TOPIC_DIR`, `USER_MODEL: str`, `next_user_turn(topic, history) -> str`.

`task`, `expected` y `verifier` son el hueco que exige **D13**. La Fase 2 necesita temas con una tarea verificable aguas abajo; si el campo no existiera ya en Fase 0, la Fase 2 tendría que correr sobre temas nuevos y dejaría de estar pareada con la Fase 1 — con la rúbrica derivada de leer temas que no vuelven a aparecer. En Fase 0 los tres valen `None` a propósito: aquí no se inventa ninguna tarea.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_there_are_eight_topics():
    assert len(load_topics()) == 8


def test_every_topic_has_an_opening_and_goals():
    for topic in load_topics():
        assert topic.opening.strip()
        assert len(topic.goals) >= 4, f"{topic.id} tiene pocos objetivos"


def test_topic_ids_are_unique():
    ids = [t.id for t in load_topics()]
    assert len(ids) == len(set(ids))


def test_the_verifiable_task_fields_are_none_in_phase_0():
    """D13: el hueco existe, pero en Fase 0 no hay tarea verificable."""
    for topic in load_topics():
        assert topic.task is None, f"{topic.id} trae task en Fase 0"
        assert topic.expected is None, f"{topic.id} trae expected en Fase 0"
        assert topic.verifier is None, f"{topic.id} trae verifier en Fase 0"


def test_the_eight_topic_files_declare_the_hole():
    """El hueco tiene que verse en el fichero, aunque el valor sea None."""
    from wrongpaste.topics import TOPIC_DIR

    paths = sorted(TOPIC_DIR.glob("*.md"))
    assert len(paths) == 8
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for field in ("task:", "expected:", "verifier:"):
            assert field in text, f"{path.name} no declara el hueco {field}"
```

Y, sobre ficheros escritos en `tmp_path`, que el parser ya sepa leerlos cuando la Fase 2 los rellene: `test_a_topic_with_the_three_fields_filled_in_parses`, `test_a_value_with_colons_keeps_everything_after_the_first_one`, `test_an_empty_or_commented_field_is_none` y `test_the_optional_fields_do_not_become_goals`.

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

# Hueco D13 — tarea verificable del tema, para que la Fase 2 corra sobre estos
# mismos temas y quede pareada con la Fase 1. En Fase 0 los tres van a None:
# aquí no se inventa ninguna tarea todavía.
# task:
# expected:
# verifier:
```

Los ocho temas son **deliberadamente dispares** y ninguno técnico de forma que se parezca a los artefactos de tipo `config`, `sql` o `stacktrace`: `mudanza`, `carrera-10k`, `elegir-colegio`, `hacer-pan`, `viaje-japon`, `huerto-balcon`, `factura-luz`, `elegir-camara`.

- [ ] **Step 4: Implementar `topics.py` y `simulated_user.py`**

`topics.py`:

```python
from dataclasses import dataclass
from pathlib import Path

TOPIC_DIR = Path(__file__).resolve().parents[2] / "data" / "topics"

# Campos opcionales del cuerpo que reserva D13 para la tarea verificable.
# En Fase 0 están comentados en los ocho ficheros y por tanto valen None.
_OPTIONAL_FIELDS = ("task", "expected", "verifier")


@dataclass(frozen=True)
class Topic:
    """Un tema de conversación doméstica del banco.

    `task`, `expected` y `verifier` son el hueco que exige D13: la Fase 2 necesita
    temas con una tarea verificable aguas abajo, y si el campo no existiera ya en
    Fase 0 la Fase 2 tendría que correr sobre temas nuevos, con lo que dejaría de
    estar pareada con la Fase 1. En Fase 0 los tres valen None a propósito: aquí
    no se inventa ninguna tarea.
    """

    id: str
    opening: str
    goals: tuple[str, ...]
    task: str | None = None
    expected: str | None = None
    verifier: str | None = None


def _parse(path: Path) -> Topic:
    """Lee un fichero de tema: frontmatter con `id` y cuerpo con el resto.

    Los campos opcionales se leen del cuerpo si están presentes como líneas
    `task:`, `expected:` o `verifier:`. Si la línea no está —o está comentada, o
    trae el valor vacío— el campo queda a None.
    """
    raw = path.read_text(encoding="utf-8")
    _, front, body = raw.split("---\n", 2)
    topic_id = front.strip().split(":", 1)[1].strip()
    opening = ""
    goals = []
    optional: dict[str, str | None] = {name: None for name in _OPTIONAL_FIELDS}
    for line in body.strip().splitlines():
        if line.startswith("opening:"):
            opening = line.split(":", 1)[1].strip()
        elif line.startswith("- "):
            goals.append(line[2:].strip())
        else:
            for name in _OPTIONAL_FIELDS:
                if line.startswith(f"{name}:"):
                    value = line.split(":", 1)[1].strip()
                    # Un valor vacío es un hueco declarado, no una tarea.
                    optional[name] = value or None
                    break
    return Topic(
        id=topic_id,
        opening=opening,
        goals=tuple(goals),
        task=optional["task"],
        expected=optional["expected"],
        verifier=optional["verifier"],
    )


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

`USER_MODEL` se fija aquí y **no se cambia durante toda la campaña** (§4 del spec). Es `terra` y no `sol` por coste: el usuario simulado genera un turno por vuelta en las 2.688 conversaciones de la Fase 1. `_SYSTEM` se registra literalmente en la cabecera de cada tirada (`user_system_prompt`, D5): si se toca, las tiradas dejan de ser comparables y el fichero lo dice.

- [ ] **Step 5: Ejecutar el test y comprobar que pasa**

```bash
uv run pytest tests/test_topics.py -v
```

Esperado: 10 passed.

- [ ] **Step 6: Commit**

```bash
git add data/topics src/wrongpaste/topics.py src/wrongpaste/simulated_user.py tests/test_topics.py
git commit -m "feat: ocho temas con hueco de tarea verificable y usuario simulado"
```

---

### Task 6: Esquema de fila, motor de conversación y prefijo compartido

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/records.py`
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/conversation.py`
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/prefixes.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_records.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_conversation.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_prefixes.py`

**Interfaces:**
- Consumes: `clients.chat`, `simulated_user.next_user_turn`, `topics.Topic`, `artifacts.Artifact`.
- Produces:
  - `records`: `ConversationRecord`, `RunHeader`, `run_header_line(...)`, `make_conversation_id(...)`, `SCHEMA_VERSION`, `N_STRATA`, `STATUSES`, `CONDITIONS`, `MESSAGE_TAGS`, `ARMS`, `ARM_NO_REPAIR`.
  - `conversation`: `api_messages(transcript)`, `build_prefix(model_id, topic, n_turns)`, `conversation_text(transcript)`, `inject_paste(model_id, transcript, artifact) -> (reacción, usage, paste_index)`, `continue_after_paste(model_id, transcript, topic, n_post=2) -> (post_indices, usages)`, `MAX_TOKENS`, `N_POST_TURNS`.
  - `prefixes`: `PREFIX_MODEL`, `PREFIX_DIR`, `prefix_id(...)`, `generate_prefix(topic, n_turns)`, `save_prefix`, `load_prefix`, `find_prefix`, `ensure_prefix(topic, n_turns)`.

**Por qué tres módulos y no uno.** `records.py` es hoja del grafo de importaciones a propósito: el runner, el verificador y el análisis lo importan sin arrastrar clientes HTTP. `conversation.py` conduce turnos. `prefixes.py` es la puerta de D1 — que exista separado es lo que impide que el runner llame a `build_prefix` por su cuenta y devuelva el eje x a depender de quién conteste.

**Por qué `build_prefix` e `inject_paste` están separadas.** La similaridad se mide contra *la conversación hasta el turno del pegote* (spec §4.1), así que el prefijo tiene que existir antes de poder elegir el artefacto. Una única `run_conversation(artifact=...)` obligaría a elegir el artefacto a ciegas. El runner (Task 7) hace: prefijo compartido → medir → muestrear → inyectar → dos turnos más.

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_records.py` — el esquema de fila (D5, D6, D7, D11, D15/D17). El test central es una lista literal de campos obligatorios:

```python
def test_la_fila_lleva_los_campos_que_exige_el_documento_de_correcciones():
    obligatorios = {
        # D5: identidad y trazabilidad
        "schema_version", "run_id", "conversation_id", "cell_index",
        "replicate_idx", "model_id", "model_label", "response_model",
        "topic_id", "n_turns", "stratum", "n_strata", "prefix_id",
        "condition", "arm", "parent_id",
        # D15/D17: género del artefacto y etiqueta del modelo
        "artifact_id", "artifact_kind", "artifact_text", "artifact_entities",
        # D2: las dos similaridades
        "similarity_user", "similarity_full", "similarity_rank",
        "similarity_pct", "ranking", "similarity_text_truncated",
        # D7: el pegote y los dos turnos posteriores
        "paste_index", "post_indices", "transcript", "reaction",
        # spec §4.2 y D9: lo que se envió
        "request_params", "system_prompt", "user_model", "prefix_model",
        "max_tokens", "stop_reasons", "usages", "seed",
        "started_at", "ended_at", "latency_ms",
        # D6: fallos como datos
        "status", "error_code", "error_body", "attempts",
    }
    assert obligatorios <= set(ConversationRecord.field_names())
```

Más: que una celda de control (D11) se construya y serialice sin artefacto ni similaridades; que `conversation_id` siga el formato de D5 y no se pise si viene dado; que `to_json()` no pierda ningún campo; que un `status` o un `condition` fuera del vocabulario revienten; y que `run_header_line` serialice con `kind="run_header"` delante, acepte campos sueltos y rechace campos inventados.

`tests/test_conversation.py` — etiquetas y turnos posteriores, con dobles, sin red:

```python
def test_prefix_tags_opening_user_sim_and_assistant(monkeypatch):
    _stub(monkeypatch)
    transcript, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=3)

    assert [m["tag"] for m in transcript] == [
        "opening", "assistant", "user_sim", "assistant", "user_sim", "assistant",
    ]


def test_chat_never_sees_the_tag_field(monkeypatch):
    seen: list[list[dict]] = []
    _stub(monkeypatch, seen=seen)

    transcript, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=2)
    conv.inject_paste("gpt-5.6-luna-tst", transcript, ART)
    conv.continue_after_paste("gpt-5.6-luna-tst", transcript, TOPIC)

    assert seen, "el stub tiene que haber visto llamadas"
    for messages in seen:
        for m in messages:
            assert set(m) == {"role", "content"}


def test_continue_after_paste_adds_four_messages(monkeypatch):
    _stub(monkeypatch)
    transcript, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=2)
    conv.inject_paste("gpt-5.6-luna-tst", transcript, ART)
    before = len(transcript)

    post_indices, usages = conv.continue_after_paste(
        "gpt-5.6-luna-tst", transcript, TOPIC
    )

    assert len(transcript) - before == 4
    assert len(usages) == 2
    assert post_indices == [before, before + 1, before + 2, before + 3]


def test_continue_after_paste_never_repairs(monkeypatch):
    """La variante (a) del spec §7: nadie menciona el pegote por el usuario."""
    _stub(monkeypatch)
    transcript, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=2)
    conv.inject_paste("gpt-5.6-luna-tst", transcript, ART)
    conv.continue_after_paste("gpt-5.6-luna-tst", transcript, TOPIC)

    assert all(m["tag"] != "repair" for m in transcript)
```

Más: que el prefijo alterne roles y acabe en `assistant` (Claude lo exige), que solo el primer mensaje lleve `opening`, que el pegote vaya literal y sin preámbulo, que `inject_paste` etiquete `paste` y devuelva el índice, y que los `post_indices` apunten a mensajes posteriores a la reacción.

`tests/test_prefixes.py` — D1, con `PREFIX_DIR` redirigido a `tmp_path` por un fixture `autouse` y `build_prefix` doblado:

```python
def test_ensure_prefix_does_not_regenerate_when_the_file_exists(monkeypatch):
    calls: list[tuple] = []
    _stub_build(monkeypatch, calls=calls)
    first = prefixes.ensure_prefix(TOPIC, 2)

    second = prefixes.ensure_prefix(TOPIC, 2)

    assert len(calls) == 1, "el segundo paso no debe volver a llamar al modelo"
    assert second == first
    assert len(list(prefixes.PREFIX_DIR.glob("*.json"))) == 1


def test_every_model_gets_the_very_same_prefix(monkeypatch):
    """D1: el eje x no puede depender de quién conteste."""
    _stub_build(monkeypatch)
    prefixes.ensure_prefix(TOPIC, 2)

    served = [prefixes.ensure_prefix(TOPIC, 2) for _ in range(3)]

    assert all(p["transcript"] == served[0]["transcript"] for p in served)
    assert len({p["prefix_id"] for p in served}) == 1
```

Más: que `prefix_id` sea determinista y cambie con la transcripción, con las etiquetas y con (tema, longitud, modelo); que `generate_prefix` use `PREFIX_MODEL` y no escriba nada; el round-trip de `save_prefix`/`load_prefix`; que `ensure_prefix` sea por (tema, longitud); y que `find_prefix` devuelva `None` con el directorio vacío.

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

```bash
uv run pytest tests/test_records.py tests/test_conversation.py tests/test_prefixes.py -v
```

Esperado: FAIL con `ModuleNotFoundError` en los tres módulos.

- [ ] **Step 3a: Implementar `records.py`**

Vocabularios cerrados y el identificador de conversación:

```python
# Versión del esquema de fila. Se sube cuando un cambio rompe a quien lea
# ficheros antiguos: el análisis puede así ramificar por versión en vez de
# adivinar qué campos existían.
SCHEMA_VERSION = 2

# Número de estratos de similaridad por defecto (spec §4.1, D3).
N_STRATA = 8

# Vocabulario cerrado de D6: un fallo es un dato, no una caída.
Status = Literal["ok", "http_error", "timeout", "refusal", "empty"]
STATUSES: tuple[str, ...] = ("ok", "http_error", "timeout", "refusal", "empty")

# D11: el brazo de control no lleva pegote.
Condition = Literal["paste", "no_paste"]
CONDITIONS: tuple[str, ...] = ("paste", "no_paste")

# Etiquetas de mensaje del transcript (D5).
MESSAGE_TAGS: tuple[str, ...] = (
    "opening", "user_sim", "paste", "repair", "assistant", "post",
)

# Brazos de reparación del spec §7. La Fase 0 corre siempre la variante (a),
# "el usuario sigue como si el pegote no existiera" (D7).
ARMS: tuple[str, ...] = ("a", "b", "c", "d")
ARM_NO_REPAIR = "a"


def make_conversation_id(
    model_id: str, topic_id: str, n_turns: int, replicate_idx: int
) -> str:
    """Identificador determinista y legible de una conversación (D5).

    Formato: ``p0-{model}-{topic}-{n_turns}-r{replicate}``. Es la clave que usa
    `main()` para saltarse celdas ya escritas al reanudar una tirada (D6), así
    que tiene que salir igual en dos ejecuciones distintas del mismo plan.
    """
    return f"p0-{model_id}-{topic_id}-{n_turns}-r{replicate_idx}"
```

`ConversationRecord` lleva **todos** los campos con valor por defecto, para que las celdas de control (D11, sin artefacto) y las fallidas (D6, sin reacción) se puedan construir sin inventar datos. Los bloques, en orden: identidad (D5) · modelo evaluado con `model_id` + `model_label` + `response_model` (D17) · celda del diseño con `stratum`, `n_strata` y `prefix_id` (D3, D1) · brazo con `condition`, `arm` y `parent_id` (D11, spec §7) · artefacto opcional con `artifact_kind` para poder medir la colinealidad de D15 · similaridades `similarity_user` y `similarity_full` más rango, percentil, `ranking` completo y `similarity_text_truncated` (D2) · transcripción con `paste_index` y `post_indices` (D5, D7) · lo enviado, con `request_params`, `system_prompt`, `prefix_model` y `stop_reasons` (D9, spec §4.2) · reloj · resultado con `status`, `error_code`, `error_body` y `attempts` (D6).

`__post_init__` resuelve el `conversation_id` si no viene dado y **valida** `condition` y `status` contra sus vocabularios: un typo en un `status` convertiría una celda fallida en una celda buena a ojos del análisis.

`RunHeader` es la primera línea de cada JSONL (D5): `run_id`, `phase`, `plan_path`, `spec_path`, `code_sha`, `bank_sha`, `topics_sha`, `master_seed`, `roster`, `planned_cells`, `embedding_model`, `prefix_model`, `user_model`, `user_system_prompt`, `started_at`. Sirve para dos cosas: reproducir la tirada y **detectar un fichero truncado** — si la cabecera dice `planned_cells: 27` y hay 19 filas, el fichero está incompleto. `run_header_line()` la serializa con `{"kind": "run_header", ...}` delante y rechaza campos inventados.

- [ ] **Step 3b: Implementar `conversation.py`**

```python
MAX_TOKENS = 1024

# Cuántos turnos de usuario van después de la reacción al pegote (D7).
N_POST_TURNS = 2


def api_messages(transcript: list[dict]) -> list[dict]:
    """La transcripción tal y como se le manda al proveedor: sin `tag`."""
    return [{"role": m["role"], "content": m["content"]} for m in transcript]


def build_prefix(
    model_id: str, topic: Topic, n_turns: int
) -> tuple[list[dict], list[dict]]:
    """Conduce n_turns de conversación normal sobre el tema.

    Devuelve la transcripción (siempre terminada en assistant, que es lo que
    Claude exige para poder continuar) y los `usage` de cada llamada.

    Etiquetas (D5): el mensaje de apertura es `opening`, los demás mensajes de
    usuario son `user_sim` (los escribe el usuario simulado) y las respuestas
    son `assistant`.

    En la Fase 0 este prefijo lo fabrica siempre `PREFIX_MODEL` y se comparte
    entre modelos evaluados (D1); ver `wrongpaste.prefixes`.
    """
    transcript: list[dict] = [
        {"role": "user", "content": topic.opening, "tag": "opening"}
    ]
    usages: list[dict] = []

    reply = chat(model_id, api_messages(transcript), max_tokens=MAX_TOKENS)
    transcript.append({"role": "assistant", "content": reply.text, "tag": "assistant"})
    usages.append(reply.usage)

    for _ in range(n_turns - 1):
        transcript.append(
            {
                "role": "user",
                "content": next_user_turn(topic, transcript),
                "tag": "user_sim",
            }
        )
        reply = chat(model_id, api_messages(transcript), max_tokens=MAX_TOKENS)
        transcript.append(
            {"role": "assistant", "content": reply.text, "tag": "assistant"}
        )
        usages.append(reply.usage)

    return transcript, usages


def conversation_text(transcript: list[dict]) -> str:
    """La conversación entera como texto (similaridad secundaria, D2)."""
    return "\n".join(m["content"] for m in transcript)


def inject_paste(
    model_id: str, transcript: list[dict], artifact: Artifact
) -> tuple[str, dict, int]:
    """Añade el pegote TAL CUAL, sin preámbulo ni envoltorio, y pide respuesta.

    Muta `transcript` in place: el registro guarda la conversación completa.

    Devuelve (reacción, usage, índice del mensaje del pegote). El índice va al
    campo `paste_index` de la fila (D5): sin él, el análisis tendría que volver
    a localizar el pegote comparando textos.
    """
    paste_index = len(transcript)
    transcript.append({"role": "user", "content": artifact.text, "tag": "paste"})
    reply = chat(model_id, api_messages(transcript), max_tokens=MAX_TOKENS)
    transcript.append({"role": "assistant", "content": reply.text, "tag": "assistant"})
    return reply.text, reply.usage, paste_index


def continue_after_paste(
    model_id: str,
    transcript: list[dict],
    topic: Topic,
    n_post: int = N_POST_TURNS,
) -> tuple[list[int], list[dict]]:
    """Dos turnos más con el usuario simulado, SIN reparación (D7).

    Es la variante (a) del spec §7: el usuario sigue a lo suyo como si el
    pegote no existiera. Sirve para separar "pivota en silencio" de "puente
    confabulado" — que a menudo solo se distinguen en el turno +1 — y para
    pilotar ya el recuento de entidades de la Fase 2.

    Muta `transcript` in place. El mensaje de usuario se etiqueta `post` y la
    respuesta `assistant`.

    Devuelve (post_indices, usages). `post_indices` son los índices de **todos**
    los mensajes añadidos aquí, usuario y asistente, en orden: el recuento de
    fuga de entidades se hace sobre las respuestas, así que dejarlas fuera
    obligaría al análisis a recalcular posiciones.
    """
    post_indices: list[int] = []
    usages: list[dict] = []

    for _ in range(n_post):
        post_indices.append(len(transcript))
        transcript.append(
            {
                "role": "user",
                "content": next_user_turn(topic, transcript),
                "tag": "post",
            }
        )
        reply = chat(model_id, api_messages(transcript), max_tokens=MAX_TOKENS)
        post_indices.append(len(transcript))
        transcript.append(
            {"role": "assistant", "content": reply.text, "tag": "assistant"}
        )
        usages.append(reply.usage)

    return post_indices, usages
```

`tag` es metadato nuestro, no del protocolo: **todas** las llamadas pasan por `api_messages()`, porque los proveedores rechazan campos desconocidos dentro de `messages`.

- [ ] **Step 3c: Implementar `prefixes.py`**

```python
# Modelo que hace de asistente al fabricar el prefijo. Es el mismo que hace de
# usuario simulado a propósito: un solo cuerpo barato fabrica la conversación
# entera, y ninguno de los modelos evaluados influye en el eje x.
PREFIX_MODEL = "gpt-5.6-terra-tst"

# Dónde viven los prefijos ya fabricados. Se lee como global en cada función
# para que los tests lo puedan redirigir a un `tmp_path`.
PREFIX_DIR = Path(__file__).resolve().parents[2] / "runs" / "prefixes"

# Longitud en hex del identificador. 16 hex = 64 bits: de sobra para ocho
# prefijos y corto como para caber en un nombre de fichero legible.
PREFIX_ID_LEN = 16


def prefix_id(
    topic_id: str, n_turns: int, prefix_model: str, transcript: list[dict]
) -> str:
    """Huella del prefijo: sha256 de su serialización determinista, 16 hex.

    Entra todo lo que puede cambiar el contexto que ve el modelo evaluado: el
    tema, la longitud, quién hizo de asistente y la transcripción completa
    (incluidas las etiquetas `tag`). Dos prefijos con el mismo `prefix_id` son
    el mismo contexto, palabra por palabra.
    """
    payload = {
        "topic_id": topic_id,
        "n_turns": int(n_turns),
        "prefix_model": prefix_model,
        "transcript": [
            {"role": m["role"], "content": m["content"], "tag": m.get("tag", "")}
            for m in transcript
        ],
    }
    blob = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:PREFIX_ID_LEN]


def generate_prefix(topic: Topic, n_turns: int) -> dict[str, Any]:
    """Fabrica un prefijo nuevo con `PREFIX_MODEL` de asistente.

    No lo guarda: eso es cosa de `save_prefix`, para que los tests y el paso de
    medición de ejes (D12) puedan generar sin ensuciar el repo.
    """
    transcript, usages = build_prefix(PREFIX_MODEL, topic, n_turns)
    return {
        "prefix_id": prefix_id(topic.id, n_turns, PREFIX_MODEL, transcript),
        "topic_id": topic.id,
        "n_turns": int(n_turns),
        "prefix_model": PREFIX_MODEL,
        "transcript": transcript,
        "usages": usages,
    }


def ensure_prefix(topic: Topic, n_turns: int) -> dict[str, Any]:
    """Devuelve el prefijo de (tema, longitud), generándolo solo si falta.

    Es la puerta que usa el runner: idempotente y barata al reanudar una
    tirada, y garantía de que los tres modelos de la Fase 0 ven exactamente el
    mismo contexto antes del pegote (D1).
    """
    existing = find_prefix(topic.id, n_turns, PREFIX_MODEL)
    if existing is not None:
        return existing
    prefix = generate_prefix(topic, n_turns)
    save_prefix(prefix)
    return prefix
```

Completan el fichero `prefix_path`, `save_prefix` (escribe `runs/prefixes/<prefix_id>.json`), `load_prefix` (revienta si no está: no regenera a escondidas) y `find_prefix`, que busca por (tema, longitud, modelo) y no por `prefix_id` porque el id solo se conoce *después* de generar la transcripción.

Los prefijos se versionan: son el eje x de la campaña entera y su coste ya está pagado.

- [ ] **Step 4: Ejecutar los tests y comprobar que pasan**

```bash
uv run pytest tests/test_records.py tests/test_conversation.py tests/test_prefixes.py -v
```

Esperado: 41 passed (17 + 12 + 12).

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/records.py src/wrongpaste/conversation.py src/wrongpaste/prefixes.py \
        tests/test_records.py tests/test_conversation.py tests/test_prefixes.py
git commit -m "feat: esquema de fila, motor de conversación etiquetado y prefijo compartido"
```

---

### Task 7: Runner de la Fase 0

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/run_phase0.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_run_phase0.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: `plan_phase0(seed) -> list[dict]`, `stratum_window(ranked, stratum, n_strata)`, `pick_artifact(ranked, stratum, kind_counts, rng, n_strata)`, `measure_axis(topics, arts, n_turns, run_id) -> dict`, `resume_state(path)`, `run_cell(...)`, `failed_record(...)`, `main(seed, out=None, measure=True)` que escribe `runs/phase0/<timestamp>.jsonl`, `runs/phase0/axis-<run_id>.json` y `runs/phase0/summary-<run_id>.json`.

Este fichero es donde aterrizan seis decisiones:

- **D3 — rotación de ejes.** El estrato va *en el plan*, como `(t + 3·m) % 8` sobre el índice de tema y el de modelo, y la longitud alterna como `LENGTHS[(t + m) % 2]`. Antes, `LENGTHS[i % 2]` sobre el índice de tema y `stratum = i % STRATA` sobre el índice global hacían que estrato ≡ tema ≡ longitud: tres ejes que eran el mismo. El orden de ejecución es **round-robin de modelos dentro de cada tema**, no modelo-mayor: con dos horas de tirada contra un gateway compartido, modelo-mayor confunde el modelo con la hora de reloj.
- **D4 — cobertura de `kind`.** Dentro del estrato se elige el artefacto cuyo género esté menos representado hasta ese momento.
- **D5 — identidad.** Primera línea `run_header`; cada fila con `conversation_id` determinista y legible.
- **D6 — fallos como datos.** `try/except` por celda, fila siempre, reanudación y resumen final.
- **D11 — tres celdas de control** sin pegote.
- **D12 — ancho del eje medido antes de gastar.**

El prefijo **no** se construye aquí: viene de `prefixes.ensure_prefix` (D1).

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_run_phase0.py` no hace una sola llamada a un modelo: `ensure_prefix`, `rank_artifacts`, `inject_paste` y `continue_after_paste` se sustituyen por dobles deterministas en un fixture `harness` que además redirige `OUT_DIR` a `tmp_path`.

Rotación de ejes (D3):

```python
def test_stratum_travels_inside_the_plan():
    """El estrato es un dato de la celda, no el orden de iteración."""
    plan = plan_phase0(seed=1)
    assert all("stratum" in c for c in plan)
    strata = {c["stratum"] for c in _paste_cells(plan)}
    assert strata <= set(range(STRATA))


def test_stratum_follows_the_documented_formula():
    plan = _paste_cells(plan_phase0(seed=1))
    by_cell = {(c["topic_id"], c["model_id"]): c for c in plan}
    for t, topic in enumerate(TOPICS):
        for m, model_id in enumerate(PHASE0_MODELS):
            cell = by_cell[(topic.id, model_id)]
            assert cell["stratum"] == (t + STRATUM_STEP * m) % STRATA
            assert cell["n_turns"] == LENGTHS[(t + m) % 2]


def test_no_stratum_equals_the_topic_index_for_all_three_models():
    """Si estrato ≡ tema, el eje de similaridad y el de tema son el mismo eje."""
    plan = _paste_cells(plan_phase0(seed=1))
    for t, topic in enumerate(TOPICS):
        strata = [c["stratum"] for c in plan if c["topic_id"] == topic.id]
        assert len(strata) == len(PHASE0_MODELS)
        assert not all(s == t for s in strata)
        assert len(set(strata)) == len(PHASE0_MODELS), (
            "los tres modelos de un tema tienen que caer en estratos distintos"
        )


def test_every_stratum_lands_on_three_different_topics():
    ...


def test_every_topic_appears_in_both_lengths():
    ...


def test_execution_order_is_round_robin_of_models_inside_each_topic():
    """Modelo-mayor confundiría el modelo con la hora de reloj del gateway."""
    plan = _paste_cells(plan_phase0(seed=1))
    assert [c["model_id"] for c in plan[: len(PHASE0_MODELS)]] == PHASE0_MODELS
    topic_order = [c["topic_id"] for c in plan[:: len(PHASE0_MODELS)]]
    assert topic_order == [t.id for t in TOPICS]
```

Brazo de control (D11):

```python
def test_plan_includes_three_control_cells_without_paste():
    controls = _control_cells(plan_phase0(seed=1))
    assert len(controls) == rp.N_CONTROL_CELLS == 3
    assert all(c["condition"] == "no_paste" for c in controls)
    assert all(c["stratum"] == -1 for c in controls)


def test_control_cells_reuse_a_length_that_the_plan_already_builds():
    """El control no puede inventarse un prefijo nuevo: sería gastar por gusto."""
    plan = plan_phase0(seed=1)
    pairs = {(c["topic_id"], c["n_turns"]) for c in _paste_cells(plan)}
    for control in _control_cells(plan):
        assert (control["topic_id"], control["n_turns"]) in pairs
```

Cobertura de género (D4), incluido el contraste con el muestreo a suerte que D4 sustituye:

```python
def test_pick_artifact_prefers_the_least_represented_kind():
    window = [
        (Artifact("a", "recipe", "t", ()), 0.1),
        (Artifact("b", "prompt", "t", ()), 0.2),
        (Artifact("c", "recipe", "t", ()), 0.3),
    ]
    counts = Counter({"recipe": 2, "prompt": 5})
    # Un único estrato que es la ventana entera, para aislar la elección.
    art, _ = pick_artifact(window, 0, counts, np.random.default_rng(0), n_strata=1)
    assert art.kind == "recipe"

    counts["recipe"] = 9
    art, _ = pick_artifact(window, 0, counts, np.random.default_rng(0), n_strata=1)
    assert art.kind == "prompt"


def test_the_sampling_plan_covers_all_eleven_kinds():
    """D4: con 24 celdas y 11 géneros, dejarlo a suerte deja géneros sin ver."""
    counts: Counter = Counter()
    for cell in _paste_cells(plan_phase0(seed=rp.MASTER_SEED)):
        rng = np.random.default_rng(cell["seed"])
        ranked = _fake_ranking(ARTS, rng)
        art, _ = pick_artifact(ranked, cell["stratum"], counts, rng)
        counts[art.kind] += 1

    assert len(ALL_KINDS) == 11
    assert set(counts) == ALL_KINDS, f"géneros sin cubrir: {ALL_KINDS - set(counts)}"


def test_sampling_without_the_kind_rule_would_miss_kinds():
    """Contraste: el muestreo a suerte es el que D4 sustituye, y se le nota."""
    ...
```

Ancho del eje (D12): `test_measure_axis_reports_min_median_and_max_per_topic`, `test_measure_axis_embeds_the_user_side_of_the_prefix`, `test_measure_axis_flags_a_narrow_topic` y `test_main_writes_the_axis_report_before_the_run`.

Sobre la tirada (D5/D6/D7/D11): que la cabecera vaya primero; una fila por celda con identidad; dos turnos después del pegote; `post_indices` y `paste_index` en la fila; las filas de control sin artefacto ni similaridad; las de pegote con **las dos** similaridades y el ranking completo; que los tres modelos de un tema compartan prefijo y ranking; idempotencia y reanudación; que la reanudación mantenga la cobertura de géneros; y que `resume_state` sobreviva a una última línea truncada.

Fallos como datos (D6):

```python
def test_a_failing_cell_still_writes_a_row_and_the_run_goes_on(harness, monkeypatch):
    ...
    monkeypatch.setattr(rp, "inject_paste", flaky)
    path = rp.main(seed=7)
    _, rows = _rows(path)

    assert len(rows) == len(plan_phase0(7)), "una celda rota no puede acortar la tirada"
    failed = [r for r in rows if r["status"] != "ok"]
    assert len(failed) == 1
    assert failed[0]["status"] == "http_error"
    assert failed[0]["error_code"] == 429
    assert failed[0]["error_body"] == "rate limited"
    assert failed[0]["attempts"] == 3
    # Lo que se sabía antes de reventar se queda en la fila.
    assert failed[0]["prefix_id"].startswith("pfx-")
    assert failed[0]["artifact_id"]


def test_an_empty_reaction_is_not_an_ok(harness, monkeypatch):
    ...
    assert all(r["status"] == "empty" for r in pasted)


def test_a_timeout_is_recorded_as_a_timeout(harness, monkeypatch):
    ...
    assert all(r["status"] == "timeout" for r in pasted)


def test_main_writes_the_final_summary(harness, capsys):
    path = rp.main(seed=7)
    summary = json.loads(rp.summary_path(path.stem).read_text(encoding="utf-8"))

    assert summary["planned"] == len(plan_phase0(7))
    assert summary["completed"] == summary["planned"]
    assert summary["failed"] == 0
    assert summary["skipped"] == 0
    out = capsys.readouterr().out
    assert "planificadas" in out and "completadas" in out and "fallidas" in out
```

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

```bash
uv run pytest tests/test_run_phase0.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.run_phase0'`.

- [ ] **Step 3a: Constantes y plan (D3, D11)**

```python
PHASE0_MODELS = ["gpt-5.6-sol-tst", "gpt-5.6-luna-tst", "claude-opus-5"]
LENGTHS = [2, 10]
STRATA = N_STRATA

# Salto de estrato entre modelos consecutivos (D3). Con 8 estratos y 3 modelos,
# 3 es coprimo con 8: los tres modelos de un mismo tema caen siempre en estratos
# distintos y el estrato deja de ser una función del tema.
STRATUM_STEP = 3

# D11: tres celdas sin pegote. No pretenden dar una tasa base creíble —eso es de
# la Fase 2—, sino demostrar que el formato, el runner y el verificador soportan
# el brazo de control.
N_CONTROL_CELLS = 3

# D12: por debajo de este rango de coseno, el tema no separa nada y la
# estratificación es decorativa. Es criterio explícito del GO/NO-GO.
NARROW_RANGE = 0.15

# Cuántos artefactos de la cola alta se listan en el informe de ejes, para que
# quien lo lea pueda juzgar si la cola alta está vacía (D12).
AXIS_TOP_N = 3

MASTER_SEED = 20260913
OUT_DIR = Path(__file__).resolve().parents[2] / "runs" / "phase0"


def plan_phase0(seed: int) -> list[dict]:
    """Devuelve las celdas de la Fase 0, en el orden en que se van a correr.

    Con `t` el índice del tema y `m` el del modelo (D3)::

        stratum = (t + 3 * m) % 8
        n_turns = LENGTHS[(t + m) % 2]

    El estrato viaja **en el dict**: no se deriva del orden de iteración, que es
    precisamente lo que hacía que estrato, tema y longitud fueran el mismo eje.

    El bucle exterior es el tema y el interior el modelo, o sea round-robin de
    modelos: si el gateway se degrada a mitad de tirada, la degradación se
    reparte entre los tres modelos en vez de caer entera sobre el último.

    Al final se añaden las tres celdas de control sin pegote (D11). Cada una
    reutiliza el prefijo de la longitud que **no** usa ese mismo modelo en ese
    mismo tema: así no genera ningún prefijo nuevo y su `conversation_id`, que
    lleva la longitud dentro, no puede chocar con el de la celda con pegote.
    """
    topics = load_topics()
    rng = np.random.default_rng(seed)
    plan: list[dict] = []

    for t, topic in enumerate(topics):
        for m, model_id in enumerate(PHASE0_MODELS):
            n_turns = LENGTHS[(t + m) % len(LENGTHS)]
            plan.append(
                _cell(
                    cell_index=len(plan),
                    model_id=model_id,
                    topic_id=topic.id,
                    n_turns=n_turns,
                    stratum=(t + STRATUM_STEP * m) % STRATA,
                    condition="paste",
                    seed=int(rng.integers(0, 2**31)),
                )
            )

    for i in range(N_CONTROL_CELLS):
        t = i % len(topics)
        m = i % len(PHASE0_MODELS)
        # La longitud contraria a la de la celda con pegote de ese (tema, modelo).
        n_turns = LENGTHS[(t + m + 1) % len(LENGTHS)]
        plan.append(
            _cell(
                cell_index=len(plan),
                model_id=PHASE0_MODELS[m],
                topic_id=topics[t].id,
                n_turns=n_turns,
                # Sin pegote no hay estrato que asignar.
                stratum=-1,
                condition="no_paste",
                seed=int(rng.integers(0, 2**31)),
            )
        )

    return plan
```

`_cell(...)` empaqueta la celda y le resuelve ya el `conversation_id` con `make_conversation_id` (D5). El plan sale con **27 celdas**: 24 con pegote (8 temas × 3 modelos) y 3 de control.

- [ ] **Step 3b: Muestreo del artefacto (D4)**

```python
def stratum_window(
    ranked: list[tuple[Artifact, float]], stratum: int, n_strata: int = STRATA
) -> list[tuple[Artifact, float]]:
    """El trozo del ranking que corresponde a un estrato.

    Se estratifica por **posición** en el ranking, no por valor de coseno: la
    distribución real está muy concentrada y los estratos por valor saldrían
    vacíos. La ventana nunca es vacía, aunque el banco sea más pequeño que el
    número de estratos.
    """
    if not ranked:
        raise ValueError("el ranking está vacío: no hay de dónde muestrear")
    if not 0 <= stratum < n_strata:
        raise ValueError(f"estrato fuera de rango: {stratum} (de {n_strata})")
    lo = len(ranked) * stratum // n_strata
    hi = len(ranked) * (stratum + 1) // n_strata
    return ranked[lo : max(hi, lo + 1)]


def pick_artifact(
    ranked: list[tuple[Artifact, float]],
    stratum: int,
    kind_counts: Counter,
    rng: np.random.Generator,
    n_strata: int = STRATA,
) -> tuple[Artifact, float]:
    """Elige artefacto dentro del estrato, cubriendo géneros (D4).

    De la ventana del estrato se queda con los artefactos cuyo `kind` esté menos
    representado **hasta ese momento en la tirada**, y desempata al azar con el
    `rng` de la celda. Con 24 celdas y 11 géneros, dejarlo a suerte permitía
    derivar la rúbrica sin haber visto nunca un `prompt` pegado, que es justo el
    caso donde el pegote es una instrucción ejecutable.

    No toca `kind_counts`: la contabilidad la lleva quien llama, que es quien
    sabe si la celda llegó a correrse.
    """
    window = stratum_window(ranked, stratum, n_strata)
    fewest = min(kind_counts[art.kind] for art, _ in window)
    candidates = [pair for pair in window if kind_counts[pair[0].kind] == fewest]
    return candidates[int(rng.integers(0, len(candidates)))]
```

- [ ] **Step 3c: Ancho del eje (D12)**

```python
def measure_axis(
    topics: list[Topic] | None = None,
    arts: list[Artifact] | None = None,
    n_turns: int = LENGTHS[0],
    run_id: str = "",
) -> dict[str, Any]:
    """Embebe los ocho prefijos contra el banco y mide el rango por tema (D12).

    Se corre **antes** de la tirada y cuesta céntimos. Sirve para no gastar el
    presupuesto en un eje que no separa: si un tema tiene un rango de coseno por
    debajo de `NARROW_RANGE`, o su cola alta está vacía, la estratificación de
    ese tema es decorativa y hay que completar el banco antes de seguir.

    Usa el prefijo corto de cada tema, que es el que `ensure_prefix` ya va a
    fabricar para la tirada: no genera trabajo extra, solo lo adelanta.

    Devuelve el informe (que `main` guarda en `runs/phase0/axis-<run_id>.json`)
    y lo imprime por pantalla de camino.
    """
    topics = load_topics() if topics is None else topics
    arts = load_artifacts() if arts is None else arts

    per_topic: list[dict[str, Any]] = []
    print(f"--- ancho del eje (D12): {len(arts)} artefactos, n_turns={n_turns}")
    for topic in topics:
        prefix = ensure_prefix(topic, n_turns)
        ranking, truncated = rank_artifacts(user_text(prefix["transcript"]), arts)
        stats = rank_stats(ranking)
        entry = {
            "topic_id": topic.id,
            "prefix_id": prefix["prefix_id"],
            "n_turns": int(n_turns),
            "min": stats["min"],
            "median": stats["median"],
            "max": stats["max"],
            "range": stats["max"] - stats["min"],
            "narrow": (stats["max"] - stats["min"]) < NARROW_RANGE,
            "truncated": bool(truncated),
            # La cola alta, para poder juzgar si está vacía de dominio.
            "top": [
                {"artifact_id": art.id, "kind": art.kind, "similarity": sim}
                for art, sim in ranking[-AXIS_TOP_N:][::-1]
            ],
        }
        per_topic.append(entry)
        print(
            f"  {topic.id:<16} min={entry['min']:.3f} "
            f"med={entry['median']:.3f} max={entry['max']:.3f} "
            f"rango={entry['range']:.3f}"
            + ("  <-- ESTRECHO" if entry["narrow"] else "")
        )

    narrow = [e["topic_id"] for e in per_topic if e["narrow"]]
    if narrow:
        print(f"  OJO: temas con rango < {NARROW_RANGE}: {', '.join(narrow)}")

    return {
        "run_id": run_id,
        "embedding_model": config.EMBEDDING_MODEL,
        "prefix_model": PREFIX_MODEL,
        "n_turns": int(n_turns),
        "n_artifacts": len(arts),
        "narrow_threshold": NARROW_RANGE,
        "narrow_topics": narrow,
        "topics": per_topic,
    }
```

- [ ] **Step 3d: Identidad, reanudación y traducción de errores (D5, D6)**

`bank_sha`, `topics_sha` y `code_sha` alimentan la cabecera. `code_sha` lee el `.git` a pelo en vez de llamar a `git rev-parse`: una tirada de dos horas no se cae por no saber el sha.

```python
def resume_state(path: Path) -> tuple[set[str], Counter]:
    """Lee un JSONL a medias: qué celdas ya están y qué géneros se han gastado.

    Los `conversation_id` presentes se saltan al reanudar, y los `artifact_kind`
    ya escritos vuelven al contador de D4: sin eso, reanudar rompería la
    cobertura de géneros justo en las celdas que quedan por correr.

    Una línea ilegible se ignora en vez de tumbar la reanudación: un fichero
    truncado a mitad de escritura es exactamente el caso que esto tiene que
    sobrevivir.
    """


def _status_for_error(exc: BaseException) -> tuple[str, int | str | None, str]:
    """Traduce una excepción al vocabulario cerrado de `status` (D6).

    `refusal` no se decide aquí: una negativa del modelo llega con HTTP 200 y
    texto, así que es `ok` en el fichero y la marca quien anota. Lo que sí es
    `refusal` es que el proveedor corte por filtro de contenido, y eso llega
    como error del proveedor con su propio código.
    """
```

- [ ] **Step 3e: Una celda (D1, D2, D4, D7, D11)**

`rank_for_prefix` cachea el ranking por `prefix_id`. No es una optimización cualquiera: como el prefijo es el mismo para los tres modelos (D1), el eje x de una celda **tiene** que salir idéntico para los tres, y recalcularlo por celda lo dejaría a merced del ruido del embedder. Devuelve el ranking primario (lado del usuario), el diccionario de similaridades secundarias por `artifact_id`, y si hubo truncado.

```python
def run_cell(cell, topic, arts, rank_cache, kind_counts, run_id, started_at, partial):
    """Corre una celda entera y devuelve su fila.

    `partial` se va rellenando sobre la marcha con lo que ya se sabe (prefijo,
    artefacto, transcripción), para que si esto revienta a mitad, la fila de
    fallo que escribe `main` no salga vacía (D6).

    Secuencia: prefijo compartido (D1), muestreo del artefacto dentro del
    estrato del plan (D3/D4), pegote literal, y dos turnos más con el usuario
    simulado sin reparación (D7). En las celdas de control (D11) se salta el
    pegote y se va directo a los turnos posteriores.
    """
    model_id = cell["model_id"]
    prefix = ensure_prefix(topic, cell["n_turns"])
    partial["prefix_id"] = prefix["prefix_id"]

    # Copia: el prefijo cacheado lo comparten los tres modelos y no se muta.
    transcript = [dict(m) for m in prefix["transcript"]]
    partial["transcript"] = transcript
    ...
    if cell["condition"] == "paste":
        rng = np.random.default_rng(cell["seed"])
        ranking, full_by_id, truncated = rank_for_prefix(prefix, arts, rank_cache)
        artifact, similarity_user = pick_artifact(
            ranking, cell["stratum"], kind_counts, rng
        )
        kind_counts[artifact.kind] += 1
        partial["artifact"] = artifact

        similarity_full = full_by_id.get(artifact.id)
        ids = [art.id for art, _ in ranking]
        similarity_rank = ids.index(artifact.id)
        # Percentil dentro del banco, 0 = el más lejano, 1 = el más parecido.
        similarity_pct = similarity_rank / (len(ids) - 1) if len(ids) > 1 else 0.0
        ranking_rows = [
            {"artifact_id": art.id, "similarity": sim} for art, sim in ranking
        ]

        reaction, paste_usage, paste_index = inject_paste(
            model_id, transcript, artifact
        )
        usages.append(paste_usage)

    post_indices, post_usages = continue_after_paste(
        model_id, transcript, topic, n_post=N_POST_TURNS
    )
    usages.extend(post_usages)

    # Una celda con pegote que devuelve reacción vacía no es un `ok`: es texto
    # que no está, y el análisis tiene que poder descartarla sin leerla.
    status = "ok"
    if cell["condition"] == "paste" and not (reaction or "").strip():
        status = "empty"
    ...
```

En `usages` van **solo** las llamadas que paga esta celda: las del prefijo se pagaron una vez y viven en `runs/prefixes/<prefix_id>.json` (D1).

`failed_record(...)` construye la fila cuando la celda revienta, con todo lo que se llegó a saber (`prefix_id`, artefacto, transcripción parcial) más `status`, `error_code`, `error_body` y `attempts`.

- [ ] **Step 3f: La tirada (`main`)**

```python
def main(
    seed: int = MASTER_SEED,
    out: Path | str | None = None,
    measure: bool = True,
) -> Path:
    """Corre la Fase 0 entera y devuelve la ruta del JSONL.

    Si `out` apunta a un fichero que ya existe, la tirada **se reanuda**: se
    saltan los `conversation_id` que ya están dentro y se sigue escribiendo al
    final del mismo fichero (D6). Si no, se crea uno nuevo con la cabecera.

    `measure=False` salta el paso de ancho de eje (D12); solo para pruebas, la
    tirada de verdad lo quiere delante.
    """
```

El cuerpo, en orden: cargar temas, banco y plan · decidir fichero (nuevo con timestamp, o reanudación) · `measure_axis` y volcado de `axis-<run_id>.json` · escribir la cabecera si no se reanuda · por cada celda, `try`/`except` alrededor de `run_cell`, fila siempre, `flush()` siempre y una línea impresa por celda · al final, `summary-<run_id>.json` con planificadas, completadas, fallidas, saltadas y el recuento de géneros, más el mismo resumen por pantalla.

- [ ] **Step 4: Ejecutar los tests y comprobar que pasan**

```bash
uv run pytest tests/test_run_phase0.py -v
```

Esperado: 40 passed.

- [ ] **Step 5: Ejecutar la suite entera sin red**

```bash
uv run pytest -q -m "not live"
```

Esperado: `149 passed, 4 deselected`.

- [ ] **Step 6: Commit**

```bash
git add src/wrongpaste/run_phase0.py tests/test_run_phase0.py
git commit -m "feat: runner de la Fase 0 con rotación de ejes, cobertura de género y fallos como datos"
```

---

### Task 8: Correr la Fase 0 y derivar la rúbrica

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/runs/prefixes/*.json` (16: ocho temas × dos longitudes)
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/<timestamp>.jsonl` (el timestamp lo pone el runner)
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/axis-<run_id>.json`
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/summary-<run_id>.json`
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/annotations-<run_id>.jsonl`
- Create: `~/Documents/repos/llm-wrong-paste/docs/rubrica-v1.md`
- Create: `~/Documents/repos/personal-website/docs/superpowers/specs/<fecha-de-la-tirada>-pegado-accidental-fase-0-resultados.md`

**Interfaces:**
- Consumes: `run_phase0.measure_axis`, `run_phase0.main`, `artifacts.entity_hits`.
- Produces: la rúbrica que la Fase 1 necesita como entrada. **Sin esto, la Fase 1 no se puede planificar.**

- [ ] **Step 1: Medir el ancho del eje ANTES de gastar (D12)**

Este paso va primero, no después. Cuesta céntimos —una tanda de embeddings y los ocho prefijos cortos, que además quedan persistidos y los reutiliza la tirada— y es lo que impide gastar el presupuesto en un eje que no separa.

```bash
cd ~/Documents/repos/llm-wrong-paste
uv run python -c "
import json
from wrongpaste.run_phase0 import axis_path, measure_axis
axis = measure_axis(run_id='preflight')
axis_path('preflight').parent.mkdir(parents=True, exist_ok=True)
axis_path('preflight').write_text(
    json.dumps(axis, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
)
print('temas estrechos:', axis['narrow_topics'])
"
```

Criterio: **ningún tema por debajo de `NARROW_RANGE = 0,15` de rango, y ninguna cola alta vacía de dominio.** Si algún tema falla, se completa el banco con artefactos de portapapeles plausibles que rocen ese dominio **sin estar escritos como distractores**, y se vuelve a medir. Sospechosos comprobados: `viaje-japon`, `elegir-camara` y `mudanza` no tienen hoy ningún artefacto de su dominio en el banco.

El rango observado por tema **entra como criterio explícito del GO/NO-GO** del Step 8.

Aquí también se cierra el pendiente de D17: decidir si `GATEWAY_URL` y `GCP_PROJECT` se quedan en `config.py` o pasan a variables de entorno antes de la primera tirada. Es material de trabajo interno en un repo público.

- [ ] **Step 2: Estimar antes de gastar**

Contar celdas (27: 24 con pegote y 3 de control), multiplicar por turnos y por el precio del modelo, y **decir en voz alta el tiempo y el coste partidos por proveedor** antes de lanzar. Referencia del spec: ≈4 $ y unas 2 h, más el ~20 % que añaden los dos turnos posteriores de D7. Los prefijos se pagan una sola vez para los tres modelos (D1), lo que abarata la tirada respecto al diseño anterior. Si la estimación se dispara por encima de 10 $, parar y revisar.

- [ ] **Step 3: Lanzar la Fase 0**

Requiere VPN activa y `gcloud auth login` vigente.

```bash
cd ~/Documents/repos/llm-wrong-paste
uv run python -m wrongpaste.run_phase0
```

Si se corta a mitad, **no se relanza de cero**: se reanuda sobre el mismo fichero, que se salta las celdas ya escritas (D6).

```bash
uv run python -c "
from wrongpaste.run_phase0 import main
print(main(out='runs/phase0/<fichero>.jsonl'))
"
```

Al acabar, mirar `summary-<run_id>.json` antes que nada: planificadas 27, completadas, fallidas, saltadas y géneros cubiertos. **Las filas fallidas son datos**: si se concentran en las conversaciones de 10 turnos o en los estratos altos, eso se dice en los resultados, porque es exactamente el sesgo que D6 anticipaba.

- [ ] **Step 4: Comprobar el caché de prefijo con el criterio de D10**

El criterio no es "que haya alguna lectura de caché". Es: **dos celdas que comparten `prefix_id` deben mostrar `cache_read > 0` en la llamada del pegote**, y se mira desglosado por proveedor. Mezclar las lecturas de dentro de una conversación con las de entre celdas daría verde validando algo que no es el ahorro que la Fase 1 necesita.

```bash
uv run python -c "
import json, pathlib
from collections import defaultdict
from wrongpaste import config

p = sorted(pathlib.Path('runs/phase0').glob('*.jsonl'))[-1]
rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
rows = [r for r in rows if r.get('kind') != 'run_header' and r['condition'] == 'paste']

def cache_read(usage):
    return int(
        usage.get('cache_read_input_tokens')
        or usage.get('prompt_tokens_details', {}).get('cached_tokens', 0)
        or 0
    )

por_prefijo = defaultdict(list)
for r in rows:
    por_prefijo[r['prefix_id']].append(r)

for pid, grupo in sorted(por_prefijo.items()):
    if len(grupo) < 2:
        continue
    # La primera celda del prefijo escribe caché; las siguientes deben leerlo.
    for r in sorted(grupo, key=lambda r: r['cell_index'])[1:]:
        prov = config.MODELS[r['model_id']].provider
        leido = cache_read(r['usages'][0]) if r['usages'] else 0
        print(f\"{pid}  {prov:<16} {r['model_id']:<18} cache_read={leido}\")
"
```

Interpretación: si `vertex_anthropic` sale a cero, el breakpoint de D10 no está llegando y hay que arreglarlo **antes** de la Fase 1, donde el caché es la diferencia entre 20 $ y bastante más. Si los cero se concentran en el brazo de 2 turnos, la explicación probable es el mínimo de tokens que cada proveedor exige para cachear: mirar entonces las celdas de 10 turnos antes de tocar nada.

- [ ] **Step 5: Contar entidades sobre los prefijos pre-pegote (D8)**

Toda entity del banco que aparezca en la conversación **antes** del pegote es ruido de base: la métrica de fuga de la Fase 2 la contaría como si el modelo la hubiera arrastrado del pegote. Hay que sustituirla en el banco antes de la Fase 2. Sospechosas conocidas: `45 minutos`, `12 horas de fermentación en frío`.

```bash
uv run python -c "
import json, pathlib
from collections import Counter
from wrongpaste.artifacts import entity_hits, load_artifacts

p = sorted(pathlib.Path('runs/phase0').glob('*.jsonl'))[-1]
rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
rows = [r for r in rows if r.get('kind') != 'run_header']
todas = [e for a in load_artifacts() for e in a.entities]

ruido = Counter()
for r in rows:
    corte = r['paste_index'] if r['paste_index'] is not None else len(r['transcript'])
    previo = '\n'.join(m['content'] for m in r['transcript'][:corte])
    for e in entity_hits(previo, todas):
        ruido[e] += 1

print('entities que ya aparecen antes del pegote:')
for e, n in ruido.most_common():
    print(f'{n:>3}  {e}')
"
```

- [ ] **Step 6: Pilotar el recuento de fuga en los turnos posteriores (D7)**

Los dos turnos de después existen para dos cosas: separar "pivota en silencio" de "puente confabulado" al leer, y **pilotar ya la segunda métrica de la Fase 2** en vez de comprometer el grueso del presupuesto sin haberla probado nunca. Sobre las 24 conversaciones con pegote, contar cuántas entidades del artefacto reaparecen en las respuestas del asistente posteriores a la reacción (`post_indices`), descontando el ruido de base del Step 5.

- [ ] **Step 7: Leer las 27 transcripciones a mano**

Enteras, no en diagonal, y las tres de control también. Para cada una, anotar qué hizo el modelo con el pegote, con qué palabras, y si encaja en alguna de las cinco categorías previas del spec §5.

Las anotaciones van a `runs/phase0/annotations-<run_id>.jsonl` con el formato de **D14**, una línea por conversación anotada:

```json
{"conversation_id": "p0-claude-opus-5-hacer-pan-10-r0", "annotator": "javier", "category_guess": "puente_confabulado", "quote": "Entiendo que el log tiene que ver con la fermentación…", "notes": "no pregunta; enlaza el stacktrace con el horno en la primera frase"}
```

Es el **único conjunto etiquetado a mano que va a existir**, y el que semilla el acuerdo juez-humano del spec §6. Va al commit.

Preguntas que la lectura debe contestar:
- ¿Aparecen conductas que no están en las cinco categorías? En particular, ¿algún modelo **ejecuta** un artefacto de tipo `prompt`? Esa sería la sexta conducta que D4 obliga a poder ver.
- ¿Alguna categoría no aparece nunca, o hay que partirla en dos?
- ¿Se separan "pivota en silencio" y "puente confabulado" en el turno +1, como supone D7?
- ¿El usuario simulado suena a persona? (riesgo declarado en §12 del spec). El prefijo pre-pegote de cada conversación ya es exactamente ese material: no hace falta el brazo de control para juzgarlo.
- ¿Hay ya señal visible de que la similaridad importe — y de que no sea solo el cambio de registro? (ver *Limitaciones declaradas*, D15).

- [ ] **Step 8: Escribir la rúbrica v1**

`docs/rubrica-v1.md`: las categorías finales, cada una con definición, **dos ejemplos literales de las transcripciones** y el criterio de desempate frente a la categoría vecina. Esto es lo que se le pasa al juez-LLM en la Fase 1.

- [ ] **Step 9: Escribir el documento de resultados de Fase 0**

En el repo del blog, siguiendo el formato de `2026-08-14-fase-0-resultados.md`: qué se corrió, qué se leyó, qué categorías sobrevivieron, coste real frente a estimado, y **decisión GO/NO-GO explícita** sobre seguir a la Fase 1.

El GO/NO-GO se apoya en criterios que ya están medidos, no en impresiones:

1. **Ancho del eje (D12)**: rango de coseno por tema ≥ 0,15 y cola alta no vacía, en los ocho temas. Si no, completar el banco es un prerrequisito, no una mejora opcional.
2. **Integridad de la tirada (D6)**: celdas fallidas y **cómo se reparten** entre longitudes, estratos y proveedores.
3. **Cobertura de género (D4)**: los once `kind` vistos al menos una vez, `prompt` incluido.
4. **Caché (D10)**: lectura de caché confirmada por proveedor entre celdas que comparten prefijo.
5. **Ruido de base de entidades (D8)**: lista de entities a sustituir antes de la Fase 2.
6. **Rúbrica**: categorías estables, con ejemplos, y desempates escritos.

- [ ] **Step 10: Commit en los dos repos**

```bash
cd ~/Documents/repos/llm-wrong-paste
git add runs/prefixes runs/phase0 docs/rubrica-v1.md
git commit -m "data: Fase 0 — 27 conversaciones, anotaciones a mano y rúbrica v1"

cd ~/Documents/repos/personal-website
git add docs/superpowers/specs/*fase-0-resultados.md
git commit -m "docs: resultados de la Fase 0 y decisión GO/NO-GO"
```

---

## Limitaciones declaradas

Van al artículo tal cual. No son deuda pendiente: son el precio de decisiones tomadas a sabiendas.

**Colinealidad entre registro y similaridad (D15).** Los ocho temas son domésticos, y buena parte del banco es de registro técnico: 8 `stacktrace`, 5 `sql`, 5 `config` y 5 `changelog` — 23 de 64 — más los 5 `prompt`. Esos caerán sistemáticamente en los estratos bajos **para todos los temas**. Es decir: "similaridad semántica baja" y "cambio de registro" son **colineales por construcción**. Un modelo que señala un stacktrace en una charla sobre pan puede estar reaccionando al registro, no a la distancia semántica, y este diseño no los separa. No se puede eliminar sin rehacer el banco entero; se **mide** —`artifact_kind` va en cada fila, y por eso está ahí— y se **declara** como límite de la interpretación. Es la forma concreta del riesgo que el spec §12 ya anticipaba. (El documento de correcciones cifró en 26 los artefactos de registro técnico; el recuento del banco tal y como quedó da 23 más 5 `prompt`. La sustancia no cambia.)

**El modelo evaluado no reacciona a sus propias palabras (coste de D1).** El prefijo lo fabrica siempre `gpt-5.6-terra-tst`, así que cuando Opus 5 recibe el pegote está reaccionando a una conversación que sostuvo otro modelo. Es menos natural que el caso real, donde el usuario pega dentro de una conversación que el propio modelo ha ido construyendo. Se acepta a cambio de que el eje x sea **idéntico entre modelos**, que es la única forma de que las curvas del spec §9 sean comparables entre sí. Un diseño que dejara a cada modelo fabricar su prefijo mediría dos cosas a la vez y no sabría separarlas.

**El pegote no va precedido de nada del usuario.** Se inyecta literal, sin preámbulo (spec §4.1). Es lo que hace que el experimento sea sobre el accidente y no sobre una petición mal formulada, pero también significa que no se está midiendo el caso —también real— de "pego esto y escribo una línea encima".

## Lo que este plan NO cubre, y por qué

- **Fase 1 y Fase 2 no tienen tareas aquí.** Su diseño depende de la rúbrica que produce la Task 8. Escribirlas ahora sería inventarse nombres de categorías que van a cambiar. Se planifican en un documento aparte cuando exista `rubrica-v1.md`.
- **Fase 3 no existe todavía**, por decisión del spec §8.
- **Los brazos (b), (c) y (d) de reparación** del spec §7 no se corren en Fase 0: el campo `arm` existe y vale siempre `"a"`. La Fase 0 pilota solo la variante sin reparación (D7).

## Prerrequisitos pendientes para la Fase 1

Se resuelven **antes** de planificar la Fase 1, no durante.

- **El juez no puede estar entre los evaluados.** El spec §4.2 lo exige, y ahora mismo la key `blog-paste-experiment` da acceso exactamente al conjunto evaluado.
  - *Opción recomendada*: añadir `gpt-5.5-tst` a la key. Ya está registrado en el gateway y no forma parte del plantel, así que sirve de juez sin tocar el diseño.
  - *Alternativa*: usar `claude-sonnet-5` como juez y sacarlo del conjunto evaluado, a costa de perder el segundo Claude.
- **Incoherencia del plantel: 7 frente a 9 modelos (D16).** El §6 del spec presupuesta 2.688 = 384 × **7** modelos; el §9 lista **nueve** verificados, que son los que `config.py` registra; y la alternativa del punto anterior propone sacar a `claude-sonnet-5`, lo que dejaría ocho. Los tres números no pueden ser correctos a la vez. **Se resuelve al planificar la Fase 1**, junto con la decisión del juez, porque las dos cosas son la misma decisión mirada desde dos lados: cuántos modelos se evalúan y quién queda fuera para juzgar. Hasta entonces queda anotado aquí para que no se pierda.
- **Sustitución de las entities ruidosas** que salgan del Step 5 de la Task 8 (D8), antes de que la Fase 2 cuente fugas.
- **Completar el banco** en los temas que el informe de ejes marque como estrechos (D12).
