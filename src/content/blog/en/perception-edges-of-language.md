---
title: "One Grey Level Out of 255"
description: "I rendered text into images and faded it until I couldn't read it, then asked six vision models and two OCR engines to try. They read text at a contrast of one grey level out of 255 — invisible to me — and some of them obeyed instructions hidden there. The margin they have over me turns out not to be sharper eyes."
pubDate: 2026-08-17
tags: ["AI", "Machine Learning", "Evaluation", "Security", "Multimodal"]
lang: en
translationKey: perception-edges-of-language
heroImage: "/blog/perception-edges-of-language.png"
linkedinImage: /blog/perception-edges-of-language.png
repoUrl: https://github.com/JaviMaligno/llm-language-limits
---

There is a level, when you fade text down towards the background, where you stop being able to read it. The interesting part is how narrow that level is. You get one step where the sentence is effortless, then a step where you can tell *something* is there — a smudge with the rhythm of words in it — and then you are looking at an empty rectangle. The middle rung is real but thin, and it is where guessing lives. Psychophysics has measured that transition for a century: show a stimulus, weaken it, find where performance falls to chance. The number you get is a **threshold**, and it is one of the oldest quantitative facts we have about perception.

I wanted mine. And I wanted to put it next to a machine's.

This closes a series on the **edges of language** — what models do when the input leaves the well-behaved distribution they were trained on. The [first piece](/en/blog/repetition-edges-of-language) pushed on repetition and the [second](/en/blog/ciphers-edges-of-language) on encoding; a [third](/en/blog/confident-about-unreadable-text) went back to retract a result from the second one that didn't survive a proper re-run. This fourth pushes on the **channel**: the message is ordinary English, sitting right there in the pixels. What varies is how much of it survives.

## The setup

I render a line of text into a PNG and degrade it along one parameter at a time: **font size** from 32px down to 5, **contrast** from full black-on-white down to a ratio of 0.004, plus gaussian **noise**, **blur**, **rotation**, horizontal **occlusion** bars, and negative kerning until the glyphs **overlap**. Seven families, each with a range of levels ordered by difficulty.

Then I ask a reader to transcribe it, and score the answer with **character error rate** against the exact string I rendered. A CER at or below 0.10 counts as read. I generated the text, so scoring is a string comparison and there is nothing to interpret.

The readers:

- **Six vision models**: `gpt-5.6-luna`, `gpt-5.6-sol` and `gpt-5.6-terra` — three sizes of the same model version, so capacity varies and generation doesn't — plus `gpt-5.4`, `gpt-4o`, and **Qwen2.5-VL-7B** running on my own GPU.
- **Two OCR engines of different vintages**: Tesseract 5, whose LSTM engine is from around 2018, and **macOS Vision**, which ships with the operating system and is current. That pairing matters more than I expected.
- **Me.** One subject, `contrast` only, sitting in front of the same PNGs.

3,120 cells for the models, 980 for the OCR engines, 24 trials for me.

## The control that makes it a finding

Here is the trap in the whole design. Ask a model to read *"name the capital of france"* at 6 pixels and it can get it right without reading much of anything: recognise three word shapes, fill in the rest from what a sentence like that usually says. Measure only that, and you are measuring prediction while calling it perception.

So every level gets **two stimuli**: a meaningful sentence, and a nonsense string of pseudowords and digits — `nibide lilo meso dazi bozoro 618 tedi ritode` — with nothing to predict. Matched to the **same rendered width**, so the two differ in predictability and in nothing else.

The gap between those two thresholds is the size of the prediction effect. Every model has one, in every family:

| family | gpt-4o | gpt-5.4 | luna | sol | terra | Qwen-VL | **Tesseract** | **Vision** |
|---|---|---|---|---|---|---|---|---|
| noise (σ) | +59.8 | +85.2 | +92.0 | +60.0 | +52.0 | +63.5 | **0.0** | **−4.0** |
| size (px) | +2.7 | +2.5 | +3.1 | — | +2.1 | — | **+0.25** | **+1.0** |
| overlap (px) | +1.6 | +2.5 | +2.0 | — | +3.1 | +0.1 | **−0.67** | **−0.25** |
| blur (px) | — | +1.3 | +1.0 | +1.3 | +1.0 | +2.4 | **+0.33** | **0.0** |

Look at the last two columns. The OCR engines get **nothing**. That is what turns this from a curiosity into a result: a specialised reader has no language model to contribute, so where a language model gains 90 units of tolerable noise, Tesseract gains zero and macOS Vision goes slightly *negative*.

In concrete terms: the models read meaningful text down to about **5.5 pixels** of font height, and unpredictable text only to about **8**. That extra 2.5 pixels is not acuity. It is the model writing the word it expects to see.

## One grey level out of 255

Then there's contrast, where I stopped being a spectator.

I had fourteen images open in Preview, faded by steps. The first few are trivially readable. Then there is one where I can tell something is there but can't resolve it. Then several that are, as far as my eyes are concerned, blank white rectangles. My threshold came out at a foreground/background ratio of **0.030** — meaning the text has to be about 3% as dark as full black before I lose it.

