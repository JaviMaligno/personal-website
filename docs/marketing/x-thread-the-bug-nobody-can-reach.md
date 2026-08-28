# X thread — "The Bug Nobody Can Reach"

Manual thread (there is no X automation in this repo). Post on publication day.
**Replace `XXXX.XXXXX` before posting.**

Short on purpose: this is the digestible companion to the long post, which has
its own 13-tweet thread. Eight tweets, each under 280 characters.

---

**1/**

```
Suppose the map your system plans on is missing a room.

Not "a bit off about the room" — the room isn't on the map.

What does that cost you?

Turns out: it depends on exactly one thing, and it isn't the size of the error.

🧵
```

**2/**

```
A robot on a plane. A fence around a high-value spot it would otherwise drive straight at.

An LLM is given the physics and writes the simulator the planner will use — and the description it gets leaves the fence out.

Then we test the code against real runs. It passes.
```

**3/**

```
Case one: the fence is a closed ring, and the model marks the whole sealed interior as forbidden, not just the rim.

Wrong about the shape of the world. And:

• no test can EVER catch it (proof, not luck)
• the planner acts exactly as it would with the true map

Free.
```

**4/**

```
Case two: a model that doesn't know the fence exists at all, with the fence on the route.

It drives at the goal, the real fence stops it dead, it replans the same doomed route every step.

Cost 1.116, on a scale where 1.0 = you might as well have acted at random.
```

**5/**

```
Now change the WORLD, not the model: open a gap in the fence in front of the robot, where it already wanted to go.

Same code. Same blindness. Cost: 0.029.

Put the same gap round the back, where no route goes: 1.116 again.

Only reach changed.
```

**6/**

```
"But in the real world I could go around it."

Right, so we ran that: a doughnut-shaped region in 3D you genuinely can walk around.

Route threads the hole → 0.019.
Same object moved so the route hits it → 0.898.

Being on the path is what costs you.
```

**7/**

```
What that splits into — the version I'd carry into a real system:

Does a plan cross the place your model is wrong? → decides what it costs.

Is that place walled off from everything you run? → decides whether any test could ever have found it.

Different questions.
```

**8/**

```
So the uncomfortable version:

A model can be exactly right on everything you can check and arbitrarily wrong beyond it — and whether that's free or catastrophic isn't a property of the error. It's a property of the plans you happen to run today.

arxiv.org/abs/XXXX.XXXXX
```
