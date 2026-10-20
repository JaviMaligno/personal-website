# A — Haiku RL correctness (89% vs R 98%)

Source: `runs3/haiku/*/Z*/*/T[1-4]/result.json`, scored with `aa.tables2.is_correct` (`status == "ok" and correct`), the same rule `tables3.md` uses.

## The 14 incorrect RL steps (R: 3)

| class | RL | R | RG | RC |
|---|---|---|---|---|
| `timeout`, hidden tests **pass** (`correct: true`) | 9 | 3 | 2 | 2 |
| `ok` but hidden tests fail: root failure | 2 | 0 | 2 | 0 |
| `ok` but hidden tests fail: carried from that root | 3 | 0 | 3 | 0 |
| **counted correct** | 114/128 | 125/128 | 121/128 | 126/128 |

Every Haiku timeout in every arm left code that passes the hidden tests. If a timeout were scored by its tests, the rates would be R 128/128 and RL 123/128 (96%).

## (b) Harness artifact: 2 of the 9 RL timeouts

`RL/Z3/0/T2` (61 turns, 694 s) and `RL/Z3/3/T2` (62 turns, 1050 s) both exited with code 0. Their final transcript record is `"stop_reason":"end_turn"`, and each ends on a finished summary: "`yarn lint` and `yarn typecheck` pass, and all 56 tests in `src/server/accounts` pass" (Z3/3/T2). `classify_status` calls these runs `timeout` only because of `usage.turns >= turn_limit` (60). The agent was never cut off. These are the only two exit-0 timeouts in the whole of study 3.

## (a) Agent behaviour induced by the lever: the other 7 RL timeouts are wall-clock kills (exit 124)

- **5 of the 7 tripped the ratchet**, and in each of them `ratchet_final.fires` is false: Haiku cleared the ratchet and then ran out of time. Among RL steps, 5 of the 36 that tripped timed out (14%), against 4 of the 92 that did not (4%). R had 3 timeouts in 128 steps (2%). Steps over 1000 s: RL 22, R 10.
- The time goes into lint-driven refactor loops. `yarn lint` is slow in every arm (R median about 100 s per step), so each extra lint pass is expensive. `RL/Z1/7/T1` ran lint 7 times (797 s): "Lint still flags the set6/set12 loops … I'll fold them into one shared helper." Later in the same run: "**Lint now passes, but the refactor broke the 3-month average tests**". It found the dropped `await`, fixed it, and was killed while running the full suite. `RL/Z3/2/T2` spent about 300 s just checking "whether the duplicate check actually fails `yarn lint` or only prints a warning". It then rewrote the whole link region, "GoCardless through EnableBanking".
- So the ratchet did push Haiku into consolidations that broke behaviour, but only while the step was still running. Each break was caught and repaired before the kill, and the evaluated trees pass.
- The other 2 wall-clock kills (`Z2/7/T2`, `Z4/2/T1`), plus `Z2/3/T3` and `Z4/5/T1`, had 0 trips. They look like ordinary R-style slowness.

## The 5 wrong-but-`ok` RL steps are missed copies, not the ratchet

Both root failures have `ratchet_trips: 0` and are in the lint-blind zones:

- `RL/Z2/1/T1`: the `forecast` consumer fails ("a ranged expense is expected at the end furthest from zero"). The diff never touches it, and the closing summary says "Lint, formatting and strict typecheck are clean." The failure carries into T3 and T4.
- `RL/Z4/5/T3`: the `dates-in-range` consumer fails ("days in a period move off listed holidays like off a weekend"). It carries into T4.

No inconsistency was unified (`inconsistencies_unified_step` is null in all five). RG shows the same pattern (Z2/3, Z2/5: missed preview, post-transaction and rule-action-sync copies, plus carries), so this is Haiku's normal missed-copy failure. R happened to have none.

## (c) Chance / small n

- Timeouts, RL 9/128 vs R 3/128: Fisher p = 0.14.
- Timeouts, tripped vs untripped RL steps: p = 0.12.
- Wrong-but-ok, RL 5 vs R 0: p = 0.06. These 5 steps come from only 2 independent root events, so the step-level count overstates the evidence. The mixed model's chain random effect only partly absorbs the dependence.

## Verdict

The -1.24 log-odds is mostly a scoring effect. About 64% of RL's deficit (9 of 14 steps) is timeouts whose code is correct. Two of those are harness misclassifications (turn count ≥ 60 on a normal `end_turn`). About five are real lever-induced cost: ratchet refactor loops on top of a slow `yarn lint` burn through the 25-minute budget. The remaining 5 steps are two missed copies in the lint-blind zones Z2 and Z4. They are unrelated to the ratchet and match RG, so they read as chance against R's clean 0. There is no evidence that the ratchet left broken behaviour in an evaluated tree.
