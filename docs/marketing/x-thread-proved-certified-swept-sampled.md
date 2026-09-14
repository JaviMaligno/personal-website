# X thread — "Proved, Certified, Swept, Sampled"

Manual thread (there is no X automation in this repo). Post on publication day,
after the arXiv ID exists. **Replace `XXXX.XXXXX` before posting** — it appears
in tweet 11.

Each tweet is kept under 280 characters so it works on a free account. Post the
first on its own, then each following one as a reply to the previous.

Attach `public/blog/proved-certified-swept-sampled-fig-1-en.png` (the tolerance
swallowing the tangency) to tweet 4, and the hero
`public/blog/proved-certified-swept-sampled.png` (the four labels) to tweet 9.

---

**1/**

```
I wrote a certificate to close one lemma in my last paper.

An adversarial reviewer refuted it three times.

The second refutation is the one I think about, because nothing was broken. The code ran. The answer was green. And it was worthless. 🧵
```

**2/**

```
The job: prove that over a whole 4-dimensional domain of parameters, a certain configuration does not fit.

Continuous domain, nothing to enumerate. So you certify it computationally — subdivide into boxes, check each one.
```

**3/**

```
v1 died fast and fairly: meshes with no Lipschitz bound (so nothing connects the sample points to what's between them), an LP running with tolerances, and one required inequality that wasn't certified at all — it was sampled.

Fair fight. Easy fix.
```

**4/**

```
v2 was written with exact rational arithmetic. No float comparisons in the acceptance test.

Except one tolerance: 1e-12. The width of the band where two quantities counted as equal.

That's the one that mattered.
```

**5/**

```
The configuration the whole lemma turns on is exactly tangent. The rings touch. The feasibility margin there isn't small — it's zero.

At a point where the margin is zero, a tolerance doesn't add a small error.

It changes the answer.
```

**6/**

```
So the certificate reported "fits" at precisely the configuration the proof depends on.

Everywhere else the tolerance was harmless. That's what makes it so bad: the test is wrong only where the question is delicate, and it says nothing about it.
```

**7/**

```
The lemma was still true. The certificate just wasn't evidence for it.

It had been reporting a property of its own acceptance band instead of a property of the geometry.
```

**8/**

```
v4 assumes no floating-point fact at all:

• arcsine bounded by a pure rational series (alternating Lagrange remainder)
• directed rounding, one ULP outward per operation
• π certified in ℚ by that same series
• math.asin called as an oracle that is NOT believed
```

**9/**

```
Which is why every claim in the paper now carries a label:

proved · box-certified · grid-swept · sampled

Not a green tick for the paper. One label per claim, plus a map pairing each computational claim with the script behind it.
```

**10/**

```
The dangerous label isn't the weak one.

The same reviewer found a claim of mine marked "proved" that was only proved on part of its range. Nobody had re-read it — because the label said it was settled.

A wrong label is worse than a weak one. It gets trusted.
```

**11/**

```
Your tests, types, property checks and one careful read-through are four kinds of evidence — and CI paints them all the same green.

Which of yours is proved, and which is just unrefuted so far?

https://www.javieraguilar.ai/en/blog/proved-certified-swept-sampled
```
