"""Issue tasks (Javier's decision, 2026-10-06): tasks authored from OPEN GitHub
issues of actualbudget/actual, next to the tasks mined from history (``aa.tasks``).

Layout of ``tasks/<id>/`` (id ``issue-<number>``)::

    task.json            kind "issue", issue, statement_path, hidden_tests, per_condition
    statement.md         what the agent sees (same leak rules as mined statements)
    hidden/<path>        the hidden tests: NEW files under packages/loot-core, written
                         against A (the A+ import rewrite of ``aa.hidden_tests`` is
                         applied on AP/APL at eval time, as for mined tasks)
    revert.<cond>.patch  empty: the start tree is the untouched variant
    reference.A.patch    implementer's fix on A (applies on A and AL)
    reference.AP.patch   implementer's fix on AP (applies on AP and APL)

``task.json`` also carries the fields ``aa.tasks.load_tasks`` reads (``sha`` = "",
``date`` = issue creation date, ``subject`` = issue title, ``touched_files``), so
the runner, the evaluator and ``load_tasks`` take issue tasks unchanged; the
evaluator treats every hidden test of an issue task as a new file
(``aa.evaluate.eval_script(new_hidden=...)``).

``check_issue_task`` is the sanity check, in the condition images with the
evaluator's own script (seeded fast-check, two passes), on all four conditions:

1. untouched variant + hidden tests -> must FAIL (``untouched_passes:<cond>``);
2. untouched variant + the family's reference as the "agent diff" -> hidden tests
   PASS and lint + typecheck green (``reference_fails|reference_lint|
   reference_typecheck:<cond>``).

A failing check is not a drop: it goes to adjudication (over-specified test ->
fix the test; wrong reference -> fix the reference; else drop by hand). The
verdict goes to ``sanity.json`` and the ledger (``sanity: ok|failed``).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from aa import config

KIND = "issue"
FAMILY = {"A": "A", "AL": "A", "AP": "AP", "APL": "AP"}
SANITY_WORK = "issue-sanity"
# Hidden tests must not name the A+ layer (they are written against A and must be
# behavioural on every condition).
APLUS_MARKERS = re.compile(r"#server/domain|server/domain/|#server/db/write|db/write\b|"
                           r"\bCents\b|\bmutation\(")

Executor = Callable[[list[str], int], int]


def is_issue_task(meta: dict) -> bool:
    return meta.get("kind") == KIND


def reference_name(cond: str) -> str:
    return f"reference.{FAMILY[cond]}.patch"


def reference_patch_path(task_dir: Path, cond: str | None) -> Path:
    """Reference diff shown next to a run: the family's patch for issue tasks
    (``reference.A.patch`` on A/AL, ``reference.AP.patch`` on AP/APL), else the
    mined task's ``reference.patch``."""
    task_dir = Path(task_dir)
    if cond in FAMILY and (task_dir / reference_name(cond)).exists():
        return task_dir / reference_name(cond)
    return task_dir / "reference.patch"


def task_id(issue: int) -> str:
    return f"issue-{int(issue)}"


def task_meta(issue: int, title: str, date: str, hidden_tests: list[str],
              touched_files: list[str] | None = None) -> dict:
    return {
        "id": task_id(issue),
        "kind": KIND,
        "issue": int(issue),
        "issue_url": f"https://github.com/actualbudget/actual/issues/{int(issue)}",
        "sha": "",
        "date": date,
        "subject": title,
        "ai_label": None,  # not applicable: issue tasks carry no [AI] commit label
        "hidden_tests": list(hidden_tests),
        "touched_files": list(touched_files or []),
        "statement_path": "statement.md",
        "hidden_dir": "hidden",
        "per_condition": {c: {"revert_patch": f"revert.{c}.patch",
                              "reference_patch": reference_name(c)} for c in config.CONDITIONS},
        "selected": False,
    }


