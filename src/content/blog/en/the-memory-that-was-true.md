---
title: "The memory that was true"
description: "I audited the 35 memories my agent keeps about this project. Three were stale, and none of them had been wrong when written: they described a state that expired on its own. The other 80% can't be checked at all, and that isn't a flaw."
pubDate: 2026-09-20
tags: ["Agents", "Memory", "Context", "Verification"]
lang: en
translationKey: the-memory-that-was-true
heroImage: "/blog/the-memory-that-was-true.png"
---

The previous article ended on an open question: where each kind of context belongs. While I was preparing it, my agent handed me a stale memory and I very nearly acted on it.

The memory said that scheduling an article on this site means creating a single-use workflow named after the article. That was true in July. The mechanism has since been replaced by a manifest: one JSON file holding the publication queue. There is **not one** of those workflows left on the main branch.

The memory wasn't wrong. **It was true, and it stopped being true while nobody was looking.** No mistake, no carelessness in writing it: the world moved and the memory stayed where it was.

Which led to a more uncomfortable question. If that one was stale and nobody knew, how many others?

## The memory you write and the memory a model writes

It turns out I run two memory systems at once, with opposite design decisions.

One is **personal**: the files Claude Code keeps per project. The agent writes them when a session ends, I review them, and they come out of conversations I was present for.

The other is **production**: the knowledge system of an internal DevOps bot that answers requests over chat. There the memory is written by a small model after every response, unsupervised, from interactions with other people that I have never read.

Side by side, the difference isn't where I expected:

| | Personal | Production |
|---|---|---|
| **Who writes** | the agent at session end, supervised | a small model after each response, alone |
| **From what** | conversations I was part of | interactions with third parties |
| **Trust** | goes straight in | `candidate` → `confirmed` after being rediscovered twice |
| **Staleness** | nobody detects it | `obsolete` status + nightly maintenance |
| **Contradiction** | they coexist quietly | recorded and resolved |
| **Usefulness** | not measured | retrieval count per fact |
| **Retrieval** | index and relevance | semantic search |

The temptation was obvious: production is more sophisticated, so port it to the personal side. I was about to propose exactly that, and it would have been a blunder.

**The difference isn't sophistication, it's who writes and with how much supervision.** When I write, or review what gets written, trust comes for free: that's why the personal system can afford to be light, and why working with it feels easy. When a model writes alone, from material nobody has read, trust has to be built from scratch — promotion through repeated evidence, contradiction detection, forgetting whatever nobody uses — and without that machinery the system degrades by itself.

Porting one onto the other would have improved nothing. It would have added ceremony where human review already does that job.

## What expires on its own

There's a distinction I was slow to see, and it orders everything else.

**A preference doesn't become false by itself.** If my standard is that an article should avoid sweeping claims, that doesn't stop being true on its own: it changes the day I change my mind, and on that day I say so. Nothing needs verifying.

**A fact about the system does expire on its own**, quietly, because the world moves without telling anyone. The publishing mechanism changed without the memory describing it noticing.

So automatic verification only makes sense over the second half. That stops being a limitation and becomes the design criterion: **you can only check what can expire without anyone touching it.**

## Putting a number on it

I wrote a small verifier to stop speculating. The idea is deliberately dumb: each memory can carry a check that runs against the repository.

```json
{
  "project_blog_publishing_mechanism": {
    "checks": [
      { "file_matches": ".github/workflows/scheduled-publish-*.yml" }
    ]
  }
}
```

That check says: *the memory claims single-use workflows exist, so there should be at least one*. Today there are none, the check fails, and the memory comes out **red**.

