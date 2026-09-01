---
title: "Stop Being the Cable"
description: "Most teams that try an agent and quietly go back weren't short on skill. They were doing the plumbing by hand — copy, paste, carry the answer back — and that costs the same every single time. What connecting it actually involves, and which part of it you'd have to build yourself."
pubDate: 2026-09-01
tags: ["AI", "Agents", "MCP", "Context Engineering", "Mentoring"]
lang: en
translationKey: stop-being-the-cable
heroImage: "/blog/stop-being-the-cable.png"
---

Someone I know was shown how to settle a cross-border tax question by handing the client's context to an internal AI instead of losing an afternoon to search. It worked. They thought it was great. The following week they were back on Google, and stayed there.

The usual reading of that story is resistance to change, and there's something to it. But look at the mechanics for a second, because they're the whole point: **the context was handed over by a person, by hand, that one time.** It wasn't wired into anything. To repeat the trick on Tuesday you had to go find the material again, paste it again, and explain the situation again — which is more expensive than the search it replaced.

That isn't a person failing to adopt a tool. That's a person correctly noticing that the cost is paid in full every time while the benefit doesn't accumulate.

## The human as cable

Watch how work actually gets done in a team that "tried it and it didn't stick," and it looks like this. Open the system where the work lives. Copy something out of it. Paste it into a chat window. Read the answer. Copy that back into the system where the work lives.

The person is the cable. They are the integration layer, executed manually, once per task.

This is the most misdiagnosed failure I run into, for two reasons. First, it *works* — the outputs are fine, so nothing looks broken. Second, it presents exactly like a skill problem: the people who persist are the ones who tolerate the tedium, so persistence gets mistaken for aptitude and the rest get filed under "didn't take to it."

And it's invisible from above. Licence dashboards measure whether the tool was opened. They cannot distinguish between an agent that reads your repository and an agent that reads what somebody was willing to paste into it — which is the difference between a tool and a very expensive text box.

## Why this bites engineers harder than it looks

If you came from engineering, [your problem is usually the opposite one](/en/blog/if-you-came-from-engineering): you review too much, delegate below your level, and check with your eyes what a mechanism should be checking.

Here's the part I'd add now. When the agent can't see your repository, your ticket, your conventions or your last four decisions, reviewing everything is *correct*. It's producing plausible code against a codebase it has never read. The over-reviewing isn't only a habit left over from before — it's a rational response to a badly wired setup, and it will not go away by trusting harder. You can't stop checking with your eyes until something else is genuinely holding the context.

Which is why "just delegate more" is bad advice on its own. Delegate more *to what?*

## Three layers people collapse into one

"Integrating AI" gets said as though it were a single thing. It's three, they fail differently, and they cost very different amounts.

**What it knows.** Where does it get everything you consider obvious about your own shop — the domain vocabulary, the decisions already made, why that module is weird? Today this mostly lives in a colleague's head and in a chat you had in March. It belongs in files the agent reads by default, in documentation it can reach, in the repository itself. I've written the same principle from the environment side: [bootstrap the environment, not the agent](/en/blog/bootstrap-the-environment-not-the-agent) — operational knowledge that lives in a conversation instead of in the repo gets re-explained every fresh session, forever.

**What it respects.** How does it know what's acceptable here and what isn't? Conventions, definition of done, what never ships. A word of caution from my own data: [I measured what prescriptive scaffolding actually buys](/en/blog/the-scaffolding-you-pay-for), and once the agent has tools, the benefit largely disappears while the bill stays. So keep this layer thin and put the weight on mechanisms rather than prose — a check that fails is worth more than a document that asks nicely. [The skills I do keep](/en/skills) are the ones encoding something the model cannot infer from the repository.

**What it can touch.** Which systems does it act on without a human in the middle? The repository, the issue tracker, the docs, the database, the team channel. This is the layer that ends the copy-paste, and it's the one almost nobody sets up — because it's the only one that requires asking someone for permission.

Most teams have some of the first, an opinion about the second, and none of the third.

## Almost all of this already exists

Here's the part worth saying plainly, because it's what turns this from a project into an afternoon: **the connectors are standard now.** Repository, issue tracker, documentation, chat, the common databases — they exist, they're maintained by the vendors, and installing one is configuration, not development. MCP is the current plumbing standard for it, and the reason it matters isn't elegance, it's that you no longer have to build the pipe.

What still takes real work is the tail, and it's a genuine tail:

