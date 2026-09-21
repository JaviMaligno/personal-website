# Pilot report

Descriptive feasibility pilot; no equivalence or human-trust inference.

Selected 0 cases from 8 candidates (0 eligible).

Synthetic cases: 8. Unmodified natural prompts: 8.

Execution status: {'valid': 159, 'invalid_output': 17}. Invalid explanations: 0.
All sensitivity controls passed: True.

Complete/partial policy benchmarks passed: True.

Correctness below uses the original assignment as reference. Invalid calls remain in the expected denominator. Controls have their own variant-specific check in JSON.

| Kind | Task | Executor | Variant | Rep | Set | Correct / expected | Status |
|---|---|---|---|---|---|---|---|
| synthetic | access-01 | claude-opus | explicit | 1 | fixed | 12/12 | valid |
| synthetic | release-01 | claude-opus | original | 0 | fixed | 11/12 | valid |
| synthetic | release-01 | gpt-sol | substituted | 1 | fixed | 11/12 | valid |
| synthetic | expense-01 | gpt-sol | explicit | 1 | fixed | 12/12 | valid |
| synthetic | access-01 | gpt-sol | eliminated | 1 | fixed | 9/12 | valid |
| synthetic | expense-01 | claude-opus | eliminated | 1 | fixed | 9/12 | valid |
| synthetic | retention-01 | claude-opus | original | 0 | fixed | 0/12 | invalid_output |
| redundant | control | gpt-sol | original | 1 | fixed | 2/2 | valid |
| synthetic | retention-01 | gpt-sol | substituted | 0 | fixed | 11/12 | valid |
| synthetic | retention-01 | gpt-sol | original | 1 | fixed | 11/12 | valid |
| positive | control | claude-opus | eliminated | 0 | fixed | 1/2 | valid |
| synthetic | retention-01 | claude-opus | eliminated | 1 | fixed | 11/12 | valid |
| synthetic | release-01 | gpt-sol | eliminated | 0 | fixed | 11/12 | valid |
| positive | control | gpt-sol | eliminated | 1 | fixed | 1/2 | valid |
| synthetic | release-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| synthetic | expense-01 | claude-opus | explicit | 1 | fixed | 12/12 | valid |
| synthetic | access-01 | claude-opus | eliminated | 0 | fixed | 9/12 | valid |
| synthetic | access-01 | gpt-sol | substituted | 1 | fixed | 9/12 | valid |
| unmodified | expense-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| synthetic | retention-01 | claude-opus | explicit | 0 | fixed | 12/12 | valid |
| synthetic | expense-01 | gpt-sol | eliminated | 1 | fixed | 9/12 | valid |
| synthetic | retention-01 | gpt-sol | explicit | 1 | fixed | 12/12 | valid |
| synthetic | retention-01 | claude-opus | eliminated | 0 | fixed | 11/12 | valid |
| synthetic | retention-01 | gpt-sol | explicit | 0 | fixed | 12/12 | valid |
| synthetic | release-01 | gpt-sol | explicit | 1 | fixed | 12/12 | valid |
| synthetic | expense-01 | gpt-sol | explicit | 1 | fixed | 12/12 | valid |
| positive | control | claude-opus | original | 1 | fixed | 2/2 | valid |
| synthetic | access-01 | claude-opus | explicit | 0 | fixed | 12/12 | valid |
| synthetic | release-01 | claude-opus | eliminated | 1 | fixed | 11/12 | valid |
| synthetic | release-01 | gpt-sol | substituted | 0 | fixed | 11/12 | valid |
| synthetic | release-01 | gpt-sol | substituted | 1 | fixed | 11/12 | valid |
| synthetic | retention-01 | gpt-sol | substituted | 0 | fixed | 11/12 | valid |
| synthetic | release-01 | gpt-sol | explicit | 0 | fixed | 12/12 | valid |
| synthetic | retention-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| unmodified | access-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| synthetic | expense-01 | gpt-sol | substituted | 1 | fixed | 9/12 | valid |
| unmodified | expense-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| unmodified | retention-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| unmodified | access-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| synthetic | access-01 | gpt-sol | substituted | 1 | fixed | 9/12 | valid |
| synthetic | release-01 | claude-opus | substituted | 1 | fixed | 0/12 | invalid_output |
| unmodified | expense-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| synthetic | access-01 | claude-opus | substituted | 1 | fixed | 9/12 | valid |
| synthetic | expense-01 | gpt-sol | eliminated | 1 | fixed | 9/12 | valid |
| synthetic | expense-01 | claude-opus | original | 0 | fixed | 0/12 | invalid_output |
| unmodified | access-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| unmodified | expense-01 | claude-opus | original | 1 | fixed | 12/12 | valid |
| unmodified | release-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| unmodified | expense-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| synthetic | access-01 | gpt-sol | explicit | 0 | fixed | 12/12 | valid |
| synthetic | release-01 | claude-opus | original | 1 | fixed | 11/12 | valid |
| synthetic | release-01 | claude-opus | explicit | 1 | fixed | 12/12 | valid |
| synthetic | expense-01 | claude-opus | explicit | 1 | fixed | 12/12 | valid |
| synthetic | retention-01 | gpt-sol | original | 0 | fixed | 11/12 | valid |
| synthetic | retention-01 | claude-opus | substituted | 1 | fixed | 11/12 | valid |
| synthetic | access-01 | claude-opus | original | 1 | fixed | 9/12 | valid |
| synthetic | expense-01 | claude-opus | explicit | 0 | fixed | 12/12 | valid |
| unmodified | retention-01 | claude-opus | original | 1 | fixed | 12/12 | valid |
| synthetic | expense-01 | gpt-sol | substituted | 1 | fixed | 9/12 | valid |
| unmodified | release-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| synthetic | retention-01 | claude-opus | eliminated | 1 | fixed | 11/12 | valid |
| unmodified | release-01 | claude-opus | original | 1 | fixed | 12/12 | valid |
| synthetic | expense-01 | claude-opus | substituted | 0 | fixed | 0/12 | invalid_output |
| synthetic | retention-01 | claude-opus | substituted | 0 | fixed | 0/12 | invalid_output |
| synthetic | retention-01 | claude-opus | substituted | 0 | fixed | 0/12 | invalid_output |
| synthetic | expense-01 | gpt-sol | explicit | 0 | fixed | 12/12 | valid |
| synthetic | expense-01 | claude-opus | eliminated | 0 | fixed | 9/12 | valid |
| synthetic | access-01 | claude-opus | eliminated | 1 | fixed | 9/12 | valid |
| synthetic | access-01 | claude-opus | substituted | 0 | fixed | 0/12 | invalid_output |
| unmodified | retention-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| synthetic | release-01 | claude-opus | substituted | 0 | fixed | 11/12 | valid |
| synthetic | release-01 | gpt-sol | eliminated | 1 | fixed | 11/12 | valid |
| synthetic | release-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| unmodified | access-01 | claude-opus | original | 1 | fixed | 12/12 | valid |
| synthetic | retention-01 | claude-opus | eliminated | 0 | fixed | 11/12 | valid |
| positive | control | claude-opus | eliminated | 1 | fixed | 1/2 | valid |
| synthetic | expense-01 | claude-opus | eliminated | 0 | fixed | 9/12 | valid |
| synthetic | retention-01 | gpt-sol | substituted | 1 | fixed | 11/12 | valid |
| unmodified | expense-01 | claude-opus | original | 1 | fixed | 12/12 | valid |
| synthetic | release-01 | claude-opus | explicit | 1 | fixed | 12/12 | valid |
| synthetic | release-01 | gpt-sol | explicit | 1 | fixed | 12/12 | valid |
| synthetic | release-01 | gpt-sol | eliminated | 0 | fixed | 11/12 | valid |
| synthetic | release-01 | claude-opus | substituted | 0 | fixed | 0/12 | invalid_output |
| redundant | control | claude-opus | eliminated | 0 | fixed | 2/2 | valid |
| synthetic | access-01 | claude-opus | original | 1 | fixed | 0/12 | invalid_output |
| synthetic | retention-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| synthetic | access-01 | gpt-sol | substituted | 0 | fixed | 9/12 | valid |
| unmodified | retention-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| synthetic | expense-01 | gpt-sol | substituted | 0 | fixed | 9/12 | valid |
| synthetic | release-01 | claude-opus | original | 1 | fixed | 0/12 | invalid_output |
| synthetic | expense-01 | gpt-sol | eliminated | 0 | fixed | 9/12 | valid |
| synthetic | release-01 | claude-opus | explicit | 0 | fixed | 12/12 | valid |
| synthetic | retention-01 | gpt-sol | explicit | 0 | fixed | 12/12 | valid |
| synthetic | release-01 | gpt-sol | substituted | 0 | fixed | 11/12 | valid |
| synthetic | retention-01 | claude-opus | explicit | 0 | fixed | 12/12 | valid |
| synthetic | expense-01 | claude-opus | original | 1 | fixed | 10/12 | valid |
| synthetic | retention-01 | claude-opus | original | 1 | fixed | 0/12 | invalid_output |
| unmodified | access-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| synthetic | retention-01 | claude-opus | explicit | 1 | fixed | 12/12 | valid |
| positive | control | gpt-sol | eliminated | 0 | fixed | 1/2 | valid |
| synthetic | access-01 | gpt-sol | original | 1 | fixed | 9/12 | valid |
| synthetic | access-01 | claude-opus | eliminated | 1 | fixed | 9/12 | valid |
| redundant | control | claude-opus | eliminated | 1 | fixed | 2/2 | valid |
| synthetic | retention-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| positive | control | claude-opus | original | 0 | fixed | 2/2 | valid |
| synthetic | expense-01 | claude-opus | substituted | 0 | fixed | 9/12 | valid |
| synthetic | access-01 | gpt-sol | original | 0 | fixed | 9/12 | valid |
| synthetic | access-01 | gpt-sol | original | 0 | fixed | 9/12 | valid |
| synthetic | access-01 | gpt-sol | eliminated | 0 | fixed | 9/12 | valid |
| redundant | control | claude-opus | original | 1 | fixed | 2/2 | valid |
| unmodified | retention-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| synthetic | access-01 | gpt-sol | explicit | 1 | fixed | 12/12 | valid |
| synthetic | access-01 | gpt-sol | original | 1 | fixed | 8/12 | valid |
| unmodified | release-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| redundant | control | gpt-sol | eliminated | 1 | fixed | 2/2 | valid |
| synthetic | access-01 | claude-opus | original | 0 | fixed | 0/12 | invalid_output |
| synthetic | release-01 | gpt-sol | eliminated | 1 | fixed | 11/12 | valid |
| synthetic | expense-01 | gpt-sol | original | 1 | fixed | 8/12 | valid |
| synthetic | expense-01 | claude-opus | original | 1 | fixed | 0/12 | invalid_output |
| synthetic | release-01 | claude-opus | substituted | 1 | fixed | 0/12 | invalid_output |
| synthetic | access-01 | gpt-sol | eliminated | 1 | fixed | 9/12 | valid |
| synthetic | release-01 | gpt-sol | original | 0 | fixed | 11/12 | valid |
| synthetic | expense-01 | claude-opus | substituted | 1 | fixed | 9/12 | valid |
| unmodified | release-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| redundant | control | gpt-sol | original | 0 | fixed | 2/2 | valid |
| synthetic | release-01 | claude-opus | eliminated | 1 | fixed | 11/12 | valid |
| synthetic | retention-01 | gpt-sol | eliminated | 1 | fixed | 11/12 | valid |
| synthetic | retention-01 | gpt-sol | eliminated | 0 | fixed | 11/12 | valid |
| synthetic | access-01 | claude-opus | substituted | 0 | fixed | 0/12 | invalid_output |
| unmodified | access-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| synthetic | expense-01 | gpt-sol | eliminated | 0 | fixed | 9/12 | valid |
| unmodified | retention-01 | claude-opus | original | 1 | fixed | 12/12 | valid |
| unmodified | retention-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| synthetic | retention-01 | gpt-sol | eliminated | 1 | fixed | 11/12 | valid |
| unmodified | release-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| synthetic | expense-01 | gpt-sol | explicit | 0 | fixed | 12/12 | valid |
| synthetic | access-01 | claude-opus | explicit | 1 | fixed | 12/12 | valid |
| synthetic | expense-01 | claude-opus | explicit | 0 | fixed | 12/12 | valid |
| synthetic | expense-01 | claude-opus | substituted | 1 | fixed | 0/12 | invalid_output |
| synthetic | expense-01 | gpt-sol | original | 1 | fixed | 9/12 | valid |
| synthetic | retention-01 | claude-opus | substituted | 1 | fixed | 11/12 | valid |
| unmodified | expense-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| unmodified | release-01 | claude-opus | original | 1 | fixed | 12/12 | valid |
| synthetic | release-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| synthetic | access-01 | claude-opus | substituted | 1 | fixed | 0/12 | invalid_output |
| synthetic | retention-01 | claude-opus | explicit | 1 | fixed | 12/12 | valid |
| synthetic | access-01 | claude-opus | original | 0 | fixed | 9/12 | valid |
| synthetic | expense-01 | gpt-sol | original | 0 | fixed | 8/12 | valid |
| positive | control | gpt-sol | original | 1 | fixed | 2/2 | valid |
| unmodified | access-01 | claude-opus | original | 1 | fixed | 12/12 | valid |
| redundant | control | gpt-sol | eliminated | 0 | fixed | 2/2 | valid |
| synthetic | retention-01 | gpt-sol | substituted | 1 | fixed | 11/12 | valid |
| unmodified | release-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| synthetic | retention-01 | claude-opus | original | 1 | fixed | 12/12 | valid |
| unmodified | expense-01 | claude-opus | original | 0 | fixed | 12/12 | valid |
| positive | control | gpt-sol | original | 0 | fixed | 2/2 | valid |
| redundant | control | claude-opus | original | 0 | fixed | 2/2 | valid |
| synthetic | access-01 | gpt-sol | explicit | 1 | fixed | 12/12 | valid |
| synthetic | expense-01 | gpt-sol | substituted | 0 | fixed | 9/12 | valid |
| unmodified | access-01 | gpt-sol | original | 0 | fixed | 12/12 | valid |
| synthetic | retention-01 | gpt-sol | explicit | 1 | fixed | 12/12 | valid |
| synthetic | access-01 | gpt-sol | eliminated | 0 | fixed | 9/12 | valid |
| synthetic | release-01 | claude-opus | eliminated | 0 | fixed | 11/12 | valid |
| synthetic | release-01 | claude-opus | explicit | 0 | fixed | 12/12 | valid |
| synthetic | access-01 | gpt-sol | substituted | 0 | fixed | 9/12 | valid |
| synthetic | release-01 | gpt-sol | explicit | 0 | fixed | 12/12 | valid |
| synthetic | release-01 | gpt-sol | original | 1 | fixed | 11/12 | valid |
| unmodified | retention-01 | gpt-sol | original | 1 | fixed | 12/12 | valid |
| synthetic | release-01 | claude-opus | eliminated | 0 | fixed | 11/12 | valid |
| synthetic | retention-01 | gpt-sol | eliminated | 0 | fixed | 11/12 | valid |
| synthetic | expense-01 | claude-opus | original | 0 | fixed | 10/12 | valid |
| synthetic | access-01 | claude-opus | explicit | 0 | fixed | 12/12 | valid |
| synthetic | access-01 | gpt-sol | explicit | 0 | fixed | 12/12 | valid |
| synthetic | expense-01 | gpt-sol | original | 0 | fixed | 9/12 | valid |
| synthetic | access-01 | claude-opus | eliminated | 0 | fixed | 9/12 | valid |
| synthetic | expense-01 | claude-opus | eliminated | 1 | fixed | 9/12 | valid |

