"""Study 2 equivalence probe (plan Task 1): behavioural diff of A, R and F beyond the suite.

The loot-core suite barely exercises some zone paths (bank-sync linking, ranged
amounts in budget templates, categories in missing groups, weekend rules across month
ends). The probe test files in substrate/study2/probe/ drive those edge cases, plus
every inconsistency F must preserve, and dump what they observe as JSON. They are
copied into a tree only for the run (like the fast-check seed) and removed after; they
are never part of a variant patch or an agent's tree.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path

from aa.config import LOOT, ROOT
from aa.suite import SEED_COPIES, files_installed, result_from_report, run_vitest, vitest_seeded_cmd

PROBE_DIR = ROOT / "substrate" / "study2" / "probe"
# probe file -> destination relative to packages/loot-core
PROBE_FILES = {
    "aa-study2-probe-db.test.ts": "src/server/aa-study2-probe-db.test.ts",
    "aa-study2-probe-template.test.ts": "src/server/budget/aa-study2-probe-template.test.ts",
}
OUTPUTS = ("db", "template")


def run_probe(tree: Path, out_dir: Path, timeout: int = 1800) -> dict:
    """Run the probe files on ``tree`` (seeded, like every harness vitest run).

    Returns {"db": ..., "template": ..., "failed": [...]}: the two JSON dumps (None if a
    file did not write one) and the vitest failures (a probe case records errors itself,
    so a failed vitest test means the probe broke, not the code under test).
    """
    loot = tree / LOOT
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUTS:
        (out_dir / f"{name}.json").unlink(missing_ok=True)
    copies = list(SEED_COPIES) + [(PROBE_DIR / src, dst) for src, dst in PROBE_FILES.items()]
    with tempfile.TemporaryDirectory() as tmp, files_installed(loot, copies):
        report = Path(tmp) / "report.json"
        run = run_vitest(vitest_seeded_cmd(str(report), list(PROBE_FILES.values())), loot,
                         {**os.environ, "ENV": "node", "AA_PROBE_OUT": str(out_dir)}, timeout)
        res = result_from_report(report, loot, run)
        (out_dir / "vitest.log").write_text(run.stdout[-20000:] + "\n---\n" + run.stderr[-20000:])
    doc: dict = {"failed": sorted(res.failed), "passed": len(res.passed)}
    for name in OUTPUTS:
        p = out_dir / f"{name}.json"
        doc[name] = json.loads(p.read_text()) if p.exists() else None
    return doc


def apply_exclusions(doc: dict, exclusions: list[dict]) -> dict:
    """A copy of a probe doc without the excluded observations (study 3, spec section 3:
    ``tasks3/probe-exclusions.json``). Each exclusion names case ids as :func:`diff_probe`
    reports them (``db:<key>`` / ``template:<key>``). Without ``rows_where`` the whole
    case is dropped; with it, only the rows of a case's ``ok`` list that match every
    given field (a case that threw keeps its error)."""
    out = copy.deepcopy(doc)
    for ex in exclusions:
        where = ex.get("rows_where")
        for cid in ex.get("cases") or ():
            name, _, key = cid.partition(":")
            dump = out.get(name)
            if not isinstance(dump, dict) or key not in dump:
                continue
            if not where:
                del dump[key]
                continue
            case = dump[key]
            if isinstance(case, dict) and isinstance(case.get("ok"), list):
                case["ok"] = [r for r in case["ok"] if not (
                    isinstance(r, dict) and all(r.get(f) == v for f, v in where.items()))]
    return out


def diff_probe(a: dict, b: dict, exclusions: list[dict] | None = None) -> list[str]:
    """Case keys whose observation differs between two probe runs (empty = identical),
    after ``exclusions`` (:func:`apply_exclusions`) on both sides.

    A missing dump or any failed probe test on either side is itself a difference.
    """
    if exclusions:
        a, b = apply_exclusions(a, exclusions), apply_exclusions(b, exclusions)
    out = []
    for side, doc in (("a", a), ("b", b)):
        for t in doc.get("failed", []):
            out.append(f"<probe test failed on {side}> {t}")
    for name in OUTPUTS:
        da, db_ = a.get(name), b.get(name)
        if da is None or db_ is None:
            out.append(f"<{name}.json missing on {'a' if da is None else 'b'}>")
            continue
        for k in sorted(set(da) | set(db_)):
            if da.get(k) != db_.get(k):
                out.append(f"{name}:{k}")
    return out


def probe_doc(out_dir: Path, report: dict | None, root: str) -> dict:
    """The doc :func:`run_probe` returns, from a probe run made elsewhere (a container):
    ``out_dir`` holds the two dumps, ``report`` is vitest's JSON report (None = the run
    left none, recorded as a failure), ``root`` the loot-core path inside that run."""
    from aa.suite import parse_vitest_json
    if report is None:
        doc: dict = {"failed": ["<no probe report>"], "passed": 0}
    else:
        res = parse_vitest_json(report, root)
        doc = {"failed": sorted(res.failed), "passed": len(res.passed)}
    for name in OUTPUTS:
        p = out_dir / f"{name}.json"
        try:
            doc[name] = json.loads(p.read_text())
        except (OSError, ValueError):
            doc[name] = None
    return doc
