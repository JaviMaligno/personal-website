# Agent abstractions — design spec

**Date:** 2026-10-05 · **Status:** draft, pending review; amended 2026-10-06
(task sources, §4) · **Owner:** Javier Aguilar

## 1. Question

Matt Pocock (after talking to @poteto) argues that in the AI age we should use
**more** abstractions than usual: combined with harsh lint rules they shrink the
design space the agent can move in, so it only makes good decisions; and
high-leverage abstractions let it do more with less code, so it spends fewer
tokens. The counter-position is that agents just want to read the raw code.

This experiment tests the first two claims on a real codebase with two real
coding agents:

- **Constraint:** do more abstractions + harsh lint reduce the agent's bad
  decisions (invariant violations that still pass the tests)?
- **Efficiency:** do they reduce tokens and turns per solved task?

Out of scope for this phase: the third claim (unwinding a bad abstraction is
cheap with agents).

## 2. Substrate

**Actual Budget**, `packages/loot-core` (MIT, ~48k LOC TypeScript, vitest with
in-memory SQLite, no Docker/network). Base commit `9732a446` (2026-10-04),
frozen for the whole phase.

Invariants the domain cares about:

1. **Sync (CRDT):** every write to a synced table must go through the `db`
   layer (`db.update/insert/delete_/…Schema`), which emits CRDT messages with a
   `Timestamp`. A direct SQL write works locally and silently breaks
   multi-device sync.
2. **Money as integers:** amounts are stored as integer minor units
   (`amountToInteger` / `integerToAmount`); float arithmetic on amounts is a bug.
3. **Undo:** user-facing mutations are wrapped in `undoable`/`runMutator`.

## 3. Conditions (2×2)

| | No extra lint | Harsh lint |
|---|---|---|
| **A — habitual** (Actual as-is) | A | A+L |
| **A⁺ — more abstraction** (domain layer on top) | A⁺ | A⁺+L |

**A (habitual).** The repo as maintainers wrote it. The agent has `db.update`
but nothing stops it from bypassing it, doing float maths on amounts, or
forgetting `undoable`.

**A⁺ (more than usual).** A domain layer added by us, designed so the bad
decision is **not expressible**, not merely discouraged:

- Domain commands (e.g. `transactions.createTransaction`,
  `categories.deleteCategory`) under `src/server/domain/`, one module per table
  group, that encapsulate CRDT emission and validation and reproduce the base
  write sequence exactly.
- A mutation helper `mutation(name, handler)` = `mutator(undoable(handler))`
  (`src/server/domain/mutation.ts`). All 82 base registrations of the form
  `app.method(name, mutator(undoable(handler)))` migrate to it with identical
  behaviour; the 21 `mutator`-only registrations (not undoable in base) keep
  their form. Undo therefore lives at handler registration, not inside
  commands (a nested `undoable` would add a second undo entry).
- A branded money type `Cents` (integer minor units; the existing `Amount`
  alias stays the float form) so passing a float amount to a command is a type
  error; conversions only through `cents.fromInteger/fromAmount/toAmount`.
- Write boundary: the generic write API (`update`, `insert`,
  `insertWithUUID`, `delete_`, `deleteAll`, `insertWithSchema`,
  `updateWithSchema`) **and** the data-specific write functions of
  `db/index.ts` (`insertTransaction`, `moveCategory`, `updatePayee`, …) move
  unchanged to `db/write.ts` (`#server/db/write`), which only `src/server/domain/`,
  `src/server/db/` and test files import. `#server/db` keeps reads and the
  generic SQL entry points (`runQuery`, `run`, `execQuery`, `cache`), so raw
  SQL writes stay expressible; the pre-existing raw writes on synced tables are
  kept verbatim behind named commands. Test files keep direct access, so the
  existing suite and the hidden tests run unchanged on A⁺. The full contract
  and honesty list are in `docs/a-plus-design.md`.

**Lint (L).** ESLint run as a team would run it: available to the agent, and
the prompt asks for `lint` to be green. Not a hidden judge.

- A+L: no SQL writes (`runQuery` INSERT/UPDATE/DELETE) on synced tables outside
  `server/db`; no `sendMessages` outside sync/db; arithmetic on identifiers
  matching amount fields must go through the money helpers. Allow-list for the
  9 pre-existing raw writes.
