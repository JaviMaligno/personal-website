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

> **A replication of *SKILL.state: Scalable Long-Horizon Agent Skills* (Badhe, Tiwari and Chung, accepted at EMNLP) across two models and 500+ episodes.** Every headline number here is a count of decisions, not an average of episodes.

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

SkillExecBench has no public code, so the environment here is a reimplementation from the paper's §4.1 description — a 500-shelf warehouse with dense pipe-separated event records, matched on **context density** rather than literal content, and running 1.2–1.5x heavier than theirs by average prompt size.

One difference is deliberate and worth stating up front: **their Table 1 runs on Gemini-3-Flash**, with Gemma-4-31B-it and Qwen-3-8B-it elsewhere in the paper. This replication runs Claude Haiku 4.5 and Claude Sonnet 5. Where a result here disagrees with theirs, the first candidate explanation is the model family, not the method — and saying which of the two it is turns out to be most of the work.

## Half of it replicates

The cost curve reproduces exactly. Average prompt at T=50, in the same unit the paper reports — characters: SKILL.state **2,157**, flat from T=10 (2,136) to T=50, against their 1,773. ReAct: **16,437** and growing linearly, against their 11,931. O(1) against O(T), as advertised, at 1.2–1.4x their density.

The accuracy half does not, and the interesting part is that it does not at any horizon they tested. Their degradation is a scaling effect — ReAct falls from 0.90 at T=10 to 0.74 at T=200 — so the only honest way to check it is to run their whole range.

