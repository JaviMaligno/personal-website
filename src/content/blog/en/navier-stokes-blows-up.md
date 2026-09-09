---
title: "Navier–Stokes Blows Up, and the Blow-up Is a Vortex You Can Picture"
description: "OpenAI published a Lean-verified proof that the 3D Navier–Stokes equations can develop a singularity in finite time. Five things the headlines skip: the model wasn't Astra, the break happens exactly where the fluid stops being a fluid, the solution is a spinning skater, a shelf of conditional theorems just changed status, and the route was opened in Madrid by two mathematicians nobody is paying."
pubDate: 2026-09-09
tags: ["AI", "Mathematics", "Agents", "Research", "OpenAI"]
lang: en
translationKey: navier-stokes-blows-up
heroImage: "/blog/navier-stokes-blows-up.png"
linkedinImage: /blog/navier-stokes-blows-up-vortex.png
linkedinLinks:
  - label: "OpenAI's announcement"
    url: "https://openai.com/index/navier-stokes-solution/"
  - label: "The paper"
    url: "https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf"
  - label: "Lean formalization"
    url: "https://github.com/openai/NavierStokesAndEuler"
  - label: "Buckmaster's statement"
    url: "https://cims.nyu.edu/~tristanb/statement.pdf"
  - label: "Tao on the Alpöge–Buckmaster results"
    url: "https://terrytao.wordpress.com/2026/09/07/finite-time-blowup-with-smooth-forcing-term-for-the-incompressible-porous-medium-boussinesq-and-incompressible-euler-equations/"
---

On 8 September OpenAI [published a proof](https://openai.com/index/navier-stokes-solution/) that the three-dimensional incompressible Navier–Stokes equations can develop a singularity in finite time: a smooth fluid, starting from rest under a smooth external force, whose speed grows without bound while its total energy stays finite. The proof comes as a [166-page paper](https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf) and a [Lean formalization](https://github.com/openai/NavierStokesAndEuler). That is the negative resolution of the Navier–Stokes Millennium Prize problem as Clay wrote it, ninety years after Leray.

The coverage has been about the million dollars and about who got there first. Both of those are better questions than the coverage makes them, and neither is the most interesting thing here. Five things, none of which fits in a headline: which model did it, what exactly "breaks" and for whom, why the solution is one you can draw on a napkin, what happens to the theorems that had been waiting on this answer, and who the prize would belong to if anyone claimed it.

<style>
.ns-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.ns-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.ns-fig img{display:block;width:100%;height:auto;margin:0;border:0;border-radius:.6rem}
.ns-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## It wasn't Astra

The proof did not come from GPT-6 Astra, the model OpenAI released five days earlier. It came from an internal model that has been training since 28 August and that OpenAI describes as "significantly more capable than GPT-6 Astra", with "unprecedented performance in our benchmarks, including mathematics". Training is still ongoing. OpenAI does not call it a mathematics model; the jump it reports is across its benchmarks, with mathematics among them. Astra's only role in the story was the last step: it produced the Lean formalization and verification in 17 hours.

What ran on top of that model is more interesting than the model, at least for anyone who builds agent systems. It was a swarm:

| | |
|---|---|
| Concurrent agents in the Navier–Stokes group | on the order of 10,000 |
| Tools | a cached snapshot of the internet, code execution |
| Wall-clock to the result | about 88 hours (1 to 5 September) |
| Messages exchanged | 2.7 million |
| Output tokens | about 130 billion |
| Lean formalization and verification | 17 hours, GPT-6 Astra |
| Across all problems attempted | 4.9 million messages, 300 billion tokens |

Three design choices stand out. First, they did not ask the swarm to *solve* Navier–Stokes. They split it into groups and prompted each with a different one of the four statements in the official problem: A and B (solutions always stay smooth) to some groups, C and D (they can break down) to others. Nobody bet on a direction. Second, they gave separate groups "easier" problems, and one of those fell first: the unforced Euler equations, the same question with viscosity removed, resolved by about 100 agents in roughly 50 hours. That proof was then fed as a prompt to the Navier–Stokes groups, and agents were pulled off the other Millennium problems to work on it. Third, groups could only talk within themselves; cross-pollination between groups was done by Codex, used to consolidate the most useful insights from each group into follow-up prompts. The group that found the proof was steered that way.

<figure class="ns-fig">
<svg viewBox="0 0 600 190" role="img" aria-label="Timeline of OpenAI's Navier–Stokes effort: training of the internal model starts on 28 August, a swarm of about ten thousand agents is launched on 1 September on every Millennium problem, the unforced Euler question falls first after about fifty hours, agents are shifted to Navier–Stokes with the Euler proof as prompt, the result arrives on 5 September after eighty-eight hours, Lean verification by GPT-6 Astra takes seventeen more hours, and the proof is published on 8 September">
  <defs>
    <marker id="ns-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#64748b"/>
    </marker>
  </defs>
  <line x1="28" y1="100" x2="572" y2="100" stroke="#64748b" stroke-width="2" marker-end="url(#ns-ar)"/>
  <g fill="#1a1a24" stroke="#94a3b8" stroke-width="2">
    <circle cx="60" cy="100" r="6"/>
    <circle cx="170" cy="100" r="6"/>
    <circle cx="275" cy="100" r="6"/>
    <circle cx="400" cy="100" r="6" stroke="#2dd4bf"/>
    <circle cx="470" cy="100" r="6"/>
    <circle cx="545" cy="100" r="6" stroke="#f59e0b"/>
  </g>
  <g fill="#2dd4bf"><circle cx="400" cy="100" r="3"/></g>
  <g fill="#f59e0b"><circle cx="545" cy="100" r="3"/></g>
  <g text-anchor="middle" font-size="10.5" fill="#e2e8f0">
    <text x="60" y="62" font-weight="700">Aug 28</text>
    <text x="60" y="76" fill="#94a3b8">internal model</text>
    <text x="60" y="88" fill="#94a3b8">starts training</text>
    <text x="170" y="128" font-weight="700">Sep 1</text>
    <text x="170" y="142" fill="#94a3b8">~10,000 agents on</text>
    <text x="170" y="154" fill="#94a3b8">every Millennium problem</text>
    <text x="275" y="62" font-weight="700">~50 h in</text>
    <text x="275" y="76" fill="#94a3b8">unforced Euler falls</text>
    <text x="275" y="88" fill="#94a3b8">(~100 agents)</text>
    <text x="400" y="128" font-weight="700" fill="#5eead4">Sep 5 · 88 h</text>
    <text x="400" y="142" fill="#94a3b8">Navier–Stokes proof</text>
    <text x="400" y="154" fill="#94a3b8">2.7 M msgs · 130 B tokens</text>
    <text x="470" y="62" font-weight="700">Sep 6</text>
    <text x="470" y="76" fill="#94a3b8">Lean verified</text>
    <text x="470" y="88" fill="#94a3b8">17 h, GPT-6 Astra</text>
    <text x="545" y="128" font-weight="700" fill="#fbbf24">Sep 8</text>
    <text x="545" y="142" fill="#94a3b8">published</text>
  </g>
  <path d="M305,100 C345,100 345,40 362,40 L382,40 C397,40 397,90 400,94" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="4 3"/>
  <rect x="300" y="22" width="130" height="14" fill="#1a1a24"/>
  <text x="365" y="33" text-anchor="middle" font-size="9.5" fill="#fbbf24">Euler proof fed as prompt, agents shifted</text>
</svg>
<figcaption>The timeline OpenAI reports. Astra appears once, at the verification step. The unforced Euler result, a stepping stone here, would have been a major result on its own.</figcaption>
</figure>

I have written before about [what agents actually say to each other](/en/blog/what-agents-say-to-each-other) when you let them talk; 2.7 million messages is that question at a scale where reading the transcript is not an option, and where the only human-legible layer is the consolidation step.

## What was proven, exactly

The theorem is short enough to state. For every positive viscosity, there is a smooth external force, compactly supported in space and time, such that the fluid that starts at rest under that force is smooth for all times before 1, has bounded kinetic energy throughout, and has a maximum speed that goes to infinity as time approaches 1. Consequently there is no smooth, finite-energy solution for all time with that force and that initial condition.

That is statement C of [Fefferman's official problem description](https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf), and compact support gives statement D, the periodic version, for free. The official problem is settled if you prove *any one* of four statements, and the four are not symmetric:

<figure class="ns-fig">
<svg viewBox="0 0 600 236" role="img" aria-label="The four statements of the Clay Navier–Stokes problem as a two-by-two grid: rows are whole space and periodic box, columns are regularity with zero force and breakdown with a smooth force allowed. Statements A and B, regularity with no force, remain open. Statements C and D, breakdown under a smooth force, were proved in September 2026">
  <g font-size="11" fill="#94a3b8" text-anchor="middle">
    <text x="245" y="26" font-weight="700" fill="#e2e8f0">Regularity</text>
    <text x="245" y="40" font-size="10">every smooth initial state, no force (f ≡ 0)</text>
    <text x="455" y="26" font-weight="700" fill="#e2e8f0">Breakdown</text>
    <text x="455" y="40" font-size="10">some initial state, some smooth force f</text>
  </g>
  <g font-size="11" fill="#e2e8f0" text-anchor="end">
    <text x="130" y="96" font-weight="700">whole space ℝ³</text>
    <text x="130" y="176" font-weight="700">periodic box ℝ³/ℤ³</text>
  </g>
  <g>
    <rect x="145" y="60" width="200" height="70" rx="8" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.18)" stroke-width="1.5" stroke-dasharray="5 4"/>
    <rect x="145" y="140" width="200" height="70" rx="8" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.18)" stroke-width="1.5" stroke-dasharray="5 4"/>
    <rect x="355" y="60" width="200" height="70" rx="8" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="2"/>
    <rect x="355" y="140" width="200" height="70" rx="8" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="2"/>
  </g>
  <g text-anchor="middle">
    <text x="245" y="92" font-size="24" font-weight="700" fill="#94a3b8">A</text>
    <text x="245" y="112" font-size="10.5" fill="#94a3b8">still open</text>
    <text x="245" y="172" font-size="24" font-weight="700" fill="#94a3b8">B</text>
    <text x="245" y="192" font-size="10.5" fill="#94a3b8">still open</text>
    <text x="455" y="92" font-size="24" font-weight="700" fill="#5eead4">C</text>
    <text x="455" y="112" font-size="10.5" fill="#5eead4">proved · Sep 2026</text>
    <text x="455" y="172" font-size="24" font-weight="700" fill="#5eead4">D</text>
    <text x="455" y="192" font-size="10.5" fill="#5eead4">proved · Sep 2026 (follows from C)</text>
  </g>
  <text x="300" y="228" text-anchor="middle" font-size="10" fill="#64748b">Proving any one of the four settles the Millennium problem. A and B would have been a yes; C and D are a no.</text>