- A⁺+L: no imports of the `db` write API outside the domain layer; no `as`
  casts to branded types; no `any`/`@ts-ignore` in touched files; mutations
  only through domain commands.

### Integrity rules for A⁺ (anti straw-man)

1. **A⁺ is designed from the domain before any task is mined**, documented in
   `docs/a-plus-design.md`, and frozen in a dated commit. It is never adjusted
   to fit tasks.
2. **The full loot-core suite must pass on A⁺** with the same results as on A.
   Baseline on base with the pinned Node 24.18.1 (`.nvmrc`): 1227 passed,
   0 failed, 2 skipped (the two `sync.property.test.ts` property tests, skipped
   in the repo itself); `yarn tsgo -b` exits 0 with 0 errors. Nothing is
   excluded: the two `parse-file.test.ts` charset failures only occur on
   Node 22, so the suite runs only on the pinned Node.
3. **The A⁺ diff is published** with the results so readers can judge whether
   it is a reasonable abstraction.
4. Lint rule sets for A+L and A⁺+L are frozen together with A⁺.

## 4. Tasks

### Amendment 2026-10-06 (task sources)

**Decided by Javier on 2026-10-06, before any experimental run**: no pilot or
full-run session has been started on any task; the only agent calls so far are
the tool-less memorisation probe, the statement reviews and the 1-line
`dummy01` adapter smoke runs (Task 8). It changes where tasks come from, not
the conditions, measures, checker or hypotheses.

**Why.** Mining alone cannot reach the target. Of the 724 candidate commits
(2024-10 → base), 153 were excluded by the "[AI]" label filter, and of the 34
that passed every static filter, 32 were dropped because the revert conflicts
on a variant (`revert_conflict:A` 30, `revert_conflict:AP` 2): history after
the commit has rewritten the same lines, so the 3-way revert no longer
applies. Only 2 tasks survived (`4556e9e244`, `81ea158cf6`), and the
memorisation probe then flagged one of them (`4556e9e244`, Codex 0.750). The
counts are in `tasks/_ledger.json`. Two changes follow:

1. **"[AI]"-labelled commits are no longer excluded.** `ai_label` becomes a
   recorded task attribute; results are reported split by it (below).
2. **A second task source: open GitHub issues** of `actualbudget/actual`,
   turned into tasks with hidden tests and references written by agents
   (§4.2). These need no revert, so they avoid the conflict problem entirely.

The target stays **15 selected tasks after the pilot**, pooled over both
sources; ~18 issue tasks are authored so the pilot has spares. The original
mining text below is kept, with filter 1 rewritten.

### 4.1 Source 1 — mined history commits

Mined from loot-core history (2024-10 → base): commits that add/modify tests
**and** modify or add at least one **function** (non-test code) whose body, in
the commit's version, contains a protected call:

- a db write API call: the generic API (`db.update/insert/insertWithUUID/
  delete_/deleteAll/insertWithSchema/updateWithSchema`) or one of the
  data-specific write functions of `db/index.ts` (`insertTransaction`,
  `updateCategory`, `mergePayees`, …);
- a raw SQL write (`INSERT/UPDATE/DELETE/REPLACE` passed to
  `runQuery/run/execQuery/cache`) on a synced table;
- `amountToInteger(` / `integerToAmount(`;
- a `mutator(` / `undoable(` handler registration.

The criterion is **function-level**: the changed lines must fall inside such a
function. A changed line that merely matches a pattern (line-level) or a
change anywhere in a file that has protected calls (file-level) does not
qualify. The candidate count under this criterion is recorded in the ledger
(the earlier line-level count, 86, is superseded).
Each task = revert the commit's non-test changes on all four variants; the
agent gets a natural-language statement (written from the commit/PR, never
mentioning the abstraction to use); the commit's tests are the hidden tests.

Filters, applied in order and logged:

1. ~~Exclude commits labelled "[AI]" (agent-written PRs).~~ *Amended
   2026-10-06:* "[AI]" commits are kept; `ai_label` (true when "[AI]" is in
   the subject or body) is recorded in `task.json` and copied into every run.
2. Prefer commits from 2026 (contamination).
3. **Memorisation probe:** each model is asked for the solution without the
   repo; if it reproduces the change, the task is dropped.
4. The revert must apply cleanly to A⁺ (the domain layer may need the task's
   code to be expressed through it; if the task cannot be posed fairly on A⁺,
   it is dropped, not adapted).
