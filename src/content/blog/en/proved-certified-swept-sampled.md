---
title: "Proved, Certified, Swept, Sampled"
description: "A sixty-page paper where written proofs, kernel-checked theorems, exact box certificates and plain sampling all print with the same face. Four labels, one per claim, and the case that made me insist on them: a certificate that reported green at exactly the configuration the proof turned on."
pubDate: 2026-09-24
tags: ["Mathematics", "Verification", "Research", "AI"]
lang: en
translationKey: proved-certified-swept-sampled
heroImage: "/blog/proved-certified-swept-sampled.png"
repoUrl: https://github.com/JaviMaligno/calamares
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/2609.15554"
linkedinSummary: |
  A claim in a paper can be backed by a written proof, by a kernel-checked theorem, by exact rational arithmetic over a whole region, or by "I sampled ten million points and nothing broke". All four print the same way: a sentence that sounds true.

  So in my last preprint every claim carries a label saying which one it is — proved, box-certified, grid-swept, sampled — and a map pairing each computational claim with the script behind it. Not a green tick for the paper: a label per claim.

  I did not start out that disciplined about it. What convinced me was a certificate I wrote for one lemma, which an adversarial reviewer refuted three times.

  Version two was the instructive one. It was already rational-directed, no floating-point comparisons in the acceptance test — except for a 1e-12 tolerance. And the configuration the whole lemma turns on is exactly tangent: the feasibility margin there is zero. A tolerance does not introduce a small error at such a point. It changes the answer. The certificate reported "fits" at precisely the configuration where the question is delicate, and it would have kept reporting it forever, because nothing was broken.

  Version four assumes no floating-point fact at all: exact rational arithmetic, an alternating Lagrange remainder for the series, and the library's arcsine used as an oracle that is consulted and not believed.

  The reviewer also caught something I would not have: a claim of mine marked "proved" that was only proved for part of its range. The label was wrong, and a wrong label is worse than a weak one, because it is trusted.

  Your tests, your types, your property checks and your one careful read-through are four different kinds of evidence, and CI paints them all the same green. Which of your claims is proved, and which is just unrefuted so far?
---

A claim in a paper can be backed by very different things.

It can have a written proof. It can have a theorem the Lean kernel has checked. It can have a certificate that ran exact rational arithmetic over an entire region and never once used a floating-point number. Or it can have "I sampled ten million configurations and none of them broke it".

All four print the same way: a sentence in a serif font that sounds true. And the fourth is worth a great deal less than the first, in a way that no amount of confidence in the prose can fix.

My last preprint — the one about [packing nested rings in a frying pan](/en/blog/count-the-rings) — is sixty pages in which all four appear, sometimes on the same page. So every claim in it carries an **epistemic label** saying which one it is: `proved`, `box-certified`, `grid-swept` or `sampled`. Not a green tick for the paper. A label per claim, and an appendix pairing every computational claim with the script that backs it.

![A ladder of four labels, each rung inset further than the one above it. Proved: a written proof, the machine can only recheck it. Box-certified: exact rational arithmetic over the whole domain. Grid-swept: checked on a mesh, silent between the points. Sampled: no contradiction found in the draws taken.](/blog/proved-certified-swept-sampled.png)

The paper says it in one sentence, in the acknowledgements, and I would defend that sentence over any of the theorems: *the mathematical guarantee for every claim is the written proof and, where a proof delegates an identity, an exact symbolic computation; the verification workflow and the numerical sweeps are quality control and evidence, never a substitute for proof.*

This article is about what convinced me to be that pedantic. It was not a principle. It was a certificate that lied to me three times, and the specific way it lied.

## The claim that looked certified

One lemma in that paper concerns a quintet of rings, and closing it needs a statement of the form: *over this whole four-dimensional domain of parameters, this configuration does not fit.* That is exactly the kind of statement you certify computationally, because the domain is continuous and there is nothing to enumerate.

