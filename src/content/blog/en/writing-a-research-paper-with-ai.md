---
title: "Writing a Research Paper with AI: Where Model Intelligence Actually Shows Up"
description: "The real process behind an AI-assisted preprint — and why the hardest frontier isn't prose but planning the science, where a more capable model stops being a convenience and becomes the thing that lets the work go further."
pubDate: 2026-07-21
tags: ["AI", "Research", "Writing", "Claude", "GPT"]
lang: en
translationKey: writing-a-research-paper-with-ai
heroImage: "/blog/writing-a-research-paper-with-ai.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/2607.14169"
---

This year I published a preprint — [*When a Verified World Model Still Loses*](https://arxiv.org/abs/2607.14169). It took about two weeks, on my own. Years before I ever used AI, I published my first one — my [mathematics thesis](https://arxiv.org/abs/2307.11414): a theorem, a proof, and more than two years of work with a university and a funded project behind me.

That contrast is the honest place to start. It's tempting to read it as "AI made me 50× faster." It didn't, and the last section of this article is about disentangling why. But something real did change — and the interesting part isn't the writing. It's *where* the intelligence of the model turned out to matter.

A companion note first: I already wrote about [writing an essay with AI](/en/blog/writing-an-essay-with-ai-codex-vs-claude-code), where the hard frontier was prose — tone, rhythm, rhetorical edge. Research is different. The prose is the easy part. The hard part is planning the science and reviewing it like a peer, and that is exactly where a more capable model stops being a convenience and becomes the thing that lets the work go further.

## The actual division of labor

Let me be honest about who did what. The prose in the paper is largely the AI's; I barely touched the wording. That's not the interesting part, though, and it isn't where the work was.

The work was upstream of the writing:

- **The idea came from reading**, not from a prompt that said "give me a paper" — specifically, an AI-assisted read of DeepMind's *Code World Models for General Game Playing*. Working through a dense paper with a model that can answer "why does this step follow?" on demand is a different activity from reading alone; it's where the question that became my preprint first took shape.
- **Experiments run by agents.** The synthesis pipelines, the sweeps, the arenas — set up and executed by agents, with me steering.
- **A discipline I held to on every strong claim: separate the *demonstrable* from the *measured*, and say which is which.** Where a statement could be *won* — an identifiability theorem, a coverage bound — I went and won it. Where it could only be measured, I reported it as measured, with intervals, and stopped there.

So yes, the AI wrote the paper. But writing was never the bottleneck. It's closer to running a small lab where the technicians are fast, tireless, and occasionally wrong in interesting ways — and the value I add isn't the typing.

## Where model intelligence shows up

The sharpest example I have comes from a **second, still-unpublished paper** — a continuous-control setting — so what follows is a note on process, not results.

The models changed under me as I worked, and the order matters. I started with **Opus 4.8** for planning and **GPT-5.5** as a second reader; it worked, but it took many rounds of my own questions and corrections. As soon as **Fable 5** came out I switched, and it quickly became my default — the day-to-day planning went more fluidly, with fewer corrections, and it volunteered genuinely useful directions instead of only executing mine. The one wall I still hit is Fable's subscription limits. Then **GPT-5.6** arrived and became an even better second reviewer — the one that saves me precisely when I've run out of Fable, because in practice I can swap one for the other. Its reviews read like real peer review.

One of those GPT-5.6 review passes is the clearest single example I have of what "planning science" means as a capability. Two catches from it.

### A model correcting another model's mistake

During planning, I asked my Opus 4.8 agent to jot down a future direction — heavier use of topology in higher dimensions — so we wouldn't forget it. It garbled the note: it wrote that certain 2D shapes (rings — regions with a hole) would require moving to a higher-dimensional state. That's wrong. A ring lives perfectly well in the plane and already has non-trivial topology. I know that; it's my field. But I wasn't the one who wrote it — the model was, and it slipped the error in while misreading what I'd asked for.

The catch came from a different model. When GPT-5.6 reviewed the plan, the first thing it flagged was exactly this:

> A ring lives perfectly well in 2D and has non-trivial homology; it does not require increasing the dimension of the state.

A weaker model introduced a conceptual error by misunderstanding my intent; a stronger one caught it on read. That's the small, legible version. The next one matters more.

### An experiment that couldn't answer its own question

The experiment's whole point was to isolate one variable — the curvature of a boundary — and measure how well a model could reconstruct it from sampled data. The plan fixed a quantity (how often random data touches the region) and declared that this left "only geometry" as the free variable. GPT-5.6's review took that apart:

> Fixing *r* does not leave "only geometry" as the variable. [...] With the current design, an observed curve would not let you attribute the result specifically to curvature.

It then rewrote the target as a factorization —

> P(repair) = P(the mode is visible) × P(the evidence is geometrically sufficient | visible) × P(the synthesizer represents it | sufficient)

— and pointed out that the plan only controlled the first factor. In plain terms: **the experiment, as designed, could not answer its own question.** That is not prose editing. That is planning science — and it's the capability a jump in model quality actually buys you.

It even proposed an experiment I hadn't planned: an *oracle baseline* that cleanly separates "the data doesn't contain enough information" from "the model can't represent it." A third paper was already on my roadmap — my idea, documented before any of this — and I'd asked the model to file any feedback worthy of that direction there rather than bolt it onto the current plan. It did, and it did so with real citations. A reviewer that parks its good ideas in your future work instead of derailing the task in front of it is doing something right.

You can see the before/after in git. The revision commit message is, verbatim: *"redesign repair-vs-geometry per expert review — factorization, graph boundaries, symmetric metrics, oracle baseline, topology fix."* Nearly half the document rewritten.

## It isn't always the smarter model — sometimes it's a second pair of eyes

Not every gain is raw capability. Sometimes the value is just a second, *different* set of eyes — the other model, or me — catching what the first pass missed. Back on the **first** paper, the git history is full of this, recorded in the commit messages themselves:

- A Claude agent relaying pipeline output complained that the failure data looked truncated. It was right — a logging step was cutting off the very numbers the model needed to see. That one complaint uncovered a confound that, once fixed, turned a shaky finding into one I could replicate across two more model families.
- A pass from Codex caught an overclaim that had survived earlier edits: a sentence saying the pipeline "reproduces the same play cost" when the confidence intervals right after it said otherwise.
- And the opposite of the hallucinated-citation problem everyone worries about: asked for a reference it didn't have, the model refused to fabricate a URL and left *"URL to be supplied by the author"* instead.

Plenty of the catches were also mine — the point isn't that the models replace the reviewer, it's that they multiply the number of independent passes a claim survives before it ships. I wrote more about this complementarity — how two AI tools disagree productively — in [Writing an Essay with AI: Codex vs Claude Code](/en/blog/writing-an-essay-with-ai-codex-vs-claude-code).

## The honest part: it wasn't only the AI

Back to that two-years-to-two-weeks contrast. Several things other than AI explain most of that gap, and it would be dishonest to pocket all of it as an AI multiplier:

- **Pure maths vs empirical ML.** Proving a theorem is intrinsically slower and harder than writing an empirical ML preprint. They're different kinds of work.
- **Abstraction and immersion.** A pure-maths object is more abstract; getting steeped in it simply takes longer — and back then I had no AI to speed up that immersion either, which is one more place the process multiplies today.
- **Length.** My maths paper is roughly twice as long.
- **Institutional overhead.** A funded university project carries process — meetings, coordination, revision cycles — that a solo preprint simply doesn't.

Normalize for all of that and the jump is still real, but it's a multiplier on someone who was already able to do the work, not a substitute for the ability. That axis — from pure mathematics toward applied ML — is also just the story of my own career move, and this project sits right on it.

## What I actually take away

- **The AI didn't remove the hard part; it moved where the hard part lives.** For me it stopped being "can I write and run this" and became "is this the right experiment, and does this claim survive scrutiny?"
- **On that hard part, model capability is the binding constraint.** The gap between a model that can plan science — design an experiment that answers its own question, review a claim like a peer — and one that can't is the gap between a paper that stalls and one that goes further. It's why Fable 5 is my default and GPT-5.6 is my reviewer of choice.
- **Capability isn't the only lever.** A second, different set of eyes — another model, or me — catches what the first pass didn't. Diversity is its own kind of intelligence.
- **What doesn't automate is the researcher's judgment.** Having been a researcher is the part that carries the weight here: the rigor, the scrutiny, the reflex to distrust a clean result, the habit of reviewing a claim until it either holds or breaks, knowing when something can be *proven* versus merely *measured*. That is the same function a research institution provides — peer review, a critical supervisor, a lab that argues with you — but running with fewer intermediaries and less administration, and more agile at every useful step.

---

*The first paper, "When a Verified World Model Still Loses," is on [arXiv](https://arxiv.org/abs/2607.14169); my earlier mathematics preprint is [here](https://arxiv.org/abs/2307.11414). On separating what you can verify from what you can't: [Results-Oriented Programming](/en/blog/results-oriented-programming) and [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know).*

*Interested in AI agent architectures? [Get in touch](/en/#contact).*
