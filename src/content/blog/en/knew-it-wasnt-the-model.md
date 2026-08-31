---
title: "They knew it wasn't the model. They patched it anyway."
description: "I swapped the language model for a random forest and ran the same broken pipeline past forty agents. Nineteen of twenty patched the symptom on each side, with the model and without it. I ran it twice: half of what I'd measured was my own setup, and what holds up isn't that they investigate less — it's what they accuse the model of."
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

That sentence cost me running the control twice.

## The setup I had to throw away

The first version did not give 260/260 in both arms. It gave 260/260 for the forest and 240/260 for the model, and I wrote those two numbers side by side as if the asymmetry were a bookkeeping detail: of thirteen contexts, twelve reproduced 20/20, and the single one that missed gave the same label all twenty times.

It was not a bookkeeping detail. It was a defect placed in the worst possible spot.

Because the analysis further down says that what predicts whether an agent looks upstream is not which head is in the box — it is **whether it builds an argument for ruling the head out**. And I had made that argument literally more available in one arm than in the other. I was measuring, in part, my own header.

The fix turned out to be the thing anyone does for cost reasons: **the system caches the head's output keyed by context**. With that, the model arm certifies 260/260 exactly like the forest, and its head file reads from disk instead of calling the network — which closes the second defect on the way, since the with-code package on the model side contained a network call, a legitimate culprit the forest didn't have.

The fault doesn't move: it's still in retrieval, upstream of the cache, so caching doesn't mask it. Verified across all 285 runs: the same projects that changed still change, with zero differences in ordering, position, prompt or code. And the two briefs now differ in **exactly one line** — "the classification is decided by a language model" against "the classification is decided by a random forest" — with a test that aborts the run if the diff is anything else.

Forty fresh agents saw the table without the code, twenty per arm. Everything below is from the second version.
## What happened

| | language model | random forest | p |
|---|---|---|---|
| **Patches the symptom** | **19/20** | **19/20** | 0.76 |
| Uses the determinism argument | 9/20 | 16/20 | **0.024** |
| Places the cause upstream | 10/20 | 16/20 | **0.048** |
| Blames the head | 12/20 | 6/20 | 0.056 |
| Finds the real cause | **0/20** | 4/20 | 0.053 |
| Asks for the data it lacks | 0/20 | 0/20 | — |

Thirty-eight of forty patched the symptom. Nineteen in each arm, the same exact figure on both sides. Wilson interval [0.84, 0.99].

That's the row that breaks the frame I brought in, and it also turns out to be the one that moved least when I fixed the setup: it was 20 and 20 before.

What did move, a lot, is the attribution. With the dirty setup, nineteen of twenty blamed the model and nine blamed the forest, at p = 0.0006. With both arms certified alike: twelve and six. Same direction, half the size.

It's worth saying out loud what just happened. This entire series is about attributing to the head what belongs to the scaffolding around it. I did exactly that to my own experiment, and I did it while printing the number that gave me away — 240/260 — in the same sentence where I explained why it didn't matter.

Looking at that table I wrote a thesis: the model doesn't change whether you patch, it changes *where you stop looking*. Ten of twenty against sixteen going upstream, and a lovely analysis saying it all ran through whether you built the exclusion argument.

And then I ran it again.

## What survived the second round

Forty fresh responses, the same two packages without a byte of change, the same brief. This time with one more variable, written down and committed before a single response was collected.

| | first round | second round | |
|---|---|---|---|
| Patches the symptom | 19/19 | 19/19 | no difference, twice |
| Uses the determinism argument | 9/16 · p=0.024 | 9/16 · p=0.024 | identical |
| Blames the head | 12/6 · p=0.055 | 13/6 · p=0.028 | replicates |
| Finds the cause | 0/4 · p=0.053 | 2/8 · p=0.032 | replicates |
| **Places the cause upstream** | 10/16 · p=0.048 | **16/17 · p=0.50** | **does not replicate** |
| Asks for the data it lacks | 0/20 and 0/20 | 0/20 and 0/20 | — |

