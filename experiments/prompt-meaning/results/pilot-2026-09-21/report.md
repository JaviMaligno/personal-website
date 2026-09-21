# Pilot report

Descriptive feasibility pilot; no equivalence or human-trust inference.

Selected 0 cases from 40 candidates (0 eligible).

Execution status: {'valid': 8}. Invalid explanations: 0.
All sensitivity controls passed: True.

Correctness below uses the original assignment as reference. Invalid calls remain in the expected denominator. Controls have their own variant-specific check in JSON.

| Kind | Task | Executor | Variant | Rep | Set | Correct / expected | Status |
|---|---|---|---|---|---|---|---|
| redundant | control | gpt-sol | eliminated | 0 | fixed | 2/2 | valid |
| redundant | control | claude-opus | eliminated | 0 | fixed | 2/2 | valid |
| positive | control | claude-opus | original | 0 | fixed | 2/2 | valid |
| redundant | control | gpt-sol | original | 0 | fixed | 2/2 | valid |
| redundant | control | claude-opus | original | 0 | fixed | 2/2 | valid |
| positive | control | gpt-sol | eliminated | 0 | fixed | 1/2 | valid |
| positive | control | gpt-sol | original | 0 | fixed | 2/2 | valid |
| positive | control | claude-opus | eliminated | 0 | fixed | 1/2 | valid |

## Do the explanations predict the change?

Exact matches require both predicted actions, before and after the intervention, to match. Compare change detection to the always-no-change baseline; many tasks may be unchanged. With one repetition these are descriptive counts only.

| Kind | Task | Explainer → executor | Variant | Set | Scorable / expected | Exact pairs | Change detection | No-change baseline | Abstentions |
|---|---|---|---|---|---|---|---|---|---|
| positive | control | gpt-sol → gpt-sol | eliminated | fixed | 2/2 | 2 | 2 | 1 | 0 |
| positive | control | gpt-sol → claude-opus | eliminated | fixed | 2/2 | 2 | 2 | 1 | 0 |
| positive | control | claude-opus → gpt-sol | eliminated | fixed | 2/2 | 2 | 2 | 1 | 0 |
| positive | control | claude-opus → claude-opus | eliminated | fixed | 2/2 | 2 | 2 | 1 | 0 |
| redundant | control | gpt-sol → gpt-sol | eliminated | fixed | 2/2 | 2 | 2 | 2 | 0 |
| redundant | control | gpt-sol → claude-opus | eliminated | fixed | 2/2 | 2 | 2 | 2 | 0 |
| redundant | control | claude-opus → gpt-sol | eliminated | fixed | 2/2 | 2 | 2 | 2 | 0 |
| redundant | control | claude-opus → claude-opus | eliminated | fixed | 2/2 | 2 | 2 | 2 | 0 |

Within-variant frequencies and raw provider usage are in report.json. Fixed and proposed cases are kept separate. Repeated decisions are not independent concepts.

No monetary total is inferred from token counts. Configure and document provider pricing separately before budgeting a larger study.