The first attempt did it the way everyone does it: subdivide the domain into boxes, evaluate at each box, use a linear program at the tight ones. An adversarial reviewer — a separate model, given the statement and told to break it — refuted it in one pass, and the refutation was not subtle. The meshes had no Lipschitz bound, so nothing connected the values at the sample points to the values between them. The linear program ran with tolerances. And one of the required inequalities was not certified at all; it had been *sampled*.

That is a fair fight and an easy fix. The second version was written rational-directed: exact arithmetic on the corners, no floating-point comparisons in the acceptance test.

It was refuted too, and this is the part worth the article.

## Why a tolerance is not a small sin

The second version still had one tolerance in it: `1e-12`. Not as a comparison, but as slack — the width of the band inside which two quantities counted as equal.

Now, the configuration the whole lemma turns on is the golden point, where the parameters all equal $\varphi$. And at that point the configuration is **exactly tangent**. The rings touch. The feasibility margin there is not small: it is zero.

![A schematic curve of feasibility margin against a configuration parameter. The curve rises to touch zero at one point — the golden point — and is negative everywhere else. A red band of thickness epsilon straddles the zero line, so the tangent point sits inside the band: the exact answer is "does not fit", and the test with a tolerance answers "fits".](/blog/proved-certified-swept-sampled-fig-1-en.png)

At a point where the margin is zero, a tolerance does not introduce a small error. It changes the answer. The $\varepsilon$-thick acceptance band swallows the tangency, and the certificate reports *fits* at precisely the configuration on which the proof depends. Everywhere else in the domain the tolerance is harmless, which is what makes it so bad: the test is wrong only where the question is delicate, and it is silent about it. Nothing crashes. Nothing looks suspicious. You get a green run and a false lemma.

I want to be careful not to over-claim here. The tolerance did not make the lemma false — the lemma is true, and the final certificate proves it. What the tolerance did was make the certificate *not evidence*. It had been reporting a property of its own acceptance band rather than a property of the geometry.

## What it takes to stop assuming

The third version repaired the tangency but still leaned on `mpmath` for the inverse trigonometry, so it still rested on a floating-point library being right about the arcsine of numbers near a tangency. The fourth version removes that too, and its shape is worth describing because it is what "certified" ends up meaning when you push on it:

- $\arcsin$ is bounded by a **pure rational series**, with $\sin^2$ and $\cos$ bracketed in $\mathbb{Q}$ by an alternating Lagrange remainder — so the bound is a theorem about the series, not a call to a library.
- Every interval addition and subtraction uses directed rounding, stepping one ULP outward after each operation, so the interval is a genuine outer bound rather than a hopeful one.
- $\pi$ and $2\pi$ are enclosed between **rational bounds** proved by that same series. They are not rational, of course; the bounds are, and bounds are all the certificate ever needs. One that hardcodes a float for $\pi$ has just assumed part of what it is checking.
- The library's `math.asin` is still called — as an **oracle that is not believed**. It proposes where to look; a bracket with certainty in each direction decides. If the oracle lied, the search would widen rather than accept.

The result closes the domain with zero tolerances, zero exclusions, and no floating-point fact assumed anywhere.

![Four panels in a row, one per version of the certificate. v1: meshes without a Lipschitz bound, an LP with tolerances, one inequality merely sampled. v2: rational-directed and still refuted, because the 1e-12 tolerance thickened the tangent variety at the golden point. v3: adds the trio theorem the refuter supplied, still leaning on mpmath. v4: rational series with an alternating Lagrange remainder, and arcsine used as an oracle that is not believed.](/blog/proved-certified-swept-sampled-fig-2-en.png)

And the golden point itself, the one the tolerance had been papering over, ended up closed algebraically rather than numerically. The apparent double corner turns out to be a ghost — a third constraint empties it — and the real corner does not fit in the mural arrangement, because the lower arc overshoots by $1.4 \times 10^{-4}$. That margin is the whole of it: a ten-thousandth, at the one place where a `1e-12` band had been declaring victory. The correct witness stacks the small ring radially instead, and at the golden point every condition falls out as an exact identity in $\mathbb{Q}[\sqrt5]$, with margin $1/\varphi^3$.

## A wrong label is worse than a weak one