Every memory lands in one of four piles: **green** (the check passes), **red** (it claims something no longer true), **grey** (no check is possible) and **error** (we can't tell). The fourth matters more than it looks: a badly written check must not count as a stale memory, because that would inflate the result in exactly the direction that suits me.

Before running it I wrote down a prediction, so the result would mean something: grey would be the largest pile, and red small but not zero.

Across the 35 memories for this project:

| state | count |
|---|---|
| green | 7 |
| **red** | **3** |
| grey | 25 |
| error | 0 |

## The three reds say the same thing

I verified each red by hand, because a red is an accusation. All three held up. And all three share a shape:

- One said the scheduling mechanism is single-use workflows.
- Another, that its article was still pending on a branch. It was published on 30 August.
- Another, that two articles were awaiting review and merge. They went out on 15 and 30 July.

**None was wrong when written. All three described a transitional state.** "This is pending", "right now it works like this". And a transitional state starts expiring the moment it's written down, because the whole point of it is that it's going to change.

There's a practical rule in there I hadn't expected to find: **a memory recording a stable fact ages well; one recording a situation in progress is born with an expiry date.** And nothing forces you back to it, because the day the work moves on you are busy moving it on.

## What can't be checked, which is nearly everything

Of the 31 memories with no check, I went through all of them and only 7 admitted one. An adversarial reviewer then rejected another as forced: it was a preference of mine, and the check substituted the presence of a literal string in a file, which is a different thing entirely.

So: **about 80% of my memory admits no mechanical check.**

I could report that as the tool's limit. I think it's more honest the other way round: that 80% is judgement, preferences and ways of working, and **it's the part that makes working with an agent bearable**. It needs no verification because it doesn't expire on its own. It is already well handled, with no machinery on top.

The instinct when you measure something is to want the number to go up. Here, pushing it up would have meant forcing checks onto memories that don't admit them — which wouldn't measure staleness at all. It would manufacture greens.

## The green that doesn't mean what it looks like

The most useful result of the exercise is one of the greens.

A memory about publishing automation comes out **green**: its seven files all exist, all verified. And inside, that same memory states that a credential expires on a date that has already passed.

The green is correct and the memory is stale, both at once. **A green certifies what was encoded, not the whole memory.** There's no contradiction here: there's a tool answering exactly the question it was asked, and a reading of mine that wanted it to answer a larger one.

I left it recorded as a question for a person, still counting as grey. A pending question is not a check.

## The verification can be broken too

This is the part that made me think hardest, and it's the part that reflects worst on me.

The verifier needed five rounds of adversarial review. The serious bugs that surfaced shared a shape with what this article is complaining about: **they were silent, and every one of them leaned towards "all fine"**. A memory came out green when the directory it looked in didn't exist. Another was classed as "not checkable" if a certain word appeared earlier in the text, and vanished from the report without a sound.

The best one was mine. I wrote the first checks describing **how the mechanism works today**, instead of what the memory claims. They all passed, of course. A check that describes the present can never fail, and **a check that always passes is worse than no check at all, because it hands you false confidence.**

The tool that measures whether a memory is still true can be wrong in precisely the same way as the memory it watches, and with the same consequence: nobody notices, because the report says everything is fine.

The test I now apply before writing a check is two questions: what concrete fact would turn it red, and could that fact happen without the memory ceasing to be true? If the answer to the second is yes, the check is no good.

## What only shows up when there's more than one of you

All of this is one person and one project. Three reds out of thirty-five is not a staleness rate for anything: it's what came out of my folder.

The interesting part starts where my case ends. In the production system the memory is written by other people's interactions, and that brings problems that don't exist alone: who maintains the current state when the record has no owner, how you correct something that other decisions already cite, and which information is appropriate to share with each person.

That's what I'm working on now, and it isn't solved. But the small exercise already left me two things:

- **Anything recording a situation in progress should be marked as such**, because it will expire and it helps to know where it will break.
- **A check that can never fail is noise wearing the clothes of a guarantee.**

The verifier's code is in [this site's repository](https://github.com/JaviMaligno/personal-website/tree/main/scripts/memory-audit), with its limits documented. It's deliberately small: the interesting part was never the tool, it was the number that came out of using it.
