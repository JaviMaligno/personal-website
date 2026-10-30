"""The four evaluators, from least to most specification of the path.

E0 final state; E1 + forbidden actions; E2 + ordering obligations; E3 + similarity
to a reference path (CORE's Path Correctness). E1 and E2 read hand-written per-task
rules; they are deliberately coarse and are not the semantic truth.
"""
from __future__ import annotations

from expr import canon


def levenshtein(a, b) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def nld(a, b) -> float:
    ld = levenshtein(a, b)
    return 0.0 if ld == 0 else 2 * ld / (len(a) + len(b) + ld)


def pc(tokens, refs) -> float:
    return max(1 - nld(tokens, r) for r in refs)


def condensed(steps) -> list[str]:
    return [s["token"] for s in steps if s["progress"]]


def _executed(s) -> bool:
    return not str(s["result"]).startswith("error")


def _forbidden(s, rule) -> bool:
    return (s["tool"] == rule["tool"] and _executed(s)
            and all(canon(s["args"].get(k, "")) == canon(v) for k, v in rule.get("args", {}).items()))


def _out_of_order(steps, rule) -> bool:
    for i, s in enumerate(steps):
        if s["tool"] == rule["then"] and s["progress"]:
            if not any(p["tool"] == rule["first"] and p["progress"] for p in steps[:i]):
                return True
    return False


def e0(trace) -> bool:
    return bool(trace["final_ok"])


def e1(trace, rules) -> bool:
    forbids = [r for r in rules if r["kind"] == "forbid"]
    return e0(trace) and not any(_forbidden(s, r) for s in trace["steps"] for r in forbids)


def e2(trace, rules) -> bool:
    befores = [r for r in rules if r["kind"] == "before"]
    return e1(trace, rules) and not any(_out_of_order(trace["steps"], r) for r in befores)


def e3(trace, refs, tau=0.8):
    if not refs:
        return None
    return e0(trace) and pc(condensed(trace["steps"]), refs) >= tau