The four labels are only useful if they are honest, and the failure mode is not the weak label. It is the label that is too strong.

The same adversarial pass that killed my certificate also read a draft about square pans, rederived all the exact algebra — the quartic, the identity $b_\square(X) = X - 1$, the staircase polynomials — and confirmed it without exception. Then it found the thing I had not declared: a claim marked *proved* that was only proved for $\alpha \ge 1$. For $\alpha < 1$ the argument simply was not there. Nobody had noticed because the label said the question was settled, and a settled question does not get read twice.

A `sampled` label is not dangerous. Everyone knows what to do with it: rely on it lightly, or go and prove the thing. A `proved` label on a claim that holds in half its range is dangerous precisely because it is trusted, and because it silently props up everything downstream of it.

The other half of that honesty is admitting when you stopped. Some regions in this paper are declared **exhausted by cost** — the sweep ran for its budget, covered what it covered, and the paper says the region was not finished rather than pretending the covered part was the whole. A claim labelled as an honest declaration is worth more than the same claim labelled as proved, because a reader can plan around the first and will be misled by the second.

## Verification that improves the result

It is easy to read all this as damage control, so here is the other direction, which surprised me more.

One of the harder lemmas, about a derivative staying above 1 on a blocking boundary, came back *confirmed* — rederived from scratch by a different route, validated in exact rational arithmetic at thirty points, cross-checked against finite differences to twenty-nine decimal places, and hammered on adversarial meshes of about ten million points with no counterexample. Zero refutations.

But the verifier did not stop at confirming. It found that a hypothesis in my draft — that the parameter had to exceed some threshold — was **an artefact of my coordinates** rather than a real constraint, so the result holds everywhere. And it found that my closing constant was suboptimal: where I had closed the argument at the golden ratio, the right inequality closes it at the Tribonacci constant, which is strictly better and consistent with another result in the paper.

That is the part of verification nobody advertises. A pass whose only job is to attack the claim will sometimes hand back a stronger claim than the one you wrote, and four documents that had been carrying "modulo this lemma" caveats got to drop them.

## What this is worth outside a paper

I do not think the labels are a mathematics thing. I think mathematics is just where the mismatch is embarrassing enough to force the issue.

Your test suite, your type checker, your property-based tests and the one careful read-through you did on a Sunday are four different kinds of evidence, with different failure modes and different silent regions — and CI paints all of them the same green. A passing test is `sampled`: it says nothing happened at the inputs you chose. A property test with a generator is closer to `grid-swept`: it says nothing happened across a shape of inputs, and stays quiet between them. A type is nearer `box-certified`: it holds over a whole domain, for the properties it can express. And the read-through is the only one that is ever `proved`, on the rare occasions the argument is small enough to hold in a head.

Three things follow, and they are the ones I would actually use:

**Know where the tolerance is.** Every system has one — a timeout, a retry, a float comparison, a rounded threshold, an "approximately equal" in a test. It is invisible almost everywhere and decisive exactly at the boundary, which is the only place anyone ever asks a hard question. Ask which of your green checks are green because of it.

**Label the claim, not the system.** "The service is tested" is the sentence that hides everything. "This invariant is enforced by a type; that one by a test at three inputs; this third one we believe because it has not broken in a year" is the sentence that lets someone else decide what to lean on.

**Let something adversarial read it that did not write it.** Not a reviewer who will agree with your framing — one that gets the statement alone and is asked to break it. It refuted me three times on one lemma, and the fourth version is the only one I would put my name to. It also found the overclaimed label I had stopped seeing.

The last one is the reason my papers now carry an appendix nobody asked for, pairing each computational claim with the script behind it and a per-round record of every refutation and repair. It is the least glamorous part of the work and the only part that would let you catch me being wrong.

*The preprint is [here](https://arxiv.org/abs/2609.15554), the [code, certificates and verification reports are open](https://github.com/JaviMaligno/calamares), and the mathematics those certificates are about is in [the companion article](/en/blog/count-the-rings). A related habit, from a different angle: [the instrument fails in your favour](/en/blog/the-instrument-fails-in-your-favour).*
