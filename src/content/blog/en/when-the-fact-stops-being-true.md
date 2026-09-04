---
title: "When the Fact Stops Being True"
description: "A replication of SKILL.state, an EMNLP paper that replaces an agent's conversation history with an explicit mutable state. The token savings are real and the bill savings are not — 7.5x becomes 1.4x once you turn caching on. And the place explicit state wins decisively is the one the paper predicted it would lose: 93 out of 93 corrections applied, against 18 out of 82 for the full transcript."
pubDate: 2026-09-12
tags: ["AI", "Agents", "Context Engineering", "Evaluation", "Research"]
lang: en
translationKey: when-the-fact-stops-being-true
heroImage: "/blog/when-the-fact-stops-being-true.png"
linkedinImage: /blog/when-the-fact-stops-being-true-fig-3.png
linkedinSummary: |
  An agent reads a correction at step 10: the pallet you filed at step 3 was never actually put away, that shelf is empty. Twenty steps later it has to decide where to store the next one.

  With the entire transcript in context — the original record, the correction, everything in between — Claude Haiku 4.5 gets that decision right 3 times out of 44. Given a 200-character JSON state object instead, and no transcript at all, it gets it right 44 out of 44. Sonnet 5 goes from 15/38 to 49/49. Explicit state does not miss a single correction in 93 dependent steps across both models.

  That is a replication of SKILL.state, an EMNLP paper proposing exactly this substitution, and the result contradicts one of the paper's own stated limitations. It also fails to reproduce the headline: on the paper's own kind of task, three of the four runtimes score a clean 1.00, because the information a warehouse agent needs is never more than about two positions away.

  The cost half is worse than it looks. The token savings are real — a flat 2,157-token prompt against one growing to 16,437 — and they are not bill savings. An append-only transcript is the ideal cacheable prefix; a state object that mutates invalidates the cache. Measured with caching on, a 7.5x advantage in tokens becomes 1.4x in money, and the two orderings disagree about second place. The same content with the state block moved in front of the transcript, which is where the paper's own template puts it, costs 5.7 times more.

  The part I would keep, though, is the instrument. Two findings in this project were fully written up — tables, non-overlapping intervals, a mechanism — and then killed by checks that cost nothing: simulate an agent that is perfect except that it ignores the thing you are measuring, and check that your effect fits inside the range your effect can have. One reported separation was larger than the maximum possible effect. It was truncation.

  What is the cheapest check that has caught you measuring your own harness instead of your system?
---

