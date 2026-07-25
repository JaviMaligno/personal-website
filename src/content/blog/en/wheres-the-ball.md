---
title: "Where's the Ball? Testing Whether a VLM Has a Spectator's Intuition"
description: "I hid the ball from vision-language models and asked them to find it from the players alone. The answer was interesting — but the more interesting part was how easily I almost concluded the wrong thing."
pubDate: 2026-07-24
tags: ["AI", "Computer Vision", "Research"]
lang: en
translationKey: wheres-the-ball
heroImage: "/blog/wheres-the-ball.png"
linkedinImage: /blog/wheres-the-ball-correlation.png
repoUrl: https://github.com/JaviMaligno/wheres-the-ball
linkedinLinks:
  - label: "Dataset (SoccerNet-Tracking)"
    url: https://github.com/SoccerNet/sn-tracking
  - label: "Closest specialist work (TranSPORTmer)"
    url: https://arxiv.org/abs/2410.17785
---

Watch a football match from the top row of the stadium, where the ball is a barely-visible speck, and something curious happens: you usually know where it is anyway. The players tell you. Bodies lean, a cluster forms, everyone starts drifting the same way — and your eye lands on the ball a beat before you actually see it. It's not tracking. It's a kind of *social* inference: you know the game, so the people tell you about the thing.

I wanted to know whether a generalist vision-language model has that same intuition. Not a specialist tracker trained on ball trajectories — those exist and they're good ([Maksai et al.](https://arxiv.org/abs/1511.06181), [Kim et al. 2023](https://arxiv.org/abs/2306.08206), [TranSPORTmer](https://arxiv.org/abs/2410.17785) all infer the ball from player motion). I mean a model that "knows the game" the way a person in the stands does, and has never been trained for this task specifically. Can it look at a frame with the ball erased and point to where it must be?

The honest answer turned out to be *yes, a little, and only the biggest models* — but getting to an answer I actually trust was most of the work, and it's the part worth writing about.

## The setup

