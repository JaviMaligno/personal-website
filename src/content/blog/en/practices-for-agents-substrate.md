---
title: "Bad Code Doesn't Stop an Agent. It Runs It Out of Budget."
description: "I degraded four repositories in nine semantically-equivalent ways and measured 750 agent runs. The degradations don't make the agent unable to fix the bug — they make it slower, and with a finite turn budget that becomes the same thing."
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

My hypothesis, written down before running anything:

> For a coding agent, **knowing where to look** — organisation, file layout, documentation —
> matters more than **how well-written the file is** once it's open.

That turned out to be wrong, and the way it's wrong is more useful than if it had been right.

## The method: break the code without changing the program

Take a working repository and degrade it in ways that are **semantically equivalent** — the program
does exactly the same thing before and after, verified by the repo's own suite giving an identical
result. Any difference in the agent's success rate is then attributable to readability or
navigability, never to the task getting harder.

Nine degradations in two families. **Family A, how it's written**: strip type annotations (A1),
rename identifiers to opaque ones (A2), destroy formatting (A3), remove comments and docstrings
(A4). **Family B, where to look**: break cohesion without changing size (B1), flatten the hierarchy
to `m1.py`, `m2.py` (B2), delete README and module docstrings (B3), hide the test suite (B4),
concatenate modules to vary file size (B5).

The tasks are **manufactured**, not found: a bug is injected programmatically and only counts if it
makes a specific set of tests fail and no others. These bugs don't exist on the internet, so there's
no contamination, and resolution is objective — no LLM judge anywhere.

