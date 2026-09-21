# A definition across an agent handoff

Third exploratory study. [Protocol](DESIGN.md) is fixed before live calls.
Local names are requested deliberately; this is not spontaneous terminology.
No model explanations are used as a proxy for execution. All actions are labels.

**Completed, 2026-09-21:** [findings](results/pilot-2026-09-21-v3/findings.md).
133 calls; seven usable handoffs preserved the stipulated rules and every tested
decision. Three received guides omitted the name but retained its definition;
the other four showed no decision changes when the name was replaced. One source
generation was invalid and was not repeated. These results do not support the
proposed handoff-loss mechanism in this bank.

Python standard library; transport/storage copied unchanged from v2. Credentials
reuse the existing local gateway and gcloud session, kept in process memory.
Never commit or package `runs/`. Public exports omit private routing and envelopes.

From this directory:

```sh
python3 -m unittest -v test_v3
python3 run.py init --run runs/pilot-03 --config ../v2/runs/config.private.json
python3 run.py all --run runs/pilot-03 --live --max-calls 160
python3 run.py export --run runs/pilot-03 --out results/pilot-2026-09-21-v3
python3 analyze.py --out results/pilot-2026-09-21-v3
```

Without `--live`, the runner only freezes/reports the next stage. Resume with the
same command: completed attempts are reused, including invalid or wrong answers.
For an unresolved transport/interruption, inspect its record and explicitly add
`--retry-transport`. Original attempt histories remain. Never change measured
sources mid-run; they are hashed at initialisation.

The four stages can also be run individually: `source`, `visible`, `handoff`,
`final`. Stage prerequisites must have resolved transport outcomes. Invalid
generation is retained and leaves dependent variants unavailable. Report that
loss of coverage instead of treating missing variants as correct.

The synthetic tests exercise all 160 calls with artificial fixture outputs,
including a repeated handoff loss, a distinct renaming effect, an invalid output,
isolation of reserved records, and refusal to advance past an interrupted call.
These fixtures are never empirical results.
