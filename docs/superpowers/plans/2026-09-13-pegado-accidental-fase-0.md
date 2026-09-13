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
- **La similaridad se mide sobre el lado del usuario (D2).** La primaria, `similarity_user`, se calcula contra la concatenación de apertura + turnos del usuario simulado: es corta, es independiente del modelo evaluado y es la definición correcta de "de qué va esta conversación". Se registra además `similarity_full` sobre la conversación entera, como secundaria, para poder ver si divergen. Guarda obligatoria antes de embeber: por encima de `MAX_EMBED_CHARS = 24_000` (≈6.000 tokens estimados, holgado frente a los 8.191 del embedder) se recorta **por el principio** conservando el final. El truncado se registra **desglosado por texto**: `similarity_user_truncated` (afecta al eje x, el que estratifica) y `similarity_full_truncated` (solo a la métrica secundaria). `similarity_text_truncated` sigue existiendo en la fila como columna derivada —el OR de los dos—, pero quien decida si una fila sirve para el eje x mira el primero: en la práctica el único texto que se pasa de los 24.000 caracteres es el completo, y colapsarlos obligaba a tirar filas perfectamente buenas.
- **Muestreo explícito donde el proveedor lo admite (D9 corregida).** `temperature = 1.0` va escrita en el cuerpo del gateway y en el de Vertex-OpenAI, para no heredar defaults que ni coinciden entre proveedores ni están congelados. **En Claude no se manda ningún parámetro de muestreo**: en la familia Claude 5 `temperature`, `top_p` y `top_k` están eliminados y devuelven 400, exactamente igual que `budget_tokens`. El cuerpo de Claude lleva solo `thinking: {"type": "adaptive"}` —sin él, Sonnet 5 correría sin razonamiento mientras Opus 5 lo lleva por defecto y los dos Claude dejarían de ser comparables— y el muestreo lo fija el proveedor, cosa que la fila refleja tal cual en `request_params`. La primera versión de D9 pedía temperatura explícita "en los tres cuerpos"; era un error que habría tumbado las ocho celdas de Claude, y hay un test de regresión que lo impide (`test_anthropic_body_nunca_manda_parametros_de_muestreo`). El cuerpo enviado, sin `messages`, se guarda en cada fila como `request_params`.
- **Los fallos son datos, no una caída (D6).** `chat()` reintenta 429 y 5xx tres veces con backoff exponencial; `main()` envuelve cada celda en `try/except` y **siempre** escribe fila, con `status ∈ ok | http_error | timeout | refusal | empty` más `error_code`, `error_body` y `attempts`; la tirada se reanuda sobre un fichero a medias saltando las celdas **ya hechas**, que son las de `status` en `DONE_STATUSES = {ok, refusal}` — una celda muerta por un 429 transitorio se reintenta, porque si no el hueco se queda justo en la zona interesante. Un JSONL de 19 filas sin marcas es indistinguible de uno completo, y el sesgo de las que faltan es predecible: fallan más las conversaciones largas y los pegotes de coseno alto. **Que un modelo se niegue a responder al pegote es un resultado**, no un error, y por eso `refusal` cuenta como celda hecha.
- **Claude va por `global`**: `https://aiplatform.googleapis.com/v1/projects/{p}/locations/global/publishers/anthropic/models/{m}:rawPredict`. En `us-central1` la cuota está a cero y devuelve 429.
- **Gemini va por OpenAI-compat de `us-central1`**: `https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{p}/locations/us-central1/endpoints/openapi/chat/completions`, modelo `google/{m}`.
- **Proyecto GCP**: sale de la variable de entorno `WRONGPASTE_GCP_PROJECT` (ver D17, aquí abajo). Cabecera `x-goog-user-project` obligatoria.
- **Prefill de turno de asistente está eliminado** en la familia Claude 5. El arnés no puede apoyarse en él.
- **Repo público (D17), ya resuelto.** `runs/` se versiona. Cada fila lleva el alias interno (`model_id`) y la etiqueta pública (`model_label`). El endpoint del gateway y el proyecto de GCP **no se versionan**: se leen de `WRONGPASTE_GATEWAY_URL` y `WRONGPASTE_GCP_PROJECT`, **sin valor por defecto** —cualquier default plausible publicaría justo lo que se quiere dejar fuera— y de forma **perezosa**, dentro de la función que necesita el valor, para que importar `config` funcione sin entorno y la suite offline corra en una máquina recién clonada. No son secretos, pero sí material de trabajo interno, y este repo de código es público porque los datos crudos son el producto. La decisión estaba pendiente "antes de la primera tirada"; se tomó al construir la Task 1 y este plan la refleja en el código de `config.py`.
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
- Produces: `Model(id: str, provider: str, label: str, tier: str)`, `MODELS: dict[str, Model]`, `gateway_url() -> str`, `gcp_project() -> str`, `EMBEDDING_MODEL: str`, `gateway_key() -> str`, `MissingConfig`, y los nombres de las variables de entorno `GATEWAY_URL_ENV` / `GCP_PROJECT_ENV` (D17).

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

Y los del repo público (D17), que son la mitad del fichero:

```python
def test_importar_config_sin_las_variables_no_reventar():
    # La lectura es perezosa: importar tiene que funcionar en una máquina
    # recién clonada, o la suite offline entera deja de correr.
    ...


def test_pedir_la_url_del_gateway_sin_variable_lanza_error_util(monkeypatch):
    monkeypatch.delenv(config.GATEWAY_URL_ENV, raising=False)
    with pytest.raises(config.MissingConfig) as exc:
        config.gateway_url()
    assert config.GATEWAY_URL_ENV in str(exc.value)


def test_una_variable_en_blanco_cuenta_como_ausente(monkeypatch):
    monkeypatch.setenv(config.GATEWAY_URL_ENV, "   ")
    with pytest.raises(config.MissingConfig):
        config.gateway_url()


def test_los_ajustes_se_releen_en_cada_llamada(monkeypatch):
    # Nada se congela al importar: si no, el valor quedaría pegado al primer
    # import y un cambio de entorno no se vería.
    ...


def test_los_nombres_en_mayusculas_siguen_resolviendo_desde_el_entorno(monkeypatch):
    # `config.GATEWAY_URL` y `config.GCP_PROJECT` siguen funcionando para los
    # usos que todavía los tratan como constantes (PEP 562, `__getattr__`).
    ...


def test_config_no_versiona_ningun_endpoint_interno():
    """El fichero es público: ni el host del gateway ni el proyecto de GCP."""
```

Más: `test_pedir_el_proyecto_gcp_sin_variable_lanza_error_util`,
`test_la_url_del_gateway_pierde_la_barra_final`,
`test_el_proyecto_gcp_sale_de_la_variable`,
`test_un_atributo_inexistente_sigue_siendo_attribute_error` y
`test_config_no_versiona_el_proyecto_ni_el_gateway_como_constante`.

El plantel son **nueve** modelos verificados. El §6 del spec presupuesta sobre siete y el prerrequisito del juez propone sacar a `claude-sonnet-5`: esa incoherencia es D16 y **se resuelve al planificar la Fase 1**, no aquí (ver *Prerrequisitos pendientes para la Fase 1*).

- [ ] **Step 3: Ejecutar el test y comprobar que falla**

```bash
cd ~/Documents/repos/llm-wrong-paste && uv venv && uv pip install -e ".[dev]"
uv run pytest tests/test_config.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.config'`.

- [ ] **Step 4: Implementar `config.py`**

El endpoint del gateway y el proyecto de GCP **no van escritos aquí** (D17): se leen del entorno, sin default y de forma perezosa.

```python
import os
from dataclasses import dataclass
from pathlib import Path

GATEWAY_URL_ENV = "WRONGPASTE_GATEWAY_URL"
GCP_PROJECT_ENV = "WRONGPASTE_GCP_PROJECT"

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


class MissingConfig(RuntimeError):
    """Falta un ajuste de entorno obligatorio para hablar con un proveedor."""


def _required_env(env_var: str, que_es: str) -> str:
    """Devuelve la variable de entorno, o explica cómo ponerla.

    El mensaje tiene que bastar para desatascarse sin leer el código: qué
    falta, para qué sirve y por qué no viene puesta de fábrica.
    """
    value = os.environ.get(env_var, "").strip()
    if not value:
        raise MissingConfig(
            f"Falta la variable de entorno {env_var} ({que_es}). "
            "No se versiona en este repositorio, que es público, así que hay "
            "que exportarla antes de cualquier llamada real:\n"
            f"    export {env_var}=...\n"
            "Los tests offline (`pytest -m \"not live\"`) no la necesitan."
        )
    return value


def gateway_url() -> str:
    """URL base del gateway LiteLLM, sin barra final."""
    return _required_env(GATEWAY_URL_ENV, "URL base del gateway LiteLLM").rstrip("/")


def gcp_project() -> str:
    """Identificador del proyecto de GCP donde vive Vertex AI."""
    return _required_env(GCP_PROJECT_ENV, "proyecto de GCP con Vertex AI habilitado")


def __getattr__(name: str) -> str:
    """Resuelve `config.GATEWAY_URL` y `config.GCP_PROJECT` de forma perezosa.

    PEP 562: Python solo llama aquí cuando el nombre **no** existe como global
    del módulo, así que estos dos se leen del entorno en el momento de usarlos
    —y fallan con el mensaje de `_required_env`— en vez de quedar congelados al
    importar. Es compatibilidad para los usos que todavía los tratan como
    constantes; lo que se debe llamar es `gateway_url()` y `gcp_project()`.
    """
    if name == "GATEWAY_URL":
        return gateway_url()
    if name == "GCP_PROJECT":
        return gcp_project()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def gateway_key() -> str:
    """Clave virtual del gateway, leída del fichero del desarrollador."""
    if not GATEWAY_KEY_PATH.exists():
        raise MissingConfig(
            f"No existe {GATEWAY_KEY_PATH}. Ahí va la clave virtual del "
            "gateway, en una sola línea y sin comillas."
        )
    return GATEWAY_KEY_PATH.read_text().strip()
