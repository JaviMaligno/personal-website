---
title: "Coding Agents and Teamwork: Social Skills, or Structure?"
description: "A recent benchmark says coding agents can't collaborate because they lack social intelligence. I test a different hypothesis: they lack structure — and find that making integration one agent's job recovers collaboration, while merge conflicts mostly mask deeper semantic failures."
pubDate: 2026-07-01
tags: ["AI", "Agents", "Evaluation"]
lang: en
translationKey: coding-agents-structure
heroImage: "/blog/coding-agents-structure.png"
---

> **Status: preliminary but complete for two model tiers, with three seeds on the headline conditions.** Results are on a 19-task subset I could run cleanly, across two capability levels. Directional, not the full benchmark — but the pattern holds across seeds.

A recent Stanford benchmark, [CooperBench](https://arxiv.org/abs/2601.13295) ("Why Coding Agents Cannot be Your Teammates Yet"), reports a striking result: when you pair up two strong coding agents to split a task, their success rate roughly *halves* versus a single agent doing the same total work. They call it the **curse of coordination**, and their reading is that the missing ingredient is *social intelligence* — agents don't use language for coordination reliably, so, they argue, this needs to be *trained*, not prompted away.

It's a careful paper, and I want to be fair to it: they **deliberately** run agents with almost no scaffolding, precisely to measure *intrinsic* coordination ability. That's a legitimate scientific choice. But it left me with an engineering question they explicitly set aside:

> Human teams don't coordinate well with *zero* process either. We don't fix a team that keeps stepping on each other with therapy — we use **structure**: code ownership, interface contracts, sequential PRs, a reviewer who integrates. So how much of the "coordination gap" is really about social skills, and how much is just the absence of structure the agents were never given?

## The setup

I started from [CooperBench's own benchmark](https://github.com/cooperbench/CooperBench) (it's open source) and reproduced the baseline: two agents, each assigned one feature of a task, working in isolated containers, patches merged afterwards. Then I added a **ladder of coordination structures**, ordered from "advisory" (the agent can ignore it) to "enforced" (the scaffold guarantees it):

- **Handshake (C1):** agents must exchange a plan before the scaffold lets them edit code. *(Analogy: a design review before coding.)*
- **File ownership (C2):** each file is owned by one agent; edits to another agent's file are reverted. *(Analogy: CODEOWNERS.)*
- **Line-range ownership (C2b):** finer version — both may edit the same file, but only in disjoint regions. *(Analogy: not stepping on each other's functions.)*
- **Sequential pipeline (C3):** agent A implements feature 1 and commits; agent B starts *from A's code* and adds feature 2. No concurrency. *(Analogy: small, sequential PRs on trunk.)*
- **Integrator (C4):** A and B work independently; a third agent reconciles both patches. *(Analogy: an integration engineer / PR reviewer.)*

The point of the ladder is to separate "did they *talk*?" from "did the process *stop them from colliding*?" — and to find the *minimum* structure that helps.

## Results

**Caveats first**, because they matter: these are **19 task-pairs across 5 repositories** — a subset I could run cleanly — not the full benchmark. But I ran the whole ladder on **two capability tiers** (a mid-tier `gpt-5.4-mini` and a stronger `gpt-5.4`), and the four headline conditions were run **three times each** so I can show a range instead of a single noisy number.

| condition | mini | gpt-5.4 |
|---|---|---|
| solo (one agent, both features) | 14% [11–16] | 30% [21–37] |
| coop (two agents, free-form) | 7% [0–11] | 7% [0–16] |
| coop + fair conflict resolution* | 7% [0–11] | 9% [0–16] |
| **sequential (C3)** | **26% [21–37]** | **35% [32–37]** |
| **integrator (C4)** | **23% [21–26]** | **33% [26–42]** |
| handshake (C1)† | 0% | 0% |
| file ownership (C2)† | 0% | 16% |
| line ownership (C2b)† | 0% | 0% |

<sub>Headline cells are mean [min–max] over three seeds; †the enforced conditions are a single run each (not replicated). *The paper's eval auto-resolves trivial merge conflicts with a small model before declaring failure; the open-source release omits that step. I added an equivalent (if anything stronger) resolver and re-scored the concurrent conditions — details in "Under the hood".</sub>

Four things stand out:

1. **The coordination gap reproduces — and it's wider for the stronger model.** Two agents working concurrently (coop) score below one agent doing the whole task (solo): 14%→7% for mini, 30%→7% for gpt-5.4. Pooled across tiers and seeds the drop is solid (paired McNemar p=0.002); split out, it's clearly significant for the strong model (p=0.002) and not for the weak one (p=0.39) — simply because mini's solo baseline is already low, so there's less to lose. The curse of coordination bites hardest where a single agent was actually competent.

2. **Two structures recover it — and sequencing does more than recover.** The **sequential pipeline (C3)** and the **integrator (C4)** both beat coop decisively at both tiers (p<0.0001). They share a mechanism: **one agent ends up owning the final integrated state** — B builds directly on A's finished work, or a reviewer reconciles both patches in a single workspace. But the two aren't equivalent. Sequencing doesn't just claw back to solo — for the *weak* model it **beats** solo (mini 26% vs 14%, ahead in all three seeds, p=0.039), while merely tying it for the strong one (large 35% vs 30%, p=0.45). The integrator recovers over coop but never significantly beats solo (p=0.23). Read plainly: decomposing the task so agent B faces "add feature 2 to a codebase that already has feature 1" is a *smaller* problem than "build both at once" — and a smaller problem helps most whoever was struggling with the big one.

3. **So structure interacts with capability — in both directions.** That's the genuinely interesting part, and it cuts two ways. **Sequencing helps the weak model more** (it lifts mini above its own solo baseline; it only matches solo for the strong one). **Enforced file ownership (C2) helps the strong model more** — it recovered nothing for mini but reached 16% for gpt-5.4. Two opposite-signed interactions: lightening the cognitive load rescues the weaker model, while a structural rule it must actively exploit rewards the stronger one. (Both are single-or-few-run signals on a small subset — directional, not settled. And C2's edge shrinks once you score coop's merges fairly: see the asterisk below.)

4. **Forcing communication does nothing — because they already communicate.** The handshake gate (C1) never even fired: agents *already* message each other before touching code (first message on turn 2, first edit on turn 6). Making them talk more changed nothing, at either tier. This echoes CooperBench's own "communication doesn't help" result — and suggests the problem isn't *whether* they exchange information, but what they *do* with it.

A smaller, slightly uncomfortable note: finer **line-range** ownership (C2b) did *worse* than coarse **file** ownership (C2, 16%) for the strong model. I first suspected an artifact of my v1 enforcement, which reverted the whole file on any overlap — so I built a v2 that reverts only the violating hunks and re-ran both tiers: **0% at both**. The binding constraint isn't revert granularity. It's that CooperBench features *intentionally* overlap on shared lines (the same import list, the same function signature), so any exclusive line ownership starves whichever agent arrives second.

One logged run shows the failure in miniature. The blocked agent escalated exactly the way a person would: it announced its plan, then asked its partner to avoid the shared regions, then — after more reverts — *delegated*: "could you add my export line, since you own that region?" I checked the plumbing on both sides: all three messages were delivered into the partner's context with turns to spare, and the partner's outbound channel demonstrably worked (it had messaged first, at the very start). The partner read the requests, even wrote "I'll need to coordinate with agent1" in its own reasoning — and then never replied, never added the one-line export it owned, and closed out its task. The bottleneck isn't the communication channel; it's **follow-through** — precisely the commitment failure CooperBench's taxonomy describes, reproduced here with the channel verified blameless.

## Under the hood: collaboration dies at the merge

Digging into *how* each condition fails changes the picture more than the pass rates do.

**Free-form coop fails at the merge, not at the code.** 14–15 of 19 coop failures (both tiers) are outright **merge conflicts** — the two agents' patches can't even be combined. And here's the striking part: **enforced ownership drives merge conflicts to zero** — 0 of 19 for both C2 and C2b, at both tiers. The failure then moves downstream: patches combine cleanly but the integrated code doesn't pass both suites.

**But is dying at a merge conflict too cheap a death?** (Isn't resolving conflicts what PR review is for?) It's a fair objection — and it turned out to be aimed at a real gap: the paper's own eval resolves trivial conflicts with a small trained model before declaring failure, but the open-source release omits that step, so my first table scored every conflict as an instant fail. I checked it both ways. First, I triaged all 29 conflicted pairs by hand: **roughly half the conflicts aren't real logic collisions** — two agents adding a different import, or a different keyword argument, to the same line; git flags it, the code wouldn't care. Then I added a trivial-conflict resolver (using a stronger model than the paper's, so coop gets every benefit of the doubt) and re-scored the conflicted pairs across all three seeds. It rescued plenty of merges — but **almost none of them became passes**: fair-merge coop lands at 7% for mini (unchanged) and 9% for gpt-5.4 (up from 7%), a single extra task. The conflicts were mostly *masking* semantic failures further down: in one rescued pair, one feature passed 71/71 tests and the other failed a genuinely broken assertion the conflict had been hiding.

So the causal chain reads:

> unstructured concurrency → ~75% merge conflicts → the *syntactic* layer can be fixed two ways — prevention (enforced territory: zero conflicts) or cure (a trivial-conflict resolver) → what's left is a *semantic* integration problem → and neither fences nor resolvers fix that. Sequencing or an integrator do.

This rhymes with CooperBench's own observation that communication reduces conflicts without improving success — the syntactic layer is simply not where the task is won.

**The "0%" rows hide half-done work.** Scoring requires *both* features to pass. Count partial success (at least one feature working) and the weak model's picture shifts: free-form coop lands only a handful of single-feature passes, while enforced ownership roughly doubles them (mini reaches 5/19 under line-range enforcement). Enforcement turns total collapse into "half the job done" more often — it's just not enough to clear the both-features bar.

**Both tiers hit the fence equally often; only one recovers.** The enforcement hook fired a similar number of times for both models (≈18–29 violations per run). The strong model isn't "tidier" — it violates territory just as much. The difference is what happens *after* the revert: the strong model re-plans and routes around it; the weak one keeps banging. All three of the strong model's C2 passes had enforcement events — the mechanism was active in every one of them, they weren't conflict-free freebies.

**Statistics, honestly.** The four headline conditions have three seeds each; the enforced conditions are single runs. Paired McNemar tests (matched per task and seed) give: the coordination gap solid pooled (p=0.002) and clearly significant for the strong model alone (p=0.002); sequencing and the integrator each beat coop overwhelmingly (p<0.0001); sequencing beats *solo* pooled (p=0.021) and for the weak model alone (p=0.039, ahead in all three seeds), while only tying solo for the strong one (p=0.45); the integrator recovers but never significantly beats solo (p=0.23). One honest caveat on the method: pooling discordant pairs across seeds treats each (task, seed) as independent, which mildly overstates significance — so I lean on the per-seed direction (mini seq > solo in 3/3 seeds) as much as on the p-value. With three seeds on a 19-task subset these are still directional; I'd want a larger repeated run before hardening any single number.

**Teamwork has a price tag.** For the strong model, per run: solo cost ~$3.60; sequential ~$7.10 and the integrator ~$9.73. Sequencing roughly doubles the bill to modestly beat solo; the integrator nearly triples it to match. On small, coupled tasks, if you must collaborate, sequence; if you can avoid it, one capable agent is the cheapest strong option.

## Can you stack the fixes?

If enforced territory kills syntactic conflicts and an integrator owns the merge, surely combining them beats either alone? I tried three combinations: **territory + integrator**, **sequencing + reviewer**, and **handshake + territory**. Short answer: **none robustly beats its own components.**

The instructive one is territory + integrator. At one seed it looked like the star of the whole experiment — 42% for the strong model, seemingly ahead of the integrator alone. Then I ran two more seeds and it collapsed to 33% [21–42]: the 42% was a lucky draw, and paired against the plain integrator across all three seeds it comes out at p=1.0 — indistinguishable. The replicates existed precisely to catch that kind of over-claim, and they did.

But a cleaner measurement rescues something real. For each pair I re-scored the tree *without* the extra stage, on the very same two agent patches — so the only variable is the extra stage itself, no run-to-run noise. The integrator, measured this way, **rescued 8 pairs and broke 0**; the reviewer (on top of a sequential pipeline) rescued 3 and broke 3, a net zero. So the integrator's contribution is genuine and one-directional — it only ever helps. The reason territory + integrator still doesn't win on the scoreboard: the territory-constrained development phase hands the integrator no better raw material than plain independent development does, so a real but modest boost starts from equally noisy inputs and washes out across seeds. The reviewer nets zero for a simpler reason — a sequential pipeline already integrated the tree, so there's nothing left to reconcile, only code to accidentally break.

The lesson isn't "structure doesn't stack." It's narrower: **stacking composes only when an earlier stage improves the *inputs* to a later one.** Sequencing→review fails that test (nothing to improve); territory→integrate fails it too (territory doesn't make better patches, just non-overlapping ones). The one lever that keeps working is the same one from the single conditions — one agent owning the integration — and doubling down on it by combination didn't buy more.

## What this does and doesn't say

It does **not** say CooperBench is wrong — I reproduced their gap at both tiers. What it adds is the piece their setup deliberately left out: **once you give agents structure, does the gap close?** On this subset, partly — and *which* structure works depends on both the structure and the model.

The honest headline isn't "structure beats social skills." It's narrower and, I think, more useful:

- The most reliable lever wasn't communication or ownership — it was **giving one agent ownership of the final integration**: hand off sequentially, or appoint an integrator/reviewer to own the merge. Both recover solo-level performance at both tiers, and sequencing does best of all.
- **The structure has to match the model.** Sequencing — which shrinks the task rather than adding rules to obey — is the one intervention that lifts the *weak* model above its own solo score; concurrent collaboration otherwise stays dead for it no matter what you fix (fair merging, fences, handshakes all leave it flat). Enforced ownership, a rule the agent has to actively exploit, only paid off for the *strong* model. Below some capability threshold, handing an agent a coordination protocol is like handing a process manual to someone who can't yet do the underlying job — but handing it a smaller job still helps.

So "they can't be teammates yet" reads, from here, less like *they lack social intelligence* and more like *they were dropped into an unstructured free-for-all no sane engineering team would run* — and the fix that generalizes is process (decompose + sequence, or appoint an integrator), not exhortations to communicate.

## Caveats and what's next

- **19 pairs, 5 repos.** The headline conditions have three seeds (hence the ranges); the enforced conditions (C1/C2/C2b) are still single runs, so treat those as the softest numbers here.
- **Passes concentrate in a few repos.** Every pass, in every condition and tier, lands in two Python repos (plus one Pillow task); four of the nine tasks were solved by nothing, ever — including solo. The effectively discriminative set is closer to ~10 pairs than 19.
- The subset skews toward what I could run natively; broadening it is the obvious next step.
- The C2b number survived a v2 with per-hunk reverts (0% at both tiers on a re-run) — it is not a revert-granularity artifact.
- A caution from building this: two conditions initially scored a false 0% due to eval-composition bugs (a stacked patch evaluated against the wrong base). We then ran two independent adversarial code audits over all five condition implementations and the eval routing; the published numbers survived, and the audit is what surfaced the missing conflict resolver behind the fair-merge row above. In agent harnesses, the scoring plumbing deserves as much testing as the conditions themselves.

The conditions are implemented on top of the open CooperBench harness — I'll share the code alongside a fuller writeup if the pattern holds up on a larger, repeated run.

---

*Responding to [CooperBench (Khatua, Zhu, et al., 2026)](https://arxiv.org/abs/2601.13295). The headline cells are three-seed means on a 19-task subset; broadening the task set is the next step.*
