---
title: "Your Agent Doesn't Know What Has Already Happened"
description: "Agents plan around events that never occurred and invent dependencies between things that don't depend on each other. It looks like a missing clock, so I measured it: 572 responses, six models, two domains. The date changes nothing, and one failure gets worse in the strongest models."
pubDate: 2026-08-13
tags: ["AI", "Agents", "Evaluation", "Context Engineering", "Research"]
lang: en
translationKey: what-has-already-happened
heroImage: "/blog/what-has-already-happened.png"
linkedinImage: /blog/what-has-already-happened-data.png
---
I've spent a few months working daily with coding agents on a project with a lot of *state*: a university course I have to record in a studio on four consecutive days, with scripts, timings and a delivery deadline before it. And one kind of suggestion kept coming back — **ordering advice that didn't hold up.**

Leave this piece for the end, because it depends on the others. Record these two together, because the second reuses the first. Reasonable-sounding, and wrong: the thing it supposedly depended on had been finished and frozen months earlier. The agent was reasoning about my project without a firm line between what was already settled and what wasn't.

The obvious diagnosis is that it doesn't know when *now* is. I'll come back to that, because it's testable and it's false.

## The anecdote I had to throw away

I went looking for the most flagrant example to open with. I found a beauty: a status file the agent had been maintaining said

```
| Recorded and good  | 2  |
| Recorded, to redo  | 3  |
| Pending            | 63 |
```

Nothing had been recorded. Not one frame — the studio booking was still weeks away. What existed were timed read-throughs in my living room, me reading a script out loud with a stopwatch to see whether it fit in ten minutes.

Perfect opening paragraph. Except that when I dug into how the file got that way, it stopped being evidence of anything.

The vocabulary was contaminated from both ends. One session had been preparing material for the real shoot and blended the two states together. And I had, more than once, called my own practice runs "recording" — in conversations about measuring timings, where the distinction didn't matter. It stopped not mattering the moment a document got written in that tense: every session afterwards inherited a status file that spoke about takes. I corrected it out loud more than once and it kept coming back, because the document was still there.

So it isn't a model conjuring a state out of nothing. It's months of drift in a shared vocabulary, with authorship on both sides, mine included.

**That's the trouble with any anecdote from your own project: I'm inside the loop.** My words go into the context, my corrections change it, there's no control condition, and whatever example I picked I'd have picked *because* it was striking — then explained it afterwards with the explanation I already believed.

A hunch is not a case. So instead of writing up the hunch, I built something I could be wrong about.

## The test

Take the *shape* of what I kept noticing out of my project and put it somewhere I have no history. Fixed material, one question, one variable at a time, enough repetitions that I can't cherry-pick.

You give a model ~1.7 KB of project facts and ask: *in what order should I do these, and are there any ordering constraints I need to respect?* The material is my real project, ambiguity included:

- Sixty-eight video pieces to record, a studio window booked for four consecutive days, a delivery deadline before it.
- Scripts **closed and frozen since July**: the text is not going to change.
- A table of measured times, and a status count: *2 good / 3 to redo / 63 pending*.
- And a trap. Two pieces look dependent — the fourth reuses a calculation written during the third — but the script of the fourth says, in as many words, **"I'll rewrite them for you."** It's self-contained. There is no ordering constraint.

Then you vary the context by one or two lines:

| | added to the material |
|---|---|
| **A** | nothing |
| **B** | "today is 11 August 2026" |
| **C** | "the measured times are practice read-throughs, not studio takes; nothing has come out of the studio yet" |
| **D** | both |
| **E** | both, plus "don't invent ordering constraints" |

Six models — `gpt-4o`, `gpt-4.1-mini`, `gpt-5.4-mini`, `claude-haiku-4.5`, `claude-sonnet-4.6`, `claude-opus-5` — and then the whole thing again in an unrelated domain: a release of twelve services, production deploy window ahead, staging rehearsals behind. Same logical structure, none of the same words. Its trap is a service that reads a table another service migrates, where the runbook says the migration is idempotent and the service "starts against the old schema or the new one, without touching anything."

**572 scored responses.** An LLM judge does the scoring, blind to the condition and required to quote the exact sentence justifying each mark. Before trusting it I hand-coded a sample and checked both candidate judges against my coding: one agreed 30/32, the other 23/32 — and eight of the loser's nine errors were false positives, marking a failure in answers that said the opposite. So there's one judge, and it's the validated one.

## Failure 1: a precedence that the document explicitly denies

