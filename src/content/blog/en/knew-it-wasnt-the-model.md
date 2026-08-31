---
title: "They knew it wasn't the model. They patched it anyway."
description: "I swapped the language model for a random forest and ran the same broken pipeline past forty agents. Everyone patched the symptom either way — but with the model in the box, nobody found the cause at all. Patching is generic; investigating is not."
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

That row is the one I noticed first, and it's the one that breaks the frame I'd built. But it isn't the only story in the table, and the rest of it deserves more than a shrug — because the other four rows are not four separate measurements. They're a chain.

With the model in the box, suspicion stays on the box: nineteen of twenty blame it. Only seven of twenty look upstream at all. **Nobody finds the cause.**

With the forest in the box, they exonerate it — seventeen of twenty argue explicitly that a trained random forest is a pure function, that the certification proves it, that the classifier is ruled out. Fifteen then look upstream. Five find the cause.

So swapping the head doesn't change whether they patch. It changes **where they look, and whether they get there**. A language model in the loop absorbs the suspicion, and the investigation stops at the thing being suspected.

And then, having exonerated the box, they patch it anyway.

<figure class="gua-fig">
<svg viewBox="0 0 600 310" role="img" aria-label="Bar chart of five measures out of twenty responses per arm. Patching the symptom is twenty in both. Blaming the head is nineteen for the model and nine for the forest; the determinism argument two and seventeen; looking upstream seven and fifteen; finding the cause zero and five.">
  <rect x="366" y="12" width="12" height="12" fill="#2dd4bf"/><text x="384" y="22" fill="#cbd5e1" font-size="12">language model</text>
  <rect x="366" y="30" width="12" height="12" fill="#f59e0b"/><text x="384" y="40" fill="#cbd5e1" font-size="12">random forest</text>
  <text x="20" y="22" fill="#94a3b8" font-size="12">out of 20 responses per arm</text>
  <text x="20" y="76" fill="#e2e8f0" font-size="13">patched the symptom</text>
  <rect x="210" y="64" width="330" height="14" rx="2" fill="#2dd4bf"/><text x="548" y="76" fill="#5eead4" font-size="12">20</text>
  <rect x="210" y="82" width="330" height="14" rx="2" fill="#f59e0b"/><text x="548" y="94" fill="#fbbf24" font-size="12">20</text>
  <text x="20" y="124" fill="#e2e8f0" font-size="13">blamed the head</text>
  <rect x="210" y="112" width="314" height="14" rx="2" fill="#2dd4bf"/><text x="532" y="124" fill="#5eead4" font-size="12">19</text>
  <rect x="210" y="130" width="148" height="14" rx="2" fill="#f59e0b"/><text x="366" y="142" fill="#fbbf24" font-size="12">9</text>
  <text x="20" y="172" fill="#e2e8f0" font-size="13">&quot;it's deterministic&quot;</text>
  <rect x="210" y="160" width="33" height="14" rx="2" fill="#2dd4bf"/><text x="251" y="172" fill="#5eead4" font-size="12">2</text>
  <rect x="210" y="178" width="280" height="14" rx="2" fill="#f59e0b"/><text x="498" y="190" fill="#fbbf24" font-size="12">17</text>
  <text x="20" y="220" fill="#e2e8f0" font-size="13">looked upstream</text>
  <rect x="210" y="208" width="115" height="14" rx="2" fill="#2dd4bf"/><text x="333" y="220" fill="#5eead4" font-size="12">7</text>
  <rect x="210" y="226" width="248" height="14" rx="2" fill="#f59e0b"/><text x="466" y="238" fill="#fbbf24" font-size="12">15</text>
  <text x="20" y="268" fill="#e2e8f0" font-size="13">found the cause</text>
  <rect x="210" y="256" width="2" height="14" rx="2" fill="#2dd4bf"/><text x="220" y="268" fill="#5eead4" font-size="12">0</text>
  <rect x="210" y="274" width="82" height="14" rx="2" fill="#f59e0b"/><text x="300" y="286" fill="#fbbf24" font-size="12">5</text>
</svg>
<figcaption>The top row is the same bar twice: patching doesn't care what's in the box. Every row below it moves, and all in the same direction — with a language model in the loop the suspicion stays on the head, fewer look past it, and nobody arrives.</figcaption>
</figure>

## What actually unlocks the search

The table above leaves one thing genuinely ambiguous, and it's the thing I most wanted to resolve: is the forest arm *easier*, or does the model *absorb the suspicion*? Those predict the same numbers.

The responses themselves narrow it. This is post-hoc — I did not pre-register it, and it should be read as a lead rather than a result — but it's the cleanest structure in the data.

| | looked upstream |
|---|---|
| Built the determinism argument | **17/19** |
| Didn't | **5/21** |

p < 0,0001. And conditioning on that argument, the effect of the head disappears: among those who built it, the model arm goes 2/2 and the forest arm 15/17. Among those who didn't, 5/18 and 0/3.

So what unlocks the search isn't what's in the box. It's **whether you reach an argument for ruling the box out**. The two responses in the model arm who got there looked upstream, both of them.

