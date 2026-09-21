"""One HTTP request per attempt; no invisible retries or parameter fallbacks."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward credentials to an unexpected destination.


def validate_model(model):
    required = {"id", "model", "transport", "endpoint", "max_tokens"}
    optional = {"temperature", "key_env", "key_file", "auth", "billing_project", "thinking"}
    if not required <= set(model) or set(model) - required - optional:
        raise ValueError("Unknown/missing model configuration fields")
    if model["transport"] not in {"openai", "anthropic", "vertex_anthropic"}:
        raise ValueError("Supported transports: openai, anthropic, vertex_anthropic")
    if any(not isinstance(model[k], str) or not model[k] for k in required - {"max_tokens"}):
        raise ValueError("Model configuration strings must be nonempty")
    url = urllib.parse.urlsplit(model["endpoint"])
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment):
        raise ValueError("Endpoint must be an HTTPS URL without embedded credentials/query/fragment")
    if type(model["max_tokens"]) is not int or model["max_tokens"] <= 0:
        raise ValueError("max_tokens must be a positive integer")
    if "temperature" in model and (type(model["temperature"]) not in (float, int)
                                   or not 0 <= model["temperature"] <= 2):
        raise ValueError("Invalid temperature")
    methods = sum(k in model for k in ("key_env", "key_file", "auth"))
    if methods != 1 or ("auth" in model and model["auth"] != "gcloud"):
        raise ValueError("Choose exactly one credential method: key_env, key_file or auth=gcloud")
    if model["transport"] == "vertex_anthropic" and model.get("auth") != "gcloud":
        raise ValueError("Vertex uses the existing gcloud login")
    if "thinking" in model and model["thinking"] != {"type": "adaptive"}:
        raise ValueError("Only the existing adaptive-thinking configuration is supported")
    if "thinking" in model and (model["transport"] == "openai" or "temperature" in model):
        raise ValueError("Adaptive Anthropic thinking cannot use temperature or OpenAI transport")


def credential(model):
    if model.get("auth") == "gcloud":
        proc = subprocess.run(["gcloud", "auth", "print-access-token"],
                              capture_output=True, text=True, timeout=45)
        if proc.returncode or not proc.stdout.strip():
            raise ValueError("gcloud authentication unavailable; inspect or refresh the existing login")
        return proc.stdout.strip()
    if "key_file" in model:
        value = Path(model["key_file"]).expanduser().read_text().strip()
    else:
        value = os.environ.get(model["key_env"], "")
    if not value:
        raise ValueError("Configured credential is empty or unavailable")
    return value


def request_parts(model, prompt):
    validate_model(model)
    if model["model"].startswith("REPLACE_"):
        raise ValueError("Replace the example model ID before making live calls")
    key = credential(model)
    payload = {"model": model["model"], "messages": [{"role": "user", "content": prompt}]}
    headers = {"Content-Type": "application/json"}
    if model["transport"] == "openai":
        headers["Authorization"] = "Bearer " + key
        payload["max_completion_tokens"] = model["max_tokens"]
    elif model["transport"] == "anthropic":
        headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        payload["max_tokens"] = model["max_tokens"]
    else:
        headers["Authorization"] = "Bearer " + key
        if model.get("billing_project"):
            headers["x-goog-user-project"] = model["billing_project"]
        payload.pop("model")  # Vertex model ID is part of the endpoint.
        payload.update({"anthropic_version": "vertex-2023-10-16", "max_tokens": model["max_tokens"]})
    if "temperature" in model:
        payload["temperature"] = model["temperature"]
    if "thinking" in model:
        payload["thinking"] = model["thinking"]
    return headers, payload, key


def normalize(model, data):
    if model["transport"] == "openai":
        choice = data["choices"][0]
        text = choice["message"].get("content") or ""
        finish = choice["finish_reason"]
        usage = data.get("usage", {})
    else:
        text = "".join(b["text"] for b in data["content"] if b.get("type") == "text")
        finish = data["stop_reason"]
        usage = data.get("usage", {})
    if not isinstance(text, str):
        raise ValueError("Unsupported response content")
    return {"text": text, "finish_reason": finish, "usage": usage,
            "truncated": finish in {"length", "max_tokens"},
            "response_model": data.get("model"), "response_id": data.get("id")}


def complete(model, prompt):
    headers, payload, key = request_parts(model, prompt)
    request = urllib.request.Request(model["endpoint"], method="POST", headers=headers,
                                     data=json.dumps(payload).encode())
    start = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=180) as response:
            # Do not log headers or arbitrary HTTP error bodies. Redact an echoed key.
            body = response.read().decode().replace(key, "[REDACTED]")
        data = json.loads(body)
        try:
            normalized = normalize(model, data)
        except (KeyError, IndexError, TypeError, ValueError):
            return {"status": "response_error", "raw_response": data,
                    "error": "Unsupported provider response", "latency_s": time.monotonic() - start}
        return {"status": "ok", **normalized, "raw_response": data,
                "request_params": {k: v for k, v in payload.items() if k != "messages"},
                "latency_s": time.monotonic() - start}
    except urllib.error.HTTPError as exc:
        return {"status": "transport_error", "error": f"HTTP {exc.code}",
                "latency_s": time.monotonic() - start}
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, ValueError) as exc:
        return {"status": "transport_error", "error": type(exc).__name__,
                "latency_s": time.monotonic() - start}
