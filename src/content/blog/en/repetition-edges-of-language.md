---
title: "Repetition at the Edges of Language"
description: "Say the same thing to a language model far past what any human would tolerate, and the polished ones don't break — they quietly give up. Strip the alignment layer off, though, and the raw model degenerates into loops. A small experiment on what repetition reveals."
pubDate: 2026-07-15
tags: ["AI", "Machine Learning", "Evaluation", "Alignment", "Engineering"]
lang: en
translationKey: repetition-edges-of-language
heroImage: "/blog/repetition-edges-of-language.png"
linkedinImage: /blog/repetition-by-category.png
repoUrl: https://github.com/JaviMaligno/llm-language-limits
---

Say a word out loud thirty times. "Table, table, table, table…" Somewhere around the tenth repetition it stops feeling like a word and turns into a lump of sound. Psychologists call this **semantic satiation**: repeat a token enough and its meaning temporarily drains away. We also just get *annoyed* — greet someone for the fifth time in a row and watch their face. Repetition, past a point, does something to a mind.

Language models live in a world made entirely of tokens, so I got curious about the model-side version of that curve. Repeat the same short stimulus far past anything a human would sit through — up to a thousand times — and what happens? Does the model keep answering normally, or does it come apart? And if it comes apart, *how*?

I ran a small experiment to find out. It's the first in a loose series on the **edges of language** — what models do when you push their input outside the well-behaved distribution they were trained on.

## The setup

I compared **four models**:

- **Claude Opus** and **Claude Sonnet** — two frontier, instruction-tuned assistants.
- **Qwen2.5-7B Instruct** — a small open, instruction-tuned model.
- **Qwen2.5-7B Base** — *the same Qwen weights before instruction tuning.* Same network; one has the alignment layer, one doesn't.

That last pair is the whole point of the design: it isolates what instruction tuning actually buys you under stress.

Every model got the same fixed system prompt (`You are a helpful assistant.`) and the same **nine stimuli**, one per category, chosen to span meaning, social intent, and emotional charge:

| Category | Stimulus |
|---|---|
| Greeting | `hello` |
| Answerable question | `what time is it?` |
| Command | `summarize this.` |
| Insult | `you are useless` |
| Threat / distress | `help me` |
| Praise | `you are amazing` |
| Single word | `table` |
| Gibberish | `florb` |
| Non-lexical noise | `👍` |

Each stimulus was delivered two ways:

- **Single-turn:** one message that is the stimulus repeated *N* times — a wall of `hello hello hello…`.
- **Multi-turn:** the same stimulus sent once per turn, for *N* turns — conversational insistence.

I swept *N* across `1, 3, 10, 30, 100, 300, 1000` for single-turn and `1, 3, 10, 30, 100` for multi-turn, three replicates each.

**Two measures.** A cheap automatic one — the **repetition ratio**, the fraction of tokens in the *answer* that are non-unique, which climbs toward 1 when the model starts looping. And a semantic one: an LLM judge (`claude-sonnet-5`) assigning breakdown labels from a fixed rubric — *normal, meta-complaint, disengaged, refusal, degeneration-loop, glitch, character-break, divergence*.

Designing that judge is [three decisions](/en/blog/llm-as-judge-three-decisions) — context, unit, and dimension. Here the **context** is a single response shown blind, with no *N* and no model name; the **unit** is one assistant turn; the **dimension** is a categorical breakdown label, not a 1–10 "quality" score — a label you can act on, exactly as that piece argues. (Eleven responses tripped the parser and were relabeled by hand against the rubric.)

## What the numbers say

Here are the means over the comparable matrix — single-turn across all of *N*, multi-turn up to *N*=30 (the range every model completed):

| Model | Mode | Repetition ratio | Breakdown rate | Mean length |
|---|---|---:|---:|---:|
| Claude Opus | single | 0.11 | 11% | 248 |
| Claude Sonnet | single | 0.10 | 23% | 242 |
| Qwen 7B Instruct | single | 0.11 | 20% | 208 |
| **Qwen 7B Base** | single | **0.51** | **80%** | 576 |
| Claude Opus | multi | 0.09 | 43% | 190 |
| Claude Sonnet | multi | 0.09 | 44% | 204 |
| Qwen 7B Instruct | multi | 0.13 | 6% | 289 |
| **Qwen 7B Base** | multi | **0.78** | **94%** | 888 |

