---
title: "The Law of the Useless Galactic Constant"
description: "This autumn the exponential time hypothesis fell, forced Navier–Stokes blew up and the Riemann hypothesis was proved, and the world works exactly as before. I propose a law to explain it: a problem open long enough that touches the real world is resolved consistently with what we observe, or its inconsistency lives where nobody can observe it."
pubDate: 2026-12-23
tags: ["Mathematics", "Philosophy of Science", "AI"]
lang: en
translationKey: law-of-the-useless-galactic-constant
heroImage: "/blog/law-of-the-useless-galactic-constant.png"
linkedinSummary: |
  Three famous math problems were settled this autumn, with machine-checked proofs. Your software, your plane and your encryption work exactly as they did before. I don't think that is a coincidence.

  The exponential time hypothesis is false, but the algorithm that beats brute force only does so with more than 10^10,000 variables. The universe has about 10^80 atoms.

  The Navier–Stokes equations can blow up, but only once the vortex is narrower than the gap between air molecules, where there is no fluid left to describe.

  The Riemann hypothesis is true, which is what a century of computation already said. Cryptography didn't notice.

  So I'm proposing a law, half as a joke: any problem open long enough that touches the real world either has a resolution consistent with what we observe, or its inconsistency lives where nothing can be observed. "Long enough" is the key: decades of engineers, solvers and computations have already tested every place we can look.

  It is refutable, and that is the part I care about. If you know a long-open problem whose resolution contradicted something measurable, I want to hear it.
---

