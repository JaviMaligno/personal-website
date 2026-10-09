---
title: "The New Model Is Cheaper. Testing It Isn't."
description: "Swapping the model behind a production agent is rarely plug-and-play, because the harness was tuned to the old one. The method I use to test a swap, what one swap cost, and the volume below which the evaluation pays the provider more than production does."
pubDate: 2026-11-02
tags: ["AI", "Evaluation", "LLM", "Engineering", "Economics"]
lang: en
translationKey: the-new-model-is-cheaper
heroImage: "/blog/the-new-model-is-cheaper.png"
---

<style>
.csw-fig { margin: 2rem 0; }
.csw-fig svg { width: 100%; height: auto; display: block; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.csw-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

In September a new generation of the model behind one of the services I maintain came out. On the same cases, its small tier cost almost half as much per classification as the one in production. On paper, that decision makes itself.

Testing the swap properly took several days and **between 47 and 65 dollars of model tokens**. The service runs around **500 classifications a month**, and its model bill in production was about **five dollars a month**. At that volume, the saving pays back the tokens of the test alone in about **two years**. The model it would replace had been on the market for **75 days**.

Both halves of that are worth looking at: why a swap needs that much testing, and what follows when the test costs more than the swap saves.

## Why a better model can do worse

A leaderboard measures a model. What you ship is a system: the model plus everything around it — prompts, tool definitions and their descriptions, how responses are parsed, reasoning settings, budgets and deadlines. Call that the **harness**. Every part of it was shaped, test after test, against the behaviour of the model it was built with.

A different model behaves differently, and none of these differences is a defect of either model:

- **Prompt adherence.** One model follows an instruction to the letter, another treats it as a suggestion. A rule written for the loose reader gets over-applied by the literal one.
- **Ambiguity.** Faced with a case the instructions don't settle, one model asks, one abstains, one picks the most plausible reading and moves on.
- **How instructions are read.** Absolute wording ("never", "always") and the exceptions written next to it get weighed differently, so the same sentence produces different case-by-case behaviour.
- **Prior knowledge.** What the model already believes about the world competes with what the harness hands it. A newer model [doesn't necessarily know which of its facts have expired](/en/blog/when-the-fact-stops-being-true), it just has different ones.
- **Tool use and reasoning.** How readily it calls a tool, how it reads the tool's description, how much it reasons before answering. In this service, the new model in its adopted configuration made about 12% more web searches per classification than the old one on the same cases. These differences move cost and latency, not only quality, and in stages the model doesn't bill itself: a slower model can be cut short by deadlines tuned for a faster one, and that looks like a quality loss.

The consequence is an asymmetry worth naming. If you drop the candidate into the incumbent's harness unchanged, what you measure is **how well the new model imitates the old one** inside a harness built for the old one. That test systematically favours whatever is already in production. It can reveal blockers. It cannot justify rejecting the candidate on quality. I call it a substitution test, and keep it apart from the real comparison, where each model runs with a harness adapted to it.

## A method for testing a swap

The procedure below is the one I wrote for an [industry classification service](/en/projects/compliance-classifier) — an agent that searches for a company, verifies it is the right one, and maps what it does to an industry code. Nothing in it is specific to that service, or to a model swap. The same procedure governs any change to the harness — a reworded prompt, a new tool, a different parser. A new model is simply the change that touches every part at once.

<figure class="csw-fig">
<svg viewBox="0 0 600 400" role="img" aria-label="The model-swap procedure as a pipeline: preconditions, a gateway probe with the exact call shapes, harness adaptation, then three measured stages and a release gate against the deployed version. Stages one and two feed back into harness adaptation, so adapting the harness and measuring it are a loop, not a step.">
  <defs>
    <marker id="csw-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
    <marker id="csw-arr-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#f59e0b"/></marker>
  </defs>
  <g font-family="system-ui,-apple-system,sans-serif">
    <rect x="20" y="20" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="105" y="44" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">Preconditions</text>
    <text x="105" y="64" text-anchor="middle" fill="#94a3b8" font-size="11.5">version pinned, priced</text>
    <text x="105" y="80" text-anchor="middle" fill="#94a3b8" font-size="11.5">no silent fallback</text>
    <rect x="215" y="20" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="300" y="44" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">Gateway probe</text>
    <text x="300" y="64" text-anchor="middle" fill="#94a3b8" font-size="11.5">exact call shapes</text>
    <text x="300" y="80" text-anchor="middle" fill="#94a3b8" font-size="11.5">every parameter honoured?</text>
    <rect x="410" y="20" width="170" height="78" rx="8" fill="#14302c" stroke="#2dd4bf"/>
    <text x="495" y="44" text-anchor="middle" fill="#5eead4" font-size="14" font-weight="600">Adapt the harness</text>
    <text x="495" y="64" text-anchor="middle" fill="#94a3b8" font-size="11.5">prompts, tools, parsing,</text>
    <text x="495" y="80" text-anchor="middle" fill="#94a3b8" font-size="11.5">reasoning, deadlines</text>
    <path d="M190,59 L211,59" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr)"/>
    <path d="M385,59 L406,59" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr)"/>
    <rect x="410" y="150" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="495" y="174" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">1 · Targeted cohort</text>
    <text x="495" y="194" text-anchor="middle" fill="#94a3b8" font-size="11.5">affected cases only</text>
    <text x="495" y="210" text-anchor="middle" fill="#94a3b8" font-size="11.5">per component, ≥ 4 rounds</text>
    <rect x="215" y="150" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="300" y="174" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">2 · Full benchmark</text>
    <text x="300" y="194" text-anchor="middle" fill="#94a3b8" font-size="11.5">paired, interleaved</text>
    <text x="300" y="210" text-anchor="middle" fill="#94a3b8" font-size="11.5">≥ 2 rounds, pre-registered</text>
    <rect x="20" y="150" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="105" y="174" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">3 · Attribution</text>
    <text x="105" y="194" text-anchor="middle" fill="#94a3b8" font-size="11.5">discordant cases only</text>
    <text x="105" y="210" text-anchor="middle" fill="#94a3b8" font-size="11.5">read in the traces</text>
    <path d="M495,98 L495,146" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr)"/>
    <path d="M410,189 L389,189" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr)"/>
    <path d="M215,189 L194,189" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr)"/>
    <path d="M330,150 C330,120 440,128 462,102" stroke="#f59e0b" stroke-width="1.6" fill="none" stroke-dasharray="5 4" marker-end="url(#csw-arr-a)"/>
    <path d="M555,150 C575,130 575,118 560,102" stroke="#f59e0b" stroke-width="1.6" fill="none" stroke-dasharray="5 4" marker-end="url(#csw-arr-a)"/>
    <rect x="352" y="112" width="74" height="16" fill="#1a1a24"/>
    <text x="389" y="124" text-anchor="middle" fill="#fbbf24" font-size="11">re-adapt</text>
    <rect x="20" y="290" width="560" height="84" rx="8" fill="#2a2216" stroke="#f59e0b"/>
    <text x="300" y="316" text-anchor="middle" fill="#fbbf24" font-size="14" font-weight="600">Release gate against the version already deployed</text>
    <text x="300" y="338" text-anchor="middle" fill="#94a3b8" font-size="11.5">same time window for both versions · changed cases re-run ≥ 2 rounds each</text>
    <text x="300" y="356" text-anchor="middle" fill="#94a3b8" font-size="11.5">a stored round from another day is not a control</text>
    <path d="M105,228 L105,286" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr)"/>
  </g>