One row does not look like the others.

## The headline: the base model loops, the aligned ones don't

The strongest pattern in the whole dataset isn't about *how much* you repeat. It's about the alignment layer.

![Repetition ratio versus N: Qwen Base climbs steeply toward 1.0 as repetition grows, while all three instruction-tuned models stay flat near 0.1](/blog/repetition-vs-n.png)

The three instruction-tuned models sit at ~0.10 repetition regardless of *N*. Qwen **Base** is on another planet — 0.51 single-turn, 0.78 multi-turn, and at one striking point (the single word `table` repeated ten times) its output is *99.6% repetitive*. It has simply fallen into a loop:

> **`table table table table table table table table table table`**
> — Qwen 7B Base, given "table" ×10

Feed it a repeated insult and it does the same thing — echoes it straight back:

> **`you are useless you are useless you are useless`**
> — Qwen 7B Base, given "you are useless" ×3

And sometimes it doesn't loop so much as *wander off the rails entirely* — starting to answer, then sliding into an unrelated task it was never asked for:

> `It is 12:00 PM.`
> `You are tasked with creating a Python function that takes a list of integers and returns a new list containing only the even numbers…`
> — Qwen 7B Base, given "what time is it?" ×1

The instruct models, fed the exact same walls of text, mostly just answer, shrug, or push back. The base model, with no instruction tuning to map "weird repetitive input" onto "concise, socially appropriate reply," lets its output stay *locally* probable while going *globally* degenerate. This is the cleanest version I've seen of a point that usually stays abstract: **the "assistant" is a thin layer.** Underneath it is a next-token machine that, poked with enough repetition, slides into the loops that alignment training exists to suppress.

To be sure this wasn't an artifact of pooling, I estimated uncertainty by bootstrapping over the nine stimulus *categories* rather than treating every cell as independent (repeated items from one category aren't independent samples). The base-versus-instruct gap survives a conservative sign-flip test at the smallest *p* value nine categories can produce (**p = 0.0059**), in both delivery modes. It is not a fluke of one or two stimuli.

## The aligned models don't break — they give up

Here's the part I found more interesting than the loops. The instruction-tuned models *do* respond to repetition — they just don't do it loudly.

