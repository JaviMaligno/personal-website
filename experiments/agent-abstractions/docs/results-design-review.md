# Blind design review of agent diffs — results (2026-10-08)

Rubric pre-registered in `docs/design-review-rubric.md` (commit eff4c9c). 470 diffs
(passes 0–2, both arms, both agents, 4 conditions), judged by Claude Opus 5.5 agents
(not an agent under test). Scores in `work/review/scores*/`, mapping in
`work/review-mapping.json`.

**Setup error found and fixed before analysis:** in the first pass, mined-task
packets pointed at the untouched variant, which already contains the upstream fix,
instead of the agent's start tree (variant + revert). Two judges flagged it. All 230
mined-task scores were discarded (`scores-contaminated/`) and re-judged against
per-task start trees; every one of the 470 diffs was verified with `git apply --check`
against its tree before judging. No condition comparison was looked at before the fix.

## Reliability (second independent judge, 70 packets)
Quadratic-weighted kappa: maintainability 0.85, duplication 0.83, reuse 0.76,
placement 0.76, scope 0.52 (scope scores pile up at 5; treat with caution).
`would_merge` exact agreement 76 %.

## Results: no condition effect on design quality
Mean maintainability (1–5), A / AL / AP / APL:

| | Phase 1 | Hard arm |
|---|---|---|
| Claude | 3.83 / 3.77 / 3.67 / 3.97 | 3.73 / 3.77 / 3.87 / 3.93 |
| Codex | 3.70 / 3.47 / 3.63 / 3.47 | 3.44 / 3.79 / 3.75 / 3.71 |

A vs AP on every dimension, agent and arm: all Mann-Whitney p ≥ 0.27; per-task sign
tests all p ≥ 0.06 (40 contrasts; the single 0.06 is placement, Claude hard arm).
`would_merge = yes` ranges 37–67 % with no consistent ordering; judges flag a bypass of
an existing abstraction in 3–20 % of diffs, also without a condition pattern.

## Reading
The broader design metric agrees with the narrow invariant metric: on this codebase,
an extra domain layer plus harsh lint neither improved nor degraded the design of
what the agents wrote. Note the treatment here was "more layers on already-abstracted
code", not "abstraction vs repetition" — that is the redesigned study.
