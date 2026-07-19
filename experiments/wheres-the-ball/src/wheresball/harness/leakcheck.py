"""Leak check for the inpainting masking condition (design §3, condition 3).

Before an inpainted item enters the evaluation set, a detector (here: any
RawVLM) is shown the edited frame and asked whether it can see the ball or any
editing artifact. Detectable items are discarded and the discard rate is
reported, per the design's anti-leak protocol.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Sequence

from .api_clients import RawVLM

LEAK_CHECK_PROMPT = """\
This image comes from a sports match and may have been digitally edited.
Look carefully and answer ONLY with a JSON object:
{
  "ball_visible": <true if you can see a ball or ball-like object>,
  "artifact_visible": <true if you notice any editing artifact, blur patch, \
smudge or inconsistent region>,
  "explanation": "<one sentence>"
}"""

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class LeakVerdict:
    item_id: str
    ball_visible: bool
    artifact_visible: bool
    explanation: str

    @property
    def leaked(self) -> bool:
        return self.ball_visible or self.artifact_visible


@dataclass(frozen=True)
class LeakReport:
    verdicts: tuple[LeakVerdict, ...]

    @property
    def discard_rate(self) -> float:
        if not self.verdicts:
            return 0.0
        return sum(v.leaked for v in self.verdicts) / len(self.verdicts)

    def clean_ids(self) -> list[str]:
        return [v.item_id for v in self.verdicts if not v.leaked]


def parse_leak_verdict(item_id: str, text: str) -> LeakVerdict:
    match = _JSON_BLOCK.search(text)
    if not match:
        # An unparseable check is treated as leaked: never let a dubious item in.
        return LeakVerdict(item_id, True, True, f"unparseable checker output: {text[:100]!r}")
    try:
        data = json.loads(match.group(0))
        return LeakVerdict(
            item_id=item_id,
            ball_visible=bool(data["ball_visible"]),
            artifact_visible=bool(data["artifact_visible"]),
            explanation=str(data.get("explanation", "")),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return LeakVerdict(item_id, True, True, f"invalid checker JSON: {text[:100]!r}")


def run_leak_check(
    inpainted: Sequence[tuple[str, bytes]],  # (item_id, edited frame PNG)
    checker: RawVLM,
) -> LeakReport:
    verdicts = []
    for item_id, image in inpainted:
        text = checker.complete(LEAK_CHECK_PROMPT, [image])
        verdicts.append(parse_leak_verdict(item_id, text))
    return LeakReport(verdicts=tuple(verdicts))
