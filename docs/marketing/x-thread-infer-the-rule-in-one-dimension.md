# X thread — "An LLM Can Infer the Rule You Forgot — in One Dimension"

Manual thread (there is no X automation in this repo). Post on announcement day,
after the arXiv ID exists. **Replace `2608.17956` before posting.**

Each tweet is kept under 280 characters so it works on a free account.

---

**1/**

```
A few weeks ago I published a preprint saying LLMs translate rules but don't infer them.

The follow-up is out. It shows exactly where that conclusion is wrong — and where it is very right.

🧵
```

**2/**

```
The setup: a cart on a rail, a wall that stops it dead, and a spec handed to the model that simply omits the wall.

When the sampled rollouts never touch the wall, the synthesized model passes its check at 100% and is exact everywhere else.
```

**3/**

```
Then the planner that trusts it drives into the region the wall occupies, gets pinned there, and replans the same doomed plan every step.

Return: 0.02, against 17.77 for the planner using the truth.

Verified. Exact off the wall. Catastrophic.
```

**4/**

```
How often the check misses is not a mystery. N sampled rollouts all miss an event of probability r exactly (1-r)^N of the time.

At r = 0.0114 and N = 40 that predicts 0.63.

Measured: 20 of 40 independent samples missed the wall.
```

**5/**

```
Now the part that broke my earlier conclusion.

When the wall IS in the sample, the model does not stay blind. It writes the true global rule:

  if x2 >= 8.0: return [8.0, 0.0]

Not a patch around the contacts it saw. 105 of 111 attempts.
```

**6/**

```
So I gave the same kind of rule one more dimension: a circular region instead of a threshold in one variable.

Same pipeline, same models, same gate.

0 of 156.
```

**7/**

```
Then I spent the rest of the work attacking my own explanation. Eight interventions:

- region-first prompt at 3x budget
- flat edges instead of curved
- naming the variable the rule reads
- making the region's interior observable
- widening the evidence

All 0/40.
```

**8/**

```
The controls locate the failure exactly.

Three lines of least squares recover the circle from the same evidence: 20/20 at the widest dose. The model: 0/20.

Give it the shape AND the location, withholding only the radius: 20/20, exact.
Shape alone: 0/20.
```

**9/**

```
What is not induced is a *located* rule. And it does not respond to more evidence at all — I dosed the coverage until the trivial fit succeeded on every sample, and the model still recovered none.
```

**10/**

```
Practical version, if you ship a synthesized model behind a sampling check:

coverage of the boundary is the whole game, and "it'll figure it out from the data" is a bet you can only make in one dimension.

Anything with a shape, you still specify.
```

**11/**

```
Preprint: https://arxiv.org/abs/2608.17956
Code and every result artifact: https://github.com/JaviMaligno/code-world-models

Long-form writeup: https://www.javieraguilar.ai/en/blog/infer-the-rule-in-one-dimension
```
