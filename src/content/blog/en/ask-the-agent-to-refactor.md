---
title: "Ask the agent to refactor. Writing the rule isn't enough"
description: "Matt Pocock says to design more abstractions for coding agents and to back them with harsh lint. I tested whether the agent itself can be the designer, with three levers on repeated code across 384 task chains. A written rule and a duplication lint helped one agent out of three. Asking for the refactor helped all three, and what it buys is search more than design."
pubDate: 2026-11-14
tags: ["Agents", "Claude Code", "Codex", "Software Design", "Experiments"]
lang: en
translationKey: ask-the-agent-to-refactor
repoUrl: "https://github.com/JaviMaligno/personal-website/tree/main/experiments/agent-abstractions"
heroImage: "/blog/ask-the-agent-to-refactor.png"
linkedinImage: "/blog/ask-the-agent-to-refactor-fig-2.png"
---

<style>
.abs-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.abs-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.abs-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

Codex gets a task in a budgeting app: schedules whose amount "is between" two values should now be planned at the worst end of the range, not the middle. It searches, writes *"I found three midpoint calculations"*, moves all three into one shared function, runs the tests, and reports: *"Previews, automatic posts, and synced rule actions all use the same calculation."* The tests pass. The step fails.

There was a fourth copy. The budget template computed the same midpoint, written differently (`Math.round(num1 + num2) / 2`), and Codex's search never matched it. In five of eight chains it never opened that file, and in those five it missed the copy every time.

