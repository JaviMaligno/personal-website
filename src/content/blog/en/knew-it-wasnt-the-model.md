---
title: "They knew it wasn't the model. They patched it anyway."
description: "I swapped the language model for a random forest and ran the same broken pipeline past forty agents. Nineteen of twenty patched the symptom on each side — but with the model in the box, nobody found the cause at all. And when I fixed a defect in my own setup, half the effect went with it."
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

What did move, a lot, is the attribution. With the dirty setup, nineteen of twenty blamed the model and nine blamed the forest, at p = 0.0006. With both arms certified alike: twelve and six. Same direction, half the size, and no longer significant. **A good part of what I had measured as a property of the model was a property of my header.**

It's worth saying out loud what just happened. This entire series is about attributing to the head what belongs to the scaffolding around it. I did exactly that to my own experiment, and I did it while printing the number that gave me away — 240/260 — in the same sentence where I explained why it didn't matter.

What survives the fix is smaller, and more interesting.

With the model in the box, ten of twenty look upstream at all. With the forest, sixteen. And reaching the cause: four with the forest, **zero with the model**. That zero is the one thing that has never moved, across setups or conditions: **zero of forty**, summing both versions of the control.

And then, having exonerated the box, they patch it anyway.

<figure class="gua-fig">
<svg viewBox="0 0 600 310" role="img" aria-label="Bar chart of five measures over twenty responses per arm, with both heads certified at the same level. Patching the symptom is nineteen in both. The determinism argument is nine with the model and sixteen with the forest; looking upstream ten and sixteen; blaming the head twelve and six; finding the cause zero and four.">
  <rect x="366" y="12" width="12" height="12" fill="#2dd4bf"/><text x="384" y="22" fill="#cbd5e1" font-size="12">language model</text>
  <rect x="366" y="30" width="12" height="12" fill="#f59e0b"/><text x="384" y="40" fill="#cbd5e1" font-size="12">random forest</text>
  <text x="20" y="22" fill="#94a3b8" font-size="12">out of 20 responses per arm</text>
  <text x="20" y="76" fill="#e2e8f0" font-size="13">patches the symptom</text>
  <rect x="210" y="64" width="314" height="14" rx="2" fill="#2dd4bf"/><text x="532" y="76" fill="#5eead4" font-size="12">19</text>
  <rect x="210" y="82" width="314" height="14" rx="2" fill="#f59e0b"/><text x="532" y="94" fill="#fbbf24" font-size="12">19</text>
  <text x="20" y="124" fill="#e2e8f0" font-size="13">&#8220;it&#8217;s deterministic&#8221;</text>
  <rect x="210" y="112" width="149" height="14" rx="2" fill="#2dd4bf"/><text x="367" y="124" fill="#5eead4" font-size="12">9</text>
  <rect x="210" y="130" width="264" height="14" rx="2" fill="#f59e0b"/><text x="482" y="142" fill="#fbbf24" font-size="12">16</text>
  <text x="20" y="172" fill="#e2e8f0" font-size="13">looks upstream</text>
  <rect x="210" y="160" width="165" height="14" rx="2" fill="#2dd4bf"/><text x="383" y="172" fill="#5eead4" font-size="12">10</text>
  <rect x="210" y="178" width="264" height="14" rx="2" fill="#f59e0b"/><text x="482" y="190" fill="#fbbf24" font-size="12">16</text>
  <text x="20" y="220" fill="#e2e8f0" font-size="13">blames the head</text>
  <rect x="210" y="208" width="198" height="14" rx="2" fill="#2dd4bf"/><text x="416" y="220" fill="#5eead4" font-size="12">12</text>
  <rect x="210" y="226" width="99" height="14" rx="2" fill="#f59e0b"/><text x="317" y="238" fill="#fbbf24" font-size="12">6</text>
  <text x="20" y="268" fill="#e2e8f0" font-size="13">finds the cause</text>
  <rect x="210" y="256" width="2" height="14" rx="2" fill="#2dd4bf"/><text x="220" y="268" fill="#5eead4" font-size="12">0</text>
  <rect x="210" y="274" width="66" height="14" rx="2" fill="#f59e0b"/><text x="284" y="286" fill="#fbbf24" font-size="12">4</text>
</svg>
<figcaption>The top row is the same bar twice: patching doesn't care what's in the box. The ones below all move, all in the same direction and none of them overwhelmingly — except the last, where with a language model inside nobody arrives.</figcaption>
</figure>

## What actually unlocks the search

The table leaves one thing genuinely ambiguous, and it's the one I most wanted to settle: is the forest arm *easier*, or does the model *absorb the suspicion*? Both predict the same numbers.

The responses themselves narrow it. This is post-hoc in origin — I didn't pre-register it — but it's the cleanest structure in the data, and it is now measured on the good setup.

| | looks upstream |
|---|---|
| Builds the determinism argument | **25/25** |
| Doesn't build it | **1/15** |

