---
title: "The Scaffolding You Pay For"
description: "I was convinced that prescriptive skills get in the way of a frontier model, so I measured it: ~640 responses and 99 agent runs. I was wrong about where the damage is — and once the agent has tools, the benefit disappears and only the bill stays."
pubDate: 2026-08-18
tags: ["AI", "Agents", "Evaluation", "Context Engineering", "Research"]
lang: en
translationKey: the-scaffolding-you-pay-for
heroImage: "/blog/the-scaffolding-you-pay-for.png"
repoUrl: https://github.com/JaviMaligno/agent-scaffolding-experiments
---
Somewhere in the last year, the way we work with coding agents grew a layer of procedure. Not prompts — **documents**. Skills, rules files, playbooks: a few thousand characters of prescribed process that ride along in the context and tell the model how to do its job. *Never fix without investigating the root cause first. Write the failing test before the implementation. Decompose the plan into steps of two to five minutes.*

I install these. [I've written some](/en/skills). And after a few months with a frontier model I had a strong hunch, which I'd also seen going around: **with a good enough model the scaffolding is dead weight, and you do better stripping it out.** The intuition is appealing. The thing is smart. Stop telling it how to think.

A hunch is not a result, so I measured it. And the first thing the measurements did was take my hunch apart.

## What "measuring a skill" means here

Two conditions throughout. **Free**: the task alone. **Constrained**: the same task plus the full text of a real skill — the actual documents people install, not a caricature I wrote to lose.

Four axes, in the order I ran them:

| axis | task | skill | scoring |
|---|---|---|---|
| 1 | fix a bug | `systematic-debugging` (9,718 chars) | tests are executed |
| 2 | order a body of work | `writing-plans` (6,079 chars) | blind judge, calibrated 30/32 against my own hand-coding |
| 3 | both, but inside a **real agent with tools** | three skills | tests, plus the whole path it took |
| 4 | requests where the deciding is the hard part | three skills | blind judge: does it flag the decision? |

Axes 1 and 2 are one turn, no tools: the skill as *text*. Six models. Axes 3 and 4 are Claude Code with a tool loop, a scratch repository, and 99 runs.

Axis 1 has visible tests the model sees failing, and hidden tests it never sees. A patch that treats the symptom passes the visible ones and fails the hidden ones — which is precisely what `systematic-debugging` promises to prevent.

## Axis 1: nothing happens

86% free against 87% constrained. **p=1.000.** Not one model moves.

The null is real and not a ceiling artefact — `gpt-4o` sits at 53%, with plenty of room, and doesn't move either. But the interesting part is *why*, and I only found it by looking at the two test sets separately: **symptomatic patching almost never happens.** Across the three hard tasks, visible ≈ hidden (88% vs 88%, 82% vs 84%, 74% vs 74%). When these models fix the symptom, they fix the cause.

So the skill has nothing to prevent. Nine thousand seven hundred characters of debugging discipline, aimed at a failure mode that didn't occur.

## Axis 2: the skill helps, and my hunch is wrong

The second task is open-ended: here is a body of work, tell me what order to do it in. The material contains a trap — two pieces look dependent, and the source explicitly cancels the dependency in the same sentence.

| avoids inventing the dependency | free | with `writing-plans` |
|---|---|---|
| five smaller models (pooled) | 0/40 (0%) | 1/43 (2%) |
| **`claude-opus-5`** | 8/20 (40%) | **15/20 (75%)** |

**+35 points, p=0.054.** Model × condition interaction: +33 points, p=0.041 by permutation.

That is the opposite of what I predicted, in the exact place I predicted it most confidently. And the mechanism, which I got from reading the responses rather than the numbers, is worth more than the effect size.

A note on those numbers, because it changed while I was writing this. At twelve runs per cell the effect was +50 points at p=0.027, and I nearly published that. Then I ran eight more per cell — the cheapest thing in the whole study — and the effect **shrank**: the free condition stayed at 40%, the constrained one fell from 92% to 75%. That is the ordinary behaviour of an underpowered cell, and the reason the headline above is a hair the wrong side of significance. I'd rather show you the number that got smaller than the one I found first.

`writing-plans` forces a constraints section. The model has to fill in a heading that says *hard ordering constraints*, and filling it in forces it to go and check whether the dependency is real. The constrained answers literally write **"hard ordering constraints: none"** and then quote the exemption in the source to justify it.

The prescribed process is not what helps. **The empty slot it creates is.** The skill's value here has nothing to do with its method being good — it's that it made the model look at something it would otherwise have glossed.

Note who this works on. The five smaller models are at zero in both conditions: the material can't help them because they can't pick it up. This lines up with [the previous article](/en/blog/what-has-already-happened), where declaring provenance only moved the one model strong enough to act on it. **Good context is an opportunity that requires the capability to take it.**

And the same skill, on the same task, **hurts** something else: tracking what has and hasn't happened drops from 81% to 65% (p=0.017), in four of five models. So even in text-only mode the honest summary isn't "scaffolding helps." It's that it *moves attention* — toward what it prescribes, away from the facts of the case.

## Axis 3: put the tools back and the benefit evaporates

Everything above measures a model answering from memory in a single turn. That is not how anybody uses a skill. In real use the agent can go and read the repo.

So: a scratch repository — eight modules, nineteen green tests, three domain rules written down in the README. Three requests with no single right answer (add currencies, add a loyalty discount, add the annual report). Four conditions: free, plus three skills of deliberately different kinds — `systematic-debugging` (hard gates), `test-driven-development` (an imposed sequence), `writing-plans` (the one that opens slots). Forty-eight runs.

Result is in three separate pieces, because they move differently:

| condition | delivers | turns | output tokens | cost |
|---|---|---|---|---|
| free | 12/12 | 26 | 9,686 | $1.16 |
| `systematic-debugging` | 12/12 | 31 (p=0.023) | 12,810 (p=0.035) | $1.57 (p=0.012) |
| `test-driven-development` | 12/12 | 34 (p=0.043) | 13,070 (p=0.026) | $1.69 (p=0.014) |
| `writing-plans` | **8/12** | 31 | **22,530** (p<0.001) | $1.88 (p=0.001) |

**Nobody broke a domain rule. 48 out of 48.** Including on a request I wrote specifically to bait it: the ticket asks, in as many words, for the new discount to stack with existing promotions, while the repository's own README says only one of them stacks. Given tools, the model goes and reads the README. Every time, in every condition, free included.

That is the finding that most limits my previous article and this one. The attention damage of axis 2 — the skill pulling focus away from the facts — **is an artefact of forcing a model to answer from memory.** Give it somewhere to look and it looks.

What survives is the bill: 32%, 35% and 133% more output tokens, and more money, in the three conditions, for no measurable improvement in anything.

## The skill that wrote a plan instead of the code

Four of the twelve `writing-plans` runs didn't deliver. All four are the same request: 0/4 against 12/12 for every other condition.

They didn't fail. They **planned**. The agent leaves a nicely written document under `docs/plans/` and never touches the source. One of them says so outright:

> "I haven't touched code: the suite is still 19 passed and the only new thing in the tree is that document."

And here's the part that makes it interesting rather than just a bug: **the plans are good.** They reason correctly about the domain, they spot the exact point where the request collides with the rounding rule in the README, they compute the right edge case. The skill improved the thinking and prevented the work.

That's the same mechanism as axis 2 — the skill directs attention to what it prescribes — except here what it prescribes is *planning*, so it quietly redefines the task. In day-to-day use this doesn't show up as a wrong answer. It shows up as an extra round trip and a "now actually do it" from you.

Global significance is p=0.093 — an indication, not a confirmed result. Within that one request it's p=0.0005, but I chose that request after seeing the data, so the honest number to quote is the first one.

And there's an obvious objection to all of it: this is the wrong test for a planning skill. These three requests were well-specified changes to an existing repository, with the information needed to decide already in the code and the README — exactly the case where planning first has least to add. Planning should pay somewhere else: new features, business decisions, trade-offs worth arguing about, the cases where what you need isn't written down anywhere. The objection is right, so I built that test too.

## Axis 4: the test a planning skill should win

Every task so far had its answer sitting in the repository — that's what makes the scoring objective, and it's also the case where planning first has least to add. So the fourth axis removes that: three requests where **the information that decides isn't anywhere.** Not in the code, not in the README, not in the wording.

- A 4% surcharge for paying in instalments. Does it belong in the taxable base, or is it a financial item outside the tax? Changes what you charge and what you declare.
- Blocking orders from customers in arrears. Hard reject, allow-and-flag, or a threshold? Three different commercial policies.
- Prices changing each season. Freeze the price on the order line, or keep a live reference with history?

Nothing in the repository settles any of them. So the measure can't be "got it right" — there is no right. It's whether the agent **flags that there's a decision it shouldn't be making alone**, naming alternatives and consequences, or **decides in silence**. Same blind judge, quoting mandatory.

I registered the prediction before running it: this is where `writing-plans` should win.

It doesn't.

| flags a decision it shouldn't make alone | rate | vs free |
|---|---|---|
| free | 5/11 (45%) | — |
| `writing-plans` | 5/10 (50%) | +5 pts (p=1.000) |
| `systematic-debugging` | 4/9 (44%) | −1 pt (p=1.000) |

Nothing moves, on any of the judge's five measures. What does move is the same thing as before: `writing-plans` writes a planning document in 60% of its runs against nobody else's 0% (p=0.011), and spends **9,600 more output tokens** doing it (p=0.005). It plans, visibly and expensively, and flags no more decisions than going without.

**The real driver isn't the skill, it's the request.** Split the same data by task instead of by condition:

| request | flags the decision |
|---|---|
| surcharge on instalments | **12/12** — every condition, every run |
| customer in arrears | 2/9 |
| historical prices | **0/9** — nobody, ever |

That's the finding. Whether the model notices there's a business decision in front of it is determined almost entirely by *which* decision it is, and barely at all by what scaffolding is loaded. A surcharge that visibly changes an invoice gets caught every time; "freeze the price or keep it live" gets caught never, by anyone, with or without a planning skill telling them to enumerate constraints.

I'd hold this one loosely: ten runs per condition detects only large effects, and the free baseline already flags half the time, which leaves little room to improve. But the direction is clear enough to say that **if a planning skill has a home, I haven't found it — and this was the test designed to let it win.**

## Prescribed cost is not accidental cost

If a skill makes an agent take more turns, that's only damning if the turns are wasted. TDD writing a failing test first is extra work *by design*. So I measured the two separately, and they separate cleanly:

- **`test-driven-development`** pays +1 red test suite (p=0.001) — that's its method, working as intended. But it also pays **+2 re-edits of the same file** (p=0.022), which is not method. That's rework.
- **`writing-plans`** pays +2 re-edits (p=0.032) and **2.3× the output tokens**. None of that is method.
- **`systematic-debugging`** is the only clean one. It costs more and disorients nothing: no extra clashes, no extra rework.

## What I'd actually do

**Stop paying for scaffolding you can't name a benefit for.** The clearest result here is the cost, and it's the one that survives correction for multiple comparisons. If a skill is in your context on every task, it is charging you between a third and well over double the output tokens per task. That's fine if you know what it buys. In this study, on these tasks, it mostly bought nothing.

**Prefer skills that create slots over skills that prescribe procedures.** The only positive effect I measured came from a heading the model had to fill in — *hard ordering constraints* — which forced it to check a fact it would otherwise have skimmed. The four-phase method around that heading contributed nothing I can detect.

**Know whether you're asking for a plan or for code, because the skill will decide if you don't.** On well-specified changes, planning first bought nothing and cost a third of that condition's runs. On requests where the deciding was the hard part, it flagged no more decisions than going without — and still wrote the document, and still charged for it. I went looking for the case where a planning skill earns its keep and didn't find it; that's not the same as it not existing, but it's where the measurements left me.

**Expect scaffolding to matter less as the agent gets tools, not more.** The one place text-only scaffolding clearly helped was a model that couldn't go and look things up. With a tool loop, that gap closes on its own.

## Limits

Axis 3 is one repository, three requests, one model — no generalisation to other languages or to large codebases. There are many comparisons and no correction applied; what survives a reasonable Bonferroni is the cost block (tokens and money, p ≤ 0.001 for `writing-plans`) and the pooled −16 points of axis 2 (p=0.017). The +35 points for Opus (p=0.054) and its interaction (p=0.041) are **indications, not confirmed results** — and after watching that effect shrink when I added runs, I'd treat them as the weakest claims in the piece.

The skills go in via the system prompt, which keeps axis 3 comparable with axis 2 but isn't identical to an agent invoking a skill mid-task. The turn ceiling I declared didn't actually bite — five runs exceeded it — so turns are observed cost, not consumption of a fixed budget.

Axis 4 is the weakest of the four: 32 runs, roughly ten per condition, 30 of them judged, and a design where the free baseline already flags half the time. It is enough to say a large effect isn't there; it is not enough to rule out a moderate one.

One instrumentation note, since the numbers depend on it: `claude -p` prints provider notices to stdout in the same shape as a response, so a batch that hits a spend limit will happily record empty runs as data. Discarded runs are now filtered on non-zero cost, a minimum of two turns and the absence of provider markers, and the ones that were caught are kept in the repository rather than deleted.

And, as ever, all of it is August 2026 against these models. [The previous article](/en/blog/what-has-already-happened) was about claims outliving the conditions they were written under. This one has the same expiry date.

---

*Everything is in [the repository](https://github.com/JaviMaligno/agent-scaffolding-experiments): raw responses, judged verdicts, the analysis scripts and the runs I threw away.*
