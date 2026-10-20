# Study 3 (the agent as abstraction designer) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run R, RG (written norm), RL (duplication ratchet) and RC (directed refactor T0)
over the study-2 chains with three agents and measure whether agents design and reuse
abstractions, and whether that pays off downstream.

**Architecture:** Reuse the study-2 harness (`aa chain …`): chains, hidden tests,
evaluator, packets, tables. New: arm images (RG, RL, RC = R + per-arm patch), a T0 step
for RC with its own evaluation (probe + inconsistency tests + completeness packet), the
ratchet script and its calibration on study-2 data, interleaved scheduling, study-3 tables
and a mixed-batch design review.

**Tech Stack:** as study 2 (Python 3.12/uv/pytest; TS/vitest; Docker; Node 24.18.1; jscpd
5.4.0 pinned).

**Spec:** `docs/specs/2026-10-10-agent-as-designer-design.md` (v2, `0051a5e`).

## Global Constraints

- Base: frozen R (tag `rf-frozen`); study-2 chains, statements, hidden tests and evaluator
  semantics unchanged; study-1/2 runs untouched.
- Arms exactly `R`, `RG`, `RL`, `RC`; F only from study-2 runs (design review re-judging).
- Agents `claude-sonnet-5-5`, `gpt-6-luna`, `claude-haiku-5-5`; effort medium; no web,
  blocked hosts, isolated config, same prompt template; T1–T4 25 min / 60 turns; T0 40 min /
  90 turns. Model ids and CLI versions recorded per run.
- Ratchet detector chosen by the registered calibration rule (spec §5) and recorded as a
  dated spec amendment **before any study-3 agent run**.
- T0 statements: behaviour only, leak check (no paths, function names, copy counts or
  locations); author ≠ implementer; inconsistency tests pass on untouched R and F.
- Intention-to-treat for RC: T1 always starts from the agent's T0 tree.
- Runs in `runs3/` (pilot `runs3-pilot/`), never mixed with `runs2/`.
- Size: 4 zones × 8 chains per arm per agent; 1,632 steps. Estimate before pilot and full run.
- Tables by script only; kappa before any comparison; anomalies read in traces first.

## Review Focus

1. **Ratchet blind to the change** (clone side outside the agent's lines, or detector
   threshold missing the zone's copy) → calibration replays real study-2 diffs; unit tests
   with a copy-based and a helper-based diff per zone. Task 1.
2. **Ratchet gamed** (ignore markers, `.jscpd*`, edited script/baseline/lint script, file
   moved out of scanned paths) → automatic flags, each with a unit test. Task 3.
3. **RC T1 not starting from the T0 tree** (or T0 counted as a chain step in T1–T4
   metrics) → runner test: T1 pre-image = T0 diff; tables test: T1–T4 metrics exclude T0,
   totals include it. Tasks 4, 6.
4. **Probe exclusions drifting** (excluded cases re-entering the T0 check, or a real
   behaviour change hidden by an exclusion) → exclusions listed by case id, test that the
   probe flags a seeded unified consolidation. Task 2.
5. **Design-review batches mixing sessions** (F packets judged apart from the study-3
   arms) → one batch file over all arms + F, seeded shuffle, test that every batch draws
   from the shuffled pool. Task 7.

---

### Task 1: Ratchet calibration on study-2 data (no agent runs)

**Files:** `src/aa/ratchet.py` (detector: jscpd over loot-core non-test sources at a given
min-tokens, clones touching added/modified lines vs a start tree), `scripts/study3_calibrate_ratchet.py`,
`out/study3/ratchet-calibration.md`, tests `tests/test_ratchet.py`.

- [ ] `new_clones(tree, start_commit, min_tokens) -> list[Clone]`: run jscpd on the tree's
  loot-core sources (`is_source_file`), resolve basenames as in `parse_jscpd`, keep clones
  with a side overlapping lines added/modified vs `start_commit` (`git diff -U0`).
- [ ] Unit tests: a diff that pastes a 15-line block next to its original → 1 clone; the
  same diff calling an extracted function → 0; an unrelated pre-existing clone → 0.
- [ ] Replay on study-2: for each `runs2/*/{R,F}/*/*/T2` step, rebuild start tree (variant +
  `eval/pre_image.patch`) and post tree (+ `diff.patch`) in a temp worktree; run the detector
  at 50, 35, 25. Sensitivity on R `copy` steps, FPR on F `helper` steps, per zone and agent.
- [ ] Apply the spec rule (highest threshold with FPR ≤ 10 %, else lowest with sensitivity
  ≥ 50 %); per-zone "lint blind" when sensitivity < 50 %. Write the report; add a dated
  amendment to the spec with the chosen threshold and blind zones; commit.

### Task 2: T0 statements, inconsistency tests, probe exclusions, RG wording

**Files:** `tasks3/Z<k>/T0/statement.md`, `tasks3/Z<k>/T0/hidden/<zone>-inconsistencies.test.ts`,
`tasks3/Z<k>/T0/consumers.json`, `tasks3/probe-exclusions.json`, `tasks3/rg-rule.md`,
`tasks3/Z<k>/T0/sites.json` (copy sites for the completeness judge, from
`docs/study2-variants.md`), `tasks3/provenance.json`; `src/aa/chains.py` (T0 support).

- [ ] Author agent per zone (not the implementer, no access to runs2/): T0 statement from
  the zone's `logic` field, behaviour only; leak check extended to T0 (no paths, function
  names, counts, locations).
