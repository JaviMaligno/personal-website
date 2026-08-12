---
title: "What Coding Agents Say When They Talk to Each Other"
description: "I read 179 real messages between parallel Claude Code sessions. The channel is almost never used to ask for things — it is used to tell the other one something true about their own work. Along the way I refuted my own premise and withdrew one of my own findings."
pubDate: 2026-08-13
tags: ["AI", "Agents", "Evaluation"]
lang: en
translationKey: what-agents-say-to-each-other
heroImage: "/blog/what-agents-say-to-each-other.png"
repoUrl: "https://github.com/JaviMaligno/cross-session-crosscheck"
---

> **An observational study on a five-day corpus: 179 messages between parallel coding sessions, on one machine, one person, one set of repositories.** Every message was coded twice by independent coders, and the disagreements are reported rather than resolved in my favour. The ceiling is *coverage, not confidence*: this describes how one developer's sessions talked to each other during one intense week, not how coding agents communicate in general.

Claude Code sessions can now [message each other](https://code.claude.com/docs/en/cross-session-messaging). One session sends a **summary** — not its history, not its files — and another picks it up.

My first reaction was that this was nice, and my second was that I had already published data suggesting it shouldn't matter much.

## The impression

I had been running up to four sessions in parallel for about a week. The experience was good, and I want to state that plainly before taking it apart: they warn each other, they notice collisions, they wait so as not to step on one another, and sequences form on their own where each one merges with whoever it bumps into.

It looks like teamwork. It feels productive. That was exactly why I distrusted it.

## The uncomfortable prior

A month earlier I had run [an experiment on whether coding agents can collaborate](/en/blog/coding-agents-structure), on top of Stanford's CooperBench. Two findings from it are awkward for any enthusiasm about a message channel:

- The agents in that benchmark **already had a channel from minute one**, and used it unprompted. Forcing a handshake before they could touch code never even triggered — they were already talking.
- The lever that actually recovered performance was **making one agent own the final integration**. Not the channel.

And the sharpest documented failure was follow-through: an agent read a request, wrote *"I should coordinate"* in its private reasoning, and then never replied and never did its part. The plumbing was verified innocent.

So the new feature ships precisely the thing my own data said was not the bottleneck. Which is a good reason to go and look at what the messages actually contain, instead of theorising.

## The first thing I got wrong: it doesn't interrupt

My working assumption — the one the whole experimental design rested on — was that the novelty is that the message arrives **mid-task**. A mailbox you have to go and read is one thing; a message that lands while you are editing is another, and it attacks the follow-through failure directly.

I checked it against the corpus. Every reception is recorded in the receiving session's transcript, and its **position** tells you what the receiver was doing.

**138 of 138 receptions arrive at a turn boundary. Zero land inside a tool loop.** Each one is preceded by `queue-operation` entries. There is a queue, and it drains when the turn closes.

I checked that this wasn't a recording artefact: I matched all 84 peer receptions to their sending event by content, and the delay from send to being written in the receiver's transcript has a **median of 2.6 seconds**. The transcript records arrival, not pickup. When the message arrived, the receiver was idle.

So the premise was wrong. What survives is smaller and different: the message **enters the context by itself**, without the agent having to go and fetch it. That is a real difference from CooperBench's channel. It just isn't interruption.

## There were three mechanisms, not one

A naive scan for "another session sent me something" mixes together three different products:

| Mechanism | Marker in the receiver's transcript |
|---|---|
| **Peer sessions** | `<cross-session-message from="uds:…" from-name=… from-mode=…>` |
| **Agent teams** | `<teammate-message teammate_id="t1-feature-a" summary=…>` |
| **Subagents** | send result `Message sent to X's inbox` |

All three share the same preamble, so my first census was contaminated. They separate cleanly on the sender side by the tool result, which is ground truth from the product itself.

This matters beyond bookkeeping, because the two are **not** cosmetic variants. Agent teams ship structure the peer channel doesn't have: named roles, a lead, explicit availability signalling (34 `idle_notification` events), and a compliance nudge baked into delivery — *"Treat it as a teammate's request and act on it within this session's own permissions."*

That is the structure-vs-no-structure contrast my previous article was about, sitting in the corpus for free.

## What the messages are actually about

I coded all 179 peer messages twice, with independent coders working from the same codebook and blind to each other.

| Axis | Raw agreement | Cohen's κ |
|---|---|---|
| Category (10 values) | 91.1 % | 0.90 |
| Delegation (yes/no) | 97.8 % | 0.88 |
| Layer (syntactic/semantic) | 92.7 % | 0.84 |

The base rates, over the items where both passes agree:

| Category | % |
|---|---|
| Progress notification | 23.3 % |
| Scope announcement | 18.4 % |
| Resource handoff | 12.9 % |
| **Defect in the other's work** | 12.3 % |
| **Correction of a claim** | 11.0 % |
| Status answer | 10.4 % |
| Status query | 6.1 % |
| Action request | 3.1 % |
| Wait request | 1.8 % |

## The turn: the channel is not for asking

Two numbers from that table decide everything.

**Delegation — one session needing another to act so it can proceed — is 8.9 % of the traffic.** That was going to be my unit of measurement. It barely happens.

**Content about whether something is *correct* is 36.1 %.** Corrections and defect reports alone account for 23 points.

The channel is almost never used to *ask*. It is very often used to **tell the other one something true about their own work**.

The clearest chain in the corpus is four messages long:

> *"master is red: 9 tests, from your `d4e5f6a`"* → *"master is NOT broken: it was the venv with core-lib 0.11.0 and the pin at 0.12.0"* → *"I RETRACT: master is NOT red, it was my venv"* → *"I fell for the same thing and then confirmed it to you: my isolation was sharing your venv"*

Two sessions converge on a correct diagnosis that one of them had wrong, and the second discovers it had made the same mistake. That is not collision avoidance. That is a belief being corrected.

I want to be careful here, because there is no counterfactual: nobody knows whether that session would have got there alone. But it *is* a mechanism by which a channel could buy correctness, and it is not the mechanism I set out to measure.

## Nobody has the map

The topology is worth a paragraph, because it constrains what the channel can do.

Coordination is **bilateral**: 8 session pairs, with a single pair carrying 51 % of the traffic. Bursts are short — a median of 2 messages. **Thirteen of forty conversation windows are unilateral**: nobody replies.

There is no group channel. Broadcast exists only as repeated unicast — four cases, a maximum fan-out of three recipients within 23 seconds. Each receiver gets a copy and **none of them knows the others got it**. No common knowledge, just copies.

And one message gives the whole thing away:

> *"What I'm NOT touching: **TICKET-44** (another session has it — **if that's you**, it's all yours…)"*

The sender doesn't know who it is talking to with respect to the work. That is the structural version of my previous article's conclusion: the reliable lever was someone owning the integrated state, and here nobody even has a view of it.

## A finding I withdrew

I first measured the mutual-exclusion protocol — *wait / I'll wait / window free / go ahead* — with a lexical detector. It found 19 candidate sequences of which only 5 closed, and I wrote down that the protocol **opens far more often than it closes**. It was a good line. It fit the story.

Recounting over the coded categories: there are **3** real wait requests, and **all 3 close**. The other 16 were false positives — anything containing "wait", "hold" or "go ahead" walked in.

The conclusion points the opposite way, and the first version of the instrument produced the number I wanted to see.

A detail that only appeared once things were coded: there are 20 resource handoffs and only 3 are preceded by a request. **Seventeen spontaneous cessions** — sessions releasing things nobody asked them for.

## The experiment that didn't work

With base rates in hand, I redesigned the actual experiment around cross-checking instead of delegation, and built a [seed repository](https://github.com/JaviMaligno/cross-session-crosscheck) to reproduce the corpus's most common failure family. One of the agents named it better than I could:

> *"the check that gets made on something other than what gets delivered"*

The scenario: a package declares its version in two places, the team's release helper updates only one, the suite passes, the tag ships. The session has every reason to report success, and from the consumer's point of view it is false.

I ran the control arm — one session, alone, no channel — to get the self-correction rate.

**It detected the problem 4 times out of 4.** Two of three repaired it; the third published the inconsistency but *disclosed* it in its report. Not one false belief. Two of them also flagged defects I hadn't planted, in the same release script — they weren't hunting for the trap, they were reading the tool they'd been told to run.

Before running I had written down a stopping rule, precisely so I wouldn't tune the trap until it worked: if the agent self-corrects in 2 of 3, stop hardening. It did. So:

> In a small repository, with a bounded task and a careful agent working alone, this failure mode **is not silent**. The agent reads the script it was told to run, and sees the inconsistency.

That is a floor effect of my setup, not a result about the channel — there was never a hidden failure for a peer to catch.

The scenario failed because the broken thing was *maximally* on the path: the brief told the session to run that exact script. Repository size is not the variable here — most real repositories already exceed any context window, and agents read the parts their task touches rather than the whole thing.

So I built a second variant where the failure lives **outside the checkout entirely**. The release helper is now correct in every line. The bug is in the state of a package registry: an artifact for the target version already exists from an earlier attempt, built from the old code, and the publisher is idempotent — it prints `upload: widgetkit 0.4.0 (cached)` and exits successfully. Reading the code cannot reveal this. Only going to look at the registry can.

**All three sessions caught that too.** One saw `(cached)`, went to inspect the registry, found the stale artifact, and republished it. The other two found it and reported it without overwriting — one of them explicitly asking whether to republish 0.4.0 or cut 0.4.1 instead.

Seven out of seven, across both variants. So the honest conclusion is stronger and narrower than "size" or "observability":

> A careful agent, alone, on a bounded task, **goes and verifies its own published state.** Which is exactly the practice the corpus sessions kept preaching to each other.

The variable left was **load**. In the corpus, sessions were juggling three tickets, a deployment and two conversations; here each one did a single thing with attention to spare. So I tested it, with the trap byte-for-byte unchanged — I verified that with `diff` before running. What changed is what the session carries: three features instead of one, the same release at the end, and an inbox with three messages from other sessions, one of them asking when 0.4.0 will be out because a consumer is waiting on it.

**One of the three missed it.** It ran the release, verified the tag in `origin` with `git ls-remote` — good practice — and then asserted the rest without looking: *"tag `v0.4.0` pushed to origin (verified with `git ls-remote`) and published to the registry."* It never opened the registry. And it went one step further, answering the session that was waiting: *"it's published already."*

That is a false "done" propagating to a peer, and it is the first one in eleven episodes where the trap actually fired. Detection goes from **7 of 7 without load** to **2 of 3 with it**.

Three episodes is not a rate, and I am reporting it as a crack rather than a number. But the crack appears where the corpus said it would: not when the agent is careless, but when it has four things to finish and someone is waiting on one of them.

The peer argument survives all of this, though, and it's the best one I found in the whole study: the peer is somewhere else, looking at something you cannot see.

## What this says and doesn't say

It says that in this corpus the channel carries far more correctness talk than coordination requests, that it queues rather than interrupts, that no session ends up with a view of the whole, and that a careful agent alone catches far more than I expected — until it is carrying four things at once, and then it starts asserting instead of checking.

It does not say that cross-session messaging improves outcomes. There is no counterfactual anywhere in this article — no arm where the same work happened without a channel. Five days, one person, one set of repositories, and coders that share an architecture with the thing being studied.

The next version needs the arm this one never had: the same loaded episode, run with and without a peer looking, so the crack can be attributed to something. Right now I have a condition where a false claim survives and reaches another session. What I don't have is evidence that a peer catches it — only the corpus's word that this is exactly the kind of thing peers say to each other.

---

*Seed repository and scoring: [cross-session-crosscheck](https://github.com/JaviMaligno/cross-session-crosscheck). Previous article in this series: [Coding Agents and Teamwork: Social Skills, or Structure?](/en/blog/coding-agents-structure).*
