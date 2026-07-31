---
title: "Where's the Ball? Part 4 — When Nothing Moves"
description: "A coda to the trilogy: chasing the specialist's blind spot led somewhere I didn't expect. The hardest ball to locate isn't the one flying through the air — it's the one sitting perfectly still."
pubDate: 2026-07-31
tags: ["AI", "Computer Vision", "Research"]
lang: en
translationKey: wheres-the-ball-4
heroImage: "/blog/wheres-the-ball-4.png"
linkedinImage: /blog/wtb4-ball-state.png
repoUrl: https://github.com/JaviMaligno/wheres-the-ball
linkedinLinks:
  - label: "Part 1 (the VLM benchmark)"
    url: https://www.javieraguilar.ai/en/blog/wheres-the-ball/
  - label: "Part 2 (the 60 kB model & transfer study)"
    url: https://www.javieraguilar.ai/en/blog/wheres-the-ball-2/
  - label: "Part 3 (opening the black box)"
    url: https://www.javieraguilar.ai/en/blog/wheres-the-ball-3/
---

[Part 3](https://www.javieraguilar.ai/en/blog/wheres-the-ball-3/) closed the trilogy on a blind spot: the little specialist is overconfident on *loose balls* — the ones out in open space, far from the player mass. I meant to stop there. But a question kept nagging, and chasing it turned out to be worth one more post.

The question: aren't those hard cases just **set pieces**? A corner, a free kick — the ball's whereabouts depends entirely on whether the taker has struck it yet. Before the kick it's on a chalk mark; after, it's a projectile the players are still reacting to. Maybe the wide error is really about that awkward in-between, the ball in flight while everyone re-forms around where it's going.

It's a good hypothesis. It's also wrong — and being wrong pointed at something better.

## The premise didn't survive contact

Metrica's data comes with an event log — every pass, shot, and set piece, timestamped with the ball's start and end. So I could label each frame by what was happening and ask where the error actually lives.

Set pieces barely registered: as a fraction of playing time they're a rounding error, because the "set piece" event is the instant of execution, not a phase you spend minutes in. Long balls and clearances *were* modestly harder than short passes — a small win for the broader version of the hypothesis — but they didn't dominate either. The wide error was spread across ordinary open play.

The sharper cut wasn't the event label at all. It was the **speed of the ball**.

![The model needs motion: the still ball is the blind spot](/blog/wtb4-ball-state.png)

And it flips the intuition on its head. The ball *in flight* — fast, airborne, the case I'd expected to be hardest — is only mildly difficult. The hardest ball to locate is the one that's barely moving at all: settled, under 2 m/s, a dead ball or one resting at someone's feet. The correlation between ball speed and error is essentially zero; the structure is entirely in that first bar.

## No motion, no signal

Once you see it, it's the most on-brand result this project could have produced. Every part of this series has landed on the same finding: the signal a model reads to place a hidden ball is **motion** — where the running mass of players is heading. So what happens when nothing is moving?

There's nothing to read.

![Velocity is the signal — and it's nearly useless when nothing moves](/blog/wtb4-velocity-mechanism.png)

Strip the velocity channel out of the model and watch how much it costs, split by whether the ball is moving. When the ball is moving, velocity is worth a lot — dropping it inflates the error by about 0.04. When the ball is still, velocity is worth almost nothing: the model with velocity and the model without it are nearly the same, because there's no coherent motion for the velocity features to feed on. The specialist's whole edge evaporates in exactly the moment the pitch goes quiet. (This held in both train/test directions, and the collapse was even sharper the other way round — velocity's contribution fell essentially to zero on still balls.)

There's a second reason still balls are hard, and it sharpens Part 3's blind spot. The *worst* of the still balls aren't the ones near a touchline, where a throw-in pulls players into a tidy cluster. They're the ones sitting **centrally, far from everyone** — a dead ball in the middle of the park with the players spread out and nobody converging. Among still balls, the correlation between "distance from the player mass" and error is strong and steady (+0.53 to +0.65 across both directions). A ball no one is near and no one is moving toward is, quite literally, undetermined: the players have stopped telling you where it is.

## But in flight, you can still read the *direction*

That leaves the other half of the original question. Even if the ball in flight isn't the hardest case, the intuition behind it was real: while a ball travels, the players are already shaping what happens next with their runs. Maybe what's recoverable there isn't the ball's exact position, but where it's *going*.

So I asked the model a different question about fast balls — not "where is it?" but "which way is it heading?" — and had it predict the ball's direction of travel from the players alone.

![In flight, which way the ball is going is readable](/blog/wtb4-direction-flight.png)

It can. A random guess at a 2D direction is off by 90° on average; the players pin it to about 45°, with half of all fast balls placed within a 45° cone. Not precise — but unmistakably real: the configuration of the pitch encodes which way the ball is travelling, because the players are already leaning into the play. I'll be honest that this doesn't cleanly beat position — in flight, direction and position turn out to be recoverable to roughly the same degree, and comparing an angle to a distance is apples-to-oranges. The honest claim is the modest one: the direction is legible, not that it wins.

## Takeaways

- **The hardest ball to find is the one standing still.** Not the ball in flight — the settled ball, under 2 m/s, is where the specialist's error is highest. Ball speed and error are otherwise uncorrelated; the difficulty is concentrated entirely in stillness.
- **Because motion is the whole signal.** Velocity features carry the localization; when the ball is still there's no motion to read, and dropping velocity costs almost nothing. The model's strength and its blind spot are the same fact seen from two sides.
- **A dead ball no one is near is undetermined.** The worst still balls are central and far from the player mass (coupling-to-error correlation +0.53 to +0.65) — the players have simply stopped pointing at it.
- **In flight, direction is readable even if position isn't precise.** Players' runs pin a fast ball's heading to ~45° (chance is 90°). The original set-piece hunch was wrong about *which* phase is hard, but right that the players are always shaping what comes next.

Four parts in, the throughline is hard to miss. A hidden ball is found through motion — the frontier models can't act on that cue, a 60 kB network reads it sharply, and it turns out to be plain geometry. Which means the one thing none of them can do is find a ball that has stopped moving and drifted away from the crowd. The blind spot was never a kind of play. It was stillness.

---

*Code, the event-log analysis, and the velocity-ablation and direction experiments in the [`wheres-the-ball`](https://github.com/JaviMaligno/wheres-the-ball) repo. Soccer tracking and event data from [Metrica Sports](https://github.com/metrica-sports/sample-data). Previously: [Part 1](https://www.javieraguilar.ai/en/blog/wheres-the-ball/), [Part 2](https://www.javieraguilar.ai/en/blog/wheres-the-ball-2/), and [Part 3](https://www.javieraguilar.ai/en/blog/wheres-the-ball-3/).*
