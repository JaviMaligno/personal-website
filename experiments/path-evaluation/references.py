"""Reference derivations for the rewrite world, found by search rather than written by hand.

Same criterion as CORE's golden paths: shortest, loop-free, no invalid step. Each
conditional step is preceded by the proof of its condition, the way a careful
derivation would be written.
"""
from __future__ import annotations

from functools import lru_cache

from expr import norm, parse, subterms, to_str
from rewrite import RewriteWorld

RULES = ("expand", "factor", "sqrt_square", "log_product")


def candidate_moves(state):
    for sub in dict.fromkeys(subterms(state)):
        s = to_str(sub)
        for tool in RULES:
            yield tool, {"sub": s}
        if sub[0] == "div":
            for f in dict.fromkeys(subterms(sub[1])):
                yield "cancel", {"sub": s, "factor": to_str(f)}


@lru_cache(maxsize=None)
def _successors(state, target, assumptions_items, allow_invalid):
    out = []
    for tool, args in candidate_moves(state):
        w = RewriteWorld(to_str(state), target, dict(assumptions_items))
        w.call(tool, args)
        step = w.steps[-1]
        if step["changed"] and (allow_invalid or step["valid"] is not False):
            out.append(((tool, args), w.state))
    return out


def successors(state, task, allow_invalid=False):
    return _successors(state, task["target"], tuple(sorted(task["assumptions"].items())), allow_invalid)


def shortest(task, max_depth=6, limit=2, allow_invalid=False):
    start, goal = norm(parse(task["start"])), norm(parse(task["target"]))
    frontier, seen, found = [(start, [])], {start}, []
    for _ in range(max_depth):
        nxt = []
        for state, path in frontier:
            for move, new in successors(state, task, allow_invalid):
                if new == goal:
                    found.append(path + [move])
                elif new not in seen:
                    seen.add(new)
                    nxt.append((new, path + [move]))
        if found:
            return found[:limit]
        frontier = nxt
    return []


def count_derivations(task, max_len):
    """Number of valid derivations (walks to the goal) of length <= max_len."""
    goal = norm(parse(task["target"]))

    @lru_cache(maxsize=None)
    def paths(state, remaining):
        total = 0
        for _, new in successors(state, task):
            if new == goal:
                total += 1
            elif remaining > 1:
                total += paths(new, remaining - 1)
        return total

    return paths(norm(parse(task["start"])), max_len)


def with_proofs(path):
    out = []
    for tool, args in path:
        if tool == "cancel":
            out.append(("prove_nonzero", {"sub": args["factor"]}))
        elif tool == "sqrt_square":
            out.append(("prove_nonnegative", {"sub": to_str(norm(parse(args["sub"]))[1][1])}))
        elif tool == "log_product":
            for f in norm(parse(args["sub"]))[1][1]:
                out.append(("prove_positive", {"sub": to_str(f)}))
        out.append((tool, args))
    return out
