"""Versioned prompt templates and strict-JSON response parsing (design §5).

Prompts are frozen artifacts: any change bumps PROMPT_VERSION, and cached
responses are keyed by it, so results are always attributable to an exact
prompt text.
"""

from __future__ import annotations

import json
import re

from .schema import Knowledge, Prediction

PROMPT_VERSION = "v1"

RESPONSE_FORMAT = """\
Answer ONLY with a JSON object, no other text:
{
  "x": <number 0-1, horizontal position, 0 = left edge>,
  "y": <number 0-1, vertical position, 0 = top edge>,
  "uncertainty_radius": <number 0-1, radius within which you believe the object lies>,
  "confidence": <number 0-100, how confident you are in your point estimate>,
  "rationale": "<one or two sentences explaining your reasoning>"
}"""

# Neutral condition: no sport named, no rules — measures pure inference from
# the visual configuration (§5, "Conocimiento del juego": prompt neutro).
NEUTRAL_TEMPLATE = f"""\
The people in this image are all interacting with a single object that is not \
clearly visible. Infer where that object most likely is, using only the \
positions, postures and movement of the people.

{RESPONSE_FORMAT}"""

# Informed condition: sport + summarized rules + attention heuristics (§5).
INFORMED_TEMPLATE = f"""\
This is a football (soccer) match. The ball is not clearly visible in the \
image, but its position can be inferred from the players, as a spectator \
watching from far away would.

Use your knowledge of the game:
- Play is organized around the ball: players orient their bodies and gaze toward it.
- Players near the ball move faster and more purposefully; those far away hold formation.
- The team in possession spreads out; the defending team compacts around the ball's zone.
- A sprinting cluster or a sudden convergence of players signals where the ball is going.

Infer where the ball most likely is right now.

{RESPONSE_FORMAT}"""

TEMPLATES: dict[tuple[str, Knowledge], str] = {
    (PROMPT_VERSION, Knowledge.NEUTRAL): NEUTRAL_TEMPLATE,
    (PROMPT_VERSION, Knowledge.INFORMED): INFORMED_TEMPLATE,
}


def build_prompt(knowledge: Knowledge, version: str = PROMPT_VERSION) -> str:
    return TEMPLATES[(version, knowledge)]


class ResponseParseError(ValueError):
    pass


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def parse_prediction(text: str) -> Prediction:
    """Parse a model response into a `Prediction`, tolerating surrounding
    prose or markdown fences but validating types and ranges strictly."""
    match = _JSON_BLOCK.search(text)
    if not match:
        raise ResponseParseError(f"no JSON object found in response: {text[:200]!r}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ResponseParseError(f"invalid JSON in response: {exc}") from exc

    try:
        x = float(data["x"])
        y = float(data["y"])
        radius = float(data.get("uncertainty_radius", 0.0))
        confidence = float(data.get("confidence", 50.0))
    except (KeyError, TypeError, ValueError) as exc:
        raise ResponseParseError(f"missing or non-numeric field: {exc}") from exc

    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise ResponseParseError(f"coordinates out of range: ({x}, {y})")
    if not 0 <= confidence <= 100:
        raise ResponseParseError(f"confidence out of range: {confidence}")

    return Prediction(
        x=x,
        y=y,
        uncertainty_radius=max(0.0, radius),
        confidence=confidence,
        rationale=str(data.get("rationale", "")),
    )
