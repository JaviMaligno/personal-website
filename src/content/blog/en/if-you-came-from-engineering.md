---
title: "If You Came From Engineering"
description: "You already know how to verify work at scale — tests, CI, pipelines. You're just not applying any of it to the agent. You're checking its output with your eyes, which is the one thing you spent a career learning doesn't work."
pubDate: 2026-08-14
tags: ["AI", "Vibe Coding", "Software", "Engineering", "Mentoring"]
lang: en
translationKey: if-you-came-from-engineering
heroImage: "/blog/if-you-came-from-engineering.png"
---

The people who struggle most with agents are not the ones who don't understand them. In my experience they're the ones who understand software best.

They review every line. They give instructions far more precise than the job requires. They break work into pieces small enough to inspect, and then inspect all of them. And when you ask why, the answer is some version of *because it's my name on it* — which is exactly right, and was exactly right five years ago. Not fifteen. These habits are recent, they were correct when we formed them, and they went out of date faster than anything else we've had to unlearn.

I include myself. I did all of this, and some days I still catch myself doing it.

It's the mirror image of [the mistake people make when they start from zero](/en/blog/if-youre-starting-from-zero). They delegate above their level, handing over what they can't check. We delegate *below* ours, refusing to hand over what we could.

Both end up slow, but on different curves. Theirs is fast right up until it isn't: it moves, and moves, and then something breaks that they have no way to diagnose and the whole thing stops. Ours never gets fast in the first place — no cliff, just a steady tax paid every day.

And only one of the two looks like diligence, which is what makes it the harder one to correct. Nobody is ever going to take you aside and suggest you review less.

## The thing you already know and aren't using

Here's what makes this particular failure strange: you solved this problem years ago.

You don't review a colleague's work by reading every line they wrote. You have tests. You have CI. You have a pipeline that says no before a human has to. You spent a career learning that verification by eyeball doesn't scale, and building the machinery that replaced it.

And then an agent produces a change and you read it line by line.

That's the gap: **a verification method we already know is inadequate, applied to the one collaborator that produces work faster than any human could.** The mechanisms we'd reach for instinctively with a teammate are sitting right there.

What that looks like in practice — this is what I actually give an agent so I don't have to check by hand:

- **Tests**, so a claim of "done" has something behind it.
- **CI**, so the check happens whether or not I remember to run it.
- **Spec-driven skills**, so the thing it builds is checked against what was asked rather than against my mood on the day.
- **Browser tooling** — I use Claude in Chrome — so it can drive the running app and come back with screenshots that show the thing working, instead of telling me it works.

That last one is the closest to a genuine unlock. "It's done" and "here's a screenshot of it doing the thing" are different categories of claim, and the second costs the agent nothing to produce.

### But the agent writes the tests

This is the first objection anyone raises, and it deserves a straight answer: if the tests come from whoever wrote the code, what exactly have you gained?

What you've gained is that **the test moved from something you write in code to something you describe in words.** You still specify the behaviour — you just say it in a sentence instead of a fixture. "A user who isn't logged in gets nothing back from this endpoint" is a specification you can write, read and argue about without touching a test framework, and it's the anchor both the code and the test are checked against.

That's also why a test written to pass trivially isn't the threat it sounds like. A test that asserts nothing is visible in seconds when what you asked for was written down. The failure mode isn't a fake test slipping past you; it's you never saying what the thing was supposed to do.

The residue that stays human isn't inspection. It's **suspicion**: noticing something smells, that a number moved when it shouldn't have, that the fix came too fast. You keep the judgment. You hand over the looking.

### When reading the code is still the right call

Mostly it isn't. But "mostly" isn't "never", and the analogy I find useful is assembly.

At some point we stopped reading what the compiler emitted. Not because it became infallible — because checking it stopped being the best use of anyone's attention. And yet there are still domains where people do drop to that level: when the thing is critical enough that the cost of being wrong justifies the time, or when there's one specific thing they need to see with their own eyes.

Same here. Payments is the obvious example. Anything where a subtle error is expensive and silent, anything under a compliance regime, anything you'd struggle to write a test for. Those earn a read.

What doesn't earn a read is *understanding*. If you want to know how something works, having the agent explain it to you is faster and better than reading it yourself — it can tell you why, which the code can't.

And there's a move that beats both reading and not reading: **make there be less to read.** A change that touches six files because nobody said where the code lived is unreviewable in practice, so it gets skimmed and merged. The same request, with the relevant area named and a standing instruction to keep changes minimal, comes back half the size and can genuinely be read in a minute. That's laying rails again — you're not deciding whether to inspect, you're deciding how much there is to inspect.

Worth being honest about the limit here, because it's the one thing tests don't cover: a stray change that breaks nothing. A config value altered for no reason passes every test you have, and turns up three weeks later in production. That is exactly the case a small diff catches and a green pipeline doesn't — which is the argument for keeping diffs small rather than for reading big ones.

## Precision, and the part worth keeping

The first symptom of delegating below your level is over-specification.

You write the instruction the way you'd write a ticket for someone junior: every file named, every step ordered, every edge case spelled out. It works. It also means you did most of the thinking, and the agent contributed typing.

