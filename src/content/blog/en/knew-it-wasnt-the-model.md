---
title: "They knew it wasn't the model. They patched it anyway."
description: "I swapped the language model for a random forest and ran the same broken pipeline past forty agents. Nineteen of twenty patch the symptom on each side, with the model and without it. What separates the two arms isn't that they investigate less: it's what they accuse the head of. The model gets called random by nature; the forest doesn't."
pubDate: 2026-09-11
tags: ["AI", "Agents", "Evaluation", "Research"]
lang: en
translationKey: knew-it-wasnt-the-model
heroImage: "/blog/knew-it-wasnt-the-model.png"
repoUrl: "https://github.com/JaviMaligno/blaming-the-model"
---

<style>
.gua-fig { margin: 2rem 0; }
.gua-fig svg { width: 100%; height: auto; display: block; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; background: #1a1a24; }
.gua-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

Two articles ago I described a habit: when a system has a language model inside it and the output wobbles, the explanation drifts to the model. Then [I measured it](/en/blog/patched-the-symptom), and the interesting result wasn't the blame — it was the behaviour. Without access to the code, nineteen of twenty agents set about damping the output instead of looking for the cause.

This piece was supposed to answer *why*. I had two hypotheses and they made different predictions, which is the good kind of problem to have. Instead I ran the control first, and the control made both of them pointless.

## The control

The design is almost embarrassingly simple. Take the same classifier, the same planted fault, the same corpus, the same five passes, the same trace format. Change one thing: **the head that does the classifying**.

In one arm it's a language model. In the other it's a random forest — trained by distilling the model's own labels, frozen into a pickle, and given the identical interface so that nothing else in the system differs by a single byte.

<figure class="gua-fig">
<svg viewBox="0 0 600 215" role="img" aria-label="Diagram of the control: the same pipeline — corpus, retrieval with the planted fault, and context assembly — feeds two different classifying heads, a language model and a frozen random forest. Everything before the head is identical in both arms.">
  <rect x="24" y="96" width="104" height="46" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.3"/>
  <text x="76" y="118" fill="#e2e8f0" font-size="12" text-anchor="middle">corpus</text>
  <text x="76" y="134" fill="#94a3b8" font-size="11" text-anchor="middle">50 projects</text>
  <rect x="160" y="96" width="120" height="46" rx="6" fill="#2a1f14" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="220" y="114" fill="#fbbf24" font-size="12" text-anchor="middle">retrieval</text>
  <text x="220" y="132" fill="#fbbf24" font-size="11" text-anchor="middle">the planted fault</text>
  <rect x="312" y="96" width="106" height="46" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.3"/>
  <text x="365" y="118" fill="#e2e8f0" font-size="12" text-anchor="middle">context</text>
  <text x="365" y="134" fill="#94a3b8" font-size="11" text-anchor="middle">identical</text>
  <path d="M128 119 L158 119 M280 119 L310 119" stroke="#64748b" stroke-width="1.4" fill="none"/>
  <path d="M152 115 L160 119 L152 123 Z" fill="#64748b"/>
  <path d="M304 115 L312 119 L304 123 Z" fill="#64748b"/>
  <path d="M418 119 L444 119 M444 119 L444 58 M444 119 L444 180 M444 58 L470 58 M444 180 L470 180" stroke="#64748b" stroke-width="1.4" fill="none"/>
  <path d="M464 54 L472 58 L464 62 Z" fill="#64748b"/>
  <path d="M464 176 L472 180 L464 184 Z" fill="#64748b"/>
  <rect x="474" y="36" width="104" height="44" rx="6" fill="#172a2a" stroke="#2dd4bf" stroke-width="1.4"/>
  <text x="526" y="56" fill="#5eead4" font-size="12" text-anchor="middle">language</text>
  <text x="526" y="72" fill="#5eead4" font-size="12" text-anchor="middle">model</text>
  <rect x="474" y="158" width="104" height="44" rx="6" fill="#171f2e" stroke="#f59e0b" stroke-width="1.4"/>
  <text x="526" y="178" fill="#fbbf24" font-size="12" text-anchor="middle">random</text>
  <text x="526" y="194" fill="#fbbf24" font-size="12" text-anchor="middle">forest</text>
</svg>
<figcaption>The whole control. The fault sits in retrieval, upstream of the head, so it is the same fault in both arms — and the head, whichever it is, classifies correctly whatever it is handed.</figcaption>
</figure>

Both briefs carry the same measured certification, and it is the piece that makes the comparison fair: *"re-running the classification over the same context reproduced the output in 260 of 260 cases"* — the real number, identical in both arms. Without it, an agent facing the forest could reason, entirely correctly, that a trained forest is deterministic and therefore the cause must be upstream, and would patch less for a good reason rather than a revealing one.

Forty agents saw the table without the code, twenty per arm. And then another forty, to find out whether what came back was the effect or the sample.

## What happened

| | language model | random forest | p |
|---|---|---|---|
| **Patches the symptom** | **19/20** | **19/20** | 0.76 |
| **Accuses it of randomness of its own** | **14/20** | **4/20** | **0.0018** |
| Proposes taking the randomness out | 17/20 | 11/20 | **0.041** |
| Blames the head | 13/20 | 6/20 | **0.028** |
| Uses the determinism argument | 9/20 | 16/20 | **0.024** |
| Places the cause upstream | 16/20 | 17/20 | 0.50 |
| Finds the real cause | 2/20 | 8/20 | **0.032** |
| Asks for the data it lacks | 0/20 | 0/20 | — |

Thirty-eight of forty patched the symptom. Nineteen in each arm, the same exact figure on both sides. Wilson interval [0.84, 0.99].

That's the row that breaks the frame I brought in. Take the language model out of the loop, put a frozen forest in its place — a pure function, and the brief says so — and the patching doesn't move by a single unit. Whatever drives an engineer to smooth an output rather than trace it, **a language model is not a prerequisite. A closed component is.**

And then, having exonerated the box, they patch it anyway.

## What it gets accused of

The second row is the one that does separate the arms, and it's the one that had to be measured properly: not *how much* they blame the head, but **what they blame it for**.

There are two ways to accuse a component of an output that wobbles. One is that it's random by nature: it samples, it has noise, it rolls the dice. The other is that it's deterministic and the system does something to it: retrains it, parallelises it, changes its configuration. Both are formulable against both heads — a forest can vote with randomness, an inference server can batch requests — and the criterion was fixed in writing, with examples of both accusations for both heads, before a single response was read.

**Fourteen of twenty against four of twenty.** Two independent coders, agreement 0.95, and the two disagreements settled by a third who didn't know how either had voted.

The vocabulary is no longer a measure, it's simply what's on the page. The model arm gives you *"it re-samples every night"*, *"temperature > 0 with no seed"*, *"sampling noise on every call"*, *"the nightly re-roll"*. The four in the forest arm who also accuse their head say nothing of the kind: they say it **retrains without `random_state`**, that `predict_proba` runs over the whole batch, that floating point moves under parallelism.

The forest gets accused of what the system does to it. The model, of what it is.

<figure class="gua-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Bar chart out of twenty responses per arm. Patching the symptom is nineteen with the model and nineteen with the forest. Accusing the head of randomness of its own is fourteen with the model and four with the forest. Proposing to take the randomness out is seventeen and eleven. Using the determinism argument to exonerate it is nine and sixteen.">
  <rect x="380" y="12" width="12" height="12" fill="#2dd4bf"/><text x="398" y="22" fill="#cbd5e1" font-size="12">language model</text>
  <rect x="380" y="30" width="12" height="12" fill="#f59e0b"/><text x="398" y="40" fill="#cbd5e1" font-size="12">random forest</text>
  <text x="20" y="22" fill="#94a3b8" font-size="12">out of 20 responses per arm</text>
  <text x="20" y="76" fill="#e2e8f0" font-size="13">patches the symptom</text>
  <rect x="230" y="64" width="294" height="14" rx="2" fill="#2dd4bf"/><text x="532" y="76" fill="#5eead4" font-size="12">19</text>
  <rect x="230" y="82" width="294" height="14" rx="2" fill="#f59e0b"/><text x="532" y="94" fill="#fbbf24" font-size="12">19</text>
  <text x="20" y="124" fill="#5eead4" font-size="13">calls it random by nature</text>
  <rect x="230" y="112" width="217" height="14" rx="2" fill="#2dd4bf"/><text x="455" y="124" fill="#5eead4" font-size="12">14</text>
  <rect x="230" y="130" width="62" height="14" rx="2" fill="#f59e0b"/><text x="300" y="142" fill="#fbbf24" font-size="12">4</text>
  <text x="20" y="172" fill="#e2e8f0" font-size="13">wants the randomness out</text>
  <rect x="230" y="160" width="263" height="14" rx="2" fill="#2dd4bf"/><text x="501" y="172" fill="#5eead4" font-size="12">17</text>
  <rect x="230" y="178" width="170" height="14" rx="2" fill="#f59e0b"/><text x="408" y="190" fill="#fbbf24" font-size="12">11</text>
  <text x="20" y="220" fill="#e2e8f0" font-size="13">&#8220;it&#8217;s deterministic&#8221;</text>
  <rect x="230" y="208" width="139" height="14" rx="2" fill="#2dd4bf"/><text x="377" y="220" fill="#5eead4" font-size="12">9</text>
  <rect x="230" y="226" width="248" height="14" rx="2" fill="#f59e0b"/><text x="486" y="238" fill="#fbbf24" font-size="12">16</text>
</svg>
<figcaption>The first row is the same bar twice: patching doesn't care what's in the box. The second is the one that separates the arms, and it drags the other two along — the head believed to be random gets its randomness taken away, and the head known to be deterministic gets exonerated with exactly that.</figcaption>
</figure>

The remedies follow the diagnosis: proposing to take the randomness out of the head, seventeen of twenty against eleven. `temperature=0` and `seed` on one side; `random_state` and `n_jobs=1` on the other. Worth noting that the first is a dial most current reasoning models no longer expose: it proposes switching off something that isn't on, on a component that in this setup reads from disk.

And six responses do both at once: they accuse the model of sampling **and** cite the certification that contradicts it, in the same document.

## The dissociation

Of the twenty-five responses that exonerated the head — across both arms, on the same argument and the same certification — **twenty-three proposed a patch anyway.**

One writes: *"a random forest is a pure function: same feature vector, same vote. The 260/260 confirms it. The classifier is ruled out."* Its fourth recommendation is to publish by margin instead of top-1, with a threshold on the confidence gap and human review below it — *"this cuts the symptom the user sees, whatever the root cause"*.

That last clause is the whole article. Cutting the symptom the user sees, whatever the root cause, is a perfectly sensible operational instinct. It is also what you do instead of finding the cause, and for *that* the thing in the box doesn't need to be a language model — it needs to be closed.

## Measured twice

Forty responses are forty responses. Before these forty there are another forty, over the same two packages without a byte of change, and they're what tells effect from sample.

<figure class="gua-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="Dot plot of the gap between arms, model minus forest, out of twenty responses, measured in two independent samples. Patching the symptom is zero both times. Blaming the head goes from plus six to plus seven. The determinism argument stays at minus seven both times. Finding the cause goes from minus four to minus six. Placing the cause upstream goes from minus six to minus one, close to zero.">
  <line x1="300" y1="52" x2="300" y2="222" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="300" y="44" fill="#94a3b8" font-size="11" text-anchor="middle">no difference</text>
  <circle cx="380" cy="20" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><text x="390" y="24" fill="#cbd5e1" font-size="11">first sample</text>
  <circle cx="500" cy="20" r="4.5" fill="#2dd4bf"/><text x="510" y="24" fill="#cbd5e1" font-size="11">second</text>
  <text x="20" y="74" fill="#e2e8f0" font-size="12">patches the symptom</text>
  <circle cx="300" cy="70" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><circle cx="300" cy="70" r="4.5" fill="#2dd4bf"/>
  <text x="20" y="112" fill="#e2e8f0" font-size="12">blames the head</text>
  <line x1="420" y1="108" x2="440" y2="108" stroke="#475569" stroke-width="1.4"/>
  <circle cx="420" cy="108" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><circle cx="440" cy="108" r="4.5" fill="#2dd4bf"/>
  <text x="20" y="150" fill="#e2e8f0" font-size="12">&#8220;it&#8217;s deterministic&#8221;</text>
  <circle cx="160" cy="146" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><circle cx="160" cy="146" r="4.5" fill="#2dd4bf"/>
  <text x="20" y="188" fill="#e2e8f0" font-size="12">finds the cause</text>
  <line x1="180" y1="184" x2="220" y2="184" stroke="#475569" stroke-width="1.4"/>
  <circle cx="220" cy="184" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><circle cx="180" cy="184" r="4.5" fill="#2dd4bf"/>
  <text x="20" y="226" fill="#f87171" font-size="12">looks upstream</text>
  <line x1="180" y1="222" x2="280" y2="222" stroke="#f87171" stroke-width="1.4"/>
  <circle cx="180" cy="222" r="4.5" fill="none" stroke="#f87171" stroke-width="1.6"/><circle cx="280" cy="222" r="4.5" fill="#f87171"/>
  <text x="160" y="250" fill="#94a3b8" font-size="11" text-anchor="middle">&#8592; more with the forest</text>
  <text x="450" y="250" fill="#94a3b8" font-size="11" text-anchor="middle">more with the model &#8594;</text>
</svg>
<figcaption>Gap between the two arms across two independent samples of twenty per arm. Where only one dot shows, both landed on the same number and overlap. The red row is the only one that really moves: looking upstream came out six apart the first time and one apart the second, so nothing can be claimed from that row.</figcaption>
</figure>

Patching comes out 19 and 19 both times. The determinism argument, nine against sixteen both times, to the digit. Blaming the head, twelve against six and thirteen against six. Finding the cause, zero against four and two against eight.

**And one doesn't replicate: placing the cause upstream.** Ten against sixteen in the first sample, sixteen against seventeen in the second. With a language model in front of them, agents look upstream as often as with a forest; the first figure was the sample. I mention it because it's exactly the kind of row you build a beautiful thesis on if you only measure it once.

## What the model does and doesn't change

The honest reading splits the thing I'd been calling one behaviour into two, and only one of them is generic.

**Patching is generic.** Nineteen of twenty on each side, in both samples, head exonerated or not.

**Investigating barely moves.** They look upstream equally. What changes is that they get less far: two of twenty against eight find the cause, and the same two against eight name the real mechanism. A small, consistent difference — not the one I expected.

**What does change, and it's the only large thing, is the nature of the suspicion.** With the same certification in front of them and the same argument available to clear it, one head gets accused of being random and the other doesn't.

That is the LLM-specific claim, and it turns out to be the oldest and simplest of the ones I brought in: it isn't that people investigate less, it's that **the model gets charged with a class of fault that the thing standing in its place does not**.

## The question that lost half its object

I came into this piece with two hypotheses about why the reflex exists. One said it was a **fossil of the training corpus** — a habit from an era when `temperature` really was the main dial and treating output variance as a property of the model really was correct. The other said it was **the model's personality**, some being more inclined than others to look outward before looking at their own work.

For the patching, both are moot: there's no model-specific behaviour there to explain, because it shows up unchanged with no model in the loop.

For the accusation they're both still live, and the first now has a hint in its favour it didn't have before: what shows up in the model arm isn't reasoning about this system, it's a vocabulary — temperature, seed, roll, sampling — applied to a component that here reads from disk. That is what a habit looks like. But still live isn't separated: a habit learned from a corpus that steers tokens without passing through any consultable belief is indistinguishable from a disposition, for any experiment that only observes behaviour. Three independent reviewers of the design converged on that before a single response was collected.

## What doesn't hold

- **Looking upstream doesn't replicate**, so I claim nothing about where the search stops. It's the row I'd most have liked to keep.
- **The difficulty band broke in the second sample.** The pre-committed criterion allowed up to four of twenty of difference in finding the cause; it came out exactly four the first time and six the second. The forest arm is somewhat easier, and that has to sit alongside that row — not alongside the patching row, which is identical in both arms.
- **The coder cannot be blinded.** The text says "the model" or "the random forest" in every paragraph, and pretending otherwise would be a lie. What stands in its place: a symmetric criterion fixed in writing before a single response was read, two independent coders agreeing at 0.95, an arbiter for the disagreements, and the quotes published so anyone can argue with each call.
- **The two samples are not pooled.** They're reported separately with an explicit statement of what replicates and what doesn't. Summing them for power would be exactly the shortcut this experiment measures in others.
- **One fault, one corpus, two heads.** That the behaviour is generic against *this* failure under *this* opacity doesn't make it generic against any.

### And a process note

The first version of this control didn't certify the two arms alike: 260/260 for the forest and 240/260 for the model. Since the argument for ruling out the head is one of the things being measured, making it more available on one side contaminated exactly what mattered. It was rebuilt — storing the output by context equalises the two certifications, and takes the network call out of the model's package on the way — and no figure from that version appears here.

It earns a line because it's the same error the experiment measures, committed by me on the experiment: I attributed to the head an effect that was in large part my own scaffolding.

## Two hundred and eighty

Across five scenarios, two kinds of head, passive permission and explicit permission, **not one of two hundred and eighty responses has asked for the information it was missing before concluding.**

That number has survived every manipulation I've thrown at it, including the one designed to break it, the one that took the language model out of the loop, and the one that repeated the whole measurement from scratch. It is the most robust thing in the whole series, and I still don't have a good explanation for it.

The best I have is the shape of what replaces it: they build their own measurement instead — a script, a sweep, a synthetic reproduction. They want the data. They just don't ask.

---

*Code, data and the script that recomputes every number: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). The series: [the observation](/en/blog/blaming-the-model), [the measurement](/en/blog/patched-the-symptom), and this control.*
