---
title: "Building Is No Longer the Bottleneck"
description: "AI has made software dramatically cheaper to build, but not customers, validation, or attention easier to earn. When another feature is the comfortable option, the hard work begins outside the editor."
pubDate: 2026-09-06
tags: ["AI", "Product", "Distribution", "Entrepreneurship", "Side Projects"]
lang: en
translationKey: building-is-no-longer-the-bottleneck
heroImage: "/blog/building-is-no-longer-the-bottleneck.png"
linkedinLinks:
  - label: "Prompt Scripter"
    url: "https://prompt-scripting-website.vercel.app"
---

It has never been easier to build software. I can describe an idea, ask for a prototype, and have something working before I have fully decided who it is for. With some more effort, that prototype can become an MVP; with much less work than it would have required a few years ago, it can even end up in production.

What I cannot ask AI to do is make somebody want it.

It can help me write outreach, prepare a landing page, or find possible users. But somebody still has to open the message. Somebody has to trust a new tool enough to try it, spend time on it, and tell me which part is useful. And I have to go looking for that person, listen to an answer I may not like, and distinguish a polite compliment from a real signal of value.

AI has compressed build time far more than distribution time. The bottleneck has moved. The problem is that many of us who know how to build — myself included — still behave as though it has not.

## Two clocks no longer moving at the same speed

A new feature used to be expensive enough to force some thought. It had to be designed, programmed, tested, and deployed. Today I can put one agent to work on it while another reviews the edge cases. The distance between “I just thought of this” and “it now exists” has collapsed.

The distance between “it now exists” and “somebody uses it” has not.

Getting ten relevant conversations still means finding ten people, giving them a reason to listen, and fitting into their calendars. A five-minute trial can take days to arrange. A customer does not appear because coverage increased or the onboarding animations improved.

They are two different clocks:

- The building clock has accelerated with AI.
- The human clock — attention, trust, adoption — has barely moved.

That changes what progress means. A full day of coding can produce a great deal of software and no evidence. A twenty-minute conversation can produce no code at all and completely change what is worth building.

## Procrastination that looks like work

When you have little experience selling or distributing, the asymmetry becomes a perfect trap.

Building is comfortable. I know when a task is finished. There is a diff, a new screen, a passing test. Even when something fails, the failure is usually legible: I can reproduce it, isolate it, and fix it. Every session leaves visible proof of progress.

Distribution is ambiguous. I can contact twenty people and hear nothing back. I can show the product and not know whether “this is great” means interest or politeness. I can choose the wrong channel, message, audience, or timing. There is no console telling me which of the four failed.

So it becomes extremely easy to negotiate with myself: before I show it, I will fix this edge case; before I publish it, I will redo the landing page; before I ask for a trial, I will add export; before I sell it, it needs to look more professional.

All of this sounds responsible. All of it creates real work. And all of it can be a sophisticated way to avoid the risk of discovering that nobody needs the thing.

AI makes this avoidance more dangerous because it makes every excuse cheaper. The unnecessary feature used to hurt enough to slow you down. Now you can accumulate them at a speed that feels like momentum.

## VitaminD Explorer: a lot of product is not a lot of validation

I have lived this with [VitaminD Explorer](https://getvitamind.app). It began as a Claude artifact answering a question I had myself and ended up as a six-language PWA with visualisations, weather data, notifications, and an MCP server. [I have already told the story of its growth from prototype to product](/en/blog/from-artifact-to-pwa-vitamind); technically, it is the kind of project that is easy to be proud of.

But every technical improvement answered a question I could solve inside the project. Can I make the calculation more precise? Can I add another visualisation? Can I let an assistant query the app directly? Almost every time, the answer was yes.

The difficult questions were outside it: who comes back tomorrow? What specific problem does it solve for them? How do they discover that it exists? What would have to happen for them to recommend it to somebody else?

No amount of code answers those questions. Building more can even postpone the answer by reinforcing the feeling that the product is not yet “ready” to be exposed.

I do not think the features I added were useless. I think something more uncomfortable: I could not know which ones were valuable until they met real usage. Technical quality and user value are not the same variable, however much more pleasant it is to work on the first.

## Prompt Scripter and the temptation to arrive finished at first contact

It happened again with [Prompt Scripter](https://prompt-scripting-website.vercel.app). The initial idea was fairly narrow: a browser extension for saving prompts as reusable templates and inserting them directly into ChatGPT or Gemini. It solved a recognisable friction for people who repeat tasks with AI and do not want to reconstruct the same prompt in every conversation. There was already something to show.

But one reasonable expansion followed another. Templates gained variables, organisation, import, and export. Then came the ability to run a sequence across several rows or pieces of text. That required tracking each run, counters, and lifecycle states. The product added authentication, monthly limits, a website, a waitlist, and eventually subscriptions and payments. Even the backend and extension ended up separated so they could be deployed and maintained independently.

There is no absurd feature in that list. That is exactly the problem. Every one could be justified technically, and every one moved the product towards a more complete version. But they also postponed the test none of them could replace: putting the extension in front of people who repeat work in ChatGPT or Gemini and seeing whether they actually turned their prompts into templates, came back to use them, and missed the product when it was gone.

When I finally launched Prompt Scripter, the lesson was not that I had built too much in absolute terms. It was that I had tried to answer in advance questions — which limits users would accept, which part deserved payment, which workflow they would repeat — that only usage could answer. The speed of building meant there was always a seemingly close version that justified waiting a little longer.

But first contact with users is not the product's final exam. It is part of the process by which the product is built.

Trying to arrive “finished” at that contact reverses the order. It means deciding alone what matters and then asking the market to confirm the decision. The sensible sequence is to expose a narrower version sooner, watch where friction appears, and use that evidence to decide the next investment.

This does not mean shipping something broken or transferring the basic work to the user. It means distinguishing the quality required for an honest test from the perfection that only delays it. An MVP does not have to do very little; it has to let you learn something specific.

## Value is discovered outside the repository

“Perfect is the enemy of good” is too weak for this problem. Perfection does not merely delay launch. It can push you to perfect the wrong thing.

Without distribution, there is no feedback. Without feedback, the backlog fills with your own intuitions. And when intuitions are so cheap to implement, the product can become more and more complete while becoming less and less informed.

The scarce resource is no longer necessarily the ability to turn an idea into software. It is the ability to discover which idea deserves to become software, for whom, and with what urgency. You discover that by talking, watching, trying to charge, seeing where people leave, and accepting that some hypotheses will not survive contact.

Distribution is not the step after building the product. It is one of the instruments with which you build the right product.

## The rule I am trying to follow now

Opening the editor still feels more natural to me than writing to a possible user. I do not have a formula that removes that discomfort. I do have a question that is beginning to help:

> **Does this task improve the product because somebody gave me a signal, or does it prevent me from having to go out and find that signal?**

Not every feature needs a literal request. Product vision still matters, and users will never articulate some foundational work. But when several consecutive tasks are disconnected from any external observation, I am probably not moving forward. I am staying on the ground where I feel competent.

The discipline, for me, is to alternate the loops. Build enough to learn; distribute enough to know what to build next. Do not let the speed of the first spare me the discomfort of the second.

Because I can now manufacture possibilities almost without limit. The difficult — and valuable — part is choosing among them with evidence.
