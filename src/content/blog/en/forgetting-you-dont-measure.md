---
title: "The Forgetting You Don't Measure"
description: "When you continually pre-train an LLM into a 'world model', it quietly forgets general knowledge — and a little data mixing buys most of it back. But the finding that stuck with me is that the cheap, default method hides the forgetting entirely. The problem was never the forgetting. It was whether you could see it."
pubDate: 2026-07-01
tags: ["AI", "Machine Learning", "Continual Learning", "LoRA", "Engineering"]
lang: en
translationKey: forgetting-you-dont-measure
heroImage: "/blog/forgetting-you-dont-measure.png"
---

There's a recent paper from the Qwen team — [Qwen-AgentWorld](https://arxiv.org/abs/2606.24597) — that turns an LLM into a *world model*: instead of answering as an assistant, the model learns to predict what an environment returns after an action. Run a shell command, and it predicts the exact terminal output, exit code and all. They build this with continual pre-training (CPT) on millions of interaction trajectories across seven domains.

Buried in the method is a design choice: during that CPT they also mix in general-knowledge corpora — law, medicine, current events. Their stated reason is capability (you can't simulate a hospital without medical knowledge), but it doubles as an anti-forgetting measure: keep feeding the model general data so specializing on narrow trajectories doesn't wash the general distribution away. It's a sensible choice. What they never do is *measure* it. There's no before/after on general benchmarks, no number on how much gets forgotten or how much the mixing saves.

So I ran the experiment at toy scale. Not to one-up a 397B model with a 0.5B one — that would be silly — but because the question is about a *training dynamic*, and dynamics show up at small scale too. Honestly, I mostly wanted to see the thing this blog keeps circling back to: not whether a system degrades, but whether you can tell when it does.

## The setup

I took `Qwen2.5-0.5B-Instruct`, generated a narrow "terminal simulator" dataset (real shell commands and their real outputs), and continually pre-trained the model to predict those outputs — teaching it to be a tiny world model. Before and after training I measured general ability on standard benchmarks (ARC, HellaSwag, WinoGrande), and I measured whether it actually learned the new task (held-out next-output accuracy). Then I swept the one knob that matters: what fraction of each training batch is *replay* — general text (Wikipedia) — instead of terminal data. Zero, 10%, 25%, 50%, and a 100% control. Three seeds each. The whole thing ran on a single spot T4 on Azure for about the price of a couple of coffees.

## Result one: yes, it forgets, and a little mixing buys it back

With no replay, the model learns the terminal task well (exact-match on held-out outputs jumps from ~0.36 to ~0.90) — and it forgets. General accuracy drops across the board, worst on ARC-Easy at −0.15. Then the mixing curve (mean drop across the four tasks, averaged over seeds):

| Replay % | Mean forgetting | ARC-Easy |
|---|---|---|
| 0%  | **−0.078** | −0.153 |
| 10% | −0.021 | −0.028 |
| 25% | −0.012 | −0.004 |
| 50% | −0.015 | −0.010 |
| 100% (control) | −0.013 | +0.005 |

Ten percent replay recovers about 73% of the average forgetting — and roughly 82% of the worst case — at **no cost to the new task** (task accuracy stays at ~0.90). The 100% control confirms the bracket: train only on replay and the model never learns to simulate anything (task accuracy collapses back down), while general ability stays flat.

I want to be upfront: this is not a new discovery. That a small replay fraction suppresses catastrophic forgetting in continual pre-training is [well-established](https://arxiv.org/html/2401.03129v1) — the continual-learning literature has been saying "mix in 1–5% of the old distribution" for years. What I did was *measure* the specific claim the world-model paper makes by design but leaves unquantified. The number was pleasant to see. It wasn't the interesting part.

## The interesting part: the method decides whether you see it at all

I ran the same sweep a second way: instead of full fine-tuning, I used **LoRA** — the cheap, default parameter-efficient method that trains a small set of adapter weights and leaves the base model frozen. Here's the mean forgetting, LoRA versus full fine-tuning, at each replay fraction:

| Replay % | Full fine-tuning | LoRA |
|---|---|---|
| 0%  | −0.078 | **+0.002** |
| 10% | −0.021 | +0.005 |
| 25% | −0.012 | +0.009 |
| 50% | −0.015 | +0.009 |

LoRA shows **no forgetting at all** — not even at zero replay — while learning the terminal task just as well (same ~0.90 accuracy). If you had only ever trained this way, you would look at your numbers, see general ability perfectly intact, and conclude that turning your model into a world model is free. And you'd be wrong. The forgetting is real. Your instrument just couldn't see it, because LoRA barely moves the weights that hold the general knowledge — it's [known to forget less](https://arxiv.org/html/2405.09673v2) precisely *because* it touches so little.

This is the same trap I keep writing about from different angles. In [Results-Oriented Programming](/en/blog/results-oriented-programming) it was verifying the output while trusting a signal that couldn't fail loudly. In [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know) it was delegating knowledge and losing the ability to tell when the retrieved answer is wrong. Here it's the same shape at the level of a training run: the danger isn't the forgetting, it's picking a method — for perfectly good reasons of cost and convenience — that can't reveal the forgetting even when it's happening. Full fine-tuning "looks worse" because it's the honest instrument. LoRA "looks safe" because it's a quieter one.

That's not an argument against LoRA. LoRA forgetting less is often exactly what you want. It's an argument against reading "my general benchmarks didn't move" as "nothing was lost," when the two can come apart entirely depending on how you trained.

## Two nuances, honestly reported

**Base versus instruct.** I expected the instruction-tuned model to forget more — more to lose. It didn't: base and instruct 0.5B forgot almost identically (−0.077 vs −0.078 at zero replay). The honest caveat is that my battery is reasoning and commonsense tasks; the place an instruct model would bleed is *instruction-following*, which I didn't measure. So this says less than it looks like it does.

**Size.** The larger model forgot a bit less: full fine-tuning 1.5B lost −0.060 on average versus 0.5B's −0.078, leaning toward "smaller models forget more." But the effect is soft and not uniform — clear on ARC-Easy, reversed on ARC-Challenge — and comparable to the noise between seeds. (Getting 1.5B full fine-tuning to fit on a 16 GB T4 at all took an offloaded 8-bit optimizer and a batch size of one; it overshot memory by 200 MB on the first try. A craft note, not a finding.)

## What it was actually worth

None of the four results would survive as a preprint — I checked, and every one of them is already in the literature: replay mitigates forgetting, LoRA forgets less, larger models forget a little less. This was a reproduction, in a new-ish setting, at a scale you can run overnight for pocket change.

The value, for me, was the middle result, and it isn't about world models at all. When you specialize a model and then check whether it kept its general ability, *the answer you get depends on how you looked*. Same model, same data, same task — one method reports a real loss, the other reports none. If you only own the quiet instrument, "no forgetting" is not evidence of no forgetting. It's just silence.

---

*Code and full results: [github.com/JaviMaligno/language-world-model-forgetting](https://github.com/JaviMaligno/language-world-model-forgetting). This is the third in a loose series on delegating to models and staying able to tell when they're wrong — see also [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know) and [Results-Oriented Programming](/en/blog/results-oriented-programming).*
