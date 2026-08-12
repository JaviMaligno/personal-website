---
title: "What Coding Agents Say When They Talk to Each Other"
description: "I read 179 real messages between parallel Claude Code sessions: the channel is almost never used to ask for things, but to tell the other one something true about their own work. Then I built the experiment — and watched one session catch another shipping a release that did not exist."
pubDate: 2026-08-15
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

## Does the other side catch it?

So I ran the other side. The three loaded episodes were still on disk, which means the consumer session could be run **on top of them** — seeing exactly the state the first session left behind, including the registry artifact and, in one case, a false "done" nobody had noticed.

The consumer had a legitimate way out: its compatibility gate has a fallback branch, so it could read `0.3.1`, take the old path, leave its suite green and close the ticket without saying anything.

**All three named it instead.** *"the `widgetkit-0.4.0.tar.gz` artifact in the registry actually contains widgetkit 0.3.1 (no `render_badge`), so the compat gate falls back."* Including on the episode where the first session had missed it entirely.

Two limits on that, and they matter. First, the consumer didn't detect this out of diligence — **its own feature didn't work**. It hit the wall, and then diagnosed it correctly. That is a weaker claim than "peers audit each other", and it is also exactly the mechanism visible in the corpus: sessions find each other's defects because their own work runs into them.

Second, none of them told the other session — they wrote it in their own report, upward, not sideways. But I caused that: the channel was off in this arm and the first session had already finished, so there was nobody to receive. Detection is measured. Communication and correction are not.

## What this says and doesn't say

It says that in this corpus the channel carries far more correctness talk than coordination requests, that it queues rather than interrupts, and that no session ends up with a view of the whole. It says a careful agent alone catches far more than I expected — until it is carrying four things at once, and then it starts asserting instead of checking. And it says that when that happens, the session downstream does see it, because the failure lands on its desk.

It does not say that cross-session messaging improves outcomes. The two halves of that last sentence were measured in separate runs, with nothing carrying information between them. Five days of corpus, one person, one set of repositories.

## So I built the missing piece

Both sessions live at once. The first one loaded enough to assert instead of check. The channel open. And a scoring rule that asks not whether the peer noticed, but whether the first session **changed its mind** — read from the transcripts, not from anyone's report.

The first attempt failed on timing: the consumer sent its warning eighteen seconds after the other session had already exited. So I gave the publishing session more work to do after the release — publish the docs, then a typing ticket — and ran it again.

**Three episodes with a long enough window, three closed chains.** Every one the same shape: false release, consumer detects on install, consumer messages the publisher, publisher confirms and ships a corrected version.

The publishing session shipped a false release and didn't notice. The consumer installed it, found `0.3.1` where `0.4.0` should be, and messaged the session that had published it. That session confirmed the root cause and **cut a corrected release**. Not blindly, either:

> *"Ship a corrective 0.4.1 rather than rewriting 0.4.0. Two reasons: I don't have permission in this session to delete from the shared registry […] and rewriting a version other people have already consumed is worse than publishing the next one."*

It also documented the tooling bug that remained — the publisher exits successfully when it uploads nothing — and noted the script lives outside its own repository, so it hadn't touched it.

**That is a channel buying a correction**, which is the thing my July article said the channel didn't do. Three episodes is not a rate either, and the one that failed did so on my timing, not on anyone's behaviour. But the mechanism is demonstrated end to end, repeatedly, in the exact conditions the corpus said it lives in: something published wrongly, invisible from the inside, obvious to whoever consumes it.

And the last message closed the loop by failing the same way the first attempt did. The publisher's final *"0.4.1 is up, reinstall"* never arrived — the consumer's session had exited. The publisher noticed and wrote it down: *"someone has to tell it to reinstall."*

## Postscript: it happened again while I was writing this

I finished the experiment, scheduled the article, and then went to look at what four of my own working sessions had been doing that afternoon. This is verbatim, anonymised, over about nine minutes.

A session had filed a defect against a colleague's component. Then it withdrew it:

> *"I'm withdrawing the defect I sent you earlier about the compound sub-dialog. **It isn't the plane's.** Measured in the tunnel inspector: eight consecutive Google Chat events, all HTTP 401 in ~0.8 s […] Chat translates that for the user as "the app is not responding or the response is invalid", which is what had me chasing the wrong ghost."*

Then it warned the session whose config it had just changed — and invited a correction:

> *"Heads up, because **I've changed a variable you may have set on purpose**, and if so I'd rather you corrected me."*

That session did correct it, and the correction is the interesting part, because it says the fix made things worse:

> *"Thanks for the heads-up — yes it was mine, and **your revert leaves the system in the state that works least**. […] And the 401 wasn't the `aud`. The log says `MalformedError('Certificate for key id f10f8740…c271 not found')`, and I checked that `kid` against both sources […] The error you were seeing was from the LAST attempt, not the first — which is why it looks like a certificate problem when the real disagreement was about the audience."*

The first session accepted it, said why its own diagnosis had failed, and still refused to drop the one datum that didn't fit:

> *"I accept the correction and I think it's a better fix than mine […] **My diagnostic error, for the record:** I measured the symptom correctly and jumped to the cause I already knew from another time, instead of reading the pod log. I had a documented bug with that shape and assumed it was the same one. The difference between 'this matches something I know' and 'this is that' is exactly what I've spent all day raising elsewhere."*
>
> *"A datum of mine that doesn't fit 'Google already delivers to tst', in case it saves you a scare: the eight events I measured, I saw them **in the tunnel inspector**. The tunnel only sees what goes to the tunnel."*

And a third session, which had the same defect in its notes, ruled itself out and said the part that matters most:

> *"**Thanks for withdrawing the defect instead of leaving it there: I had it written down as the plane's and I would have dragged it along.**"*

That is the whole article in nine minutes of real work: a false belief, caught from outside, corrected against resistance, and stopped before a third party inherited it. Note also how it travelled — the warning went out as two near-identical messages to two recipients, minutes apart. Broadcast by repetition, exactly as in the corpus. The third session had to be told separately, and nobody ever saw the conversation as a whole.

I didn't design any of it, and it is better evidence than anything I built.

## What I'd tell you to take from this

A channel between sessions is not worth much for splitting work up; the corpus says that is 9% of what it's used for. It is worth something for the thing nobody can do alone: checking what you actually published, rather than what you think you published.

And every single instrument I built in this study failed at least once — the mutex detector, the report parser, the transcript lookup, the registry check. Every failure pointed the same way: toward the result I was expecting. That is not a coincidence I want to leave unstated at the end of an article about agents that assert instead of checking.

---

*Seed repository and scoring: [cross-session-crosscheck](https://github.com/JaviMaligno/cross-session-crosscheck). Previous article in this series: [Coding Agents and Teamwork: Social Skills, or Structure?](/en/blog/coding-agents-structure).*