I used [SoccerNet-Tracking](https://github.com/SoccerNet/sn-tracking): broadcast clips with per-frame bounding boxes for every player and the ball. For each frame I **removed the ball** with LaMa inpainting — deep inpainting that reconstructs a coherent patch of grass, line, or shirt where the ball was, so the model can't cheat by spotting an editing smudge. (Classical inpainting left tell-tale blurs on pitch lines; a leak-control step with a VLM confirmed the deep version leaves nothing to latch onto.) Then I asked several models for the ball's coordinates and scored the distance to the truth.

The models: **GPT-5.4**, **Claude Opus 4.8**, **Claude Sonnet 4.6** (all via API), and **Qwen2.5-VL-7B** as an open-source reference, run on a GPU. Against them, two dumb baselines: "the ball is at the center of the frame" and "the ball is at the centroid of the players."

## The trap I walked straight into

My first run looked great. GPT beat the center baseline; on the hardest cases — balls far from the middle of the frame — it seemed to win **64%** of the time. Tidy story: generalist AI has spectator intuition. I could have written *that* article.

Two problems, both mine.

First, a confound. Broadcast cameras *follow the ball* — they keep it near the center of the shot. So "just guess the center" isn't a dumb baseline at all; it's a strong one, and any model that leans central looks smart for the wrong reason. Second, and worse: my sample was tiny. That 64% came from **14 items**. When I put a bootstrap confidence interval around it, the interval ran from 36% to 86% — comfortably including 50%, i.e. chance.

![How a small sample almost fooled us](/blog/wheres-the-ball-sample-trap.png)

So I rebuilt the test to defuse both issues: I balanced the dataset by the ball's distance from the center (so "guess the center" is useless by construction), and I scaled up. At a larger sample the same off-center win-rate settled at **55%**, and its interval *still* touched 50%. The exciting first result hadn't survived contact with statistics. It was a mirage made of a followed camera and fourteen data points.

I mention this not to be self-deprecating but because it's the whole point: a confounded baseline plus a small sample will hand you a satisfying, publishable, wrong conclusion, and it will feel true. The only defense is boring — de-bias, scale, bootstrap, and try to break your own finding before you believe it.

## What's actually true

Once the sample was honest, I stopped leaning on error-on-a-hard-subset (still underpowered) and used a better-behaved measure: **does the model's prediction correlate with where the ball actually is**, across the whole range of positions? That question the data can answer.

![Correlation of each model's prediction with the true ball position](/blog/wheres-the-ball-correlation.png)

- **Claude Opus 4.8** has the clearest signal — its guesses track the true ball position on both axes, and the confidence intervals stay clear of zero.
- **GPT-5.4** shows partial signal (solid horizontally, noisier vertically).
- **Qwen2.5-VL-7B (open)** and **Claude Sonnet 4.6** are, statistically, **flat** — their intervals straddle zero. They aren't pointing at the center out of laziness (I checked — their predictions are spread out); they're just not tracking the ball.

So the spectator intuition is real, but faint, and it's a frontier-model trait: it shows up in the big closed models and not in the smaller open one or the mid-tier Claude. And a sober caveat that survived all the scaling: **from a single frame, no model reliably beats the center bias on genuinely off-center balls.** The intuition is there in aggregate; it isn't strong enough to nail the hard, wide cases from one still image.

One more twist, which I liked. I gave every model an "informed" prompt — naming the sport and spelling out what a spectator uses (players orient toward the ball, converge on it, the carrier leads a cluster). It helped **GPT a lot** (its correlation jumped), did **nothing for Sonnet**, and barely moved Opus. Read that carefully: Sonnet's problem was never that it didn't know football. Telling it the rules changed nothing, because its bottleneck is *seeing*, not *knowing*. For GPT, which could already reason about the scene, the framing unlocked headroom — the prompt mattered about as much as the model tier.

![Neutral vs informed prompt: mean correlation with the true ball position, per model](/blog/wheres-the-ball-informed.png)

## The video that wasn't about video

Here's where I was sure I knew the answer in advance. A single frame is ambiguous; a spectator's real trick is watching the play *develop*. So I gave the models short sequences — four frames spanning a few seconds, the ball erased from all of them — expecting the motion to unlock the hard cases.

It did seem to help GPT. But before believing it, I ran the control that matters: I **shuffled the frames into a random order**. If a model reads motion, scrambling time should destroy the benefit.

![Nobody reads motion — it is a multi-view effect](/blog/wheres-the-ball-multiview.png)

Shuffling changed nothing. The order of the frames was the single cleanest null in the whole experiment. No model is integrating the *trajectory* of the play — they aren't reasoning about motion at all. What actually changed with multiple frames was something duller and stranger: **extra views of the scene**, in any order. And the two frontier models handle that in opposite ways. GPT *aggregates* — more looks at the moment, even scrambled, sharpen its guess. Opus gets *diluted* — the extra frames pull it away from a target-frame read it was already better at. The best single-frame model was the worst at using more frames.

That's a more interesting finding than "video helps," and I'd have missed it if I'd trusted the first, flattering version.

## Takeaways

- **Generalist VLMs do have a faint spectator's intuition** — their guesses correlate with the hidden ball — but it's a frontier-model trait (Opus clearest, GPT partial) and it's weak: a single frame doesn't crack the genuinely hard cases.
- **They don't reason about motion.** What looks like temporal understanding is really multi-view aggregation, and models differ in whether extra views help or hurt.
- **Knowledge isn't the bottleneck; seeing is.** Explaining the game helped the model that could already reason visually and did nothing for the one that couldn't.
- **The methodology was the hard part.** A followed camera and a small sample produced a clean, wrong story that felt right. De-biasing, scaling, bootstrapping, and adversarially auditing my own results changed the conclusion twice.

There's a Level 2 waiting — other sports, whether the skill transfers, and the geometry underneath it all — but that's for later. For now the honest headline is smaller and better than the one I almost wrote: the model in the stands can feel where the ball is, a little, if it's big enough; it just can't watch the play to find it.

---

*Code, data pipeline, and the full audit (bootstrap CIs and all) are in the [`wheres-the-ball`](https://github.com/JaviMaligno/wheres-the-ball) repo. Built on [SoccerNet-Tracking](https://github.com/SoccerNet/sn-tracking); ball removed with [LaMa](https://github.com/advimman/lama) via [IOPaint](https://github.com/Sanster/IOPaint). Prior specialist work worth reading: [Maksai et al.](https://arxiv.org/abs/1511.06181), [Kim et al. 2023](https://arxiv.org/abs/2306.08206), [TranSPORTmer](https://arxiv.org/abs/2410.17785).*
