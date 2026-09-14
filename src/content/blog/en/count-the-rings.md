---
title: "Count the Rings or Sear the Squid"
description: "Drop squid rings into a frying pan and two reasonable goals — fit as many as possible, or sear as much surface as possible — turn out to be different problems with different answers. Unless the sizes obey one condition, and then not only do the goals agree: where you put each ring stops mattering at all."
pubDate: 2026-09-22
tags: ["Mathematics", "Geometry", "Optimization", "Research"]
lang: en
translationKey: count-the-rings
heroImage: "/blog/count-the-rings.png"
repoUrl: https://github.com/JaviMaligno/calamares
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/XXXX.XXXXX"
linkedinSummary: |
  Drop squid rings into a frying pan and you have already made a decision, whether or not you noticed making it.

  You can fit as many rings as possible. Or you can sear as much squid as possible — the thing that actually cooks. They sound like the same instruction phrased twice. They are not, and the smallest case where they come apart is small enough to draw.

  A pan of radius 10, rings of width 1, sizes 9.0, 4.2, 4.2, 4.2. Lay out the three small ones and you get three rings and about 69.7 of contact area. Use the big one instead, with a small one dropped inside its hole, and you get two rings and about 76.7. More rings, less dinner. What makes it interesting is that a ring is an obstacle and a container at the same time, so the choice is real.

  Then the part that surprised me. If every ring is bigger than all the smaller ones put together, the disagreement disappears — one arrangement maximises every objective in a broad class at once. And something stronger: it stops mattering where you put each ring. Best fit, worst fit, random, adversarial — all identical. The proof never mentions the shape of the pan, so it holds for rectangular griddles and for spherical shells in three dimensions too.

  That guarantee is sharp in a way I did not expect: it holds for up to three rings and breaks at four. And no cleverer rule fixes it — there are two instances that are identical in every quantity a rule could observe at the decisive moment, and that require opposite decisions.

  The question underneath is one I keep meeting outside mathematics: what am I actually maximising, and is the proxy I optimise the same as the thing I want — or only inside the region I happen to be standing in?
---

Drop a handful of squid rings into a frying pan and you have already made a decision, whether or not you noticed making it.

You can lay them out so that as many rings as possible are in the pan. Or you can lay them out so that as much squid as possible is touching hot metal, which is the thing that actually cooks. Those sound like the same instruction phrased twice. They are not, and the gap between them is wide enough to prove theorems in.

What makes it a real problem rather than a word game is that a ring has a hole. A small enough ring drops inside the hole of a larger one and sits flat on the pan, touching metal exactly as much as it would have on its own. So the rings are not competing for area the way coins on a table compete: a big ring is an obstacle and a container at the same time.

That is the whole setup. It is also, once you strip the squid off it, a selection-flavoured relative of the Recursive Circle Packing Problem, introduced by Pedroso, Cunha and Tavares (*International Transactions in Operational Research*, 2016) to model telescoping tubes in shipping containers and later solved exactly by Gleixner, Maher, Müller and Pedroso. That literature is algorithmic: it asks how to pack a fixed set of rings into as few containers as possible, and its methods are heuristics — procedures that propose placements without guaranteeing that the placement mattered. I wanted the structural questions instead. Which objective does the obvious greedy algorithm *provably* optimise? When is the choice of *where* to put each ring provably irrelevant? And which condition on the sizes decides the answer?

