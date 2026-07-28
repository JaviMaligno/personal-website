"""Minimal, dependency-free adapters for the provider APIs.

Only stdlib: the point of this harness is that anyone can run it with a bare
python3 and a set of API keys, without a requirements.txt to fight with.

Each adapter exposes the same call signature:

    complete(model: str, prompt: str, max_tokens: int, temperature: float) -> str

Model ids are passed as "<provider>:<model>", e.g. "anthropic:claude-opus-4-6"
or "openai:gpt-5". The provider prefix is what routes the call, so the rest of
the harness never has to know which vendor a judge belongs to.

## Azure as a transport

The prefix is the *vendor*, never the host. Azure AI Foundry serves several
vendors' models, so it is wired here as a transport override rather than as a
fourth provider: set the environment variables below and the matching prefixes
are served from Azure instead of the vendor's own API, with the model name
becoming the Azure *deployment* name.

    AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_KEY        serves openai: and xai:
    AZURE_ANTHROPIC_ENDPOINT / AZURE_ANTHROPIC_KEY  serves anthropic:

That split is not cosmetic. Anthropic models on Foundry speak the native
Messages API at /anthropic/v1/messages and 404 on the OpenAI-compatible route;
OpenAI and xAI models are both served by /openai/v1/chat/completions on the same
resource. Keeping the vendor in the id is what lets `family()` stay honest — a
self-preference measurement that grouped every model under "azure" would be
measuring nothing.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

TIMEOUT = 180
RETRIES = 4


class ProviderError(RuntimeError):
    pass


def _post(url: str, headers: dict, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    last = None
    for attempt in range(RETRIES):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            last = ProviderError(f"HTTP {e.code} from {url}: {detail}")
            # 4xx other than 429 will not fix themselves.
            if e.code < 500 and e.code != 429:
                raise last
        except (urllib.error.URLError, TimeoutError) as e:
            last = ProviderError(f"network error calling {url}: {e}")
        time.sleep(2 ** attempt)
    raise last


def _require(var: str) -> str:
    key = os.environ.get(var)
    if not key:
        raise ProviderError(f"{var} is not set")
    return key


def _anthropic(model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    azure = os.environ.get("AZURE_ANTHROPIC_ENDPOINT")
    if azure:
        url = azure.rstrip("/") + "/anthropic/v1/messages"
        headers = {"x-api-key": _require("AZURE_ANTHROPIC_KEY")}
    else:
        url = (os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
               + "/v1/messages")
        headers = {"x-api-key": _require("ANTHROPIC_API_KEY")}
    data = _post(
        url,
        {**headers, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


_FIXED_TEMPERATURE: set[str] = set()  # models that accept only their default temperature


def _chat_completions(url: str, headers: dict, model: str, prompt: str,
                      max_tokens: int, temperature: float) -> str:
    """The OpenAI /chat/completions shape, which Azure serves for OpenAI and xAI alike."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": max_tokens,
    }
    # Reasoning models reject a non-default temperature; only send it when asked for.
    if temperature != 1.0 and model not in _FIXED_TEMPERATURE:
        payload["temperature"] = temperature
    try:
        data = _post(url, headers, payload)
    except ProviderError as e:
        # Some reasoning models (gpt-5.x) accept only the default temperature and
        # reject even temperature=0. Drop it and say so rather than losing the call.
        if "temperature" not in str(e) or "temperature" not in payload:
            raise
        if model not in _FIXED_TEMPERATURE:
            print(f"  ! {model} rejects temperature={temperature}; running it at its "
                  f"default for the rest of the run", file=sys.stderr)
            _FIXED_TEMPERATURE.add(model)
        payload.pop("temperature")
        data = _post(url, headers, payload)
    return data["choices"][0]["message"]["content"] or ""


def _openai(model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    azure = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if azure:
        url = azure.rstrip("/") + "/openai/v1/chat/completions"
        headers = {"api-key": _require("AZURE_OPENAI_KEY"), "Content-Type": "application/json"}
    else:
        url = (os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
               + "/chat/completions")
        headers = {"Authorization": f"Bearer {_require('OPENAI_API_KEY')}",
                   "Content-Type": "application/json"}
    return _chat_completions(url, headers, model, prompt, max_tokens, temperature)


def _xai(model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    azure = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if azure:
        url = azure.rstrip("/") + "/openai/v1/chat/completions"
        headers = {"api-key": _require("AZURE_OPENAI_KEY"), "Content-Type": "application/json"}
    else:
        url = (os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
               + "/chat/completions")
        headers = {"Authorization": f"Bearer {_require('XAI_API_KEY')}",
                   "Content-Type": "application/json"}
    return _chat_completions(url, headers, model, prompt, max_tokens, temperature)


def _gemini(model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    key = _require("GEMINI_API_KEY")
    data = _post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        {"Content-Type": "application/json"},
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        },
    )
    parts = data["candidates"][0]["content"].get("parts", [])
    return "".join(p.get("text", "") for p in parts)


ADAPTERS = {
    "anthropic": _anthropic,
    "openai": _openai,
    "gemini": _gemini,
    "xai": _xai,
}


def complete(model_id: str, prompt: str, max_tokens: int = 2048, temperature: float = 0.0) -> str:
    if ":" not in model_id:
        raise ProviderError(f"model id must be '<provider>:<model>', got {model_id!r}")
    provider, model = model_id.split(":", 1)
    if provider not in ADAPTERS:
        raise ProviderError(f"unknown provider {provider!r}; known: {sorted(ADAPTERS)}")
    return ADAPTERS[provider](model, prompt, max_tokens, temperature)


def family(model_id: str) -> str:
    """The grouping used for self-preference: everything before the colon."""
    return model_id.split(":", 1)[0]