<style>
.gal-fig { margin: 2rem 0; padding: 1rem; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }
.gal-fig svg { width: 100%; height: auto; display: block; font-family: system-ui, -apple-system, sans-serif; }
.gal-fig figcaption { margin-top: 0.75rem; font-size: 0.9rem; color: #94a3b8; text-align: center; }
</style>

This autumn three problems that had been open for decades were solved, or announced solved with a machine-checked proof: the [exponential time hypothesis is false](/en/blog/exponential-time-hypothesis-falls), the [forced Navier–Stokes equations blow up](/en/blog/navier-stokes-blows-up) in finite time, and the [Riemann hypothesis is true](/en/blog/riemann-hypothesis-proof). I wrote an article on each, and all three ended with a "what changes" section that said, in different words, the same thing: in practice, nothing.

I started taking that seriously because of a WhatsApp conversation. A friend wrote, half joking, that it will turn out P = NP after all, but with a useless galactic constant. I replied:

> We could establish the law of the useless galactic constant: any problem open long enough that affects the real world either has a resolution consistent with what is observed in the real world, or the inconsistency occurs in cases that cannot be observed in the real world.

I wrote it as a joke, but I think it is true, and this article is my attempt to give it shape. It is not a theorem. It is an empirical regularity about how mathematical problems that touch the world get resolved, with an explanation of why it should hold and a concrete condition that would break it.

## This autumn's cases

**All three results contradict what many people believed, and none of them contradicts anything anyone has measured.**

**The exponential time hypothesis.** ETH said that 3-SAT, the reference problem of satisfying a pile of logical constraints at once, cannot be solved in subexponential time. In October OpenAI and Anthropic published algorithms that do it. But Anthropic's only beats brute force once the number of variables exceeds $10^{10\,000}$. The observable universe has about $10^{80}$ atoms. That is the galactic constant of the joke, and the name is not mine: Dick Lipton and Ken Regan call algorithms that are wonderful asymptotically and never used to compute anything [galactic algorithms](https://rjlipton.com/2010/10/23/galactic-algorithms/). Your SAT solver is as fast as before. What was observed, that nobody could find a practical algorithm, is still true. What was believed, that none existed, was false, but only in a region that does not fit in the universe.

**Navier–Stokes.** September's result builds a fluid that, pushed by a smooth force designed for the purpose, reaches infinite speed at a point in finite time. Your drain is not going to burst because the water suddenly flows infinitely fast, and planes are not going to fall out of the sky. The core of the vortex shrinks below the mean free path of air molecules, a few tens of nanometres, long before the speed diverges. At that scale there is no fluid any more, only molecules, and the continuum equations stopped describing anything a while back. As I wrote then, the equations do not predict an infinitely fast fluid; they predict their own boundary.

**The Riemann hypothesis.** Here the resolution is the consistent one: it is true, which is what more than a century of numerical computation said, with trillions of zeros checked on the critical line. Cryptography does not notice. No deployed system depended on it being false, and knowing it is true does not factor any number faster.

## An old case: the Lebesgue-designed airplane

**The law is not from this autumn; mathematicians have been joking about it for a long time.** Richard Hamming, of Hamming codes, once asked: "Does anyone believe that the difference between the Lebesgue and Riemann integrals can have physical significance, and that whether say, an airplane would or would not fly could depend on this difference? If such were claimed, I should not care to fly in that plane."

The question has an answer. Andrew Lewis, of Queen's University, gave it in a paper I remember from university, whose title says it all: [*Should we fly in the Lebesgue-designed airplane?*](https://mast.queensu.ca/~andrew/notes/abstracts/2007c.html) Lewis defends the Lebesgue integral, but his defence is not that the plane flies differently. The two integrals agree on every function a physical measurement can produce; where they differ is on functions so pathological that no sensor would ever see them. Lebesgue's advantage is a different one: it gives spaces of functions the properties you need to prove that the solutions you then compute exist. The difference matters to theorems and not to airplanes, which is exactly what the law says.

<figure class="gal-fig">
<svg viewBox="0 0 600 330" role="img" aria-label="Diagram of the law: a problem open long enough that touches the real world is resolved along one of two branches. Consistent with observation: the Riemann hypothesis, and Lebesgue versus Riemann integration. Inconsistent only where nobody can look: the exponential time hypothesis, whose refutation only beats brute force above 10 to the 10,000 variables, and forced Navier–Stokes, whose blow-up happens below the mean free path of air. A third case is missing: a resolution that contradicts something measurable.">
  <rect x="150" y="14" width="300" height="50" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.25)" stroke-width="1.5"/>
  <text x="300" y="35" text-anchor="middle" font-size="12.5" font-weight="700" fill="#f8fafc">A problem open long enough</text>
  <text x="300" y="52" text-anchor="middle" font-size="11" fill="#94a3b8">that affects the real world</text>
  <path d="M300 64 L300 82 L155 82 L155 100" fill="none" stroke="#64748b" stroke-width="1.5"/>
  <path d="M300 82 L445 82 L445 100" fill="none" stroke="#64748b" stroke-width="1.5"/>
  <rect x="20" y="100" width="270" height="150" rx="8" fill="rgba(45,212,191,0.08)" stroke="#2dd4bf" stroke-width="2"/>
  <text x="155" y="122" text-anchor="middle" font-size="12.5" font-weight="700" fill="#5eead4">Resolution consistent with observation</text>
  <text x="38" y="152" font-size="11.5" font-weight="700" fill="#e2e8f0">Riemann hypothesis</text>
  <text x="38" y="168" font-size="10.5" fill="#94a3b8">true, as the computations said;</text>
  <text x="38" y="182" font-size="10.5" fill="#94a3b8">cryptography untouched</text>
  <text x="38" y="208" font-size="11.5" font-weight="700" fill="#e2e8f0">Lebesgue vs Riemann integral</text>
  <text x="38" y="224" font-size="10.5" fill="#94a3b8">same value on every function</text>
  <text x="38" y="238" font-size="10.5" fill="#94a3b8">a measurement can produce</text>
  <rect x="310" y="100" width="270" height="150" rx="8" fill="rgba(245,158,11,0.08)" stroke="#f59e0b" stroke-width="2"/>
  <text x="445" y="122" text-anchor="middle" font-size="12.5" font-weight="700" fill="#fbbf24">Inconsistent only where unseen</text>
  <text x="328" y="152" font-size="11.5" font-weight="700" fill="#e2e8f0">Exponential time (ETH)</text>
  <text x="328" y="168" font-size="10.5" fill="#94a3b8">beats brute force if n &gt; 10^10,000;</text>
  <text x="328" y="182" font-size="10.5" fill="#94a3b8">the universe has ~10^80 atoms</text>
  <text x="328" y="208" font-size="11.5" font-weight="700" fill="#e2e8f0">Forced Navier–Stokes</text>
  <text x="328" y="224" font-size="10.5" fill="#94a3b8">blows up below the mean free path</text>
  <text x="328" y="238" font-size="10.5" fill="#94a3b8">of air, where there is no fluid</text>
  <rect x="150" y="270" width="300" height="46" rx="8" fill="none" stroke="rgba(255,255,255,0.25)" stroke-width="1.5" stroke-dasharray="5 4"/>
  <text x="300" y="290" text-anchor="middle" font-size="11.5" font-weight="700" fill="#94a3b8">Empty: a resolution that contradicts</text>
  <text x="300" y="306" text-anchor="middle" font-size="11.5" font-weight="700" fill="#94a3b8">something we can measure</text>
</svg>
<figcaption>The two branches the law allows, with this autumn's cases and an old one. The empty box is the one that would refute it.</figcaption>
</figure>

## The key words: long enough

**Without "long enough", the law would be either trivial or overstated, and it is worth seeing why.**

Drop the condition and apply the law to a newly posed problem, and the second branch becomes trivial. Any new claim that has not been tested against reality is, obviously, in the unobserved. Saying that its inconsistency "occurs in unobserved cases" says nothing: almost nothing has been observed yet.

And if, without the time condition, I say "unobservable" instead of "unobserved", the law becomes overstated. I cannot claim something is impossible to observe just because nobody has looked yet.

