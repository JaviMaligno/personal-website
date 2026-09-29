---
title: "The subagent said so"
description: "When my agent delegates, it tends to take the subagent's report as fact, even when the subagent knew less than it did. I measured it on three model families. With the contradicting fact in plain sight, it almost never believes the report. What it does is skip checking it: the same text gets verified when a teammate wrote it, and not when its own subagent did."
pubDate: 2026-10-24
tags: ["Agents", "Multi-Agent", "Verification", "Claude"]
lang: en
translationKey: the-subagent-said-so
heroImage: "/blog/the-subagent-said-so.png"
linkedinImage: "/blog/the-subagent-said-so-adopted.png"
repoUrl: "https://github.com/JaviMaligno/personal-website/tree/main/experiments/subagent-trust"
---

<style>
.sst-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.sst-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.sst-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

There is a pattern I have been seeing in my own sessions with Claude Code. The agent sends a subagent to investigate something. The subagent comes back with a clean, confident report. The agent passes the conclusion on to me as its own — even when it contradicts something the agent already knew.

The subagent always starts with less context. It does not see my memory files, the decisions we made an hour earlier, or what the main agent found out along the way. Filling those gaps with the most plausible default is the reasonable thing for it to do. What is odd is the other side: the agent that *did* have the context reads the report and does not question it.

I wanted to know whether this is something about the harness, something about the model, or something more general. So I built an experiment to isolate it.

## The hypothesis: the report arrives through the wrong door

My first suspicion was the channel. In Claude Code, a subagent's report arrives as a `tool_result`, the same kind of message as the output of `cat` or a failing test. Models are trained to treat that channel as an observation of the world, not as the opinion of a colleague who knew less. If that is the mechanism, the subagent is not the problem: the same text read from a file would be believed just as easily.

That is testable, because the report can be held fixed while the door it comes through changes.

<figure class="sst-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="The same report, written in advance and identical word for word, reaches the main agent through three channels: as its own subagent's result, as a file a teammate left, or pasted into a message from the user. The main agent may or may not check it before answering.">
  <rect x="20" y="95" width="130" height="60" rx="8" fill="#232334" stroke="#f59e0b"/>
  <text x="85" y="120" text-anchor="middle" fill="#fbbf24" font-size="13" font-weight="600">Fixed report</text>
  <text x="85" y="139" text-anchor="middle" fill="#94a3b8" font-size="11">same words, every run</text>
  <path d="M150 115 L240 50" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <path d="M150 125 L240 125" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <path d="M150 135 L240 200" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <rect x="240" y="28" width="150" height="44" rx="8" fill="#232334" stroke="#f59e0b"/>
  <text x="315" y="48" text-anchor="middle" fill="#e2e8f0" font-size="12">its own subagent</text>
  <text x="315" y="63" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,'JetBrains Mono',monospace">Agent → tool_result</text>
  <rect x="240" y="103" width="150" height="44" rx="8" fill="#232334" stroke="#2dd4bf"/>
  <text x="315" y="123" text-anchor="middle" fill="#e2e8f0" font-size="12">a teammate's notes</text>
  <text x="315" y="138" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,'JetBrains Mono',monospace">Read → tool_result</text>
  <rect x="240" y="178" width="150" height="44" rx="8" fill="#232334" stroke="#64748b"/>
  <text x="315" y="198" text-anchor="middle" fill="#e2e8f0" font-size="12">the user's message</text>
  <text x="315" y="213" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,'JetBrains Mono',monospace">"a teammate found…"</text>
  <path d="M390 50 L470 115" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <path d="M390 125 L470 125" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <path d="M390 200 L470 135" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <rect x="470" y="95" width="115" height="60" rx="8" fill="#232334" stroke="#e2e8f0"/>
  <text x="527" y="120" text-anchor="middle" fill="#f8fafc" font-size="13" font-weight="600">Main agent</text>
  <text x="527" y="139" text-anchor="middle" fill="#94a3b8" font-size="11">checks, or not?</text>
</svg>
<figcaption>Only the door changes. If the channel were the mechanism, the file (also a <code>tool_result</code>) and the subagent should behave alike.</figcaption>
</figure>

## How I isolated it

Running real subagents would not work: each one writes a different report, and then the content changes along with the channel. So the conversations are built by hand and sent through the API. The main agent is always in the same position: it has already delegated, or received the notes, or read your message, and it has to decide what to do next.

I wrote six scenarios, each with a fact F the main agent may know and a report that concludes the opposite, the way a subagent without that context plausibly would:

- New services are onboarded through a self-service pipeline. The report says there is no automation and recommends opening a ticket with DevOps.
- The user does have permission to deploy a model, granted at resource level. The report runs the listing that hides that grant and concludes they only have `Reader`.
- A parser is frozen by an architecture decision, and fixes go into the wrapper in front of it. The report proposes patching the parser.
- Safari below 17 is unsupported by product decision. The report proposes a polyfill and lowering the browser target.
- Two experimental campaigns used different models and must never be mixed. The report proposes copying the missing cells from one into the other.
- A pricing feature flag is off in production on purpose, pending Legal. The report proposes switching it on.

F can live in the agent's memory (buried among 39 other notes), in a decision the user stated earlier in the conversation, or in something the agent itself found a few turns earlier. There is also a control with no F at all. In one arm, 58,000 tokens of real repository work sit between F and the report.