</svg>
<figcaption>A and B ask whether a fluid left alone can break down; nobody knows that yet. C and D ask whether a fluid pushed by a smooth force can; now it can.</figcaption>
</figure>

The force is the part to be honest about. It is not gravity, and it was not chosen first. The paper says it plainly: for any incompressible flow you can *define* the force as whatever residual the equations leave, and then the equations hold by construction. The whole difficulty is choosing a flow that blows up while that residual stays smooth, all the way through the singular time, with all its derivatives. The background vortex alone leaves a residual that diverges; the paper cancels it with spatially oscillatory pulses and then removes the remaining errors order by order. That is what the 166 pages are for. It is also why some mathematicians will call this a resolution of the problem as written and others will call it a loophole in the problem as written. Both are right: the statement is closed, and the question most people mean by it, whether a fluid with no one pushing it can blow up, is exactly as open as it was last week. OpenAI says it will not claim the prize.

## Where the fluid stops being a fluid

The Navier–Stokes equations are Newton's second law applied to a continuum. There are no molecules in them; a "fluid parcel" is a mathematical point with a velocity, and the equations describe how those velocities push each other around. Everything they are used for, aircraft design, weather forecasting, blood flow, relies on that continuum picture being good enough.

A singularity is the equations exiting that picture from the inside. In the construction, the core of the vortex has a radius that shrinks like the square root of the time left, and a peak speed that grows slightly faster than one over that square root. Long before the time left reaches zero, the core is narrower than the mean free path of air molecules, the speed is past the speed of sound, and incompressibility, the assumption that the fluid cannot be squeezed, is already false. At that point the continuum has nothing to say. To keep modelling the system you would have to track the particles one by one: kinetic theory, molecular dynamics, whichever level of description has not yet given up. The equations do not predict an infinitely fast fluid. They predict their own boundary.

