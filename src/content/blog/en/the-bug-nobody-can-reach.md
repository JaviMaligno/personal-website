---
title: "The Bug Nobody Can Reach"
description: "A model of the world can be flatly wrong about a whole region, pass every test you can write, and cost you exactly nothing — provably. Move the same mistake a few metres, onto the path something actually walks, and it costs you everything. What decides is not the size or the shape of the error. It is reach."
pubDate: 2026-09-17
tags: ["AI", "Machine Learning", "Testing", "Research", "Agents"]
lang: en
translationKey: the-bug-nobody-can-reach
heroImage: "/blog/the-bug-nobody-can-reach.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/2608.28541"
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

This is the short version of a preprint ([arXiv:2608.28541](https://arxiv.org/abs/2608.28541)); the [long post](/en/blog/being-wrong-can-be-free) has the same story with the numbers, the proofs and the parts that went wrong. Here I want just the one idea, because it is the one I would actually use.

<style>
.cwm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.cwm-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.cwm-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>


## The setup, in one paragraph

A small robot on a plane. Somewhere on that plane there is a band it must not cross — a fence around a high-value spot it would otherwise drive straight at. A language model is handed the physics and asked to write the simulator the planner will use, and the description it receives simply leaves the fence out. Then the model's simulator is tested: run the real system a few dozen times, check that the written code predicts every step exactly. If it does, the code is accepted. That is all a "test suite" is here, and it is exactly what one is in practice.

Fences, containment shells, geofenced no-go zones: that is the shape safety-critical omissions actually take, and it is why I stopped using walls and started using rings.

<figure class="cwm-fig">
<!-- fig:plain-setup -->
<svg viewBox="0 0 600 252" role="img" aria-label="The setup: a robot outside a fenced band, the high-value spot inside it, and the straight route the robot wants to take">
<defs><marker id="mk-setup" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<circle cx="300.0" cy="128.0" r="72.25" fill="none" stroke="#f43f5e" stroke-width="25.50" stroke-opacity="0.85"/>
<polygon points="300.0,110.2 295.4,121.6 283.0,122.5 292.5,130.4 289.5,142.4 300.0,135.9 310.5,142.4 307.5,130.4 317.0,122.5 304.6,121.6" fill="#fbbf24"/>
<circle cx="158.9" cy="128.0" r="4.2" fill="#f8fafc"/>
<line x1="164.9" y1="128.0" x2="202.2" y2="128.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-setup)"/>
<path d="M207.8,122.5 L218.8,133.5 M218.8,122.5 L207.8,133.5" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
<text x="158.9" y="112.0" font-size="11" fill="#f8fafc" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the robot</text>
<text x="396.0" y="133.0" font-size="11" fill="#fbbf24" text-anchor="start" font-family="ui-monospace,'JetBrains Mono',monospace">what it wants</text>
<text x="300.0" y="32.0" font-size="11" fill="#fb7185" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the fence — not in the description it was given</text>
<text x="30.0" y="226.0" font-size="10" fill="#64748b" text-anchor="start" font-family="ui-monospace,'JetBrains Mono',monospace">it stops here — and the model never mentioned it</text>
</svg>
<!-- /fig:plain-setup -->
<figcaption>The setup. The robot wants the high-value spot; the fence around it is real but absent from the description the model was given, so the code the model writes says the way is clear.</figcaption>
</figure>


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

<figure class="cwm-fig">
<!-- fig:plain-free-vs-costly -->
<svg viewBox="0 0 600 244" role="img" aria-label="The same gap in the fence, in front of the robot and behind the goal, with the cost of the blind model in each case">
<defs><marker id="mk-plain" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<rect x="10" y="22" width="285" height="170" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="152.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">gap in front of the robot</text>
<circle cx="152.0" cy="104.0" r="59.50" fill="none" stroke="#6366f1" stroke-width="21.00" stroke-opacity="0.9" stroke-dasharray="338.54 35.31" stroke-dashoffset="169.27"/>
<polygon points="152.0,90.7 148.6,99.3 139.4,99.9 146.4,105.8 144.2,114.8 152.0,109.9 159.8,114.8 157.6,105.8 164.6,99.9 155.4,99.3" fill="#fbbf24"/>
<circle cx="42.8" cy="104.0" r="3.6" fill="#f8fafc"/>
<line x1="47.8" y1="104.0" x2="132.4" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-plain)"/>
<text x="152.0" y="180.0" font-size="15" fill="#6366f1" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  0.029</text>
<text x="152.0" y="210.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the route goes through</text>
<rect x="305" y="22" width="285" height="170" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="447.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">the same gap, round the back</text>
<circle cx="447.0" cy="104.0" r="59.50" fill="none" stroke="#f43f5e" stroke-width="21.00" stroke-opacity="0.9" stroke-dasharray="338.54 35.31" stroke-dashoffset="356.20"/>
<polygon points="447.0,90.7 443.6,99.3 434.4,99.9 441.4,105.8 439.2,114.8 447.0,109.9 454.8,114.8 452.6,105.8 459.6,99.9 450.4,99.3" fill="#fbbf24"/>
<circle cx="337.8" cy="104.0" r="3.6" fill="#f8fafc"/>
<line x1="342.8" y1="104.0" x2="367.2" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-plain)"/>
<path d="M371.3,99.0 L381.3,109.0 M381.3,99.0 L371.3,109.0" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
<text x="447.0" y="180.0" font-size="15" fill="#f43f5e" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  1.116</text>
<text x="447.0" y="210.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the fence still blocks it</text>
<text x="300.0" y="232.0" font-size="11.5" fill="#f8fafc" text-anchor="middle" font-style="italic">same model, same fence, same size of gap</text>
</svg>
<!-- /fig:plain-free-vs-costly -->
<figcaption>The same blind model in two worlds that differ by a rotation. On the left the gap sits where the robot was already going, so its confident wrong route turns out to be allowed. On the right the identical gap sits behind the goal, the fence still blocks the route, and the model costs more than acting at random.</figcaption>
</figure>


