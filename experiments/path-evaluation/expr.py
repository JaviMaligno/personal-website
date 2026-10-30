"""Expression trees that never simplify on their own.

sympy auto-cancels x*y/x and (x+1)/(x+1) at construction time, which would let an
agent cancel a factor without any rule, and without any side condition. So the
state of the rewrite world is a plain tuple tree; sympy is only consulted to check
conditions and to compute what expand/factor produce.

Node shapes:
    ("num", int) ("sym", str) ("add", (t, ...)) ("mul", (t, ...))
    ("div", num, den) ("pow", base, int) ("sqrt", t) ("log", t) ("neg", t)
"""
from __future__ import annotations

import ast

import sympy

PREC = {"add": 1, "mul": 2, "div": 2, "neg": 3, "pow": 4,
        "num": 5, "sym": 5, "sqrt": 5, "log": 5}
ASSUME = {"positive": {"positive": True},
          "nonzero": {"real": True, "nonzero": True},
          "real": {"real": True}}


def to_str(t) -> str:
    k = t[0]
    if k == "num":
        return str(t[1])
    if k == "sym":
        return t[1]
    if k in ("sqrt", "log"):
        return f"{k}({to_str(t[1])})"
    if k == "neg":
        return "-" + _wrap(t[1], 3)
    if k == "pow":
        return f"{_wrap(t[1], 5)}**{t[2]}"
    if k == "mul":
        return "*".join(_wrap(c, 2.5) for c in t[1])
    if k == "div":
        return f"{_wrap(t[1], 2)}/{_wrap(t[2], 5)}"
    out = to_str(t[1][0])
    for c in t[1][1:]:
        out += f" - {_wrap(c[1], 1.5)}" if c[0] == "neg" else f" + {_wrap(c, 1.5)}"
    return out


def _wrap(t, need) -> str:
    s = to_str(t)
    return f"({s})" if PREC[t[0]] < need else s


def parse(s: str):
    return _from_ast(ast.parse(s.strip(), mode="eval").body)


def _from_ast(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, int):
        return ("num", n.value)
    if isinstance(n, ast.Name):
        return ("sym", n.id)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
        return ("neg", _from_ast(n.operand))
    if isinstance(n, ast.BinOp):
        a, b = _from_ast(n.left), _from_ast(n.right)
        if isinstance(n.op, ast.Add):
            return _flat("add", [a, b])
        if isinstance(n.op, ast.Sub):
            return _flat("add", [a, ("neg", b)])
        if isinstance(n.op, ast.Mult):
            return _flat("mul", [a, b])
        if isinstance(n.op, ast.Div):
            return ("div", a, b)
        if isinstance(n.op, ast.Pow) and b[0] == "num":
            return ("pow", a, b[1])
    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id in ("sqrt", "log") and len(n.args) == 1):
        return (n.func.id, _from_ast(n.args[0]))
    raise ValueError(f"unsupported expression: {ast.unparse(n)}")


def _flat(kind, items):
    out = []
    for it in items:
        out.extend(it[1] if it[0] == kind else [it])
    return (kind, tuple(out))


def _key(kind, c):
    # Sums read "x + 1" and "x - 1"; products put the number first ("2*x").
    if kind == "add":
        return (c[0] == "num", c[0] == "neg", to_str(c))
    return (c[0] not in ("num", "neg"), to_str(c))


def norm(t):
    k = t[0]
    if k in ("add", "mul"):
        kids = _flat(k, [norm(c) for c in t[1]])[1]
        return (k, tuple(sorted(kids, key=lambda c: _key(k, c))))
    if k == "div":
        return ("div", norm(t[1]), norm(t[2]))
    if k == "pow":
        return ("pow", norm(t[1]), t[2])
    if k in ("sqrt", "log", "neg"):
        return (k, norm(t[1]))
    return t


def subterms(t):
    yield t
    k = t[0]
    if k in ("add", "mul"):
        for c in t[1]:
            yield from subterms(c)
    elif k == "div":
        yield from subterms(t[1])
        yield from subterms(t[2])
    elif k in ("pow", "sqrt", "log", "neg"):
        yield from subterms(t[1])


def replace(t, old, new):
    """Replace the first occurrence (preorder) of `old`. Returns (tree, replaced)."""
    if t == old:
        return new, True
    k = t[0]
    if k in ("add", "mul"):
        kids = list(t[1])
        for i, c in enumerate(kids):
            r, ok = replace(c, old, new)
            if ok:
                kids[i] = r
                return (k, tuple(kids)), True
        return t, False
    if k == "div":
        r, ok = replace(t[1], old, new)
        if ok:
            return ("div", r, t[2]), True
        r, ok = replace(t[2], old, new)
        return (("div", t[1], r), True) if ok else (t, False)
    if k == "pow":
        r, ok = replace(t[1], old, new)
        return ("pow", r, t[2]), ok
    if k in ("sqrt", "log", "neg"):
        r, ok = replace(t[1], old, new)
        return (k, r), ok
    return t, False


def to_sympy(t, assumptions: dict | None = None):
    loc = {name: sympy.Symbol(name, **ASSUME[a]) for name, a in (assumptions or {}).items()}
    loc.update(sqrt=sympy.sqrt, log=sympy.log)
    return sympy.sympify(to_str(t), locals=loc)


def from_sympy(e):
    return norm(parse(str(e)))


def canon(v) -> str:
    """Canonical spelling of an argument; non-expressions are kept as given."""
    try:
        return to_str(norm(parse(str(v))))
    except (ValueError, SyntaxError):
        return str(v)