5. **Solvable with margin:** on A, median ≤ 50 % of the turn/time budget and no
   run hitting the cap (pilot, 3 runs per agent).

### 4.2 Source 2 — open GitHub issues (amendment 2026-10-06)

**Eligible issues.** Open issues of `actualbudget/actual` (snapshot date and
issue state recorded in the ledger) whose natural fix requires **writes to
synced tables and/or money arithmetic in `packages/loot-core`**, i.e. it would
touch the same protected surface as the mined criterion. Excluded: fixes that
are UI-only or outside loot-core, that need dependency or migration changes
(the `touches_deps` analogue), feature requests without a decidable expected
behaviour, and bugs that do not reproduce on base `9732a446`. The triage
decision and its one-line reason are logged per issue.

**Start tree.** The untouched variant of each condition (no revert); the same
agent-config stripping as every other run (§5).

**Statement.** Written from the issue (title, body, discussion), describing
behaviour only; the same leak check and second-reader review as mined
statements.

**Hidden tests.** Written by an **author agent** from the issue, in a session
that never sees a reference solution. They are behavioural: they drive the
code through handlers / the public API and assert on resulting DB state and
returned values; they never name implementation functions, never import or
mention the A⁺ layer (`domain/`, `Cents`, `#server/db/write`), and may read
state only through read APIs that exist identically on all four variants.
They are written against A; on AP/APL they get only the mechanical rewrite of
§6 ("Hidden tests on A⁺"), nothing else. They **must fail on all four
untouched variants**; otherwise the task is dropped (`not_discriminating`).

**References.** Written by an **implementer agent different from the author**
(separate session, sees the statement and the repo, never the hidden tests):

- one reference on **A**, used for A and AL;
- one reference on **AP**, used for AP and APL.

Each reference must pass the hidden tests on both of its conditions with
`lint` and typecheck green there (so the A reference must satisfy the A+L
rules and the AP reference the A⁺+L rules), and the hidden checker must report
0 violations on it (as it does on mined original commits, §11 step 3).

**Adjudication.** When a reference fails, the failing test, the reference and
the statement are read side by side and the failure is classified:
*over-specified test* (asserts something the statement does not require) →
fix the test and re-check both references and the fail-on-untouched rule;
*wrong reference* → fix the reference (implementer agent again). Each
decision, with its reason, is logged in the task's ledger entry. A task that
does not converge after two adjudication rounds is **dropped**, never forced.

**Eligibility rule (decision 2026-10-06, orchestrator, applying the paragraph
"Eligible issues" literally; Javier may override).** Triage judges the *natural*
fix; the rule that counts is applied to the fix actually written. An issue task
is **eligible iff its `reference.A.patch` changes at least one function that
contains a protected call**, decided by the same function-level detector as the
mined criterion (§4.1; `aa.tasks.has_protected_call`): a db write API call
(generic or data-specific write function), a raw SQL write on a synced table,
`amountToInteger`/`integerToAmount`, or a `mutator`/`undoable` registration.
It is computed deterministically (`aa issues eligibility`: the patch is applied
to the committed HEAD of `work/variants/A`, units from the TypeScript compiler)
and recorded as `protected_hits_A`, `protected_units_A` and `eligible` in
`task.json` and the ledger. An ineligible task is dropped with reason
`invariant_not_at_stake`: its fix only changes decision logic (matching, date
windows, budget-template arithmetic without a money helper), so A and A⁺ give the
agent nothing different to respect. Mined tasks keep their own criterion (§4.1).
Result on 2026-10-06: 11 of the 19 sanity-ok issue tasks are eligible (1331,
1827, 3218, 4280, 5012, 5694, 6244, 6738, 8855, 8856, 8857); 8 are dropped
`invariant_not_at_stake` (1062, 1957, 3759, 4805, 8009, 8464, 8494, 8558).
issue-6244's eligibility is recomputed when its blind reference lands.

**Provenance (2026-10-06).** Every issue `task.json` records `author`
(`author-agent:<task>`), `implementer` (`implementer-agent:<task>`) and
`adjudicated_by`, with the workflow session ids. A task whose hidden tests were
edited in adjudication has `tasks/<id>/adjudication.md` (what changed, why, and
the pre-adjudication version as far as it can be reconstructed). The harvest
(26 issues: authored, dropped and why) and the orchestrator's audit of the 20
implementer transcripts are in `tasks/_issues.json`. An implementer found to
have seen the hidden tests is replaced by a blind re-implementation
(issue-6244).