Who does this affect? Almost nobody who uses them. The singularity needs a force engineered to cancel four diverging terms at every order at a single point in space and time; nothing in a wing, a hurricane, or an artery supplies it. Numerical solvers already regularize everything below the grid scale. And the core's kinetic energy actually *decreases* to zero as the singularity approaches, so the whole event carries vanishing energy in a vanishing volume. Nobody re-runs a simulation tomorrow. My reading is that the practical consequence for the overwhelming majority of fluid mechanics is nil, and I would be surprised if any engineering code changes because of this. What has changed is the status of the model: we used to believe the equations were a closed, self-consistent description that merely happened to be applied outside its range sometimes. Now we know the equations themselves contain the exit, and can be driven to it with a smooth push.

## The intuitive part

The construction is a vortex that spirals inward while stretching along its axis. Anyone who has watched water go down a drain can read the shape of it. These are the threads of the core at three successive times, integrated from the leading-order field the paper describes:

<figure class="ns-fig">
<img src="/blog/navier-stokes-vortex-3d.png" alt="Three snapshots of the vortex core as a bundle of fluid threads: teal threads spiral inward and spin up near a mid-plane while amber threads leave along the axis above and below it, and from one snapshot to the next the bundle thins faster than it shortens" aria-label="Three snapshots of the vortex core as a bundle of fluid threads: teal threads spiral inward and spin up near a mid-plane while amber threads leave along the axis above and below it, and from one snapshot to the next the bundle thins faster than it shortens" />
<figcaption>Threads integrated from the paper's leading-order field, not traced from its figure: radial inflow, azimuthal spin-up, and axial outflow on both sides of the dividing plane. The axial stretching is exaggerated, as it is in the paper's own schematic, because at the true exponent the difference would be invisible. <a href="https://github.com/JaviMaligno/personal-website/blob/main/scripts/figures/navier-stokes-vortex-3d.py">Script</a>.</figcaption>
</figure>

Seen from the side, with the scalings written onto it, the same object:

