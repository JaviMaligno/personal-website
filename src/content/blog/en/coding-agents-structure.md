---
title: "Coding Agents and Teamwork: Social Skills, or Structure?"
description: "A recent benchmark says coding agents can't collaborate because they lack social intelligence. I test a different hypothesis: they lack structure — and find that sequencing the work recovers collaboration, while enforced structure only pays off for a capable-enough model."
pubDate: 2026-07-01
tags: ["AI", "Agents", "Evaluation"]
lang: en
translationKey: coding-agents-structure
heroImage: "/blog/coding-agents-structure.png"
---

> **Status: preliminary but complete for two model tiers.** Results are on a 19-task subset I could run cleanly, across two capability levels. Directional, not the full benchmark — but the pattern is consistent enough to report.

A recent Stanford benchmark, [CooperBench](https://arxiv.org/abs/2601.13295) ("Why Coding Agents Cannot be Your Teammates Yet"), reports a striking result: when you pair up two strong coding agents to split a task, their success rate roughly *halves* versus a single agent doing the same total work. They call it the **curse of coordination**, and their reading is that the missing ingredient is *social intelligence* — agents don't use language for coordination reliably, so, they argue, this needs to be *trained*, not prompted away.

It's a careful paper, and I want to be fair to it: they **deliberately** run agents with almost no scaffolding, precisely to measure *intrinsic* coordination ability. That's a legitimate scientific choice. But it left me with an engineering question they explicitly set aside:

> Human teams don't coordinate well with *zero* process either. We don't fix a team that keeps stepping on each other with therapy — we use **structure**: code ownership, interface contracts, sequential PRs, a reviewer who integrates. So how much of the "coordination gap" is really about social skills, and how much is just the absence of structure the agents were never given?

## The setup

I started from CooperBench's own benchmark (it's open source) and reproduced the baseline: two agents, each assigned one feature of a task, working in isolated containers, patches merged afterwards. Then I added a **ladder of coordination structures**, ordered from "advisory" (the agent can ignore it) to "enforced" (the scaffold guarantees it):

- **Handshake (C1):** agents must exchange a plan before the scaffold lets them edit code. *(Analogy: a design review before coding.)*
- **File ownership (C2):** each file is owned by one agent; edits to another agent's file are reverted. *(Analogy: CODEOWNERS.)*
- **Line-range ownership (C2b):** finer version — both may edit the same file, but only in disjoint regions. *(Analogy: not stepping on each other's functions.)*
- **Sequential pipeline (seq):** agent A implements feature 1 and commits; agent B starts *from A's code* and adds feature 2. No concurrency. *(Analogy: small, sequential PRs on trunk.)*
- **Integrator (c4):** A and B work independently; a third agent reconciles both patches. *(Analogy: an integration engineer / PR reviewer.)*

The point of the ladder is to separate "did they *talk*?" from "did the process *stop them from colliding*?" — and to find the *minimum* structure that helps.

## Results

**Caveats first**, because they matter: these are **19 task-pairs across 5 repositories** — a subset I could run cleanly — not the full benchmark. But I ran the whole ladder on **two capability tiers**: a mid-tier `gpt-5.4-mini` and a stronger `gpt-5.4`.

| condition | mini | gpt-5.4 |
|---|---|---|
| solo (one agent, both features) | 16% | 37% |
| coop (two agents, free-form) | 0% | 5% |
| handshake (C1) | 0% | 0% |
| file ownership (C2) | 0% | **16%** |
| line ownership (C2b) | 0% | 5% |
| integrator (c4) | 0% | 0% |
| **sequential (seq)** | **21%** | **32%** |

Four things stand out:

1. **The coordination gap reproduces — at both tiers.** Solo solves 16% / 37%; the moment two agents work concurrently (coop), it collapses to 0% / 5%. CooperBench's core finding holds up on my subset.

2. **Sequencing is what recovers it — regardless of capability.** The **sequential pipeline** recovers to the solo level for both models (21% vs 16% for mini; 32% vs 37% for the strong one — statistically indistinguishable from solo in both cases), while every concurrent condition sits far below. My reading: this isn't really "coordination" at all. When agent B starts from A's *finished* feature and only adds one thing on top, it's doing a *smaller, cleaner task* than solo. Decomposition plus sequencing is the lever — not more talking, not stricter territory.

3. **Structure interacts with capability — the interesting part.** Enforced **file ownership (C2)** recovered nothing for the weak model (0%) but a meaningful chunk for the strong one (0% → **16%**). The stronger model can actually *use* a structural rule it's given; the weaker one can't. That interaction — *the same scaffold helps or doesn't depending on who's using it* — is exactly what a noisy 4-task pilot couldn't show, and it's the part I find most worth chasing. (With one run per cell this particular contrast is suggestive, not significant — more below.)

4. **Forcing communication does nothing — because they already communicate.** The handshake gate (C1) never even fired: agents *already* message each other before touching code (first message on turn 2, first edit on turn 6). Making them talk more changed nothing, at either tier. This echoes CooperBench's own "communication doesn't help" result — and suggests the problem isn't *whether* they exchange information, but what they *do* with it. The integrator (c4) also didn't help either model.

A smaller, slightly uncomfortable note: finer **line-range** ownership (C2b, 5%) did *worse* than coarse **file** ownership (C2, 16%) for the strong model — likely an artifact of my v1 that reverts the whole file on any overlap. Enforcement design details matter, and I haven't optimized them.

## Under the hood: collaboration dies at the merge

Digging into *how* each condition fails changes the picture more than the pass rates do.

**Free-form coop fails at the merge, not at the code.** 14–15 of 19 coop failures (both tiers) are outright **merge conflicts** — the two agents' patches can't even be combined. And here's the striking part: **enforced ownership drives merge conflicts to zero** — 0 of 19 for both C2 and C2b, at both tiers. The failure then moves downstream: patches combine cleanly but the integrated code doesn't pass both suites. So the causal chain reads:

> unstructured concurrency → ~75% merge conflicts → enforced territory eliminates conflicts entirely → what's left is a *semantic* integration problem → and model capability decides whether that remaining problem gets solved (the strong model partly does; the weak one doesn't).

