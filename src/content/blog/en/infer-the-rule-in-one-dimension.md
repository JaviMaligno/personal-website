---
title: "An LLM Can Infer the Rule You Forgot — in One Dimension"
description: "My last preprint concluded that LLMs translate rules and don't infer them. In continuous control that turns out to be false for a wall and true for a circle: the model repairs an omitted 1D rule in 105 of 111 attempts, and never once recovers the 2D version — through eight interventions designed to fix it."
pubDate: 2026-08-20
tags: ["AI", "Machine Learning", "Testing", "Research", "Agents"]
lang: en
translationKey: infer-the-rule-in-one-dimension
heroImage: "/blog/infer-the-rule-in-one-dimension.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/ARXIV_PENDING"
  - label: "Companion paper"
    url: "https://arxiv.org/abs/2607.14169"
linkedinSummary: |
  A few weeks ago I published a preprint arguing that LLMs translate rules and don't infer them. The follow-up is out, and it shows exactly where that conclusion stops being true.

  Move the same question from board games to continuous control — a cart on a rail, a wall that stops it dead, and a spec that simply omits the wall — and a current model does infer the missing rule from a handful of contact transitions. Not a local patch fitted to what it saw: the true global rule, with the right constant. It did that in 105 of 111 attempts, exact on 50 of 56 independent sample blocks.

  Then I gave the rule one more dimension: a circular region instead of a threshold in one variable. Repair collapsed to 0 of 156. So I spent the rest of the work attacking my own explanation — a region-first prompt at triple budget, flat edges instead of curved, naming the variable the rule reads, making the region's interior observable, and widening the evidence until three lines of least squares recover the region on every single sample. Eight interventions. None of them restored it, and the failure does not respond to more evidence at all.

  The positive controls place it precisely. Give the model the region's shape and its location, withholding only the radius, and it infers that number exactly, 20 times out of 20. Give it the shape alone and it recovers none. What is not induced is a located rule.

  The practical version, for anyone shipping a synthesized model behind a sampling check: coverage of the boundary is the whole game, and "it'll figure it out from the data" is a bet you can only make in one dimension. Anything with a shape, you still have to specify.

  Where have you seen a passing test suite certify precisely the part of the space that turned out not to matter?
---
A few weeks ago I wrote about [a world model that passes every test and still loses](/en/blog/verified-world-model-still-loses). The finding I was most confident about in that work was the pessimistic half: LLMs perform **rule translation, not rule inference**. They faithfully encode rules you *tell* them, and they don't reliably infer rules you merely *show* them. I tried hard to repair a rule-blind model from data — proper DAgger, harvested states, two model sizes — and it stayed blind.

That conclusion was right about the setting I measured it in, and I've now spent a few more weeks finding out where it stops being true. The short version: move from board games to continuous control, and a current model *does* infer the omitted rule from a handful of examples — reliably, exactly, writing the true global rule rather than a curve fit. Then give the same rule one more dimension and the whole capability disappears, through every intervention I could design against it. The write-up is a preprint, *An Omitted Mode Is a Rare Rule* (**[arXiv:PENDING](https://arxiv.org/abs/ARXIV_PENDING)**), with the [code and result artifacts open](https://github.com/JaviMaligno/code-world-models).

