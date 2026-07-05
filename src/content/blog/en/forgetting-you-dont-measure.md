---
title: "The Forgetting You Don't Measure"
description: "When you continually pre-train an LLM into a 'world model', it quietly forgets general knowledge — and a little data mixing buys most of it back. But how much it forgets depends heavily on how you specialize it, and full fine-tuning pays three costs a single benchmark undersells."
pubDate: 2026-07-06
tags: ["AI", "Machine Learning", "Continual Learning", "LoRA", "Engineering"]
lang: en
translationKey: forgetting-you-dont-measure
heroImage: "/blog/forgetting-you-dont-measure.png"
linkedinImage: /blog/forgetting-mixing-curve.png
repoUrl: https://github.com/JaviMaligno/language-world-model-forgetting
---

There's a recent paper from the Qwen team — [Qwen-AgentWorld](https://arxiv.org/abs/2606.24597) — that turns an LLM into a *world model*: instead of answering as an assistant, the model learns to predict what an environment returns after an action. Run a shell command, and it predicts the exact terminal output, exit code and all. They build this by taking a finished, general-purpose model and training it further on millions of interaction trajectories — a step called **continual pre-training** (you keep pre-training an already-trained model on new data to teach it something new).

The catch with that kind of training is well known: pour enough narrow data on a model and it starts to *forget* things it used to know — the classic "catastrophic forgetting." The standard defense is **replay** (also called data mixing): while you train on the new narrow data, you keep mixing in a fraction of general text, so the model rehearses its old knowledge instead of letting it wash away. The Qwen paper does exactly this — during continual pre-training they blend in general-knowledge corpora (law, medicine, current events). They frame it as a capability move (you can't simulate a hospital without medical knowledge), but it doubles as anti-forgetting insurance. It's a sensible choice. What they never do is *measure* it: there's no before/after on general benchmarks, no number on how much gets forgotten or how much the replay saves.

So I ran the experiment at toy scale. Not to one-up a 397B model with a 0.5B one — that would be silly — but because the question is about a *training dynamic*, and dynamics show up at small scale too. Honestly, I mostly wanted to see the thing this blog keeps circling back to: not whether a system degrades, but whether you can tell when it does.

## The setup

I took `Qwen2.5-0.5B-Instruct`, generated a narrow "terminal simulator" dataset (real shell commands and their real outputs), and continually pre-trained the model to predict those outputs — teaching it to be a tiny world model. Before and after training I measured general ability on standard benchmarks (ARC, HellaSwag, WinoGrande), and I measured whether it actually learned the new task (held-out next-output accuracy). Then I swept the one knob that matters: what fraction of each training batch is *replay* — general text (Wikipedia) — instead of terminal data. Zero, 10%, 25%, 50%, and a 100% control. Three seeds each. The whole thing ran on a single spot T4 on Azure for about the price of a couple of coffees.

## Result one: yes, it forgets, and a little mixing buys it back

With no replay, the model learns the terminal task well (exact-match on held-out outputs jumps from ~0.36 to ~0.90) — and it forgets. General accuracy drops across the board: on average −0.078, and −0.15 on the worst-hit benchmark (ARC-Easy). Then I dialed replay up. The amber line below is the story:

![Forgetting vs. replay: full fine-tuning recovers most of it by 10% mixing; LoRA barely forgets at all](/blog/forgetting-mixing-curve.png)

Ten percent replay recovers about 73% of the average forgetting — and roughly 82% of the worst case — at **no cost to the new task** (task accuracy stays at ~0.90). Past 25% you get diminishing returns. And a 100%-replay control (not plotted) confirms the bracket from the other side: train only on general text and the model never learns to simulate anything (task accuracy collapses back to baseline), while general ability stays flat.

I want to be upfront: this is not a new discovery. That a small replay fraction suppresses catastrophic forgetting is [well-established](https://arxiv.org/html/2401.03129v1) — the continual-learning literature has been saying "mix in 1–5% of the old distribution" for years. What I did was put a number on the specific claim the world-model paper makes by design but leaves unquantified. That was the easy part. The blue line — LoRA — is where it got interesting.

## The more interesting part: how much you forget depends on how you specialize

Replay is one lever. The training *method* is a bigger one. Everything above used **full fine-tuning** — every weight in the model is free to change. So I re-ran the whole sweep with **LoRA** instead: the cheap, popular parameter-efficient method that freezes the original model and trains only a small set of add-on "adapter" weights. That's the blue line in the chart above — flat, near zero, at *every* replay fraction, including zero.

LoRA barely forgets, even with no replay at all, while learning the terminal task just as well (same ~0.90 accuracy). This isn't mysterious: because the original weights are frozen, the general knowledge they hold sits untouched by construction. LoRA is [known to forget less](https://arxiv.org/html/2405.09673v2) precisely *because* it changes so little. Full fine-tuning, by contrast, lets the optimizer overwrite any weight — including the ones holding general ability.

So I pushed on what full fine-tuning actually costs, beyond the reasoning benchmarks. Two more probes, at zero replay:

| Probe (at 0% replay) | Full fine-tuning | LoRA |
|---|---|---|
| Instruction-following (IFEval) | −0.071 | **+0.033** |
| World model on unseen commands | **0.00** | **0.15** |

- **Instruction-following.** My reasoning benchmarks couldn't see this, so I added IFEval — instructions a script can grade automatically (obey a format, a length, include a given word). Full fine-tuning drops it 37% relative (0.194 → 0.123); LoRA actually nudges it up. This is the concrete thing that "general benchmarks barely moved" was hiding on the full-FT side: an instruction-tuned model quietly losing the instruction-following it was tuned for.
- **Depth of the learned task.** Here I expected the opposite — that LoRA, changing so little, would learn a *shallower* world model. It was the reverse. Both score ~0.90 predicting outputs for the kinds of commands they trained on, but on genuinely unfamiliar commands (things like `sed`, `awk`, `grep` and pipes, which the training set never contained) full fine-tuning collapses to zero while LoRA still gets 0.15. Full fine-tuning memorized the exact command shapes it saw; LoRA, riding on the frozen base, kept some ability to generalize.

So the honest read is simpler than a "gotcha": **full fine-tuning pays three costs — general reasoning, instruction-following, and out-of-distribution robustness — that a single benchmark undersells, and LoRA mostly doesn't pay them, because it perturbs the model far less.** That's not LoRA hiding anything; it's LoRA doing less damage. The mild version of the lesson still holds, though, and it's the through-line of [Results-Oriented Programming](/en/blog/results-oriented-programming) and [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know): one number ("my general accuracy held") can quietly stand in for several you didn't check.

The trade-off is the usual one: LoRA learns the *new* task a bit less aggressively than full-FT. Here the terminal task was easy enough that both hit the same ~0.90, so LoRA looks strictly better — but on a harder target where you need every point of task performance, full fine-tuning's willingness to overwrite is exactly what you're paying for. There's no free lunch, just a dial between "learn more, forget more" and "learn less, forget less."

## Two nuances, honestly reported

**Base versus instruct.** I expected the instruction-tuned model to forget more — more to lose. On reasoning it didn't: base and instruct 0.5B forgot almost identically (−0.14 vs −0.17 mean at zero replay). Where the instruct model *does* bleed is instruction-following itself (the IFEval drop above) — a base model has little of that to lose in the first place. So "more to lose" is true, but only on the axis the instruct model was tuned for.

**Size.** The larger model forgot a bit less: full fine-tuning 1.5B lost −0.060 on average versus 0.5B's −0.078, leaning toward "smaller models forget more." But the effect is soft and not uniform — clear on ARC-Easy, reversed on ARC-Challenge — and comparable to the noise between seeds. (Getting 1.5B full fine-tuning to fit on a 16 GB T4 at all took an offloaded 8-bit optimizer and a batch size of one; it overshot memory by 200 MB on the first try. A craft note, not a finding.)

## The takeaway

None of this is new physics — replay mitigating forgetting, LoRA forgetting less, and the rest are all things the literature already knows. This was a small reproduction you can run overnight for the price of a few coffees. What it made concrete for me is how much the answer to "did it keep its general ability?" depends on *what you measured and how you trained*.

Full fine-tuning on a narrow task looked fine on reasoning, until IFEval showed the instruction-following it had shed and an unfamiliar-command probe showed how narrowly it had actually learned. Same model, same data — the losses were real, they just weren't in the first place you'd look. The fix isn't exotic: when you specialize a model, check more than one capability, pick the training method deliberately (LoRA and full fine-tuning are genuinely different trades, not interchangeable defaults), and don't read one flat benchmark as proof that nothing was lost.

---

*Code and full results: [github.com/JaviMaligno/language-world-model-forgetting](https://github.com/JaviMaligno/language-world-model-forgetting). This is the third in a loose series on delegating to models and staying able to tell when they're wrong — see also [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know) and [Results-Oriented Programming](/en/blog/results-oriented-programming).*
