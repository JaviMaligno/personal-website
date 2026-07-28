#!/usr/bin/env python3
"""Build blinded judging batches for the subagent-executed pilot.

The pilot could not use run.py: this environment has no provider API keys, only
Claude Code subagents. So generation and judging happen through agents, and this
script does the bookkeeping run.py would otherwise do — pair enumeration, slot
assignment, and (critically) keeping the model identities out of anything a
judge can see.

Writes, into results/pilot-raw/:
  batch-ab.json   comparisons in canonical slot order   (no model names)
  batch-ba.json   the same comparisons, slots swapped   (no model names)
  key.json        comparison_id -> which model sat in which slot
"""

from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "results" / "pilot-raw"

sys.path.insert(0, str(ROOT))
import protocol  # noqa: E402

MODELS = ["opus", "sonnet", "haiku"]


def main() -> int:
    tasks = json.loads((ROOT / "tasks.json").read_text())
    outputs = {
        m: {o["task_id"]: o["text"] for o in json.loads((RAW / f"gen-{m}.json").read_text())}
        for m in MODELS
    }

    ab, ba, key = [], [], {}
    for task in tasks:
        # protocol.pairs emits both orders; take the canonical half and derive
        # the swapped half from it, so the two batches are exactly paired.
        canonical = [p for p in protocol.pairs(MODELS) if p[0] <= p[1]]
        for m1, m2 in canonical:
            cid = f"{task['id']}__{m1}_vs_{m2}"
            key[cid] = {"task_id": task["id"], "slot_a": m1, "slot_b": m2}
            ab.append({
                "comparison_id": cid,
                "prompt": protocol.JUDGE_TEMPLATE.format(
                    task=task["prompt"], a=outputs[m1][task["id"]], b=outputs[m2][task["id"]]
                ),
            })
            ba.append({
                "comparison_id": cid,
                "prompt": protocol.JUDGE_TEMPLATE.format(
                    task=task["prompt"], a=outputs[m2][task["id"]], b=outputs[m1][task["id"]]
                ),
            })

    (RAW / "batch-ab.json").write_text(json.dumps(ab, indent=2))
    (RAW / "batch-ba.json").write_text(json.dumps(ba, indent=2))
    (RAW / "key.json").write_text(json.dumps(key, indent=2))

    leak = [m for m in MODELS if any(m in c["prompt"] for c in ab + ba)]
    print(f"{len(ab)} comparisons per order, {len(key)} keyed")
    print(f"blinding check — model names appearing in batch prompts: {leak or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