- [ ] Inconsistency tests (spec §3 list only), driven through handlers; sanity: pass on
  untouched R and F; fail on a seeded "unified" consolidation patch per test.
- [ ] `probe-exclusions.json`: probe case ids for the excluded cases (un-awaited
  6/12-month, missing-group NULL, insert key set), each with the reason; test that the
  remaining probe still flags the seeded unified patches.
- [ ] Implementer agent per zone does T0 on R from the statement only (hidden tests not
  mounted; transcript audited): its tree passes the probe (minus exclusions) and the
  inconsistency tests — proves T0 is solvable.
- [ ] RG rule text frozen (spec §4 wording) in `tasks3/rg-rule.md`. Commit; `git tag study3-tasks`.

### Task 3: Arm images (RG, RL, RC) and the ratchet in lint

**Files:** `substrate/patches/study3/rg.patch` (AGENTS.md rule), `substrate/patches/study3/rl.patch`
(`packages/loot-core/bin/dup-check.mjs`, its config pinned to the calibrated threshold, wired
into root `lint` and `lint:fix`), `src/aa/config.py` (`CONDITIONS3 = ("R","RG","RL","RC")`,
patches: RG = R + rg, RL = R + rl, RC = R), CLI choices; `src/aa/static3.py` (gaming flags);
tests `tests/test_static3.py`, `tests/test_dupcheck.py` (runs the .mjs on fixtures).

- [ ] `dup-check.mjs`: start commit = the run's start commit (`git rev-parse` of the
  harness's `start` commit, available in every run); jscpd at the calibrated threshold;
  fail with each offending clone (file:lines both sides) if any clone touches lines changed
  since start. Fixture tests: copy → fails and lists the clone; helper → passes; unrelated
  clone → passes.
- [ ] Gaming flags from the step diff: touched `dup-check.mjs`, its config, root
  `package.json` lint scripts, `.jscpd*`, `jscpd:ignore` markers added, source file moved
  outside scanned paths. One unit test per flag.
- [ ] Build images `aa-actual:RG`, `aa-actual:RL`, `aa-actual:RC` (= R); smoke: in RL a
  pasted copy makes `yarn lint` fail with the clone listed, and `yarn lint:fix` too.

### Task 4: Runner — arms, T0, interleaving

**Files:** `src/aa/chain_runner.py`, `src/aa/chains.py`, tests `tests/test_chain_runner.py`.

- [ ] RC chains: steps T0–T4; T0 uses `tasks3/Z<k>/T0/statement.md` and the T0 limits;
  T1–T4 carry from T0 exactly as study 2 carries between steps. RG/RL/R: T1–T4 on their image.