<figure class="ns-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Three snapshots of the blow-up vortex at successive times. Fluid spirals inward toward a vertical axis and flows out along the axis above and below a dividing plane. From one snapshot to the next the core's radius shrinks faster than its height, the rotation speeds up, and the peak speed grows without bound while the kinetic energy of the core goes to zero">
  <defs>
    <marker id="ns-ab" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#f59e0b"/>
    </marker>
    <marker id="ns-at" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#2dd4bf"/>
    </marker>
  </defs>
  <!-- panel 1 -->
  <g transform="translate(110,160)">
    <line x1="0" y1="-118" x2="0" y2="118" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
    <ellipse cx="0" cy="0" rx="78" ry="32.8" fill="rgba(45,212,191,0.07)" stroke="none"/>
    <path d="M78.0,0.0 L77.4,3.1 L76.1,6.1 L74.1,9.0 L71.5,11.9 L68.3,14.6 L64.5,17.2 L60.1,19.6 L55.3,21.8 L50.0,23.8 L44.2,25.6 L38.2,27.1 L31.8,28.4 L25.2,29.4 L18.4,30.2 L11.6,30.7 L4.6,30.9 L-2.3,30.8 L-9.2,30.5 L-15.9,29.8 L-22.4,29.0 L-28.7,27.9 L-34.7,26.5 L-40.3,24.9 L-45.5,23.1 L-50.3,21.1 L-54.6,19.0 L-58.4,16.7 L-61.7,14.2 L-64.3,11.7 L-66.4,9.1 L-67.9,6.4 L-68.7,3.6 L-69.0,0.9 L-68.6,-1.8 L-67.6,-4.5 L-66.0,-7.1 L-63.9,-9.7 L-61.2,-12.1 L-58.0,-14.4 L-54.3,-16.6 L-50.1,-18.6 L-45.5,-20.4 L-40.6,-22.0 L-35.4,-23.4 L-29.8,-24.6 L-24.1,-25.6 L-18.2,-26.3 L-12.2,-26.8 L-6.1,-27.0 L-0.0,-27.0 L6.0,-26.8 L12.0,-26.3 L17.7,-25.6 L23.3,-24.7 L28.6,-23.6 L33.6,-22.2 L38.3,-20.7 L42.6,-19.0 L46.4,-17.2 L49.9,-15.2 L52.8,-13.1 L55.3,-10.9 L57.2,-8.7 L58.6,-6.3 L59.5,-4.0 L59.9,-1.6 L59.7,0.8 L59.0,3.1 L57.7,5.4 L56.0,7.6 L53.8,9.8 L51.1,11.8 L48.0,13.7 L44.5,15.5 L40.7,17.1 L36.5,18.5 L32.0,19.8 L27.3,20.9 L22.4,21.8 L17.4,22.4 L12.2,22.9 L7.0,23.2 L1.7,23.2 L-3.5,23.1 L-8.6,22.7 L-13.6,22.2 L-18.4,21.4 L-23.0,20.5 L-27.3,19.4 L-31.4,18.2 L-35.2,16.7 L-38.6,15.2 L-41.6,13.5 L-44.2,11.8 L-46.4,9.9 L-48.2,8.0 L-49.5,6.0 L-50.3,4.0 L-50.7,2.0 L-50.7,0.0 L-50.2,-2.0 L-49.3,-3.9 L-47.9,-5.8 L-46.1,-7.7 L-44.0,-9.4 L-41.4,-11.0 L-38.6,-12.6 L-35.4,-13.9 L-31.9,-15.2 L-28.2,-16.3 L-24.3,-17.2 L-20.2,-18.0 L-16.0,-18.6 L-11.7,-19.1 L-7.3,-19.3 L-2.9,-19.4 L1.4,-19.3 L5.7,-19.1 L9.9,-18.7 L14.0,-18.1 L17.9,-17.3 L21.5,-16.4 L25.0,-15.4 L28.1,-14.3 L31.0,-13.0 L33.6,-11.7 L35.8,-10.2 L37.7,-8.7 L39.3,-7.1 L40.4,-5.5 L41.2,-3.9 L41.6,-2.2 L41.7,-0.6 L41.3,1.1 L40.6,2.7 L39.6,4.3 L38.2,5.8 L36.5,7.2 L34.5,8.6 L32.2,9.8 L29.6,11.0 L26.9,12.0 L23.9,12.9 L20.7,13.7 L17.4,14.4 L14.0,14.9 L10.6,15.3 L7.0,15.5 L3.5,15.6 L0.0,15.6 L-3.5,15.4 L-6.8,15.1 L-10.1,14.6 L-13.2,14.0 L-16.2,13.4 L-19.0,12.6 L-21.5,11.7 L-23.9,10.7 L-25.9,9.6 L-27.8,8.5 L-29.3,7.3 L-30.6,6.0 L-31.5,4.8 L-32.2,3.5 L-32.5,2.2 L-32.6,0.9 L-32.4,-0.4 L-31.9,-1.7 L-31.1,-2.9 L-30.0,-4.1 L-28.7,-5.2 L-27.2,-6.3 L-25.5,-7.3 L-23.5,-8.2 L-21.4,-9.0 L-19.1,-9.7 L-16.7,-10.3 L-14.2,-10.8 L-11.6,-11.2 L-8.9,-11.5 L-6.2,-11.7 L-3.5,-11.8 L-0.9,-11.8 L1.7,-11.6 L4.3,-11.4 L6.8,-11.1 L9.1,-10.6 L11.4,-10.1 L13.4,-9.5 L15.4,-8.9 L17.1,-8.1 L18.6,-7.4 L20.0,-6.5 L21.1,-5.6 L22.1,-4.7 L22.8,-3.8 L23.3,-2.8 L23.5,-1.9 L23.6,-0.9 L23.4,-0.0" fill="none" stroke="#2dd4bf" stroke-width="2.0" stroke-linecap="round" marker-end="url(#ns-at)"/>
    <path d="M-14,-38 L-14,-98" fill="none" stroke="#f59e0b" stroke-width="2.2" marker-end="url(#ns-ab)"/>
    <path d="M14,38 L14,98" fill="none" stroke="#f59e0b" stroke-width="2.2" marker-end="url(#ns-ab)"/>
    <line x1="-78" y1="108" x2="78" y2="108" stroke="#64748b" stroke-width="1"/>
    <line x1="-78" y1="104" x2="-78" y2="112" stroke="#64748b" stroke-width="1"/>
    <line x1="78" y1="104" x2="78" y2="112" stroke="#64748b" stroke-width="1"/>
    <text x="0" y="122" text-anchor="middle" font-size="9.5" fill="#94a3b8">radius</text>
    <text x="0" y="140" text-anchor="middle" font-size="11" font-weight="700" fill="#e2e8f0">t₁</text>
  </g>
  <!-- panel 2 -->
  <g transform="translate(300,160)">
    <line x1="0" y1="-118" x2="0" y2="118" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
    <ellipse cx="0" cy="0" rx="50" ry="21.0" fill="rgba(45,212,191,0.07)" stroke="none"/>
    <path d="M50.0,0.0 L49.6,2.0 L48.8,3.9 L47.5,5.8 L45.8,7.6 L43.8,9.4 L41.3,11.0 L38.5,12.6 L35.4,14.0 L32.0,15.3 L28.4,16.4 L24.5,17.4 L20.4,18.2 L16.2,18.9 L11.8,19.3 L7.4,19.7 L3.0,19.8 L-1.5,19.7 L-5.9,19.5 L-10.2,19.1 L-14.4,18.6 L-18.4,17.9 L-22.2,17.0 L-25.8,16.0 L-29.2,14.8 L-32.3,13.5 L-35.0,12.2 L-37.4,10.7 L-39.5,9.1 L-41.2,7.5 L-42.6,5.8 L-43.5,4.1 L-44.0,2.3 L-44.2,0.6 L-44.0,-1.2 L-43.3,-2.9 L-42.3,-4.6 L-41.0,-6.2 L-39.2,-7.8 L-37.2,-9.2 L-34.8,-10.6 L-32.1,-11.9 L-29.2,-13.1 L-26.0,-14.1 L-22.7,-15.0 L-19.1,-15.8 L-15.4,-16.4 L-11.7,-16.8 L-7.8,-17.2 L-3.9,-17.3 L-0.0,-17.3 L3.9,-17.2 L7.7,-16.9 L11.4,-16.4 L14.9,-15.8 L18.3,-15.1 L21.5,-14.3 L24.5,-13.3 L27.3,-12.2 L29.8,-11.0 L32.0,-9.8 L33.8,-8.4 L35.4,-7.0 L36.7,-5.5 L37.6,-4.1 L38.1,-2.5 L38.4,-1.0 L38.3,0.5 L37.8,2.0 L37.0,3.5 L35.9,4.9 L34.5,6.3 L32.8,7.6 L30.8,8.8 L28.5,9.9 L26.1,11.0 L23.4,11.9 L20.5,12.7 L17.5,13.4 L14.4,13.9 L11.1,14.4 L7.8,14.7 L4.5,14.9 L1.1,14.9 L-2.2,14.8 L-5.5,14.6 L-8.7,14.2 L-11.8,13.7 L-14.7,13.1 L-17.5,12.4 L-20.1,11.6 L-22.5,10.7 L-24.7,9.7 L-26.6,8.7 L-28.3,7.6 L-29.7,6.4 L-30.9,5.1 L-31.7,3.9 L-32.3,2.6 L-32.5,1.3 L-32.5,0.0 L-32.2,-1.3 L-31.6,-2.5 L-30.7,-3.7 L-29.6,-4.9 L-28.2,-6.0 L-26.6,-7.1 L-24.7,-8.1 L-22.7,-8.9 L-20.5,-9.7 L-18.1,-10.4 L-15.6,-11.1 L-12.9,-11.6 L-10.2,-11.9 L-7.5,-12.2 L-4.7,-12.4 L-1.9,-12.4 L0.9,-12.4 L3.7,-12.2 L6.4,-12.0 L9.0,-11.6 L11.4,-11.1 L13.8,-10.5 L16.0,-9.9 L18.0,-9.2 L19.9,-8.4 L21.5,-7.5 L23.0,-6.6 L24.2,-5.6 L25.2,-4.6 L25.9,-3.5 L26.4,-2.5 L26.7,-1.4 L26.7,-0.4 L26.5,0.7 L26.1,1.7 L25.4,2.7 L24.5,3.7 L23.4,4.6 L22.1,5.5 L20.6,6.3 L19.0,7.0 L17.2,7.7 L15.3,8.3 L13.3,8.8 L11.2,9.2 L9.0,9.5 L6.8,9.8 L4.5,9.9 L2.3,10.0 L0.0,10.0 L-2.2,9.9 L-4.4,9.7 L-6.5,9.4 L-8.5,9.0 L-10.4,8.6 L-12.2,8.0 L-13.8,7.5 L-15.3,6.8 L-16.6,6.2 L-17.8,5.4 L-18.8,4.7 L-19.6,3.9 L-20.2,3.1 L-20.6,2.2 L-20.9,1.4 L-20.9,0.6 L-20.8,-0.3 L-20.4,-1.1 L-19.9,-1.9 L-19.3,-2.6 L-18.4,-3.3 L-17.4,-4.0 L-16.3,-4.7 L-15.1,-5.2 L-13.7,-5.8 L-12.2,-6.2 L-10.7,-6.6 L-9.1,-6.9 L-7.4,-7.2 L-5.7,-7.4 L-4.0,-7.5 L-2.3,-7.6 L-0.6,-7.5 L1.1,-7.5 L2.8,-7.3 L4.3,-7.1 L5.9,-6.8 L7.3,-6.5 L8.6,-6.1 L9.8,-5.7 L11.0,-5.2 L12.0,-4.7 L12.8,-4.2 L13.6,-3.6 L14.1,-3.0 L14.6,-2.4 L14.9,-1.8 L15.1,-1.2 L15.1,-0.6 L15.0,-0.0" fill="none" stroke="#2dd4bf" stroke-width="1.9" stroke-linecap="round" marker-end="url(#ns-at)"/>
    <path d="M-9,-26 L-9,-86" fill="none" stroke="#f59e0b" stroke-width="2.6" marker-end="url(#ns-ab)"/>
    <path d="M9,26 L9,86" fill="none" stroke="#f59e0b" stroke-width="2.6" marker-end="url(#ns-ab)"/>
    <text x="0" y="140" text-anchor="middle" font-size="11" font-weight="700" fill="#e2e8f0">t₂</text>
  </g>
  <!-- panel 3 -->
  <g transform="translate(490,160)">
    <line x1="0" y1="-118" x2="0" y2="118" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
    <ellipse cx="0" cy="0" rx="27" ry="11.3" fill="rgba(45,212,191,0.07)" stroke="none"/>
    <path d="M27.0,0.0 L26.8,1.1 L26.3,2.1 L25.7,3.1 L24.8,4.1 L23.6,5.1 L22.3,5.9 L20.8,6.8 L19.1,7.5 L17.3,8.2 L15.3,8.9 L13.2,9.4 L11.0,9.8 L8.7,10.2 L6.4,10.4 L4.0,10.6 L1.6,10.7 L-0.8,10.7 L-3.2,10.5 L-5.5,10.3 L-7.8,10.0 L-9.9,9.6 L-12.0,9.2 L-14.0,8.6 L-15.8,8.0 L-17.4,7.3 L-18.9,6.6 L-20.2,5.8 L-21.3,4.9 L-22.3,4.0 L-23.0,3.1 L-23.5,2.2 L-23.8,1.3 L-23.9,0.3 L-23.7,-0.6 L-23.4,-1.6 L-22.9,-2.5 L-22.1,-3.3 L-21.2,-4.2 L-20.1,-5.0 L-18.8,-5.7 L-17.3,-6.4 L-15.8,-7.1 L-14.1,-7.6 L-12.2,-8.1 L-10.3,-8.5 L-8.3,-8.8 L-6.3,-9.1 L-4.2,-9.3 L-2.1,-9.4 L-0.0,-9.4 L2.1,-9.3 L4.1,-9.1 L6.1,-8.9 L8.1,-8.6 L9.9,-8.2 L11.6,-7.7 L13.2,-7.2 L14.7,-6.6 L16.1,-6.0 L17.3,-5.3 L18.3,-4.5 L19.1,-3.8 L19.8,-3.0 L20.3,-2.2 L20.6,-1.4 L20.7,-0.5 L20.7,0.3 L20.4,1.1 L20.0,1.9 L19.4,2.6 L18.6,3.4 L17.7,4.1 L16.6,4.7 L15.4,5.4 L14.1,5.9 L12.6,6.4 L11.1,6.9 L9.5,7.2 L7.8,7.5 L6.0,7.8 L4.2,7.9 L2.4,8.0 L0.6,8.0 L-1.2,8.0 L-3.0,7.9 L-4.7,7.7 L-6.4,7.4 L-8.0,7.1 L-9.5,6.7 L-10.9,6.3 L-12.2,5.8 L-13.3,5.3 L-14.4,4.7 L-15.3,4.1 L-16.1,3.4 L-16.7,2.8 L-17.1,2.1 L-17.4,1.4 L-17.6,0.7 L-17.6,0.0 L-17.4,-0.7 L-17.1,-1.4 L-16.6,-2.0 L-16.0,-2.7 L-15.2,-3.3 L-14.3,-3.8 L-13.3,-4.3 L-12.2,-4.8 L-11.0,-5.3 L-9.8,-5.6 L-8.4,-6.0 L-7.0,-6.2 L-5.5,-6.4 L-4.0,-6.6 L-2.5,-6.7 L-1.0,-6.7 L0.5,-6.7 L2.0,-6.6 L3.4,-6.5 L4.8,-6.3 L6.2,-6.0 L7.5,-5.7 L8.6,-5.3 L9.7,-4.9 L10.7,-4.5 L11.6,-4.0 L12.4,-3.5 L13.1,-3.0 L13.6,-2.5 L14.0,-1.9 L14.3,-1.3 L14.4,-0.8 L14.4,-0.2 L14.3,0.4 L14.1,0.9 L13.7,1.5 L13.2,2.0 L12.6,2.5 L11.9,3.0 L11.1,3.4 L10.3,3.8 L9.3,4.2 L8.3,4.5 L7.2,4.7 L6.0,5.0 L4.9,5.2 L3.7,5.3 L2.4,5.4 L1.2,5.4 L0.0,5.4 L-1.2,5.3 L-2.4,5.2 L-3.5,5.1 L-4.6,4.9 L-5.6,4.6 L-6.6,4.3 L-7.5,4.0 L-8.3,3.7 L-9.0,3.3 L-9.6,2.9 L-10.1,2.5 L-10.6,2.1 L-10.9,1.6 L-11.1,1.2 L-11.3,0.7 L-11.3,0.3 L-11.2,-0.1 L-11.0,-0.6 L-10.8,-1.0 L-10.4,-1.4 L-9.9,-1.8 L-9.4,-2.2 L-8.8,-2.5 L-8.1,-2.8 L-7.4,-3.1 L-6.6,-3.4 L-5.8,-3.6 L-4.9,-3.7 L-4.0,-3.9 L-3.1,-4.0 L-2.2,-4.1 L-1.2,-4.1 L-0.3,-4.1 L0.6,-4.0 L1.5,-3.9 L2.3,-3.8 L3.2,-3.7 L3.9,-3.5 L4.7,-3.3 L5.3,-3.1 L5.9,-2.8 L6.5,-2.5 L6.9,-2.3 L7.3,-2.0 L7.6,-1.6 L7.9,-1.3 L8.1,-1.0 L8.1,-0.7 L8.2,-0.3 L8.1,-0.0" fill="none" stroke="#2dd4bf" stroke-width="1.8" stroke-linecap="round" marker-end="url(#ns-at)"/>
    <path d="M-5,-16 L-5,-74" fill="none" stroke="#f59e0b" stroke-width="3.0" marker-end="url(#ns-ab)"/>
    <path d="M5,16 L5,74" fill="none" stroke="#f59e0b" stroke-width="3.0" marker-end="url(#ns-ab)"/>
    <text x="0" y="140" text-anchor="middle" font-size="11" font-weight="700" fill="#e2e8f0">t₃ → 1</text>
  </g>
  <g font-size="10" fill="#94a3b8">
    <text x="20" y="18"><tspan fill="#5eead4">teal</tspan>: inward spiral, spinning up</text>
    <text x="20" y="32"><tspan fill="#fbbf24">amber</tspan>: axial outflow above and below the mid-plane</text>
    <text x="580" y="18" text-anchor="end">τ = time left before the singularity</text>
  </g>
  <g font-size="10" fill="#94a3b8" text-anchor="middle">
    <text x="300" y="318">radius ∝ τ<tspan font-size="7" baseline-shift="super">1/2</tspan>  ·  height ∝ τ<tspan font-size="7" baseline-shift="super">1/2−h</tspan>  ·  h &lt; 1/100  ·  peak speed ∝ τ<tspan font-size="7" baseline-shift="super">−1/2−h</tspan>  ·  core energy ∝ τ<tspan font-size="7" baseline-shift="super">1/2−3h</tspan> → 0</text>
  </g>
