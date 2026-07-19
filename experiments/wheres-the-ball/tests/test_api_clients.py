import base64
import json

import pytest

from wheresball.dataset import generate_items
from wheresball.harness.api_clients import (
    AnthropicRaw,
    ApiVLMClient,
    GeminiRaw,
    OpenAIRaw,
    TransportError,
)
from wheresball.prompts import ResponseParseError
from wheresball.schema import Condition, Knowledge, Masking, TemporalContext
from wheresball.viz import synthetic_image_provider

CONDITION = Condition(TemporalContext.SINGLE_FRAME, Knowledge.NEUTRAL, Masking.NATURAL)
PNG = b"\x89PNG\r\n\x1a\nfakebytes"
GOOD_JSON = '{"x": 0.4, "y": 0.6, "uncertainty_radius": 0.1, "confidence": 60, "rationale": "r"}'


@pytest.fixture(autouse=True)
def api_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-a")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-o")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-g")


class RecordingTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, payload):
        self.calls.append({"url": url, "headers": headers, "payload": payload})
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_anthropic_payload_and_parse():
    transport = RecordingTransport([
        {"content": [{"type": "text", "text": GOOD_JSON}]},
    ])
    raw = AnthropicRaw(model_id="claude-test", transport=transport)
    text = raw.complete("find it", [PNG])
    assert json.loads(text)["x"] == 0.4

    call = transport.calls[0]
    assert call["headers"]["x-api-key"] == "test-key-a"
    assert call["payload"]["model"] == "claude-test"
    assert call["payload"]["temperature"] == 0
    image_block, text_block = call["payload"]["messages"][0]["content"]
    assert image_block["source"]["data"] == base64.b64encode(PNG).decode()
    assert text_block["text"] == "find it"


def test_openai_payload_and_parse():
    transport = RecordingTransport([
        {"choices": [{"message": {"content": GOOD_JSON}}]},
    ])
    raw = OpenAIRaw(model_id="gpt-test", transport=transport)
    assert raw.complete("p", [PNG]) == GOOD_JSON
    payload = transport.calls[0]["payload"]
    assert payload["messages"][0]["content"][0]["image_url"]["url"].startswith(
        "data:image/png;base64,"
    )


def test_gemini_payload_and_parse():
    transport = RecordingTransport([
        {"candidates": [{"content": {"parts": [{"text": GOOD_JSON}]}}]},
    ])
    raw = GeminiRaw(model_id="gemini-test", transport=transport)
    assert raw.complete("p", [PNG, PNG]) == GOOD_JSON
    call = transport.calls[0]
    assert "gemini-test:generateContent" in call["url"]
    assert len(call["payload"]["contents"][0]["parts"]) == 3  # 2 images + text


def test_retry_on_429_then_success():
    sleeps = []
    transport = RecordingTransport([
        TransportError("rate limited", status=429),
        TransportError("overloaded", status=529),
        {"content": [{"type": "text", "text": "ok"}]},
    ])
    raw = AnthropicRaw(transport=transport, sleep=sleeps.append, backoff_s=1.0)
    assert raw.complete("p", []) == "ok"
    assert sleeps == [1.0, 2.0]  # exponential backoff


def test_no_retry_on_client_error():
    transport = RecordingTransport([TransportError("bad request", status=400)])
    raw = AnthropicRaw(transport=transport, sleep=lambda s: None)
    with pytest.raises(TransportError):
        raw.complete("p", [])
    assert len(transport.calls) == 1


def test_missing_key_raises_helpfully(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    raw = AnthropicRaw(transport=RecordingTransport([]))
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        raw.complete("p", [])


class FakeRaw:
    model_id = "fake"

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def complete(self, prompt, images):
        self.prompts.append(prompt)
        return self.replies.pop(0)


def test_api_client_predicts_via_provider():
    item = generate_items(4, seed=0)[0]
    raw = FakeRaw([GOOD_JSON])
    client = ApiVLMClient(raw, image_provider=synthetic_image_provider((160, 100)))
    pred = client.predict(item, CONDITION, "prompt")
    assert pred.x == pytest.approx(0.4)
    assert pred.confidence == 60


def test_api_client_reparse_retry_then_fail():
    item = generate_items(4, seed=0)[0]
    raw = FakeRaw(["gibberish", GOOD_JSON])
    client = ApiVLMClient(raw, image_provider=synthetic_image_provider((160, 100)))
    pred = client.predict(item, CONDITION, "prompt")
    assert pred.y == pytest.approx(0.6)
    assert "ONLY the JSON" in raw.prompts[1]

    raw2 = FakeRaw(["gibberish", "still gibberish"])
    client2 = ApiVLMClient(raw2, image_provider=synthetic_image_provider((160, 100)))
    with pytest.raises(ResponseParseError):
        client2.predict(item, CONDITION, "prompt")
