---
title: "It Takes a Product to Send Messages"
description: "The work that never gets automated isn't the hard work. It's repetitive work that needs a judgement on every row — already being done by hand, inside a chat window. And every way out of doing it by hand asks you to build a product first: an account with a token bill, a prompt you now have to test call by paid call, and an interface for whoever reads the results."
pubDate: 2026-09-14
tags: ["AI", "Automation", "LLM", "Tooling", "Product"]
lang: en
translationKey: too-small-to-automate
heroImage: "/blog/too-small-to-automate.png"
linkedinImage: "/blog/too-small-run-in-chat.png"
linkedinLinks:
  - label: "Prompt Scripter — Chrome Web Store"
    url: "https://chromewebstore.google.com/detail/aamjoicocabhfkomhejfkmnkjkdomadg"
  - label: "Prompt Scripter"
    url: "https://promptscripter.javieraguilar.ai"
---

A hundred and fifty support messages, each needing one call: billing problem or login problem. Ninety free-text fields to rewrite in the house voice without inventing a claim. Forty markets to size: the same question about software in Spain, then about biotech in Portugal, then logistics in France, forty times over — same wording every time, two words swapped. The work repeats, and every row needs a judgement, which is why it is already being done inside a chat window — one message at a time, by a person who reads each answer as it lands and would notice at row thirty if the wording had drifted.

Almost nobody automates that. Not because it's hard.

## Two things called hard

Two different difficulties share a word, and the argument dies if you let them merge. One is intellectual: the problem you don't yet know how to solve. That is the one that genuinely resists a script, because you cannot write down a procedure you don't have — and it's also the one that gets attention, because it's interesting to work on.

The work above is the other thing entirely. Each row is easy: one decision, two seconds, obvious to anyone who knows the domain. What makes it unbearable is that there are a hundred and fifty of them and a person has to be present for all of them. Nothing about it is difficult. It's repetitive *and* it needs judgement, and it's the pair that strands it — remove either half and it would have been dealt with years ago.

I've argued before that when a team copies context into a chat and carries the answer back, [the person is the integration layer](/en/blog/stop-being-the-cable). The fix there is usually a connector nobody remembered to ask permission for. Here there's nothing to install, because the thing being repeated isn't a system call. It's a message.

## The disproportion

So why does it stay manual? Because of what you're asked to build in exchange. The work is: paste a row into a chat, read the answer, paste the next one. The moment you want to stop doing that with your hands, every available exit walks you out of the chat and hands you a product to build. A provider account, an API key and a bill metered by the token. A prompt that now has to be tested the way code is tested, except each test is a paid call and there's no green tick waiting at the end. And an output that a person has to read, which means a presentation, which means an interface with rows, pagination and a login in front of it.

That's a product. To send messages in a chat.