- **The internal system nobody wrote a connector for.** The in-house tool, the legacy service, the thing with an API only your team uses. [I built one of these once for Bitbucket](/en/blog/mcp-server-bitbucket) because the official server didn't exist and the community ones stopped at basic repository operations.
- **The standard one that doesn't meet your requirements.** It exists, but it can't scope permissions the way your compliance people need, or it has no audit trail, or it would expose a field that legally cannot leave.

That's the honest split. If your answer to "what are we pasting by hand?" is GitHub, Jira, Confluence or Slack, you don't have a development problem — you have a permissions request nobody has filed. The custom work is real, but it's the exception, and treating the whole thing as a build project is the most reliable way to never start.

### If you're the person who administers the subscription

This part is for you specifically, because the decision sits with you and almost nobody has told you it's a decision.

You bought seats. What you have not done — because nobody asked — is decide what those seats are allowed to reach. Until somebody does, every person on that licence is manually ferrying context between systems they already have access to, and the tool is being evaluated on a fraction of what it does. If adoption looks disappointing, this is a likelier cause than the team.

Three things worth knowing before the request lands on your desk, since the answer is usually "no" by default and nobody revisits it:

- **The connector is not a new vendor.** Connecting the agent to your repository doesn't hand your code to somebody new; it lets a tool you already pay for read a system your staff already read. The risk conversation worth having is about scope and retention, not about whether to allow it at all. (The related question — *which* tool you're allowed to use in the first place — [is its own argument](/en/blog/the-tool-youre-allowed-to-use).)
- **Read and write are separate decisions, and should be granted separately.** Almost all of the value is in reading. Almost all of the risk is in writing. Teams ask for both at once because it's one form; you can say yes to half and revisit in a month.
- **"The agent has my access" is the sentence to interrogate.** Whose access, scoped to what, and — the part that gets skipped — what can it do by default versus what stops and asks for approval? A tool that opens a pull request for a human to merge and a tool that pushes to the main branch are the same integration with two very different settings, and the difference is a configuration choice somebody has to make deliberately.

None of this is expensive. It's just unowned, and unowned decisions default to the most restrictive option that nobody has to defend.

There's a mirror image to all of this that I've written about separately: instead of connecting agents to your systems, [putting your app inside the agent your users already have](/en/blog/bring-your-app-to-the-agent). Same plumbing, opposite direction.

## What connecting it costs

An agent that can write to real systems is an agent that can write to real systems while being wrong. That's not a reason to leave it disconnected, but it does mean the questions change the moment you plug something in:

- **Permissions stop being theoretical.** "The agent has my access" is a sentence worth reading twice, especially if your access is broad. And it's only half the setting: the other half is what it may do *by default* versus what has to stop and ask. Opening a pull request, writing a comment, and merging to the main branch are three very different answers to the same connector, and the sane default is that anything irreversible waits for a human.
- **Anything it reads is potentially an instruction.** A ticket, a document, a comment from outside your organisation — text it ingests can attempt to steer it. Reading widely and writing widely are different risk levels, and it's reasonable to grant them at different speeds.
- **Internal context now flows further.** Agents are [remarkably bad at knowing which of their context was meant to stay inside](/en/blog/internal-context-leakage). Connect more sources and there's more to leak.

None of these are arguments for the text box. They're arguments for doing this deliberately, in the order that puts the read-only connectors first. If you want the full inventory of what else changes once something you built is real, that's [the map](/en/blog/what-you-still-need-to-know-to-ship) — where this now has a category of its own, sitting directly behind the ceiling.

## Four questions that tell you where you are

Cheap, and I've yet to see a team answer them without something falling out:

1. **What do you paste into the chat every single time?** The same context, a schema, a ticket, the conventions. Anything that recurs is a wiring job you're doing with your hands.
2. **Which systems does your actual work live in?** List them. Repository, tracker, docs, spreadsheets, database.
3. **How many of those can the agent reach on its own?** For most teams, honestly: zero.
4. **Who authorises access to the one that matters most, and how long do they take?** If you don't know, that's the first task — not a technical one.

The last question is the one that stalls teams, and it's the one that has nothing to do with AI.

## The test

Here's the way I'd check whether an agent is genuinely part of how a team works, or a demo people are being polite about.

**If the clipboard stopped working tomorrow, how much of it would survive?**

If the answer is "none of it," the tool was never integrated. A person was.

---

*A follow-up to the three pieces on what building software with agents actually requires: [the map](/en/blog/what-you-still-need-to-know-to-ship), [starting from zero](/en/blog/if-youre-starting-from-zero), and [coming from engineering](/en/blog/if-you-came-from-engineering). If you'd rather work through this with your own team — including which of your systems has a connector already and which one doesn't — [that's what I do](/en/mentoring).*
