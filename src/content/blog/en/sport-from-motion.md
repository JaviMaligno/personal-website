---
title: "Which Sport Is It? Recognising a Sport Only From How the Players Move"
description: "I removed the pitch, the ball and the kits and kept only moving dots. A small classifier recognises the sport 83% of the time; of five frontier models, only one shows that it uses the order of the snapshots."
pubDate: 2026-10-24
tags: ["AI", "Vision", "Sports", "Evaluation", "Claude"]
lang: en
translationKey: sport-from-motion
heroImage: "/blog/sport-from-motion.png"
repoUrl: "https://github.com/JaviMaligno/sport-from-motion"
linkedinImage: "/blog/sport-from-motion-quiz.png"
---

<style>
.sfm-fig{margin:2rem 0;padding:1rem;background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:8px}
.sfm-fig svg{width:100%;height:auto;display:block}
.sfm-fig img{width:100%;height:auto;display:block;margin:0 !important;border-radius:4px}
.sfm-fig figcaption{color:#94a3b8;font-size:.9rem;margin-top:.75rem;line-height:1.5}
.sfm-fig .t{fill:#e2e8f0;font:600 13px ui-sans-serif,system-ui,sans-serif}
.sfm-fig .s{fill:#94a3b8;font:11px ui-sans-serif,system-ui,sans-serif}
.sfm-fig .box{fill:#20202c;stroke:rgba(255,255,255,0.12)}
.sfm-fig .dot{fill:#5eead4}
.sfm-fig .dim{fill:#64748b}
.sfm-fig .arw{stroke:#fbbf24;stroke-width:1.5;fill:none}
.sfm-fig .trk{stroke:#5eead4;stroke-width:1.6;fill:none}
</style>

When we watch sport, there is something we do without thinking: we recognise what we are watching before we can explain why. I noticed it while watching a video where you could barely make out the pitch. Even so, I knew straight away it was rugby and not football. What gave it away was not the setting but **how the players moved**.

I was left wondering whether that can be isolated. If I remove everything else (the pitch, the ball, the colours, the kits) and turn the players into dots, is the sport still there? And does a model see it?

To test it I prepared images like this one, which is exactly what the models received:

![Eight snapshots of the same play: ten grey dots on a white background, no pitch, no ball](/blog/sport-from-motion-quiz.png)

Eight snapshots of a play, about 0.5 seconds apart. Ten grey dots, one per player, seen from above. Nothing else: no pitch, no ball, no colours, no scale. Which sport is it? I'll give the answer at the end, along with what the models said.

The question is a sibling of [*Where's the Ball?*](/en/blog/wheres-the-ball), where I hid the ball and asked models to find it by looking at the players. Here I hide **everything** except the players and ask about the whole game: **is movement enough to recognise a sport?**

## Moving dots

The representation comes from a classic perception experiment: [Johansson's (1973)](https://en.wikipedia.org/wiki/Biological_motion) point-light displays, in which a person filmed in the dark with a few lights on their joints is instantly recognised as someone walking or dancing. Here each dot is a whole player, and what has to be recognised is the sport.

I used real tracking data from four sports:

- **American football**: [NFL Big Data Bowl 2023](https://www.kaggle.com/competitions/nfl-big-data-bowl-2023).
- **Basketball**: NBA SportVU 2015-16, 31 games.
- **Handball**: [EIGD-H](https://data.uni-hannover.de/dataset/eigd) (German Bundesliga, Kinexon sensors) and [TeamTrack](https://github.com/AtomScott/TeamTrack).
- **Soccer**: [SkillCorner](https://github.com/SkillCorner/opendata), [Metrica](https://github.com/metrica-sports/sample-data) and TeamTrack.

Rugby, the original question, is left out: there is no public rugby tracking data good enough to do this properly.

Each clip is 4 seconds of 10 randomly chosen players (the number of players would give the sport away), randomly rotated and rescaled so that the size of the pitch says nothing either. The models got 400 clips, 100 per sport, from 151 different games.

The interesting part is not only whether they get it right, but **which part of the signal they use**. So each clip is shown under several conditions, always the same clips:

<figure class="sfm-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Five conditions for the same clip: eight snapshots in order; the same eight shuffled; a single snapshot; each player in their own cell, which removes the team's shape; and each player also rotated, which removes their shared direction too.">
<g transform="translate(6,10)">
<rect class="box" width="110" height="150" rx="6"/>
<circle class="dot" cx="25" cy="40" r="3"/><circle class="dot" cx="45" cy="48" r="3"/><circle class="dot" cx="70" cy="42" r="3"/><circle class="dot" cx="90" cy="55" r="3"/>
<circle class="dot" cx="30" cy="95" r="3"/><circle class="dot" cx="52" cy="102" r="3"/><circle class="dot" cx="76" cy="96" r="3"/><circle class="dot" cx="95" cy="110" r="3"/>
<path class="arw" d="M20 70 H95 M89 66 L95 70 L89 74"/>
<text class="s" x="55" y="135" text-anchor="middle">1 → 8</text>
<text class="t" x="55" y="178" text-anchor="middle">Motion</text>
<text class="s" x="55" y="195" text-anchor="middle">8 snapshots</text><text class="s" x="55" y="209" text-anchor="middle">in order</text>
</g>
<g transform="translate(125,10)">
<rect class="box" width="110" height="150" rx="6"/>
<circle class="dot" cx="25" cy="40" r="3"/><circle class="dot" cx="45" cy="48" r="3"/><circle class="dot" cx="70" cy="42" r="3"/><circle class="dot" cx="90" cy="55" r="3"/>
<circle class="dot" cx="30" cy="95" r="3"/><circle class="dot" cx="52" cy="102" r="3"/><circle class="dot" cx="76" cy="96" r="3"/><circle class="dot" cx="95" cy="110" r="3"/>
<text class="s" x="55" y="135" text-anchor="middle">5, 2, 8, 1…</text>
<text class="t" x="55" y="178" text-anchor="middle">Shuffled</text>
<text class="s" x="55" y="195" text-anchor="middle">the same 8,</text><text class="s" x="55" y="209" text-anchor="middle">out of order</text>
</g>
<g transform="translate(244,10)">
<rect class="box" width="110" height="150" rx="6"/>
<circle class="dot" cx="35" cy="60" r="3"/><circle class="dot" cx="55" cy="72" r="3"/><circle class="dot" cx="75" cy="58" r="3"/><circle class="dot" cx="48" cy="92" r="3"/><circle class="dot" cx="80" cy="95" r="3"/>
<text class="s" x="55" y="135" text-anchor="middle">1</text>
<text class="t" x="55" y="178" text-anchor="middle">Formation</text>
<text class="s" x="55" y="195" text-anchor="middle">a single</text><text class="s" x="55" y="209" text-anchor="middle">snapshot</text>
</g>
<g transform="translate(363,10)">
<rect class="box" width="110" height="150" rx="6"/>
<path class="trk" d="M18 30 q10 -6 20 2"/><path class="trk" d="M62 32 q8 8 22 2"/>
<path class="trk" d="M18 70 q12 4 20 -4"/><path class="trk" d="M62 72 q10 -8 22 -2"/>
<path class="trk" d="M18 108 q10 -4 20 4"/><path class="trk" d="M62 110 q8 6 22 -4"/>
<text class="t" x="55" y="178" text-anchor="middle">Kinematics</text>
<text class="s" x="55" y="195" text-anchor="middle">each player in a</text><text class="s" x="55" y="209" text-anchor="middle">cell: no shape</text>
</g>
<g transform="translate(482,10)">
<rect class="box" width="110" height="150" rx="6"/>
<path class="trk" d="M18 32 q2 -10 16 -6"/><path class="trk" d="M84 26 q-10 8 -20 6"/>
<path class="trk" d="M26 64 q10 10 12 0"/><path class="trk" d="M66 78 q10 -10 20 -2"/>
<path class="trk" d="M34 116 q-10 -4 -14 -12"/><path class="trk" d="M62 104 q8 10 22 8"/>
<text class="t" x="55" y="178" text-anchor="middle">Solo kinematics</text>
<text class="s" x="55" y="195" text-anchor="middle">and each rotated:</text><text class="s" x="55" y="209" text-anchor="middle">no shared direction</text>
</g>
<text class="s" x="300" y="242" text-anchor="middle">Same clips in every condition: each difference is measured clip by clip</text>
</svg>
<figcaption>If a model does as well with the snapshots shuffled as in order, it is not reading motion: it is reading loose shapes. That comparison is what everything else hinges on.</figcaption>
</figure>

## First, check that the signal exists

Before asking anyone, I needed to know whether the question has an answer. I trained two small specialists, with cross-validation grouped by game so they could not recognise the game instead of the sport: [MiniRocket](https://arxiv.org/abs/2012.08791), which is essentially thousands of random filters plus a regression, and a [DeepSets](https://arxiv.org/abs/1703.06114) network over each player's trajectory. Minutes of CPU on a laptop.

On the same 400 clips the models would see, **MiniRocket is right 83% of the time and DeepSets 80%**, against a 25% chance level. And motion is what counts: shuffle the snapshots and MiniRocket loses 12 points; give DeepSets a single snapshot and it drops to 54%. The information is in how the players move, and a very small model finds it.

It is the same pattern as in [Part 2 of *Where's the Ball?*](/en/blog/wheres-the-ball-2): the signal is there, and the interesting question is who can see it.

## The hard part was removing the shortcuts

That 83% did not come out on the first try, and most of the work in the experiment went into making sure it was not lying. A trained classifier learns anything that separates the classes, and tracking data has plenty of things that separate sports without being the sport:

- **The number of players.** Basketball has 10, soccer 22. So every clip has exactly 10, chosen at random.
- **The size of the pitch.** So everything is rescaled. And keeping the 10 *most central* players turned out to be a shortcut too: in soccer and handball that compact group looks like a basketball court. With 10 random players, the specialists gain 7 points.
- **The capture system.** This was the most instructive one.

<figure class="sfm-fig">
<img src="/blog/sport-from-motion-jitter-en.png" alt="Trained on Metrica, SkillCorner and SportVU, MiniRocket is right 97% of the time on those sources but only 17% on TeamTrack, which it had not seen; with the same smoothing for every source it rises to 89%." aria-label="Trained on Metrica, SkillCorner and SportVU, MiniRocket is right 97% of the time on those sources but only 17% on TeamTrack, which it had not seen; with the same smoothing for every source it rises to 89%." />
<figcaption>Trained on three sources and tested on a fourth it has never seen, the classifier sinks below chance. It had not learned to tell soccer from basketball: it had learned to tell cameras apart.</figcaption>
</figure>

TeamTrack films with a fisheye camera, and on a large soccer pitch its positions jitter: about seven times the acceleration of the same sport measured by other systems. A classifier that has not seen TeamTrack reads that jitter as basketball's stop-and-go and labels almost all of its soccer as basketball. Smoothing every source the same way fixes it, and on the final set it reaches 95% on the unseen source.

There were more, all of the same kind:

- NFL plays started just before the snap, so every clip was "still, then everyone at once". Now each clip starts at a random moment of the play, at least one second after the snap.
- TeamTrack marks undetected players with the coordinate (0, 0), which, unfiltered, shows up as a motionless dot in a corner.
- SportVU sometimes records the same player under two IDs, so the model saw 9 dots instead of 10.
- The two halves of the same handball game counted as different games in the validation.

None of these shortcuts is exotic. They are what happens when you mix data from six sources with different capture systems, and none of them shows up if you only look at the final number.

## The frontier models

With clean data, I prepared a run with five frontier models: **GPT-5.6 Sol, GPT-5.6 Terra, Claude Opus 5.5, Claude Sonnet 5 and Gemini 3.1 Pro**. I also added [Jev](/en/blog/jev-after-the-hype), a typed-decision model that only reads text and returns a probability per option directly. Before seeing a single answer I wrote down a [pre-registration](https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/preregistration.md): the hypotheses, the four primary contrasts per model, the correction for multiple comparisons, and the exact rule for saying that a model "reads motion". With 20 contrasts and data like this, it is very easy to find something without rules fixed in advance.

<figure class="sfm-fig">
<img src="/blog/sport-from-motion-accuracy-en.png" alt="Accuracy with 8 snapshots in order: frontier models land between 0.26 and 0.47 once their response bias is corrected; MiniRocket reaches 0.83 and DeepSets 0.80." aria-label="Accuracy with 8 snapshots in order: frontier models land between 0.26 and 0.47 once their response bias is corrected; MiniRocket reaches 0.83 and DeepSets 0.80." />
<figcaption>The best frontier model is right 47% of the time; the specialists, 80-83%. Hollow circles are raw accuracy; filled ones, accuracy corrected for each model's favourite sport.</figcaption>
</figure>

The first thing that stands out is that the models have a **favourite sport** they fall back on when unsure. GPT-5.6 Sol answers American football on 62% of clips, Gemini on 66%, and Sonnet answers soccer on 64%. That inflates accuracy on the favourite and sinks it on the rest, so besides raw accuracy I computed a version **corrected for that bias**, always estimated on games other than the clip's own. With the correction, Sol, Terra, Opus and Gemini sit above chance. Sonnet 5 does not.

<figure class="sfm-fig">
<img src="/blog/sport-from-motion-recall-en.png" alt="Recall by sport: frontier models recognise American football or soccer depending on their favourite, but none goes above 0.15 on handball; MiniRocket is between 0.79 and 0.90 on all four." aria-label="Recall by sport: frontier models recognise American football or soccer depending on their favourite, but none goes above 0.15 on handball; MiniRocket is between 0.79 and 0.90 on all four." />
<figcaption>No frontier model recognises handball (between 0.04 and 0.15). Basketball and handball end up read as American football or soccer. MiniRocket recognises all of them about equally well.</figcaption>
</figure>

## Does the order matter?

The question that decides whether a model *sees motion* is the one from the conditions figure: is it less accurate when the snapshots are shuffled?

<figure class="sfm-fig">
<img src="/blog/sport-from-motion-order-en.png" alt="Accuracy points lost when the snapshots are shuffled, with confidence intervals: Claude Opus 5.5 loses 0.10 [0.05, 0.16]; the other four models sit around zero; MiniRocket loses 0.12. With 8-second clips and no American football, Opus and GPT-5.6 Sol lose 0.08." aria-label="Accuracy points lost when the snapshots are shuffled, with confidence intervals: Claude Opus 5.5 loses 0.10 [0.05, 0.16]; the other four models sit around zero; MiniRocket loses 0.12. With 8-second clips and no American football, Opus and GPT-5.6 Sol lose 0.08." />
<figcaption>Only Claude Opus 5.5 clearly loses accuracy when the snapshots are shuffled (the only difference that survives the correction for multiple comparisons). Hollow circles are an exploratory test with 8-second clips and no American football.</figcaption>
</figure>

Under the rule fixed in advance, **Claude Opus 5.5 is the only one of the five that reads temporal order**: shuffling the snapshots costs it 10 points, with an interval from 5 to 16, almost as much as MiniRocket. It holds up across replicates and, as an exploratory check, with 8-second clips.

Some nuances matter:

- **Opus's effect is concentrated in American football and basketball**, and is null in handball and soccer. In American football part of the signal may be the acceleration at the start of the play, which is still there even though the clips start after the snap. The 8-second test has no American football and the effect is still there (+0.08), which suggests it is not only that.
- **For the other four there is no evidence**, which is not the same as evidence that they don't read it. From the intervals, order adds at most 3 to 6 points for them. And there are exploratory hints: GPT-5.6 Sol loses 8 points with 8-second clips, and Sol and Gemini read order within American football, offset in the total by other sports.
- **They get something from shapes.** Sol, Terra and Gemini are above chance even with the snapshots shuffled, and Sol even with a single snapshot. They see something in how the players are arranged, but there is no evidence that how that arrangement changes helps them.

## What didn't help

I also tried three things that looked promising, and none of them moved the results clearly:

- **Coordinates as text instead of images.** Neither consistently worse nor better. Gemini does somewhat better with text, without reaching significance. Jev, which can only read text, stays at chance: it answers "soccer" on 90-100% of clips. Its probabilities seem to move a little with the order (bias-corrected, 0.34 with the snapshots in order against 0.21-0.23 shuffled), but they almost never change its answer, and it is not a difference I tested.
- **Telling it what to look for.** A prompt that describes how each sport moves, without numbers, raises accuracy by 0 to 3 points. Nothing that survives the correction.
- **Trails and video.** Drawing each player's trail helps no one, and costs Sol 7 points. With video, Gemini is about 7 points better than with the sheet, but it is exploratory and not enough to claim.

## What I take away

The information needed to recognise a sport is in the players' movement, and a classifier that fits on a laptop extracts it 83% of the time. Frontier models, on this task and with these representations, land between chance and 47%, and only one of the five shows that it uses the order of the snapshots.

I don't conclude from this that the others "don't see movement": I conclude that there is no evidence they use it, and that if they do, it is not much. Nor that Opus reads movement in general: it does so mostly in two sports. What does seem robust to me is the gap with the specialists, and how much it took to reach a number worth trusting. Every shortcut I removed would have told a different story.

And the sheet at the top is **basketball**. Three models answered American football (ten dots almost in a line look like a line of scrimmage) and two answered soccer. All three specialists, MiniRocket, DeepSets and the movement-statistics classifier, got it right.

---

*Code, pre-registration and full results at [github.com/JaviMaligno/sport-from-motion](https://github.com/JaviMaligno/sport-from-motion). The analysis follows the [pre-registration](https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/preregistration.md), and the [results](https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/results-final.md) include everything that did not work out. The data is not redistributed; each source has its own licence.*
