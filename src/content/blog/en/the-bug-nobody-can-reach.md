---
title: "The Bug Nobody Can Reach"
description: "A model of the world can be flatly wrong about a whole region, pass every test you can write, and cost you exactly nothing — provably. Move the same mistake a few metres, onto the path something actually walks, and it costs you everything. What decides is not the size or the shape of the error. It is reach."
pubDate: 2026-09-05
tags: ["AI", "Machine Learning", "Testing", "Research", "Agents"]
lang: en
translationKey: the-bug-nobody-can-reach
heroImage: "/blog/the-bug-nobody-can-reach.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/XXXX.XXXXX"
linkedinSummary: |
  Suppose the map your system plans on is missing a room. Not "slightly off about the room" — the room is not on the map at all. What does that cost you?

  I spent a few months making that question precise, and the answer turned out to depend on exactly one thing. Not the size of the error, not how confident the model was, not even whether the missing thing is dangerous. Only this: can anything that plans on that map get to the room?

  When it cannot, the error is free — and I mean that in the strong sense. In the instrument I built, the model marks a whole sealed-off area as forbidden when only its rim is, no test can catch it (there is a proof, not a hope: no possible sample distinguishes the two), and the planner trusting it takes the same action at every step as one holding the truth. Same result, same route, decision for decision. Certified, wrong, free.

  Then the other kind: a model that does not know the fence exists at all, with the fence sitting on the route. That one costs 1.116 on a scale where 1.0 means you might as well have acted at random — the model actively promises a way through that is not there.

  The interesting part is what separates those two numbers, because it is not the model. Open a gap in the fence in front of the robot, on the way it already wanted to go, and the same blind model costs 0.029. Put the same gap round the back, where no route goes, and it is 1.116 again. Same code, same mistake, same shape of hole. Only reach changed.

  The tempting objection is "in your toy, the thing was walled off; in the real world I can go around". So the paper runs that too — a shape you genuinely can walk around. What survives is the danger: put it on the route and it is exploited exactly as before. What disappears is the guarantee that no test could have caught it.

  That is the practical split I would carry into a real system. Whether a plan crosses your model's error decides what it costs you. Whether the error is walled off decides whether any test could ever have found it. They are different questions, and most reviews I have seen ask neither.

  Which part of your system's world model would nobody notice was wrong — because nothing you run ever goes there?
---
Suppose the map your system plans on is missing a room. Not "slightly off about the room" — the room is not on the map at all. What does that cost you?

I have spent a few months making that question precise, and the answer turned out to be narrower and stranger than I expected. It depends on exactly one thing, and it is not the size of the error, not how confident the model was, not even whether the missing thing is dangerous. It is whether anything that plans on that map can *get* to the room.

This is the short version of a preprint ([arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX)); the [long post](/en/blog/being-wrong-can-be-free) has the same story with the numbers, the proofs and the parts that went wrong. Here I want just the one idea, because it is the one I would actually use.

## The setup, in one paragraph

A small robot on a plane. Somewhere on that plane there is a band it must not cross — a fence around a high-value spot it would otherwise drive straight at. A language model is handed the physics and asked to write the simulator the planner will use, and the description it receives simply leaves the fence out. Then the model's simulator is tested: run the real system a few dozen times, check that the written code predicts every step exactly. If it does, the code is accepted. That is all a "test suite" is here, and it is exactly what one is in practice.

Fences, containment shells, geofenced no-go zones: that is the shape safety-critical omissions actually take, and it is why I stopped using walls and started using rings.

## When being wrong is free

Close the band fully — a complete ring around the spot — and here is what the model writes: not a ring, but a filled disc. The whole interior marked as forbidden, when in truth only the rim is. Wrong about the shape of the world, not by a millimetre but categorically.

Two things are true about that wrong model, and they are the reason I wrote the paper.

**No test can catch it.** Not "we got unlucky", not "you would need more samples". There is a proof. The fence stops the robot on contact, so no run that starts outside can ever end up inside; therefore no observation that any test could ever make distinguishes the filled disc from the truth. You can run a million samples at any tolerance you like. They agree, always, because the place where they disagree is a place nothing can reach.

