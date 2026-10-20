# The agent as abstraction designer — design spec (study 3)

Date: 2026-10-10 (v2, after self-review and an independent methodological review; v1 is
in git history, `03d2bc5`). Builds on study 2
(`docs/specs/2026-10-08-repetition-vs-abstraction-design.md`, `docs/results-study2.md`).

## 1. Objective

Study 2: starting from repeated code (R), agents *extend* the repeated pattern (T2 new
consumer: a copy in 32/32 Sonnet chains, 30/32 Codex, 31/32 Haiku) and blind judges score
their design lower than in human-factored code (F). Study 3 asks whether the agent can be
the designer, under three levers that differ in how much they tell it:

1. **Unprompted design under a norm** — a written design rule in the repo's agent
   instructions (the usual CLAUDE.md/AGENTS.md practice). Does the agent, at the moment a
   task invites a copy, choose to extract and reuse?
2. **Unprompted design under a hard constraint** — Pocock's "harsh lint": a duplication
   lint that fails the agent's checks when it adds a clone.
3. **Directed design** — an explicit refactor step before the work. Can the agent
   design the abstraction (find the copies, choose the interface, keep behaviour) when
   asked, and does an agent-made abstraction pay off like the human one?

Payoff is judged on the work that follows, with fresh agent context at every step: any
benefit can reach later steps only through the code.

## 2. Arms

All arms start from the frozen R variant (tag `rf-frozen`) and run the study-2 chains
(statements, hidden tests, consumers, evaluator unchanged).

| Arm | Lever | Steps |
|---|---|---|
| **R** | none: fresh concurrent control, full n | T1–T4 |
| **RG** (guidance) | AGENTS.md gains one rule (§4) | T1–T4 |
| **RL** (lint) | `yarn lint` and `yarn lint:fix` run a duplication ratchet (§5) | T1–T4 |
| **RC** (directed refactor) | step T0 before the chain (§3) | T0, T1–T4 |
| F | study-2 F runs: ceiling, descriptive only; its chain packets re-judged with this study's (§7) | — |

A fresh R replaces the reuse of study-2 R: the comparison must not mix the treatment with
model or service drift. Exact model ids and CLI versions are recorded per run. Run order is
interleaved within each agent (arm order rotated by chain index) so time trends hit all
arms alike.

## 3. RC: the T0 step

- **Statement** per zone, behaviour only, by an author agent with the leak check (no files,
  functions, copy counts or locations): it names the behaviour area (the zone's `logic`
  field) and asks that this logic live in one place, behaviour unchanged. This is a
  *directed* refactor: the experimenter chooses what and when; reported as such.
- **Limits:** T0 gets 40 min / 90 turns (a full consolidation is larger than a chain step:
  F's Z3 refactor was +241/−303). T1–T4 keep 25 min / 60 turns. T0 time and tokens count
  in RC's chain totals.
- **Hidden behaviour check (T0):** `aa probe2` (the study-2 behavioural probe, 553 cases
  driving every copy site through its handler) must give the same outputs as untouched R;
  plus a per-zone file of *observable, defensible* inconsistencies: Z1 `setZero` writes
  hidden categories; Z2 template rounding (`halfOfRoundedSum`); Z3 only PluggyAI sends the
  file id, GoCardless stores `mask`/official name, Akahu reports only `transactions`.
  Excluded as unfair or unobservable: un-awaited 6/12-month calls, the missing-group NULL
  case, the insert key set; the probe comparison drops the same cases (listed in the plan
  by probe case id before any T0 run). Each test must pass on untouched R and F and fail on a seeded
  "unified" consolidation (sanity).
- **Downstream rule, decided now:** T1 starts from the agent's T0 tree whatever T0's
  outcome. **Primary analyses are intention-to-treat** (every RC chain). Analyses
  conditioned on T0 completeness or correctness are exploratory (both happen after
  treatment).
- **Completeness** (judged blind, second judge on 25 %, kappa reported): share of the
  zone's copy sites whose *decision* now goes through one shared definition. Z4 is scored
  on the shared decision (whether/how to adjust), not the date arithmetic base already
  shares. Z2: re-using the existing exported helper counts (finding and reusing it is the
  design act).
- **Interface quality** (T0 packets only, 1–5): parameters for the real variation, no
  speculative options, inconsistencies made explicit.

## 4. RG: the written norm

One line added to the root AGENTS.md (which every arm already has), in its conventions
section, worded as a team rule and not as a hint about this code: "Do not copy logic: when
new code needs behaviour that already exists, extract it into a shared function and reuse
it; when a rule changes, change it in one place." Nothing else differs from R.

## 5. RL: the duplication ratchet

- **Detector calibrated before anything is built, on study-2 data only** (no study-3
  outcome is seen): replay candidate detectors on the 384 study-2 R step trees (each step's
  start tree and the agent's diff). Candidates: jscpd over loot-core non-test sources at
  min-tokens 50, 35, 25. *Sensitivity* = share of T2 steps classified `copy` where the
  detector reports a new clone touching the agent's added lines; *false-positive rate* =
  share of study-2 F T2 steps classified `helper` where it fires. Rule (fixed now): the
  highest threshold with FPR ≤ 10 %, then the lowest threshold whose sensitivity ≥ 50 % if
  the first fails it. Zones where the chosen detector's sensitivity is < 50 % are reported
  as "lint blind" and excluded from RL's confirmatory analyses (kept descriptively).
- **Ratchet per change, not per total:** the check fails if any clone has a side
  overlapping lines added or modified relative to the step's start commit (generic: no
  zone list). Removing unrelated duplication elsewhere earns no slack.
- **Gaming, flagged automatically** (plus trace reading): changes to the check script, its
  config, the lint scripts, `.jscpd*` files, `jscpd:ignore` markers, files moved outside
  the scanned paths; and a judge question on RL packets: "was duplicated logic disguised
  (renamed/reordered) rather than removed?".
- **Correctness is unchanged** (hidden tests only); a failing final ratchet is reported
  separately, not folded into `correct`.

## 6. Measures

Per step and chain as study 2 (registered missed copy, correct, carried defects split into
never-passed vs regressions, efficiency, jscpd on zone files). Added:

- **T2 reuse (primary payoff measure):** the new consumer calls a shared function that
  also serves the pre-existing consumers (`t2_reuses_logic = helper`, extended to
  agent-made helpers), vs copies or reimplements.
- **Rule steps through one place:** at T1/T3, whether the change lands in one shared
  definition used by all consumers (static check of the diff + judge).
- **Abstraction drift** (chain packets): flags/parameters added to a helper per step,
  special-case branches, call sites bypassing it (judge question).
- **Cost:** total chain tokens and wall time (RC including T0).
- RL: lint runs per step, final ratchet status, gaming flags. RG: whether the agent
  quotes or follows the rule (trace).

## 7. Hypotheses (per agent; all directional vs R)

- **H1 (primary, design):** maintainability of the chain's T1–T4 diff is higher in RG, RL
  and RC than in R. For RC the diff starts from the agent's T0 tree (the analogue of F's
  diff from F); the T0..T4 diff is secondary. R, RG, RL, RC and the study-2 F chain packets
  are judged together in the same blinded, shuffled batches (scores from different
  sessions are not compared).
- **H2 (payoff):** T2 reuse is higher in each lever arm than in R (R base ~0–6 %, so there
  is room).
- **H3 (directed designer):** at T0, median completeness ≥ 0.75 with the probe unchanged in
  ≥ 75 % of RC chains.
- **H4 (lint):** in non-blind zones, ≥ 90 % of RL steps that trip the ratchet end with it
  passing and no gaming flag (counted only over steps where it fired).
- **H5 (cost):** RC's total chain tokens vs R's (does T0 pay for itself?), descriptive with
  intervals; also RG/RL vs R.
- **Secondary:** registered missed copy (floor: Sonnet/Haiku 5–6 % in R; only Codex has
  room; reported, not confirmatory), correct, closeness to F (descriptive).
- **Rival:** levers change the surface (a token helper, lint dodged) but not downstream
  reuse or judged design.

## 8. Size, power, analysis

- R, RG, RL: 3 agents × 4 zones × 8 chains × 4 steps = 384 each; RC: × 5 = 480.
  **1,632 steps.** Same agents/effort/isolation as study 2 (Sonnet 5.5, gpt-6-luna,
  Haiku 5.5; medium).
- Power: study 2 found R vs F chain maintainability 2.94 vs 3.56 at n = 32 (p < 0.001), so
  H1 is detectable at that size; H2 from a ~0 % base is detectable from ~25 points.
- Z4 is pre-declared weak (study 2: base already shares the date arithmetic; T1's "drop"
  cannot be expressed by a date-returning helper): confirmatory analyses with and without
  Z4.