But "let it decide the how" is too blunt, and I don't believe it. If you have a view on the approach, that view is worth something — it's the whole reason [having an opinion is the top of the scale](/en/blog/what-you-still-need-to-know-to-ship) rather than a nice-to-have. Architecture, the shape of the solution, sometimes the stack: those are yours to argue for.

The distinction that matters is between the **conceptual how** and the **sequence of steps**. Which approach, which trade-off, which stack — bring your opinion, it's earned. Which file to open first, in what order, named what — that's the part where being specific costs you the contribution you were paying for.

And the more useful reframe isn't about who decides. It's that **you can argue with it as an equal.** Ask what it would do. Say why you don't like the answer. Hear the response. It will propose stacks and approaches you hadn't considered, and often enough it's right that dismissing them on reflex is expensive. The posture that works is neither dictating nor deferring: it's letting yourself be steered while staying willing to push back.

There's a related incoherence I see a lot, and it's worth naming because it wastes money as well as time: **asking for tiny tasks from a large slow model.** If you're going to hand over work in five-minute pieces, use something fast — the whole economics of a small task assume a quick turnaround. Match the size of the request to the tool. Big careful model for the big careful job; something quick for the small stuff. Paying premium latency for a one-line change is the worst of both worlds, and almost nobody notices they're doing it.

## Waiting isn't the cost you think it is

This is the belief underneath everything else, and until it flips nothing else does.

When an agent is working and you're sitting there, it feels like waiting. Dead time. Something you'd rather minimise, which is why you break work into pieces small enough that the wait is never long — and why you never start a second thing while the first is running.

But that time isn't lost. It's **freed**. The only reason it feels like waiting is that you haven't put anything in it yet.

And there's a queue of things that fit. The maintenance you keep postponing. The optimisation you can never quite justify prioritising. And the parts of the job that were never code in the first place — writing something up properly, researching a decision instead of guessing at it, talking to whoever needs talking to, or just thinking about where the thing is going. Those were always the first to get squeezed out, and this is the first time in a while that something has handed the space back.

Once that lands, parallelising stops being an advanced technique and becomes the obvious thing to do. My rule for where to start is boring and works: **run things in parallel when they don't touch the same files.** That's it. Two features in different areas, a refactor here and a test suite there. No coordination required, because there's nothing to coordinate.

Beyond that there are worktrees, which let you run genuinely conflicting work side by side — but then you own the merges, so it's worth it when the work is big enough to justify the bookkeeping and not before.

## Session hygiene, which nobody explains

The other thing that separates people who move fast is unglamorous and rarely discussed: knowing when to keep going and when to start over.

What I actually do:

**New task, new session.** If it isn't related to what came before, the previous context is noise at best.

**Related work stays.** Follow-ups, or several tasks inside the same spec, can share a session — the accumulated context is doing real work there.

**Compact when it starts labouring.** Sometimes I let it compact automatically, sometimes it asks, sometimes I just notice it's losing the thread and do it. Approaching the limits of what it can hold — call it the last fifth — is usually a good moment regardless.

None of this is deep. But the difference between someone who does it and someone who doesn't is enormous, and it doesn't show up in any documentation because it isn't a feature. It's a habit.

## A caveat about tooling

Everything above assumes you have a capable agent to hand. That assumption isn't free.

If you're working with an autocomplete-style assistant, a limited chat window, or a smaller open model, the advice changes shape: you'll subdivide more, build more of the scaffolding yourself, and stay closer to the work — not out of reflex, but because the tool genuinely needs it. Whether you can change that is often not your call, and it deserves its own piece rather than a paragraph here.

## What actually shifts it

There's no technique for the trust part, and I've stopped pretending otherwise. For me and for the colleagues I've watched go through it, the sequence was the same and it wasn't intellectual: **you see it come out right, enough times, and you stop bracing.**

Two things genuinely help. The tools keep getting better, so the same amount of trust buys more than it did last year. And you get better at **laying the rails** — building the setup that makes the agent do the right thing, rather than checking afterwards whether it did. That's the skill. Not confidence: track-laying.

Which is why the advice I give a colleague on day one sounds almost too simple. **Don't over-engineer the setup** — start with the defaults, try things, see how it goes before building scaffolding around it. And **ask more**, genuinely more than feels natural: it resolves things faster than you'd find them yourself, and going off to search first is the most expensive habit we brought with us. That one lands strangely, because searching *was* the skill. It just isn't the fastest route to the same answer anymore.

The reason it's worth the discomfort is that this rewards exactly what you already do. Not writing code — specifying precisely, building verification that runs without you, and knowing what to be suspicious of. That's the job description, and someone arriving here from nothing has none of the three. The ceiling is higher for us than for them, sitting behind a door held shut by a habit that was correct until recently.

So: **stop checking with your eyes what a mechanism should be checking.** Keep the eyes for the cases that earn them. The trust arrives on its own once the mechanisms are carrying the weight.

---

*Third of three pieces on what building software with agents actually requires. The first is [the map](/en/blog/what-you-still-need-to-know-to-ship), the second is [for people starting from zero](/en/blog/if-youre-starting-from-zero). If you'd rather work through this with your own team, [that's what I do](/en/mentoring).*