- [ ] Record per run: model id, CLI version (`claude --version`, `codex --version`).
- [ ] Scheduler: per agent, jobs ordered by chain index with arm order rotated
  (`ARMS[(i + k) % 4]`); chains in parallel, steps in series; `--runs` absolute.
- [ ] Tests: T1 pre-image of an RC chain = T0 diff (Review Focus 3); arm order rotates;
  chains isolated per (agent, arm, zone, chain).

### Task 5: Evaluator — T0 and new measures

**Files:** `src/aa/chain_eval.py`, `src/aa/probe2.py` (callable with exclusions on any
tree), tests `tests/test_chain_eval.py`.

- [ ] T0 evaluation: probe on the agent's tree vs untouched R (minus exclusions) →
  `probe_changed_cases`; inconsistency tests → `inconsistencies_unified`; `correct` =
  both clean; jscpd zone files before/after; T0 packet for completeness + interface judging.
- [ ] RL fields per step: `lint_runs` (count of lint invocations in the transcript),
  `ratchet_final` (dup-check on the post tree), `gaming_flags`.
- [ ] `t2_reuses_logic` for study 3: `helper` if the new consumer calls a function also
  called by a pre-existing consumer in the post tree (static, via grep of call sites), `copy`
  on zone markers, else None → left to the judge; judge label is the primary T2 reuse
  measure, static label secondary (agreement reported).
- [ ] Rule steps (T1/T3): `rule_sites_touched` = number of distinct functions whose body the
  diff changes among the zone's copy sites and any helper they call (static); judge question
  "does the rule change land in one shared definition?" on T1/T3 packets (primary label).
- [ ] RG field: `rule_cited` (transcript mentions the AGENTS.md rule or extracting/reusing).
- [ ] Tests: T0 with a seeded unified patch → `inconsistencies_unified` non-empty; probe
  exclusions respected (Review Focus 4); RL flags propagated.

### Task 6: Tables

**Files:** `src/aa/tables3.py`, `aa tables3`, tests `tests/test_tables3.py`.

- [ ] Per agent, each lever arm vs R: T2 reuse (Wilson, mixed logistic), registered missed
  copy, correct, carried (never-passed vs regressions), efficiency per step, chain totals
  (RC with T0), jscpd zone files; with and without Z4; RL confirmatory over non-blind zones.
- [ ] T0 table (RC): completeness, probe unchanged, inconsistencies unified, interface.
- [ ] RL table: lint runs, ratchet fired / passed at end, gaming. RG: rule cited.
- [ ] F descriptive column from study-2 results.
- [ ] Test: T1–T4 metrics exclude T0; totals include it (Review Focus 3).

### Task 7: Design review (mixed batches)

**Files:** `src/aa/chain_eval.py` (`export_review_packets` for runs3: T1–T4 chain diffs, RC
from its T0 tree; T0..T4 secondary; T0 packets with `sites.json`), `work/review3/`,
`docs/design-review-rubric.md` (study-3 addendum, committed before scoring),
`scripts/study3_design_review.py`.

- [ ] Packets for runs3 + the study-2 F chain packets re-exported with the same salt
  scheme; one seeded shuffled batch file across all (Review Focus 5); 25 % second judge on T0
  packets, 15 % on the rest.
- [ ] Rubric addendum: T2-reuse label, abstraction-drift question (chain packets),
  disguised-duplication question (RL packets), completeness + interface (T0 packets).
- [ ] Judge workflow (Opus 5.5, as study 2); kappa; then H1 comparisons.

### Task 8: Pilot, estimate, full run, analysis

- [ ] Pilot: 1 chain per zone × arm × agent → `runs3-pilot/` (≈204 steps). Checks per spec
  §9; read traces of every 0 %/100 % cell; `docs/study3-pilot-report.md`.
- [ ] Estimate (time + quota) → Javier's go.
- [ ] Full run (agents sequential, interleaved arms, `--workers 2`), evaluate, `aa tables3`,
  design review, `docs/results-study3.md`.

