# X thread — "Being Wrong Can Be Free — Until the Planner Can Reach It"

Manual thread (there is no X automation in this repo). Post on publication day,
after the arXiv ID exists. **Replace `XXXX.XXXXX` before posting.**

Each tweet is kept under 280 characters so it works on a free account.

---

**1/**

```
Last week: a synthesized world model passes every sampled test and is still wrong where the samples never land.

New preprint asks the question I couldn't answer then — what if the part it gets wrong is somewhere nothing can ever reach?

It's free. Provably.

🧵
```

**2/**

```
The instrument: an annular no-go band wrapped around a high-reward region a planner wants.

Fences, containment shells, geofenced no-go zones — that's the shape.

The spec handed to the model pins the physics and simply omits the band.
```

**3/**

```
With the band closed, the model writes a filled disc: no hole at all. Wrong topology, not wrong parameters.

That artifact is unfalsifiable by ANY sampling gate. Not "unlikely to be caught" — there's a proof, and it needs no assumption on sample size or tolerance.
```

**4/**

```
It's also harmless, bitwise.

A planner trusting the filled disc picks the same action every step as one that knows the truth: same return, same final state, same contacts, seed for seed.

Certified. Wrong. Free. Three things that usually travel together, coming apart.
```

**5/**

```
Then I opened a channel in the band, facing the start — 0.1 radians, about a third of the planner's own step.

Exploitation collapsed: 1.116 with the band closed → 0.348 at that width → 0.029 once it's wide.

The knee is where a step first fits through the gap.
```

**6/**

```
Now the same channel. Same width. Same first Betti number.

Rotated so it hides behind the goal, where no plan goes.

Play cost: 1.116 — the closed band's own number, to four decimals.

Identical topology. Opposite consequence.
```

**7/**

```
So danger is topology relative to reach — not topology.

Which kills a tempting shortcut: you cannot audit a wrong model by the shape of its error, not even by an invariant as robust as "is there a hole".

You have to ask where the thing planning against it can go.
```

**8/**

```
Can the loop repair a ring? Three model families, 903 artifacts, 39 conditions.

From outside the band: none recover it. My favourite failure froze on exact float equality with its one contact state — its certificate was the last bit of sin() on the machine that made it.
```

**9/**

```
The held-out audit is the part I'd want to see in someone else's paper.

Independent-gate acceptance coincides with "that gate's own sample also missed the band" in 156 of 156 artifacts.

Of 214 in-sample passes, 121 fail an independent gate — every one at a contact.
```

**10/**

```
To help repair I fed each attempt an honest topological summary of its evidence.

A summary is a sensor, and sensors have resolution: this one reports a closed loop for every gap narrower than ~2 arc-units, and the artifacts follow the report rather than the truth.
```

**11/**

```
Quadruple the evidence and it gets MORE confident in the wrong topology: false-loop rate 1/5 → 3/5 seeds.

Resolving a narrow channel needs a different filtration, not a bigger sample.
```

**12/**

```
Does that claim line *cause* it? I pre-registered the test: flip only that line, 60 paired seeds, everything else byte-identical.

9 moved as predicted, 2 against. p = 0.065.

Directional, not significant — so the paper keeps the association and drops the causal claim.
```

**13/**

```
A sampling gate certifies the reachable restriction of your model, nothing else.

So the question isn't "is the model right?" but "does where it's wrong intersect the reach of whatever plans against it?"

arxiv.org/abs/XXXX.XXXXX
github.com/JaviMaligno/code-world-models
```
