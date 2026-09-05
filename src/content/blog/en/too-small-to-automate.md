---
title: "Too Small to Automate"
description: "The work that never gets automated isn't the hard work. It's the batch of a hundred and fifty rows that sits just below the line where writing the script pays for itself — and that line moved twice, in opposite directions, while nobody recalculated where it is."
pubDate: 2026-09-13
tags: ["AI", "Automation", "Productivity", "Engineering", "Tooling"]
lang: en
translationKey: too-small-to-automate
linkedinLinks:
  - label: "Prompt Scripter"
    url: "https://promptscripter.javieraguilar.ai"
---

I keep a mental folder of things I never automated. The hard ones aren't in it. Hard problems got scripts years ago, because a hard problem is interesting and a script is a good excuse to solve it.

What's in the folder is small. A hundred and fifty short descriptions that each need one judgement call. A column of free text that needs rewriting in a house voice. Ninety somethings, one decision each, none of them difficult.

I know how to automate every item in that folder. I've known for years. That's the part worth explaining.

Sort the folder by tedium and nothing lines up — the jobs that did get scripted, years ago, were exactly as tedious as the ones that didn't. What sorts it is size, and the cut is sharper than it has any right to be: the big tedious jobs all got automated, the medium ones never did, and the boundary between them sits somewhere I've never actually calculated. **The work that never gets automated isn't the hard work. It's the work sitting just below the line where writing the script pays for itself.** That line is the one thing here nobody recalculates, and it has moved twice since most of us last looked.

## The arithmetic everyone half-remembers

The version in most people's heads is the one from the famous xkcd table: automate when the time you'll save exceeds the time it takes to build. Total manual cost is rows times seconds; total automated cost is the build, plus a much smaller per-row cost. Cross the line, write the script.

It's a good rule and it has a hole in it. The formula has three terms, not two:

- **Build.** Writing the thing.
- **Run.** Executing it, per row.
- **Check.** Establishing that the output is right, per row.

For the automation most engineers grew up with, the third term was invisible, and invisible for a good reason: it was genuinely near zero. A script that renames files by a rule either implements the rule or doesn't. You inspect three outputs, convince yourself the rule is right, and the other three hundred are correct by construction. Determinism means you verify the *program*, once, not the *output*, N times.

So we all learned a two-term formula, from a world where the third term rounded to nothing. Then the third term stopped rounding to nothing, and we kept using the formula.

## What changed, and it changed twice

**Build got cheap.** This is the part everyone noticed. A coding agent writes the CSV loop faster than you can specify it. The build term, which used to be the whole argument, collapsed. On its own, that pushes the threshold down: more things are worth automating than were before, and there's real work sitting in that gap.

**And a new class of task walked into the band.** This is the part that matters more, and it gets discussed less. It's the per-row work where the operation is a judgement. Does this message describe a billing problem or a login problem. Is this clause unusual for a contract of this type. Rewrite this in our tone without inventing a claim. Summarise this in one line that a non-specialist would understand.

What arrived late isn't the capability — it's a cheap, ordinary way to point it at a list: something you can reach without an integration, a budget line or anyone's sign-off. Which is why nobody has a habit for the category. For most people it never had an automated form worth reaching for; it was either a person, or a project nobody was going to fund. You never needed a threshold rule for it, so you never built one, and now the tasks are arriving and the rule is missing.

## The one term that didn't get cheaper

Here is where the two changes point in opposite directions.

The tasks that just became automatable are exactly the ones whose acceptance criterion is fuzzy. There's no assertion for *does this read right*. There's no unit test for *is this the correct category, given a taxonomy that lives partly in someone's head*. Which means the check term does not collapse the way the build term did. It stays roughly linear in the number of rows, with a human-sized constant.

|  | build once | run per row | check per row |
|---|---|---|---|
| Deterministic script, 2019 | hours | ~0 | ~0 — verify the program |
| Deterministic script, 2026 | minutes | ~0 | ~0 — verify the program |
| Per-row model judgement | minutes | seconds, plus tokens | the whole job |

That table is structure, not measurement — I haven't timed any of it and I'm not going to pretend otherwise. But the shape is the argument. Automation used to move work from *doing* to *building*. For fuzzy per-row work it moves it from *doing* to *checking*, and checking is the term that doesn't parallelise, doesn't amortise, and doesn't get delegated. It's the same resource I've argued is the real currency in [build-versus-buy decisions](/en/blog/build-vs-buy-attention): your attention, which is the one input that didn't get cheaper when everything else did.

This is also why the naive update — *building is free now, so automate everything* — produces bad decisions. It optimises the term that already collapsed and ignores the one that's now binding. I've had to make [the same correction in how I review agent output](/en/blog/results-oriented-programming): the question stopped being *is the implementation right* and became *is the result right*, and those cost wildly different amounts to answer.

## Why the script is more expensive than the script

I have a stake in the three costs below, and you should discount them accordingly.

There's a second reason the band is wider than the formula suggests, and it's the one a technical reader will resist, because from the inside it looks like an excuse.

"I'd do that in twenty lines of Python." True. But the twenty lines aren't the cost.

**The account is a cost.** To run rows through a model from a script you need an API key, a choice of provider, and a bill that meters tokens. At home that's a payment method and a spend limit to set up for an afternoon's work. At work it's a procurement conversation, and if you don't control what you're allowed to use, it may be a conversation you can't win. I've written about [what changes when the tool isn't your choice](/en/blog/the-tool-youre-allowed-to-use); this is one of the places it bites hardest, because the blocker isn't technical and no amount of engineering removes it.