<style>
.wfs-fig { margin: 2rem 0; }
.wfs-fig svg { width: 100%; height: auto; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.wfs-fig figcaption { margin-top: 0.6rem; font-size: 0.9rem; color: #94a3b8; line-height: 1.5; }
</style>

> **A replication of *SKILL.state: Scalable Long-Horizon Agent Skills* (Badhe, Tiwari and Chung, accepted at EMNLP) across two models and 500+ episodes.** Every headline number here is a count of decisions, not an average of episodes, and two results that were already written up with clean confidence intervals were killed by checks described at the end. Those checks are the transferable part.

An agent reads an event at step 10: *the pallet you filed at step 3 was never actually put away; that shelf is empty.* Twenty steps later it has to decide where to store the next pallet. The correct answer is the shelf the correction freed.

With the entire transcript in its context — the original record, the correction, everything in between — Claude Haiku 4.5 gets that decision right **3 times out of 44**. Given a 200-character JSON state object instead, and no transcript at all, the same model gets it right **44 out of 44**.

That is the strongest effect in this replication, and the paper being replicated predicts the opposite.

## What the paper proposes

[*SKILL.state*](https://arxiv.org/abs/2608.26263) replaces the append-only conversation history of a ReAct-style agent with an explicit, mutable execution state. At each step the model receives the procedure `P`, the current state `Σ_t`, and the latest observation `O_t`. It replies with a JSON patch and an action. The patch is validated and merged, `Σ_{t+1} = Σ_t ⊕ ΔΣ_t`, and the reasoning that produced it is **discarded**. Nothing accumulates.

The claim has two halves: better accuracy on long procedures, and a prompt that stays O(1) instead of growing O(T).

<figure class="wfs-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Four runtimes compared by what each one sends to the model at step t: ReAct sends the whole transcript, Memory a prose summary plus a three-step window, Stateful a state object followed by the whole transcript, and SKILL.state only the state object and the latest observation.">
  <defs>
    <style>
      .wl { fill:#e2e8f0; font:12px ui-sans-serif,system-ui; }
      .wm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .wh { fill:#f8fafc; font:600 12.5px ui-sans-serif,system-ui; }
      .wt { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .wc { font:10px ui-monospace,'JetBrains Mono',monospace; }
    </style>
  </defs>
  <text x="16" y="24" class="wt">What each runtime sends at step t</text>
  <text x="16" y="42" class="wm">grey = grows with T · teal = bounded</text>

  <g transform="translate(16,58)">
    <text x="0" y="12" class="wh">ReAct</text>
    <rect x="0" y="20" width="120" height="16" rx="3" fill="#334155" stroke="#64748b"/>
    <text x="6" y="32" class="wc" fill="#cbd5e1">procedure</text>
    <rect x="0" y="40" width="120" height="42" rx="3" fill="#3f3f46" stroke="#64748b"/>
    <text x="6" y="56" class="wc" fill="#cbd5e1">full transcript</text>
    <text x="6" y="70" class="wc" fill="#94a3b8">O(T)</text>
    <rect x="0" y="86" width="120" height="16" rx="3" fill="#164e4a" stroke="#2dd4bf"/>
    <text x="6" y="98" class="wc" fill="#5eead4">observation</text>
  </g>

  <g transform="translate(154,58)">
    <text x="0" y="12" class="wh">Memory</text>
    <rect x="0" y="20" width="120" height="16" rx="3" fill="#334155" stroke="#64748b"/>
    <text x="6" y="32" class="wc" fill="#cbd5e1">procedure</text>
    <rect x="0" y="40" width="120" height="42" rx="3" fill="#3f3f46" stroke="#64748b"/>
    <text x="6" y="56" class="wc" fill="#cbd5e1">prose summary</text>
    <text x="6" y="70" class="wc" fill="#cbd5e1">+ 3-step window</text>
    <rect x="0" y="86" width="120" height="16" rx="3" fill="#164e4a" stroke="#2dd4bf"/>
    <text x="6" y="98" class="wc" fill="#5eead4">observation</text>
  </g>

  <g transform="translate(292,58)">
    <text x="0" y="12" class="wh">Stateful</text>
    <rect x="0" y="20" width="120" height="16" rx="3" fill="#334155" stroke="#64748b"/>
    <text x="6" y="32" class="wc" fill="#cbd5e1">procedure</text>
    <rect x="0" y="40" width="120" height="16" rx="3" fill="#78350f" stroke="#f59e0b"/>
    <text x="6" y="52" class="wc" fill="#fbbf24">state object</text>
    <rect x="0" y="60" width="120" height="22" rx="3" fill="#3f3f46" stroke="#64748b"/>
    <text x="6" y="75" class="wc" fill="#cbd5e1">full transcript</text>
    <rect x="0" y="86" width="120" height="16" rx="3" fill="#164e4a" stroke="#2dd4bf"/>
    <text x="6" y="98" class="wc" fill="#5eead4">observation</text>
  </g>

  <g transform="translate(430,58)">
    <text x="0" y="12" class="wh">SKILL.state</text>
    <rect x="0" y="20" width="120" height="16" rx="3" fill="#334155" stroke="#64748b"/>
    <text x="6" y="32" class="wc" fill="#cbd5e1">procedure</text>
    <rect x="0" y="40" width="120" height="16" rx="3" fill="#78350f" stroke="#f59e0b"/>
    <text x="6" y="52" class="wc" fill="#fbbf24">state object</text>
    <rect x="0" y="86" width="120" height="16" rx="3" fill="#164e4a" stroke="#2dd4bf"/>
    <text x="6" y="98" class="wc" fill="#5eead4">observation</text>
  </g>

  <text x="16" y="188" class="wl">The reasoning that produced the patch is discarded. In SKILL.state,</text>
  <text x="16" y="206" class="wl">everything the agent will ever know about step 3 has to be inside</text>
  <text x="16" y="224" class="wl">the state object by step 4 — or it is gone.</text>
</svg>
<figcaption>The four arms differ only in what sits between the procedure and the latest observation. Stateful and ReAct carry nearly the same content; the order they carry it in turns out to cost 5.7x.</figcaption>
</figure>

SkillExecBench has no public code, so the environment here is a reimplementation from the paper's §4.1 description — a 500-shelf warehouse with dense pipe-separated event records, matched on **context density** rather than literal content, running about 1.2–1.5x heavier than theirs. Two models: Claude Haiku 4.5 and Claude Sonnet 5.

## Half of it replicates

The cost curve reproduces exactly. Average prompt at T=50: SKILL.state **2,157 tokens**, flat from T=10 (2,136) to T=50. ReAct: **16,437**, growing linearly. O(1) against O(T), as advertised.

The accuracy half does not. At T=50, with 16k-token prompts and 172 actionable events per episode, three of the four arms score a clean 1.00:

| runtime | T=10 | T=25 | T=50 | paper, T=50 |
|---|---|---|---|---|
| ReAct | 1.00 | 1.00 | **1.00** | 0.88 |
| Memory | 1.00 | 0.96 | **0.75** | 0.93 |
| Stateful | 1.00 | 1.00 | **1.00** | 0.94 |
| SKILL.state | 1.00 | 1.00 | **1.00** | 0.96 |

The only arm that degrades is the one that summarises into prose, and it degrades further than in the paper. Re-measuring the SKILL.state cell with 3 seeds × 6 repetitions gives **18/18 at exactly 1.000, zero deviation** — this is not a lucky run.

The reason is worth naming, because it governs the rest of the work: in this task the load-bearing information is never far away. The freed shelf an agent has to reuse sits **1.9 positions from the top of the stack on average**, at most 7. Making the horizon longer adds steps without moving information further from its use. If you want to measure whether a runtime remembers, `T` is the wrong knob.

## The token count is not the bill

The paper compares tokens. Anyone running this compares money, and those are different quantities the moment prompt caching is on. An append-only transcript is the ideal cacheable prefix: every step re-sends exactly what it sent before, plus a suffix. A state object that mutates invalidates the cache from the point it mutates.

Anthropic bills cache reads at 0.1x and cache writes at 1.25x. Measured over T=50 episodes, with the transcript sent as immutable per-turn blocks so the cache can actually match:

<figure class="wfs-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Raw token counts versus billed token counts for four runtimes. SKILL.state uses the fewest raw tokens at 109k, but ReAct falls from 826k raw to 152k billed because its append-only transcript caches, so the 7.5x advantage in tokens becomes 1.4x in money.">
  <defs>
    <style>
      .cl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .cv { fill:#f8fafc; font:600 11px ui-monospace,'JetBrains Mono',monospace; }
      .ct { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .cm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="24" class="ct">Input tokens per episode, T=50</text>
  <rect x="200" y="32" width="11" height="9" fill="#475569"/><text x="216" y="40" class="cm">raw</text>
  <rect x="256" y="32" width="11" height="9" fill="#2dd4bf"/><text x="272" y="40" class="cm">actually billed</text>

  <g transform="translate(0,52)">
    <text x="126" y="12" class="cl" text-anchor="end">SKILL.state</text>
    <rect x="132" y="2" width="46" height="12" fill="#475569"/><text x="184" y="12" class="cv">109k</text>
    <rect x="132" y="18" width="46" height="12" fill="#2dd4bf"/><text x="184" y="28" class="cv">109k</text>
    <text x="228" y="28" class="cm">cache saves 0%</text>
  </g>
  <g transform="translate(0,100)">
    <text x="126" y="12" class="cl" text-anchor="end">ReAct</text>
    <rect x="132" y="2" width="350" height="12" fill="#475569"/><text x="488" y="12" class="cv">826k</text>
    <rect x="132" y="18" width="64" height="12" fill="#2dd4bf"/><text x="202" y="28" class="cv">152k</text>
    <text x="246" y="28" class="cm">cache saves 82%</text>
  </g>
  <g transform="translate(0,148)">
    <text x="126" y="12" class="cl" text-anchor="end">Memory</text>
    <rect x="132" y="2" width="133" height="12" fill="#475569"/><text x="271" y="12" class="cv">313k</text>
    <rect x="132" y="18" width="133" height="12" fill="#2dd4bf"/><text x="271" y="28" class="cv">313k</text>
    <text x="316" y="28" class="cm">cache saves 0%</text>
  </g>
  <g transform="translate(0,196)">
    <text x="126" y="12" class="cl" text-anchor="end">Stateful</text>
    <rect x="132" y="2" width="370" height="12" fill="#475569"/><text x="508" y="12" class="cv">873k</text>
    <rect x="132" y="18" width="370" height="12" fill="#2dd4bf"/><text x="508" y="28" class="cv">873k</text>
    <text x="132" y="46" class="cm">same content as ReAct, state block placed first — 5.7x the bill</text>
  </g>
</svg>
<figcaption>Every method that compresses rewrites its prefix, and rewriting the prefix kills the cache. The one arm that caches is the one that never touches what it already sent.</figcaption>
</figure>

**SKILL.state's advantage goes from 7.54x in raw tokens to 1.39x in money.** And the two orderings disagree: by tokens it is SKILL.state < Memory < ReAct < Stateful; by money it is SKILL.state < **ReAct** < Memory < Stateful.

The Stateful row is the one to keep. It sends almost exactly what ReAct sends. It puts a mutating state block in front of the transcript instead of behind it, which is where the paper's own Appendix A.3 template puts it, and pays **5.7 times more** for it. Prompt order is a first-order cost variable.

Two things scope this. Caching has a minimum prefix length, and the procedure used here (~1,300 tokens) is below it — measured directly, Haiku 4.5 does not cache a ~2,200-token system block and does cache a ~4,200-token one. With a longer procedure every arm would cache its static part and the 1.39x would move. The direction is arithmetic and holds regardless; the magnitude belongs to this prompt length and this model.

## Where explicit state actually wins

The paper's stated limitation **L2** predicts that the method will fail when the objective depends on provenance — on *why* a fact is in the state, not just what it says. So the natural probe is the case where a fact's provenance is overturned: the agent files a pallet at step `t`; at `t+10` a correction says that put-away never completed and the shelf is empty. From then on that shelf is the lowest free one, and **every subsequent decision** depends on having applied the correction.

Two design choices make this measurable at all. First, the unit of counting is not the episode or the seed but the **dependent step**: each step after the notice whose correct action changes because of it. Second, the seeds are chosen by measured range before spending anything — a perfect-but-deaf agent, one that executes everything correctly and simply never applies the correction, defines the floor, and seeds differ enormously in how much room there is above it:

| seed | perfect-but-deaf floor | dependent steps |
|---|---|---|
| 0 | 0.931 | 2 |
| 1 | 0.893 | 3 |
| 2 | **1.000** | **0** |
| 4 | **0.522** | **11** |
| 6 | 0.846 | 4 |
| 10 | 0.759 | 7 |

Seeds 4, 10 and 6 carry 22 dependent steps per repetition. Seeds 0, 1 and 2 carry five between them, and one of them carries none at all. Computing that table costs zero API calls.

<figure class="wfs-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Percentage of dependent steps on which the retroactive correction was applied. With the full transcript, Haiku applies it on 3 of 44 steps and Sonnet on 15 of 38. With explicit state, both models apply it on every single step: 44 of 44 and 49 of 49.">
  <defs>
    <style>
      .pl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .pv { fill:#f8fafc; font:600 11.5px ui-monospace,'JetBrains Mono',monospace; }
      .pt { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .pm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .ph { fill:#fbbf24; font:600 11.5px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="24" class="pt">Dependent steps on which the correction was applied</text>
  <text x="16" y="42" class="pm">seeds 4, 10 and 6 · 2 repetitions · episodes with &gt;3 truncated replies excluded</text>

  <line x1="150" y1="56" x2="150" y2="196" stroke="rgba(255,255,255,0.12)"/>
  <line x1="530" y1="56" x2="530" y2="196" stroke="rgba(255,255,255,0.12)"/>
  <text x="150" y="212" class="pm" text-anchor="middle">0%</text>
  <text x="530" y="212" class="pm" text-anchor="middle">100%</text>

  <text x="16" y="70" class="ph">Haiku 4.5</text>
  <g transform="translate(0,76)">
    <text x="144" y="11" class="pl" text-anchor="end">ReAct</text>
    <rect x="150" y="1" width="26" height="13" rx="2" fill="#64748b"/>
    <text x="184" y="12" class="pv">3/44 — 6.8%</text>
  </g>
  <g transform="translate(0,96)">
    <text x="144" y="11" class="pl" text-anchor="end">SKILL.state</text>
    <rect x="150" y="1" width="380" height="13" rx="2" fill="#2dd4bf"/>
    <text x="404" y="12" class="pv" style="fill:#0f172a">44/44 — 100%</text>
  </g>

  <text x="16" y="140" class="ph">Sonnet 5</text>
  <g transform="translate(0,146)">
    <text x="144" y="11" class="pl" text-anchor="end">ReAct</text>
    <rect x="150" y="1" width="150" height="13" rx="2" fill="#64748b"/>
    <text x="308" y="12" class="pv">15/38 — 39.5%</text>
  </g>
  <g transform="translate(0,166)">
    <text x="144" y="11" class="pl" text-anchor="end">SKILL.state</text>
    <rect x="150" y="1" width="380" height="13" rx="2" fill="#2dd4bf"/>
    <text x="404" y="12" class="pv" style="fill:#0f172a">49/49 — 100%</text>
  </g>
</svg>
<figcaption>Explicit state does not miss a single correction in 93 dependent steps across two models. The full transcript, which physically contains the correction, applies it on 18 of 82.</figcaption>
</figure>

Three things only visible when you count decisions rather than average episodes:

**The transcript arm fails all-or-nothing per scenario.** In Haiku, errors of any other kind are exactly zero across all six episodes: its *only* mistakes are the correction steps, and it misses them in blocks — 11 of 11, 7 of 7, 4 of 4. This is not an agent drifting. It is an agent executing a 50-step procedure flawlessly while never updating one fact. In Sonnet the same pattern appears bimodally: one episode applies all 11, the next repetition on the same scenario misses all 11.

**More capability helps and does not solve it.** Sonnet with the full transcript goes from 6.8% to 39.5%. It reconciles the contradiction far more often, and still loses three decisions in five.

**Explicit state buys it, and in Sonnet charges for it elsewhere.** Sonnet emitted 66 out-of-schema patches across 8 episodes, exhausting the retry budget on 10 steps that then produced no action at all, which cost it 21 errors of other kinds. Haiku emitted zero. Accuracy on the correction is 100% in both; the runtime's *reliability* is model-dependent, and that is a property of the method rather than of the task.

The mechanism is unglamorous. Explicit state has exactly one place where the fact lives, and correcting it is the operation the runtime already performs every step. The transcript erases nothing: it holds the original record and its retraction simultaneously, and every subsequent step has to resolve the contradiction again from scratch.

**Having a single place where the truth lives is an advantage precisely when the truth changes** — which is the opposite of what L2 predicts, and it replicates across both models.

## Where explicit state does nothing

The complementary probe: at step `t` the environment announces a shelf is quarantined. At `t + k` that shelf is the lowest free one and the correct action is to skip it. The dependent step and the shelf are identical for every `k`; only the distance between the information and its use moves. Nothing gets contradicted — the fact simply has to survive.

Here explicit state, by itself, does nothing at all. At `k=40`, Haiku with a state object and no field for the notice: **0 out of 24**. What changes the outcome is not the runtime but where the fact is allowed to live:

<figure class="wfs-fig">
<svg viewBox="0 0 600 210" role="img" aria-label="Three ways of keeping a standing fact available, measured on Haiku over 24 paired episodes. With no schema field the agent acts on it 0 times out of 24. Repeating the original notice verbatim gets 16 of 24. Repeating three distilled fields gets 24 of 24. The three Wilson confidence intervals do not overlap.">
  <defs>
    <style>
      .rl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .rv { fill:#f8fafc; font:600 11.5px ui-monospace,'JetBrains Mono',monospace; }
      .rt { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .rm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="24" class="rt">Acting on a standing fact 40 steps later</text>
  <text x="16" y="42" class="rm">Haiku 4.5 · 3 seeds × 8 repetitions · paired · bars are 95% Wilson intervals</text>

  <line x1="215" y1="54" x2="215" y2="176" stroke="rgba(255,255,255,0.12)"/>
  <line x1="530" y1="54" x2="530" y2="176" stroke="rgba(255,255,255,0.12)"/>
  <text x="215" y="192" class="rm" text-anchor="middle">0%</text>
  <text x="530" y="192" class="rm" text-anchor="middle">100%</text>

  <g transform="translate(0,66)">
    <text x="196" y="12" class="rl" text-anchor="end">no field for it</text>
    <line x1="215" y1="8" x2="259" y2="8" stroke="#64748b" stroke-width="3"/>
    <circle cx="215" cy="8" r="5" fill="#64748b"/>
    <text x="272" y="12" class="rv">0/24 — 0%</text>
  </g>
  <g transform="translate(0,106)">
    <text x="196" y="12" class="rl" text-anchor="end">notice repeated verbatim</text>
    <line x1="363" y1="8" x2="473" y2="8" stroke="#f59e0b" stroke-width="3"/>
    <circle cx="426" cy="8" r="5" fill="#f59e0b"/>
    <text x="353" y="12" class="rv" style="fill:#fbbf24" text-anchor="end">16/24 — 67%</text>
  </g>
  <g transform="translate(0,146)">
    <text x="196" y="12" class="rl" text-anchor="end">three fields, distilled</text>
    <line x1="486" y1="8" x2="530" y2="8" stroke="#2dd4bf" stroke-width="3"/>
    <circle cx="530" cy="8" r="5" fill="#2dd4bf"/>
    <text x="476" y="12" class="rv" style="fill:#5eead4" text-anchor="end">24/24 — 100%</text>
  </g>
</svg>
<figcaption>Availability accounts for two thirds of the effect; distillation accounts for the rest, and it is the third that separates "usually" from "always".</figcaption>
</figure>

Three interventions, measured paired on the same seeds:

- **A schema field that names the fact** (`quarantined_shelves`) takes Haiku from 0/24 to 100% and Sonnet from 12% to 75%. It works because the schema's designer anticipated exactly this fact — which is the paper's limitation **L1**, now with a number attached.
- **A generic free-text field** (`notes`, no indication of what to put in it) scores 5/24 = 21% on Sonnet, confidence interval 9–40%, statistically indistinguishable from having no field at all. On one seed it scores 0/8, *worse* than nothing.
- **Re-injecting the standing fact into every observation** takes Haiku from 0/24 to **24/24** and Sonnet from 12% to 83%, and requires anticipating nothing.

And the last one splits further. The re-injected banner carries three of the original notice's fifteen fields, hoisted to the top. Repeating the **entire original notice** verbatim instead, same position, same header, 981 characters instead of 67, scores **16/24 = 67%**. All three Wilson intervals are disjoint, and the distilled version wins on all three seeds.

So: making the fact available recovers two thirds of the failure. The remaining third is distillation — with the same fact present at every single step, buried among fourteen fields of operational metadata, the agent overlooks it one time in three.

The practical version, scoped to what was measured (one environment, `k=40`, the three-level comparison on Haiku only): **if a fact stays true across many steps, re-inject the field, not the record.** A system that replays the whole document into context leaves a third of the failures on the table. This is the same shape as the finding in [The Scaffolding You Pay For](/en/blog/the-scaffolding-you-pay-for) — the intervention that survives is the one that changes what the model is looking at, not the one that adds structure around it.

## The instrument, and two results it killed

An experiment on agents produces numbers whether or not it is measuring anything, and the failure mode is not noise. It is a clean result.

Two findings in this project were fully written up — tables, non-overlapping confidence intervals, a mechanism — before being retracted by checks that cost nothing. Both are checks any replication of this kind needs:

**Compute the floor before the effect.** Simulate an agent that is perfect except that it ignores exactly the thing you are measuring. On the correction probe that agent scores 0.931, 0.893 and 1.000 on seeds 0, 1 and 2 — so the maximum possible effect on those seeds averages 0.06, and a seed with a floor of 1.000 carries no information at all. A measured separation of **+0.199** on those seeds was therefore impossible before anyone looked at what caused it. The cause was truncation: the transcript arm was losing 8 to 19 replies out of 50 to the output cap, and a reply cut off before its `Action:` line is a step with no action, which scores as an error.

**Count steps with no action separately from steps with a wrong action.** They are different events with different fixes, and averaging them together is what let a budget artefact look like a cognitive one. Raising the cap does not fix it either: on the same scenario, 600 tokens gave 19 truncated replies, 1,500 gave 11, and 4,000 gave 18. A fixed output budget penalises the arm whose prompt grows, because its replies grow with the transcript — and the original paper reports ReAct degrading as `T` grows without reporting truncation.

**Decompose the score by the type of step it averages.** A second environment was built as a domain control and reported a sign-flipping interaction between models, with non-overlapping intervals on both separations. Instrumented, all four cells got the load-bearing rule right — 12/12, 14/15, 12/13, and all of them. Only 5 of 34 actionable steps tested the rule at all, a blind policy scored 0.853, and the entire reported effect lived in routine steps and in out-of-schema patches. The whole section was withdrawn.

**And know your noise floor.** The same seed, byte-identical prompt, eight repetitions: one seed alternated hit and miss eight times running. Single-step accuracy carries tens of points of sampling noise; an average over ~170 events carries almost none; token accounting carries none at all. Every claim that fell in this project was of the first kind, and the ones that survived are of the second and third.

## What I would take from this

- **The advertised axis is the wrong axis.** How much context you keep barely moves accuracy on a task where the information is nearby. What moves it is whether the load-bearing fact is present, current, and distilled at the moment of the decision.
- **Explicit state earns its place when facts get invalidated.** One location to correct beats a transcript holding a claim and its retraction — 93/93 against 18/82, in both models. If your agent's world only ever accumulates, this buys you much less.
- **Compressing context and caching context are in conflict.** Every method that rewrites its prefix pays full price for it. Measure the bill, not the token count, and put your mutating block *after* whatever you want cached.
- **A schema protects only against what its designer anticipated.** A generic field to "write things down in" measured indistinguishable from no field at all.

The claims here are scoped to two models, one environment that discriminates, and a procedure short enough to sit below the caching threshold. What generalises is not any single number but the arithmetic: check that your effect fits inside the range your effect can have.

---

*Replication of [SKILL.state: Scalable Long-Horizon Agent Skills](https://arxiv.org/abs/2608.26263) (Badhe, Tiwari and Chung, accepted at EMNLP). Related: [The Scaffolding You Pay For](/en/blog/the-scaffolding-you-pay-for) on interventions that cost more than they buy, and [The Forgetting You Don't Measure](/en/blog/forgetting-you-dont-measure) on what a single benchmark number hides.*
