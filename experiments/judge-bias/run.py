#!/usr/bin/env python3
"""Run the judge-bias experiment across providers.

    export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=...
    python3 run.py \
        --generators anthropic:claude-opus-4-6 openai:gpt-5 gemini:gemini-2.5-pro \
        --judges     anthropic:claude-opus-4-6 openai:gpt-5 gemini:gemini-2.5-pro \
        --out results/cross-family.json

    python3 analyze.py results/cross-family.json

Generators and judges are independent lists, but the interesting design is the
one where they overlap: self-preference can only be measured for a model that
both produces and judges.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

import protocol
import providers

HERE = pathlib.Path(__file__).parent


def generate(tasks: list[dict], models: list[str], workers: int) -> list[dict]:
    jobs = [(t, m) for t in tasks for m in models]

    def one(job):
        task, model = job
        text = providers.complete(model, task["prompt"], max_tokens=2048, temperature=0.0)
        print(f"  generated {task['id']} / {model}", file=sys.stderr)
        return {
            "task_id": task["id"],
            "model": model,
            "text": text,
            **protocol.size(text),
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, jobs))


def judge(tasks: list[dict], outputs: list[dict], judges: list[str], workers: int) -> list[dict]:
    by_task: dict[str, dict[str, str]] = {}
    for o in outputs:
        by_task.setdefault(o["task_id"], {})[o["model"]] = o["text"]

    jobs = []
    for task in tasks:
        got = by_task.get(task["id"], {})
        for slot_a, slot_b in protocol.pairs(sorted(got)):
            for j in judges:
                jobs.append((task, got, slot_a, slot_b, j))

    def one(job):
        task, got, slot_a, slot_b, judge_model = job
        prompt = protocol.JUDGE_TEMPLATE.format(
            task=task["prompt"], a=got[slot_a], b=got[slot_b]
        )
        raw = providers.complete(judge_model, prompt, max_tokens=512, temperature=0.0)
        try:
            verdict = protocol.parse_verdict(raw)
        except ValueError as e:
            print(f"  ! unparseable verdict ({judge_model}, {task['id']}): {e}", file=sys.stderr)
            verdict = None
        print(f"  judged {task['id']} {slot_a} vs {slot_b} by {judge_model} -> {verdict}",
              file=sys.stderr)
        return {
            "task_id": task["id"],
            "judge": judge_model,
            "slot_a": slot_a,
            "slot_b": slot_b,
            "verdict": verdict,
            "raw": raw,
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, jobs))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generators", nargs="+", required=True)
    ap.add_argument("--judges", nargs="+", required=True)
    ap.add_argument("--tasks", default=str(HERE / "tasks.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    tasks = json.loads(pathlib.Path(args.tasks).read_text())

    print("generating...", file=sys.stderr)
    outputs = generate(tasks, args.generators, args.workers)
    print("judging...", file=sys.stderr)
    judgments = judge(tasks, outputs, args.judges, args.workers)

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {
            "generators": args.generators,
            "judges": args.judges,
            "execution": "api",
            "notes": args.notes,
        },
        "tasks": tasks,
        "outputs": outputs,
        "judgments": judgments,
    }, indent=2))
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