def init_issue_task(issue: int, title: str, date: str, hidden_tests: list[str], *,
                    root: Path | None = None) -> Path:
    """Scaffold ``tasks/issue-<n>/``: task.json and the empty revert patches. The
    author agent then writes statement.md and hidden/<path>, the implementers the
    two reference patches. Never overwrites an existing task.json."""
    d = (root or config.TASKS) / task_id(issue)
    if (d / "task.json").exists():
        raise FileExistsError(d / "task.json")
    d.mkdir(parents=True, exist_ok=True)
    meta = task_meta(issue, title, date, hidden_tests)
    for c in config.CONDITIONS:
        (d / meta["per_condition"][c]["revert_patch"]).write_text("")
    (d / "task.json").write_text(json.dumps(meta, indent=2) + "\n")
    return d


# --------------------------------------------------------------------------- layout

def _patch_paths(patch: str) -> set[str]:
    out = set()
    for ln in patch.splitlines():
        if ln.startswith("diff --git "):
            out.update(p[2:] for p in ln.split()[2:4] if p[:2] in ("a/", "b/"))
    return out


def _in_variant(variant: Path, path: str) -> bool:
    r = subprocess.run(["git", "cat-file", "-e", f"HEAD:{path}"], cwd=variant,
                       capture_output=True)
    return r.returncode == 0


def validate_layout(task_dir: Path, variants: Path | None = None) -> list[str]:
    """Host-side problems with an issue task dir (empty = fine). ``variants``
    (default ``work/variants``): when a condition tree is built there, every hidden
    test must be absent from it (new files only)."""
    from aa.tasks import is_test_file, statement_leaks

    task_dir = Path(task_dir)
    probs: list[str] = []
    try:
        meta = json.loads((task_dir / "task.json").read_text())
    except (OSError, json.JSONDecodeError) as e:
        return [f"task.json: {type(e).__name__}"]
    if not is_issue_task(meta):
        probs.append("kind is not 'issue'")
    if meta.get("id") != task_dir.name:
        probs.append(f"id {meta.get('id')!r} != dir name {task_dir.name!r}")
    if not isinstance(meta.get("issue"), int):
        probs.append("issue number missing")
    for k in ("sha", "date", "subject", "touched_files"):
        if k not in meta:
            probs.append(f"task.json lacks {k!r} (aa.tasks.load_tasks needs it)")
    sp = task_dir / meta.get("statement_path", "statement.md")
    if not sp.is_file() or not sp.read_text().strip():
        probs.append("missing or empty statement")
    else:
        probs += [f"statement {p}" for p in statement_leaks(sp.read_text())]
    hidden = meta.get("hidden_tests") or []
    if not hidden:
        probs.append("no hidden_tests")
    for t in hidden:
        if not t.startswith(config.LOOT + "/") or not is_test_file(t):
            probs.append(f"hidden test not a loot-core test file: {t}")
        src = task_dir / meta.get("hidden_dir", "hidden") / t
        if not src.is_file():
            probs.append(f"hidden copy missing: {t}")
        elif APLUS_MARKERS.search(src.read_text(errors="replace")):
            probs.append(f"hidden test names the A+ layer: {t}")
    per = meta.get("per_condition") or {}
    for c in config.CONDITIONS:
        rp = (per.get(c) or {}).get("revert_patch")
        if not rp or not (task_dir / rp).is_file():
            probs.append(f"{c}: revert patch file missing")
        elif (task_dir / rp).read_text().strip():
            probs.append(f"{c}: revert patch is not empty")
    for fam in sorted(set(FAMILY.values())):
        ref = task_dir / f"reference.{fam}.patch"
        if not ref.is_file() or not ref.read_text().strip():
            probs.append(f"reference.{fam}.patch missing or empty")
            continue
        clash = _patch_paths(ref.read_text(errors="surrogateescape")) & set(hidden)
        if clash:
            probs.append(f"reference.{fam}.patch touches hidden tests: {sorted(clash)}")
    variants = variants or config.WORK / "variants"
    for c in config.CONDITIONS:
        v = variants / c
        if (v / ".git").exists():
            probs += [f"{c}: hidden test already exists: {t}" for t in hidden if _in_variant(v, t)]
    return probs