</svg>
<figcaption>The leading-order flow in the paper's own scalings: the core thins faster than it shortens, by an exponent smaller than one hundredth, and that tiny mismatch is the entire mechanism.</figcaption>
</figure>

Three ideas, all old:

- **Angular momentum.** A parcel of fluid with no torque on it conserves its angular momentum per unit mass, radius times tangential speed. Pull it inward and it spins faster. This is the skater pulling in their arms, and it is why the water above a drain speeds up as it approaches the hole.
- **Incompressibility.** What flows in must flow out. The fluid spiralling toward the axis leaves along it, upward on one side of a dividing plane and downward on the other. The core stretches while it thins; the paper's own image is spaghetti.
- **Vortex stretching.** Stretching a spinning tube along its axis thins it and, by the first point, spins it up. Fluid dynamicists have known since Helmholtz that this is *the* mechanism by which three-dimensional flows concentrate rotation, and that two-dimensional flows cannot do it, which is why the two-dimensional problem was settled decades ago.

The part that is not intuitive, and that took the machine, is the balance. Viscosity is not overwhelmed in this construction; the radial Reynolds number stays of order one all the way down, so diffusion keeps competing with the inflow and the core evolves as a self-similar shape rather than collapsing. The radius shrinks as the square root of the time left and the height as that same square root divided by a tiny power, with exponent below one hundredth. Everything in the equations diverges, and the divergences must cancel precisely enough to leave a smooth force behind. Terence Tao's 2016 result, that an averaged version of Navier–Stokes blows up, was read at the time as a hint that any real blow-up would have to be engineered like a machine built out of fluid. What the proof shows is that the machine is a spiral. Intuitive to read; not to prove.

