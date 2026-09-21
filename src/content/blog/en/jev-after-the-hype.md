---
title: "Jev: what survives the hype"
description: "I tested Jev for fraud detection, invoice checking and my work with coding agents. What helped, what did not, and why some improvements cannot reach production."
pubDate: 2026-09-22
tags: ["AI", "Evaluation", "Agents", "Architecture"]
lang: en
translationKey: jev-after-the-hype
heroImage: "/blog/jev-after-the-hype.png"
linkedinLinks:
  - label: "Jev / TypeSafe"
    url: "https://docs.typesafe.ai/"
---

In one of the systems I work on, a model reads invoices and extracts prices, amounts and other fields. I then need to check something much smaller: **is that value actually in the invoice?** I do not need another model to write a report. I need a decision.

That is the gap [Jev, from TypeSafe](https://docs.typesafe.ai/introduction), fits into. I give it information and a question with bounded answers; it returns a category, a score or a probability. The promise is to make those decisions much faster and more cheaply than a large generative model.

Jev has just launched and attracted plenty of hype. I wanted to see how much survived testing it on things I actually do. I have used it at three levels: my work with agents, the products I develop, and the environments where I would have to deploy it. Each has exposed a different boundary.

![Where I tested Jev: my work with agents, product decisions, and environments with data restrictions.](/blog/jev-after-the-hype-levels-en.png)

## Personal: helping me work with agents

When I use Claude Code or Codex, different tasks need different models. Finding a file is different from reviewing an authentication change. There are also decisions before running commands: reading a file, deleting data and deploying an application have different consequences.

In Claude Code, I have connected Jev to both points. It recommends a model tier for a task and assesses command risk. I run it **in shadow mode**: it records what it would recommend, while the actual decision stays with the agent and me.

In an initial test with invented tasks, it distinguished clear examples well: searches and mechanical edits on one side, architecture or security work on the other. The queries cost a fraction of a cent. That lets me collect recommendations cheaply; finding out whether cheaper models are worthwhile also requires measuring whether they finish the work correctly and how often it needs to be repeated.

In Codex, I ran a comparison using actual agent work on a test project: fixing a pagination bug and a discount calculation. I ran each task with the same model, once with Jev and once without it. For the Jev version, I connected it as a tool that Codex consulted before using the terminal.

**Codex solved both tasks correctly in both conditions.** But in these runs, consulting Jev took roughly twice as long. The Jev requests cost a fraction of a cent; the additional work came from the exchanges the agent needed to request and read each assessment.

It is a small test, but it gave me a concrete result: adding an opinion before every read or test did not improve those fixes, and it made them slower. That integration is useful for experimentation; it has not yet improved that workflow for me.

The distinction between those uses matters to me. Choosing the right model can save an expensive task. Consulting a model before every step adds work even when the answer was obvious. For now, I see more value in reserving Jev for decisions that change what I am about to do.

## Product: detecting deception and checking data

### SMS: telling a legitimate notification from a scam

One of the systems I work on analyzes SMS messages for fraud: messages impersonating an organization to get someone to open a link, disclose credentials or make a payment.

I tested the Jev integration with **80 Spanish messages**, mixing legitimate messages and scams. The complete system correctly classified **78 of those 80**. Both mistakes were scams it missed; it did not flag any legitimate message in the test as fraud.

Reviewing the two misses showed me where to improve. One message fell just below the alert threshold when the scores were combined. The other went back to the previous detector because Jev's answer was not certain enough, and that detector missed it. The test pointed me toward two concrete changes: how I combine Jev's assessment with the other signals, and how I review uncertain messages.

### Invoices: checking is different from asking “are you sure?”

For invoices, I wanted to know whether Jev could find errors in another model's extracted data. I supplied the invoice text and the values I wanted checked.

That check was much more useful than the confidence reported by the extractor itself. I found incorrect values, or values absent from the document, that the extractor had assigned very high confidence. Comparing them against the text, Jev flagged many of those problems.

The limit was what I meant by an “error.” A field can be correct even if the extractor normalizes its format or combines information from several parts of the document. In the initial test, roughly half of Jev's alerts were false alarms. Refining what it should check made the review more useful.

I see a useful component here: an inexpensive second reader that flags suspicious fields for review. I would not treat every flagged field as incorrect.

### Email: deciding when expensive analysis is necessary

For email, I already had a second review with Sonnet for suspicious messages. I tried placing Jev before it: let Jev settle clear cases and leave uncertain ones to Sonnet.

On the evaluation set, Jev resolved **56% of emails** without needing that second call. I observed no errors in the cases it handled on its own. The estimated cost of that stage fell from about **\$11.90 to \$5.30 per thousand emails**.

![With Jev resolving clear cases and Sonnet reviewing the rest, the estimated cost of email analysis falls to less than half.](/blog/jev-after-the-hype-cost-en.png)

I can connect that saving to a specific decision: avoiding expensive calls that are unnecessary. The test included reconstructed attacks, so it supports an evaluation on live traffic rather than a claim that it will catch every new campaign.

I also tested Jev for reviewing suspicious transactions. In a test with twenty simulated frauds, it detected seventeen, the same ones as Haiku, and produced the same false alarms on legitimate transactions. It did so faster and more cheaply. That is promising for a second opinion, with the obvious limitation that the frauds were simulated.

### Where it did not add enough

Not everything that looks like classification improves when I add Jev.

I tested it for selecting the correct material among catalog candidates, and it recovered none of the human corrections I was looking for. On fraudulent domains with a single changed letter, it missed cases the previous model detected. When selecting chatbot tools, ambiguous tool descriptions still led to wrong choices.

I also evaluated whether it could decide which user feedback should become a ticket. Creating an unnecessary ticket is annoying; discarding a real problem can make it invisible. The test did not contain enough examples of that second risk. I am interested in using it to propose tickets, but I lack evidence to let it discard reports automatically.

My reading is concrete: it works better when I provide the necessary evidence and well-defined options. If the catalog is ambiguous or information is missing, an inexpensive model still faces a poorly specified problem.

## Infrastructure: cases that work but I still cannot deploy

My [industry classification service](/en/projects/compliance-classifier) investigates what a company does and assigns it a category. That process contains several classification and source-verification steps where I tested Jev. My experience was that it produced results equivalent to GPT‑5.6 Luna, faster and more cheaply.

Data policy nevertheless limited adoption. I encountered something similar in the industrial pilots: the client's environment required an approved route through Azure Foundry, and the integration I was testing did not meet that requirement.

That boundary is easy to forget while looking at a results table. I can establish that a model performs a task well and still be unable to send it the data it would need.

[TypeSafe's privacy policy](https://typesafe.ai/legal/privacy-policy) says the service is hosted in the United States. It offers a [data processing agreement](https://typesafe.ai/legal/data-processing), commits to [not training on customer data without consent](https://typesafe.ai/legal/mca), and provides [zero retention for enterprise customers](https://docs.typesafe.ai/legal). None replaces a requirement to process data in a particular region or through an approved provider.

Using OpenRouter does not resolve that by itself either: I need to check the [terms of the provider processing the request](https://openrouter.ai/docs/guides/privacy/provider-logging).

Other limits can be addressed in the design. If I need to add amounts or compare dates, I do it in code. Jev is intended for judgments about text, and its own documentation warns about [difficulties with arithmetic, irrelevant context and adversarial instructions](https://docs.typesafe.ai/model-jaggedness/jev-1.13). I give it only what it needs and keep an alternative for failures or answers that are not clear enough.

## What remains of the hype

**Jev has not changed my life, but it has made parts of my work faster and cheaper.**

I am left with a useful tool for some small decisions I was paying a large model to make. Document verification and filtering before an expensive analysis are the most convincing cases for me. In my work with agents, I am still finding where the extra query pays off.

My bet is that OpenAI, Anthropic, Google or others will eventually offer comparable *one-shot* classification models. It would make sense to me: many applications need to choose among a few options quickly and cheaply.

If they appear, I want to compare them on these same decisions. What I want to keep is the questions, the tests and the criteria for deciding when to trust an answer. Jev has passed some of those tests. In others, I prefer what I already had, and in some the limit comes from the environment I work in.
