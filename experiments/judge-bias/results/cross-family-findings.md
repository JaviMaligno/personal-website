# Cross-family findings — GPT-5.5 / Grok-4.3 / Claude Sonnet 4.6

15 tasks × 3 generators × 3 judges × 2 presentation orders = 270 judgments, 45 comparisons,
plus 108 length-control judgments. Blinded, pairwise, ties allowed. Zero unparseable
verdicts. See `../README.md` for the design and `pilot-findings.md` for the within-family
pilot this was built to test.

Run: `results/cross-family.json`, served through Azure AI Foundry (swedencentral).
Reproduce the tables below with `python3 analyze.py results/cross-family.json`.

**This is the run the harness was built for.** The pilot could only compare tiers of one
family; this one compares families. Three of the pilot's five findings survive, one
reverses, and one turns out to have been a single model's habit rather than a law.

## 1. The judge changes the ranking

| Generator | Overall | by gpt-5.5 | by grok-4.3 | by claude-sonnet-4-6 | Mean words |
|---|---|---|---|---|---|
| gpt-5.5 | 66.1% | **85.0%** | 58.3% | 55.0% | 66 |
| claude-sonnet-4-6 | 45.0% | 35.0% | 38.3% | **61.7%** | 85 |
| grok-4.3 | 38.9% | 30.0% | **53.3%** | 33.3% | 55 |

Three judges, three different orderings:

- gpt-5.5 as judge: gpt > claude > grok
- grok-4.3 as judge: gpt > grok > claude
- claude-sonnet-4-6 as judge: claude > gpt > grok

Every judge scores its own output highest of the three columns in its row, and every judge
ranks itself above where the other two put it. The one thing they agree on is that
gpt-5.5's answers are good: it wins under two of the three judges and is second under the
third.

This is the symptom. The rest of this document is the diagnosis.

## 2. Position bias — real, large, and a property of one judge

| Judge | slot-A rate | exact binomial vs 50% | flip rate |
|---|---|---|---|
| gpt-5.5 | 52.6% | p = 0.73 | 8.9% |
| claude-sonnet-4-6 | 51.5% | p = 0.90 | 20.0% |
| grok-4.3 | **72.4%** | **p < 0.001** | **35.6%** |

The pilot found no position bias anywhere and said so plainly. That was not wrong, but it
was a statement about three models from one family. Cross-family, one judge in three has a
position bias big enough to swamp everything else: grok-4.3 picks whatever it reads first
almost three times in four, and reverses itself on more than a third of comparisons when
the slots are swapped.

And it gets worse exactly where you would least want it to:

| grok-4.3 | low subjectivity | medium | high |
|---|---|---|---|
| slot-A rate | 64% (p = 0.29) | 75% (p = 0.023) | 77% (p = 0.005) |
| flip rate | 13% | 40% | 53% |

On the subjective third of the task set, grok-4.3 reverses its own verdict on **more than
half** of all comparisons. A judge that cannot reproduce its own answer when you swap two
paragraphs is not measuring the answers. The other two judges stay flat across
subjectivity (gpt-5.5: 55/54/50%, claude: 56/40/57%, none significant).

So "randomize the presentation order" survives as advice — but the reason to do it is not
that all judges lean first. It is that **some do, catastrophically, and you cannot tell
which without measuring**.

## 3. Self-preference — the pilot's ambiguous result becomes unambiguous

| Judge | Own rate | Peers, same pairs | Delta | Bootstrap 95% CI | vs neutral judge only |
|---|---|---|---|---|---|
| gpt-5.5 | 85.0% | 56.7% | **+28.3pp** | [+16.7, +40.0] | +21.7pp [+8.3, +35.0] |
| claude-sonnet-4-6 | 61.7% | 36.7% | **+25.0pp** | [+12.5, +36.7] | +15.0pp [+0.0, +28.3] |
| grok-4.3 | 53.3% | 31.7% | **+21.7pp** | [+9.2, +35.8] | +13.3pp [−1.7, +30.0] |