## Theorems that changed status overnight

Ninety years of not knowing produced a large literature of conditional results, and a conditional theorem does not change when its hypothesis is decided, but its meaning does. Three families, and what happened to each:

- **"If a singularity forms, then…"** Beale–Kato–Majda: the maximum vorticity cannot be integrable in time. Caffarelli–Kohn–Nirenberg: the singular set has zero one-dimensional parabolic measure. Until Monday these were descriptions of a hypothetical object. Now they are a checklist the vortex must satisfy, and it does: its singular set is a single point at the origin at time 1, as CKN allows, and its vorticity does what BKM demands. Each of these is now a cross-check on the proof, not a constraint on a ghost.
- **"If solutions stay smooth, then…"** Long-time behaviour, convergence of numerical schemes on arbitrary intervals, uniqueness arguments that route through regularity. These were theorems with a hypothesis everyone expected to come free. They are still theorems. But for the forced problem the hypothesis is no longer available in general; each result now has a domain, the forces for which regularity holds, and that domain excludes at least one smooth force.
- **"The forced 3D Navier–Stokes equations are globally regular."** A conjecture most people held. Now false. This is the one statement that was falsified rather than reinterpreted.

Two things did not move. Statements A and B, regularity of the *unforced* equations, are untouched; every theorem conditional on them keeps exactly the status it had. And the results that regularity criteria were proved for do not all transfer: Escauriaza, Seregin and Šverák's criterion, that the L³ norm must blow up, was proved for the unforced Cauchy problem, so it does not automatically constrain this vortex.

There is also a question that just became concrete. Leray proved in 1934 that weak solutions continue past any singular time. Whether they continue *uniquely* is not known, and Albritton, Brué and Colombo showed in 2022 that with a force singular at the initial time they do not. Until now, "what does the fluid do after the singularity" was a question about a trajectory nobody had exhibited. Now there is a smooth trajectory from rest to a singular point, and what lies past it is a question about a specific object.

## The route was opened in Madrid

Fefferman's C and D do not ask for any old force. They ask for a *smooth* one, and squeezing a singularity out of a force that stays smooth through the singular time is a specific programme with a specific history. That history is not OpenAI's.

For several years Diego Córdoba, at the Institute for Mathematical Sciences in Madrid, and Luis Martínez-Zoroa, at CUNEF University, have been building forced blow-ups, by analysis, while most of the field was pointing computers at the problem. The method is to construct a sequence of solutions that are individually harmless and stack them into what Martínez-Zoroa calls an infinite cascade, each scale amplifying the next: allow an external force, get the singularity that way, then fight to make the force as regular as you can. In 2024, with Fan Zheng, they proved finite-time blow-up with finite energy for the hypo-dissipative Navier–Stokes equations, the real equations with the viscosity weakened, under a force that is Hölder-continuous in space and integrable in time rather than smooth. Two gaps separated that from Fefferman: the dissipation had to be restored to the true Laplacian, and the force had to become smooth. The second gap is why the smoothness of the force runs through this whole story. It is the criterion their cascade could not yet meet, and it is the step both teams that finished the job had to take.

