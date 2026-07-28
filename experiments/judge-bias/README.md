# Judge-bias experiment

Does the model you pick as an LLM judge change the ranking it produces?

This harness measures four things that are usually asserted rather than measured:

| Metric | Question | Unbiased value |
|---|---|---|
| **slot-A rate** | Does the judge prefer whichever answer it reads first? | 50% |
| **flip rate** | How often does swapping the two slots reverse the verdict? | 0% |
| **self-preference delta** | Does a judge favour its own output *more than other judges do*? | 0pp |
| **longer-wins rate** | Does the longer answer win? | 50% |

Plus inter-judge agreement (Cohen's kappa) broken down by how subjective the task is.

## The one metric that needs explaining

Self-preference is easy to measure badly. "Judge X picked X's own answer 70% of the
time" proves nothing — X's answer may simply be better. The claim only holds if X
picks its own answer *more often than its peers pick that same answer, on the same
pairs*. That difference is the `delta` column, and it is the only self-preference
number here worth quoting.

## Design

- **Pairwise, not 1–10 scores.** Absolute rubric scores are far less stable.
- **Blinded.** Judges never see model identities; `build_batches.py` asserts that no
  model name appears in any judge prompt.
- **Both presentation orders.** Every comparison is judged twice with the slots
  swapped. The reversal rate *is* the position bias — it is measured, not assumed.
- **Ties allowed.** Forcing a binary choice between two equally good answers
  manufactures coin flips that then get misread as position bias.
- **Three subjectivity levels** in `tasks.json` (`low` / `medium` / `high`), because
  the interesting hypothesis is that judge choice matters more as subjectivity rises.

## Running it across families

Needs API keys; no other dependencies (stdlib only).

```bash
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=...

python3 run.py \
  --generators anthropic:<model> openai:<model> gemini:<model> \
  --judges     anthropic:<model> openai:<model> gemini:<model> \
  --out results/cross-family.json

python3 analyze.py results/cross-family.json
```

Generators and judges are separate lists, but they should overlap: self-preference
can only be measured for a model that both produces and judges.

## The pilot in `results/`

`results/pilot-claude-family.json` is a **within-family** run: Opus 5, Sonnet 5 and
Haiku 4.5 as both generators and judges. It was produced in an environment with no
provider API keys, so `pilot/build_batches.py` and `pilot/assemble.py` drive the same
protocol through Claude Code subagents and emit the identical results schema.

Read it with its limits in mind:

- **Within-family only.** It can say something about self-preference between *tiers*
  of one family. It cannot say anything about GPT-vs-Claude-vs-Gemini, which is the
  question actually worth answering. Run `run.py` with real keys for that.
- **Agent-mediated.** Every model carried a coding-agent system prompt rather than
  being called bare, which shifts style.
- **Batched contexts.** Each judge saw 18 comparisons in one context. The two
  presentation orders were separate contexts, so the position measurement is clean,
  but comparisons within a batch were not fully independent.
- **No execution.** Judges were forbidden from running code, so even the
  low-subjectivity tasks were graded by reading. That is deliberate — the point is to
  measure the *LLM judge*, not to replace it with a test runner (which, where you can,
  you should).
- **Small.** 6 tasks, 18 comparisons, 108 judgments. Directional, not conclusive.

Source discussion: `docs/research/llm-judge-bias-conversation.md`.