</svg>
<figcaption>Adapting the harness and measuring it are a loop. What reaches the release gate is the candidate model plus its adapted harness, compared with what is actually deployed.</figcaption>
</figure>

The order of the stages is deliberate: it goes from specific to exhaustive. The first stage isolates twice. It runs only the cases a change is meant to affect — safety cases, hard cases, the target case of each safeguard — and it runs them on the component that changed: the search step alone, the verifier replayed on content already captured, the agent with its search results frozen. Many rounds, few cases, so a regression shows up while it is still cheap to find. Only a candidate that survives it gets the full benchmark. Attribution then goes back to the cases where the two arms disagreed, and only those. The expensive runs come last and are aimed by the cheap ones.

The rules that carry most of the weight:

- **Measure the service, not the model.** Components are tested in isolation, but the decision rests on what the system returns end to end — answer, evidence, confidence, cost, latency — never on a vendor claim or a playground prompt.
- **Pin it, and see it.** The model version is pinned so the provider can't change it under a measurement. Before the service is involved, a short probe through the gateway uses the exact call shapes the service sends. A gateway can drop a parameter it doesn't support and still answer 200, and a parameter honoured on one API surface can be ignored on another. Every response records which model actually served it: a silent fallback serves a different model under the candidate's name.
- **Paired, interleaved, repeated.** Every case runs every arm in the same session, with the order rotated. The system is not deterministic, so one round per case decides nothing, and two may not either: in this service, among cases whose first two rounds agreed, rounds three and four returned a different code **24% of the time**. Before reading any difference, measure how much the control disagrees with itself on the same cases. An effect smaller than that floor is not an effect.
- **Separate an outage from an answer.** A call that didn't arrive (timeout, gateway error) is excluded. A call that arrived with something unusable (unparseable, empty, out of range) counts against the candidate: it is part of what's being measured. The trace has to tell the two apart before the run starts.
- **Keep a register of mechanisms.** Many safeguards are instructions adopted because they changed the incumbent's behaviour in a measured way. A new model can read them differently, so a mechanism can stop working while the aggregate stays flat. Each one is listed with its target case and checked on the candidate.
- **Different is not better.** The decision rules are written before the first call: zero hard safety failures, no case moving from pass to fail beyond the control's own variation, no increase in confident-and-wrong answers, stability no worse, cost and latency within agreed limits. A candidate that fixes one case and breaks another is not an improvement.
- **Gate against what is deployed, in the same window.** Passing against the old model on the same build isn't enough to promote. The release is compared with the version running in the next environment, in the same time window, because [LLM judges](/en/blog/three-judges-three-rankings) and external data drift from one day to the next.