Buckmaster, whose own results this week stand on that programme, is explicit about the debt in [his public statement](https://cims.nyu.edu/~tristanb/statement.pdf): the credit for the basic idea, he writes, goes to Córdoba and Martínez-Zoroa, and the ideas that make this line of attack possible are theirs. He goes past credit, too, and says in the same statement that in view of this body of work he believes Martínez-Zoroa deserves a Fields Medal. He is not alone in the assessment: Charles Fefferman, who wrote the official problem statement in 2000, told [Quanta](https://www.quantamagazine.org/ai-has-solved-one-of-maths-1-million-millennium-prize-problems-20260908/) that the two of them are "the heroes of the story".

That leaves one detail worth checking rather than assuming, and the answer moved overnight. The paper OpenAI put out on 8 September ran to 165 pages and sixteen references — Leray, Navier, Stokes, Euler, Fefferman, Caffarelli–Kohn–Nirenberg, Escauriaza–Seregin–Šverák, Buckmaster–Vicol, Albritton–Brué–Colombo, Daneri–Székelyhidi, Tao and five more — and not one of them was theirs. The names appeared nowhere in it. The version now up is 166 pages with twenty-two references, and three of the new ones are theirs: the forced-Euler blow-up of 2023, the porous-medium singularities of 2024, and the hypo-dissipative paper with Zheng, which has since appeared in the Archive for Rational Mechanics and Analysis.

The paragraph that arrived with the citations is worth more than the citations. It states that those works established the strategy of forcing a singularity by amplification across scales while keeping the regularity of the external force under control, that in their constructions larger-scale strain amplifies smaller-scale vorticity with the feedback on the larger scales suppressed, and that OpenAI's own construction exploits the same dynamical amplification with the amplified disturbances playing a different role: oscillatory pulses that generate a mean momentum flux, supplying the missing force on a collapsing vortex. That is a lineage, described in the paper's own words. It was not in the paper the day before. The mathematics did not change overnight; the reference list did. And it changed in the paper only: the announcement post, which is what most people actually read, named none of them on the evening of 8 September and still named none of them on the morning of the 9th.

<figure class="ns-fig">
<svg viewBox="0 0 600 348" role="img" aria-label="A ladder of results: at the bottom Cordoba and Martinez-Zoroa's forced blow-up method, then their 2024 hypo-dissipative Navier-Stokes blow-up with a rough force, then Alpoge and Buckmaster's smooth-force results for Euler, Boussinesq and the porous medium equation, then their announced but unreleased hypo-dissipative Navier-Stokes result, then OpenAI's full Navier-Stokes blow-up with a smooth force which settles Fefferman C and D, and at the top the unforced problem, Fefferman A and B, which nobody has closed">
  <defs>
    <marker id="ns-up" viewBox="0 0 10 10" refX="5" refY="9" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,10 L5,0 L10,10 z" fill="#64748b"/>
    </marker>
  </defs>
  <line x1="24" y1="336" x2="24" y2="14" stroke="#64748b" stroke-width="1.5" marker-end="url(#ns-up)"/>
  <text x="13" y="176" font-size="9.5" fill="#94a3b8" text-anchor="middle" transform="rotate(-90 13 176)">closer to the Millennium problem</text>

  <g>
    <rect x="44" y="22" width="536" height="46" rx="7" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.2)" stroke-width="1.5" stroke-dasharray="5 4"/>
    <rect x="44" y="76" width="536" height="46" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="2"/>
    <rect x="44" y="130" width="536" height="46" rx="7" fill="rgba(245,158,11,0.07)" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="5 4"/>
    <rect x="44" y="184" width="536" height="46" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)" stroke-width="1.2"/>
    <rect x="44" y="238" width="536" height="46" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)" stroke-width="1.2"/>
    <rect x="44" y="292" width="536" height="46" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)" stroke-width="1.2"/>
  </g>
  <g stroke="rgba(255,255,255,0.12)" stroke-width="1">
    <line x1="336" y1="30" x2="336" y2="60"/>
    <line x1="336" y1="84" x2="336" y2="114"/>
    <line x1="336" y1="138" x2="336" y2="168"/>
    <line x1="336" y1="192" x2="336" y2="222"/>
    <line x1="336" y1="246" x2="336" y2="276"/>
    <line x1="336" y1="300" x2="336" y2="330"/>
  </g>

  <g font-size="12" font-weight="700" fill="#e2e8f0">
    <text x="58" y="42" fill="#94a3b8">3D Navier&#8211;Stokes</text>
    <text x="58" y="96" fill="#5eead4">3D Navier&#8211;Stokes</text>
    <text x="58" y="150">hypo-dissipative Navier&#8211;Stokes</text>
    <text x="58" y="204">3D Euler, 2D Boussinesq, porous medium</text>
    <text x="58" y="258">hypo-dissipative Navier&#8211;Stokes</text>
    <text x="58" y="312">forced blow-ups</text>
  </g>
  <g font-size="10" fill="#94a3b8">
    <text x="58" y="58">no force &#183; Fefferman A and B</text>
    <text x="58" y="112">smooth force &#183; Fefferman C and D</text>
    <text x="58" y="166">smooth force</text>
    <text x="58" y="220">smooth force</text>
    <text x="58" y="274">rough force, H&#246;lder in space</text>
    <text x="58" y="328">the construction method</text>
  </g>
  <g font-size="11" fill="#e2e8f0">
    <text x="350" y="42" fill="#94a3b8">nobody</text>
    <text x="350" y="96" fill="#5eead4" font-weight="700">OpenAI</text>
    <text x="350" y="150" fill="#fbbf24">Alp&#246;ge &amp; Buckmaster</text>
    <text x="350" y="204">Alp&#246;ge &amp; Buckmaster</text>
    <text x="350" y="258">C&#243;rdoba, Mart&#237;nez-Zoroa, Zheng</text>
    <text x="350" y="312">C&#243;rdoba &amp; Mart&#237;nez-Zoroa</text>
  </g>
  <g font-size="10" fill="#94a3b8">
    <text x="350" y="58">still open</text>
    <text x="350" y="112">8 Sep 2026 &#183; Lean-verified</text>
    <text x="350" y="166">announced, not released</text>
    <text x="350" y="220">7 Sep 2026 &#183; Lean-verified</text>
    <text x="350" y="274">2024 &#183; finite energy</text>
    <text x="350" y="328">years of work &#183; the route</text>
  </g>
</svg>
<figcaption>Every rung weakens an assumption the rung below it needed. The top one is the problem as the field reads it, and it is empty.</figcaption>
</figure>

## The concurrent work

The rumour that set OpenAI off was real, and its object was not what the rumour said.

