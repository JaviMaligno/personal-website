---
title: "The Death of the Prompt Engineer"
description: "A claimed counterexample to a 30-year-old conjecture emerged from prompts like 'do a breakthrough' and 'just continue.' The craft of writing the perfect prompt is dying — and something more interesting is taking its place."
pubDate: 2026-07-25
tags: ["AI", "Prompt Engineering", "Agents", "Trends"]
lang: en
translationKey: death-of-prompt-engineering
heroImage: "/blog/death-of-prompt-engineering.png"
---

This week, researcher [Dmitry Rybin published](https://x.com/DmitryRybin1/status/2079904005652893709) what appears to be a compact counterexample to a graph-theory conjecture that had been open for roughly thirty years. In the proposed construction, the fractional flow costs 58, while every indivisible flow — even allowing a capacity violation of up to 15 — costs at least 60. If the construction holds up under formal scrutiny, the Dinitz–Garg–Goemans conjecture is false. The candidate came out of a [public chat session with GPT-5.6 Pro](https://chatgpt.com/share/6a60b2eb-0b64-83ee-9c76-7931ca1de063).

Here is the part that should stop you. The prompts that produced it read, verbatim, like this:

> "Construct a counterexample to general (non-planar) case of Dinitz Garg Goemans conjecture. You should do a breakthrough and find a structured counterexample."
>
> "please continue research and find a complete unconditional counterexample"
>
> "Continue the search. Have a clear strategy obtained from deeper understanding of the problem structure."
>
> "it's enough of partial results. let's finish with a complete unconditional counterexample"

That is the prompt engineering. *Do a breakthrough. Just continue. Enough partial results, let's finish.* The same week, a meme compressed the joke into four blunt instructions. Here is an original rendering of that research loop:

![Four stages of an AI research loop moving from "Do a breakthrough" through "Continue" and "Clear strategy" to "Finish it", ending in a verified graph.](/blog/prompt-breakthrough-loop.png)

*Original illustration inspired by the exchange between [@Merkaloid](https://x.com/Merkaloid) and [@mattshumer_](https://x.com/mattshumer_) on X.*

It's a joke. It's also the most honest description of the state of the art I've seen this year.

Something else died quietly in the spectacle. It was prompt engineering.

## What actually died

Not prompting. Prompting — asking a model for what you want — is more central than ever. What died is prompt engineering as an *artifact craft*: the belief that the value lived in the wording.

For a couple of years that belief had a whole economy around it. Templates. `You are an expert…` preambles. Few-shot scaffolds you tuned like hyperparameters. Delimiter tricks and "think step by step" incantations. Prompt marketplaces. Job posts for "Prompt Engineer" at six figures, as if the skill were a stable profession rather than a temporary artifact of weak models. A few months ago I wrote an article that listed prompt engineering, without irony, as one of the core skills that would matter going forward. I was describing a moving target and didn't know it.

The tell is the math example. If prompting were still an artifact craft, producing a serious candidate counterexample to a thirty-year-old conjecture would demand the most exquisitely engineered prompt anyone had ever written. Instead it took "do a breakthrough." The wording carried almost no information. All of it came from the model and the loop.

## The everyday version: the ramble

You don't need an open conjecture to see it. Andrej Karpathy described the ordinary version in a post that Carlos Santana amplified with exactly the right framing — that Karpathy wasn't discovering anything, just naming out loud what practitioners already did in silence:

> "One pattern I find useful for working with LLMs is a nice long ramble session… I like to lean back, switch to /voice and just ramble for like 10 minutes, total mess, anything goes, full stream of consciousness… I find that the LLMs are somehow very good at reconstructing long incoherent rambles and often their echo of your own tangle of thoughts comes out quite a bit cleaner than what you started with."

If you've done this, you know the feeling: you stop composing and start *gesturing*. You dump a mess and the model hands back something more coherent than what you put in. This very article started as a ten-minute voice ramble, typos and all — which is why it can end by describing itself.

That is the opposite of prompt engineering. You're not curating the input. You're trusting the system to reconstruct intent from noise.

## Why it died: the harness ate the job

Two things killed the artifact.

The first is the **harness**. Modern coding and research agents don't sit and wait for a perfectly specified request. They search your environment, retrieve the relevant files, carry memory across turns, and run agentic loops that gather the context you used to hand-feed. The work that prompt engineering used to do — assembling exactly the right bits in exactly the right order — got absorbed into the tooling. You give a badly worded paragraph; the harness goes and finds the rest.

The second is **raw capability**. The models are now good enough to reconstruct intent from a bad input, and to keep going when the instruction is just "continue." In the conjecture case there is barely any prompt engineering left to point to — it's replaced by *iteration*: repeat "keep going, now finish" while the agent decomposes the problem itself. The intelligence moved from the sentence into the model and the loop around it.

## What didn't die — and this is the important part

It would be a lie to end on "just ramble and the machine does everything." For the genuinely hard problems, effort didn't disappear; it changed shape.

Behind "do a breakthrough" there is still a person who knows a real result from a plausible one. When I [wrote a research paper with AI](/en/blog/writing-a-research-paper-with-ai), the discipline that mattered wasn't the wording — it was separating what could be *demonstrated* from what could only be *measured*, and refusing to blur the two. In one planning session a model garbled a note about topology, claiming a ring in the plane needed a higher dimension. I caught it because it's my field, not because I'd written a clever prompt. The model can do the search; you still have to know when the answer is real.

And for the hardest work you increasingly reach not for a better prompt but for a **structure** — a skill, a harness — that forces the model to try several strategies, decompose the problem into smaller parts or lemmas, run experiments, write tests, review its own output, hold a standard of rigor. That scaffolding is the successor to the prompt template. It's not a magic sentence; it's a process. The candidate counterexample didn't emerge from one lucky message either — it came from a loop that kept insisting on rigor until a partial result became a complete one.

So the skill didn't vanish. It moved — from the *words* to the *framing, the steering, and the verification*. Karpathy's term for the goal is the "mind meld": getting the model aligned with what you actually mean, so you have to correct it less from that point on. That is the craft now. The trend line is unmistakable: every generation does more with less, and the part you can leave to the model keeps growing.

## The effort didn't disappear — it moved up

If prompt engineering is dying, it's not because engineering left. It's because it climbed the stack. The leverage used to sit at the level of the sentence. Now it sits at the level of the *system*: which model you hand a task to, whether you plan with a strong one and execute with a cheap one, what structure you wrap around the loop.

That's a whole discipline of its own — the one I'd argue is replacing prompt engineering rather than merely outliving it — and it deserves its own piece. For now the short version is this: the best "prompt" in 2026 is a ten-minute ramble to a system that already knows your codebase, and the skill worth having is knowing what to build around it.

The prompt was never the point. Getting the machine to understand you was.

---

*This is the first of two pieces on how "engineering" work in AI keeps relocating. The second is about **routing engineering** — choosing which model and how much reasoning to spend on each task. See also [Software Is Dissolving Into the Model](/en/blog/software-dissolving-into-the-model).*