```

`Model.label` no es decorativo: viaja a cada fila del JSONL como `model_label` junto al alias interno `model_id` (D17).

- [ ] **Step 5: Ejecutar el test y comprobar que pasa**

```bash
uv run pytest tests/test_config.py -v
```

Esperado: 17 passed.

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
- Consumes: `config.MODELS`, `config.gateway_key`, `config.gcp_project` (vía `config.GCP_PROJECT`), las tres URLs.
- Produces: `Reply(text, usage, raw, stop_reason, response_model, attempts, latency_ms)`, `chat(model_id, messages, max_tokens=1024, request_params_out=None) -> Reply`, `embed(texts) -> numpy.ndarray`, y las constantes `TEMPERATURE`, `MAX_ATTEMPTS`, `BACKOFF_BASE_SECONDS`, `POST_PREFIX_TAGS`.

`messages` usa siempre la forma OpenAI (`{"role": "user"|"assistant", "content": str}`), opcionalmente con el `tag` de D5 colgado de cada mensaje; la traducción al formato de Anthropic —y el saneado del `tag`, que los proveedores rechazan— ocurre dentro del cliente. Así el resto del arnés no sabe de proveedores.

Este fichero carga con cuatro decisiones a la vez: **D9** (temperature solo donde el proveedor la admite, thinking adaptive, nada de `budget_tokens` ni de muestreo en Claude), **D10** (`cache_control` al final del prefijo, localizado por `tag`), **D6** (reintentos, `stop_reason`, `attempts`) y **D5** (`response_model`, `request_params`).

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
def test_temperature_explicita_donde_el_proveedor_la_admite():
    # D9 corregida: nada de heredar el default de los proveedores que sí
    # aceptan muestreo explícito... y nada de mandárselo a los que no.
    msgs = [{"role": "user", "content": "x"}]
    assert _gateway_body("gpt-5.6-sol-tst", msgs, 32)["temperature"] == TEMPERATURE
    assert _vertex_openai_body("gemini-2.5-pro", msgs, 32)["temperature"] == TEMPERATURE
    assert TEMPERATURE == 1.0


def test_anthropic_body_nunca_manda_parametros_de_muestreo():
    # Regresión de la D9 original: en la familia Claude 5 `temperature`,
    # `top_p` y `top_k` están ELIMINADOS y devuelven 400. Mandarlos habría
    # tumbado las ocho celdas de Claude de la tirada.
    body = _anthropic_body([{"role": "user", "content": "x"}], max_tokens=32)
    for prohibido in ("temperature", "top_p", "top_k"):
        assert prohibido not in body


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

Y dónde acaba el prefijo, que **se decide por `tag` y no por posición** — esta es la parte que el plan anterior daba por trivial y no lo es:

```python
def test_breakpoint_con_turnos_post_no_cae_sobre_la_reaccion():
    """En los dos turnos `post` de D7 el último mensaje ya no es el pegote.

    Contar posiciones dejaría el breakpoint sobre la reacción al pegote —texto
    que cambia en cada celda— y ninguna celda leería caché de otra.
    """
    msgs = [
        {"role": "user", "content": "apertura", "tag": "opening"},
        {"role": "assistant", "content": "respuesta", "tag": "assistant"},
        {"role": "user", "content": "PEGOTE", "tag": "paste"},
        {"role": "assistant", "content": "reacción", "tag": "assistant"},
        {"role": "user", "content": "sigo a lo mío", "tag": "post"},
    ]
    enviados = _anthropic_body(msgs, max_tokens=32)["messages"]
    assert _cache_control_of(enviados[1]) == {"type": "ephemeral"}
    assert all(_cache_control_of(m) is None for m in enviados[2:])
```

Más, en la misma línea: `test_breakpoint_en_el_pegote_sigue_al_final_del_prefijo`,
`test_breakpoint_en_celda_de_control_sin_pegote` (D11: sin pegote, el
breakpoint sigue siendo el último `assistant` del prefijo),
`test_breakpoint_durante_la_construccion_del_prefijo`,
`test_breakpoint_sin_tags_degrada_al_penultimo_mensaje` (transcripciones
crudas: se asume que el último mensaje es el pegote, y quien llame así asume la
degradación), `test_breakpoint_sin_respuesta_de_asistente_en_el_prefijo`,
`test_los_tags_no_se_envian_a_ningun_proveedor` y
`test_marcar_el_prefijo_no_muta_la_transcripcion_etiquetada`.

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

# D9: muestreo explícito **donde el proveedor lo admite**. No se delega en el
# default de cada proveedor, que puede cambiar sin avisar y que no es el mismo
# en los tres. En Claude no se manda: ver `_anthropic_body`.
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

Los tres cuerpos, con `temperature` en los dos que la admiten (D9 corregida) y el breakpoint de caché en el de Anthropic (D10). Los tres sanean el `tag` de D5 con `_api_message`, porque los proveedores rechazan claves desconocidas dentro de `messages`:

```python
def _api_message(message: dict) -> dict:
    """Deja el mensaje como lo espera el proveedor: solo `role` y `content`.

    El transcript lleva además `tag` (D5), que es metadato nuestro. Sanear aquí
    permite pasarle a `chat()` la transcripción etiquetada, que es la única
    forma de que el breakpoint de caché sepa dónde acaba el prefijo.
    """
    return {"role": message["role"], "content": message["content"]}


def _gateway_body(model_id: str, messages: list[dict], max_tokens: int) -> dict:
    return {
        "model": model_id,
        "messages": [_api_message(m) for m in messages],
        "max_completion_tokens": max_tokens,
        "temperature": TEMPERATURE,
    }