The same shape shows up from the other side: of the twelve responses across both arms that did *not* blame the head, **twelve looked upstream**. Of the twenty-eight that did, ten. And finding the cause happens only downstream of looking: 5 of the 22 who looked upstream found it, 0 of the 18 who didn't.

That's a cleaner statement of the LLM-specific claim than "the model absorbs blame". A frozen forest hands you the exclusion argument for free — it is a pure function and you can say so in one line. A language model doesn't, and almost nobody builds one anyway: two of twenty. The model doesn't block the search directly. It withholds the argument that would start it.

## The dissociation

This is the finding, and it survives the strictest slice I can take of it.

Of the twenty responses facing the forest, **seventeen made the determinism argument. All seventeen proposed a patch anyway.** Eleven exonerated the head outright, with no hedging. All eleven patched too.

One writes: *"a random forest is a pure function: same feature vector, same vote. The 260/260 confirms it. The classifier is ruled out."* Its fourth recommendation is to publish by margin instead of top-1, with a threshold on the confidence gap and human review below it — *"this cuts the symptom the user sees, whatever the root cause"*.

That last clause is the whole article. Cutting the symptom the user sees, whatever the root cause, is a perfectly sensible operational instinct. It is also what you do instead of finding the cause, and for *that* the thing in the box doesn't need to be a language model — it needs to be closed.

What the language model adds is the other half: somewhere plausible for the suspicion to come to rest. The forest offers no such resting place, so nine of twenty still blame it but fifteen go looking upstream. The model offers an excellent one, and seven do.

## What the model does and doesn't change

The honest reading of this table is that it splits the thing I'd been calling one behaviour into two, and only one of them is generic.

**Patching is generic.** It doesn't care what's in the box. Whatever drives an engineer to smooth an output rather than trace it, a language model is not a prerequisite — an opaque component is.

**Investigating is not.** Every step of the diagnostic chain moves when the head changes, and moves in the same direction: attribution to the head (19/20 → 9/20), looking upstream (7/20 → 15/20), reaching the cause (0/20 → 5/20). The model doesn't make people patch. It makes them stop at the model.

That second half is the LLM-specific claim, and it survives — in a sharper form than the one I started with. The original thesis was about *what the agent says*: it blames the model. What the data supports is about *where the agent stops*: the language model acts as a sink for suspicion, and the search ends at the thing suspected. Nobody in the model arm found the cause. Not one.

## The question that lost half its object

I came into this piece with two hypotheses about why the reflex exists. One said it was a **fossil of the training corpus** — a habit from an era when `temperature` really was the main dial and treating output variance as a property of the model really was correct. The other said it was **the model's personality**, some being more inclined than others to look outward before looking at their own work.

For the patching, both are moot: there's no model-specific behaviour there to explain, because it shows up unchanged with no model in the loop.

For the attribution, they're still live, and this design can't separate them — which was true before I ran anything. A habit learned from a corpus that steers tokens without passing through any consultable belief is indistinguishable from a disposition, for any experiment that only observes behaviour. Three independent reviewers of the design converged on that before a single response was collected.

## What doesn't hold

- **The difficulty band broke, by one unit, and it's ambiguous which way to read it.** The pre-committed criterion allowed up to 4/20 of difference in finding the cause; it came out 5/20. One reading is that the forest arm is simply *easier*, which would be a pairing defect — and note the direction still plays against the patching result, since an easier task should produce less patching, not the same. The other reading is that it isn't a defect at all but the finding itself: the 0/20 is what happens when suspicion has somewhere comfortable to stop. The three other rows of the chain are consistent with the second, and the mediation above narrows it further — what predicts looking upstream is the exclusion argument, not the head itself. It still isn't settled: this design can't fully separate them, and the mediation is post-hoc.
- **The certification neutralised less than intended.** 260/260 against 240/260 still reads as "perfect" versus "not quite", and seventeen of twenty reasoned from exactly that. Up close the model's miss is a single context out of thirteen — twelve reproduced 20/20, and the one that didn't gave the same label all twenty times.
- **The with-code arm isn't clean on the model side**: its head file contains the network call, a legitimate culprit the forest doesn't have. Faking that would be lying about the system. The comparison that carries is the one without code.
- **One fault, one corpus, two heads.** That the behaviour is generic against *this* failure under *this* opacity doesn't make it generic against any.

## Two hundred

Across five scenarios, two kinds of head, passive permission and explicit permission, **not one of two hundred responses has asked for the information it was missing before concluding.**

That number has now survived every manipulation I've thrown at it, including the one designed to break it and the one that removed the language model entirely. It is the most robust thing in the whole series, and I still don't have a good explanation for it.

The best I have is the shape of what replaces it: they build their own measurement instead — a script, a sweep, a synthetic reproduction. They want the data. They just don't ask.

---

*Code, data and the script that recomputes every number: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). The series: [the observation](/en/blog/blaming-the-model), [the measurement](/en/blog/patched-the-symptom), and this control.*