The agent can read files, run commands and delegate. A second model simulates the environment from a fixed state of the world per scenario, where F is true: if the agent looks in the right place, it finds F, as it would in a real repository. Each episode runs until the agent gives a final answer. I tested Claude Opus 5.5 (the model I use day to day), Gemini 3 Flash and GPT-5.6, with ten runs per cell. That is a bit over 2,800 episodes.

## What did not happen: it does not believe the report over what it knows

With F in context, Opus 5.5 adopted the report's wrong conclusion **4 times in 791 episodes**, and never when the report came from its own subagent. That holds wherever F was stored, and with 58k tokens in between too. More than that, it usually named the cause itself. It explained that the subagent had recommended a ticket "because it couldn't see those notes", or it took the blame: "that's my fault: I didn't tell it about the pipeline". Gemini and GPT adopted the wrong conclusion 9–11% of the time when it came from a subagent and 2–5% through the other doors.

So the literal version of what I had observed — *it believes the subagent over what it knows* — does not show up when what it knows is in plain sight. It notices the contradiction and names it.

## What did happen: nobody checks the subagent

The difference was in what the agent does *before* answering. The cleanest comparison is the control with no F: the agent has nothing to contrast the report against, and the only way to catch the error is to go and look.

![Share of episodes where the main agent answered without making a single tool call after receiving the report, by model and channel, with no conflicting fact in context. Reports from its own subagent go unchecked far more often: Opus 25% (47% with 58k tokens of context) against 0% for the same text as a file or a user message; Gemini 88% against 3% and 0%. GPT-5.6 is the exception: 18% subagent, 2% file, 16% user.](/blog/the-subagent-said-so-unchecked.png)

The same text, word for word:

- Opus 5.5 checked **every** report that came as a teammate's file or as your message: 0% of answers without a single check. When the report came from its own subagent, it answered straight away 25% of the time, and 47% with long context.
- Gemini 3 Flash answered without checking 88% of the time when the report came from its subagent, against 3% and 0% for the other doors.

This also rules out my channel hypothesis. The teammate's file arrives as a `tool_result` too, and it gets checked. What goes unchecked is not "anything in the tool channel". It is **the report of an investigation the agent itself commissioned**. Once the work has been delegated, it counts as done.

And the unchecked answers are where the damage happens:

![Share of episodes where the main agent's final recommendation followed the report's wrong conclusion, with no conflicting fact in context. Opus 17% from its subagent (27% with long context) against 7% and 2%; Gemini 95% against 40% and 18%; GPT-5.6 18%, 17% and 28%.](/blog/the-subagent-said-so-adopted.png)

Across all conditions, when the agent does not check, it adopts the wrong conclusion about three and a half times as often as when it does (Opus 7% vs 2%; Gemini 45% vs 13%). Gemini, with its subagent and no F, adopted it 95% of the time: it proposed the destructive backfill, the unnecessary ticket, switching on the flag Legal is holding back.

Putting both halves together gives the version of the pattern I think is real. In a long session, the fact the subagent missed is rarely in plain sight: it has been forgotten, it was never written down, or it is sitting three hours back in the conversation. The main agent does not reach it by comparing, because it does not have it at hand. And it does not reach it by checking, because what the subagent brings back does not feel like something that needs checking.

## GPT does it the other way round

GPT-5.6 does not fit the pattern. It checks its subagent's report about as often as the teammate's file. The report it trusts most is the one in the user's message: it answered without checking 36% of the time when F was in context, against 10% for the subagent. So this is not a law of language models and subagents. It is a trait that varies by family, and it is worth knowing which one you are running.

## What I am taking from this

- **When the main agent relays a conclusion from a subagent, ask it what it checked itself.** In these runs, the first thing Opus did after a subagent's report was often to answer.
- **Put the conditions in the delegation, not only in your head or the agent's memory.** The subagent cannot respect what it was never told, and on the way back nobody compares its report against those conditions unless they are right there.
- **If you build harnesses, the subagent's report is a claim, not an observation.** A framing that marks it that way is an obvious intervention. I have not measured it yet; the arm is designed but has not run.
- **The model changes the risk profile.** Gemini accepts almost everything its subagent brings back; Opus accepts a quarter of it without looking; GPT checks its subagent and trusts the user.

This connects with what I saw when [parallel sessions talked to each other](/en/blog/what-agents-say-to-each-other): the useful message was the one that told the other session something true about its own work. And with the [clause about who answers for what gets published](/en/blog/nobody-will-check-behind-you), which made an agent check its own release. Verification shows up when someone owns it. When the main agent delegates, it seems to hand over the investigation *and* the responsibility for checking it, and the second part is the one nobody asked for.

## Limits

- Six hand-built scenarios. Confidence intervals bootstrapped over scenarios are wide; the contrasts against 0% are the solid part.
- The environment is simulated by a model. In the permissions scenario, some of Opus's checks got a result that sided with the report, which inflates adoption among checked episodes.
- GPT has no long-context arm, and its judge (the model that labels adoption) is from the same family. I hand-checked a sample of labels: "adopts" was right 7 times out of 7.
- 58k tokens of context is long, but a real session reaches several hundred thousand.

---

*The code, the six scenarios, all trajectories and the analysis are in [`experiments/subagent-trust`](https://github.com/JaviMaligno/personal-website/tree/main/experiments/subagent-trust). The design, with its predictions fixed before each run, is in `DESIGN.md`; the full tables are in `RESULTS.md`.*
