# agent-abstractions

Do more abstractions and a harsh lint help coding agents? Matt Pocock
[argued](https://x.com/mattpocockuk/status/2106425743479546343) that agents work better in
codebases with more abstractions and a strict lint, because the structure constrains what
they can write. This experiment tests that claim on real code: Actual Budget's
`packages/loot-core` (MIT licence), with three agents at the same reasoning effort
(medium): Claude Code with Claude Sonnet 5.5, Claude Code with Claude Haiku 5.5, and Codex
with gpt-6-luna.

Everything here is the harness, the task material, the registered tables, the judge
scores and a compact, anonymised per-step dataset. Specs (with every amendment, written
before the data they govern was read) are in `docs/specs/`.

## Three phases

| Phase | Question | One-line result | Report |
|---|---|---|---|
| 1 | Habitual code (A) vs more abstraction (A⁺), each with and without a harsh lint, on 10 tasks mined from Actual's history and issues (480 runs, Sonnet + Codex) | Nothing to constrain: 0 bad decisions in A already, no efficiency effect (tokens, turns, tool calls flat, all p > 0.4) | [`docs/results-phase1.md`](docs/results-phase1.md) (hard-task arm: [`docs/results-hard-arm.md`](docs/results-hard-arm.md)) |
| 2 | Repeated code (R) vs human-factored code (F) over 4-step task chains that change a rule repeated across call sites (768 steps, 3 agents) | F lowers missed copies in direction for every agent and stops duplication from accumulating; no difference in lines or tokens; judged design is better in F | [`docs/results-study2.md`](docs/results-study2.md) |
| 3 | Starting from R, can a lever make the agent design the abstraction itself? (1,632 steps, 3 agents) | Asking for the refactor (RC) is the only lever that improves judged maintainability for all three agents; a written rule and a duplication ratchet help Sonnet only, and Codex games the ratchet's surface | [`docs/results-study3.md`](docs/results-study3.md) |

### Study 3 arms (the main study)

All arms start from study 2's frozen repeated-code variant R; 4 zones × 8 chains per arm
and agent.

| Arm | Lever |
|---|---|
| R | none (fresh concurrent control) |
| RG | one rule in `AGENTS.md`: do not copy logic; extract shared behaviour into one function and change a rule in one place (`tasks3/rg-rule.md`) |
| RL | duplication ratchet in `yarn lint`: jscpd (min-tokens 35) fails on any clone touching lines the step added |
| RC | a T0 step before the chain: a directed refactor ("this logic should live in one place, behaviour unchanged") |

Design quality is scored by a blind LLM judge on every step and chain diff (rubric:
`docs/design-review-rubric.md`), with a second blind pass on 340 packets for agreement
(kappa 0.70–1.00 by dimension, `out/study3/design-kappa.json`).

## Layout

| Path | What |
|---|---|
| `src/aa/` | harness (`aa` CLI): substrate and condition variants, Docker images, agent runners (Claude Code, Codex), chain runner, evaluation, ratchet, blind review packets, tables |
| `scripts/` | study 2/3 analysis scripts: design review and kappa, secondary measures, ratchet calibration, T0 and load re-checks |
| `substrate/` | pinned Actual commit (`BASE`), condition patches (A⁺, lint, R, F, RG, RL), Dockerfile, runtime probe |
| `tasks/` | phase 1 tasks (mined commits and open issues, hidden tests, ledger) |
| `tasks2/`, `tasks3/` | study 2 and study 3 chains per zone (`Z1`–`Z4`, steps `T0`–`T4`): statements, hidden and consumer tests, sanity records |
| `tests/` | harness unit tests and fixtures |
| `docs/` | specs, plans, pilot reports, run logs, rubrics, results reports; `docs/harness.md` is the harness's original setup guide |
| `out/` | phase 1 tables (`tables*.md`, `summary.json`, `hard/`, `pooled/`), `out/study2/`, `out/study3/` (registered tables, design review, labels, kappa, ratchet calibration, trace reads) |
| `data/study2-steps.jsonl` | one row per study-2 step (768): agent, arm, zone, chain, step, model, status, correctness, missed copy, T2 reuse label, consumers passed, carried defects, tokens, turns, tool calls, wall time, lines changed, duplication before/after |
| `data/study3-steps.jsonl` | one row per study-3 step (1,632): the study-2 fields plus ratchet fields (firing, trips, kind), rule citation, gaming flags, and for T0 the probe and inconsistency-test outcomes |
| `data/diffs/<study>/<agent>/<arm>/<zone>/<chain>/<step>.patch` | each step's diff as the agent left it |
| `data/review3/scores/`, `data/review3/scores2/` | judge scores per blind packet (first pass, second pass) |
| `data/review3/scores_sol/` | cross-family judge (GPT-6.1 Sol via Codex) on the 480 chain packets; `scripts/study3_cross_judge*.py`, `out/study3/cross_judge.md` |
| `data/review3/mapping.json` | packet id → `{kind, agent, cond, zone, chain, step, step_kind}` |

Agents are `claude` (Sonnet 5.5), `haiku` (Haiku 5.5) and `codex` (gpt-6-luna). In the
step rows `arm` is the condition (`R`/`F` in study 2; `R`/`RG`/`RL`/`RC` in study 3).

## Reproducing

```bash
uv sync --extra dev
uv run pytest -q                         # harness unit tests, no Docker or network
```

One unit test (`test_issue_tasks.py::test_eligible_when_reference_changes_a_function_with_a_db_write`)
expects the TypeScript function parser from the Actual checkout (`aa substrate fetch` +
`yarn install`); without it the harness falls back to a brace-matching parser and that test
fails.

The design review, its labels and the kappa are rebuilt from the published judge scores
alone (this reproduces `out/study3/design_review3.md`, `design-labels.json` and
`design-kappa.json` byte for byte):

```bash
uv run python scripts/study3_design_review.py \
  --review data/review3 --mapping data/review3/mapping.json
```

Running the study needs Docker, Node 24.18.1 with Yarn 4 (Actual's `.nvmrc`), a Claude
Code login (`claude setup-token`, read from `~/.aa-claude-token`) and a Codex login
(`~/.codex/auth.json`). Details in `docs/harness.md`.

```bash
uv run aa substrate fetch                 # Actual at substrate/BASE -> work/actual-base
uv run aa variant build R && uv run aa variant install R
uv run aa image build-study3              # loot-core images for R, RG, RL, RC -> out/study3/images.json
uv run aa chain run --agent claude --study 3      # -> runs3/ (also --agent haiku, --agent codex)
uv run aa chain evaluate --all --study 3          # result.json per step
uv run aa chain packets --study 3                 # blind review packets -> work/review3
uv run python scripts/study3_design_review.py     # after the judges have scored the packets
uv run aa tables3 --labels out/study3/design-labels.json --kappa out/study3/design-kappa.json
```

`aa tables3` reads the full run directories (`runs3/`, and `runs2/` for the F column),
which are not published; the step-level numbers it aggregates are in
`data/study3-steps.jsonl`.

## What is omitted, and why

- **Agent transcripts** (`transcript.jsonl`), stderr logs and evaluation work trees: tens
  of GB, and they carry the agents' full tool output from the host. The diffs, the
  per-step measures and the trace reads (`out/study3/trace-reads/`) carry what the reports
  quote.
- **Code trees** (`work/`: Actual checkouts, condition variants, review packets and
  trees): reproducible from `substrate/BASE` and the patches.
- **Docker images**: rebuilt by `aa image build-study3`; their digests are in
  `out/study3/images.json`.
- Large run logs (`*.log`) and machine-specific resume scripts.

Local paths have been made relative to the repository or to `~`.
