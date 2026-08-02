---
title: "What You Still Need to Know to Ship"
description: "You can build software now without writing a line of it. What's left isn't coding — it's a way of working, and a list of things you have to know exist or you'll never think to ask. Here's both."
pubDate: 2026-08-02
tags: ["AI", "Vibe Coding", "Software", "Engineering", "Mentoring"]
lang: en
translationKey: what-you-still-need-to-know-to-ship
heroImage: "/blog/what-you-still-need-to-know-to-ship.png"
---

The people building software today did not all learn to build software. Some came from marketing, from operations, from running a small business, from nothing technical at all. They describe what they want, an agent builds it, and it works. That part is real and it isn't going away.

What's also real is that a chunk of them are shipping things with the database wide open, the API key sitting in the browser bundle, and no way back to the version that worked last Tuesday. Not because they're careless. Because nobody told them those were categories of thing that exist.

That's the actual gap, and it's smaller and stranger than "learn to code."

## The ceiling: you can't ask about a space you don't know is there

Every failure I've watched, in myself and in the people I've taught, traces back to the same place. Not a missing skill. A missing *category*.

You don't need to know how authentication works. You need to know that having a login screen and being protected are two different things — because the moment you know that, you can ask, and the agent handles the rest. If you don't know it, you'll never ask, and the agent won't volunteer it. Agents answer questions well. They're much worse at telling you which question you should have asked.

I wrote about this from the other side in [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know) — the engineer's version, where you delegate knowledge you used to hold and have to work out what you're still on the hook for. This is the same wall from the other direction: not what you're allowed to forget, but what you never learned and now can't skip.

It's worth saying where this comes from. Most of my teaching has been with technical colleagues, which is a different problem and mostly a different article. With non-technical people my sample is smaller and more informal — friends, mostly, and that moment when someone meets a terminal for the first time. The rest comes from building this way myself, and from what I've caught agents doing along the way.

There are two things to get, and they're independent. One is a way of working. The other is a map.

## Part one: the loop

Specify → build → check → correct. Then again.

There is nothing new about this. It's spec/develop/test, the way software has been made for decades. If you came from anything technical you have it in your bones and can skip ahead. If you didn't, it is genuinely novel, and its absence is the single biggest difference between someone who ships and someone who has a very long chat history.

The default failure mode without it isn't dramatic. You ask, you receive, you believe it, you ask for the next thing. Nothing checks anything. It feels like progress right up until you try to show someone.

**The agent is in all four phases**, which is what makes this confusing. It helps you specify. It builds. It runs checks and tells you what to look at. It proposes the fix. So what's left? The useful question isn't where the agent is — it's always there — but what human residue each phase leaves:

- **Specify** — the intent is yours. The agent will write down what you want far better than you would. It does not know what you want.
- **Build** — nothing is left. Delegates completely.
- **Check** — the agent runs things and reports. What stays yours is knowing *which categories need checking at all*, and calling it done.
- **Correct** — nothing is left either. Correcting is building again, and the agent does it. When a failure makes you decide the whole thing should be rebuilt or dropped instead, that isn't correcting — that's going back to Specify with a different intent.

So the loop splits in half. Two phases hand over completely, two keep something human — and the two that vanish are exactly the ones people mean when they say "programming". What's left is saying what you want, and knowing whether you got it.

Which is why "you don't need to know how to program anymore" is both true and unhelpful. It's true about half the loop and silent about the other half, which is the half that was never taught to anyone.

Notice where checking sits: **inside the loop, from day one.** It isn't a level you reach — it's a phase you're already in. What grows with experience isn't *whether* you check, it's *what you're able to check*. It comes in three ranges: the agent tells you what to look at and you look; you check what you know to ask about; or you also know whether the check was any good and what it missed. The first range is available to a complete beginner on their first afternoon, and it's enough more often than you'd think.

### Three ways to catch things, none of which involve reading code

This is the part people assume is impossible without a technical background, and it isn't. Everything I catch, I catch one of three ways, and they apply to every category further down.

**Write it into the spec up front.** The cheapest one, because you don't catch the problem — you prevent it. If you say at the start that these values must come from the database and nothing may be hardcoded, you don't have to find the hardcoded value later. Most of what an agent gets "wrong" is a reasonable default it chose because you didn't state a preference.

