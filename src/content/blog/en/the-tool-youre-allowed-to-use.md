---
title: "The Tool You're Allowed to Use"
description: "Every piece of advice about working with agents assumes you picked the tool. Plenty of people didn't. Here's what changes when the choice isn't yours — and the argument to make if it partly is."
pubDate: 2026-08-27
tags: ["AI", "Enterprise", "Software", "Engineering", "Tooling"]
lang: en
translationKey: the-tool-youre-allowed-to-use
heroImage: "/blog/the-tool-youre-allowed-to-use.png"
---

Everything I've written about working with agents — [the map](/en/blog/what-you-still-need-to-know-to-ship), [where to start](/en/blog/if-youre-starting-from-zero), [what engineers get wrong](/en/blog/if-you-came-from-engineering) — quietly assumes something that isn't true for a lot of people: that you chose your tool.

I'm freelance. I pick what I use, I change it when something better appears, and the cost of being wrong is mine. That's an unusual position, and writing as though it were universal is a blind spot I'd rather name than have pointed out.

Plenty of people are handed a licence for one thing and told to get on with it. So: what actually changes, and what can you do about it.

## Two situations, and they're not the same problem

**You have some influence over what gets adopted.** Then this is a persuasion problem, and the argument that works isn't the one most people reach for.

**You don't, and won't.** Then it's a working problem, and most of the standard advice needs adjusting rather than following.

## If you can influence it: the objection is rarely price

When a company won't move to a capable agent, the stated reason is usually cost. It's almost never the real one. The real one is that sending company code or customer data to an outside provider feels unacceptable — and until recently that instinct was well founded.

The facts moved, and a lot of people haven't updated. As of now, on the two providers I checked directly:

**Anthropic** states that it does not train models on customer content from its commercial products — the API, Claude for Work, Enterprise, Education. Commercial customers were explicitly kept out of the consumer policy changes. API inputs and outputs are deleted from their backend within 30 days by default, and eligible enterprise customers can get a Zero Data Retention agreement where inputs and outputs aren't stored at all beyond abuse screening.

**OpenAI** states that by default it does not use data from ChatGPT Enterprise, Business, Edu or the API platform — inputs or outputs — to train or improve models. Training on business data requires the customer to opt in explicitly. Zero data retention is available to eligible enterprise customers on supported endpoints.

Two things worth being precise about, because overselling this is how you lose the argument in the room:

**Zero retention doesn't cover everything.** With Anthropic it applies to the Messages and Token Counting APIs, and explicitly not to stateful features like Batch, the Files API, Managed Agents, or the Console. "We have ZDR" is not the same sentence as "nothing is ever stored".

**Default is not the same as guaranteed.** These are contractual and policy commitments that can change, and enforcement of usage policies means some signals are retained regardless. That's a normal vendor risk, the same one you already accept with your cloud provider and your CRM — but it should be argued as managed risk rather than as absence of risk.

The useful reframe for a conversation with whoever says no: **your company already sends its data to third parties.** Email, source control, CI, the CRM, the error tracker. The question was never whether to trust an outside provider — it's whether this one's terms are acceptable, on the same basis you assessed the others. That's a procurement conversation, and it has an answer.

There's a second argument, and it's the one that lands with finance rather than with security: **the licences you already bought are mostly unopened.** Paying for capability nobody uses is the expensive outcome, not the licence price.

## If you can't influence it: what actually changes

Here I'm on thinner ice and I'd rather say so. My recent experience is with capable agents; what I know about working under real constraints is a few years old, from when using AI meant pasting code into a chat window and back — a live version of Stack Overflow — or autocomplete where you were still doing the typing. Both have moved on since, and I'd be guessing about exactly how far.

What I'm reasonably confident about is the shape of it.

**Smaller units of work.** The single biggest difference between a strong agent and a limited assistant is how much you can hand over at once. If the tool loses the thread after a couple of files, the answer isn't to push through — it's to give it work that fits. That's not a worse way to operate; it's the correct way to operate with that tool.

**More scaffolding, built by you.** With a capable agent you can lay rails cheaply: standing instructions, spec files, tooling it can run itself. With less, you carry more of that in your head or in your process. The work doesn't vanish, it relocates — onto you.

**Verification gets more expensive, which makes it more important.** The advice I've given elsewhere — build mechanisms so you don't check by hand — holds regardless. But if your tool can't run its own tests or drive its own browser, someone has to wire that up. It's still worth it. It's just not free.

**The loop survives intact.** Specify, build, check, correct. Nothing about that depends on which tool you hold, and it remains the thing that separates people who ship from people with a long chat history.

**The map survives intact too.** Keys don't belong in code no matter what wrote the code. Data still can't be regenerated. Every one of the thirteen categories is about the software, not the assistant.

So the honest summary is: **the method transfers, the pace doesn't.** Anyone telling you that a constrained setup makes the fundamentals different is selling something.

## The part that isn't fair

There's a real gap opening between people who choose their tools and people who are issued them, and it doesn't track talent at all. Two engineers of identical ability, one with a capable agent and standing permission to use it, one with a limited assistant and a policy against pasting anything into it, will produce visibly different output within a quarter. That difference will get read as a difference in them.

I don't have a fix for that, and I'm suspicious of anyone who claims one — training doesn't close a gap that's structural rather than educational. What I'd say to anyone in the second group is narrower and I think true: **the part of this that's actually a skill is the part you can still build.** Knowing what to ask for, knowing what to check, knowing which categories exist. That travels with you, including to your next job, where the tooling might be someone else's decision made better.

---

*Fourth piece on what building software with agents actually requires, and the one that questions an assumption the first three were making. The others: [the map](/en/blog/what-you-still-need-to-know-to-ship), [starting from zero](/en/blog/if-youre-starting-from-zero), [coming from engineering](/en/blog/if-you-came-from-engineering).*

*Sources for the provider policies, both checked on 2026-08-10: [Anthropic Privacy Center on zero data retention](https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to) and [OpenAI on business data privacy](https://openai.com/business-data/). Policies change — check them yourself before quoting them in a meeting.*