This is the failure that abstraction is supposed to prevent. If the rule lives in one place, there is no fourth copy to miss. Matt Pocock put the case for more abstractions [in a tweet](https://x.com/mattpocockuk/status/2106425743479546343) that I have been testing for two weeks:

> My hot take from chatting to @poteto is that we should use MORE abstractions in the AI age. You can use them (combined with harsh lint rules) to reduce the design space available to the agent and constrain them only to good decisions. [...] Be braver! Design abstractions.

He is talking to the humans who design the code. My question in this third round was the next one: if the code is already repeated, can the agent be the one who designs the abstraction? And what makes it do so: a rule, a lint, or asking?

## Where this came from

I ran this in three studies, all on the same real codebase: `loot-core`, the core of the open-source budgeting app [Actual](https://github.com/actualbudget/actual), about 48k lines of TypeScript. The agents were Claude Code with Sonnet 5.5 and with Haiku 5.5, and Codex with GPT-6 Luna, all at medium effort.

The first study tested the "harsh lint" half directly. With the habitual code, the agents made zero bad design decisions in 240 runs each, so neither more abstraction nor lint had anything left to remove. Nor did they save tokens.

The second study built two versions of the same four areas of code: one where the logic is repeated in several places (R), and one where a human had factored it into shared functions (F). Then it ran chains of four tasks on each. With F the agents missed fewer copies and blind judges scored the design higher, especially across a whole chain: Sonnet's chains scored 2.94 out of 5 in R against 3.56 in F. Token cost did not change. So abstraction helps, but in that study a human had designed it.

## The experiment

Every arm starts from the repeated code of study 2 and runs the same chains. Each chain has four steps, each in a fresh session, so whatever an agent learns can only reach the next step through the code. T1 changes a business rule, T2 adds a new consumer of that logic, T3 changes the rule again, T4 builds something on top. The arms differ in one lever:

<figure class="abs-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="The four arms. All start from the same repeated code and run the same four steps: rule change, new consumer, rule change, build. R has no lever. RG adds one rule to AGENTS.md. RL adds a duplication check to the lint. RC adds a step zero, a directed refactor asking for the logic to live in one place.">
  <text x="335" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">refactor</text>
  <text x="400" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">rule</text>
  <text x="460" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">consumer</text>
  <text x="520" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">rule</text>
  <text x="575" y="22" text-anchor="middle" fill="#94a3b8" font-size="10">build</text>
  <g font-size="12">
    <text x="16" y="56" fill="#e2e8f0" font-weight="600">R</text><text x="52" y="56" fill="#94a3b8">repeated code, no lever</text>
    <text x="16" y="106" fill="#e2e8f0" font-weight="600">RG</text><text x="52" y="106" fill="#94a3b8">+ one rule in AGENTS.md</text>
    <text x="16" y="156" fill="#e2e8f0" font-weight="600">RL</text><text x="52" y="156" fill="#94a3b8">+ duplication check in lint</text>
    <text x="16" y="206" fill="#fbbf24" font-weight="600">RC</text><text x="52" y="206" fill="#94a3b8">+ "make it live in one place"</text>
  </g>
  <g fill="#232334" stroke="#2dd4bf">
    <rect x="375" y="38" width="50" height="28" rx="6"/><rect x="435" y="38" width="50" height="28" rx="6"/><rect x="495" y="38" width="50" height="28" rx="6"/><rect x="552" y="38" width="46" height="28" rx="6"/>
    <rect x="375" y="88" width="50" height="28" rx="6"/><rect x="435" y="88" width="50" height="28" rx="6"/><rect x="495" y="88" width="50" height="28" rx="6"/><rect x="552" y="88" width="46" height="28" rx="6"/>
    <rect x="375" y="138" width="50" height="28" rx="6"/><rect x="435" y="138" width="50" height="28" rx="6"/><rect x="495" y="138" width="50" height="28" rx="6"/><rect x="552" y="138" width="46" height="28" rx="6"/>
    <rect x="375" y="188" width="50" height="28" rx="6"/><rect x="435" y="188" width="50" height="28" rx="6"/><rect x="495" y="188" width="50" height="28" rx="6"/><rect x="552" y="188" width="46" height="28" rx="6"/>
  </g>
  <rect x="310" y="188" width="50" height="28" rx="6" fill="#232334" stroke="#f59e0b"/>
  <g font-size="11" text-anchor="middle" fill="#e2e8f0">
    <text x="400" y="56">T1</text><text x="460" y="56">T2</text><text x="520" y="56">T3</text><text x="575" y="56">T4</text>
    <text x="400" y="106">T1</text><text x="460" y="106">T2</text><text x="520" y="106">T3</text><text x="575" y="106">T4</text>
    <text x="400" y="156">T1</text><text x="460" y="156">T2</text><text x="520" y="156">T3</text><text x="575" y="156">T4</text>
    <text x="400" y="206">T1</text><text x="460" y="206">T2</text><text x="520" y="206">T3</text><text x="575" y="206">T4</text>
    <text x="335" y="206" fill="#fbbf24">T0</text>
  </g>
  <path d="M360 202 L373 202" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="300" y="240" text-anchor="middle" fill="#94a3b8" font-size="11">3 agents × 4 code areas × 8 chains per arm · a fresh session at every step</text>
</svg>
<figcaption>Same starting code, same tasks. Only the lever changes: a written norm, a hard check, or an explicit request to refactor before the work starts.</figcaption>
</figure>

- **RG**, the written rule. One line in the root `AGENTS.md`, worded as a team convention: *"Do not copy logic: when new code needs behaviour that already exists, extract it into a shared function and reuse it; when a rule changes, change it in one place."*
- **RL**, the harsh lint. `yarn lint` runs a duplication check (jscpd) that fails if any clone touches lines the step added. Removing unrelated duplication elsewhere earns no slack.
- **RC**, the directed refactor. Before T1, a step T0 that names the behaviour area and asks for it to live in one place, with behaviour unchanged. It doesn't say which files, how many copies, or where.

That makes 384 chains and 1,632 steps. Correctness comes from hidden tests. Design comes from blind judges (Claude Opus 5.5), who scored 2,206 diffs without knowing the arm, the agent, or that arms existed. A second judge scored 340 of them, and I computed agreement before comparing anything: weighted kappa between 0.70 and 0.89 on every score. The design and every analysis were registered before the runs.

## Only one lever reaches all three agents

The main measure is the maintainability of a chain's full diff, as the judges scored it from 1 to 5:

<figure class="abs-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Judged maintainability of the chain diff by agent and arm. Claude: R 2.59, rule 3.09, lint 3.19, refactor 3.06, human factoring 3.41. Codex: R 2.19, rule 2.16, lint 2.34, refactor 2.59, human factoring 2.78. Haiku: R 3.56, rule 3.78, lint 3.69, refactor 3.91, human factoring 3.91. The refactor request raises all three agents; the rule and the lint clearly raise only Claude.">
  <g stroke="rgba(255,255,255,0.08)"><path d="M55 250 H595"/><path d="M55 202.5 H595"/><path d="M55 155 H595"/><path d="M55 107.5 H595"/><path d="M55 60 H595"/></g>
  <g fill="#94a3b8" font-size="10" text-anchor="end"><text x="48" y="253">2.0</text><text x="48" y="205.5">2.5</text><text x="48" y="158">3.0</text><text x="48" y="110.5">3.5</text><text x="48" y="63">4.0</text></g>
  <g font-size="12" font-weight="600" fill="#e2e8f0" text-anchor="middle"><text x="140" y="36">Claude (Sonnet)</text><text x="325" y="36">Codex (Luna)</text><text x="510" y="36">Claude (Haiku)</text></g>
  <!-- Claude -->
  <rect x="68" y="194" width="30" height="56" fill="#64748b"/><rect x="106" y="146" width="30" height="104" fill="#2dd4bf"/><rect x="144" y="137" width="30" height="113" fill="#2dd4bf"/><rect x="182" y="149" width="30" height="101" fill="#f59e0b"/>
  <path d="M62 116 H220" stroke="#e2e8f0" stroke-width="1.5" stroke-dasharray="5 4"/>
  <!-- Codex -->
  <rect x="253" y="232" width="30" height="18" fill="#64748b"/><rect x="291" y="235" width="30" height="15" fill="#2dd4bf"/><rect x="329" y="218" width="30" height="32" fill="#2dd4bf"/><rect x="367" y="194" width="30" height="56" fill="#f59e0b"/>
  <path d="M247 176 H405" stroke="#e2e8f0" stroke-width="1.5" stroke-dasharray="5 4"/>
  <!-- Haiku -->
  <rect x="438" y="102" width="30" height="148" fill="#64748b"/><rect x="476" y="81" width="30" height="169" fill="#2dd4bf"/><rect x="514" y="89" width="30" height="161" fill="#2dd4bf"/><rect x="552" y="69" width="30" height="181" fill="#f59e0b"/>
  <path d="M432 69 H590" stroke="#e2e8f0" stroke-width="1.5" stroke-dasharray="5 4"/>
  <text x="436" y="64" fill="#cbd5e1" font-size="10">human F</text>
  <g font-size="10" text-anchor="middle" fill="#94a3b8">
    <text x="83" y="265">R</text><text x="121" y="265">rule</text><text x="159" y="265">lint</text><text x="197" y="265" fill="#fbbf24">refactor</text>
    <text x="268" y="265">R</text><text x="306" y="265">rule</text><text x="344" y="265">lint</text><text x="382" y="265" fill="#fbbf24">refactor</text>
    <text x="453" y="265">R</text><text x="491" y="265">rule</text><text x="529" y="265">lint</text><text x="567" y="265" fill="#fbbf24">refactor</text>
  </g>
  <g font-size="10" text-anchor="middle" fill="#e2e8f0"><text x="121" y="140">✓</text><text x="159" y="131">✓</text></g>
  <g font-size="10" fill="#cbd5e1"><text x="224" y="119">human F</text><text x="409" y="179">human F</text></g>
  <text x="300" y="290" text-anchor="middle" fill="#94a3b8" font-size="10">maintainability (1–5, Opus judge), axis from 2.0 · ✓ survives correction for 9 tests · dashed: human-factored</text>
</svg>
<figcaption>The refactor request (amber) is the only lever that raises all three agents, by 0.35 to 0.47 points (p ≈ 0.02 each, the same direction in 11 of 12 code areas). The rule and the lint clearly move only Sonnet (the lint is tested on the two areas where it can see copies).</figcaption>
</figure>

For Sonnet, the three levers all work, and with the registered judge the rule and the lint survive correction for multiple tests. For Codex and Haiku, the rule and the lint do nothing measurable. Only the refactor request moves all three. On its own, each agent's refactor effect is around p = 0.02 and would not survive correction, but it points the same way in 11 of the 12 code areas, and it is the only lever that also moves correctness.

Haiku is a special case: it starts close to the ceiling (3.56 against 3.91 for the human-factored code), so there is little room to gain.

The judges are Claude, and so are two of the three agents. To check that they weren't just preferring their own family's code, I had GPT-6.1 Sol, through Codex, re-score the 480 chain diffs blind with the same rubric. The two judges agree well on maintainability (weighted kappa 0.79), and there is a family effect: compared with Sol, Opus scores Claude-written code 0.21 points higher than Codex-written code. Every comparison above is within the same agent, so a constant offset cancels out, and with Sol as the judge the refactor request still raises all three agents (+0.34, +0.25 and +0.28 points; p = 0.03, 0.09 and 0.04). The written rule still helps Sonnet (p = 0.02). What shrinks is the lint's gain for Sonnet, from 1.13 to 0.43 points in the areas where it can see copies: the family gap is largest in the rule and lint arms.

## What the refactor buys: search

Back to the missed copy. With the repeated code and no lever, Codex misses a copy at a rule step in 33% of cases and gets 59% of steps right. After its own refactor, it misses 12% and gets 70% right. That is better than the code a human had factored in study 2 (22% and 66%).

<figure class="abs-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Codex: missed copies at rule steps were 33 percent with no lever, 31 with the rule, 31 with the lint, 12 with the refactor request, and 22 with study 2's human-factored code. Correct steps were 59, 55, 59, 70 and 66 percent.">
  <g stroke="rgba(255,255,255,0.08)"><path d="M55 220 H590"/><path d="M55 175 H590"/><path d="M55 130 H590"/><path d="M55 85 H590"/></g>
  <g fill="#94a3b8" font-size="10" text-anchor="end"><text x="48" y="223">0%</text><text x="48" y="178">25%</text><text x="48" y="133">50%</text><text x="48" y="88">75%</text></g>
  <g font-size="12" font-weight="600" fill="#e2e8f0" text-anchor="middle"><text x="175" y="36">missed a copy (rule steps)</text><text x="445" y="36">correct steps</text></g>
  <rect x="80" y="161" width="34" height="59" fill="#64748b"/><rect x="122" y="164" width="34" height="56" fill="#2dd4bf"/><rect x="164" y="164" width="34" height="56" fill="#2dd4bf"/><rect x="206" y="198" width="34" height="22" fill="#f59e0b"/><rect x="248" y="180" width="34" height="40" fill="none" stroke="#e2e8f0" stroke-dasharray="4 3"/>
  <rect x="350" y="114" width="34" height="106" fill="#64748b"/><rect x="392" y="121" width="34" height="99" fill="#2dd4bf"/><rect x="434" y="114" width="34" height="106" fill="#2dd4bf"/><rect x="476" y="94" width="34" height="126" fill="#f59e0b"/><rect x="518" y="101" width="34" height="119" fill="none" stroke="#e2e8f0" stroke-dasharray="4 3"/>
  <g font-size="11" text-anchor="middle" fill="#e2e8f0">
    <text x="97" y="155">33</text><text x="139" y="158">31</text><text x="181" y="158">31</text><text x="223" y="192" fill="#fbbf24">12</text><text x="265" y="174">22</text>
    <text x="367" y="108">59</text><text x="409" y="115">55</text><text x="451" y="108">59</text><text x="493" y="88" fill="#fbbf24">70</text><text x="535" y="95">66</text>
  </g>
  <g font-size="10" text-anchor="middle" fill="#94a3b8">
    <text x="97" y="236">R</text><text x="139" y="236">rule</text><text x="181" y="236">lint</text><text x="223" y="236" fill="#fbbf24">refactor</text><text x="265" y="236">F</text>
    <text x="367" y="236">R</text><text x="409" y="236">rule</text><text x="451" y="236">lint</text><text x="493" y="236" fill="#fbbf24">refactor</text><text x="535" y="236">F</text>
  </g>
  <text x="300" y="262" text-anchor="middle" fill="#94a3b8" font-size="10">Codex (GPT-6 Luna), 64 rule steps and 128 steps per arm · F: human-factored code (study 2)</text>
</svg>
<figcaption>With Codex, the rule and the lint leave the missed copies where they were. After a refactor it made itself, it misses a copy a third as often as with no lever.</figcaption>
</figure>

When I read the traces, the mechanism was simpler than "the agent designed a good abstraction". In the repeated code, Codex does consolidate at the rule step, but only the copies it finds. The refactor request says the logic is "repeated rather than defined once", and that sentence sends it looking for every copy. A rule change doesn't. Once the copies sit behind one function, the next rule change reaches all of them with one edit, including the budget template, without the agent ever opening that file.

The two misses that remain repeat, with Codex's own abstraction, the two failures I had seen with the human one. In one chain, the refactor never found the template copy. In the other, Codex had preserved the template's odd rounding as a named mode, and at the next step it treated that mode as a protected requirement: *"Schedule templates explicitly request a separate sum-first rounding mode; I'll preserve that behavior."* An abstraction that names an exception invites the next agent to protect it.

All three agents built the same kinds of abstraction at T0: a category-selection function, one shared flow for linking bank accounts, one weekend-rule function. The judges found most refactors complete: the median share of copy sites routed through the shared definition was 100% for every agent. Behaviour was kept too: my behaviour check flagged four of the 96 refactors, and only two of those were real changes (both Codex's). The other two were an artefact of how finely the check records internal calls.

## The lint, and how Codex got past it

With Sonnet, the duplication check produced the most clearly better design in the study. In the bank-sync area it built one linking pipeline for every provider. A judge wrote: *"Adding a provider becomes a few lines."*

With Codex it produced something else. In four steps it marked the code so the checker would skip it:

```ts
// jscpd:ignore-start -- This provider has the same link lifecycle as the others.
```

with the justification *"The duplication check is unusually strict here: it flags the same established provider lifecycle even when the implementation is intentionally parallel."* In other chains it reused by stretching another provider's function with flags until it served both. A judge described one: *"a SimpleFin handler stretched with an 'orgDomain' in-check to also serve Fintegra."* In others it kept copies reshaped enough that the checker stopped matching them. The duplication count went down, and the design scores didn't move.

The lint also has a structural blind spot: it only sees copies that look alike. In the area where the duplication is four different implementations of the same weekend rule, it never fires, and Sonnet's design there came out slightly worse than with no lever.

## What not to oversell

When I read the judges' justifications, most of the design gain is fewer copies of the same rule rather than a different structure. The main complaint about the repeated code, "this rule lives in several places", is still there in every arm. What changes is that six places become two. If I account for the number of duplicated blocks the judge itself counted, the arms' effect on Sonnet shrinks to between a fifth and a half. The one-pipeline case is the exception.

The refactor doesn't pay for itself in tokens over four tasks. With T0 included, a refactor chain costs 16% to 23% more than one with no lever. A longer chain might recover it. This one didn't.

The written rule is never quoted. Sonnet follows it without citing it, and it does so mostly by reusing helper functions it created itself in the previous step. Codex has the file in context, and it follows another instruction in it (run commands from the repository root) in 541 of 544 steps. This one it ignores.

## What I would do

If you want an abstraction in an agent-maintained codebase, ask the agent for it as a task, not as a rule. Name the area, say it should live in one place, and say which differences must survive. The last part matters: an exception that is not named either gets erased or gets wrapped in a mode that the next agent treats as sacred.

A rule in `AGENTS.md` costs nothing, but whether it works depends on the agent. A duplication lint is a safety net, not a designer: some agents meet it by building the abstraction, others by getting past the check. And none of these levers replaces the search. What made the difference was that someone asked the agent to go find every copy.

Pocock asked people to be braver and design abstractions. My data adds one thing: when the code is already repeated, you can delegate the design, as long as you ask for it explicitly.

---

*Limits: one codebase, one effort level, three agents. The registered judge and its second pass are the same model; the cross-family check with Sol covers the chain diffs, not every score. With four code areas, the per-area sign test can never reach significance. A related result: in [an earlier experiment](/en/blog/practices-for-agents-substrate) on how the way code is written affects agents, the effects only appeared in large repositories. The pre-registered design, the code, the anonymised data and the full report are [in the repository](https://github.com/JaviMaligno/personal-website/tree/main/experiments/agent-abstractions).*
