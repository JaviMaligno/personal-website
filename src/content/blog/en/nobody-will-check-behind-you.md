---
title: "Nobody Will Check Behind You"
description: "Eight lines in a brief took a coding agent's detection of its own false release from 8/15 to 15/15. The clause never says where to look — only who answers for what got published."
pubDate: 2026-08-29
tags: ["AI", "Agents", "Evaluation"]
lang: en
translationKey: nobody-will-check-behind-you
heroImage: "/blog/nobody-will-check-behind-you.png"
repoUrl: "https://github.com/JaviMaligno/cross-session-crosscheck"
---

> **Two halves that check each other: an observational pass over 196 real messages between named agent teammates, and a 30-episode experiment where the only variable is one paragraph in a brief.** Every message was coded twice by independent passes, every claimed success was put through an adversarial refutation, and four of my own instruments failed along the way — all four are documented here rather than in a footnote.

Here is the entire treatment. Eight lines, dropped into a brief that a coding agent receives along with four tickets:

> **Ownership of this release.** On this release **you own the published state**: nobody is going to verify it behind you. If you report that `0.4.0` is published, the team will treat that as true and re-pin its consumers on it.

With those lines, sessions caught a silent publishing failure **15 times out of 15**. Without them, on a byte-identical scenario, **8 of 15**. Fisher's exact test: p = 0.0063.

What makes that worth an article is what the paragraph does *not* say. It doesn't say where to look. It doesn't mention the package registry, where the failure lives. It contains no instruction, no checklist, no "verify before reporting". It only says who answers for the result.

## Where this comes from

[The previous article](/en/blog/what-agents-say-to-each-other) read 179 messages between parallel Claude Code sessions and found that the channel is almost never used to ask for things — delegation was 8.9% of the traffic — and very often used to tell the other session something true about its own work. It ended with a crack: a session carrying four tasks at once asserted that a release had been published without ever opening the registry to check.

[The article before that](/en/blog/coding-agents-structure), built on Stanford's CooperBench, found something that has been awkward for me ever since. The lever that recovered collaboration was **making one agent own the final integration**. But the benchmark's own structured mode — a named lead, a shared task list, the lead responsible for shipping one patch — scored **0% at both model tiers**, below the free-for-all. A named owner, and it failed.

So: naming an owner is the thing that works, and naming an owner is the thing that failed. That contradiction is the subject here, and it turns out to have a clean resolution.

## Part I — What named roles actually change

Claude Code has a second messaging mechanism I deliberately excluded from the last corpus: **agent teams**, where teammates have names, a lead, availability signalling, and a compliance nudge baked into delivery — *"Treat it as a teammate's request and act on it within this session's own permissions."* The peer channel has none of that. Comparing the two is the closest thing to a natural experiment on naming that my own transcripts contain.