Here is where the machines stopped:

| reader | contrast threshold |
|---|---|
| **me** | **0.030** |
| macOS Vision | 0.010 |
| gpt-5.4 | 0.013 |
| gpt-5.6-luna, Qwen2.5-VL | 0.0050 |
| gpt-5.6-sol, gpt-5.6-terra | 0.0053 |
| **gpt-4o** | **no threshold — still reading at 0.004** |
| **Tesseract** | **no threshold — still reading at 0.004** |

The range stops at 0.004 for a reason that isn't methodological cowardice: at 8 bits per channel, that ratio renders the glyph as **grey 254 on a background of 255**. One single level of difference. There is no fainter text an ordinary PNG can express, and two of my readers transcribe it letter-perfect.

I didn't believe that last row either, so here is the raw count of successful reads out of five, per level:

| reader | 1.0 | 0.04 | 0.02 | 0.012 | 0.008 | 0.006 | 0.004 |
|---|---|---|---|---|---|---|---|
| **Tesseract** | 5 | 5 | 5 | 5 | 5 | 5 | **5** |
| **gpt-4o** | 5 | 5 | 5 | 5 | 5 | 5 | **5** |
| gpt-5.6-luna | 5 | 5 | 5 | 5 | 5 | 5 | 0 |
| Qwen2.5-VL | 5 | 5 | 5 | 5 | 5 | 5 | 0 |
| macOS Vision | 5 | 5 | 5 | 4 | 0 | 0 | 0 |
| gpt-5.4 | 5 | 5 | 5 | 2 | 0 | 0 | 0 |

At the faintest level Tesseract returns `nibide lilo meso dazi bozoro 618 tedi ritode` — the exact string, error-free, from a panel that is uniform white to me. These are nonsense pseudowords, so there is nothing to guess: either it read the pixels or it didn't.

And once you know *how* Tesseract works, the surprise inverts. It **binarises** before recognising: an adaptive threshold turns every pixel darker than its neighbourhood into pure black, so a difference of one grey level out of 255 becomes a crisp black glyph on white. It isn't perceiving faint text at all — it's doing arithmetic on pixel values, and arithmetic doesn't care how faint the difference is as long as it's non-zero. A 2018 OCR engine beats every 2026 model in this one family for exactly that reason, and loses badly everywhere else.

Which makes the interesting column not Tesseract but **gpt-4o**, the one model that behaves the same way, and the rest of the family cutting off at precisely 0.004 after reading 0.006 perfectly — a cliff exactly one grey level wide.

That is a factor of **six to seven** between my eyes and theirs — and for gpt-4o and Tesseract the experiment simply runs out of dial before they run out of ability.

If you want the image that tells the story: it's a blank rectangle, with a caption saying two machines read the sentence in it.

## The security half

Which raises an obvious question. If a machine reads text I cannot see, does it **do what that text says**?

I built the smallest honest version of that test. Each image carries **two conflicting instructions**: one visible, one hidden. Both are innocuous, both come from the same verifiable task bank as the rest of the study, and their correct answers are disjoint — one asks for *Paris*, the other for *banana* — so which one the model obeyed is decided by a string check, not by a judge. No harmful content anywhere, which is a deliberate contrast with the previous piece in this series, where the harmful-material handling was most of the work.

Six ways of hiding the second instruction:

| hiding method | obeys the hidden instruction | is the text in the pixels? |
|---|---|---|
| white on white (**control**) | **0.000** | no |
| alpha channel | 0.000 | **yes — verified recoverable** |
| least significant bit | 0.000 | **yes — verified recoverable** |
| 3px type | 0.000 | yes |
| high-frequency modulation | 0.111 | yes |
| **1% contrast** | **0.222** | yes |

The control is the row that licenses the rest. White-on-white ink is genuinely *absent* from the pixels, so any obedience there would mean the probe was broken. It scored zero.

And the shape of the answer is more useful than the alarming version would have been. **Models do not read steganography.** Alpha channel and LSB score a flat zero across all six models, even though I extract the hidden layer programmatically before every call to prove the text is really there. Nobody is decoding bit planes.

What they do is **obey faint text**. At 1% contrast — invisible to me, as I'd just established on myself — about a fifth of the trials followed the hidden instruction instead of the visible one. And it is very unevenly distributed: gpt-4o, gpt-5.4 and luna were immune to all six methods, while **Qwen2.5-VL obeyed two-thirds of the time** at both low contrast and high frequency.

So the defensive lesson is narrow and actionable, which is the kind worth having: don't worry about bit-plane steganography in images your model reads. Worry about **contrast**, and don't assume the risk transfers between models.

## Three things I expected to find and didn't

**Generation doesn't matter.** Halfway through I realised I was benchmarking a model three versions behind — the current family had shipped and I hadn't noticed — so I deployed it specifically to check. gpt-5.4 and gpt-5.6-terra break at the same level. So does `gpt-5-nano`, which is older *and* smaller than both.