All three deltas are positive, all three intervals exclude zero, and the effect is roughly
the same size in all three families. Within one family the pilot got +16.7, −14.6 and
+4.2pp — a mess that pointed nowhere. Across families it is a straight line.

**The "vs neutral" column is the honest number.** With three judges that double as the
three generators, the peer set for a comparison between A and B contains the *opponent*,
whose own self-preference pushes the other way and inflates A's measured delta. Restricting
the baseline to the judge with no stake in the pair cuts every delta by roughly a third —
and the effect still survives for gpt-5.5 and (marginally) for claude-sonnet-4-6, while
grok-4.3's interval now touches zero. Quote the neutral-baseline number, not the headline
one.

### Where it lives: self-preference scales with subjectivity

| Judge | low | medium | high |
|---|---|---|---|
| gpt-5.5 | +17.5pp | +25.0pp | +42.5pp |
| grok-4.3 | +7.5pp | +27.5pp | +30.0pp |
| claude-sonnet-4-6 | −2.5pp | +30.0pp | +47.5pp |

This is the cleanest result in the run, and it is the one the original intuition predicted:
on tasks with a checkable answer — parse this string, fix this bug, merge these intervals —
self-preference is small or absent (claude-sonnet-4-6 is at −2.5pp, i.e. slightly *harder*
on itself than a neutral judge is). On tasks where the criterion is taste — error copy,
postmortem tone, an explanation for a PM — it reaches +30 to +48pp.

The practical reading: **a judge from the same family as one of the systems you are
comparing is close to harmless on objective work and close to unusable on subjective work.**

## 4. Length — the elaboration effect replicates perfectly; the inversion does not

### The confounded number, and why it is worthless in both directions

| Judge | Longer answer wins | n |
|---|---|---|
| gpt-5.5 | 48.6% | 72 |
| grok-4.3 | 48.6% | 72 |
| claude-sonnet-4-6 | 64.6% | 65 |

In the pilot this number read 80–85% and looked like a textbook length bias. Here it reads
~50% and looks like no length bias at all. **Both readings are wrong**, and for the same
reason: length and quality are confounded in the generator pool, and which way the number
points depends on whether the verbose models happen to be the good ones. In the pilot they
were. Here the most verbose model (claude-sonnet-4-6, 85 words mean) is not the
best-ranked one, so the effect cancels out. Anyone quoting this statistic is quoting an
accident of their model lineup.

### The control

Same model, same task, two target lengths, judge shown the base prompt only. Manipulation
check: short variants averaged 46 words, long 174, consistently across all three models.

| Judge | Long wins (controlled) | Flip rate | n |
|---|---|---|---|
| gpt-5.5 | 77.8% | 11.1% | 18 |
| grok-4.3 | 86.1% | 16.7% | 18 |
| claude-sonnet-4-6 | 88.9% | 5.6% | 18 |

So the preference is not just real, it is **stronger than the uncontrolled number suggests**
— the exact opposite of the direction people assume the confound runs.

### Split by what the task rewards

| What the task rewards | Long wins | n |
|---|---|---|
| elaboration | **100.0%** | 27 |
| concision | 68.5% | 27 |

| Length probe | Rewards | Long wins |
|---|---|---|
| `len-index` (explain a DB index) | elaboration | 100% |
| `len-idempotency` (explain idempotency to a PM) | elaboration | 100% |
| `len-queue-tradeoff` (explain a queue tradeoff) | elaboration | 100% |
| `len-commit` (write a commit message) | concision | 83.3% |
| `len-summarize` (summarize, preserving numbers) | concision | 72.2% |
| `len-error-copy` (write an error message) | concision | 50.0% |

**The elaboration half is unanimous: 27 out of 27, every judge, every generator, both
orders.** Add the pilot's 18 and it is 45 for 45 across six different judges from three
families. If anything in this experiment deserves to be called a law, it is that one.

**The concision half does not replicate.** The pilot reported a reversal — judges preferring
the short answer on summarization, 38.9% long-wins — and read it as judges inferring the
task's implicit goal. Cross-family, the same probe reads 72.2% long, and the concision
category as a whole sits at 68.5%: above chance, not below it. Broken down by judge, the
pilot's effect was essentially one model's habit:

