"""Render a neutral conversation for each provider and make one HTTP call.

One request per attempt; no invisible retries. Credentials are never logged.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

GCLOUD = str(Path.home() / "Downloads/google-cloud-sdk/bin/gcloud")
_token = {"value": None, "at": 0.0}


def gcloud_token(force=False):
    if force or not _token["value"] or time.time() - _token["at"] > 600:
        proc = subprocess.run([GCLOUD, "auth", "print-access-token"],
                              capture_output=True, text=True, timeout=180)
        if proc.returncode or not proc.stdout.strip():
            raise RuntimeError("gcloud login unavailable; run `gcloud auth login`")
        _token.update(value=proc.stdout.strip(), at=time.time())
    return _token["value"]


# ---------- rendering ----------

def render_anthropic(system, msgs, tools):
    out = []
    for m in msgs:
        if m["role"] == "assistant" and m.get("raw_kind") == "anthropic":
            out.append({"role": "assistant", "content": m["raw"]})
            continue
        if m["role"] == "assistant":
            content = [{"type": "text", "text": m["text"]}] if m["text"] else []
            content += [{"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["input"]}
                        for c in m["tool_calls"]]
            if m.get("cache"):
                content[-1]["cache_control"] = {"type": "ephemeral"}
            out.append({"role": "assistant", "content": content})
            continue
        block = ({"type": "tool_result", "tool_use_id": m["id"], "content": m["content"]}
                 if m["role"] == "tool" else {"type": "text", "text": m["text"]})
        if out and out[-1]["role"] == "user":
            out[-1]["content"].append(block)
        else:
            out.append({"role": "user", "content": [block]})
    return {"system": system, "messages": out,
            "tools": [{"name": t["name"], "description": t["description"],
                       "input_schema": t["schema"]} for t in tools]}


def render_openai(system, msgs, tools):
    out = [{"role": "system", "content": system}]
    for m in msgs:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["text"]})
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": m["id"], "content": m["content"]})
        elif m.get("raw_kind") == "openai":
            out.append(m["raw"])
        else:
            msg = {"role": "assistant", "content": m["text"] or None}
            if m["tool_calls"]:
                msg["tool_calls"] = [{"id": c["id"], "type": "function",
                                      "function": {"name": c["name"],
                                                   "arguments": json.dumps(c["input"])}}
                                     for c in m["tool_calls"]]
            out.append(msg)
    return {"messages": out,
            "tools": [{"type": "function", "function": {"name": t["name"],
                       "description": t["description"], "parameters": t["schema"]}}
                      for t in tools]}


def render_gemini(system, msgs, tools):
    contents = []
    for m in msgs:
        if m["role"] == "assistant" and m.get("raw_kind") == "gemini":
            contents.append({"role": "model", "parts": m["raw"]})
            continue
        if m["role"] == "assistant":
            parts = [{"text": m["text"]}] if m["text"] else []
            # History was not produced by this model, so there is no real thought signature.
            parts += [{"functionCall": {"name": c["name"], "args": c["input"]},
                       "thoughtSignature": "skip_thought_signature_validator"}
                      for c in m["tool_calls"]]
            contents.append({"role": "model", "parts": parts})
            continue
        part = ({"functionResponse": {"name": m["name"], "response": {"content": m["content"]}}}
                if m["role"] == "tool" else {"text": m["text"]})
        if contents and contents[-1]["role"] == "user":
            contents[-1]["parts"].append(part)
        else:
            contents.append({"role": "user", "parts": [part]})
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents}
    if tools:
        body["tools"] = [{"functionDeclarations": [{"name": t["name"], "description": t["description"],
                                                    "parameters": t["schema"]} for t in tools]}]
    return body


def render_responses(system, msgs, tools):
    """OpenAI Responses API. The model's own turns are replayed as its raw output items."""
    items = []
    for m in msgs:
        if m["role"] == "user":
            items.append({"role": "user", "content": m["text"]})
        elif m["role"] == "tool":
            items.append({"type": "function_call_output", "call_id": m["id"], "output": m["content"]})
        elif m.get("raw_kind") == "responses":
            items.extend(m["raw"])
        else:
            if m["text"]:
                items.append({"role": "assistant", "content": m["text"]})
            items += [{"type": "function_call", "call_id": c["id"], "name": c["name"],
                       "arguments": json.dumps(c["input"])} for c in m["tool_calls"]]
    body = {"instructions": system, "input": items}
    if tools:
        body["tools"] = [{"type": "function", "name": t["name"], "description": t["description"],
                          "parameters": t["schema"]} for t in tools]
    return body


# ---------- calls ----------

def _post(url, headers, payload, secret):
    req = urllib.request.Request(url, method="POST", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode().replace(secret, "[REDACTED]"))