My pretty thesis fell over. With a language model in front of them, agents look upstream **exactly as often** as with a forest: sixteen against seventeen. And the chain analysis — whoever builds the exclusion argument looks upstream 25 of 25, whoever doesn't, 1 of 15 — went from p below 0.0001 to **p = 0.22**. It was post-hoc, it was the most elegant thing I had, and it doesn't survive a second sample.

What did survive is everything else, and one row replicated to the digit: nine against sixteen on the determinism argument, both times.

<figure class="gua-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Dot plot of the gap between arms, model minus forest, out of twenty responses. Each measure has a hollow dot for the first round and a filled one for the second, joined by a line. Patching the symptom is zero both times. Blaming the head goes from plus six to plus seven; the determinism argument stays at minus seven both times; finding the cause goes from minus four to minus six; placing the cause upstream goes from minus six to minus one, close to zero. Accusing the head of being random, measured only in the second round, is plus ten.">
  <line x1="300" y1="52" x2="300" y2="270" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="300" y="44" fill="#94a3b8" font-size="11" text-anchor="middle">no difference</text>
  <circle cx="392" cy="20" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><text x="402" y="24" fill="#cbd5e1" font-size="11">first round</text>
  <circle cx="492" cy="20" r="4.5" fill="#2dd4bf"/><text x="502" y="24" fill="#cbd5e1" font-size="11">second</text>
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
  <text x="20" y="264" fill="#5eead4" font-size="12">calls it random by nature</text>
  <circle cx="500" cy="260" r="4.5" fill="#2dd4bf"/>
  <text x="160" y="290" fill="#94a3b8" font-size="11" text-anchor="middle">&#8592; more with the forest</text>
  <text x="450" y="290" fill="#94a3b8" font-size="11" text-anchor="middle">more with the model &#8594;</text>
</svg>
<figcaption>Gap between the two arms, out of twenty responses each, measured twice. Almost everything stays where it was. The red row is the one that moved: looking upstream came so close to zero that the thesis I had built on it no longer stands. Where only one dot shows, the two rounds landed on the same number and overlap. The last row has one for a different reason: it was only measured in the second round — it's the one that was written down before looking.</figcaption>
</figure>

## What it gets accused of

The new variable is the one I'd had in mind from the start, which is why I wrote it down before running anything: not *how much* they blame the head, but **what they blame it for**.

There are two ways to accuse a component of an output that wobbles. One is that it's random by nature: it samples, it has noise, it rolls the dice. The other is that it's deterministic but the system does something to it: retrains it, parallelises it, changes its configuration. Both are formulable against both heads — a forest can vote with randomness, an inference server can batch requests — and the coding criterion was fixed in writing, with examples of both accusations for both heads, before a single response was read.

| | language model | random forest | p |
|---|---|---|---|
| **Accuses it of randomness of its own** | **14/20** | **4/20** | **0.0018** |

Two independent coders, agreement 0.95; the two disagreements were settled by a third who didn't know how either had voted.

And the vocabulary, which is no longer a measure but simply what's on the page: the model arm gives you "it re-samples every night", "temperature > 0 with no seed", "sampling noise on every call", "the nightly re-roll". The four in the forest arm who also accuse their head say nothing of the kind. They say it **retrains without `random_state`**, that `predict_proba` runs over the whole batch, that floating point moves under parallelism.

The forest gets accused of what the system does to it. The model, of what it is.

The patches follow the diagnosis, as always: proposing to take the randomness out of the head, seventeen of twenty against eleven of twenty. `temperature=0` and `seed` on one side; `random_state` and `n_jobs=1` on the other. Worth noting that the first is a dial that most current reasoning models no longer expose.

Six responses do both at once: they accuse the model of sampling **and** cite the certification that exonerates it, in the same document.

## The dissociation

This is the finding, and it has now come out twice with the same figure.

Of the twenty-five responses that exonerated the head — across both arms, on the same argument and the same certification — **twenty-three proposed a patch anyway.** In the first round: twenty-five and twenty-three.