On 7 September, Levent Alpöge, an employee of Anthropic, and Tristan Buckmaster, a mathematician at NYU, published three results: finite-time blow-up with smooth forcing for the incompressible porous medium equation, for the two-dimensional Boussinesq system, and for the three-dimensional incompressible Euler equations, each with a Lean formalization. Terence Tao [wrote them up](https://terrytao.wordpress.com/2026/09/07/finite-time-blowup-with-smooth-forcing-term-for-the-incompressible-porous-medium-boussinesq-and-incompressible-euler-equations/) the same day. They also say they believe they have blow-up for hypo-dissipative Navier–Stokes, held back because the Lean verification is unfinished, and Buckmaster notes it suggests a path to the *unforced* Euler equations, which is the direction that would matter.

Four days earlier, a rumour was going round that Anthropic had resolved a major open problem, with versions of it attaching Alpöge's name to a solution; a prediction market moved on it. OpenAI says that rumour is what made it launch its own effort on 1 September. The object of the rumour was this collaboration, and the framing was wrong in a way worth noting: Buckmaster describes it as a purely personal collaboration with no institutional involvement by either employer, funded out of his own research budget, using Claude, Codex and later Astra. An employer's name travelled further than the work did.

The two accounts of what happened next do not agree, and both are public.

OpenAI says that after finishing the proof and its Lean verification it reached out on 6 September to offer a concurrent release and to recognise the other team's priority on forced Euler, that it offered them visibility into its prompts and later the proof itself, and that no researcher or agent saw their work before it was public.

Buckmaster's account of the same days is longer, and he has written it out:

- He contacted OpenAI first, on 3 September, after the rumour about his own work reached him through a colleague.
- In the calls of 6 September he was told "very little human input" had been used. That turned out not to be so: an entire team had been working on the problem, and even the prompt he was shown had been written by prompting Codex.
- It was eventually agreed that the first prompt had gone out within the previous few days, after news of his work reached OpenAI.
- He asked whether the model had been trained on the Codex sessions holding his drafts, and got no answer about training.
- Of two arrangements put to him, one had him presenting the result alone, with Alpöge removed from authorship and Alpöge's employment at Anthropic named as the reason. He declined both.

Sébastien Bubeck has called the allegations circulating about him false and inflammatory, and says he handled the discussion according to academic norms.

Buckmaster is careful about what he is not claiming: he has not seen the proof, does not know what the model did, and is not accusing anyone of anything. His own summary of what would be right is the standard worth keeping. If a model did close the gap, he writes, that should be said loudly, by them, "with the history intact".

There is a second thing in that statement with nothing to do with the dispute. The drafts the models produced were, by his account, the most horrendous he had ever read, and the Euler writeup "can only be described as AI slop"; the work of the fortnight before publication was turning a machine proof into something a person can read. Lean settles whether a proof is correct and says nothing about whether it is legible, and those are not the same deliverable. That gap is the whole subject of [what it takes to write a research paper with AI](/en/blog/writing-a-research-paper-with-ai): the drafting moves, the judgment does not.

## Who would the prize belong to?

Nobody, for at least two years, and possibly nobody at all.

The Clay Mathematics Institute does not pay out on a preprint. Its rules require that a solution be published in a qualifying outlet, that at least two years pass after publication, and that it have "received general acceptance in the global mathematics community". A Lean certificate does a great deal for the first condition and nothing for the third: acceptance is a social fact about mathematicians, not a property of a proof. OpenAI, in any case, says it does not intend to claim the prize.

So the live question is not who gets paid, it is who the field will say resolved it. There are four defensible answers.

- **OpenAI.** It produced the proof of C and D, in full, with a formal verification. If the standard is who wrote down the argument that settles the official statement, this is the answer and there is no contest.
- **Córdoba and Martínez-Zoroa.** They chose the route, and choosing the route is the hard part. Nobody arrives at the smooth-force direction by reading the problem statement; Buckmaster says almost nobody he knew of was working on it. On the mathematics the idea is theirs, and everything above it is engineering, however formidable.
- **Alpöge and Buckmaster.** They took a programme built for rough forces and pushed it to smooth ones, published the neighbouring cases with formalizations, and hold a claimed hypo-dissipative result that points at the unforced problem. If the last rung turns out to be reachable from theirs, priority arguments will run for years.
- **Nobody yet.** If the field reads C and D as a loophole in the wording, then the problem people care about is still open, and the strongest future claim belongs to whoever closes the unforced case.

The prize is the wrong instrument for what happened. It was designed to name a person, and this result has a route with two names on it, a completion with two more, a proof produced by a system nobody outside can inspect, and a formal verification done by a fourth model. Any single allocation of that cheque would be a false statement about how the work happened. Buckmaster's standard is the better one, and it costs nothing: say it loudly, and keep the history intact.

## What to take from it

- **The problem as written is closed, in the negative.** The question most people mean by it, whether a fluid with no external push can blow up, is still open, and the proof's own structure says how far it is from answering it: the force is defined as whatever residual makes the construction work.
- **Nothing changes for the people who use the equations.** The break happens at scales where the continuum was never a valid description, with vanishing energy, under a force nothing in nature supplies. The equations were already a model with a range; we now know the range has an edge that can be reached from inside.
- **The model is not one you can use**, and the system around it is a ten-thousand-agent swarm with a coding agent as editor. The Lean step, the only part anyone outside can check, is the part Astra did.
- **The route is not OpenAI's.** Two mathematicians in Madrid spent years making forced blow-ups work, another pair pushed their method to a smooth force the day before, and the paper that finished the job needed a revision, a day later, to say where the strategy came from.
- **The shape was always there.** A skater pulling in their arms, stretched along the spin axis, balanced against viscosity by an exponent smaller than one percent. It took ninety years and a machine to write it down, and about a minute to explain.


---

*Sources: [OpenAI's announcement](https://openai.com/index/navier-stokes-solution/), the [paper](https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf), the [Lean formalization](https://github.com/openai/NavierStokesAndEuler), [Fefferman's official problem statement](https://www.claymath.org/wp-content/uploads/2022/06/navierstokes.pdf) for the Clay Mathematics Institute, [Tristan Buckmaster's statement](https://cims.nyu.edu/~tristanb/statement.pdf), [Terence Tao on the Alpöge–Buckmaster results](https://terrytao.wordpress.com/2026/09/07/finite-time-blowup-with-smooth-forcing-term-for-the-incompressible-porous-medium-boussinesq-and-incompressible-euler-equations/), [Córdoba, Martínez-Zoroa and Zheng on hypo-dissipative blow-up](https://arxiv.org/abs/2407.06776), and [Quanta's report](https://www.quantamagazine.org/ai-has-solved-one-of-maths-1-million-millennium-prize-problems-20260908/).*
