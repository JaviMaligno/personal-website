---
title: "The memory that was true"
description: "I audited the 35 memories my agent keeps about this project. Three were stale, and none of them had been wrong when written: they described a state that expired on its own. The other 80% can't be checked at all, and that isn't a flaw."
pubDate: 2026-09-20
tags: ["Agents", "Memory", "Context", "Verification"]
lang: en
translationKey: the-memory-that-was-true
heroImage: "/blog/the-memory-that-was-true.png"
repoUrl: "https://github.com/JaviMaligno/personal-website/tree/main/scripts/memory-audit"
---

The previous article ended on an open question: where each kind of context belongs. While I was preparing it, my agent handed me a stale memory and I very nearly acted on it.

The memory said that scheduling an article on this site means creating a single-use workflow named after the article. That was true in July. The mechanism has since been replaced by a manifest: one JSON file holding the publication queue. There is **not one** of those workflows left on the main branch.

The memory wasn't wrong. **It was true, and it stopped being true while nobody was looking.** No mistake, no carelessness in writing it: the world moved and the memory stayed where it was.

Which led to a more uncomfortable question. If that one was stale and nobody knew, how many others?

## Two memories with opposite rules

I run two memory systems at once, and they are built on deliberately opposite criteria.

One is **personal**: the files Claude Code keeps per project. The agent writes them when a session ends, I review them, and they come out of conversations I was present for.

The other is **production**: the knowledge system of an internal DevOps bot that answers requests over chat. There the memory is written by a small model after every response, unsupervised, from interactions with other people that I have never read.

That second system carries machinery the personal one doesn't need, and every piece of it answers a specific problem of writing without supervision. A new fact doesn't enter as true: it enters as a candidate, and only gets promoted when the bot independently reaches it again in a later investigation. Whatever nobody confirms within a month is deleted. Whatever goes ninety days without a single query retrieving it turns obsolete and stops being injected, though it isn't destroyed: confirm it again and it comes back. And every night a job clusters whatever looks too similar and decides whether to merge it.

| | Personal | Production |
|---|---|---|
| **Who writes** | the agent at session end | a small model, alone |
| **Reviewed by** | me, before it's stored | nobody |
| **From what** | conversations I was part of | third-party interactions |
| **Trust** | goes straight in | two confirmations |
| **Staleness** | nobody detects it | expiry through disuse |
| **Contradiction** | they coexist quietly | resolved |
| **Usefulness** | not measured | retrieval counted |

Seen side by side, the difference isn't sophistication. **It's who writes and with how much supervision.** When I write, or review what gets written, trust comes for free: that's why the personal system can afford to be light, and why working with it feels easy. When a model writes alone, from material nobody has read, trust has to be built from scratch, and without that machinery the system degrades by itself.

They are different problems and there is no reason for them to converge. Bringing promotion-by-evidence and nightly forgetting into a folder I review myself would add ceremony where a person is already doing that job.

## What expires on its own

There's a distinction I was slow to see, and it orders everything else.

**A preference doesn't become false by itself.** If my standard is that an article should avoid sweeping claims, that doesn't stop being true on its own: it changes the day I change my mind, and on that day I say so. Nothing needs verifying.

**A fact about the system does expire on its own**, quietly, because the world moves without telling anyone. The publishing mechanism changed without the memory describing it noticing.

So automatic verification only makes sense over the second half. That stops being a limitation and becomes the design criterion: **you can only check what can expire without anyone touching it.**

## Counting them

I let an agent build a verifier, to see whether automating it turned up anything that wouldn't show by hand. The idea is simple: attach to each memory a check that runs against the repository, along the lines of *this memory claims those workflows exist, so there should be at least one*. If there isn't, the memory gets flagged.

```json
{ "file_matches": ".github/workflows/scheduled-publish-*.yml" }
```

Across the 35 memories this project had on 11 September:

| state | count | |
|---|---|---|
| green | 7 | the check passes |
| **red** | **3** | claims something no longer true |
| grey | 25 | no check is possible |

Let me give the verdict on the tool up front, because it isn't the interesting part: **it's clumsy**. Every check has to be written by hand, and writing one means reading the whole memory and deciding what it claims. Once you've done that, you already know whether it's still alive; the program only confirms it. Reviewing all 35 by hand would have cost about the same and produced the same number.

What justifies the detour is what turned up along the way, and it isn't the number. ([The code is here](https://github.com/JaviMaligno/personal-website/tree/main/scripts/memory-audit), with its limits documented.)

## The three reds say the same thing

I verified each red by hand, because a red is an accusation. All three held up. And all three share a shape:

- One said the scheduling mechanism is single-use workflows.
- Another, that its article was still pending on a branch. It was published on 30 August.
- Another, that two articles were awaiting review and merge. They went out on 15 and 30 July.

**None was wrong when written. All three described a transitional state.** "This is pending", "right now it works like this". And a transitional state starts expiring the moment it's written down, because the whole point of it is that it's going to change.

There's a practical rule in there I hadn't expected to find: **a memory recording a stable fact ages well; one recording a situation in progress is born with an expiry date.** And nothing forces you back to it, because the day the work moves on you are busy moving it on.

