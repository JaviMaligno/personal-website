"""Runtime-probe plumbing on the host: install the probe, run vitest with it, canary.

Used by `aa checker baseline` (plan Task 5, Step 2) and mirrored inside the
evaluation container by :mod:`aa.evaluate`.

Why not ``aa.suite.run_suite(setup_files=...)``: vitest 5 (Actual's version at
base 9732a446) has no ``--setupFiles`` CLI flag, so that call exits with
``CACError: Unknown option --setupFiles`` and produces no report. The probe is
added instead through ``substrate/checker/vitest.aa.config.ts``, which wraps the
package's own ``vitest.config.ts`` and appends the probe to ``setupFiles``.

Two-pass rule (spec section 6, freeze gate 2026-10-05): the probe slowed fast-check
property tests past vitest's timeouts, so correctness is never measured with the probe.
The evaluator runs the hidden tests clean (decides ``correct``) and again with the
probe and raised timeouts (only collects violations); ``aa checker baseline`` compares
a probe run with raised timeouts against the probe-free baseline. The probe itself
only builds a formatted stack when it emits an event (see probe.setup.ts).

fast-check seed (freeze gate 2026-10-06): every vitest run here, clean or probed, also
gets ``substrate/checker/seed.setup.ts`` (fixed ``fc.configureGlobal`` seed) through
``vitest.aa-seed.config.ts``; ``vitest.aa.config.ts`` extends that config, so the probe
pass is seeded identically. See :mod:`aa.suite`.

Canary (review finding 5): ``substrate/checker/canary.test.ts`` performs one raw
``UPDATE categories``, one raw ``UPDATE category_groups`` inside a ``batchMessages``
callback, and one non-integer ``transactions.amount`` write through the
normal db code paths. :func:`run_canary` fails unless the probe reports all three, with
the canary file as caller. It guards against a probe that silently records nothing
(e.g. ``vi.spyOn`` unable to replace an ESM export), which would make every run
look clean. Validated on base with Node 24.18.1 / vitest 5.0.0: the first probe
version (``applyMessages`` spy) never saw money values and leaked CRDT-internal
writes as ``raw_write``; the current probe passes.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from aa import config
from aa.static_check import read_probe_events
from aa.suite import (CHECKER_DIR, SEED_CONFIG_DST, SEED_CONFIG_SRC, SEED_COPIES,  # noqa: F401
                      SEED_DST, SEED_SRC, SuiteResult, files_installed, keep_logs,
                      result_from_report, run_vitest, vitest_seeded_cmd)

PROBE_SRC = CHECKER_DIR / "probe.setup.ts"
CONFIG_SRC = CHECKER_DIR / "vitest.aa.config.ts"
CANARY_SRC = CHECKER_DIR / "canary.test.ts"
BASELINE_WRITERS = CHECKER_DIR / "baseline-writers.json"
# Destinations relative to packages/loot-core.
PROBE_DST = "src/mocks/aa-probe.setup.ts"
CONFIG_DST = "vitest.aa.config.ts"
CANARY_DST = "src/server/aa-canary.test.ts"


# Probe runs only: vitest's default testTimeout / hookTimeout (5 s / 10 s) times ten.
# The probe slows write-heavy property tests (fast-check in
# src/server/aql/schema/executors.test.ts); correctness is never decided on a probe run
# (spec section 6, two-pass rule), so the probe run only has to finish, not to be fast.
PROBE_TIMEOUT_FACTOR = 10
PROBE_TEST_TIMEOUT_MS = 5_000 * PROBE_TIMEOUT_FACTOR
PROBE_HOOK_TIMEOUT_MS = 10_000 * PROBE_TIMEOUT_FACTOR


def vitest_clean_cmd(report: str, files: list[str] = ()) -> list[str]:
    """vitest argv (run from packages/loot-core), repo config + fast-check seed, default
    timeouts, no probe, JSON report: the pass that decides correctness."""
    return vitest_seeded_cmd(report, files)


def vitest_probe_cmd(report: str, files: list[str] = (), raised_timeouts: bool = True) -> list[str]:
    """vitest argv (run from packages/loot-core) with the probe config and a JSON report;
    by default with testTimeout/hookTimeout raised by PROBE_TIMEOUT_FACTOR."""
    timeouts = ([f"--testTimeout={PROBE_TEST_TIMEOUT_MS}", f"--hookTimeout={PROBE_HOOK_TIMEOUT_MS}"]
                if raised_timeouts else [])
    return ["yarn", "vitest", "--run", "--config", CONFIG_DST, *timeouts, "--reporter=json",
            f"--outputFile={report}", *files]


@contextmanager
def probe_installed(loot: Path, canary: bool = False) -> Iterator[None]:
    """Copy the seed setup + its config, probe + wrapper config (and optionally the
    canary) into ``loot``; always remove."""
    copies = [*SEED_COPIES, (PROBE_SRC, PROBE_DST), (CONFIG_SRC, CONFIG_DST)]
    if canary:
        copies.append((CANARY_SRC, CANARY_DST))
    with files_installed(loot, copies):
        yield


def run_with_probe(tree: Path, files: list[str] | None = None, timeout: int = 1200,
                   canary: bool = False, raised_timeouts: bool = True,
                   log_dir: Path | None = None,
                   label: str = "probe") -> tuple[SuiteResult, list[dict]]:
    """Run vitest in ``tree``'s loot-core with the fast-check seed and the probe (raised
    vitest timeouts by default); returns (suite result, probe events). On any failure
    the report, stdout/stderr and probe events are kept under ``log_dir``."""
    loot = tree / config.LOOT
    with tempfile.TemporaryDirectory() as tmp, probe_installed(loot, canary=canary):
        report = Path(tmp) / "report.json"
        events_file = Path(tmp) / "probe.jsonl"
        env = {**os.environ, "ENV": "node", "AA_PROBE_OUT": str(events_file)}
        env.pop("AA_PROBE_SETUP", None)
        run = run_vitest(vitest_probe_cmd(str(report), files or [], raised_timeouts), loot, env,
                         timeout)
        events = read_probe_events(events_file)
        res = result_from_report(report, loot, run)
        keep_logs(log_dir, label, run, res, {"report.json": report, "probe.jsonl": events_file})
        return res, events


# --------------------------------------------------------------------------- canary

CANARY_CALLER_FILE = CANARY_DST


@dataclass
class CanaryResult:
    problems: list[str]
    events: list[dict] = field(default_factory=list)
    suite: SuiteResult | None = None

    @property
    def ok(self) -> bool:
        return not self.problems


def canary_problems(events: list[dict], suite: SuiteResult | None = None) -> list[str]:
    """Why the canary run does not prove the probe works (empty list = it works)."""
    problems: list[str] = []
    if suite is not None:
        mine = [t for t in suite.passed | suite.failed | suite.skipped
                if t.startswith(CANARY_DST + "::")]
        if not mine:
            problems.append(f"canary tests did not run (no {CANARY_DST} in the vitest report)")
        failed = sorted(t for t in suite.failed if t.startswith(CANARY_DST + "::")
                        or t.startswith("<suite>::"))
        if failed:
            problems.append(f"canary tests failed: {failed}")

    def from_canary(e: dict) -> bool:
        return str(e.get("caller", "")).startswith(CANARY_CALLER_FILE + ":")

    if not any(e.get("kind") == "raw_write" and e.get("table") == "categories" and from_canary(e)
               for e in events):
        problems.append("probe recorded no raw_write on categories from the canary "
                        "(runQuery spy not active, or caller attribution broken)")
    if not any(e.get("kind") == "raw_write" and e.get("table") == "category_groups"
               and from_canary(e) for e in events):
        problems.append("probe recorded no raw_write on category_groups from the canary's "
                        "batchMessages callback (a sync/ frame up the stack hid a raw write)")
    if not any(e.get("kind") == "non_integer_money" and e.get("table") == "transactions"
               and e.get("column") == "amount" and from_canary(e) for e in events):
        problems.append("probe recorded no non_integer_money on transactions.amount from the "
                        "canary (sendMessages spy not active, or caller attribution broken)")
    return problems


Runner = Callable[..., tuple[SuiteResult, list[dict]]]


def run_canary(tree: Path, timeout: int = 600, runner: Runner = run_with_probe,
               **kw) -> CanaryResult:
    """Run only the canary test with the probe on ``tree``. Call before (and refuse to
    write) ``baseline-writers.json`` if it fails."""
    suite, events = runner(tree, files=[CANARY_DST], timeout=timeout, canary=True, **kw)
    return CanaryResult(canary_problems(events, suite), events, suite)


def baseline_entries(events: list[dict]) -> list[dict]:
    """Sorted unique ``{"caller", "sql"}`` raw writers from base probe events,
    excluding the canary's own writes."""
    pairs = {(e["caller"], e.get("sql", "")) for e in events
             if e.get("kind") == "raw_write" and not str(e.get("caller", "")).startswith(CANARY_CALLER_FILE)}
    return [{"caller": c, "sql": q} for c, q in sorted(pairs)]


def is_canary_event(e: dict) -> bool:
    return str(e.get("caller", "")).startswith(CANARY_CALLER_FILE + ":")


def money_events(events: list[dict]) -> list[dict]:
    """``non_integer_money`` events outside the canary (plan Task 5 Step 2: must be 0 on
    the untouched variants, or each one justified in baseline-writers.json)."""
    return [e for e in events if e.get("kind") == "non_integer_money" and not is_canary_event(e)]


def baseline_document(runs: dict[str, dict], writers: list[dict]) -> dict:
    """Content of ``baseline-writers.json``: informational raw-writer list (union over the
    four untouched variants, canary excluded) plus per-condition run evidence."""
    return {
        "note": ("Raw writes to synced tables seen by the probe on the four untouched "
                 "variants (full loot-core suite). Informational only: the checker counts "
                 "a raw_write only when its caller is a line the agent added "
                 "(aa.static_check.probe_violations). Canary writes are excluded."),
        "runs": runs,
        "non_integer_money": [],
        "writers": writers,
    }
