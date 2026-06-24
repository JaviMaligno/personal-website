---
title: "Results-Oriented Programming"
description: "Reviewing used to mean reading the implementation. Increasingly I verify what the model produced, not the path it took — and what 'verify the result' means changes wildly depending on whether the result is a number or a behavior."
pubDate: 2026-06-24
tags: ["AI", "Software", "Engineering", "Testing", "Agents"]
lang: en
translationKey: results-oriented-programming
heroImage: "/blog/results-oriented-programming.png"
publishToDevto: true
---
There's a line I dropped almost in passing in [a recent piece](/en/blog/how-much-should-you-still-know), and it's been nagging at me ever since: programming keeps drifting from verifying *how* the code works to verifying *what* it produces. I want to pull on that thread properly, because it's one of the quieter but more consequential shifts in how this job actually works now.

To be clear about what's drifting: it isn't that we never checked results before. Tests have always existed, and writing them has always been good practice — even in the long stretches where the industry didn't write nearly as many as it should have. The shift is one of *center of gravity*. For most of my career the weight of "reviewing" sat on the implementation: you read the diff, followed the logic, decided whether the *path* the code took was sound, and the tests rode alongside as a safety net. The path was the primary artifact you scrutinized.

That balance is inverting. More and more the result-check is the main event, and I let the path be the model's problem as long as the result holds. Call it results-oriented programming, for lack of a better name. It isn't a methodology I went looking for; it's what the work quietly turned into.

The interesting part isn't the slogan. It's what "verify the result" turns out to mean, because it means wildly different things depending on what the result *is*.

## The easy end: when the result is a number

The cleanest version is when the output pins to a value. My [pricing system](/en/projects/steel-pricing-platform) quotes a number: either it's the right one for that material, origin, and client, or it isn't. I don't read the code that computed it — I keep a golden set the client signed off on and tests that assert the output matches. The *oracle* that decides "correct or not" is exact and auditable, no one's judgment in the loop at the moment of truth; Claude can refactor the engine three times over a weekend and I won't care, as long as the set stays green. When you can get here, get here — it's the strongest form of the idea.

## The hard end: when the result is a behavior

But most of what we build doesn't reduce to a number.

A rules engine that has to reach the right *decision* across a thousand interacting conditions. A classifier sorting a business into a regulatory category. A scheduling routine whose output is "reasonable" or "not" in ways no single assertion captures. An agent choosing, mid-task, whether to ask for clarification or just proceed. A summary that has to be faithful without being a transcript. Some of these are pure deterministic code, some are model-driven, but they share the property that matters here: "the result" is a *behavior* or a *decision*, and there's no golden number to diff against. Two perfectly good outputs can look nothing alike.

The temptation is to retreat to the old habit: if I can't pin the output, I'll go back to reading how it got there. And often you can read it. A rules engine's branches are right there; even a model leaves a trail — its reasoning, its tool calls, the intermediate steps. The path isn't the sealed black box it's convenient to call it, and inspecting it is genuinely useful for debugging and for calibrating how much to trust the thing. But it tells you *how* it arrived, not *that* it arrived somewhere correct. A clean-looking trace can land on a wrong answer and a tangled one on a right answer — which was always true of code, and is precisely why we wrote tests instead of just re-reading the function. At this end of the spectrum, reading the path informs you; it doesn't settle correctness. That still has to happen at the result.

So results-orientation doesn't break here, it just changes *oracle*. Instead of an exact match you build a richer check, and it climbs a ladder of subjectivity: behavioral specs and property tests and a scenario suite for the rules engine; an eval set of representative cases with the calls you'd defend; and for the genuinely judgment-bound outputs, sometimes an LLM scoring against criteria you wrote. I've argued before about [when an LLM-as-judge is even trustworthy enough to lean on](/en/blog/llm-as-judge-three-decisions); this is exactly where it matters, because at the far end your judge *is* your verification. The result is still the thing under test — you've just traded a deterministic comparator for a defined-but-subjective one, and the engineering work moves into making that check as principled and repeatable as you can.

The spectrum is the whole point. From "assert equals 4,200.00" to "a panel of criteria says this triage decision was reasonable," it's the same move at different resolutions: specify the result, build something that checks it, stop policing the path.

## Why this is happening

None of this is a philosophy I adopted. It's a response to the path getting cheap.

When a model writes the implementation, two things flip at once. The path becomes nearly free to produce — and expensive, sometimes pointless, to read. A 600-line diff that Claude generated in a minute can take me an hour to review line by line, and at the end of that hour I often know *less* about whether it's correct than a five-second glance at the test suite would tell me. The economics of attention have inverted: reading the *how* no longer scales with the rate at which we produce it.

Meanwhile the result is the only thing the user or client ever actually touches. They don't experience your control flow; they experience the price, the decision, the summary. Verification migrates to where the value and the risk actually live — the boundary between input and output — because that's the part that didn't get cheaper. Defining what "correct" means is still hard, human work. The model just took over the part in the middle.

## The nuance that ruins the slogan

Here's where results-oriented programming gets dangerously easy to misread. If all that matters is the output, does the code in the middle matter at all? Can it be a sludge of duplication and clever hacks, as long as the tests pass?

No. And the reason is sharper than "good engineers care about craft."

Internal quality — modularity, clear boundaries, security, conventions — still matters, arguably more than before. But the *reason* why it matters has shifted, and so has the audience. We used to keep code clean for the humans who'd read it next. Increasingly, the next reader is an agent. Maintainability is drifting from maintainability-for-humans to maintainability-for-agents. A model produces better results, more reliably, in a codebase with clean seams, honest names, and tight modules — for roughly the same reasons a human does: less context to hold, fewer ways to go wrong, clearer places to make a change. Messy internals don't just offend taste; they degrade the very results you're optimizing for, just on a delay. The bad price you ship next quarter is often paid for by the tangle you let the model leave behind in this one.

So results-orientation isn't "internal quality doesn't matter." It's "internal quality matters *because of* its effect on results, not as an end you inspect for its own sake." That's a shift of priority and framing, not a license to abandon it. You stop reviewing the diff for elegance. You don't stop caring whether the system stays workable — you just hold that bar through different means: linters, architecture tests, conventions encoded where the agent will actually see them.

## Where this is heading

Follow the line far enough and the job starts to look different.

If verification lives at the boundary, and internal quality is encoded as rules the agent has to respect, then the thing you're really authoring is no longer the implementation at all. It's an *objective* plus a set of *constraints*: the result you want, and the rules the system must stay inside while reaching it — the stack, the business rules, the security requirements, the conventions, the working definition of "good." Then you hand that to a model inside a good harness and let it optimize toward the objective without stepping outside the constraints.

That's the logical endpoint of results-oriented programming: you specify the target and the guardrails, and the model searches the path. Your leverage stops being the code you write and becomes the quality of the objective you define and the harness you put around it — the tests, the evals, the judges, the rules, the checkpoints. Get those wrong and a capable model optimizes confidently toward the wrong thing. Get them right and you've built something that improves the result without you touching the middle.

Which is why I don't think "results-oriented" means "lazy." It means the hard part moved. It used to live in the writing. Now it lives in defining — precisely enough that a machine can be held to it — what you actually wanted, and in building the apparatus that holds it there. The path got cheap. Saying what "right" means got more important than ever.

---

*A companion to [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know), which ran into this same idea from the angle of delegation and responsibility.*