**Statement leak check for issue tasks (2026-10-06).** Besides the mined rules,
a statement must not carry an upstream pointer: `issue NNNN` / `PR NNNN`, the
slug `actualbudget/actual`, or any GitHub URL (`aa tasks check-statements`).

**Shared with mined tasks.** Filters 3 (memorisation probe, scored against
the A reference) and 5 (solvable with margin, pilot) apply unchanged; filter 4
is replaced by the per-condition reference requirement above. `task.json`
records `source: "issue"`, the issue number and URL, the author and
implementer agents/models, and `ai_label: null`.

### 4.3 Selection and reporting

Both sources go through the same pilot and selection rule (plan Task 12); the
target is 15 selected tasks in total, with no fixed quota per source. Every
task carries `source` (`mined` | `issue`) and, for mined tasks, `ai_label`;
both are copied into each `result.json`. Every headline table is reported
pooled **and** split by source, and the mined rows are further split by
`ai_label` (human vs "[AI]" commits); see §6 and §8. Since tasks are mined
and authored after A⁺ is frozen, rule 3.1 holds.

**Amendment 2026-10-06 14:10 BST (margin rule; Javier's decision, recorded
after the Codex pilot and BEFORE the Claude pilot).** The pilot margin rule is
measured in wall time, not turns: a task passes for an agent if it is correct
in ≥2/3 pilot runs, its median wall time is ≤ 12.5 min (50 % of the 25 min
budget), and no run hits either cap (25 min wall, 60 turns). The former
"median turns ≤ 30" clause is dropped because turns are not comparable across
agents: the harness counts every Codex command item as a turn, while Claude
Code reports model turns. Disclosure: under the old clause 4 tasks would have
failed for Codex (median 35, 42, 35, 36 counted turns; max 46, all ≤ 6 min wall),
leaving 9 instead of 13 Codex-passing tasks. Also recorded from the Codex pilot
(60 runs on A): 0 violations of any kind; the probe recorded only base writers.

**Amendment 2026-10-06 ~19:55 (Javier): only 10 tasks pass the pilot for both
agents (`docs/pilot-report.md`); instead of 15 tasks × 4 passes the full run uses
the 10 tasks × 6 passes (60 runs per condition per agent, same planned power).
The pilot showed 0 violations in 120 condition-A runs, so H1 has little room to
show a reduction; a possible increase in A⁺ and H2 remain fully testable.**

**Tie-break when more than 15 tasks pass the pilot (decision 2026-10-06,
recorded before any pilot run; `runs/` holds only the `dummy01` smoke runs).**
Only tasks that pass the pilot rule (plan Task 12 Step 3) for **both** agents
compete. They are ordered by:

1. **alternating sources**, mined / issue, starting with the source that has
   **fewer** survivors (equal counts: mined first); when one source runs out,
   the rest come from the other;
2. **most recent date first within each source** (mined: commit author date;
   issue: issue creation date; equal dates: task id ascending).

The first 15 of that order are selected. Nothing else (pilot scores, invariant,
`ai_label`, contamination flag) enters the order.

## 5. Agents and models

Phase 1 (this spec):

- **Claude Code**, `claude-sonnet-5-5`:
  `claude -p --model claude-sonnet-5-5 --output-format stream-json
  --permission-mode bypassPermissions --max-turns 60`, with a temporary
  `CLAUDE_CONFIG_DIR` (credentials only: no global CLAUDE.md, memory, MCPs,
  skills or hooks).
- **Codex CLI**, `gpt-6-luna`, ChatGPT login (no gateway):
  `codex exec --model gpt-6-luna --json --sandbox workspace-write`, with a
  temporary `CODEX_HOME` holding only `auth.json`; default reasoning effort.

Same prompt for both: task statement + "leave `test` and `lint` green".

**Repo agent config.** The Actual repo ships agent configuration. In every
variant and condition, `.claude/`, `.codex/`, `.agents/` and `.cursor/` are
removed from the tree before the run (they could carry skills, hooks or
instructions that differ by agent). `AGENTS.md` and `CLAUDE.md` stay: they
are part of the codebase as maintainers wrote it, and they are identical
across the four conditions and seen by both agents.
Phase 2 (only if phase 1 shows an effect or a ceiling): Opus 5.5 and
gpt-6.1-sol, same tasks.