## Do the explanations predict the change?

Exact matches require both predicted actions, before and after the intervention, to match. Compare change detection to the always-no-change baseline; many tasks may be unchanged. With one repetition these are descriptive counts only.

| Kind | Task | Explainer → executor | Variant | Set | Scorable / expected | Exact pairs | Change detection | No-change baseline | Abstentions |
|---|---|---|---|---|---|---|---|---|---|
| synthetic | access-01 | gpt-sol → gpt-sol | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | access-01 | gpt-sol → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | access-01 | gpt-sol → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | access-01 | gpt-sol → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | access-01 | claude-opus → gpt-sol | eliminated | fixed | 18/24 | 17 | 17 | 17 | 6 |
| synthetic | access-01 | claude-opus → gpt-sol | substituted | fixed | 18/24 | 17 | 17 | 17 | 6 |
| synthetic | access-01 | claude-opus → claude-opus | eliminated | fixed | 18/24 | 18 | 18 | 18 | 6 |
| synthetic | access-01 | claude-opus → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 6 |
| synthetic | access-01 | gpt-sol → gpt-sol | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | access-01 | gpt-sol → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | access-01 | gpt-sol → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | access-01 | gpt-sol → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | access-01 | claude-opus → gpt-sol | eliminated | fixed | 24/24 | 24 | 24 | 24 | 0 |
| synthetic | access-01 | claude-opus → gpt-sol | substituted | fixed | 24/24 | 24 | 24 | 24 | 0 |
| synthetic | access-01 | claude-opus → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 0 |
| synthetic | access-01 | claude-opus → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 0 |
| synthetic | expense-01 | gpt-sol → gpt-sol | eliminated | fixed | 20/24 | 20 | 20 | 20 | 4 |
| synthetic | expense-01 | gpt-sol → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | expense-01 | gpt-sol → claude-opus | eliminated | fixed | 20/24 | 20 | 20 | 20 | 4 |
| synthetic | expense-01 | gpt-sol → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | expense-01 | claude-opus → gpt-sol | eliminated | fixed | 20/24 | 20 | 20 | 20 | 4 |
| synthetic | expense-01 | claude-opus → gpt-sol | substituted | fixed | 20/24 | 20 | 20 | 20 | 4 |
| synthetic | expense-01 | claude-opus → claude-opus | eliminated | fixed | 20/24 | 20 | 20 | 20 | 4 |
| synthetic | expense-01 | claude-opus → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 4 |
| synthetic | expense-01 | gpt-sol → gpt-sol | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | expense-01 | gpt-sol → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | expense-01 | gpt-sol → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | expense-01 | gpt-sol → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | expense-01 | claude-opus → gpt-sol | eliminated | fixed | 24/24 | 24 | 24 | 24 | 0 |
| synthetic | expense-01 | claude-opus → gpt-sol | substituted | fixed | 24/24 | 24 | 24 | 24 | 0 |
| synthetic | expense-01 | claude-opus → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 0 |
| synthetic | expense-01 | claude-opus → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 0 |
| synthetic | release-01 | gpt-sol → gpt-sol | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | gpt-sol → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | gpt-sol → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | gpt-sol → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | claude-opus → gpt-sol | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | claude-opus → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | claude-opus → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | claude-opus → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | gpt-sol → gpt-sol | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | gpt-sol → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | gpt-sol → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | gpt-sol → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | release-01 | claude-opus → gpt-sol | eliminated | fixed | 24/24 | 24 | 24 | 24 | 0 |
| synthetic | release-01 | claude-opus → gpt-sol | substituted | fixed | 24/24 | 24 | 24 | 24 | 0 |
| synthetic | release-01 | claude-opus → claude-opus | eliminated | fixed | 12/24 | 12 | 12 | 12 | 0 |
| synthetic | release-01 | claude-opus → claude-opus | substituted | fixed | 12/24 | 12 | 12 | 12 | 0 |
| synthetic | retention-01 | gpt-sol → gpt-sol | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | gpt-sol → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | gpt-sol → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | gpt-sol → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | claude-opus → gpt-sol | eliminated | fixed | 24/24 | 22 | 22 | 22 | 0 |
| synthetic | retention-01 | claude-opus → gpt-sol | substituted | fixed | 24/24 | 22 | 22 | 22 | 0 |
| synthetic | retention-01 | claude-opus → claude-opus | eliminated | fixed | 24/24 | 22 | 22 | 22 | 0 |
| synthetic | retention-01 | claude-opus → claude-opus | substituted | fixed | 12/24 | 11 | 11 | 11 | 0 |
| synthetic | retention-01 | gpt-sol → gpt-sol | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | gpt-sol → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | gpt-sol → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | gpt-sol → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | claude-opus → gpt-sol | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | claude-opus → gpt-sol | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | claude-opus → claude-opus | eliminated | fixed | 0/24 | 0 | 0 | 0 | 24 |
| synthetic | retention-01 | claude-opus → claude-opus | substituted | fixed | 0/24 | 0 | 0 | 0 | 24 |
| positive | control | gpt-sol → gpt-sol | eliminated | fixed | 4/4 | 4 | 4 | 2 | 0 |
| positive | control | gpt-sol → claude-opus | eliminated | fixed | 4/4 | 4 | 4 | 2 | 0 |
| positive | control | claude-opus → gpt-sol | eliminated | fixed | 4/4 | 4 | 4 | 2 | 0 |
| positive | control | claude-opus → claude-opus | eliminated | fixed | 4/4 | 4 | 4 | 2 | 0 |
| redundant | control | gpt-sol → gpt-sol | eliminated | fixed | 4/4 | 4 | 4 | 4 | 0 |
| redundant | control | gpt-sol → claude-opus | eliminated | fixed | 4/4 | 4 | 4 | 4 | 0 |
| redundant | control | claude-opus → gpt-sol | eliminated | fixed | 4/4 | 4 | 4 | 4 | 0 |
| redundant | control | claude-opus → claude-opus | eliminated | fixed | 4/4 | 4 | 4 | 4 | 0 |

Within-variant frequencies and raw provider usage are in report.json. Fixed and proposed cases are kept separate. Repeated decisions are not independent concepts.

No monetary total is inferred from token counts. Configure and document provider pricing separately before budgeting a larger study.
