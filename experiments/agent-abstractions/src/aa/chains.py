"""Study-2 chain tasks: load and validate ``tasks2/<zone>/``.

Minimal loader written by the chain runner (plan Task 3) before Task 2 existed; Task 2
extends this module (sanity, consumers.json, references) without changing the shapes
below, which the runner depends on.

Layout (plan Task 2)::

    tasks2/<zone>/chain.json        {"zone": "Z1", "steps": [{"id": "T1", "kind": "rule",
                                      "consumers": ["..."]}, ...]}
    tasks2/<zone>/T<k>/statement.md  behaviour-only statement given to the agent
    tasks2/<zone>/T<k>/hidden/...    hidden tests (never read by the runner)

Step ids are ``T1..Tn`` in order; the runner carries the agent's tree from step to
step in this order.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from pathlib import Path

from aa import config

TASKS2 = config.ROOT / "tasks2"
_STEP_RE = re.compile(r"^T(\d+)$")


class ChainError(ValueError):
    """A malformed ``tasks2/<zone>/`` directory."""


@dataclass(frozen=True)
class Step:
    id: str
    kind: str | None
    consumers: tuple[str, ...]
    statement_path: Path
    # Per-step limits (study 3's T0: 40 min / 90 turns); None = the runner's defaults
    # (T1-T4: config.WALL_LIMIT_S / config.TURN_LIMIT).
    wall_limit_s: int | None = None
    turn_limit: int | None = None

    def statement(self) -> str:
        return self.statement_path.read_text()


@dataclass(frozen=True)
class Chain:
    zone: str
    root: Path
    steps: tuple[Step, ...]

    @property
    def step_ids(self) -> tuple[str, ...]:
        return tuple(s.id for s in self.steps)


def load_chain(zone: str, root: Path | None = None) -> Chain:
    """Load and validate ``<root>/<zone>/chain.json`` and its step statements."""
    zdir = (root or TASKS2) / zone
    meta_file = zdir / "chain.json"
    if not meta_file.exists():
        raise ChainError(f"{meta_file} missing")
    try:
        meta = json.loads(meta_file.read_text())
    except json.JSONDecodeError as e:
        raise ChainError(f"{meta_file}: {e}") from e
    if meta.get("zone") != zone:
        raise ChainError(f"{meta_file}: zone {meta.get('zone')!r} != directory {zone!r}")
    raw = meta.get("steps")
    if not isinstance(raw, list) or not raw:
        raise ChainError(f"{meta_file}: no steps")
    steps: list[Step] = []
    for i, s in enumerate(raw, start=1):
        sid = s.get("id") if isinstance(s, dict) else s
        m = _STEP_RE.match(str(sid))
        if not m or int(m.group(1)) != i:
            raise ChainError(f"{meta_file}: step {i} has id {sid!r}, expected 'T{i}'")
        st = zdir / sid / "statement.md"
        if not st.exists() or not st.read_text().strip():
            raise ChainError(f"{st} missing or empty")
        info = s if isinstance(s, dict) else {}
        steps.append(Step(id=sid, kind=info.get("kind"),
                          consumers=tuple(info.get("consumers") or ()), statement_path=st))
    return Chain(zone=zone, root=zdir, steps=tuple(steps))


def list_zones(root: Path | None = None) -> list[str]:
    """Zones that have a chain.json, sorted."""
    r = root or TASKS2
    if not r.exists():
        return []
    return sorted(p.name for p in r.iterdir() if (p / "chain.json").exists())


# ------------------------------------------------------------- statement leak check
# Study 2 statements (spec §3, amendment 2026-10-08): the study-1 leak rules (no file
# paths, protected APIs, upstream pointers) plus two study-2 rules, because the
# primary measure is whether the agent finds every copy on its own:
#  * no hint to search exhaustively ("everywhere", "wherever", "every place", "make
#    sure all", "nothing in Actual that ...", "every month-wide action", ...);
#  * no enumeration of the zone's pre-existing consumer families (two or more named
#    in one statement, e.g. Z1 naming the copy / zero / average bulk actions).
# A behaviour stated once for the concept ("month-wide budget actions leave ... ")
# is what a maintainer writes and passes.

HINT_RE = re.compile(
    r"\beverywhere\b|\bwherever\b|\bwhenever\b|\bthroughout\b|\bexhaustive(?:ly)?\b"
    r"|\bevery\s+one\s+of\b"
    r"|\bmake\s+sure\s+(?:that\s+)?(?:all|every|each|no|nothing)\b"
    r"|\b(?:everything|nothing|anything|anywhere|everyone)\s+(?:else\s+)?in\s+(?:Actual|the\s+app)\b"
    r"|\bthe\s+rest\s+of\s+(?:Actual|the\s+app)\b"
    r"|\bacross\s+the\s+(?:app|codebase|code)\b"
    r"|\bconsistent(?:ly)?\b|\bmust\s+(?:all\s+)?agree\b|\bmust\s+(?:keep\s+)?hold(?:ing)?\b"
    r"|\b(?:do\s+not|don't|never)\s+miss\b"
    r"|\b(?:every|all|any)\s+(?:other\s+)?rules?\s+that\s+appl(?:y|ies)\b"
    r"|\b(?:every|each|all(?:\s+the)?|any)\s+(?:[\w-]+\s+){0,2}?(?:places?|sites?|copies|"
    r"callers?|consumers?|locations?|spots?|code\s+paths?|usages?|implementations?|"
    r"actions?|providers?|handlers?|functions?|methods?)\b",
    re.I)

# Pre-existing consumer families per zone (the T1 consumers in chain.json), as a
# statement would name them. Two or more distinct families in one statement = leak.
CONSUMER_TERMS: dict[str, dict[str, str]] = {
    "Z1": {"copy-previous-month": r"\bcop(?:y|ies|ying|ied)\b",
           "set-zero": r"\b(?:to|at)\s+zero\b|\bzero(?:ed|ing|es)\b",
           "set-n-month-avg": r"\baverag\w*|\b\d+[- ]months?\b"},
    "Z2": {"forecast": r"\bforecast\w*",
           "preview": r"\bpreview\w*|\bupcoming\b",
           "post-transaction": r"\bpost(?:s|ed|ing)?\s+(?:a\s+|the\s+)?transactions?\b",
           "rule-action-sync": r"\brule\s+actions?\b|\bschedule(?:'s)?\s+rules?\b",
           "budget-template": r"\btemplates?\b"},
    "Z3": {"gocardless": r"\bgo\s?cardless\b", "simplefin": r"\bsimple\s?fin\b",
           "pluggyai": r"\bpluggy", "akahu": r"\bakahu\b",
           "enablebanking": r"\benable\s?banking\b"},
    "Z4": {"next-date": r"\bnext\s+(?:date|occurrence)\b",
           "upcoming-dates": r"\bupcoming\b|\bpreview\w*",
           "budget-template": r"\btemplates?\b"},
}


def statement_leaks2(text: str, zone: str, allowed: frozenset[str] = frozenset()) -> list[str]:
    """Leak-check findings for one study-2 statement (empty = clean). ``allowed``: the
    public method names a consumer step introduces (e.g. ``budget/set-last-month-
    spending``), which the study-1 path rule would otherwise read as a file path."""
    from aa.tasks import statement_leaks
    found = [f for f in statement_leaks(text)
             if not (f.startswith("file path: ") and f[len("file path: "):].strip("'\"") in allowed)]
    found += [f"exhaustive-search hint: {m.group(0)!r}" for m in HINT_RE.finditer(text)]
    hits = {fam: m.group(0) for fam, rx in CONSUMER_TERMS.get(zone, {}).items()
            if (m := re.search(rx, text, re.I))}
    if len(hits) >= 2:
        found.append("consumer enumeration: "
                     + ", ".join(f"{f}={w!r}" for f, w in sorted(hits.items())))
    return found


def check_statements2(root: Path | None = None) -> dict[str, list[str]]:
    """{'<zone>/<step>': problems} for every chain step whose statement leaks; empty =
    all clean."""
    out: dict[str, list[str]] = {}
    for zone in list_zones(root):
        ch = load_chain(zone, root)
        meta = json.loads((ch.root / "chain.json").read_text())
        for s, info in zip(ch.steps, meta["steps"]):
            allowed = frozenset(re.findall(r"\b[a-z]+/[a-z0-9-]+\b", info.get("summary") or "")
                                if s.kind == "consumer" else ())
            probs = statement_leaks2(s.statement(), zone, allowed)
            if probs:
                out[f"{zone}/{s.id}"] = probs
    return out


# --------------------------------------------------------------------------- sanity
# Plan Task 2: (a) on the untouched R and F images every consumer test fails when run
# alone (Review Focus 3); (b) the implementer's references, applied cumulatively
# (T1..Tk) to the untouched variant, pass steps 1..k's hidden tests with lint and
# typecheck green; (c) no reference patch carries hidden-test content.
# Containers mirror aa.chain_eval: aa-actual:<cond>, network off, seeded vitest.

SANITY_FILE = "sanity_check.json"
UNTOUCHED_TIMEOUT_S = 3 * 3600
REFERENCE_TIMEOUT_S = 2 * 3600
_LITERAL = re.compile(r"""(['"`])((?:(?!\1)[^\\\n]|\\.){12,})\1""")


def _name_pattern(full_name: str) -> str:
    """vitest ``-t`` regex for one JSON-report fullName. The report joins describe and
    test titles with a space, while ``-t`` matches them joined with " > ", so every
    space may be either; the verdict checks that only the target test ran."""
    return "^" + re.escape(full_name).replace("\\ ", "(?: | > )") + "$"


def _split_name(name: str, hidden: list[str]) -> tuple[list[str], str]:
    """(loot-relative files to run, fullName) for a consumers.json key."""
    loot = config.LOOT + "/"
    if "::" in name:
        f, full = name.split("::", 1)
        return [f[len(loot):] if f.startswith(loot) else f], full
    return [h[len(loot):] for h in hidden], name


def untouched_script(tests: list[tuple[str, list[str], str]], all_hidden: list[str]) -> str:
    """Bash for one untouched image: stage every hidden test, then one seeded vitest
    process per (key, files, fullName) writing /out/u/<i>.json."""
    import shlex

    from aa.checker import SEED_CONFIG_DST, SEED_CONFIG_SRC, SEED_DST, SEED_SRC, vitest_clean_cmd
    from aa.evaluate import HIDDEN_SRC
    q = shlex.quote
    lines = ["set -u", "mkdir -p /out/u", "cd /work/actual",
             f"for t in {' '.join(q(t) for t in all_hidden)}; do mkdir -p \"$(dirname \"$t\")\" "
             f"&& cp /out/{HIDDEN_SRC}/\"$t\" \"$t\" || exit 3; done",
             f"cd {config.LOOT}",
             f"cp /checker/{SEED_SRC.name} {SEED_DST} && cp /checker/{SEED_CONFIG_SRC.name} "
             f"{SEED_CONFIG_DST} || exit 3"]
    for i, (_, files, full) in enumerate(tests):
        cmd = " ".join(q(a) for a in vitest_clean_cmd(f"/out/u/{i}.json", files))
        lines.append(f"ENV=node timeout 600 {cmd} -t {q(_name_pattern(full))} "
                     f"> /out/u/{i}.log 2>&1; echo $? > /out/u/{i}.rc")
    lines.append("echo done > /out/u/done")
    return "\n".join(lines) + "\n"


def reference_script(step_hidden: list[list[str]], *, static_checks: bool = True) -> str:
    """Bash for one (zone, cond): apply /refs/T<k>.patch cumulatively; after each step
    lint + typecheck on the tree as patched, then the hidden tests of steps 1..k
    (seeded, clean) -> /out/T<k>/report.json; hidden tests and seed removed again
    before the next patch. A patch that does not apply stops the chain
    (/out/T<k>/apply_error)."""
    import shlex

    from aa.checker import SEED_CONFIG_DST, SEED_CONFIG_SRC, SEED_DST, SEED_SRC, vitest_clean_cmd
    from aa.evaluate import HIDDEN_SRC
    q = shlex.quote
    commit = "git -c user.name=aa -c user.email=aa@local -c commit.gpgsign=false commit -q --no-verify"
    lines = ["set -u", "cd /work/actual",
             f"{{ git add -A && {commit} --allow-empty -m evalbase; }} > /out/base.log 2>&1 || exit 3"]
    cum: list[str] = []
    for k, hidden in enumerate(step_hidden, start=1):
        cum += hidden
        rel = [t[len(config.LOOT) + 1:] for t in cum]
        out = f"/out/T{k}"
        clean = " ".join(q(a) for a in vitest_clean_cmd(f"{out}/report.json", rel))
        lines += [
            f"mkdir -p {out}; cd /work/actual",
            f"git apply --whitespace=nowarn /refs/T{k}.patch > {out}/apply.log 2>&1 "
            f"|| {{ echo 1 > {out}/apply_error; echo done > /out/done; exit 0; }}",
            f"git diff --stat > {out}/stat.txt",
            f"cd {config.LOOT}",
        ]
        if static_checks:
            lines += [f"timeout 1200 yarn lint > {out}/lint.log 2>&1; echo $? > {out}/lint_rc",
                      f"timeout 1200 yarn tsgo -b > {out}/typecheck.log 2>&1; "
                      f"echo $? > {out}/typecheck_rc"]
        lines += [
            f"( cd /work/actual && for t in {' '.join(q(t) for t in cum)}; do "
            f"mkdir -p \"$(dirname \"$t\")\" && cp /out/{HIDDEN_SRC}/\"$t\" \"$t\" || exit 1; done ) "
            f"|| {{ echo 1 > {out}/hidden_error; }}",
            f"cp /checker/{SEED_SRC.name} {SEED_DST} && cp /checker/{SEED_CONFIG_SRC.name} {SEED_CONFIG_DST}",
            f"ENV=node timeout 1200 {clean} > {out}/vitest.log 2>&1; echo $? > {out}/vitest_rc",
            f"rm -f {SEED_DST} {SEED_CONFIG_DST}",
            f"( cd /work/actual && rm -f {' '.join(q(t) for t in cum)} )",
        ]
    lines.append("echo done > /out/done")
    return "\n".join(lines) + "\n"


def _docker(cond: str, name: str, out: Path, script: str, extra: list[str]) -> list[str]:
    """The container name carries a short hash of the work dir (``out``'s parent), so
    two sanity / t0-reference runs on different work dirs never collide."""
    import hashlib

    from aa.checker import SEED_SRC
    tag = hashlib.sha256(str(Path(out).resolve().parent).encode()).hexdigest()[:6]
    return ["docker", "run", "--rm", "--name", re.sub(r"[^\w.-]", "_", f"{name}-{tag}"),
            "--network", "none", "--cpus", "2", "--memory", "6g",
            "-v", f"{SEED_SRC.parent}:/checker:ro", "-v", f"{out}:/out", *extra,
            f"aa-actual:{cond}", "bash", "-c", script]


def _load_report(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def untouched_verdicts(tests: list[tuple[str, list[str], str]], out: Path) -> dict[str, dict]:
    """Per key: the test must be the only one that ran and it (every match) must fail."""
    from aa.suite import parse_vitest_json
    root = f"/work/actual/{config.LOOT}"
    res: dict[str, dict] = {}
    for i, (key, files, full) in enumerate(tests):
        rep = _load_report(out / "u" / f"{i}.json")
        if rep is None:
            res[key] = {"ok": False, "why": "no report"}
            continue
        r = parse_vitest_json(rep, root)
        ran = sorted(r.passed | r.failed)
        mine = [t for t in ran if t.split("::", 1)[1] == full and t.split("::", 1)[0] in files]
        others = [t for t in ran if t not in mine]
        failed = [t for t in mine if t in r.failed]
        ok = bool(mine) and not others and len(failed) == len(mine)
        why = None if ok else ("did not run" if not mine else
                               f"other tests ran: {others[:3]}" if others else "passed")
        res[key] = {"ok": ok, "ran": len(ran), "failed": len(failed), "why": why}
    return res


def _read(p: Path) -> str:
    try:
        return p.read_text()
    except OSError:
        return ""


def reference_leaks(zone: str, cond: str, root: Path | None = None) -> dict[str, Any]:
    """Hidden-test content in a zone's reference patches: files under any step's hidden
    paths or test files, test names, and >=12-char string literals of the hidden tests
    on added lines that are neither in the step statements (public, case-insensitive)
    nor already in the touched files of the untouched variant (work/variants/<cond>)."""
    from aa.chain_eval import load_chain as eval_chain
    ch = eval_chain(zone, root)
    hidden_paths = {h for s in ch.steps for h in s.hidden}
    names = {n.split("::", 1)[-1] for s in ch.steps for n in s.tests}
    literals: set[str] = set()
    for s in ch.steps:
        for h in s.hidden:
            literals |= {m.group(2) for m in _LITERAL.finditer((s.dir / "hidden" / h).read_text())}
    public = "\n".join(s.dir.joinpath("statement.md").read_text() for s in ch.steps).lower()
    variant = config.WORK / "variants" / cond
    out: dict[str, Any] = {}
    for s in ch.steps:
        p = s.dir / f"reference.{cond}.patch"
        if not p.exists():
            out[s.id] = {"missing": True}
            continue
        text = p.read_text()
        files = re.findall(r"^diff --git a/(\S+) b/", text, re.M)
        added = "\n".join(l[1:] for l in text.splitlines()
                          if l.startswith("+") and not l.startswith("+++"))
        out[s.id] = {
            "files": files,
            "hidden_or_test_files": [f for f in files if f in hidden_paths
                                     or re.search(r"\.(test|spec)\.[jt]sx?$|__mocks__|/mocks/", f)],
            "test_names": sorted(n for n in names if n in added),
            "literals": sorted(l for l in literals if l in added and l.lower() not in public
                               and not any(l in _read(variant / f) for f in files)),
        }
    return out


def sanity(zone: str, conds: tuple[str, ...] = config.CONDITIONS2, *, root: Path | None = None,
           work: Path | None = None, untouched: bool = True, references: bool = True,
           runner: Any = None) -> dict[str, Any]:
    """Run the sanity checks for one zone; return the verdicts (also written to
    ``tasks2/<zone>/sanity_check.json``). ``work``: scratch dir for container outputs."""
    import subprocess
    import tempfile

    from aa.chain_eval import load_chain as eval_chain
    from aa.chain_eval import step_outcome
    from aa.evaluate import stage_hidden_tests
    run = runner or (lambda argv, t: subprocess.run(argv, capture_output=True, text=True,
                                                     timeout=t).returncode)
    ch = eval_chain(zone, root)
    work = Path(work or tempfile.mkdtemp(prefix=f"aa-sanity-{zone}-"))
    result: dict[str, Any] = {"zone": zone, "conds": {}}
    for cond in conds:
        cres: dict[str, Any] = {"leaks": reference_leaks(zone, cond, root)}
        if untouched:
            out = work / cond / "untouched"
            out.mkdir(parents=True, exist_ok=True)
            all_hidden: list[str] = []
            tests: list[tuple[str, list[str], str]] = []
            for s in ch.steps:
                all_hidden += stage_hidden_tests(s.dir, s.hidden, cond, out)
                for key in s.tests:
                    files, full = _split_name(key, s.hidden)
                    tests.append((f"{s.id}::{key}", files, full))
            run(_docker(cond, f"aa-sanity-u-{zone}-{cond}", out,
                        untouched_script(tests, all_hidden), []), UNTOUCHED_TIMEOUT_S)
            v = untouched_verdicts(tests, out)
            per_step = {s.id: {k.split("::", 1)[1] if k.count("::") == 1 else k[len(s.id) + 2:]:
                               vv for k, vv in v.items() if k.startswith(s.id + "::")}
                        for s in ch.steps}
            cres["untouched"] = {"all_fail_individually": all(x["ok"] for x in v.values()),
                                 "steps": per_step}
        if references:
            out = work / cond / "refs"
            refs = out / "refs"
            refs.mkdir(parents=True, exist_ok=True)
            step_hidden = []
            for s in ch.steps:
                step_hidden.append(stage_hidden_tests(s.dir, s.hidden, cond, out))
                src = s.dir / f"reference.{cond}.patch"
                (refs / f"{s.id}.patch").write_text(src.read_text() if src.exists() else "")
            run(_docker(cond, f"aa-sanity-r-{zone}-{cond}", out, reference_script(step_hidden),
                        ["-v", f"{refs}:/refs:ro"]), REFERENCE_TIMEOUT_S)
            steps: dict[str, Any] = {}
            for s in ch.steps:
                d = out / s.id
                if not d.exists():
                    steps[s.id] = {"ok": False, "why": "not reached"}
                    continue
                if (d / "apply_error").exists():
                    steps[s.id] = {"ok": False, "why": "patch does not apply",
                                   "log": (d / "apply.log").read_text()[:500]}
                    continue
                rc = {k: (int((d / f"{k}_rc").read_text()) if (d / f"{k}_rc").exists() else None)
                      for k in ("lint", "typecheck")}
                rep = _load_report(d / "report.json")
                # tests a later step deliberately contradicts (chain.json supersedes)
                upto = {p.id: step_outcome(rep, p, ch.superseded(s, p)) for p in ch.steps[:s.index]}
                failing = {sid: sorted(n for n, ok in o["tests"].items() if not ok)
                           for sid, o in upto.items()}
                ok = all(o["correct"] for o in upto.values()) and rc["lint"] == 0 \
                    and rc["typecheck"] == 0
                steps[s.id] = {"ok": ok, "lint_ok": rc["lint"] == 0,
                               "typecheck_ok": rc["typecheck"] == 0,
                               "own": {"consumers_passed": upto[s.id]["consumers_passed"],
                                       "consumers_total": upto[s.id]["consumers_total"]},
                               "superseded": {p.id: sorted(ch.superseded(s, p))
                                              for p in ch.steps[:s.index - 1]
                                              if ch.superseded(s, p)},
                               "failing": {k: v for k, v in failing.items() if v}}
            cres["references"] = {"all_ok": all(x["ok"] for x in steps.values()), "steps": steps}
        result["conds"][cond] = cres
    (ch.dir / SANITY_FILE).write_text(json.dumps(result, indent=2) + "\n")
    return result


# ===================================================================== study 3: T0
# The RC arm's directed refactor (spec 2026-10-10 section 3, plan Task 2). Layout::
#
#     tasks3/<zone>/T0/statement.md      behaviour only (zone logic), leak-checked
#     tasks3/<zone>/T0/hidden/...        inconsistency tests (spec section 3 list only;
#                                        none for a zone with no listed case)
#     tasks3/<zone>/T0/consumers.json    {vitest fullName: inconsistency id}
#     tasks3/<zone>/T0/sites.json        copy sites, for the completeness judge
#     tasks3/<zone>/T0/sanity/<seed>.patch, sanity/seeds.json
#                                        seeded consolidations of R: {seed: {"kind":
#                                        "inconsistency"|"excluded", "target": id}}
#     tasks3/<zone>/T0/sanity.json       t0_sanity verdicts
#     tasks3/probe-exclusions.json       probe cases the T0 comparison drops

TASKS3 = config.ROOT / "tasks3"
T0_ID = "T0"
T0_LIMITS = {"minutes": 40, "turns": 90}
PROBE_EXCLUSIONS_FILE = "probe-exclusions.json"
T0_SANITY_FILE = "sanity.json"
# inconsistency: breaks one listed inconsistency (its test fails, the others pass, the
# probe minus exclusions sees it); excluded: changes only an excluded probe case;
# behaviour: a behaviour-changing consolidation with no inconsistency test (Z4), seen
# by the probe minus exclusions and by no T0 test.
_SEED_KINDS = ("inconsistency", "excluded", "behaviour")


class T0Error(ValueError):
    """A malformed ``tasks3/<zone>/T0/`` directory or exclusion file."""


@dataclass(frozen=True)
class T0Task:
    zone: str
    dir: Path
    statement_path: Path
    hidden: tuple[str, ...]
    tests: dict[str, str]           # vitest fullName -> inconsistency id
    sites: dict[str, Any]
    seeds: dict[str, dict[str, str]]

    def statement(self) -> str:
        return self.statement_path.read_text()

    @property
    def inconsistencies(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(self.tests.values()))

    def seed_patch(self, name: str) -> Path:
        return self.dir / "sanity" / f"{name}.patch"


def list_t0_zones(root: Path | None = None) -> list[str]:
    r = root or TASKS3
    if not r.exists():
        return []
    return sorted(p.name for p in r.iterdir() if (p / T0_ID / "statement.md").exists())


def load_t0(zone: str, root: Path | None = None) -> T0Task:
    """Load and validate ``<root>/<zone>/T0``."""
    from aa.chain_eval import is_source_file
    d = (root or TASKS3) / zone / T0_ID
    st = d / "statement.md"
    if not st.exists() or not st.read_text().strip():
        raise T0Error(f"{st} missing or empty")
    hdir = d / "hidden"
    hidden = tuple(sorted(p.relative_to(hdir).as_posix() for p in hdir.rglob("*")
                          if p.is_file())) if hdir.is_dir() else ()
    for h in hidden:
        if not h.startswith(config.LOOT + "/") or is_source_file(h):
            raise T0Error(f"{zone}/T0: hidden path is not a loot-core test file: {h}")
    try:
        tests = json.loads((d / "consumers.json").read_text())
        sites = json.loads((d / "sites.json").read_text())
    except (OSError, ValueError) as e:
        raise T0Error(f"{zone}/T0: {e}") from e
    if not isinstance(tests, dict) or bool(tests) != bool(hidden):
        raise T0Error(f"{zone}/T0: consumers.json must map the hidden tests' names to "
                      "inconsistency ids (empty only when there are no hidden tests)")
    texts = "\n".join((hdir / h).read_text() for h in hidden)
    for name in tests:
        if not any(part in texts for part in _title_parts(name)):
            raise T0Error(f"{zone}/T0: test {name!r} not found in the hidden files")
    seeds_file = d / "sanity" / "seeds.json"
    seeds = json.loads(seeds_file.read_text()) if seeds_file.exists() else {}
    for name, s in seeds.items():
        if s.get("kind") not in _SEED_KINDS:
            raise T0Error(f"{zone}/T0: seed {name}: kind must be one of {_SEED_KINDS}")
        if s["kind"] == "inconsistency" and s.get("target") not in tests.values():
            raise T0Error(f"{zone}/T0: seed {name} targets unknown inconsistency "
                          f"{s.get('target')!r}")
        if not (d / "sanity" / f"{name}.patch").is_file():
            raise T0Error(f"{zone}/T0: seed {name} has no patch")
    unseeded = sorted(set(tests.values()) - {s["target"] for s in seeds.values()
                                             if s["kind"] == "inconsistency"})
    if unseeded:
        raise T0Error(f"{zone}/T0: inconsistencies without a seeded patch: {unseeded}")
    return T0Task(zone=zone, dir=d, statement_path=st, hidden=hidden, tests=dict(tests),
                  sites=sites, seeds=seeds)


# Study-3 pilot blocking item 9: which T0 inconsistency tests still hold after each
# T1..T4 step (``<root>/inconsistency-scope.json``: {"zones": {zone: {id: {"superseded_at":
# ["T1", ...], "reason": ...}}}}).
INCONSISTENCY_SCOPE_FILE = "inconsistency-scope.json"
CHAIN_STEP_IDS = ("T1", "T2", "T3", "T4")


def load_inconsistency_scope(root: Path | None = None) -> dict[str, dict[str, dict]]:
    """{zone: {inconsistency id: {"superseded_at": [step ids], "reason": str}}}; every
    entry needs a reason and only T1..T4 step ids."""
    p = (root or TASKS3) / INCONSISTENCY_SCOPE_FILE
    try:
        zones = json.loads(p.read_text())["zones"]
    except (OSError, ValueError, KeyError) as e:
        raise T0Error(f"{p}: {e}") from e
    for z, ids in zones.items():
        for i, v in ids.items():
            if not isinstance(v, dict) or not str(v.get("reason") or "").strip():
                raise T0Error(f"{p}: {z}/{i}: a reason is required")
            bad = [s for s in v.get("superseded_at") or [] if s not in CHAIN_STEP_IDS]
            if bad:
                raise T0Error(f"{p}: {z}/{i}: unknown steps {bad}")
    return zones


def scope_tests(t0: "T0Task", step_id: str, scope: dict[str, dict[str, dict]]) -> dict[str, str]:
    """{vitest fullName: inconsistency id} of ``t0``'s tests that ``step_id``'s post tree
    must still pass (not superseded at that step). An id missing from the scope file is
    an error (every test must be decided)."""
    zone = scope.get(t0.zone, {})
    missing = sorted(set(t0.inconsistencies) - set(zone))
    if missing:
        raise T0Error(f"{t0.zone}: inconsistencies without a scope decision: {missing}")
    return {n: i for n, i in t0.tests.items()
            if step_id not in (zone[i].get("superseded_at") or [])}


T0_KIND = "refactor"
# The arm whose chains start with the T0 directed refactor (spec section 2).
T0_ARM = "RC"


def t0_step(zone: str, root: Path | None = None) -> Step:
    """RC's T0 as a chain step: ``<root>/<zone>/T0/statement.md`` with the T0 limits."""
    st = (root or TASKS3) / zone / T0_ID / "statement.md"
    if not st.exists() or not st.read_text().strip():
        raise T0Error(f"{st} missing or empty")
    return Step(id=T0_ID, kind=T0_KIND, consumers=(), statement_path=st,
                wall_limit_s=T0_LIMITS["minutes"] * 60, turn_limit=T0_LIMITS["turns"])


def load_arm_chain(zone: str, cond: str, root: Path | None = None,
                   t0_root: Path | None = None) -> Chain:
    """The steps a chain of arm ``cond`` runs: the study-2 chain (``tasks2/<zone>``,
    T1..Tn unchanged) and, for RC only, T0 (``tasks3/<zone>/T0``) in front of it.
    T1 then starts from T0's tree (plan Task 4, Review Focus 3)."""
    chain = load_chain(zone, root)
    if cond != T0_ARM:
        return chain
    return Chain(zone=chain.zone, root=chain.root,
                 steps=(t0_step(zone, t0_root),) + chain.steps)


def _title_parts(full_name: str) -> list[str]:
    """Candidate literal titles inside a fullName ('describe test'): its every suffix
    starting at a word, longest first (the `it` title is one of them)."""
    words = full_name.split(" ")
    return [" ".join(words[i:]) for i in range(len(words))][:-1] or [full_name]


# T0 statements (spec section 3): behaviour only, no files, functions, copy counts or
# locations. On top of the study-2 rules (statement_leaks2): code identifiers
# (camelCase / inner-capital names, calls, code spans), counts of places, and words
# that point at where the code lives.
_T0_IDENT_RE = re.compile(r"`[^`]+`|\b[a-z]+[A-Z][A-Za-z0-9]*\b|\b[A-Z][a-z]+[A-Z]\w*\b"
                          r"|\b\w+\(\)")
_T0_COUNT_RE = re.compile(
    r"\b(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(?:[\w-]+\s+){0,2}?"
    r"(?:places?|copies|sites?|times|functions?|handlers?|actions?|providers?|callers?|"
    r"spots?|definitions?|implementations?|requests?|files?|versions?)\b"
    r"|\btwice\b|\bboth\b", re.I)
_T0_LOCATION_RE = re.compile(
    r"\b(?:files?|modules?|folders?|director(?:y|ies)|packages?|lines?\s+\d+|"
    r"(?:server|client)[- ]side)\b", re.I)


def t0_statement_leaks(text: str, zone: str) -> list[str]:
    """Leak-check findings for one T0 statement (empty = clean)."""
    found = statement_leaks2(text, zone)
    found += [f"code identifier: {m.group(0)!r}" for m in _T0_IDENT_RE.finditer(text)]
    found += [f"copy count: {m.group(0)!r}" for m in _T0_COUNT_RE.finditer(text)]
    found += [f"location: {m.group(0)!r}" for m in _T0_LOCATION_RE.finditer(text)]
    return found


def check_statements_t0(root: Path | None = None) -> dict[str, list[str]]:
    """{'<zone>/T0': problems} for every T0 statement that leaks; empty = all clean."""
    out: dict[str, list[str]] = {}
    for zone in list_t0_zones(root):
        probs = t0_statement_leaks(load_t0(zone, root).statement(), zone)
        if probs:
            out[f"{zone}/{T0_ID}"] = probs
    return out


def load_probe_exclusions(root: Path | None = None) -> list[dict[str, Any]]:
    """``tasks3/probe-exclusions.json`` -> its exclusion list (validated)."""
    p = (root or TASKS3) / PROBE_EXCLUSIONS_FILE
    try:
        ex = json.loads(p.read_text())["exclusions"]
    except (OSError, ValueError, KeyError) as e:
        raise T0Error(f"{p}: {e}") from e
    for e in ex:
        if not e.get("id") or not e.get("reason") or not isinstance(e.get("cases"), list):
            raise T0Error(f"{p}: every exclusion needs id, reason and a cases list: {e}")
        bad = [c for c in e["cases"] if not re.match(r"^(db|template):\S", c)]
        if bad:
            raise T0Error(f"{p}: {e['id']}: case ids must be db:<key> or template:<key>: {bad}")
    return ex


# ------------------------------------------------------------------- T0 sanity
# For each tree (untouched R, untouched F, R + one seeded patch): the T0 hidden tests of
# every zone in one seeded vitest run (/out/tests.json), then the study-2 probe in
# another (/out/probe/{db,template}.json, /out/probe/report.json). Verdicts (spec
# section 3): every inconsistency test passes on untouched R and F; an "inconsistency"
# seed fails its target test, passes the others, and the probe minus exclusions flags
# it; an "excluded" seed is invisible to the probe minus exclusions and fails no T0
# test; a "behaviour" seed (a consolidation that changes behaviour where no
# inconsistency test exists, Z4) is flagged by the probe minus exclusions.

T0_SANITY_TIMEOUT_S = 3600


def t0_script(hidden: list[str], *, patch: bool, typecheck: bool = False,
              lint: bool = False, related: list[str] = ()) -> str:
    """Bash for one container (cwd-independent). ``hidden``: repo-relative T0 test paths,
    staged under /out/hidden_src; ``patch``: apply /seed/seed.patch first; ``typecheck``:
    on the tree as patched, before any test is staged, ``yarn tsgo -b`` (the
    evaluator's check, /out/typecheck_rc) and loot-core's ``yarn typecheck``
    (``tsgo -b && tsc-strict``, /out/typecheck_full_rc); ``lint``: the repo's root
    ``yarn lint`` (oxfmt --check + oxlint, /out/lint_root_rc) and the evaluator's
    ``yarn lint`` from loot-core (/out/lint_rc); ``related``: loot-core-relative source
    paths whose existing tests (``vitest related``, seeded, node) run before the hidden
    tests are staged (/out/related.json)."""
    import shlex

    from aa.checker import SEED_CONFIG_DST, SEED_CONFIG_SRC, SEED_DST, SEED_SRC
    from aa.evaluate import HIDDEN_SRC
    q = shlex.quote
    lines = ["set -u", "cd /work/actual"]
    if patch:
        lines.append("git apply --whitespace=nowarn /seed/seed.patch > /out/apply.log 2>&1 "
                     "|| { echo 1 > /out/apply_error; echo done > /out/done; exit 0; }")
    lines.append("git diff --stat > /out/stat.txt")
    if typecheck:
        lines += t0_typecheck_lines()
    if lint:
        lines += t0_lint_lines()
    if related:
        lines += [t0_related_line(related), t0_related_retry_line()]
    if hidden:
        lines.append(f"for t in {' '.join(q(t) for t in hidden)}; do mkdir -p \"$(dirname \"$t\")\" "
                     f"&& cp /out/{HIDDEN_SRC}/\"$t\" \"$t\" || exit 3; done")
    lines += [f"cd {config.LOOT}",
              f"cp /checker/{SEED_SRC.name} {SEED_DST} && cp /checker/{SEED_CONFIG_SRC.name} "
              f"{SEED_CONFIG_DST} || exit 3"]
    if hidden:
        lines += t0_tests_lines(hidden)
    lines += t0_probe_lines()
    lines.append("echo done > /out/done")
    return "\n".join(lines) + "\n"


# Pieces of t0_script, shared with the study-3 evaluator's T0 step (aa.chain_eval):
# the same commands, the same /out files.

def t0_typecheck_lines() -> list[str]:
    """The evaluator's ``yarn tsgo -b`` (/out/typecheck_rc) and loot-core's ``yarn
    typecheck`` (``tsgo -b && tsc-strict``, /out/typecheck_full_rc); from /work/actual."""
    return [f"( cd {config.LOOT} && timeout 1200 yarn tsgo -b > /out/typecheck.log 2>&1; "
            "echo $? > /out/typecheck_rc )",
            f"( cd {config.LOOT} && timeout 1800 yarn typecheck > /out/typecheck_full.log "
            "2>&1; echo $? > /out/typecheck_full_rc )"]


def t0_lint_lines(env: str = "") -> list[str]:
    """The repo's root ``yarn lint`` (/out/lint_root_rc) and loot-core's ``yarn lint``
    (/out/lint_rc), from /work/actual. ``env``: assignments put before each ``timeout``
    (the study-3 evaluator's fresh start repository, for RL's dup-check)."""
    e = f"{env} " if env else ""
    return [f"( {e}timeout 1800 yarn lint > /out/lint_root.log 2>&1; echo $? > /out/lint_root_rc )",
            f"( cd {config.LOOT} && {e}timeout 1200 yarn lint > /out/lint.log 2>&1; "
            "echo $? > /out/lint_rc )"]


def _related_cmd() -> list[str]:
    from aa.checker import vitest_clean_cmd
    rcmd = vitest_clean_cmd("/out/related.json", [])
    assert rcmd[:2] == ["yarn", "vitest"]
    return ["yarn", "vitest", "related", *rcmd[2:]]


def t0_related_line(related: list[str]) -> str:
    """Existing tests related to ``related`` (loot-core-relative sources), seeded, from
    /work/actual: /out/related.json, /out/related_rc."""
    import shlex

    from aa.checker import SEED_CONFIG_DST, SEED_CONFIG_SRC, SEED_DST, SEED_SRC
    q = shlex.quote
    rcmd = [*_related_cmd(), *related]
    return (f"( cd {config.LOOT} && cp /checker/{SEED_SRC.name} {SEED_DST} "
            f"&& cp /checker/{SEED_CONFIG_SRC.name} {SEED_CONFIG_DST} "
            f"&& ENV=node timeout 2400 {' '.join(q(a) for a in rcmd)} > /out/related.log "
            f"2>&1; echo $? > /out/related_rc; rm -f {SEED_DST} {SEED_CONFIG_DST} )")


RELATED_RETRY = "related_retry.json"
# The test files of /out/related.json that did not pass (loot-core-relative; cwd
# packages/loot-core).
_FAILED_FILES_JS = ("const fs=require('fs'),p=require('path');"
                    "const r=JSON.parse(fs.readFileSync('/out/related.json','utf8'));"
                    "for(const f of r.testResults||[])if(f.status!=='passed')"
                    "console.log(p.relative(process.cwd(),f.name))")


def t0_related_retry_line() -> str:
    """After a related run that did not pass (/out/related_rc != 0): its failing test
    files once more, alone, same seeded config (/out/related_retry.json,
    /out/related_retry_rc). From /work/actual. A file-level retry of the exact files
    that failed; :func:`t0_related_compare` counts a new failure only if it fails again
    (review of the pre-pilot fixes, MEDIUM: executors.test.ts timing out at 20 s in one
    run of the RC image and passing in the next)."""
    import shlex

    from aa.checker import SEED_CONFIG_DST, SEED_CONFIG_SRC, SEED_DST, SEED_SRC, vitest_clean_cmd
    q = shlex.quote
    cmd = " ".join(q(a) for a in vitest_clean_cmd(f"/out/{RELATED_RETRY}", []))
    return (f"if [ -s /out/related_rc ] && [ \"$(cat /out/related_rc)\" != 0 ] "
            f"&& [ -s /out/related.json ]; then ( cd {config.LOOT} "
            f"&& node -e {q(_FAILED_FILES_JS)} > /out/related_failed_files 2>/dev/null; "
            "mapfile -t RF < /out/related_failed_files; if [ ${#RF[@]} -gt 0 ]; then "
            f"cp /checker/{SEED_SRC.name} {SEED_DST} "
            f"&& cp /checker/{SEED_CONFIG_SRC.name} {SEED_CONFIG_DST} "
            f'&& ENV=node timeout 1200 {cmd} "${{RF[@]}}" > /out/related_retry.log 2>&1; '
            f"echo $? > /out/related_retry_rc; rm -f {SEED_DST} {SEED_CONFIG_DST}; fi ); fi")


def t0_related_from_file_line(list_file: str) -> str:
    """:func:`t0_related_line` with the sources read at run time from ``list_file`` (one
    loot-core-relative path per line); no sources -> no run, no /out/related_rc."""
    import shlex

    from aa.checker import SEED_CONFIG_DST, SEED_CONFIG_SRC, SEED_DST, SEED_SRC
    q = shlex.quote
    cmd = " ".join(q(a) for a in _related_cmd())
    return (f"mapfile -t REL < {q(list_file)}; if [ ${{#REL[@]}} -gt 0 ]; then "
            f"( cd {config.LOOT} && cp /checker/{SEED_SRC.name} {SEED_DST} "
            f"&& cp /checker/{SEED_CONFIG_SRC.name} {SEED_CONFIG_DST} "
            f'&& ENV=node timeout 2400 {cmd} "${{REL[@]}}" > /out/related.log '
            f"2>&1; echo $? > /out/related_rc; rm -f {SEED_DST} {SEED_CONFIG_DST} ); fi")


def t0_tests_lines(hidden: list[str]) -> list[str]:
    """The T0 hidden tests (already in place), seeded, cwd packages/loot-core:
    /out/tests.json, /out/tests_rc; then removed."""
    import shlex

    from aa.checker import vitest_clean_cmd
    q = shlex.quote
    rel = [t[len(config.LOOT) + 1:] for t in hidden]
    cmd = " ".join(q(a) for a in vitest_clean_cmd("/out/tests.json", rel))
    return [f"ENV=node timeout 1200 {cmd} > /out/tests.log 2>&1; echo $? > /out/tests_rc",
            f"rm -f {' '.join(q(r) for r in rel)}"]


def t0_probe_lines() -> list[str]:
    """The study-2 probe (mounted at /probe), cwd packages/loot-core with the seed in
    place: /out/probe/{db,template}.json, /out/probe/report.json, /out/probe/rc."""
    import shlex

    from aa.checker import vitest_clean_cmd
    from aa.probe2 import PROBE_DIR, PROBE_FILES
    q = shlex.quote
    assert PROBE_DIR.name == "probe"
    lines = ["mkdir -p /out/probe"]
    for src, dst in PROBE_FILES.items():
        lines.append(f"cp /probe/{q(src)} {q(dst)}")
    cmd = " ".join(q(a) for a in vitest_clean_cmd("/out/probe/report.json", list(PROBE_FILES.values())))
    lines.append(f"ENV=node AA_PROBE_OUT=/out/probe timeout 1800 {cmd} > /out/probe/vitest.log "
                 f"2>&1; echo $? > /out/probe/rc")
    return lines


def t0_test_results(report: dict | None, tests: dict[str, str]) -> dict[str, str]:
    """{fullName: passed|failed|skipped|missing} for one zone's T0 tests."""
    from aa.suite import parse_vitest_json
    if report is None:
        return {n: "missing" for n in tests}
    r = parse_vitest_json(report, f"/work/actual/{config.LOOT}")
    status: dict[str, str] = {}
    for kind, ids in (("passed", r.passed), ("failed", r.failed), ("skipped", r.skipped)):
        for tid in ids:
            status[tid.split("::", 1)[1]] = kind
    return {n: status.get(n, "missing") for n in tests}


def t0_seed_verdict(seed: dict[str, str], tests: dict[str, str], results: dict[str, str],
                    raw: list[str], kept: list[str]) -> dict[str, Any]:
    """Verdict for one seeded patch: ``results`` of the zone's T0 tests on R + seed,
    ``raw`` / ``kept`` the probe differences from untouched R before / after exclusions."""
    target = [n for n, i in tests.items() if i == seed["target"]]
    others = [n for n in tests if n not in target]
    v: dict[str, Any] = {"kind": seed["kind"], "target": seed["target"], "tests": results,
                         "probe_raw": raw, "probe_minus_exclusions": kept}
    if seed["kind"] == "inconsistency":
        v["target_fails"] = bool(target) and all(results.get(n) == "failed" for n in target)
        v["other_tests_pass"] = all(results.get(n) == "passed" for n in others)
        v["probe_flags"] = bool(kept)
        v["ok"] = v["target_fails"] and v["other_tests_pass"] and v["probe_flags"]
    elif seed["kind"] == "behaviour":
        v["tests_pass"] = all(results.get(n) == "passed" for n in tests)
        v["probe_flags"] = bool(kept)
        v["ok"] = v["tests_pass"] and v["probe_flags"]
    else:
        v["tests_pass"] = all(results.get(n) == "passed" for n in tests)
        v["probe_flags"] = bool(kept)
        v["ok"] = v["tests_pass"] and not kept
    return v


def _image_id(cond: str) -> str | None:
    import subprocess
    r = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", f"aa-actual:{cond}"],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def t0_sanity(zones: list[str] | None = None, *, root: Path | None = None,
              work: Path | None = None, workers: int = 2, runner: Any = None,
              write: bool = True) -> dict[str, Any]:
    """Run the T0 sanity checks in Docker for ``zones`` (default: all) and write each
    zone's ``tasks3/<zone>/T0/sanity.json``; returns {zone: verdicts}."""
    import datetime
    import subprocess
    import tempfile
    from concurrent.futures import ThreadPoolExecutor

    from aa.evaluate import stage_hidden_tests
    from aa.probe2 import PROBE_DIR, diff_probe, probe_doc
    run = runner or (lambda argv, t: subprocess.run(argv, capture_output=True, text=True,
                                                     timeout=t).returncode)
    zones = zones or list_t0_zones(root)
    tasks = {z: load_t0(z, root) for z in zones}
    exclusions = load_probe_exclusions(root)
    # absolute: docker treats a relative -v source as a named volume
    work = Path(work or tempfile.mkdtemp(prefix="aa-t0-sanity-")).resolve()
    loot_root = f"/work/actual/{config.LOOT}"
    hidden_all = [(t.dir, h) for t in tasks.values() for h in t.hidden]

    jobs: list[tuple[str, str, Path | None]] = [("untouched-R", "R", None),
                                                ("untouched-F", "F", None)]
    for t in tasks.values():
        jobs += [(f"{t.zone}-{name}", "R", t.seed_patch(name)) for name in t.seeds]

    def one(job: tuple[str, str, Path | None]) -> tuple[str, dict]:
        label, cond, patch = job
        out = work / label
        out.mkdir(parents=True, exist_ok=True)
        staged: list[str] = []
        for d, h in hidden_all:
            staged += stage_hidden_tests(d, [h], cond, out)
        extra = ["-v", f"{PROBE_DIR}:/probe:ro"]
        if patch is not None:
            (out / "seed").mkdir(exist_ok=True)
            (out / "seed" / "seed.patch").write_text(patch.read_text())
            extra += ["-v", f"{out / 'seed'}:/seed:ro"]
        rc = run(_docker(cond, f"aa-t0-sanity-{label}", out,
                         t0_script(staged, patch=patch is not None), extra), T0_SANITY_TIMEOUT_S)
        res = {"docker_rc": rc, "finished": (out / "done").exists(),
               "apply_error": (out / "apply_error").exists(),
               "tests_report": _load_report(out / "tests.json"),
               "probe": probe_doc(out / "probe", _load_report(out / "probe" / "report.json"),
                                  loot_root)}
        return label, res

    with ThreadPoolExecutor(max(1, workers)) as ex:
        runs = dict(ex.map(one, jobs))
    ref = runs["untouched-R"]["probe"]
    images = {c: _image_id(c) for c in ("R", "F")}
    out_all: dict[str, Any] = {}
    for z, t in tasks.items():
        untouched = {}
        for cond in ("R", "F"):
            r = t0_test_results(runs[f"untouched-{cond}"]["tests_report"], t.tests)
            untouched[cond] = {"tests": r, "all_pass": all(s == "passed" for s in r.values())}
        f_raw = diff_probe(ref, runs["untouched-F"]["probe"])
        seeds = {}
        for name, s in t.seeds.items():
            rr = runs[f"{z}-{name}"]
            if rr["apply_error"] or not rr["finished"]:
                seeds[name] = {**s, "ok": False, "docker_rc": rr["docker_rc"],
                               "why": "patch does not apply" if rr["apply_error"]
                               else "container did not finish"}
                continue
            seeds[name] = t0_seed_verdict(
                s, t.tests, t0_test_results(rr["tests_report"], t.tests),
                diff_probe(ref, rr["probe"]), diff_probe(ref, rr["probe"], exclusions))
        probe_ok = runs["untouched-R"]["finished"] and not ref["failed"] and ref.get("db") is not None and ref.get("template") is not None
        res = {
            "zone": z, "date": datetime.date.today().isoformat(),
            "images": images,
            "probe_cases": {"db": len(ref.get("db") or {}), "template": len(ref.get("template") or {})},
            "probe_reference_ok": probe_ok,
            "untouched": untouched,
            "containers_finished": {k: v["finished"] for k, v in runs.items()
                                    if k.startswith(("untouched-", f"{z}-"))},
            "probe_F_vs_R": {"raw": f_raw, "minus_exclusions": diff_probe(
                ref, runs["untouched-F"]["probe"], exclusions)},
            "seeds": seeds,
        }
        res["all_ok"] = (probe_ok and all(res["containers_finished"].values()) and all(u["all_pass"] for u in untouched.values())
                         and not res["probe_F_vs_R"]["raw"]
                         and all(s["ok"] for s in seeds.values()))
        if write:
            (t.dir / T0_SANITY_FILE).write_text(json.dumps(res, indent=2) + "\n")
        out_all[z] = res
    return out_all


SCOPE_SANITY_FILE = "scope_sanity.json"


def scope_sanity(zones: list[str] | None = None, conds: tuple[str, ...] = ("R", "F"), *,
                 root: Path | None = None, tasks_root: Path | None = None,
                 work: Path | None = None, runner: Any = None,
                 write: bool = True) -> dict[str, Any]:
    """Study-3 pilot blocking item 9: check ``inconsistency-scope.json`` against the
    chains' reference trees. Per zone with T0 tests and per cond, one container applies
    ``tasks2/<zone>/T<k>/reference.<cond>.patch`` cumulatively and runs the zone's T0
    inconsistency tests after each step. A test in scope at a step must pass on that
    reference tree (``ok``); a superseded one is reported (it is expected to fail where
    the statement changed the behaviour). Writes ``<zone>/T0/scope_sanity.json``.
    Containers run one at a time."""
    import datetime
    import subprocess
    import tempfile

    from aa.chain_eval import load_chain as eval_chain
    from aa.evaluate import stage_hidden_tests
    run = runner or (lambda argv, t: subprocess.run(argv, capture_output=True, text=True,
                                                     timeout=t).returncode)
    scope = load_inconsistency_scope(root)
    work = Path(work or tempfile.mkdtemp(prefix="aa-scope-sanity-")).resolve()
    out_all: dict[str, Any] = {}
    for z in zones or list_t0_zones(root):
        t0 = load_t0(z, root)
        if not t0.tests:
            continue
        ch = eval_chain(z, tasks_root)
        res: dict[str, Any] = {"zone": z, "date": datetime.date.today().isoformat(),
                               "images": {c: _image_id(c) for c in conds}, "conds": {}}
        for cond in conds:
            out = work / z / cond
            refs = out / "refs"
            refs.mkdir(parents=True, exist_ok=True)
            hidden = stage_hidden_tests(t0.dir, list(t0.hidden), cond, out)
            for st in ch.steps:
                src = st.dir / f"reference.{cond}.patch"
                (refs / f"{st.id}.patch").write_text(src.read_text() if src.exists() else "")
            script = reference_script([hidden] + [[] for _ in ch.steps[1:]],
                                      static_checks=False)
            rc = run(_docker(cond, f"aa-scope-sanity-{z}-{cond}", out, script,
                             ["-v", f"{refs}:/refs:ro"]), REFERENCE_TIMEOUT_S)
            steps: dict[str, Any] = {}
            for st in ch.steps:
                d = out / st.id
                in_scope = scope_tests(t0, st.id, scope)
                if not d.exists() or (d / "apply_error").exists():
                    steps[st.id] = {"ok": False, "why": "reference does not apply"
                                    if (d / "apply_error").exists() else "not reached"}
                    continue
                results = t0_test_results(_load_report(d / "report.json"), t0.tests)
                steps[st.id] = {
                    "results": {t0.tests[n]: v for n, v in results.items()},
                    "in_scope": sorted(set(in_scope.values())),
                    "ok": all(results[n] == "passed" for n in in_scope),
                    "superseded_failing": sorted({t0.tests[n] for n, v in results.items()
                                                  if n not in in_scope and v != "passed"}),
                }
            res["conds"][cond] = {"docker_rc": rc, "steps": steps,
                                  "ok": all(v["ok"] for v in steps.values())}
        res["all_ok"] = all(c["ok"] for c in res["conds"].values())
        if write:
            (t0.dir / SCOPE_SANITY_FILE).write_text(json.dumps(res, indent=2) + "\n")
        out_all[z] = res
    return out_all


# ------------------------------------------------------- T0 reference implementations
# Plan Task 2: an implementer agent (not the author) did T0 on R from the statement
# only, leaving tasks3/<zone>/T0/reference.R.patch. The patch applied to R inside
# aa-actual:R must typecheck, pass the zone's inconsistency tests and leave the probe
# minus exclusions identical to untouched R (run in the same batch). Its added lines
# must carry no hidden-test content. Verdict: tasks3/<zone>/T0/reference_check.json.

T0_REFERENCE_PATCH = "reference.R.patch"
T0_REFERENCE_FILE = "reference_check.json"
_MIN_COPIED_LINE = 30


def t0_reference_verdict(tests: dict[str, str], results: dict[str, str],
                         typecheck_rc: int | None, raw: list[str],
                         kept: list[str], *, typecheck_full_rc: int | None = 0,
                         lint_root_rc: int | None = 0, lint_rc: int | None = 0,
                         related: dict[str, Any] | None = None) -> dict[str, Any]:
    """Verdict for one zone's reference: typecheck clean (evaluator ``tsgo -b`` and
    loot-core ``yarn typecheck``), lint clean (root ``yarn lint`` and the evaluator's
    ``yarn lint``), every T0 test passed, the existing tests related to the touched
    files no worse than on untouched R (``related``: see :func:`t0_related_compare`)
    and the probe minus exclusions identical to untouched R (``raw`` kept for the
    record)."""
    v: dict[str, Any] = {"typecheck_rc": typecheck_rc, "typecheck_full_rc": typecheck_full_rc,
                         "typecheck_ok": typecheck_rc == 0 and typecheck_full_rc == 0,
                         "lint_root_rc": lint_root_rc, "lint_rc": lint_rc,
                         "lint_ok": lint_root_rc == 0 and lint_rc == 0,
                         "tests": results,
                         "tests_pass": all(results.get(n) == "passed" for n in tests),
                         "related": related,
                         "related_ok": related is None or related["ok"],
                         "probe_raw": raw, "probe_minus_exclusions": kept,
                         "probe_same": not kept}
    v["ok"] = (v["typecheck_ok"] and v["lint_ok"] and v["tests_pass"] and v["related_ok"]
               and v["probe_same"])
    return v


def t0_related_compare(base: dict | None, ref: dict | None, ref_rc: int | None,
                       retry: dict | None = None) -> dict[str, Any]:
    """Existing loot-core tests related to the touched files: the reference run against
    the untouched-R run (a superset: related to every zone's touched files). ``ok`` when
    the reference report exists, ran tests, and no test that passed on untouched R
    failed or went missing (no load failure either). ``retry``: the report of the
    failing files run once more, alone (:func:`t0_related_retry_line`); a new failure
    that passes there (e.g. a 20 s timeout under Docker load) is listed as ``flaky`` and
    not counted (spec amendment 2026-10-11f)."""
    from aa.suite import parse_vitest_json
    root = f"/work/actual/{config.LOOT}"
    if ref is None:
        return {"ok": False, "why": "no report", "rc": ref_rc}
    r = parse_vitest_json(ref, root)
    b = parse_vitest_json(base, root) if base is not None else None
    ran = r.passed | r.failed
    files = sorted({t.split("::", 1)[0] for t in ran | r.skipped})
    out: dict[str, Any] = {"rc": ref_rc, "files": files, "passed": len(r.passed),
                           "failed": sorted(r.failed), "skipped": len(r.skipped)}
    if b is None:
        out.update(ok=False, why="no untouched-R report")
        return out
    out["base_failed"] = sorted(t for t in b.failed if t.split("::", 1)[0] in files)
    out["new_failures"] = sorted(t for t in r.failed if t not in b.failed)
    out["missing"] = sorted(t for t in b.passed if t.split("::", 1)[0] in files
                            and t not in ran and t not in r.skipped)
    if retry is not None:
        again = parse_vitest_json(retry, root).passed
        out["flaky"] = sorted(t for t in out["new_failures"] + out["missing"] if t in again)
        out["new_failures"] = [t for t in out["new_failures"] if t not in again]
        out["missing"] = [t for t in out["missing"] if t not in again]
    out["ok"] = bool(ran) and not out["new_failures"] and not out["missing"]
    return out


def _patch_sources(text: str) -> list[str]:
    """loot-core-relative non-test source files a patch touches (for ``vitest related``)."""
    pre = config.LOOT + "/"
    return [f[len(pre):] for f in re.findall(r"^diff --git a/(\S+) b/", text, re.M)
            if f.startswith(pre) and re.search(r"\.[cm]?[jt]sx?$", f)
            and not re.search(r"\.(test|spec)\.[jt]sx?$", f)]


def t0_reference_leaks(zone: str, root: Path | None = None,
                       variant: Path | None = None) -> dict[str, Any]:
    """Hidden-test content in ``<zone>/T0/reference.R.patch``: files under the hidden
    paths or test files; test titles (from consumers.json) on added lines; >=12-char
    string literals of the hidden tests on added lines that are neither in the statement
    (case-insensitive) nor already in the touched files of the untouched variant; hidden
    test lines (>= 30 chars, stripped) copied verbatim onto added lines and not already
    in the variant. ``variant``: untouched R tree (default work/variants/R)."""
    t = load_t0(zone, root)
    p = t.dir / T0_REFERENCE_PATCH
    if not p.exists():
        return {"missing": True, "clean": False}
    variant = variant or config.WORK / "variants" / "R"
    hdir = t.dir / "hidden"
    texts = [(hdir / h).read_text() for h in t.hidden]
    literals = {m.group(2) for x in texts for m in _LITERAL.finditer(x)}
    hidden_lines = {l.strip() for x in texts for l in x.splitlines()
                    if len(l.strip()) >= _MIN_COPIED_LINE}
    titles: set[str] = set()
    for x in texts:
        titles |= {m.group(2) for m in re.finditer(
            r"""\b(?:it|test|describe)(?:\.\w+)?\(\s*(['"`])((?:(?!\1).)+)\1""", x)}
    public = t.statement().lower()
    text = p.read_text()
    files = re.findall(r"^diff --git a/(\S+) b/", text, re.M)
    added_lines = [l[1:] for l in text.splitlines()
                   if l.startswith("+") and not l.startswith("+++")]
    added = "\n".join(added_lines)
    before = "\n".join(_read(variant / f) for f in files)
    out: dict[str, Any] = {
        "files": files,
        "hidden_or_test_files": [f for f in files if f in t.hidden
                                 or re.search(r"\.(test|spec)\.[jt]sx?$|__mocks__|/mocks/", f)],
        "test_names": sorted(n for n in titles | set(t.tests) if n in added),
        "literals": sorted(l for l in literals if l in added and l.lower() not in public
                           and l not in before),
        "lines": sorted({l.strip() for l in added_lines if l.strip() in hidden_lines
                         and l.strip() not in before}),
    }
    out["clean"] = not any(out[k] for k in ("hidden_or_test_files", "test_names",
                                            "literals", "lines"))
    return out


def t0_reference_check(zones: list[str] | None = None, *, root: Path | None = None,
                       work: Path | None = None, workers: int = 1, runner: Any = None,
                       variant: Path | None = None, write: bool = True) -> dict[str, Any]:
    """Check each zone's blind T0 reference in Docker (aa-actual:R) against an untouched
    R run of the same batch; write ``<zone>/T0/reference_check.json``; {zone: verdict}."""
    import datetime
    import subprocess
    import tempfile
    from concurrent.futures import ThreadPoolExecutor

    from aa.evaluate import stage_hidden_tests
    from aa.probe2 import PROBE_DIR, diff_probe, probe_doc
    run = runner or (lambda argv, t: subprocess.run(argv, capture_output=True, text=True,
                                                     timeout=t).returncode)
    zones = zones or list_t0_zones(root)
    tasks = {z: load_t0(z, root) for z in zones}
    exclusions = load_probe_exclusions(root)
    work = Path(work or tempfile.mkdtemp(prefix="aa-t0-reference-")).resolve()
    loot_root = f"/work/actual/{config.LOOT}"
    jobs: list[tuple[str, T0Task | None]] = [("untouched-R", None)]
    jobs += [(f"{z}-reference", t) for z, t in tasks.items()
             if (t.dir / T0_REFERENCE_PATCH).exists()]
    touched = {z: _patch_sources((t.dir / T0_REFERENCE_PATCH).read_text())
               for z, t in tasks.items() if (t.dir / T0_REFERENCE_PATCH).exists()}
    every_touched = sorted({f for fs in touched.values() for f in fs})

    def one(job: tuple[str, T0Task | None]) -> tuple[str, dict]:
        label, t = job
        out = work / label
        out.mkdir(parents=True, exist_ok=True)
        staged = stage_hidden_tests(t.dir, list(t.hidden), "R", out) if t else []
        extra = ["-v", f"{PROBE_DIR}:/probe:ro"]
        if t is not None:
            (out / "seed").mkdir(exist_ok=True)
            (out / "seed" / "seed.patch").write_text((t.dir / T0_REFERENCE_PATCH).read_text())
            extra += ["-v", f"{out / 'seed'}:/seed:ro"]
        related = touched[t.zone] if t is not None else every_touched
        script = t0_script(staged, patch=t is not None, typecheck=True, lint=True,
                           related=related)
        rc = run(_docker("R", f"aa-t0-reference-{label}", out, script, extra),
                 T0_SANITY_TIMEOUT_S)

        def num(name: str) -> int | None:
            try:
                return int((out / name).read_text())
            except (OSError, ValueError):
                return None

        return label, {"docker_rc": rc, "finished": (out / "done").exists(),
                       "script": script,
                       "apply_error": (out / "apply_error").exists(),
                       "apply_log": _read(out / "apply.log")[:2000],
                       "typecheck_rc": num("typecheck_rc"),
                       "typecheck_full_rc": num("typecheck_full_rc"),
                       "lint_root_rc": num("lint_root_rc"), "lint_rc": num("lint_rc"),
                       "related_rc": num("related_rc"), "related_files_in": related,
                       "related_report": _load_report(out / "related.json"),
                       "related_retry_report": _load_report(out / RELATED_RETRY),
                       "typecheck_log_tail": _read(out / "typecheck.log")[-3000:],
                       "typecheck_full_log_tail": _read(out / "typecheck_full.log")[-3000:],
                       "lint_root_log_tail": _read(out / "lint_root.log")[-3000:],
                       "lint_log_tail": _read(out / "lint.log")[-3000:],
                       "tests_rc": num("tests_rc"),
                       "stat": _read(out / "stat.txt"),
                       "tests_report": _load_report(out / "tests.json"),
                       "probe": probe_doc(out / "probe",
                                          _load_report(out / "probe" / "report.json"), loot_root)}

    with ThreadPoolExecutor(max(1, workers)) as ex:
        runs = dict(ex.map(one, jobs))
    ref = runs["untouched-R"]["probe"]
    probe_ok = (runs["untouched-R"]["finished"] and not ref["failed"]
                and ref.get("db") is not None and ref.get("template") is not None)
    image = _image_id("R")
    base = runs["untouched-R"]
    untouched = {k: base[k] for k in ("finished", "typecheck_rc", "typecheck_full_rc",
                                      "lint_root_rc", "lint_rc", "related_rc")}
    if base["related_report"] is not None:
        from aa.suite import parse_vitest_json
        br = parse_vitest_json(base["related_report"], loot_root)
        untouched["related"] = {"files_in": every_touched, "passed": len(br.passed),
                                "failed": sorted(br.failed), "skipped": len(br.skipped)}
    for k in ("typecheck_full_log_tail", "lint_root_log_tail"):
        if base[k.replace("_log_tail", "_rc")] not in (0, None):
            untouched[k] = base[k]
    out_all: dict[str, Any] = {}
    for z, t in tasks.items():
        res: dict[str, Any] = {"zone": z, "date": datetime.date.today().isoformat(),
                               "patch": f"tasks3/{z}/{T0_ID}/{T0_REFERENCE_PATCH}",
                               "image": image, "untouched_R": untouched,
                               "probe_reference_ok": probe_ok,
                               "probe_cases": {"db": len(ref.get("db") or {}),
                                               "template": len(ref.get("template") or {})},
                               "leaks": t0_reference_leaks(z, root, variant)}
        rr = runs.get(f"{z}-reference")
        if rr is None:
            res.update(ok=False, why="no reference patch")
        elif rr["apply_error"] or not rr["finished"]:
            res.update(ok=False, docker_rc=rr["docker_rc"], apply_log=rr["apply_log"],
                       why="patch does not apply" if rr["apply_error"]
                       else "container did not finish")
        else:
            v = t0_reference_verdict(
                t.tests, t0_test_results(rr["tests_report"], t.tests), rr["typecheck_rc"],
                diff_probe(ref, rr["probe"]), diff_probe(ref, rr["probe"], exclusions),
                typecheck_full_rc=rr["typecheck_full_rc"], lint_root_rc=rr["lint_root_rc"],
                lint_rc=rr["lint_rc"],
                related=t0_related_compare(base["related_report"], rr["related_report"],
                                           rr["related_rc"], rr["related_retry_report"]))
            res.update(v, stat=rr["stat"], related_files_in=rr["related_files_in"],
                       commands=rr["script"])
            if not v["typecheck_ok"]:
                res["typecheck_log_tail"] = rr["typecheck_log_tail"]
                res["typecheck_full_log_tail"] = rr["typecheck_full_log_tail"]
            if not v["lint_ok"]:
                res["lint_root_log_tail"] = rr["lint_root_log_tail"]
                res["lint_log_tail"] = rr["lint_log_tail"]
            res["ok"] = v["ok"] and probe_ok and res["leaks"]["clean"]
        if write:
            (t.dir / T0_REFERENCE_FILE).write_text(json.dumps(res, indent=2) + "\n")
        out_all[z] = res
    return out_all
