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

### The length control

The plain `longer-wins rate` is reported but is **not** on its own evidence of length bias.
If the models that write longest are also the ones judges rank highest — which is what
happened in the pilot — length and quality are confounded and the number cannot separate
them.

`tasks-length.json` is the control. It holds model and task fixed and varies only the
target length: the two variants share an identical base prompt and differ by one appended
sentence ("Answer in roughly N words"). The judge sees the **base prompt only**, never the
directive, so it grades which answer is better rather than which one hit a word count it
was told about.

Keep both kinds of probe task in the set. In the pilot the controlled preference was
unanimous for the long variant on explanation tasks and reversed on summarization — a task
set containing only one kind would have produced a confident and wrong headline number.

## Running it across families — the actual experiment

This is the run that answers the original question. Everything in `results/` so far is a
within-family pilot that cannot.

Needs API keys; no other dependencies (stdlib only, Python 3.10+).

```bash
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=...

python3 run.py \
  --generators anthropic:<model> openai:<model> gemini:<model> \
  --judges     anthropic:<model> openai:<model> gemini:<model> \
  --out results/cross-family.json

python3 analyze.py results/cross-family.json
```

Model ids are `<provider>:<model>`; the provider prefix is what routes the call. Pick
current model ids at run time rather than trusting any hardcoded here.

Four things to get right, learned the hard way in the pilot:

1. **Generators and judges must overlap.** Self-preference can only be measured for a
   model that both produces and judges. Pass the same three ids to both flags.
2. **Match capability tiers.** In the pilot, inter-judge agreement tracked the capability
   gap more strongly than task subjectivity did. Comparing a frontier model against a
   small one will produce a "family effect" that is really a capability effect. Use each
   vendor's comparable tier.
3. **Do not pass `--skip-length`.** The uncontrolled longer-wins rate is the single most
   misleading number the harness produces.
4. **Expand the task set first.** 6 main tasks + 3 length probes is thin. The metrics are
   per-judge over ~12–36 observations, which is why the pilot reports bootstrap CIs and
   calls most of its numbers underpowered. Aim for 4–6 tasks per subjectivity level.

Then compare against `results/pilot-findings.md`: the interesting question is which of the
pilot's within-family findings survive when the judges come from different vendors.

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
- **Small.** 6 tasks + 3 length probes, 162 judgments total. Directional, not conclusive.

Findings and the notes for the eventual article: `results/pilot-findings.md`.
Source discussion: `docs/research/llm-judge-bias-conversation.md`.

## Status

- [x] Harness, provider-agnostic, stdlib only
- [x] Within-family pilot (Opus 5 / Sonnet 5 / Haiku 4.5), 162 judgments
- [x] Length control, with both elaboration- and concision-rewarding probes
- [ ] **Cross-family run** — blocked on API keys, see above
- [ ] Expanded task set (4–6 per subjectivity level)
- [ ] Article — deliberately not written until the cross-family data exists
