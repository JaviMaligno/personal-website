# X thread — "Count the Rings or Sear the Squid"

Manual thread (there is no X automation in this repo). Post on publication day,
after the arXiv ID exists. **Replace `XXXX.XXXXX` before posting** — it appears
in tweet 10.

Each tweet is kept under 280 characters so it works on a free account. Post the
first on its own, then each following one as a reply to the previous.

Tweet 3 is the one to attach an image to: `public/blog/count-the-rings-fig-1-en.png`
(the two arrangements side by side). Tweet 8 can carry
`public/blog/count-the-rings-fig-3-en.png`.

---

**1/**

```
Drop squid rings into a frying pan and you've already made a decision, whether you noticed or not.

Fit as many rings as possible — or sear as much squid as possible.

Those are not the same instruction. The gap between them is wide enough to prove theorems in. 🧵
```

**2/**

```
What makes it a real problem: a ring has a hole.

A small enough ring drops inside a bigger one and still sits flat on the pan, searing exactly as much as it would alone.

So a big ring is an obstacle and a container at the same time.
```

**3/**

```
The smallest case where the two goals disagree.

Pan of radius 10, rings of width 1, sizes 9.0, 4.2, 4.2, 4.2.

Three small rings: 3 rings, 69.7 of contact area.
The big one with a small one nested inside: 2 rings, 76.7.

More rings, less dinner.
```

**4/**

```
It takes real structure for that to happen at all.

Two rings can never disagree.
Three can, but only when they're so thick no hole can hold anything — and then it isn't about nesting any more.

The mechanism that needs holes needs four rings. That's the minimum.
```

**5/**

```
Now the part that surprised me.

Call the sizes superincreasing when every ring is bigger than ALL the smaller ones put together.

Under that condition the descending greedy doesn't just optimise one goal. It maximises every positive, increasing, superadditive objective at once.
```

**6/**

```
And something stronger.

It stops mattering where you put each ring.

Best fit, worst fit, random, adversarial — every rule places exactly the same set.

The decision you'd agonise over has no downstream consequence.
```

**7/**

```
The proof never mentions the shape of the pan.

It only ever looks inside the ball vacated by a moved ring — so it holds for an arbitrary container in any dimension.

Rectangular griddles. Spherical shells nested in 3D. Covered verbatim, not by extension.
```

**8/**

```
That guarantee is sharp, and sharper than I expected: it holds for up to three rings and fails at four.

Pan 15, width 0.3, sizes 10, 5, 4.9, 4.8. All four fit.

Best fit nests the 5 — which looks tidy, forces the 4.9 out, and strands the 4.8. Worst fit places all four.
```

**9/**

```
"So write a smarter rule."

You can't. Two instances exist where containers, capacities, occupants, incoming ring, R and w are ALL identical at the decisive step — and the correct move is opposite.

The information isn't in the state. It's in the rings you haven't looked at.
```

**10/**

```
There's also a conjecture that died: the natural threshold looked like the Tribonacci constant (1.839…), and an explicit golden family breaks it earlier, at φ ≈ 1.618.

Proved in one direction. The matching lower bound is still open.
```

**11/**

```
Since the preprint went out I checked whether the sharp half is really about round pans.

In balls of any dimension, nothing moves — same counterexample, same twins, same floor.

In a SQUARE the constant changes: the bound there is ≈ 1.6845, not φ. The corner is what changes it.
```

**12/**

```
Preprint: https://arxiv.org/abs/XXXX.XXXXX
Code, figures and Lean certificates: https://github.com/JaviMaligno/calamares

Full write-up, with the phase diagram and the twins: https://www.javieraguilar.ai/en/blog/count-the-rings
```