## How this differs from testing you already know

| | Traditional software | Traditional ML | Swapping the model in an LLM system |
|---|---|---|---|
| Who changes the component | You | You (you retrain) | The provider, on their schedule |
| Same input, same output? | Yes | Yes, once trained | No: sampling, search results, judges |
| What you tune | Code | Weights, features, hyperparameters | Prompts, tool descriptions, call shapes — in natural language |
| A test is | Pass or fail | An aggregate on a held-out set | Paired, repeated, per case, above a noise floor |
| What decides | The assertion | The metric | The metric, then a person or an agent reading every disagreement in the traces |

Self-hosted open-weight models sit closer to traditional ML on one axis: you decide when to change, nobody retires the model from under you, and the evaluation runs on your own GPUs. On the other axis they don't move at all. Unless you fine-tune, you still swap one set of weights for another and adapt prompts and tools to it, exactly as with a hosted provider.

## What one swap cost

Here is the bill for the swap in the opening, counting **only what the language model costs**. The service also pays for web search, but that spend has its own dynamics and stays out of this calculation.

The twelve days of testing around the swap were not all about the swap. About half of it would have happened anyway: the release gate of a version from before the change, fixes that came out of that gate, integration work, a round of fixes requested by a customer. That half stays out too. What counts is the paired comparison of the two models with the harness adaptation, the release gates of the first versions on the new model, and the fixes those gates produced. Some of those fixes repaired defects that predated the new model, but the comparison is what brought them back up, so they count toward it.

| | Value |
|---|---:|
| Model tokens spent on the swap, in the runs that were saved | 47 $ |
| … scaled up for the 27% of calls that were not saved (smoke tests, interrupted runs) | ≈ 65 $ |
| Model cost per classification, paired on the same build: model in production → candidate | 0.0098 → 0.0053 $ |
| **Saving per classification** | **≈ 0.0045 $** |
| Production volume | ≈ 500 / month |

On top of the tokens there is engineering time. The session that carried out the swap logged about **20 active hours of agent work**. Mine, inside it, came to about **four hours**. Valuing my four hours at 50 $/h and leaving aside what the agent's hours cost, the swap comes to roughly **250 to 265 dollars**.

