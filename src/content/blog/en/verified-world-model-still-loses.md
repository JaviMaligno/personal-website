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

<style>
.cwm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.cwm-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.cwm-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
.cwm-table{width:100%;border-collapse:collapse;margin:1.5rem 0;font-size:.92rem}
.cwm-table th,.cwm-table td{padding:.55rem .7rem;border-bottom:1px solid rgba(255,255,255,0.1);text-align:left}
.cwm-table th{color:#94a3b8;font-weight:600}
.cwm-table td.n{font-family:ui-monospace,'JetBrains Mono',monospace;text-align:right;white-space:nowrap}
</style>

## The setup: Code World Models

The paradigm I was poking at comes from DeepMind's *Code World Models for General Game Playing* ([Lehrach et al., 2025](https://arxiv.org/abs/2510.04542)). Instead of asking a large language model to *play* a game directly, you ask it to **write the game's rules as a Python program** — a "world model" with functions for legal moves, transitions, and outcomes. Then a classical planner ([Monte Carlo Tree Search](https://en.wikipedia.org/wiki/Monte_Carlo_tree_search)) plays *against that synthesized program*. The division of labour is elegant: the LLM does translation (rules → code), classical search does the looking-ahead.

It works well, and on known games a small model + MCTS beats the same model used as a direct policy by wide margins. I reproduced that. But one step bothered me: **the verification step.**

Before the planner trusts the synthesized world model, the model is *refined* until it reaches 100% transition accuracy on a batch of random play-throughs — predicted next-state, legal moves, outcome, all matching the true game. Pass that and you "pass the gate." It looks like a clean, automatic correctness check.

The question I couldn't shake: **passing that gate means the model matches the truth on random play. Does it mean the model is good enough to plan with?**

## The honest null

The first thing I'll say is the boring, important part: on small, fully-specified games, the gate *is* enough. Tic-tac-toe, a generalized-chess variant (`army5x5a`, below), [Trike](https://boardgamegeek.com/boardgame/307379/trike) — whenever a synthesized model passed the gate, it was also correct on the states the planner actually visits. No gap. I report that as a null result, because it sets the boundary: the gate is a strong filter when the rules are complete and the state space is small.

So the interesting question becomes: **when can the gate be fooled?** And the condition is precise: you need a rule that random play almost never triggers but competent play reliably seeks out.

## The instrument: a rare rule that decides games

To make that condition real I didn't invent a game from scratch — I took a small generalized-chess game *from that same DeepMind paper* (`army5x5a`, defined in [its Appendix H.5](https://arxiv.org/abs/2510.04542): a 5×5 board with general, infantry, and cavalry pieces, won by capturing the enemy general) and added one rule: if the game reaches a long move cap with both generals still alive, the player with more material wins instead of drawing. Under *random* play, that rule decides the game about 2.5% of the time — random games end early, by blunder. Under *competent* play it decides roughly half of all games, because good play survives to the cap.

<figure class="cwm-fig">
<svg viewBox="0 0 600 200" role="img" aria-label="How often the rule decides the game: 2.5% under random play, about 50% under competent play">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF" text-anchor="middle">
    <line x1="150" y1="30" x2="150" y2="170" stroke="rgba(255,255,255,0.1)"/>
    <line x1="360" y1="30" x2="360" y2="170" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <line x1="570" y1="30" x2="570" y2="170" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <text x="150" y="188">0%</text><text x="360" y="188">50%</text><text x="570" y="188">100%</text>
  </g>
  <text x="140" y="72" text-anchor="end" fill="#f8fafc" font-size="13">Random play</text>
  <rect x="150" y="58" width="10.5" height="26" rx="4" fill="#f43f5e"/>
  <text x="168" y="76" fill="#f43f5e" font-size="12" font-family="ui-monospace,monospace">2.5%</text>
  <text x="140" y="132" text-anchor="end" fill="#f8fafc" font-size="13">Competent play</text>
  <rect x="150" y="118" width="210" height="26" rx="4" fill="#6366f1"/>
  <text x="368" y="136" fill="#818cf8" font-size="12" font-family="ui-monospace,monospace">~50%</text>
</svg>
<figcaption>How often the material-at-cap rule actually decides the game. The gate samples <em>random</em> play (2.5%); the game is decided under <em>competent</em> play (~50%). The gate looks where the rule almost never matters.</figcaption>
</figure>

Now omit that rule from the spec and synthesize a world model. The result is a model that:

- passes the gate at **100% transition accuracy**,
- is **≥98% accurate** on the exact distribution of states the planner visits,
- and yet **loses systematically at play** (win rate 0.404 vs 0.495 for a calibrated fair baseline — a *play cost* of 0.091, with non-overlapping 95% confidence intervals; seed-clustered 95% CI [0.065, 0.117] over 20 seeds).

Throughout, **play cost** is just the win rate the flaw gives up: the fair baseline's win rate minus the flawed model's, both playing the true game at the same budget. 0 means "plays as well as the truth"; bigger means "the flaw is costing you games."

The handful of states it gets wrong are exactly the ones that decide games. Averages hide it — the error is *diluted* away by all the ordinary positions it gets right. Prediction accuracy and play-adequacy come apart, cleanly and reproducibly.

<figure class="cwm-fig">
<svg viewBox="0 0 600 195" role="img" aria-label="Win rates with 95% confidence intervals: fair baseline 0.495, rule-blind 0.404, intervals do not overlap">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF" text-anchor="middle">
    <line x1="150" y1="40" x2="150" y2="150" stroke="rgba(255,255,255,0.1)"/>
    <line x1="355" y1="40" x2="355" y2="150" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <line x1="560" y1="40" x2="560" y2="150" stroke="rgba(255,255,255,0.1)"/>
    <text x="150" y="168">0.35</text><text x="355" y="168">0.45</text><text x="560" y="168">0.55</text>
    <text x="355" y="186" fill="#94a3b8" font-family="'Inter',sans-serif">win rate vs the true game</text>
  </g>
  <text x="138" y="74" text-anchor="end" fill="#f8fafc" font-size="13">Fair baseline</text>
  <line x1="406.25" y1="70" x2="488.25" y2="70" stroke="#6366f1" stroke-width="2"/>
  <line x1="406.25" y1="63" x2="406.25" y2="77" stroke="#6366f1" stroke-width="2"/>
  <line x1="488.25" y1="63" x2="488.25" y2="77" stroke="#6366f1" stroke-width="2"/>
  <circle cx="447.25" cy="70" r="6" fill="#6366f1" stroke="#1a1a24" stroke-width="2"/>
  <text x="447.25" y="52" text-anchor="middle" fill="#818cf8" font-size="12" font-family="ui-monospace,monospace">0.495</text>
  <text x="138" y="124" text-anchor="end" fill="#f8fafc" font-size="13">Rule-blind CWM</text>
  <line x1="219.7" y1="120" x2="301.7" y2="120" stroke="#f43f5e" stroke-width="2"/>
  <line x1="219.7" y1="113" x2="219.7" y2="127" stroke="#f43f5e" stroke-width="2"/>
  <line x1="301.7" y1="113" x2="301.7" y2="127" stroke="#f43f5e" stroke-width="2"/>
  <circle cx="260.7" cy="120" r="6" fill="#f43f5e" stroke="#1a1a24" stroke-width="2"/>
  <text x="260.7" y="142" text-anchor="middle" fill="#f43f5e" font-size="12" font-family="ui-monospace,monospace">0.404</text>
  <line x1="301.7" y1="95" x2="406.25" y2="95" stroke="#9CA3AF" stroke-width="1" stroke-dasharray="2 3"/>
  <text x="354" y="90" text-anchor="middle" fill="#9CA3AF" font-size="11" font-family="ui-monospace,monospace">gap 0.091</text>
</svg>
<figcaption>The gate-passing, ≥98%-accurate rule-blind model (rose) loses to the fair baseline (indigo). The 95% intervals don't overlap — the 0.091 play cost isn't a sampling artifact.</figcaption>
</figure>

To be sure this wasn't an artifact of my hand-written stand-in, I also ran it end-to-end through the actual synthesis pipeline, at the same budget and with its own confidence intervals: the synthesized model passes the gate *only* when the rare rule happens to be absent from its sample, and when it does, it loses at play — with a cost at least as large as the one above. Same effect, no human in the loop drawing the flawed model by hand.

<table class="cwm-table">
<thead><tr><th>Arm (vs the true game)</th><th style="text-align:right">Win rate [95% CI]</th><th style="text-align:right">Play cost</th></tr></thead>
<tbody>
<tr><td><span style="color:#6366f1">●</span> Fair baseline (truth vs truth)</td><td class="n">0.495 [0.475, 0.515]</td><td class="n">—</td></tr>
<tr><td><span style="color:#f43f5e">●</span> Rule-blind instrument (Panel A)</td><td class="n">0.404 [0.384, 0.424]</td><td class="n"><strong>0.091</strong></td></tr>
<tr><td><span style="color:#f43f5e">●</span> Synthesized, rule-absent (Panel B)</td><td class="n">0.345 [0.317, 0.374]</td><td class="n"><strong>0.154</strong></td></tr>
</tbody></table>

<p style="color:#94a3b8;font-size:.82rem;margin:-.5rem 0 1.5rem;text-align:center">Play cost is measured paired-by-seed against each arm's own fair baseline; the synthesized arm's larger cost reflects imperfections beyond the omitted rule. Full numbers and CIs in the <a href="https://arxiv.org/abs/2607.14169">preprint</a>.</p>

## A law for when verification goes blind

The nice part is that this isn't a one-off anecdote; it has a shape. The expected harm follows

$$
\text{danger} = \text{play\_cost} \times (1 - \text{rarity})^N
$$

where `rarity` is how often a random play-through triggers the omitted rule and $N$ is how many play-throughs the gate samples. The $(1 - \text{rarity})^N$ factor is exact — it's just the probability that $N$ independent random games all miss the rule. So harm is negligible while the rule is common enough to get caught, rises through a threshold as it gets rarer, and saturates at the full cost of the rule once it almost always escapes the gate.

<figure class="cwm-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="Danger law: expected harm versus rule rarity, staying near the full play cost while the rule is rare and collapsing once it is common enough to catch">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF">
    <line x1="70" y1="30" x2="70" y2="210" stroke="rgba(255,255,255,0.1)"/>
    <line x1="70" y1="210" x2="560" y2="210" stroke="rgba(255,255,255,0.1)"/>
    <text x="70" y="228" text-anchor="middle">0</text>
    <text x="233" y="228" text-anchor="middle">5%</text>
    <text x="396" y="228" text-anchor="middle">10%</text>
    <text x="560" y="228" text-anchor="middle">15%</text>
    <text x="315" y="248" text-anchor="middle" fill="#94a3b8" font-family="'Inter',sans-serif">rule rarity (fraction of random games it triggers)</text>
    <text x="58" y="34" text-anchor="end">0.5</text>
    <text x="58" y="214" text-anchor="end">0</text>
    <text x="20" y="120" text-anchor="middle" fill="#94a3b8" font-family="'Inter',sans-serif" transform="rotate(-90 20 120)">expected harm</text>
  </g>
  <path d="M70,30 L102.7,90 L135.3,129.6 L151.7,144.9 L168,156.7 L200.7,174.7 L233.3,186.9 L266,194.9 L331.3,203.5 L396.7,207.3 L462,208.9 L560,209.7" fill="none" stroke="#6366f1" stroke-width="2.5"/>
  <circle cx="151.7" cy="144.9" r="6" fill="#f43f5e" stroke="#1a1a24" stroke-width="2"/>
  <line x1="151.7" y1="144.9" x2="151.7" y2="210" stroke="#f43f5e" stroke-width="1" stroke-dasharray="2 3"/>
  <text x="160" y="120" fill="#f43f5e" font-size="11" font-family="ui-monospace,monospace">our rule (2.5%)</text>
  <text x="300" y="70" fill="#94a3b8" font-size="12">harm ≈ full play cost while the rule</text>
  <text x="300" y="88" fill="#94a3b8" font-size="12">is too rare for a size-N gate to catch</text>
</svg>
<figcaption>danger = play_cost × (1 − rarity)<tspan font-size="0.8em">N</tspan>, here with N = 40 gate samples. Harm stays near the full play cost while the rule is rare enough to slip past the gate, then collapses once it's common enough to be caught. Our engineered rule (rose) sits squarely in the dangerous zone.</figcaption>
</figure>

There's a sharper way to read that factor. When the rule never shows up in the sample, the data is *literally identical* whether the rule is in the model or not. So no learner of any kind — not a bigger LLM, not gradient descent, not exhaustive search — can recover the rule **from that sample alone**. It isn't a model weakness; it's missing information. Any recovery has to come from the specification, not the data.

<figure class="cwm-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="Random sampled trajectories terminate shallow; the deep region that decides competent games is never sampled">
  <defs>
    <linearGradient id="cwm-deep" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f43f5e" stop-opacity="0"/>
      <stop offset="1" stop-color="#f43f5e" stop-opacity="0.18"/>
    </linearGradient>
  </defs>
  <rect x="40" y="180" width="520" height="65" fill="url(#cwm-deep)"/>
  <line x1="40" y1="180" x2="560" y2="180" stroke="#f43f5e" stroke-width="1" stroke-dasharray="4 4" opacity="0.6"/>
  <text x="552" y="173" text-anchor="end" fill="#f43f5e" font-size="11" font-family="ui-monospace,monospace">deep region — decides competent games, never sampled</text>
  <text x="48" y="24" fill="#9CA3AF" font-size="11" font-family="ui-monospace,monospace">start</text>
  <circle cx="300" cy="30" r="4" fill="#94a3b8"/>
  <g fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" opacity="0.85">
    <path d="M300,30 L180,90 L120,140"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.2s" repeatCount="indefinite"/></path>
    <path d="M300,30 L250,95 L230,150"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.6s" begin="0.3s" repeatCount="indefinite"/></path>
    <path d="M300,30 L360,92 L410,145"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.4s" begin="0.6s" repeatCount="indefinite"/></path>
    <path d="M300,30 L430,88 L500,150"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.8s" begin="0.15s" repeatCount="indefinite"/></path>
    <path d="M300,30 L300,100 L320,155"><animate attributeName="stroke-dasharray" from="0 300" to="300 0" dur="2.5s" begin="0.9s" repeatCount="indefinite"/></path>
  </g>
  <g fill="#6366f1">
    <circle cx="120" cy="140" r="3.5"/><circle cx="230" cy="150" r="3.5"/><circle cx="410" cy="145" r="3.5"/><circle cx="500" cy="150" r="3.5"/><circle cx="320" cy="155" r="3.5"/>
  </g>
  <path d="M300,30 L305,110 L300,200 L302,235" fill="none" stroke="#f43f5e" stroke-width="2" stroke-dasharray="3 5" opacity="0.45"/>
  <circle cx="302" cy="235" r="5" fill="none" stroke="#f43f5e" stroke-width="2">
    <animate attributeName="r" values="5;9;5" dur="1.8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.7;0.2;0.7" dur="1.8s" repeatCount="indefinite"/>
  </circle>
</svg>
<figcaption>What a sampling gate sees: random play-throughs (indigo) end shallow, by blunder. The deep region where competent play lives — and where the rare rule decides the game — is almost never reached, so the gate never tests it.</figcaption>
</figure>

## Translation, not inference

That leads to the finding I find most practical. Can you *repair* the gap by feeding the model examples of the rule? I tried — properly: DAgger, on-manifold harvested states, dozens of discriminating examples, two model sizes, refinement loops that draw fresh data every iteration.

(For the imitation-learning fans: "proper DAgger" here means the [Ross et al. (2011)](https://arxiv.org/abs/1011.0686) loop — collect states from the current flawed model's own play and relabel them with the oracle — not just dumping competent trajectories.)

It doesn't work. Across the board, the synthesized model stays rule-blind even when the rule is present in its training trajectories with near-certainty (you can watch it: the gate accuracy sits far below 1.0, meaning the rule *is* in the data, and after six refinement passes the model still hasn't encoded it). The behaviour is **rule translation, not rule inference**: the model faithfully encodes rules it is *told*, and does not reliably infer rules it is only *shown*. The actionable version: complete the specification before you synthesize. Verifying on the play distribution will *detect* an incomplete spec; it will not *repair* it.

## The same split on the belief side

Games with hidden information — poker and the like — add a second thing the model has to get right: not just the dynamics, but a *belief function*, the code that reconstructs what a player can't see from what they can. I expected the gap to show up here too. The first surprise was that it doesn't — and the reason is almost funny.

On small poker games (Kuhn, Leduc) the sampling gate is *provably* enough to certify the belief function; one can write the bound down. Random play turns out to be a **more** thorough explorer of a betting tree than skilled play, because it raises and calls indiscriminately while good play folds and bails. So the rare belief-states never hide from the gate — competent play only ever visits a subset of what random already covered. No gap.

But that tells you exactly what a gap *would* need: a game where skill takes you **deeper** than randomness — where depth comes from *surviving*, not from flailing. So I built the smallest game I could that has that shape. Call it Beacon, and it's essentially the picture you'd draw on a napkin: a walk where, at each step, you pick a move — one choice lets you continue, the wrong one ends the game on the spot. Random play wanders off the path almost immediately; skilled play walks all the way to the end. And at the very end there's a single decision that turns on a hidden fact about your opponent — a fact you could have read from the moves they made on the way down.

<figure class="cwm-fig">
<svg viewBox="0 0 600 235" role="img" aria-label="Beacon: a walk where one move continues and the wrong move ends the game; the final decision depends on hidden information the gate never tests">
  <g stroke="#6366f1" stroke-width="2.5" fill="none" marker-end="url(#cwm-arrow)">
    <line x1="72" y1="90" x2="126" y2="90"/><line x1="152" y1="90" x2="206" y2="90"/>
    <line x1="232" y1="90" x2="286" y2="90"/><line x1="312" y1="90" x2="366" y2="90"/>
    <line x1="392" y1="90" x2="446" y2="90"/><line x1="472" y1="90" x2="524" y2="90"/>
  </g>
  <g stroke="#f43f5e" stroke-width="1.5" fill="none" opacity="0.7">
    <line x1="60" y1="104" x2="60" y2="146"/><line x1="140" y1="104" x2="140" y2="146"/>
    <line x1="220" y1="104" x2="220" y2="146"/><line x1="300" y1="104" x2="300" y2="146"/>
  </g>
  <g fill="#f43f5e" opacity="0.75" font-size="10" font-family="ui-monospace,monospace" text-anchor="middle">
    <text x="60" y="162">✕ ends</text><text x="140" y="162">✕ ends</text>
    <text x="220" y="162">✕ ends</text><text x="300" y="162">✕ ends</text>
  </g>
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="10" fill="#f8fafc" text-anchor="middle">
    <circle cx="60" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="60" y="94">s0</text>
    <circle cx="140" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="140" y="94">s1</text>
    <circle cx="220" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="220" y="94">s2</text>
    <circle cx="300" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="300" y="94">s3</text>
    <circle cx="380" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="380" y="94">s4</text>
    <circle cx="460" cy="90" r="12" fill="#1a1a24" stroke="#6366f1" stroke-width="2"/><text x="460" y="94">s5</text>
    <circle cx="540" cy="90" r="14" fill="#1a1a24" stroke="#f43f5e" stroke-width="2.5"/><text x="540" y="94">s6</text>
  </g>
  <text x="540" y="60" fill="#f43f5e" font-size="15" text-anchor="middle">?</text>
  <text x="540" y="45" fill="#f43f5e" font-family="'Inter',sans-serif" font-size="10" text-anchor="middle">hidden-info decision</text>
  <text x="52" y="192" fill="#818cf8" font-family="'Inter',sans-serif" font-size="11">Random play falls off the path within a step or two…</text>
  <text x="256" y="212" fill="#f43f5e" font-family="'Inter',sans-serif" font-size="11">…so the gate never tests s5–s6, where the game is decided.</text>
  <defs><marker id="cwm-arrow" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#6366f1"/></marker></defs>
</svg>
<figcaption>Beacon: a hand-built witness where skill means <em>surviving</em> deeper, not exploring wider. One move continues; the wrong move ends the game. The final decision turns on a hidden fact — so a belief function that's wrong only at s6 passes a random-play gate and still loses every game.</figcaption>
</figure>

Now hand a model a belief function that is correct everywhere *except* that final stretch — the deep end of the walk that only skilled play ever reaches. It sails through the gate (random play never gets far enough to test it) and then loses every single game, because the one place its beliefs are wrong is the one place the game is actually decided. Same shape as the rare rule, now on the belief side: verified, and still wrong exactly where it counts.

To be upfront: Beacon is a *deliberately constructed witness*, not something a model stumbled into — an existence proof. And the deep placement isn't a trick, it's the whole point: it's the *only* spot that is simultaneously unreachable by the gate (which samples shallow, random play) and decisive for the outcome (the game is settled in the final round). Put the error anywhere shallower and the gate catches it; make it somewhere that doesn't decide games and it costs nothing. "Wrong exactly where the gate can't look *and* the game is won" is precisely the corner the construction has to hit — and Beacon proves that corner is non-empty.

There's a clean structural point underneath: a transition-accuracy gate is **blind by construction** to the belief function. What a player can and cannot see never appears in a "this state became that state" transition — so no amount of transition-checking can catch a wrong belief model; you need a *separate* check on the beliefs themselves. (These imperfect-information results use games I instrumented by hand to isolate the effect, rather than fully synthesized models — a distinction I'm careful to keep in the paper.)

The more hopeful half of the story is that this separate check is often *enough*, and provably so. In the paper I work out a coverage bound: a random inference gate is guaranteed to catch belief errors once it samples more than roughly `bᵈ` play-throughs, where `b` is how many choices a player faces at each step and `d` is how deep the game's decisions reach. Shallow games clear that bar easily — which is exactly why Kuhn and Leduc poker show *no* belief gap at all; their gate is provably sufficient. For games too large to enumerate, there's a companion bound that caps the undetected error a gate-passing belief function can hide. Beacon is simply the case engineered to sit on the wrong side of that bound. What's still missing — and what I'd flag as future work — is an *adversarial* belief check that deliberately samples the deep, skill-reachable region instead of hoping random play wanders in; that's the check that would actually close the Beacon-shaped hole.

## What I actually take from this

A passing test suite — or a sampling-based gate — is a *result-check with a coverage blind spot*. It certifies the model exactly where your samples land, and competent behaviour systematically lands somewhere else: the rare, pivotal, deep parts of the space. If you verify a world model (or, honestly, any model used for planning or decisions) by sampling, measure adequacy **on the distribution it will actually be used on**, not on a convenient random one. And when correctness depends on a rule, put the rule in the spec — don't hope the system infers it.

If you want the formal version, with the theorems and the numbers, it's in the [preprint](https://arxiv.org/abs/2607.14169). The [code is open too](https://github.com/JaviMaligno/code-world-models).

---

*Preprint: "When a Verified World Model Still Loses" ([arXiv:2607.14169](https://arxiv.org/abs/2607.14169)) · [code](https://github.com/JaviMaligno/code-world-models). Related reading: [Results-Oriented Programming](/en/blog/results-oriented-programming) and [Software Dissolving Into the Model](/en/blog/software-dissolving-into-the-model).*