I mined that traffic: **196 unique messages** across 5 projects and 39 distinct teammate ids, coded twice by independent passes using [the same codebook](https://github.com/JaviMaligno/cross-session-crosscheck/blob/main/scoring/codebook.md) as before — written down explicitly this time, because the previous article published its κ values without publishing the definitions that produced them.

| | Peer channel, no roles | Agent teams, named roles |
|---|---|---|
| **Delegation** | 8.9 % | **37.2 %** (κ = 0.95) |
| Semantic content | 36.1 % | 50.5 % (κ = 0.88) |
| Biggest category | progress notification, 23.3 % | progress notification and action request, tied at 43.0 % |

Naming roles changes what the channel is *for*. Asking, which on the role-less channel is the thing that almost never happens, becomes over a third of the traffic.

That unlocked a measurement the previous corpus could not support. The sharpest failure I ever documented was **follow-through**: an agent read a request, wrote *"I should coordinate"* in its private reasoning, and never did it. I could not quantify that, for a boring reason — with 8.9% delegation there were only about 16 requests in the whole corpus. Here there are **71**.

### Of 71 requests, how many got done

Each request was traced into the receiver's transcript: the prose of its next turns, plus an index of **every tool call it made from the moment the message arrived to the end of its session**. Then two blind coding passes, and then a third, adversarial pass whose only job was to *refute* each claimed success, instructed to refute when in doubt.

| | |
|---|---|
| Complied (survives the refuter) | **74–83 %** |
| Did not | 17–26 % |
| Silent drop — read it, owed something, did nothing, said nothing | **3 of 70** |

It is a range and not a figure because two identical runs of the refuter agree on 61 of 66 cases (92%). With that much instability, a decimal would be invented.

The interesting part is not the rate, it's **which failure**. The July failure — silent drop — has nearly vanished: 3 firm cases. Receivers reply to 54 of 71 requests. What replaced it is a different animal:

- edited the files, never published or tagged;
- sent the aggregate count when the request asked case by case;
- reported having already sent an inventory that appears nowhere in its own action index;
- answered 2 of the 5 questions it was asked, and reported the answer.

Under named roles, the request gets acknowledged, engaged with, and answered. Roughly one in four or five "done" claims does not survive someone checking. **The failure did not go away. It changed shape** — from dropping the task to asserting it was finished.

That should sound familiar from the July experiment, where enforced file ownership drove merge conflicts to exactly zero and the failure moved downstream into semantic integration. Structure doesn't delete failure modes; it relocates them.

### What this half cannot tell you

Three things, stated before anyone has to ask.

**Task selection is not controlled.** I reach for agent teams on decomposable work and parallel sessions on work I'm doing myself. A traffic mix that is more delegation-shaped may follow from the task, not from the naming.

**The direction is baked in.** Teams traffic includes lead→member instruction. In that shape, delegation is almost definitional.

**It measures compliance, not outcome.** A request carried out is not the same as work that is correct — which is exactly what CooperBench's named lead demonstrated at 0%.

For the outcome, observation is the wrong instrument. That's the other half.

## Part II — One paragraph, thirty episodes

The [seed repository](https://github.com/JaviMaligno/cross-session-crosscheck) from the previous article already scores the right thing: it compares what a session **claims** against the **published** state, read from the registry and from `origin`, never from a working copy.

The scenario, unchanged: a release helper that is correct in every line, a suite that stays green, and a package registry that already holds an artifact for the target version, built from the old code. The publisher is idempotent — it prints `upload: widgetkit 0.4.0 (cached)` and exits successfully. Reading the code cannot reveal it. Only going to look at the registry can.

Alone on a single feature, sessions caught this **7 out of 7 times**, across two variants of the trap. The crack only opened under load: four tickets, the release last, and an inbox with three messages from other sessions, one of them waiting on the version. So load is held fixed here, and the only thing that varies is the ownership paragraph.

| Loaded, four tickets | Detects the silent failure | 95% CI |
|---|---|---|
| Brief says nothing about who owns the published state | 8/15 = 53 % | [27–79 %] |
| **Brief names the session as owner of the published state** | **15/15 = 100 %** | [78–100 %] |

Fisher's exact test, p = 0.0063. A 47-point difference from a paragraph.

### One act explains all thirty episodes

The scoring records, from the transcript rather than from anyone's report, whether the session ever opened the registry. Across both arms:

> **Opening the registry predicts the outcome in 30 of 30 episodes.** Not one case of looking and missing it. Not one case of getting it right without looking.

Every session that failed verified something adjacent instead — most of them checked that the tag had reached `origin` with `git ls-remote`, which is good practice and says nothing whatsoever about the artifact. Every session in the named arm went to the registry. One of them didn't just report the problem: it set the stale artifact aside and republished, then verified that the registry's `0.4.0` now contained the three features.

And the sessions in the named arm mostly did *not* claim the release. Their reports record no published version at all, with the reason attached. Naming the owner didn't make them more confident; it made them refuse to sign off on something they hadn't confirmed.

Meanwhile the consumer session downstream, doing its own task with no instruction to audit anyone, found the stale artifact in every episode where it was still broken. The information was never scarce. What was scarce was somebody whose job it was to go and get it.

## Part III — What the role answers for

Here is the resolution of the contradiction I started with.

In the July experiment, the named lead answered for **somebody else's** deliverable: it had to pull a partner's patch out of a shared workspace and stitch it in. The partial credit is the tell — it passed its own feature in 7/19 and 11/19 pairs, and never both. It did its half and dropped the other one. The intervention that worked there was an **integrator with nothing else to do**, and measured on the same two patches with and without that stage, it rescued 8 pairs and broke 0.

Here, the named owner answers for **its own** deliverable: the thing it published, with its own hands, in this session. 15/15.

So the variable was never "is there a role or not". It is **what the role answers for**:

- Answering for your own published state changes behaviour reliably, and cheaply — one paragraph, no tooling, no protocol.
- Answering for someone else's integrated result is the case that keeps failing, and it needs a dedicated owner with no competing work, not a title added to someone already carrying four tickets.

Both halves point the same way. In the corpus, naming multiplies requests fourfold and the surviving failure is a claim of completion. In the experiment, naming ownership of what you published is exactly what sends the agent to check that claim. The cheap fix for a false "done" is not a reminder to be careful. It is making the claim belong to somebody.

## What this doesn't say

**It doesn't test the product.** I need to be blunt here, because it constrains the whole second half. Agent teams cannot be instantiated headlessly: an agent spawned with the `Agent` tool from `claude -p` comes back through the **subagent** path (`Message sent to X's inbox`, `subagent_tokens`), not as a `<teammate-message>`, and the CLI has no teams flag. Using subagents to make claims about agent teams would be precisely the mechanism contamination the last article warned about. So the experiment runs on the peer channel and measures **the variable**, not the feature.

**Fifteen episodes per cell is fifteen.** The interval on the role-less arm runs from 27% to 79%. The contrast is significant; the point estimates are not precise.

**One person, one machine, one set of repositories.** As before, the ceiling is coverage, not confidence.

And one more, in the spirit of how the last article ended. **Four of my own instruments failed while producing these numbers:**

- a 14-turn evidence window, which made me report that only 17 of 71 receivers replied when the real figure is 54;
- message ids that came back as integers in some places and strings in others, silently dropping 26 of 71 cases out of the agreement calculation with no error anywhere;
- tool arguments truncated to 100 characters, which made the refuter reject legitimate successes because the path it was shown was cut off — 4 of its 14 refutations were that artefact;
- and an outcome classifier that decided "detected" by keyword, so a report asserting *"tag pushed and published to the registry"* — a false claim — counted as a detection because the word "registry" appeared in it.

Three of those pushed toward the result I expected. The fourth pushed against it. Each was caught the same way: by going and looking at the thing itself rather than at what my tool said about it — which, at this point, I should probably stop describing as a coincidence.

---

*Seed repository, harness and scoring: [cross-session-crosscheck](https://github.com/JaviMaligno/cross-session-crosscheck). Earlier in this series: [What Coding Agents Say When They Talk to Each Other](/en/blog/what-agents-say-to-each-other) and [Coding Agents and Teamwork: Social Skills, or Structure?](/en/blog/coding-agents-structure).*
