# Z1 adjudication (plan Task 2)

## Blind references (spec amendment 6), 2026-10-08

**Adjudicator:** orchestration audit agent. It wrote neither the tests nor any reference.
**References:** `implementer-agent-blind:Z1`. **Verdict:** all 4 steps kept; the chain is kept.
**Rounds used:** 0 of 1 (nothing to adjudicate). No test, statement or chain.json was changed.

**Why regenerated.** The first implementer read `chain.json` and `provenance.json` before implementing (self-reported), and listed the top level of the test author's scratch dir (file names only). That material lists the consumers and
the zone files, so its references were not written from the statement only (spec section 3).
Those references are replaced. The old patches stay in git history, and their sha256 prefixes
are in `provenance.json` (`references_blind.patch_sha256_16_old_to_new`).

**Independence audit.** The auditor could not read the blind implementer's transcript; the
orchestrator audits it. Checks on the implementer's work dir (outside the repo):
- The statements are byte-identical to `afb4d8e:tasks2/Z1/T*/statement.md`, which is unchanged at HEAD.
- The R and F baselines are identical to the frozen variant trees.
- Each tree's history is the baseline plus 4 step commits, and no commit adds a test file.
- No file in the work dir has a hidden-test file name, and none mentions `tasks2`, `hidden/`,
  `consumers.json` or the adjudication.
- None of the hidden tests' describe/it titles appears in the patches, the scratch files or the statements.
- Hidden-test lines (minus upstream test lines) overlap with no added patch line.
- Each installed patch equals that step's commit diff in the implementer's tree.
- Hidden-test content scan of the patches (`chains.reference_leaks`, run in `aa chain sanity`):
  no hidden or test files, no test names.

**Checks run.** `aa chain sanity Z1 Z2 Z3 Z4 --workers 1` was run with one container at a
time. It is the same method as before: (1) each consumer test runs alone on untouched
`aa-actual:R`/`F` and must be the only test that ran and must fail; (2) `reference.<cond>.patch`
T1→T4 are applied cumulatively, with `yarn lint`, `yarn tsgo -b` and the seeded hidden tests of
steps 1..k after each step. Output: `sanity_check.json`.

| Step | Kind | Consumers (N) | Consumer tests | Untouched R/F fail individually | Blind reference R/F cumulative + lint/typecheck |
|---|---|---|---|---|---|
| T1 | rule | 5 | 5 | pass | pass |
| T2 | consumer | 1 | 3 | pass | pass |
| T3 | rule | 6 | 6 | pass | pass |
| T4 | build | 6 | 6 | pass | pass |

---

## Earlier adjudication (first references, now replaced)

**Date:** 2026-10-08 · **Adjudicator:** adjudicator agent. It authored neither the tests nor the references.
**Verdict:** all 4 steps kept; the chain is kept. **Rounds used:** 0 of 2 (nothing to adjudicate).

## Checks run

Command: `aa chain sanity Z1` (`src/aa/chains.py:sanity`). The machine-readable
output is `tasks2/Z1/sanity_check.json`.

1. **Untouched trees (Review Focus 3).** Each `consumers.json` test was run alone
   (one seeded vitest process, `-t` anchored to that test) on untouched `aa-actual:R`
   and `aa-actual:F` (network off), with every hidden test of the chain staged. Each test
   passes the check only if it is the only test that ran and it failed. Result: **every
   consumer test of every step fails individually on R and on F.**
2. **References, applied cumulatively.** In one container per condition, applied in
   order to the untouched variant: `reference.<cond>.patch` for T1, T2, T3, then T4.
   After each step the check ran `yarn lint`, then `yarn tsgo -b` on the tree as patched,
   then the hidden tests of steps 1..k (seeded, clean; the evaluator's test-status
   logic). Result: **every step passes on R and on F.** Each step's own tests and every
   earlier step's tests pass, with lint and typecheck green.
3. **Implementer audit (substitute).** The implementer transcript was not available to
   the adjudicator, so the check looked instead for hidden-test content in the reference
   patches (`chains.reference_leaks`): files under hidden paths or test files,
   consumers.json test names, and string literals of 12 or more characters from the
   hidden tests on added lines that are neither in the public statements nor already in
   the touched variant files. Result: none. Every reference patch (R and F, T1-T4) touches only `packages/loot-core/src/server/budget/actions.ts`, plus `server/budget/app.ts` at T2. No test file, no hidden path, no consumers.json test name, and no hidden-test string literal of 12 or more characters on an added line.

## Per step

| Step | Kind | Consumers (N) | Consumer tests | Untouched R/F fail individually | Reference R/F cumulative + lint/typecheck |
|---|---|---|---|---|---|
| T1 | rule | 5 | 5 | pass | pass |
| T2 | consumer | 1 | 3 | pass | pass |
| T3 | rule | 6 | 6 | pass | pass |
| T4 | build | 6 | 6 | pass | pass |

## Notes

- The author's own `sanity.json` (an earlier, independent run of check 1) agrees.
- No test or reference was changed.