**750 measured runs across four repositories**: a 2×2 (untouched, family A, family B, both) on two
of them and two model tiers with three passes, plus each of the eight practices removed and restored
one at a time, plus a file-size curve, plus a TypeScript probe. All of it
[in the repo](https://github.com/JaviMaligno/agent-code-practices).

## The headline table

python-stdnum, three passes per cell.

| Condition | Low tier | Median turns | High tier | Median turns |
|---|---|---|---|---|
| **T0** untouched | 14/18 — **78%** | 11 | 18/18 — **100%** | 6 |
| **T1** family A | 15/17 — 88% | 10 | 18/18 — 100% | 6 |
| **T2** family B | 12/15 — 80% | 12 | 14/14 — 100% | 18 |
| **T3** both | 8/15 — **53%** | 19 | 13/15 — **87%** | 15 |

Every condition is six tasks × three passes = 18 runs. The denominator drops to 15 in T2 and T3
because three runs there **measured nothing**: the injected fault broke no test at all, so the cell
says nothing about the agent and is excluded rather than scored as a failure. Why that happens, and
why excluding it isn't charity, is [further down](#three-times-a-broken-transformation-looked-like-a-failing-agent).

Read the turn columns, not just the percentages. That's where the finding is.

## What the degradations actually do

Neither family hurts alone: T1 (88%) and T2 (80%) sit at the baseline's 78%. Both together drop it to 53%. That's an
interaction, and it's what I'd have reported if I'd stopped there.

But the same experiment on **pint** — real, large, interconnected code instead of small
self-contained validators — says something the percentages alone hide:

| | Untouched | Family A |
|---|---|---|
| Resolved | 8/12 | **2/12** |
| Median turns | 30 | **40 (the ceiling)** |
| Runs that hit the ceiling | 3/12 | **10/12** |

The agent doesn't become incapable with degraded code. **It runs out of turns.** In pint under
family A, ten of twelve runs exhaust the 40-turn budget, and three are recorded as "fixed it
halfway" — a failure mode that doesn't occur at all in the untouched tree.

Line the three regimes up and the mechanism is the same in all of them:

Each row compares the untouched tree with the worst condition of that run: median turns before and
after, how many runs hit the 40-turn ceiling, and what the resolution did.

| Run | Median turns | Runs at the ceiling | Resolution |
|---|---|---|---|
| python-stdnum, high tier | 6 → 18 | 0 of 15 | 100% → 87% |
| python-stdnum, low tier | 11 → 19 | 0 of 15 | 78% → 53% |
| pint, low tier | 30 → **40** | **10 of 12** | 67% → 18% |

**The capable model doesn't absorb the damage by being smart — it absorbs it by starting with
margin.** It pays the same toll, tripling its turns from 6 to 18, and can afford it. pint starts at
30 out of 40 and the same toll puts it through the ceiling.

So the degradations don't destroy the agent's ability. They make the work more expensive, and with a
finite budget expensive becomes impossible. That reframes the practical question: not *"can the
agent work in this codebase"* but *"how much margin does it have left"*.

## Which practice pays: none of them, individually

Removing each of the eight practices on its own, three passes, 18 runs per condition:

| Removed | Resolution | Median turns |
|---|---|---|
| Baseline | 78% | 11 |
| Type annotations | 83% | 10 |
| Readable names | 67% | 12 |
| Formatting | 78% | 10 |
| Comments and docstrings | 72% | 10 |
| Cohesion | 72% | 10 |
| Hierarchy | 89% | 9 |
| README and module docs | 83% | 14 |
| Visible tests | 83% | 12 |

Everything lands between 67% and 89% around a 78% baseline, and every turn median
between 9 and 14. **No single practice does damage this data can separate from
noise.** Give any one of them back to fully-degraded code and it recovers most of
the way — 72% to 94% against T3's 53% — which is the other face of the
interaction: it isn't one practice carrying the effect, it's their absence
together.

I'm reporting this the way I am because the first version of this table said
something else. Run once instead of three times, it showed naming costing 28
points and doubling the turns, and I had a tidy mechanism ready for it: opaque
names make finding the right function expensive. The evidence was that A2 broke a
task the baseline solves every time. At three passes that cell is 3 out of 3
solved, in 10, 11 and 7 turns. It was one unlucky run.

Which is what this article says two sections down about variance being the same
order as the effects. I wrote that sentence and then published a one-pass table
anyway.

## Where nothing can be measured, and why I'm showing it

Five blocks of this campaign are uninterpretable, and they're published with the rest:

- **The high tier's breakdown**: thirteen of its sixteen conditions at 100% and the other three at
  83%, median 6 turns, one pass each. With the baseline at the ceiling there's no room for a drop.
- **The high tier generally**: 18/18 untouched.
- **pint's domain tasks**: 1/6 at baseline. I wrote those two by hand and made them too expensive —
  five of their six baseline runs hit the turn ceiling before finishing.
- **A third repository, sqlglot**: 0/3 at baseline. I brought it in for one reason — it is the only
  one of the four candidates whose files can be concatenated into four genuinely different sizes,
  which is what a threshold needs. Its tasks turned out to be beyond this model entirely, so the
  curve it was there to provide can't be read: there's nothing to fall from.
- **The TypeScript probe**: 1/12 at baseline, also on the floor. Built to check whether the result
  about types is an artefact of Python's being optional; it can't answer that, and
  [what it did settle](#what-this-doesnt-answer) is a fact about the transformation, not about agents.

The first one is worth dwelling on. My original plan was to run the breakdown in **one** tier, the
one where family A and family B were furthest apart — which is the high tier. Doing only that would
have produced sixteen identical cells at 100% and no information. Running both tiers is the only
reason there's a breakdown to show.

The size curve survives in pint: 67% → 50% at ~500 lines per file → 33% at ~2,000. Monotonic, and
with three points and six runs each, no threshold is visible. The design wanted to find one; what
there is, is a slope.

## The variance that makes single-pass results fiction

Four of 22 measurable cells gave different answers across three identical passes:

```
untouched, generic (a dropped None check)     no → OK → OK
family A,  the same one degraded              no → OK → OK
family A,  domain (an ISO checksum rotation)  no → no → OK
both,      generic (an inverted condition)    OK → OK → no
```

Same task, same condition, same model, same prompt. One of those cells took 27 turns to fail, 17 to
succeed, and 40 to succeed again.

The single-pass version of the headline table — which I had, earlier the same day — showed family B
at 100% and would have supported the opposite conclusion.

## Three times a broken transformation looked like a failing agent

The failure mode the whole design defends against, and it showed up three times, each producing
numbers I would have published.

**The first time, I had a complete table in which not one number was about an agent.** My runner
injected each task's fault into the already-degraded tree, where it no longer fit; two conditions
came out empty and a third came out as six agents that "broke something else". Nothing about that
table looked broken. The fix was to invert the order — fault first, degradation on top — and then
verify by running the code that the fault survived.

**The second is why some conditions are scored out of 15 instead of 18 in [the headline
table](#the-headline-table).** Which tests a fault breaks
can't be read off the task file, because the degradations move the tests too. So every cell builds
two degraded trees, clean and faulty, and asks the suite what changed. For one task under family B
the answer was *nothing*: its only test was a doctest living in a module docstring, and family B
deletes module docstrings. The fault was still there; no test was left to notice. Scoring those
three as failures would have moved T3 from 53% to 44% on the strength of a missing doctest.

**And for a while the result depended on which Python ran the experiment.** pint uses syntax only
3.12 parses. Under 3.11 the transformer couldn't read one file and skipped it silently, renaming a
class everywhere except where it was referenced — the package died on import and a whole condition
read as an agent breaking things. Transforming now stops and names the files it can't read: a
half-renamed tree isn't equivalent, and not producing it is the only honest option.

Two of those three only appeared when I added the second repository.

## What this doesn't answer

**The turn ceiling is a design choice.** Forty turns is where the budget bites; with a hundred, pint
would probably look like python-stdnum. The finding isn't "degraded code can't be fixed", it's "it
costs more, and budgets are finite" — which holds for any real agent, but the specific numbers here
are tied to that ceiling.

**The two repositories the 2×2 runs on are both Python, and the probe meant to fix that didn't.** Types in Python are
checked by nobody at runtime, so A1 measures them as documentation; in a language that checks them
they are also a contract. Building the TypeScript probe turned up one thing worth keeping: **stripping
annotations there is not a semantically-equivalent transformation** — under `strict` the program stops
compiling (`TS7006`), and a repo's test script usually runs the compiler too, so the annotations are
part of what the suite verifies. What works is replacing each annotation with `any`: still compiles,
erased at emit, and verified identical across hono's 4,968 runtime tests.

Then the cells ran, and the block joins the dead zones. Baseline 1/12 — on the floor — so its 5/12
with types erased says the baseline failed to discriminate, not that erasing types helps. A single
earlier pass over the same four tasks had scored 2 of 4 and looked like it discriminated; those two
tasks come out 0/3 and 1/3 at three passes, with the same turn counts. So the question this
probe was built to answer is still open, and the machinery to answer it is
[in the repo](https://github.com/JaviMaligno/agent-code-practices/tree/main/infra/ts).

**The domain stratum rests on two tasks in one repository.** python-stdnum's held; pint's came out
too hard to read.

I'd rather publish a table with its dead zones marked than a headline the data doesn't carry. The
750 runs are [in the repo](https://github.com/JaviMaligno/agent-code-practices/tree/main/results),
including the ones that measured nothing.

---

*Code and data: [agent-code-practices](https://github.com/JaviMaligno/agent-code-practices). This
continues the line of [Coding Agents and Teamwork](/en/blog/coding-agents-structure), which asked
whether structure beats social skill for a team of agents; this one asks it one level down, about
the structure of the code itself.*