def call(model, system, msgs, tools):
    """Return a normalized result. On a Vertex 401, refresh the gcloud token and retry once:
    `gcloud auth print-access-token` can hand back a cached token about to expire."""
    r = _call(model, system, msgs, tools)
    for attempt in range(6):  # rate limit only: the same request, later; counted in the record
        if not r.get("error", "").startswith("HTTP 429"):
            break
        time.sleep(min(120, 10 * 2 ** attempt))
        r = _call(model, system, msgs, tools)
        r["rate_limit_retries"] = attempt + 1
    if model["transport"].startswith("vertex") and r.get("error", "").startswith("HTTP 401"):
        try:
            gcloud_token(force=True)
        except RuntimeError as exc:  # login itself expired: record, don't crash the run
            return {**r, "error": f"{r['error']} | refresh failed: {exc}"}
        r = _call(model, system, msgs, tools)
        r["token_refreshed"] = True
    return r


def _call(model, system, msgs, tools):
    kind = model["transport"]
    start = time.monotonic()
    try:
        if kind == "vertex_anthropic":
            tok = gcloud_token()
            body = render_anthropic(system, msgs, tools)
            if not tools:
                body.pop("tools")
            body.update(anthropic_version="vertex-2023-10-16", max_tokens=model["max_tokens"],
                        **model.get("params", {}))
            url = (f"https://aiplatform.googleapis.com/v1/projects/{model['project']}/locations/"
                   f"global/publishers/anthropic/models/{model['model']}:rawPredict")
            data = _post(url, {"Authorization": f"Bearer {tok}",
                               "x-goog-user-project": model["project"]}, body, tok)
            blocks = data["content"]
            res = {"text": "".join(b["text"] for b in blocks if b["type"] == "text"),
                   "tool_calls": [{"id": b["id"], "name": b["name"], "input": b["input"]}
                                  for b in blocks if b["type"] == "tool_use"],
                   "stop": data["stop_reason"], "usage": data.get("usage", {}),
                   "response_id": data.get("id"), "raw_kind": "anthropic", "raw": blocks}
        elif kind == "vertex_gemini":
            tok = gcloud_token()
            body = render_gemini(system, msgs, tools)
            body["generationConfig"] = {"maxOutputTokens": model["max_tokens"],
                                        **model.get("params", {})}
            url = (f"https://aiplatform.googleapis.com/v1beta1/projects/{model['project']}/"
                   f"locations/global/publishers/google/models/{model['model']}:generateContent")
            data = _post(url, {"Authorization": f"Bearer {tok}",
                               "x-goog-user-project": model["project"]}, body, tok)
            cand = data["candidates"][0]
            parts = cand.get("content", {}).get("parts", [])
            res = {"text": "".join(p.get("text", "") for p in parts if not p.get("thought")),
                   "tool_calls": [{"id": f"g{i}", "name": p["functionCall"]["name"],
                                   "input": p["functionCall"].get("args", {})}
                                  for i, p in enumerate(q for q in parts if "functionCall" in q)],
                   "stop": cand.get("finishReason"), "usage": data.get("usageMetadata", {}),
                   "response_id": data.get("responseId"), "raw_kind": "gemini", "raw": parts}
        elif kind == "openai":
            key = Path(model["key_file"]).expanduser().read_text().strip()
            body = render_openai(system, msgs, tools)
            body.update(model=model["model"], max_completion_tokens=model["max_tokens"],
                        **model.get("params", {}))
            if not tools:
                body.pop("tools")
            auth = ({"api-key": key} if model.get("auth_header") == "api-key"
                    else {"Authorization": f"Bearer {key}"})
            data = _post(model["endpoint"], auth, body, key)
            choice = data["choices"][0]
            msg = choice["message"]
            res = {"text": msg.get("content") or "",
                   "tool_calls": [{"id": c["id"], "name": c["function"]["name"],
                                   "input": json.loads(c["function"]["arguments"] or "{}")}
                                  for c in msg.get("tool_calls") or []],
                   "stop": choice["finish_reason"], "usage": data.get("usage", {}),
                   "response_id": data.get("id"), "raw_kind": "openai",
                   "raw": {k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")}}
        elif kind == "responses":
            key = Path(model["key_file"]).expanduser().read_text().strip()
            body = render_responses(system, msgs, tools)
            body.update(model=model["model"], max_output_tokens=model["max_tokens"],
                        **model.get("params", {}))
            data = _post(model["endpoint"], {"api-key": key}, body, key)
            out = data.get("output", [])
            text = "".join(c.get("text", "") for o in out if o.get("type") == "message"
                           for c in o.get("content", []) if c.get("type") == "output_text")
            res = {"text": text,
                   "tool_calls": [{"id": o["call_id"], "name": o["name"],
                                   "input": json.loads(o.get("arguments") or "{}")}
                                  for o in out if o.get("type") == "function_call"],
                   "stop": data.get("status"), "usage": data.get("usage", {}),
                   "response_id": data.get("id"), "raw_kind": "responses", "raw": out}
        else:
            raise ValueError(f"unknown transport {kind}")
        return {"status": "ok", **res, "latency_s": round(time.monotonic() - start, 2)}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        return {"status": "http_error", "error": f"HTTP {exc.code}: {detail}",
                "latency_s": round(time.monotonic() - start, 2)}
    except (urllib.error.URLError, TimeoutError, OSError, KeyError, IndexError,
            ValueError, RuntimeError) as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"[:500],
                "latency_s": round(time.monotonic() - start, 2)}
