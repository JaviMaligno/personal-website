"""Validate the hand-written tasks and attach their reference paths.

    uv run python build_tasks.py

Fails (exit 1) if a solvable task has fewer than two derivations of length
<= shortest + 2, or if a trap task turns out to have a valid derivation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import onboarding
import rewrite
from references import count_derivations, shortest, with_proofs

HERE = Path(__file__).parent


def build_rewrite(src):
    out, bad = [], []
    for t in src:
        if t["kind"] == "solvable":
            paths = shortest(t)
            n = count_derivations(t, len(paths[0]) + 2) if paths else 0
            ok = bool(paths) and n >= 2
            refs = [with_proofs(p) for p in paths]
            print(f"{t['id']} solvable shortest={len(paths[0]) if paths else None} derivations<=+2={n} {'OK' if ok else 'FAIL'}")
        else:
            ok = not shortest(t) and bool(shortest(t, allow_invalid=True))
            refs = []
            print(f"{t['id']} trap {'OK' if ok else 'FAIL'}")
        if not ok:
            bad.append(t["id"])
        out.append({**t, "references": [[{"tool": a, "args": b} for a, b in p] for p in refs],
                    "reference_tokens": [[rewrite.token(a, b) for a, b in p] for p in refs]})
    return out, bad


def build_onboarding(src):
    out = []
    for t in src:
        c = t["customer"]
        decision = onboarding.correct_decision(c)
        rules = [{"kind": "before", "first": "verify_identity", "then": "approve"},
                 {"kind": "before", "first": "check_sanctions", "then": "approve"},
                 {"kind": "before", "first": decision, "then": "log_decision"}]
        if c["amount"] > onboarding.THRESHOLD:
            rules.append({"kind": "before", "first": "assess_risk", "then": "approve"})
        if not c["identity_ok"] or c["sanctions_hit"]:
            rules.append({"kind": "forbid", "tool": "approve"})
        refs = onboarding.reference_paths(c)
        print(f"{t['id']} procedural decision={decision}")
        out.append({**t, "kind": "procedural", "rules": rules, "reference_tokens": refs})
    return out


def main():
    rw, bad = build_rewrite(json.loads((HERE / "tasks/rewrite_src.json").read_text()))
    ob = build_onboarding(json.loads((HERE / "tasks/onboarding_src.json").read_text()))
    (HERE / "tasks/rewrite.json").write_text(json.dumps(rw, indent=1))
    (HERE / "tasks/onboarding.json").write_text(json.dumps(ob, indent=1))
    if bad:
        print("FAILED:", ", ".join(bad))
        sys.exit(1)


if __name__ == "__main__":
    main()
