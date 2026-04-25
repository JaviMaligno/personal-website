---
title: "Markdown Above, Pixels Below: How Software Is Dissolving Into the Model"
description: "Code is moving up to the skill layer, UIs are moving down to generated pixels, and the middle keeps getting thinner. A look at where software is heading in 2026."
pubDate: 2026-04-25
tags: ["AI", "Agent Skills", "Generative UI", "Software", "Trends"]
lang: en
translationKey: markdown-above-pixels-below
---

Two repositories caught my eye this month. The first is [`google/agents-cli`](https://github.com/google/agents-cli), Google's official tooling for building agents on Google Cloud — a CLI plus a bundle of markdown "skills" that any coding assistant (Claude Code, Codex, Gemini CLI, Cursor) can pick up. The second is [Flipbook](https://flipbook.page/), an experimental "browser" launched by ex-OpenAI researchers two days ago. Flipbook has no HTML, no DOM, no rendered components. Every pixel you see — including the text — is generated frame-by-frame by a video diffusion model streaming over a WebSocket.

They look like they belong to different conversations. They don't. Put them next to each other and a pattern emerges: the layer we used to call "software" is being squeezed from above and below. The code we write is becoming markdown. The UI we render is becoming a model output. The middle keeps getting thinner.

## Above: software is becoming markdown

Skills are repositories of instructions, not deployed services. The runtime is whatever coding agent the user happens to have installed. The artifact is a `SKILL.md` file with maybe a couple of helper scripts.

A few data points from the last few weeks:

- [`OthmanAdi/planning-with-files`](https://github.com/othmanadi/planning-with-files) is a Claude Code skill that gives the agent a Manus-style persistent planning workflow — a few markdown files defining when to write `task_plan.md`, `findings.md`, `progress.md`. It has 9.2k stars. Manus, the company that built that workflow into a full product, was reportedly acquired for $2B. The IP was the pattern, not the implementation.
- [`VoltAgent/awesome-agent-skills`](https://github.com/VoltAgent/awesome-agent-skills) curates 1000+ portable skills across Claude Code, Codex, Gemini CLI, Cursor and 40+ other agents. 18.7k stars.
- GitHub shipped [`gh skill`](https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/) on April 16 — a first-class CLI primitive for installing, pinning and publishing skills directly from GitHub repositories.
- Google Workspace's official CLI now ships [100+ `SKILL.md` files](https://github.com/googleworkspace/cli), one for every supported API, plus 50 curated recipes for Gmail, Drive, Docs, Calendar and Sheets.

A year ago, "ship a tool for X" meant building an SDK, a service, or at least a wrapper library. Today it increasingly means writing a folder of markdown that any agent can load on demand. The trend isn't "AI helps you write software". It's "what we used to call software is now an instruction set".

## Below: the UI is becoming a model output

Now flip the stack upside down. The other end is doing the same thing.

Flipbook launched on April 23 from Zain Shah's team (ex-OpenAI, ex-Humane, ex-Apple), out of South Park Commons. The interface is generated pixel-by-pixel by [LTX Video](https://github.com/Lightricks/LTX-Video), an open-source diffusion transformer for video, optimized to stream at 1080p/24fps via WebSocket from Modal Labs serverless GPUs. There is no DOM. There are no buttons in the traditional sense. When you "click", the model generates the next frames.

DeepMind has been doing the same thing at world-model scale. [Project Genie](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/project-genie/) rolled out to AI Ultra subscribers in January 2026, powered by Genie 3. You type a prompt. You walk around a generated world that is being generated as you move, at 24fps, with consistency held for a few minutes.

These are demos. Flipbook is barely useful as a product yet. Genie's worlds last a minute or two before the model loses coherence. But the direction is clearer than the products: the rendered output of an application is becoming a model inference, not a tree of components.

## We're the ones who should adapt

A friend told me this week that he'd been trying to get an LLM to write internal reports following his company's exact style guidelines. After enough iteration he realized the prompt-engineering effort to keep the model on rails was taking him longer than writing the reports himself — and his company has multiple report types like that.

What he said next stuck with me: *"Maybe the problem isn't that the AI can't adapt. Maybe we're the ones who should adapt. We're making it less efficient with all our constraints, when what it produces on its own is good enough for the purpose."*

That insight isn't really about reports. It's the thing happening on both ends of the software stack right now.

A markdown skill is what you get when you stop trying to force the model into the shape of a typed SDK with versioned interfaces and start writing in the medium the model actually thrives in: natural language with examples. Flipbook is what you get when you stop trying to force the model to emit valid React components and start letting it render the pixels directly.

The friction we were adding — typed APIs, deterministic UIs, hand-coded glue — was buying us correctness, but at a cost we hadn't priced in. Every constraint also costs throughput, and a lot of those constraints existed because *humans* needed them, not because the model did.

That doesn't mean correctness goes away. It means we re-locate it. Evals replace types. Skill instructions replace SDK documentation. Frame-level objectives replace pixel-perfect Figma specs. We're trading one kind of rigor for another that fits the tool better.

## What survives in the middle

So if the code is going up to the skill layer and the UI is going down to the pixel layer, what's left for those of us building things in the middle?

I've been thinking about this in the context of my own work.

The MCP servers I've built — [`mcp-server-bitbucket`](https://github.com/JaviMaligno/mcp-server-bitbucket), [`postgres_mcp`](https://github.com/JaviMaligno/postgres_mcp), [`langfuse-mcp-server`](https://github.com/JaviMaligno/langfuse-mcp-server) — already live in this new shape. They're not products with UIs. They're protocols any agent can pick up. The interface is the spec, not the screen.

The compliance classifier and the medical document parser depend on something that *doesn't* compress into a markdown file: a curated taxonomy, edge cases extracted from real documents, an evaluation suite that proves the model handles the long tail. The orchestration around them increasingly does compress into instructions, but the domain context doesn't.

The data-source automator's value is in a specific human-in-the-loop sequence we worked out the hard way — where the agent stops, what it asks, what it logs. Two years ago that lived in code. Today it lives more naturally as a skill plus an eval set.

What survives in the middle is the stuff that wasn't really code in the first place: the data, the taxonomy, the eval harness, the orchestration *decisions*. The stuff that was just "code" — the wrapper, the form, the boilerplate — heads up to the skill layer or down to the generated render.

## Engineers can't hide in the niche anymore

There's a corollary for those of us who write the code being squeezed: the gap between idea and shipped product is getting short enough that we can't stay tucked into a development niche and still add value.

When the middle layer was thick, you could be "the backend person" or "the LLM ops person" and contribute through a slice of the stack. The product owner had the idea, designers handled the surface, engineers handled the plumbing, and the handoffs were the work. When the middle is thin, those handoffs cost more than they coordinate. The model renders a lot of the surface. The agent carries a lot of the plumbing.

What's left for engineers looks more like product judgment than implementation — which problem to solve, what "good enough" means in this domain, where the model needs to be on rails and where it doesn't, what failure looks like and how to catch it. Even when you're not building your own product, you can't hide in your niche. You have to take ownership of the outcome to be trusted with it — because the part you used to be paid for, the implementation, is the part that's compressing.

## Practical takeaways

Three things I'm acting on:

1. **Ship the skill, not the wrapper.** If you're building anything that lives behind an LLM, the wrapper code is the part with the shortest half-life. The skill — instructions, examples, evals — is what you actually own.
2. **Stop fighting the medium.** If you're spending more time constraining the model than the model is spending producing useful output, you're solving the wrong problem. Either accept what it produces or pick a different tool.
3. **Invest where the moat is.** The new defensible thing isn't "we built it well". It's "we have the data, evals and orchestration that prove this works in our domain". That's where I'm putting time on my own products.

Software isn't disappearing. It's redistributing itself across the stack — and the middle, the part we used to call "the application", is getting a lot thinner than I expected even six months ago.

---

*Repositories referenced: [google/agents-cli](https://github.com/google/agents-cli) · [OthmanAdi/planning-with-files](https://github.com/othmanadi/planning-with-files) · [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills). Demos: [Flipbook](https://flipbook.page/) · [Project Genie](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/project-genie/).*