This was the hardest adaptation I have had to make. More typically, one round of testing with two or three iterations of the harness gets there in one or two hours, with correspondingly fewer calls. Even that does not change the conclusion at this volume: before the next model arrives, the saving recovers about six dollars, less than a single hour of engineering.

| Cost of the swap | Classifications to break even | At 500 a month |
|---|---:|---:|
| Tokens, saved runs (47 $) | ≈ 10,500 | ≈ 21 months |
| Tokens, scaled (65 $) | ≈ 14,400 | ≈ 29 months |
| Tokens + my 4 hours (≈ 265 $) | ≈ 59,000 | ≈ 10 years |

The tokens alone already put a return two years away at this volume. Engineering time pushes it out to a decade. And the relevant horizon is not years: it is how long until the next model.

<figure class="csw-fig">
<svg viewBox="0 0 600 360" role="img" aria-label="Months needed to recover the cost of a model swap, against monthly volume, on log scales. At 500 classifications a month it takes between 21 and 29 months counting tokens only, and about 118 months counting four hours of engineering. Recovering it before the next release, 2.5 months away, needs between about 4,200 and 23,500 classifications a month.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <g stroke="rgba(255,255,255,0.08)" stroke-width="1">
      <line x1="70" y1="30" x2="570" y2="30"/><line x1="70" y1="95" x2="570" y2="95"/><line x1="70" y1="160" x2="570" y2="160"/><line x1="70" y1="225" x2="570" y2="225"/><line x1="70" y1="290" x2="570" y2="290"/>
      <line x1="70" y1="30" x2="70" y2="290"/><line x1="236.7" y1="30" x2="236.7" y2="290"/><line x1="403.3" y1="30" x2="403.3" y2="290"/><line x1="570" y1="30" x2="570" y2="290"/>
    </g>
    <g fill="#94a3b8" font-size="11" text-anchor="end">
      <text x="62" y="34">1,000</text><text x="62" y="99">100</text><text x="62" y="164">10</text><text x="62" y="229">1</text><text x="62" y="294">0.1</text>
    </g>
    <g fill="#94a3b8" font-size="11" text-anchor="middle">
      <text x="70" y="308">100</text><text x="236.7" y="308">1k</text><text x="403.3" y="308">10k</text><text x="570" y="308">100k</text>
    </g>
    <text x="320" y="334" text-anchor="middle" fill="#94a3b8" font-size="12">classifications per month</text>
    <text x="20" y="160" text-anchor="middle" fill="#94a3b8" font-size="12" transform="rotate(-90 20 160)">months to break even</text>
    <line x1="70" y1="199.1" x2="570" y2="199.1" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="6 4"/>
    <line x1="186.5" y1="30" x2="186.5" y2="290" stroke="#5eead4" stroke-width="1" stroke-dasharray="3 3"/>
    <rect x="191" y="270" width="66" height="16" fill="#1a1a24"/>
    <text x="194" y="282" fill="#5eead4" font-size="11.5">500 / month</text>
    <rect x="76" y="203" width="182" height="16" fill="#1a1a24"/>
    <text x="80" y="215" fill="#fbbf24" font-size="11.5">next model in that tier: 2.5 months</text>
    <line x1="70" y1="44.9" x2="570" y2="240.0" stroke="#e2e8f0" stroke-width="2"/>
    <line x1="70" y1="84.7" x2="570" y2="279.7" stroke="#2dd4bf" stroke-width="2"/>
    <line x1="70" y1="93.6" x2="570" y2="288.6" stroke="#64748b" stroke-width="2"/>
    <circle cx="186.5" cy="90.4" r="4" fill="#e2e8f0"/>
    <circle cx="186.5" cy="130.1" r="4" fill="#2dd4bf"/>
    <circle cx="186.5" cy="139.0" r="4" fill="#64748b"/>
    <circle cx="465.3" cy="199.1" r="3.5" fill="#f59e0b"/>
    <circle cx="363.5" cy="199.1" r="3.5" fill="#f59e0b"/>
    <circle cx="340.7" cy="199.1" r="3.5" fill="#f59e0b"/>
    <rect x="340" y="40" width="224" height="66" rx="6" fill="#1a1a24" stroke="rgba(255,255,255,0.1)"/>
    <line x1="352" y1="56" x2="372" y2="56" stroke="#e2e8f0" stroke-width="2"/><text x="378" y="60" fill="#e2e8f0" font-size="11.5">tokens + my 4 hours (265 $)</text>
    <line x1="352" y1="74" x2="372" y2="74" stroke="#2dd4bf" stroke-width="2"/><text x="378" y="78" fill="#e2e8f0" font-size="11.5">tokens, scaled (65 $)</text>
    <line x1="352" y1="92" x2="372" y2="92" stroke="#64748b" stroke-width="2"/><text x="378" y="96" fill="#e2e8f0" font-size="11.5">tokens, saved runs (47 $)</text>
  </g>
