---
title: "A World Model Can Pass Every Test and Still Lose"
description: "I set out to reproduce a DeepMind result and instead found a clean way verification can lie to you: a code world model that passes its gate at 100% accuracy, stays 99% accurate on the states a planner visits, and still loses systematically at play."
pubDate: 2026-06-28
tags: ["AI", "Machine Learning", "Testing", "Research", "Agents"]
lang: en
translationKey: verified-world-model-still-loses
heroImage: "/blog/verified-world-model-still-loses.png"
publishToDevto: true
---
A while back I wrote that programming is drifting from verifying *how* code works to verifying *what* it produces — [results-oriented programming](/en/blog/results-oriented-programming). This post is what happened when I took that idea seriously enough to break it. I set out to reproduce a DeepMind result and instead spent a few weeks on a small, stubborn question: **if a result-check passes, does that actually mean the result is right?** The answer, it turns out, is "not necessarily" — and you can say exactly when it fails, and prove part of why.

I wrote the whole thing up as a preprint, *When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models*. <!-- TODO: replace with the real arXiv URL once posted --> The arXiv link will go here once it's up; the rest of this post is the story in plain language.

## The setup: Code World Models

The paradigm I was poking at comes from DeepMind's *Code World Models for General Game Playing* ([Lehrach et al., 2025](https://arxiv.org/abs/2510.04542)). Instead of asking a large language model to *play* a game directly, you ask it to **write the game's rules as a Python program** — a "world model" with functions for legal moves, transitions, and outcomes. Then a classical planner (Monte Carlo Tree Search) plays *against that synthesized program*. The division of labour is elegant: the LLM does translation (rules → code), classical search does the looking-ahead.

It works well, and on known games a small model + MCTS beats the same model used as a direct policy by wide margins. I reproduced that. But one step bothered me: **the verification step.**

Before the planner trusts the synthesized world model, the model is *refined* until it reaches 100% transition accuracy on a batch of random play-throughs — predicted next-state, legal moves, outcome, all matching the true game. Pass that and you "pass the gate." It looks like a clean, automatic correctness check.

The question I couldn't shake: **passing that gate means the model matches the truth on random play. Does it mean the model is good enough to plan with?**

## The honest null

The first thing I'll say is the boring, important part: on small, fully-specified games, the gate *is* enough. Tic-tac-toe, a generalized chess variant, Trike — whenever a synthesized model passed the gate, it was also correct on the states the planner actually visits. No gap. I report that as a null result, because it sets the boundary: the gate is a strong filter when the rules are complete and the state space is small.

So the interesting question becomes: **when can the gate be fooled?** And the condition is precise: you need a rule that random play almost never triggers but competent play reliably seeks out.

## The instrument: a rare rule that decides games

To make that condition real I didn't invent a game from scratch — I took a small generalized-chess game *from that same DeepMind paper* (a 5×5 board with general, infantry, and cavalry pieces, called `army5x5a`) and added one rule: if the game reaches a long move cap with both generals still alive, the player with more material wins instead of drawing. Under *random* play, that rule decides the game about 2.5% of the time — random games end early, by blunder. Under *competent* play it decides roughly half of all games, because good play survives to the cap.

Now omit that rule from the spec and synthesize a world model. The result is a model that:

- passes the gate at **100% transition accuracy**,
- is **≥99% accurate** on the exact distribution of states the planner visits,
- and yet **loses about 2:1 at play** (win rate 0.376 vs a calibrated 0.493 baseline, with non-overlapping confidence intervals).

The 1% it gets wrong is exactly the 1% that decides games. Averages hide it — the error is *diluted* away by all the ordinary positions it gets right. Prediction accuracy and play-adequacy come apart, cleanly and reproducibly.

## A law for when verification goes blind

The nice part is that this isn't a one-off anecdote; it has a shape. The expected harm follows

$$\text{danger} = \text{play\_cost} \times (1 - \text{rarity})^N$$

where `rarity` is how often a random play-through triggers the omitted rule and $N$ is how many play-throughs the gate samples. The $(1 - \text{rarity})^N$ factor is exact — it's just the probability that $N$ independent random games all miss the rule. So harm is negligible while the rule is common enough to get caught, rises through a threshold as it gets rarer, and saturates at the full cost of the rule once it almost always escapes the gate.

There's a sharper way to read that factor. When the rule never shows up in the sample, the data is *literally identical* whether the rule is in the model or not. So no learner of any kind — not a bigger LLM, not gradient descent, not exhaustive search — can recover the rule **from that sample alone**. It isn't a model weakness; it's missing information. Any recovery has to come from the specification, not the data.

## Translation, not inference

That leads to the finding I find most practical. Can you *repair* the gap by feeding the model examples of the rule? I tried — properly: DAgger, on-manifold harvested states, dozens of discriminating examples, two model sizes, refinement loops that draw fresh data every iteration.

(For the imitation-learning fans: "proper DAgger" here means the [Ross et al. (2011)](https://arxiv.org/abs/1011.0686) loop — collect states from the current flawed model's own play and relabel them with the oracle — not just dumping competent trajectories.)

It doesn't work. Across the board, the synthesized model stays rule-blind even when the rule is present in its training trajectories with near-certainty (you can watch it: the gate accuracy sits far below 1.0, meaning the rule *is* in the data, and after six refinement passes the model still hasn't encoded it). The behaviour is **rule translation, not rule inference**: the model faithfully encodes rules it is *told*, and does not reliably infer rules it is only *shown*. The actionable version: complete the specification before you synthesize. Verifying on the play distribution will *detect* an incomplete spec; it will not *repair* it.

## The same trap on the belief side

Games with hidden information (poker-like) add a second surface: the model's *belief function* — how it reconstructs what it can't see. Here I could prove something clean: a sampling gate over random play is *provably* enough to certify the belief function on small or shallow games (it's why Kuhn and Leduc poker show no gap). But the belief function has its own blind spot, and a transition-accuracy gate is *structurally* blind to it — the information about what a player can and can't see never appears in a transition at all. I show this with hand-built witnesses rather than synthesized models, and I'm explicit about that line in the paper.

## What I actually take from this

Two things, one technical and one about how the work got made.

**Technical:** a passing test suite — or a sampling-based gate — is a *result-check with a coverage blind spot*. It certifies the model exactly where your samples land, and competent behaviour systematically lands somewhere else: the rare, pivotal, deep parts of the space. If you verify a world model (or, honestly, any model used for planning or decisions) by sampling, measure adequacy **on the distribution it will actually be used on**, not on a convenient random one. And when correctness depends on a rule, put the rule in the spec — don't hope the system infers it.

**Meta:** the discipline that hardened this paper wasn't "claim less." It was, for each big claim, separating the part I could actually *prove* from the part that was only *measured* — and saying which was which. That's the same results-oriented reflex (verify the result, and be precise about what "verified" covers), applied to a paper instead of a program.

If you want the formal version, with the theorems and the numbers, it's in the preprint. <!-- TODO: arXiv URL --> The code is open too.

---

*Preprint: "When a Verified World Model Still Loses" (arXiv link coming soon). Related reading: [Results-Oriented Programming](/en/blog/results-oriented-programming) and [Software Dissolving Into the Model](/en/blog/software-dissolving-into-the-model).*
