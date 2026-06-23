---
title: "How Much Should You Still Know?"
description: "I build systems whose business logic I couldn't recite if you woke me up at 3am. The model holds it for me — and that's fine. The hard question isn't how much you delegate, it's whether you can still tell when the answer is wrong."
pubDate: 2026-06-23
tags: ["AI", "Cognitive Debt", "Claude", "Software", "Engineering"]
lang: en
translationKey: how-much-should-you-still-know
heroImage: "/blog/how-much-should-you-still-know.png"
publishToDevto: true
---

I'm building a [pricing system](/en/projects/steel-pricing-platform) for a client right now, and I have to admit something: I couldn't tell you most of how it prices things.

Not because the code is opaque — I wrote it, or rather Claude and I wrote it. Because the *business logic* is enormous. Prices depend on the client, the material, the origin, and a long tail of extras and exceptions that each have their own rules. There are more of these than I can hold in my head, and they change. Every time I hit a gap — a price whose logic I can't find, a case the documentation doesn't cover — Claude Code and I log it in a "pending data" document. That document gets reviewed and sent to the client.

Here's the part that should bother me more than it does. A few times the client has come back asking me to clarify how something is priced, and to answer I've had to ask Claude first. I'm the external consultant. I don't carry the business knowledge, and honestly I don't think I should try to. Claude has access to all the documentation and is far more reliable at retrieving the right rule than I would be at internalizing the whole thing.

The instinct is to feel guilty about that. I've decided the guilt is mostly aimed at the wrong question.

## Offloading knowledge isn't new, and it isn't automatically debt

We've been outsourcing memory for a long time. Most of us stopped memorizing phone numbers two decades ago. We don't memorize facts we can look up; we remember *where* to look. Psychologists have a name for it — the "Google effect" — and the sky did not fall. Knowing how to find something is itself a kind of knowledge, and it's often the more useful kind.

An LLM is the next rung on that ladder. It doesn't just tell you where the answer lives; it retrieves it, applies it to your specific case, and explains it. For something like a sprawling, client-specific pricing rulebook, that's not a degradation of my work. It's the only sane way to do it. Memorizing thousands of volatile rules that belong to someone else's business would be a waste of the one thing I'm actually paid for.

There's a term going around — "cognitive debt" — borrowed from technical debt, and a much-shared MIT study ("Your Brain on ChatGPT") that measured reduced neural engagement in people who wrote essays with an LLM. It's a useful phrase. But I think it gets applied too broadly. Not all offloading is debt. Buying groceries instead of farming isn't "agricultural debt." The question is never *whether* you delegate knowledge. It's how much, when, and — the part everyone skips — what you remain on the hook for.

## What actually changes: responsibility

A student who delegates their learning to an LLM is only hurting themselves. If they don't understand the essay, the cost lands on them, later, privately. That's a clean trade they're free to make.

I don't have that exit. I'm responsible for a pricing system that will quote real numbers to real customers. If it prices something wrong, "Claude told me" is not an answer I can give the client. The knowledge is delegable. The responsibility is not.

That reframes the whole thing. The question I kept asking myself — *how much of this should I know?* — is the wrong one. The right question is: **do I know enough to answer for it?** And those are very different bars.

## Three questions, and where the line actually falls

So when *is* it enough to just be able to ask in the moment? What should you know without asking? And how deep does that understanding need to go? Let me answer with the pricing system, because the line falls in a specific place.

**The individual data points — ask away.** What's the surcharge for this material from that origin? I will never hold that in my head, and I shouldn't. It's volatile, it's the client's domain, and the model retrieves it more reliably than I would. Being able to ask in the moment is genuinely sufficient here. This is the layer where delegation is not just acceptable but correct.

**The shape of the system — know it without asking.** What *categories* of rules exist, how they compose, which inputs can move a price and which can't, where the dangerous interactions are. I can't recite every surcharge, but I have to know that surcharges-by-origin are a thing that exists, or I won't even know to ask. You can't query a space whose existence you're unaware of. This is the map, and the map is mine to hold.

**Deep enough to catch a wrong answer — and honest about what that means.** This is the real threshold, and it's not about *how much* you know but about *what kind*. Here's where I have to be honest, though: I can't validate every output by hand, and pretending I could would just be a different flavor of dishonesty. I'm not going to compute a price manually, and often I don't even know what the correct price *is* — that's the client's business, not mine. What I can catch directly is the gross stuff: a number that's an order of magnitude off, a rule applied to a case it should never touch, two extras stacking that shouldn't. The basic-logic violations.

The exact application — the part I can't eyeball — doesn't get validated by my judgment at all. It gets validated by *tests*, and by a golden set the client signs off on. That's the move that actually scales: I don't hold the right answer in my head, I hold a *mechanism* that checks it. Validation itself gets delegated — but to something deterministic and auditable, not to vibes. It's part of why programming keeps drifting toward being results-oriented: increasingly you specify and verify the behavior, not the path the model took to produce it.