<style>
.cwm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.cwm-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.cwm-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
.cwm-table{width:100%;border-collapse:collapse;margin:1.5rem 0;font-size:.92rem}
.cwm-table th,.cwm-table td{padding:.55rem .7rem;border-bottom:1px solid rgba(255,255,255,0.1);text-align:left}
.cwm-table th{color:#94a3b8;font-weight:600}
.cwm-table td.n{font-family:ui-monospace,'JetBrains Mono',monospace;text-align:right;white-space:nowrap}
</style>

## From board games to a cart with a wall

The reason to redo this in continuous control is that the literature there disagrees with the shape of my result. Model-based RL treats world-model error as **pervasive and compounding** — a bit wrong everywhere, getting worse as you roll forward. My discrete result was the opposite: error that is *localized and pivotal*, exactly zero almost everywhere and catastrophic on a thin set. If that geometry doesn't survive the move to continuous state spaces, it's a quirk of board games.

So: a cart on a track, sigmoid reward plateaus at both ends, and a wall at some position that stops the cart dead. A planner does random-shooting MPC against a synthesized Python model of the physics. The spec handed to the LLM pins the integrator exactly and simply **omits the wall clause**. The gate is the same idea as before — synthesize, refine against 40 sampled rollouts, accept when every transition matches to $10^{-9}$.

When the training sample happens to contain no wall contact, the result is the discrete headline reproduced in physics, end to end: the artifact passes the gate at 1.000, is exact everywhere off the wall, is fully wall-blind on probes, and the planner that trusts it drives into the phantom region, gets **pinned at the wall in every episode**, and replans the same doomed plan every step for the whole episode — a return of about 0.02 against the true planner's 17.77. All 20 of those seeds, across two model sizes on disjoint sample blocks, did exactly that.

The rate that event happens at is not a mystery either. If a critical event has probability $r$ under the gate's sampling law and the gate draws $N$ rollouts, the probability that all $N$ miss it is exactly $(1-r)^N$ — no asymptotics, no assumptions beyond i.i.d. rollouts. At the headline knob $r = 0.0114$, so $(1-r)^{40} = 0.63$; measured, 20 of 40 independent samples missed the wall. The interesting factor of the danger is the one you can compute in closed form.

## This time, the model repairs the rule

Here is where my earlier conclusion breaks. When the wall *does* appear in the training sample — often just a handful of contact transitions — GPT-5.x doesn't stay blind and doesn't fit a curve. It reads the failing transitions and writes the true global rule:

```python
if x2 >= 8.0:
    return [8.0, 0.0]
```

Not a local patch around the observed contacts. The rule, with the right constant, valid everywhere.

Across the two one-dimensional instruments (the cart's position clamp and a pendulum's angular stop) it did this in **105 of 111 mode-containing synthesis draws**. Those draws share sampled rollout blocks, so the honest unit is the block rather than the draw: every attempt was exact on **50 of 56 instrument–stream blocks**, an exact 95% interval of [0.781, 0.960]. Of the six that missed, the gate caught two — superstitious local patches fitted to the observed contacts, which it refused.

That is a genuine reversal of the "translation, not inference" residual, and it's worth saying plainly rather than burying it: a numerically manifested discontinuity is learnable from data in a way a symbolic game rule was not. A wall announces itself. Four rows out of 3,200 tilt a linear fit by twelve orders of magnitude; the LLM instead names the discontinuity and writes it down.

## Then I made the rule two-dimensional

The obvious next question is whether that capability is about *dimension* or about *discontinuity*. So I built a 4D instrument: a mover in a plane, two circular patches, and the rule is that entering a patch freezes you. Same pipeline, same gate, same tolerance, same models. The rule is now a region — three constants instead of one.

Repair does not survive the move.

<figure class="cwm-fig">
<svg viewBox="0 0 600 210" role="img" aria-label="Repair from data: 105 of 111 draws on one-dimensional rules, 0 of 156 on two-dimensional regions">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF" text-anchor="middle">
    <line x1="170" y1="30" x2="170" y2="175" stroke="rgba(255,255,255,0.1)"/>
    <line x1="380" y1="30" x2="380" y2="175" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <line x1="590" y1="30" x2="590" y2="175" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
    <text x="170" y="193">0%</text><text x="380" y="193">50%</text><text x="590" y="193" text-anchor="end">100%</text>
  </g>
  <text x="160" y="70" text-anchor="end" fill="#f8fafc" font-size="13">1D rule (wall, stop)</text>
  <rect x="170" y="56" width="397" height="26" rx="4" fill="#6366f1"/>
  <text x="360" y="74" fill="#0b0b12" font-size="12" font-weight="700" font-family="ui-monospace,monospace">105 / 111 draws</text>
  <text x="160" y="134" text-anchor="end" fill="#f8fafc" font-size="13">2D rule (disc, square)</text>
  <rect x="170" y="120" width="3" height="26" rx="1.5" fill="#f43f5e"/>
  <text x="184" y="138" fill="#f43f5e" font-size="12" font-family="ui-monospace,monospace">0 / 156 draws</text>
</svg>
<figcaption>The same pipeline, the same models, the same gate. On one-dimensional hard rules the synthesizer recovers the true rule from a few contact transitions; on two-dimensional regions it recovers it in none of 156 mode-containing draws, spread over 20 distinct gate samples.</figcaption>
</figure>

Zero is a number that deserves suspicion, so: those 156 draws sit over 20 distinct sampled rollout blocks, which caps the per-block repair probability at 0.168 with 95% confidence. It isn't "never" — it's "not once in the evidence I have, and the evidence is wide enough to make that mean something."

What the artifacts write instead is the interesting part. The dominant failure is **dimensional reduction**: the disc becomes a half-plane at the right location and the wrong shape — a 1D threshold, the thing that worked on the cart, applied to a rule that isn't one. Others fit the convex hull of the freeze positions they observed, or invent a zone around the reward landmarks. Not one of the 76 artifacts that saw a patch encoded the patch it saw.

## Eight interventions, and what survives them

At this point the honest move is to attack your own explanation. If it's curvature, flat edges should fix it. If it's the prompt, a better prompt should fix it. So I ran eight interventions, each aimed at one candidate cause, and reported what each one changed beyond its target.

<table class="cwm-table">
<thead><tr><th>Intervention</th><th style="text-align:right">Repaired</th><th>What it rules out</th></tr></thead>
<tbody>
<tr><td>Region-first prompt, 3× budget</td><td class="n">0/40</td><td>the tested prompting and budget</td></tr>
<tr><td>Axis-aligned square, flat edges</td><td class="n">0/40</td><td>boundary curvature</td></tr>
<tr><td>A second model family</td><td class="n">0/3</td><td>one family's idiosyncrasy</td></tr>
<tr><td>A band in one coordinate</td><td class="n">0/40</td><td><em>nothing — target not identifiable</em></td></tr>
<tr><td>Naming the variable the trigger reads</td><td class="n">0/40</td><td>variable ambiguity</td></tr>
<tr><td>Mover stops inside the region</td><td class="n">0/40</td><td>the interior being unobservable</td></tr>
<tr><td>Mover clamped to the boundary</td><td class="n">0/40</td><td>the same, at matched evidence</td></tr>
<tr><td>Wider angular coverage of contacts</td><td class="n">0/40</td><td>the evidence's coverage</td></tr>
</tbody></table>

<p style="color:#94a3b8;font-size:.82rem;margin:-.5rem 0 1.5rem;text-align:center">Each row is a full campaign on the same 20 sampled blocks. None of them restores repair. The fourth is recorded rather than counted: on that instrument the target is provably unidentifiable, so a zero there means nothing.</p>

Two of those deserve a sentence. The square was the one I expected to work — if the model can write `x2 >= 8.0`, a box is four of those. It failed in a mirror image of the disc: artifacts wrote *discs* on square evidence. And the interior one was aimed at a theorem in the paper: because the patch freezes the mover at its previous position, no rollout ever occupies the region's interior, so a sample can only ever witness *entries* into it. That censoring is real, and I was fairly sure it was the cause. Two campaigns lifted it — one supplying eleven times more mode evidence — and repair stayed at zero. Being wrong about your own mechanism is the part of the process that actually moves it.

## What is actually missing: a *located* rule

The interventions are all negatives, and a negative is only worth the guarantee that its target was learnable in the first place. So, two positive controls.

**From outside the pipeline:** a plain algebraic least-squares circle fit — three lines of linear algebra, no prior, no language model — on exactly the evidence the synthesizer was handed. It recovers both the centre and the radius to within a tenth on 12 of 20 samples. And because the instrument lets me widen the angular spread of the contacts while holding their *number* fixed, I can dose the evidence until that fit succeeds on every single sample.

<figure class="cwm-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="As evidence coverage rises the trivial fit goes from 12 to 20 of 20 while the synthesizer stays at 0 of 20">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF">
    <line x1="105" y1="40" x2="105" y2="185" stroke="rgba(255,255,255,0.14)"/>
    <line x1="105" y1="185" x2="575" y2="185" stroke="rgba(255,255,255,0.14)"/>
    <text x="95" y="45" text-anchor="end">20/20</text>
    <text x="95" y="189" text-anchor="end">0/20</text>
    <text x="160" y="207" text-anchor="middle">111°</text>
    <text x="340" y="207" text-anchor="middle">129°</text>
    <text x="520" y="207" text-anchor="middle">185°</text>
    <text x="340" y="230" text-anchor="middle" fill="#64748b">angular coverage of the contact evidence</text>
  </g>
  <polyline points="160,101 340,73 520,45" fill="none" stroke="#6366f1" stroke-width="2.5"/>
  <circle cx="160" cy="101" r="5" fill="#6366f1"/><circle cx="340" cy="73" r="5" fill="#6366f1"/><circle cx="520" cy="45" r="5" fill="#6366f1"/>
  <text x="536" y="42" fill="#818cf8" font-size="12" font-family="ui-monospace,monospace">20</text>
  <text x="160" y="92" fill="#818cf8" font-size="11" text-anchor="middle" font-family="ui-monospace,monospace">12</text>
  <text x="340" y="64" fill="#818cf8" font-size="11" text-anchor="middle" font-family="ui-monospace,monospace">16</text>
  <polyline points="160,185 340,185 520,185" fill="none" stroke="#f43f5e" stroke-width="2.5"/>
  <circle cx="160" cy="185" r="5" fill="#f43f5e"/><circle cx="340" cy="185" r="5" fill="#f43f5e"/><circle cx="520" cy="185" r="5" fill="#f43f5e"/>
  <text x="536" y="189" fill="#f43f5e" font-size="12" font-family="ui-monospace,monospace">0</text>
  <text x="170" y="127" fill="#818cf8" font-size="12">three lines of least squares</text>
  <text x="170" y="170" fill="#f43f5e" font-size="12">the synthesizer</text>
</svg>
<figcaption>Holding the number of contacts fixed and widening only their angular spread. The trivial estimator improves until it recovers the region on every sample; the synthesizer recovers it on none, at every dose. The failure does not respond to evidence at all.</figcaption>
</figure>

**From inside the pipeline:** replace the missing clause with a *partial* one that states the rule's form and effect while withholding constants. Two levels, and they separate completely:

- Given the region's form **and** its centres, with only the radius withheld — one unknown number — the synthesizer infers it **exactly in 20 of 20 seeds**, agreeing with the truth at IoU 1.000 on every point of the probe grid. One artifact even comments "radius inferred from the provided transitions".
- Given the form **alone**, centres withheld: **0 of 20**.

Put together, that places the failure precisely, and it is narrower and stranger than "2D is harder". It is not the evidence — three lines of linear algebra recover the region from the same sample. It is not an inability to fit constants — given the location it nails the radius to float precision. It is not representational — told the rule outright, every arm writes the disc at gate 1.000 in zero refinement iterations. What the synthesizer does not do is **induce a *located* rule**: the form alone doesn't rescue it, the form plus its location does. When the template is refused, it memorises the contacts instead of fitting them.

And this isn't a code-versus-neural-networks story either. I ran the most favourable learned baseline I could build — the true physics pinned, with only the event function learned. On the cart it matches the code exactly: it recovers the threshold at 8.0 from four contacts, is float-exact on 3,200 held-out transitions, and passes the same $10^{-9}$ gate. On the 2D instrument it recovers the near patch on 12 of 20 blocks and *both* patches on none. The wall is easy for everything; the circle is hard for everything that has to find it from data.

## Verified, and wrong in a new way

One more result, because it's the one that changed how I read a passing gate. Among the 1D repairs, four artifacts wrote the correct clamp **and** a second, invented stop on the other side — at an angle their own training rollouts never reach. Their samples cannot refute the invention, so the gate accepts them at 1.000. I re-scored all 1,034 committed artifacts against freshly drawn, disjoint acceptance samples: an independent gate caught *one* of those four, by the luck of its draw. What convicts the other three is a dense grid, not any rollout.

That is the whole thesis in miniature, and it has a theorem attached. Because the mode freezes the mover, there is an entire class of wrong rules that agree with the truth on every transition of every possible rollout — unfalsifiable at any sample size and any tolerance. On one instrument the larger model reliably writes exactly such a rule: nineteen of its twenty artifacts pass the gate, an independent gate, and the paper's own probe, without encoding the region at all. The consolation is that the same argument makes them harmless: a model that is wrong only where no planner can reach costs nothing at play.

## What I take from this

Sampling verification certifies your model where your samples land. That was the last paper's point, and it survives the move to continuous control intact — including the closed-form factor for how often the sample misses what matters.

What's new is the repair story, and it's narrower than I'd have guessed in either direction. A capable synthesizer *will* recover a rule it has been shown, exactly and globally, when that rule is a threshold in one variable. It will not recover the same kind of rule when finding it means locating a region, and it doesn't get better with a stronger prompt, more budget, flatter geometry, or more evidence — I tried all four. So the practical rule I'd give is one clause sharper than last time: **coverage of the boundary is the whole game, and "the model will figure it out from the data" is a bet you can only make in one dimension.** Everything with a shape, you still have to specify.

If you want the formal version — the exact gate-miss law, the volume budget that separates programs from Lipschitz models, and the unfalsifiability theorem — it's in the [preprint](https://arxiv.org/abs/ARXIV_PENDING), and the [code and every result artifact are open](https://github.com/JaviMaligno/code-world-models).

---

*Preprint: "An Omitted Mode Is a Rare Rule" ([arXiv:PENDING](https://arxiv.org/abs/ARXIV_PENDING)) · [code](https://github.com/JaviMaligno/code-world-models). Companion paper: [When a Verified World Model Still Loses](https://arxiv.org/abs/2607.14169), and the post about it — [A World Model Can Pass Every Test and Still Lose](/en/blog/verified-world-model-still-loses).*
