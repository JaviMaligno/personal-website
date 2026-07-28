# Pilot findings — within-family (Opus 5 / Sonnet 5 / Haiku 4.5)

6 tasks × 3 generators × 3 judges × 2 presentation orders = 108 judgments, 18 comparisons,
plus 54 length-control judgments. Blinded, pairwise, ties allowed. See `../README.md` for
the design and its limits.

> **The task set has since grown.** This pilot ran on 2 tasks per subjectivity level and 3
> length probes. `tasks.json` now holds 5 per level (15) and `tasks-length.json` holds 6,
> balanced 3 elaboration-rewarding / 3 concision-rewarding, precisely because of §3 below.
> The pilot scripts filter to the tasks their raw data actually covers, so these numbers
> stay reproducible; the cross-family run will use the full set and is not comparable
> task-for-task.

**This is a pilot.** n is small enough that most of what follows is a hypothesis for the
cross-family run, not a result. Where a number is not distinguishable from noise, it says so.

## Overall ranking

| Generator | Win score | Mean words (low / med / high subjectivity) |
|---|---|---|
| opus-5 | 63.9% | 51 / 85 / 118 |
| sonnet-5 | 59.7% | 79 / 77 / 87 |
| haiku-4.5 | 26.4% | 53 / 74 / 76 |

All three judges separate Haiku from the other two cleanly. Opus and Sonnet are close.

## 1. Position bias — not detected

| Judge | slot-A rate | exact binomial vs 50% | flip rate |
|---|---|---|---|
| opus-5 | 55.2% (16/29) | p = 0.71 | 5.6% |
| sonnet-5 | 45.8% (11/24) | p = 0.84 | 5.6% |
| haiku-4.5 | 55.9% (19/34) | p = 0.61 | 22.2% |

No judge shows a preference for the first slot. This is worth stating plainly because
"randomize the order" is repeated as though position bias were universal; at this scale,
in this family, on these tasks, it is not there.

The **flip rate** is the more interesting column. Opus and Sonnet reverse themselves on
about 1 comparison in 18; Haiku on 1 in 4.5 (p = 0.087 against the other two combined —
suggestive, not significant). Three of Haiku's four flips are on `med-extract`, a task
with a checkable correct answer. The weakest model is not a *biased* judge so much as an
*unstable* one, and instability concentrates where the task has a right answer it cannot
reliably see.

## 2. Self-preference — one suggestive delta, one pointing the other way

| Judge | Own rate | Peers on same pairs | Delta | Bootstrap 95% CI |
|---|---|---|---|---|
| opus-5 | 75.0% | 58.3% | **+16.7pp** | [+2.1, +31.2] |
| sonnet-5 | 50.0% | 64.6% | −14.6pp | [−29.2, +2.1] |
| haiku-4.5 | 29.2% | 25.0% | +4.2pp | [−14.6, +22.9] |

Opus's interval nominally excludes zero — but n = 12 paired cells, it is one of three
tests, and the lower bound is +2.1pp. Treat it as a hypothesis worth powering properly,
not as a measured effect.

Sonnet is the useful counterweight: it rates its own output **lower** than its peers rate
it. If self-preference were a mechanical property of judging your own family's style, it
should not reverse sign between two tiers of that same family. Within-family self-
preference is not a reliable phenomenon at this scale.

Note also how misleading the raw column is on its own. Opus picks its own answer 75% of
the time — a number that reads like damning bias until you see that its peers pick that
same answer 58% of the time. Most of the 75% is that Opus's answers are simply rated best
by everyone.

## 3. Length — the naive number is uninterpretable; the controlled one inverts

### The number everyone quotes

| Judge | Longer answer wins | n |
|---|---|---|
| opus-5 | 80.0% | 25 |
| sonnet-5 | 85.0% | 20 |
| haiku-4.5 | 50.0% | 30 |

80–85% looks like a textbook length bias. It is not usable evidence: in this task set the
models that write longest are also the models every judge ranks highest, so length and
quality are confounded and the number cannot distinguish "judges reward verbosity" from
"the verbose answers were better".

### The control