- Analysis as study 2: Wilson CIs, mixed-effects logistic / ordinal (zone, chain random
  effects), Mann-Whitney + per-zone sign tests, kappa before any comparison, nothing near
  p = 0.05 read as an effect on its own. Tables by script only; anomalies read in traces
  before interpretation.

## 9. Pilot

1 chain per zone × arm × agent = 48 chains (≈ 204 steps). Checks: T0 sanity (probe and
inconsistency tests pass on R and F, fail on seeded breakages), the ratchet fires in the
pilot where calibration says it should, T0 fits its limits (Z3 especially), chains end to
end, traces of any 0 % / 100 % cell read. Estimate repeated before the full run.

## 10. Build order

1. Ratchet calibration on study-2 data (§5) → registered in this spec as an amendment
   before any study-3 run.
2. T0 statements and inconsistency tests (author agent, leak check, sanity); RG wording
   frozen; tag `study3-tasks`.
3. RL image (ratchet script, lint wiring, unit tests); RG and RC images.
4. Harness: arms, T0 step and its evaluation, new measures, interleaved scheduling.
5. Pilot → report → full run → evaluate → tables → design review (all arms + F, mixed) →
   `docs/results-study3.md`.

## 11. Out of scope

Unwinding a bad abstraction (a misparameterised helper), for later.

## Amendment 2026-10-10: ratchet calibration (§5), registered before any study-3 run

**Superseded by amendment 2026-10-11** (threshold 35, not 25). Kept as registered;
its replay data and per-zone table at 25 still stand.

Calibration replayed on study-2 data only (`scripts/study3_calibrate_ratchet.py`,
report `out/study3/ratchet-calibration.md`, per-step data
`out/study3/ratchet-calibration.json`). Detector: `aa.ratchet` (jscpd 5.4.0 pinned in
`aa-actual:R`, over the non-test sources under `packages/loot-core/src`; a step fires
when a clone has a side on a line added or modified since the step's start tree). Replay
set: the 192 study-2 T2 steps (the plan's reading of §5's "R step trees": T2 is the
step with a copy/helper label); sensitivity over R steps labelled `copy` (n = 93), FPR
over F steps labelled `helper` (n = 91); the 8 other-labelled steps are left out.

| min-tokens | sensitivity | FPR |
|---|---|---|
| 50 | 28/93 = 30 % [22–40] | 20/91 = 22 % [15–32] |
| 35 | 47/93 = 51 % [41–60] | 29/91 = 32 % [23–42] |
| 25 | 56/93 = 60 % [50–70] | 50/91 = 55 % [45–65] |

**Chosen threshold: min-tokens 25.** The §5 rule, applied as written: no threshold has
FPR ≤ 10 %, so the second clause applies: the lowest threshold with sensitivity ≥ 50 % is
25. (Read literally, "lowest" picks the most sensitive and noisiest detector. Had it meant
the highest such threshold, the result would be 35. That reading was not applied.)

Per zone at min-tokens 25 (pooled over agents):

| zone | sensitivity | FPR | status |
|---|---|---|---|
| Z1 | 24/24 = 100 % | 15/24 = 62 % | in |
| Z2 | 2/22 = 9 % | 0/20 = 0 % | **lint blind** |
| Z3 | 24/24 = 100 % | 24/24 = 100 % | in |
| Z4 | 6/23 = 26 % | 11/23 = 48 % | **lint blind** |

**Lint-blind zones: Z2, Z4.** Excluded from RL's confirmatory analyses (H4 and RL's arm
of H1/H2) and kept descriptively.

What the numbers mean for RL (read in the replayed clones, not a change to the rule):
- The FPR is real duplication, not a detector artefact. Z3's helper-style F steps still
  add a provider download function that repeats the shape of the existing ones (e.g.
  `sync.ts` 319–358 vs 296–319). Z1's F steps add short loops (26–33 tokens) parallel to
  their neighbours. The ratchet is generic, so it will also ask for that duplication to
  be removed. In Z3 it fires on every replayed step, helper or copy, so in Z3 it cannot
  tell the two designs apart.
- Z2's R copies are a one-line expression or call, below jscpd's reach at any threshold.
  Z4's copies are short date-adjust branches.
- Any interpretation of RL must keep in mind that, at this threshold, the lint also
  fires on changes judged good in study 2.

## Amendment 2026-10-11: ratchet threshold 35 (a disclosed deviation), RL wiring, rule scope (§5), before any study-3 run

Supersedes the threshold choice of amendment 2026-10-10 (its replay data are unchanged and
reused: `out/study3/ratchet-calibration.json`; no detector was re-run for the threshold).
Decided by the study lead before any study-3 agent run; no study-3 outcome was seen. A
first version of this amendment (same date, `6a8a05c`) justified the change as the "only
coherent reading" of the rule; that justification was wrong and is replaced by this text
after an independent review of plan Tasks 1-3.

**Threshold: a deviation from the registered rule, not a reading of it.** §5's second
clause, "the lowest threshold whose sensitivity ≥ 50 %", is well defined: among the
thresholds that see at least half the copies, take the most sensitive one. It gives
**min-tokens 25** (pooled sensitivity 56/93 = 60 % [50–70], FPR 50/91 = 55 % [45–65]),
which amendment 2026-10-10 applied. It was replaced by "the *highest* threshold whose
sensitivity ≥ 50 %" **after** sensitivity and FPR at every threshold were known, because
at 25 the detector fires on 15/24 = 62 % of Z1's helper-reuse steps (0/24 at 35). The
first clause is unchanged (highest threshold with FPR ≤ 10 %; none qualifies). This is a
post-hoc, disclosed deviation, decided before any study-3 agent run; every RL result is
reported with it noted.

**Chosen threshold: min-tokens 35**, borderline: pooled sensitivity 47/93 = 51 % [41–60]
(the CI includes values below 50 %), FPR 29/91 = 32 % [23–42]. Pinned in
`substrate/patches/study3/rl.patch` (`dup-check.config.json`) and
`aa.config.RATCHET_MIN_TOKENS`; `aa-actual:RL` rebuilt with it. The calibration script
(`scripts/study3_calibrate_ratchet.py`) encodes the amended rule, with unit tests in
`tests/test_study3_calibration.py`; `out/study3/ratchet-calibration.md` and its summary
JSON were regenerated from the stored per-step data.

Per zone at min-tokens 35 (T2, pooled over agents):

| zone | sensitivity | FPR | status |
|---|---|---|---|
| Z1 | 19/24 = 79 % | 0/24 = 0 % | in |
| Z2 | 1/22 = 5 % | 0/20 = 0 % | **lint blind** |
| Z3 | 24/24 = 100 % | 24/24 = 100 % | in; non-discriminating (descriptive) |
| Z4 | 3/23 = 13 % | 5/23 = 22 % | **lint blind** |

**Lint-blind zones: Z2, Z4** (unchanged): excluded from RL's confirmatory analyses (H4
and RL's arm of H1/H2), kept descriptively. "Lint blind" keeps its registered meaning,
T2 copy sensitivity < 50 %; it does **not** mean that the lint never fires there (below).

**Z3 is non-discriminating.** Its copy steps are caught at every threshold (100 %), and
its helper steps fire too (100 % at 35 and 25, 79 % at 50): the replayed F steps add a
provider download function that repeats the shape of the existing ones, so in Z3 the lint
cannot tell the two designs apart at T2. Recorded descriptively; Z3 stays in RL's
confirmatory analyses as registered, since its sensitivity is ≥ 50 %.

**Rule scope and firing at every step type.** The registered per-change rule counts a
clone with a side on *any* added or modified line, including a line edited inside a clone
that existed at the step's start (as SonarQube's "duplication on new code"). It is kept.
So the ratchet also fires on rule steps that edit duplicated blocks, and can force a
consolidation there. Replay of all study-2 R and F steps at 35 (T1, T3, T4: 576 steps,
none failed; T2 from the calibration data, all labels; `out/study3/ratchet-firing-by-step.json`,
section "Firing by step type" of the report), fired / 24 steps per cell:

| zone | R T1 | R T2 | R T3 | R T4 | F T1 | F T2 | F T3 | F T4 |
|---|---|---|---|---|---|---|---|---|
| Z1 | 24 (100 %) | 19 (79 %) | 10 (42 %) | 24 (100 %) | 3 (12 %) | 0 | 0 | 24 (100 %) |
| Z2 | 2 (8 %) | 1 (4 %) | 1 (4 %) | 0 | 0 | 0 | 1 (4 %) | 0 |
| Z3 | 24 (100 %) | 24 (100 %) | 1 (4 %) | 24 (100 %) | 24 (100 %) | 24 (100 %) | 0 | 24 (100 %) |
| Z4 | 7 (29 %) | 3 (12 %) | 22 (92 %) | 2 (8 %) | 4 (17 %) | 5 (21 %) | 8 (33 %) | 2 (8 %) |

