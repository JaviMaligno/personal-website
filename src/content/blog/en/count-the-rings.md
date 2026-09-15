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
    url: "https://arxiv.org/abs/2609.15554"
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

## The idealisation, stated up front

Real squid rings do something the model forbids: they ride up on each other. A ring resting partly on top of another is not gone — it still sears everywhere outside the overlap — and because the rings have thickness, that pose is not a measure-zero accident. It is what actually happens in a crowded pan.

![Two frying pans seen from above. On the left, the model: two rings side by side at exact tangency, the closest the rules ever allow them. On the right, the same two rings overlapping, one riding partly on top of the other, with the two crossing regions marked in red — the only places where contact with the pan is lost.](/blog/count-the-rings-fig-6-en.png)

The model in this article is the rigid one: siblings in a container must be packable as balls with disjoint interiors, so nothing ever rides on anything. That is a real idealisation and it is worth naming before the theorems rather than after, because every result below is a result about the rigid model.

The flexible version is a named open direction rather than an oversight. Let $\delta$ be the width of the lifted ramp a bent ring makes around each overlap. Then $\delta = 0$ — contact area equals the annulus minus the overlapped region — defines a continuous relaxation in which partial placements trade contact for cardinality, and $\delta > 0$ penalises overlaps by a dead band proportional to the overlap perimeter. Neither is solved here.

Stripped of the squid, the rigid problem is a selection-flavoured relative of the Recursive Circle Packing Problem, introduced by Pedroso, Cunha and Tavares (*International Transactions in Operational Research*, 2016) to model telescoping tubes in shipping containers and later solved exactly by Gleixner, Maher, Müller and Pedroso. That literature is algorithmic: it asks how to pack a fixed set of rings into as few containers as possible, and its methods are heuristics — procedures that propose placements without guaranteeing that the placement mattered. I wanted the structural questions instead. Which objective does the obvious greedy algorithm *provably* optimise? When is the choice of *where* to put each ring provably irrelevant? And which condition on the sizes decides the answer?

