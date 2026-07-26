---
title: "Routing Engineering"
description: "Once prompting stops being the hard part, a new question takes its place: which model, at what reasoning effort, for which slice of the work. Choosing well is becoming its own engineering discipline."
pubDate: 2026-07-26
tags: ["AI", "Routing", "Agents", "Cost", "Trends"]
lang: en
translationKey: routing-engineering
heroImage: "/blog/routing-engineering.png"
---

In the [first part of this pair](/en/blog/death-of-prompt-engineering) I argued that prompt engineering — the craft of wording — is dying, and that the effort didn't vanish so much as climb the stack. This is where it climbed to.

Here is the new friction. I sit down to a task and, before I've done anything, I face a grid. [OpenAI now ships GPT-5.6](https://openai.com/index/gpt-5-6/) in three tiers — Sol, Terra, Luna — with several reasoning-effort settings and a new `max` level. Add the earlier 5.x models still in rotation and the Codex variants, and one vendor already gives you dozens of plausible (model × effort) routes. [Claude's effort ladder](https://platform.claude.com/docs/en/build-with-claude/effort) spans `low`, `medium`, `high`, and `max`, with `xhigh` on supported models. Gemini has a thinking budget. The wording is no longer the decision. *The allocation* is: which model, at what effort, for which slice of the work. Getting that right is what I'd call routing engineering, and it's quietly become one of the more valuable things to be good at.

## The matrix nobody asked for

The uncomfortable part is that the grid grew faster than our ability to reason about it. When a single model had one setting, "use the best one" was a complete strategy. Now the knobs multiply with every release, and most of them trade the same three things against each other: quality, latency, and cost. A `max`-effort frontier model will grind through almost anything, but it's slow and it burns tokens. A cheap model at `low` effort is instant and nearly free, and it will confidently wreck a task that needed a moment of thought.

Nobody hand-optimizes a hundred-cell grid per task, so in practice we all collapse it into a handful of habits. The interesting question — the engineering one — is *which* habits actually pay, and when the granularity is worth the bother at all.

## What I actually do

My own default is embarrassingly simple, and it's a routing decision. In Claude Code I plan with Fable 5 and then execute with Opus or something lighter. If I let the planning-grade model drive the whole task, token usage explodes; the plan is where the intelligence has to be, and the execution mostly has to *follow* the plan. Splitting the two along that seam is the single change that made long agent sessions affordable for me.

*Publication note: two days before this article went live, [Opus 5 arrived](https://www.anthropic.com/news/claude-opus-5) with performance close to Fable 5 on many tasks at half the price. It has already replaced Fable as my planner. The route changed before the article even shipped, which is almost too on-theme.*

I do the same thing in research. In [writing a paper with AI](/en/blog/writing-a-research-paper-with-ai) the division that mattered was Fable 5 for planning the science and GPT-5.6 as a second reviewer — a strong model where judgment lives, a swap when I hit usage limits, and cheaper execution in between. None of that is prompt craft. It's routing: matching the model to the shape of the work.

## Why the split works

The reason this particular seam — plan strong, execute cheap — keeps showing up is that most of a task's difficulty is concentrated in a few decisions. [Cursor put a number on it recently](https://cursor.com/blog/agent-swarm-model-economics). In a study on long-running agent "swarms," they had a fleet build SQLite from scratch in Rust, working only from its 835-page manual, and varied who planned and who executed. Their own summary of the mechanism is the clearest statement of the principle I've seen:

> "There are few moments in a large task that truly require frontier intelligence — the initial decomposition, the design decisions, certain trade-offs. Once a frontier planner has turned ambiguity into a detailed, explicit instruction, the cheaper models simply have to follow it."

The result was that every model mix reached *similar quality*, while cost varied by roughly 8× — from about \$1,339 for an Opus-4.8-plans / Composer-2.5-executes hybrid, up to \$10,565 for GPT-5.5 doing everything itself. On the execution slice alone the gap was starker: the cheap workers cost around \$411 where the all-frontier run's workers cost \$9,373. Same destination, an order of magnitude apart on the fare.

And this isn't only a vendor's marketing claim. The older academic evidence already pointed the same way: [RouteLLM](https://github.com/lm-sys/RouteLLM) reported up to **85% cost reduction while keeping 95% of GPT-4's quality** by routing each query to a strong or weak model; [FrugalGPT](https://arxiv.org/abs/2305.05176), earlier still, showed cascades matching a top model at up to 98% lower cost. Those are useful proofs that the asymmetry has been known for years, not measurements of today's frontier. The more current picture is also more sobering: [LLMRouterBench](https://arxiv.org/abs/2601.07206), published in January 2026, re-evaluated ten routing methods across more than 400,000 examples, 21 datasets, and 33 models. It confirmed that models are complementary, but found that several recent methods — including commercial routers — did not reliably beat a simple baseline. The savings are real; extracting them reliably is still unsolved.

## The part that makes it *engineering*

If it were just "plan with the smart one," it would be a tip, not a discipline. What makes it engineering is that the obvious move is often wrong.

The same Cursor study has a detail I keep coming back to: the hybrid built on the *stronger, newer* planner (Fable 5) ended up **more expensive** than the one built on Opus 4.8 — even though the Fable planner's own bill was slightly lower. The catch was downstream: its plans led the cheap workers to consume several times more tokens, and workers are where the volume is (they accounted for at least 69% of tokens in every run, over 90% in most). A better planner produced a costlier run.

That's the whole lesson in one data point. The cost of a route is non-linear and it lives mostly in second-order effects — how a plan shapes execution, not the planner's own price tag. You cannot read it off a spec sheet. You have to measure the route end to end, which is exactly the kind of thing engineering disciplines exist to do.

## Manual, or automatic

You can route by hand, the way I do, or hand the decision to a system.

The automatic tier is filling in fast. Cursor now ships a request-level **[Router](https://cursor.com/blog/router)** that classifies each task and sends it to an appropriate model, with an Auto mode you can bias toward intelligence, balance, or cost — they report 30–50% cost reductions at frontier quality in early enterprise use. [OpenRouter](https://openrouter.ai)'s `auto` endpoint routes per-prompt (powered by NotDiamond's model) with a cost-versus-quality dial. Martian and NotDiamond sell the same idea as a service. There's even a small benchmark literature trying to answer "how good is routing, really," and the honest read is *promising but unsettled*: some routers save real money, and some, under scrutiny, just default to the expensive model.

There is a deeper difficulty: **you often cannot know how hard a task is until you start doing it**. A prompt that looks routine can hide a nasty dependency three tool calls in; a frightening one can collapse after the first inspection. One-shot routing has to predict that latent difficulty before seeing the evidence the work itself will reveal. Recent research is starting to move the decision inside the execution loop. [TwinRouterBench](https://arxiv.org/abs/2605.18859), from May 2026, routes at every call inside coding and research-agent trajectories and checks whether the whole task still succeeds. In one diagnostic, even Opus 4.6 acting as the router identified only 7 of 147 steps that execution later showed really needed the high tier, and all 40 SWE-bench trajectories failed. [R2R](https://proceedings.neurips.cc/paper_files/paper/2025/file/b39cef2ef90591cffdc9c674cd55bebe-Paper-Conference.pdf), at NeurIPS 2025, goes finer still: it begins generating with a 1.5B DeepSeek-R1 distilled model and invokes the 32B model token by token when the reasoning path starts to diverge. The router is no longer a receptionist choosing a model at the door; it is a supervisor watching the work unfold and escalating when necessary.

Automatic routing will get better, but it inherits the hard part above: to route well it has to predict the second-order cost, not just classify difficulty. For now I trust a hand-drawn seam I've measured over a router I haven't.

## When it's worth it

Here's the part I'd push back on the hype about: routing granularity has a cost of its own, and it isn't always worth paying.

For a one-off task, the entire calculus is often "use the best model and move on" — the time you'd spend tuning a route dwarfs the tokens you'd save. Granular routing earns its keep when one of three things is true: **volume** (you're running the task thousands of times), **tight cost or latency budgets**, or a **clear plan/execute asymmetry** like the long agent sessions above. Outside those, a router is premature optimization wearing an engineering costume. Knowing when *not* to route is as much a part of the discipline as the routing itself.

## The unit keeps getting bigger

Step back and there's a through-line with where all of this is heading. Cursor framed their swarm as a kind of probabilistic compiler — planners decompose intent into a tree, cheaper models compile the leaves — and noted that "the unit of work becomes the specification." That rhymes with the [software dissolving into the model](/en/blog/software-dissolving-into-the-model): what you hand the system keeps getting larger and less literal, and the scarce skill becomes describing intent well and deciding what runs where.

There's one more honest wrinkle worth keeping. In that same study, the team wanted to use GPT-5.6 Sol as their frontier planner and couldn't — the new model was so sensitive to literal, emphatic wording that it spiraled out of control, and they fell back to GPT-5.5 rather than re-tune the prompts. So even at the frontier of routing, a ghost of prompt engineering is still in the room. The craft didn't die so much as move — from the words, to the wiring. Choosing the model *is* the new craft.

---

*This is the second of two pieces on how "engineering" work in AI keeps relocating up the stack. The first is [The Death of the Prompt Engineer](/en/blog/death-of-prompt-engineering).*