The preprint is [*Greedy Packing of Nested Rings*](https://arxiv.org/abs/XXXX.XXXXX); the [code, figures and Lean certificates are open](https://github.com/JaviMaligno/calamares). This is the readable version of what is in it.

## Two goals that sound like one goal

Fix a width `w` — how thick the squid wall is — and say a ring of outer radius `r` has a hole of radius `r - w`. The area touching the pan is the annulus:

```
a(r) = π · ( r² − max(0, r−w)² )
```

which for thin rings is close to `2πw·r`. So *sear* — total contact area — behaves almost like the sum of the radii, minus a fixed penalty `πw²` for every ring you use. *Count* is just the number of rings.

That "minus a fixed penalty per ring" is the seed of the whole disagreement. Adding a ring always adds to the count. It does not always add enough area to be worth the space it occupies, because the space it occupies might have gone to something bigger.

Say the two objectives **diverge** on an instance when the area-optimal arrangement uses strictly fewer rings than the count-optimal one. The question is when that happens, and it turns out you need a surprising amount of structure before it can happen at all.

With two rings, never. If both fit together, take both: area strictly increases when you add a ring, so the full set wins on both counts. If they don't fit together, every feasible arrangement has at most one ring, and the area optimum already achieves that count. Two rings cannot disagree with themselves.

With three, it can happen — but only in a degenerate way. Take a pan of radius 10 with very thick rings, `w = 9/2`, and radii `{8, 101/20, 99/20}`. The two small rings are exactly diametral: `101/20 + 99/20 = 10`, so they fit side by side across the pan and nothing else fits with them. The big ring's hole has radius `7/2`, too small for either of them, so nothing nests. And the areas are

```
a(8)      = 207π/4
a(101/20) + a(99/20) = 198π/4
```

The single big ring sears more than both small ones together. Count says two, area says one. But look at why: the rings are so thick that no hole can hold anything, and the problem has quietly collapsed into ordinary circle packing. The nesting — the thing that makes this squid and not coins — has been switched off.

## The smallest disagreement that is really about rings

Turn the width back down so nesting is live again, and the disagreement almost disappears. Almost. The smallest instance where it survives *with the holes doing work* needs four rings:

A pan of radius 10, width 1, and radii `{9.0, 4.2, 4.2, 4.2}`.

Play it both ways. If you want rings on the pan, take the three 4.2s: they fit side by side, `N = 3`, and they sear about 69.7. If you want squid cooked, take the 9.0 and drop one 4.2 into its hole: only `N = 2`, but about 76.7 of contact area. The big ring is worth more than two small ones, and using it costs you the room for them.

![The minimal divergence instance: a pan of radius 10 holding rings of width 1. On the left, the area optimum — the radius-9 ring with one 4.2 ring nested inside its hole, two rings and about 76.7 units of contact area. On the right, the cardinality optimum — three separate 4.2 rings side by side in the pan, three rings but only about 69.7 units of area.](/blog/count-the-rings-fig-1-en.png)

Three rings or more dinner. Not both.

The mechanism is worth naming, because it is narrow. It needs small rings that fit `k` times in the pan but at most `k − 2` times in the big ring's hole. If they fit `k − 1` times in the hole, the two objectives tie and there is nothing to argue about. That off-by-one is the entire divergence in the nesting regime, which is why the minimal instance has four rings and not three.

## Where the disagreement lives

Once you know it exists, you can map it. Fix the width at 1 and the pan at radius 10, take the family "one large ring plus as many equal small rings of radius `s` as you like", and sweep.

![Phase diagram of the divergence band for one large ring plus equal small rings of radius s, at width 1 in a pan of radius 10. The band forms a staircase: each step is set by the proved optimal threshold for packing n equal circles in a disk, and the band's upper edge is exactly the three-circle threshold, 0.4641 times the pan radius.](/blog/count-the-rings-fig-2-en.png)

The divergence region is a staircase, and the steps are not arbitrary — each one sits at a proved optimal threshold for packing `n` equal circles in a disk, results that go back to Pirl and Melissen. The band's upper edge is exactly the three-circle threshold, `0.4641 R`. Above that, small rings are big enough that three of them no longer fit and the arithmetic stops working.

One honest note, in the same breath as the claim: for the thick-ring family of the previous section, the onset of three-ring divergence sits near `w/R ≈ 0.26`. That number is **swept, not proved**. I sampled it; I did not establish it. The paper says so at that sentence rather than in a footnote, because "I swept a grid and this is where it turned" and "I proved this is where it turns" are not the same currency, and a reader who cannot tell them apart will lean on the wrong one.

## One condition, and the problem stops being interesting

Now the other half, which surprised me more than the divergence did.

Call the radii **superincreasing** when every ring is bigger than all the smaller ones put together: `rᵢ > Σ_{j>i} rⱼ`. It is a strong condition — the sizes have to fall away fast, each one dominating the entire tail — but it is not exotic. It is the same condition that makes greedy work for coin systems, and the one-dimensional ancestor of this result is a 1987 theorem of Coffman, Garey and Johnson: for bin packing with *divisible* item sizes, First Fit Decreasing is optimal.

Under superincreasing radii, the descending greedy — take the biggest ring, place it, move on — produces the **lexicographically maximal** feasible set. And that has a consequence bigger than it first looks: lex-max means it simultaneously maximises

```
Σ v(rᵢ)
```

for *every* positive, strictly increasing, superadditive `v`. Contact area is one such `v`. So is the sum of radii, and the sum of perimeters. All of them at once, by the same arrangement.

Which means that in this regime the disagreement I spent the first half of this article building is simply gone. Sear and count-by-value stop being different questions, because one set answers all of them.

Count itself, note, is *not* rescued, and the reason is precise: cardinality is `v ≡ 1`, which is not superadditive, so the dominance argument simply does not apply to it. There is an explicit counterexample — a pan of radius 10, width 4.8, radii `{9.95, 5.0, 4.3, 0.6}`. The greedy takes `{9.95, 5.0}`: two rings, optimal area, and no step even offers a choice of container, so every placement rule agrees. Meanwhile `{5.0, 4.3, 0.6}` packs in a row in the pan for three. The frontier is exactly superadditivity, and cardinality sits on the wrong side of it. That is the honest shape of the result — not "greedy is optimal", but "greedy is optimal for every objective in a class, and here is the class, and here is what falls out of it".

## And then where you put things stops mattering

This is the part I did not expect when I started.

Under the same condition, you do not merely have *an* optimal greedy. Every descending greedy is optimal, with an **arbitrary** rule for choosing which container to drop each ring into. Best fit — the tightest container that will take it. Worst fit — the roomiest. Random. Adversarial. They all place exactly the same lex-max set.

The intuition worth holding onto is not "the algorithm is clever". It is that under superincreasing radii the decision you agonise over has no downstream consequence: whatever you do with the current ring, the rings still to come are collectively smaller than it, and the exchange argument can always rearrange them around your choice.

And because that argument only ever looks inside the ball vacated by a moved ring, it never mentions what the pan looks like. The theorem is stated and proved for an arbitrary compact container `K ⊂ ℝᵈ`, with rings read as spherical shells. A round pan, a rectangular griddle, tubes and spherical shells nested in three dimensions — the original shipping-container setting — are all covered verbatim, not by extension. I do not know of a comparable placement-independence guarantee elsewhere in the circle-packing literature.

The computational corroboration is the kind I like, because it is a genuine attempt to break the claim: 100 random superincreasing instances, run under best fit, worst fit and random placement. All three produced optimal — and therefore identical — outcomes, without exception.

## Three rings, and then four

A theorem is only as interesting as its edge, so: how much of this survives without the condition?

On a disk pan, with *arbitrary* radii and no superincreasing hypothesis at all, every descending greedy on **at most three rings** still lands on the lex-max set. Three rings are simply not enough room to make a bad choice.

Four are.

![The four-ring counterexample: a pan of radius 15 with rings of width 0.3 and radii 10, 5, 4.9 and 4.8. All four fit — the 10 and the 5 exactly tangent in the pan, the 4.9 and 4.8 exactly filling the hole of the 10 — but best fit nests the 5 inside the 10, which forces the 4.9 into the pan and leaves the 4.8 with nowhere to go.](/blog/count-the-rings-fig-3-en.png)

Pan of radius 15, width 0.3, radii `{10, 5, 4.9, 4.8}`. All four rings fit, and the arrangement that achieves it is tight in both places at once: the 10 and the 5 are exactly tangent in the pan (`10 + 5 = 15`), and the 4.9 and 4.8 exactly fill the hole of the 10 (`4.9 + 4.8 = 9.7`, the hole radius).

Now run best fit. Facing the 5, it prefers the snug container — the hole of the 10 — and nests it. That single reasonable-looking decision forces the 4.9 out into the pan, and once the 4.9 is in the pan, the 4.8 has nowhere left: not the pan, not the hole. Best fit gets three rings. Worst fit gets four.

So placement obliviousness is sharp. It holds unconditionally at three and fails at four.

## The twins

You might reasonably conclude that the fix is a better rule. Best fit is naive; write a smarter one.

You can't, and the reason is the sharpest result in the paper.

Take a pan of radius 15, a 10 and a 5, width 0.505 — so the hole of the 10 has radius 9.495 — and these two instances:

```
I₁ = {10, 5, 4.99, 4.50}
I₂ = {10, 5, 4.76, 4.74}
```

In `I₁` the two small rings sum to 9.49, which fits in the hole. So the 5 belongs in the pan, and worst fit gets it right while best fit fails. In `I₂` the two small rings sum to 9.50, which does *not* fit in the hole. So the 5 belongs in the hole, and now best fit gets it right while worst fit fails.

Opposite decisions. And here is the point: **at the moment of decision, the two instances are indistinguishable.** The containers are the same, their capacities are the same, the occupants are the same, the incoming ring is the same, `R` and `w` are the same. Every quantity a placement rule could look at, reading the state in front of it, is identical — and the correct move is different.

The consequence is not "best fit is bad". It is that no deterministic rule which is a function of the observable state can be optimal on all instances, and every randomised rule fails some instance with probability at least one half. The information required to decide is not present in the state. It is in the rings you have not looked at yet.

## The constant that wasn't

There is one more thread, and it ends in the nicest wrong guess I have had in a while.

If superincreasing radii give you all of this and violating them costs you all of it, there should be a threshold in between. Measure the violation by how badly the worst ring is beaten by its own tail:

```
ρ = maxᵢ ( Σ_{j>i} rⱼ ) / rᵢ
```

so `ρ ≤ 1` is exactly the superincreasing condition. In the *additive* relaxation of the model — where siblings are feasible precisely when their radii sum to at most the capacity, geometry stripped out — the threshold is exactly `ρ = 1`. Clean, universal, and the reason the additive model is the right place to isolate the combinatorial half of the difficulty.

The geometric model is where it gets interesting. The rigid four-ring family of counterexamples has an infimum, and that infimum is exactly the **Tribonacci constant** `T ≈ 1.83929` — the analogue of the golden ratio for the recurrence that sums the previous *three* terms. It is proved, with no tangency idealisation smuggled in. Given that three-term structure and a problem about rings inside rings inside rings, the natural conjecture writes itself: `T` is the global threshold.

It isn't. There is an explicit family — pan of radius `φ + 1`, radii `{φ, 1, φ/2 + 2ε, φ/2 + ε}` — that breaks placement obliviousness at `ρ = φ + 3ε`, for every small `ε > 0`. Since `φ ≈ 1.618 < 1.839 ≈ T`, that proves the geometric threshold `τ` satisfies

```
τ ≤ φ < T
```

and the Tribonacci conjecture is dead. The golden ratio gets there first.

What I would love to tell you is that `τ = φ`. I can't. The matching lower bound `τ ≥ φ` is proved for pair profiles and outside an explicit heavy region, and remains a conjecture in general. So the golden value is a theorem in one direction and an open problem in the other, with Tribonacci demoted from "the threshold" to "the exact floor of the rigid nested family" — still a sharp constant, just not the one I expected it to be.

One boundary worth stating plainly, since I made a point of the theorems holding in every dimension: **none of this sharpness does.** The `n = 4` transition, the twins, the Tribonacci floor and the golden family are all disk results. Their analogues for square pans and in `ℝ³` are open — the first thing I want to know is what replaces Tribonacci when the Descartes-style pocket becomes a corner. The generality lives in the positive half of the paper. The edge has only ever been measured in a frying pan.

## What I take from this

Two things, and neither is about squid.

The first is that "what am I actually maximising?" is not a philosophical warm-up question. It is the question that decides the answer. Count and sear look interchangeable until you write them down, and then they pull apart in a region you can draw. If a system optimises the proxy you gave it rather than the thing you wanted, the failure is often not that the optimiser is bad — it is that you handed it the wrong `v` and the two only coincide outside the band you happen to be in.

The second is more cheerful. There exist regimes where the hard part evaporates: where every objective in a broad class agrees, where the obvious algorithm is provably right, and where the decision you would have spent your time on has no consequence at all. Knowing whether you are inside one is worth more than any amount of cleverness spent on the decision itself. Here the test fits on one line — is every ring bigger than the sum of the rest? — and the reward for passing it is that you get to stop thinking.

This is a long way from the algebra I spent my [doctorate on](/en/publications), and it started, genuinely, in a frying pan. The [preprint](https://arxiv.org/abs/XXXX.XXXXX) has the proofs; the [repository](https://github.com/JaviMaligno/calamares) has the code, the figures and the Lean certificates for the exact identities.
