---
title: "Bad Code Doesn't Hurt an Agent. Until the Repository Is Large."
description: "I degraded four repositories in nine semantically-equivalent ways and measured 2,929 agent runs. In small code nothing measurable happens. In large interconnected code, degrading how it's written halves what the agent solves."
pubDate: 2026-09-08
tags: ["AI", "Agents", "Evaluation"]
lang: en
translationKey: practices-for-agents-substrate
heroImage: "/blog/practices-for-agents-substrate.png"
repoUrl: "https://github.com/JaviMaligno/agent-code-practices"
---

Software practices were justified for human readers. Names you can understand, consistent
formatting, modules with one responsibility, documentation that tells you where things live. Today
a growing share of the reads of any repository are done by an agent, and I couldn't find a
measurement of which of those practices help *it* and which only ever helped *us*.

My hypothesis, written down before running anything, came from how a language model works:

> An LLM is an excellent text processor. What it doesn't have is the repository in its head. So it
> should care **more about knowing where to look** — organisation, file layout, documentation —
> **than about how well-written the file is** once it's open.

The reasoning seemed sound and the result inverts it: the only thing that does measurable damage is
**how the text already in front of it is written**. Knowing where to look it solves on its own, with
the search tools every agent carries.

## The method: break the code without changing the program

Take a working repository and degrade it in ways that are **semantically equivalent** — the program
does exactly the same thing before and after, verified by the repo's own suite giving an identical
result. Any difference in success rate is then attributable to readability or navigability, never to
the task getting harder.

Nine degradations in two families. **How it's written**: strip type annotations, rename identifiers
to opaque ones, destroy formatting, remove comments and docstrings. **Where to look**: break cohesion
without changing size, flatten the hierarchy to `m1.py`, `m2.py`, delete README and module
docstrings, hide the test suite, concatenate modules to vary file size.

The tasks are **manufactured**, not found: a bug is injected programmatically and only counts if it
makes a specific set of tests fail and no others. These bugs don't exist on the internet, so there's
no contamination, and resolution is objective — no LLM judge anywhere.

And one condition the first version of this experiment lacked: **a task only enters if the untouched
tree solves it with margin**. If the clean code already exhausts the turn budget, there is no room
for a degradation to show, and the cell reads zero either way.

