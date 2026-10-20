# Pilot report (phase 1)

Pilot runs: `runs-pilot/` (effort=medium for both agents, commit ab43575), condition A, 3 passes per task, 20 eligible tasks. Earlier pilot at default effort archived in `work/superseded/` (not used for selection).

Rule (spec §4.3 as amended 2026-10-06 14:10): per agent ≥2/3 correct, median wall ≤ 12.5 min, no run at a cap; must hold for BOTH agents.

| task | codex correct | codex wall med (s) | claude correct | claude wall med (s) | passes both |
|---|---|---|---|---|---|
| 041f9f3b6e | 3/3 | 186 | 3/3 | 1010 | no |
| 068185751c | 3/3 | 261 | 3/3 | 130 | yes |
| 208283a517 | 3/3 | 152 | 3/3 | 64 | yes |
| 35e04473aa | 0/3 | 221 | 3/3 | 557 | no |
| 53dae19f70 | 3/3 | 88 | 3/3 | 36 | yes |
| 81ea158cf6 | 3/3 | 309 | 3/3 | 628 | yes |
| 93508bc6a3 | 2/3 | 265 | 3/3 | 518 | yes |
| 9788bb123a | 3/3 | 273 | 3/3 | 1063 | no |
| df4dc0d6cc | 1/3 | 141 | 3/3 | 255 | no |
| f78a6fa041 | 3/3 | 254 | 3/3 | 1050 | no |
| issue-1331 | 2/3 | 213 | 2/3 | 476 | yes |
| issue-1827 | 3/3 | 170 | 3/3 | 96 | yes |
| issue-3218 | 1/3 | 158 | 3/3 | 183 | no |
| issue-4280 | 3/3 | 132 | 3/3 | 155 | yes |
| issue-5012 | 0/3 | 132 | 3/3 | 389 | no |
| issue-5694 | 0/3 | 58 | 3/3 | 921 | no |
| issue-6738 | 3/3 | 184 | 3/3 | 106 | yes |
| issue-8855 | 1/3 | 101 | 3/3 | 382 | no |
| issue-8856 | 3/3 | 99 | 3/3 | 395 | yes |
| issue-8857 | 2/3 | 261 | 3/3 | 1054 | no |

**Selected: 10 tasks** (target was 15): 068185751c, 208283a517, 53dae19f70, 81ea158cf6, 93508bc6a3, issue-1331, issue-1827, issue-4280, issue-6738, issue-8856.

Violations in the pilot: 0 in all 120 runs (both agents, condition A). The probe was verified to record base writers on real runs.

**Decision (Javier, 2026-10-06 ~19:55):** run the 10 selected tasks with 6 passes each (60 runs per condition per agent, the planned power) instead of 15 × 4. Analysis uses a task random effect; generalisation across tasks is limited to 10 tasks and is reported as such.
