---
title: "Explicit State Doesn't Forget. It Misremembers."
description: "The second half of my SKILL.state replication, on the paper's own model and a second one, with every cell repeated. Explicit state holds exactly where the paper says it does. Where it breaks, it breaks by writing the state wrong — and the runtime that keeps the transcript alongside it barely notices."
pubDate: 2026-10-21
tags: ["AI", "Agents", "Context Engineering", "Evaluation", "Research"]
lang: en
translationKey: explicit-state-misremembers
heroImage: "/blog/explicit-state-misremembers.png"
repoUrl: https://github.com/JaviMaligno/delayed-relevance
linkedinLinks:
  - label: "The paper (SKILL.state)"
    url: "https://arxiv.org/abs/2608.26263"
---

<style>
.esm-fig { margin: 2rem 0; }
.esm-fig svg { width: 100%; height: auto; display: block; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.esm-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
.esm-fig .t { fill: #e2e8f0; font: 13px system-ui, sans-serif; }
.esm-fig .m { fill: #94a3b8; font: 12px system-ui, sans-serif; }
.esm-fig .mono { fill: #e2e8f0; font: 12px ui-monospace, 'JetBrains Mono', monospace; }
.esm-fig .h { fill: #f8fafc; font: 600 14px system-ui, sans-serif; }
</style>

In the [first half of this replication](/en/blog/when-the-fact-stops-being-true) I ran
[SKILL.state](https://arxiv.org/abs/2608.26263) on Claude and found that its headline
degradation did not appear there. The obvious objection is that the paper runs on
Gemini-3-Flash, not Claude. So this half runs on theirs — `gemini-3-flash-preview`
through Vertex, in an environment rebuilt to match their Appendix B — plus Claude Haiku
4.5 under the same environment and output cap, with **every cell repeated** and
every episode kept as a per-step trace.

The short version: the paper's central claim holds on its own model, more cleanly than
the paper reports it. On a second model it does not, and the way it fails is the
interesting part. Explicit state does not lose track of the procedure. It **writes the
state wrong**, and nothing checks the write.

## Repeat every cell, even at temperature zero

The protocol started from an assumption that sounds safe: with greedy decoding, a seed is
an instance of the environment, and one run per cell is enough. It is not. The same cell,
repeated five times at `temperature=0`, scored anywhere between **0.830 and 0.960**. The
distribution has a long left tail, because failures cascade: the agent stores one pallet
on the wrong shelf, and every later decision that touches that shelf inherits the error.

Three conclusions written up from single runs — an environment effect, a monotonic
noise curve, a noise estimate — did not survive repetition. Every figure below is a mean over
15 to 24 runs, with the spread computed over runs, not over seed means.

## On their model, the thesis holds

Their Table 1 has four runtimes: ReAct (full transcript), Memory (rolling summary),
Stateful (state block plus transcript) and SKILL.state (state block only). Here are the
two that carry the argument, ours against theirs:

<figure class="esm-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="On Gemini-3-Flash, SKILL.state scores 1.000 at every horizon from 10 to 200 steps, and ReAct falls only to 0.913 at T=200, against 0.74 in the paper.">
  <text x="20" y="24" class="h">Score against horizon, gemini-3-flash-preview (15 runs per cell)</text>
  <line x1="80" y1="40" x2="80" y2="250" stroke="#64748b"/>
  <line x1="80" y1="250" x2="580" y2="250" stroke="#64748b"/>
  <text x="72" y="44" class="m" text-anchor="end">1.00</text>
  <text x="72" y="114" class="m" text-anchor="end">0.90</text>
  <text x="72" y="184" class="m" text-anchor="end">0.80</text>
  <text x="72" y="254" class="m" text-anchor="end">0.70</text>
  <line x1="80" y1="110" x2="580" y2="110" stroke="rgba(255,255,255,0.06)"/>
  <line x1="80" y1="180" x2="580" y2="180" stroke="rgba(255,255,255,0.06)"/>
  <text x="110" y="270" class="m" text-anchor="middle">10</text>
  <text x="220" y="270" class="m" text-anchor="middle">25</text>
  <text x="330" y="270" class="m" text-anchor="middle">50</text>
  <text x="440" y="270" class="m" text-anchor="middle">100</text>
  <text x="550" y="270" class="m" text-anchor="middle">200</text>
  <text x="330" y="290" class="m" text-anchor="middle">horizon T (steps)</text>
  <polyline points="110,40 220,40 330,68 440,82 550,82" fill="none" stroke="#2dd4bf" stroke-width="2" stroke-dasharray="6 4" opacity="0.7"/>
  <polyline points="110,110 220,96 330,124 440,152 550,222" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="6 4" opacity="0.7"/>
  <polyline points="110,40 220,40 330,40 440,40 550,40" fill="none" stroke="#2dd4bf" stroke-width="2.6"/>
  <polyline points="110,44.9 220,71.5 330,84.8 440,68 550,100.9" fill="none" stroke="#f59e0b" stroke-width="2.6"/>
  <circle cx="550" cy="40" r="3.5" fill="#2dd4bf"/>
  <circle cx="550" cy="100.9" r="3.5" fill="#f59e0b"/>
  <circle cx="550" cy="222" r="3.5" fill="#f59e0b" opacity="0.7"/>
  <text x="545" y="122" class="t" text-anchor="end">ReAct, ours 0.913</text>
  <text x="558" y="86" class="m" style="fill:#5eead4">0.94</text>
  <text x="545" y="218" class="t" text-anchor="end">ReAct, theirs 0.74</text>
  <text x="545" y="58" class="t" text-anchor="end">SKILL.state, ours 1.000</text>
  <rect x="96" y="194" width="208" height="42" fill="#1a1a24"/>
  <line x1="104" y1="206" x2="128" y2="206" stroke="#94a3b8" stroke-width="2.6"/>
  <text x="134" y="210" class="m">this replication</text>
  <line x1="104" y1="226" x2="128" y2="226" stroke="#94a3b8" stroke-width="2" stroke-dasharray="6 4"/>
  <text x="134" y="230" class="m">their Table 1</text>
</svg>
<figcaption>Solid lines are this replication, dashed lines their Table 1. SKILL.state (teal) does not miss once in 75 episodes. The full-transcript arm (amber) degrades far less than they report, and the gap widens with the horizon.</figcaption>
</figure>

**SKILL.state does not fail once in 75 episodes of up to 200 steps**, where theirs loses
six points. The direction of their thesis reproduces with room to spare. The magnitude
does not: our ReAct loses 0.080 between 10 and 200 steps where theirs loses 0.160, and
sits **17 points above theirs** at T=200. Reasoning budget, output cap and the three
environment gaps I could find against their appendix were each varied, and none moves it.
The model name is theirs, but `gemini-3-flash-preview` may not be the exact checkpoint
behind their `Gemini-3-Flash`, so I cannot rule the model out — only say I did not change
it.

One arm does not line up with theirs for a reason of mine: at T=200 our Memory's mean
prompt is fourteen times smaller than theirs, and at T=100 and T=200 it comes last. That
measures our summarisation policy, not summarisation as a category.

## On a second model, explicit state writes the state wrong

Same environment, same output cap, Claude Haiku 4.5 through Microsoft Foundry, 24 runs
per cell at the two ends of the horizon:

| T=200 | ReAct | Stateful | SKILL.state |
|---|---|---|---|
| Gemini-3-Flash | 0.913 | 0.930 | **1.000** |
| Claude Haiku 4.5 | 0.974 | **0.999** | 0.958 |

On Haiku the ordering turns over. The full-transcript arm is almost flat (−0.005 from
T=50 to T=200) and SKILL.state is the one that drops. To find out why, I replayed every
episode against the real environment and compared, step by step, the inventory the model
*believes* — the one in its state object — with the one that is actually on the shelves.

Every failure of explicit state has the same origin. In all 17 episodes where the belief
drifted from reality, the step that corrupted it was a **`Move` executed correctly with a
state patch written wrong**. `Move` is the only transition that makes the model copy one
shelf's contents into another key of its own state, and that copy is where it slips.

<figure class="esm-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="At step 132 the model executes a correct Move from shelf 7 to shelf 3, but writes into its state the contents of shelf 6 instead of shelf 7. Five steps later it ships from shelf 3 based on that belief and the environment rejects the action.">
  <text x="20" y="24" class="h">Haiku 4.5, seed 2 — the action is right, the patch is not</text>
  <rect x="20" y="40" width="170" height="190" rx="6" fill="none" stroke="rgba(255,255,255,0.1)"/>
  <text x="105" y="62" class="t" text-anchor="middle">step 132</text>
  <text x="105" y="84" class="mono" text-anchor="middle">Move 7 → 3</text>
  <text x="105" y="106" class="m" text-anchor="middle">action: correct ✓</text>
  <text x="34" y="140" class="m">reality, shelf 3</text>
  <text x="34" y="158" class="mono" style="fill:#5eead4">SKU-K · L-8558</text>
  <text x="34" y="190" class="m">state patch, shelf 3</text>
  <text x="34" y="208" class="mono" style="fill:#fbbf24">SKU-J · L-5231</text>
  <text x="34" y="222" class="m">(copied from shelf 6)</text>
  <line x1="190" y1="135" x2="228" y2="135" stroke="#64748b" stroke-width="1.6"/>
  <polygon points="228,130 238,135 228,140" fill="#64748b"/>
  <rect x="240" y="40" width="170" height="190" rx="6" fill="none" stroke="rgba(255,255,255,0.1)"/>
  <text x="325" y="62" class="t" text-anchor="middle">step 137</text>
  <text x="325" y="84" class="mono" text-anchor="middle">order: SKU-J</text>
  <text x="325" y="118" class="m" text-anchor="middle">belief: SKU-J on</text>
  <text x="325" y="134" class="m" text-anchor="middle">shelves 3 and 6</text>
  <text x="325" y="166" class="mono" text-anchor="middle" style="fill:#fbbf24">Ship shelf 3 ✗</text>
  <text x="325" y="190" class="m" text-anchor="middle">correct: shelf 6</text>
  <line x1="410" y1="135" x2="448" y2="135" stroke="#64748b" stroke-width="1.6"/>
  <polygon points="448,130 458,135 448,140" fill="#64748b"/>
  <rect x="460" y="40" width="120" height="190" rx="6" fill="none" stroke="rgba(255,255,255,0.1)"/>
  <text x="520" y="62" class="t" text-anchor="middle">step 138 →</text>
  <text x="520" y="92" class="m" text-anchor="middle">ACTION</text>
  <text x="520" y="108" class="m" text-anchor="middle">REJECTED</text>
  <text x="520" y="140" class="m" text-anchor="middle">state not</text>
  <text x="520" y="156" class="m" text-anchor="middle">corrected</text>
  <text x="520" y="190" class="t" text-anchor="middle" style="fill:#fbbf24">~25 failures</text>
  <text x="520" y="208" class="m" text-anchor="middle">follow</text>
</svg>
<figcaption>The failure SKILL.state was built to prevent is losing track of the procedure. The one it has is writing a wrong fact into the only place the agent looks — and even an explicit rejection from the environment does not make it re-read that fact.</figcaption>
</figure>

It is systematic, not noise: in 6 of the 8 runs of seed 2 the corruption happens at
exactly that step, and from there the agent cascades through about 25 failures. Not
every miswritten patch matters — in seed 0 the model copies the wrong *lot number*,
which no later decision reads, and those runs lose nothing — but the write is never
checked against what the action did. Gemini never made this error in 75 episodes; Haiku
wrote at least one wrong patch in 17 of 24 at T=200.

The paper does study erroneous state updates — premature overwrites, schema and type
errors. This is a narrower thing: a schema-valid patch with the wrong value in it, which
passes every check the runtime runs.

## Keeping the transcript absorbs it

The Stateful arm is the control that makes this legible. It maintains the same kind of
state block, and it also keeps the full transcript. On Haiku it makes **the same kind of
write error** — its belief drifts from reality in 8 of 15 episodes at T=200, always a
correct action with a miswritten patch — and loses nothing to it: the wrong state
prescribes a different action on only 4 steps, and on all 4 the model does what reality
requires. None of its failures comes from its state.

On Gemini the same arm behaves the other way round: its state drifts in 11 of 15
episodes, where SKILL.state on the same model never drifted, and 77 of its 211 failures
happen with a correct state in front of it. Stateful and SKILL.state also differ in
response format, parsing and retries, so this describes rather than isolates the effect
of the transcript. But the practical reading is hard to avoid: on the model that
misremembers, the redundant copy of the history is what catches it.

## Where explicit state wins, measured by the decision

The paper's recovery experiment asks what happens when a fact the agent was told stops
being true. I measure it per episode: on a correct trajectory the correction decides
exactly one step in each of the three scenarios used, so the question is whether the
agent gets that step right. Three models now, the same design on each:

<figure class="esm-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Retroactive correction applied: SKILL.state 24 of 24 on Haiku, 22 of 24 on Sonnet and 24 of 24 on Gemini; ReAct 1 of 24, 9 of 24 and 0 of 24.">
  <text x="20" y="24" class="h">A fact is retracted — does the agent act on the retraction?</text>
  <text x="20" y="44" class="m">episodes where the decisive step is right, out of 24 (seeds 4, 10, 6 × 8)</text>
  <text x="130" y="82" class="t" text-anchor="end">Haiku 4.5</text>
  <rect x="140" y="66" width="360" height="12" fill="#2dd4bf"/><text x="508" y="77" class="t">24</text>
  <rect x="140" y="82" width="15" height="12" fill="#f59e0b"/><text x="162" y="93" class="t">1</text>
  <text x="130" y="132" class="t" text-anchor="end">Sonnet 5</text>
  <rect x="140" y="116" width="330" height="12" fill="#2dd4bf"/><text x="478" y="127" class="t">22</text>
  <rect x="140" y="132" width="135" height="12" fill="#f59e0b"/><text x="282" y="143" class="t">9</text>
  <text x="130" y="182" class="t" text-anchor="end">Gemini-3-Flash</text>
  <rect x="140" y="166" width="360" height="12" fill="#2dd4bf"/><text x="508" y="177" class="t">24</text>
  <rect x="140" y="182" width="2" height="12" fill="#f59e0b"/><text x="150" y="193" class="t">0</text>
  <rect x="140" y="206" width="12" height="10" fill="#2dd4bf"/><text x="158" y="215" class="m">SKILL.state</text>
  <rect x="250" y="206" width="12" height="10" fill="#f59e0b"/><text x="268" y="215" class="m">ReAct (full transcript)</text>
</svg>
<figcaption>70 of 72 episodes with explicit state, 10 of 72 with the full transcript. Every missed decisive step is exactly what an agent that never heard the correction would do.</figcaption>
</figure>

**Explicit state applies the correction in 70 of 72 episodes (Wilson 95 % interval
90–99 %); the full transcript in 10 of 72 (8–24 %).** This is the paper's own claim, and
it reproduces cleanly. It is also smaller than the "93 of 93" I reported in the first
half: that count read its dependent steps off a simulated trajectory instead of the
agent's real one, and it could not register a miss that came from the agent doing
nothing. Measured on the real trajectory, the direction survives and the perfection does
not.

The other probe tests the limitation the paper declares: explicit state only protects
what its schema anticipated. A fact announced at step `t` first becomes relevant at step
`t+40`, and the agent either stored it somewhere or did not.

| SKILL.state, fact first needed 40 steps later | Haiku 4.5 | Gemini-3-Flash |
|---|---|---|
| No dedicated field | 0/24 | 0/24 |
| Free-form `notes` field | 10/24 | 1/24 |
| Schema field that names the fact | **24/24** | **16/24** |

Sonnet 5 is left out of this table because a quarter of its episodes never reach the test
— its trajectory has diverged by step `t+40` — and its cells need two rates to read
honestly; they are in the paper.

A place to put it is not enough; the place has to say what goes there. "No dedicated
field" does not mean nowhere to store it — Sonnet's few successes in that arm wrote the
quarantine straight into the inventory object — but the named field is what reliably
works, and these experiments cannot separate the extra slot from the cue its name gives.
For the runtime with no schema at all, a reminder attached to the observation does the
job: ReAct goes from 0–34 % to 71–96 % across the three models.

## The bill

The cost half of the first article stands. With a short procedure, caching shrinks
SKILL.state's input-cost advantage over the transcript from **7.5x to 1.4x** on
Anthropic, because an append-only transcript is an ideal cacheable prefix and a mutating
state block is not. On Vertex the same accounting barely moves the ratio — 7.5x in tokens
is 7.2x in effective input — because implicit caching there saved ReAct 6.8 % of its
input, against 82 % on Anthropic.

And prompt order, isolated this time, is a first-order cost variable. The same Stateful
runtime, sending the same content, with the transcript marked as a cacheable prefix in
both arms, costs **5.2x more** when its state block goes in front of the transcript than
behind it — 869k against 168k effective input tokens per 50-step episode — for the same
score. The paper's own prompt template puts the state block in front.

## What I would take from it

- **Explicit state does what the paper says on the paper's model.** On Gemini it never
  loses a step, and it applies retractions almost every time on all three models.
- **Its failure mode is writing, not remembering.** A schema can validate the shape of a
  patch; nothing in the runtime checks that the value matches what the action did. If
  you build on explicit state, that check is the part to add.
- **Keeping the transcript next to the state is cheap insurance on some models.** It cost
  Stateful nothing on Haiku and caught every wrong write that would have mattered.
- **Put the mutating part last.** It is a one-line change and, measured in isolation, a
  5.2x difference on the invoice.
- **Repeat the cell.** Temperature zero is not a reproducibility guarantee, and a single
  run hides exactly the tail where the failures live.

Every number here was recomputed from the per-step traces by an independent adversarial
reviewer — nine rounds of it, each allowed to read the raw data and none of the prose —
and the paper, the traces and the code are public.

---

*Code, per-step traces and the full paper draft: [JaviMaligno/delayed-relevance](https://github.com/JaviMaligno/delayed-relevance). The original paper: [SKILL.state (arXiv 2608.26263)](https://arxiv.org/abs/2608.26263). The first half of the replication: [When the Fact Stops Being True](/en/blog/when-the-fact-stops-being-true).*
