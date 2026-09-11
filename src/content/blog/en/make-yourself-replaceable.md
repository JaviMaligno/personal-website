---
title: "Making yourself replaceable"
description: "The ability to let someone else take over your work without needing you for every decision. How to prepare a handover when you work with agents: separating the current state from its history while preserving the reasons."
pubDate: 2026-09-19
tags: ["Agents", "Context", "Teams", "Memory"]
lang: en
translationKey: make-yourself-replaceable
heroImage: "/blog/make-yourself-replaceable.png"
---

There is one ability I particularly value in a company: **helping someone else take over your work without needing you for every decision.**

The better you do this, the more value you contribute. Yet the result is that you become less essential to keeping that work going.

I find this paradox interesting because we tend to talk about being irreplaceable as something to aspire to. Being the person who knows the most, solves the difficult problems and has all the answers. But **if that knowledge has to pass through you before anyone else can use it, you have also put a limit on what the team can do when you are unavailable.**

I would particularly value someone who does their work well and also gives others the tools, knowledge and context to do it independently. That ability remains valuable after the handover: they can apply it again on another project, with another team or to a harder problem.

I arrived at this reflection through something quite concrete: preparing a handover when you work with agents.

## What isn't in the repository

Handing over the code and explaining how to run it covers part of the work. But there is much more you have accumulated along the way: how changes are reviewed, what gets checked before a task is considered finished, which constraint the client requested, which alternative was rejected and why an apparently better solution cannot be used yet.

When I try to sort out where each of those ends up, I get three different places:

- **The documentation**, which is the part we usually treat as the deliverable.
- **The conversations with Codex or Claude Code**, where the approach was argued out, where something was tried and failed, where the standard for reviewing work was agreed.
- **Whatever came from elsewhere** and never entered the project at all: an email, a Slack thread, a meeting where a priority changed.

**That third category is the worst preserved, and it is usually the one that weighs most.** A client constraint is rarely written down as a constraint; it arrives in an email, it shapes the code, and then it disappears. The code remains. The reason does not.

When someone joins to help you, they need to find their way through all of it. The repository tells them what exists. To continue the work, they also need to understand what has been agreed, what remains open and the reasons behind it. **Without that, they can read the entire codebase and still propose the alternative that was rejected a month ago**, for a reason that still holds and that nobody wrote down.

## Archive and memory

In my case the practice is fairly simple: I keep records of the communications relevant to the projects my agents work on. Emails, Slack conversations and meeting notes, in files that live in the project repository itself.

The material comes in through two routes, and the difference matters more than it looks. For email and Slack I use connectors, so **the agent can consult them itself** when it needs to. For meetings I use the notes Gemini and Granola produce, and those I bring in myself. Some conversations have no connector at all and I simply paste them.

That asymmetry is why the local files are not redundant once you have connectors. **A connector solves whatever is connected; the files are the only place everything else can land.** They are also what makes the context outlive the tool: if I switch note-taking systems tomorrow, whatever has already been captured is still there.

The part I care about most is **separating the current state from its history while preserving the reasons and decisions.** They are two different artefacts and it pays not to merge them:

| | Archive | Maintained memory |
|---|---|---|
| **What it holds** | every communication, in full | only what still applies |
| **How it's ordered** | by date | by topic |
| **Question it answers** | what happened, and when? | what do we know today? |
| **When something changes** | one more entry is added | it's rewritten, the old marked superseded |
| **What it's for** | investigating, checking, citing | getting to work |

I keep that up at two moments. **When new material arrives**, it is archived as it is and whatever it changes in the current state gets updated. **And when a working session ends**, whatever was decided during that session goes down into the memory too.

Both are needed. The first captures what happens outside; the second, what happens while you work. With only the first, the memory never records the decisions you made yourself. With only the second, **the memory has no idea the client changed their mind on Tuesday.**

Right now I supervise both distillations. Automating them is the next step, not something I have already solved.

Imagine that in the meeting on the 17th we agree to deliver an integration on Friday the 18th. That meeting note is archived with its date, and the memory now says delivery is Friday. Two days later an email arrives: there is a dependency on the client and delivery moves to the following Tuesday. The email is archived with its date, exactly as the note was. And the earlier memory entry is not deleted:

```markdown
## Integration delivery

Date: Tuesday 22                      [decision · 19 Sep]
Blocked by: client dependency
Outstanding: confirmation of the staging endpoint
Source: email 19 Sep — client

~~Date: Friday 18~~                   [superseded · 19 Sep]
Source: meeting record, 17 Sep
```

