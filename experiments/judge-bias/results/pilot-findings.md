# Pilot findings — within-family (Opus 5 / Sonnet 5 / Haiku 4.5)

6 tasks × 3 generators × 3 judges × 2 presentation orders = 108 judgments, 18 comparisons.
Blinded, pairwise, ties allowed. See `../README.md` for the design and its limits.

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

## 3. Length — measured, and uninterpretable by design

| Judge | Longer answer wins | n |
|---|---|---|
| opus-5 | 80.0% | 25 |
| sonnet-5 | 85.0% | 20 |
| haiku-4.5 | 50.0% | 30 |

80–85% looks like a textbook length bias. It is not usable evidence, because in this
task set the models that write longest are also the models every judge ranks highest.
Length and quality are confounded, so the number cannot distinguish "judges reward
verbosity" from "the verbose answers were better".

This is the pilot's clearest methodological lesson, and it applies to the statistic as it
is usually quoted in blog posts: a longer-wins rate without a length control measures
almost nothing. **Fix before the cross-family run:** add paired tasks where the same
content is produced at two lengths, so length varies with quality held fixed.

One concrete case cuts against the bias reading. On `med-summarize` the prompt capped the
answer at 100 words; Opus wrote 104, Sonnet 91, Haiku 84. Every judge — including Opus
itself — preferred Sonnet over Opus on that comparison. The judges did penalise the
over-long answer when a stated constraint made length checkable.

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

Carry forward to the cross-family run: the length control above, more tasks per
subjectivity level, and judges of comparable capability tier so the capability effect does
not swamp the family effect.