This rhymes with CooperBench's own observation that communication reduces conflicts without improving success — except enforcement doesn't just reduce conflicts, it removes them, and at the stronger tier that *does* start converting into passes.

**The "0%" rows hide half-done work.** Scoring requires *both* features to pass. Count partial success (at least one feature working) and the weak model's picture changes: free-form coop manages 1/19, but under line-range ownership it reaches **10/19**. Enforcement turns total collapse into "half the job done, reliably" — it's just not enough to clear the bar.

**Both tiers hit the fence equally often; only one recovers.** The enforcement hook fired a similar number of times for both models (≈18–29 violations per run). The strong model isn't "tidier" — it violates territory just as much. The difference is what happens *after* the revert: the strong model re-plans and routes around it; the weak one keeps banging. All three of the strong model's C2 passes had enforcement events — the mechanism was active in every one of them, they weren't conflict-free freebies.

**Statistics, honestly.** With one run per cell and N=19, individual contrasts are fragile. What survives paired testing (McNemar): the coordination gap (solo vs coop, pooled across tiers, p≈0.004) and sequencing's recovery over coop (pooled p≈0.004). What doesn't: seq vs solo is indistinguishable (p≈1 — seq *recovers* solo, it doesn't beat it), and the C2 capability interaction (p≈0.5) is a hypothesis for a bigger run, not a result.

**Teamwork has a price tag.** For the strong model: solo cost ~$3.60 for 37%; sequential ~$7.10 for 32%; the integrator ~$9.73 for 0%. On small, coupled tasks, two agents cost roughly twice as much to at best match one — if you must collaborate, sequence; if you can avoid it, don't.

## What this does and doesn't say

It does **not** say CooperBench is wrong — I reproduced their gap at both tiers. What it adds is the piece their setup deliberately left out: **once you give agents structure, does the gap close?** On this subset, partly — and *which* structure works depends on both the structure and the model.

The honest headline isn't "structure beats social skills." It's narrower and, I think, more useful:

- The single most reliable lever wasn't communication or ownership — it was **restructuring the work itself**: decompose, then sequence. That helped both models.
- **Enforced structure only pays off for a capable-enough model.** Below some threshold, handing an agent a coordination protocol is like handing a process manual to someone who can't yet do the underlying job.

So "they can't be teammates yet" reads, from here, less like *they lack social intelligence* and more like *they were dropped into an unstructured free-for-all no sane engineering team would run* — and the fix that generalizes is process (decompose + sequence), not exhortations to communicate.

## Caveats and what's next

- **19 pairs, 5 repos, one run each.** No error bars yet; single-run pass/fail is noisy. Treat the small differences (5% vs 16%) as suggestive, not settled.
- **Passes concentrate in a few repos.** Every pass, in every condition and tier, lands in two Python repos (plus one Pillow task); four of the nine tasks were solved by nothing, ever — including solo. The effectively discriminative set is closer to ~10 pairs than 19.
- The subset skews toward what I could run natively; broadening it is the obvious next step.
- The line-range enforcement deserves a per-hunk revert before I trust the C2b number.

The conditions are implemented on top of the open CooperBench harness — I'll share the code alongside a fuller writeup if the pattern holds up on a larger, repeated run.

---

*Responding to [CooperBench (Khatua, Zhu, et al., 2026)](https://arxiv.org/abs/2601.13295). Preliminary — numbers will change as the experiment completes.*
