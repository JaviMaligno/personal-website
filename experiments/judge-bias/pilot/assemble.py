#!/usr/bin/env python3
"""Fold the subagent pilot output into the same results schema run.py produces,
so analyze.py cannot tell the two execution paths apart.

    python3 pilot/assemble.py
    python3 analyze.py results/pilot-claude-family.json
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

# Short name used in the raw files -> the id reported in the results.
NAMES = {"opus": "opus-5", "sonnet": "sonnet-5", "haiku": "haiku-4.5"}


def assemble_length(missing: list) -> dict | None:
    """The length control, in the shape run.py's length_probe() emits."""
    if not (RAW / "lenkey.json").exists():
        return None
    key = json.loads((RAW / "lenkey.json").read_text())
    # Only the tasks this pilot actually ran — the task file grows, the raw data doesn't.
    ran = {k["task_id"] for k in key.values()}
    tasks = [t for t in json.loads((ROOT / "tasks-length.json").read_text()) if t["id"] in ran]

    outputs = []
    for short, name in NAMES.items():
        for o in json.loads((RAW / f"len-{short}.json").read_text()):
            outputs.append({
                "task_id": o["task_id"],
                "model": name,
                "variant": o["variant"],
                "text": o["text"],
                **protocol.size(o["text"]),
            })

    judgments = []
    for short, name in NAMES.items():
        for order in ("sl", "ls"):
            path = RAW / f"lenjudge-{short}-{order}.json"
            if not path.exists():
                missing.append(path.name)
                continue
            seen = set()
            for v in json.loads(path.read_text()):
                k = key[v["comparison_id"]]
                seen.add(v["comparison_id"])
                va, vb = ("short", "long") if order == "sl" else ("long", "short")
                judgments.append({
                    "task_id": k["task_id"],
                    "judge": name,
                    "model": NAMES[k["model"]],
                    "slot_a_variant": va,
                    "slot_b_variant": vb,
                    "verdict": protocol.parse_verdict(json.dumps({"winner": v["verdict"]})),
                    "raw": v.get("reason", ""),
                })
            gap = set(key) - seen
            if gap:
                missing.append(f"{path.name}: {len(gap)} missing")

    return {"tasks": tasks, "outputs": outputs, "judgments": judgments}


def main() -> int:
    key = json.loads((RAW / "key.json").read_text())
    ran = {k["task_id"] for k in key.values()}
    tasks = [t for t in json.loads((ROOT / "tasks.json").read_text()) if t["id"] in ran]

    outputs = []
    for short, name in NAMES.items():
        for o in json.loads((RAW / f"gen-{short}.json").read_text()):
            outputs.append({
                "task_id": o["task_id"],
                "model": name,
                "text": o["text"],
                **protocol.size(o["text"]),
            })

    judgments, missing = [], []
    for short, name in NAMES.items():
        for order in ("ab", "ba"):
            path = RAW / f"judge-{short}-{order}.json"
            if not path.exists():
                missing.append(path.name)
                continue
            seen = set()
            for v in json.loads(path.read_text()):
                cid = v["comparison_id"]
                k = key[cid]
                seen.add(cid)
                # In the 'ba' batch the two responses were shown swapped, so the
                # slot a model is the one the key calls slot_b.
                a, b = (k["slot_a"], k["slot_b"]) if order == "ab" else (k["slot_b"], k["slot_a"])
                judgments.append({
                    "task_id": k["task_id"],
                    "judge": name,
                    "slot_a": NAMES[a],
                    "slot_b": NAMES[b],
                    "verdict": protocol.parse_verdict(json.dumps({"winner": v["verdict"]})),
                    "raw": v.get("reason", ""),
                })
            gap = set(key) - seen
            if gap:
                missing.append(f"{path.name}: {len(gap)} comparisons missing")

    probe = assemble_length(missing)

    if missing:
        print("INCOMPLETE:", "; ".join(missing), file=sys.stderr)
        return 1

    out = ROOT / "results" / "pilot-claude-family.json"
    out.write_text(json.dumps({
        "meta": {
            "generators": list(NAMES.values()),
            "judges": list(NAMES.values()),
            "execution": "claude-code-subagents",
            "notes": (
                "Within-family pilot. Generation and judging ran through Claude Code "
                "subagents, not raw API calls, so each model carried a coding-agent "
                "system prompt. Judges saw 18 blinded comparisons per batch in one "
                "context, and the two presentation orders were separate contexts. "
                "Judges were forbidden from executing code, so even the low-subjectivity "
                "tasks were graded by reading, not by running tests."
            ),
        },
        "tasks": tasks,
        "outputs": outputs,
        "judgments": judgments,
        "length_probe": probe,
    }, indent=2))
    print(f"wrote {out}: {len(outputs)} outputs, {len(judgments)} judgments"
          + (f", + {len(probe['judgments'])} length-control judgments" if probe else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