def _vertex_openai_body(model_id: str, messages: list[dict], max_tokens: int) -> dict:
    return {
        "model": f"google/{model_id}",
        "messages": [_api_message(m) for m in messages],
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


# Etiquetas (D5) que marcan que el prefijo compartido ya se acabó: el primer
# mensaje con una de ellas es el pegote, la reparación o un turno posterior, y
# ninguno de los tres pertenece al prefijo que se sirve de caché (D10).
POST_PREFIX_TAGS: frozenset[str] = frozenset({"paste", "repair", "post"})


def _prefix_breakpoint_index(convo: list[dict]) -> int | None:
    """Índice del mensaje donde acaba el prefijo compartido, o `None`.

    Con etiquetas (el caso normal: todo lo que fabrica `conversation.py`), el
    prefijo acaba en el **último mensaje con `tag == "assistant"` anterior al
    primer mensaje etiquetado con `POST_PREFIX_TAGS`**. No se supone ninguna
    posición: en la llamada del pegote ese mensaje es el penúltimo, pero en los
    dos turnos `post` de D7 y en las celdas de control de D11 el último mensaje
    es un turno de usuario posterior, y contar posiciones dejaría el breakpoint
    sobre la reacción al pegote —texto que cambia de celda en celda y que por
    tanto no se puede cachear entre celdas que comparten `prefix_id`.

    Sin etiquetas (llamada suelta, transcripciones crudas) no hay forma de
    saber dónde acaba el prefijo: se **degrada** a marcar el penúltimo mensaje,
    que es lo correcto solo si el último es el pegote.
    """
    if not any(message.get("tag") for message in convo):
        return len(convo) - 2 if len(convo) >= 2 else None

    boundary = len(convo)
    for index, message in enumerate(convo):
        if message.get("tag") in POST_PREFIX_TAGS:
            boundary = index
            break

    for index in range(boundary - 1, -1, -1):
        if convo[index].get("tag") == "assistant":
            return index
    # Prefijo sin ninguna respuesta del asistente: no hay nada estable que
    # cachear delante del pegote.
    return None


def _mark_cacheable_prefix(convo: list[dict]) -> list[dict]:
    """Pone el breakpoint de caché al final del prefijo (D10).

    El prefijo —idéntico entre todas las celdas que comparten `prefix_id`— es
    lo que interesa servir de caché; lo que venga después (pegote, reacción,
    turnos `post`) cambia en cada celda. Dónde acaba lo decide
    `_prefix_breakpoint_index` a partir de las etiquetas, no de la posición.

    Devuelve una lista nueva, ya en forma de API (sin `tag`): no muta la
    transcripción del llamante, que se guarda tal cual en el JSONL.
    """
    marked = [_api_message(m) for m in convo]
    target_index = _prefix_breakpoint_index(convo)
    if target_index is None:
        return marked
    target = marked[target_index]
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
        # NO mandar `temperature` / `top_p` / `top_k`: en la familia Claude 5
        # los parámetros de muestreo están ELIMINADOS y devuelven 400, igual
        # que `budget_tokens`. La versión original de D9 pedía temperatura
        # explícita en los tres cuerpos; era un error y habría tumbado todas
        # las celdas de Claude. Aquí el muestreo lo fija el proveedor, y eso se
        # registra como tal en `request_params`.
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

Esperado: 30 passed.

- [ ] **Step 5: Ejecutar el smoke test con red**

Requiere VPN activa (el gateway resuelve a IP privada), `gcloud auth login` vigente y las dos variables de entorno de D17 exportadas (`WRONGPASTE_GATEWAY_URL`, `WRONGPASTE_GCP_PROJECT`); si faltan, `MissingConfig` dice cuál y cómo ponerla.

```bash
uv run pytest tests/test_smoke_live.py -v -m live
```

Esperado: 4 passed. Coste: céntimos. **Este es el momento de confirmar contra el proveedor que el cuerpo de Claude pasa con `thinking: adaptive` y sin ningún parámetro de muestreo** (D9 corregida): si algo devolviera 400, hay que verlo aquí y no a mitad de una tirada de dos horas.

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

El formato, con un artefacto **real del banco** copiado literalmente — `data/artifacts/recipe-pan-centeno.md`:

```markdown
---
id: recipe-pan-centeno
kind: recipe
entities: ["masa madre de centeno", "70 % de hidratación", "12 horas de fermentación en frío", "240 °C con vapor"]
---
Pan de centeno 60/40 — notas de la cuarta hornada.
400 g de harina de trigo panadero, 260 g de harina integral de centeno.
Autólisis de 45 minutos solo con harinas y agua, sin sal ni fermento.
Añadir 130 g de masa madre de centeno refrescada por la mañana y 13 g de sal.
Trabajar hasta 70 % de hidratación; con más, la miga de centeno se apelmaza
y el corte se cierra en el horno.
Tres pliegues cada 40 minutos en bloque, a 24 °C de temperatura ambiente.
Formar, cesto enharinado y 12 horas de fermentación en frío en la nevera baja.
Hornear directo de la nevera: 20 minutos a 240 °C con vapor, luego 25 minutos
a 210 °C sin vapor y con la puerta entreabierta los últimos cinco.
No cortarlo hasta el día siguiente. La hornada tres se cortó caliente y la miga
quedó gomosa.
```

Tres cosas que este ejemplo enseña y que hay que repetir en los 64:

- El frontmatter son tres claves planas (`id`, `kind`, `entities`) y `entities` es una lista JSON en una sola línea: así la parsea `_parse` sin dependencia de YAML.
- Las `entities` son términos **distintivos**: cantidades raras, nombres propios, identificadores. `12 horas de fermentación en frío` sirve; `45 minutos` no, y por eso está en el cuerpo pero **no** en `entities` — es la clase de entity de ruido de base que el Step 5 de la Task 9 va a cazar (D8).
- El artefacto está escrito como nota de portapapeles real, no como distractor del tema `hacer-pan`: el banco se escribe **antes** y sin mirar los temas (§4.1 del spec).

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

`rank_artifacts` ya no devuelve solo el ranking: devuelve también si hubo que recortar. El runner la llama **dos veces por prefijo** —una contra el lado del usuario y otra contra la conversación entera— y copia cada bandera a su campo de la fila: `similarity_user_truncated` y `similarity_full_truncated` (ver Task 6). Un truncado silencioso en el brazo de 10 turnos sería exactamente el fallo que D2 vino a cerrar.

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
  - `conversation`: `api_messages(transcript)`, `reply_traces(replies)`, `build_prefix(model_id, topic, n_turns, request_params_out=None) -> (transcript, usages, replies)`, `conversation_text(transcript)`, `inject_paste(model_id, transcript, artifact, request_params_out=None) -> (reacción, usage, paste_index, reply)`, `continue_after_paste(model_id, transcript, topic, n_post=2, request_params_out=None) -> (post_indices, usages, replies)`, `MAX_TOKENS`, `N_POST_TURNS`.
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
        "similarity_pct", "ranking",
        "similarity_user_truncated", "similarity_full_truncated",
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

Y el desglose del truncado de D2, que es lo que sustituye al booleano único:

```python
def test_los_dos_truncados_existen_por_separado_y_se_serializan():
    ...


@pytest.mark.parametrize(
    "user, full, esperado",
    [(False, False, False), (True, False, True), (False, True, True), (True, True, True)],
)
def test_similarity_text_truncated_es_el_or_de_los_dos(user, full, esperado):
    """El nombre viejo sobrevive como columna derivada, no como campo."""
    ...


def test_similarity_text_truncated_no_se_puede_asignar():
    ...


def test_el_nombre_viejo_sigue_aceptandose_en_el_constructor():
    """Un llamador sin migrar marca los DOS truncados y se lleva un aviso.

    El valor colapsado era un OR y un OR no se deshace: no hay forma de saber
    cuál de los dos textos se recortó, así que se marcan los dos (lado
    pesimista: una fila de más marcada como sospechosa, nunca una de menos sin
    marcar) y se emite `DeprecationWarning`.
    """
```

`tests/test_conversation.py` — etiquetas, turnos posteriores y trazabilidad, con dobles, sin red:

```python
def test_prefix_tags_opening_user_sim_and_assistant(monkeypatch):
    _stub(monkeypatch)
    transcript, _, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=3)

    assert [m["tag"] for m in transcript] == [
        "opening", "assistant", "user_sim", "assistant", "user_sim", "assistant",
    ]


def test_chat_never_sees_the_tag_field(monkeypatch):
    seen: list[list[dict]] = []
    _stub(monkeypatch, seen=seen)

    transcript, _, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=2)
    conv.inject_paste("gpt-5.6-luna-tst", transcript, ART)
    conv.continue_after_paste("gpt-5.6-luna-tst", transcript, TOPIC)

    assert seen, "el stub tiene que haber visto llamadas"
    for messages in seen:
        for m in messages:
            assert set(m) == {"role", "content"}


def test_continue_after_paste_adds_four_messages(monkeypatch):
    _stub(monkeypatch)
    transcript, _, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=2)
    conv.inject_paste("gpt-5.6-luna-tst", transcript, ART)
    before = len(transcript)

    post_indices, usages, replies = conv.continue_after_paste(
        "gpt-5.6-luna-tst", transcript, TOPIC
    )

    assert len(transcript) - before == 4
    assert len(usages) == len(replies) == 2
    assert post_indices == [before, before + 1, before + 2, before + 3]


def test_continue_after_paste_never_repairs(monkeypatch):
    """La variante (a) del spec §7: nadie menciona el pegote por el usuario."""
    _stub(monkeypatch)
    transcript, _, _ = conv.build_prefix("gpt-5.6-luna-tst", TOPIC, n_turns=2)
    conv.inject_paste("gpt-5.6-luna-tst", transcript, ART)
    conv.continue_after_paste("gpt-5.6-luna-tst", transcript, TOPIC)

    assert all(m["tag"] != "repair" for m in transcript)
```

Y la trazabilidad de D5/D6, que es lo que hace que la fila no salga vacía de datos del proveedor:

```python
def test_la_trazabilidad_llega_entera_de_extremo_a_extremo(monkeypatch):
    """`stop_reason`, `response_model`, `attempts` y `latency_ms` por llamada.

    Sin devolver los `Reply`, las 27 filas salían con `stop_reasons=[]`,
    `response_model=""` y `attempts=1`: la fila afirmaba que ninguna llamada
    había reintentado nunca.
    """


def test_build_prefix_solo_cuenta_las_llamadas_al_modelo_evaluado(monkeypatch):
    """Los turnos del usuario simulado los paga otro modelo: no son trazas."""


def test_las_tres_funciones_ceden_request_params_out_a_chat(monkeypatch):
    """D9: el cuerpo enviado tiene que poder llegar a la fila desde cualquiera."""
```

Más: que el prefijo alterne roles y acabe en `assistant` (Claude lo exige), que solo el primer mensaje lleve `opening`, que el pegote vaya literal y sin preámbulo, que `inject_paste` etiquete `paste` y devuelva el índice **y el `Reply` de la llamada del pegote** (que es la que decide la conducta que mide el experimento), que los `post_indices` apunten a mensajes posteriores a la reacción, que `reply_traces` dé exactamente las columnas que espera la fila y aguante un `Reply` sin trazas, y que sin `request_params_out` no se le pase ningún dict a `chat`.

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

`ConversationRecord` lleva **todos** los campos con valor por defecto, para que las celdas de control (D11, sin artefacto) y las fallidas (D6, sin reacción) se puedan construir sin inventar datos. Los bloques, en orden: identidad (D5) · modelo evaluado con `model_id` + `model_label` + `response_model` (D17) · celda del diseño con `stratum`, `n_strata` y `prefix_id` (D3, D1) · brazo con `condition`, `arm` y `parent_id` (D11, spec §7) · artefacto opcional con `artifact_kind` para poder medir la colinealidad de D15 · similaridades `similarity_user` y `similarity_full` más rango, percentil, `ranking` completo y los **dos** truncados por separado, `similarity_user_truncated` y `similarity_full_truncated` (D2) · transcripción con `paste_index` y `post_indices` (D5, D7) · lo enviado, con `request_params`, `system_prompt`, `prefix_model` y `stop_reasons` (D9, spec §4.2) · reloj · resultado con `status`, `error_code`, `error_body` y `attempts` (D6).

El booleano colapsado de antes, `similarity_text_truncated`, **ya no es un campo**: es una propiedad derivada (el OR de los dos) que `to_json()` sigue escribiendo como columna, más un `InitVar` que lo acepta en el constructor marcando los dos truncados y avisando con `DeprecationWarning`. Quien decida si una fila sirve para el eje x mira `similarity_user_truncated`; la columna derivada no distingue cuál de los dos textos se recortó, y en la práctica el que se pasa de los 24.000 caracteres es siempre el completo.

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


def reply_traces(replies: list[Reply]) -> list[dict]:
    """Los campos de trazabilidad de cada `Reply`, listos para el JSONL (D5).

    Un dict por llamada al modelo evaluado, en orden, con `stop_reason`,
    `response_model`, `attempts` y `latency_ms`. Existe para que el runner no
    tenga que conocer el dataclass ni repetir el mismo bucle en tres sitios:
    `Reply` no es serializable tal cual (lleva `raw`, la respuesta entera).
    """
    return [
        {
            "stop_reason": r.stop_reason,
            "response_model": r.response_model,
            "attempts": r.attempts,
            "latency_ms": r.latency_ms,
        }
        for r in replies
    ]


def build_prefix(
    model_id: str,
    topic: Topic,
    n_turns: int,
    request_params_out: dict | None = None,
) -> tuple[list[dict], list[dict], list[Reply]]:
    """Conduce n_turns de conversación normal sobre el tema.

    Devuelve la transcripción (siempre terminada en assistant, que es lo que
    Claude exige para poder continuar), los `usage` de cada llamada y los
    `Reply` completos de esas mismas llamadas, en el mismo orden: sin ellos las
    filas saldrían con `stop_reasons=[]`, `response_model=""` y `attempts=1`
    aunque hubiera habido reintentos (D5/D6).

    `request_params_out`, si se pasa, se le cede a `chat()`, que lo rellena con
    el cuerpo enviado sin `messages` (D9). Queda con el de la **última**
    llamada, que es representativo porque todas las de una celda van al mismo
    modelo con el mismo `max_tokens`.

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
    replies: list[Reply] = []

    reply = chat(
        model_id,
        api_messages(transcript),
        max_tokens=MAX_TOKENS,
        request_params_out=request_params_out,
    )
    transcript.append({"role": "assistant", "content": reply.text, "tag": "assistant"})
    usages.append(reply.usage)
    replies.append(reply)

    for _ in range(n_turns - 1):
        transcript.append(
            {
                "role": "user",
                "content": next_user_turn(topic, transcript),
                "tag": "user_sim",
            }
        )
        reply = chat(
            model_id,
            api_messages(transcript),
            max_tokens=MAX_TOKENS,
            request_params_out=request_params_out,
        )
        transcript.append(
            {"role": "assistant", "content": reply.text, "tag": "assistant"}
        )
        usages.append(reply.usage)
        replies.append(reply)

    return transcript, usages, replies


def conversation_text(transcript: list[dict]) -> str:
    """La conversación entera como texto (similaridad secundaria, D2)."""
    return "\n".join(m["content"] for m in transcript)


def inject_paste(
    model_id: str,
    transcript: list[dict],
    artifact: Artifact,
    request_params_out: dict | None = None,
) -> tuple[str, dict, int, Reply]:
    """Añade el pegote TAL CUAL, sin preámbulo ni envoltorio, y pide respuesta.

    Muta `transcript` in place: el registro guarda la conversación completa.

    Devuelve (reacción, usage, índice del mensaje del pegote, `Reply`). El
    índice va al campo `paste_index` de la fila (D5): sin él, el análisis
    tendría que volver a localizar el pegote comparando textos. El `Reply` es el
    de **la llamada del pegote**, que es la que decide la conducta que mide el
    experimento: si un modelo se corta por `max_tokens` en vez de terminar, la
    fila tiene que decirlo (D6).
    """
    paste_index = len(transcript)
    transcript.append({"role": "user", "content": artifact.text, "tag": "paste"})
    reply = chat(
        model_id,
        api_messages(transcript),
        max_tokens=MAX_TOKENS,
        request_params_out=request_params_out,
    )
    transcript.append({"role": "assistant", "content": reply.text, "tag": "assistant"})
    return reply.text, reply.usage, paste_index, reply


def continue_after_paste(
    model_id: str,
    transcript: list[dict],
    topic: Topic,
    n_post: int = N_POST_TURNS,
    request_params_out: dict | None = None,
) -> tuple[list[int], list[dict], list[Reply]]:
    """Dos turnos más con el usuario simulado, SIN reparación (D7).

    Es la variante (a) del spec §7: el usuario sigue a lo suyo como si el
    pegote no existiera. Sirve para separar "pivota en silencio" de "puente
    confabulado" — que a menudo solo se distinguen en el turno +1 — y para
    pilotar ya el recuento de entidades de la Fase 2.

    Muta `transcript` in place. El mensaje de usuario se etiqueta `post` y la
    respuesta `assistant`.

    Devuelve (post_indices, usages, replies). `post_indices` son los índices de
    **todos** los mensajes añadidos aquí, usuario y asistente, en orden: el
    recuento de fuga de entidades se hace sobre las respuestas, así que dejarlas
    fuera obligaría al análisis a recalcular posiciones. `replies` son los
    `Reply` completos de los `n_post` turnos del modelo evaluado, con la misma
    trazabilidad que los demás (D5/D6).
    """
    post_indices: list[int] = []
    usages: list[dict] = []
    replies: list[Reply] = []

    for _ in range(n_post):
        post_indices.append(len(transcript))
        transcript.append(
            {
                "role": "user",
                "content": next_user_turn(topic, transcript),
                "tag": "post",
            }
        )
        reply = chat(
            model_id,
            api_messages(transcript),
            max_tokens=MAX_TOKENS,
            request_params_out=request_params_out,
        )
        post_indices.append(len(transcript))
        transcript.append(
            {"role": "assistant", "content": reply.text, "tag": "assistant"}
        )
        usages.append(reply.usage)
        replies.append(reply)

    return post_indices, usages, replies
```

`tag` es metadato nuestro, no del protocolo: **todas** las llamadas pasan hoy por `api_messages()`, porque los proveedores rechazan campos desconocidos dentro de `messages`.

**Pendiente conocido, y hay que resolverlo antes de fiarse del ahorro de caché.** `clients._prefix_breakpoint_index` localiza el final del prefijo **por `tag`** (Task 2), y `clients._api_message` ya sanea el `tag` dentro de cada cuerpo; pero `conversation.py` llama a `chat()` con `api_messages(transcript)`, que quita las etiquetas **antes**. Con lo cual el cliente nunca las ve y siempre cae en la rama degradada: marcar el penúltimo mensaje. Eso es correcto en la llamada del pegote y **no lo es** en los dos turnos `post` de D7 ni en las celdas de control de D11, donde el breakpoint acaba sobre la reacción —texto que cambia en cada celda y que por tanto no se cachea entre celdas. La sonda de caché de D10 (Task 7) lo mide sobre la llamada del pegote, así que puede salir en verde sin que esto esté arreglado. Arreglo: pasarle a `chat()` la transcripción etiquetada, que es justo lo que `_api_message` permite.

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
    transcript, usages, _ = build_prefix(PREFIX_MODEL, topic, n_turns)
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

**Defecto abierto en `prefixes.py`, a cerrar antes de la primera llamada real.** El fichero tal y como está hoy escribe `transcript, usages = build_prefix(...)`, con dos nombres para la tupla de **tres** que `build_prefix` devuelve desde que lleva los `Reply`. Eso levanta `ValueError` en cuanto se genera el primer prefijo de verdad; la suite offline no lo ve porque `tests/test_prefixes.py` dobla `build_prefix`. El arreglo es la línea de arriba (`transcript, usages, _ = ...`), y conviene además que el doble del test devuelva una tupla de tres, que es lo que habría cazado esto.

- [ ] **Step 4: Ejecutar los tests y comprobar que pasan**

```bash
uv run pytest tests/test_records.py tests/test_conversation.py tests/test_prefixes.py -v
```

Esperado: 62 passed (27 + 23 + 12).

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
- Produces: `plan_phase0(seed) -> list[dict]`, `stratum_window(ranked, stratum, n_strata)`, `pick_artifact(ranked, stratum, kind_counts, rng, n_strata)`, `measure_axis(topics, arts, lengths, run_id) -> dict`, `probe_cache(...) -> dict`, `bank_sha`, `topics_sha`, `code_sha`, `resume_state(path)`, `read_run_header(path)`, `is_resumable(path)`, `looks_like_content_filter(body)`, `status_for_stop_reasons(stop_reasons)`, `rank_for_prefix(...)`, `run_cell(...)`, `failed_record(...)`, `build_header(...)`, `main(seed, out=None, measure=True)`, y las rutas laterales `axis_path`, `summary_path`, `cache_probe_path`. `main` escribe `runs/phase0/<timestamp>.jsonl`, `axis-<run_id>.json` y `summary-<run_id>.json`; `probe_cache` escribe `cache-probe-<run_id>.json`.

Este fichero es donde aterrizan siete decisiones:

- **D3 — rotación de ejes.** El estrato va *en el plan*, como `(t + 2·m) % 8` sobre el índice de tema y el de modelo, y la longitud alterna como `LENGTHS[(t + m) % 2]`. **El coeficiente tiene que ser par.** Antes, `LENGTHS[i % 2]` sobre el índice de tema y `stratum = i % STRATA` sobre el índice global hacían que estrato ≡ tema ≡ longitud: tres ejes que eran el mismo. La primera corrección de D3 puso `(t + 3·m) % 8`, que arregló estrato↔tema y **dejó intacto estrato↔longitud**: como `3m ≡ m (mod 2)`, la paridad del estrato era exactamente el índice de longitud, y los cuatro estratos pares caían siempre en conversaciones de 2 turnos y los impares siempre en las de 10. Cualquier coeficiente impar tiene ese problema, porque módulo 2 todos valen 1. Con coeficiente par la paridad del estrato depende solo de `t`, la longitud depende de `(t + m)`, y los dos ejes se separan; cada estrato sigue cayendo en tres temas distintos (`t = s, s−2, s−4`) y cada modelo sigue recorriendo los ocho estratos. El orden de ejecución es **round-robin de modelos dentro de cada tema**, no modelo-mayor: con dos horas de tirada contra un gateway compartido, modelo-mayor confunde el modelo con la hora de reloj.
- **D4 — cobertura de `kind`.** Dentro del estrato se elige el artefacto cuyo género esté menos representado hasta ese momento.
- **D5 — identidad.** Primera línea `run_header`; cada fila con `conversation_id` determinista y legible, más lo que se envió (`request_params`, `system_prompt`) y lo que contestó el proveedor (`response_model`, `stop_reasons`, `attempts`).
- **D6 — fallos como datos.** `try/except` por celda, fila siempre, reanudación que solo da por hechas las celdas con `status` en `DONE_STATUSES`, y resumen final.
- **D10 — sonda de caché.** `probe_cache()` repite dos veces la misma llamada contra un modelo de cada proveedor. Es el único sitio donde el criterio de D10 se puede comprobar de verdad; ver el Step 3d.
- **D11 — tres celdas de control** sin pegote, repartidas entre las dos longitudes y los tres modelos.
- **D12 — ancho del eje medido antes de gastar**, en **las dos longitudes**.

El prefijo **no** se construye aquí: viene de `prefixes.ensure_prefix` (D1).

- [ ] **Step 1: Escribir los tests que fallan**

`tests/test_run_phase0.py` no hace una sola llamada a un modelo: `ensure_prefix`, `rank_artifacts`, `inject_paste` y `continue_after_paste` se sustituyen por dobles deterministas en un fixture `harness` que además redirige `OUT_DIR` a `tmp_path`.

Rotación de ejes (D3). **El par de ejes que faltaba —estrato × longitud— es paso obligatorio**: sin él, la suite salía en verde certificando una rotación incompleta, y esa es la razón de que el fallo sobreviviera a una revisión.

```python
def test_the_stratum_step_is_even():
    """Un salto impar confunde estrato y longitud: 3·m ≡ m (mod 2)."""
    assert STRATUM_STEP % 2 == 0, (
        "con salto impar la paridad del estrato ES el índice de longitud"
    )


def test_every_stratum_crosses_both_lengths():
    """El test que faltaba (D3): estrato × longitud.

    Con `stratum = (t + 3·m) % 8` los ocho estratos existían, cada uno caía en
    tres temas... y los pares salían **siempre** en conversaciones de 2 turnos y
    los impares **siempre** en las de 10. Saber el estrato era saber la
    longitud, así que cualquier efecto de la similaridad y cualquier efecto de
    la longitud quedaban pegados sin forma de separarlos después.
    """
    plan = _paste_cells(plan_phase0(seed=1))
    per_stratum: dict[int, set[int]] = {}
    for cell in plan:
        per_stratum.setdefault(cell["stratum"], set()).add(cell["n_turns"])
    assert set(per_stratum) == set(range(STRATA))
    for stratum, lengths in sorted(per_stratum.items()):
        assert lengths == set(LENGTHS), (
            f"el estrato {stratum} solo aparece con n_turns={sorted(lengths)}: "
            "estrato y longitud están confundidos"
        )


def test_the_parity_of_the_stratum_does_not_determine_the_length():
    """La forma concreta en que fallaba la fórmula impar, escrita como test."""
    plan = _paste_cells(plan_phase0(seed=1))
    for parity in (0, 1):
        lengths = {c["n_turns"] for c in plan if c["stratum"] % 2 == parity}
        assert lengths == set(LENGTHS), (
            f"los estratos de paridad {parity} solo salen con {sorted(lengths)}"
        )


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


def test_every_model_walks_the_eight_strata():
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


def test_control_cells_cover_both_lengths():
    """Sin control corto, la tasa base no vale para la mitad de las celdas."""
    controls = _control_cells(plan_phase0(seed=1))
    assert {c["n_turns"] for c in controls} == set(LENGTHS)


def test_control_cells_spread_over_the_three_models():
    controls = _control_cells(plan_phase0(seed=1))
    assert {c["model_id"] for c in controls} == set(PHASE0_MODELS)


def test_control_cells_use_distinct_topics():
    controls = _control_cells(plan_phase0(seed=1))
    assert len({c["topic_id"] for c in controls}) == len(controls)


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

Ancho del eje (D12): `test_measure_axis_reports_min_median_and_max_per_topic_and_length`, `test_measure_axis_measures_both_lengths`, `test_measure_axis_with_one_length_reports_only_that_one`, `test_measure_axis_embeds_the_user_side_of_the_prefix`, `test_measure_axis_flags_a_narrow_topic` y `test_main_writes_the_axis_report_for_both_lengths`.

Sonda de caché (D10): `test_probe_cache_repeats_the_very_same_call_twice_per_model`, `test_probe_cache_reports_the_cache_read_of_each_call`, `test_probe_cache_fails_the_criterion_when_nothing_is_cached`, `test_probe_cache_records_a_failed_call_instead_of_dying`, `test_probe_cache_writes_its_report_next_to_the_run`, `test_probe_cache_defaults_to_one_model_per_provider` y `test_main_never_spends_money_on_the_cache_probe` (la sonda se lanza a mano; `main` no la llama).

Sobre la tirada (D5/D6/D7/D11): que la cabecera vaya primero; una fila por celda con identidad; dos turnos después del pegote; `post_indices` y `paste_index` en la fila; las filas de control sin artefacto ni similaridad; las de pegote con **las dos** similaridades y el ranking completo; que los tres modelos de un tema compartan prefijo y ranking; que la fila lleve los `request_params` que de verdad se enviaron, los `stop_reasons`, el `response_model` y los `attempts` —incluido `test_a_retried_turn_is_visible_in_the_row`—; que el `system_prompt` salga de lo enviado y en Fase 0 sea `None`; que los dos truncados se registren por separado y el runner no use el booleano colapsado; idempotencia y reanudación; que la reanudación mantenga la cobertura de géneros; que solo `ok` y `refusal` cuenten como hechas (`test_only_ok_and_refusal_count_as_done`, `test_a_cell_that_died_on_a_transient_error_is_retried_on_resume`, `test_a_row_without_status_is_treated_as_done`); que un fichero de salida vacío **no** sea una reanudación y que uno con filas pero sin cabecera no se reanude ni se pise; y que `resume_state` sobreviva a una última línea truncada.

Y una familia entera sobre lo que **no** es una negativa, porque clasificar un fallo del arnés como conducta del modelo contamina justo la variable que mide el experimento: `test_a_malformed_request_mentioning_content_is_not_a_refusal`, `test_a_non_json_body_with_the_word_content_is_not_a_refusal`, `test_an_openai_content_filter_is_a_refusal`, `test_a_nested_responsible_ai_violation_is_a_refusal`, `test_a_vertex_block_reason_is_a_refusal`, `test_a_server_error_is_never_a_refusal`, `test_the_body_is_analysed_whole_and_stored_truncated` y `test_stop_reasons_decide_a_refusal_without_an_http_error`.

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

# Salto de estrato entre modelos consecutivos (D3). **Par a propósito.** Con 8
# estratos, un salto par deja la paridad del estrato dependiendo solo del índice
# de tema, mientras la longitud depende de `(t + m)`: los dos ejes se separan.
# Cualquier salto impar (la versión original de D3 usaba 3) hace que la paridad
# del estrato sea exactamente el índice de longitud, porque módulo 2 todos los
# impares valen 1, y entonces los cuatro estratos pares caen siempre en
# conversaciones de 2 turnos y los impares siempre en las de 10.
STRATUM_STEP = 2

# D11: tres celdas sin pegote. No pretenden dar una tasa base creíble —eso es de
# la Fase 2—, sino demostrar que el formato, el runner y el verificador soportan
# el brazo de control. Se reparten entre las dos longitudes: un control que solo
# existe en conversaciones largas no sirve de tasa base para las cortas.
N_CONTROL_CELLS = 3

# D12: por debajo de este rango de coseno, el tema no separa nada y la
# estratificación es decorativa. Es criterio explícito del GO/NO-GO.
NARROW_RANGE = 0.15

# Cuántos artefactos de la cola alta se listan en el informe de ejes, para que
# quien lo lea pueda juzgar si la cola alta está vacía (D12).
AXIS_TOP_N = 3

MASTER_SEED = 20260913
OUT_DIR = Path(__file__).resolve().parents[2] / "runs" / "phase0"
REPO_ROOT = Path(__file__).resolve().parents[2]

# Rutas declaradas en la cabecera (D5). Viven en el repo del blog, no en este.
PLAN_PATH = "docs/superpowers/plans/2026-09-13-pegado-accidental-fase-0.md"
SPEC_PATH = "docs/superpowers/specs/2026-09-13-pegado-accidental-design.md"

# El system prompt del usuario simulado es privado de su módulo; se lee así para
# poder registrarlo en la cabecera sin tocar un fichero que no es de este.
USER_SYSTEM_PROMPT = getattr(simulated_user, "_SYSTEM", "")

# Cuánto del cuerpo de error se guarda en la fila cuando una celda falla (D6).
ERROR_BODY_CHARS = 2000

# D6: qué cuenta como celda hecha al reanudar. `ok` es el resultado normal y
# `refusal` es **un resultado** —que un modelo se niegue es conducta, no
# avería—, así que ninguno de los dos se repite. `http_error`, `timeout` y
# `empty` son averías del arnés o del proveedor: se vuelven a intentar, porque
# si no, una celda que murió por un 429 transitorio no se corre jamás y el hueco
# queda en la zona interesante del diseño (largas, cosenos altos).
DONE_STATUSES: frozenset[str] = frozenset({"ok", "refusal"})


def plan_phase0(seed: int) -> list[dict]:
    """Devuelve las celdas de la Fase 0, en el orden en que se van a correr.

    Con `t` el índice del tema y `m` el del modelo (D3)::

        stratum = (t + 2 * m) % 8
        n_turns = LENGTHS[(t + m) % 2]

    El estrato viaja **en el dict**: no se deriva del orden de iteración, que es
    precisamente lo que hacía que estrato, tema y longitud fueran el mismo eje.
    El coeficiente 2 no es intercambiable por cualquier otro: ver `STRATUM_STEP`.

    El bucle exterior es el tema y el interior el modelo, o sea round-robin de
    modelos: si el gateway se degrada a mitad de tirada, la degradación se
    reparte entre los tres modelos en vez de caer entera sobre el último.

    Al final se añaden las tres celdas de control sin pegote (D11). Cada una
    coge la longitud **contraria** a la de la celda con pegote de ese mismo
    (tema, modelo): así no genera ningún prefijo nuevo (cada tema se fabrica en
    las dos longitudes de todos modos) y su `conversation_id`, que lleva la
    longitud dentro, no puede chocar con el de la celda con pegote. Los tres
    (tema, modelo) se eligen con `t = 2·i` para que `t + m` cambie de paridad
    entre controles y los tres no acaben en la misma longitud.
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
        t = (2 * i) % len(topics)
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

Los ficheros laterales de una tirada (informe de ejes, resumen, sonda de caché) siguen **al fichero de salida** y no a `OUT_DIR`: si alguien corre la tirada con `out=/otro/sitio/tirada.jsonl`, el informe que explica los datos tiene que quedar al lado de los datos, y no huérfano —o peor, pisando el de otra tirada con el mismo `run_id`.

```python
def _sidecar_path(name: str, run_id: str, out: Path | str | None = None) -> Path:
    base = Path(out).parent if out is not None else OUT_DIR
    return base / f"{name}-{run_id}.json"


def axis_path(run_id, out=None):  # runs/phase0/axis-<run_id>.json
    return _sidecar_path("axis", run_id, out)


def summary_path(run_id, out=None):  # summary-<run_id>.json
    return _sidecar_path("summary", run_id, out)


def cache_probe_path(run_id, out=None):  # cache-probe-<run_id>.json
    return _sidecar_path("cache-probe", run_id, out)


def measure_axis(
    topics: list[Topic] | None = None,
    arts: list[Artifact] | None = None,
    lengths: Iterable[int] | int = tuple(LENGTHS),
    run_id: str = "",
) -> dict[str, Any]:
    """Embebe los prefijos contra el banco y mide el rango por (tema, longitud).

    Se corre **antes** de la tirada y cuesta céntimos. Sirve para no gastar el
    presupuesto en un eje que no separa: si un tema tiene un rango de coseno por
    debajo de `NARROW_RANGE`, o su cola alta está vacía, la estratificación de
    ese tema es decorativa y hay que completar el banco antes de seguir.

    Mide **las dos longitudes** por defecto. El ancho del eje es criterio
    GO/NO-GO (D12) y la mitad de las celdas corren sobre el prefijo largo: un
    prefijo de diez turnos habla de bastantes más cosas que uno de dos, así que
    su rango de cosenos no tiene por qué parecerse. Medir solo el corto
    certificaba media tirada sin haberla mirado.

    Usa los prefijos que `ensure_prefix` ya va a fabricar para la tirada (cada
    tema se construye en las dos longitudes): no genera trabajo extra, solo lo
    adelanta.

    Devuelve el informe (que `main` guarda en `axis-<run_id>.json`) y lo imprime
    por pantalla de camino.
    """
    topics = load_topics() if topics is None else topics
    arts = load_artifacts() if arts is None else arts
    lengths = [int(lengths)] if isinstance(lengths, int) else [int(n) for n in lengths]

    entries: list[dict[str, Any]] = []
    print(f"--- ancho del eje (D12): {len(arts)} artefactos, longitudes={lengths}")
    for topic in topics:
        for n_turns in lengths:
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
            entries.append(entry)
            print(
                f"  {topic.id:<16} n={n_turns:<3} min={entry['min']:.3f} "
                f"med={entry['median']:.3f} max={entry['max']:.3f} "
                f"rango={entry['range']:.3f}"
                + ("  <-- ESTRECHO" if entry["narrow"] else "")
            )

    narrow_cells = [
        {"topic_id": e["topic_id"], "n_turns": e["n_turns"]}
        for e in entries
        if e["narrow"]
    ]
    narrow_topics = sorted({c["topic_id"] for c in narrow_cells})
    if narrow_cells:
        detalle = ", ".join(f"{c['topic_id']}(n={c['n_turns']})" for c in narrow_cells)
        print(f"  OJO: rango < {NARROW_RANGE} en: {detalle}")

    return {
        "run_id": run_id,
        "embedding_model": config.EMBEDDING_MODEL,
        "prefix_model": PREFIX_MODEL,
        "lengths": lengths,
        "n_artifacts": len(arts),
        "narrow_threshold": NARROW_RANGE,
        "narrow_cells": narrow_cells,
        "narrow_topics": narrow_topics,
        "entries": entries,
    }
```

- [ ] **Step 3d: Sonda de caché (D10)**

**Por qué existe.** El criterio escrito de D10 es «dos celdas con el mismo `prefix_id` deben mostrar `cache_read > 0` en la llamada del pegote, desglosado por proveedor». Sobre el plan de la Fase 0 ese criterio **no se puede comprobar nunca**: cada (tema, longitud) tiene su propio `prefix_id` y los tres modelos que lo comparten son de proveedores distintos, así que no hay ninguna pareja de celdas del mismo proveedor con el mismo prefijo. Un chequeo que no puede fallar tampoco verifica nada.

`probe_cache()` monta prefijo + pegote una sola vez y manda **exactamente esa misma petición** dos veces a un modelo de cada proveedor. La primera llamada escribe la caché y la segunda tiene que leerla. Son cuatro llamadas de céntimos y responden la pregunta de verdad —¿el breakpoint está donde creemos y el proveedor lo respeta?— antes de presupuestar la Fase 1 contando con el ahorro.

```python
# Un modelo por proveedor: D10 se declara «desglosado por proveedor», y lo que
# cambia entre proveedores es justo el mecanismo (Claude necesita el
# `cache_control` explícito que pone `clients._mark_cacheable_prefix`; el
# gateway cachea el prefijo solo).
CACHE_PROBE_MODELS = ["claude-opus-5", "gpt-5.6-sol-tst"]

# Dos es el mínimo que responde a la pregunta: la primera escribe, la segunda lee.
CACHE_PROBE_REPEATS = 2


def _cache_read_tokens(usage: dict) -> int | None:
    """Tokens servidos de caché, o None si el proveedor no lo dice.

    Dos formas: Anthropic lo pone en `cache_read_input_tokens`, y los cuerpos
    estilo OpenAI en `usage.prompt_tokens_details.cached_tokens`.
    """


def probe_cache(
    models=None, topic=None, artifact=None, n_turns=LENGTHS[0],
    repeats=CACHE_PROBE_REPEATS, run_id="", out=None, write=True,
) -> dict[str, Any]:
    """Repite dos veces la misma llamada y reporta el `cache_read` de cada una.

    No la llama `main()`: se lanza a mano (`python -m wrongpaste.run_phase0
    probe-cache`) porque gasta dinero y su respuesta vale para toda la fase, no
    para una tirada. Una llamada que falle se registra como llamada fallida en
    vez de tumbar la sonda (D6).
    """
```

Cada entrada del informe lleva `model_id`, `model_label`, `provider`, las `calls` con su `usage`, la lista `cache_reads` y el veredicto:

```python
        after_first = [c["cache_read_input_tokens"] for c in calls[1:]]
        entry = {
            ...,
            # El criterio de D10, hecho comprobable: a partir de la segunda
            # llamada, el proveedor tiene que decir que ha leído caché.
            "criterion_met": bool(after_first)
            and all(value is not None and value > 0 for value in after_first),
        }
```

y el informe de arriba añade `by_provider` (`{proveedor: criterio}`) y un `criterion_met` global. Se escribe en `cache-probe-<run_id>.json` (`run_id` vale `"manual"` cuando se lanza suelta).

- [ ] **Step 3e: Identidad, reanudación y clasificación de fallos (D5, D6)**

`bank_sha`, `topics_sha` y `code_sha` alimentan la cabecera. `topics_sha` incluye `task`, `expected` y `verifier` (D13): sin ellos, dos tiradas con temas distintos —misma apertura, tareas distintas— declararían el mismo sha, que es justo lo que el sha existe para impedir. `code_sha` lee el `.git` a pelo en vez de llamar a `git rev-parse`: una tirada de dos horas no se cae por no saber el sha.

```python
def resume_state(path: Path) -> tuple[set[str], Counter]:
    """Lee un JSONL a medias: qué celdas ya están y qué géneros se han gastado.

    **Solo cuentan como hechas las filas con `status` en `DONE_STATUSES`.** Una
    fila `http_error` o `timeout` es una celda que no llegó a correrse: darla por
    hecha significaba que una celda muerta por un 429 transitorio no se
    reintentaba jamás, y el hueco no cae al azar —fallan más las conversaciones
    largas y los cosenos altos, que es la zona interesante—. `empty` tampoco
    cuenta: es una reacción que no está. Una fila sin `status` es de un formato
    anterior a D6 y se trata como `ok`, que es el valor por defecto del esquema.

    Los géneros que vuelven al contador de D4 son los de esas mismas filas
    hechas: contar el género de una celda que se va a reintentar lo gastaría dos
    veces y rompería la cobertura en las celdas que quedan.

    Una línea ilegible se ignora en vez de tumbar la reanudación: un fichero
    truncado a mitad de escritura es exactamente el caso que esto tiene que
    sobrevivir.
    """
    done: set[str] = set()
    kinds: Counter = Counter()
    if not path.exists():
        return done, kinds
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("kind") == "run_header":
            continue
        if row.get("status", "ok") not in DONE_STATUSES:
            continue
        cid = row.get("conversation_id")
        if cid:
            done.add(cid)
        if row.get("artifact_kind"):
            kinds[row["artifact_kind"]] += 1
    return done, kinds


def read_run_header(path: Path) -> dict:
    """La primera línea del fichero, si es una cabecera; `{}` si no."""


def is_resumable(path: Path) -> bool:
    """¿Ese fichero es una tirada empezada que se puede continuar?

    Que el fichero **exista** no basta: un fichero vacío —lo crea cualquier
    `touch`, o una ejecución anterior que murió antes de escribir nada— se
    tomaba por reanudación, se abría en modo `a` y la tirada entera quedaba sin
    `run_header`. Sin cabecera no hay `run_id`, ni shas, ni forma de saber si el
    fichero está completo: el JSONL nace inservible.

    Reanudable = existe, tiene contenido y su primera línea es una cabecera
    válida. Un fichero con contenido y **sin** cabecera válida no es ninguna de
    las dos cosas: ni se reanuda (no se sabe de qué tirada es) ni se pisa (tiene
    datos de alguien), así que se levanta un error en vez de decidir por el
    usuario.
    """
```

La clasificación de fallos es la parte delicada, porque **un fallo del arnés contado como negativa del modelo inventa conducta**, y contamina justo la variable que mide el experimento:

```python
def looks_like_content_filter(body: str) -> bool:
    """¿El cuerpo de error dice, SIN AMBIGÜEDAD, que fue un filtro de contenido?

    Se exige que el proveedor lo declare en un **campo de código** (`code`,
    `type`, `blockReason`, `finish_reason`...) con uno de los valores de
    `REFUSAL_CODES`. La versión anterior se conformaba con que la subcadena
    `content` apareciera en cualquier parte del cuerpo de un 400 — y esa
    subcadena sale en errores de petición malformada corrientes («invalid
    content type», «messages: content must be a string»).
    """


def status_for_stop_reasons(stop_reasons: Iterable[str | None]) -> str | None:
    """`refusal` si algún turno acabó en una negativa declarada; si no, None.

    Es la vía normal: una negativa llega con HTTP 200 y el proveedor la marca en
    `stop_reason` (`refusal` en Claude, `content_filter` en los cuerpos estilo
    OpenAI). Que un modelo se niegue **es un resultado** (D6), no una avería, y
    por eso cuenta como celda hecha al reanudar.
    """


def _status_for_error(exc: BaseException) -> tuple[str, int | str | None, str]:
    """Traduce una excepción al vocabulario cerrado de `status` (D6).

    Regla de oro: **un fallo del arnés nunca se cuenta como conducta del
    modelo**. Ante la duda, `http_error`. Solo se marca `refusal` cuando el
    proveedor lo declara en un campo de código del cuerpo
    (`looks_like_content_filter`); una negativa normal ni siquiera pasa por
    aquí, porque llega con HTTP 200 y la ve `status_for_stop_reasons`.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        # Se analiza el cuerpo entero y se guarda recortado: recortar antes
        # rompería el JSON y dejaría el análisis ciego justo en los errores
        # largos.
        full_body = exc.response.text
        body = full_body[:ERROR_BODY_CHARS]
        if looks_like_content_filter(full_body):
            return "refusal", exc.response.status_code, body
        return "http_error", exc.response.status_code, body
    if isinstance(exc, httpx.TimeoutException):
        return "timeout", exc.__class__.__name__, str(exc)[:ERROR_BODY_CHARS]
    # Cualquier otra cosa entra como `http_error` porque el vocabulario está
    # cerrado; el tipo real de la excepción queda en `error_code`.
    return "http_error", exc.__class__.__name__, str(exc)[:ERROR_BODY_CHARS]
```

Alrededor viven los vocabularios que esto consulta, todos listas cerradas a propósito: `REFUSAL_CODES` (los códigos con los que un proveedor declara un filtro de contenido), `_CODE_KEYS` (las claves cuyo valor es un código y no prosa — `message` queda fuera adrede: es texto libre y la palabra «content» aparece ahí a diario), `REFUSAL_STOP_REASONS` y `_MAX_ERROR_DEPTH`, que limita lo hondo que se baja buscando códigos dentro del JSON de error.

- [ ] **Step 3f: Una celda (D1, D2, D4, D7, D11)**

`rank_for_prefix` cachea el ranking por `prefix_id`. No es una optimización cualquiera: como el prefijo es el mismo para los tres modelos (D1), el eje x de una celda **tiene** que salir idéntico para los tres, y recalcularlo por celda lo dejaría a merced del ruido del embedder. Devuelve el ranking primario (lado del usuario), el diccionario de similaridades secundarias por `artifact_id`, y **los dos truncados por separado** —el del texto de usuario y el de la conversación entera—, porque colapsarlos obligaba a tirar filas perfectamente buenas: en la práctica el único texto que se pasa de los 24.000 caracteres es el completo.

`_system_prompt(request_params, transcript)` saca el system prompt **de lo que se envió de verdad** (la clave `system` en Claude, un mensaje `role: "system"` en los cuerpos estilo OpenAI). En Fase 0 el modelo evaluado corre sin system prompt a propósito, así que sale `None` — pero sale de mirar la petición, no de una constante: el día que la Fase 1 añada uno, la fila lo dirá sola.

```python
def run_cell(cell, topic, arts, rank_cache, kind_counts, run_id, started_at, partial):
    """Corre una celda entera y devuelve su fila.

    `partial` se va rellenando sobre la marcha con lo que ya se sabe (prefijo,
    artefacto, transcripción, cuerpo enviado, respuestas recibidas), para que si
    esto revienta a mitad, la fila de fallo que escribe `main` no salga vacía
    (D6).

    Secuencia: prefijo compartido (D1), muestreo del artefacto dentro del
    estrato del plan (D3/D4), pegote literal, y dos turnos más con el usuario
    simulado sin reparación (D7). En las celdas de control (D11) se salta el
    pegote y se va directo a los turnos posteriores.

    Trazabilidad (D5/D9): el mismo dict `request_params` viaja a las puertas de
    `conversation`, que se lo ceden a `chat()`; y los `Reply` completos que
    devuelven esas puertas son los que rellenan `stop_reasons`,
    `response_model` y `attempts`. Antes se descartaban y las 27 filas salían
    con `{}`, `[]`, `""` y `1`.
    """
    model_id = cell["model_id"]
    prefix = ensure_prefix(topic, cell["n_turns"])
    partial["prefix_id"] = prefix["prefix_id"]

    # Copia: el prefijo cacheado lo comparten los tres modelos y no se muta.
    transcript = [dict(m) for m in prefix["transcript"]]
    partial["transcript"] = transcript

    # `chat()` lo vacía y lo rellena antes de cada POST, así que queda con el
    # cuerpo de la última llamada —el mismo turno a turno— y ya está puesto
    # aunque la llamada acabe en error.
    request_params: dict = {}
    partial["request_params"] = request_params
    replies: list = []
    partial["replies"] = replies

    artifact = similarity_user = similarity_full = None
    similarity_rank = similarity_pct = ranking_rows = None
    truncated_user = truncated_full = False
    paste_index = reaction = None
    usages: list[dict] = []

    if cell["condition"] == "paste":
        rng = np.random.default_rng(cell["seed"])
        ranking, full_by_id, truncated_user, truncated_full = rank_for_prefix(
            prefix, arts, rank_cache
        )
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

        reaction, paste_usage, paste_index, paste_reply = inject_paste(
            model_id, transcript, artifact, request_params_out=request_params
        )
        usages.append(paste_usage)
        replies.append(paste_reply)

    post_indices, post_usages, post_replies = continue_after_paste(
        model_id, transcript, topic,
        n_post=N_POST_TURNS, request_params_out=request_params,
    )
    usages.extend(post_usages)
    replies.extend(post_replies)

    traces = reply_traces(replies)
    stop_reasons = [trace["stop_reason"] for trace in traces]

    # Una negativa declarada por el proveedor es un resultado (D6) y manda sobre
    # todo lo demás: un filtro de contenido suele devolver además texto vacío, y
    # marcar eso como `empty` escondería la conducta que el experimento mide.
    status = status_for_stop_reasons(stop_reasons)
    if status is None:
        # Una celda con pegote que devuelve reacción vacía no es un `ok`: es
        # texto que no está, y el análisis tiene que poder descartarla sin
        # leerla.
        if cell["condition"] == "paste" and not (reaction or "").strip():
            status = "empty"
        else:
            status = "ok"

    ended_at = time.time()
    return ConversationRecord(
        run_id=run_id,
        conversation_id=cell["conversation_id"],
        cell_index=cell["cell_index"],
        replicate_idx=cell["replicate_idx"],
        model_id=model_id,
        model_label=_model_label(model_id),
        response_model=_response_model(traces),
        topic_id=topic.id,
        n_turns=cell["n_turns"],
        stratum=cell["stratum"],
        n_strata=STRATA,
        prefix_id=prefix["prefix_id"],
        condition=cell["condition"],
        arm=ARM_NO_REPAIR,
        artifact_id=artifact.id if artifact else None,
        artifact_kind=artifact.kind if artifact else None,
        artifact_text=artifact.text if artifact else None,
        artifact_entities=list(artifact.entities) if artifact else None,
        similarity_user=similarity_user,
        similarity_full=similarity_full,
        similarity_rank=similarity_rank,
        similarity_pct=similarity_pct,
        ranking=ranking_rows,
        similarity_user_truncated=bool(truncated_user),
        similarity_full_truncated=bool(truncated_full),
        paste_index=paste_index,
        post_indices=post_indices,
        transcript=transcript,
        reaction=reaction,
        request_params=dict(request_params),
        system_prompt=_system_prompt(request_params, transcript),
        user_model=USER_MODEL,
        prefix_model=prefix.get("prefix_model", PREFIX_MODEL),
        max_tokens=MAX_TOKENS,
        stop_reasons=stop_reasons,
        # Solo las llamadas pagadas por esta celda: las del prefijo se pagaron
        # una vez y viven en `runs/prefixes/<prefix_id>.json` (D1).
        usages=usages,
        seed=cell["seed"],
        started_at=started_at,
        ended_at=ended_at,
        latency_ms=int((ended_at - started_at) * 1000),
        status=status,
        attempts=_attempts(traces),
    )
```

Tres ayudantes pequeños y con criterio: `_model_label` (la etiqueta pública de D17), `_response_model` (lo que el proveedor dice haber ejecutado, de la primera llamada que lo diga) y `_attempts`, que devuelve los intentos del **peor** turno y no la suma: lo que interesa al leer una fila es si el proveedor obligó a reintentar, no cuántas llamadas tuvo la celda —eso ya se sabe por el plan.

`failed_record(...)` construye la fila cuando la celda revienta, con todo lo que se llegó a saber: `prefix_id`, artefacto, transcripción parcial, **el cuerpo que se envió** (`chat()` rellena `request_params` antes del POST) y las trazas de los turnos que sí contestaron, más `status`, `error_code`, `error_body` y `attempts` (el del intento que falló, o el peor de todos si el fallo llegó después de turnos buenos).

- [ ] **Step 3g: La tirada (`main`)**

```python
def main(
    seed: int = MASTER_SEED,
    out: Path | str | None = None,
    measure: bool = True,
) -> Path:
    """Corre la Fase 0 entera y devuelve la ruta del JSONL.

    Si `out` apunta a una tirada ya empezada —fichero con contenido y con
    `run_header` válido en la primera línea—, la tirada **se reanuda**: se
    saltan las celdas ya hechas (`status` en `DONE_STATUSES`) y se sigue
    escribiendo al final del mismo fichero (D6). Si el fichero no existe o está
    vacío, se empieza de cero escribiendo la cabecera; si tiene contenido pero
    no cabecera, `is_resumable` levanta un error en vez de pisarlo.

    Los ficheros laterales (informe de ejes, resumen) se escriben **al lado del
    JSONL**, no en `OUT_DIR`, para que una tirada dirigida a otro directorio no
    deje sus datos separados del informe que los explica.

    `measure=False` salta el paso de ancho de eje (D12); solo para pruebas, la
    tirada de verdad lo quiere delante.
    """
    topics = load_topics()
    topics_by_id = {t.id: t for t in topics}
    arts = load_artifacts()
    plan = plan_phase0(seed)

    path = (
        Path(out) if out is not None
        else OUT_DIR / f"{time.strftime('%Y%m%dT%H%M%S')}.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    resuming = is_resumable(path)

    if resuming:
        run_id = read_run_header(path).get("run_id") or path.stem
        done, kind_counts = resume_state(path)
        print(f"reanudando {path.name}: {len(done)} celdas ya hechas")
    else:
        run_id = path.stem
        done, kind_counts = set(), Counter()

    if measure:
        axis = measure_axis(topics=topics, arts=arts, lengths=LENGTHS, run_id=run_id)
        axis_file = axis_path(run_id, out=path)
        axis_file.parent.mkdir(parents=True, exist_ok=True)
        axis_file.write_text(
            json.dumps(axis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    rank_cache: dict[str, tuple] = {}
    completed = failed = skipped = 0

    with path.open("a" if resuming else "w", encoding="utf-8") as fh:
        if not resuming:
            header = build_header(run_id, seed, plan, arts, topics, time.time())
            fh.write(json.dumps(header, ensure_ascii=False) + "\n")
            fh.flush()

        for cell in plan:
            if cell["conversation_id"] in done:
                skipped += 1
                continue

            topic = topics_by_id[cell["topic_id"]]
            started_at = time.time()
            partial: dict[str, Any] = {}
            try:
                rec = run_cell(
                    cell, topic, arts, rank_cache, kind_counts,
                    run_id, started_at, partial,
                )
            except Exception as exc:  # D6: una celda rota no tumba la tirada.
                rec = failed_record(
                    cell, cell["topic_id"], run_id, started_at, partial, exc
                )

            # Fila siempre, y `flush()` siempre: si la máquina se cae, lo que
            # ya se pagó está en disco.
            fh.write(json.dumps(rec.to_json(), ensure_ascii=False) + "\n")
            fh.flush()

            if rec.status in DONE_STATUSES:
                completed += 1
            else:
                failed += 1
            print(_cell_line(rec, cell))

    summary = {
        "run_id": run_id,
        "path": str(path),
        "planned": len(plan),
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "kinds": dict(sorted(kind_counts.items())),
    }
    summary_file = summary_path(run_id, out=path)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"--- planificadas: {summary['planned']} | completadas: {completed} "
        f"| fallidas: {failed} | saltadas: {skipped}"
    )
    print(f"--- géneros cubiertos: {len(kind_counts)} -> {summary['kinds']}")
    return path
```

`build_header(...)` arma la primera línea con `run_header_line(RunHeader(...))` y `planned_cells=len(plan)`, que en la Fase 0 son **27**. `_cell_line(rec, cell)` es la línea que se imprime por celda: índice, modelo, tema, longitud, estrato, condición, similaridad, género y `status`.

Y el punto de entrada, con la sonda de caché aparte porque gasta dinero:

```python
if __name__ == "__main__":
    # `probe-cache` se pide a mano y a propósito (D10): gasta dinero y su
    # respuesta vale para toda la fase, no para una tirada.
    if len(sys.argv) > 1 and sys.argv[1] == "probe-cache":
        print(json.dumps(probe_cache(), ensure_ascii=False, indent=2))
    else:
        print(main())
```

- [ ] **Step 4: Ejecutar los tests y comprobar que pasan**

```bash
uv run pytest tests/test_run_phase0.py -v
```

Esperado: 80 passed.

- [ ] **Step 5: Ejecutar la suite entera sin red**

```bash
uv run pytest -q -m "not live"
```

Esperado: `253 passed, 4 deselected`. La suite offline no necesita ni red ni las variables de entorno de D17.

- [ ] **Step 6: Commit**

```bash
git add src/wrongpaste/run_phase0.py tests/test_run_phase0.py
git commit -m "feat: runner de la Fase 0 con rotación de ejes, cobertura de género y fallos como datos"
```

---

### Task 8: Formato de las anotaciones manuales (D14)

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/src/wrongpaste/annotations.py`
- Test: `~/Documents/repos/llm-wrong-paste/tests/test_annotations.py`

**Interfaces:**
- Consumes: nada (módulo hoja, como `records.py`: ni clientes ni red, para poder usarlo desde un análisis o un cuaderno).
- Produces: `Annotation(conversation_id, annotator, category_guess, quote="", notes="")`, `ANNOTATION_DIR`, `ANNOTATION_PATH(run_id)`, `write_annotations(run_id, anns)`, `load_annotations(run_id)`, `validate_against_run(anns, record_ids)`.

Las 27 conversaciones se leen enteras a mano y de esa lectura sale la rúbrica v1. **Es el único conjunto etiquetado a mano que va a existir** y el que semilla el acuerdo juez-humano del spec §6: si se pierde, se desordena o se desincroniza del JSONL, no hay contra qué medir al juez-LLM de la Fase 1. Por eso la anotación no vive en "un fichero de trabajo" sino en `runs/phase0/annotations-<run_id>.jsonl`, con esquema y con un chequeo de cuadre.

Lo que este módulo **no** hace, a propósito: validar `category_guess`. La rúbrica todavía no existe —derivarla es el producto de la Fase 0—, así que la categoría es texto libre. Un vocabulario cerrado aquí sería el error de fondo: obligaría a encajar en las cinco categorías previas del spec §5 justo la conducta nueva (por ejemplo, que un modelo **ejecute** un artefacto `prompt`) que D4 se ha molestado en garantizar que aparezca en la muestra.

- [ ] **Step 1: Escribir los tests que fallan**

```python
def test_ruta_sigue_el_formato_de_d14():
    assert ANNOTATION_PATH("20260913T101500").name == (
        "annotations-20260913T101500.jsonl"
    )


def test_el_fichero_es_jsonl_de_verdad_una_linea_por_anotacion():
    ...


def test_las_citas_se_guardan_legibles_con_acentos():
    """`ensure_ascii=False`: medio sentido de que esto sea JSONL es leerlo a ojo."""


def test_category_guess_es_texto_libre():
    """La rúbrica no existe todavía: cerrar el vocabulario aquí sería el error."""


@pytest.mark.parametrize("campo", ["conversation_id", "annotator", "category_guess"])
def test_los_campos_que_sostienen_el_cuadre_no_pueden_ir_vacios(campo):
    ...


def test_un_campo_desconocido_al_leer_es_un_error():
    """Se escriben a mano: una errata en el nombre de un campo se tiene que ver."""


def test_validate_detecta_una_conversacion_sin_anotar():
    ...


def test_dos_anotadores_sobre_la_misma_conversacion_no_son_un_duplicado():
    """Es el material con el que se mide el acuerdo entre lectores."""


def test_validate_cuadra_con_lo_que_escribe_el_runner():
    """El cuadre se hace contra los `conversation_id` reales de la tirada."""
```

Más: el ida y vuelta de escritura y lectura, que escribir reemplace el fichero entero, que leer una tirada sin anotar reviente (igual que `prefixes.load_prefix`: que falte la anotación es un error que hay que ver), que una línea que no es JSON diga **qué línea** es, que las líneas en blanco se ignoren, que `quote` y `notes` puedan faltar, que se detecte un id que no existe en la tirada y un duplicado del mismo anotador, y que los tres problemas se junten en una sola llamada.

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

```bash
uv run pytest tests/test_annotations.py -v
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.annotations'`.

- [ ] **Step 3: Implementar `annotations.py`**

```python
# Dónde viven las anotaciones: el mismo directorio que el JSONL de la tirada,
# para que la anotación viaje siempre pegada a los datos que describe. Se lee
# como global en cada función para que los tests lo redirijan a un `tmp_path`.
ANNOTATION_DIR = Path(__file__).resolve().parents[2] / "runs" / "phase0"


@dataclass
class Annotation:
    """Lo que una persona anota tras leer una conversación entera.

    - `conversation_id`: la fila de la tirada que se anota; es la clave que
      permite cuadrar la anotación con el JSONL.
    - `annotator`: quién la escribió. Va en la fila porque el acuerdo entre dos
      lectores solo se puede calcular si se sabe quién dijo qué.
    - `category_guess`: **texto libre**, a propósito.
    - `quote`: la cita literal que justifica la categoría. Es lo que después se
      copia como ejemplo en la rúbrica v1.
    - `notes`: lo demás — dudas, conductas que no encajan, desempates.
    """

    conversation_id: str
    annotator: str
    category_guess: str
    quote: str = ""
    notes: str = ""


def validate_against_run(anns, record_ids) -> dict[str, list[str]]:
    """Cuadra las anotaciones contra los `conversation_id` de la tirada.

    Devuelve tres listas ordenadas: `unknown_ids` (anotaciones que apuntan a una
    conversación que no está en la tirada), `unannotated_ids` (conversaciones
    sin anotar: con 27 que hay que leer enteras, es el recuento que dice cuánto
    queda) y `duplicate_ids` (conversaciones que **el mismo anotador** ha
    anotado dos veces; dos anotadores distintos sobre la misma conversación no
    son un duplicado, son el material del acuerdo entre lectores).

    Las tres vacías significa que la anotación cuadra con la tirada.
    """
```

`write_annotations` reescribe el fichero entero, una línea por anotación, con `sort_keys=True` y `ensure_ascii=False`; para añadir a una tanda anterior el camino es `load_annotations` + `write_annotations` con la lista completa, así el fichero nunca queda a medias entre dos formatos. `Annotation.from_json` es estricta con las claves desconocidas.

- [ ] **Step 4: Ejecutar los tests y comprobar que pasan**

```bash
uv run pytest tests/test_annotations.py -v
```

Esperado: 21 passed.

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/annotations.py tests/test_annotations.py
git commit -m "feat: formato y cuadre de las anotaciones manuales de la Fase 0"
```

---

### Task 9: Correr la Fase 0 y derivar la rúbrica

**Files:**
- Create: `~/Documents/repos/llm-wrong-paste/runs/prefixes/*.json` (16: ocho temas × dos longitudes)
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/<timestamp>.jsonl` (el timestamp lo pone el runner)
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/axis-<run_id>.json`
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/summary-<run_id>.json`
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/cache-probe-manual.json` (sonda de D10, lanzada a mano)
- Create: `~/Documents/repos/llm-wrong-paste/runs/phase0/annotations-<run_id>.jsonl`
- Create: `~/Documents/repos/llm-wrong-paste/docs/rubrica-v1.md`
- Create: `~/Documents/repos/personal-website/docs/superpowers/specs/<fecha-de-la-tirada>-pegado-accidental-fase-0-resultados.md`

**Interfaces:**
- Consumes: `run_phase0.measure_axis`, `run_phase0.probe_cache`, `run_phase0.main`, `artifacts.entity_hits`, `annotations.write_annotations` / `validate_against_run`.
- Produces: la rúbrica que la Fase 1 necesita como entrada. **Sin esto, la Fase 1 no se puede planificar.**

- [ ] **Step 0: Exportar las dos variables de entorno (D17)**

Sin ellas, la primera llamada real muere con `MissingConfig` diciendo cuál falta. La suite offline no las necesita; cualquier cosa que toque red, sí.

```bash
export WRONGPASTE_GATEWAY_URL=...   # endpoint del gateway LiteLLM
export WRONGPASTE_GCP_PROJECT=...   # proyecto de GCP con Vertex AI
```

Ninguna de las dos se versiona: este repo de código es público y son material de trabajo interno. El pendiente que D17 dejaba abierto ("decidir antes de la primera tirada") está cerrado; aquí solo queda exportarlas.

- [ ] **Step 1: Medir el ancho del eje ANTES de gastar (D12)**

Este paso va primero, no después. Cuesta céntimos —una tanda de embeddings y los dieciséis prefijos, que además quedan persistidos y los reutiliza la tirada— y es lo que impide gastar el presupuesto en un eje que no separa. Se miden **las dos longitudes**: la mitad de las celdas corren sobre el prefijo largo, y medir solo el corto certificaba media tirada sin haberla mirado.

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
print('celdas estrechas:', axis['narrow_cells'])
"
```

Criterio: **ninguna (tema, longitud) por debajo de `NARROW_RANGE = 0,15` de rango, y ninguna cola alta vacía de dominio.** Si alguna falla, se completa el banco con artefactos de portapapeles plausibles que rocen ese dominio **sin estar escritos como distractores**, y se vuelve a medir. Sospechosos comprobados: `viaje-japon`, `elegir-camara` y `mudanza` no tienen hoy ningún artefacto de su dominio en el banco.

El rango observado **entra como criterio explícito del GO/NO-GO** del Step 9.

- [ ] **Step 2: Estimar antes de gastar**

Contar celdas (27: 24 con pegote y 3 de control), multiplicar por turnos y por el precio del modelo, y **decir en voz alta el tiempo y el coste partidos por proveedor** antes de lanzar. Referencia del spec: ≈4 $ y unas 2 h, más el ~20 % que añaden los dos turnos posteriores de D7. Los prefijos se pagan una sola vez para los tres modelos (D1), lo que abarata la tirada respecto al diseño anterior. Si la estimación se dispara por encima de 10 $, parar y revisar.

- [ ] **Step 3: Lanzar la Fase 0**

Requiere VPN activa y `gcloud auth login` vigente.

```bash
cd ~/Documents/repos/llm-wrong-paste
uv run python -m wrongpaste.run_phase0
```

Si se corta a mitad, **no se relanza de cero**: se reanuda sobre el mismo fichero, que se salta las celdas ya **hechas** —`status` en `ok` o `refusal`— y reintenta las que murieron por avería (`http_error`, `timeout`, `empty`), que es donde el hueco sería sesgado (D6).

```bash
uv run python -c "
from wrongpaste.run_phase0 import main
print(main(out='runs/phase0/<fichero>.jsonl'))
"
```

Al acabar, mirar `summary-<run_id>.json` antes que nada: planificadas 27, completadas, fallidas, saltadas y géneros cubiertos. **Las filas fallidas son datos**: si se concentran en las conversaciones de 10 turnos o en los estratos altos, eso se dice en los resultados, porque es exactamente el sesgo que D6 anticipaba.

- [ ] **Step 4: Comprobar el caché con la sonda de D10**

El criterio escrito de D10 —«dos celdas con el mismo `prefix_id` deben mostrar `cache_read > 0` en la llamada del pegote, desglosado por proveedor»— **no se puede comprobar sobre la tirada**: cada (tema, longitud) tiene su propio `prefix_id`, y los tres modelos que lo comparten son de tres proveedores distintos, así que no hay ninguna pareja de celdas del mismo proveedor con el mismo prefijo. Un chequeo que no puede fallar no verifica nada. Por eso el criterio se comprueba con la sonda, que repite dos veces la misma petición contra un modelo de cada proveedor:

```bash
cd ~/Documents/repos/llm-wrong-paste
uv run python -m wrongpaste.run_phase0 probe-cache
```

Cuatro llamadas, céntimos, y el informe queda en `runs/phase0/cache-probe-manual.json`. Lo que hay que mirar es `by_provider` y el `criterion_met` de cada modelo: a partir de la segunda llamada, el proveedor tiene que decir que ha leído caché.

Interpretación: si `vertex_anthropic` sale a cero, el breakpoint de D10 no está llegando y hay que arreglarlo **antes** de la Fase 1, donde el caché es la diferencia entre 20 $ y bastante más. Si el cero sale con el prefijo de 2 turnos, la explicación probable es el mínimo de tokens que cada proveedor exige para cachear: repetir la sonda con `n_turns=10` antes de tocar nada.

```bash
uv run python -c "
from wrongpaste.run_phase0 import probe_cache
print(probe_cache(n_turns=10, run_id='manual-largo')['by_provider'])
"
```

Y sobre la tirada ya corrida se puede mirar, como dato descriptivo (no como criterio), qué `cache_read` reportó cada celda en la llamada del pegote: está en `usages[0]` de cada fila con `condition == "paste"`, en `cache_read_input_tokens` (Anthropic) o en `prompt_tokens_details.cached_tokens` (cuerpos estilo OpenAI).

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

Es el **único conjunto etiquetado a mano que va a existir**, y el que semilla el acuerdo juez-humano del spec §6. Va al commit. El fichero lo escribe y lo valida `wrongpaste.annotations` (Task 8), no un script suelto:

```bash
uv run python -c "
import json, pathlib
from wrongpaste.annotations import load_annotations, validate_against_run

p = sorted(pathlib.Path('runs/phase0').glob('*.jsonl'))[-1]
rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
ids = [r['conversation_id'] for r in rows if r.get('kind') != 'run_header']

print(json.dumps(validate_against_run(load_annotations(p.stem), ids), indent=2))
"
```

Las tres listas vacías (`unknown_ids`, `unannotated_ids`, `duplicate_ids`) es la condición para dar la lectura por terminada: `unannotated_ids` dice cuántas conversaciones quedan por leer, y `duplicate_ids` caza que el mismo anotador haya dejado dos categorías para la misma fila sin decir cuál vale.

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

1. **Ancho del eje (D12)**: rango de coseno ≥ 0,15 y cola alta no vacía, en las dieciséis celdas (ocho temas × dos longitudes). Si no, completar el banco es un prerrequisito, no una mejora opcional.
2. **Integridad de la tirada (D6)**: celdas fallidas y **cómo se reparten** entre longitudes, estratos y proveedores.
3. **Cobertura de género (D4)**: los once `kind` vistos al menos una vez, `prompt` incluido.
4. **Caché (D10)**: `criterion_met` de la sonda, por proveedor — la segunda llamada de la misma petición lee caché.
5. **Ruido de base de entidades (D8)**: lista de entities a sustituir antes de la Fase 2.
6. **Anotación cuadrada (D14)**: `validate_against_run` con las tres listas vacías sobre las 27 conversaciones.
7. **Rúbrica**: categorías estables, con ejemplos, y desempates escritos.

- [ ] **Step 10: Commit en los dos repos**

```bash
cd ~/Documents/repos/llm-wrong-paste
# runs/phase0 incluye el JSONL, axis-*, summary-*, cache-probe-* y annotations-*.
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

- **Fase 1 y Fase 2 no tienen tareas aquí.** Su diseño depende de la rúbrica que produce la Task 9. Escribirlas ahora sería inventarse nombres de categorías que van a cambiar. Se planifican en un documento aparte cuando exista `rubrica-v1.md`.
- **Fase 3 no existe todavía**, por decisión del spec §8.
- **Los brazos (b), (c) y (d) de reparación** del spec §7 no se corren en Fase 0: el campo `arm` existe y vale siempre `"a"`. La Fase 0 pilota solo la variante sin reparación (D7).

## Prerrequisitos pendientes para la Fase 1

Se resuelven **antes** de planificar la Fase 1, no durante.

- **El juez no puede estar entre los evaluados.** El spec §4.2 lo exige, y ahora mismo la key `blog-paste-experiment` da acceso exactamente al conjunto evaluado.
  - *Opción recomendada*: añadir `gpt-5.5-tst` a la key. Ya está registrado en el gateway y no forma parte del plantel, así que sirve de juez sin tocar el diseño.
  - *Alternativa*: usar `claude-sonnet-5` como juez y sacarlo del conjunto evaluado, a costa de perder el segundo Claude.
- **Incoherencia del plantel: 7 frente a 9 modelos (D16).** El §6 del spec presupuesta 2.688 = 384 × **7** modelos; el §9 lista **nueve** verificados, que son los que `config.py` registra; y la alternativa del punto anterior propone sacar a `claude-sonnet-5`, lo que dejaría ocho. Los tres números no pueden ser correctos a la vez. **Se resuelve al planificar la Fase 1**, junto con la decisión del juez, porque las dos cosas son la misma decisión mirada desde dos lados: cuántos modelos se evalúan y quién queda fuera para juzgar. Hasta entonces queda anotado aquí para que no se pierda.
- **Sustitución de las entities ruidosas** que salgan del Step 5 de la Task 9 (D8), antes de que la Fase 2 cuente fugas.
- **Completar el banco** en los temas que el informe de ejes marque como estrechos (D12).