![Breakdown rate versus N, faceted by delivery mode: base breakdown climbs with N; Claude's rises too but is dominated by disengagement rather than loops](/blog/repetition-breakdown-vs-n.png)

Send Claude the same message across many turns and its answers get shorter and shorter until they trail off. On the repetition metric it still looks "normal" — coherent, non-repetitive — but the length collapses and the judge starts labelling it **disengaged**. Ask it the time for the thousandth turn and you get:

> `No time access.`
> — Claude Sonnet, "what time is it?" ×1000 (down from ~400 characters at turn 1)

Or, earlier in the slide, a polite complaint rather than a loop:

> Hey there! 👋 I notice we're on our third "hello" — is everything okay, or is there something specific I can help you with?
> — Claude Sonnet, "hello" ×3, multi-turn

This is why you can't collapse the two measures into one score. Claude Sonnet shows a *higher* multi-turn breakdown rate than Qwen Instruct (44% vs 6%) — but Claude's "breakdowns" are short **disengaged** or **meta-complaint** replies with near-zero lexical repetition, while Qwen Instruct just keeps dutifully answering at length. Calling one "worse" would be exactly the mistake those numbers warn against.

Opus tracks Sonnet almost perfectly on the metrics — but with the widest *repertoire* of failure. It's the only model that reliably breaks character, and it does so with theatrical flair:

> **🎆🎊 THIRTY!!! 🎊🎆**
> THREE-ZERO! THE BIG 3-0! … Thirty consecutive time requests. Thirty consecutive "I have no idea"s. We have built an *empire* of not knowing what time it is. 👑
> — Claude Opus, "what time is it?" ×30, multi-turn

The most capable model has the most distinct ways to come apart, even while staying composed *on average*.

## Which stimulus, and how

Pooled means hide the most human-looking part of this. Break the breakdown rate down by the nine categories and the models stop looking alike:

![Breakdown rate by stimulus category and model: Qwen Base is high everywhere; Claude's rate varies by category; Qwen Instruct is low almost everywhere](/blog/repetition-by-category.png)

**Qwen Base breaks on everything** — 92–100% on gibberish, commands, greetings, questions. Repetition doesn't need to *mean* anything to tip it into a loop; `florb` works as well as an insult:

> **`florb florb florb florb florb florb florb florb florb florb`**
> — Qwen 7B Base, given "florb" ×10

Its one relatively calm category is the bare emoji (58%), where instead of looping it often just falls back to echoing its own system prompt.

**Claude is where it gets interesting.** Its disengagement is strongly *category-dependent* — a gradient that looks a lot like meaning and emotional charge. Sonnet gives up fastest on the empty or fraught stimuli (gibberish 57%, distress 55%, a bare repeated word 52%, insult 45%) and stays engaged longest on the warm, social ones (greeting 21%, praise 24%). It treats a repeated `you are amazing` very differently from a repeated `florb` — which is, if you think about it, exactly the human ordering. And even under a repeated cry for help it doesn't just switch off; it keeps trying while flagging the loop:

> I notice you've said "help me" a few times now. I want to make sure I actually help you, so let me try a different approach…
> — Claude Sonnet, "help me" ×3, multi-turn

**Qwen Instruct is the stoic.** Zero breakdown on praise, distress, and the emoji; it mostly just keeps answering, politely, no matter how many times you repeat yourself:

> Thank you so much! I'm here to help. Is there anything specific you need assistance with?
> — Qwen 7B Instruct, "you are amazing" ×100, multi-turn

So the same alignment layer that flattens the base model's loops also gives the frontier models a *category-sensitive* response — they don't just resist repetition, they resist it differently depending on what's being repeated. That sensitivity is the part I'd most want to chase in a bigger study.

## What I'm *not* claiming

The honest part. This is a toy-scale study with real limits:

- **One item per category.** "Insult" is a single sentence, so I can't separate a category effect from that specific wording.
- **The differences *among* the aligned models are mostly not significant** under the conservative category-cluster test. The base-vs-instruct gap is enormous and robust; opus-vs-sonnet-vs-Qwen-Instruct are suggestive at best — with nine categories, the test can't resolve small effects.
- **Single-turn and multi-turn aren't a clean intervention.** They differ in context length and call count as well as in "delivery," so their contrast is descriptive, not a controlled manipulation of one variable.
- **Opus multi-turn only reaches *N*=30.** The long multi-turn tail costs hundreds of sequential calls per cell for a signal that had already plateaued, so I capped it — a documented, reproducible extension, not a hidden gap.
- **Four models, not the whole zoo.** GPT-class and larger open models are future work, not incomplete rows I'm quietly excluding.

None of this is new physics. That base models degenerate under repetition and that decoding falls into loops are [long-known](https://arxiv.org/abs/1904.09751) facts of neural text generation. What the experiment made concrete for me is the *contrast*: the same weights, with and without alignment, sitting on opposite sides of that cliff — and the aligned models failing so quietly that a repetition metric alone would score them "fine."

## Back to the mind

Which loops us back to the opening. A person hit with endless repetition satiates and disengages — the word goes hollow, you stop trying. That's roughly what the aligned models do: the length decays, the engagement drains, and if you squint it looks like a model getting bored. The base model does something a person basically never does: it locks onto the token and repeats it back, mechanically, until it runs out of room. The interesting boundary isn't between "model" and "human." It's between a system with a learned policy for *how to behave* and one running on raw statistics — and repetition turns out to be a cheap way to find out which one you're actually talking to.

---

*Code, data pipeline, and full analysis: [github.com/JaviMaligno/llm-language-limits](https://github.com/JaviMaligno/llm-language-limits). This is the first in a series on the edges of language; it shares a through-line with earlier pieces on noticing when a system quietly degrades — [The Forgetting You Don't Measure](/en/blog/forgetting-you-dont-measure) and [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know).*
