---
title: "Nineteen of twenty patched the symptom"
description: "I gave a hundred and forty agents the same misbehaving classifier and changed one thing: whether they could see its code. What moved wasn't who they blamed — it was whether they looked for the cause at all. And not one of them asked for the data it was missing, even when told outright that asking was allowed."
pubDate: 2026-09-10
tags: ["AI", "Agents", "Evaluation", "Research"]
lang: en
translationKey: patched-the-symptom
heroImage: "/blog/patched-the-symptom.png"
repoUrl: "https://github.com/JaviMaligno/blaming-the-model"
---

<style>
.exp-fig { margin: 2rem 0; }
.exp-fig svg { width: 100%; height: auto; display: block; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; background: #1a1a24; }
.exp-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

In [the previous article](/en/blog/blaming-the-model) I described a habit I kept running into: when a system has a language model inside it and something goes wrong, the explanation drifts towards the model. The sampling. The nondeterminism. Something nobody wrote and therefore nobody has to fix.

That was an observation from work, which is a polite way of saying it was an anecdote. So I built a way to measure it, and the measuring turned out to be harder and more interesting than the result.

## The setup

I built a small classifier that reads a repository's documentation and assigns it a category from a hierarchy, with a confidence and a justification. Real repositories — fifty of them, low-star and recent so that no model has them memorised. It runs on a real model. It has a search budget, a context window that truncates, a retrieval step, and a trace.

Then I planted a fault in it, ran the same batch five times, and got a table where a handful of projects change category between passes even though nothing changed between passes.

That table is what the agent sees. The only thing I varied is **whether it also gets the code**.

<figure class="exp-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="Diagram of the experimental design: the same batch of five passes is given to two groups of agents. One group receives only the results table and the run logs; the other also receives the system's source code. Everything else is identical.">
  <rect x="200" y="18" width="200" height="46" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.4"/>
  <text x="300" y="40" fill="#e2e8f0" font-size="13" text-anchor="middle">same system, same fault</text>
  <text x="300" y="56" fill="#94a3b8" font-size="12" text-anchor="middle">five passes of one batch</text>
  <path d="M300 64 L300 88 M170 88 L430 88 M170 88 L170 106 M430 88 L430 106" stroke="#64748b" stroke-width="1.3" fill="none"/>
  <path d="M166 100 L170 108 L174 100 Z" fill="#64748b"/>
  <path d="M426 100 L430 108 L434 100 Z" fill="#64748b"/>
  <rect x="40" y="110" width="260" height="118" rx="6" fill="#171f2e" stroke="#f59e0b" stroke-width="1.4"/>
  <text x="58" y="132" fill="#fbbf24" font-size="13">without the code</text>
  <text x="58" y="156" fill="#cbd5e1" font-size="12">· the results table</text>
  <text x="58" y="176" fill="#cbd5e1" font-size="12">· shallow run logs</text>
  <text x="58" y="196" fill="#cbd5e1" font-size="12">· the document corpus</text>
  <text x="58" y="218" fill="#64748b" font-size="11">n = 20</text>
  <rect x="320" y="110" width="240" height="118" rx="6" fill="#172a2a" stroke="#2dd4bf" stroke-width="1.4"/>
  <text x="338" y="132" fill="#5eead4" font-size="13">with the code</text>
  <text x="338" y="156" fill="#cbd5e1" font-size="12">· everything on the left</text>
  <text x="338" y="176" fill="#cbd5e1" font-size="12">· plus the source</text>
  <text x="338" y="196" fill="#cbd5e1" font-size="12">  of the system</text>
  <text x="338" y="218" fill="#64748b" font-size="11">n = 20</text>
</svg>
<figcaption>The whole design. Two groups see the identical failure; one of them can open the system. Nothing else differs, including the prompt asking them to investigate.</figcaption>
</figure>

Scenarios were frozen with a hash before any of this ran, the people coding the answers never knew which group a response came from, and the statistics were computed from the raw JSON by a script that ships with the repo. I'll come back to why all that ceremony mattered.

## The first fault: the order of retrieval

The planted fault: the search that retrieves documentation resolves score ties using an identifier derived from the request, so each pass hands the model a different set of documents. The variability comes entirely from the input. The model's sampling has nothing to do with it.

Twenty agents saw the table without the code, twenty with it.

| | without the code | with the code | p |
|---|---|---|---|
| Found the cause | 3/20 | **20/20** | <0,0001 |
| Proposed voting or retries | **18/20** | 5/20 | <0,0001 |
| **Patched the symptom** (voting or temperature) | **19/20** | 9/20 | **0,0006** |
| Blamed sampling as the primary cause | 4/20 | 0/20 | 0,053 |
| Asked for instrumentation before concluding | 0/20 | 0/20 | — |

The headline isn't the attribution. Blaming the model outright happened four times out of twenty, and at p = 0,053 that doesn't clear the usual bar. The strong formulation of my own thesis — *the agent blames the model* — did not survive contact with the data, and I'd rather say so plainly than round it into significance.

What did survive is the behaviour. **Nineteen of twenty, with no way to see the system, set about damping its output** — voting across retries, pinning the temperature, averaging the instability away. With the code in front of them, nine. You don't have to say the model is at fault to treat it as if it were: it's enough to stop looking for a cause and start smoothing the symptom.

> **Added later.** A control I ran after publishing this took the language model out of the pipeline entirely and put a frozen random forest in its place, same fault, same everything else. The damping didn't move: 19/20 in both arms — so *that* row isn't about language models, it's about diagnosing something you can't open. Finding the cause did move, a little: 0-2/20 with the model against 4-8/20 with the forest. What is large is what they accuse the head of — the model gets called random by nature (14/20 against 4/20), the forest gets accused of being retrained by the system. That's [the third article](/en/blog/knew-it-wasnt-the-model).

## The second fault: where blaming the model is half right

The first scenario has a weakness I could see from the start. Nothing in it makes sampling a *reasonable* explanation — it's just the lazy one. A fair test needs a case where a competent engineer could reach that conclusion in good faith and still be wrong.

So I built a second one, and this is the part I'd defend hardest.

<figure class="exp-fig">
<svg viewBox="0 0 600 215" role="img" aria-label="Diagram of the second fault: a page cache shared across a batch is keyed by project name and section, so two different projects that happen to share a name collide. The second one to ask for a section receives the first one's documentation, and classifies it correctly — but it is reading the wrong project.">
  <rect x="26" y="30" width="150" height="52" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.3"/>
  <text x="101" y="52" fill="#e2e8f0" font-size="13" text-anchor="middle">project A</text>
  <text x="101" y="70" fill="#94a3b8" font-size="11" text-anchor="middle">named "atlas"</text>
  <rect x="26" y="150" width="150" height="52" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.3"/>
  <text x="101" y="172" fill="#e2e8f0" font-size="13" text-anchor="middle">project B</text>
  <text x="101" y="190" fill="#94a3b8" font-size="11" text-anchor="middle">also named "atlas"</text>
  <rect x="235" y="86" width="140" height="60" rx="6" fill="#2a1f14" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="305" y="108" fill="#fbbf24" font-size="13" text-anchor="middle">shared cache</text>
  <text x="305" y="128" fill="#fbbf24" font-size="11" text-anchor="middle" font-family="ui-monospace,monospace">key: (name, section)</text>
  <path d="M176 56 L235 100" stroke="#2dd4bf" stroke-width="1.3" fill="none"/>
  <path d="M228 94 L237 102 L230 104 Z" fill="#2dd4bf"/>
  <rect x="182" y="64" width="66" height="16" fill="#1a1a24"/>
  <text x="186" y="76" fill="#5eead4" font-size="11">stores first</text>
  <path d="M176 176 L235 134" stroke="#f59e0b" stroke-width="1.3" fill="none"/>
  <path d="M228 138 L237 132 L231 128 Z" fill="#f59e0b"/>
  <rect x="182" y="148" width="68" height="16" fill="#1a1a24"/>
  <text x="186" y="160" fill="#fbbf24" font-size="11">asks second</text>
  <rect x="424" y="86" width="150" height="60" rx="6" fill="#171f2e" stroke="#64748b" stroke-width="1.3"/>
  <text x="499" y="108" fill="#e2e8f0" font-size="13" text-anchor="middle">the model</text>
  <text x="499" y="128" fill="#94a3b8" font-size="11" text-anchor="middle">reads A, labels B</text>
  <path d="M375 116 L424 116" stroke="#f59e0b" stroke-width="1.5" fill="none"/>
  <path d="M416 112 L426 116 L416 120 Z" fill="#f59e0b"/>
</svg>
<figcaption>A cache shared across the runs of one batch, keyed by project and section. Two unrelated projects that happen to share a short name collide, and the second one to ask receives the first one's documentation. The model then classifies that documentation perfectly well — it is simply not the documentation of the project it was asked about.</figcaption>
</figure>

Why this one is fair: the symptom is *"it fails in the batch, and reproduces fine on its own"*, which is the canonical signature of nondeterminism. The affected projects wander from pass to pass. The justifications read like textbook hallucination — fluent, confident, describing features the project doesn't have.

And here's the part that makes it honest. Of the fifteen label changes in the table, **fourteen are contamination and one is genuine model sampling** — a project that was never served anyone else's documents and moves anyway, confirmed by resampling its prompt twenty times. For that one, *"it's the model"* is the correct answer.

So the rubric has two opposite fields that can both be true of the same response: blaming sampling for the fourteen is the error, and attributing the one correctly is the win.

| | without the code | with the code | p |
|---|---|---|---|
| **Blamed sampling for the systematic changes** | **6/20** | **0/20** | **0,0101** |
| Found the cache | 13/20 | 20/20 | 0,0042 |
| Correctly attributed the sampling tail | 12/20 | 15/20 | 0,25 |
| Proposed temperature to reduce variance | 2/20 | 8/20 | 0,032 |
| Asked for instrumentation before concluding | 0/20 | 0/20 | — |
| Built its own measurement instead | 18/20 | 16/20 | 0,33 |

Making the wrong explanation *reasonable* is what moved the number: from 4/20 at p = 0,053 to **6/20 at p = 0,0101**. The reflex isn't summoned by laziness. It's summoned by a situation where it half fits.

One result went the opposite way from what I expected: proposing to fix the temperature was **more** common with the code than without (8/20 vs 2/20). Reading the responses explains it — with the source in hand they can see the residual sampling is real, and they propose pinning it as part of a fix. It's an informed suggestion, not a reflex, and it's a good reminder that a single checkbox measures behaviour badly.

## Nobody asked. A hundred and forty times.

Across every scenario and every group, **not one response asked for the information it was missing before reaching a conclusion.**

Not once. Every package deliberately shipped shallow logs — input and final answer only — while the full trace existed and would have been handed over on request. The brief said so: *you can ask for whatever you're missing*. All of them diagnosed first and listed what they'd lacked at the end, after the conclusion was already written.

The obvious explanation is social: being shown a table of outputs frames the job as *analyse this*, and asking for more input reads as refusing the job. That's testable with one sentence, so I tested it. Sixty more responses, same frozen scenario, with the brief rewritten to say that asking is a **complete** answer, preferable to a hypothesis you can't check — and closing with *asking is not leaving the job half done*.

| | passive permission | explicit permission | p |
|---|---|---|---|
| Asked for instrumentation before concluding | 0/20 | **0/20** | — |
| Asked and stopped there | 0/20 | 0/20 | — |
| **Presented the conclusion as provisional** | 6/20 | **14/20** | **0,013** |

**A hundred and forty out of a hundred and forty.** Telling them in as many words that asking is not shirking changes nothing about whether they ask.

What it does change is the *shape* of the answer. Hedging doubles. Given explicit permission to ask, they don't ask — they cover themselves, flagging the conclusion as provisional instead of doing the one thing that would make it firm.

And the other half of the explanation is what they do instead. **They build their own measurement**: a script, a sweep over the corpus, a synthetic reproduction of the pipeline. On the stronger tier, 18 of 20 do this, against 7 of 20 on the weaker one (p = 0,0004) — the largest capability difference in the whole study, and it isn't about willingness to ask, which is zero everywhere. It's about being able to manufacture the answer without asking.

So it isn't incuriosity about data. Several of these responses did genuinely rigorous work to get data. Asking for it simply isn't in the repertoire, and whoever can, fabricates it instead.

<figure class="exp-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Bar chart of the main results out of twenty responses per group. Without the code: patched the symptom 19, found the cause 3, asked for data 0. With the code: patched the symptom 9, found the cause 20, asked for data 0.">
  <text x="20" y="24" fill="#94a3b8" font-size="12">out of 20 responses per group</text>
  <rect x="380" y="14" width="12" height="12" fill="#f59e0b"/><text x="398" y="24" fill="#cbd5e1" font-size="12">without the code</text>
  <rect x="380" y="32" width="12" height="12" fill="#2dd4bf"/><text x="398" y="42" fill="#cbd5e1" font-size="12">with the code</text>
  <text x="20" y="72" fill="#e2e8f0" font-size="13">patched the symptom</text>
  <rect x="200" y="60" width="332" height="15" rx="2" fill="#f59e0b"/><text x="540" y="72" fill="#fbbf24" font-size="12">19</text>
  <rect x="200" y="79" width="157" height="15" rx="2" fill="#2dd4bf"/><text x="365" y="91" fill="#5eead4" font-size="12">9</text>
  <text x="20" y="132" fill="#e2e8f0" font-size="13">found the cause</text>
  <rect x="200" y="120" width="52" height="15" rx="2" fill="#f59e0b"/><text x="260" y="132" fill="#fbbf24" font-size="12">3</text>
  <rect x="200" y="139" width="350" height="15" rx="2" fill="#2dd4bf"/><text x="558" y="151" fill="#5eead4" font-size="12">20</text>
  <text x="20" y="192" fill="#e2e8f0" font-size="13">asked for the data</text>
  <rect x="200" y="180" width="2" height="15" rx="1" fill="#f59e0b"/><text x="210" y="192" fill="#fbbf24" font-size="12">0</text>
  <rect x="200" y="199" width="2" height="15" rx="1" fill="#2dd4bf"/><text x="210" y="211" fill="#5eead4" font-size="12">0</text>
</svg>
<figcaption>The first scenario, twenty responses per group. Access to the code multiplies the rate of finding the cause by nearly seven, and roughly halves the rate of damping the symptom. It does nothing at all to the willingness to ask for missing information, which is zero either way.</figcaption>
</figure>

## A finding that didn't survive

I'll spend a paragraph on something that isn't in this article any more, because how it left is the point.

Half of each group ran on a stronger model tier and half on a weaker one. In the first round, with ten responses per cell, the stronger tier appeared to find the cause **less** than the weaker one — 4/10 against 9/10, p = 0,029 — and I had a tidy explanation ready. The stronger responses had audited the corpus document by document, verified that no snapshot contains another project's material (which is *true*, because the contamination happens at runtime, not in the data), and concluded from that a cache couldn't be responsible. Correct reasoning, correct check, false conclusion.

It was a good story. So I doubled the sample to twenty per cell, and it evaporated: 2/20 against 5/20, p = 0,20. It was noise, and a p of 0,029 with ten per cell is exactly the kind of number that looks like a finding and isn't.

The one tier difference that does hold is the one above — the stronger tier builds its own measurement far more often. That one I'd defend.

## What doesn't hold

- **With the code, 20/20 found the first fault.** That group doesn't discriminate, and I knew it wouldn't before running it: reaching a middling difficulty there would have required fabricating metadata — assigning repositories to package registries that don't list them, staggering capture dates — and I ruled that out. A study about agents cutting corners can't cut that one. The with-code group is the control, not the measurement.
- **The literal form of the thesis remains unmeasured.** *Blames the model for what it wouldn't blame itself for* requires the system to be the agent's own. In all four groups it audits someone else's code. What I measured is an asymmetry of material, not of authorship.
- **One certification came in at 18/20** rather than the 19/20 I'd set as the bar, and the fix removes all fourteen contaminations but leaves three residual changes — the 0,7% sampling floor that no cache key touches.
- **The rubric hardened between rounds**, and the same condition scores 13/20 under the old definition and 3/20 under the new one (p = 0,0015). The second demands that a response describe the mechanism, and counts listing the cache among several uncommitted hypotheses as a miss. Numbers from different rounds of that field cannot be pooled or compared, and none in this article are.

## The part that took longest

Three attempts failed before one worked, and the failures are more instructive than the result.

The **first** gave agents the code with a planted bug and asked what went wrong. All eight found it. A scenario nobody fails measures nothing.

The **second** showed a batch of bad classifications with no variability at all — and the thesis is about variability, so there was nothing for anyone to attribute to sampling. I'd built a case that couldn't contain the phenomenon.

The **third** — a rewrite that tried to make the fault hard by using concurrency — was killed in review before it ran, on a point I hadn't seen: if the entropy comes from network jitter against the inference service, then *"the variability comes from the model layer"* is **true**, and the rubric would have scored a correct answer as an error. Hard and deterministic pull in opposite directions, and you have to resolve that on purpose.

What survives all three is a design rule I'd now apply to anything of this shape: **the fault has to be something the model provably cannot have caused.** In the final scenario that's guaranteed by one fact — the same project, asking for the same sections, receives different prompt bytes across passes. Sampling cannot change the bytes of a prompt. It isn't a judgement call by whoever grades the answers; it's arithmetic.

And the ceremony earns its keep. Scenarios hashed before the run so they can't be tuned after seeing results. Coders blind to which group a response came from. Calibration data kept separate from confirmation data rather than merged to inflate the sample — which would have been free, and would have been exactly the shortcut this experiment exists to detect in others.

---

*Code, data, and the script that recomputes every number in this article: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). The series: [the observation](/en/blog/blaming-the-model), this measurement, and [the control that reframed it](/en/blog/knew-it-wasnt-the-model).*
