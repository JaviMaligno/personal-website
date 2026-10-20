import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = (ROOT / "substrate" / "BASE").read_text().strip()
ACTUAL_URL = "https://github.com/actualbudget/actual.git"
CONDITIONS = ("A", "AL", "AP", "APL")
# Patches applied, in order, to build each condition from base.
CONDITION_PATCHES = {
    "A": ("lint-script.patch",),
    "AL": ("lint-script.patch", "lint-a.patch"),
    "AP": ("lint-script.patch", "aplus.patch"),
    "APL": ("lint-script.patch", "aplus.patch", "lint-aplus.patch"),
    # Study 2 (docs/specs/2026-10-08-repetition-vs-abstraction-design.md): R = zones
    # repeated (base, plus the Z2 helper inlined at its loot-core call sites), F = each
    # zone factored into one helper. `lint` = typecheck in both, as in A.
    "R": ("lint-script.patch", "study2/r.patch"),
    "F": ("lint-script.patch", "study2/f.patch"),
    # Study 3 (docs/specs/2026-10-10-agent-as-designer-design.md): each arm is R plus
    # one lever. RG = the written rule in AGENTS.md (spec §4); RL = the duplication
    # ratchet in loot-core's `yarn lint` (the one the prompt names) and in the root
    # `yarn lint`/`lint:fix`, run even when the check before it fails (spec §5); RC = R
    # itself (its lever is the T0 step, not an image change).
    "RG": ("lint-script.patch", "study2/r.patch", "study3/rg.patch"),
    "RL": ("lint-script.patch", "study2/r.patch", "study3/rl.patch"),
    "RC": ("lint-script.patch", "study2/r.patch"),
}
# Study 2 conditions; kept apart from CONDITIONS so study-1 code paths (runner, tables,
# tasks, issue checks) never iterate over them.
CONDITIONS2 = ("R", "F")
# Study 3 arms; R is study 2's condition (fresh runs, same image).
CONDITIONS3 = ("R", "RG", "RL", "RC")
ALL_CONDITIONS = CONDITIONS + CONDITIONS2 + tuple(c for c in CONDITIONS3 if c not in CONDITIONS2)
# RL's ratchet threshold: jscpd min-tokens chosen by the registered calibration (spec
# amendment 2026-10-11, which supersedes 2026-10-10's 25; out/study3/ratchet-calibration.md);
# pinned in the RL image by substrate/patches/study3/rl.patch
# (packages/loot-core/bin/dup-check.config.json).
RATCHET_MIN_TOKENS = 35
AGENTS = ("claude", "codex", "haiku")
MODELS = {"claude": "claude-sonnet-5-5", "codex": "gpt-6-luna", "haiku": "claude-haiku-5-5"}
# CLI that runs each agent. `haiku` (study 2, amendment 12) is Claude Code with a
# different model and is identical to `claude` in every other respect (flags, no-web,
# effort, token, parsers, contamination checks); the agent name stays in outputs/paths.
ENGINE = {"claude": "claude", "haiku": "claude", "codex": "codex"}


def engine(agent: str) -> str:
    """CLI engine ("claude" or "codex") of an agent; ValueError if unknown."""
    try:
        return ENGINE[agent]
    except KeyError:
        raise ValueError(f"unknown agent {agent!r}") from None

# Reasoning effort pinned to the same named level for both agents (Javier,
# 2026-10-06): with an empty config Claude Code ran an adaptive low effort
# (median 151 thinking tokens, tests never run) against Codex's ~734.
EFFORT = "medium"
WALL_LIMIT_S = 25 * 60
TURN_LIMIT = 60
CONCURRENCY = 3
PASSES = 4
LOOT = "packages/loot-core"
WORK = ROOT / "work"
# Study-2 suite baselines (seeded, incl. a seeded A reference) live here, apart from
# study 1's work/baseline-*.json, which predate the fast-check seed and stay untouched.
STUDY2_WORK = WORK / "study2"
# Pilot runs go to a separate tree (AA_RUNS_DIR=runs-pilot) so the runs used to
# select tasks are never reused as experimental passes (that would bias A).
RUNS = ROOT / os.environ.get("AA_RUNS_DIR", "runs")
TASKS = ROOT / "tasks"
PATCHES = ROOT / "substrate" / "patches"
# Tests that fail on the untouched base for environmental reasons; excluded on
# every condition. From `aa suite baseline` (Task 1, Step 7) on base 9732a446 with
# the pinned Node v24.18.1: 1227 passed, 0 failed, 2 skipped -> nothing to exclude.
# The two "charset" failures quoted in the spec only appear on Node 22.x:
#   src/server/transactions/import/parse-file.test.ts::File import handles windows-1252 charset
#   src/server/transactions/import/parse-file.test.ts::File import csv import accepts iso-8859-1 as a windows-1252 alias
# They pass on Node 24, so the suite is run only on the .nvmrc Node
# (aa.suite.node_mismatch) instead of excluding them.
EXCLUDED_TESTS: frozenset[str] = frozenset()