## What can't be checked, which is nearly everything

I went through the 31 memories with no check and only 7 admitted one. Of those 7 I dropped another as forced: it was a preference of mine about how to order a document, and the check substituted the presence of a literal string in a file. Rewriting that heading would have turned it red without my changing my mind, and ignoring the preference while leaving the string in place would have kept it green. It wasn't measuring what it claimed to measure.

So: **about 80% of my memory admits no mechanical check.**

I could report that as the tool's limit. I think it's more honest the other way round: that 80% is judgement, preferences and ways of working, and **it's the part that makes working with an agent bearable**. It needs no verification because it doesn't expire on its own. It is already well handled, with no machinery on top.

The instinct when you measure something is to want the number to go up. Here, pushing it up would have meant forcing checks onto memories that don't admit them — which wouldn't measure staleness at all. It would manufacture greens.

## The green that doesn't mean what it looks like

The most useful result of the exercise was one of the greens.

A memory about publishing automation came out **green**: its seven files all exist, all verified. And inside, that same memory said a credential expired on a date that by then was a month past.

The green was correct and the memory was stale, both at once. **A green certifies what was encoded, not the whole memory.** There's no contradiction: there's a tool answering exactly the question it was asked, and a reading of mine that wanted it to answer a larger one.

When I went to fix it, the credential turned out to be perfectly alive: it had been renewed in August and nobody wrote that down anywhere. So the fix wasn't correcting the date, because a new date expires again in sixty days and the problem repeats. It was **removing it and recording where the state can be checked** — which turned out to be a daily workflow that was already checking exactly that and writing it into its own log.

The memory went from asserting a fact with an expiry date to saying where to look. The second kind doesn't age.

## A check that cannot fail

There's one last result, and it's about the attempt to automate itself: it's why I don't trust the number beyond what it's worth.

The first checks that went in described **how the mechanism works today**: that the manifest exists, that no single-use workflows are left. Those are true statements, so they all passed. But a check like that watches nothing: it describes the present, and the present always describes itself. For reality to be able to contradict a memory, you have to encode **what the memory claims**, not what is the case now.

**A check that always passes is worse than no check at all**, because an unchecked memory is known to be unchecked, while one with a vacuous check looks watched.

And that's the limit of the whole approach: the tool that measures whether a memory is still true can be wrong in the same way as the memory it watches, with the same consequence. Nobody notices, because the report says everything is fine. A real verifier would need someone verifying the verifier, and that doesn't hold up on its own.

## What actually fixes it

After the whole detour, what keeps a memory alive isn't checking it: it's **closing the session by updating it**.

When a piece of work ends — the article goes out, the mechanism changes, the decision gets made — that is the moment the memory describing it stops being true, and it's also the only moment when someone has the whole context in their head to fix it. Half an hour later it already costs something, and a week later it has to be reconstructed.

The good news is that the agent often does this on its own, unprompted. The bad news is that "often" isn't "always", and the three reds above are precisely the cases where it didn't happen. So it's worth making sure: let closing a session include asking what, of what was written down, has stopped being true today.

It's less impressive than a verifier and it works better, because it attacks the problem where it starts instead of detecting it months later.

## What only shows up when there's more than one of you

All of the above is one person and one project. Three reds out of thirty-five is not a staleness rate for anything: it's what came out of my folder.

The interesting part starts where my case ends, and that's where I am now. When several people feed the memory, three questions appear that don't exist alone.

**Who maintains the current state when the record has no owner.** There are more options here than it looks, and none is obviously right: name someone responsible; have each person update whatever their own contribution touches, since they're the ones in a position to know; have updates be proposed and then maintained automatically; or let whatever nobody uses wither on its own, the way the production system expires facts through disuse. Several of these probably coexist, depending on the kind of memory.

**How you correct something other decisions already cite.** Here I take the idea from the production system that strikes me as its most transferable: if manual corrections become frequent, what needs fixing is how things get saved, not building a more comfortable deletion tool. Correcting a lot by hand isn't healthy maintenance, it's a symptom.

**And what each person sees**, which framed as "which person sees what" is the wrong framing. Whatever is common to the project has to reach every agent, and therefore every person: that's what common means. The finer point is roles. A PM and a dev on the same project may have different access, or the same access organised differently, so that what is knowledge for one is general context for the other.

What isn't common is the other half: **each person's own practices and methodology**, which differ partly because each of us works with different agents. That shouldn't be unified, and forcing it would repeat the mistake of wanting two systems with different problems to look alike.

But there's a nice case in between. When several of those personal practices **converge on their own** — the same habit showing up in people who never agreed on it — that is exactly the signal the production system uses to promote a fact from candidate to confirmed: someone arriving at it independently. Applied to ways of working rather than to facts, it gives a route to standardise without imposing: what converges gets proposed, and the rest is either decided together or left where it is.

None of it is solved. But the small exercise leaves two things I do take with me:

- **Anything recording a situation in progress should be marked as such**, because it will expire and it helps to know where it will break.
- **The moment to fix a memory is when the work that makes it stale finishes**, not months later with a tool.
