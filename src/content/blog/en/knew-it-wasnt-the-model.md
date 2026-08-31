---
title: "They knew it wasn't the model. They patched it anyway."
description: "I swapped the language model for a random forest and ran the same broken pipeline past forty agents. Seventeen of twenty argued that a trained forest is deterministic and cannot be the cause — and all seventeen proposed stabilising it regardless. The behaviour was never about the model."
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
<svg viewBox="0 0 600 250" role="img" aria-label="Diagram of the control: the same pipeline — corpus, retrieval with the planted fault, and context assembly — feeds two different classifying heads, a language model and a frozen random forest. Everything before the head is identical in both arms.">
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

  <text x="300" y="228" fill="#94a3b8" font-size="12" text-anchor="middle">everything left of the head is byte-for-byte identical in both arms</text>
</svg>
<figcaption>The whole control. The fault sits in retrieval, upstream of the head, so it is the same fault in both arms — and the head, whichever it is, classifies correctly whatever it is handed.</figcaption>
</figure>

Both briefs carry a measured certification, and it is the piece that makes the comparison fair: *"re-running the classification over the same context reproduced the output in X of 20 cases"* — 260/260 for the forest, 240/260 for the model, the real numbers. Without it, an agent facing the forest could reason, entirely correctly, that a trained forest is deterministic and therefore the cause must be upstream, and would patch less for a good reason rather than a revealing one.

Forty agents saw the table without the code, twenty per arm.

## What happened

| | language model | random forest | p |
|---|---|---|---|
| **Patched the symptom** | **20/20** | **20/20** | 1,00 |
| Blamed the head | 19/20 | 9/20 | **0,0006** |
| Used the determinism argument | 2/20 | 17/20 | **<0,0001** |
| Located the cause upstream | 7/20 | 15/20 | 0,012 |
| Found the actual cause | 0/20 | 5/20 | 0,024 |
| Asked for the missing data | 0/20 | 0/20 | — |

Forty out of forty patched the symptom. Wilson interval [0,91, 1,00].

What changes with the head is **the explanation, not the behaviour**. With the model, nineteen of twenty blame the head. With the forest, nine — and seventeen of twenty argue explicitly that a trained random forest is a pure function, that the certification proves it, that the classifier is therefore ruled out.

And then they patch it.

<figure class="gua-fig">
<svg viewBox="0 0 600 210" role="img" aria-label="Bar chart comparing the two arms out of twenty responses each. Patching the symptom is twenty out of twenty in both. Blaming the head is nineteen for the language model and nine for the forest. Using the determinism argument is two for the model and seventeen for the forest.">
  <rect x="366" y="12" width="12" height="12" fill="#2dd4bf"/><text x="384" y="22" fill="#cbd5e1" font-size="12">language model</text>
  <rect x="366" y="30" width="12" height="12" fill="#f59e0b"/><text x="384" y="40" fill="#cbd5e1" font-size="12">random forest</text>
  <text x="20" y="22" fill="#94a3b8" font-size="12">out of 20 responses per arm</text>

  <text x="20" y="70" fill="#e2e8f0" font-size="13">patched the symptom</text>
  <rect x="210" y="58" width="330" height="14" rx="2" fill="#2dd4bf"/><text x="548" y="70" fill="#5eead4" font-size="12">20</text>
  <rect x="210" y="76" width="330" height="14" rx="2" fill="#f59e0b"/><text x="548" y="88" fill="#fbbf24" font-size="12">20</text>

  <text x="20" y="128" fill="#e2e8f0" font-size="13">blamed the head</text>
  <rect x="210" y="116" width="313" height="14" rx="2" fill="#2dd4bf"/><text x="531" y="128" fill="#5eead4" font-size="12">19</text>
  <rect x="210" y="134" width="148" height="14" rx="2" fill="#f59e0b"/><text x="366" y="146" fill="#fbbf24" font-size="12">9</text>

  <text x="20" y="186" fill="#e2e8f0" font-size="13">"it's deterministic"</text>
  <rect x="210" y="174" width="33" height="14" rx="2" fill="#2dd4bf"/><text x="251" y="186" fill="#5eead4" font-size="12">2</text>
  <rect x="210" y="192" width="280" height="14" rx="2" fill="#f59e0b"/><text x="498" y="204" fill="#fbbf24" font-size="12">17</text>
