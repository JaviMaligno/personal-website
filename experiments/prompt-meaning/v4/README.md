# Project handoff replay

See [DESIGN.md](DESIGN.md) for the frozen protocol and
[sources/manifest.json](sources/manifest.json) for the source revision/hashes.
This fourth study uses existing research maintenance instructions and code,
three successive generated handoffs, and review probes based on existing
regression behavior. It does not identify the original author of project terms.

**Completed:** [findings and limitations](results/findings.md). Main study: 40
calls, including two refused source generations. Two separately documented
exploratory follow-ups bring the total to 76 calls, $4.968829 reference cost.
The concrete evidence concerns a loop-entry condition lost in the first summary;
the targeted label/ambiguous-reference mechanism did not reproduce.

## Reproduction

From this directory, with a private model configuration in the same format as
the earlier studies:

```sh
python3 -m unittest -v test_v4.py
python3 run.py init --root runs/new-run --config /path/to/private-config.json
python3 run.py run --root runs/new-run --live
python3 run.py export --root runs/new-run
python3 analyze.py
```

The additional frozen checks have separate run folders and exports:

```sh
python3 supplement.py freeze
python3 supplement.py run
python3 supplement.py export
python3 factor_check.py freeze
python3 factor_check.py run
python3 factor_check.py export
python3 summarize.py
```

Read `SUPPLEMENT.md` and `FACTOR-CHECK.md` before interpreting them. They are
adaptive follow-ups, not amendments silently folded into the initial design.
Their scripts default to the recorded run paths; preserve those records before
preparing a new replication. In this run gcloud startup sometimes exceeded the
transport's 45-second allowance. The supplement used an operational bootstrap
allowing 180 seconds to obtain that same credential once in RAM; no measurement
prompt, model setting, response or frozen protocol was changed.

`run.py` reuses the frozen storage and transport utilities in `../v3/`. It
checks the hashes of measurement code and sources before execution/export.
Authentication is obtained once per process and kept only in RAM. The run is
single-writer locked. There are no automatic retries, including for invalid
model responses. Source datasets and all generated prompts are retained.

Only `results/data.json` contains the allowlisted public response fields;
provider envelopes and private configuration remain under ignored `runs/`.
`results/public-source-verification.json` records unauthenticated downloads of
all eight upstream files and their exact match to the source snapshots. An
initial automatic approval rejection treated those files as private; the
public byte-identity check resolved the premise before execution was retried.
No model call occurred during that blocked launch.

## Validation before live calls

- All 14 original tests across evidence-dose, geometry metrics and artifact
  classification passed against the existing repository implementation.
- Additional direct checks verified the short-background fallback and the
  zero-iteration refinement exception used in the boundary probes.
- The local protocol tests verify withheld-answer isolation, consistent label
  replacement in both context and proposals, and scorer discrimination between
  wrong decisions, abstentions, lexical changes and malformed output.

## Interpretation boundaries

This is a controlled replay of isolated review sessions, not a field observation
of deployed agents. Review proposals are researcher-constructed descriptions of
changes, not executable patches. Expected decisions refer to current project
behavior, including documented exceptions. No changes are actually applied to
the source project. The handoff sequence and word targets create compression
pressure explicitly. The absent retrieval tool is also part of the treatment.

A loss between source context and summaries measures information loss or its
behavioral consequences. Only the paired renaming contrast addresses surface
terminology, and even it concerns pre-existing local labels rather than proven
LLM inventions. The probes do not measure human readability.