Six lines doing three things at once: **they say what currently applies, they let you see what came before, and they point at the source of both.** Whoever picks up the project finds the live date first, along with what is still needed to meet it, which is what they need in order to start working. If they need to understand the change, the earlier agreement is one step away. Merging the two forces you to read everything just to work out what still stands.

This is why **the date of a note, where it came from and whether it records a proposal or a decision matter a great deal.** Someone floating a date is not the same as the team agreeing to one, and in a summary those two look far too similar. **A summary can be useful and wrong.** Being able to return to the email or the meeting record helps prevent an agent's interpretation from turning into an agreement nobody made.

There is one last decision that looks administrative and isn't: **whether those files get committed.** I don't always commit them. While they sit uncommitted they are my memory, and they work just as well for my own work. The moment they enter the repository they stop being mine and become the team's context, available to anyone who opens the project. **Same technical gesture, completely different purpose.**

What holds that gesture back isn't laziness, it's that it forces you to decide what may go in. A Slack thread carries names, an email may carry client data, a meeting record captures things people said without expecting them to be written down. Preparing that material to be shared is real work, and it is precisely the work that makes the handover possible. Until it is done, **what I have is a very comfortable personal practice that is no use to anyone else.**

## This helps me too

None of this requires anyone to be joining. I forget things too. I also return to projects after several weeks and need to recover why we decided something. Keeping that record reduces the work of getting my bearings again.

That is the part I didn't expect: **when the current state is written down somewhere, changes become visible.** If the memory says delivery is Friday and an email turns up assuming a different date, the contradiction surfaces. When everything lives in your head, that same contradiction resolves itself quietly, usually in favour of whatever you read most recently.

For someone new, the difference can be greater. We are asking them to continue conversations they were never part of. If they also have to discover where those conversations happened, who remembers what and which parts still matter, **much of their onboarding becomes a search for context.**

Access to that material does not instantly bring anyone to your level. Experience, practice and guidance still matter. But it lets **that guidance focus on developing judgement instead of reconstructing what has already happened.**

This is where preparing a handover starts to look like a daily practice rather than a farewell task. Every important decision that remains easy to find and up to date is something you will not have to explain from scratch later. It helps when you take a holiday, bring in support or simply want a colleague to make progress while you are busy.

## The company has to make room for it

If sharing knowledge always happens after the "important work" is finished, **it will be the first thing dropped under pressure.** And there is always pressure.

If recognition also goes only to whoever personally unblocks every problem, preparing others to solve it will receive little credit, because **its effect shows up exactly where nobody is looking: in the problems that stop escalating.**

It should count as a contribution when a colleague can take on a responsibility that previously depended on you. The same applies when someone can recover a decision without calling you, or when the team keeps going while you are away. These are outcomes worth considering when evaluating someone's work, and they are hard to see if you only look at the problems that were solved and not at the ones that stopped arriving.

## Where each kind of context belongs

The next technical step would be to move this memory into a shared environment: several agents consulting the same context, and updates reaching the project even when its lead did not attend a meeting or write that code.

Before that there is a more basic question, and it is the one I have open: **where each kind of context belongs.**

For what belongs to the project — dates, agreements, client constraints, what was ruled out — the repository itself is a reasonable home. It sits where the work sits, it is versioned along with it, and it reaches only the people who already have access.

But there is another half that **belongs to no single project**: how a change gets reviewed, what is checked before calling something finished, which technologies we have tried and which we dropped, the skills and tooling I have been refining. That applies across every project at once. **Copying it into each repository guarantees the copies drift apart**, and that the good version ends up being the one in the head of whoever wrote it — which is exactly the starting point I was trying to get away from.

That material needs a home of its own that can be shared, and there the questions change:

- How the current version is maintained when nobody owns the file.
- How a mistake gets corrected once a practice becomes obsolete.
- Which information is appropriate to share with each person.

There is enough engineering behind that for another article. But **you can start long before solving any of it**: capturing what matters, distinguishing agreements from proposals, and making clear what still applies and where to check it. Files in a repository take you a long way.

I want my contribution to show in what others can do afterwards, too. If someone can carry on my work with good judgement because I prepared the context and helped them learn, that independence is part of a job I have done well.

**Making yourself replaceable is an ability worth keeping on the team.**