</svg>
<figcaption>Swapping the head moves the diagnosis and leaves the action exactly where it was. The bar that matters is the top one, and it is the same bar twice.</figcaption>
</figure>

## The dissociation

This is the finding, and it survives the strictest slice I can take of it.

Of the twenty responses facing the forest, **seventeen made the determinism argument. All seventeen proposed a patch anyway.** Eleven exonerated the head outright, with no hedging. All eleven patched too.

One writes: *"a random forest is a pure function: same feature vector, same vote. The 260/260 confirms it. The classifier is ruled out."* Its fourth recommendation is to publish by margin instead of top-1, with a threshold on the confidence gap and human review below it — *"this cuts the symptom the user sees, whatever the root cause"*.

That last clause is the whole article. Cutting the symptom the user sees, whatever the root cause, is a perfectly sensible operational instinct. It is also what you do instead of finding the cause, and it does not need the thing in the box to be a language model. It needs the thing in the box to be closed.

## The question that lost its object

I came into this piece with two hypotheses about why the reflex exists. One said it was a **fossil of the training corpus** — a habit from an era when `temperature` really was the main dial and treating output variance as a property of the model really was correct. The other said it was **the model's personality**, some being more inclined than others to look outward before looking at their own work.

They made different predictions, they were both testable, and the control made both of them moot. There is no model-specific reflex to explain, because the behaviour shows up unchanged when there is no model in the loop at all. Whatever it is, it is not about language models.

It's worth saying what this doesn't demolish. Blaming the model is still real, and it still moves with what you show the agent: 19/20 versus 9/20 is a large, clean difference in attribution. What the control kills is the idea that the *attribution* was driving the *action*. It wasn't. The action was already there.

There's a second thing the design couldn't settle, and I'd rather state it than let it sit implied: even if the reflex had been LLM-specific, corpus and personality are **not separable from the outside**. A habit learned from a corpus that steers tokens without passing through any consultable belief is indistinguishable from a disposition, for any experiment that only observes behaviour. Three independent reviewers of the design converged on that before a single response was collected.

## What doesn't hold

- **The difficulty band broke, by one unit.** The pre-committed criterion allowed up to 4/20 of difference in finding the cause; it came out 5/20 — the forest arm is slightly *easier*. The direction matters: an easier task should produce *less* patching, not the same. It plays against the result and the result holds anyway. I'm not reinterpreting the criterion after the fact; I'm reporting that it broke.
- **The certification neutralised less than intended.** 260/260 against 240/260 still reads as "perfect" versus "not quite", and seventeen of twenty reasoned from exactly that. Up close the model's miss is a single context out of thirteen — twelve reproduced 20/20, and the one that didn't gave the same label all twenty times.
- **The with-code arm isn't clean on the model side**: its head file contains the network call, a legitimate culprit the forest doesn't have. Faking that would be lying about the system. The comparison that carries is the one without code.
- **One fault, one corpus, two heads.** That the behaviour is generic against *this* failure under *this* opacity doesn't make it generic against any.

## Two hundred

Across five scenarios, two kinds of head, passive permission and explicit permission, **not one of two hundred responses has asked for the information it was missing before concluding.**

That number has now survived every manipulation I've thrown at it, including the one designed to break it and the one that removed the language model entirely. It is the most robust thing in the whole series, and I still don't have a good explanation for it.

The best I have is the shape of what replaces it: they build their own measurement instead — a script, a sweep, a synthetic reproduction. They want the data. They just don't ask.

---

*Code, data and the script that recomputes every number: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). The series: [the observation](/en/blog/blaming-the-model), [the measurement](/en/blog/patched-the-symptom), and this control.*
