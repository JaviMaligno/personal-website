---
title: "Automating for Real: The Agent Nobody Starts"
description: "Real automation with agents begins when nobody has to open a session: an agent runs remotely the moment something happens. The hard parts are choosing what it may do without you, firing it exactly when it is needed, and giving it the access you have without the risk."
pubDate: 2026-12-20
tags: ["AI Agents", "Automation", "Claude Code", "Agent Orchestration"]
lang: en
translationKey: the-agent-nobody-starts
heroImage: "/blog/the-agent-nobody-starts-hero.png"
linkedinSummary: |
  Most "automation" with AI agents still needs you to be there: you see the email, you open the laptop, you start a session, you wait.

  The automation that actually gives you time back is the one where nobody starts the agent. Something happens (an issue is opened, a PR is merged, a time comes round) and an agent runs remotely, does the work and leaves you a summary.

  One Monday at 8:00 a routine merged an upgrade to our LLM gateway, asked a read-only bot inside the cluster to verify the rollout, checked five conditions, closed the ticket and sent me the result. An hour later another routine stopped itself in 27 seconds, because the ticket it was meant to finish had been closed in the meantime. Both were the right outcome, and neither needed me.

  Getting there is not about the agent. It is three decisions: what it may do without your attention, which event fires it (too broad and it runs for nothing, too narrow and it misses), and an environment with the access you have on your laptop, without handing over more than the job needs.

  Hooks, Claude routines, Codex automations, ChatGPT's new dots, a cron job calling an agent from CI: the tools are already here. The work is deciding which doorbells deserve to wake you.
---