| asserts the dependency anyway | course domain | deployment domain |
|---|---|---|
| `gpt-4.1-mini` | 100% | 100% |
| `gpt-4o` | 100% | 100% |
| `claude-haiku-4.5` | 100% | 96% |
| `gpt-5.4-mini` | 100% | 86% |
| `claude-sonnet-4.6` | 100% | 100% |
| **`claude-opus-5`** | **52%** | **10%** |

Five of six models say B must come after A. In the course domain that's **92 out of 92 responses** — not a tendency, a ceiling.

And the exemption isn't buried in an appendix. It's in the *same sentence* as the dependency. Here's `gpt-4o`, unedited, three lines apart:

> `auth-db-migrator` — Prepares the schema `auth-api` uses. **It's idempotent and backward-compatible.**
>
> […]
>
> **Always deploy `auth-db-migrator` before `auth-api`**, since it adjusts the schema.

It read the exemption, wrote it down, and reasoned as if it hadn't. Nothing was missing from the context: the model **reproduced** the information and then overrode it. What loses isn't the fact — it's the fact's *scope*. The relation ("B reuses something from A") survives; the clause that cancels the relation does not.

The shape of the result matters as much as the size. **This is not a gradient, it's a threshold.** `gpt-5.4-mini` and `claude-sonnet-4.6` are strong recent models and they fail exactly as often as the smallest one in the set. One model out of six is in a different regime; the other five are indistinguishable from each other.

## Failure 2: a premise that expired in July

Both materials contain something that *invites* a convention from the training corpus. In the course, an opener that describes the whole course — and in video production you shoot the intro last, because the intro has to match what you ended up making. In the release, a gateway that publishes the manifest for everything — and in deployments the gateway goes last, so it doesn't advertise services that aren't up.

Both are real, sensible practices. And both rest on a condition that this material explicitly removes: **the scripts were frozen in July and the artefacts were signed in July.** Nothing done later can change what they say. The reason to defer them expired before the window even opened.

| defers it *because it depends on the rest* | course | deployment |
|---|---|---|
| five smaller models | 36% | 69% |
| **`claude-opus-5`** | **60%** | **98%** |

This is the failure I find most interesting, because it's temporal in the purest sense: the model retrieves a rule about *when* to do something, and doesn't check whether the rule's precondition still holds. It's the same move as advising someone to book early for a trip that already happened.

The model that reads the exemption is among the *worst* at this — 25 out of 25 in the deployment domain, the highest number in the study.

I want to be careful, because there's a tidy story available and the data doesn't quite support it. The tidy story is "the failure grows with capability." Not monotonically: in the deployment domain `gpt-4.1-mini` falls for it 79–90% of the time while `gpt-4o` does 20–40%. What the data does support is narrower and still useful: **being a better model does not help here.** The three strongest models in the set fail this 92–100% of the time in the deployment domain. If your plan is "wait for a better model," this is the part that will still be waiting.

My reading, offered as interpretation and not measurement: the two failures pull opposite ways because one is about reading and the other about producing. Ignoring the exemption is under-reading. Deferring the opener is over-producing — the model doesn't just answer, it supplies a *reason*, and a fluent plausible reason is exactly the shape a wrong ordering constraint takes.

## Failure 3: what has and hasn't happened

The status count — *2 good / 3 to redo* — is genuinely ambiguous in condition A. Reading it as finished output isn't crazy; the material doesn't settle it. So condition C settles it: *these are rehearsals, nothing has come out of the studio yet.*

What that line buys depends entirely on which model reads it.

**`claude-opus-5` acts on it.** The state error drops from 92% to 20% in the course domain (p=3.7·10⁻⁷) and from 20% to 0% in deployment. It also *says* it, going from 12% to 100% and 16% to 96%.

**The smaller models mostly just repeat it.** `gpt-5.4-mini` goes from never mentioning provenance to mentioning it 40–48% of the time; `claude-sonnet-4.6`, 0% to 62% in one domain. And then they plan around 63 pending anyway.

**And for three of them it made the planning worse.** In deployment, adding the clarification raised the state error in `claude-haiku-4.5` (12% → 32%), `claude-sonnet-4.6` (12% → 25%) and `gpt-5.4-mini` (12% → 20%). Small numbers, no individual significance, and I won't claim a mechanism. But the direction is the opposite of free: **giving a model a caveat gives it something new to talk about, and talking about it is not using it.**

That's what I'd have missed testing one model. The same sentence of context is a large fix, a no-op, or a mild irritant depending on what reads it.

## So is the outlier better or worse?