p < 0.0001. And conditioning on that argument, the effect of the head **disappears entirely**: among those who build it, the model arm goes 9 of 9 and the forest arm 16 of 16. Among those who don't, 1 of 11 and 0 of 4.

It's a four-link chain in which the head only touches the first link:

**what's in the box → whether you build the argument to rule it out → whether you look upstream → whether you reach the cause**

A frozen forest hands you that argument: it's a pure function, it takes one line to say, and sixteen of twenty say it. A language model, with exactly the same certification in front of it and in the same position in the brief, does not: nine of twenty. **The model doesn't block the search. It withholds the argument that would have started it.**

And there is what my dirty setup did. In the first version that figure wasn't nine of twenty — it was two. The setup bias and the real effect pushed in the same direction, which is the most uncomfortable way to be wrong: the result comes out prettier and you don't know how much of it is yours.

The same shape shows up from the other side: of the twenty-two responses that did *not* blame the head, **twenty-two looked upstream**. Of the eighteen that did, four. And finding the cause only ever happens downstream of looking: 4 of the 26 who looked, 0 of the 14 who didn't.

## The dissociation

This is the finding, and it survives the strictest slice I can take of it.

Of the twenty-five responses that exonerated the head — across both arms, on the same argument and the same certification — **twenty-three proposed a patch anyway.**

One writes: *"a random forest is a pure function: same feature vector, same vote. The 260/260 confirms it. The classifier is ruled out."* Its fourth recommendation is to publish by margin instead of top-1, with a threshold on the confidence gap and human review below it — *"this cuts the symptom the user sees, whatever the root cause"*.

That last clause is the whole article. Cutting the symptom the user sees, whatever the root cause, is a perfectly sensible operational instinct. It is also what you do instead of finding the cause, and for *that* the thing in the box doesn't need to be a language model — it needs to be closed.

## What the model does and doesn't change

The honest reading splits the thing I'd been calling one behaviour into two, and only one of them is generic.

**Patching is generic.** Nineteen of twenty on each side, head exonerated or not. Whatever drives an engineer to smooth an output rather than trace it, a language model is not a prerequisite — an opaque component is.

**Investigating, less so.** Every step of the chain moves when the head changes, all in the same direction, but on the clean setup the effects are small and sitting on the threshold: 0.024 for the argument, 0.048 for looking upstream, 0.053 for reaching the cause, 0.056 for attribution. At twenty per arm, that is exactly what it looks like when something is there and it isn't large.

So the LLM-specific claim survives, smaller than I had measured it and with its shape changed. The version I brought in was about *what the agent says*: it blames the model. That's precisely the one that nearly falls over once the defect is removed — twelve against six, p = 0.056. The one that holds is about *where it stops*: with a language model in front of them, the argument that unlocks the investigation occurs to fewer than half, and nobody gets as far as the cause.

## The question that lost half its object

I came into this piece with two hypotheses about why the reflex exists. One said it was a **fossil of the training corpus** — a habit from an era when `temperature` really was the main dial and treating output variance as a property of the model really was correct. The other said it was **the model's personality**, some being more inclined than others to look outward before looking at their own work.

For the patching, both are moot: there's no model-specific behaviour there to explain, because it shows up unchanged with no model in the loop.

For what's left, they're still live, and this design can't separate them — which was true before I ran anything. A habit learned from a corpus that steers tokens without passing through any consultable belief is indistinguishable from a disposition, for any experiment that only observes behaviour. Three independent reviewers of the design converged on that before a single response was collected.

## What doesn't hold

- **Blaming the head no longer reaches significance.** p = 0.056. On the previous setup it looked like the most solid effect in the table, and it was in large part the asymmetric certification. It stands as a trend, and should be read as one.
- **The difficulty band passed by a hair.** The pre-committed criterion allowed up to 4 of 20 of difference in finding the cause, and it came out exactly 4 (zero against four). On the first version it came out 5 and broke. Passing at the line is not the same as passing comfortably.
- **The mediation is post-hoc in origin.** I didn't pre-register it. It replicates here on the clean setup and comes out stronger than on the dirty one, which helps; it is still an analysis I thought of while looking at data.
- **The with-code arm hasn't been re-run.** The cache fix would clean it too, but the only numbers I have for it come from the defective version, so I don't use them for anything.
- **One fault, one corpus, two heads.** That the behaviour is generic against *this* failure under *this* opacity doesn't make it generic against any.

## Two hundred and forty

Across five scenarios, two kinds of head, passive permission and explicit permission, two different setups of the same control, **not one of two hundred and forty responses has asked for the information it was missing before concluding.**

That number has now survived every manipulation I've thrown at it, including the one designed to break it, the one that removed the language model entirely, and the one that fixed my own setup. It is the most robust thing in the whole series, and I still don't have a good explanation for it.

The best I have is the shape of what replaces it: they build their own measurement instead — a script, a sweep, a synthetic reproduction. They want the data. They just don't ask.

---

*Code, data and the script that recomputes every number: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). The series: [the observation](/en/blog/blaming-the-model), [the measurement](/en/blog/patched-the-symptom), and this control.*
