---
title: "The Only Software You Need Is a Subscription"
description: "Agents made building almost free, which exposed what you were actually buying all along — not the software, but the maintenance, the de-risking, and your attention. A build-vs-buy calculus rewritten around the one resource that doesn't parallelize."
pubDate: 2026-06-30
tags: ["AI", "Agents", "Software", "Engineering", "Automation"]
lang: en
translationKey: build-vs-buy-attention
heroImage: "/blog/build-vs-buy-attention.png"
publishToDevto: true
---
There's a small piece of software I use every day that doesn't exist as a product. It watches my calendars — personal, work, the consulting one — and copies the busy blocks across all of them, so that anyone looking at any single calendar sees when I'm actually blocked, even when the block lives somewhere else. Paid tools do exactly this. I looked at them, then spent an evening with Claude Code writing a script and a routine that runs on a schedule. It's been running quietly for months. I barely remember it's there.

That last sentence is the whole article, but let me get there slowly.

Because the tempting conclusion right now — the one the moment keeps pushing you toward — is the maximalist one: with agents like Claude Code and Codex, building almost anything is suddenly within reach, so why pay for anything? Taken to its limit, the only software you need is a subscription to Claude or ChatGPT, and everything else you just *build*. There's enough truth in that to be dangerous, which is exactly why it's worth slowing down on.

## What getting cheap actually reveals

It's easy to read the agent moment as "building got cheap" and stop there. True, but not the interesting part. The interesting part is what cheap building *exposes* — because buy vs build was never really a contest about the cost of building.

When you paid for software, the price tag was mostly not for the code. The code was the least of it. What you were buying was three things the code quietly carried:

- **Someone else absorbs the maintenance.** The thing keeps working when an API changes, when an edge case shows up, when the platform shifts under it. That liability is the provider's, not yours — forever, or until you cancel.
- **Someone else already paid the trial-and-error tax.** A built product has been through the loop of "this looked right and wasn't" hundreds of times before it reached you. You skip that. You buy the far side of a learning curve.
- **It doesn't cost you your attention.** This is the one that matters most and gets named least.

Agents collapsed the first cost everyone talks about — the writing — and in doing so they pulled the curtain back on the other three. The bill you were paying was never really for the software. It was for not having to care about it.

## The resource that doesn't parallelize

Of those three, attention is the one I keep coming back to, because it behaves differently from the rest.

Time, agents genuinely give back. You can fan five of them out at once and compress a week of work into an afternoon — I've [written before about what that does and doesn't buy you](/en/blog/human-limits-managing-ai-agents). But attention isn't time. You can run five agents in parallel; you cannot *attend to* five things in parallel. Every tool you build is a small standing claim on your attention — a thing that can break, drift, surprise you, and quietly ask to be looked at. Build enough of them and you haven't bought yourself freedom; you've appointed yourself the on-call engineer for a sprawl of one-person software nobody else can page for.

So the real build-vs-buy question, now that code is nearly free, isn't "can I build this?" The answer is almost always yes. It's: **who ends up holding the maintenance, and who ends up holding my attention?**

## When I build anyway

Framed that way, two situations make building the obvious call.

**When it's trivial and then goes silent.** The calendar sync is the clean case. I built it once, it runs on a schedule, and it makes no further claim on me. The attention cost was a single evening and then approximately zero. This is the sweet spot the maximalists are actually right about: small, well-scoped, set-and-forget. When something can be built quickly and then left to run without watching, building wins easily — you skip the subscription and you pay almost nothing in the currency that's actually scarce.

**When nothing on the market fits well enough.** [VitaminD Explorer](/en/blog/from-artifact-to-pwa-vitamind) — my solar vitamin-D calculator — started as a Claude artifact and grew into a real PWA precisely because what I wanted didn't exist in a form I'd have paid for. When the market's answer is "close, but not the thing," the build/buy math stops being about cost at all. You're not undercutting a product; you're filling a gap a product never filled.

Notice that neither of these is "build because building is free." Free is the *precondition* that puts building on the table. It isn't the reason.

## The trap, and the limits

The flip side is where the maximalist position quietly breaks.

The trap is everything that *doesn't* go silent. A tool that needs babysitting, that breaks in ways you can't predict, that demands a decision every time something upstream moves — that's not a saving, it's a second job you assigned yourself. Here the provider's offer is honest and worth taking: pay us and the maintenance, the drift, the 3 a.m. failure mode become *our* problem. For anything that would otherwise sit on your attention indefinitely, that's often the better deal even when you could build it in a weekend. *Could* and *should* part company exactly here.

And then there are the plain limits that the "just a subscription" framing waves away. Usage ceilings are real. Some things genuinely shouldn't run unattended, no matter how capable the agent — anything with money, identity, or irreversible consequences on the other end wants a human in the loop, which means it never fully leaves your attention. The reductio — *the only software you need is a subscription* — is a useful provocation and a bad operating plan. The subscription is the workshop, not the warehouse.

## Same logic, at company scale

This isn't only a personal calculus, and the enterprise version is the part that's been talked to death — "the death of SaaS," every company becoming a software company, the great unbundling. I don't have much to add to that discourse except to point out that the axis it usually argues over is the wrong one. The debate fixates on cost and capability: now that we *can* build internal tools cheaply, should we stop buying SaaS? But the deciding variable is the same one as in the personal case — attention, just spread across a team instead of a person.

I've built internal monitoring systems that run on their own, watching logs and doing automated performance and code-quality reviews. Tools like that absolutely exist on the market. The reason to build wasn't a gap — it was a thin layer of customization the off-the-shelf option couldn't match cheaply, on top of something that, once built, mostly runs itself. Low standing attention cost, modest effort, a fit you couldn't buy: the *personal* sweet spot, scaled up.

The same trap scales up too. A company can build something that it then has to staff forever, pulling a team off the actual line of business to babysit internal software — which is just the on-call sprawl problem with a payroll attached. The question a company should ask isn't "can we build this instead of buying it?" It's the same two questions: **who carries the maintenance, and whose attention does it spend?** A dedicated internal-tools team is sometimes exactly the right answer to that — and sometimes it's the most expensive way a company ever learned it should have just bought the thing.

## Where I land

I build by default now, more than I used to, and I'm not embarrassed about it. Code got cheap; that genuinely changed the math. But the version of "build everything" worth holding is narrower than the slogan: build the things that are trivial enough to leave running, or that the market never built for you — and *especially* the ones that, once built, go quiet and stop asking for you.

For everything else, the most useful thing a paid tool sells isn't the software. It's the right to stop paying attention. That's a real product, and some days it's the only one worth buying.

---

*A companion to [Human Limits in Managing AI Agents](/en/blog/human-limits-managing-ai-agents) and [Results-Oriented Programming](/en/blog/results-oriented-programming). VitaminD Explorer lives at [getvitamind.app](https://getvitamind.app).*