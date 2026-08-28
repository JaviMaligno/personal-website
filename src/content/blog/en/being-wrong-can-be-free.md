---
title: "Being Wrong Can Be Free — Until the Planner Can Reach It"
description: "A synthesized world model can get a whole region wrong, pass any sampling gate, and cost exactly nothing — provably. Then I opened a 0.1-radian door in that region and the danger collapsed; I hid the same door behind the goal and it stayed at full strength. Same topology, opposite danger."
pubDate: 2026-09-02
tags: ["AI", "Machine Learning", "Testing", "Research", "Agents"]
lang: en
translationKey: being-wrong-can-be-free
heroImage: "/blog/being-wrong-can-be-free.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/XXXX.XXXXX"
  - label: "Companion paper"
    url: "https://arxiv.org/abs/2608.17956"
linkedinSummary: |
  Last week I argued that coverage of the boundary is the whole game when you certify a synthesized world model against sampled tests. The follow-up preprint asks the question that was still open, and the answer surprised me: sometimes being wrong costs nothing at all, and you can compute when.

  The instrument is a ring — an annular no-go band wrapping a high-reward region the planner wants. Fences, containment shells and geofenced no-go zones are the practical shape of this, and the model is handed a spec that simply omits the band.

  When the band closes fully, the model writes a filled disc: the wrong topology, no hole at all. That artifact is unfalsifiable by any sampling gate — not "unlikely to be caught", but provably unable to be caught at any sample size and any tolerance — and it is also bitwise harmless: same return, same final state, same contacts, seed for seed, as the true physics. Certification, correctness and consequence come apart three ways.

  Then the part I did not expect. Open a channel in the band the planner can actually drive through — 0.1 radians, about a third of its own step — and the exploitation collapses: 1.116 with the band closed, 0.348 at that width, 0.029 once the channel is wide. Take the same channel, same width, same Betti number, and hide it behind the goal where no plan goes: 1.116 again, the closed band's own number to four decimals. Identical topology, opposite consequence. What makes an omission dangerous is not its shape but whether a competent planner's path crosses it.

  Two more results I had to report against myself. The topological summary guiding the repair loop has a measured resolution limit — it reports a closed loop for every channel narrower than about two arc-units, and the artifacts track that wrong report rather than the truth. I pre-registered an intervention to test whether the summary's claim line causes that, ran 60 paired seeds, got 9 against 2 in the predicted direction, and p = 0.065. Directionally consistent, not significant, so the causal reading stays unearned and the paper says so.

  The practical version: a sampling gate certifies the reachable restriction of your model and nothing else. So the safety question is never "is the model right?" but "does the place where it is wrong intersect the operative reach of whatever is planning against it?"

  Where in your system would a wrong answer be genuinely free — and how would you know the reach hasn't changed?
---
Last week I wrote about [a model that infers the rule you forgot, but only in one dimension](/en/blog/infer-the-rule-in-one-dimension). The practical rule I ended on was that coverage of the boundary is the whole game: your sampling gate certifies your model where your samples land, and a rule with a shape you still have to specify.