Read: on R the ratchet fires at the rule step T1 in Z1 and Z3 on every chain (the rule
edit touches the copied blocks) and at T3 in Z4 on 22/24 (lint blind at T2, not at T3).
It also fires on every T4 step in Z1 and Z3, in R *and* F, so at T4 it does not separate
the designs either. RL's effect on rule steps is therefore a direct lever, not only the
T2 one; the per-step firing above is the expected exposure, reported with RL's results.

**RL wiring (fixed with this amendment, before any run).** The prompt (identical in every
arm) names `yarn test` and `yarn lint` **in packages/loot-core**. In R that `lint` is
`tsgo -b` (`lint-script.patch`); the first RL patch wired dup-check only into the root
`lint`/`lint:fix`, which the agent is never told to run. Now loot-core's `lint` in RL is
`tsgo -b` then dup-check, and the root `lint` and `lint:fix` keep it. In all three,
dup-check runs even when the command before it fails, and the script fails if either
failed (yarn 4 shell: `…; a=$?; node …/dup-check.mjs; b=$?; [ $a -eq 0 ] && [ $b -eq 0 ]`),
so an agent fixing a type or format error still sees its clones. Smoke-tested in
`aa-actual:RL` (`tests/test_dupcheck.py`): untouched tree passes loot-core `yarn lint`; a
pasted copy of `set3MonthAvg` fails loot-core `yarn lint`, root `yarn lint` and root
`yarn lint:fix`, each listing the clone; with a formatting, oxlint or type error present
the clone list still appears.

**Evaluator `lint_ok` in RL.** The evaluator's `lint_ok` runs loot-core's `yarn lint`, the
command the prompt names. In RL it therefore now includes the ratchet: intended, so that
`lint_ok` means "the agent's stated checks pass" in every arm. Known defect, to be fixed
in plan Task 5 before any evaluation: in the evaluator's container the repository's
history is the image's (`base` → `variant` → `evalbase`), so dup-check takes `base` as
the start commit and fails even on the untouched RL tree (checked in `aa-actual:RL`: one
clone from the R variant's own Z2 inlining). Task 5 must give the evaluated tree a root
commit named `start` at the step's start tree (as the runner does) before `yarn lint`;
`ratchet_final` (Task 5) is computed separately.

**Message.** The RL failure message reports only the failing check, the clones and the
pass condition, as a lint does, without advice and without claiming the clone is new:
"dup-check: duplicated code on lines added or changed in this task:", one line per clone,
"The check passes when no duplicated block includes a line added or changed in this
task." (The first version said "introduced since the start of this task", which is false
when the agent edited a line inside an old clone.)

**Gaming flags added** (`aa.static3`): `lint_scripts` also covers loot-core's `lint`;
`added_code_outside_scope` (≥ 10 non-blank added lines of non-test code in paths
dup-check does not scan); `start_commit_rewritten`, from the chain runner, which records
the start commit before the agent and, after it, the root commit dup-check would use and
whether HEAD still descends from it (`git diff <start>` cannot show a rewritten start).

**T0 sanity (§3), same date.** Z4 has no inconsistency tests, so its sanity was vacuous.
Added a seeded behaviour-changing consolidation (`tasks3/Z4/T0/sanity/`: one shared
weekend-rule helper reading the parsed schedule's field names, which the budget template
calls with its date condition, whose mode field is named differently): the probe minus
exclusions flags it (46 template cases); `sanity.json` all ok. An inconsistency seed now
also requires the zone's other T0 tests to pass (all existing seeds did).

## Amendment 2026-10-11b: evaluator start commit, the ratchet-firing split, study-3 measures (§§3, 5, 6), before any pilot

Registered with plan Task 5 (the evaluator), before any study-3 agent run (no pilot, no
`runs3/`); no study-3 outcome was seen. Answers the re-review of plan Tasks 1-4
(MEDIUM: RL `lint_ok`; LOW-MEDIUM: split of RL firing).

**RL `lint_ok` (fixes the known defect of amendment 2026-10-11).** For every study-3
step (all arms, T0..T4) the evaluator gives the evaluated tree a root commit named
`start` at *that step's own* start tree, made as the chain runner makes it (fresh
repository, `git init -b main`, `git add -A`, one commit `start`), in a separate git dir
so the image repository the rest of the evaluation uses is untouched; loot-core's
`yarn lint` (and, at T0, the root `yarn lint`) run against it, so RL's dup-check diffs
against the step start. Its tree id is compared with the runner's recorded `start_tree`
(`tree_check.start_fresh`): equal on a real study-2 step in the image it ran on; a
rebuilt image shows as a mismatch. Guard tests in `aa-actual:RL`
(`tests/test_chain_eval3_docker.py`): the untouched step tree gives `lint_ok = true`
(before the fix: false, from the R variant's own Z2 inlining clone
`schedules/app.ts:591-601 ~ shared/schedules.ts:496-506`); a pasted copy of
`set3MonthAvg` gives `lint_ok = false`.

