"""The parts of the experiment that must be identical no matter how it is run.

The pilot in results/ was produced through Claude Code subagents rather than raw
API calls, so the judge prompt, the pair enumeration and the verdict parsing all
live here — that way the two execution paths cannot silently drift apart.
"""

from __future__ import annotations

import itertools
import json
import re

# Blinded on purpose: the judge never learns which model produced which slot.
# Ties are allowed. Forcing a binary choice on two equally good answers
# manufactures coin flips that then show up as "position bias".
JUDGE_TEMPLATE = """You are evaluating two responses to the same task.

## Task given to both responders

{task}

## Response A

{a}

## Response B

{b}

## Your job

Decide which response is better for the task as stated. Judge only the responses
themselves; you have no information about who or what produced them.

Answer with a single JSON object and nothing else:

{{"winner": "A" | "B" | "tie", "reason": "<one sentence>"}}
"""


def pairs(models: list[str]) -> list[tuple[str, str]]:
    """Every unordered pair, emitted in both orders.

    Both orders is the whole point: the rate at which a judge changes its mind
    when the same two responses swap slots *is* the position bias.
    """
    out = []
    for m1, m2 in itertools.combinations(sorted(models), 2):
        out.append((m1, m2))
        out.append((m2, m1))
    return out


_JSON = re.compile(r"\{[^{}]*\}", re.S)


def parse_verdict(raw: str) -> str:
    """Pull 'A' / 'B' / 'tie' out of a judge response. Raises on anything else."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text).strip()
    blob = _JSON.search(text)
    if blob:
        try:
            winner = json.loads(blob.group(0)).get("winner")
        except json.JSONDecodeError:
            winner = None
        if isinstance(winner, str) and winner.strip().lower() in {"a", "b", "tie"}:
            return winner.strip().lower()
    bare = text.lower().strip().strip('"').strip(".")
    if bare in {"a", "b", "tie"}:
        return bare
    raise ValueError(f"could not parse a verdict from: {raw[:200]!r}")


def size(text: str) -> dict:
    return {"chars": len(text), "words": len(text.split())}
