---
title: "Demos That Wow vs Demos That Work"
description: "Two philosophies of the client demo — mock-first spectacle vs functional proof-of-concept — and why, with AI, the prettier one hides exactly what matters: latency and non-determinism."
pubDate: 2026-06-17
tags: ["AI", "Product", "Engineering", "Demos"]
lang: en
translationKey: demos-that-wow-vs-demos-that-work
heroImage: "/blog/demos-that-wow-vs-demos-that-work.png"
---

I've worked on two teams with opposite philosophies of how to demo to a client, and I still go back and forth on which one is right.

One builds demos for **impact**. Everything is mocked: the screens are polished, the flow is choreographed, and the result that lands on screen is the best possible version of itself. The backend isn't really doing the work — and crucially, the AI isn't really being called. It's a beautiful film of the product.

The other builds **functional proof-of-concepts**. As much as possible is real and wired up — real services, real model calls, real data — and then you iterate on top of it. The first version is rougher and less choreographed, but what you're looking at is actually happening.

Both "work" in the sense that both can win a room. They just optimise for different things, and the gap between them gets a lot wider the moment AI is involved.

## The case for the mock

It's easy to be snobby about mocked demos, so let me steelman them first, because the reasons are good ones.

A mock is **fast**. You're not blocked on infrastructure, model access, data pipelines, or the ten unglamorous things that have to exist before a real flow runs end to end. You can demo a product that doesn't exist yet.

A mock is **controlled**. Demos fail in stupid, memorable ways — a timeout, a rate limit, a model having a bad day in front of the one person you needed to impress. A mock removes that variance. The story you rehearsed is the story they see.

And a mock sells the **vision**, not the current state. Early on, what you're really validating is desire: do people *want* this? A crisp mock answers that question without you having to build the thing first. For a non-technical stakeholder deciding whether to fund the next phase, a polished mock can be exactly the right artifact.

None of that is dishonest. It's a legitimate strategy with real upsides.

## The case for the functional PoC

The functional PoC gives up some polish and a lot of control in exchange for one thing: **what you show is true**.

That truth compounds. A functional PoC isn't thrown away after the meeting — it's the first commit of the product. You iterate on it instead of rebuilding from a slide deck. The feedback you get is real feedback, because people are reacting to real behaviour, not to your best-case storyboard. And the hard parts surface *now*, while they're cheap, instead of after a contract is signed and the timeline is fixed.

I've felt this directly. In one live demo, someone asked the assistant about errors that had occurred, and its answer blended what had gone *well* in with what had gone wrong. The person watching reacted on the spot: this needs to be more concise. In the same session, someone asked whether it could do a particular thing that — because of an internal constraint — it simply couldn't. Two concrete pieces of feedback and two new tickets, in the span of one demo. With a mock, you can't even attempt those questions: the script answers what it was scripted to, and nothing real is being tested.

It's slower to first wow. But it never has to walk anything back.

## Where AI widens the gap

For ordinary software, the distance between a mock and the real thing is mostly **polish**: the real version will be a bit slower, a bit less pretty, a few edge cases will misbehave. Manageable.

With AI, the distance is **substance** — because a mock hides the two properties that define how the product will actually feel:

- **Latency.** In a mock, the answer appears instantly (or after a scripted, tasteful little spinner). In reality, the model call takes time — sometimes a second, sometimes ten, sometimes longer if it reasons or chains tool calls. "Instant" is the single easiest thing to fake and one of the hardest to deliver. I've [written before](/en/blog/ag-ui-third-protocol) about a demo where the real fix wasn't UI at all — it was lowering the model's reasoning effort so responses came back in ~1.5s instead of 10–20s. You only discover that when the model is actually in the loop.
- **Non-determinism.** A mock always returns the perfect answer, because someone wrote it. The real model returns *a* answer — usually good, sometimes wrong, occasionally confidently wrong, and different each time. The mock demonstrates a certainty the product doesn't have. Everything I keep harping on about [evaluating LLM outputs](/en/blog/llm-as-judge-three-decisions) exists precisely because real results vary and you have to measure that variance. A mock makes it disappear.

So when you demo AI with a mock, you're not just smoothing over rough edges. You're selling away the two risks the project actually has. The client falls in love with an instant, always-correct assistant, and then the team has to build something that is neither of those by default. That gap doesn't close itself — someone pays for it later, usually in eroded trust during the build.

## So which one?

Honestly, it depends on what you're trying to learn from the demo:

- If you're validating **desire** — "would anyone want this?" — and talking to people who think in outcomes, not architectures, a mock is often the efficient, correct tool. Don't build a backend to answer a marketing question.
- If you're validating **feasibility** — "can we actually build this, and will it feel good?" — a mock answers the wrong question convincingly. That's where you want the real thing wired up.

My own bias leans toward the functional PoC, and it's leaned further the more I work with AI — because with AI the risk lives exactly in what the mock paints over. A functional PoC doesn't have to be ugly or slow to build, either: the [AG-UI demo](/en/blog/ag-ui-third-protocol) I put together recently is real end to end — real model, real latency, real rendered widgets — and it's about a hundred lines. The "real is too expensive to demo" assumption is often less true than it looks.

But I hold it loosely. A mock that honestly sells a vision, followed by a team that closes the gap, is a perfectly good way to build a company. The failure mode isn't mocking — it's mocking the risky parts and then quietly hoping reality will cooperate.

## Or run both

It doesn't have to be binary. I've worked on projects that ran both at once: a **mocked path** to guarantee a clean end-to-end walkthrough — the story you can always tell without something breaking mid-meeting — and the **real system alongside it**, to probe live with different cases. The mock de-risks the narrative; the real part invites the hard questions. You get the controlled wow and the honest feedback in the same session, as long as everyone in the room knows which half is which.

## The question I'd open up

Maybe the real question isn't "mock or functional." It's **which moment you're optimising for**: the signature at the end of the demo, or the trust at the end of the first sprint. Sometimes those point the same way. With AI, more often than I'd like, they don't.

How does your team demo — and have you ever been bitten by the gap between the demo and the thing you shipped? I'd genuinely like to hear it.

---

*Related: [When the Chat Builds Its Own Interface](/en/blog/ag-ui-third-protocol) (a functional demo, end to end) and [LLM-as-Judge Is Three Decisions](/en/blog/llm-as-judge-three-decisions) (on measuring the variance a mock hides).*