That is the whole finding, and the reason the slogan is *reach*, not shape: you cannot look at what your model got wrong — not its size, not its geometry, not even a robust structural property like "is there a hole in it" — and conclude anything at all about what it will cost you. You have to ask where the thing planning against it can go.

## "But in the real world I could go around it"

That was the first objection I got, and it is the right one. In two dimensions a ring is a wall: of course nothing gets in. Maybe the whole result is an artefact of a toy where the mistake happens to be sealed off.

So the paper runs the case where going around is genuinely possible: a doughnut-shaped region floating in three-dimensional space, between the robot and its target. Nothing is sealed off — there is an explicit route that goes around it without touching it at all.

<figure class="cwm-fig">
<!-- fig:torus-3d -->
<svg viewBox="0 0 600 250" role="img" aria-label="The same solid torus in three dimensions: with the route through its hole it costs 0.019, and moved so the route runs into the tube it costs 0.898 — while a contact-free path around it still exists">
<defs><marker id="t3-mk" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<defs><marker id="t3b-mk" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<defs><marker id="t3b-mk2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#22d3ee"/></marker></defs>
<rect x="10" y="22" width="285" height="176" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="152.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">the route threads the hole</text>
<ellipse cx="152.0" cy="172.0" rx="46" ry="7" fill="#000" fill-opacity="0.30"/>
<defs><clipPath id="t3-far"><rect x="152.0" y="2.0" width="72.0" height="204.0"/></clipPath><clipPath id="t3-near"><rect x="80.0" y="2.0" width="72.0" height="204.0"/></clipPath></defs>
<path d="M120.0,104.0 A32.0,62.0 0 1,0 184.0,104.0 A32.0,62.0 0 1,0 120.0,104.0 Z" fill="none" stroke="#6366f1" stroke-width="20" stroke-opacity="0.55" clip-path="url(#t3-far)"/>
<circle cx="34.0" cy="104.0" r="3.4" fill="#f8fafc"/>
<line x1="40.0" y1="104.0" x2="254.0" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#t3-mk)"/>
<path d="M120.0,104.0 A32.0,62.0 0 1,0 184.0,104.0 A32.0,62.0 0 1,0 120.0,104.0 Z" fill="none" stroke="#6366f1" stroke-width="20" clip-path="url(#t3-near)"/>
<polygon points="268.0,91.0 264.6,99.4 255.6,100.0 262.6,105.8 260.4,114.5 268.0,109.7 275.6,114.5 273.4,105.8 280.4,100.0 271.4,99.4" fill="#fbbf24"/>
<text x="152.0" y="186.0" font-size="15" fill="#6366f1" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  0.019</text>
<text x="152.0" y="214.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">it never touches the object</text>
<rect x="305" y="22" width="285" height="176" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="447.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">the same torus, moved</text>
<ellipse cx="447.0" cy="172.0" rx="86" ry="7" fill="#000" fill-opacity="0.30"/>
<defs><clipPath id="t3b-far"><rect x="323.0" y="34.0" width="248.0" height="70.0"/></clipPath><clipPath id="t3b-near"><rect x="323.0" y="104.0" width="248.0" height="70.0"/></clipPath></defs>
<path d="M363.0,104.0 A84.0,30.0 0 1,0 531.0,104.0 A84.0,30.0 0 1,0 363.0,104.0 Z" fill="none" stroke="#f43f5e" stroke-width="21" stroke-opacity="0.55" clip-path="url(#t3b-far)"/>
<circle cx="329.0" cy="104.0" r="3.4" fill="#f8fafc"/>
<line x1="335.0" y1="104.0" x2="365.0" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#t3b-mk)"/>
<path d="M350.0,99.0 L360.0,109.0 M360.0,99.0 L350.0,109.0" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
<path d="M337.0,104.0 Q447.0,16.0 549.0,104.0" fill="none" stroke="#22d3ee" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#t3b-mk2)"/>
<text x="447.0" y="36.0" font-size="9.5" fill="#22d3ee" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">a way around, contact-free</text>
<path d="M363.0,104.0 A84.0,30.0 0 1,0 531.0,104.0 A84.0,30.0 0 1,0 363.0,104.0 Z" fill="none" stroke="#f43f5e" stroke-width="21" clip-path="url(#t3b-near)"/>
<polygon points="563.0,91.0 559.6,99.4 550.6,100.0 557.6,105.8 555.4,114.5 563.0,109.7 570.6,114.5 568.4,105.8 575.4,100.0 566.4,99.4" fill="#fbbf24"/>
<text x="447.0" y="186.0" font-size="15" fill="#f43f5e" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  0.898</text>
<text x="447.0" y="214.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the route runs into the tube</text>
<text x="300.0" y="238.0" font-size="11" fill="#f8fafc" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">nothing here is sealed off  ·  same object, same contact rarity 0.0033</text>
</svg>
<!-- /fig:torus-3d -->
<figcaption>The doughnut in three dimensions. On the left the route passes through its hole and the wrong model costs almost nothing; on the right the same object has been moved so the route runs into it, and it costs nearly as much as acting at random. The dashed path arcing over the top is the one that matters for the second half of the story: it reaches the goal without touching anything, which is what makes the error catchable in principle again.</figcaption>
</figure>


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

*The long version, with the danger curves, the repair experiments and a pre-registered test that came out null: [Being Wrong Can Be Free](/en/blog/being-wrong-can-be-free). The formal version: [arXiv:2608.28541](https://arxiv.org/abs/2608.28541), with [code and every result artifact open](https://github.com/JaviMaligno/code-world-models).*