<figure class="wfs-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Score against horizon for both models. Gemini-3-Flash with the full transcript falls from 0.90 at T=10 to 0.74 at T=200, and its explicit-state arm from 1.00 to 0.94. Claude Haiku 4.5 stays at 1.00 in both arms across every horizon, ending at 0.987 for the transcript and 1.00 for explicit state.">
  <defs>
    <style>
      .sm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .st { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .ss { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .sl { fill:#e2e8f0; font:11px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="22" class="st">Their degradation, and the same measurement on Claude</text>
  <text x="16" y="40" class="ss">score against horizon · ReAct solid, SKILL.state dashed · 3 seeds each</text>
  <line x1="88" y1="62.0" x2="568" y2="62.0" stroke="rgba(255,255,255,0.09)"/>
  <text x="80" y="66.0" class="sm" text-anchor="end">1.00</text>
  <line x1="88" y1="114.7" x2="568" y2="114.7" stroke="rgba(255,255,255,0.09)"/>
  <text x="80" y="118.7" class="sm" text-anchor="end">0.90</text>
  <line x1="88" y1="167.3" x2="568" y2="167.3" stroke="rgba(255,255,255,0.09)"/>
  <text x="80" y="171.3" class="sm" text-anchor="end">0.80</text>
  <line x1="88" y1="220.0" x2="568" y2="220.0" stroke="rgba(255,255,255,0.09)"/>
  <text x="80" y="224.0" class="sm" text-anchor="end">0.70</text>
  <text x="96" y="240" class="sm" text-anchor="middle">10</text>
  <text x="212" y="240" class="sm" text-anchor="middle">25</text>
  <text x="328" y="240" class="sm" text-anchor="middle">50</text>
  <text x="444" y="240" class="sm" text-anchor="middle">100</text>
  <text x="560" y="240" class="sm" text-anchor="middle">200</text>
  <polyline points="96,114.7 212,104.1 328,125.2 444,146.3 560,198.9" fill="none" stroke="#f59e0b" stroke-width="2.2" stroke-dasharray="none" stroke-linejoin="round"/>
  <circle cx="96" cy="114.7" r="3.4" fill="#f59e0b"/>
  <circle cx="212" cy="104.1" r="3.4" fill="#f59e0b"/>
  <circle cx="328" cy="125.2" r="3.4" fill="#f59e0b"/>
  <circle cx="444" cy="146.3" r="3.4" fill="#f59e0b"/>
  <circle cx="560" cy="198.9" r="3.4" fill="#f59e0b"/>
  <polyline points="96,62.0 212,62.0 328,83.1 444,93.6 560,93.6" fill="none" stroke="#f59e0b" stroke-width="2.2" stroke-dasharray="5 3" stroke-linejoin="round"/>
  <circle cx="96" cy="62.0" r="3.4" fill="#f59e0b"/>
  <circle cx="212" cy="62.0" r="3.4" fill="#f59e0b"/>
  <circle cx="328" cy="83.1" r="3.4" fill="#f59e0b"/>
  <circle cx="444" cy="93.6" r="3.4" fill="#f59e0b"/>
  <circle cx="560" cy="93.6" r="3.4" fill="#f59e0b"/>
  <polyline points="96,62.0 212,62.0 328,62.0 444,62.0 560,68.8" fill="none" stroke="#2dd4bf" stroke-width="2.2" stroke-dasharray="none" stroke-linejoin="round"/>
  <circle cx="96" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="212" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="328" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="444" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="560" cy="68.8" r="3.4" fill="#2dd4bf"/>
  <polyline points="96,62.0 212,62.0 328,62.0 444,62.0 560,62.0" fill="none" stroke="#2dd4bf" stroke-width="2.2" stroke-dasharray="5 3" stroke-linejoin="round"/>
  <circle cx="96" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="212" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="328" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="444" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <circle cx="560" cy="62.0" r="3.4" fill="#2dd4bf"/>
  <text x="300" y="262" class="sm" text-anchor="middle">horizon T (steps)</text>
  <line x1="120" y1="282" x2="150" y2="282" stroke="#f59e0b" stroke-width="2.2"/>
  <text x="156" y="286" class="sl">Gemini-3-Flash (their Table 1)</text>
  <line x1="330" y1="282" x2="360" y2="282" stroke="#2dd4bf" stroke-width="2.2"/>
  <text x="366" y="286" class="sl">Claude Haiku 4.5 (this replication)</text>
  <text x="120" y="298" class="ss">At T=200 their transcript arm is at 0.74. Ours is at 0.987, and misses one decision in 600.</text>
</svg>
<figcaption>Their transcript arm degrades with the horizon exactly as they report. On a different model family, on an environment 1.2–1.4x denser than theirs, run out to the same T=200, it does not.</figcaption>
</figure>

| runtime | T=10 | T=25 | T=50 | T=100 | T=200 |
|---|---|---|---|---|---|
| ReAct | 1.00 | 1.00 | 1.00 | 1.00 | **0.99 ±0.02** |
| SKILL.state | 1.00 | 1.00 | 1.00 | 1.00 | **1.00 ±0.00** |
| Stateful | 1.00 | 1.00 | 1.00 | 0.99 ±0.02 | — |
| Memory | 1.00 | 0.96 | 0.75 | 0.72 | — |

At T=200 the transcript arm is holding a 48,000-character prompt and 690 actionable events, and it misses **one decision out of roughly 600**. On Gemini-3-Flash the same arm misses a quarter of them. Re-measuring the T=50 SKILL.state cell with 3 seeds × 6 repetitions gives 18/18 at exactly 1.000, zero deviation, so this is not a lucky run either.

⚠️ **The Memory row is the one number here I do not trust.** Its runtime is the only one that makes a second call per step, and at T=100 it lost 23, 14 and 2 replies out of 100 to the output cap on the three seeds — scoring 0.58, 0.67 and 0.91 in that order. That is not a summarising failure, it is a budget failure, and it is being re-measured with a budget that removes it.

The reason the other three hold is worth naming, because it governs everything after: in this task the load-bearing information is never far away. The freed shelf an agent has to reuse sits **1.9 positions from the top of the stack on average**, at most 7. Making the horizon longer adds steps without moving information further from its use. If you want to measure whether a runtime remembers, `T` is the wrong knob — which is what the rest of this article is about.

## The token count is not the bill

The paper compares **tokens**. Anyone running this compares **money**, and the moment prompt caching is on those are different quantities. An append-only transcript is the ideal cacheable prefix: every step re-sends exactly what it sent before, plus a suffix. A block that mutates invalidates the cache from the point it mutates.

There is one number you have to measure before any of this means anything: **the minimum cacheable prefix**. Below it, nothing caches at all. On Claude Haiku 4.5 it is **4,096 tokens exactly** — a 3,984-token system block, sent twice, reads nothing from cache; a 4,116-token one reads all of it. So the answer depends on how long your procedure is, and both cases are worth having.

<figure class="wfs-fig">
<svg viewBox="0 0 600 322" role="img" aria-label="Cost of one 50-step episode under two procedure lengths. With a short procedure SKILL.state is billed 109k tokens and ReAct 152k, a 1.39x advantage against 7.54x in raw tokens. With a realistic 5,243-token procedure SKILL.state falls to 64k and ReAct rises to 162k, a 2.51x advantage. Stateful is billed around 850k in both, roughly five times ReAct for nearly identical content.">
  <defs>
    <style>
      .cl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .cv { fill:#f8fafc; font:600 11.5px ui-monospace,'JetBrains Mono',monospace; }
      .ct { fill:#fbbf24; font:600 12px ui-sans-serif,system-ui; }
      .cs { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .cm { fill:#94a3b8; font:10px ui-monospace,'JetBrains Mono',monospace; }
      .ch { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="22" class="ch">What the same 50-step episode actually costs</text>
  <text x="16" y="40" class="cs">Claude Haiku 4.5 · input only · 3 seeds</text>
  <text x="592" y="40" class="cs" text-anchor="end">$ per 1,000 episodes</text>
  <text x="16" y="70" class="ct">Short procedure — 1,491 tokens</text>
  <text x="16" y="85" class="cs">below the 4,096-token caching threshold: only ReAct's growing transcript caches</text>
  <text x="126" y="110" class="cl" text-anchor="end">SKILL.state</text>
  <rect x="132" y="100" width="33.2" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="100" width="33.2" height="13" rx="2" fill="#2dd4bf"/>
  <text x="172.2" y="110" class="cm">109k</text>
  <text x="592" y="110" class="cv" text-anchor="end">$109</text>
  <text x="126" y="130" class="cl" text-anchor="end">ReAct</text>
  <rect x="132" y="120" width="251.9" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="120" width="46.4" height="13" rx="2" fill="#2dd4bf"/>
  <text x="390.9" y="130" class="cm">826k</text>
  <text x="592" y="130" class="cv" text-anchor="end">$152</text>
  <text x="126" y="150" class="cl" text-anchor="end">Memory</text>
  <rect x="132" y="140" width="95.5" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="140" width="95.5" height="13" rx="2" fill="#2dd4bf"/>
  <text x="234.5" y="150" class="cm">313k</text>
  <text x="592" y="150" class="cv" text-anchor="end">$313</text>
  <text x="126" y="170" class="cl" text-anchor="end">Stateful</text>
  <rect x="132" y="160" width="266.3" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="160" width="266.3" height="13" rx="2" fill="#2dd4bf"/>
  <text x="405.3" y="170" class="cm">873k</text>
  <text x="592" y="170" class="cv" text-anchor="end">$873</text>
  <text x="16" y="188" class="ct">Realistic procedure — 5,243 tokens</text>
  <text x="16" y="203" class="cs">above the threshold: every arm now caches its static half</text>
  <text x="126" y="228" class="cl" text-anchor="end">SKILL.state</text>
  <rect x="132" y="218" width="91.5" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="218" width="19.5" height="13" rx="2" fill="#2dd4bf"/>
  <text x="230.5" y="228" class="cm">300k</text>
  <text x="592" y="228" class="cv" text-anchor="end">$64</text>
  <text x="126" y="248" class="cl" text-anchor="end">ReAct</text>
  <rect x="132" y="238" width="313.8" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="238" width="49.4" height="13" rx="2" fill="#2dd4bf"/>
  <text x="452.8" y="248" class="cm">1029k</text>
  <text x="592" y="248" class="cv" text-anchor="end">$162</text>
  <text x="126" y="268" class="cl" text-anchor="end">Memory</text>
  <rect x="132" y="258" width="150.7" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="258" width="78.7" height="13" rx="2" fill="#2dd4bf"/>
  <text x="289.7" y="268" class="cm">494k</text>
  <text x="592" y="268" class="cv" text-anchor="end">$258</text>
  <text x="126" y="288" class="cl" text-anchor="end">Stateful</text>
  <rect x="132" y="278" width="330.0" height="13" rx="2" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="3 2"/>
  <rect x="132" y="278" width="258.9" height="13" rx="2" fill="#2dd4bf"/>
  <text x="469.0" y="288" class="cm">1082k</text>
  <text x="592" y="288" class="cv" text-anchor="end">$849</text>
  <rect x="132" y="306" width="26" height="9" rx="2" fill="#2dd4bf"/>
  <text x="165" y="314" class="cs">what you are billed</text>
  <rect x="322" y="306" width="26" height="9" rx="2" fill="none" stroke="#64748b" stroke-dasharray="3 2"/>
  <text x="355" y="314" class="cs">raw tokens</text>
</svg>
<figcaption>Raw tokens are the dashed outline; the filled bar is what you are billed. Every method that compresses rewrites its prefix, and rewriting the prefix kills the cache — until the procedure itself is long enough to cache on its own.</figcaption>
</figure>

**Short procedure — 1,491 tokens.** Below the threshold, so no arm's procedure caches. Only ReAct caches, and only because its accumulated transcript pushes the prefix past 4,096 on its own. **SKILL.state's advantage over ReAct falls from 7.54x in raw tokens to 1.39x in money.** The orderings disagree too: by tokens it is SKILL.state < Memory < ReAct < Stateful; by money, SKILL.state < **ReAct** < Memory < Stateful.

**Realistic procedure — 5,243 tokens.** A field reference for the 112 fields the events actually carry, six exception rules, five worked examples. Real operating procedures look like this. Now every arm's static half caches, and two things happen:

- **SKILL.state gets 41% cheaper: $109 → $64 per thousand episodes.** The procedure got three and a half times longer and the bill went down, because it crossed the threshold. Memory goes from saving 0% to 48%, Stateful from 0% to 22%.
- **The advantage in money widens to 2.51x while the advantage in raw tokens narrows to 3.43x.** In both conditions the raw token count is the wrong number to quote: it says 7.54x or 3.43x where the invoice says 1.39x or 2.51x.

The row to actually act on is Stateful. It sends almost exactly what ReAct sends. It puts a mutating state block **in front of** the transcript instead of behind it — which is where the paper's own Appendix A.3 template puts it — and is billed **$849 against $162 per thousand episodes**. Same content, same task, same score of 1.00. A 5.2x difference, and it holds in both conditions.

On Sonnet 5, at 3x the input price, those become $2,546 against $486. Per thousand episodes, prompt order is a four-figure line item.

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
<svg viewBox="0 0 600 218" role="img" aria-label="Every decision that depended on the retroactive correction, one cell each. With explicit state all 44 Haiku cells and all 49 Sonnet cells are filled. With the full transcript, Haiku fills 3 of 44 and misses whole episodes at a time; Sonnet fills 15 of 38, applying every correction in one episode and none in the next on the same scenario.">
  <defs>
    <style>
      .dl { fill:#e2e8f0; font:11.5px ui-sans-serif,system-ui; }
      .dt { fill:#f8fafc; font:600 13px ui-sans-serif,system-ui; }
      .dm { fill:#94a3b8; font:10.5px ui-sans-serif,system-ui; }
      .dh { fill:#fbbf24; font:600 11.5px ui-sans-serif,system-ui; }
    </style>
  </defs>
  <text x="16" y="24" class="dt">Every decision that depended on the correction</text>
  <text x="16" y="42" class="dm">one cell = one decision · gaps separate episodes · seeds 4, 10 and 6</text>
  <text x="16" y="62" class="dh">Haiku 4.5</text>
  <text x="16" y="130" class="dh">Sonnet 5</text>
    <text x="184" y="80" class="dl" text-anchor="end">ReAct · 3/44</text>
    <rect x="192.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="199.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="206.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="213.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="220.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="227.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="234.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="247.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="254.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="261.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="268.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="275.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="282.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="289.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="302.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="309.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="316.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="323.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="330.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="337.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="344.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="351.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="358.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="365.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="372.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="385.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="392.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="399.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="406.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="413.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="420.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="427.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="434.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="441.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="448.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="455.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="468.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="475.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="482.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="489.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="502.0" y="70" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="509.0" y="70" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="516.0" y="70" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="523.0" y="70" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <text x="184" y="102" class="dl" text-anchor="end">SKILL.state · 44/44</text>
    <rect x="192.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="199.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="206.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="213.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="220.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="227.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="234.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="247.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="254.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="261.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="268.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="275.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="282.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="289.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="302.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="309.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="316.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="323.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="330.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="337.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="344.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="351.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="358.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="365.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="372.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="385.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="392.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="399.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="406.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="413.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="420.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="427.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="434.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="441.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="448.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="455.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="468.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="475.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="482.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="489.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="502.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="509.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="516.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="523.0" y="92" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <text x="184" y="148" class="dl" text-anchor="end">ReAct · 15/38</text>
    <rect x="192.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="199.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="212.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="219.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="226.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="233.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="240.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="247.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="254.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="267.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="274.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="281.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="288.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="295.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="302.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="309.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="322.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="329.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="336.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="343.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="350.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="357.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="364.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="371.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="378.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="385.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="392.0" y="138" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="405.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="412.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="419.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="426.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="433.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="440.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="447.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="454.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="461.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="468.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <rect x="475.0" y="138" width="5.7" height="13" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
    <text x="184" y="170" class="dl" text-anchor="end">SKILL.state · 49/49</text>
    <rect x="192.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="199.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="212.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="219.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="226.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="233.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="240.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="247.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="254.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="267.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="274.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="281.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="288.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="295.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="302.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="309.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="322.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="329.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="336.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="349.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="356.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="363.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="370.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="377.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="384.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="391.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="398.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="405.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="412.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="419.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="432.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="439.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="446.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="453.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="460.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="467.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="474.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="481.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="488.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="495.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="502.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="515.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="522.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="529.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="536.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="549.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="556.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="563.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
    <rect x="570.0" y="160" width="5.7" height="13" rx="1.4" fill="#2dd4bf"/>
  <rect x="192" y="196" width="5.7" height="11" rx="1.4" fill="#2dd4bf"/>
  <text x="205" y="205" class="dm">correction applied</text>
  <rect x="342" y="196" width="5.7" height="11" rx="1.4" fill="#3f3f46" stroke="#64748b" stroke-width="0.8"/>
  <text x="355" y="205" class="dm">missed</text>
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

## Four checks this kind of experiment needs

An experiment on agents produces numbers whether or not it is measuring anything, and when it goes wrong the output is not noise — it is a clean result. Two findings here were fully written up, tables and non-overlapping intervals included, before these four removed them.

- **Compute the floor before the effect.** Simulate an agent that is perfect except that it ignores the thing you are measuring. On seeds 0, 1 and 2 that agent scores 0.931, 0.893 and 1.000, so the largest possible effect there averages 0.06 and one seed carries no information at all. A separation of **+0.199** measured on those seeds was arithmetically impossible before anyone asked what caused it.
- **Count steps with no action separately from steps with a wrong action.** That +0.199 was truncation: the transcript arm lost 8 to 19 replies out of 50 to the output cap, and a reply cut off before its `Action:` line scores as an error. Raising the cap does not fix it — 600 tokens gave 19 truncated replies, 1,500 gave 11, 4,000 gave 18. A fixed output budget penalises the arm whose prompt grows, and the paper reports ReAct degrading with `T` without reporting truncation.
- **Decompose the score by the type of step it averages.** A second environment reported a sign-flipping interaction between models, with non-overlapping intervals on both separations. Instrumented, all four cells got its load-bearing rule right; only 5 of 34 actionable steps tested that rule, a blind policy scored 0.853, and the whole reported effect lived in routine steps. The section was withdrawn.
- **Know your noise floor.** Same seed, byte-identical prompt, eight repetitions: one seed alternated hit and miss eight times running. Single-step accuracy carries tens of points of sampling noise; an average over ~170 events carries almost none; token accounting carries none.
## What I would take from this

- **The advertised axis is the wrong axis.** How much context you keep barely moves accuracy on a task where the information is nearby. What moves it is whether the load-bearing fact is present, current, and distilled at the moment of the decision.
- **Explicit state earns its place when facts get invalidated.** One location to correct beats a transcript holding a claim and its retraction — 93/93 against 18/82, in both models. If your agent's world only ever accumulates, this buys you much less.
- **Compressing context and caching context are in conflict.** Every method that rewrites its prefix pays full price for it. Measure the bill, not the token count, and put your mutating block *after* whatever you want cached.
- **A schema protects only against what its designer anticipated.** A generic field to "write things down in" measured indistinguishable from no field at all.

The claims here are scoped to two models, one environment that discriminates, and a procedure short enough to sit below the caching threshold. What generalises is not any single number but the arithmetic: check that your effect fits inside the range your effect can have.

---

*Replication of [SKILL.state: Scalable Long-Horizon Agent Skills](https://arxiv.org/abs/2608.26263) (Badhe, Tiwari and Chung, accepted at EMNLP). Related: [The Scaffolding You Pay For](/en/blog/the-scaffolding-you-pay-for) on interventions that cost more than they buy, and [The Forgetting You Don't Measure](/en/blog/forgetting-you-dont-measure) on what a single benchmark number hides.*