`tasks-length.json` holds model and task fixed and varies only the target length. The two
variants share an identical base prompt and differ by one appended sentence ("Answer in
roughly N words"). The judge is shown the **base prompt only** — never the length
directive — so it cannot be grading compliance with a word count it was told about.

Manipulation check: short answers averaged 59 words, long 193, consistently across all
three models.

| Judge | Long wins (controlled) | Flip rate | n |
|---|---|---|---|
| opus-5 | 88.9% | 0% | 9 |
| sonnet-5 | 66.7% | 0% | 9 |
| haiku-4.5 | 83.3% | 33.3% | 9 |

So the preference survives the control — but the aggregate hides the actual finding.

### Broken down by task, it inverts

| Length-probe task | Long wins | Detail |
|---|---|---|
| `len-index` (explain a DB index) | **100%** | 9/9, unanimous across all judges and models |
| `len-idempotency` (explain idempotency to a PM) | **100%** | 9/9, unanimous |
| `len-summarize` (summarize, preserving numbers) | **38.9%** | short preferred; Haiku flipped on all 3 |

On the two explanation tasks the verdict is unanimous — 18 out of 18 comparisons, every
judge, every model, both orders, zero flips. That is about as strong as a signal gets at
this n.

On summarization it reverses. And not because the short answers were worse: **every
variant, short and long, preserved all 9 numbers from the source.** The judges' stated
reasons are explicit about why they went short — "genuinely condensed form, whereas B is
essentially a full paraphrase", "reads as narrative retelling rather than a summary",
"unnecessary editorializing".

Split by what the task rewards rather than by subjectivity, the same data reads:

| What the task rewards | Long wins | n |
|---|---|---|
| elaboration | **100.0%** | 18 |
| concision | **38.9%** | 9 |

Note the unbalanced n — the pilot's probe set happened to be 2 elaboration tasks against
1 concision task. Had it been 3 elaboration tasks, the aggregate would have read "judges
prefer longer answers 100% of the time" and the reversal would have been invisible.
`tasks-length.json` is now balanced 3/3, and `analyze.py` reports this split above the
subjectivity one, because this is the axis the effect actually lives on.

### What this actually means

The received claim is "LLM judges equate longer with better". The controlled measurement
says something more specific and more useful: **judges reward elaboration, and that
reward inverts when the task's implicit success criterion is concision.** Nobody told the
judges the summary had a length limit — the word "summarize" was enough for them to treat
brevity as part of the goal.

Which reframes the practical advice. "Watch out for length bias" is the wrong instruction,
because on explanation tasks the longer answer plausibly *was* better and penalising it
would be wrong. The right instruction is to know whether your task rewards elaboration or
compression, and to check that your judge has inferred the same thing from the prompt you
gave it — which is a `Dimension` question in the three-decisions sense, not a bias to
correct away.

Note also that Haiku flipped on all three summarization comparisons — the same pattern as
in §1: its instability concentrates on the task where the right answer is contested.

## 4. Inter-judge agreement (Cohen's kappa)

| Judge pair | low | medium | high |
|---|---|---|---|
| opus-5 vs sonnet-5 | +0.70 | +0.36 | +1.00 |
| opus-5 vs haiku-4.5 | +0.50 | +0.11 | −0.20 |
| sonnet-5 vs haiku-4.5 | +0.25 | −0.33 | −0.20 |

The expected pattern — agreement decaying as subjectivity rises — shows up for the two
pairs involving Haiku, and inverts for Opus vs Sonnet, whose +1.00 on high subjectivity
rests on 6 cells and should not be read as meaningful.

The stronger reading of this table is not about subjectivity at all: **capability gap
predicts disagreement better than task type does.** The two frontier tiers agree with each
other; both agree less with Haiku; and Sonnet vs Haiku is at or below chance on medium and
high tasks. If that holds up cross-family, the practical advice changes shape — a judge
panel's value would come from combining judges of *comparable* capability, and adding a
weaker judge would inject noise rather than diversity.

## What this pilot cannot tell you

It is within one family, so it says nothing about the actual question — whether a GPT
judge favours GPT-shaped answers over Claude-shaped ones. Every model here also ran under
a coding-agent system prompt rather than bare, which shifts style. And 6 tasks is small.

Carry forward to the cross-family run: more tasks per subjectivity level, more length-probe
tasks split between elaboration-rewarding and concision-rewarding phrasings, and judges of
comparable capability tier so the capability effect does not swamp the family effect.

## Article notes (not written yet — waiting on the cross-family data)

Working angle: the sequel to `llm-as-judge-three-decisions`. That post covered *what* you
score; this one covers *who* scores it, and what happens when you actually measure the
things everyone repeats about judges.

The spine, in the order the evidence supports:

1. **Position bias didn't show up.** Universally-repeated advice, absent at this n.
   Randomizing order is still right — it's free — but the justification usually given
   for it isn't what the data shows.
2. **The real failure mode was instability, not bias.** Haiku reversed itself 4× more
   often than the frontier tiers, concentrated on tasks with a contested right answer.
   A judge that can't reproduce its own verdict is a worse problem than one that leans.
3. **Self-preference needs a delta, not a rate.** Opus picking its own answer 75% of the
   time reads as damning until you see peers pick it 58%. And Sonnet's delta goes
   *negative*, which is hard to square with a mechanical style-recognition story.
4. **Length bias is the best story.** The naive 80–85% is uninterpretable; the controlled
   version is unanimous *in both directions* depending on whether the task rewards
   elaboration or compression. This is the section that earns the post — it shows a
   commonly-cited statistic being wrong in a way you can only see by building the control.
5. **Agreement tracked capability gap more than subjectivity**, which if it survives
   cross-family would change the panel-of-judges advice: pair judges of comparable
   capability rather than assuming more judges = more robustness.

Honesty requirements for the draft:
- State the within-family limitation up front, not in a footnote — until the cross-family
  run exists, this measures tiers, not families, and therefore does not answer the
  question that started it.
- The claims inherited from `docs/research/llm-judge-bias-conversation.md` about prior
  work are uncited. Either find the actual papers or drop the appeals to literature and
  stand on the measurements.
- n is small. Every number above wants the word "pilot" near it.
