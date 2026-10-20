# agent-abstractions

Harness for the experiment "do more abstractions + harsh lint constrain coding
agents?": Claude Code and Codex on real Actual Budget (`packages/loot-core`)
tasks under four conditions (A, A+L, A⁺, A⁺+L).

- Spec: `docs/specs/2026-10-05-agent-abstractions-design.md`
- Plan: `docs/plans/2026-10-05-agent-abstractions-plan.md`

## Setup

```bash
uv venv && uv pip install -e '.[dev]'
uv run pytest                      # harness unit tests
```

Actual needs Node 24.18.1 (its `.nvmrc`) and Yarn 4 via corepack. Put that
Node first on `PATH` (e.g. `nvm use 24.18.1`) before any command that runs
`yarn`.

## Substrate and baseline

```bash
uv run aa substrate fetch          # work/actual-base at substrate/BASE (full history)
(cd work/actual-base && yarn install --immutable)
uv run aa suite baseline           # writes work/baseline-A.json
uv run aa variant build <cond>     # work/variants/<cond>: fresh one-commit repo + patches
```

Each condition's patches (`substrate/patches/`, applied in order) are listed in
`aa.config.CONDITION_PATCHES`. Tests that fail on the untouched base for
environmental reasons are listed in `aa.config.EXCLUDED_TESTS`.
`work/baseline-typecheck.txt` records the base `yarn tsgo -b` error count.

`work/` and `runs/` are gitignored.

## Study 2 conditions (R / F)

`docs/study2-variants.md` describes R (repeated) and F (factored); their patches are
`substrate/patches/study2/{r,f}.patch` on top of `lint-script.patch`, frozen at tag
`rf-frozen`.

```bash
uv run aa variant build R && uv run aa variant install R      # same for F
uv run aa suite baseline --cond A --study2                     # seeded A -> work/study2/
uv run aa suite baseline --cond R                              # -> work/study2/baseline-R.json
uv run aa equivalence A R && uv run aa equivalence R F         # 0 differences expected
uv run aa probe2 --conds A,R,F                                 # behavioural probe, identical
uv run aa image build R && uv run aa image build F             # + pinned jscpd
```

## Study 3 arms (R / RG / RL / RC)

`docs/specs/2026-10-10-agent-as-designer-design.md`. Each arm is R plus one lever
(`aa.config.CONDITION_PATCHES`); RC's lever is the T0 step (`tasks3/<zone>/T0/`), not
an image change.

```bash
uv run aa image build-study3        # R, RG, RL, RC rebuilt together, verified;
                                    # image ids + checks -> out/study3/images.json
uv run aa chain run --agent claude --study 3 --pilot --chains 1   # -> runs3-pilot/
uv run aa chain run --agent claude --study 3                      # -> runs3/ (2 chains at once)
uv run aa chain run-one --agent haiku --cond RC --zone Z3 --step T0
uv run aa chain evaluate --all --study 3 --pilot                  # runs3-pilot/; T0 evals run alone
uv run aa chain packets --study 3                                # blind packets, trees, batches -> work/review3
```

Study 3 chains interleave the arms per agent (chain `i`, zone `z`, arm order
`ARMS[(i + k + z) % 4]`, spec amendment 2026-10-11e); an RC chain runs T0 (40 min / 90 turns) and carries its tree into
T1. `--runs` is resolved to an absolute path; study-2 invocations (`--conds R,F`, the
default) still write to `runs2/` exactly as before.
