"""Part B: a core-Lean theorem; truth = compiles, statement intact, no sorry, standard axioms only."""
from __future__ import annotations

import re
import shutil
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
        shutil.rmtree(dest)
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
                     + f"\nexample{rest} := by\n  apply {t['name']}\n#print axioms {t['name']}\n", encoding="utf-8")
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
    score = pc(toks, refs) if toks else 0.0
    last_edit = max((i for i, a in enumerate(actions) if a["kind"] == "edit"), default=None)
    compiled_after = last_edit is None or any(a["kind"] == "compile" for a in actions[last_edit + 1:])
    e1 = e0 and not forbidden
    return {"truth": truth, "E0": e0, "E1": e1, "E2": e1 and compiled_after, "E3": e0 and score >= tau,
            "pc": round(score, 3), "tactics": toks, "sorry": uses_sorry, "axioms": sorted(ax) if ax is not None else None,
            "statement_intact": intact}