**Ratchet measures for every arm (counterfactual for R, RG, RC).** Computed by the
harness detector (`aa.ratchet`: jscpd at min-tokens 35 over loot-core's non-test sources,
the same clones as RL's dup-check, `tests/test_dupcheck.py`) on the step's start and post
trees, against the same `start` commit:
- `ratchet_final`: clones of the post tree with a side on a line added or modified since
  `start` (RL's rule, on the tree the agent left);
- `ratchet_start_fires`: the step modifies or deletes a line inside a clone the start
  tree already had;
- `ratchet_kind` (None when `ratchet_final` does not fire): `adds_new_clone_side` (a
  firing clone has a side on a line *added* by the step), `touches_preexisting_only`
  (firing clones touch only *modified* lines, and the step edits a pre-existing clone),
  and a residual `modified_into_clone` (only modified lines, no pre-existing clone
  touched: a clone made by editing lines). *Added vs modified*: within each change block
  of the diff, a new line is modified when its text is similar (difflib ratio ≥ 0.6) to
  a line the same block removed, else added; blocks that remove nothing are wholly added;
  untracked files are wholly added.
- RL only: the agent may see the ratchet fire and remove the clone, so the final tree
  no longer shows the firing. Each dup-check failure in the transcript is classified
  (`ratchet_trip_kinds`): `touches_preexisting_only` when every clone it lists matches a
  clone of the start tree (same two files, both sides' lines overlapping), else
  `adds_new_clone_side` (approximate: line numbers are those of the agent's tree at that
  moment). `ratchet_trips` counts those failures, `lint_runs` the lint invocations.

**Split of H-RL analyses (registered now).** Every RL analysis of lint runs, efficiency
(tokens, turns, wall time) and design score is also reported split by the step's
`ratchet_split`: the first readable trip's kind when the agent saw the ratchet fire,
else `ratchet_kind` (what the ratchet says on the final tree), else `no_fire`. The same
variable is computed on R, RG and RC (where it is `ratchet_kind` or `no_fire`), so each
RL class has its counterfactual R class. **The primary RL comparison (H1/H2/H4 as
registered) is unchanged**; the split is reported beside it, descriptively, and
`modified_into_clone` is reported as its own (expected rare) row.

**Other study-3 measures, as implemented (plan Task 5).**
- T0: the probe on the agent's tree vs untouched R minus `tasks3/probe-exclusions.json`
  → `probe_changed_cases` (raw differences kept as `probe_changed_raw`); inconsistency
  tests → `inconsistencies_unified` (ids whose test did not pass; Z4 has none);
  `correct` = both empty. Also, as `aa chain t0-reference`: typecheck (`tsgo -b`,
  `yarn typecheck`), root and loot-core lint, and the existing tests related to the
  touched sources (`vitest related`, on the image's test infra), compared with one
  cached untouched-R run of the full seeded suite and the probe. A T0 packet (statement,
  diff, `sites.json`) for the completeness and interface judges.
- T2 static label (secondary to the judge's): the new consumer's code = the step's
  added or modified source lines outside the copy sites' bodies (`sites.json`). `helper`
  when it calls, directly or through one zone function, a zone-defined function that is
  not a copy site, that a copy site also calls (directly or through one), and whose body
  carries a zone marker (the zone's decision); Z4's `getDateWithSkippedWeekend` is
  excluded (§3: base already shares the date arithmetic; in untouched R it is the only
  function shared by two or more copy sites whose body carries a zone marker). `copy`
  when that code matches a zone marker or calls a copy site; else None (judge only).
  Replayed on study-2 T2 steps (descriptive, no study-3 data): F `helper` in 24/24 Z1,
  20/24 Z2, 24/24 Z3, 24/24 Z4; R `copy` in 11/24 Z1, 4/24 Z2, 24/24 Z3, 15/24 Z4. The
  other R steps read `helper` (Z1 13, Z2 20, Z4 9): their new consumer calls a helper
  the agent itself made at T1 and the copy sites call, which study 2's label (a fixed
  list of names) could not see. It is the "extended to agent-made helpers" case of §6,
  but it also means the static R base rate of `helper` is not ~0 %, so H2's base is read
  from the judge's label as registered.
- T1/T3 `rule_sites_touched`: distinct functions, among the copy sites and the zone
  functions they call (functions nested in a site count as the site), whose body the
  step changes. It also counts a site edited only to pass a new argument, so it is high
  for F at T1 in Z1 and Z3 as well (study-2 replay: F Z1 median 6); the judge's "one
  shared definition" label stays primary.
- `rule_cited` (all arms, so R is the baseline): the agent's own prose (Claude Code
  text/thinking, Codex messages/reasoning) quotes the RG rule or talks about extracting or
  reusing logic; `gaming_flags` = `aa.static3.step_gaming_flags` (diff + runner record).

## Amendment 2026-10-11c: one pre-existing-clone rule for every arm, trips past `tail`, `rule_cited` (§§5, 6), before any pilot

Registered with the review fixes of plan Task 5, before any study-3 agent run (no pilot,
no `runs3/`); no study-3 outcome was seen. Refines 2026-10-11b; the primary RL comparison
is still unchanged.

**The split was not the same rule in RL and in R/RG/RC (review, HIGH).** As registered,
`ratchet_kind` called a firing clone new as soon as one side lay on an *added* line, so a
rule check *inserted* inside copies the start tree already had (the T1 edit of Z1 and
Z3, the T3 edit of Z4) read `adds_new_clone_side` with `ratchet_start_fires = false`,
while RL's trip classification, which matches the clones against the start tree's,
called the same edit `touches_preexisting_only`. Now both use one matcher
(`aa.chain_eval3.matches_start_clone`): a firing clone (final tree or RL trip) is
pre-existing when it joins the same two files as a start-tree clone and each side,
mapped to start-tree lines through the step's `-U0` diff (inserted lines map to the
start lines around the insertion, so a copy grown by a rule check maps onto the copy),
overlaps that clone's side. `ratchet_kind`: `touches_preexisting_only` when every firing
clone is pre-existing; else `adds_new_clone_side` when a new firing clone has a side on
an added line; else, as before, `touches_preexisting_only` if the step edits a
pre-existing clone or `modified_into_clone`. `ratchet_start_fires` also counts lines
inserted inside a start-tree clone and firing clones that are a start-tree clone. A
trip's line numbers are mapped with the step's final diff (exact when the tree at the
trip is the final one). On real runs2 R steps (claude, chain 0: Z1 T1, Z3 T1, Z4 T3;
fixtures in `tests/fixtures/study3/ratchet_real/`), R's counterfactual and an RL trip
listing the same clones now both read `touches_preexisting_only`, with
`ratchet_start_fires = true` (before: R read `adds_new_clone_side`, Z1 and Z3 with
`ratchet_start_fires = false`). A copy pasted beside a pre-existing pair still reads
`adds_new_clone_side`.

**Trips past `tail` (review, LOW).** A tool result counts as a dup-check failure when it
prints dup-check's header, its closing line or one of its clone rows as a line, so
`yarn lint | tail -N` that cut the header still counts (clones read from the rows that
remain); the script's own source (quoted literals) does not. Output that hides all of
them cannot be seen; `ratchet_split` then falls back to `ratchet_kind`, as registered.

**`rule_cited` (review, LOW).** `rule_cited` is now the rule *quoted* (the RG rule's
distinctive phrases in the agent's own prose). Talk about extracting or reusing logic is
common in every arm and is kept as detail (`rule_cited_detail.reuse_talk`,
`reuse_mentions`), so R's baseline of `rule_cited` is not inflated by ordinary words.

**Bookkeeping.** In study 3 the T2 `t2_reuses_logic` is the static3 label only: when
static3 cannot run (step not evaluated, zone files or `sites.json` missing) it is None
(`t2_reuse_detail.reason = static3_not_run`), and study 2's label (computed on R's
helper list for RG/RL/RC) stays detail. `chain_result.json` says which tree
`duplication.T0` is (`duplication_T0_tree`: `untouched_variant`, or `agent_t0_post` in
an RC chain, whose untouched start is `duplication.start`). The chain evaluator's
progress line no longer reads keys a T0 result lacks (it aborted RC chains).

## Amendment 2026-10-11d: adjacent pastes, unfinished T0 evals, minor measure fixes (§§3, 5, 6), before any pilot

Registered with the second round of review fixes of plan Task 5, before any study-3 agent
run (no pilot, no `runs3/`); no study-3 outcome was seen. Corrects 2026-10-11c; the
primary RL comparison is still unchanged.

**Adjacent pastes (review, HIGH).** 2026-10-11c's last sentence ("a copy pasted beside a
pre-existing pair still reads `adds_new_clone_side`") was false when the copy is inserted
*directly* before or after an old clone side: the mapping sent inserted lines to the start
lines around the insertion, so the new copy's side overlapped the old side it sits
against and the clone read pre-existing (`touches_preexisting_only`, with
`ratchet_start_fires = true`). It happened on a real step: runs2/claude/R/Z1/1/T2 inserts
`setLastMonthSpending` after start line 345 of `actions.ts`, right before
`set12MonthAvg` (start lines 346-368, a side of an old clone with `set3MonthAvg`); jscpd
at 35 finds the new function copying `set3MonthAvg` on inserted lines only. Now a side
maps to start lines through its *start-backed* lines only (unchanged lines and lines
*modified* from a removed line, the added/modified rule of 2026-10-11b); lines the step
*added* map nowhere, and a side whose lines are mostly added (fewer than half
start-backed) maps to nothing and matches no start clone. A copy grown by a rule check
(inserted lines a minority of the side, the Z1/Z3 T1 and Z4 T3 shape) still maps onto
the copy it grew from. On the real step the two firing clones now read new:
`ratchet_kind = adds_new_clone_side`, `ratchet_start_fires = false`, and an RL trip
listing them reads the same (fixture `tests/fixtures/study3/ratchet_real/R-Z1-T2`, built
from `work/variants/R` + T1's patch + T2's patch with `aa.ratchet`). The three real rule
steps of 2026-10-11c read as before.

**Unfinished T0 evals (review, MEDIUM).** When RC's T0 evaluation did not finish
(`eval_error`: `container`, `eval_timeout`, `seed_install`, `test_infra_restore`,
`hidden_restore`), the probe and inconsistency fields (`probe_changed_cases`,
`probe_changed_raw`, `probe_unchanged`, `probe_passed`, `t0_tests`,
`inconsistencies_unified`) are None, not read from missing outputs (which counted as a
changed probe and every inconsistency unified, inflating H3's probe-changed rate with
infrastructure failures); checks that did run (typecheck, lint, related tests: their rc
files) are kept, and `correct` is false. Such steps are excluded from H3's rates as
missing, like any eval error.

**Minor (review, LOW).** `lint_runs` also splits commands on a single `&` (a backgrounded
command; `&>` and `2>&1` stay redirections), so `( ... ) & yarn lint` counts
(runs2/haiku/R/Z1/6/T3). `gaming_flags` also reads the evaluator's `step.patch` (start ->
agent tree; flags from both merged), so a `tree.tar` fallback step whose `diff.patch`
missed a change is still flagged. Without `start.json` or a carry record, RC's T1 is an
evaluation setup error rather than an image start (it starts from T0's tree; the runner
always writes the plan, so this was latent).

## Amendment 2026-10-11e: arm rotation offset by zone, pre-pilot table and concurrency fixes (§§2, 7, 9), before any pilot

Registered with the pre-pilot fixes of the final review of plan Tasks 1-6, before any
study-3 agent run (no pilot, no `runs3/`, no `runs3-pilot/`); no study-3 outcome was seen.

**Arm order (§2).** The scheduler rotated the arms by chain index only
(`ARMS[(i + k) % 4]`), so with one chain per cell (the pilot, §9) every zone ran R, RG,
RL, RC in the same order: R always first, RC always last within each (chain, zone). Now
the rotation is also offset by the zone's own index (`Z<n>` → n − 1; a subset of zones
keeps each zone's offset): chain `i`, zone `z` runs `ARMS[(i + k + z) % 4]`, k = 0..3. In
the pilot each arm runs first in exactly one zone (Z1 R, Z2 RG, Z3 RL, Z4 RC); over the
8 chains of the full run every arm still takes every position twice in every zone
(`aa.chain_runner.build_chain_queue3`, tests in `tests/test_chain_runner.py`).

**Tables (§7, plan Task 6), descriptive refinements, no hypothesis changed.**
- T0's pooled "any inconsistency unified" is over Z1–Z3; Z4 has no inconsistency tests
  (its value is always empty) and is shown apart, not pooled as a pass.
- T0's typecheck (both), lint (loot-core and root) and related-tests rates keep the
  checks that ran in an evaluation with a non-fatal `eval_error`, as amendment 2026-10-11d
  states; H3's probe and inconsistency rates still treat such steps as missing.
- An RC chain without `duplication.start` is missing for the start-based duplication
  growth (and counted), never read as its T0 tree.
- Efficiency is reported per step (T1..T4) as well as pooled over T1–T4.
- Beside the registered H4 (steps where the ratchet fired: seen by the agent or on the
  final tree), a seen-only H4 (`ratchet_trips` > 0), descriptive.
- Every judge-based row (T2 reuse, one shared definition, completeness, interface) says
  "kappa pending" until the inter-judge kappa is supplied (`aa tables3 --kappa`): kappa
  comes before any comparison (§8).

**Concurrency (no effect on measures).** `aa chain run` defaults to 2 chains in parallel
in study 3 (3 in study 2, unchanged); `aa chain evaluate` admits an RC T0 evaluation
(its untouched-R reference run and its container) exclusively, never beside another
evaluator container, since two T0-sized containers exhaust the 6 GB Docker VM.
`aa chain evaluate` / `packets` take the runs dir from `--study` (runs3/, `--pilot`
runs3-pilot/) when `--runs` is not given, and evaluator container names carry a short
hash of the runs root, so runs3, runs3-pilot and test trees never collide.

## Amendment 2026-10-11f: design-review blinding, related-test retry, CLI guards (§§3, 7, 9), before any pilot

Registered with the fixes of an independent review of the pre-pilot fixes and plan Task 7,
before any study-3 agent run (no pilot, no `runs3/`, no `runs3-pilot/`) and before any
study-3 packet is judged; no study-3 outcome was seen.

**Design-review packets (§7; rubric study-3 addendum, amended the same day).**
- *Per-packet trees (review, HIGH).* RC's chain packet (H1 primary) and RC's T1 step
  packet carried T0's tree as a non-empty pre-image, with a `tree.txt` saying to apply
  it, where every R/RG/RL chain and T1 packet had an empty one (dry run on study-2 data:
  96/96 empty vs 4/4 RC non-empty): the packet's form marked it as RC. Now no packet ships
  a pre-image: `aa.review3.PacketTrees` applies each packet's sanitised pre-image to its
  base tree in one neutral bare repository, one parentless commit per packet (fixed date,
  packet id as message), and every `tree.txt` names that repository and the packet's
  commit in the same form. The T0 refactor's *content* in RC's trees remains (inherent).
- *Batches (review, HIGH).* An RC chain's `t0` and `chain_full` packets could land in
  the same batch. Now a batch holds at most one packet per chain (agent, arm, zone,
  chain): first fit in the seeded shuffled order.
- *Sanitising (review, LOW).* Lines naming AGENTS.md, a duplication lint/check/ratchet,
  jscpd or dup-check, and common paraphrases of the RG rule are redacted, and the leak
  scan flags them; any `AGENTS.md` section is stripped. `package.json` is no longer
  stripped in every arm (it hid legitimate dependency changes): its dup-check lines are
  redacted, and the section is stripped only when the redacted section cannot apply to
  the neutral base (`package_json_stripped` in the mapping).
- *Kappa first (review, LOW).* `scripts/study3_design_review.py` writes the flat kappa
  JSON `aa tables3 --kappa` reads (`out/study3/design-kappa.json`) and writes the labels
  and H1 tables only once the second judge has scored the whole planned second sample
  (`batches.json`); `aa tables3 --kappa` rejects a file with no judged measure (it
  silently printed "kappa pending").
- `aa chain packets --study 3` runs the study-3 exporter (`aa.review3`) into
  `work/review3`; it ran study 2's exporter into study 3's paths, overwriting the blinded
  mapping.

**T0 related tests: one retry of failing files (§3 checks, review MEDIUM).** In one run
of `tests/test_chain_eval3_docker.py` the RC image's T0 evaluation timed out three tests of
`src/server/aql/schema/executors.test.ts` at 20 s, which counted as new related-test
failures (`related_ok = false`) for seeds that do not touch that code. Re-run with no
other container: both seeds pass (2 passed). In the reference re-run below (one
container, host CPU busy with other test processes) the same tests timed out at 20 s in
untouched R (3) and in Z1's reference (2), and passed when the file ran again alone (5/5).
The timeouts are load, not the tree. Now, when the related run does not pass, its failing test files run once more,
alone, same seeded config (`aa.chains.t0_related_retry_line`, `/out/related_retry.json`);
a new failure (or missing test) that passes in the retry is reported as `flaky` and not
counted; one that fails again still counts. Same rule in `aa chain t0-reference` and in
the study-3 T0 evaluation. Typecheck, lint, probe and inconsistency tests are unchanged.

**T0 references re-checked on the current R image (review MEDIUM).** The pre-pilot
rebuild left `tasks3/Z*/T0/reference_check.json` recording image `a2f09e9`; `aa chain
t0-reference` re-run in place on `aa-actual:R` = `f9bfc01`: Z1-Z4 all `ok` (typecheck,
lint, inconsistency tests, related tests with no new failure, probe minus exclusions
unchanged, leak audit clean); Z1's related run went through the retry (`flaky: []`: the
two timed-out tests were also untouched-R failures, so not new). Known limit: a test
that times out in the cached untouched-R run is a base failure and cannot count as new
in that run (sensitivity, not a false failure).

**Guards (review, LOW).** `--pilot` without `--study` is an error (it read
runs2-pilot/). Agent-run container names (`aa3-<tag>-…`) and t0-sanity / t0-reference
container names carry a short hash of their runs root / work dir, as the evaluator's
already did.

## Amendment 2026-10-12: pilot blocking fixes 1-4 and 9 (§§6, 7, 9), after the pilot, before the full run

Registered with the fixes of `docs/study3-pilot-report.md` §6, blocking items 1-4 and 9.
Unlike the earlier amendments this one is written **after** the pilot's outcomes were
seen (n = 1 per cell, not effect estimates); no primary hypothesis or measure definition
changes, only how runs are classified, how usage is read, how RL trips are split and one
added descriptive measure. Re-derivations of existing step dirs go through harness
commands that rewrite only derived fields, each with a record on the rewritten file and
in `<runs>/rederive-log.jsonl`; transcripts, diffs and stderr are never edited.

**Run status (item 1).** A step whose transcript ends in transport / connection errors
with no agent progress after them (Codex `Reconnecting...`, `stream disconnected`, DNS
`Name does not resolve`; Claude Code API retry notices or a synthetic `API Error:
Connection error.`) is `infra` whatever its exit code (`aa.agents.transport_stalled`,
`aa.runner.classify_status`), and so is a wall-clock kill with no agent activity at all
(no turn, tool call or token). Missing usage alone is not "no activity": Codex reports
tokens only at `turn.completed`, so every Codex wall-clock kill has missing usage,
including real agent timeouts (study 2 `codex/F/Z3/1/T1`, `codex/F/Z4/0/T1` were killed
while running commands). `infra` is re-queued and never carried; the chain runner
resumes at that step and removes the later steps built on its tree (unchanged rule).
`aa chain reclassify --runs DIR` applies the rule to finished steps (only changes to
`infra`; agent.json `status` + `status_reclassified`, result.json and chain.json
follow); `aa chain run --dry-run` lists what each chain would re-run and discard.
`aa tables3` does not count a step that follows an `infra` step of its chain
(`after_infra`) until the chain is re-run. Pilot: `codex/R/Z3/0/T1` and
`codex/RC/Z3/0/T2` reclassified (`timeout` -> `infra`, transport stall); their chains
resume there and discard T2-T4 / T3-T4. Study 2 was **not** reclassified: the rule would
also flip `runs2/codex/F/Z2/0/T1` (`ok`, exit 1, `workspace routing discovery timed out`
reconnects, `correct = true`), a registered study-2 result left as it is.

**Usage (items 2, 3).** Claude usage and turns are the sum over every `result` event of
the stream (Claude Code writes one per wake after background tasks), plus any assistant
message after the last `result`; a Codex stream without `turn.completed` has missing
tokens (None), not 0 (turns and tool calls are still counted from the stream). The
evaluator re-parses the transcript for result.json's `tokens` / `turns` / `tool_calls`
(`usage_source`, `usage_missing`; the runner's agent.json record is kept, and a
difference is kept as `usage_reparsed`); `aa chain reparse --runs DIR` re-derives
existing results and chain summaries. Every token distribution (tables2, tables3: H5,
efficiency, chain totals, cost growth) excludes missing values and reports their count;
a chain with a missing step has no token total. The turn limit is checked on the summed
turns (no pilot or study-2 step reaches it). Re-parsed: pilot 5/136 Claude-engine steps
and 2 Codex steps (missing), study 2 16/512 Claude-engine steps and 3 Codex steps.

**RL trip kinds (item 4).** Each clone a dup-check trip lists is matched against the
step's start tree as the tree was at that trip (`aa.chain_eval3.classify_trip`), not
through the final diff whatever happened after: when the clone is still a clone of the
post tree at exactly the same lines, the final diff maps it (exact); otherwise the agent
changed those lines after the trip (typically it consolidated what the trip showed) and
the trip's line numbers are read as start-tree lines, pre-existing when its two files
hold a start-tree clone whose sides overlap the trip's (approximate: lines inserted above
the clone before the trip shift it; only the overlap absorbs that). The basis is
recorded per trip (`ratchet_trip_basis`: `final_tree`, `start_lines`, `mixed`). The
runner keeps no snapshot of the tree at a trip and the transcripts cannot rebuild one
(Codex `file_change` items carry no content; agents also edit through shell scripts);
an exact per-trip snapshot would need the runner to record `git diff -U0 <start>` at
each dup-check run (not built). `aa chain rederive-trips --runs DIR` re-derives the
trip fields from the eval outputs on disk (no container); `ratchet_split` follows.