## 6. Measures

Per run:

1. **Correct:** hidden tests pass.
2. **Violations (primary constraint outcome):** hidden checker, **stricter than
   and different from the visible lint**, applied identically to all four arms
   (otherwise the +L arms would win by definition):
   - CRDT probe: after the task's tests, every row change in synced tables has
     matching CRDT messages.
   - Money probe: stored amounts are integers; AST check for float arithmetic
     on amount values in the diff.
   - Bypass check: direct SQL writes / `sendMessages` / unwrapped user-facing
     mutations introduced by the diff.
   - **Bad decision = correct AND ≥1 violation**; violation rate is also
     reported over all runs.
   - **`bad_decision_hidden_only` (secondary, pre-registered):** correct AND
     ≥1 violation that neither visible lint set can flag: runtime-probe
     events (`raw_write` whose caller line `no-raw-synced-write` would not
     flag, e.g. dynamic SQL; `non_integer_money`) and the static float
     patterns that are stricter than the lint (`parseFloat(`/`Number(` on an
     amount, `toFixed(` on an amount). Computed identically on all four arms.
     It answers whether the +L arms reduce bad decisions beyond what the
     visible lint literally reports, so an L advantage on `bad_decision` that
     vanishes here reads as "the agent obeyed the lint", not "the agent
     respected the invariant".
3. **Efficiency:** input/output tokens (cached reported separately), turns,
   tool calls, wall time, diff size, and "reimplementation" (diff re-creates
   functionality the available abstraction already provides).
4. **Trace (explanatory, not outcome):** files read, first edit turn, lint
   invocations.
5. **Contamination flag (per task, copied into every run):** `contaminated`
   is true when the task's commit predates the training cutoff of either
   model (cutoffs recorded in config) or its memorisation-probe similarity is
   at least half the drop threshold (≥ 0.25 with the 0.5 drop threshold).
   Flagged tasks are not dropped (filter 2 only prefers 2026 commits); every
   headline table is also reported restricted to unflagged tasks, and a
   result that holds only on flagged tasks is reported as such.
   For issue tasks (amendment 2026-10-06) there is no upstream commit before
   base: `contaminated` is true when an upstream fix for the issue was merged
   (recorded at selection) or the probe similarity against the A reference is
   ≥ 0.25.
   *Amended 2026-10-06 (before any experimental run):* for issue tasks,
   **any public fix PR, merged or not**, sets `contaminated` (an open or
   closed-unmerged PR is as visible to training data and to an agent as a
   merged one). Per issue task, `task.json` records `related_prs` (every PR
   returned by `gh pr list -R actualbudget/actual --search "<issue>" --state
   all`, plus cross-referenced PRs from the issue timeline; raw, may include
   PRs that only mention the number), `public_fix_prs` (the subset that closes
   the issue or proposes a code fix for it) and `public_fix_pr` (true iff
   `public_fix_prs` is non-empty). `related_prs` and `public_fix_prs` feed the
   per-run contamination markers (`aa.agents.task_refs`), next to the issue
   number. On 2026-10-06, `public_fix_pr` is true for 1062, 1957, 3759, 5012,
   6244, 8009, 8464, 8856 and 8857 (4 of the 11 eligible tasks: 5012, 6244,
   8856, 8857); details in `tasks/_issues.json`.
6. **Task source attributes (amendment 2026-10-06, per task, copied into
   every run):** `source` (`mined` | `issue`) and `ai_label` (mined only;
   `null` for issue tasks). Every headline table (rates per condition, the
   contrasts and tokens) is reported pooled, per source, and for mined tasks
   per `ai_label`. Strata are not dropped or reweighted after the fact.