</svg>
<figcaption>Months to recover the swap with a saving of 0.0045 $ per classification. At 500 a month, between 21 and 29 months on tokens alone, about ten years with engineering time. To recover it before the next model arrives, the service would need roughly 4,200 to 23,500 classifications a month.</figcaption>
</figure>

## Who gets paid

The engineering hours stay with whoever pays the engineer. The tokens don't: they go to the model provider, and that changes how the swap looks from the other side.

At 500 classifications a month, this service was paying the provider about five dollars a month in production, and on the new model it pays under three. The comparison paid it between 47 and 65: **the equivalent of 10 to 13 months of production at the old price, or 18 to 25 at the new one**. A release that a team has to test can bring the provider more from the testing than from a year or two of real use.

The proportion flips with volume. The evaluation costs roughly the same however many classifications run in production — what moves it is the number of rounds, not traffic. Production revenue grows with traffic. Over the 75 days a model in that tier lasted, production on the new model would match the cost of the comparison at **around 3,500 to 4,900 classifications a month**. Below that line, each swap a team tests earns the provider more in evaluation than the new model earns in production before the next one arrives.

I am not claiming providers release models to collect evaluation fees. Competition explains the releases without any help. But the side effect is real and it compounds with cadence. Since GPT-5 in August 2025, OpenAI has shipped a new generation [roughly every two months](https://en.wikipedia.org/wiki/GPT-6). At Anthropic, the gap between consecutive [Sonnet releases](https://en.wikipedia.org/wiki/Claude_(language_model)) went from almost five months to about three. What matters for a given system is the cadence of the tier it uses, not of the catalogue — here, 75 days.

## When a swap is worth it

On cost alone, a swap pays when

**saving per run × monthly volume × months you'll keep the new model > cost of the swap**

Four things follow from it.

**You don't have to take every release.** The horizon is how long you will stay on the new model, not how long until the next launch. A team at low volume that skips generations pays the cost of a swap once per forced migration — when the old model is retired — instead of once per release.

**At low volume, cost cannot justify a swap; only quality can.** The rule then becomes *errors avoided per run × cost of an error × volume × months > cost of the swap*. In a compliance classifier, one confident wrong answer can cost more than all the tokens involved. But that cost per error has to be stated, not assumed, or the formula justifies anything.

**The thinner the harness, the cheaper the swap.** Every instruction written to steer one model's behaviour is something the next model may read differently, and something to check again. A harness that holds only what the task needs has less to re-adapt. How thin it can be depends on the task: the more specific and regulated the work, the more has to be spelled out and the less room there is. But stronger models tend to need less explicit guidance, so a new generation is also a chance to remove instructions rather than add them.

**The cost of a swap is not fixed across swaps.** Much of what this method needs is infrastructure built once: selecting the model per request, every response recording what served it, case banks with reviewed references, the register of mechanisms. The first swap pays for it. Later swaps reuse it. Whether that brings the next swap below the line is something the next swap will measure.

All of this is one service, one swap and one provider, with engineering time reconstructed from session logs and nothing counted that happened outside them. It is enough to show the shape of the problem, not to set a number for anyone else's. The formula is the part that travels: put in your own volume, your own saving and your own cost of testing, and see which side of the line you are on.