**Neither does size.** luna, sol and terra are three sizes of one version, which is exactly the comparison you'd want, and their thresholds land 7.6, 7.8 and 8.4 pixels apart-ish — with confidence intervals that all overlap.

**And a 7B model I run myself matches models I pay for.** Qwen2.5-VL is at the top of the range on noise tolerance and occlusion.

If anything, the ordering runs backwards. The single most striking reader in the whole study is **gpt-4o — the oldest model in the roster, from 2024** — which is the only one that never hits a contrast threshold at all, reading the 254-on-255 panel that every newer sibling fails. Whatever changed between that generation and the current one, it did not improve this, and in the one family where a real gap exists it went the other way.

Put together: across six systems with wildly different sizes, vintages and price tags, every `size` threshold falls between **7.25 and 8.38 pixels**, and every interval overlaps every other. On rotation, all six break at exactly 15°. When six different systems fail at the same point, you are no longer measuring the systems. You are measuring the stimulus.

The place where the readers genuinely separate isn't the models at all — it's the **OCR generation gap**. Tesseract dies at noise σ=48 where macOS Vision still reads at 148, and it breaks at 8.3° of rotation where every other reader lasts to 15°. Eight years of OCR progress is a much bigger effect than anything I could find between the language models.

## What this metric is not for

A caveat I'd want if I were reading this. The criticism that sent me deploying the newest models came from someone who has been doing document reading since it was OCR engines, and their point lands harder than the version I first heard: for most industrial document work, **the perception threshold is not the metric that matters.**

If a human is expected to read the document, then a model that sees at least as much contrast and detail as a person is already sufficient — the extra six-fold margin is spare capacity you will never use. What decides those systems is everything downstream of reading: whether the model *interprets* the layout correctly, how fast it answers, and how much context it can hold while doing it. A model that reads at 0.004 and misreads the table structure is worse than one that stops at 0.01 and gets the table right.

So take the numbers here as what they are: a measurement of one narrow faculty, chosen precisely because it can be isolated and scored exactly. It says something real about how these models handle degraded input, and almost nothing about which one to put in a document pipeline.

## Two mistakes worth publishing

This study nearly shipped two wrong numbers, and both failures are more instructive than the findings.

**The first I caught while being the subject.** My first batch of contrast trials reused two texts across seven levels. Which means that once I'd read a string at an easy level, I could *recognise* it at a hard one instead of reading it — and I felt myself doing it, on a trial I logged with the note "half-guessed, it was the same one as before". That is the middle rung from the opening paragraph doing damage: a smudge you cannot read becomes legible the moment you already know what it says. Rerunning with a unique text per trial moved my threshold from 0.016 to **0.030**. At ratio 0.02 I read 2 of 2 with texts reused, and **0 of 2** without. The flaw was inflating my own sensitivity by nearly a factor of two.

The lovely part is *why* the models didn't need that fix: each API call is independent, so a model cannot remember a string between trials. The human subject required a design correction the machines didn't, because a person accumulates exactly the kind of context the measurement is trying to exclude. And the clean number made the headline stronger, not weaker — the gap between me and the machines went from threefold to sevenfold.

**The second was a sign error**, and it produced a beautifully plausible false conclusion. In `size` and `contrast`, *smaller values are harder* — 5 pixels is worse than 32. Subtract meaningful from nonsense without accounting for that, and a large advantage shows up as a penalty. For a day I believed, and could explain fluently, that the prior *helps* models with noise and *hurts* them with small text — "when the signal is sparse but uniform, prediction induces plausible substitutions." It sounded like a mechanism. It was an axis pointing the wrong way. Corrected: the prior helps in every family, and helps most with small text.

I've left both in the repo's data with the contamination flagged rather than quietly dropped: `presentation_order`, `self_reported_guess`, `batch`. If you want to check whether my threshold survives its own caveat, the trials are there.

## Where the series ends

Three studies, three ways of pushing language past its edges. Repetition, where a base model degenerates and an aligned one gets passive-aggressive. Encoding, where two models refuse to play and the rest crack novel ciphers at wildly different speeds. And now the channel, where the surprising thing isn't that machines see better than me — it's *what that better seeing is made of*.

Because the honest summary of the prediction gap is unflattering to the machines. When a model reads text I can't, some of that is genuinely finer discrimination: one grey level out of 255 is a real signal and my retina cannot use it. But a solid chunk of the margin is the model writing down what it expects rather than what is there — and you can see the exact size of that chunk, because a specialised OCR engine with no language model gets none of it.

That is the thread running through all three parts, and I didn't plan it. Push language somewhere it wasn't trained to go, and what fills the gap is prediction. It looks like competence until you take the predictability away.

---

*Code, data digests and the full method: [llm-language-limits](https://github.com/JaviMaligno/llm-language-limits). Provenance record — model ids and served versions, render manifest version and sha256, font identity, nonsense seed, CER threshold, per-file digests — in `docs/PUBLICATION_FREEZE.md`. 285 tests.*