**Two-pass rule: the probe never decides correctness (decision 2026-10-05,
freeze gate).** The runtime probe slows write-heavy property tests (fast-check
in `src/server/aql/schema/executors.test.ts`) past vitest's timeouts: with the
probe on, the full suite showed 2/3/4/4 differences (A/AL/AP/APL, all
timeouts) against 0 without it. So the evaluator runs the hidden tests twice
in the same container: **pass 1, clean** (repo config, default timeouts, no
probe) decides `correct`; **pass 2, probe** (probe + `testTimeout`/`hookTimeout`
raised ×10) only collects runtime violations. If pass 2 errors, times out or
does not finish, the run records `probe_incomplete=true` and keeps the
violations seen so far; `correct` and the static checks are unaffected. The
probe-equivalence check (`aa checker baseline`) compares a probe-on run with
the raised timeouts against the probe-off baseline, and must show 0
differences on all four variants. The probe itself only formats a stack when
it emits an event; the per-write sync-origin check uses raw call sites, and a
write counts as CRDT-engine work only when its issuing frame (nearest frame
outside `db/`, `platform/`, libraries and the probe) is in `sync/`, so a raw
write inside a `batchMessages` callback is still a `raw_write` (third canary
case).

**Fixed fast-check seed in every harness vitest run (decision 2026-10-06,
freeze gate).** Two unseeded fast-check property tests in
`src/server/aql/schema/executors.test.ts` ("queries the correct transactions
with a filter" / "without filters", `numRuns: 300`) failed intermittently
inside the full suite (APL once; the same file passed 3/3 alone and the full
APL rerun passed), which made the freeze gate's equivalence checks flaky. Every
vitest run the harness makes therefore adds one extra setup file,
`substrate/checker/seed.setup.ts` (copied in as `src/mocks/aa-seed.setup.ts`
through the wrapper config `vitest.aa-seed.config.ts`, because vitest 5 has no
`--setupFiles` flag), which calls `fc.configureGlobal({...fc.readConfigureGlobal(),
seed: 20261006})`: suite baselines (`aa suite baseline`), hence the equivalence
checks, `aa checker baseline` probe-off and probe-on (the probe config
`vitest.aa.config.ts` extends the seeded one), both evaluation passes and the
task sanity check. It is identical on the four conditions, is not part of any
variant patch, and is never in an agent's start tree (copied in after lint and
typecheck, like the probe). Every fast-check property then draws the same inputs
on every run and condition; per-call parameters still win, and no loot-core test
sets its own seed. Host vitest runs that fail (non-zero exit, host timeout, no
report, any failed test) keep their JSON report, stdout and stderr (and probe
events) under `work/logs/<label>-<timestamp>/`; in the evaluator they already live
in the run's `eval/` dir.
Result (Node 24.18.1, run twice in a row): suite baselines A/AL 1227 passed,
AP/APL 1231 passed, 0 failed, 2 skipped; `aa equivalence` A-AP, A-AL, AP-APL
→ 0 differences; `aa checker baseline --conds A,AL,AP,APL` → 0 differences
probe-on vs probe-off on all four, canary 3/3, 0 `non_integer_money`, 17 raw
writers (unchanged). Both runs produced byte-identical pass/fail sets
(`work/baseline-<cond>.json`, `work/probe-baseline-<cond>.json`) and an
identical `baseline-writers.json`.

**Hidden tests on A⁺ (decision 2026-10-05).** On AP and APL the hidden
tests get the same mechanical rewrite that `aplus.patch` applied to Actual's
own tests (`docs/a-plus-design.md` §5 item 10, §8 item 5), and nothing else:
(1) imports of a moved write function from `#server/db` are repointed to
`#server/db/write`; (2) a `vi.mock('#server/db')` that targets moved functions
also mocks `#server/db/write`; (3) `vi.hoisted(() => vi.resetModules())` is
added when the test mocks writes that the code under test reaches through the
domain layer. No assertion changes. **Control:** the original commit's
solution must pass the rewritten hidden tests in all four conditions; if it
fails in any one, the task is dropped for **all** conditions, never adapted.

Run status: `ok` / `timeout` (25 min wall or 60 turns → counts as failure,
flagged) / `infra` (429, usage limit, crash → retried with backoff, never
counted as agent failure).

## 7. Pre-registered hypotheses