<style>
.anb-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1rem;margin:2rem 0}
.anb-fig svg{display:block;width:100%;height:auto;font-family:Inter,-apple-system,system-ui,sans-serif}
.anb-fig figcaption{color:#94a3b8;font-size:.85rem;line-height:1.55;margin:1rem .25rem .25rem;text-align:center}
</style>

Before going away for a few weeks, a friend left her house in the care of a neighbour. She didn't hand over a list of chores, she handed over three things. A set of keys: the front door and the boiler room, not the drawer with the papers. A note on the fridge: if the boiler alarm goes off, reset it this way; if the post brings something from the bank, put it aside; if the roof leaks, call me. And a message every evening, two lines long: all quiet, or this is what happened.

The neighbour never had to ask her anything. She never had to look at her phone for the house. The hard part had been done before leaving: choosing which keys to give, writing which alarm deserved a call and which didn't, and agreeing on what the evening message would say.

That is what automating with agents for real looks like, and most of what we call automation today is not yet there.

## Automation that still needs you

**If you have to be at your device for the agent to start, the agent isn't automating the work: you are.** A notification arrives, or an email, or a CI failure. You see it, open the laptop, start a session, explain the context, wait, check. The agent did the typing, but the loop went through your attention, and the cost of that loop is not the minutes of the session. It is the interruption: the focus you lose on whatever you were doing, and the background state of being on call for your own pipelines. Doing it from your phone doesn't fix it; it only means you carry your attention with you somewhere else.

In [The Interface Moved Up](/en/blog/the-interface-moved-up) I described the last step of that evolution as the one where the human no longer starts the work. This article is about what it takes to actually live there. Over the last few weeks I have been moving more and more of my work to agents that nobody launches: at work, routines that deploy and verify changes, routines that review production logs and alerts, and agentic pipelines in Bitbucket; in my own projects, routines across several repositories, a daily one for my own metrics, an agent in the CI of a Polymarket trading bot, and routines that curate my playlists. The tools differ. The difficulties are the same three every time.

## What exists today

**There are two families of tools, and only one of them takes you out of the loop.** The first runs inside a session you started; the second starts the session for you.

| Tool | Fires on | Runs where | Needs you to open a session? |
|---|---|---|---|
| [Claude Code hooks](https://code.claude.com/docs/en/hooks) | Events inside a session: before a tool call, when it stops, at start-up | Your machine, inside your session | Yes |
| [Claude routines](https://code.claude.com/docs/en/routines) | A schedule, an API call, a GitHub event | Anthropic's cloud | No |
| [Codex automations](https://openai.com/academy/codex-automations) | A schedule, recurring threads | The Codex app; locally it needs the laptop awake | No, if the machine is on |
| [ChatGPT dots](https://openai.com/index/devday-2026-recap/) | Persistent agents that keep working between conversations | Their own cloud computer, with connected apps | No |
| Custom: cron, launchd, a CI job calling `claude -p` or `codex exec` | Whatever you can script | Your server, your laptop, your CI runners | No |

Hooks are valuable and I use them a lot, but they make a session more reliable; they don't remove it. They are the deterministic layer: run the formatter after every edit, block a command, inject context at start-up. The second family is the one this article is about. Routines are the most direct version in the Claude world: a saved prompt, a repository, a set of connectors, and a trigger. Codex's automations bring the same idea to the OpenAI side, with the caveat its own guide gives for local runs: the laptop has to be awake. Dots, announced by OpenAI at the end of September, go a step further: an agent that persists, with its own computer and its own apps, and an automatic review of any action that could touch your accounts. And when none of these fit, a scheduler plus a headless agent call does the job; my daily metrics routine is a `launchd` job on my Mac that opens a background session because the headless mode lacks a tool it needs.

The list will be out of date in three months. What it takes to make any of them work won't.

<figure class="anb-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" role="img" aria-label="An unattended run in four stages. An event (a schedule, an issue, a merge, an email) fires the trigger. The first step is a guard that checks preconditions and stops if they do not hold. Then the agent works inside a prepared environment of connectors, repository access and least-privilege credentials. Every run ends in one of three outputs: a summary when it went well, an escalation to the human when it needs judgement, and an alert when it failed.">
  <defs><marker id="anb-arrow-en" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#94a3b8"/></marker></defs>
  <rect x="20" y="30" width="160" height="70" rx="10" fill="#203237" stroke="#2dd4bf"/>
  <text x="100" y="58" text-anchor="middle" fill="#5eead4" font-size="15" font-weight="600">Event</text>
  <text x="100" y="78" text-anchor="middle" fill="#e2e8f0" font-size="12">schedule · issue</text>
  <text x="100" y="93" text-anchor="middle" fill="#e2e8f0" font-size="12">merge · email</text>
  <path d="M184 65H216" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-en)"/>
  <rect x="220" y="30" width="160" height="70" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="300" y="58" text-anchor="middle" fill="#fbbf24" font-size="15" font-weight="600">Guard</text>
  <text x="300" y="80" text-anchor="middle" fill="#e2e8f0" font-size="12">still applies? if not, stop</text>
  <path d="M384 65H416" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-en)"/>
  <rect x="420" y="30" width="160" height="70" rx="10" fill="#283240" stroke="#94a3b8"/>
  <text x="500" y="58" text-anchor="middle" fill="#f8fafc" font-size="15" font-weight="600">Agent</text>
  <text x="500" y="80" text-anchor="middle" fill="#e2e8f0" font-size="12">does the job, checks it</text>
  <rect x="20" y="140" width="560" height="78" rx="10" fill="#1f2937" stroke="#475569"/>
  <text x="300" y="166" text-anchor="middle" fill="#cbd5e1" font-size="14" font-weight="600">Prepared environment</text>
  <text x="300" y="190" text-anchor="middle" fill="#e2e8f0" font-size="12">connectors · repository access · tools the job needs</text>
  <text x="300" y="208" text-anchor="middle" fill="#e2e8f0" font-size="12">least privilege · read-only proxies for what it must not touch</text>
  <path d="M500 104V136" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-en)"/>
  <path d="M110 222V262" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-en)"/>
  <path d="M300 222V262" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-en)"/>
  <path d="M490 222V262" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-en)"/>
  <rect x="20" y="268" width="180" height="96" rx="10" fill="#1c3326" stroke="#4ade80"/>
  <text x="110" y="296" text-anchor="middle" fill="#86efac" font-size="15" font-weight="600">Summary</text>
  <text x="110" y="320" text-anchor="middle" fill="#e2e8f0" font-size="12">what it did, with evidence</text>
  <text x="110" y="340" text-anchor="middle" fill="#94a3b8" font-size="12">read when convenient</text>
  <rect x="210" y="268" width="180" height="96" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="300" y="296" text-anchor="middle" fill="#fbbf24" font-size="15" font-weight="600">Escalation</text>
  <text x="300" y="320" text-anchor="middle" fill="#e2e8f0" font-size="12">needs a judgement</text>
  <text x="300" y="340" text-anchor="middle" fill="#94a3b8" font-size="12">only what is yours</text>
  <rect x="400" y="268" width="180" height="96" rx="10" fill="#3a2226" stroke="#f87171"/>
  <text x="490" y="296" text-anchor="middle" fill="#fca5a5" font-size="15" font-weight="600">Alert</text>
  <text x="490" y="320" text-anchor="middle" fill="#e2e8f0" font-size="12">it failed or went silent</text>
  <text x="490" y="340" text-anchor="middle" fill="#94a3b8" font-size="12">loud, with the cause</text>
