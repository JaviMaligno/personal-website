---
title: "LLM-as-Judge Is Three Decisions"
description: "Before you write a judge prompt, you owe three decisions: the context, the unit, and the dimension. Here is the framework, applied to evaluating my production DevOps agent."
pubDate: 2026-06-14
tags: ["AI Agents", "Evals", "LLM", "Observability"]
lang: en
translationKey: llm-as-judge-three-decisions
heroImage: "/blog/llm-as-judge-three-decisions.png"
---

Last week I went to [AI Signals x LangChain Community London #32](https://lu.ma/hn9dhq7e), and one idea from [Bilge Aksu](https://www.linkedin.com/in/bilge-aksu-90595837/)'s talk on evaluation has been rattling around my head since. She put it on a slide that read **"Context comes first"** — with a subtitle I keep quoting: *you can't even choose the right unit or the right dimension until you know the context.*

That sentence reframed how I think about LLM-as-judge. We tend to treat "use an LLM to grade outputs" as a prompt-engineering problem: write a good rubric, ask for a score from 1 to 10, parse the number. But a judge that produces a number is not the same as a judge that produces a *useful* number. The useful part is decided long before the prompt — in three choices that most people make implicitly and therefore make badly.

## The trap: a score that nobody validated

Here is the failure mode Bilge described that landed hardest for me. Your judge says a conversation was "good" — but the user never came back. Or it flags a conversation as "bad" — and that user is your most loyal returning customer. The judge's criteria and the actual signal from users point in opposite directions.

When that happens, the instinct is to tweak the rubric. The real problem is usually upstream: the judge was scoring the wrong **unit**, on the wrong **dimension**, with too little **context** to know better. A 1-to-10 "overall quality" score hides all three mistakes behind one confident-looking integer.

So before writing a single line of judge prompt, I now force myself through three decisions, in order.

## Decision 1 — Context: the situation, decided first

Context is *what the judge gets to see*, and it is logically prior to everything else. Who is the user? What kind of request is this? What information was actually available when the answer was produced?

A judge with the wrong context will be confidently wrong. If I ask "was this diagnosis correct?" but only show the judge the final chat message — not the logs, not the tool outputs the agent actually saw — then the judge is grading prose, not correctness. It will reward a fluent, plausible answer over a terse, right one.

Getting context right means deciding deliberately: does the judge see the original question, the retrieved documents, the tool calls and their results, the full thread? Each of those is a knob, and leaving them at the default ("just the output") is how you end up with scores that correlate with verbosity instead of truth.

## Decision 2 — Unit: a turn, a conversation, or across sessions

The unit is *what you score*. The same system can be evaluated at three very different granularities, and they answer different questions:

| Unit | What it answers | Good for |
|------|-----------------|----------|
| **Turn** (one-shot) | Was this single response correct? | Questions with a clear, checkable answer |
| **Conversation** (thread) | Did the whole interaction reach the goal? | Iterative, multi-step problem-solving |
| **Session / across sessions** | Did the user's underlying problem get solved over time? | Retention, trust, real-world outcome |

This distinction became concrete when I started evaluating my [production DevOps agent](https://www.javieraguilar.ai/en/projects/devops-slack-bot/) — a Slack bot that triages infrastructure questions by querying real tools (Kubernetes, cloud CLIs, CI/CD, logs).

Some of its requests are genuinely one-shot: *"where do I find the logs for service X?"* has a right answer, and a turn-level judge is the correct unit — did it point to the right place, yes or no. Others are iterative: a 500-error investigation that takes ten reasoning rounds and a dozen tool calls. Scoring only the final turn there throws away the most important information — *how* it got there.

And a third category isn't really a quality judgment at all. Tool-call count, tool-call *type*, token usage, number of reasoning rounds, wall-clock time — these are efficiency metrics. They belong on their own axis, not blended into a "quality" score. Conflating "was it right" with "was it cheap" is one of the fastest ways to produce a meaningless number.

## Decision 3 — Dimension: which aspect of "good"

The dimension is *which property you are measuring*. "Good" is not one thing — it's accuracy, helpfulness, warmth, safety, conciseness, and a dozen others, and they trade off against each other. A single judge that scores "overall good" is silently averaging incompatible properties.

The fix is boring and effective: one judge, one dimension, ideally a binary verdict plus a short written critique rather than a number on a scale. "Is this factually correct? yes/no, and why" gives you something you can act on and audit. "Rate the quality 1–10" gives you noise with a decimal point.

## Putting it together: grading the DevOps agent

When I validated the DevOps agent against real support history, the three decisions made the evaluation legible instead of hand-wavy.

**Context:** I took real requests from an internal support channel and gave the judge the original human resolution thread *alongside* the bot's answer — so it was comparing like with like, not grading the bot in a vacuum.

**Unit:** per request (turn-level for the one-shot ones, thread-level for the investigations), plus a separate efficiency track.

**Dimension:** correctness first (is the answer right?), then thoroughness (did it find what the human found — or more?), with efficiency kept on its own axis.

The headline numbers, across ten real cases:

| Metric | Value |
|--------|-------|
| Correct responses | 10/10 (100%) |
| Better than the human resolution | 6/10 (60%) |
| Worse than the human | 0/10 |
| Average response time | ~2.5 min vs hours/days for the human cycle |

<br>

Then I shipped a persistent memory system and re-ran the *same* ten cases as a before/after benchmark — and this is where keeping efficiency on its own axis paid off. Quality (correctness) stayed flat at 100%, which is exactly what you want: the change wasn't supposed to make answers *more correct*, it was supposed to make them *cheaper to produce*. On that axis the gain was clear — total time dropped 57%, and one "known-answer" case went from 16 tool calls to 2 (about 7× faster) because the bot remembered the answer instead of re-investigating. Two cases didn't improve, and one actually over-investigated — which the efficiency metrics surfaced immediately, where a blended "quality" score would have hidden it.

## The dimension you forgot to validate

Now back to Bilge's trap, because my own numbers contain it. "Better than the human in 60% of cases" — better on *which dimension*, and *who decided*? I decided, reading threads, using my own judgment as the rubric. That's a perfectly good starting point. It is not the same as the dimension that actually matters in production: did the person who asked get unblocked and trust the answer enough to act on it?

That gap — between the criterion your judge optimizes and the outcome your users actually experience — is the whole game. The three decisions don't close it for you. What they do is make it *visible*: when you've named your context, unit, and dimension explicitly, you can point at exactly which one is drifting from reality, instead of staring at a single number and wondering why it disagrees with your retention chart.

## A checklist before you write the judge prompt

1. **Context** — What exactly does the judge see? Does it have everything a fair grader would need, and nothing that just rewards fluency?
2. **Unit** — Am I scoring a turn, a conversation, or a session? Does that match the question I'm actually asking?
3. **Dimension** — One property per judge. Is "efficiency" sneaking into my "quality" score?
4. **Verdict shape** — Binary + critique over a 1–10 scale, wherever I can.
5. **Validation** — Have I checked the judge against a real-world signal (human labels, retention, did-they-come-back) — or am I trusting a number nobody validated?

The prompt is the last 10% of building a good eval. The first 90% is deciding what you're measuring, on what, with what in view. Context comes first.

---

*Inspired by [Bilge Aksu](https://www.linkedin.com/in/bilge-aksu-90595837/)'s talk at [AI Signals x LangChain Community London #32](https://lu.ma/hn9dhq7e). The DevOps agent it's applied to is [described here](https://www.javieraguilar.ai/en/blog/building-a-production-devops-agent). Further reading: [Hamel Husain's guide to LLM-as-judge](https://hamel.dev/blog/posts/llm-judge/) and the [MT-Bench paper](https://arxiv.org/abs/2306.05685) that kicked off the field.*
