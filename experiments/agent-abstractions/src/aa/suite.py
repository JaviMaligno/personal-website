from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from aa.config import LOOT, ROOT

# fast-check seed (freeze gate 2026-10-06, spec section 6): every harness vitest run
# (suite baselines, probe-on and probe-off checker runs, both evaluation passes, task
# sanity check) adds substrate/checker/seed.setup.ts as an extra setupFile through the
# wrapper config vitest.aa-seed.config.ts, identically on the four conditions. Only
# copied in for the run, never part of a variant patch or an agent's start tree.
CHECKER_DIR = ROOT / "substrate" / "checker"
SEED_SRC = CHECKER_DIR / "seed.setup.ts"
SEED_CONFIG_SRC = CHECKER_DIR / "vitest.aa-seed.config.ts"
# Destinations relative to packages/loot-core.
SEED_DST = "src/mocks/aa-seed.setup.ts"
SEED_CONFIG_DST = "vitest.aa-seed.config.ts"
SEED_COPIES = ((SEED_SRC, SEED_DST), (SEED_CONFIG_SRC, SEED_CONFIG_DST))


@dataclass
class SuiteResult:
    passed: set[str] = field(default_factory=set)
    failed: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)
    raw: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"passed": sorted(self.passed), "failed": sorted(self.failed),
                "skipped": sorted(self.skipped)}

    @classmethod
    def from_json(cls, d: dict) -> "SuiteResult":
        return cls(passed=set(d.get("passed", [])), failed=set(d.get("failed", [])),
                   skipped=set(d.get("skipped", [])))


def parse_vitest_json(report: dict, root: str) -> SuiteResult:
    r = SuiteResult(raw=report)
    for f in report.get("testResults", []):
        rel = os.path.relpath(f["name"], root)
        for a in f.get("assertionResults", []):
            tid = f"{rel}::{a['fullName']}"
            {"passed": r.passed, "failed": r.failed}.get(a["status"], r.skipped).add(tid)
        if not f.get("assertionResults") and f.get("status") == "failed":
            # File failed to load (syntax/type error at import): count as one failure.
            r.failed.add(f"{rel}::<load>")
    return r


def node_mismatch(tree: Path, actual: str | None = None) -> tuple[str, str] | None:
    """(expected, actual) if the Node on PATH differs from the tree's .nvmrc, else None.

    Node 22 fails two loot-core charset tests that pass on Actual's pinned Node 24,
    so the suite must only ever run on the pinned version.
    """
    nvmrc = tree / ".nvmrc"
    if not nvmrc.exists():
        return None
    expected = nvmrc.read_text().strip()
    if actual is None:
        actual = subprocess.run(["node", "--version"], capture_output=True,
                                text=True).stdout.strip()
    return None if actual == expected else (expected, actual)


@contextmanager
def files_installed(loot: Path, copies: list[tuple[Path, str]]) -> Iterator[None]:
    """Copy each (source, destination relative to ``loot``); always remove them after."""
    dsts = [loot / dst for _, dst in copies]
    try:
        for (src, _), dst in zip(copies, dsts):
            shutil.copy(src, dst)
        yield
    finally:
        for dst in dsts:
            dst.unlink(missing_ok=True)


def seed_installed(loot: Path) -> AbstractContextManager[None]:
    """Copy the fast-check seed setup + its wrapper config into ``loot`` for one run."""
    return files_installed(loot, list(SEED_COPIES))


def vitest_seeded_cmd(report: str, files: list[str] = ()) -> list[str]:
    """vitest argv (run from packages/loot-core): repo config + fast-check seed (wrapper
    config), default timeouts, no probe, JSON report."""
    return ["yarn", "vitest", "--run", "--config", SEED_CONFIG_DST, "--reporter=json",
            f"--outputFile={report}", *files]


@dataclass
class VitestRun:
    """What a host vitest run left behind, for :func:`keep_logs`."""
    cmd: list[str]
    returncode: int | None  # None = killed by the host timeout
    stdout: str
    stderr: str


def _text(b: str | bytes | None) -> str:
    return b.decode(errors="replace") if isinstance(b, bytes) else (b or "")


def run_vitest(cmd: list[str], cwd: Path, env: dict, timeout: int) -> VitestRun:
    """subprocess.run that never raises on the host timeout (partial output is kept)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return VitestRun(cmd, p.returncode, p.stdout, p.stderr)
    except subprocess.TimeoutExpired as e:
        return VitestRun(cmd, None, _text(e.stdout), _text(e.stderr) + f"\n<host timeout {timeout}s>\n")


def keep_logs(log_dir: Path | None, label: str, run: VitestRun, result: SuiteResult,
              extra: dict[str, Path] | None = None) -> Path | None:
    """On any failure (non-zero exit, host timeout, no report, a failed test) save the
    command, stdout, stderr, the JSON report and ``extra`` files under
    ``<log_dir>/<label>-<timestamp>/`` so the failure can be diagnosed afterwards.
    Returns that directory, or None if nothing failed (or no ``log_dir``)."""
    if log_dir is None or (run.returncode == 0 and not result.failed):
        return None
    d = Path(log_dir) / f"{label}-{time.strftime('%Y%m%dT%H%M%S')}"
    n = 1
    while d.exists():
        n += 1
        d = d.with_name(f"{label}-{time.strftime('%Y%m%dT%H%M%S')}-{n}")
    d.mkdir(parents=True)
    (d / "cmd.txt").write_text(" ".join(run.cmd) + f"\nreturncode={run.returncode}\n")
    (d / "stdout.log").write_text(run.stdout)
    (d / "stderr.log").write_text(run.stderr)
    (d / "failed.txt").write_text("".join(f"{t}\n" for t in sorted(result.failed)))
    for name, src in (extra or {}).items():
        if src.exists():
            shutil.copy(src, d / name)
    return d


def result_from_report(report: Path, loot: Path, run: VitestRun) -> SuiteResult:
    if not report.exists():
        tag = "<host timeout>" if run.returncode is None else "<no report>"
        return SuiteResult(failed={f"<suite>::{tag}"})
    try:
        return parse_vitest_json(json.loads(report.read_text()), root=str(loot))
    except json.JSONDecodeError:
        return SuiteResult(failed={"<suite>::<bad report>"})


def run_suite(tree: Path, files: list[str] | None = None, timeout: int = 1200,
              log_dir: Path | None = None, label: str = "suite") -> SuiteResult:
    """Plain vitest run (no probe) with the fast-check seed. For a probed run use
    aa.checker.run_with_probe: vitest 5 has no --setupFiles flag, so the seed and the
    probe go in via wrapper configs. On any failure the report and logs are kept under
    ``log_dir`` (:func:`keep_logs`)."""
    loot = tree / LOOT
    with tempfile.TemporaryDirectory() as tmp, seed_installed(loot):
        out = Path(tmp) / "report.json"
        run = run_vitest(vitest_seeded_cmd(str(out), files or []), loot,
                         {**os.environ, "ENV": "node"}, timeout)
        res = result_from_report(out, loot, run)
        keep_logs(log_dir, label, run, res, {"report.json": out})
        return res
