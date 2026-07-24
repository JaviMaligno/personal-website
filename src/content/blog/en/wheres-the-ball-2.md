---
title: "Where's the Ball? Part 2 — a 60-Kilobyte Model, Two Sports, and the Signal VLMs Miss"
description: "A tiny network trained on my laptop solves the hidden-ball cases that frontier VLMs can't — and a two-sport transfer study reveals what, exactly, a model learns about a game."
pubDate: 2026-07-27
tags: ["AI", "Computer Vision", "Research"]
lang: en
translationKey: wheres-the-ball-2
heroImage: "/blog/wheres-the-ball-2.png"
linkedinImage: /blog/wtb2-david-goliath.png
repoUrl: https://github.com/JaviMaligno/wheres-the-ball
linkedinLinks:
  - label: "Part 1 (the VLM benchmark)"
    url: https://www.javieraguilar.ai/en/blog/wheres-the-ball/
  - label: "NBA SportVU tracking data"
    url: https://github.com/linouk23/NBA-Player-Movements
---

[Part 1](https://www.javieraguilar.ai/en/blog/wheres-the-ball/) ended on a sober note. Frontier vision-language models have a faint spectator's intuition — their guesses about a hidden football correlate with where it really is — but on the cases that matter, balls genuinely far from the center of the frame, none of them reliably beat the dumbest possible strategy: point at the middle and trust the camera operator.

That left an uncomfortable question hanging. Maybe the hard cases are just *hard* — maybe the players' positions don't contain enough information to find an off-center ball, and I'd been asking the models to do the impossible.

So I tested that directly. The answer is no: the information is there, and a model small enough to email can extract it.

## David, meet Goliath

I trained a [DeepSets](https://arxiv.org/abs/1703.06114) network — a permutation-invariant architecture that eats an unordered set of players and pools them into one guess — on the player *tracks* of SoccerNet's training clips: each player's position and velocity over one second, and nothing else. No pixels, no grass, no bodies. About 14,000 parameters, roughly 60 kB of weights, a few minutes of CPU on my laptop, zero API calls.

Then I evaluated it on the same hidden-ball items from Part 1, paired with the same models.

![A tiny tracker-fed network beats the camera bias where frontier VLMs sit at chance](/blog/wtb2-david-goliath.png)

On off-center balls the tiny network beats the camera bias **82% of the time**; given pixels, GPT-5.4 and Claude Opus 4.8 sit at 53% — statistically, a coin flip. Two honest footnotes before this goes to anyone's head. First, the little model reads *ground-truth* player tracks, so this is an information ceiling — it answers "is the signal there?". Second, the VLMs still post better global medians (0.147 vs 0.195), because they are pixel-precise on the easy, centered items where the camera has already done the work.

There's an obvious objection, though, and it deserved its own experiment: this is apples and oranges. One system reads pixels; the other reads clean tracking data. Maybe the VLMs would do fine if you handed them the tracks. So I ran the missing cell of the comparison: I gave GPT and Opus the **exact same one-second player tracks the tiny net saw, as plain text coordinates**, and asked the same question.

They got *worse*, not better. On the hard subset they dropped to 35–38% — below chance — and their correlation with the true ball position went from weakly positive to null or slightly *negative*. Handed the raw numbers, they appear to fall into the very centroid trap that broadcast geometry punishes (more on that below). Whatever spatial intuition these models have seems to live in pixels, not in coordinates. (The fourth cell of the grid — the tiny architecture trained on raw pixels — needs a vision model and stays out of scope; the grid is three cells and says plenty.)

That result sharpened the conclusion beyond what I expected, and it reframes Part 1: **the ball's position is written in the players' movements — plainly enough for a toy model — and the frontier models' failure isn't perception. Given the same information with the pixels stripped away, they do worse. What's missing is the geometric inference itself.** A fair caveat cuts the other way too: the tiny net was *trained* for this exact task and the VLMs are zero-shot — but that is precisely the question Part 1 asked, whether general game-knowledge substitutes for specialization. On this task, it doesn't.

## The camera lies

Along the way, one statistic explained something that had been bugging me since Part 1: why is naive geometry so useless in broadcast frames? The centroid of the players — "the ball is where the crowd is" — isn't just uninformative in image space. It's *anti*-correlated with the ball (−0.58): when the ball is far from the center of the frame, the player mass tends to be on the *opposite side*.

![The same statistic, two spaces: the camera flips its sign](/blog/wtb2-camera-lies.png)

The reason is the camera operator. When a ball is off-center, it's usually because it's moving fast — a long pass, a clearance — running *ahead* of the play while the players trail behind. Project that onto a camera that chases the ball and the geometry inverts. Strip the camera away — compute the same centroid in field coordinates — and the correlation flips to +0.83. Same statistic, same matches; the camera flips its sign. Every system in Part 1 that leaned on "the ball is near the players" was leaning on a lie.

## Two sports, one question: what actually transfers?

With a working specialist in hand, I could finally ask the question that motivated this whole project from the stands: **how much of this skill is "knowing football", and how much is universal team-sport structure?** I trained the same architecture on soccer (Metrica and SkillCorner tracking data) and on basketball (NBA SportVU), and crossed them.

![Zero-shot transfer between sports is asymmetric](/blog/wtb2-asymmetry.png)

Zero-shot — trained on one sport, tested cold on the other — the result is asymmetric in a way I didn't predict. Soccer→basketball fails: worse than an *untrained* centroid. But basketball→soccer *works*: 0.17 median error, beating soccer's own geometric baselines without ever seeing a football match. And no, it's not that the basketball dataset is bigger — subsampling it to match the soccer data leaves the result intact (0.174).

My working interpretation: in basketball the ball is almost always tightly coupled to the player mass — dribbles, screens, short passes — so the model learns a strong coupling that happens to be a decent universal prior. Football, with its long balls and loose play, teaches a weak coupling that doesn't export. If you want a model with portable game-reading instincts, train it on the sport where the ball never leaves the crowd.

## Fine-tuning, and a hypothesis that died twice

Does pretraining on one sport at least give you a head start on another? Here I got burned by my own enthusiasm — twice — and both times a control caught it.

First pass: with instantaneous player features, pretraining on soccer gave *no* advantage over training from scratch on the same basketball minutes. Second pass: with one-second trajectories it *did* — and I nearly wrote "temporal dynamics is what transfers." Then a shuffled-target control (pretrain the same net on soccer inputs with randomized ball positions — same optimization warm-up, zero knowledge) showed a third of that advantage was generic warm-start. And a feature ablation showed the rest wasn't about temporal depth at all: the advantage tracks whichever variants use *velocity* features, snapshot or trajectory alike.

![Real pretraining beats both scratch and the shuffled control, in both directions](/blog/wtb2-pretraining-arms.png)

What survives all the controls, pooled across both transfer directions: real pretraining wins in 12/13 seeds against scratch (p=0.002) and 9/10 against the shuffled control (p=0.011), with a modest ~5% edge that only shows up once you have ~30 minutes of the target sport. The refined picture: **positions carry the core signal, but their mapping is easy — half an hour of any sport teaches it from zero. What genuinely transfers is the harder-won skill of exploiting velocities**, which misleads zero-shot (speed scales are sport-specific) but pays off once briefly recalibrated.

"Knowing the game," for this family of models, turns out to mean something narrow and specific: knowing what to do with motion.

## Takeaways

- **The signal is in the tracks — and the VLM failure isn't perception.** A 60 kB network on player tracks solves the off-center balls that frontier VLMs can't (82% vs chance). Given the *same tracks as plain text*, the VLMs get worse, not better (35–38%, below chance). What they lack is the geometric inference itself; their spatial priors live in pixels, not coordinates.
- **Broadcast geometry is a trap.** The player centroid is anti-correlated with the ball in image space (−0.58) and strongly correlated in field coordinates (+0.83). The camera flips the sign.
- **Transfer between sports is real, small, and asymmetric.** Basketball exports its ball-sense to football; football doesn't return the favor. What transfers isn't rules or formations — it's the use of velocity features, worth ~5% after calibration.
- **The controls did the heavy lifting, again.** A shuffled-target pretraining control and a feature ablation each overturned a conclusion I was ready to publish. This project is three-for-three on "the first version of the story was wrong."

Next up is Level 3 of this ladder: the geometry and topology underneath — *when* do the players determine the ball, and can interpretable structure (Voronoi cells, pitch control, persistent homology) recover what the little black box learned? A workshop paper collecting the full transfer study is also in the works.

---

*Code, data pipelines, controls, and audits in the [`wheres-the-ball`](https://github.com/JaviMaligno/wheres-the-ball) repo. Player tracking from [SoccerNet-Tracking](https://github.com/SoccerNet/sn-tracking), [Metrica Sports](https://github.com/metrica-sports/sample-data), [SkillCorner](https://github.com/SkillCorner/opendata), and the NBA SportVU 2015-16 logs ([mirror](https://github.com/linouk23/NBA-Player-Movements); no explicit license — used for research only, not redistributed). Architecture: [DeepSets](https://arxiv.org/abs/1703.06114).*
