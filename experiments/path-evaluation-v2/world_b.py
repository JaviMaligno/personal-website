"""Part B: a core-Lean theorem; truth = compiles, statement intact, no sorry, standard axioms only."""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

from pc import pc

STD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
FORBIDDEN = re.compile(r"\b(sorry|admit|axiom|native_decide|implemented_by|extern)\b")


SCOPE_CMDS = re.compile(r"(?<![\w.'])(namespace|section|open|notation|macro|macro_rules|syntax|infix|infixl|infixr|prefix|postfix)(?![\w.'])")


def header(t: dict) -> str:
    return t["prelude"] + "\n" + t["statement"]


def materialize(t: dict, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest, onexc=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))
    dest.mkdir(parents=True)
    (dest / "Main.lean").write_text(header(t) + " := by\n  sorry\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    return dest


def compile_lean(path: Path) -> tuple[int, str]:
    r = subprocess.run(["lean", path.name], cwd=path.parent, capture_output=True, text=True,
                       encoding="utf-8", timeout=300)
    return r.returncode, r.stdout + r.stderr


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def strip_comments(s: str) -> str:
    """Remove `--` line comments and (nested) `/- -/` block comments."""
    out, i, depth = [], 0, 0
    while i < len(s):
        if s.startswith("/-", i):
            depth += 1
            i += 2
        elif depth and s.startswith("-/", i):
            depth -= 1
            i += 2
        elif depth:
            i += 1
        elif s.startswith("--", i):
            j = s.find("\n", i)
            i = len(s) if j < 0 else j
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def statement_intact(t: dict, text: str) -> bool:
    """Prelude untouched at the top and the statement present verbatim outside comments; helper lemmas in between are fine."""
    code = _norm(strip_comments(text))
    prelude = _norm(t["prelude"])
    if not (code.startswith(prelude) and _norm(t["statement"]) in code):
        return False
    # scope/notation commands after the prelude can re-bind the names the statement mentions
    # (an unclosed `namespace` makes it a different theorem), so they count as changing it.
    return not SCOPE_CMDS.search(code[len(prelude):])


def axioms(t: dict, work: Path) -> set[str] | None:
    probe = work / "AxiomsProbe.lean"
    # `example` re-states the original type and closes it with the root-level theorem, so a weaker
    # theorem that merely sits next to a (commented / namespaced) copy of the statement fails to compile.
    rest = t["statement"].split(t["name"], 1)[1]
    probe.write_text((work / "Main.lean").read_text(encoding="utf-8")
                     # `<;> assumption` closes the statement's own hypotheses that `apply` leaves open
                     + f"\nexample{rest} := by\n  apply {t['name']} <;> assumption\n#print axioms {t['name']}\n", encoding="utf-8")
    code, out = compile_lean(probe)
    probe.unlink()
    if code != 0:
        return None
    if "does not depend on any axioms" in out:
        return set()
    m = re.search(r"depends on axioms: \[([^\]]*)\]", out)
    return {a.strip() for a in m.group(1).split(",")} if m else None


_NEXT_DECL = re.compile(r"^(?:@\[[^\n]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+)*"
                        r"(?:theorem|lemma|def|abbrev|instance|example|structure|inductive|class|#\w+)(?![\w'])", re.M)


def proof_body(t: dict, text: str) -> str:
    """Tactic text of the final proof: the exact-name theorem, up to the next top-level declaration."""
    code = strip_comments(text)
    m = re.search(rf"^theorem\s+{re.escape(t['name'])}(?![\w.'])", code, re.M)
    i = code.find(":= by", m.end()) if m else -1
    if i < 0:
        return ""
    body = code[i + 5:]
    n = _NEXT_DECL.search(body)
    return body[:n.start()] if n else body


def tactics(body: str) -> list[str]:
    out = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        line = re.sub(r"^\|\s*[^=]*=>\s*", "", line)
        for part in re.split(r";|<;>", line):
            m = re.match(r"[·.]?\s*([A-Za-z_][A-Za-z_0-9?!']*)", part.strip())
            if m:
                out.append(m.group(1))
    return out


STRUCTURAL = {"induction": "induction", "cases": "cases", "rcases": "cases", "match": "cases",
              "generalize": "generalize", "have": "aux", "suffices": "aux", "calc": "calc"}
NEUTRAL = {"intro", "intros", "show", "unfold", "dsimp", "using"}


def strategy_from_tactics(tacs: list[str], var: dict | None = None) -> list[str]:
    """Strategy skeleton: structural moves kept, every closing tactic (simp, rw, omega, rfl,
    exact, simpa, decide...) collapsed into one 'close' step. `simp` vs `rw` vs `omega` is
    another tool for the same step, not another route."""
    out = []
    for i, name in enumerate(tacs):
        tok = STRUCTURAL.get(name) or (None if name in NEUTRAL else "close")
        if tok == "induction" and var and i in var:
            tok = f"induction:{var[i]}"
        if tok and not (out and out[-1] == tok == "close"):
            out.append(tok)
    return out


def _induction_vars(body: str) -> dict:
    vars_, k = {}, 0
    for line in body.splitlines():
        line = re.sub(r"^\|\s*[^=]*=>\s*", "", line.strip())
        if not line or line.startswith("--"):
            continue
        for part in re.split(r";|<;>", line):
            m = re.match(r"[·.]?\s*([A-Za-z_][A-Za-z_0-9?!']*)\s*(\S*)", part.strip())
            if m:
                if m.group(1) == "induction":
                    vars_[k] = m.group(2)
                k += 1
    return vars_


def strategy_of_body(body: str) -> list[str]:
    return strategy_from_tactics(tactics(body), _induction_vars(body))


def strategy(t: dict, text: str) -> list[str]:
    """Skeleton of the final proof; 'aux' first if it relies on a helper lemma declared in the file."""
    body = proof_body(t, text)
    skel = strategy_of_body(body)
    helpers = re.findall(r"^(?:theorem|lemma)\s+([\w.']+)", strip_comments(text), re.M)
    if "aux" not in skel and any(h != t["name"] and re.search(rf"\b{re.escape(h)}\b", body) for h in helpers):
        skel = ["aux"] + skel
    return skel


def judge(t: dict, work: Path, actions: list[dict], tau: float = 0.8) -> dict:
    main = work / "Main.lean"
    text = main.read_text(encoding="utf-8")
    code, out = compile_lean(main)
    e0 = code == 0
    uses_sorry = ("declaration uses `sorry`" in out or "declaration uses 'sorry'" in out)
    ax = axioms(t, work) if e0 else None
    intact = statement_intact(t, text)
    truth = e0 and intact and not uses_sorry and ax is not None and ax <= STD_AXIOMS
    forbidden = bool(FORBIDDEN.search(text.replace(t["prelude"], "", 1))) or not intact
    toks = tactics(proof_body(t, text))
    refs = [tactics(p) for p in t["proofs"]]
    score = pc(toks, refs) if toks and refs else 0.0  # Mathlib trial tasks have no references
    last_edit = max((i for i, a in enumerate(actions) if a["kind"] == "edit"), default=None)
    compiled_after = last_edit is None or any(a["kind"] == "compile" for a in actions[last_edit + 1:])
    e1 = e0 and not forbidden
    skel = strategy(t, text)
    score_s = pc(skel, [strategy_of_body(p) for p in t["proofs"]]) if skel and t["proofs"] else 0.0
    return {"truth": truth, "E0": e0, "E1": e1, "E2": e1 and compiled_after, "E3": e0 and score >= tau,
            "pc": round(score, 3), "tactics": toks, "sorry": uses_sorry, "axioms": sorted(ax) if ax is not None else None,
            "statement_intact": intact,
            # E3s: same metric over the strategy skeleton (another route vs another tactic)
            "E3s": e0 and score_s >= tau, "pc_strategy": round(score_s, 3), "strategy": skel}
