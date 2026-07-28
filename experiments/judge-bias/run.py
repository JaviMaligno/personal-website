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


def judge(tasks: list[dict], outputs: list[dict], judges: list[str], workers: int,
          judge_max_tokens: int) -> list[dict]:
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
        raw = providers.complete(judge_model, prompt, max_tokens=judge_max_tokens,
                                 temperature=0.0)
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


def length_probe(tasks: list[dict], models: list[str], judges: list[str], workers: int,
                 judge_max_tokens: int) -> dict:
    """Same model, same task, two target lengths, judged against each other."""
    gen_jobs = [(t, m, v) for t in tasks for m in models for v in ("short", "long")]

    def gen_one(job):
        task, model, variant = job
        text = providers.complete(
            model, protocol.length_variant_prompt(task, variant),
            max_tokens=2048, temperature=0.0,
        )
        print(f"  generated {task['id']}/{variant} / {model}", file=sys.stderr)
        return {
            "task_id": task["id"],
            "model": model,
            "variant": variant,
            "text": text,
            **protocol.size(text),
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        outputs = list(pool.map(gen_one, gen_jobs))

    by = {(o["task_id"], o["model"], o["variant"]): o["text"] for o in outputs}
    judge_jobs = [
        (t, m, j, order)
        for t in tasks for m in models for j in judges
        for order in (("short", "long"), ("long", "short"))
    ]

    def judge_one(job):
        task, model, judge_model, (va, vb) = job
        prompt = protocol.length_judge_prompt(
            task, by[(task["id"], model, va)], by[(task["id"], model, vb)]
        )
        raw = providers.complete(judge_model, prompt, max_tokens=judge_max_tokens,
                                 temperature=0.0)
        try:
            verdict = protocol.parse_verdict(raw)
        except ValueError as e:
            print(f"  ! unparseable length verdict: {e}", file=sys.stderr)
            verdict = None
        return {
            "task_id": task["id"],
            "judge": judge_model,
            "model": model,
            "slot_a_variant": va,
            "slot_b_variant": vb,
            "verdict": verdict,
            "raw": raw,
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        judgments = list(pool.map(judge_one, judge_jobs))

    return {"tasks": tasks, "outputs": outputs, "judgments": judgments}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generators", nargs="+", required=True)
    ap.add_argument("--judges", nargs="+", required=True)
    ap.add_argument("--tasks", default=str(HERE / "tasks.json"))
    ap.add_argument("--length-tasks", default=str(HERE / "tasks-length.json"))
    ap.add_argument("--skip-length", action="store_true",
                    help="skip the length control (not recommended: the plain "
                         "longer-wins rate is uninterpretable without it)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--judge-max-tokens", type=int, default=1024,
                    help="output budget for a judgment. Reasoning models spend most of "
                         "it before the JSON verdict appears — grok-4.3 burns ~350 "
                         "tokens of reasoning on a single comparison, so the old 512 "
                         "left almost no room for the answer.")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    tasks = json.loads(pathlib.Path(args.tasks).read_text())

    print("generating...", file=sys.stderr)
    outputs = generate(tasks, args.generators, args.workers)
    print("judging...", file=sys.stderr)
    judgments = judge(tasks, outputs, args.judges, args.workers, args.judge_max_tokens)

    probe = None
    if not args.skip_length:
        print("length control...", file=sys.stderr)
        probe = length_probe(
            json.loads(pathlib.Path(args.length_tasks).read_text()),
            args.generators, args.judges, args.workers, args.judge_max_tokens,
        )

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {
            "generators": args.generators,
            "judges": args.judges,
            "execution": "api",
            "judge_max_tokens": args.judge_max_tokens,
            "notes": args.notes,
        },
        "tasks": tasks,
        "outputs": outputs,
        "judgments": judgments,
        "length_probe": probe,
    }, indent=2))
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
