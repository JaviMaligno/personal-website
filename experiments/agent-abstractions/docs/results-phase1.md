# Phase 1 results (2026-10-07)

Full run: 10 tasks × 6 passes × 4 conditions × 2 agents = 480 runs (commit 4110d24,
effort=medium for both agents). 0 infra failures. Tables: `out/tables-pooled.md`,
`out/tables.md` (split by source). Pilot: `docs/pilot-report.md`.

## Pre-registered hypotheses vs data

| | Claude Code (Sonnet 5.5) | Codex (gpt-6-luna) |
|---|---|---|
| Correct A / AL / AP / APL | 88 / 95 / 98 / 98 % | 83 / 87 / 83 / 78 % |
| Bad decisions (all conditions) | 0 / 240 | 0 / 240 |
| Any violation | 0 / 240 | 1 / 240 (APL; checker false positive, see below) |
| Tokens on correct runs, A vs AP | 327k vs 312k, p = 0.83 | 826k vs 825k, p = 0.86 |
| Turns / tool calls, A vs AP | 12/12 vs 10/10, p = 0.62 / 0.75 | 23/18 vs 24/18, p = 0.45 / 0.53 |

- **H1 (constraint): not testable as a reduction.** Habitual code (A) already
  produced 0 bad decisions in 240 runs per agent (and 0 in 120 pilot runs).
  Neither more abstraction (A⁺) nor harsh lint has anything left to remove. The
  pre-registered null reading applies: *coherent habitual code already
  constrains these agents*. A⁺ did not **increase** violations either.
- **H2 (efficiency): no effect detected.** Tokens, turns and tool calls are flat
  for both agents (all p > 0.4).
- **H3 (lint × A⁺ interaction): no signal** (no variation in violations; for
  correctness the interaction term is not distinguishable from 0).
- **Rival (legibility):** cannot be separated, since nothing moved.

## Things that look like effects and are not (checked in the traces)

1. **Claude correctness A 88 % vs AP 98 % (p = 0.061).** 6 of the 7 non-correct
   A runs are 25-min **timeouts**, and in 5 of them the final code passed the
   hidden tests. The time goes on whole-monorepo `yarn typecheck` / `yarn lint`
   plus sleep/until waits; Claude does that in 78–90 % of runs in **every**
   condition, so it is not condition-driven. Read as a timeout artefact.
2. **Claude wall time A 320 s vs AP 232 s (p = 0.049).** Same turns, tool calls
   and tokens; only the clock differs. Consistent with machine-load variation
   overnight (two agents in parallel); one p ≈ 0.05 among 16 contrasts. Not an
   effect.
3. **The single violation** (codex/APL/issue-1331/0) is
   `Number(candidate.amount) === -Number(transaction.amount)`: a comparison of
   integer amounts, flagged by the static rule that treats `Number(` on an
   amount as float money maths. False positive; the run was also incorrect.

## Limits

- 10 tasks (target 15); 60 runs per condition per agent; detectable
  differences in correctness ≈ 11–20 points.
- Violations were measured by a hidden checker of three invariant families
  (CRDT write path, integer money, undo registration). Other kinds of bad
  decision are not measured.
- Pilots and smoke runs are archived in `work/superseded/` and `runs-pilot/`
  and never counted.
