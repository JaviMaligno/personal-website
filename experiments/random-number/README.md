# Random number from 1 to 10: people vs language models

Data behind the first figure of
[What AI makes you learn](https://www.javieraguilar.ai/en/blog/what-ai-makes-you-learn).

## People

YouGov, adults in Great Britain, fieldwork 12–13 September 2024, n = 2,241.
Open question: *"Think of a random number from 1-10. What number did you think of?"*
([article](https://yougov.com/en-gb/articles/51866-seven-is-the-most-random-number),
[results table](https://ygo-assets-websites-editorial-emea.yougov.net/documents/Internal_Random_Number_240913.pdf)).

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|
| 2% | 4% | 7% | 9% | 8% | 14% | 33% | 14% | 6% | 4% |

## Models

Measured on 2026-10-16 with the same question plus "Answer with the number only.",
100 independent calls per model, provider defaults (no temperature set).

| Model | Via | Answers of 7 |
|---|---|---|
| `haiku` (alias) | Claude Code | 100 / 100 |
| `sonnet` (alias) | Claude Code | 100 / 100 |
| `opus` (alias) | Claude Code | 100 / 100 |
| `claude-sonnet-4-5` | Claude Code | 100 / 100 |
| `claude-haiku-4-5` | Claude Code | 100 / 100 |
| `gpt-6-astra` | Codex | 100 / 100 |
| `gpt-6.1-sol` | Codex | 100 / 100 |
| `gpt-6-luna` | Codex | 100 / 100 |
| `gpt-5.6-sol` | Codex | 100 / 100 |

The aliases resolve to the latest model of each tier on the run date.

**How the calls were made, and what that limits.** These are command-line
tools, not the chat apps most people use, so each model sees some context
besides the question:

- `run_cli.py`: `claude -p` with `--safe-mode`, project settings only, an empty
  working directory, no tools and the system prompt "You are a helpful
  assistant." Claude Code still adds its environment block (working directory,
  platform, date).
- `run_codex.py`: `codex exec` in an empty directory, read-only sandbox,
  ephemeral session. Codex keeps its own agent system prompt, and the
  reasoning effort is the one in the local Codex configuration.

A different interface or temperature could spread the answers somewhat. The
result here is not that the share is exactly 100% everywhere, but that nine
models across two providers converged on the same number every time.

## Reproduce

```bash
python run_cli.py <empty_dir> 100 haiku sonnet opus claude-sonnet-4-5 claude-haiku-4-5
python run_codex.py <empty_dir> 100 gpt-6-astra gpt-6.1-sol gpt-6-luna gpt-5.6-sol
python figure.py en   # prints the figure as inline SVG
```

Each run writes `results/<via>-<model>.json` with every answer.