> **Note 2026-10-11 (pre-pilot review):** the full run uses `--workers 2` (was
> `--workers 3`), now the study-3 default of `aa chain run`: the 6 GB Docker VM holds two
> loot-core containers at most. `aa chain evaluate --study 3` (or `--pilot`) reads
> runs3/ (runs3-pilot/) and runs each RC T0 evaluation alone. Arm order is
> `ARMS[(i + k + z) % 4]` (spec amendment 2026-10-11e).

> **Note 2026-10-11 (review of the pre-pilot fixes and Task 7):** design-review packets
> carry no pre-image (one neutral repository, one commit per packet, named in
> `tree.txt`); a batch holds at most one packet per chain; `aa chain packets --study 3`
> runs the study-3 exporter; T0 related tests retry failing files once (spec amendment
> 2026-10-11f).

- Note (2026-10-12, pilot): 7 Codex pilot chains ended `infra_exhausted` overnight. The
  host `~/.codex/auth.json` (logged in 2026-10-01) is copied into each container and
  container-side refreshes are never written back; when the 10-day access token expired,
  parallel containers raced on the single-use refresh token and every later step got 401.
  Not an agent failure (classified infra; the chains resume from the failed step after a
  re-login). Guard added: `aa chain run --agent codex` refuses to start with < 24 h of
  login left (`--min-codex-auth-hours`), and the scheduler stops dispatching (status
  `auth_expired`, no infra attempts spent) when < 2 h remain. Re-login before the full run
  if it could end within 24 h of expiry.

- Note (2026-10-12, pilot blocking items 1-4 and 9; spec amendment 2026-10-12): network
  stalls are `infra` (`aa chain reclassify`, `aa chain run --dry-run`), Claude usage is
  summed over every `result` and Codex usage is missing without `turn.completed`
  (`aa chain reparse`), RL trips are classified against the start tree as at the trip
  (`aa chain rederive-trips`), and the in-scope T0 inconsistency tests run on every T1-T4
  post tree (`tasks3/inconsistency-scope.json`, `aa chain scope-sanity`, `aa chain
  behaviour-check`). Before the full run, re-run the two reclassified pilot Codex chains
  (`aa chain run --agent codex --study 3 --pilot --chains 1` resumes `R/Z3/0` at T1 and
  `RC/Z3/0` at T2, discarding their later steps) only if the pilot tables are to be
  completed; the full run uses the fixed runner and evaluator directly.

- Note (2026-10-12, pilot items 5-8; spec amendment 2026-10-12b, rubric "T0 completeness
  levels"): RL firing is benchmarked against calibration only at RL T1 and on the R/RG/RC
  counterfactual fields (RL T2-T4 firing is a treatment outcome); H4's fired steps are
  decomposed (a) consolidation / (ab) mixed / (b) edit moved outside the clone / (u)
  unreadable / (g) gaming / (c) seen not fixed / (d0, d1) never seen; (a)/(b)/(ab)/(u)
  need the derived `ratchet_trip_clones` field (follow-up in `chain_eval3` / `tables3`,
  required before `docs/results-study3.md`); RG compliance is behaviour only
  (`aa.rg_check`, `agents_md_read` → `agents_md_explicit_read`, `rule_cited` descriptive);
  T0 completeness scores sites full / partial (0.5) / none. Run protocol: Codex block
  first (token expires 2026-10-22 06:57 UTC), host on AC under `caffeinate -dims`,
  `aa chain run --dry-run` after each block.

- Note (2026-10-12, spec amendment 2026-10-12c): the 2026-10-12b follow-ups are built:
  `agents_md_explicit_read` written by the evaluator and reported (descriptive) by
  `aa tables3`; the calibration benchmark of ratchet firing (`aa tables3 --calibration`,
  "off" cells); `ratchet_trip_clones` (evaluator, `aa chain rederive-trips`) and the H4
  decomposition table. Re-derivations now log chain.json status changes and every
  rewritten chain summary; `aa chain record-summaries` added retrospective records for
  the 2026-10-12 rewrites (runs2 192 chains, pilot 48). Pilot and study-2 reports
  annotated with the re-derived values.
