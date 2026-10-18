# Repetition vs abstraction, over task chains — design spec (study 2)

**Date:** 2026-10-08 · **Status:** draft, pending review; amended 2026-10-08 (see end) · **Owner:** Javier Aguilar
**Predecessor:** `2026-10-05-agent-abstractions-design.md` (study 1: "more layers on
already-abstracted code"; result: null on invariant violations, efficiency and blind
design review — see `docs/results-*.md`).

## 1. Why a second study

Study 1 tested an extra domain layer (A⁺) on top of a codebase that already had its
high-leverage helpers. Its "bad decision" metric (bypassing an invariant-protecting
abstraction) sat at 0 % in every condition, and a blind design review found no
difference either. Two things it did **not** test (Javier, 2026-10-08):

1. **Abstraction vs repetition.** The core of the original claim: high-leverage
   abstractions let the agent "do more with less code" and constrain it, versus the
   same logic copied in N places, as in many real repositories.
2. **Maintainability over time.** One task cannot show whether code degrades,
   duplication accumulates, or later changes get more expensive.

This study tests both, on one treatment, measured over chains of dependent tasks.
A third question — the agent as abstraction *designer* — is a later, separate study.

## 2. Substrate and treatment

Actual Budget, `packages/loot-core`, base `9732a446` (same harness, images, isolation,
evaluator and checker infrastructure as study 1). Four **zones**: domain logic that
appears in several places (paths relative to `packages/loot-core/src`):

| Zone | Logic | Copies | Where (base) | R origin |
|---|---|---|---|---|
| Z1 | Which categories a bulk budget action touches (visible-categories query, income-category rule, sign inversion) | 5 | `server/budget/actions.ts` `copyPreviousMonth`, `setZero`, `set3MonthAvg`, `set6MonthAvg`, `set12MonthAvg` | natural |
| Z2 | Scheduled amount of a ranged (`isbetween`) schedule | 4 server sites + 1 hand copy | helper `shared/schedules.ts` `getScheduledAmount`; callers `server/forecast/forecast-schedules.ts`, `server/schedules/app.ts` (×2), `shared/schedules.ts`; hand copy `server/budget/schedule-template.ts` | **artificial**: helper inlined at its server call sites |
| Z3 | Linking a bank-sync provider account (upgrade vs insert, transfer payee, initial sync, sync event) | 5 | `server/accounts/app.ts` `link{GoCardless,SimpleFin,PluggyAi,Akahu,EnableBanking}Account` | natural |
| Z4 | Weekend adjustment of schedule dates | 4 | `shared/schedules.ts`, `server/schedules/app.ts`, `server/budget/schedule-template.ts` (×2) | natural |

**Conditions (2):**
- **R — repeated:** zones as they are in base (Z2: the helper inlined at its server
  call sites, declared as the only artificial repetition).
- **F — factored:** each zone's copies replaced by one high-leverage helper.

No lint factor (flat in study 1). **Existing inconsistencies are preserved in F** (e.g.
`setZero` does not skip hidden categories; the hand copy in Z2 rounds differently;
only PluggyAI sends `X-Actual-File-Id`; Z4 reads `weekendSolve` vs `weekendSolveMode`)
through explicit helper parameters, so behaviour is identical and the treatment changes
only the *shape* of the code.

**Integrity (anti straw-man), as in study 1:**
1. R and F are built and **frozen (tag `rf-frozen`) before any task is written**.
2. The full loot-core suite gives identical pass/fail sets on R and F (seeded fast-check);
   typecheck 0 errors on both.
3. The R/F diff is published. F's helpers are what a competent maintainer would extract
   (reviewed by an independent agent before freezing: "is this a reasonable refactor or
   a straw man in either direction?").
4. The repo's own agent config is stripped as in study 1; AGENTS.md/CLAUDE.md stay.

## 3. Tasks and chains

**Chains:** one chain of 4 dependent tasks per zone, invented (no upstream solution →
no memorisation), written from the domain, never from the code:

| Step | Kind | Example (Z1) |
|---|---|---|
| T1 | change the rule (must reach every copy) | bulk actions skip hidden categories and categories with a goal template |
| T2 | add a new consumer of the logic | new bulk action "set to last month's spending" |
| T3 | extend the rule | …and also skip categories in groups marked "fixed" |
| T4 | a change that builds on the previous ones | per-action override to include hidden categories |

**Statements** describe behaviour only and **never mention how many places implement
the logic or where** (that is what is measured). Leak check as in study 1 (no file
paths, function names, copy counts).

**Hidden tests:**
- **Per consumer:** for each step, one behavioural test per site where the change must
  land (through the public handlers; only the network boundary — `post` to the sync
  server / bank providers — is mocked, nothing internal), so coverage is measurable as
  "k of N consumers updated".
- **Cumulative:** at step k the evaluator also runs steps 1..k-1's tests on the agent's
  tree → **carried defects**.
- Must fail on untouched R and F; must not import or name the F helpers or the R copies.

**References:** an implementer agent (separate from the test author, statement only, no
access to hidden tests — enforced by not mounting them, and audited in its transcript)
writes a reference chain on R and on F; each step's reference must pass that step's and
all previous steps' hidden tests on its version. Adjudication as in study 1 (≤2 rounds,
else drop the step and its chain).