**Behaviour check outside T0 (item 9, descriptive).** The zone's T0 inconsistency tests
that no step statement supersedes run on every T1-T4 post tree in every arm
(`inconsistencies_unified_step`: ids whose test did not pass; None when no test is in
scope at that step or the check did not run). Which tests a step supersedes is decided
per test in `tasks3/inconsistency-scope.json` with reasons: Z1's `setzero-writes-hidden`
and Z2's `template-half-of-rounded-sum` are superseded from T1 on (T1's statements
redefine the hidden-category rule and the ranged amount for every consumer), Z3's three
tests are in scope at every step, Z4 has none; so in practice the check covers Z3.
Checked against the chains' reference trees (`aa chain scope-sanity`,
`tasks3/<zone>/T0/scope_sanity.json`): in R and F the Z3 tests pass after each reference
step T1-T4, and the Z1 / Z2 tests fail from T1 on, as the statements require. The full
evaluation runs them after the hidden tests (`/out/scope_tests.json`); `aa chain
behaviour-check --runs DIR` adds the field to evaluated steps (post tree rebuilt in a
fresh container, `eval_behaviour/`, its tree id checked against the evaluator's own `eval/post_tree`; a mismatch leaves the field None). `aa tables3` reports it per arm and step, beside
H4 (fired RL steps; how many counted as H4 successes unified an inconsistency) and the
T2 static label. Not a hypothesis; H4 is unchanged.

## Amendment 2026-10-12b: pilot pre-registration items 5-8 and run protocol (§§3, 5, 6, 7, 9), after the pilot, before the full run

Registers `docs/study3-pilot-report.md` §6, blocking items 5-8, and the pilot's operational
lessons. Like amendment 2026-10-12 it is written **after** the pilot's outcomes were seen
(n = 1 per cell, no effect estimate) and **before** the full run and before any design-review
packet exists or is judged (`work/review3/` does not exist on this date). No hypothesis, its
direction, its threshold or its registered denominator changes. Items 5-7 fix how already
registered quantities are benchmarked, decomposed and named; item 8 fixes how the T0
`completeness` judge scores a partly consolidated site, which the rubric left open. The
weight of a partial site (0.5) was chosen after reading the 12 pilot T0 diffs (no judge
score); that is disclosed here and two sensitivity readings are registered with it.

**Calibration benchmark of ratchet firing (item 5).** The calibration
(`out/study3/ratchet-firing-by-step.json`, study-2 R and F trees, amendment 2026-10-11)
describes where the ratchet fires on trees the study-3 lever has not touched. It is the
benchmark only where the step's tree is such a tree:
- RL at **T1** (its start tree is the untouched R variant, as in calibration R T1);
- the counterfactual `ratchet_final` (and `ratchet_kind`) of **R** at T1-T4 (R is the
  calibration's own arm, run fresh); and of **RG and RC** at T1-T4, reported beside the
  same calibration cells with the caveat that their trees may already differ by treatment
  (RG's rule; RC's T1 starts from the agent's T0 tree), so a departure there is read as
  drift *or* treatment, not as a detector failure.
- **RL at T2-T4 is not benchmarked against calibration.** Its start tree is the agent's
  T1 (and later) output under the ratchet, so its firing is downstream of the treatment:
  it is a treatment outcome, reported per zone and step beside R's counterfactual firing at
  the same step (e.g. pilot Z3 T4: RL 0/3, R 3/3, after the RL agents consolidated at T1),
  descriptively and never as "the ratchet fires where calibration says".
- Comparison rule: per zone × step, the full run's firing rate with its Wilson 95 % interval
  beside calibration's (n = 24); a cell whose two intervals do not overlap is "off
  calibration" and is read in the traces before any interpretation (pilot example: R Z4 T2
  2/3 vs 3/24, both firing steps `adds_new_clone_side`).
- §9's "the ratchet fires where calibration says it should" means exactly these
  benchmarked cells.

**Decomposition of H4's fired steps (item 6).** Registered H4 is unchanged: over RL steps in
the non-blind zones (Z1, Z3) where the ratchet fired, i.e. `ratchet_trips > 0` (seen) or
`ratchet_final.fires` (fires on the final tree), the share that end with `ratchet_final`
not firing and no gaming flag. Every fired step falls in exactly one class, tested in this
order:
- **(g) passing with a gaming flag:** `ratchet_final.fires` false and `gaming_flags`
  non-empty. H4 failure.
- **(d) fired, never seen:** `ratchet_trips == 0` and `ratchet_final.fires`. Split (d0)
  `lint_runs == 0` (no lint run at all) and (d1) `lint_runs > 0` (the agent ran lint but no
  failure is visible: an edit after its last lint run, or output it hid, e.g. `| tail -1`).
  H4 failure; it says the lever never reached the agent, not that the agent ignored it.
- **(c) seen, not fixed:** `ratchet_trips > 0` and `ratchet_final.fires`. H4 failure. A
  final message that reports lint as passing against its own tool output (pilot: one of
  two) is noted from trace reading, descriptively; no field.
- **Seen, passing** (`ratchet_trips > 0`, `ratchet_final.fires` false, no gaming flag): H4
  success, split by what happened to the clones the trips listed. Let *L* be the start-tree
  clones that some trip clone matches (`classify_trip`'s per-clone basis and matcher,
  amendment 2026-10-12), *N* the trip clones that match no start-tree clone (clones the
  agent itself had added), and *Rm* the members of *L* still a clone of the post tree
  (`matches_start_clone` of a post-tree clone, through the step's final diff).
  - **(a) by consolidation:** *Rm* empty: every listed pre-existing clone is gone from the
    post tree, and any clone the agent added is gone (e.g. a paste replaced by a call).
  - **(b) by moving the edit outside the clone:** *L* non-empty and *Rm* = *L*: every
    listed pre-existing clone is still duplicated in the post tree; the agent passed by
    keeping its changed lines off it (e.g. a check moved into one wrapper around
    unchanged copies). The rule allows it; it removes no duplication.
  - **(ab) mixed:** some but not all of *L* remain.
  - **(u) unreadable:** a trip whose clone rows cannot be read (`ratchet_trip_kinds`
    holds None), or the scans needed are missing (`ratchet_error`).
  H4 success = (a) + (ab) + (b) + (u); failure = (c) + (d) + (g).
- **Fields.** (c), (d), (g) and the "seen, passing" total come from fields every
  study-3 `result.json` already has (`ratchet_trips`, `ratchet_final.fires`, `lint_runs`,
  `gaming_flags`). (a) / (b) / (ab) / (u) need one derived field per RL step,
  `ratchet_trip_clones = {listed_preexisting: |L|, remaining: |Rm|, new_listed: |N|,
  unreadable_trips: int}`, computed from outputs already on disk (`eval/ratchet_start`,
  `eval/ratchet_post` scans and file lists, `eval/ratchet_diff.patch`, the transcript's
  trips), without a container, like `aa chain rederive-trips`. Not built by this
  amendment (the evaluator and `aa tables3` are being changed by another workstream); a
  read-only check of the definition on the pilot (a scratch script calling
  `aa.chain_eval3`'s parser and matcher, nothing written) reproduces the pilot report's
  trace reading of all 12 fired non-blind steps: (a) 6 (claude Z1 T4 and Z3 T1, codex Z1
  T1, haiku Z1 T1, Z1 T2 and Z3 T2; haiku Z1 T2 listed only a clone it had added), (b) 2
  (codex Z3 T1: 7 of 7 listed clones remain; haiku Z3 T1: 1 of 1), (c) 2 (claude Z1 T2,
  codex Z3 T2), (d) 2 (claude Z1 T1 d0; codex Z1 T4 d1), (g) 0, (u) 0.
- **Reporting (`aa tables3`, RL table).** Per agent: fired steps and the counts of (a),
  (ab), (b), (u), (g), (c), (d0), (d1), with registered H4 and its Wilson interval beside;
  confirmatory scope Z1 + Z3, Z2 / Z4 descriptive; also split T1 vs T2-T4 (T1 alone shares
  R's start tree). Beside the successes, how many unified an in-scope T0 inconsistency
  (`inconsistencies_unified_step`, amendment 2026-10-12). Until `ratchet_trip_clones`
  exists the table shows (a) + (ab) + (b) + (u) as one "seen, passing" row; that is
  enough for registered H4, and the split is required before `docs/results-study3.md`.
  (b) is read as evidence for the rival hypothesis (the lint dodged, not duplication
  removed), never as a failure of H4.

**RG manipulation check (item 7).** As built, the transcript cannot observe use of the RG
rule. `rule_cited` (the rule's distinctive phrases in the agent's prose) was 0/48 RG steps
and 0/204 overall; `agents_md_read` was false in 204/204, by construction: Claude Code
loads the variant's `CLAUDE.md` (`@AGENTS.md`) and Codex loads AGENTS.md into the agent's
context itself, so the file is never opened with a tool call; Claude/Haiku thinking blocks
are nearly always empty in the stream (1 of 249 non-empty for Sonnet, 0 of 946 for Haiku)
and Codex emits no reasoning items. Registered now:
- **RG compliance is measured by behaviour only**: the judge's T2 `t2_reuse` label and
  rule-step `one_place` label (primary), and the static `t2_reuses_logic` label
  (secondary), each RG vs R as in H1/H2. There is no RG manipulation check; that the rule
  reached the agent rests on delivery (the rule is in the loaded AGENTS.md:
  `work/variants/RG/AGENTS.md`, 19.9 KB, under Codex's 32 KiB limit), not on an observed
  use. A null RG result is therefore "the rule, delivered, did not change behaviour", not
  "the rule was read and ignored".
- `agents_md_read` is renamed **`agents_md_explicit_read`** (the agent opened AGENTS.md
  with a tool call), documented as **not** a manipulation check. Readers go through
  `aa.rg_check` (`agents_md_explicit_read`, `normalise_rule_detail`), which accept both
  keys, so pilot `result.json` files need no re-derivation; `aa.chain_eval3.rule_cited`
  writes the new key when it is next changed (one key in `rule_cited_detail` and its
  test; left to the workstream that owns that file).
- `rule_cited` is kept as a **descriptive** measure in every arm (R the baseline), with
  `reuse_talk` as detail; it is not a manipulation check and not a hypothesis.
- §6's "RG: whether the agent quotes or follows the rule (trace)" now reads "RG: whether
  the agent follows the rule (behaviour); quoting it is descriptive".

**T0 completeness of partial sites (item 8).** `docs/design-review-rubric.md`, study-3
addendum, amended the same day (before any T0 packet is judged): each site of `sites.json`
is scored **full** (1), **partial** (0.5) or **not consolidated** (0); `completeness` =
(full + 0.5 × partial) / sites. *Partial*: the site calls the shared definition but still
decides part of the zone's decision locally (a filter, condition, branch, dispatch or
flag computation the shared definition takes, or should take, for the other sites). A
site left out on purpose to keep a registered inconsistency is *not consolidated*, with
its reason recorded; carrying the inconsistency as an explicit parameter of the shared
definition is *full*. A T0 whose probe changed or that unified an inconsistency is scored
like any other (the judge is not told) and **flagged**: `aa tables3` shows completeness
with `t0_probe_changed` / `t0_inconsistency_unified` beside it, and an exploratory
completeness over unflagged T0s. H3 is unchanged (median completeness ≥ 0.75 and probe
unchanged in ≥ 75 % of RC chains). Sensitivity, reported beside the primary: partial = 1
(lenient) and partial = 0 (strict). Reliability: the quadratic-weighted kappa on
completeness in quarters as registered, plus per-site agreement on the three levels
(Cohen's kappa over the sites of the double-judged T0 packets), descriptive. The judge
writes `per_site` as levels; `aa.review3`'s parser already accepts any `value` in 0..1, so
the change needs no code to be read; checking that `value` equals the levels' formula and
the per-site kappa are follow-ups before the first T0 packet is judged.

**Run protocol (operational lessons, §9).**
- **Codex login.** The guard of `01189b3` stays on: `aa chain run --agent codex` refuses to
  start with < 24 h of login left (`--min-codex-auth-hours`), and the scheduler stops
  dispatching (`auth_expired`, no infra attempt spent) below 2 h. The current token
  expires **2026-10-22 06:57 UTC** (guard refuses from 2026-10-21 06:57 UTC). The full run
  therefore runs the **Codex block first** (order codex → claude → haiku), unless a fresh
  login is made immediately before a later Codex block; the Claude blocks start after the
  weekly window reset (2026-10-12 21:00 UTC).
- **Power.** The host stays plugged in, and every `aa chain run` / `aa chain evaluate` runs
  under `caffeinate -dims` (its `-s` holds only on AC power). Pilot incident 1: a power
  loss killed two in-flight steps, rerun as infra. Check `pmset -g batt` shows AC power before starting.
- **Network.** A host network stall is `infra` (item 1, amendment 2026-10-12): re-queued,
  never carried, the chain resumes at that step. After each block, `aa chain run --dry-run`
  lists any chain still to resume before evaluation starts.
- **Docker.** At most two loot-core containers (6 GB VM): agent blocks with `--workers 2`,
  evaluation never overlapping agent runs, T0 evaluations alone (amendment 2026-10-11e).

## Amendment 2026-10-12c: follow-ups of 2026-10-12b built, records for derived chain files (§§5, 6), after the pilot, before the full run

Implements what amendment 2026-10-12b registered and left to a later change, and closes
the gaps a review of the 2026-10-12 re-derivations found. No hypothesis, measure
definition, threshold or denominator changes.

- **RG (item 7).** `aa.chain_eval3.rule_cited` writes `agents_md_explicit_read`; pilot
  results keep `agents_md_read`, and `aa tables3` reads either through `aa.rg_check`. The
  RG table reports it beside `rule_cited` and `reuse talk`, descriptive in every arm and
  labelled as not a manipulation check.
- **Calibration benchmark (item 5).** `aa tables3` (`--calibration`, default
  `out/study3/ratchet-calibration-summary.json`, `firing_by_step_at_chosen.R`) prints per
  zone × step each arm's firing (seen or on the final tree) with its Wilson interval
  beside calibration's (n = 24): R, RG and RC at T1-T4 and RL at T1 are benchmarked, and
  a benchmarked cell whose interval does not overlap calibration's is marked **off**;
  RL at T2-T4 is marked as a treatment outcome and never flagged.
- **H4 decomposition (item 6).** `ratchet_trip_clones` = {`listed_preexisting` |L|,
  `remaining` |Rm|, `new_listed` |N|, `unreadable_trips`} is computed by
  `aa.chain_eval3.trip_clone_counts` (the matcher and per-clone basis of
  `classify_trip`), written by the evaluator and by `aa chain rederive-trips` (from the
  eval outputs on disk, no container). `aa tables3` classifies each fired RL step in the
  registered order ((g), (d0)/(d1), (c), then (u), (a), (b), (ab); `seen_passing` for
  results without the field) and prints the counts per scope (non-blind Z1+Z3, all
  zones) and period (T1-T4, T1, T2-T4), with registered H4 and the successes that unified
  an in-scope T0 inconsistency. A trip with no readable clone row makes its step (u).
  Pilot (`aa chain rederive-trips --runs runs3-pilot`, 11 steps, recorded): (a) 6, (b) 2,
  (c) 2, (d0) 1, (d1) 1, (g) 0, (u) 0 over the 12 fired non-blind steps, as the
  read-only check of amendment 2026-10-12b found.
- **Records for derived chain files.** Every file a re-derivation rewrites now has a
  record in `<runs>/rederive-log.jsonl`: `aa chain reclassify` logs the chain.json
  `status` change (`chain_status`: {from, to}); a chain summary rewritten by `aa chain
  reparse` logs `resummarise_chain` (the chain_result.json keys that changed, old and new,
  and cumulative.patch's sha256 before and after); `aa chain rederive-trips` records
  every field change, not only a change of kind. The summaries rewritten on 2026-10-12
  before this rule have retrospective records (`aa chain record-summaries --before
  <backup>`, from a backup of agent.json, result.json, chain.json and chain_result.json
  taken before the re-derivations; cumulative.patch was not in it): runs2 192 chains
  (chain_result.json gained `totals`, `cumulative_diff.from` and `duplication_T0_tree`
  null -> `untouched_variant`; `cost_growth` changed in 13), runs3-pilot 48 chains
  (`totals`; `cost_growth` in 4; chain.json `status` `ok` -> null and the step status
  `timeout` -> `infra` in the 2 reclassified chains). For all 240 cumulative.patch files
  the content now equals its source (the last step's `eval/post_tree.patch`, which
  predates the backup), the code that writes it has copied that file verbatim since
  `ae85094` (2026-10-08), and its files / added / removed counts equal the backup's; so
  the rewrite left the content unchanged, although the previous bytes were not kept.
- **Still open, disclosed.** (1) `aa chain reclassify` keeps rewriting agent.json
  `status` (the chain runner reads the status from there; the old value stays in
  `status_reclassified.from`). (2) The `start_lines` basis of a trip whose clone is gone
  from the post tree remains approximate (amendment 2026-10-12); the per-trip snapshot
  (`git diff -U0 <start>` at each dup-check run) is not built, and the 4 pilot
  `ratchet_split` flips depend on it. (3) The Claude Code stall patterns are tested on
  synthetic transcripts only: no transcript under `runs/`, `runs-*`, `runs2*` or
  `runs3-pilot/` has an API retry or `API Error` event. (4) Study 2 keeps
  `runs2/codex/F/Z2/0/T1` as `ok`, which the study-3 rule would make `infra`
  (`docs/results-study2.md` §4.5 gives the sensitivity); the decision is the user's.

## Amendment 2026-10-17: full-run execution record (§§7, 9), after the agent runs, before any comparison

Written after all 384 chains ran and all 1,632 steps were evaluated, before the design
review, the kappa or any arm comparison was read. `out/study3/tables3.md` exists but
only the secondary missed-copy table was looked at (in the run log of 2026-10-17).

- **Agent blocks.** Codex 2026-10-12 15:47 to 2026-10-13 01:54 BST, 128/128 chains, 0
  re-queues. Sonnet to 2026-10-14 15:21, 128/128, 177 re-queues (a Claude subscription
  session limit, HTTP 429 "You've hit your session limit", 2026-10-13 ~17:00-20:00 BST;
  and host network loss), 0 `infra_exhausted`. Haiku to 2026-10-16 08:58, 128/128, 13
  re-queues logged (its first 2-worker phase ran with buffered stdout and the lines of
  that process were lost when it was stopped; the step records are complete). Final step
  statuses: Codex 544 ok; Sonnet 540 ok, 4 timeout; Haiku 528 ok, 16 timeout. Every
  `timeout` is a wall-clock kill with agent activity (registered rule) and none overlaps a
  host sleep window (next item).
- **Host sleep is `infra` (deviation).** The laptop slept with its lid closed on
  2026-10-13 22:54 to 2026-10-14 07:35 BST and 2026-10-15 22:21 to 2026-10-16 06:14 BST
  (`pmset -g log`: Clamshell / Thermal Emergency sleep with dark wakes). The container
  clock kept counting while the host's monotonic clock did not, so a step could reach exit
  124 after 581 s of host time. Four Haiku steps whose window overlaps the second sleep and
  that were recorded `timeout` are reclassified `infra` (reason `host_sleep`) and re-run
  from that step: `haiku/R/Z2/7/T2`, `haiku/RG/Z2/7/T2`, `haiku/RL/Z1/7/T2`,
  `haiku/RG/Z4/7/T1` (the last had no extractable diff, so its T2 was a
  `harness_error`). The original chain dirs are kept in
  `runs3-archive/host-sleep-2026-10-16/`, the records in `runs3/reclassify-host-sleep.jsonl`
  (copy in `out/study3/`); agent.json keeps `status_before_reclassify`. No step overlapping
  a sleep window is left with a status other than `ok`: the other overlapping steps were
  `infra` already (re-run) or `ok` (3 Sonnet, 1 Haiku; their `wall_s` includes the sleep
  and is excluded from wall-time comparisons by the same window test). Four containers left
  unkillable by the sleep were cleared by a Docker restart. The pilot rule (network stall
  is `infra`) did not cover a host suspend; this extends it with the same rationale (the
  agent did not get its wall budget) and an objective window test.
- **Haiku's last 36 chains at 4 workers (deviation from §9 Docker).** The Docker VM went
  from 6 to 10 GiB on 2026-10-15 18:08 BST and the Haiku block resumed with `--workers 4`:
  146 Haiku steps in 36 chains started then. The arms are interleaved, so the remaining
  chains spread over R, RG, RL and RC; wall time of those steps is reported separately
  (load), tokens, turns and outcomes are unaffected by the worker count itself. Final Haiku
  timeouts: 12 in steps started at 2 workers, 4 in steps started at 4 workers
  (`haiku/RC/Z3/7/T2`, `haiku/RG/Z3/6/T1`, `haiku/RL/Z1/7/T1`, `haiku/RL/Z2/7/T2`);
  timeouts are a step outcome, so this split is reported with the results.
- **Evaluation parallelism.** `aa chain evaluate --all --study 3` ran with 4, 6, 8 and 10
  workers (Docker VM 12 GiB from 2026-10-16 13:45), restarted at each change; a step counts
  as evaluated only when its result.json is written, so a restart re-evaluates the steps in
  flight. The host CPU was thermally limited (`pmset -g therm`, CPU_Speed_Limit 56-70) for
  part of the evaluation.
- **T0 evaluations shared the gate (deviation from amendment 2026-10-11e), failures
  re-checked alone.** From 2026-10-16 15:09 BST (`START=1792159767`) the evaluation ran
  with `AA_T0_SHARED=1`: an RC T0 evaluation takes the shared side of `chain_eval.GATE`
  instead of the exclusive one (`aa.chain_eval.evaluate_step`; default unchanged;
  `tests/test_study3_prepilot.py::test_t0_gate_mode_follows_aa_t0_shared`). Rationale:
  load only produces false failures (the 20 s test timeouts of amendment 2026-10-11f), so
  a T0 that passes every check under load is valid. Every T0 evaluated in shared mode with
  any failing check (correct, related tests, probe, typecheck, T0 tests or eval_error;
  `scripts/study3_t0_recheck.py`) was re-evaluated alone with `--force` (`--workers 1`, no
  other container): 18 steps (`out/study3/t0-recheck-alone.txt`). Alone, 14 have no
  failing check and 4 stay incorrect with probe changes (`codex/RC/Z1/6/T0` 6,
  `codex/RC/Z3/2/T0` 8, `haiku/RC/Z3/1/T0` 12, `haiku/RC/Z3/4/T0` 12). Of the 18, one
  changed `correct` (`haiku/RC/Z1/1/T0`: probe changes 1 under load, 0 alone) and one its
  probe count (`haiku/RC/Z3/1/T0`: 13 -> 12): the probe has load-sensitive cases too. The
  other 13 were flagged by a check other than `correct` (the run log keeps only correct,
  probe changes and unified per step; the shared-mode values of related/typecheck/T0 tests
  were overwritten by the re-check). The 33 T0 evaluated before `START` ran exclusive.
- **Load check of T1-T4 (to do before any comparison).** T1-T4 evaluations ran beside up
  to 9 others; no vitest log has a timeout message, and the Sonnet correct rate was the
  same at 4 and 8 workers (54/514 vs 2/30 incorrect). Since the probe showed
  load-sensitive cases, every T1-T4 step evaluated at 6 or more workers with
  `correct = false` is re-evaluated at low load before results are written; any change
  is reported. **Done 2026-10-17** (`scripts/study3_load_recheck.py`, two chain-disjoint
  shards, steps of a chain in order, later steps of a changed step re-evaluated too;
  `out/study3/load-recheck/before-after.json`): 226 steps, 2 changed, both T4 (no later
  step): `codex/RC/Z1/6/T4` had `eval_error = container` (its evaluator container failed
  under load; a step with an eval error counted as incorrect) and is correct, 6/6
  consumers, at low load; `haiku/RG/Z4/3/T4` went from 2/3 to 3/3 consumers (one
  load-sensitive hidden test). No result in runs3 has an `eval_error` now. Chain summaries
  and tables were regenerated afterwards.
- **T0 completeness follow-ups of amendment 2026-10-12b item 8 built (before any packet is
  judged).** `aa.review3.normalise` computes `completeness` from the judge's `per_site`
  levels (full 1, partial 0.5, none 0; legacy booleans read as full / none), adds
  `lenient` (partial = 1) and `strict` (partial = 0), and replaces a judge `value` that
  disagrees with its own levels, recording `value_mismatch` {given, levels};
  `reliability` adds `per_site` (Cohen's kappa and agreement over the sites of the
  double-judged T0 packets); `labels_from` passes the sensitivities to `aa tables3`, whose
  T0 table now shows lenient / strict completeness, how many judged T0s are flagged (probe
  changed / inconsistency unified) and the exploratory completeness over unflagged T0s.
  The other analysis follow-ups listed before the full run (`aa.rg_check` with
  `agents_md_explicit_read`, the H4 split of `ratchet_trip_clones`, the calibration
  comparison) were already in the code (amendment 2026-10-12c).