| Judge | elaboration | concision |
|---|---|---|
| gpt-5.5 | 100% | 55.6% |
| grok-4.3 | 100% | 72.2% |
| claude-sonnet-4-6 | 100% | 77.8% |
| *pilot:* opus-5 | 100% | 66.7% |
| *pilot:* sonnet-5 | 100% | **0.0%** |
| *pilot:* haiku-4.5 | 100% | 50.0% |

Six judges, one of which (sonnet-5) preferred the short answer every single time and
dragged the pilot's aggregate below 50%. The corrected claim is narrower and less
satisfying than the pilot's: **judges reward elaboration everywhere, and the reward merely
weakens — with wide variance between judges — when the task's implicit criterion is
compression.** Only one judge out of six actually inverted.

That still matters for practice, and it still lands on the same instruction: the number you
get depends on whether your probe set is balanced, and a single judge can carry the
headline. But the pilot's "the reward inverts" was an over-claim, and this run is what
retires it.

## 5. Agreement collapses to chance on subjective tasks

| Judge pair | low | medium | high |
|---|---|---|---|
| gpt-5.5 vs grok-4.3 | +0.41 | +0.32 | −0.01 |
| gpt-5.5 vs claude-sonnet-4-6 | +0.31 | +0.35 | −0.03 |
| grok-4.3 vs claude-sonnet-4-6 | +0.20 | +0.02 | +0.05 |

The expected pattern, which the pilot could not cleanly show, is here: agreement decays
monotonically as subjectivity rises, and on the high-subjectivity tasks **all three pairs
are indistinguishable from chance**. Cohen's kappa of −0.03 means two frontier judges
grading the same subjective comparisons agree exactly as often as two coin flips would.

The pilot's alternative hypothesis — that the capability gap, not the task type, predicts
disagreement — is not supported here. The two pairs involving the strongest and the weakest
model in the lineup (gpt-5.5 vs grok-4.3, gpt-5.5 vs claude-sonnet-4-6) agree *more* than
the pair that excludes the strongest.

## What this run still cannot tell you

- **One model per family, and the tiers are not matched.** Azure had no quota for
  `claude-opus-5` or `claude-sonnet-5` at run time, so the Anthropic seat is
  `claude-sonnet-4-6` — a generation behind the other two. The obvious worry is that a
  capability gap is being read as a family effect. Two things push back: the older model is
  *not* the lowest-ranked overall (grok-4.3 is), and the self-preference deltas are within
  7pp of each other across all three families. But the
  clean version of this experiment runs same-tier models, and this is not it.
- **gpt-5.5 did not run at temperature 0**, because it refuses to: the API accepts only its
  default. The other two ran at 0. Some part of gpt-5.5's flip rate is sampling noise the
  others did not have.
- **One run, no repeats.** The two presentation orders give a within-comparison stability
  measure, but nothing separates judge instability from run-to-run sampling.
- **No execution.** Even the low-subjectivity tasks were graded by reading, deliberately —
  the point is to measure the judge, not to replace it with a test runner. Where you *can*
  run the tests, run the tests.
- **15 tasks and 6 length probes.** Bigger than the pilot by 2.5×, still small. Every
  interval here is wide.
- **Everything was served through Azure AI Foundry**, so any provider-side system prompt or
  content filtering applies uniformly but is not identical to hitting each vendor's own API.

## The five claims, and what happened to each

| Pilot claim | Cross-family verdict |
|---|---|
| Position bias didn't show up | **Reversed.** One judge in three has it badly, and it grows with subjectivity. |
| The real failure mode is instability, not bias | **Held, and sharpened.** grok-4.3 flips 53% of subjective comparisons. |
| Self-preference needs a delta, not a rate | **Held, and the delta is now unambiguous** — positive in all three families, and it scales with subjectivity. |
| Length bias is the best story: the reward inverts on compression tasks | **Half held.** Elaboration is unanimous at 45/45. The inversion was one model. |
| Agreement tracks capability gap more than subjectivity | **Not supported.** Subjectivity dominates; agreement hits chance on subjective tasks. |
