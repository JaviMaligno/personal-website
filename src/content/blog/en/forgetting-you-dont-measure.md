---
title: "The Forgetting You Don't Measure"
description: "When you continually pre-train an LLM into a 'world model', it quietly forgets general knowledge — and a little data mixing buys most of it back. But how much it forgets depends heavily on how you specialize it, and full fine-tuning pays three costs a single benchmark undersells."
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

## The more interesting part: how much you forget depends on how you specialize

Data mixing is one lever. The *method* is a bigger one. I ran the same setup a second way: instead of full fine-tuning, **LoRA** — the cheap, default parameter-efficient method that trains a small set of adapter weights and leaves the base model frozen. Same mean forgetting, LoRA versus full fine-tuning, at each replay fraction:

| Replay % | Full fine-tuning | LoRA |
|---|---|---|
| 0%  | −0.078 | **+0.002** |
| 10% | −0.021 | +0.005 |
| 25% | −0.012 | +0.009 |
| 50% | −0.015 | +0.009 |

LoRA barely forgets — not even at zero replay — while learning the terminal task just as well (same ~0.90 accuracy). This isn't mysterious: LoRA freezes the base weights and only trains a thin adapter, so the general knowledge sits untouched by construction. It's [known to forget less](https://arxiv.org/html/2405.09673v2) precisely *because* it moves so little. Full fine-tuning, by contrast, lets the optimizer overwrite any weight — including the ones holding general ability.

So I pushed on what full fine-tuning actually costs, beyond the reasoning benchmarks. Two more probes, at zero replay, full-FT versus LoRA:

| Probe | Full fine-tuning | LoRA |
|---|---|---|
| **IFEval** (instruction-following) | 0.194 → 0.123 (**−0.071**) | 0.194 → 0.227 (**+0.033**) |
| **Held-out sim on OOD commands** (sed/awk/grep/pipes) | **0.00** | **0.15** |

Both cost full-FT, both spare LoRA:

- **Instruction-following.** My reasoning/commonsense battery couldn't see this, so I added IFEval — programmatically-checkable instructions (format, length, required words). Full fine-tuning drops it 37% relative; LoRA actually nudges it up. This is the concrete thing that "general benchmarks barely moved" was hiding on the full-FT side: an instruct model quietly losing the instruction-following it was tuned for.
- **Depth of the learned task.** I expected the opposite here — that LoRA, touching so little, would learn a *shallower* world model. It's the reverse. Both score ~0.90 on held-out commands drawn from the training distribution, but on genuinely out-of-distribution commands (ones the training set never contains) full fine-tuning collapses to zero while LoRA still gets 15%. Full-FT overfits the exact command shapes it saw; LoRA, riding on the frozen base, generalizes a little.

So the honest read is simpler than a "gotcha": **full fine-tuning pays three costs — general reasoning, instruction-following, and out-of-distribution robustness — that a single benchmark undersells, and LoRA mostly doesn't pay them, because it perturbs the model far less.** That's not LoRA hiding anything; it's LoRA doing less damage. The mild version of the lesson still holds, though, and it's the through-line of [Results-Oriented Programming](/en/blog/results-oriented-programming) and [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know): one number ("my general accuracy held") can quietly stand in for several you didn't check.

The trade-off is the usual one: LoRA learns the *new* task a bit less aggressively than full-FT. Here the terminal task was easy enough that both hit the same ~0.90, so LoRA looks strictly better — but on a harder target where you need every point of task performance, full fine-tuning's willingness to overwrite is exactly what you're paying for. There's no free lunch, just a dial between "learn more, forget more" and "learn less, forget less."

## Two nuances, honestly reported

**Base versus instruct.** I expected the instruction-tuned model to forget more — more to lose. On reasoning it didn't: base and instruct 0.5B forgot almost identically (−0.14 vs −0.17 mean at zero replay). Where the instruct model *does* bleed is instruction-following itself (the IFEval drop above) — a base model has little of that to lose in the first place. So "more to lose" is true, but only on the axis the instruct model was tuned for.

**Size.** The larger model forgot a bit less: full fine-tuning 1.5B lost −0.060 on average versus 0.5B's −0.078, leaning toward "smaller models forget more." But the effect is soft and not uniform — clear on ARC-Easy, reversed on ARC-Challenge — and comparable to the noise between seeds. (Getting 1.5B full fine-tuning to fit on a 16 GB T4 at all took an offloaded 8-bit optimizer and a batch size of one; it overshot memory by 200 MB on the first try. A craft note, not a finding.)

## What it was actually worth

None of these results would survive as a preprint — I checked, and each is already in the literature: replay mitigates forgetting, LoRA forgets less, larger models forget a little less. This was a reproduction, in a new-ish setting, at a scale you can run overnight for pocket change.

The value, for me, was seeing how much the answer to "did it keep its general ability?" depends on *what you measured and how you trained*. Full fine-tuning on a narrow task looked fine on reasoning, until IFEval showed the instruction-following it had shed and an OOD probe showed how narrowly it had actually learned. Same model, same data — the losses were real, they just weren't in the first place you'd look. The fix isn't exotic: when you specialize a model, check more than one capability, and remember that the training method sets how much there was to lose in the first place.

---

*Code and full results: [github.com/JaviMaligno/language-world-model-forgetting](https://github.com/JaviMaligno/language-world-model-forgetting). This is the third in a loose series on delegating to models and staying able to tell when they're wrong — see also [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know) and [Results-Oriented Programming](/en/blog/results-oriented-programming).*
