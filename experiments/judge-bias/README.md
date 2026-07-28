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

**Keep the probe set balanced between the two kinds of task.** Each entry declares
`rewards: "elaboration" | "concision"`, and `analyze.py` reports the split by that field
*above* the split by subjectivity, because that is the axis the effect lives on.

This is the pilot's main lesson, and it reframes what the metric is for. The received
claim is "LLM judges equate longer with better". The controlled measurement says something
narrower: judges reward **elaboration**, and the reward **inverts** when the task's
implicit success criterion is compression — on summarization the short variant won even
though every variant preserved all the source numbers, with judges citing "condensed form"
against "full paraphrase" in their own reasons. Nobody told them the summary had a length
limit; the word "summarize" was enough.

So "watch out for length bias" is the wrong instruction — on an explanation task the
longer answer plausibly *was* better and penalising it would be the error. The right
question is whether your task rewards elaboration or compression, and whether your judge
inferred the same thing from the prompt you gave it. That is a **Dimension** question in
the three-decisions sense, not a bias to correct away.

An unbalanced probe set hides this completely: the pilot ran 2 elaboration tasks against 1
concision task, and with one more elaboration task the aggregate would have read "long
wins 100%" with the reversal invisible. `tasks-length.json` is balanced 3/3.

## Running it across families — the actual experiment

This is the run that answers the original question. Everything in `results/` so far is a
within-family pilot that cannot.

Needs API keys; no other dependencies (stdlib only, Python 3.10+).

```bash
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... XAI_API_KEY=... GEMINI_API_KEY=...

python3 run.py \
  --generators anthropic:<model> openai:<model> xai:<model> \
  --judges     anthropic:<model> openai:<model> xai:<model> \
  --out results/cross-family.json

python3 analyze.py results/cross-family.json
```

Model ids are `<provider>:<model>`; the provider prefix is what routes the call. Pick
current model ids at run time rather than trusting any hardcoded here.

### …or through one Azure AI Foundry subscription

Getting three vendors' keys is the boring half of this experiment. Azure serves all
three, so `providers.py` treats Azure as a *transport*: keep the vendor in the model
id and set the endpoints, and the same command runs unchanged.

```bash
export AZURE_OPENAI_ENDPOINT=https://<resource>.cognitiveservices.azure.com
export AZURE_OPENAI_KEY=...       # serves openai: and xai: ids
export AZURE_ANTHROPIC_ENDPOINT=https://<resource>.cognitiveservices.azure.com
export AZURE_ANTHROPIC_KEY=...    # serves anthropic: ids

python3 run.py \
  --generators openai:gpt-5.5 xai:grok-4.3 anthropic:claude-sonnet-4-6 \
  --judges     openai:gpt-5.5 xai:grok-4.3 anthropic:claude-sonnet-4-6 \
  --out results/cross-family.json
```

The model name becomes the Azure *deployment* name, so name deployments after their
models. Four things Azure will teach you the slow way:

1. **The two routes are not interchangeable.** OpenAI and xAI models answer on
   `/openai/v1/chat/completions`; Anthropic models 404 there and answer on the native
   `/anthropic/v1/messages` instead. Hence two endpoint variables, not one.
2. **Deploying an Anthropic model needs an undocumented `modelProviderData` block**
   (`organizationName`, `countryCode`, `industry`) that the portal and the CLI do not
   expose — and on a freshly created resource the request can still be rejected as
   "unusual activity". Budget time for this, or reuse a resource that already has a
   Claude deployment.
3. **`gpt-5.5` refuses `temperature=0`** — only its default is accepted. The adapter
   detects the 400, drops the parameter, and says so. It is not a knob you can win.
4. **Reasoning models spend the output budget before they answer.** `grok-4.3` burns
   ~350 tokens of reasoning on one comparison, so the judge budget defaults to 1024
   (`--judge-max-tokens`); at 512 the verdict JSON can get truncated into nothing.

Four things to get right, learned the hard way in the pilot:

1. **Generators and judges must overlap.** Self-preference can only be measured for a
   model that both produces and judges. Pass the same three ids to both flags.
2. **Match capability tiers.** In the pilot, inter-judge agreement tracked the capability
   gap more strongly than task subjectivity did. Comparing a frontier model against a
   small one will produce a "family effect" that is really a capability effect. Use each
   vendor's comparable tier.
3. **Do not pass `--skip-length`.** The uncontrolled longer-wins rate is the single most
   misleading number the harness produces.
4. **The task set is already sized for this.** `tasks.json` holds 5 tasks per subjectivity
   level (15 total) and `tasks-length.json` holds 6 probes balanced 3/3 by what they
   reward. With 3 generators that is 45 comparisons × 2 orders × 3 judges = 270 main
   judgments plus 108 length-control ones. Budget accordingly, and don't shrink the set to
   save tokens — the pilot's numbers were underpowered at 6 tasks, which is why it reports
   bootstrap CIs and calls most of them directional.

Then compare against `results/pilot-findings.md`: the interesting question is which of the
pilot's within-family findings survive when the judges come from different vendors.

**That run now exists**: `results/cross-family.json` (gpt-5.5, grok-4.3,
claude-sonnet-4-6 — 270 judgments + 108 length-control), written up in
`results/cross-family-findings.md`. Short version: the ranking changes with the judge,
self-preference is real in all three families and scales with subjectivity, position bias
turns out to be a property of one specific judge rather than a universal, and the pilot's
"the length reward inverts on compression tasks" was one model's habit.

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
- **Small.** It ran on 6 tasks + 3 length probes, 162 judgments. Directional, not
  conclusive — and smaller than the set now in `tasks.json`, which grew in response to it.
  The pilot scripts filter to the tasks their raw data covers, so re-running
  `pilot/assemble.py` still reproduces these numbers.

Findings and the notes for the eventual article: `results/pilot-findings.md`.
Source discussion: `docs/research/llm-judge-bias-conversation.md`.

## Status

- [x] Harness, provider-agnostic, stdlib only
- [x] Within-family pilot (Opus 5 / Sonnet 5 / Haiku 4.5), 162 judgments
- [x] Length control, with both elaboration- and concision-rewarding probes
- [x] Expanded task set — 15 main (5 per level), 6 length probes (3/3 by reward)
- [x] **Cross-family run** — 3 vendors through Azure, 378 judgments, 0 unparseable
      (`results/cross-family-findings.md`)
- [ ] Same-tier rerun — the Anthropic seat is a generation behind the other two, because
      that was the only Claude quota available. Redo it when a current Claude deploys.
- [ ] Article
