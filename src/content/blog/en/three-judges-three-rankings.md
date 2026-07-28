---
title: "Three Judges, Three Rankings"
description: "I ran the same 45 blinded comparisons past a GPT, a Grok and a Claude judge. Each produced a different ranking, each favoured its own answers, and the effect scales with how subjective the task is."
pubDate: 2026-07-30
tags: ["AI Agents", "Evals", "LLM", "Research"]
lang: en
translationKey: three-judges-three-rankings
heroImage: "/blog/three-judges-three-rankings.png"
linkedinImage: /blog/judge-bias-self-preference.png
repoUrl: https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias
linkedinLinks:
  - label: "Part 1 — LLM-as-Judge Is Three Decisions"
    url: https://www.javieraguilar.ai/en/blog/llm-as-judge-three-decisions/
  - label: "Zheng et al., Judging LLM-as-a-Judge (MT-Bench)"
    url: https://arxiv.org/abs/2306.05685
  - label: "Panickssery et al., LLM Evaluators Recognize and Favor Their Own Generations"
    url: https://arxiv.org/abs/2404.13076
---

[An earlier post here](https://www.javieraguilar.ai/en/blog/llm-as-judge-three-decisions/) argued that LLM-as-judge is three decisions — context, unit, dimension — and that all three happen before you write the prompt. That post was about *what* you score. This one is about *who* scores it.

The question came out of a conversation about evaluating two systems, one built on GPT and one on Claude. If you use a GPT judge, is the comparison still fair? The judge never sees a model name. But it doesn't need one: every family has a recognisable house style, and a judge that learned to produce a style may well reward it.

That is a testable claim, and "several papers have found this" is not the same as having measured it on your own tasks. So I built a harness and measured it. Everything below is 378 judgments across three model families, and every number is reproducible from [the repo](https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias).

## The setup, in one paragraph

Fifteen tasks, split evenly across three levels of subjectivity: objective ones with a checkable answer (parse a duration string, fix a median bug, merge intervals), medium ones (summarize, extract to JSON, classify tickets), and subjective ones (error-message copy, a postmortem opening, explaining eventual consistency to a PM). Three models answer all fifteen: **GPT-5.5**, **Grok-4.3** and **Claude Sonnet 4.6**. Then each of those three models judges every pair of answers, blinded — no model names anywhere in the prompt, which the harness asserts before sending. Every comparison is judged **twice, with the two answers swapped**, because the rate at which a judge reverses itself when you swap the slots *is* the position bias, measured rather than assumed. Ties are allowed: forcing a binary choice between two equally good answers manufactures coin flips that later get misread as bias.

All three families ran through a single Azure AI Foundry subscription, which is the cheap trick that made this affordable — one billing relationship instead of three vendor accounts. (It also cost me an afternoon: Anthropic models on Foundry answer on the native Messages API and 404 on the OpenAI-compatible route, GPT-5.5 refuses `temperature=0` outright, and Grok-4.3 spends ~350 tokens thinking before it emits a one-line verdict, which silently truncates your answer if you budgeted 512. The README has the full list of scars.)

## 1. The ranking depends on who is holding the clipboard

![Three judges, three different rankings of the same 45 comparisons](/blog/judge-bias-ranking.png)

Same answers. Same blinded prompt. Both presentation orders. The only thing that changes between those three columns is which model is judging — and the ordering changes with it:

| Generator | Overall | by GPT-5.5 | by Grok-4.3 | by Claude Sonnet 4.6 | Mean words |
|---|---|---|---|---|---|
| GPT-5.5 | 66.1% | **85.0%** | 58.3% | 55.0% | 66 |
| Claude Sonnet 4.6 | 45.0% | 35.0% | 38.3% | **61.7%** | 85 |
| Grok-4.3 | 38.9% | 30.0% | **53.3%** | 33.3% | 55 |

Three judges, three different orderings. Every judge puts itself higher than the other two put it. Two of them crown GPT-5.5; the third crowns itself. And all three disagree about the rest of the order — so if you had run this evaluation with a single judge and shipped the ranking, part of what you shipped would have been the judge.

That is the symptom. The rest is the diagnosis.

## 2. Self-preference is real, and it scales with subjectivity

The naive way to measure self-preference is to count how often a judge picks its own answer. That measure is useless: GPT-5.5 picks its own answer 85% of the time, but its answers might simply be the best ones — and by the other two judges' reckoning, they largely are.

What actually proves bias is the **delta**: how much more often a judge picks its own answer *than its peers pick that same answer, on the same comparisons*.

| Judge | Own rate | Peers, same pairs | Delta | 95% CI | vs uninvolved judge only |
|---|---|---|---|---|---|
| GPT-5.5 | 85.0% | 56.7% | **+28.3pp** | [+16.7, +40.0] | +21.7pp [+8.3, +35.0] |
| Claude Sonnet 4.6 | 61.7% | 36.7% | **+25.0pp** | [+12.5, +36.7] | +15.0pp [+0.0, +28.3] |
| Grok-4.3 | 53.3% | 31.7% | **+21.7pp** | [+9.2, +35.8] | +13.3pp [−1.7, +30.0] |

All three positive, all three intervals excluding zero, all three about the same size. This is the part that a within-family pilot could not show: when I ran the same harness across three tiers of *one* family, the deltas came out +16.7, −14.6 and +4.2pp — noise pointing nowhere. Across families it is a straight line.

That last column deserves a note, because it is the one I would quote. With three judges that double as the three generators, the "peers" baseline for a comparison between A and B includes **B itself** — and B's own self-preference pushes the verdict away from A, inflating A's measured delta. Restricting the baseline to the judge with no stake in the pair knocks about a third off every number. The effect survives that correction for GPT-5.5, marginally for Claude, and becomes indistinguishable from zero for Grok. Anyone measuring self-preference with a judge panel drawn from the models under test is over-counting unless they do this.

Now the finding I care most about:

![A judge's bias towards its own answers grows with how subjective the task is](/blog/judge-bias-self-preference.png)

| Judge | Objective | Medium | Subjective |
|---|---|---|---|
| GPT-5.5 | +17.5pp | +25.0pp | +42.5pp |
| Grok-4.3 | +7.5pp | +27.5pp | +30.0pp |
| Claude Sonnet 4.6 | −2.5pp | +30.0pp | +47.5pp |

On tasks with a checkable answer, self-preference is small or absent — Claude Sonnet 4.6 is actually *harder* on itself than a neutral judge is. On tasks where the criterion is taste, it reaches +30 to +48 percentage points.

Which turns a vague warning into a usable rule: **a judge from the same family as one of the systems you're comparing is close to harmless on objective work and close to unusable on subjective work.** If your rubric is "did the extraction produce the right JSON", relax. If it is "which error message reads better", your judge is a participant.

## 3. Position bias is not a law of nature — it is a property of one judge

Everyone repeats "randomize the presentation order." Here is what the order actually did:

| Judge | slot-A rate | exact binomial vs 50% | flip rate |
|---|---|---|---|
| GPT-5.5 | 52.6% | p = 0.73 | 8.9% |
| Claude Sonnet 4.6 | 51.5% | p = 0.90 | 20.0% |
| Grok-4.3 | **72.4%** | **p < 0.001** | **35.6%** |

Two of the three judges show no position preference whatsoever. The third picks whatever it reads first almost three times in four, and reverses its own verdict on more than a third of comparisons when you swap the slots. And it degrades exactly where you'd least want it to:

| Grok-4.3 | Objective | Medium | Subjective |
|---|---|---|---|
| slot-A rate | 64% (p = 0.29) | 75% (p = 0.023) | 77% (p = 0.005) |
| flip rate | 13% | 40% | **53%** |

On the subjective third of the task set, Grok-4.3 reverses itself on more than half of all comparisons. At that point it isn't grading the answers; it's grading their addresses.

So keep randomising order — it's free. But notice that the usual justification ("LLM judges prefer the first answer") is not what the data says. The data says *some judges do, catastrophically, and you cannot tell which one without measuring it.* Running every comparison in both orders costs you a 2× on judge calls and turns an unknown into a number.

## 4. The length statistic everyone quotes is uninterpretable

Here is the number people report:

| Judge | Longer answer wins |
|---|---|
| GPT-5.5 | 48.6% |
| Grok-4.3 | 48.6% |
| Claude Sonnet 4.6 | 64.6% |

Looks like there's barely any length bias. In my within-family pilot the same statistic read 80–85% and looked like a textbook one. **Both readings are wrong**, and for the same reason: in any normal model lineup, length and quality are confounded. If your verbose models happen to be your good models, the number inflates; if they don't, it cancels. It is an accident of your lineup, not a property of your judge.

The control holds the model and the task fixed and varies **only** the target length: two variants from an identical base prompt, differing by one appended sentence ("answer in roughly N words"). The judge is then shown the base prompt *without* that sentence — otherwise it would be grading compliance with a word count it was told about. Short variants came out at 46 words on average, long ones at 174.

| Judge | Long wins (controlled) | Flip rate |
|---|---|---|
| GPT-5.5 | 77.8% | 11.1% |
| Grok-4.3 | 86.1% | 16.7% |
| Claude Sonnet 4.6 | 88.9% | 5.6% |

So the preference is not just real, it is **stronger** than the uncontrolled number implied — the opposite of the direction people assume the confound runs.

Split by what the task actually rewards, though, it isn't a length preference at all:

| What the task rewards | Long wins | n |
|---|---|---|
| elaboration (explain X) | **100.0%** | 27 |
| concision (summarize, commit message, error copy) | 68.5% | 27 |

Twenty-seven out of twenty-seven. Every judge, every generator, both orders. Add the pilot's runs and it's 45 for 45 across six judges from three families. If anything here deserves to be called a law, it's that one: **on a task that invites elaboration, the longer answer always wins.**

### Where I was wrong

The pilot found something better than that, and I wrote it up: on summarization the preference *inverted* — judges picked the short version and said so explicitly in their reasons ("genuinely condensed form, whereas B is essentially a full paraphrase"). The tidy conclusion was that judges infer the task's implicit goal, so "watch out for length bias" is the wrong instruction.

That did not replicate. Cross-family, the same summarization probe reads 72.2% long-wins, and the concision category sits at 68.5% — above chance, not below it. Broken down by judge, the pilot's effect was one model:

| Judge | elaboration | concision |
|---|---|---|
| GPT-5.5 | 100% | 55.6% |
| Grok-4.3 | 100% | 72.2% |
| Claude Sonnet 4.6 | 100% | 77.8% |
| *pilot:* Opus 5 | 100% | 66.7% |
| *pilot:* Sonnet 5 | 100% | **0.0%** |
| *pilot:* Haiku 4.5 | 100% | 50.0% |

Six judges. One of them preferred the short answer every single time and dragged a three-judge aggregate below 50%, which I then reported as a general finding. The corrected version is narrower: judges reward elaboration everywhere, and the reward merely *weakens*, with wide variance between judges, when the task's implicit criterion is compression. One judge in six actually inverted.

I'm keeping both write-ups in the repo, pilot first, because the failure mode is the useful part: a confident headline drawn from three judges of one family, retired once six judges from three families had a say.

## 5. On subjective tasks, judges agree at chance

| Judge pair | Objective | Medium | Subjective |
|---|---|---|---|
| GPT-5.5 vs Grok-4.3 | +0.41 | +0.32 | −0.01 |
| GPT-5.5 vs Claude Sonnet 4.6 | +0.31 | +0.35 | −0.03 |
| Grok-4.3 vs Claude Sonnet 4.6 | +0.20 | +0.02 | +0.05 |

Cohen's kappa: 1.0 is perfect agreement, 0.0 is chance. On the subjective tasks all three pairs are indistinguishable from chance. Two frontier judges grading the same subjective comparison agree exactly as often as two coin flips.

This is the number to keep if you keep only one. A judge panel is supposed to average out individual quirks — but averaging three judges who agree at chance doesn't give you a robust signal, it gives you a smoother random one. On subjective dimensions, the honest move is not more judges. It is to stop pretending the dimension is measurable by judge and go find a proxy that is: did the user come back, did the ticket get reopened, did the PR get merged.

## What I'd actually do with this

- **Match the judge to the dimension, not to a leaderboard.** Objective, checkable dimension → any competent judge, self-preference is near zero. Subjective dimension → assume the judge is a participant.
- **Never use a judge from a family you're evaluating on a subjective dimension.** +30 to +48 percentage points is not a rounding error, and blinding does not remove it.
- **Run both orders. Always.** Not because all judges lean first, but because one in three of these did, and the swap is what tells you which.
- **Screen the judge before trusting it.** Flip rate on ~20 comparisons costs almost nothing and would have disqualified Grok-4.3 in ten minutes.
- **Distrust any length statistic that isn't controlled** — including one that says your judge has no length bias.
- **If your judges agree at chance, the problem is the dimension, not the panel.**

## What this doesn't show

One model per family, and the tiers aren't matched: Azure had no quota for a current Claude at run time, so the Anthropic seat is Sonnet 4.6, a generation behind the other two. The obvious worry is reading a capability gap as a family effect. Two things push back — the older model isn't the lowest-ranked overall (Grok-4.3 is), and the three self-preference deltas land within 7pp of each other. But the clean version of this experiment uses same-tier models, and this isn't it.

Also: GPT-5.5 did not run at temperature 0, because it refuses to. Fifteen tasks and six length probes is 2.5× the pilot and still small — every interval here is wide. It's one run, with no repeats to separate judge instability from sampling noise. And nothing was executed: even the objective tasks were graded by reading, deliberately, because the point was to measure the judge. Where you can run the tests instead, run the tests.

None of which changes the shape of the result. Three judges looked at the same 45 comparisons and produced three different rankings, and the gap between them was widest exactly where the answer was a matter of taste — which is precisely where teams reach for an LLM judge in the first place.

---

*Harness, raw judgments and both write-ups: [experiments/judge-bias](https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias). Prior work worth reading: [Zheng et al. on position, verbosity and self-enhancement bias](https://arxiv.org/abs/2306.05685), [Wang et al. on position bias](https://aclanthology.org/2024.acl-long.511/), [Panickssery, Bowman and Feng on self-recognition and self-preference](https://arxiv.org/abs/2404.13076), and [Dubois et al. on length-controlled evaluation](https://arxiv.org/abs/2404.04475).*