- **H1 (constraint):** violations A > A⁺ and A > A+L; A⁺+L lowest.
- **H2 (efficiency):** A⁺ uses fewer tokens than A on solved tasks.
- **H3 (interaction, the tweet's claim):** lint helps more on A⁺ than on A
  ("don't bypass X" is easier to obey than "respect the invariant").
- **Rival (from agent-code-practices):** what helps is the *legibility of
  named intent*, not constraint → A⁺ ≈ A⁺+L, and any gain is A → A⁺.
- **Pre-registered null reading:** if A shows few violations because agents
  copy the surrounding pattern, H1 is flat and that is a result ("habitual
  coherent code already constrains"), not a design failure.

## 8. Power and analysis

~60 runs per condition per agent (15 tasks × 4 passes) → 240 per agent, 480
total. With 60 vs 60, drops of roughly 20+ points in a rate are detectable;
smaller ones are reported as "not detectable", never as "no effect".
Tests: Fisher exact on rates per contrast, mixed-effects logistic regression
(task random effect) for the 2×2 interaction; tokens via Mann-Whitney on solved
runs and a log-linear model with task effect. Wilson intervals throughout.
All tables are generated from `result.json` files by script, never typed.

**Task source (amendment 2026-10-06).** The mixed-effects logistic and the
log-linear token model include task source (`mined` / `issue`) as a fixed
covariate next to the task random effect; the pooled estimates are the
headline. Each contrast is also reported **per source** (and, for mined tasks,
per `ai_label`) with Wilson intervals and Fisher p. A condition × source
interaction is fitted and reported as exploratory: with ~15 tasks split two
ways, per-source contrasts are underpowered, so a per-source difference is
reported as "not detectable" unless it clears the same bar as the pooled
test, and a pooled result that holds in only one source is reported as such.

## 9. Execution

Laptop only (GCP is off-limits). Each run: fresh copy of the variant in a temp
dir, new single-commit `.git` (no history to mine), inside a Docker container
with `node_modules` pre-installed; only the affected test files run during
evaluation. Concurrency ~3 runs per agent, raised if quotas allow.

Estimate (phase 1): 480 runs × 5–15 min → ~15–25 h wall per agent at 3
parallel. Marginal cost ≈ 0 (subscriptions) but consumes Claude and ChatGPT
quota; API-equivalent reference ~$0.5–1.5 per Sonnet run (~$150–350). A fresh
estimate is given before each batch, including the pilot.

## 10. Visibility

- `runs/<agent>/<condition>/<task>/<pass>/`: `transcript.jsonl` (raw stream),
  `diff.patch`, `tests.log`, `lint.log`, `checker.log`, `result.json`.
- Per-run HTML viewer: readable conversation (thinking, commands, reads,
  edits), final diff next to the original solution, violations highlighted.
- Live `status.html` regenerated after each run: progress per agent ×
  condition, rates with Wilson CIs, mean tokens, latest failures linked to their
  viewer, `infra` retry counter. Optionally published as a private Artifact.
- Monitoring during runs: if a condition drops to 0 % or `infra` spikes, stop
  and read traces before explaining anything.

## 11. Build order

1. Variant generator: A⁺ domain layer (+ design doc), lint rule sets; freeze.
2. Equivalence check: full suite on A and A⁺.
3. Hidden checker, validated on the original commits (must report 0
   violations) and on hand-made bad solutions (must catch them).
4. Task miner + filters + memorisation probe; issue tasks (§4.2,
   amendment 2026-10-06).
5. Runner (Claude Code, Codex), isolation, retries; viewer and status page.
6. Pilot (3 runs per agent on A) → task selection → estimate → full run.

## 12. Later (not this phase)

- Replication on Excalidraw (`mutateElement` must bump
  `version`/`versionNonce`), only after phase 1 is closed.
- Phase 2 models (Opus 5.5, gpt-6.1-sol).
- Claim 3: unwinding a bad abstraction.

### Amendment 2026-10-07 — hard-task arm (Javier)

Phase 1 (docs/results-phase1.md) used the 10 tasks that passed the pilot's
margin rule, which by construction removes the tasks where agents struggle —
exactly where shortcuts might appear. Decided after phase 1 and before running
it: a second arm runs the **10 eligible tasks that failed the margin rule** (041f9f3b6e, 35e04473aa, 9788bb123a, df4dc0d6cc, f78a6fa041, issue-3218, issue-5012, issue-5694, issue-8855, issue-8857)
on the same frozen A⁺, lint sets, checker, prompt, effort (medium) and models,
10 tasks × 6 passes × 4 conditions × 2 agents, in `runs-hard/`. Analysed and
reported separately from phase 1 (not pooled). Timeouts count as not correct,
as in phase 1. The pilot already showed 0 violations in condition A on these
tasks (60 runs per agent); this arm tests whether A⁺ / lint change that under
pressure, and H2 on harder tasks.
