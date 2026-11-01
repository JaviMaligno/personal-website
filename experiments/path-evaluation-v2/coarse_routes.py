"""Sensitivity check on the Lean strategy skeleton, which is our translation of CORE to proofs and
counts every `have` as an auxiliary lemma. A deliberately coarse route class keeps only what no
one would call style: what the proof inducts on (and how it generalises), whether it relies on a
helper lemma declared in the file, and whether it uses no induction at all.

    uv run python coarse_routes.py
"""
from __future__ import annotations

import json
import re
from collections import defaultdict

import analyze
import world_b

INDUCT = re.compile(r"\b(induction|fun_induction|induction_on|Nat\.rec|strongRecOn|rec_on)\b\s*([^\s,]*)")


def statement_args(t: dict) -> set[str]:
    """Names bound in the theorem's own binders: inducting on one of them is a real choice; any
    other name is a variable the model introduced itself (in a `have` or helper), named at will."""
    names = set()
    for group in re.findall(r"[({]([^:(){}]+):", t["statement"]):
        names.update(group.split())
    return names


def coarse(t: dict, text: str | None, body: str | None = None) -> tuple:
    body = body if body is not None else world_b.proof_body(t, text)
    args = statement_args(t)
    targets = tuple(sorted({(m.group(1).split(".")[-1], m.group(2).rstrip(",") if m.group(2).rstrip(",") in args else "local")
                            for m in INDUCT.finditer(body)}))
    generalizing = "generalizing" in body or "revert" in body
    helper = False
    if text is not None:
        helpers = re.findall(r"^(?:theorem|lemma)\s+([\w.']+)", world_b.strip_comments(text), re.M)
        helper = any(h != t["name"] and re.search(rf"\b{re.escape(h)}\b", body) for h in helpers)
    return (targets or ("no induction",), generalizing, helper)


def main() -> None:
    recs = [r for r in analyze.load(*analyze.SOURCES, sources=analyze.SOURCES)
            if r["world"] == "b" and r["judge"].get("truth_lenient", r["judge"]["truth"])]
    by_task = defaultdict(list)
    for r in recs:
        by_task[r["task"]].append(r)
    classes, outside, total = {}, 0, 0
    for task, rs in sorted(by_task.items()):
        t = json.loads((analyze.HERE / "theorems" / f"{task}.json").read_text(encoding="utf-8"))
        # references are proof bodies only; a helper lemma inside them shows up as `have`/aux text
        refs = {coarse(t, None, p)[:2] for p in t["proofs"]}
        cs = [coarse(t, r["final"]) for r in rs]
        classes[task] = len(set(cs))
        outside += sum(c[:2] not in refs for c in cs)
        total += len(cs)
    multi = sum(n >= 2 for n in classes.values())
    print(f"valid proofs: {total}; theorems with >=2 coarse routes: {multi} of {len(classes)}; "
          f"max routes on one theorem: {max(classes.values())}")
    print(f"valid proofs whose induction target/generalisation matches neither reference: {outside}")
    print(dict(sorted(classes.items())))


if __name__ == "__main__":
    main()
