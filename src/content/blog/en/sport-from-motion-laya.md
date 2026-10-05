---
title: "Teaching a Small Model to Recognise a Sport From Moving Dots"
description: "I fine-tuned Laya, a 322M open-weights decision model, on the same moving dots the frontier models failed on. With the official recipe it learned nothing; with enough training it learned to read the order of the snapshots, but only for some seeds."
pubDate: 2026-10-30
tags: ["AI", "Fine-tuning", "Sports", "Evaluation", "Open Models"]
lang: en
translationKey: sport-from-motion-laya
heroImage: "/blog/sport-from-motion-laya.png"
repoUrl: "https://github.com/JaviMaligno/sport-from-motion"
linkedinImage: "/blog/sport-from-motion-laya-curves-en.png"
---

<style>
.sfml-fig{margin:2rem 0;padding:1rem;background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:8px}
.sfml-fig img{width:100%;height:auto;display:block;margin:0 !important;border-radius:4px}
.sfml-fig figcaption{color:#94a3b8;font-size:.9rem;margin-top:.75rem;line-height:1.5}
</style>

In [*Which Sport Is It?*](/en/blog/sport-from-motion) I turned players into dots and asked whether the sport could still be recognised from how they move. The answer had two halves. A small classifier trained on the dots got it right 83% of the time. Five frontier models, shown the same clips, landed between chance and 47%, and only one of them, Claude Opus 5.5, showed that it used the order of the snapshots.

That left an obvious gap in the middle. The specialists that worked had been trained on the data; the language models that struggled had not. What happens if you take a language model, a small one, and train it on exactly what the specialists saw?

## The model: Laya

[Laya](https://huggingface.co/convaiinnovations/laya) is an open-weights decision model from Convai Innovations, released under Apache 2.0. Like [Jev](/en/blog/jev-after-the-hype), it does not write an answer: you give it a state, a question and a list of options, and it returns a probability for each option. I used the multilingual checkpoint, 322 million parameters on an mmBERT encoder, because its 1,024-token context fits every clip without cutting anything.

The input is the one Jev received in the previous experiment: the coordinates of the 10 dots over 8 snapshots, written as text. The question is the same too, four options: American football, basketball, handball or soccer. Untouched, Laya gets 24% of the clips right, which is chance.

To make the comparison fair, I trained it the way the specialists were trained:

- **The same folds.** Five splits grouped by game, so that no game appears in both training and test, built with the same seed as MiniRocket and DeepSets. Each clip ends up predicted by a model that never saw it.
- **The same 400 clips** that the frontier models answered, so every number here sits next to theirs.
- **The same conditions**: snapshots in order, the same snapshots shuffled, and a single snapshot.

Training ran on Kaggle's free GPUs (two T4s), so it cost nothing, and before the first run I wrote a [pre-registration](https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/preregistration-laya.md) with the hypotheses, the four contrasts and the correction for multiple comparisons, as in the main experiment.

## The official recipe learned nothing

Laya ships with a fine-tuning notebook for exactly this hardware. I used it as is: 4 epochs, its learning rates, its loss. The result was 23% on the 400 clips. Looking inside, the model had settled on giving all four options the same score for every clip, whatever the dots were doing.

That number alone says nothing about Laya. A model can end up at chance because there is nothing to learn, because the code is broken, or because it was not trained for long enough, and from the outside the three look identical. To separate them I ran a **positive control**: the same clips, but with an arbitrary tag at the top of each one that encodes the answer (`tag: Q7` for soccer, `tag: M2` for basketball, and so on). The tag means nothing, so the untrained model cannot use it; a model that learns during training can.

With the official recipe, the control reached 72%. So the code trains, but even a perfect clue is not fully learned in that budget. The notebook fine-tunes on about 6,000 examples, which comes to some 375 weight updates; here there are about 1,100 per fold, and 72 updates in total.

The fix had to be chosen without looking at the result I wanted to measure, so I used the control for that too: the number of epochs became the first point at which the control is learned (≥ 95% on a slice of training held out for the purpose). That was 8. With 8 epochs, motion stayed at chance.

<figure class="sfml-fig">
<img src="/blog/sport-from-motion-laya-curves-en.png" alt="Training cross-entropy per epoch: the arbitrary-tag control falls to zero by epoch 11; one motion run starts falling at epoch 10 and ends at 0.48; another starts only at epoch 22; a third stays at the chance value, 1.39, for all 32 epochs." aria-label="Training cross-entropy per epoch: the arbitrary-tag control falls to zero by epoch 11; one motion run starts falling at epoch 10 and ends at 0.48; another starts only at epoch 22; a third stays at the chance value, 1.39, for all 32 epochs." />
<figcaption>The control (amber) is learned within the first 11 epochs. The real task takes longer to start, when it starts at all: the loss on the dots sits at the chance value for 10 epochs, sometimes 22, and sometimes never leaves it. The official recipe stops at 4.</figcaption>
</figure>

The training loss shows why. On the dots it did not just fail to generalise: it stayed at the value of guessing among four options even on the clips it was trained on. The clue the control measured is easy to find; the movement is not, and it takes longer to start.

## With enough training, it reads the order

So I let it train for up to 32 epochs and, for each split, kept the epoch that did best on that held-out slice of training, never on the test clips. That is ordinary early stopping, written into the pre-registration before running it.

<figure class="sfml-fig">
<img src="/blog/sport-from-motion-laya-configs-en.png" alt="Accuracy on the 400 clips: with 4 epochs, 0.23; with 8 epochs, 0.28 in order, 0.22 shuffled and 0.25 with a single snapshot; with up to 32 epochs and early stopping, 0.36 in order against 0.27 shuffled and 0.27 with a single snapshot. MiniRocket is at 0.83." aria-label="Accuracy on the 400 clips: with 4 epochs, 0.23; with 8 epochs, 0.28 in order, 0.22 shuffled and 0.25 with a single snapshot; with up to 32 epochs and early stopping, 0.36 in order against 0.27 shuffled and 0.27 with a single snapshot. MiniRocket is at 0.83." />
<figcaption>Only the longest training separates the conditions: with the snapshots in order Laya reaches 0.36; shuffled or reduced to one snapshot, it stays near chance. Three seeds per bar, except the official recipe.</figcaption>
</figure>

With three seeds, the four pre-registered contrasts:

| Contrast | Difference | 95% interval | Corrected p |
|---|---|---|---|
| Fine-tuned vs untrained, snapshots in order | +0.12 | [0.04, 0.20] | 0.005 |
| In order vs shuffled | +0.08 | [0.03, 0.14] | 0.007 |
| In order vs a single snapshot | +0.08 | [0.02, 0.14] | 0.007 |
| Laya vs MiniRocket | −0.48 | [−0.54, −0.42] | 0.0008 |

The second row is the one I was after. Shuffling the snapshots costs Laya 8 points, of the same order as the 10 it cost Opus 5.5, the only frontier model that showed it read the order. A 322M model trained on about 1,100 clips extracts something from the coordinates written as text that depends on time, not only on where the players are.

## How it compares

<figure class="sfml-fig">
<img src="/blog/sport-from-motion-laya-compare-en.png" alt="Left: accuracy with the snapshots in order on the same 400 clips. MiniRocket 0.83 and DeepSets 0.80; Claude Opus 5.5 0.52 with text and 0.47 with images; the other frontier models between 0.28 and 0.42; fine-tuned Laya 0.36; Jev 0.25; untrained Laya 0.24. Right: accuracy lost when the snapshots are shuffled. MiniRocket 0.12, Opus 0.10 and fine-tuned Laya 0.08 lose clearly; the other frontier models and Jev stay around zero." aria-label="Left: accuracy with the snapshots in order on the same 400 clips. MiniRocket 0.83 and DeepSets 0.80; Claude Opus 5.5 0.52 with text and 0.47 with images; the other frontier models between 0.28 and 0.42; fine-tuned Laya 0.36; Jev 0.25; untrained Laya 0.24. Right: accuracy lost when the snapshots are shuffled. MiniRocket 0.12, Opus 0.10 and fine-tuned Laya 0.08 lose clearly; the other frontier models and Jev stay around zero." />
<figcaption>Left: in accuracy, fine-tuned Laya sits among the frontier models, below Opus 5.5 and far from the specialists. Right: in what it does with the order, it sits with MiniRocket and Opus, the only ones that lose accuracy when the snapshots are shuffled. Lines are 95% intervals; circles read the coordinates as text, triangles as an image.</figcaption>
</figure>

Same 400 clips, snapshots in order, every model in the previous article next to Laya:

- **Against the specialists**, Laya is 48 points below MiniRocket (0.83) and 45 below DeepSets (0.80), which work on the coordinates directly.
- **Against the frontier models reading the same text**, it is level with GPT-5.6 Sol (0.41), GPT-5.6 Terra (0.36), Claude Sonnet 5 (0.35) and Gemini 3.1 Pro (0.42): none of the differences is significant. Claude Opus 5.5 reads the text better (0.52, 16 points above Laya).
- **Against Jev**, the other decision model, which received the same text without training, it is 11 points higher (0.25 against 0.36), a difference that does not reach significance with these 400 clips.

The panel on the right is where it changes company. In accuracy, Laya is one more of the frontier models. In what it does with the order, it sits with MiniRocket and Opus, the only three that lose accuracy when the snapshots are shuffled; the other four frontier models and Jev stay around zero.

By sport, Laya recognises American football and basketball about half the time, handball a third of the time and soccer almost never, the same sports the frontier models struggled with.

## Same data, same recipe, different seed

There is a part of the result that the averages hide.

<figure class="sfml-fig">
<img src="/blog/sport-from-motion-laya-seeds-en.png" alt="Accuracy with the snapshots in order for each seed and fold, with the epoch chosen: seeds 0 and 1 reach between 0.38 and 0.53 in four of their five folds; seed 2 stays between 0.20 and 0.25 in four folds and reaches 0.47 only in the last, at epoch 32." aria-label="Accuracy with the snapshots in order for each seed and fold, with the epoch chosen: seeds 0 and 1 reach between 0.38 and 0.53 in four of their five folds; seed 2 stays between 0.20 and 0.25 in four folds and reaches 0.47 only in the last, at epoch 32." />
<figcaption>Each cell is one fine-tuning run with the snapshots in order. Teal: it learned. Rose: it stayed at chance. Seed 2 learns in only one of five splits, and late.</figcaption>
</figure>

The fifteen runs with the snapshots in order share the data split, the recipe and the number of epochs; only the random seed changes. In 9 of them the training loss clearly drops below the chance value at some point; in the other 6 it never leaves it in 32 epochs. With seeds 0 and 1 alone, Laya reached 0.40 and the order effect was +0.12. Seed 2 brings the average down to the numbers above.

The contrasts hold with the three seeds, and the sign is the same in each one. But if I had trained a single model, the conclusion would have depended on which seed I happened to use: anything from "Laya learns to read movement" to "Laya does not learn this".

## What I take away

A small open model can learn to read the order of the snapshots from coordinates written as text. It does so about as much as the only frontier model that did it without any training, and it stays far from a specialist that works on the numbers directly.

The two things that nearly hid that result seem more general to me than the result itself:

- **A model card's recipe is tuned for its own data size.** With five times fewer examples, the official notebook gives a model at chance. A cheap positive control (a trivial clue the model can only learn by training) tells apart "this model does not learn this" from "it was not trained enough", which otherwise look the same.
- **One fine-tuning run is a sample, not a measurement.** Here the same configuration learns or does not depending on the seed. Three seeds were enough to see it; one would have hidden it in either direction.

---

*Code, pre-registration and results at [github.com/JaviMaligno/sport-from-motion](https://github.com/JaviMaligno/sport-from-motion). The [results of this arm](https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/results-laya.md) include the configurations that did not work and every deviation from the [pre-registration](https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/preregistration-laya.md), written before running it. The tracking data is not redistributed; each source has its own licence.*