**2,929 measured runs across four repositories**, at ten or fifteen passes per cell. All of it
[in the repo](https://github.com/JaviMaligno/agent-code-practices).

## Where nothing happens

python-stdnum: tax-number validators, small self-contained files.

| Condition | Solves | 95% CI | Turns | Ceiling before→after | Distinct from baseline? |
|---|---|---|---|---|---|
| untouched (baseline) | 91/167 — 54% | [47%, 62%] | 30 | 62 | — |
| how it's writtenᵃ | 45/155 — 29% | [22%, 37%] | 40 | 62→96 | **p=0.000** |
| where to look | 76/161 — 47% | [40%, 55%] | 38 | 62→75 | n.s. (≥16% would be visible) |
| bothᵃ | 37/157 — 24% | [18%, 31%] | 40 | 62→103 | **p=0.000** |

Conditions sharing a mark (ᵃ) **cannot be told apart from each other**, only from the baseline.

Nothing separates from the baseline. Not even degrading everything at once. And the last column
carries what matters for reading this table: sixty cells per condition would have shown a
twenty-point drop, so the claim is not "it makes no difference" but "if there is an effect, it is
smaller than that".

With the capable model the same thing happens for a different reason:

| Condition | Solves | 95% CI | Turns | Ceiling before→after | Distinct from baseline? |
|---|---|---|---|---|---|
| untouched (baseline) | 59/60 — 98% | [91%, 100%] | 6 | 1 | — |
| how it's writtenᵃ | 58/60 — 97% | [89%, 99%] | 6 | 1→2 | n.s. (≥7% would be visible) |
| where to lookᵃ | 58/60 — 97% | [89%, 99%] | 6 | 1→1 | n.s. (≥7% would be visible) |
| bothᵃ | 56/60 — 93% | [84%, 97%] | 6 | 1→2 | n.s. (≥7% would be visible) |

Conditions sharing a mark (ᵃ) **cannot be told apart from each other**, only from the baseline.

Here the baseline solves 98%. There is no room to fall from.

## Where it does

pint: physical units, large interconnected code where fixing anything means understanding several
pieces at once.

| Condition | Solves | 95% CI | Turns | Ceiling before→after | Distinct from baseline? |
|---|---|---|---|---|---|
| untouched (baseline) | 19/35 — 54% | [38%, 70%] | 30 | 12 | — |
| how it's writtenᵃ | 7/26 — 27% | [14%, 46%] | 40 | 12→14 | **p=0.040** |
| where to lookᵃ | 11/30 — 37% | [22%, 54%] | 38 | 12→15 | n.s. (≥36% would be visible) |
| both | 0/25 — 0% | [0%, 13%] | 40 | 12→18 | **p=0.000** |

Conditions sharing a mark (ᵃ) **cannot be told apart from each other**, only from the baseline.

**From 54% to 24%.** Degrading both families at once takes away more than half of what the agent was
solving, and degrading only *how it's written* costs almost as much, with the median turn count
pinned at the ceiling. At nearly two hundred cells per condition both drops sit far below chance
(p<0.001) and **they are also distinct from each other**: hiding *where to look* adds damage on top
of dirtying the text, but on its own it does nothing this data separates from noise.

That is the answer to the hypothesis, and it is the opposite of what I wrote down. Hiding *where to
look* produces no effect this data can separate from noise. Dirtying the text does.

The explanation I find most plausible turns on exactly the thing the hypothesis got right — that the
agent is a text processor: **finding the file is a problem it has already solved** — it searches,
lists, opens — and flattening the hierarchy or deleting the README removes help it wasn't using.
Reading unreadable code it cannot delegate to any tool: it pays for that in full, line by line, and
in a repository where there is a lot to read that accumulates until the budget is gone.

## It is paid in turns before it is paid in failures

The three runs lined up, comparing the untouched tree with its worst condition:

| Run | Baseline | Worst condition | Turns | Runs at the ceiling |
|---|---|---|---|---|
| python-stdnum, high tier | 98% | 93% | 6 → 6 | 1/60 → 2/60 |
| python-stdnum, low tier | 83% | 81% | 10 → 11 | 2/59 → 5/59 |
| pint | 54% | 24% | 30 → 40 | 62/167 → 103/157 |

The capable model doesn't absorb the damage by being smarter: **it starts with margin**. It solves
in 6 turns out of 40, and even if degradation tripled that it would still have budget to spare. pint
starts at 30 out of 40, and any added cost pushes it through the ceiling.

That reframes the practical question. Not *"can the agent work in this codebase?"* but *"how much
margin does it have left?"*. A small repository with a good model tolerates almost anything. A large
one with a stretched model tolerates nothing.

## Which practice pays: the answer is in giving them back, not in removing them

Removing each practice on its own from clean code, and giving each one back on its own to fully
degraded code. Sixty cells per condition:

| Practice | Removed from clean code | Given back to destroyed code |
|---|---|---|
| *(baseline: 49/59 — 83%)* | | |
| type annotations | 81% n.s. | 80% n.s. |
| readable names | 81% n.s. | 97% **(p=0.016)** |
| formatting | 85% n.s. | 80% n.s. |
| comments and docstrings | 87% n.s. | 85% n.s. |
| cohesion | 86% n.s. | 78% n.s. |
| hierarchy | 84% n.s. | 82% n.s. |
| README and module docs | 85% n.s. | 86% n.s. |
| visible tests | 71% n.s. | 86% n.s. |

Removing any practice **on its own** does nothing: all eight land inside the baseline's interval.
But giving **readable names** back to otherwise destroyed code recovers 97%, and that does separate
— from the baseline and from giving back almost anything else (p=0.002 against cohesion, 0.004
against formatting, 0.007 against types; three survive a Bonferroni correction).

The asymmetry is the finding: **names are not necessary while the rest of the context is intact, but
they are sufficient when nothing else is left**. With the code formatted, commented and organised, it
hardly matters that the functions are called `f1` and `f2`; there is plenty to infer from. Once
everything else has been erased, identifiers are the only place the author's intent survives.

It is also a correction of my own. An earlier version of this section, at one pass per cell, said
removing names cost 28 points, and I had a tidy mechanism ready to explain it. At three passes that
vanished, and at ten it turns out the real effect is on the other side of the experiment.

## File size: no visible effect

| File size | Solves | Distinct? |
|---|---|---|
| original | 91/167 — 54% | — |
| ~500 lines | 41/71 — 58% | n.s. (p=0.67) |
| ~2.000 lines | 33/70 — 47% | n.s. (p=0.32) |

Concatenating pint's modules up to ~500 and ~2,000 lines per file changes nothing detectable. The
design was looking for a threshold; with these cells, neither threshold nor slope.

## Where nothing can be measured, and whose fault that is

**The domain stratum and sqlglot.** The first version of this experiment declared them
"uninterpretable" and left it there. True, and an excuse: they were uninterpretable because I chose
tasks the *untouched* tree already failed, and without margin there is no drop to measure. After
adding the affordability filter — a task only enters if clean code solves it in under half the
budget — and regenerating them, **sqlglot produced not one valid task in 56 attempts**. That is no
longer a bad choice on my part: it is a fact about that repository and this model.

**The TypeScript probe.** It existed to check whether the result about types is an artefact of
Python's being optional. Building it left a finding that depends on no cell: in TypeScript,
**stripping annotations is not a semantically-equivalent transformation** — under `strict` the
program stops compiling and the test script usually runs the compiler, so annotations are part of
what the suite verifies. What works is replacing each annotation with `any`: still compiles, erased
at emit, verified identical across hono's 4,968 runtime tests. Its cells, with the baseline on the
floor, settle nothing.

## Variance, which is the reason for almost everything above

This experiment has produced, across three successive versions, three different conclusions about
the same repositories:

| With | It said |
|---|---|
| 1 pass per cell | naming costs 28 points |
| 3 passes | no practice does anything; degrading everything drops to 53% |
| 10-15 passes | not that either; the effect is in pint and in giving names back |

Neither of the first two was dishonest and all three came out of the same code. What changed was
statistical power. At eighteen cells per condition only drops of thirty-eight points or more are
visible: a flat table did not mean "makes no difference", it meant "we cannot tell", and I read it
as the former.

That is why every row in this article carries its interval and, where there is no difference, the
drop that would have been visible. It is the only way a reader can tell those apart without running
the experiment again.

## What this doesn't answer

**The 40-turn ceiling is a design choice.** It is where the budget bites; at a hundred, pint would
probably look like python-stdnum. The finding isn't "degraded code can't be fixed", it's "it costs
more, and budgets are finite".

**One model per tier, and one pair of tiers.** The contrast between the model with margin and the one
without is the most robust result here, and it rests on two models.

**Two repositories carry everything.** python-stdnum says where nothing happens; pint, where it does.
The other two came in for the size curve and the type probe, and neither produced an interpretable
block.

I'd rather publish a table with its dead zones marked than a headline the data doesn't carry. The
runs are [in the repo](https://github.com/JaviMaligno/agent-code-practices/tree/main/results),
including the ones that measured nothing.

---

*Code and data: [agent-code-practices](https://github.com/JaviMaligno/agent-code-practices). This
continues the line of [Coding Agents and Teamwork](/en/blog/coding-agents-structure), which asked
whether structure beats social skill for a team of agents; this one asks it one level down, about
the structure of the code itself.*