One model behaves differently from the other five on every measure, which invites the question: is `claude-opus-5` exceptionally good at this, or exceptionally bad? It's genuinely both, and I think it's one property seen from two sides.

Line up the state error by condition:

| error rate | without the clarification | with it |
|---|---|---|
| the five smaller models | 0–70% | 0–56% |
| **`claude-opus-5`** | **92% / 20% — worst in its column** | **20% / 0% — best** |

In both domains it is the *worst* of the six when the material leaves the status ambiguous, and the *best* once the material settles it. Without a fact to constrain it, it builds the most natural reading — those numbers are finished output — and plans on that reading with conviction. Given the fact, it updates and plans on the new one. The smaller models sit in a mediocre middle either way, because they commit less to any interpretation.

That also reconciles the gateway result, which otherwise looks contradictory. What this model reliably uses is what's **explicit**: "I'll rewrite them for you", "these are rehearsals". What needs its consequence derived in two steps — *frozen since July*, therefore nothing later can invalidate the opener — it doesn't use, and there the corpus convention wins. It wins harder, in fact, precisely because this is the model that elaborates most.

Offered as interpretation, not measurement. But the practical consequence runs opposite to the intuition: **with a stronger model, the quality of your document matters more, not less.** A small model gives you something mediocre almost regardless of what you wrote. A large one gives you back what you gave it — which is good news if you write carefully and bad news if the load-bearing fact is only implied.

## It isn't the clock

Which brings me back to the obvious diagnosis. Every failure above is about time — precedence, expiry, what has occurred — so the natural fix is to tell the model when *now* is. It's also the mitigation every tool ships by default: your agent almost certainly has today's date stamped into its system prompt right now. Mine did, throughout.

Adding the date explicitly moved nothing. Not one of the four measures (all p > 0.5).

Nor did the other two things I tried. Declaring what the numbers are doesn't make a model read the runbook clause — different failure, no transfer. And condition E adds, in plain language, *don't invent ordering constraints*: still **96%**. You can write the prohibition into the prompt and watch it violated in nineteen of twenty runs.

So the deficit isn't the timestamp. A calendar tells you where *now* sits; it tells you nothing about which of your facts are already fixed, which relations still hold, and which rule's precondition expired last month. That structure lives in the document, and it's the part that doesn't survive being read.

## What I'd actually do

**Don't write an exemption — write the sentence you mean.** The best-supported item here, and it's a documentation habit rather than a prompt trick. If a constraint doesn't apply, don't state the constraint and then except it: the exception loses 96–100% of the time in five of six models. "B reuses A's calculation, but it rewrites it" becomes "B is self-contained."

**Say what's frozen, not just what's done.** Failure 2 happens because a generic "do this last" rule outranks a specific fact about my project. "Scripts closed since July" apparently reads as history; "the scripts cannot change, so nothing later can invalidate the opener" states the consequence, which is what the rule needed to be checked against.

**Make provenance inseparable from the value.** Not a note elsewhere saying the numbers are rehearsals — a mark that can't be copied off. In my project what worked was writing `8:25 †`, where the dagger means "this delta is meaningless," so the number can't travel to another table without its caveat. Scope: this is *document design*. Declaring it in a prompt reliably changes only what the model says back.

**Stop expecting the date to do work,** and don't add caveats assuming they're free. Both are cheap to inject and neither does what you think.

**Watch your own vocabulary.** The one lesson from the anecdote I threw away, and it survives precisely because it isn't about the model: I called practice runs "recording" when it didn't matter, and it stopped not mattering as soon as it was written down. In a long-running project, loose words get committed to a file, and what's in the file becomes the state of the world.

## Limits

Two domains is not a sample of domains, and both are *ordering work with a window ahead*; diagnosis or analysis tasks might behave differently. Sixteen comparisons, so under a Bonferroni correction what I'd call confirmed is the exemption result and the two provenance effects in `claude-opus-5`; the worsening in three smaller models and the effect of the explicit prohibition are indications, labelled as such above. The judge shares a model family with two subjects, which I'd fix with a third judge next time — the bias would flatter that family, and it came out worst on failure 2, so the direction is at least safe.

And a caveat this article is itself an example of: all of it is measured in **August 2026** against those six models. The failure I've spent the whole post describing is a claim outliving the conditions it was written under. Mine will too.

---

*The three failures need different fixes, which is why I think they're worth separating. Under-reading you fix by writing better documents. Stale-premise reasoning I couldn't fix at all — not with the date, not with a declaration, not with a direct prohibition — and it's the one the strongest models were worst at.*