That leaves a question I could not answer with the instruments in that paper. All of those wrong models were wrong *somewhere a planner could get to*. What happens when the part the model gets wrong encloses something nothing can ever reach? The answer turns out to be sharper than "it's probably fine", in both directions: the error becomes provably uncatchable *and* provably costless — and then a door 0.1 radians wide, in the right place, undoes the second half while leaving the topology untouched. That is a preprint, *An Enclosed Mode Is a Gauge Choice* (**[arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX)**), with the [code, result artifacts and Lean proofs open](https://github.com/JaviMaligno/code-world-models).

<style>
.cwm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.cwm-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.cwm-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
.cwm-table{width:100%;border-collapse:collapse;margin:1.5rem 0;font-size:.92rem}
.cwm-table th,.cwm-table td{padding:.55rem .7rem;border-bottom:1px solid rgba(255,255,255,0.1);text-align:left}
.cwm-table th{color:#94a3b8;font-weight:600}
.cwm-table td.n{font-family:ui-monospace,'JetBrains Mono',monospace;text-align:right;white-space:nowrap}
</style>

## A mode with an inside

The instrument is deliberately minimal: a thrust-and-drag mover on a plane, and an annular band — inner radius 3.5, outer radius 5.0 — that freezes the mover the instant it touches. Inside the ring's hole sits a high-reward "lode" the planner would love to visit. The spec handed to the language model pins the physics exactly and simply omits the band, exactly as before.

The reason for a ring rather than another wall is that this is the shape safety-critical omissions actually take. Fences, containment shells, geofenced no-go regions: a boundary drawn around something, with an inside. And a pipeline that cannot tell a fenced void from a fenced hazard — or a fence from a filled wall — is certifying less than it looks like it is.

Three knobs, all fixed before any run: the width $\gamma$ of an angular channel cut through the band (at $\gamma = 0$ the ring is closed), whether that channel faces the start or hides behind the lode, and whether the mover starts outside the ring or inside its hole. Everything in the paper follows from what those knobs do to one object: the set of state-action pairs a rollout can actually query.

## Beyond reach is gauge

Here is the theory in one sentence. If a gate accepts every candidate whose sampled transitions match, then acceptance-with-certainty pins the model down exactly on the reachable query set — and *everything beyond reach is gauge*, in the physicist's sense: a free choice that changes no observable. Two models that differ only out there are the same model as far as any sampling gate can ever be.

On the closed ring that has a limiting case you can hold in your hand. The natural wrong artifact is a **filled disc**: no hole at all, the whole interior frozen. It is wrong about the topology, not just the parameters. And it is:

- **unfalsifiable by any sampling gate.** Not "unlikely to be caught" — there is a proof, and it needs no assumption about sample size or tolerance. Because the band freezes the mover on contact, no rollout that starts outside can ever be inside the hole, so no possible transition distinguishes the filled disc from the truth.
- **bitwise harmless at play.** The planner that trusts the filled disc plans identically to the planner that knows the truth: same action at every step, same return, same final state, same contacts, seed for seed. Paired-seed MPC episodes confirm it exactly, not approximately.

So certification, correctness and consequence come apart three ways rather than two. This artifact is certified, wrong, and free. My previous two papers had shown certified-and-wrong-and-costly, and certified-and-wrong-and-unfalsifiable; the ring is where "wrong" and "expensive" fully decouple, with a theorem rather than a measurement.

## Two identical holes, opposite danger

That is the calm half. Now open a channel in the band — a gap of angular width $\gamma$, facing the start, so the planner can drive through it.

The exploitation collapses. A dense sweep of the scripted blind model — 16 paired MPC episodes per point — puts `play_cost` (how much return the planner loses by trusting the wrong model, normalised against the truth planner) at 0.999 with the ring closed, 0.139 at $\gamma = 0.1$, and essentially zero from $\gamma = 0.15$ on. There is a knee, and it sits exactly where the channel becomes wide enough for a step to fit through: at $\gamma = 0.1$ the gap's arc is about 0.35 world-units, comparable to the planner's own step. The synthesis arm reproduces the collapse on its own exploited blind artifacts, in both model sizes and in the Claude relay: 0.348 at the knee, 0.029 by $\gamma = 0.6$.

Then take the same channel, the same width, the same first Betti number, and rotate it so it hides behind the lode, where no plan ever goes. At $\gamma = 0.6$ the blind artifact's play cost is 1.116. At $\gamma = 1.2$ it is 1.116 again — and with the band fully closed, 1.116 once more. Not "comparable to" the closed ring: its number to four decimals, because it is the same blind program facing the same reachable world.

<figure class="cwm-fig">
<svg viewBox="0 0 600 268" role="img" aria-label="Play cost against channel width: both the dense scripted sweep and the synthesized blind artifacts collapse once the facing channel admits the planner's step, while the hidden channel of the same width holds the closed-band value of 1.116">
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#9CA3AF">
    <line x1="98" y1="38" x2="98" y2="190" stroke="rgba(255,255,255,0.14)"/>
    <line x1="98" y1="190" x2="578" y2="190" stroke="rgba(255,255,255,0.14)"/>
    <text x="88" y="49" text-anchor="end">1.12</text>
    <text x="88" y="194" text-anchor="end">0.00</text>
    <text x="120" y="210" text-anchor="middle">0</text>
    <text x="215" y="210" text-anchor="middle">0.1</text>
    <text x="310" y="210" text-anchor="middle">0.2</text>
    <text x="450" y="210" text-anchor="middle">0.6</text>
    <text x="560" y="210" text-anchor="middle">1.2</text>
    <text x="338" y="230" text-anchor="middle" fill="#64748b">channel width γ (radians)</text>
  </g>
  <polyline points="120,61 140,120 165,146 215,172 245,190 310,188 450,187 560,189" fill="none" stroke="#6366f1" stroke-width="2.4"/>
  <circle cx="120" cy="61" r="4" fill="#6366f1"/><circle cx="215" cy="172" r="4" fill="#6366f1"/>
  <text x="136" y="78" fill="#818cf8" font-size="11.5" font-family="ui-monospace,monospace">0.999</text>
  <text x="228" y="168" fill="#818cf8" font-size="11.5" font-family="ui-monospace,monospace">0.139</text>
  <circle cx="215" cy="145" r="5" fill="#22d3ee"/><circle cx="450" cy="186" r="5" fill="#22d3ee"/><circle cx="560" cy="187" r="5" fill="#22d3ee"/>
  <text x="228" y="141" fill="#22d3ee" font-size="11.5" font-family="ui-monospace,monospace">0.348</text>
  <circle cx="120" cy="46" r="5.5" fill="#f43f5e" fill-opacity="0.25" stroke="#f43f5e" stroke-width="2"/>
  <circle cx="450" cy="46" r="5.5" fill="#f43f5e"/><circle cx="560" cy="46" r="5.5" fill="#f43f5e"/>
  <line x1="120" y1="46" x2="560" y2="46" stroke="#f43f5e" stroke-width="2.2" stroke-dasharray="5 4"/>
  <text x="470" y="38" fill="#fb7185" font-size="11.5" font-family="ui-monospace,monospace">1.116</text>
  <text x="152" y="33" fill="#fb7185" font-size="11.5">closed band</text>
  <text x="300" y="63" fill="#fb7185" font-size="12">hidden channel, same γ: nothing changes</text>
  <text x="300" y="120" fill="#818cf8" font-size="12">facing channel: danger collapses</text>
  <g font-size="11" font-family="ui-monospace,'JetBrains Mono',monospace">
    <line x1="120" y1="255" x2="146" y2="255" stroke="#6366f1" stroke-width="2.4"/>
    <text x="154" y="259" fill="#9CA3AF">scripted blind model, dense sweep</text>
    <circle cx="380" cy="255" r="5" fill="#22d3ee"/>
    <text x="392" y="259" fill="#9CA3AF">synthesized blind artifacts</text>
  </g>
</svg>
<figcaption>Blind-model play cost against channel width, 16 paired MPC episodes per point. Both series collapse once the facing channel admits the planner's step: the dense scripted sweep from 0.999 to 0.139 at γ = 0.1 and to ~0 beyond, and the synthesized artifacts from 1.116 to 0.348 at the knee and 0.029 by γ = 0.6. Rotating that same channel behind the lode (rose) holds 1.116 at γ = 0.6 and γ = 1.2 — the closed band's own value, to four decimals.</figcaption>
</figure>

Same hole, same Betti number, opposite danger. Which tells you that the property doing the work is not topological at all. **Danger is topology relative to reach.** And the mechanism is the gate quotient showing up on the play side: as the channel opens where the planner actually drives, the phantom stops being phantom — the blind plan (straight at the lode) becomes *executable in the truth*, so the blind model and the truth agree along the operative path, which is the only path that gets to bill you.

I like this result because it kills a tempting shortcut. If you are auditing a synthesized model, you cannot look at the geometry of what it got wrong — not even at an invariant as robust as "is there a hole" — and conclude anything about consequence. You have to ask where the thing planning against it can go.

## Can the loop repair a ring?

Same question as last time, harder shape. Three model families (GPT-5.x at two sizes, Qwen, Claude), the same synthesize-refine-accept loop, 903 artifacts across 39 conditions in the end.

**From outside the ring, nothing recovers the region.** Not one artifact encodes the band. What they write instead are superstitious point fits: an integrator plus a comment hypothesising a tiny localised trap, freezing on exact float equality with the single contact state their sample happened to contain. One of those is my favourite specimen in the whole series — it passed its own gate at 1.000, and the hardcoded coordinate sits two floating-point ulps away from the same trajectory computed with a different maths library. Its certificate was a property of the last bit of `sin` on the machine that generated it. An independent gate rejects it on every platform.

That is not the models being careless; it is the theory being obeyed. From outside, ring evidence and disc evidence are *pathwise identical* — there is no observation that separates them — so an honest summary of the evidence can only report the reachable arc.

**From inside the hole, they pose the right topology and cannot pin it.** Start the mover inside and the interior becomes reachable, so the omission is falsifiable now. Artifacts do pose hollow structures, loops, annuli — the right shape — and gate-pass rates stay at essentially zero anyway, because the band's radii are not round numbers and the gate wants $10^{-9}$. The single gate-certified recovery out of twenty used the one form whose only free parameter is anchored in the reward spec: the *complement* of a disc whose radius is the lode's own. The strongest cross-family repairer wrote exactly the same form.

The held-out audit is the part I would want to see in someone else's paper. Re-scoring every artifact on a disjoint gate block: acceptance coincides with "that independent gate's own sample also missed the band" in **156 of 156** cases — an exact identity, per artifact, zero off-diagonal. And of 214 in-sample gate passes, 121 fail an independent gate, every single one of them *at a contact with the band*. An in-sample pass is training-set consistency, and what it omits is exactly the mode.

## The sensor that guides the loop has a resolution limit

To give repair its best shot I fed each attempt an honest topological summary of its own evidence — cluster counts, bounding box, and a persistent-homology estimate $\hat\beta_1$ of how many holes the contact cloud has. Wording frozen before any run, no shape family ever named.

A summary like that is a **sensor**, and sensors have resolution. This one reports $\hat\beta_1 = 1$ — a closed loop — for every channel narrower than about two arc-units, even though the true $\beta_1$ is 0 for *every* $\gamma > 0$: a ring with a gap is not a loop. The flip happens around $\gamma = 1.8$.

That limit is geometric rather than budgetary, and the paper proves the two-sided version: below a scale set by the largest angular gap in the sample, the gap is invisible to the detector, and above another explicit scale the loop cannot survive. A factorial over the detector's point budget (30, 90, 270) and the evidence dose (40 and 160 rollouts) does not move the flip at all.

Worse, at the boundary more evidence makes it *more* confident in the wrong topology: quadruple the dose and the false-loop rate rises from 1 of 5 seeds to 3 of 5, because the denser sample fills the shells adjacent to the channel and the spurious bar's persistence grows from 0.05 to 0.50 while the detector's own threshold grows only modestly. Resolving a narrow channel takes a different filtration, not a bigger sample.

And the posed topology of the artifacts tracks the *summary*, not the truth: closed structures dominate wherever the summary says "closed loop" and all but vanish where it honestly says "arc" — 1 closed against 26 arc-shaped at $\gamma = 2.4$.

Now the part I have to report against myself. That crossover is cross-gap: the environment and the summary change together, so it does not isolate the summary's claim as the cause. So I pre-registered an intervention — design, analysis script and stopping rule committed before any outcome existed — that flips *only* the claim line: same 60 seeds, bit-identical evidence, every other byte of the prompt held fixed, the $\hat\beta_1$ line and its one interpretive sentence negated, scored against a freshly generated honest control.

Result: of 11 discordant pairs, 9 moved in the direction the claim predicted and 2 against. Exact two-sided binomial $p = 0.065$, with the registered interval on the effect spanning one half. Directionally consistent, and short of the level I committed to. So the paper reports the association and refuses the causal sentence, and the pre-registration is what makes that refusal cost me nothing to write.

## Mitigation has to match the dimension *and* the direction

The companion paper's defense against this failure mode was a distrust fence: when the model's prediction is contradicted at some state, mark a ball around it and make the planner treat imagined paths through it as untrustworthy. On the patch instrument, that worked.

On the ring, at its calibrated radius, it does nothing at all — and the reason is a counting argument, not an implementation detail. A point fence is a zero-dimensional object; the ring's reachable boundary is a one-dimensional curve roughly 16 world-units long. Sealing a curve with $\varepsilon$-balls needs covering-number-many of them, boundary length over fence radius, and the planner concedes two to four contacts per episode while re-routing through the unfenced arc.

<table class="cwm-table">
<thead><tr><th>Defense</th><th style="text-align:right">play cost</th><th>Why</th></tr></thead>
<tbody>
<tr><td>Point fences, calibrated radius</td><td class="n">0.999 → 1.003</td><td>0-dimensional cover of a 1-dimensional boundary</td></tr>
<tr><td>Point fences, 4× radius</td><td class="n">0.999 → 0.742</td><td>partial relief once the balls reach the geometry's scale</td></tr>
<tr><td>Dimension-matched fence, per episode</td><td class="n">0.999 → 0.957</td><td>right shape, forgotten every episode</td></tr>
<tr><td><strong>Dimension-matched, persisted</strong></td><td class="n">0.999 → <strong>0.058</strong></td><td>two lessons total, truth-equal returns from episode 2</td></tr>
<tr><td>Any distrust fence, invented mode</td><td class="n">1.769 → 1.769</td><td>fires 18.6 times per episode, changes nothing</td></tr>
<tr><td><strong>Freedom patch, invented mode</strong></td><td class="n">1.769 → <strong>0.029</strong></td><td>the dual certificate: un-freeze where the model was over-pessimistic</td></tr>
</tbody></table>

The last two rows are the ones I did not see coming. Point the same machinery at the *opposite* error — a model that hallucinates an obstacle where the world is empty, which costs more than the phantom-freedom case at 1.769 — and every distrust variant is inert by construction: it fires constantly, because the model is being contradicted everywhere, and it has nothing to offer, because distrust cannot manufacture the freedom the planner needs. The defense that works is the dual: mark the states where the model was refuted as *too pessimistic* and let imagination run free there. That collapses it at once.

Two wrongnesses, opposite defenses, and each defense's cost is set by how often its failure lies to you. A false obstruction refutes itself at every single step, so one episode teaches the planner everything. A false freedom refutes itself only at the rare boundary, so you have to pay for coverage. Same geometry as the rest of the paper, seen from the planner's side.

## In *n* dimensions both knobs max out

One extension, because it separates two things that look like one. Replace the ring with an enclosing shell in $n$ dimensions and sweep $n$.

The **rarity** of contact collapses geometrically — a measured factor of 0.411 per dimension, with the exponential rate proved for an isotropic action interface and an explicit bound for the instrument's own. That factor comes from a 10,000-rollout sweep of the cone event, because the cheaper calibration runs out of resolution first: contacts fall to 1 in 600 rollouts by $n = 4$, and past it 600 rollouts can no longer separate the cells (0 in 600 at $n = 5$, 1 in 600 again at $n = 6$). Either way mis-synthesis becomes near-certain: the gate's sample almost never contains the thing the spec omitted.

Meanwhile the **danger** does not decay at all. A competent planner with a vector action interface is exploited at `play_cost` ≈ 1.0 at every $n \le 6$: it drives straight at the lode and gets pinned. Rarity lives on the synthesis axis, reachability on the play axis, and they are independent knobs. A high-dimensional enclosed mode maxes out both — the omission is almost certain to happen and fully exploitable when it does.

(One methods note that cost me a day: the same sweep with the *scalar* planner's candidate set measures zero danger at every $n$, and that is a property of the planner, not the geometry. Its candidates lack the axial sequences that drive straight at the shell. Competence is a property of the action interface, and an incidental planner weakness can hide a fully exploitable model.)

## What I take from this

A sampling gate certifies the reachable restriction of your model and nothing else. That is the whole series in one sentence, and the ring is where it stops being a slogan: beyond reach, the model's content is a free choice that no test can pin and no planner can bill you for — a gauge, and the wrong-topology artifact that exploits it is both uncatchable and harmless, by theorem.

Which flips the question you should be asking. Not "is the model right?" but **"does the place where it is wrong intersect the operative reach of whatever is planning against it?"** Three consequences I would carry into a real system:

- **Reach, not shape.** The geometry and even the topology of an omission tell you nothing about consequence on their own. The same hole, moved from in front of the goal to behind it, went from harmless to fully exploited without changing a single invariant. So an audit that classifies model errors by kind, and not by whether a plan crosses them, is measuring the wrong thing.
- **Your evidence summary is a sensor with a resolution.** If anything in the loop — a monitor, a report, a retrieval step, a topological or statistical summary — decides *what shape the evidence has*, its blind spot propagates into what gets certified. Ours reports a closed loop for every gap narrower than two arc-units, and the artifacts follow the report. More data made it worse, not better.
- **Fences pay for dimension and direction.** A defense built from points cannot seal a curve, and a defense built from distrust cannot repair over-pessimism. Match the boundary's dimension, persist what you learn across episodes, and know which of the two errors you are defending against — they need opposite certificates.

If you want the formal version — the gate quotient, the unfalsifiable-and-harmless theorem, the two-sided resolution sandwich, the $n$-dimensional rate, and which parts are machine-checked in Lean — it is in the [preprint](https://arxiv.org/abs/XXXX.XXXXX), and the [code and every result artifact are open](https://github.com/JaviMaligno/code-world-models).

---

*Preprint: "An Enclosed Mode Is a Gauge Choice" ([arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX)) · [code](https://github.com/JaviMaligno/code-world-models). Companion papers: [An Omitted Mode Is a Rare Rule](https://arxiv.org/abs/2608.17956) and the post about it — [An LLM Can Infer the Rule You Forgot](/en/blog/infer-the-rule-in-one-dimension) — and [When a Verified World Model Still Loses](https://arxiv.org/abs/2607.14169).*