**Use the running thing.** Not the code — the app. Click it, poke it, try the thing a user would try and then the thing they shouldn't. This is how I found an endpoint sitting open that shouldn't have been: it surfaced during testing, not during any code review.

**Ask when something smells.** A number that never changes when it should. A page that loads suspiciously fast. A screen that works when you're logged out. You don't need to know what's wrong to say "why does this never change?" — and the agent is genuinely excellent at going from that to a cause.

None of these require reading a line of code. All of them require knowing that the category exists, which is the entire point of the map below.

## Part two: the map, and how to read your level

For each category below there are three levels:

**Aware** — you know this category exists and can go wrong. You don't need to know how it works or what it's called. You need to know it's there, because that's what makes you ask.

**Fluent** — you understand the vocabulary, can form the question, and can tell whether the answer makes sense. Worth saying plainly: **this is the level you can reach by asking the agent itself.** Deliberately, with patience, one category at a time. It's the cheapest education available right now and almost nobody uses it on purpose.

**Opinionated** — you have your own view and can choose between options.

Two things about this that matter more than the levels themselves.

**Your level is a vector, not a number.** Nobody sits on the same rung across the board. You can be Opinionated about access control and completely unaware of what your hosting costs. The profile is jagged, and that's normal — it's a map with holes in it, not a ladder you climb whole.

**Opinionated is optional — until it isn't.** You can ship most categories without ever forming a view of your own. But wherever the project is actually betting something, the top level stops being a luxury: if you charge money, you need a view on cost; if you hold other people's data, you need one on access.