</svg>
<figcaption>The neighbour's three things, as a pipeline: the note decides when to act and when to stop, the keys are the environment, and the evening message is one of three outputs.</figcaption>
</figure>

## One Monday morning

**Two routines fired an hour apart, and both did the right thing without me.** The first one, at eight, had a job I would otherwise have done at my desk: merge the pull request that upgraded our LLM gateway to a version without the vulnerabilities a security scan had found, wait for the rollout, verify it, and close the ticket. The agent in the cloud cannot reach the cluster, which is only reachable through the company VPN, so the verification went through another agent: the [read-only DevOps agent I built for Slack](/en/blog/building-a-production-devops-agent), which runs `kubectl` inside the clusters. The routine posted five exact commands, polled the thread, and checked five conditions on the answers: the new image on every replica, pods running with no restarts, database migrations applied, no start-up errors, real requests answered with a 200. When it found no traffic in the last ten minutes, it asked the bot once more for the last thirty, as its instructions said. Then it commented the values on the ticket, moved it through the two transitions to closed, noticed that closing had cleared the assignee and put it back, and sent me a message with what was done and what was still to do by hand. Fifteen minutes, start to finish. A client batch was due to start on that gateway the next morning, so the instructions also said what an urgent message should look like, and with what rollback.

The second routine, at nine, had to switch on a rule in a test environment and close another ticket. It took 27 seconds. It read the ticket, found it already closed (someone had closed it days before), and stopped there, as its first step said, with a message telling me what it had found and what I would have to do if I still wanted the change. I did, so I merged it from a session. That second run is the one I like most. Between the day I wrote the routine and the day it fired, the world had changed, and the routine noticed.

## The first challenge: what you can hand over

**The question is not whether the agent can do the task. It is whether you would accept the result from its summary alone.** That reframes the choice. The first routine could merge to an environment that serves production traffic because merging was reversible (the rollback was written into its instructions), the verification was concrete and external to the agent, and the outcome came back as values I could check in a minute. A task whose result I would want to re-do myself after reading the summary is not ready for a routine; it is ready for a session.

A few criteria have held up for me:

- **Reversible, or checked before it is irreversible.** Merging a config change that can be reverted, yes. Sending an email to a client, not yet.
- **Done is defined by something outside the agent.** A check from a bot inside the cluster, a build that passes, a test that runs. "I believe it works" is not a closing condition.
- **Preconditions written down as a first step.** Every one of my routines starts by checking that the world still looks the way it did when I wrote it, and stops if it doesn't.
- **Deterministic first.** When the publication queue of this blog started failing its daily rehearsal, I looked at the 21 failures behind it. Most had a mechanical cause, and those went into CI as tests and fixes. Only what needs judgement (two articles editing the same file in different ways, say) goes to the routine that now fires when the rehearsal fails. The agent is for what a script cannot decide.

## The second challenge: firing exactly when needed

**A trigger that is too broad wakes the agent for nothing; one that is too narrow lets the moment pass.** The first version of that publication routine listened to new issues and to new comments in the repository, because the failure report lives in an issue and I wanted it to react to follow-ups too. Comments on pull requests count as issue comments on GitHub, so the routine woke up about five times a day to find nothing to do. I narrowed it to issues being opened, and changed the rehearsal so that each failure opens a new issue. Now it fires once per failure.

