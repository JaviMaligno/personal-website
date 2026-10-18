# Z2 adjudication (plan Task 2)

## Blind references (spec amendment 6), 2026-10-08

**Adjudicator:** orchestration audit agent. It wrote neither the tests nor any reference.
**References:** `implementer-agent-blind:Z2`. **Verdict:** all 4 steps kept; the chain is kept.
**Rounds used:** 0 of 1 (nothing to adjudicate). No test, statement or chain.json was changed.

**Why regenerated.** The first implementer read `chain.json` and `provenance.json` (self-reported). That material lists the consumers and
the zone files, so its references were not written from the statement only (spec section 3).
Those references are replaced. The old patches stay in git history, and their sha256 prefixes
are in `provenance.json` (`references_blind.patch_sha256_16_old_to_new`).

**Independence audit.** The auditor could not read the blind implementer's transcript; the
orchestrator audits it. Checks on the implementer's work dir (outside the repo):
- The statements are byte-identical to `afb4d8e:tasks2/Z2/T*/statement.md`, which is unchanged at HEAD.
- The R and F baselines are identical to the frozen variant trees.
- Each tree's history is the baseline plus 4 step commits, and no commit adds a test file.
- No file in the work dir has a hidden-test file name, and none mentions `tasks2`, `hidden/`,
  `consumers.json` or the adjudication.
- None of the hidden tests' describe/it titles appears in the patches, the scratch files or the statements.
- Hidden-test lines (minus upstream test lines) overlap with no added patch line.
- Each installed patch equals that step's commit diff in the implementer's tree.
- Hidden-test content scan of the patches (`chains.reference_leaks`, run in `aa chain sanity`):
  no hidden or test files, no test names. The only literal flagged is `#shared/schedules` at T2, which is the repo's module alias in an import line.

**Checks run.** `aa chain sanity Z1 Z2 Z3 Z4 --workers 1` was run with one container at a
time. It is the same method as before: (1) each consumer test runs alone on untouched
`aa-actual:R`/`F` and must be the only test that ran and must fail; (2) `reference.<cond>.patch`
T1→T4 are applied cumulatively, with `yarn lint`, `yarn tsgo -b` and the seeded hidden tests of
steps 1..k after each step. Output: `sanity_check.json`.

| Step | Kind | Consumers (N) | Consumer tests | Untouched R/F fail individually | Blind reference R/F cumulative + lint/typecheck |
|---|---|---|---|---|---|
| T1 | rule | 5 | 15 | pass | pass |
| T2 | consumer | 1 | 4 | pass | pass |
| T3 | rule | 6 | 18 | pass | pass |
| T4 | build | 6 | 24 | pass | pass (12 earlier tests superseded, as declared in chain.json) |

---

## Earlier adjudication (first references, now replaced)

**Date:** 2026-10-08 · **Adjudicator:** adjudicator agent. It authored neither the tests nor the references.
**Verdict:** all 4 steps kept; the chain is kept. **Rounds used:** 1 of 2.

## Checks run

Command: `aa chain sanity Z2` (`src/aa/chains.py:sanity`). The machine-readable output
is `tasks2/Z2/sanity_check.json` (round-2 run). The method is the same as for Z1, Z3 and
Z4:

1. **Untouched trees:** each consumers.json test run alone on untouched `aa-actual:R`/`F`.
   It must be the only test that ran, and it must fail.
2. **References:** `reference.<cond>.patch` T1→T4 applied cumulatively to the untouched
   variant. After each step: `yarn lint`, `yarn tsgo -b`, then the seeded hidden tests of
   steps 1..k.
3. **Implementer audit (substitute):** the implementer transcript was not available, so
   the reference patches were scanned for hidden-test content instead (files, test
   names, literals). Result: none. The references touch `shared/schedules.ts`,
   `server/forecast/forecast-schedules.ts`, `server/schedules/app.ts`,
   `server/budget/schedule-template.ts`, `server/api.ts` and `server/api-models.ts`, plus
   a comment-only edit in `desktop-client/.../accounts/Balance.tsx`. The only literal
   match is `#shared/schedules`, the repo's module alias in an import line.

