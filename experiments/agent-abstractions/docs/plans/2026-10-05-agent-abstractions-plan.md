# Agent Abstractions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the harness that runs Claude Code and Codex on 15 real Actual
Budget tasks under four conditions (A, A+L, A⁺, A⁺+L) and measures invariant
violations and token cost per run.

**Architecture:** A Python package (`aa`) drives everything from the host:
it fetches Actual at a frozen commit, builds four variant trees from versioned
patch files, mines tasks from git history, runs each agent inside a Docker
container on a fresh copy of the task tree, then evaluates the agent's diff in
a clean container (hidden tests + visible lint + hidden checker) and writes one
`result.json` per run. HTML viewers and a live status page read those files.
The TypeScript side (A⁺ domain layer, ESLint rules, checker probe) lives in
`substrate/` as patches and source files applied onto the Actual checkout.

**Tech Stack:** Python 3.12 + uv + pytest (harness); TypeScript, vitest,
ESLint 9 flat config (inside Actual); Docker 29 (local daemon); Node 24.18.1 +
Yarn 4 (Actual's `.nvmrc`); Claude Code 2.1.289; Codex CLI 0.159.3.

**Spec:** `docs/specs/2026-10-05-agent-abstractions-design.md` (read it first;
section numbers below refer to it).

## Global Constraints

- Substrate: `actualbudget/actual`, package `packages/loot-core`, base commit `9732a446` (2026-10-04), frozen for the phase.
- Conditions: exactly four — `A`, `A+L`, `A⁺`, `A⁺+L` (ids in code: `A`, `AL`, `AP`, `APL`).
- Agents: Claude Code `claude-sonnet-5-5`; Codex `gpt-6-luna` via ChatGPT login, **no API gateway**.
- Agent config isolation: Claude Code gets credentials only (no global CLAUDE.md, memory, MCPs, skills, hooks); Codex gets only `auth.json`.
- Same prompt for both agents: task statement + "leave `test` and `lint` green".
- Per-run limits: 25 min wall clock, 60 turns. Hitting either = `timeout` (counts as failure, flagged).
- `infra` status (429, usage limit, crash) is retried with exponential backoff and never counted as agent failure.
- Concurrency: 3 runs per agent by default.
- Target: 15 tasks × 4 passes × 4 conditions × 2 agents = 480 runs.
- Task sources (amendment 2026-10-06, spec §4): (1) mined history commits, **including** "[AI]"-labelled ones (`ai_label` is a recorded attribute, not a filter); (2) issue tasks authored from open `actualbudget/actual` issues (Task 6b). 15 selected after the pilot, pooled, no per-source quota; ~18 issue tasks authored as spares. `source` and `ai_label` are copied into every `result.json`; tables are reported pooled, per source, and per `ai_label` for mined tasks.
- Hidden checker is stricter than and different from the visible lint, applied identically to all four conditions.
- A⁺ is designed and frozen (dated commit) **before** any task is mined; never adjusted afterwards.
- Full loot-core suite must give identical pass/fail sets on A and A⁺. Baseline on base with Node 24.18.1: **1227 passed, 0 failed, 2 skipped** (the `sync.property.test.ts` `it.skip` tests); `yarn tsgo -b` exit 0, 0 errors. `EXCLUDED_TESTS` is empty: the 2 `parse-file.test.ts` charset failures occur only on Node 22, so the suite runs only on the pinned Node.
- A⁺ adds the domain helper `mutation(name, handler)` = `mutator(undoable(handler))` in `src/server/domain/mutation.ts`; all 82 base `app.method(name, mutator(undoable(handler)))` registrations migrate to it (identical behaviour); the 21 `mutator`-only registrations keep their form. Details in `docs/a-plus-design.md` §4.12.
- Task criterion (miner): a candidate counts when the commit modifies or adds a **function** (non-test code) whose body contains a protected call — db write API incl. the data-specific write functions of `db/index.ts`, a raw SQL write on a synced table, `amountToInteger`/`integerToAmount`, or a `mutator`/`undoable` registration. Function-level, not line-level, not file-level.
- Repo agent config is stripped from every variant in all conditions: `.claude/`, `.codex/`, `.agents/`, `.cursor/` removed; `AGENTS.md` and `CLAUDE.md` stay (identical across conditions and agents).
- Outcomes add `bad_decision_hidden_only` (correct AND ≥1 violation no visible lint set can flag) and a per-task `contaminated` flag copied into every run; headline tables are also reported on unflagged tasks only (spec §6).
- Laptop only. No GCP of any kind.
- All result tables are generated from `result.json` by script; never typed by hand.
- Atlassian/Jira not involved. Code and repo docs in English.

## Review Focus

1. **A task whose revert touches `package.json`/`yarn.lock`/migrations** → the per-variant image no longer matches; expected: the miner drops it with reason `touches_deps`. Test in Task 6.
2. **Agent leaves the tree uncompilable or deletes the hidden test directory** → the evaluator must still produce a `result.json` with `correct=false` and checker results, never crash or skip. Test in Task 9.
3. **Claude Code refuses `--permission-mode bypassPermissions` when run as root** → the container must run as the non-root `node` user; expected: the adapter smoke test passes inside the image. Test in Task 8.
4. **Usage-limit message arriving as a normal assistant message with exit code 0** (not an HTTP 429) → must be classified `infra`, not `ok`/fail. Test in Task 8.
5. **A raw SQL write that was already in base (9 known sites) shows up during hidden tests** → the checker must not count it; only *new* writer locations count. Test in Task 5.

---

## File Structure

```
agent-abstractions/
├── pyproject.toml
├── README.md
├── .gitignore                      # work/, runs/, .venv/
├── docs/
│   ├── specs/2026-10-05-agent-abstractions-design.md
│   ├── plans/2026-10-05-agent-abstractions-plan.md
│   └── a-plus-design.md            # Task 2 (frozen before mining)
├── substrate/
│   ├── BASE                        # "9732a446"
│   ├── patches/
│   │   ├── lint-script.patch       # Task 4: `"lint": "tsgo -b"` in all four conditions
│   │   ├── aplus.patch             # Task 3: domain layer + migration of callers
│   │   ├── lint-a.patch            # Task 4: ESLint rules for A+L
│   │   └── lint-aplus.patch        # Task 4: ESLint rules for A⁺+L (applies on top of aplus.patch)
│   ├── checker/
│   │   ├── probe.setup.ts          # Task 5: vitest setup file (runtime probe)
│   │   └── baseline-writers.json   # Task 5: raw-writer locations seen on base
│   └── docker/Dockerfile           # Task 8
├── src/aa/
│   ├── __init__.py
│   ├── cli.py                      # `aa <subcommand>`
│   ├── config.py                   # constants from Global Constraints
│   ├── substrate.py                # Task 1: fetch base, build variant trees
│   ├── suite.py                    # Task 1: run vitest, parse JSON report
│   ├── static_check.py             # Task 5: diff-based checks
│   ├── tasks.py                    # Task 6: miner + filters + task materialisation
│   ├── memo_probe.py               # Task 7
│   ├── agents.py                   # Task 8: claude / codex adapters, outcome classification
│   ├── runner.py                   # Task 8: docker run, budget, retries
│   ├── evaluate.py                 # Task 9
│   ├── viewer.py                   # Task 10
│   ├── status.py                   # Task 10
│   ├── stats.py                    # Task 11 (copied from agent-code-practices)
│   └── tables.py                   # Task 11
├── tasks/<task_id>/                # Task 6 / 6b output (versioned)
│   ├── task.json
│   ├── statement.md
│   └── revert.patch
├── tests/                          # pytest for the harness
├── work/                           # gitignored: checkouts, variant trees
└── runs/                           # gitignored: run outputs
```

---

### Task 1: Scaffold, substrate fetch and baseline suite

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `README.md`, `substrate/BASE`, `src/aa/__init__.py`, `src/aa/config.py`, `src/aa/substrate.py`, `src/aa/suite.py`, `src/aa/cli.py`
- Test: `tests/test_suite.py`, `tests/test_substrate.py`

**Interfaces:**
- Produces:
  - `aa.config`: `BASE_COMMIT: str`, `CONDITIONS = ("A", "AL", "AP", "APL")`, `WORK: Path`, `RUNS: Path`, `LOOT = "packages/loot-core"`.
  - `aa.substrate.fetch_base() -> Path` (returns `work/actual-base`, a full clone checked out at `BASE_COMMIT`).
  - `aa.substrate.build_variant(cond: str) -> Path` (returns `work/variants/<cond>`, a copy of base with the condition's patches applied, its own git repo with one commit).
  - `aa.suite.SuiteResult` dataclass: `passed: set[str]`, `failed: set[str]`, `skipped: set[str]`, `raw: dict`.
  - `aa.suite.parse_vitest_json(report: dict) -> SuiteResult` (test id = `"<relative file>::<full title>"`).
  - `aa.suite.run_suite(tree: Path, files: list[str] | None = None) -> SuiteResult`. (Superseded: the `setup_files` parameter was removed; vitest 5 has no `--setupFiles` flag. Probed runs use `aa.checker.run_with_probe`, which loads the probe through the wrapper config `substrate/checker/vitest.aa.config.ts`.)

- [ ] **Step 1: Scaffold**

```toml
# pyproject.toml
[project]
name = "aa"
version = "0.1.0"
description = "Do more abstractions + harsh lint constrain coding agents?"
requires-python = ">=3.12"
dependencies = ["unidiff>=0.7"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
aa = "aa.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: needs the Actual checkout / Docker, not run by default"]
```

```
# .gitignore
work/
runs/
.venv/
__pycache__/
```

```python
# src/aa/config.py
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
}
AGENTS = ("claude", "codex")
MODELS = {"claude": "claude-sonnet-5-5", "codex": "gpt-6-luna"}
WALL_LIMIT_S = 25 * 60
TURN_LIMIT = 60
CONCURRENCY = 3
PASSES = 4
LOOT = "packages/loot-core"
WORK = ROOT / "work"
RUNS = ROOT / "runs"
TASKS = ROOT / "tasks"
PATCHES = ROOT / "substrate" / "patches"
```

`substrate/BASE` contains `9732a446`. Run `uv venv && uv pip install -e '.[dev]'`.

`substrate/patches/lint-script.patch` is created here (after Step 7's fetch): in a scratch copy of base, add `"lint": "tsgo -b",` to the `scripts` of `packages/loot-core/package.json` and save `git diff` as the patch. Every condition applies it first; Task 4 only adds the ESLint part for AL/APL.

- [ ] **Step 2: Write the failing parser test**

```python
# tests/test_suite.py
from aa.suite import parse_vitest_json

REPORT = {
    "testResults": [
        {
            "name": "/x/packages/loot-core/src/server/db/index.test.ts",
            "assertionResults": [
                {"fullName": "db insert works", "status": "passed"},
                {"fullName": "db update fails", "status": "failed"},
                {"fullName": "db skip", "status": "pending"},
            ],
        }
    ]
}


def test_parse_vitest_json_ids_relative_to_loot_core():
    r = parse_vitest_json(REPORT, root="/x/packages/loot-core")
    assert r.passed == {"src/server/db/index.test.ts::db insert works"}
    assert r.failed == {"src/server/db/index.test.ts::db update fails"}
    assert r.skipped == {"src/server/db/index.test.ts::db skip"}
```

- [ ] **Step 3: Run it, expect FAIL** — `uv run pytest tests/test_suite.py -v` → `ModuleNotFoundError: aa.suite`.

- [ ] **Step 4: Implement `suite.py`**

```python
# src/aa/suite.py
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from aa.config import LOOT


@dataclass
class SuiteResult:
    passed: set[str] = field(default_factory=set)
    failed: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)
    raw: dict = field(default_factory=dict)


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


def run_suite(tree: Path, files: list[str] | None = None,
              setup_files: list[Path] = (), timeout: int = 1200) -> SuiteResult:
    loot = tree / LOOT
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.json"
        cmd = ["yarn", "vitest", "--run", "--reporter=json", f"--outputFile={out}"]
        for s in setup_files:
            cmd += ["--setupFiles", "./src/mocks/setup.ts", "--setupFiles", str(s)]
        cmd += files or []
        subprocess.run(cmd, cwd=loot, env={**os.environ, "ENV": "node"},
                       capture_output=True, text=True, timeout=timeout)
        if not out.exists():
            return SuiteResult(failed={"<suite>::<no report>"})
        return parse_vitest_json(json.loads(out.read_text()), root=str(loot))
```

- [ ] **Step 5: Run test, expect PASS.**

- [ ] **Step 6: Implement `substrate.py`** (fetch + build variant)

```python
# src/aa/substrate.py
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from aa.config import ACTUAL_URL, BASE_COMMIT, CONDITION_PATCHES, PATCHES, WORK


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


def fetch_base() -> Path:
    base = WORK / "actual-base"
    if not base.exists():
        WORK.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", ACTUAL_URL, str(base)], check=True)
    _git(base, "checkout", "--detach", BASE_COMMIT)
    return base


def fresh_repo(src: Path, dst: Path) -> Path:
    """Copy a tree without history and commit it once (the agent can't mine git log)."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "node_modules"))
    _git(dst, "init", "-q", "-b", "main")
    _git(dst, "add", "-A")
    _git(dst, "-c", "user.name=aa", "-c", "user.email=aa@local", "commit", "-qm", "base")
    return dst


def apply_patches(tree: Path, patches: tuple[str, ...]) -> None:
    for p in patches:
        _git(tree, "apply", "--index", "--whitespace=nowarn", str(PATCHES / p))
    if patches:
        _git(tree, "-c", "user.name=aa", "-c", "user.email=aa@local", "commit", "-qm", "variant")


def build_variant(cond: str) -> Path:
    base = fetch_base()
    dst = fresh_repo(base, WORK / "variants" / cond)
    apply_patches(dst, CONDITION_PATCHES[cond])
    return dst
```

Test (`tests/test_substrate.py`): with a tiny temporary git repo and a patch file in a temp `PATCHES` dir (monkeypatch `aa.substrate.PATCHES`), `fresh_repo` produces exactly one commit and no `node_modules`; `apply_patches` applies and commits. Run → PASS.

- [ ] **Step 7: Baseline (integration, manual)**

```bash
uv run aa substrate fetch            # cli: fetch_base()
cd work/actual-base && yarn install --immutable && cd -
uv run aa suite baseline             # runs full suite on base, writes work/baseline-A.json
```

`cli.py` exposes `substrate fetch`, `variant build <cond>`, `suite baseline [--cond C]` (writes `work/baseline-<cond>.json` with the three sets as sorted lists). Observed on base (Node 24.18.1): 1227 passed, 0 failed, 2 skipped; `config.EXCLUDED_TESTS` stays empty (the charset failures only occur on Node 22).

- [ ] **Step 8: Commit** — `git add -A && git commit -m "Scaffold harness: substrate fetch, variants, vitest parsing"`.

---

### Task 2: A⁺ design document (frozen before mining)

**Files:**
- Create: `docs/a-plus-design.md`

**Interfaces:**
- Produces: the list of domain modules and their exported commands used by Tasks 3–5. **No task may be mined until this file and `aplus.patch` are committed (Task 3) and tagged `aplus-frozen`.**

- [ ] **Step 1: Inventory write call sites in base (input to the design, not the tasks)**

```bash
cd work/actual-base/packages/loot-core
grep -rnE "db\.(update|insert|insertWithUUID|delete_|insertWithSchema|updateWithSchema)\(" src --include='*.ts' | grep -v -E "\.test\.ts|__tests__|/db/index\.ts" > ../../../../work/write-sites.txt
grep -rnE "runQuery\(\s*['\`](INSERT|UPDATE|DELETE)" src --include='*.ts' | grep -v test >> ../../../../work/write-sites.txt
grep -rnE "\b(amountToInteger|integerToAmount)\(" src --include='*.ts' | grep -v test > ../../../../work/money-sites.txt
wc -l ../../../../work/write-sites.txt ../../../../work/money-sites.txt
```

Group the sites by table (`transactions`, `categories`, `category_groups`, `accounts`, `payees`, `schedules`, `rules`, `notes`, `tags`, `zero_budgets`/`reflect_budgets`, others).

- [ ] **Step 2: Write `docs/a-plus-design.md`** with these sections, filled from the inventory:

1. **Principle:** every mutation of synced data goes through a domain command; the command owns CRDT emission (via existing `db.*`), undo wrapping where user-facing, and validation. Money crosses the domain boundary only as `Cents` (branded).
2. **`Cents` type** (`src/server/domain/money.ts`): `type Cents = number & { readonly __brand: 'Cents' }`; constructors `cents.fromAmount(a: Amount, decimals = 2): Cents`, `cents.fromInteger(n: number): Cents` (throws if `!Number.isInteger(n)`); operations `cents.add`, `cents.sub`, `cents.neg`, `cents.sum(xs)`, `cents.toAmount`. No other way to obtain a `Cents`.
3. **Domain modules** — one per table group above, e.g. `domain/transactions.ts` exporting `createTransaction`, `updateTransaction`, `deleteTransaction`, `moveTransaction`; `domain/categories.ts`, `domain/accounts.ts`, `domain/payees.ts`, `domain/schedules.ts`, `domain/rules.ts`, `domain/budget.ts`, `domain/notes.ts`, `domain/tags.ts`. Each command signature uses domain row types with `Cents` for amount fields. List every command with its signature.
4. **Boundary (structural, not lint):** the db write API (`update`, `insert`, `insertWithUUID`, `delete_`, `insertWithSchema`, `updateWithSchema` and the data-specific write functions) moves from `db/index.ts` to `db/write.ts`. `#server/db` keeps only reads, so non-domain code that wants to write has to reach for the domain commands; `db/write` is imported only by `src/server/domain/`, `src/server/db/` and tests. No lint enforces this in A⁺ — enforcement is what the "+L" factor adds (Task 4), so lint stays the only difference between AP and APL.
5. **What is NOT abstracted** (honesty list): `batchMessages`, `runMutator`/`undoable` internals, reads/queries (AQL), sync engine.
6. **Why this is "more than usual"**: compare with A in a short table (A: helpers exist, nothing stops bypass; A⁺: bypass needs an import from a path no non-domain module imports, float money is a type error).

- [ ] **Step 3: Self-check** — the doc mentions no task, commit SHA from history, or test name. `grep -nE "[0-9a-f]{7,}" docs/a-plus-design.md` returns only `9732a446`.

- [ ] **Step 4: Commit** — `git commit -m "A+ design doc (domain layer, Cents, boundary)"`. **Gate: Javier reviews this doc before Task 3** (it defines the treatment).

---

### Task 3: Implement A⁺ and prove equivalence

**Files:**
- Create (inside `work/variants/AP`, then exported): `packages/loot-core/src/server/domain/{money.ts,internal.ts,transactions.ts,categories.ts,accounts.ts,payees.ts,schedules.ts,rules.ts,budget.ts,notes.ts,tags.ts,index.ts}`, `packages/loot-core/src/server/db/write.ts`, `packages/loot-core/src/server/domain/money.test.ts`
- Modify (inside the variant): every file in `work/write-sites.txt`
- Create (harness): `substrate/patches/aplus.patch`, `src/aa/equivalence.py`, `tests/test_equivalence.py`

**Interfaces:**
- Consumes: `build_variant`, `run_suite`, baseline JSON (Task 1); `docs/a-plus-design.md` (Task 2).
- Produces: `substrate/patches/aplus.patch`; git tag `aplus-frozen`; `aa.equivalence.compare(a: SuiteResult, b: SuiteResult, excluded: set[str]) -> list[str]` (returns differing test ids, empty = equivalent).

- [ ] **Step 1: Write `money.test.ts` first (inside the variant)**

```ts
// packages/loot-core/src/server/domain/money.test.ts
import { cents } from './money';

describe('cents', () => {
  it('converts amounts with rounding', () => {
    expect(cents.fromAmount(12.345)).toBe(1235);
    expect(cents.fromAmount(-0.1 - 0.2)).toBe(-30);
  });
  it('rejects non-integers', () => {
    expect(() => cents.fromInteger(1.5)).toThrow('Cents must be an integer');
  });
  it('adds and sums', () => {
    const a = cents.fromInteger(150);
    const b = cents.fromInteger(-50);
    expect(cents.add(a, b)).toBe(100);
    expect(cents.sum([a, b, a])).toBe(250);
  });
  it('round-trips to amount', () => {
    expect(cents.toAmount(cents.fromInteger(1999))).toBe(19.99);
  });
});
```

Run `cd work/variants/AP/packages/loot-core && ENV=node yarn vitest --run src/server/domain/money.test.ts` → FAIL (module not found).

- [ ] **Step 2: Implement `money.ts`**

```ts
// packages/loot-core/src/server/domain/money.ts
import { amountToInteger, integerToAmount, type Amount } from '#shared/util';

declare const brand: unique symbol;
export type Cents = number & { readonly [brand]: 'Cents' };

function fromInteger(n: number): Cents {
  if (!Number.isInteger(n)) throw new Error('Cents must be an integer');
  return n as Cents;
}

export const cents = {
  fromInteger,
  fromAmount: (a: Amount, decimals = 2): Cents => fromInteger(amountToInteger(a, decimals)),
  toAmount: (c: Cents, decimals = 2): Amount => integerToAmount(c, decimals),
  add: (a: Cents, b: Cents): Cents => (a + b) as Cents,
  sub: (a: Cents, b: Cents): Cents => (a - b) as Cents,
  neg: (a: Cents): Cents => -a as Cents,
  sum: (xs: readonly Cents[]): Cents => xs.reduce<number>((s, x) => s + x, 0) as Cents,
  zero: 0 as Cents,
};
```

Run the test → PASS.

- [ ] **Step 3: Move the write API to `db/write.ts`** — cut `update`, `insertWithUUID`, `insert`, `delete_`, `deleteAll`, `insertWithSchema`, `updateWithSchema` and the data-specific write functions (`insertCategoryGroup`, `updateCategoryGroup`, `moveCategoryGroup`, `deleteCategoryGroup`, `insertCategory`, `updateCategory`, `moveCategory`, `deleteCategory`, `insertPayee`, `deletePayee`, `deleteTransferPayee`, `updatePayee`, `mergePayees`, `insertAccount`, `updateAccount`, `deleteAccount`, `moveAccount`, `insertAccountGroup`, `updateAccountGroup`, `moveAccountGroup`, `deleteAccountGroup`, `insertTransaction`, `updateTransaction`, `deleteTransaction`, `moveTransaction`, `moveSchedule`, `insertTag`, `deleteTag`, `updateTag`) from `db/index.ts` into `db/write.ts`, unchanged. `db/index.ts` keeps reads. Add `"#server/db/write": "./src/server/db/write.ts"` to `package.json` `imports` (mirror how `#server/db` is declared there). Update every **test** file importing those names to import from `#server/db/write` (mechanical: `grep -rl` + edit).

- [ ] **Step 4: Write domain commands** — for each module in the design doc, implement commands that call `db/write` functions. Example (copy this shape for every module):

```ts
// packages/loot-core/src/server/domain/transactions.ts
import * as w from '#server/db/write';
import type { DbTransaction } from '#server/db';
import { type Cents } from './money';

export type NewTransaction = Omit<Partial<DbTransaction>, 'amount'> & {
  account: string;
  date: number | string;
  amount: Cents;
};

export async function createTransaction(t: NewTransaction): Promise<string> {
  return w.insertTransaction(t);
}

export async function updateTransaction(
  t: { id: string; amount?: Cents } & Omit<Partial<DbTransaction>, 'amount'>,
): Promise<void> {
  await w.updateTransaction(t);
}

export async function deleteTransaction(t: { id: string }): Promise<void> {
  await w.deleteTransaction(t);
}
```

`domain/index.ts` re-exports all modules and `cents`. `domain/internal.ts` re-exports `#server/db/write` for commands that need the generic `update/insert/delete_` on tables without a dedicated function (document each such use in the design doc's command list).

- [ ] **Step 5: Migrate callers** — for each line in `work/write-sites.txt`, replace the `db.<write>` call with the domain command; where an amount value flows in, wrap with `cents.fromInteger(...)` (value already integer) or `cents.fromAmount(...)` (value is a float amount). The 9 raw `runQuery('INSERT|UPDATE|DELETE …')` sites stay as they are but move behind a domain function each (`domain/internal.ts` documents them). After each module: `yarn tsgo -b` from `packages/loot-core` must be clean.

- [ ] **Step 6: Verify the boundary holds**

```bash
cd work/variants/AP/packages/loot-core
grep -rnE "from '#server/db/write'|from '\.\./db/write'|from '\./write'" src --include='*.ts' \
  | grep -vE "\.test\.ts|__tests__|src/server/domain/|src/server/db/" 
```

Expected: no output.

- [ ] **Step 7: Equivalence test (harness)**

```python
# tests/test_equivalence.py
from aa.equivalence import compare
from aa.suite import SuiteResult


def test_identical_sets_are_equivalent():
    a = SuiteResult(passed={"f::x", "f::y"}, failed={"g::z"})
    b = SuiteResult(passed={"f::x", "f::y", "money::new"}, failed={"g::z"})
    assert compare(a, b, excluded={"g::z"}, allow_new_passing_prefix="src/server/domain/") == []


def test_regression_is_reported():
    a = SuiteResult(passed={"f::x"})
    b = SuiteResult(failed={"f::x"})
    assert compare(a, b, excluded=set()) == ["f::x"]
```

```python
# src/aa/equivalence.py
from aa.suite import SuiteResult


def compare(a: SuiteResult, b: SuiteResult, excluded: set[str],
            allow_new_passing_prefix: str | None = None) -> list[str]:
    diff = []
    for tid in sorted((a.passed | a.failed | b.passed | b.failed) - excluded):
        sa = "p" if tid in a.passed else "f" if tid in a.failed else "-"
        sb = "p" if tid in b.passed else "f" if tid in b.failed else "-"
        if sa == sb:
            continue
        if sa == "-" and sb == "p" and allow_new_passing_prefix and tid.startswith(allow_new_passing_prefix):
            continue
        diff.append(tid)
    return diff
```

Run pytest → PASS. Then integration: `uv run aa suite baseline --cond AP` and `uv run aa equivalence A AP` → must print `equivalent (0 differences)`. Also `yarn typecheck` in the variant must be as clean as on base (compare error counts; base count recorded in Task 1).

- [ ] **Step 8: Export patch, freeze, commit**

```bash
cd work/variants/AP && git add -A && git diff --cached HEAD > ../../../substrate/patches/aplus.patch && cd -
uv run aa variant build AP && uv run aa equivalence A AP   # rebuilt from the patch: still equivalent
git add substrate/patches/aplus.patch src/aa/equivalence.py tests/test_equivalence.py docs/a-plus-design.md
git commit -m "A+ domain layer: Cents, domain commands, write boundary; equivalent to base"
git tag aplus-frozen
```

---

### Task 4: Lint rule sets (A+L and A⁺+L)

**Files:**
- Create (inside variants, exported as patches): `packages/loot-core/eslint.agent.config.mjs`, `packages/loot-core/eslint-rules/{no-raw-synced-write.mjs,no-float-money.mjs,mutator-required.mjs}`, `packages/loot-core/eslint-rules/__tests__/rules.test.mjs`; add script `"lint:agent"` to `packages/loot-core/package.json`; add `eslint@9` and `typescript-eslint` as devDependencies **in the base install layer of the Docker image** (Task 8), not in `yarn.lock` of the task tree.
- Create: `substrate/patches/lint-script.patch`, `substrate/patches/lint-a.patch`, `substrate/patches/lint-aplus.patch`

**Interfaces:**
- Produces: in AL/APL variants, `yarn lint` in `packages/loot-core` runs the repo's oxlint **and** `eslint -c eslint.agent.config.mjs src`; exits non-zero on any violation. In A/AP, `yarn lint` is just the repo's existing lint (so the prompt is identical across conditions).

Rules for **A+L** (invariant expressed on habitual code):
1. `no-raw-synced-write`: flags `runQuery`/`execQuery`/`run` calls whose first argument is a string/template literal starting (after whitespace) with `INSERT`, `UPDATE`, `DELETE`, `REPLACE` and naming a synced table (list from `src/server/sync` dataset names; hard-code the list in the rule), outside `src/server/db/` and `src/server/sync/`. Allow-list: the 9 base sites by file path + exact SQL prefix.
2. `no-restricted-imports`/`no-restricted-syntax`: `sendMessages` may only be referenced in `src/server/db/` and `src/server/sync/`.
3. `no-float-money`: binary `*` or `/` where one operand is the literal `100` (or `10 ** n`, `Math.pow(10, n)`) and the other is an identifier/member matching `/amount|balance|budgeted|spent|carryover/i`, outside `src/shared/util.ts` → "use amountToInteger/integerToAmount".
4. `mutator-required`: `app.method('<name>', fn)` registrations whose handler is not wrapped in `mutator(` (for names not starting with `get`/`query`/`list`) → error.

Rules for **A⁺+L** (do not bypass the abstraction):
1. `no-restricted-imports`: `#server/db/write`, `../db/write`, `./db/write` forbidden outside `src/server/domain/` and `src/server/db/` (non-test files).
2. `no-restricted-syntax`: `TSAsExpression[typeAnnotation.typeName.name='Cents']` outside `domain/money.ts` → "construct Cents with cents.fromInteger/fromAmount".
3. `@typescript-eslint/no-explicit-any` and `@typescript-eslint/ban-ts-comment` as errors on files under `src/server/` (excluding tests).
4. Same `sendMessages` and `mutator-required` rules as A+L.

- [x] **Step 1: Write RuleTester tests** for each custom rule (valid + invalid cases):

```js
// packages/loot-core/eslint-rules/__tests__/rules.test.mjs
import { RuleTester } from 'eslint';
import tsParser from '@typescript-eslint/parser';
import noRaw from '../no-raw-synced-write.mjs';
import noFloat from '../no-float-money.mjs';
import mutatorRequired from '../mutator-required.mjs';

const t = new RuleTester({ languageOptions: { parser: tsParser } });

t.run('no-raw-synced-write', noRaw, {
  valid: [
    { code: "runQuery('SELECT * FROM transactions')", filename: 'src/server/x.ts' },
    { code: "runQuery('UPDATE transactions SET x=1')", filename: 'src/server/db/index.ts' },
  ],
  invalid: [
    { code: "db.runQuery('UPDATE transactions SET amount = ?', [1])", filename: 'src/server/x.ts', errors: 1 },
    { code: 'db.runQuery(`DELETE FROM categories WHERE id = ?`, [id])', filename: 'src/server/x.ts', errors: 1 },
  ],
});

t.run('no-float-money', noFloat, {
  valid: [{ code: 'const x = amountToInteger(amount)', filename: 'src/server/x.ts' }],
  invalid: [
    { code: 'const x = amount * 100', filename: 'src/server/x.ts', errors: 1 },
    { code: 'const y = t.balance / 100', filename: 'src/server/x.ts', errors: 1 },
  ],
});

t.run('mutator-required', mutatorRequired, {
  valid: [
    { code: "app.method('category-create', mutator(undoable(createCategory)))" },
    { code: "app.method('get-categories', getCategories)" },
  ],
  invalid: [{ code: "app.method('category-create', createCategory)", errors: 1 }],
});
```

Run: `node --test eslint-rules/__tests__/rules.test.mjs` → FAIL (rules missing).

- [x] **Step 2: Implement the three rules** (standard ESLint rule objects with `meta`, `create(context)`; filename checks via `context.filename`). Example:

```js
// packages/loot-core/eslint-rules/no-float-money.mjs
const MONEY = /amount|balance|budgeted|spent|carryover/i;
const isHundred = n =>
  (n.type === 'Literal' && n.value === 100) ||
  (n.type === 'BinaryExpression' && n.operator === '**' && n.left.value === 10) ||
  (n.type === 'CallExpression' && n.callee.type === 'MemberExpression' &&
    n.callee.object.name === 'Math' && n.callee.property.name === 'pow');
const isMoney = n =>
  (n.type === 'Identifier' && MONEY.test(n.name)) ||
  (n.type === 'MemberExpression' && !n.computed && MONEY.test(n.property.name));

export default {
  meta: { type: 'problem', messages: { float: 'Money must be converted with amountToInteger/integerToAmount (or cents.*), not raw * or / by 100.' } },
  create(context) {
    if (context.filename.endsWith('src/shared/util.ts')) return {};
    return {
      BinaryExpression(node) {
        if ((node.operator === '*' || node.operator === '/') &&
            ((isHundred(node.left) && isMoney(node.right)) || (isHundred(node.right) && isMoney(node.left)))) {
          context.report({ node, messageId: 'float' });
        }
      },
    };
  },
};
```

`no-raw-synced-write` and `mutator-required` follow the same structure (CallExpression visitor; inspect `node.arguments[0]` literal / template quasis; for `mutator-required` check `node.callee.property.name === 'method'` and that `node.arguments[1]` is a `CallExpression` whose callee name is `mutator`). Run tests → PASS.

- [x] **Step 3: Config files**

```js
// packages/loot-core/eslint.agent.config.mjs  (A+L version)
import tsParser from '@typescript-eslint/parser';
import noRaw from './eslint-rules/no-raw-synced-write.mjs';
import noFloat from './eslint-rules/no-float-money.mjs';
import mutatorRequired from './eslint-rules/mutator-required.mjs';

export default [
  { ignores: ['**/*.test.ts', '**/__tests__/**', '**/__mocks__/**', 'eslint-rules/**'] },
  {
    files: ['src/**/*.ts'],
    languageOptions: { parser: tsParser },
    plugins: { agent: { rules: { 'no-raw-synced-write': noRaw, 'no-float-money': noFloat, 'mutator-required': mutatorRequired } } },
    rules: {
      'agent/no-raw-synced-write': 'error',
      'agent/no-float-money': 'error',
      'agent/mutator-required': 'error',
      'no-restricted-syntax': ['error', {
        selector: "Identifier[name='sendMessages']",
        message: 'Only db/ and sync/ may call sendMessages; use the db write helpers.',
      }],
    },
  },
  { files: ['src/server/db/**', 'src/server/sync/**'], rules: { 'no-restricted-syntax': 'off', 'agent/no-raw-synced-write': 'off' } },
];
```

A⁺+L version: same file plus the `no-restricted-imports` block for `#server/db/write`, the `Cents` cast selector, and `@typescript-eslint/no-explicit-any` + `ban-ts-comment`; `domain/` and `db/` exempt from the import rule.

`lint` script in `packages/loot-core/package.json`, so the prompt ("leave `lint` green") means something in every condition: A and AP get `"lint": "tsgo -b"` (a one-line `substrate/patches/lint-script.patch` applied first in **every** condition — see `CONDITION_PATCHES` in Task 1 — so A is "base + lint script", not raw base); AL and APL get `"lint": "tsgo -b && eslint -c eslint.agent.config.mjs src"`.

- [x] **Step 4: Lint must be green on the untouched variant**

```bash
uv run aa variant build AL && (cd work/variants/AL/packages/loot-core && yarn lint)    # exit 0
uv run aa variant build APL && (cd work/variants/APL/packages/loot-core && yarn lint)  # exit 0
```

If a base site trips a rule, add it to the rule's allow-list (file + line content), never weaken the rule globally. Record the allow-list size in `docs/a-plus-design.md` § honesty list.

- [x] **Step 5: Export patches and commit** — `lint-a.patch` = diff of AL vs base; `lint-aplus.patch` = diff of APL vs AP. Rebuild all four variants from patches and re-run Step 4 + `aa equivalence A AL`, `aa equivalence AP APL` (lint must not change test results). Commit; move tag `aplus-frozen` to this commit (`git tag -f aplus-frozen`) — the treatment is A⁺ **plus** both lint sets; mining starts after this.

**As implemented (2026-10-05):**
- Rule files in each lint variant: `eslint-rules/{allow-list.mjs,base-allow-list.mjs,mutator-required.mjs,no-send-messages.mjs}`; AL adds `no-raw-synced-write.mjs` and `no-float-money.mjs`; APL adds `with-allow-list.mjs` (wraps `@typescript-eslint/no-explicit-any` and `ban-ts-comment` so base sites are allow-listed per line). `sendMessages` is a custom rule (`agent/no-send-messages`) instead of `no-restricted-syntax`, so base sites can be allow-listed per line.
- `mutator-required` takes `form`: `'mutator'` in AL (`app.method('<name>', mutator(...))`), `'mutation'` in APL (`app.method(...mutation('<name>', handler))`; `mutator(...)` alone is reported). Only `app.method` registrations are checked, as in the checker.
- `no-raw-synced-write` names every CRDT-written table (probe list + `account_groups`, `banks`, `cleanup_groups`, `dashboard_pages`, `payee_locations`, `schedules_next_date`, `zero_budget_months`).
- `ban-ts-comment` bans `@ts-expect-error` even with a description (the default allows it, which is the escape hatch from a `Cents` type error).
- The APL import rule is a `no-restricted-imports` regex `^(#server/db/write|(../)+db/write|./db/write)(.[jt]s)?$`; `static_check._LINT_DB_WRITE_IMPORT` matches it.
- RuleTester tests live in the harness (`substrate/lint/rules.test.mjs`, run by `tests/test_lint_rules.py` against the AL/APL trees), not in the variant: loot-core's vitest would collect a `*.test.mjs` there and change the AL/APL test set.
- Allow-list sizes: `docs/a-plus-design.md` §5 item 12.

---

### Task 5: Hidden checker (runtime probe + static diff checks)

**Files:**
- Create: `substrate/checker/probe.setup.ts`, `substrate/checker/baseline-writers.json`, `src/aa/static_check.py`, `tests/test_static_check.py`, `tests/fixtures/bad-*.patch`

**Interfaces:**
- Consumes: `run_suite(tree, files, setup_files)` (Task 1).
- Produces:
  - Probe writes `$AA_PROBE_OUT` (JSONL), one line per event: `{"kind": "raw_write", "table": str, "sql": str, "caller": "src/...:line"}` or `{"kind": "non_integer_money", "table": str, "column": str, "value": number, "caller": str}`.
  - `aa.static_check.check_diff(diff_text: str, cond: str) -> list[Violation]`, `Violation(kind: str, file: str, line: int, detail: str)`.
  - `aa.static_check.probe_violations(events: list[dict], diff_text: str, cond: str) -> list[Violation]`. (Superseded signature: a `raw_write` counts only when its caller lands on a line the agent added; `baseline-writers.json` is informational and discounts nothing. `aa checker baseline` runs `aa.checker.run_canary` first and refuses to write on failure.)

**Checker definition (identical for all four conditions):**
- `raw_write`: a SQL write to a synced table executed during the hidden tests whose **caller location** (first stack frame outside `src/server/db/`, `src/platform/`, `src/server/sync/`) is not in `baseline-writers.json`.
- `non_integer_money`: a value written (via CRDT message or raw SQL) to an amount column (`transactions.amount`, `zero_budgets.amount`, `reflect_budgets.amount`, `zero_budgets.carryover`… — list in the probe) that is not an integer.
- Static (diff added lines only): `send_messages_outside_db` (reference to `sendMessages` outside db/sync), `unwrapped_mutation` (new `app.method('<mutating name>', h)` without `mutator(`), `float_money_math` (same pattern as the lint rule **plus** `parseFloat(`/`Number(` applied to an amount-named value and `toFixed(` on amounts), `db_write_import_outside_domain` (AP/APL only meaningful; computed for all: an added import of `#server/db/write` outside domain/db).
- **Bad decision** = hidden tests pass AND ≥1 violation.

- [ ] **Step 1: Probe setup file**

```ts
// substrate/checker/probe.setup.ts — appended as an extra vitest setupFile at evaluation only
import { appendFileSync } from 'fs';

import * as sqlite from '#platform/server/sqlite';
import * as sync from '#server/sync';

const OUT = process.env.AA_PROBE_OUT!;
const SYNCED = new Set(['transactions', 'accounts', 'categories', 'category_groups', 'payees',
  'payee_mapping', 'schedules', 'rules', 'notes', 'tags', 'zero_budgets', 'reflect_budgets',
  'custom_reports', 'dashboard', 'preferences', 'transaction_filters', 'category_mapping']);
const MONEY: Record<string, string[]> = {
  transactions: ['amount'], zero_budgets: ['amount', 'carryover', 'goal', 'long_goal'],
  reflect_budgets: ['amount', 'carryover', 'goal', 'long_goal'],
};
const IGNORED_FRAMES = /src\/(server\/db|server\/sync|platform)\/|node_modules|probe\.setup/;

function caller(): string {
  const frames = (new Error().stack ?? '').split('\n').slice(2);
  for (const f of frames) {
    const m = f.match(/(src\/[^\s):]+):(\d+)/);
    if (m && !IGNORED_FRAMES.test(f)) return `${m[1]}:${m[2]}`;
  }
  return 'unknown';
}
const emit = (e: object) => appendFileSync(OUT, JSON.stringify(e) + '\n');
const WRITE = /^\s*(INSERT(\s+OR\s+\w+)?\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+["`]?(\w+)/i;

let applying = false;
const origApply = sync.applyMessages;
vi.spyOn(sync, 'applyMessages').mockImplementation(async (msgs, ...rest) => {
  for (const m of msgs) {
    const cols = MONEY[m.dataset];
    if (cols?.includes(m.column) && typeof m.value === 'number' && !Number.isInteger(m.value)) {
      emit({ kind: 'non_integer_money', table: m.dataset, column: m.column, value: m.value, caller: caller() });
    }
  }
  applying = true;
  try { return await origApply(msgs, ...rest); } finally { applying = false; }
});

const origRun = sqlite.runQuery;
vi.spyOn(sqlite, 'runQuery').mockImplementation(((db, sql, params, fetchAll) => {
  const text = typeof sql === 'string' ? sql : (sql as { source?: string }).source ?? '';
  const m = text.match(WRITE);
  if (m && !applying && SYNCED.has(m[3].toLowerCase())) {
    emit({ kind: 'raw_write', table: m[3].toLowerCase(), sql: text.slice(0, 200), caller: caller() });
  }
  return origRun(db, sql, params, fetchAll);
}) as typeof sqlite.runQuery);
```

> Implementation note: if `vi.spyOn` cannot replace ESM namespace exports in this vitest setup, use `vi.mock('#platform/server/sqlite', async importOriginal => …)` with the same wrapping logic; Step 3 validation decides which works.

- [x] **Step 2: Baseline writers** — run the full suite on each of the four untouched variants with the probe; union of all `raw_write` callers → `baseline-writers.json` (sorted list). Command: `uv run aa checker baseline` (cli; sets `AA_PROBE_OUT` and passes `setup_files=[probe.setup.ts copied into the tree at src/mocks/aa-probe.setup.ts]`). Expected: suite results unchanged vs Task 1 baseline (probe must not alter behaviour: `aa equivalence` with probe vs without → 0 differences); `non_integer_money` events on base = 0 (if not 0, inspect each and either fix the probe's column list or record as baseline with justification in the file).

- [ ] **Step 3: Static check tests first**

```python
# tests/test_static_check.py
from aa.static_check import check_diff, probe_violations

DIFF_FLOAT = """\
--- a/packages/loot-core/src/server/budget/actions.ts
+++ b/packages/loot-core/src/server/budget/actions.ts
@@ -10,3 +10,4 @@
 export function f(amount) {
+  const cents = amount * 100;
   return x;
 }
"""

DIFF_SEND = """\
--- a/packages/loot-core/src/server/budget/actions.ts
+++ b/packages/loot-core/src/server/budget/actions.ts
@@ -1,2 +1,3 @@
 import x from 'y';
+await sendMessages([{ dataset: 'categories', row: id, column: 'hidden', value: 1, timestamp: Timestamp.send() }]);
"""

DIFF_METHOD = """\
--- a/packages/loot-core/src/server/budget/app.ts
+++ b/packages/loot-core/src/server/budget/app.ts
@@ -1,2 +1,3 @@
 const app = createApp();
+app.method('category-hide', hideCategory);
"""


def test_float_money_detected():
    v = check_diff(DIFF_FLOAT, cond="A")
    assert [x.kind for x in v] == ["float_money_math"]
    assert v[0].file.endswith("budget/actions.ts") and v[0].line == 11


def test_send_messages_outside_db_detected():
    assert [x.kind for x in check_diff(DIFF_SEND, cond="AP")] == ["send_messages_outside_db"]


def test_unwrapped_mutation_detected():
    assert [x.kind for x in check_diff(DIFF_METHOD, cond="AL")] == ["unwrapped_mutation"]


def test_probe_only_counts_new_writers():
    events = [
        {"kind": "raw_write", "table": "transactions", "sql": "UPDATE …", "caller": "src/server/old.ts:10"},
        {"kind": "raw_write", "table": "transactions", "sql": "UPDATE …", "caller": "src/server/new.ts:5"},
    ]
    v = probe_violations(events, baseline_callers={"src/server/old.ts:10"})
    assert [(x.kind, x.file) for x in v] == [("raw_write", "src/server/new.ts")]
```

Run → FAIL. Implement `static_check.py` with `unidiff.PatchSet`: iterate added lines in files under `packages/loot-core/src/` excluding tests; regexes mirroring the rule definitions above; `probe_violations` dedupes by `(kind, caller)`. Note `probe_violations` compares callers by file **and** line, but line numbers shift when the agent edits a file above a baseline writer: match baseline by `(file, sql prefix)` instead of line — add that case to the test (`caller` line differs, same file and same SQL prefix → not a violation). Run → PASS.

- [x] **Step 4: Validate the checker on known-good and known-bad solutions**
  - Known-good: for 5 mined candidate commits (any, mining not needed: take 5 commits from `git log -- packages/loot-core/src/server` in the scout list), apply nothing (base already contains them) → 0 violations. 
  - Known-bad: write `tests/fixtures/bad-raw-write.patch` (replace a `db.updateCategory` call in `src/server/budget/` with `db.runQuery('UPDATE categories SET hidden = ? WHERE id = ?', …)`), `bad-float.patch` (store `amount * 100` without rounding where `amountToInteger` was used), `bad-unwrapped.patch` (register a mutating method without `mutator`). Apply each to A and to AP (adapting the call to the domain command in AP), run the affected test files with the probe + static check → each must report its violation, and the suite must still pass (that's the point: bad decisions that pass tests). Integration test marked `@pytest.mark.integration`.

**Steps 2 and 4 as implemented (2026-10-05):**
- `uv run aa checker baseline` per condition: canary first (must report its 2 events, which are then excluded), full suite with the probe, pass/fail comparison with the probe-free run (`work/baseline-<cond>.json`, created if missing); refuses to write on a canary failure, any difference, or a `non_integer_money` event. Result on all four variants (Node 24.18.1): A/AL 1227 passed, AP/APL 1231 passed, 0 failed, 2 skipped; 0 differences vs no probe; 0 `non_integer_money`; 13 raw writers per variant, 17 in the union (test fixtures and `migrate/migrations.ts`). `aa equivalence A AL`, `AP APL`, `A AP` → 0 differences. `baseline-writers.json` is now an object (`note`, `runs`, `non_integer_money`, `writers`), read by `static_check.load_baseline`.
- The canary takes the write API from `./db/write` when it exists (A⁺ write boundary) via `import.meta.glob`, so the same file runs in all four conditions. `vi.spyOn` intercepts (cross-module calls), no `vi.mock` needed.
- Known-bad fixtures target `src/server/accounts/app.ts` instead of `budget/` (no loot-core test reaches `category-update`; `account-update` is exercised by `account-groups/app.test.ts`): `tests/fixtures/bad-{raw-write,float,unwrapped}-{A,AP}.patch`. raw-write = rename via `db.runQuery('UPDATE accounts …')` (probe, attributed to the added line); float = starting balance `balance * 100` (AP: `(balance * 100) as Cents`; static `float_money_math`; no test creates an account with a balance, so the runtime `non_integer_money` path is proven by the canary); unwrapped = `account-update` registered without `mutator`/`mutation`. Each is caught with exactly its kind while the 3 affected test files pass (`tests/test_checker_fixtures.py`, `AA_INTEGRATION=1 -m integration`).
- Known-good: the untouched A/AP trees give 0 violations on the same tests, and 8 upstream commits touching `src/server` just before base give 0 static violations.

- [x] **Step 5: Commit** — `git commit -m "Hidden checker: runtime probe, static diff checks, validated on good/bad fixtures"`.

---

### Task 6: Task miner and materialisation

**Files:**
- Create: `src/aa/tasks.py`, `tests/test_tasks.py`, `tasks/<id>/{task.json,statement.md,revert.patch}` (output)

**Interfaces:**
- Consumes: `fetch_base`, `build_variant`, `run_suite`, `CONDITION_PATCHES` (Task 1); tag `aplus-frozen` must exist (assert at start of `mine`).
- Produces:
  - `aa.tasks.Candidate(sha, date, subject, files, test_files, ai_label: bool)`.
  - `aa.tasks.mine(since="2024-10-01") -> list[Candidate]`.
  - `aa.tasks.filter_reason(c: Candidate) -> str | None` (`"ai_label" | "touches_deps" | "no_tests" | "no_protected_sites" | None`).
  - `aa.tasks.materialise(c: Candidate) -> TaskDir | DropReason` — for each condition, starting from the variant tree, `git revert --no-commit <sha>` (3-way, using the base clone as object source); if the revert conflicts on any condition → drop `revert_conflict:<cond>`. Hidden tests = the commit's test files as they exist at base. The task start tree has those test files reverted too (agent never sees them).
  - `tasks/<id>/task.json`: `{"id", "sha", "date", "subject", "hidden_tests": [...], "touched_files": [...], "statement_path", "per_condition": {"A": {"revert_patch": "revert.A.patch"}, ...}}`.
  - `aa.tasks.load_tasks(selected_only=True) -> list[Task]`.

- [ ] **Step 1: Tests first** (pure functions on fake candidates)

```python
# tests/test_tasks.py
from aa.tasks import Candidate, filter_reason


def c(**kw):
    base = dict(sha="abc1234", date="2026-03-01", subject="fix: x", files=["packages/loot-core/src/server/budget/a.ts"],
                test_files=["packages/loot-core/src/server/budget/a.test.ts"], ai_label=False, protected_hits=2)
    base.update(kw)
    return Candidate(**base)


def test_ai_label_dropped():
    assert filter_reason(c(ai_label=True)) == "ai_label"


def test_deps_dropped():
    assert filter_reason(c(files=["package.json", "packages/loot-core/src/x.ts"])) == "touches_deps"
    assert filter_reason(c(files=["packages/loot-core/migrations/1700_x.sql"])) == "touches_deps"


def test_needs_tests_and_protected_sites():
    assert filter_reason(c(test_files=[])) == "no_tests"
    assert filter_reason(c(protected_hits=0)) == "no_protected_sites"


def test_ok():
    assert filter_reason(c()) is None
```

(`Candidate` also carries `protected_hits: int` = number of distinct changed functions (or top-level statements) whose body, pre- or post-commit, contains a protected call — the function-level criterion in Global Constraints; boundaries from `substrate/tools/functions.mjs`.) Run → FAIL; implement; PASS.

- [ ] **Step 2: Implement `mine`** — `git log --since=2024-10-01 --format=%H%x09%ad%x09%s --date=short -- packages/loot-core/src` on the base clone; per commit `git show --name-only` and `git show -U0` to compute `files`, `test_files` (`.test.ts`, `__tests__/`), `protected_hits`; `ai_label = "[AI]" in subject or "[AI]" in body`. Sort: 2026 commits first, then newer first.

- [ ] **Step 3: Implement `materialise`** as specified above, writing `revert.<cond>.patch` = `git diff` of the reverted tree vs the variant. Drop if the revert of non-test files is empty on any condition (commit already superseded).

- [ ] **Step 4: Sanity check per surviving task (integration)** — for each condition: start tree + hidden tests restored → hidden tests **fail** (the task is not trivially solved); start tree + original commit's non-test changes re-applied → hidden tests **pass**. Drop otherwise (`not_discriminating` / `reference_fails:<cond>`).

- [ ] **Step 5: Statements** — for each surviving task, write `statement.md` from the commit message, PR title/body (`gh api repos/actualbudget/actual/commits/<sha>/pulls`) and the diff, describing **behaviour only**. Then run the leak check:

```python
FORBIDDEN = re.compile(r"\b(db\.|sendMessages|amountToInteger|integerToAmount|cents\b|Cents\b|domain/|mutator|undoable|runQuery|insert\w*\(|update\w*\()", re.I)
```

`aa tasks check-statements` fails if any statement matches, or names a file path. Statements are written by one subagent per batch and **reviewed by a second subagent** that sees only statement + diff and answers "could someone solve this from the statement alone, and does it reveal the implementation?".

*As implemented (2026-10-06):* the revert and `reference.patch` skip `upcoming-release-notes/*.md` (Actual deletes them at each release, so the reverse patch aborted on every candidate) and Playwright screenshot baselines (`*-snapshots/*.png`, binary, never run here); `aa.tasks.is_non_code`. `aa tasks check-statements` implements the leak check (forbidden regex + file paths, surviving tasks only). The statement reviewer is a separate `claude -p --tools ""` process per batch that sees only statement + commit diff; its answers are kept in `tasks/_reviews/`.

- [ ] **Step 6: Commit** — `tasks/` (all candidates with drop reasons in `tasks/_ledger.json`, surviving tasks with full dirs). `git commit -m "Mine tasks from Actual history (frozen A+)"`.

*Result (2026-10-06):* 724 candidates → 2 survivors. Drops: `no_tests` 379, `ai_label` 153, `no_protected_sites` 77, `touches_deps` 73, `revert_conflict` 32 (A 30, AP 2) of the 34 static passers, `no_tests_at_base` 8.

**Amendment 2026-10-06 (spec §4).** `ai_label` is no longer a drop reason: `filter_reason` stops returning `"ai_label"` (update `test_ai_label_dropped` to assert `None` and that `Candidate.ai_label` is kept), `task.json` gains `"source": "mined"` and `"ai_label": bool`, and the 153 ledger entries dropped with `ai_label` are re-run through Steps 3–5 (static filters, materialise, sanity, statements, leak check, review). Existing ledger entries keep their history: the old drop is recorded as `superseded_reason: "ai_label (amendment 2026-10-06)"`, not deleted. The memorisation probe (Task 7) then runs on the new survivors with `--missing-only`.

---

### Task 6b: Issue tasks from open GitHub issues (amendment 2026-10-06)

Decided by Javier on 2026-10-06, before any experimental run; spec §4.2 is
normative. Reason: mining yields 2 tasks (32/34 static passers conflict on
revert; 153 "[AI]" commits were excluded), so tasks are also authored from open
issues, which need no revert.

**Files:**
- Create: `src/aa/issue_tasks.py`, `tests/test_issue_tasks.py`, `tasks/issue-<n>/{task.json,statement.md,hidden/…,reference.A.patch,reference.AP.patch,triage.json,adjudication.md}` (output), `tasks/_issues.json` (triage ledger).

**Interfaces:**
- Consumes: `build_variant`, `CONDITION_PATCHES` (Task 1); hidden-test rewrite for AP/APL (`aa.hidden_tests`, Task 9 decision); `run_suite` (seeded, Task 1/9); lint + typecheck commands (Task 4); `check_diff` and the probe (Task 5); `aa tasks check-statements` and the statement reviewer (Task 6 Step 5); memo probe (Task 7). Tag `aplus-frozen` must exist.
- Produces:
  - `task.json` with `{"id": "issue-<n>", "source": "issue", "issue": {"number", "url", "title", "created_at", "state_at_snapshot", "snapshot_date"}, "ai_label": null, "hidden_tests": [...], "per_condition": {"A": {"reference_patch": "reference.A.patch"}, "AL": {"reference_patch": "reference.A.patch"}, "AP": {"reference_patch": "reference.AP.patch"}, "APL": {"reference_patch": "reference.AP.patch"}}, "start_tree": "untouched", "author": {"agent", "model"}, "implementer": {"agent", "model"}, "selected": false}`. No `revert_patch`: the runner applies an empty patch (start tree = variant).
  - `aa issues triage`, `aa issues sanity <id>`, `aa issues status`.

- [ ] **Step 1: Snapshot and triage.** `gh issue list -R actualbudget/actual --state open --limit 1000 --json number,title,body,labels,createdAt,url` → `work/issues-snapshot-<date>.json` (snapshot date recorded). Triage (one subagent, logged per issue in `tasks/_issues.json` with a one-line reason) keeps issues whose natural fix needs writes to synced tables and/or money arithmetic in `packages/loot-core`, and drops: UI-only / outside loot-core, needs deps or migrations, no decidable expected behaviour, does not reproduce on base `9732a446`, or an upstream fix already linked (recorded for the contamination flag). Order survivors by issue number descending; author until **~18** pass Step 6.

- [ ] **Step 2: Statement.** From the issue only (title, body, discussion), behaviour only; `aa tasks check-statements` leak check and the second-reader review (Task 6 Step 5), unchanged.

- [ ] **Step 3: Hidden tests (author agent).** A separate session per task that sees the issue, the statement and the A tree, never a reference. Rules, checked by `aa issues sanity` and in review:
  - behavioural: drive the code through handlers / the public API and assert on resulting DB state and return values;
  - never name implementation functions to be written, never import or mention `domain/`, `Cents`, `#server/db/write` or any lint rule; reads only through APIs present identically on all four variants;
  - placed as new `*.test.ts` files under `packages/loot-core/src/` (listed in `hidden_tests`), absent from every start tree;
  - on AP/APL the hidden files get only the mechanical rewrite of the "Hidden-test rewrite on AP/APL" decision (Task 9), nothing else.

- [ ] **Step 4: Fail on untouched.** Run the hidden tests (seeded suite runner, clean pass) on the four untouched variants: each must have ≥1 failing test. Otherwise drop `not_discriminating`.

- [ ] **Step 5: References (implementer agent ≠ author).** Separate sessions that see the statement and the repo only (no hidden tests, no issue discussion beyond the statement): one on **A** (→ `reference.A.patch`, used for A and AL) and one on **AP** (→ `reference.AP.patch`, used for AP and APL). Agent quota rule: Codex at any time; Claude Code only after 22:00 local.

- [ ] **Step 6: Reference check.** For each condition: untouched variant + its reference + hidden tests → all hidden tests pass (clean pass), `yarn lint` and `yarn tsgo -b` green **in that condition** (A reference under the A+L rules on AL; AP reference under the A⁺+L rules on APL), and `check_diff` + probe report 0 violations. Write `sanity.json` per condition.

- [ ] **Step 7: Adjudicate failures.** For each failing check, read test + reference + statement side by side and classify in `adjudication.md`: *over-specified test* (asserts something the statement does not require) → fix the test (author agent) and rerun Steps 4 and 6; *wrong reference* → fix the reference (implementer agent) and rerun Step 6. At most two rounds; otherwise drop `no_convergence`. Every decision and reason is logged; nothing is forced through.

- [ ] **Step 8: Memorisation probe and contamination.** Run Task 7's probe on the issue tasks, scored against `reference.A.patch` (drop at ≥ 0.5). `contaminated` = a public fix PR exists, merged or not (`public_fix_pr` in task.json; amended 2026-10-06), or similarity ≥ 0.25 (spec §6 item 5).

- [ ] **Step 8b: Eligibility (decision 2026-10-06, spec §4.2).** `aa issues eligibility`: eligible iff `reference.A.patch` changes a function with a protected call (mined detector); else dropped `invariant_not_at_stake`. Rerun after any reference is regenerated. Provenance (`author`, `implementer`, `adjudicated_by`), `adjudication.md`, `related_prs` / `public_fix_prs` and `tasks/_issues.json` are recorded per spec §4.2 / §6 item 5.

- [ ] **Step 9: Harness wiring.** `load_tasks` returns both sources; runner and evaluator take `start_tree: "untouched"` (empty revert) and the per-condition reference; `result.json` gains `source` and `ai_label`. Tests: `tests/test_issue_tasks.py` covers task.json schema, empty start patch, reference-per-condition mapping, and the drop reasons (`not_discriminating`, `reference_fails:<cond>`, `no_convergence`). Run → PASS.

- [ ] **Step 10: Commit** — `tasks/issue-*`, `tasks/_issues.json`, code and tests. `git commit -m "Issue tasks from open actualbudget/actual issues (amendment 2026-10-06)"`.

---

### Task 7: Memorisation probe

**Files:**
- Create: `src/aa/memo_probe.py`, `tests/test_memo_probe.py`

**Interfaces:**
- Consumes: `load_tasks(selected_only=False)` (Tasks 6 and 6b; for issue tasks the reference diff is `reference.A.patch`).
- Produces: `aa.memo_probe.similarity(predicted_diff: str, reference_diff: str) -> float` (token Jaccard over **added** lines, identifiers and string literals only); `aa memo-probe run` writes `tasks/<id>/memo.json` = `{"claude": {"similarity": float, "raw": path}, "codex": {...}}` and marks the task `memorised` in the ledger if either similarity ≥ 0.5.

- [ ] **Step 1: Test similarity**

```python
from aa.memo_probe import similarity

REF = "+++ b/a.ts\n+  const total = sumAmounts(rows);\n+  return total;\n"


def test_identical_is_one():
    assert similarity(REF, REF) == 1.0


def test_unrelated_is_low():
    assert similarity("+++ b/a.ts\n+  console.log('hi');\n", REF) < 0.2


def test_ignores_removed_lines():
    assert similarity("+++ b/a.ts\n-  const total = sumAmounts(rows);\n", REF) == 0.0
```

Run → FAIL; implement (regex `[A-Za-z_]\w+|'[^']*'|"[^"]*"` over lines starting with `+` but not `+++`); PASS.

- [ ] **Step 2: Probe runner** — prompt (same for both): *"This is a change in the open-source repository actualbudget/actual (packages/loot-core). Without access to the repository, write the unified diff you believe implements it. Statement: <statement.md>. Files likely touched: <touched_files>."* Claude: `claude -p --model claude-sonnet-5-5 --output-format json` from an empty temp dir with the isolated config of Task 8; Codex: `codex exec --model gpt-6-luna --skip-git-repo-check -o <file>` from an empty temp dir with isolated `CODEX_HOME`. Store raw outputs under `work/memo/`.

- [ ] **Step 3: Estimate, then run** — before running, print `N tasks × 2 agents` and expected wall time (~1 min per call, 4 parallel); this consumes subscription quota only. Run; commit `memo.json` files and ledger.

  *As implemented (2026-10-06):* both CLIs run with **no tools** (`claude --tools ""`; `codex exec --strict-config -c web_search=disabled --disable shell_tool …`). Without that, Codex web-searched github.com/actualbudget/actual and copied the merged fix (4556e9e244, similarity 1.0). A canary prompt confirmed that both agents then answer `NO_TOOLS`. Any transcript that shows tool use is rejected as invalid. An answer without a diff (a refusal: "can't inspect the repository") is re-asked up to 2 times and never scored as 0.0. Rate-limit and usage-limit errors are infra and are retried with backoff (60 s doubling, capped at 30 min). `aa memo-probe run --missing-only` re-probes only the entries that have no similarity, so the valid samples are not re-drawn. Results (N=2): 81ea158cf6 claude 0.375 / codex 0.310 → clean. Both overlaps come from the statement, which gives the `getCategoryAverage` signature, the algorithm and the UI wording, plus keywords; there are no reference-specific helpers. 4556e9e244 claude 0.224 / codex 0.750 → **memorised by the 0.5 rule**. Manual reading says it is a generic, obvious fix: the reference adds only 13 distinct tokens, mostly keywords, and the shared idiom is `new Set((await db.getCategories()).map(…)).has(…)`. Codex placed it in a different function and said it couldn't verify the API. Claude wrote the same idea independently. That makes it a likely false positive caused by the tiny reference. The rule is applied as written. Eligible after the probe: 1 (81ea158cf6).

---

### Task 8: Docker image, agent adapters and runner

**Files:**
- Create: `substrate/docker/Dockerfile`, `src/aa/agents.py`, `src/aa/runner.py`, `tests/test_agents.py`, `tests/fixtures/claude-stream-*.jsonl`, `tests/fixtures/codex-*.jsonl`

**Interfaces:**
- Consumes: variants (Tasks 3–4), tasks (Task 6), `config` constants.
- Produces:
  - Images `aa-actual:<cond>` (variant tree at `/work/actual`, `node_modules` installed, owned by `node`).
  - `aa.agents.Usage(input_tokens:int, output_tokens:int, cached_input_tokens:int, turns:int, tool_calls:int)`.
  - `aa.agents.parse_claude_stream(lines: Iterable[str]) -> tuple[Usage, Outcome]`, `aa.agents.parse_codex_stream(lines) -> tuple[Usage, Outcome]`; `Outcome = Literal["ok", "timeout", "infra"]`.
  - `aa.agents.classify_infra(text: str) -> bool` (usage-limit / rate-limit / overloaded / auth messages).
  - `aa.runner.run_one(agent: str, cond: str, task_id: str, pass_idx: int) -> Path` (run dir with `transcript.jsonl`, `diff.patch`, `agent.json`).
  - `aa run --agent claude --conds A,AL,AP,APL --tasks all --passes 4` (resumable: skips run dirs whose `agent.json` has status `ok`/`timeout`; re-queues `infra` with backoff 60 s → 120 → 240 → … cap 30 min).

- [ ] **Step 1: Dockerfile**

```dockerfile
# substrate/docker/Dockerfile
FROM node:24.18.1-bookworm
RUN corepack enable && apt-get update && apt-get install -y --no-install-recommends git python3 build-essential ripgrep && rm -rf /var/lib/apt/lists/*
RUN npm i -g @anthropic-ai/claude-code@2.1.289 @openai/codex@0.159.3
ARG COND
COPY --chown=node:node variant/ /work/actual/
USER node
WORKDIR /work/actual
RUN yarn install --immutable && (cd packages/loot-core && yarn add -D eslint@9 @typescript-eslint/parser@8 typescript-eslint@8 --mode=skip-build || true)
RUN git config --global user.email agent@local && git config --global user.name agent
```

Note: the eslint devDependencies must be identical in all four images (installed in all, configured only in AL/APL) so the environment differs only by the patches. Build: `uv run aa image build <cond>` copies `work/variants/<cond>` into a temp build context as `variant/` and runs `docker build --build-arg COND=<cond> -t aa-actual:<cond>`. Verify: `docker run --rm aa-actual:A bash -lc 'cd packages/loot-core && ENV=node yarn vitest --run src/server/db/index.test.ts'` passes.

- [ ] **Step 2: Auth setup (one-time, Javier)** — Claude: `claude setup-token` → store token in `~/.aa-claude-token` (chmod 600); passed as `CLAUDE_CODE_OAUTH_TOKEN`. Codex: copy `~/.codex/auth.json` into a per-run temp `CODEX_HOME` (read-only bind of a copy). Nothing else from `~/.claude` or `~/.codex` is mounted.

- [ ] **Step 3: Parser tests first** — record real fixtures by running one trivial prompt per agent inside the image (`"Print the number of files in packages/loot-core/src/server/db"`), save stdout to `tests/fixtures/claude-stream-ok.jsonl` and `codex-ok.jsonl`; hand-write `claude-stream-usage-limit.jsonl` (a final `result` event with `is_error: true` and text containing `usage limit`) and `codex-ratelimit.jsonl` (an `error` event with `429`).

```python
# tests/test_agents.py
from pathlib import Path
from aa.agents import parse_claude_stream, parse_codex_stream, classify_infra

F = Path(__file__).parent / "fixtures"


def test_claude_ok_has_usage():
    usage, outcome = parse_claude_stream((F / "claude-stream-ok.jsonl").read_text().splitlines())
    assert outcome == "ok" and usage.input_tokens > 0 and usage.turns >= 1


def test_claude_usage_limit_is_infra_even_with_exit_0():
    _, outcome = parse_claude_stream((F / "claude-stream-usage-limit.jsonl").read_text().splitlines())
    assert outcome == "infra"


def test_codex_ok_and_ratelimit():
    assert parse_codex_stream((F / "codex-ok.jsonl").read_text().splitlines())[1] == "ok"
    assert parse_codex_stream((F / "codex-ratelimit.jsonl").read_text().splitlines())[1] == "infra"


def test_classify_infra():
    assert classify_infra("Claude AI usage limit reached|1760000000")
    assert classify_infra("Error: 429 Too Many Requests")
    assert classify_infra("You've hit your usage limit")
    assert not classify_infra("Tests failed: 3")
```

Run → FAIL; implement parsers (Claude: sum `usage` from `assistant` messages, `num_turns` from final `result`; Codex: sum `token_count`/`turn.completed` usage events, count `item.completed` of type command/tool as tool calls); PASS. Field names must be taken from the recorded fixtures, not assumed.

- [ ] **Step 4: Prompt** (identical for both agents, stored in `src/aa/prompt.md`):

```
You are working in the repository at /work/actual (Actual Budget). The relevant
package is packages/loot-core.

Task:
<statement.md contents>

When you are done, `yarn test` and `yarn lint` in packages/loot-core must pass
(run the relevant test files; the full suite is slow). Do not ask questions;
make the change.
```

- [ ] **Step 5: `run_one`** — create run dir `runs/<agent>/<cond>/<task>/<pass>/`; `docker run --rm --name aa-<agent>-<cond>-<task>-<pass> --cpus 2 --memory 6g` with env (token / CODEX_HOME bind), command:

```bash
git apply --whitespace=nowarn - && rm -rf .git && git init -q -b main && git add -A && git commit -qm start \
  && touch /out/setup_ok || exit 3
timeout 1500 <agent command> < /dev/null ; git add -A && git diff --cached HEAD > /out/diff.patch
```

(Superseded mount layout: the revert patch arrives on stdin (`docker run -i`) and git history is reset to one `start` commit, so no solution, A⁺ or lint patch is visible to the agent. Only `/task/prompt.txt` (ro) and `/out` are mounted. Missing `setup_ok` → `setup_error`, final.)

Claude command: `claude -p "$(cat /task/prompt.txt)" --model claude-sonnet-5-5 --output-format stream-json --verbose --permission-mode bypassPermissions --max-turns 60 > /out/transcript.jsonl`, with `CLAUDE_CONFIG_DIR=/tmp/cc` (empty). Codex command: `codex exec --model gpt-6-luna --json --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "$(cat /task/prompt.txt)" > /out/transcript.jsonl` with `CODEX_HOME=/tmp/codexhome` (contains only `auth.json`). The container is the sandbox (hence the bypass flags), runs as `node`, and mounts only `/task` (ro) and `/out`. Exit 124 from `timeout` or turns ≥ 60 → `timeout`. Write `agent.json` = `{status, usage, wall_s, started_at, image_digest, cli_version}`.

- [ ] **Step 6: Root check (Review Focus #3)** — integration test: `run_one` with a 1-line dummy task inside `aa-actual:A` for each agent → status `ok`, `diff.patch` non-empty.

- [ ] **Step 7: Scheduler** — `aa run` builds the queue (agent × cond × task × pass), interleaving conditions per task (so quota drift affects all conditions equally: order = for pass, for task, shuffled conds with fixed seed), runs `CONCURRENCY` workers per agent, re-queues `infra`. Commit.

---

### Task 9: Evaluator

**Files:**
- Create: `src/aa/evaluate.py`, `tests/test_evaluate.py`

**Interfaces:**
- Consumes: run dir from Task 8; `run_suite`, probe, `check_diff`, `probe_violations`, `baseline-writers.json`.
- Produces: `runs/.../result.json`:

```json
{
  "agent": "claude", "cond": "AP", "task": "t07", "pass": 2,
  "status": "ok", "correct": true,
  "violations": [{"kind": "raw_write", "file": "src/server/x.ts", "line": 40, "detail": "UPDATE categories"}],
  "bad_decision": true,
  "lint_ok": true, "typecheck_ok": true,
  "tokens": {"input": 0, "output": 0, "cached_input": 0},
  "turns": 0, "tool_calls": 0, "wall_s": 0,
  "diff": {"files": 0, "added": 0, "removed": 0},
  "reimplementation": false,
  "trace": {"files_read": [], "first_edit_turn": null, "lint_invocations": 0}
}
```

- [ ] **Step 1: Tests first** — with fixture run dirs (fake `agent.json`, small `diff.patch`) and the suite runner monkeypatched: (a) passing hidden tests + no violations → `correct=true, bad_decision=false`; (b) passing + a float-money line → `bad_decision=true`; (c) `diff.patch` that breaks compilation (suite returns `<load>` failure) → `correct=false`, result still written (Review Focus #2); (d) diff deleting the hidden test file → evaluator restores hidden tests from base before running, so deletion has no effect; (e) `status=timeout` still evaluated (diff may be partial) but `correct` counted as false in analysis via `status`.

- [ ] **Step 2: Implement** — in a fresh container of the same image: apply `revert.patch`, apply agent `diff.patch` (if it fails to apply → `correct=false`, `violations=[]`, `eval_error="diff_apply"`), **overwrite hidden test files with their base version**, copy `probe.setup.ts`, run `vitest --run <hidden tests>` with the probe, run `yarn lint` (records `lint_ok`) and `yarn tsgo -b` (`typecheck_ok`), run `check_diff` on `diff.patch`, merge violations. `reimplementation`: added lines define a function whose body contains `sendMessages(` or `Math.round(` × 100 pattern or a raw SQL write, while an equivalent helper existed (static: true if any of those kinds fired — reported separately, not part of `bad_decision`). Trace from transcript: files read (Read/cat/sed tool inputs), first edit turn, count of `lint` invocations.

**Two-pass rule (decision 2026-10-05, spec §6; replaces "run `vitest --run
<hidden tests>` with the probe" in Step 2).** After lint and typecheck, the
container runs the hidden tests twice: pass 1 clean (`aa.checker.vitest_clean_cmd`,
no probe, default timeouts → `report.json`, then `clean_done`) decides
`correct`; pass 2 copies the probe + wrapper config and reruns them with
`--testTimeout=50000 --hookTimeout=100000` (`aa.checker.vitest_probe_cmd`
→ `probe.jsonl`, `probe_report.json`, `vitest_probe_rc`) only to collect
violations. `result.json` gains `probe_incomplete`: true when pass 2 did not
finish, was killed by `timeout`, wrote no report, or failed a test that passed
clean; its violations are kept either way. A container that dies (or a host
timeout) after `clean_done` is not an `eval_error`. The task sanity check
(Task 6) reads `report.json`, i.e. the clean pass.

**fast-check seed (decision 2026-10-06, spec §6).** Before pass 1 (after lint
and typecheck) the container copies `seed.setup.ts` → `src/mocks/aa-seed.setup.ts`
and `vitest.aa-seed.config.ts`; pass 1 runs with `--config vitest.aa-seed.config.ts`
(`aa.checker.vitest_clean_cmd`), pass 2 with `vitest.aa.config.ts`, which extends
it. A failed copy → `eval_error="seed_install"`. Host runs (`aa.suite.run_suite`,
`aa.checker.run_with_probe`) install the same files for the run only and keep the
report + stdout/stderr under `work/logs/` on any failure.
Freeze-gate rerun with the seed (2026-10-06, twice): suite baselines A/AL 1227,
AP/APL 1231 passed, 0 failed; equivalence A-AP, A-AL, AP-APL = 0; checker
baseline probe-on vs off = 0 differences on all four; both runs' pass sets
identical (`aa checker baseline` now also writes `work/probe-baseline-<cond>.json`).

**Hidden-test rewrite on AP/APL (decision 2026-10-05, spec §6).** The hidden
test files used on AP and APL are the base versions plus the same mechanical
rewrite `aplus.patch` applied to Actual's own tests, and nothing else:
imports of moved write functions → `#server/db/write`; a `vi.mock` of
`#server/db` that targets moved functions → also mock `#server/db/write`;
`vi.hoisted(() => vi.resetModules())` when the test mocks writes reached via
the domain. No assertion changes. The rewritten files are what the evaluator
restores from the image (Step 2), so A/AL get the base version and AP/APL the
rewritten one. Control (checked in Task 6 Step 4): the original commit's
non-test changes must pass the rewritten hidden tests in all four conditions,
otherwise the task is dropped for **all** conditions (`reference_fails:<cond>`
drops the task, not the condition).

- [ ] **Step 3: Run tests → PASS. Commit.**

---

### Task 10: Visibility — run viewer and live status page

**Files:**
- Create: `src/aa/viewer.py`, `src/aa/status.py`, `src/aa/templates/{run.html,status.html}`, `tests/test_viewer.py`

**Interfaces:**
- Consumes: run dirs + `result.json` (Tasks 8–9), reference diff per task (`git show <sha>` non-test files, stored by Task 6 as `tasks/<id>/reference.patch`).
- Produces: `runs/.../view.html` per run; `runs/status.html`; `aa view <run_dir>`, `aa status [--watch]`.

- [ ] **Step 1: Test** — given fixture transcripts (the recorded ones from Task 8), `render_run()` returns HTML containing each tool call command, the diff, and a `<mark class="violation">` on the violating line number; `render_status()` over 3 fixture results shows counts per agent×cond and a Wilson interval string. Run → FAIL.

- [ ] **Step 2: Implement** — plain Python string templates (no JS framework), self-contained HTML, CSS tokens with light/dark. Run view: left column conversation (assistant text, collapsed thinking, tool calls with input/output truncated to 2 kB with expand), right column agent diff vs reference diff, violations list linking to lines; header with status, correct, tokens, turns, wall time. Status page: table agent × cond with `done/total`, `correct %`, `bad decision %` (Wilson CI), median tokens, `infra` retries; list of latest 20 non-ok or bad-decision runs linking to their `view.html`. `aa status --watch` regenerates after every new `result.json` (poll 30 s). Run → PASS. Commit.

---

### Task 11: Statistics and tables

**Files:**
- Create: `src/aa/stats.py` (copy `~/Documents/repos/agent-code-practices/src/acp/stats.py` verbatim, keep attribution comment), `src/aa/tables.py`, `tests/test_tables.py`

**Interfaces:**
- Produces: `aa tables` → `out/tables.md` and `out/summary.json` with, per agent: rates (correct, bad decision, any violation) per condition with Wilson CIs; Fisher p for contrasts A vs AP, A vs AL, AP vs APL, AL vs APL; interaction via mixed-effects logistic regression (`statsmodels` `BinomialBayesMixedGLM` with task random effect — add `statsmodels` to dependencies); tokens: median and IQR on correct runs, Mann-Whitney A vs AP; detectable difference at the achieved n (`detectable_difference`).
  - *Amendment 2026-10-06 (spec §6 item 6, §8):* the mixed-effects logistic and the log-linear token model add task `source` as a fixed covariate (task random effect kept); every table is emitted pooled, per source (`mined` / `issue`), and for mined tasks per `ai_label`; a condition × source interaction is fitted and labelled exploratory. Test fixture extended with `source`/`ai_label` so the per-stratum cells are checked by hand.

- [ ] **Step 1: Test** — fixture of 16 synthetic `result.json` files with known counts → table cells match hand-computed values (e.g. 3/4 → `75% [30–95]` using `wilson`). Run → FAIL; implement; PASS. Commit.

---

### Task 12: Pilot, task selection, estimate (gate) and full run

**Files:**
- Modify: `tasks/_ledger.json` (selection), `docs/specs/...` only if Javier changes something.
- Create: `docs/pilot-report.md`

- [ ] **Step 1: Pilot estimate** — tasks surviving Tasks 6, 6b and 7 (N, reported per source and per `ai_label`), 3 runs per agent on condition A only: `N × 3 × 2` runs. Print wall-time estimate (median observed from Task 8 smoke runs × count / concurrency) and quota note; **wait for Javier's go**.

- [ ] **Step 2: Run pilot** — `aa run --agent claude --conds A --passes 3` and same for codex, `aa status --watch` open.

- [ ] **Step 3: Select** — keep tasks where, for **both** agents: ≥2/3 correct, median wall ≤ 12.5 min, no run at a cap (25 min wall, 60 turns). *(Amendment 2026-10-06 14:10, spec §4.3: the "median turns ≤ 30" clause is dropped — turns are not comparable across agents; decided after the Codex pilot, before the Claude pilot.)* Same rule for both sources (amendment 2026-10-06), no per-source quota. If >15 survive, apply the tie-break (decision 2026-10-06, recorded here and in spec §4.3 before any pilot run): among tasks passing the rule for **both** agents, order by (a) alternating sources mined / issue, starting with the source that has fewer survivors (equal counts: mined first; when one source runs out, continue with the other), (b) most recent date first within each source (mined: commit date; issue: issue creation date; ties: task id ascending); take the first 15; if <15, **stop and report to Javier** with the ledger (options: relax to ≥1/3 correct, mine since 2024-01, or add hand-resolved reverts for `revert_conflict` tasks — each option changes validity and is his call). Write `docs/pilot-report.md` (counts, drop reasons, per-task pilot stats).

- [ ] **Step 4: Full-run estimate (gate)** — 15 × 4 × 4 × 2 = 480 runs; wall time from pilot medians at concurrency 3 per agent; quota consumption; API-equivalent cost from pilot token totals (Sonnet 5.5 list price; gpt-6-luna list price). **Wait for Javier's go.**

- [ ] **Step 5: Full run** — both agents in parallel (`aa run --agent claude …` and `aa run --agent codex …` as background processes), `aa status --watch`; monitor: if any condition's correct rate on ≥10 runs is 0 % or `infra` retries exceed 20 % of attempts, **pause and read traces before any explanation**.

- [ ] **Step 6: Tables** — `aa tables`; commit `out/` and a short `docs/results-phase1.md` with the pre-registered hypotheses H1–H3 and the rival read against the numbers (no prose beyond what the tables support).

---

## Self-review notes (resolved inline)

- Spec §3 "lint run as a team would": every condition now has a `lint` script (typecheck in A/AP, typecheck + ESLint in AL/APL) so the prompt is identical — Task 4 Step 3.
- Spec §3.1 integrity: `aplus-frozen` tag asserted by `mine` — Task 6 Interfaces.
- Spec §4 filter order (amended 2026-10-06: the AI label is an attribute, not a filter; issue tasks follow Task 6b): AI label → date preference (sort) → memorisation (Task 7) → clean revert (Task 6 Step 3) → solvable with margin (Task 12) — all present.
- Spec §9 "only affected test files run during evaluation": Task 9 runs hidden tests only.
- Line-shift false positives in the probe baseline: matched by file + SQL prefix — Task 5 Step 3.