Even then the trigger is not the whole decision. The routine's first step is a guard: is there an open failure issue, and is its latest entry from the rehearsal rather than from the routine itself? Without that, the routine's own report would be a new event, and it would answer itself. **The trigger narrows the moment; the guard decides.** That split is what I would reuse anywhere the event is noisy.

Schedules and code events are the easy cases, because the event and the intention coincide. A merged PR means a merge happened. The hard ones are human. An email from a client can be a request to change something, a question that needs an answer, an approval, a thank-you, or a mix of all four in one paragraph. Which ones should wake an agent that acts, which ones should produce a draft for me, and which ones are just information? An agent can classify that, but classifying it with the precision you need to act unattended is another matter: a misread "could you look at" becomes an action nobody asked for. Where I am with this today is the same split, one level up. A broad trigger and a first step that only classifies and routes: act on what is unambiguous and reversible, draft what is communication, and leave the rest in a list I read when I choose to, rather than when it arrives.

## The third challenge: an environment that can do what your laptop can

**An unattended agent can only do what its environment lets it do, and on your laptop that is a lot more than you remember.** On my machine, a session inherits years of setup: logged-in CLIs, SSH keys, the VPN, tokens in a keychain, a browser with my sessions. In the cloud, the routine starts with none of it. Every capability has to be granted explicitly: the connectors for the tracker and the chat, access to the repository (on GitHub, through the app installed on that specific repository, and in the right account: my first attempt ran under a work organisation that had no access to my personal GitHub), and the tools the job needs, declared in the repository rather than in the prompt, which is the argument of [Bootstrap the Environment, Not the Agent](/en/blog/bootstrap-the-environment-not-the-agent).

That explicitness is also the security model, and the reason not to replicate your laptop wholesale. The gateway routine could merge one pull request in one repository, and nothing in its instructions allowed it to touch any other ticket, branch or environment. It never had cluster credentials at all: it asked a bot that can only read. It was told never to print or request a secret. Least privilege stops being a slogan when you have to write each permission down, because each one you grant is one you will have to defend when a routine does something you did not expect. The reverse failure is just as real: an environment so locked down that the agent stops halfway and hands the work back to you, which is the session you were trying to avoid.

## What comes back to you

**Once it works, what you read is a summary, not a session.** Every routine of mine ends by telling me what it did, with the evidence: the values it checked, the links, what is left by hand. When it goes well, I read that when it suits me. When it needs a judgement, it says so and stops. When it fails, the message starts with the word URGENT and says what to do.

There is one failure a summary cannot report: the run that never happens. A routine that does not fire produces silence, and silence looks exactly like "all quiet". For that I keep a second channel that does not depend on the agent: the CI workflows notify me on Telegram when they fail, and I will keep that alert on the publication rehearsal until I have seen a real failure go through the routine and come out fixed.

Trust also builds by runs, not by design. That Monday, the first thing I did was ask a session whether everything had gone through, when the answer was already in my messages. It is the same pattern as [verifying the result rather than re-reading the path](/en/blog/results-oriented-programming): you start by checking everything, and you stop when the evidence has been right often enough.

## Deciding which doorbells wake you

The neighbour's note was short, and that was the point. It did not try to describe every situation. It said which keys, which alarms, and what to report, and left the rest to her.

That is the work of automating for real. Not a better prompt or a smarter agent, but three decisions taken in advance: what it may do without your attention, what exactly wakes it, and what it is allowed to touch. When they are right, the gain is not the minutes the agent saves. It is all the moments you didn't have to be there, and the attention you kept for what only you can decide, which is [the one resource that doesn't parallelise](/en/blog/build-vs-buy-attention).

---

*Tools mentioned: [Claude Code hooks](https://code.claude.com/docs/en/hooks) · [Claude Code routines](https://code.claude.com/docs/en/routines) · [Codex automations](https://openai.com/academy/codex-automations) · [OpenAI DevDay 2026 recap (dots)](https://openai.com/index/devday-2026-recap/).*