**The prompt is a cost, and it's not where you think.** The prompt that actually works is not the one you'd write into a file. It's the one you arrived at after six rounds of correcting it in a chat window, watching an output, noticing it drifted, tightening one clause. That loop is the reason it works. Freezing it into a script means committing to it at the exact moment you're least sure it's right — and the thing the script removes is precisely the loop that got you there.

**The output shape is a cost.** A script wants structured output it can write to a file. Which means you're now specifying JSON schemas and handling parse failures and deciding what to do with row 90, and you have added a serialisation problem to a task that didn't have one, because the actual consumer of those hundred and fifty answers is a person who was going to read them.

Add those up and the honest build term for a fuzzy hundred-and-fifty-row job isn't the twenty lines. It's a decision you may not be authorised to make, a prompt you have to commit to while you're still editing it, and a serialisation problem you invented on the way. That's why the folder exists.

## What the band actually wants

Given that shape, the interesting question isn't *how do I build the pipeline faster*. It's *what does this band want, if it isn't a pipeline*.

It wants the repetition removed without the loop being closed. That's one property, not a list of features: whatever does the repeating has to leave the judgement exactly where it already is, still watching output as it arrives, still able to stop at row thirty because row thirty revealed the prompt was wrong. Anything that keeps the check that cheap qualifies. What fails is any arrangement that collects the output for review afterwards, because that's the arrangement that makes you commit to the whole run before you know the prompt is right.

That's a smaller ambition than a pipeline and it's the correct one for the band. A pipeline is the right answer once the job repeats forever, and it earns its retries, logging and resumability then. Below that, [the same argument I made about exploratory versus scripted browser testing](/en/blog/playwright-cli-vs-scripts-ai-agents) applies: the script is the right artefact when you'll run it many times and the criterion is stable, and the wrong one when you're still discovering what correct means.

I built a thing that does exactly this: **Prompt Scripter runs one prompt over a list of rows inside the chat you already use — ChatGPT, Claude or Gemini. No API key of your own and no token bill: the model call happens in the session you already pay for.** That's the whole of the pitch and I'm not going to dress it up. It's a Chrome extension, it's new, and it has an account of its own — which is a cost too, just not an API key. And when you're signed in, your rows travel over HTTPS to a server of mine to open the run. The dataset record it creates keeps only the row count and the column names — but each row's input and the model's answer to it are stored, as the results of that run, which is exactly what the account export is built out of. In a piece whose whole position is precision it would be cheap of me to leave that out, and I got it wrong myself once before checking the second route. I have no measurement of time saved, so I'm not claiming one. The argument above is the reason I built it. If the argument is wrong, the tool is wrong too, and you should say so.

## Where I'd still write the script

The threshold moving doesn't mean it disappeared. Four places where the pipeline is straightforwardly the better answer:

- **When the job repeats on a schedule.** Amortisation is real. Weekly forever beats any interactive loop, and the build cost gets divided by every future run.
- **When the output feeds a system, not a person.** If row 90's answer lands in a database, you need schemas, validation and a retry policy, and a chat window is a bad place to get any of the three.
- **When the judgement is actually deterministic.** A surprising amount of "the model should decide" is a rule you haven't written down yet. Write the regex. It's faster, free, and you can test it.
- **When N is genuinely large.** At some scale the per-row check has to become sampling and statistics rather than reading, and once you're sampling you want the infrastructure that makes sampling meaningful.

And the boundary at the other end, which matters just as much: **at some small number of rows, do it by hand.** Templating the prompt, splitting the columns and deciding what a header row means is setup, and setup is paid once whether the list is thirty rows or three hundred — so there is a length below which the setup *is* the job. I haven't measured where that falls and it will move with the task, but the criterion is easy to apply: if you'd have finished the list before you'd finished describing it, describing it was the wrong move. The band has a floor as well as a ceiling, and forgetting the floor is how people end up automating something they'd have finished in ten minutes.

## Limits

I want to be exact about what this argument does and doesn't rest on.

It rests on structure, not data. I haven't measured build time, check time or throughput for anything described here, and the table above is a shape, not a result. When I do have numbers I say so and I show the ones that got smaller as well as the ones that got bigger — that's what happened when [I measured what prescriptive scaffolding actually buys](/en/blog/the-scaffolding-you-pay-for), and the honest version was less flattering than the hunch. This piece has no equivalent measurement behind it, so read it as reasoning you can check against your own folder rather than as a finding.

It also assumes the check term is real, which is only true if you actually check. If nobody reads the hundred and fifty outputs, the argument collapses — but so does the value of the work, and [that failure is quieter than people expect](/en/blog/nobody-will-check-behind-you).

## The question that sorts the folder

The row count turns out to be the wrong first question. Before writing anything, I ask what I'd have to read to know it worked.

If the answer is "three outputs and then I trust the rule", it's a deterministic job. Write the script. The check term is near zero and the arithmetic everybody half-remembers is the right arithmetic.

If the answer is "all of it", it isn't a pipeline problem. It's a queue, and the only part of a queue worth removing is the part that isn't reading.

That's what my folder turned out to be, almost all of it. I'd guess yours is the same.

---

*Related: [attention as the real currency in build-versus-buy](/en/blog/build-vs-buy-attention), [verifying results instead of implementations](/en/blog/results-oriented-programming), [when a script beats interactive exploration](/en/blog/playwright-cli-vs-scripts-ai-agents), and [why a conversational wrapper around a fixed sequence is just an expensive form](/en/blog/expensive-form).*