**It costs nothing.** The planner trusting the filled disc picks the same action at every step as a planner holding the true map: same route, same result, same contacts, run for run, seed for seed. Not approximately — identically.

So: certified, wrong, and free. Those three usually travel together in our heads; here they come apart cleanly.

A word on how I measure the cost, because it makes the rest readable. I compare what the planner earns against two references: what it would earn holding the truth, and what it would earn acting at random. **Zero means the wrong model costs nothing. One means you might as well have acted at random. Above one means the model actively steered you somewhere worse than random.**

## The same blindness, a different world

That was one kind of wrong model: one that invents a forbidden region where nothing can go. Here is the other, and the one that actually hurts — a model that simply does not know the fence is there at all. It is the common case: the description omitted the fence, the test runs never happened to touch it, so the code came back without it.

Now the fence *is* on the route. The planner drives confidently at the high-value spot, the real fence stops it dead, and it replans the same doomed route every step. Cost: **1.116** — worse than acting at random, because the model is not merely uninformative, it is actively promising a route that does not exist.

Now change one thing, and it is a thing about the world, not about the model: cut a gap in the fence wide enough to drive through, and put that gap **in front of** the robot, on the way it already wanted to go. Same model. Same blindness. Same missing clause in the code. Cost: **0.029**. Almost nothing — because the confident wrong route now goes somewhere the truth actually allows.

And to be sure the gap itself is not what did it, put the same gap — identical width, and in both cases the fence is equally not-a-closed-ring — round the back, where no route ever goes. Cost: **1.116** again, to four decimals the same as the fully closed fence.

Same model, same mistake, same shape of hole. One number is 0.029 and the other is 1.116, and the only thing separating them is whether the robot's own path crosses the gap.

That is the whole finding, and the reason the slogan is *reach*, not shape: you cannot look at what your model got wrong — not its size, not its geometry, not even a robust structural property like "is there a hole in it" — and conclude anything at all about what it will cost you. You have to ask where the thing planning against it can go.

## "But in the real world I could go around it"

That was the first objection I got, and it is the right one. In two dimensions a ring is a wall: of course nothing gets in. Maybe the whole result is an artefact of a toy where the mistake happens to be sealed off.

So the paper runs the case where going around is genuinely possible: a doughnut-shaped region floating in three-dimensional space, between the robot and its target. Nothing is sealed off — there is an explicit route that goes around it without touching it at all.

The result splits in two, and this is the version I would carry into a real system.

**The danger survives.** Put the doughnut so the planned route runs into its solid part and the cost is **0.898**. Move it so the route threads the hole instead and the cost is **0.019** — same object, same rarity of contact, same trivial shape. Being on the path is what costs you, whether or not the thing encloses anything.

**The guarantee does not.** Once you can go around, there is no region a competent planner provably cannot query, so there is no longer any proof that a test could not have caught the error. It becomes merely unlikely to be caught, which is a much weaker and much more familiar situation.

Two different questions, then, and they had been fused together in my head until this experiment pulled them apart:

- **Does a plan cross the place where my model is wrong?** This decides what the error costs.
- **Is that place walled off from everything I can run?** This decides whether any test could ever have found it.

## What I would ask of my own system

Three questions, and none of them needs the mathematics:

1. **Where is my model wrong in a way nothing I run ever visits?** That part is free today — and it is also invisible to every test I have, so I will not be told when it stops being free.
2. **What would put a plan through it?** A new feature, a new goal, a shortcut someone adds next quarter. Reach is not a property of the model; it is a property of the model *plus* whatever is planning with it, and the second half changes far more often than the first.
3. **Do my tests sample where my system acts, or where it is easy to sample?** A passing suite certifies the reachable part and says nothing whatsoever about the rest.

The uncomfortable version of all this: a model can be exactly right on everything you can check and arbitrarily wrong beyond it, and the difference between "free" and "catastrophic" is not a property of the error. It is a property of the plans you happen to run today.

---

*The long version, with the danger curves, the repair experiments and a pre-registered test that came out null: [Being Wrong Can Be Free](/en/blog/being-wrong-can-be-free). The formal version: [arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX), with [code and every result artifact open](https://github.com/JaviMaligno/code-world-models).*