So the line is a little wider than "can I personally tell it's wrong." It's: **do I have *some* way to catch a wrong answer — my own eye for the crude errors, a test or a golden set for the exact ones?** If I have none of those, I'm not delegating — I'm abdicating. Delegation keeps a human, or a check the human owns, in the loop. Abdication removes both. They look identical right up until the answer is wrong, and then they could not be more different.

## The quiet symptom: documentation only the agents read

Here's where I notice the line getting blurry in my own work. More and more of the knowledge about my systems lives in files written for machines. `CLAUDE.md`. `AGENTS.md`. Skills. And in this project, that "pending data" document — half spec, half question-list, written so the agent and I can navigate a domain neither the client nor I have fully written down anywhere else.

I wrote about this drift from another angle in [Software Is Dissolving Into the Model](/en/blog/software-dissolving-into-the-model): the layer we used to call software is collapsing into instructions on one side and generated output on the other. The flip side of that convenience is this — when documentation is written *for the agent*, who's keeping a map for the humans who remain responsible? It's easy to end up with a system that's beautifully legible to Claude and slowly going dark to everyone accountable for it.

The interesting thing is that my "pending data" document accidentally does the right thing. It's not just context for the agent; it's a human-in-the-loop checkpoint. It forces a moment where a person — me, then the client — has to look at what's missing and decide. That's the pattern worth keeping. The answer to "docs only agents read" probably isn't writing fewer of them. It's deliberately designing the points where a responsible human has to stop and validate, instead of letting the loop close without one.

## The part nobody wants to admit out loud

There's a social layer to all of this that the technical framing skips. Telling you I sometimes ask Claude before answering my own client costs me something. It brushes right up against impostor syndrome — the quiet fear that the moment people see how the sausage is made, they'll decide I'm not the expert they hired.

The strange thing is that transparency is the cure for that feeling, not the trigger. Impostor syndrome grows in the gap between the image you project and how you actually work. Saying out loud "I asked the model and then verified the rule applies" closes that gap. There's nothing left to be found out.

But I won't pretend the cost is imaginary. With some clients you genuinely will come off worse for being open about it — not because you did anything wrong, but because they don't yet understand what good AI use looks like. They hear "I asked Claude" and pattern-match it to "didn't know," when it should pattern-match to "retrieved the authoritative rule and checked it." The irony is sharp: those are often exactly the clients I'm hired to help integrate AI into their own processes. The same gap in understanding that makes transparency risky is the reason the work exists.

That's why the validation line matters here too, not just technically. Transparency isn't confessing "I don't know anything, Claude does it." It's being precise about *what* you delegate and, crucially, that you kept the ability to check it. "I asked Claude and confirmed the rule applies to this case" is a completely different sentence from "I asked Claude." One describes a professional using a tool well. The other describes the thing the client is afraid of. Being able to validate is what makes the honesty defensible — and over time, modeling that distinction is part of how clients learn to tell the two apart.

## Where I've landed

I'm not going to tell you to delegate less. In the pricing project, delegating the business knowledge is the right call, and pretending otherwise would just make me slower and no more trustworthy. The line I'm drawing isn't between "implementation you can offload" and "knowledge you must keep." It's between knowledge you can still *validate* and knowledge you've gone blind to.

Three things I'm actually doing about it:

1. **Hold the map, not the territory.** Don't memorize the data; do know what categories of things exist and how they interact. You can't ask a question about a space you don't know is there.
2. **Treat "can I check this?" as the real test.** Before I let the model own a decision, I ask whether I have a *way* to catch it being wrong — my own eye for the crude errors, a test or golden set for the exact ones. Note that "check" rarely means "compute it myself"; usually it means owning the mechanism that does. If there's no mechanism at all, that's not delegation, and I either build one or don't ship it unattended.
3. **Design the checkpoints, not just the prompts.** When knowledge moves into agent-readable docs, add the human moment back on purpose — a review step, a pending-questions doc, a sign-off — so the loop can't silently close without someone accountable in it.

The honest answer to "how much should you still know?" turns out not to be a quantity at all. It's a capability: enough to know when the answer is wrong. Everything above that line, ask freely. Below it, you're not saving effort — you're just postponing the moment you find out.

There's a more radical version of this idea, where instead of trusting the model's judgment you force it to externalize its reasoning into code you can actually read and test. That's the experiment in the next post — delegation you can audit, line by line.

---

*This is the first of two pieces on delegation and understanding. The next one gets concrete: an experiment in making a model write down its world as verifiable code instead of keeping it in its head. Related reading: [Software Is Dissolving Into the Model](/en/blog/software-dissolving-into-the-model).*