Time is what turns one into the other. A problem that has been open for decades and touches the real world has spent those decades being tested, without anyone intending to: millions of engineers simulating fluids, decades of SAT solvers in production, trillions of zeros of the zeta function computed. If there were a discrepancy in the region we can look at, with that many people looking, it would have shown up. Given long enough, what remains unobserved stops being "what we have not looked at yet" and becomes, with fair confidence, "what cannot be looked at".

## Why it should hold

**The law is almost a selection effect: the world has already run the experiment across the whole accessible region.**

A mathematical resolution cannot contradict data that already exists, because the world produced the data and the world is consistent with itself. If a problem is settled after so long, it can only disagree with what we believed in places nobody had been able to check. And after decades of checking, those places are the extremes: sizes larger than the universe, scales smaller than a molecule, functions no instrument produces.

ETH shows it well. That nobody found a practical algorithm for 3-SAT in 27 years was an observation about the world, made by thousands of people with every incentive to find one. When the hypothesis fell, the algorithm that brought it down had to respect that observation, and it did in the only way available: by being useless in practice.

## What the law does not say

**It does not say mathematics doesn't matter; it says a resolution does not change what had already been measured.** In all three articles the "what changes" section was not empty. Whole shelves of theorems changed status: what had been proved "assuming ETH" lost its hypothesis, what began "assuming the Riemann hypothesis" gained it, and the study of what happens after a singularity got a concrete object. Those changes happen inside mathematics, which is where the problems live.

**And mathematics is not just results, nor just what it gives the real world.** In the [Riemann article](/en/blog/riemann-hypothesis-proof), in the section "Math is dead", I argued that the discipline is more alive than ever. This law reaches the same place from another side. If proving the most famous conjecture in number theory changes nothing outside it, the value of proving it was never out there. It is in understanding why the primes are distributed the way they are, in the connections between fields the proof forces you to make, and in the questions it leaves open. Usefulness does arrive sometimes, often decades later and by routes nobody planned: in 1940 G. H. Hardy boasted that number theory was good for nothing, and today it holds up the internet's cryptography. But measuring mathematics by what it changes in the world is measuring it with the wrong ruler, and the law explains why that ruler reads almost zero precisely when a great problem falls.

**Nor does it forbid inventions.** The law is about what a resolution says about past observations, not about new capabilities it might bring. A practical algorithm for factoring large integers would really change the world. But look at what the law predicts for that case: factoring has been open for a long time, half the internet depends on it, and decades of cryptanalysts have not found a fast classical algorithm. If factoring is ever shown to be easy, my bet, following the law, is that it will come with a galactic constant. Shor's algorithm is not a counterexample: it runs on a different machine, a quantum computer, and whether a large one can be built is precisely one of the questions still in the unobserved.

**And it can be refuted.** All it takes is a problem open for decades, with real-world consequences, whose resolution contradicts something measurable: the empty box in the figure. A practical algorithm for a problem that had resisted professionals for thirty years, or a real fluid behaving the way the singularity says. I don't know of one.

## An open law

**I'm in no hurry to close it, because the cases keep coming.** On the same day as the Riemann proof, Terence Tao noted an announced finite-time blow-up for Navier–Stokes *without* an external force, the case most people have in mind when they talk about the problem. I have not read it yet. If it holds, it is the next test for the law, and the prediction is concrete: the singularity will again happen below the scale at which a fluid is a fluid.

I will keep adding cases to this article as problems fall. If you know one that fits the empty box, I'm far more interested in it than in any of the ones that confirm the law.

## What to take from it

- **Open problems that touch the world get resolved without contradicting the world.** Either the resolution matches what was observed (Riemann), or it disagrees only where nobody can look (ETH, forced Navier–Stokes).
- **"Long enough" is what gives the law content.** Without it, "unobserved" is trivial and "unobservable" is overstated; with decades of unintended testing, one becomes the other.
- **What changes, changes inside mathematics**: the status of conditional theorems, the methods, the new questions. And its value was never measured by what it gives the real world.
- **The law makes predictions and can be refuted.** Easy factoring would come with a galactic constant; unforced Navier–Stokes blow-up, if confirmed, would live below the molecular scale.

---

*Sources: my articles on [the exponential time hypothesis](/en/blog/exponential-time-hypothesis-falls), [Navier–Stokes](/en/blog/navier-stokes-blows-up) and [the Riemann hypothesis](/en/blog/riemann-hypothesis-proof), with their primary sources; Dick Lipton on [galactic algorithms](https://rjlipton.com/2010/10/23/galactic-algorithms/); Andrew Lewis, [*Should we fly in the Lebesgue-designed airplane?*](https://mast.queensu.ca/~andrew/notes/abstracts/2007c.html); and [Terence Tao's note of 20 November](https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/).*