One writes: *"a random forest is a pure function: same feature vector, same vote. The 260/260 confirms it. The classifier is ruled out."* Its fourth recommendation is to publish by margin instead of top-1, with a threshold on the confidence gap and human review below it — *"this cuts the symptom the user sees, whatever the root cause"*.

That last clause is the whole article. Cutting the symptom the user sees, whatever the root cause, is a perfectly sensible operational instinct. It is also what you do instead of finding the cause, and for *that* the thing in the box doesn't need to be a language model — it needs to be closed.

## What the model does and doesn't change

**Patching is generic.** Nineteen of twenty on each side, in both rounds, with both heads, exonerated or not. Whatever drives an engineer to smooth an output rather than trace it, a language model is not a prerequisite — an opaque component is.

**Investigating barely moves.** They look upstream equally — sixteen against seventeen; what changes is that they get less far: two of twenty against eight find the cause, and the same two against eight name the real mechanism. A real difference, and a small one — not the one I had announced.

**What does change, and it's the only large thing left, is the nature of the suspicion.** With the same certification in front of them and the same argument available to clear it, one head gets accused of being random and the other doesn't. Fourteen against four.

That is the LLM-specific claim, and it's the oldest and simplest of the ones I brought in: it isn't that people investigate less, it's that **the model gets charged with a class of fault that the thing standing in its place does not**.

## The question that lost half its object

I came into this piece with two hypotheses about why the reflex exists. One said it was a **fossil of the training corpus** — a habit from an era when `temperature` really was the main dial and treating output variance as a property of the model really was correct. The other said it was **the model's personality**, some being more inclined than others to look outward before looking at their own work.

For the patching, both are moot: there's no model-specific behaviour there to explain, because it shows up unchanged with no model in the loop.

For the accusation they're both still live, and the first now has one hint in its favour it didn't have before: what shows up in the model arm isn't reasoning about this system, it's a vocabulary — temperature, seed, roll, sampling — applied to a component that in this setup reads from disk. That is what a habit looks like. But still live isn't separated: a habit learned from a corpus that steers tokens without passing through any consultable belief is indistinguishable from a disposition, for any experiment that only observes behaviour. Three independent reviewers of the design converged on that before a single response was collected.

## What doesn't hold

- **The where-the-search-stops thesis, which is the one I had published.** Looking upstream came out 10 against 16 in the first round and 16 against 17 in the second. It doesn't replicate, and the mediation that propped it up went from p < 0.0001 to p = 0.22. I wrote it off one sample with an analysis I thought of while looking at the data; both show.
- **The difficulty band passed by a hair in the first round** — four of twenty of difference in finding the cause, exactly the committed limit — and broke in the second, at six.
- **The coder cannot be blinded.** The text says "the model" or "the random forest" in every paragraph, and pretending otherwise would be a lie. What stands in its place: a symmetric criterion fixed in writing before a single response was read, two independent coders agreeing at 0.95, an arbiter for the disagreements, and the quotes published so anyone can argue with each call.
- **The two rounds are not pooled.** They're reported separately with an explicit statement of what replicates and what doesn't. Summing them for power would be exactly the shortcut this experiment measures in others.
- **The with-code arm hasn't been re-run.** The cache fix would clean it too, but the only numbers I have for it come from the defective version, so I don't use them.
- **One fault, one corpus, two heads.** That the behaviour is generic against *this* failure under *this* opacity doesn't make it generic against any.

## Two hundred and eighty

Across five scenarios, two kinds of head, passive permission and explicit permission, three different setups of the same control, **not one of two hundred and eighty responses has asked for the information it was missing before concluding.**

That number has survived every manipulation I've thrown at it: the one designed to break it, the one that took the language model out of the loop, the one that fixed my own setup, and the one that repeated the whole measurement from scratch. It is the most robust thing in the whole series, and I still don't have a good explanation for it.

The best I have is the shape of what replaces it: they build their own measurement instead — a script, a sweep, a synthetic reproduction. They want the data. They just don't ask.

---

*Code, data and the script that recomputes every number: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). The series: [the observation](/en/blog/blaming-the-model), [the measurement](/en/blog/patched-the-symptom), and this control.*