**Chain execution:** step k starts from the tree the same agent left at step k-1 in the
same chain (agent's diff applied, not the reference). A broken step does not stop the
chain; carried defects are part of the outcome. Each step is a fresh agent session (no
memory between steps) — the code is the only carrier, as in a real team.

## 4. Agents

Unchanged from study 1 (final configuration): Claude Code `claude-sonnet-5-5` and Codex
`gpt-6-luna`, both `effort=medium`, no web tools, GitHub/npm hosts blocked, isolated
config, same prompt template ("leave `test` and `lint` green"; `lint` = typecheck in both
conditions), 25 min / 60 turns per step.

## 5. Measures

Per step:
1. **Correct:** the step's hidden tests all pass.
2. **Consumer coverage (primary on rule steps T1, T3):** k/N consumers whose tests pass;
   **missed copy** = at least one consumer updated and at least one not (the
   high-level bad decision); zero consumers updated is simply *incorrect*, not a missed copy.
   On T2 the analogous measure is whether the new consumer reuses the logic (F: calls the
   helper; R: copies or calls an existing copy) and whether it matches the rule.
3. **Carried defects:** previous steps' hidden tests failing on this step's tree.
4. **Efficiency:** lines added/removed, tokens (cached separately), turns, tool calls, wall.
5. **Design review:** the pre-registered rubric of `docs/design-review-rubric.md`, on the
   step's diff against its exact pre-image (`git apply --check` verified).

Per chain (after T4):
6. **Duplication:** jscpd clones in the zone's files (count and duplicated lines), compared
   with the start of the chain.
7. **Zone design review:** the same rubric on the cumulative diff of the chain.
8. **Cost growth:** tokens of T4 relative to T1 within the chain.

## 6. Pre-registered hypotheses

- **H1 (constraint):** missed-copy rate on T1/T3 is higher in R than in F.
- **H2 (efficiency):** F needs fewer added lines and fewer tokens per step.
- **H3 (maintainability):** in R, duplication grows along the chain and carried defects
  accumulate; in F they do not (condition × step interaction).
- **H4 (design):** design-review maintainability is higher in F.
- **Rival:** agents grep for every copy, so R ≈ F on coverage; any F advantage shows only
  in tokens/lines.
- **Null reading pre-registered:** if R's missed-copy rate is ~0, the result is "agents
  find copies reliably at N≈5", not a design failure.

## 7. Size, power, analysis

- 4 zones × 2 conditions × 8 chains × 4 steps = **256 runs per agent, 512 total**.
- Primary: missed copy on T1+T3 → 4 × 8 × 2 = 64 observations per condition per agent,
  clustered by chain; detects ≈25-point differences. If the pilot shows base rates in
  20–80 %, chains go to 10 per zone (amendment recorded before the full run).
- Analysis: mixed-effects logistic (zone and chain random effects) for missed copy;
  log-linear / Mann-Whitney + per-zone sign tests for lines and tokens; condition × step
  interaction for duplication and carried defects; rubric scores as in study 1.
  Detectable differences reported; nothing near p = 0.05 read as an effect on its own.
- Tables generated by script from result files.

## 8. Pilot

1 chain per zone × condition × agent (32 steps per agent), condition-agnostic checks:
every step solvable at least sometimes, consumer tests discriminate, chains run end to
end. Then the estimate for the full run (time per agent, quota) before launching.

## 9. Execution, visibility, cost

Laptop only. Chains run in parallel, steps within a chain in series; concurrency 2
(Codex) + 3 (Claude). Estimate: Codex ≈ 5 h, Claude ≈ 12 h; subscription quota only.
Per-run artefacts, viewer and status page as in study 1, plus a per-chain view (the 4
steps and the cumulative diff).

## 10. Build order

1. R/F variants for the 4 zones + independent refactor review + equivalence → freeze `rf-frozen`.
2. Chain tasks: statements, per-consumer hidden tests, references (author/implementer
   separation, audit), sanity on R and F.
3. Harness: chain runner (state carried between steps), cumulative evaluation, coverage,
   jscpd, per-chain viewer.
4. Pilot → estimate → full run → analysis.

## 11. Later

Study 3 — the agent as abstraction designer (tasks whose good solution requires creating
an abstraction; follow-up tasks that reuse it; unwinding a bad abstraction).

## Amendment 2026-10-08 (before any pilot run)

Recorded before any pilot or full run; no agent has run a study task. R and F stay
frozen (`rf-frozen`); hidden tests are unchanged. Each item says what changes against
the sections above and why.

1. **Primary measure: `missed_copy_preexisting`** (replaces "missed copy" as primary in
   §5.2 and H1). On rule steps (T1, T3) it is computed only over the consumers that
   existed at T1 (the zone's original copies, `chain.json` T1 consumers). The consumer
   added at T2 is measured separately (`missed_copy_t2_consumer`: on T3/T4, whether the
   rule reached the T2-added consumer), because whether that consumer is a copy, a
   call to an existing copy or a call to the helper depends on what the same agent did
   at T2, so it is an outcome of the chain, not a fixed copy of the treatment.
   The all-consumer missed copy of §5.2 is still reported, as secondary.
2. **Z4 is a weak contrast, pre-registered as such and reported per zone.** In F,
   `applyWeekendRule` factors the weekend adjustment, but its callers still compute
   dates their own way and each needs an edit for a rule change such as T1 (skip
   weekend days for daily schedules) or T3 (holidays). R and F therefore differ less in
   Z4 than in Z1-Z3. Z4 stays in the pooled analysis; every primary and secondary
   result is also reported per zone, and a pooled effect carried only by Z1-Z3 (or
   absent only in Z4) is read in that light, not as a contradiction.
3. **Z2 preview tests: declared deviation from §3 "through the public handlers".**
   No server handler exposes the schedule preview, so the Z2 `preview` consumer tests
   call `computeSchedulePreviewTransactions` directly. It is the only consumer test
   that does not go through a handler; it is the same function name on R and F (not a
   helper introduced by F), so it does not favour either condition.
4. **T2 correctness also reported conditional on T1 correct.** T2 builds on T1's rule,
   so a T2 failure can be inherited. Besides unconditional T2 correctness, the tables
   report T2 correctness over the chains whose T1 was correct (with n).
5. **Statements de-hinted.** The statements as first written told the agent to search
   exhaustively ("everywhere", "wherever the app works out a schedule's dates",
   "nothing in Actual that ... may still", "for every one of these actions") and some
   enumerated the consumer families (Z1/T1 and Z1/T2 named the copy / zero / average
   bulk actions). That hints at the very thing H1 measures. Every `tasks2/*/T*/statement.md`
   was rewritten to state the behaviour once, for the concept, as a maintainer would
   ("month-wide budget actions leave ... untouched"; "the amount a ranged schedule is
   expected to post is ..."), with the behaviour still fully specified (where a T2
   statement relied on "as Actual does everywhere else", the rule is now stated
   explicitly). The study-2 leak check (`aa chain check-statements`,
   `aa.chains.statement_leaks2`) now flags, besides the study-1 rules, exhaustive-search
   phrases and any statement naming two or more of the zone's pre-existing consumer
   families; all 16 statements are clean.
6. **References regenerated blind, all zones.** An orchestrator audit of the
   implementer transcripts (2026-10-08) found that all four implementers read author
   material (`chain.json`, `provenance.json`), which lists the consumers and the zone
   files, so the references were not written from the statement only (§3). The
   references of every zone are regenerated by fresh implementers that see only the
   de-hinted statements and the variant tree (no `tasks2/` author files, no hidden
   tests), audited in their transcripts, and the sanity and adjudication of §3 are
   rerun on them.
7. **Refactor review redone.** The R/F refactor review (§2, integrity 3) is redone by
   an independent agent that did not take part in building R or F or in the first
   review; F is not changed unless that review finds a straw man, in which case the
   freeze is reopened and the amendment says so before any pilot run.
8. **Z4: the budget-template consumer is merged into next-date** (added 2026-10-08,
   before any pilot run; from a review of the blind references). The schedule template
   walks a schedule's occurrences with `getNextDate(..., true)`, so it is not
   independent of the next-date site: the blind T1 reference on R changes `getNextDate`
   (and `rule-utils.ts`, `schedules/app.ts`) and the budget-template test passes with the
   template's own two copies untouched. A separate budget-template consumer would then
   credit a tree with "updating" the template through the next-date edit alone, so the
   two would not be separate copies of the rule. So, for coverage, the template's test now belongs to the `next-date`
   consumer at T1, T3 and T4 (`consumers.json`; `chain.json` steps and
   `consumer_sites.next-date`, whose earlier note claiming independence is corrected).
   T4 is merged too, so the T1-listed consumers stay the pre-existing ones there and the
   template is not taken for the consumer added at T2. Z4 has **2 pre-existing
   consumers** (next-date, upcoming-dates); `next-date` counts as updated only when both
   its own test and the template test pass. No test, statement or reference changes.
   The Z4 mutant check was re-run against the blind references
   (`tasks2/Z4/mutant_check.json`): with the full T1 reference both tests pass; with
   `getNextDate`'s change reverted the merged consumer is not updated (R and F); on R,
   with the template's copies updated on their own but `getNextDate` not, the template
   test passes and the next-date test fails, so the merged consumer is still not
   updated; on F, reverting the template's own change leaves the template test passing. Z4 remains a weak contrast (item 2); with 2
   pre-existing consumers its missed copy means "exactly one of the two updated".
9. **Provenance records cleaned up** (added 2026-10-08, before any pilot run). In every
   `tasks2/*/provenance.json` the blocks that described the superseded implementer and
   its references (`implementation` in Z1, Z3, Z4; `references` in Z2) are moved under
   `references_superseded`, so the top level describes only the blind references; each
   file gains `implementer_audit` pointing to the orchestrator's transcript audit
   (`docs/audits/2026-10-08-blind-implementers.md`, clean).
10. **Doc-comment confound tagged per step** (added 2026-10-08, before any pilot run;
    from `docs/study2-refactor-review-independent.md`, recommendation 1). Some of F's
    doc comments state an inconsistency between copies, not only the rule: Z1 (the
    average actions skip a category whose group row is missing, copy does not), Z2
    (the template's rounding of a range and why it is harmless), Z4 (`weekendSolve` vs
    `weekendSolveMode`). Each step in `chain.json` carries
    `depends_on_f_comment_fact: true/false`: true when the step's hidden tests depend on
    a fact stated only in F's comments, decided by reading the hidden tests (the basis is
    recorded in each zone's `f_comment_fact`). Result: Z1 all false (every test category
    has an existing group); Z2 all false (from T1 on no tested value is a range midpoint,
    so neither rounding mode is exercised); Z3 all false (its comment facts, PluggyAI's
    `fileId` and Akahu's tables, are visible at the R copies, and no assertion depends on
    `fileId`); Z4 T1 false (daily weekend days are dropped "whichever direction"), T2, T3
    and T4 true (new code must move dates in the configured direction, and the tests
    assert both directions). The evaluator copies the tag into each `result.json`;
    `aa tables2` reports missed copy (primary) and correctness by condition for
    `depends` and `independent` steps (`f_comment_fact_split`). An F advantage
    confined to `depends` is read as at least partly a documentation effect, and the
    write-up then describes the treatment as "factored + documented helpers".
    Rule steps tagged true are only Z4 T3, so this split is a check, not a test.
11. **Denominators of the missed-copy rate** (added 2026-10-08, before any pilot run;
    as implemented in `src/aa/tables2.py`). The missed-copy rate (primary, item 1) is
    k / n over the **counted rule steps** (T1, T3) of the condition, where counted means
    status not `setup_error`, `harness_error` or `infra*`, and no `eval_error` (the
    excluded steps are reported by reason). A step is a missed copy when at least one
    and not all of its pre-existing consumers are updated.
    - **Timeouts** stay in the denominator: a timed-out step is evaluated on the tree
      the agent left, and is a missed copy or not on that tree like any other step (it
      is never correct).
    - **Zero consumers updated** stays in the denominator as *not* a missed copy (it is
      incorrect, §5.2), so the rate is per counted rule step, not per partially
      updated step.
    - **Sensitivity:** `aa tables2` repeats the missed-copy rate (T1+T3 and per step) and
      correctness per step with the timed-out steps removed
      (`sensitivity_excluding_timeouts`, with the number dropped per condition). A
      primary result that does not hold there is reported as dependent on timeouts.
12. **Third agent: Haiku 5.5** (2026-10-08). Haiku 5.5 (Claude Code, effort medium) added
    as a third agent, decided BEFORE any pilot result was inspected (the pilot was
    running, no step evaluated); motivation: a weaker model gives H1 room above the
    floor; same tasks, same pilot rule; size +256 runs. Agent `haiku` = Claude Code CLI
    with model `claude-haiku-5-5`, identical to `claude` in every other respect (CLI
    flags, no web, `--effort medium`, token, parsers, contamination detection,
    transcripts); runs under `runs2*/haiku/`, reported as its own agent by `aa tables2`
    (§4, §7: 768 runs in total).
