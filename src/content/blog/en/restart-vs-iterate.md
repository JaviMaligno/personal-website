---
title: "Let the Loop Iterate: Restarting Only Pays If You Know What to Throw Away"
description: "Karpathy suggested letting a stuck agent restart instead of grinding on. I built a loop with visible tests and measured it: iterating on feedback beats clean restarts at equal compute — and handing the agent a scoped restart button reveals that knowing *what* to discard is what separates the tiers."
pubDate: 2026-07-17
tags: ["AI", "Agents", "Evaluation"]
lang: en
translationKey: restart-vs-iterate
heroImage: "/blog/restart-vs-iterate.png"
---

> **A complete study: 3 seeds × 3 policies × 2 model tiers on a 29-feature slice, with the eval harness audited before trusting a single number.** Same rigor protocol as [the coordination article](https://www.javieraguilar.ai/en/blog/coding-agents-structure) — this experiment is its direct sequel.

There's a piece of agent folklore, crystallized by Andrej Karpathy as *"let the loop restart"*: when a coding agent's attempt is going badly, don't keep patching the sinking ship — throw the attempt away and let it start fresh. It has intuitive appeal. Anyone who has watched an agent dig itself deeper into a broken approach has felt it.

But is it true? In [my previous experiment](https://www.javieraguilar.ai/en/blog/coding-agents-structure) I couldn't even test it: CooperBench agents make a single pass and never see their test results, so the failure signal that would prompt a restart never reaches them. I mined all 1,806 trajectories and found exactly **zero** voluntary restarts — an artifact of the setup, not a finding. Measuring restart-vs-iterate properly needed a different harness.

So I built one.

## The setup

On top of the same CooperBench-derived stack (29 single-feature tasks across 5 real repositories, two model tiers: a mid-tier `gpt-5.4-mini` and a stronger `gpt-5.4`), I added the missing piece: a **loop with a visible evaluator**. The agent attempts the feature; the harness runs the feature's test suite and shows the agent the results (pass/fail counts plus the failing tests' output); then comes the next round — up to **K = 4 rounds**, stopping early on success.

Every policy gets the same K, the same per-round compute caps, and the *same feedback format* — so the only variable is what happens **between** rounds:

- **ITERATE** — the classic loop: code and context accumulate; the agent patches its own work with the test results in hand.
- **RESTART-FRESH** — the literal Karpathy reading: each round starts from a clean checkout with a fresh context. No memory of prior attempts. This is deliberately best-of-K sampling — that *is* the claim, tested at equal compute, not apologized for.
- **RESTART-INFORMED** — clean checkout, but the context carries a short summary of what failed, built by the harness from artifacts (never written by the failing agent itself). This separates the mechanism: if informed beats fresh, the *lesson* helps; if fresh matches informed, the contaminated context was the problem.
- **AGENT-DECIDES** — the interesting one: an iterate-style loop where the agent holds an explicit **restart tool with scope** — `restart(file | directory | all-my-work)` — presented as a legitimate, cost-free option. It chooses when to discard and *how much*.

## Results

Three seeds per headline cell; the table shows mean [min–max] over 29 features.

| policy | mini | gpt-5.4 |
|---|---|---|
| iterate (patch with feedback) | 74% [72–76] | 86% [79–90] |
| restart-fresh (clean best-of-K) | 63% [62–66] | 69% [69–69] |
| restart-informed (1 seed) | 69% | 79% |
| **agent-decides (scoped restart tool)** | **75% [69–79]** | **91% [90–93]** |

Four findings, in order of how well they survive the statistics:

1. **Iterating on feedback beats clean restarting — decisively for the strong model.** Paired McNemar across the three seeds: gpt-5.4 iterate wins 17–2 over restart-fresh (p=0.001); mini leans the same way (15–6, p=0.078). At equal compute, K attempts refining one trajectory with test feedback outperform K independent clean attempts. The literal *let-the-loop-restart* — restart as blind resampling — **loses** on this benchmark.

2. **What hurts isn't the contaminated context — it's losing the working tree.** Restart-informed (clean code, lesson retained) lands *between* fresh and iterate at both tiers. The harness-built lesson recovers part of the gap, but nothing beats keeping the actual code. At this horizon (K=4), the "poisoned context" the restart intuition worries about simply wasn't the binding constraint.

3. **Handing the agent the decision is the best cell in the table — and it never hurts.** Agent-decides tops both tiers (91% for gpt-5.4, its best; 75% for mini). Against restart-fresh at the strong tier it wins **19–0** (p<0.001). Against pure iterate the edge is not significant (8–4, p=0.39) — so read it conservatively: the bulk of the value is in iterating; the restart *option* adds a plausible-but-unproven bonus and costs nothing.

4. **The capability marker is restart *style* — though the causal story is subtler than "scalpel vs. wrecking ball."** This is the finding I'd keep if I could keep only one, and it's the one a sharp reader (@alex_spinov, in the comments) pushed hardest — rightly. The raw pattern is real: across three seeds the strong model restarted **rarely and surgically** (7 restarts, 5 file-scoped, **3 of 4** restarted feature-runs solved), while the weak model restarted **often and destructively** (34 restarts, 23 of them `scope=all`, only **1 of 14** restarted feature-runs solved). But restarts are *self-selected* — the agent reaches for one exactly where it's already losing — so restarted features are a hard subset by construction. The honest test is the counterfactual: the *same* features and seeds under pure `iterate`, which the harness already ran. It separates the tiers cleanly:
   - **Weak tier — the wrecking ball is a symptom, not the cause.** Those same 14 features solve just **2/14 under iterate**, nowhere near the 74% base. Broad restarts didn't destroy winnable work; the agent razed everything *because* the feature was already lost. Restart is roughly neutral here (1/14 vs 2/14), not destructive.
   - **Strong tier — the scalpel genuinely rescues.** Those same 4 features solve **0/4 under iterate**; the scoped restart turned three of them into wins. Against the right baseline — the matched subset, not the 91% global rate — that's a real causal gain, though at n=4 it's directional (exact p≈0.25), not significant.

   So the sharpened claim: knowing *what* to throw away is the metacognition, and it's the strong tier's scoped restart that actually pays — while the weak tier's broad restart is the *signature* of an agent that has already lost, not the mechanism of its loss.

## Under the hood

**The pilot earned its keep.** Before spending on the full grid, a 6-feature pilot caught **three real composition bugs** in my own harness — patches that the evaluator accepted but the next round couldn't re-apply, and (the big one) iterate rounds being scored against a tree that was missing the earlier rounds' work. That last one is the same bug class that produced a false 0% in the previous article. All three were fixed test-first and the contaminated pilot data was discarded and re-run. If you build agent loops: **the round-to-round state composition is where the bodies are buried.**

**An adversarial audit gated the spend.** As in the previous article, an independent reviewer agent audited the loop before Phase 1 — verdict FAIL, two integrity issues (a cost cap that could silently drop features from the denominators, and harness-error rounds masquerading as "no progress"), both fixed and re-audited to PASS before any headline run. Every round persists its patch, its test results, and the exact composed tree that was evaluated, so all curves are re-analyzable offline without re-spending.

**Equal compute, honestly.** Restart-fresh is best-of-K sampling and was treated as such — same rounds, same caps. Its failure mode is visible in the round curves: when fresh fails, it burns all four rounds without converging (its per-feature cost on failures ran 5–10× the successes). Iterate's failure mode is the plateau — rounds without gaining a single test — which happened, but less often than the restart intuition predicts (about 1 in 5 unsolved runs at the strong tier).

**Cost.** The whole experiment — pilot, three policies × two tiers × three seeds, the decision phase, and all the debugging — came to about **\$102** of API spend. The per-solve cost differences between policies were small compared to the pass-rate differences; nothing in the money changes the ranking.

## What this does and doesn't say

It does **not** say Karpathy is wrong in general. It says: *in the regime I measured* — feature-sized tasks on existing codebases, four rounds, tests visible — restart-as-resampling loses to iteration, and the restart that *does* pay is scoped, informed, and rare. Regimes where I'd expect the balance to shift toward restarting: greenfield tasks (where "start over" genuinely means a blank page and first attempts anchor hard), much longer horizons (where context genuinely rots), and models below some competence floor (where every attempt is a fresh dice roll anyway — though note that even our weak tier did better iterating).

The echo with the [coordination article](https://www.javieraguilar.ai/en/blog/coding-agents-structure) is hard to miss. There, the lever that worked was structural (one agent owning the integration) and the strong model was the one that could exploit a rule. Here, the lever that works is *keeping your work and reading the feedback*, and the strong model is the one that can wield a scalpel. Both experiments land on the same shape: **capability doesn't just raise pass rates — it changes which process helps.** Give a weak agent a powerful affordance (a coordination protocol, a restart button) and it flails with it; give it a smaller problem or a tighter loop and it improves. Give a strong agent the same affordance and it uses it the way you hoped.

If you run coding agents in practice, the actionable version is three lines:

- Default to **iterate with visible tests** — don't restart-by-default, and don't hide the feedback.
- If you add a restart affordance, expect **only your stronger models to wield it well** — on our data, the strong tier's scoped reverts rescued features plain iteration lost (3/4 vs 0/4 on the same features), while the weak tier's restarts merely marked work that was already sunk. Don't count on *forcing* narrow scope to lift a weaker model's pass rate.
- Watch the *style* of your agent's discards. Frequent, broad restarts aren't decisiveness; on our data they're the signature of an agent that's already lost — iteration fails those same features too.

## Caveats and what's next

- **29 features, 5 repos, K=4.** Three seeds on the headline cells (informed has one). Small-N caveats apply as always; the iterate-beats-fresh result is the one with real statistical teeth (p=0.001), the agent-decides edge over iterate is directional only.
- **Not greenfield.** Feature-scoped restarts on an existing codebase cap how much "starting over" can even mean. The scope tool's ceiling is low here by construction.
- **One agent framework, one model family** (GPT-5.4 tiers on Azure) — cross-family replication is the obvious next step.
- The decision prompt frames restarting as legitimate and cost-free; a different framing might shift restart rates (though it shouldn't shift the *payoff asymmetry* between tiers, which is the core finding).

Everything is reproducible: the loop harness, all four policies, the metrics, and the per-round artifacts are public in [github.com/JaviMaligno/CooperBench](https://github.com/JaviMaligno/CooperBench/tree/experiment/restart-loop) (branch `experiment/restart-loop`).

---

*Prompted by Andrej Karpathy's "let the loop restart" observation. Sequel to [Coding Agents and Teamwork: Social Skills, or Structure?](https://www.javieraguilar.ai/en/blog/coding-agents-structure)*
