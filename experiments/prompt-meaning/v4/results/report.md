# Real-project handoff replay

Two maintenance areas from one existing research project; four generated chains. Review proposals are constructed probes, not historical PRs. Coinage provenance is unverified. Repeated decisions are not independent discoveries.

Calls: 40; attempts: 40; invalid reviews: 0; invalid handoffs: 2.

| Model | Context | Correct | Wrong | Abstain | Valid / expected |
|---|---|---:|---:|---:|---:|
| claude-opus | first | 63 | 0 | 1 | 64 / 64 |
| claude-opus | full | 64 | 0 | 0 | 64 / 64 |
| claude-opus | last | 64 | 0 | 0 | 64 / 64 |
| claude-opus | opaque | 63 | 0 | 1 | 64 / 64 |
| gpt-sol | first | 63 | 0 | 1 | 64 / 64 |
| gpt-sol | full | 64 | 0 | 0 | 64 / 64 |
| gpt-sol | last | 62 | 0 | 2 | 64 / 64 |
| gpt-sol | opaque | 62 | 2 | 0 | 64 / 64 |

## Stable errors introduced after first handoff: 0


## Stable errors already in first handoff: 0


## Stable decisions changed by opaque renaming: 1

- geometry--gpt-sol / gpt-sol / p04: Treat candidate code that cannot execute its step function as gate_failing rather than invalid.
  {"full": ["reject", "reject"], "first": ["reject", "reject"], "last": ["needs_context", "needs_context"], "opaque": ["reject", "reject"]}

## All routine probes pass, but a boundary fails: 0


## Handoff lengths

- dose--gpt-sol h2: 519 words
- dose--claude-opus h1: 0 words
- geometry--gpt-sol h1: 641 words
- geometry--claude-opus h1: 0 words
- geometry--gpt-sol h2: 505 words
- dose--gpt-sol h1: 735 words
- geometry--gpt-sol h3: 367 words
- dose--gpt-sol h3: 401 words

## Accounting

Wall time: 430.8 s. Reference cost only, using prior-run rates:
- claude-opus: 287141 input, 33290 output tokens; $2.267955.
- gpt-sol: 184965 input, 20663 output tokens; $1.153120.
