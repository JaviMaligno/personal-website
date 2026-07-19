import pytest

from wheresball.prompts import (
    PROMPT_VERSION,
    ResponseParseError,
    build_prompt,
    parse_prediction,
)
from wheresball.schema import Knowledge


def test_templates_exist_and_differ():
    neutral = build_prompt(Knowledge.NEUTRAL)
    informed = build_prompt(Knowledge.INFORMED)
    assert neutral != informed
    # The neutral prompt must not leak the sport (§5).
    assert "football" not in neutral.lower()
    assert "ball" not in neutral.lower().replace("football", "")
    assert "football" in informed.lower()
    assert "JSON" in neutral and "JSON" in informed


def test_unknown_version_raises():
    with pytest.raises(KeyError):
        build_prompt(Knowledge.NEUTRAL, version="v999")
    assert PROMPT_VERSION == "v1"


def test_parse_valid_response_with_prose():
    text = """Sure! Here is my answer:
    ```json
    {"x": 0.42, "y": 0.13, "uncertainty_radius": 0.08, "confidence": 70,
     "rationale": "players converge on the left wing"}
    ```"""
    pred = parse_prediction(text)
    assert pred.x == pytest.approx(0.42)
    assert pred.y == pytest.approx(0.13)
    assert pred.confidence == 70
    assert "wing" in pred.rationale


def test_parse_defaults_for_optional_fields():
    pred = parse_prediction('{"x": 0.5, "y": 0.5}')
    assert pred.uncertainty_radius == 0.0
    assert pred.confidence == 50.0


@pytest.mark.parametrize(
    "text",
    [
        "no json here",
        '{"x": 1.5, "y": 0.5}',            # out of range
        '{"x": 0.5}',                       # missing y
        '{"x": 0.5, "y": 0.5, "confidence": 200}',
        '{"x": "left", "y": 0.5}',          # non-numeric
    ],
)
def test_parse_rejects_invalid(text):
    with pytest.raises(ResponseParseError):
        parse_prediction(text)
