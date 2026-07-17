---
title: "A World Model Can Pass Every Test and Still Lose"
description: "I set out to reproduce a DeepMind result and instead found a clean way verification can lie to you: a code world model that passes its gate at 100% accuracy, stays 98% accurate on the states a planner visits, and still loses systematically at play."
pubDate: 2026-07-15
tags: ["AI", "Machine Learning", "Testing", "Research", "Agents"]
lang: en
translationKey: verified-world-model-still-loses
heroImage: "/blog/verified-world-model-still-loses.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
---
A while back I wrote that programming is drifting from verifying *how* code works to verifying *what* it produces — [results-oriented programming](/en/blog/results-oriented-programming). This post is what happened when I took that idea seriously enough to break it. I set out to reproduce a DeepMind result and instead spent a few weeks on a small, stubborn question: **if a result-check passes, does that actually mean the result is right?** The answer, it turns out, is "not necessarily" — and you can say exactly when it fails, and prove part of why.

I wrote the whole thing up as a preprint, *When a Verified World Model Still Loses: Play-Adequacy vs Prediction-Accuracy in LLM-Synthesized Code World Models*, now on arXiv (**[arXiv:2607.14169](https://arxiv.org/abs/2607.14169)**). The [code and full reproduction log are open](https://github.com/JaviMaligno/code-world-models); the rest of this post is the story in plain language.

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
- is **≥98% accurate** on the exact distribution of states the planner visits,
- and yet **loses systematically at play** (win rate 0.404 vs 0.495 for a calibrated fair baseline — a play cost of 0.091, with non-overlapping 95% confidence intervals; seed-clustered 95% CI [0.065, 0.117] over 20 seeds).

The handful of states it gets wrong are exactly the ones that decide games. Averages hide it — the error is *diluted* away by all the ordinary positions it gets right. Prediction accuracy and play-adequacy come apart, cleanly and reproducibly.

To be sure this wasn't an artifact of my hand-written stand-in, I also ran it end-to-end through the actual synthesis pipeline, at the same budget and with its own confidence intervals: the synthesized model passes the gate *only* when the rare rule happens to be absent from its sample, and when it does, it loses at play — with a cost at least as large as the one above. Same effect, no human in the loop drawing the flawed model by hand.

## A law for when verification goes blind

The nice part is that this isn't a one-off anecdote; it has a shape. The expected harm follows

$$
\text{danger} = \text{play\_cost} \times (1 - \text{rarity})^N
$$

where `rarity` is how often a random play-through triggers the omitted rule and $N$ is how many play-throughs the gate samples. The $(1 - \text{rarity})^N$ factor is exact — it's just the probability that $N$ independent random games all miss the rule. So harm is negligible while the rule is common enough to get caught, rises through a threshold as it gets rarer, and saturates at the full cost of the rule once it almost always escapes the gate.

There's a sharper way to read that factor. When the rule never shows up in the sample, the data is *literally identical* whether the rule is in the model or not. So no learner of any kind — not a bigger LLM, not gradient descent, not exhaustive search — can recover the rule **from that sample alone**. It isn't a model weakness; it's missing information. Any recovery has to come from the specification, not the data.

## Translation, not inference

That leads to the finding I find most practical. Can you *repair* the gap by feeding the model examples of the rule? I tried — properly: DAgger, on-manifold harvested states, dozens of discriminating examples, two model sizes, refinement loops that draw fresh data every iteration.

(For the imitation-learning fans: "proper DAgger" here means the [Ross et al. (2011)](https://arxiv.org/abs/1011.0686) loop — collect states from the current flawed model's own play and relabel them with the oracle — not just dumping competent trajectories.)

It doesn't work. Across the board, the synthesized model stays rule-blind even when the rule is present in its training trajectories with near-certainty (you can watch it: the gate accuracy sits far below 1.0, meaning the rule *is* in the data, and after six refinement passes the model still hasn't encoded it). The behaviour is **rule translation, not rule inference**: the model faithfully encodes rules it is *told*, and does not reliably infer rules it is only *shown*. The actionable version: complete the specification before you synthesize. Verifying on the play distribution will *detect* an incomplete spec; it will not *repair* it.

## The same split on the belief side

Games with hidden information — poker and the like — add a second thing the model has to get right: not just the dynamics, but a *belief function*, the code that reconstructs what a player can't see from what they can. I expected the gap to show up here too. The first surprise was that it doesn't — and the reason is almost funny.

On small poker games (Kuhn, Leduc) the sampling gate is *provably* enough to certify the belief function; one can write the bound down. Random play turns out to be a **more** thorough explorer of a betting tree than skilled play, because it raises and calls indiscriminately while good play folds and bails. So the rare belief-states never hide from the gate — competent play only ever visits a subset of what random already covered. No gap.

But that tells you exactly what a gap *would* need: a game where skill takes you **deeper** than randomness — where depth comes from *surviving*, not from flailing. So I built the smallest game I could that has that shape. Call it Beacon, and it's essentially the picture you'd draw on a napkin: a walk where, at each step, you pick a move — one choice lets you continue, the wrong one ends the game on the spot. Random play wanders off the path almost immediately; skilled play walks all the way to the end. And at the very end there's a single decision that turns on a hidden fact about your opponent — a fact you could have read from the moves they made on the way down.

Now hand a model a belief function that is correct everywhere *except* that final stretch — the deep end of the walk that only skilled play ever reaches. It sails through the gate (random play never gets far enough to test it) and then loses every single game, because the one place its beliefs are wrong is the one place the game is actually decided. Same shape as the rare rule, now on the belief side: verified, and still wrong exactly where it counts.

There's a clean structural point underneath: a transition-accuracy gate is **blind by construction** to the belief function. What a player can and cannot see never appears in a "this state became that state" transition — so no amount of transition-checking can catch a wrong belief model; you need a separate check on the beliefs themselves. (These imperfect-information results use games I instrumented by hand to isolate the effect, rather than fully synthesized models — a distinction I'm careful to keep in the paper.)

## What I actually take from this

A passing test suite — or a sampling-based gate — is a *result-check with a coverage blind spot*. It certifies the model exactly where your samples land, and competent behaviour systematically lands somewhere else: the rare, pivotal, deep parts of the space. If you verify a world model (or, honestly, any model used for planning or decisions) by sampling, measure adequacy **on the distribution it will actually be used on**, not on a convenient random one. And when correctness depends on a rule, put the rule in the spec — don't hope the system infers it.

If you want the formal version, with the theorems and the numbers, it's in the [preprint](https://arxiv.org/abs/2607.14169). The [code is open too](https://github.com/JaviMaligno/code-world-models).

---

*Preprint: "When a Verified World Model Still Loses" ([arXiv:2607.14169](https://arxiv.org/abs/2607.14169)) · [code](https://github.com/JaviMaligno/code-world-models). Related reading: [Results-Oriented Programming](/en/blog/results-oriented-programming) and [Software Dissolving Into the Model](/en/blog/software-dissolving-into-the-model).*