![The map: twelve risk categories in five families, plus one of taste](https://www.javieraguilar.ai/blog/what-you-still-need-to-know-map.png)

## Twelve categories, plus one

Twelve where things can go wrong, and one that's a different animal. Read down and find the ones you didn't know were categories — those are your answer.

### The ceiling

**1. What can even be asked for.** This one sits alone because it limits the other twelve. If you think an agent writes text, you will ask it to write text, and everything below stays theoretical.

- **Aware** — an agent builds entire working systems, not just snippets of writing
- **Fluent** — describe what you want by outcome, ask it to research and propose before it builds, and understand it when it says something can't be done or offers a different route
- **Opinionated** — which model, which tool, which hardware. A topic for a later piece.

### Where it is and how I get it back

**2. Where your app lives.** The environment question is where the genuinely scary mistakes live. Almost nobody deletes production data on purpose — they delete it believing they're in the test copy. And the separation you think you have may not exist: I've had pipelines that didn't distinguish environments at all, running CI against dev and prod alike, with no real separation behind the names. I found out by looking at the deployment dashboard, not by reading configuration — and then wrote the separation down so it stayed true.

- **Aware** — "running on my laptop" and "running on the internet" are different things. Close the laptop: is it still alive?
- **Fluent** — ask for a deploy, understand the difference between the test site and the real one, run a command you're handed without freezing, and know which of the two you're touching right now
- **Opinionated** — domains, per-environment settings, host logs, rolling back a deploy, choosing where it runs

**3. Code versus data.** Agents hardcode constantly — a value written into the code where it should have been read from the database. It's a reasonable shortcut when the goal is something that runs, and it's wrong the moment that data is meant to change. It's the standard case for the first and third techniques above: say up front that it mustn't happen, and ask later when a number looks suspiciously stable.

- **Aware** — code can be regenerated, data cannot; some data is sitting inside the code; data needs backups
- **Fluent** — ask where something gets stored and understand the answer, know whether the database is local or remote, and confirm a backup exists rather than having been mentioned
- **Opinionated** — migrations, test data versus real data, restoring, what kind of database and shape

**4. Getting back.** "It was working, now it isn't, and I don't know what changed" is the most common disaster in this field and the most completely solved one. The agent already commits for you. What's missing is you knowing the rescue exists so you can call for it.

- **Aware** — there's a way to recover yesterday's version and it isn't Ctrl+Z
- **Fluent** — ask for a save point before a big change, ask to go back, and check the history to confirm that point is really there
- **Opinionated** — branches, tags, pull requests, reading a diff

### Who gets hurt if this fails

**5. Secrets.** You do not need to be able to read a `.env` file. You need to know it exists and that keys belong in it. What isn't obvious: taking a key out of the code doesn't remove it from the project's history, and I've had to scrub keys out of that history more than once. There are tools that watch for this — GitGuardian and similar — and, depending on how critical the key is, safe ways to hand one to someone that aren't a chat message.

- **Aware** — keys don't live in the code, they live somewhere separate; a key that's been seen once is no longer secret
- **Fluent** — ask for a key to be moved out of the code, understand why that file isn't uploaded, know where a key comes from when you're asked for one, and know that a server key and a public client key are different animals
- **Opinionated** — rotating a leaked key, secret managers, per-environment secrets

**6. Who can get in.** The open endpoint above is this category. Worth restating what actually did the work there: the check was cheap and took a minute. Knowing it was a check worth running is the part that isn't free.

- **Aware** — having a login does not mean being protected
- **Fluent** — ask "can anyone call this?" and understand the answer; authentication is who you are, authorization is what you're allowed to touch; log in as one user and confirm you can't see another's data
- **Opinionated** — roles and permissions, row-level security, tokens, reviewing what's exposed

**7. Other people's data.** The one category with a moral asymmetry: everything else here costs you money or embarrassment, and this one is paid by someone who never agreed to your learning curve.

- **Aware** — if you store things about other people, the cost of getting it wrong isn't yours
- **Fluent** — know what you're collecting and why, know there are legal obligations attached, and ask for anything unnecessary not to be stored at all
- **Opinionated** — consent, retention, minimization, where the data physically lives

### What's going to surprise me

**8. What this costs.** Surprise bills are more common than breaches, easier to prevent, and almost nobody prevents them — because "there is no default limit" isn't something you'd think to ask about. Early on I built agentic systems without asking for token costs to be tracked, which meant I had no cost estimate at the end and had to run the whole batch again just to measure it. Not measuring cost has a cost, and it's paid in exactly the currency you were trying to find out about. Ask for it in the spec and it's free.

- **Aware** — this generates a bill and by default nothing caps it
- **Fluent** — understand the shape of the bill (model and API usage, hosting, database, storage, traffic), fixed versus per-use, that CPU and GPU aren't priced alike; ask for a cap and look at real consumption
- **Opinionated** — alerts, your own rate limits, bot protection, designing for cost

**9. Who you depend on.** Separate from cost because the failure isn't financial. It's that something which worked stops existing. I've run a migration between platforms that the agent reported as complete, and which fell over the moment I tried to run on the new one alone — the old platform was still quietly holding it up, and became the backup I hadn't planned for. "Migration complete" and "the old thing can be switched off" are different claims, and only the second one is testable.

- **Aware** — your app leans on other people's services, and they can raise prices, change, or shut down
- **Fluent** — know which pieces are someone else's and which are yours, and ask what happens when one goes away
- **Opinionated** — choose by coupling rather than price alone, and have an exit route

**10. Holding more than you tested.** Nothing in the building process warns you about this, because while you're building there is exactly one user.

- **Aware** — it works with three users and can fall over with three hundred
- **Fluent** — know that testing and holding load are different questions, and ask what breaks first
- **Opinionated** — measure it, size it, decide what's worth optimizing

### How I know it's still fine

**11. Tests, and where it breaks.** There should be tests for one unglamorous reason: without them, every check you'll ever do is you clicking through the finished app guessing what happened in the middle. That's a maze, and it grows with the project.

- **Aware** — there have to be tests, and "the agent says it works" isn't one
- **Fluent** — understand what you're told when someone says frontend or backend, run the tests and see them pass, and know where to look for an error depending on which side it's on
- **Opinionated** — which kind of test for which risk

**12. Still working in six months.** As a project grows messy and undocumented, **the agent starts failing more.** That's the argument — not architectural purity, but your own tool getting worse at helping you. The failure mode is specific and easy to miss: documentation drifts out of date, the agent trusts it completely, and you get confident work built on a description that stopped being true months ago. Documentation only stays true if something reviews it against the code — and that something can be the agent itself, if you ask.

- **Aware** — mess degrades the thing you're relying on
- **Fluent** — ask for documentation, and understand the difference between docs for people and instructions for the agent, and notice when the project's own summary no longer matches what it does
- **Opinionated** — what belongs in permanent instructions versus the conversation, and how to split the project up

### Plus one: taste

The thirteenth isn't like the other twelve, which is why it's last and separate. In all twelve, failure has a victim. Here there's no failure — just absence.

Agents are good at *working*. They're mediocre at *good*. The layout will be reasonable, the spacing fine, the colors the ones everything else has. Functionally correct and completely anonymous. Nobody will ever tell you it's wrong, because it isn't.

- **Aware** — what comes out by default works and looks like everything else
- **Fluent** — name what you don't like precisely enough for it to get fixed
- **Opinionated** — have a direction of your own and hold it

It's also the only one with no shortcut. In the other twelve, knowing the category exists is enough to ask and let the agent carry it. Here you have to look at the thing and decide you don't like it, and nobody can do that part for you.

## The production line isn't about you

I spent a while trying to define the point where a toy becomes real software as a level you reach. That's wrong, and it's worth saying why, because the correct version is more useful.

**Production doesn't require you to be at a level. It requires that no category is left unchecked by anyone — you, a test, a service, or another person — and that you know which is which.**

That's the same conclusion I reached from the engineering side: you don't need to hold the knowledge, you need to hold the mechanism. It applies just as well to someone who was never an engineer. A category covered by a test is covered. A category covered by a service you pay for is covered. A category you check by hand every time is covered, expensively.

Which is what Aware is actually for. It doesn't let you check anything. It lets you see that the box is **empty**. An empty box you know about is a managed risk. An empty box you don't know exists is the thing that ends up in the news.

![The same project as a toy and as a production system](https://www.javieraguilar.ai/blog/what-you-still-need-to-know-toy-vs-production.png)

## Where you're starting from

The map is the same for everyone. Which parts you already hold, and which way you fail, depends on where you came from.

**With no technical background**, your bottleneck is the ceiling, not the details. You ask for less than you could because you don't know what's askable. The loop is genuinely new. The terminal is frightening in a way that's hard to explain to someone who's used one for a decade. And your characteristic failure is delegating *above* your level — handing over things you have no way to check and, worse, don't know need checking.

**Coming from engineering or ops**, you have the loop already and most of the twelve. Your failure is the mirror image: you delegate *below* your level. You review every line, take steps too small, and check by hand what a machine should be checking. You're slower than you need to be and it feels like diligence.

More on both in the next two pieces.

## How much to let go

Here's what all of this measures, and it isn't knowledge.

**Your level is how much you can hand over without going blind.**

Each rung doesn't let you type more, it lets you *release* more, because you have some way to catch it coming back wrong. Aware means you'll notice the category came up at all. Fluent means you can interrogate it. Opinionated means you can overrule it. At every step, the amount you can safely stop watching goes up.

Which makes both failure modes the same mistake with the sign flipped. Delegating above your level is handing over what you can't check. Delegating below it is refusing to hand over what you can. The fix is identical in both directions: find your rung — in each category separately, because it's a vector — and let go of exactly as much as it holds.

You don't need to learn to code. You need a loop, a map of what exists, and enough honesty about which boxes are empty.

---

## The whole thing on one page

| | Aware | Fluent | Opinionated |
|---|---|---|---|
| **1. What can be asked for** | agents build whole systems | describe by outcome, ask it to propose | model, tooling, hardware |
| **2. Where it lives** | laptop vs internet | deploy, test site vs real, run a given command | domains, env settings, rollback |
| **3. Code vs data** | data can't be regenerated | where is this stored, local vs remote database | migrations, restores, schema |
| **4. Getting back** | yesterday is recoverable | ask for a save point, confirm it exists | branches, tags, diffs |
| **5. Secrets** | keys live outside the code | secrets file, server vs client key | rotation, secret manager |
| **6. Who gets in** | login ≠ protected | can anyone call this, authn vs authz | roles, permissions, tokens |
| **7. Other people's data** | the damage isn't yours to pay | what you collect and why, legal duties | consent, retention, residency |
| **8. What it costs** | no default limit | shape of the bill, ask for a cap | alerts, rate limits, cost design |
| **9. Who you depend on** | someone else's service can vanish | which pieces aren't yours | coupling, exit plan |
| **10. Holding load** | works at three users, not three hundred | testing vs load are different questions | measure, size, optimize |
| **11. Tests and breakage** | there have to be tests | frontend vs backend, run them, read the failure | which test for which risk |
| **12. Six months on** | mess degrades the agent | docs for people vs for agents | permanent instructions, structure |
| **+1. Taste** | the default is anonymous | name what you don't like | a direction of your own |

---

*This is the first of three pieces on what building software with agents actually requires. The next two take the same map from opposite ends: one for people with no technical background, one for people who have too much of it and can't put it down. Related reading: [How Much Should You Still Know?](/en/blog/how-much-should-you-still-know).*
