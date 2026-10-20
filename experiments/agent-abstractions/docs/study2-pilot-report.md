# Study 2 pilot report (2026-10-08)

1 chain per zone × condition × agent (Claude Sonnet 5.5, Codex gpt-6-luna, Claude Haiku 5.5;
effort medium), 96 steps, `runs2-pilot/` (commit 6fb1846). 0 infra failures after fixing a
relative `--runs` path in the pilot script (first launch: 10 steps failed to start, nothing ran).
Tables: `out/study2-pilot/tables2.md`.

| | correct T1/T2/T3/T4 (of 4) | missed copy (T1+T3) | steps with carried defects | timeouts |
|---|---|---|---|---|
| Claude R | 4/3/3/3 | 1 (Z2/T3) | 3 | 2 |
| Claude F | 4/4/4/4 | 0 | 0 | 0 |
| Codex R | 3/3/3/3 | 0 | 3 (Z4) | 0 |
| Codex F | 2/4/3/1 | 1 (Z2/T1) | 7 (Z2, Z3, Z4) | 0 |
| Haiku R | 4/4/4/4 | 0 | 0 | 0 |
| Haiku F | 4/4/4/4 | 0 | 0 | 0 |

## Traces read
- **Claude R Z2/T3:** a genuine missed copy — 7 files edited, the schedule *preview* path left on
  the old rule.
- **Codex F Z2/T1:** a deliberate one — "budget template midpoint behavior is preserved". In F the
  pre-existing template inconsistency is a named helper mode (`rangeRounding`); the agent read it
  as an intentional exception and kept it, although the statement asked for the rule to apply.
  A treatment effect worth reporting (explicit exceptions in an abstraction get preserved), not a
  measurement error.
- State carry verified (start tree of step k == post tree of step k-1, `exact: true`).

## Checks required by the spec (condition-agnostic)
- Every step solved at least once: yes. Consumer tests discriminate: yes. Chains end to end: yes.
- Base missed-copy rates ≈ 1/8 per agent-condition, below the 20–80 % band → chains stay at 8
  per zone (no amendment).

## Timing for the full run (8 chains per zone × cond × agent = 768 steps)
Median step wall: Claude 450 s, Codex 159 s, Haiku 449 s. Estimate: Codex ≈ 6–9 h, Claude ≈ 16 h,
Haiku ≈ 11–16 h (agents in parallel), plus ≈ 6 h evaluation → ~1 day wall. Subscription quota only.