## Round 1: finding

Untouched check: passed on R and F. References: T1, T2 and T3 passed on both
conditions. **T4 failed on both conditions**, with the same 12 earlier-step tests failing
and all 6 of T4's own consumers passing:

- the 5 T1 tests "a ranged income is expected at the end furthest from zero"
  (forecast, preview, post-transaction, rule-action-sync, budget-template);
- the 6 T3 tests "an approximate income is expected at the end of its tolerance
  furthest from zero" (the same five consumers plus api-schedule-list);
- the single T2 test "ranged schedules report the amount they are expected to post",
  which asserted an expense and an income in one test.

## Round 1: decision

**The reference is right and the earlier tests are right for their own steps. The
chain contradicts itself by design.** The T4 statement ("Worst case means the least
money in") deliberately changes the T1/T3 rule for money coming in: the expected amount
becomes the end closest to zero instead of the end furthest from zero. A tree that
implements T4 correctly *must* fail those income assertions. Counting them as carried
defects would charge every correct agent 12 defects at T4, and the cumulative-reference
requirement could never hold. Neither "wrong reference" nor "drop" fits: the step is a
legitimate requirement change, which is exactly the kind of change a maintenance chain
should contain.

Fix (behaviour-level, condition-neutral):

1. **Supersession, declared in the chain.** `chain.json` step T4 now carries
   `supersedes: {T1: [5 income tests], T2: [1 income test], T3: [6 income tests]}`
   (plus `supersedes_reason`). From the superseding step on, the evaluator
   (`chain_eval.step_outcome(..., ignore=)`, via `Chain.superseded`) leaves those tests
   out of carried defects and out of the earlier step's carried correctness. If every
   test of a consumer is superseded, that consumer is left out too. Each step's own
   correctness and coverage are unchanged, and so are T2's and T3's carried defects.
   Only from T4 on do the superseded tests stop counting. `result.json` records
   `superseded_tests` per earlier step. The loader rejects a `supersedes` entry that
   names a non-earlier step or a test that does not exist. Tests:
   `tests/test_chain_eval.py::test_superseded_tests_are_not_carried_defects` and
   `::test_supersedes_must_name_earlier_tests`.
2. **T2 test split (the over-specified test).** The mixed test was split into
   "a ranged expense reports the amount it is expected to post" and "a ranged income
   reports the amount it is expected to post". The assertions are unchanged; each test
   now creates one schedule. Only the income half is superseded at T4, so the expense
   half keeps being a carried check of T2 at T4. `T2/consumers.json` was updated (T2 now
   has 4 tests, all for consumer `api-schedule-list`).

No statement and no reference patch was changed.

## Round 2: result

Untouched: every consumer test, including the two new T2 tests, fails individually on R
and on F. References: every step passes on R and on F, cumulatively, with lint and
typecheck green. At T4 the 12 superseded tests are excluded and every other T1–T3 test
passes.

## Per step (after adjudication)

| Step | Kind | Consumers (N) | Consumer tests | Untouched R/F fail individually | Reference R/F cumulative + lint/typecheck |
|---|---|---|---|---|---|
| T1 | rule | 5 | 15 | pass | pass |
| T2 | consumer | 1 | 4 | pass | pass |
| T3 | rule | 6 | 18 | pass | pass |
| T4 | build | 6 | 24 | pass | pass (12 earlier tests superseded) |

## Notes

- The author's `sanity.json` predates the T2 split, so it lists the old T2 test name.
  `sanity_check.json` is the current record.
- Analyses of carried defects at T4 in Z2 should report the supersession, because the
  income half of the earlier rule is intentionally no longer carried.
