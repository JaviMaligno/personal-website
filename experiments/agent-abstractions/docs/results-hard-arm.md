# Hard-task arm results (2026-10-08)

Amendment 2026-10-07 (spec §, commit 8316e38): the 10 eligible tasks that failed
the pilot margin rule, same frozen A⁺, lint, checker, prompt, effort (medium) and
models; 10 tasks × 6 passes × 4 conditions × 2 agents = 480 runs in `runs-hard/`.
0 infra failures. Tables: `out/hard/tables.md`, `out/hard-by-source/tables.md`.

| | Claude Code (Sonnet 5.5) | Codex (gpt-6-luna) |
|---|---|---|
| Correct A / AL / AP / APL | 77 / 77 / 82 / 87 % | 50 / 40 / 52 / 57 % |
| Bad decisions / any violation | 0 / 240, 0 / 240 | 0 / 240, 0 / 240 |
| Pairwise correctness contrasts | all p ≥ 0.24 | all p ≥ 0.10 |
| Tokens AP/A, per-task medians (geo-mean) | 1.00 (AP>A in 3/10 tasks, p = 0.34) | 1.30 (AP>A in 7/10 tasks, p = 0.34) |

## Reading

- **Harder tasks did not produce shortcuts.** Agents fail far more (Codex ~50 %),
  but they fail on logic, never by bypassing the db layer, writing float money or
  skipping undo: 0 violations in 480 runs here, 0 in 480 in phase 1, 0 in 240
  pilot runs (one checker false positive in phase 1). This answers the objection
  that phase 1's tasks were too easy for H1.
- **H2 still not supported.** No token saving from A⁺; for Codex on hard tasks the
  point estimate goes the other way (+30 % tokens on A⁺), not significant.
- **H3 (lint × A⁺) is noise.** The Codex correctness interaction is +0.98 (sd
  0.35) here but −0.75 (0.38) in phase 1: the sign flips between arms. The
  hard-arm value is driven by AL's 40 %, which comes from 3 timeouts with correct
  code and one task (issue-8857: 6/6 in A, 3/6 in AL; the AL failures emit an
  extra `template_settings` CRDT message, short runs with 2 lint calls — not lint
  friction).
- **No cost of more abstraction either**: correctness in AP/APL is never below A
  for either agent in either arm (within the detectable 19–26 points here).

## Limits

Same as phase 1, plus: 60 runs per condition per agent detect only ≈20–26 point
differences at these base rates; the arm was decided after seeing phase 1.
