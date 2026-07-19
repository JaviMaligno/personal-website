"""Real VLM API clients (design §4) — implemented, NOT yet exercised.

Everything here is written against the providers' public REST APIs with an
injectable transport, so the code is fully unit-tested offline. Running for
real only requires API keys in the environment:

    ANTHROPIC_API_KEY   → AnthropicRaw   (Claude)
    OPENAI_API_KEY      → OpenAIRaw      (GPT)
    GEMINI_API_KEY      → GeminiRaw      (Gemini)

Design constraints encoded here (§5): temperature 0, strict-JSON prompting
with one reparse retry, exact model ids recorded in every result via
`model_id`, and multi-image support for the multi-frame condition.

NOTE (local run): verify current model ids and API versions before Phase 3;
the defaults below were chosen at implementation time and models rotate.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Callable, Protocol, Sequence

from ..prompts import ResponseParseError, parse_prediction
from ..schema import Condition, Item, Prediction

Transport = Callable[[str, dict, dict], dict]

RETRYABLE_STATUSES = {408, 409, 429, 500, 502, 503, 529}


class TransportError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def http_post_json(url: str, headers: dict, payload: dict) -> dict:
    """Default transport: blocking POST with JSON body and response."""
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise TransportError(f"HTTP {exc.code}: {detail}", status=exc.code) from exc
    except urllib.error.URLError as exc:
        raise TransportError(f"network error: {exc.reason}") from exc


def _require_key(env_var: str) -> str:
    key = os.environ.get(env_var)
    if not key:
        raise RuntimeError(
            f"{env_var} is not set. API calls are Phase-3 work meant to run "
            "locally with credentials; see TODO.md."
        )
    return key


class RawVLM(Protocol):
    """Low-level completion interface: prompt + images -> raw text."""

    model_id: str

    def complete(self, prompt: str, images: Sequence[bytes]) -> str: ...


class _RetryingRaw:
    """Shared retry/backoff machinery for the concrete providers."""

    def __init__(
        self,
        transport: Transport = http_post_json,
        max_retries: int = 4,
        backoff_s: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._transport = transport
        self._max_retries = max_retries
        self._backoff_s = backoff_s
        self._sleep = sleep

    def _post(self, url: str, headers: dict, payload: dict) -> dict:
        attempt = 0
        while True:
            try:
                return self._transport(url, headers, payload)
            except TransportError as exc:
                retryable = exc.status is None or exc.status in RETRYABLE_STATUSES
                if not retryable or attempt >= self._max_retries:
                    raise
                self._sleep(self._backoff_s * (2**attempt))
                attempt += 1


class AnthropicRaw(_RetryingRaw):
    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(self, model_id: str = "claude-sonnet-5", max_tokens: int = 1024, **kwargs):
        super().__init__(**kwargs)
        self.model_id = model_id
        self.max_tokens = max_tokens

    def complete(self, prompt: str, images: Sequence[bytes]) -> str:
        content: list[dict] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(img).decode("ascii"),
                },
            }
            for img in images
        ]
        content.append({"type": "text", "text": prompt})
        payload = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": content}],
        }
        headers = {
            "x-api-key": _require_key("ANTHROPIC_API_KEY"),
            "anthropic-version": self.API_VERSION,
        }
        data = self._post(self.API_URL, headers, payload)
        return "".join(
            block["text"] for block in data.get("content", []) if block.get("type") == "text"
        )


class OpenAIRaw(_RetryingRaw):
    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, model_id: str = "gpt-4o", max_tokens: int = 1024, **kwargs):
        super().__init__(**kwargs)
        self.model_id = model_id
        self.max_tokens = max_tokens

    def complete(self, prompt: str, images: Sequence[bytes]) -> str:
        content: list[dict] = [
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64," + base64.b64encode(img).decode("ascii")
                },
            }
            for img in images
        ]
        content.append({"type": "text", "text": prompt})
        payload = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": content}],
        }
        headers = {"Authorization": f"Bearer {_require_key('OPENAI_API_KEY')}"}
        data = self._post(self.API_URL, headers, payload)
        return data["choices"][0]["message"]["content"] or ""


class GeminiRaw(_RetryingRaw):
    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, model_id: str = "gemini-2.0-flash", **kwargs):
        super().__init__(**kwargs)
        self.model_id = model_id

    def complete(self, prompt: str, images: Sequence[bytes]) -> str:
        parts: list[dict] = [
            {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": base64.b64encode(img).decode("ascii"),
                }
            }
            for img in images
        ]
        parts.append({"text": prompt})
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0},
        }
        url = f"{self.API_BASE}/{self.model_id}:generateContent"
        headers = {"x-goog-api-key": _require_key("GEMINI_API_KEY")}
        data = self._post(url, headers, payload)
        candidate = data["candidates"][0]
        return "".join(p.get("text", "") for p in candidate["content"]["parts"])


ImageProvider = Callable[[Item, Condition], Sequence[bytes]]


def file_image_provider(item: Item, condition: Condition) -> list[bytes]:
    """Default provider for real data: reads the item's `frame_refs` paths.
    Single-frame conditions use only the last (target) frame."""
    if not item.frame_refs:
        raise ValueError(f"item {item.item_id} has no frame_refs")
    refs = item.frame_refs
    if condition.temporal.value == "single_frame":
        refs = refs[-1:]
    return [open(ref, "rb").read() for ref in refs]


REPARSE_REMINDER = (
    "\n\nYour previous answer could not be parsed. Respond again with ONLY the "
    "JSON object, no markdown fences, no extra text."
)


class ApiVLMClient:
    """Adapts a RawVLM to the harness `VLMClient` protocol: builds images for
    the condition, calls the model, parses strict JSON with one retry (§5)."""

    def __init__(
        self,
        raw: RawVLM,
        image_provider: ImageProvider = file_image_provider,
        max_parse_retries: int = 1,
    ):
        self.raw = raw
        self.model_id = raw.model_id
        self.image_provider = image_provider
        self.max_parse_retries = max_parse_retries

    def predict(self, item: Item, condition: Condition, prompt: str) -> Prediction:
        images = list(self.image_provider(item, condition))
        attempt_prompt = prompt
        last_error: ResponseParseError | None = None
        for _ in range(self.max_parse_retries + 1):
            text = self.raw.complete(attempt_prompt, images)
            try:
                return parse_prediction(text)
            except ResponseParseError as exc:
                last_error = exc
                attempt_prompt = prompt + REPARSE_REMINDER
        raise ResponseParseError(
            f"{self.model_id} on {item.item_id}: unparseable after retries: {last_error}"
        )