The arithmetic most of us carry around is [xkcd's table](https://xkcd.com/1205/), *Is It Worth the Time?* — how long you can spend automating something before you spend more than you save. It's a good table and nothing here contradicts it. It just prices the one term that has already collapsed. Writing the loop isn't the problem; a coding agent writes it faster than you can specify it, which is most of what I mean when I say [building is no longer the bottleneck](/en/blog/building-is-no-longer-the-bottleneck). The three costs above survive that untouched, and not one of them is code.

## What I built instead

[Prompt Scripter](https://promptscripter.javieraguilar.ai) — [on the Chrome Web Store](https://chromewebstore.google.com/detail/aamjoicocabhfkomhejfkmnkjkdomadg) — takes one prompt with placeholders where those two words go — `Analyse the {{ sector }} market in {{ country }}` — and a list of rows, and sends one message per row into the conversation you already have open, in ChatGPT, Claude or Gemini. It waits for each answer to finish before sending the next.

![The Save as Template dialog open over a ChatGPT conversation, turning a market-research prompt into a template with {{ sector }} and {{ country }} as its placeholders](/blog/too-small-save-as-template.png)

The template comes from a message you already sent. There is no separate editor to learn: the prompt you spent six rounds getting right is sitting in the thread, and a button on it turns that message into the template.

The answers then arrive as answers, in the thread, with the platform's own formatting and its own citations — which is the image at the top of this page, and the part that decides whether any of this is worth doing. The answers land in the thread, which is where you were reading them anyway.

The rest of this piece is the three costs it exists to avoid. None of them is the twenty lines of Python.

## The bill you didn't have

To push a row through a model from a script, you need a credential of your own. Pick a provider, add a payment method, keep a key somewhere that isn't the repository — and from then on every row and every retry has a unit price. An afternoon of office work becomes a budget line with somebody watching the spend. At home that's an annoyance; at work it's a procurement conversation, and if you don't control what you're allowed to use, it's one you may not win.

The obvious way to make that bill tolerable is to drop to a cheaper model, and it's the move I'd warn against hardest. I took the same task through progressively weaker models and measured that [the capability was the expensive part](/en/blog/it-was-never-the-restriction): the weakest one never once went and looked, and filed fourteen reports about a release that didn't exist. Cheap tokens on work that needs judgement buy you confident answers nobody checked.

The bill isn't the only thing you take on by leaving. The prompt you refined was refined against a particular model, in a particular conversation, and neither of those is incidental. The platforms have spent two years making that conversation load-bearing: a project holding the documents the task depends on, memory that already knows the house voice you keep asking for, a thread where the last forty answers are still on screen. Go out to an API and all of it drops. What the chat gave you as a setting becomes something you have to engineer — retrieval, a system prompt that reconstructs what the project already knew, and some way of keeping the two in step as the work changes. You left to save an afternoon and inherited a context problem.

The extension sidesteps the line item entirely, because the model call isn't a network call of its own. It types into the page and presses send: the inference is ChatGPT, Claude or Gemini, in your tab, on the subscription you already pay for — the same model, in the same conversation, with whatever project and memory that conversation already has. No key to obtain, no provider to choose, and no context to rebuild. It does have an account of its own, and I'd rather say what that costs: a flat plan with caps on templates, runs and rows rather than a token meter, a loop that runs on a chat page without signing in at all, and — when you are signed in — rows travelling over HTTPS to a server of mine, each row's input and the model's answer stored as that run's results.

## A prompt is code you can't read

Committing a prompt to a file is not the problem. A prompt lives in a repository like anything else and gets edited like anything else; version control is not the part that hurts.

The cost is that a prompt is non-deterministic code, and non-deterministic code isn't checked by reading it. You check it by running it, and a run doesn't come back as an assertion that passed. It comes back as a text somebody has to judge. No red, no green — a person reading outputs and deciding whether they're right, which is the same activity the automation was supposed to remove, relocated into the test suite. And the loop that makes a prompt work in the first place — reword it, cut the sentence that made it verbose, add one example, run it again — is N runs over M cases, every one billed, before the first useful row comes out.

The tempting shortcut is to have another model judge, so the loop closes without you in it. I measured that one: [the same 45 blinded comparisons, three judges, three different rankings](/en/blog/three-judges-three-rankings), each judge preferring its own answers, and on the subjective tasks agreement at roughly chance. On exactly the kind of question this article is about, the judge is a participant rather than an instrument — and [the prompt was always the last 10% anyway](/en/blog/llm-as-judge-three-decisions). The first 90% is deciding what you're measuring, on what, with what in view. That is the product you didn't want to build.

What the extension avoids isn't the testing. It's having to build the test bench somewhere else and pay for its rounds separately. The prompt you automate is the one you already tuned by hand in that same chat, watching real answers, on a flat subscription — there's a button on your own messages that turns one of them into a template. The trial and error happens where it was already happening; the tool picks it up at the end instead of opening a second place to do it.

## Somebody has to read this

Serialising JSON is trivial, and has been for twenty years. The problem is who the JSON is for. The person who has to read a hundred and fifty answers is not going to open an array of objects. They want the input beside the output, to jump to row 90, to reread a long answer without stepping over escaped quotes, and to find it still there tomorrow. That's a view: pairing, pagination, legible text. It's an application. And an application holding other people's rows drags the rest along with it — accounts, permissions, retention.

I've paid that bill. Building a conversational KYC flow, we ended up maintaining [our own interrupt format and a widget registry](/en/blog/ag-ui-third-protocol) by hand, until a standard turned up to do it for us. That's the honest price of presenting a model's output to somebody who isn't you.

The extension builds none of it, because the output appears where the reading was already happening: answers arrive in the thread as ordinary messages, with the platform's own formatting — headings, lists, code blocks, copy button. No screen had to be designed, because the screen was already there. There's a CSV export on the server for when you want the file. There is no screen, because the screen was already there.

## Where the script is still right

None of this abolishes the threshold; it just isn't the point, so here it is briefly. Write the pipeline when the job runs on a schedule forever and the build cost gets divided by every future run. Write it when the output feeds a system rather than a person, because then you genuinely do want schemas, validation and a retry policy. Write it when the judgement turns out to be deterministic after all — a surprising amount of "the model should decide" is a rule nobody has written down yet, and the regex is faster and free. And write it when N is large enough that checking becomes sampling rather than reading.

There's a floor as well as a ceiling, and the floor gets forgotten more often: below some number of rows, describing the job *is* the job. If you'd have finished the list before you finished explaining it, you should have finished the list.

## The direction

What I keep noticing is that all the available exits point outward. The work happens in a chat, and every way to stop doing it by hand proposes a new destination: a console, a dashboard, a platform with its own login, its own bill and its own tab in somebody's browser. I've made the opposite argument about products in general — [put your app inside the agent your users already have](/en/blog/bring-your-app-to-the-agent) instead of asking them to come to you — and this is that argument turned inward, at your own work. If the job lives in the chat, the automation belongs in the chat.

Prompt Scripter is that argument with a build attached. The disproportion above is the whole reason it exists; if the disproportion isn't real, neither is the tool, and I'd rather be told.

Here's the test I'd apply to your own version of that pile of work. Write down what you'd have to build to stop doing it by hand. If the list comes out as a provider account, a test bench and an interface — and the job is sending messages in a chat — the list is the argument.

---

*Related: [the person as integration layer](/en/blog/stop-being-the-cable), [what an LLM judge actually costs](/en/blog/three-judges-three-rankings), [what building the reference costs](/en/blog/the-instrument-fails-in-your-favour), and [putting your app inside the agent](/en/blog/bring-your-app-to-the-agent). [Prompt Scripter](https://promptscripter.javieraguilar.ai) is on the [Chrome Web Store](https://chromewebstore.google.com/detail/aamjoicocabhfkomhejfkmnkjkdomadg).*