The preprint is [*Greedy Packing of Nested Rings*](https://arxiv.org/abs/2609.15554); the [code, figures and Lean certificates are open](https://github.com/JaviMaligno/calamares). This is the readable version of what is in it.

## Two goals that sound like one goal

Fix a width $w$ — how thick the squid wall is — and say a ring of outer radius $r$ has a hole of radius $r - w$. The area touching the pan is the annulus:

$$
a(r) = \pi\left(r^2 - \max(0,\ r-w)^2\right)
$$

which for thin rings is close to $2\pi w r$. So *sear* — total contact area — behaves almost like the sum of the radii, minus a fixed penalty $\pi w^2$ for every ring you use. *Count* is just the number of rings.

That penalty per ring is the seed of the whole disagreement. Adding a ring always adds to the count. It does not always add enough area to be worth the space it occupies, because the space it occupies might have gone to something bigger.

Say the two objectives **diverge** on an instance when the area-optimal arrangement uses strictly fewer rings than the count-optimal one. It turns out you need a surprising amount of structure before that can happen at all.

With two rings, never. If both fit together, take both: area strictly increases when you add a ring, so the full set wins on both counts. If they don't fit together, every feasible arrangement has at most one ring, and the area optimum already achieves that count. Two rings cannot disagree with themselves.

## Three rings can disagree, for the wrong reason

With three it can happen, but only in a degenerate way. Take a pan of radius $R = 10$ with very thick rings, $w = 9/2 = 4.5$, and radii

$$
\{8,\ \tfrac{101}{20},\ \tfrac{99}{20}\} = \{8,\ 5.05,\ 4.95\}
$$

The two small rings are exactly diametral — $5.05 + 4.95 = 10$ — so they fit side by side across the pan and nothing else fits with them. The big ring's hole has radius $8 - 4.5 = 3.5$, too small for either of them, so nothing nests. And the areas compare as

$$
a(8) = \tfrac{207}{4}\pi \;>\; \tfrac{198}{4}\pi = a(5.05) + a(4.95)
$$

![Two pans of radius 10 with rings of width 4.5. On the left, a single ring of radius 8, whose contact area is 207π/4, about 162.6. On the right, two rings of radii 5.05 and 4.95 exactly touching each other and the pan wall, two rings but only 198π/4 of area, about 155.5.](/blog/count-the-rings-fig-0-en.png)

The single big ring sears more than both small ones together: count says two, area says one. But look at why. The rings are so thick that no hole can hold anything, and the problem has quietly collapsed into ordinary circle packing. The nesting — the thing that makes this squid and not coins — has been switched off.

## The smallest disagreement that is really about rings

Turn the width back down so nesting is live again, and the disagreement almost disappears. Almost. The smallest instance where it survives *with the holes doing work* needs four rings: a pan of radius $10$, width $1$, and radii $\{9.0,\ 4.2,\ 4.2,\ 4.2\}$.

Play it both ways. If you want rings on the pan, take the three 4.2s: they fit side by side, $N = 3$, and they sear about $69.7$. If you want squid cooked, take the 9.0 and drop one 4.2 into its hole: only $N = 2$, but about $76.7$ of contact area.

![The minimal divergence instance: a pan of radius 10 holding rings of width 1. On the left, the area optimum — the radius-9 ring with one 4.2 ring nested inside its hole, two rings and about 76.7 units of contact area. On the right, the cardinality optimum — three separate 4.2 rings side by side in the pan, three rings but only about 69.7 units of area.](/blog/count-the-rings-fig-1-en.png)

Three rings or more dinner. Not both.

The mechanism is worth naming, because it is narrow. It needs small rings that fit $k$ times in the pan but at most $k-2$ times in the big ring's hole. If they fit $k-1$ times in the hole, the two objectives tie and there is nothing to argue about. That off-by-one is the entire divergence in the nesting regime, which is why the minimal instance has four rings and not three.

## Where the disagreement lives

Once you know it exists, you can map it. Fix the width at $1$ and the pan at radius $10$, take the family "one large ring of radius $b$ plus as many equal small rings of radius $s$ as you like", and sweep.

![Phase diagram of the divergence band for one large ring plus equal small rings of radius s, at width 1 in a pan of radius 10. The band forms a staircase: each step is set by the proved optimal threshold for packing n equal circles in a disk, and the band's upper edge is exactly the three-circle threshold, 0.4641 times the pan radius. The worked example at b = 9.0, s = 4.2 is marked with a star inside the band.](/blog/count-the-rings-fig-2-en.png)

The divergence region is a staircase, and the steps are not arbitrary — each one sits at a proved optimal threshold for packing $n$ equal circles in a disk, results that go back to Pirl and Melissen. The band's upper edge is exactly the three-circle threshold, $0.4641\,R$. Above that, small rings are big enough that three of them no longer fit and the arithmetic stops working.

One honest note, in the same breath as the claim: for the thick-ring family of the previous section, the onset of three-ring divergence sits near $w/R \approx 0.26$. That number is **swept, not proved**. I sampled it; I did not establish it. The paper says so at that sentence rather than in a footnote, because "I swept a grid and this is where it turned" and "I proved this is where it turns" are not the same currency, and a reader who cannot tell them apart will lean on the wrong one.

## One condition, and the problem stops being interesting

Now the other half, which surprised me more than the divergence did.

Call the radii **superincreasing** when every ring is bigger than all the smaller ones put together: $r_i > \sum_{j>i} r_j$ for all $i$. It is a strong condition — the sizes have to fall away fast, each one dominating the entire tail — but it is not exotic. It is the same condition that makes greedy work for coin systems, and the one-dimensional ancestor of this result is a 1987 theorem of Coffman, Garey and Johnson: for bin packing with *divisible* item sizes, First Fit Decreasing is optimal.

Under superincreasing radii, the descending greedy — take the biggest ring, place it, move on — produces the **lexicographically maximal** feasible set. And that has a consequence bigger than it first looks: lex-max means it simultaneously maximises

$$
\sum_{i \in S} v(r_i)
$$

for *every* positive, strictly increasing, superadditive $v$. Contact area is one such $v$. So is the sum of radii, and the sum of perimeters. All of them at once, by the same arrangement. In this regime the disagreement I spent the first half of this article building is simply gone.

Count itself is *not* rescued, and the reason is precise: cardinality is $v \equiv 1$, which is not superadditive, so the dominance argument does not apply to it at all.

![A pan of radius 10 with rings of width 4.8 and superincreasing radii 9.95, 5.0, 4.3 and 0.6. On the left, what the greedy does: the 9.95 with the 5.0 nested inside its hole, two rings, which is the best possible area. On the right, three rings that do fit — 5.0, 4.3 and 0.6 in a row across the pan — showing the greedy is beaten on count even though the radii are superincreasing.](/blog/count-the-rings-fig-5-en.png)

The counterexample is a pan of radius $10$, width $4.8$, radii $\{9.95,\ 5.0,\ 4.3,\ 0.6\}$. The greedy takes $\{9.95,\ 5.0\}$: two rings, optimal area, and no step even offers a choice of container, so every placement rule agrees. Meanwhile $\{5.0,\ 4.3,\ 0.6\}$ packs in a row in the pan for three. The frontier is exactly superadditivity, and cardinality sits on the wrong side of it.

## And then where you put things stops mattering

This is the part I did not expect when I started.

Under the same condition, you do not merely have *an* optimal greedy. Every descending greedy is optimal, with an **arbitrary** rule for choosing which container to drop each ring into. Best fit — the tightest container that will take it. Worst fit — the roomiest. Random. Adversarial. They all place exactly the same lex-max set.

The intuition worth holding onto is not "the algorithm is clever". It is that under superincreasing radii the decision you agonise over has no downstream consequence: whatever you do with the current ring, the rings still to come are collectively smaller than it, and the exchange argument can always rearrange them around your choice.

And because that argument only ever looks inside the ball vacated by a moved ring, it never mentions what the pan looks like. The theorem is stated and proved for an arbitrary compact container $K \subset \mathbb{R}^d$, with rings read as spherical shells. A round pan, a rectangular griddle, tubes and spherical shells nested in three dimensions — the original shipping-container setting — are all covered verbatim, not by extension. I do not know of a comparable placement-independence guarantee elsewhere in the circle-packing literature.

The computational corroboration is the kind I like, because it is a genuine attempt to break the claim: 100 random superincreasing instances, run under best fit, worst fit and random placement. All three produced optimal — and therefore identical — outcomes, without exception.

## Three rings, and then four

A theorem is only as interesting as its edge, so: how much of this survives without the condition?

With *arbitrary* radii and no superincreasing hypothesis at all, every descending greedy on **at most three rings** still lands on the lex-max set. Three rings are simply not enough room to make a bad choice.

Four are.

![The four-ring counterexample: a pan of radius 15 with rings of width 0.3 and radii 10, 5, 4.9 and 4.8. On the right, worst fit places all four — the 10 and the 5 exactly tangent in the pan, the 4.9 and 4.8 exactly filling the hole of the 10. On the left, best fit nests the 5 inside the 10, which forces the 4.9 into the pan and leaves the 4.8 with nowhere to go, marked with a red cross outside the pan.](/blog/count-the-rings-fig-3-en.png)

Pan of radius $15$, width $0.3$, radii $\{10,\ 5,\ 4.9,\ 4.8\}$. All four rings fit, and the arrangement that achieves it is tight in both places at once: the 10 and the 5 are exactly tangent in the pan ($10 + 5 = 15$), and the 4.9 and 4.8 exactly fill the hole of the 10 ($4.9 + 4.8 = 9.7$, the hole radius).

Now run best fit. Facing the 5, it prefers the snug container — the hole of the 10 — and nests it. That single reasonable-looking decision forces the 4.9 out into the pan, and once the 4.9 is in the pan, the 4.8 has nowhere left. Best fit gets three rings. Worst fit gets four.

So placement obliviousness is sharp. It holds unconditionally at three and fails at four.

## The twins

You might reasonably conclude that the fix is a better rule. Best fit is naive; write a smarter one.

You can't, and the reason is the sharpest result in the paper.

Take a pan of radius $15$, a 10 and a 5, width $w = 0.505$ — so the hole of the 10 has radius $9.495$ — and these two instances:

$$
I_1 = \{10,\ 5,\ 4.99,\ 4.50\}, \qquad I_2 = \{10,\ 5,\ 4.76,\ 4.74\}
$$

In $I_1$ the two small rings sum to $9.49$, which fits in the hole. So the 5 belongs in the pan, and worst fit gets it right while best fit fails. In $I_2$ they sum to $9.50$, which does *not* fit in the hole. So the 5 belongs in the hole, and now best fit gets it right while worst fit fails.

![The twin instances. Two identical pictures of a pan of radius 15 containing the ring of radius 10, with the ring of radius 5 waiting at the rim to be placed. In the first, the remaining rings sum to 9.49, which fits the 9.495 hole, so the 5 belongs in the pan. In the second they sum to 9.50, which does not fit, so the 5 belongs in the hole. At the moment of decision the two pictures are the same.](/blog/count-the-rings-fig-4-en.png)

Opposite decisions. And here is the point: **at the moment of decision, the two instances are indistinguishable.** The containers are the same, their capacities are the same, the occupants are the same, the incoming ring is the same, $R$ and $w$ are the same. Every quantity a placement rule could look at, reading the state in front of it, is identical — and the correct move is different.

The consequence is not "best fit is bad". It is that no deterministic rule which is a function of the observable state can be optimal on all instances, and every randomised rule fails some instance with probability at least $1/2$. The information required to decide is not in the state. It is in the rings you have not looked at yet.

## The constant that wasn't

There is one more thread, and it ends in the nicest wrong guess I have had in a while.

If superincreasing radii give you all of this and violating them costs you all of it, there should be a threshold in between. Measure the violation by how badly the worst ring is beaten by its own tail:

$$
\rho = \max_i \frac{\sum_{j>i} r_j}{r_i}
$$

so $\rho \le 1$ is exactly the superincreasing condition. In the *additive* relaxation — where siblings are feasible precisely when their radii sum to at most the capacity, geometry stripped out — the threshold is exactly $\rho = 1$. Clean, universal, and the reason the additive model is the right place to isolate the combinatorial half of the difficulty.

The geometric model is where it gets interesting. The rigid four-ring family of counterexamples has an infimum, and that infimum is exactly the [Tribonacci constant](https://oeis.org/A058265) $T \approx 1.83929$ — the analogue of the golden ratio for the recurrence that sums the previous *three* terms. It is proved, with no tangency idealisation smuggled in. Given that three-term structure and a problem about rings inside rings inside rings, the natural conjecture writes itself: $T$ is the global threshold.

It isn't. There is an explicit family — pan of radius $\varphi + 1$, radii $\{\varphi,\ 1,\ \varphi/2 + 2\varepsilon,\ \varphi/2 + \varepsilon\}$ — that breaks placement obliviousness at $\rho = \varphi + 3\varepsilon$, for every small $\varepsilon > 0$. Since $\varphi \approx 1.618 < 1.839 \approx T$, that proves the geometric threshold $\tau$ satisfies

$$
\tau \le \varphi < T
$$

and the Tribonacci conjecture is dead. The golden ratio gets there first.

What I would love to tell you is that $\tau = \varphi$. I can't, and I want to be exact about where the gap is, because it is the obvious thing to assume once you have seen the upper bound. The matching lower bound $\tau \ge \varphi$ is proved for pair profiles, and proved outside an explicit heavy region — but not in general. So the golden value is a theorem in one direction and an open problem in the other, and Tribonacci is demoted from "the threshold" to "the exact floor of the rigid nested family": still a sharp constant, just not the one I expected it to be.

## What the edge looks like outside the frying pan

Everything above about the *edge* — the transition at four, the twins, the floor, the golden family — was originally a statement about a round pan in the plane. The positive half never needed the shape; the sharp half had only ever been measured there. Which of the two the boundary really belongs to is a question I could not answer when the preprint went out, so I went and asked it.

What follows is written and checked but **not yet public**: it is going into the second version of the preprint, and it has not been through independent adversarial review the way the v1 results were. Read it as a set of claims with proofs attached, not as settled literature.

In balls of any dimension, nothing moves. The three-ring guarantee holds for an arbitrary compact container in any dimension — the v1 proof leaned on $r_1 + r_2 \le R$, but what it actually needs is that shrinking a ball while keeping its centre preserves feasibility, which is true for any container, a square included. The failure at four survives too, with the *same* instance $\{10,\ 5,\ 4.9,\ 4.8\}$, and so do the twins, and so does the Tribonacci floor. The reason is a reduction lemma worth stating on its own: balls of radii $a_1, \dots, a_k$ fit as siblings inside a ball of radius $R$ in $\mathbb{R}^d$ if and only if they fit in $\mathbb{R}^{k-1}$. Sibling queries of three or fewer rings therefore have identical answers in every dimension $d \ge 2$, and every result whose proof only ever asks such questions comes along for free.

The first query that can tell dimension 2 from dimension 3 needs **four** pieces, and there is an explicit one: radii $\{441,\ 440,\ 439,\ 438\}/1000$ in a ball of radius $1$, which fits in 3D with centres at the four points $(\pm a, \pm a, \pm a)$ of even sign, $a = 8/25$ — the margins are exact rationals — and does not fit in the plane.

Square pans are where the constant genuinely changes. There is now an explicit four-ring counterexample in a square with $\rho = 337/200 = 1.685$, with the geometric exclusion of the offending trio kernel-checked in Lean for all coordinates rather than sampled; there are twin instances in a square, killing state-based rules there too; and the bound has been pushed down to

$$
1 \le \tau_{\square} \le Y \approx 1.684487745872346
$$

where $Y$ is the positive root of $(17 + 10\sqrt2)Y^2 + (72 + 16\sqrt2)Y - (112 + 96\sqrt2) = 0$. So the disk and the square do not share a threshold: $\varphi \approx 1.618$ against something near $1.684$. The shape of the pan changes the constant, and the corner is what changes it.

For balls the honest statement is weaker than I would like: $1 \le \tau_d \le \varphi$ for every $d \ge 2$, and that is all. It does not follow that $\tau_d = \tau_2$, and it does not follow that $\tau_d = \varphi$ — counterexamples with four or more siblings need not reduce to a plane.

## What I take from this

Two things, and neither is about squid.

The first is that "what am I actually maximising?" is not a philosophical warm-up question. It is the question that decides the answer. Count and sear look interchangeable until you write them down, and then they pull apart in a region you can draw. If a system optimises the proxy you gave it rather than the thing you wanted, the failure is often not that the optimiser is bad — it is that you handed it the wrong $v$, and the two only coincide outside the band you happen to be in.

The second is more cheerful. There exist regimes where the hard part evaporates: where every objective in a broad class agrees, where the obvious algorithm is provably right, and where the decision you would have spent your time on has no consequence at all. Knowing whether you are inside one is worth more than any amount of cleverness spent on the decision itself. Here the test fits on one line — is every ring bigger than the sum of the rest? — and the reward for passing it is that you get to stop thinking.

This is a long way from the algebra I spent my [doctorate on](/en/publications), and it started, genuinely, in a frying pan. The [preprint](https://arxiv.org/abs/2609.15554) has the proofs; the [repository](https://github.com/JaviMaligno/calamares) has the code, the figures and the Lean certificates for the exact identities.
