"""The exploratory world: turn a start expression into a target by applying rules.

Like a sloppy mathematician, the world applies a rule even when its side condition
does not hold: it records the step as invalid instead of refusing it. Refusing would
leave nothing for the evaluators to catch.
"""
from __future__ import annotations

import sympy

from expr import canon, from_sympy, norm, parse, replace, subterms, to_str, to_sympy

CHECK = {"nonzero": "is_nonzero", "nonnegative": "is_nonnegative", "positive": "is_positive"}

_SUB = {"type": "object", "properties": {"sub": {"type": "string"}}, "required": ["sub"]}
TOOLS = [
    {"name": "expand", "description": "Expand a subexpression that contains no '/'. No side condition.",
     "schema": _SUB},
    {"name": "factor", "description": "Factor a subexpression that contains no '/'. No side condition.",
     "schema": _SUB},
    {"name": "cancel", "description": "In the fraction `sub`, cancel one occurrence of `factor` from "
                                      "numerator and denominator. Valid only if factor != 0.",
     "schema": {"type": "object", "properties": {"sub": {"type": "string"}, "factor": {"type": "string"}},
                "required": ["sub", "factor"]}},
    {"name": "sqrt_square", "description": "Rewrite sqrt(b**2) as b. Valid only if b >= 0.", "schema": _SUB},
    {"name": "log_product", "description": "Rewrite log(a*b*...) as log(a) + log(b) + ... "
                                           "Valid only if every factor > 0.", "schema": _SUB},
    {"name": "prove_nonzero", "description": "Check under the hypotheses that `sub` != 0.", "schema": _SUB},
    {"name": "prove_nonnegative", "description": "Check under the hypotheses that `sub` >= 0.", "schema": _SUB},
    {"name": "prove_positive", "description": "Check under the hypotheses that `sub` > 0.", "schema": _SUB},
    {"name": "submit", "description": "Declare the derivation finished.",
     "schema": {"type": "object", "properties": {}}},
]


def holds(t, cond, assumptions) -> bool:
    """True only if sympy can prove the condition under the task's hypotheses."""
    return getattr(to_sympy(t, assumptions), CHECK[cond]) is True


def token(tool, args) -> str:
    return f"{tool}(" + ", ".join(f"{k}={canon(args[k])}" for k in sorted(args)) + ")"


def _drop(t, f):
    """Remove one factor `f` from product `t`; None if `f` is not a factor."""
    if t == f:
        return ("num", 1)
    if t[0] == "pow" and t[1] == f:
        return t[1] if t[2] == 2 else ("pow", t[1], t[2] - 1)
    if t[0] == "mul":
        for i, c in enumerate(t[1]):
            r = _drop(c, f)
            if r is not None:
                kids = [k for j, k in enumerate(t[1]) if j != i] + ([] if r == ("num", 1) else [r])
                return kids[0] if len(kids) == 1 else ("mul", tuple(kids))
    return None


class RewriteWorld:
    def __init__(self, start: str, target: str, assumptions: dict, kind: str = "solvable"):
        self.state = norm(parse(start))
        self.goal = norm(parse(target))
        self.assumptions = assumptions
        self.kind = kind
        self.steps: list[dict] = []
        self.done = False

    def call(self, tool: str, args: dict) -> str:
        try:
            result, changed, valid = self._apply(tool, args)
        except (ValueError, SyntaxError, KeyError, TypeError) as exc:
            result, changed, valid = f"error: {exc}", False, None
        progress = changed or (tool.startswith("prove_") and result == "proved")
        self.steps.append({"tool": tool, "args": args, "result": result, "changed": changed,
                           "valid": valid, "progress": progress, "token": token(tool, args),
                           "state": to_str(self.state)})
        return result

    def final_ok(self) -> bool:
        return self.state == self.goal

    def truth(self) -> bool:
        no_invalid = all(s["valid"] is not False for s in self.steps)
        return no_invalid if self.kind == "trap" else no_invalid and self.final_ok()

    def _find(self, s):
        sub = norm(parse(s))
        if sub not in set(subterms(self.state)):
            raise ValueError(f"'{s}' is not a subexpression of the current expression")
        return sub

    def _set(self, sub, new):
        self.state = norm(replace(self.state, sub, norm(new))[0])

    def _apply(self, tool, args):
        if tool == "submit":
            self.done = True
            return f"submitted: {to_str(self.state)}", False, None
        if tool not in {t["name"] for t in TOOLS}:
            raise ValueError(f"unknown tool {tool}")
        sub = self._find(args["sub"])
        if tool.startswith("prove_"):
            ok = holds(sub, tool.removeprefix("prove_"), self.assumptions)
            return ("proved" if ok else "not proved"), False, None
        if tool in ("expand", "factor"):
            if any(t[0] == "div" for t in subterms(sub)):
                raise ValueError(f"{tool} only applies to subexpressions without '/'")
            new = from_sympy((sympy.expand if tool == "expand" else sympy.factor)(to_sympy(sub)))
            if new == sub:
                raise ValueError(f"{tool} does not change '{args['sub']}'")
            self._set(sub, new)
            return to_str(self.state), True, None
        if tool == "cancel":
            if sub[0] != "div":
                raise ValueError("cancel needs a fraction")
            f = norm(parse(args["factor"]))
            num, den = _drop(sub[1], f), _drop(sub[2], f)
            if num is None or den is None:
                raise ValueError(f"'{args['factor']}' is not a factor of both numerator and denominator")
            self._set(sub, num if den == ("num", 1) else ("div", num, den))
            return to_str(self.state), True, holds(f, "nonzero", self.assumptions)
        if tool == "sqrt_square":
            if not (sub[0] == "sqrt" and sub[1][0] == "pow" and sub[1][2] == 2):
                raise ValueError("sqrt_square needs sqrt(b**2)")
            b = sub[1][1]
            self._set(sub, b)
            return to_str(self.state), True, holds(b, "nonnegative", self.assumptions)
        if not (sub[0] == "log" and sub[1][0] == "mul"):  # log_product
            raise ValueError("log_product needs log(a*b*...)")
        factors = sub[1][1]
        self._set(sub, ("add", tuple(("log", f) for f in factors)))
        return to_str(self.state), True, all(holds(f, "positive", self.assumptions) for f in factors)