# --------------------------------------------------------------------------- containers

def run_condition(task_dir: Path, cond: str, mode: str, *, execute: Executor | None = None,
                  checker_dir: Path | None = None, work_root: Path | None = None) -> dict:
    """One evaluator run on ``cond``: ``mode="untouched"`` (empty agent diff, no
    lint/typecheck) or ``mode="reference"`` (the family's reference as the agent
    diff, lint + typecheck). Same script as ``aa.evaluate.evaluate_run``: empty
    revert, hidden tests staged as new files, seeded clean pass decides, probe pass
    after it."""
    from aa import evaluate as ev
    from aa.static_check import check_diff, probe_violations, read_probe_events

    if mode not in ("untouched", "reference"):
        raise ValueError(mode)
    task_dir = Path(task_dir).resolve()
    meta = json.loads((task_dir / "task.json").read_text())
    hidden = meta["hidden_tests"]
    base = (work_root or config.WORK / SANITY_WORK) / meta["id"] / cond
    run_dir, out = base / mode, base / f"{mode}-out"
    for d in (run_dir, out):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    diff = (task_dir / reference_name(cond)).read_text(errors="surrogateescape") \
        if mode == "reference" else ""
    (run_dir / "diff.patch").write_text(diff, errors="surrogateescape")
    ev.stage_hidden_tests(task_dir, hidden, cond, out)
    revert = meta["per_condition"][cond]["revert_patch"]
    script = ev.eval_script(revert, hidden, static_checks=mode == "reference", new_hidden=hidden)
    argv = ev.eval_docker_argv(cond, run_dir, task_dir, out, script,
                               checker_dir or ev.PROBE_SRC.parent)
    eval_error = None
    try:
        (execute or ev.docker_execute)(argv, ev.HOST_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        eval_error = "eval_timeout"
    if eval_error is None:
        e = (out / "eval_error").read_text().strip() if (out / "eval_error").exists() else ""
        eval_error = e or None
    if eval_error is None and not (out / "eval_done").exists():
        eval_error = "container"
    if eval_error in ("container", "eval_timeout") and (out / ev.CLEAN_DONE).exists():
        eval_error = None  # died in the probe pass: the clean pass already decided
    report = None
    try:
        report = json.loads((out / "report.json").read_text())
    except (OSError, json.JSONDecodeError):
        pass
    res: dict[str, Any] = {**ev.hidden_outcome(report, hidden), "eval_error": eval_error,
                           "out_dir": str(out)}
    if mode == "reference":
        lint_rc, tc_rc = ev._read_int(out / "lint_rc"), ev._read_int(out / "typecheck_rc")
        res["lint_ok"] = None if lint_rc is None else lint_rc == 0
        res["typecheck_ok"] = None if tc_rc is None else tc_rc == 0
        res["probe_incomplete"] = ev.probe_incomplete(out, report)
        vs = check_diff(diff, cond)
        vs += probe_violations(read_probe_events(out / "probe.jsonl"), diff, cond)
        res["violations"] = [v.to_json() for v in vs]  # information for adjudication
    return res


def verdict(runs: dict[str, dict], conds: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """(reasons, warnings) from ``{"<cond>:<mode>": outcome}``; no reasons = usable."""
    reasons: list[str] = []
    warnings: list[str] = []
    for c in conds:
        u, r = runs.get(f"{c}:untouched"), runs.get(f"{c}:reference")
        if u is None or r is None:
            reasons.append(f"not_run:{c}")
            continue
        if u["eval_error"]:
            reasons.append(f"sanity_error:{c}:untouched:{u['eval_error']}")
        elif u["correct"]:
            reasons.append(f"untouched_passes:{c}")
        elif all(t.endswith("::<load>") or t.startswith("<") for t in u["failed_tests"]):
            # nothing failed by assertion: the file did not load (e.g. it imports
            # something that only the fix adds = it names the implementation)
            warnings.append(f"untouched_no_assertion_failure:{c}")
        if r["eval_error"]:
            reasons.append(f"sanity_error:{c}:reference:{r['eval_error']}")
            continue
        if not r["correct"]:
            reasons.append(f"reference_fails:{c}")
        if r.get("lint_ok") is not True:
            reasons.append(f"reference_lint:{c}")
        if r.get("typecheck_ok") is not True:
            reasons.append(f"reference_typecheck:{c}")
        if r.get("violations"):
            warnings.append(f"reference_violations:{c}:{len(r['violations'])}")
    return reasons, warnings


def check_issue_task(task_dir: Path, *, conds: tuple[str, ...] = config.CONDITIONS,
                     execute: Executor | None = None, checker_dir: Path | None = None,
                     work_root: Path | None = None, variants: Path | None = None,
                     workers: int = 1, record: bool = True,
                     tasks_root: Path | None = None) -> dict:
    """Sanity check of one issue task on ``conds`` (see module docstring). Returns
    ``{"id", "ok", "reasons", "warnings", "layout", "runs"}``; with ``record`` it is
    written to ``<task_dir>/sanity.json`` and the ledger (``sanity: ok|failed``).
    Layout problems skip the container runs."""
    task_dir = Path(task_dir)
    meta = json.loads((task_dir / "task.json").read_text())
    layout = validate_layout(task_dir, variants)
    runs: dict[str, dict] = {}
    if layout:
        reasons, warnings = [f"layout:{p}" for p in layout], []
    else:
        jobs = [(c, m) for c in conds for m in ("untouched", "reference")]

        def one(job: tuple[str, str]) -> None:
            c, m = job
            runs[f"{c}:{m}"] = run_condition(task_dir, c, m, execute=execute,
                                             checker_dir=checker_dir, work_root=work_root)

        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            list(pool.map(one, jobs))
        runs = {k: runs[k] for k in sorted(runs)}
        reasons, warnings = verdict(runs, conds)
    doc = {"id": meta.get("id", task_dir.name), "kind": KIND, "ok": not reasons,
           "reasons": reasons, "warnings": warnings, "layout": layout,
           "conds": list(conds), "runs": runs}
    if record:
        (task_dir / "sanity.json").write_text(json.dumps(doc, indent=2) + "\n")
        from aa.tasks import read_ledger, update_ledger
        root = tasks_root or task_dir.parent
        # A drop decided elsewhere (eligibility, needs_migration, ...) survives a recheck.
        dropped = read_ledger(root).get(doc["id"], {}).get("dropped") or meta.get("dropped")
        update_ledger(root, doc["id"], kind=KIND,
                      issue=meta.get("issue"), date=meta.get("date"),
                      subject=meta.get("subject"), status="dropped" if dropped else "ok",
                      sanity="ok" if doc["ok"] else "failed",
                      sanity_reasons=reasons or None)
    return doc


def issue_task_dirs(root: Path | None = None) -> list[Path]:
    out = []
    for tj in sorted((root or config.TASKS).glob("*/task.json")):
        try:
            if is_issue_task(json.loads(tj.read_text())):
                out.append(tj.parent)
        except (OSError, json.JSONDecodeError):
            continue
    return out


# ------------------------------------------------------------------ eligibility
# Orchestrator decision (2026-10-06), applying spec 4.2 literally; Javier may
# override: an issue task is eligible iff its reference.A.patch changes a function
# that contains a protected call, by the SAME detector as the mined criterion
# (``aa.tasks.has_protected_call`` at function level: db write API incl. the
# data-specific write functions, raw SQL write on a synced table, money helpers,
# mutator/undoable registration). Deterministic: reference.A.patch applied to the
# committed HEAD of work/variants/A, units from the TypeScript compiler.
INELIGIBLE = "invariant_not_at_stake"
ELIGIBILITY_RULE = ("reference.A.patch changes >=1 function containing a protected call "
                    "(aa.tasks.has_protected_call, function-level); spec 4.2, decision 2026-10-06")


def _git_out(cwd: Path, *args: str, input: str | None = None, env: dict | None = None) -> str:
    import os
    r = subprocess.run(["git", *args], cwd=cwd, input=input, capture_output=True, text=True,
                       check=True, errors="surrogateescape",
                       env={**os.environ, **(env or {})})
    return r.stdout


def reference_protected_units(task_dir: Path, variant: Path | None = None) -> list[str]:
    """Changed units of ``reference.A.patch`` (on the committed HEAD of ``variant``,
    default work/variants/A) whose body has a protected call, sorted. The variant's
    working tree is never touched: the patch is applied to the index of a shared,
    no-checkout clone in a temporary directory."""
    import tempfile

    from aa.tasks import compute_protected_units, parse_patch
    variant = Path(variant or config.WORK / "variants" / "A")
    patch = (Path(task_dir) / reference_name("A")).read_text(errors="surrogateescape")
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        _git_out(Path(tmp), "clone", "-q", "--shared", "--no-checkout", str(variant), str(repo))
        _git_out(repo, "read-tree", "HEAD")
        _git_out(repo, "apply", "--cached", "--unidiff-zero", "--whitespace=nowarn", "-", input=patch)
        tree = _git_out(repo, "write-tree").strip()
        fixed = {"GIT_AUTHOR_NAME": "aa", "GIT_AUTHOR_EMAIL": "aa@localhost",
                 "GIT_COMMITTER_NAME": "aa", "GIT_COMMITTER_EMAIL": "aa@localhost",
                 "GIT_AUTHOR_DATE": "2026-10-06T00:00:00Z",
                 "GIT_COMMITTER_DATE": "2026-10-06T00:00:00Z"}
        sha = _git_out(repo, "commit-tree", tree, "-p", "HEAD", "-m", "reference.A",
                       env=fixed).strip()
        diff = _git_out(repo, "diff", "-U0", "--no-renames", "--no-color", "--no-ext-diff",
                        "HEAD", sha)
        _, changes = parse_patch(diff)
        return sorted(compute_protected_units(repo, [(sha, changes)])[sha])


def record_eligibility(task_dir: Path, *, tasks_root: Path | None = None,
                       variant: Path | None = None, units: list[str] | None = None) -> dict:
    """Compute (or take ``units``) and record ``protected_hits_A``,
    ``protected_units_A`` and ``eligible`` in task.json and the ledger. An
    ineligible task is dropped with reason ``invariant_not_at_stake``; a task that
    becomes eligible again (e.g. a regenerated reference) loses only that drop.
    Other drops (needs_migration, ...) are left alone."""
    from aa.tasks import read_ledger, update_ledger
    task_dir = Path(task_dir)
    root = tasks_root or task_dir.parent
    tj = task_dir / "task.json"
    meta = json.loads(tj.read_text())
    if units is None:
        units = reference_protected_units(task_dir, variant)
    eligible = bool(units)
    entry = read_ledger(root).get(meta["id"], {})
    fields: dict[str, Any] = {"protected_hits_A": len(units), "protected_units_A": units,
                              "eligible": eligible, "eligibility_rule": ELIGIBILITY_RULE}
    meta.update(fields)
    prev = entry.get("dropped") or meta.get("dropped")
    if not eligible and not prev:
        meta["dropped"], meta["selected"] = INELIGIBLE, False
        fields.update(status="dropped", dropped=INELIGIBLE,
                      reason=f"{INELIGIBLE}: reference.A.patch changes no function with a "
                             "protected call (no synced-table write, money helper or "
                             "mutator/undoable in a changed function)")
    elif eligible and prev == INELIGIBLE:
        meta.pop("dropped", None)
        fields.update(status="ok", dropped=None, reason=None)
    tj.write_text(json.dumps(meta, indent=2) + "\n")
    update_ledger(root, meta["id"], **fields)
    return {"id": meta["id"], **fields}

