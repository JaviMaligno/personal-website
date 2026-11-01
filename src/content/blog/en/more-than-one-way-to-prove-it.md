---
title: "More Than One Way to Prove It"
description: "Grading an agent by comparing its tool calls with a reference path sounds stricter than checking where it ended up. Across 694 runs fixing real bugs and writing Lean proofs, the path rejected a third of the valid proofs, two reasonable rules ranked the models in reverse, and the clearest false claim was in a sentence no grader reads."
pubDate: 2026-11-02
tags: ["AI", "Agents", "Evaluation", "Lean", "Research"]
lang: en
translationKey: more-than-one-way-to-prove-it
heroImage: "/blog/more-than-one-way-to-prove-it.png"
---
Here are two proofs that the $n$-th Fibonacci number is at most $2^n$, written by two different agents.

```lean
-- gpt-6.1-sol: prove something stronger, by induction
have bounds : ∀ k, fib k ≤ 2 ^ k ∧ fib (k + 1) ≤ 2 ^ (k + 1) := by
  intro k
  induction k with
  | zero => decide
  | succ k ih =>
    constructor
    · exact ih.2
    · simp only [fib, Nat.pow_succ] at *
      omega
exact (bounds n).1

-- Claude Sonnet: no induction tactic, the theorem calls itself
match n with
| 0 => simp [fib]
| 1 => simp [fib]
| n + 2 =>
  have h1 := fib_le_pow n
  have h2 := fib_le_pow (n + 1)
  simp only [fib]
  rw [Nat.pow_succ, Nat.pow_succ] at *
  omega
```

Both are correct; Lean's kernel accepts them. They are different routes. The first strengthens the claim to two consecutive numbers at once, so that a plain induction goes through. The second splits on $n$ and uses the theorem itself for the two previous numbers, a recursion Lean checks terminates. Scored against reference paths, the first gets a path correctness of 1.0 and the second 0.63. With the usual threshold, the first passes and the second fails.

That is the kind of grading proposed by *CORE: Full-Path Evaluation of LLM Agents Beyond Final State* ([Michelakis, Hadjiyiannis and Stamoulis, 2025](https://arxiv.org/abs/2509.20998)). Its argument is sound as far as it goes: if you only check the final state, agents that behaved very differently look the same. CORE encodes each task as a set of valid tool-use paths and measures how close the agent's path is to one of them.

My doubt was about tasks where the next useful step is not known in advance. A proof, or a debugging session, is exploratory: you don't know which lemma or which print statement will unlock it. Writing down the path might demand something the task never needed. Writing down what is required and what is forbidden might be enough. So I measured both, on tasks where several valid routes really exist.

<style>
.path-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.path-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.path-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Three worlds, six models, four graders

**World A: real bugs.** Ten bugs reintroduced into [humanize](https://github.com/python-humanize/humanize), a real Python library, each one reverting a fix the maintainers made. The agent gets a bug report, a failing test and the command to run the suite. The truth is the library's own suite plus hidden tests of the same behaviour, run against whatever the agent left in `src/`.

**World B: Lean without Mathlib.** Twenty-six theorems about lists, sums and recursive functions, from one-line inductions to proofs that need a generalised hypothesis. Each one has two reference proofs with different strategies, written by a model that is not among the ones evaluated. The truth is mechanical: the file compiles, the statement is untouched, there is no `sorry`, and `#print axioms` lists only the three standard ones.

**World C: Mathlib.** Nine competition problems from [miniF2F](https://github.com/yangky11/miniF2F-lean4), four of them hard (two AIME, two IMO), with full Mathlib available.

Six models ran each task three times: Claude Haiku, Sonnet and Opus through Claude Code; `gpt-6.1-sol` and `gpt-6-luna` through Codex; and Qwen 3.5 9B in a plain tool loop. That makes 180 runs in A and 468 in B. World C was a smaller trial with three models, 46 runs.

Every run was scored by four graders, each one a different idea of what to check:

<figure class="path-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="The four graders. E0 checks the final state. E1 adds forbidden actions and E2 adds order obligations on top of E1. E3 is a separate branch from E0 that adds path correctness against reference paths.">
  <g font-size="12">
    <rect x="20" y="190" width="560" height="52" rx="8" fill="#232333" stroke="#64748b"/>
    <text x="40" y="212" fill="#f8fafc" font-weight="700" font-family="ui-monospace,'JetBrains Mono',monospace">E0</text>
    <text x="80" y="212" fill="#e2e8f0">Final state: the visible check passes</text>
    <text x="80" y="230" fill="#94a3b8">the failing test now passes · lean exits with code 0</text>
    <rect x="20" y="104" width="270" height="62" rx="8" fill="#232333" stroke="#2dd4bf"/>
    <text x="36" y="126" fill="#5eead4" font-weight="700" font-family="ui-monospace,'JetBrains Mono',monospace">E1</text>
    <text x="66" y="126" fill="#e2e8f0">+ nothing forbidden</text>
    <text x="36" y="146" fill="#94a3b8">no test edited · no sorry, no axiom,</text>
    <text x="36" y="160" fill="#94a3b8">statement unchanged</text>
    <rect x="20" y="18" width="270" height="62" rx="8" fill="#232333" stroke="#2dd4bf"/>
    <text x="36" y="40" fill="#5eead4" font-weight="700" font-family="ui-monospace,'JetBrains Mono',monospace">E2</text>
    <text x="66" y="40" fill="#e2e8f0">+ order obligations</text>
    <text x="36" y="60" fill="#94a3b8">tests run before the first edit and after</text>
    <text x="36" y="74" fill="#94a3b8">the last · compile after the last edit</text>
    <rect x="310" y="61" width="270" height="62" rx="8" fill="#232333" stroke="#f59e0b"/>
    <text x="326" y="83" fill="#fbbf24" font-weight="700" font-family="ui-monospace,'JetBrains Mono',monospace">E3</text>
    <text x="356" y="83" fill="#e2e8f0">+ the path (CORE)</text>
    <text x="326" y="103" fill="#94a3b8">path correctness against the</text>
    <text x="326" y="117" fill="#94a3b8">reference paths ≥ τ = 0.8</text>
  </g>
  <g stroke="#64748b" stroke-width="1.5" fill="none">
    <path d="M155 190 V166"/><path d="M155 104 V80"/><path d="M445 190 V123"/>
  </g>
</svg>
<figcaption>Rules on the left, path on the right. E1 and E2 say what must and must not happen; E3 says how close the sequence of steps has to be to a known route. All four are compared with the same mechanical truth.</figcaption>
</figure>

Path correctness is CORE's: one minus a normalised edit distance between the agent's condensed sequence of steps $p$ and the closest reference $r$,

$$
\mathrm{PC}(p) \;=\; \max_{r \in R}\left(1 - \frac{2\,d(p,r)}{|p| + |r| + d(p,r)}\right),
\qquad
E_3 \;=\; E_0 \,\wedge\, \mathrm{PC}(p) \ge \tau ,
$$

where $d$ is the Levenshtein distance. In A the steps are the state-changing calls, condensed the way the paper does: edits to each file and test runs, with repeats collapsed. CORE was built for tool calls, not proofs, so in Lean the steps are my translation of its idea: the skeleton of the proof's strategy. That means induction and on what, auxiliary facts, case splits, generalisation, and a single token for however the goal is closed. Tactic names (`simp` against `rw`) are deliberately left out, so that a different tactic does not count as a different route. The skeleton does count every intermediate `have` as an auxiliary fact, which is a matter of style, so the section on what the path rejects also gives a coarser count that ignores it.

## What the final state lets through

In Lean, almost nothing. Out of 468 runs in B, three produced a file that compiles without being a valid proof of the theorem. One was Qwen replacing the whole theorem with `theorem test : True := by trivial`. One was a model leaving `sorry` in place and saying so. The third rewrote the statement so that it only covers types in the lowest universe, which is technically weaker. E1, the grader with the forbidden list, caught all three. The type checker does the heavy lifting; the forbidden list closes the two doors it leaves open, `sorry` and a changed statement.

In World C the three files that compiled without being proofs were all the same thing: a `sorry`, next to a final message saying the proof was not finished. Here is Luna on an IMO problem:

> I haven’t found a proof yet, so `sorry` is still in `Main.lean`. I can’t claim the theorem is proved or that `lean Main.lean` passes.

Python is different. Of 180 runs in A, 21 left a fix that passes the failing test and fails the library's suite or the hidden tests. Eleven of them fail for reasons nobody would argue with: a fix that breaks other tests in the library, or a special case such as `if days == 0.5: days = 0`. The other ten are all on the same bug and depend on a single disputed case, which gets its own section below. So the final state lets through between 11 and 21 of 180 runs, roughly 6 to 12 per cent. And here the forbidden list barely helps: E1 removes one of the 21, the only run that edited the tests. The rest did nothing forbidden. They just fixed less than they appeared to.

<figure class="path-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="False passes and false fails for each grader in each world. The path grader E3 trades a handful of false passes for many false fails: 25 in A, 136 in B and 18 of 19 in C.">
  <g font-size="12" fill="#94a3b8" text-anchor="middle">
    <text x="245" y="24">A · bugs</text><text x="390" y="24">B · Lean</text><text x="535" y="24">C · Mathlib</text>
    <text x="245" y="40" font-size="10.5">157 valid · 23 not</text><text x="390" y="40" font-size="10.5">400 valid · 68 not</text><text x="535" y="40" font-size="10.5">28 valid · 18 not</text>
  </g>
  <g font-size="12" fill="#e2e8f0" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="30" y="82">E0 final state</text><text x="30" y="128">E1 + forbidden</text><text x="30" y="174">E2 + order</text><text x="30" y="220">E3 + path</text>
  </g>
  <g fill="#232333" stroke="rgba(255,255,255,0.1)">
    <rect x="180" y="56" width="130" height="38" rx="6"/><rect x="325" y="56" width="130" height="38" rx="6"/><rect x="470" y="56" width="120" height="38" rx="6"/>
    <rect x="180" y="102" width="130" height="38" rx="6"/><rect x="325" y="102" width="130" height="38" rx="6"/><rect x="470" y="102" width="120" height="38" rx="6"/>
    <rect x="180" y="148" width="130" height="38" rx="6"/><rect x="325" y="148" width="130" height="38" rx="6"/><rect x="470" y="148" width="120" height="38" rx="6"/>
    <rect x="180" y="194" width="130" height="38" rx="6"/><rect x="325" y="194" width="130" height="38" rx="6"/><rect x="470" y="194" width="120" height="38" rx="6"/>
  </g>
  <g font-size="13" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="245" y="80"><tspan fill="#fbbf24">21</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">0</tspan></text>
    <text x="390" y="80"><tspan fill="#fbbf24">3</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">0</tspan></text>
    <text x="530" y="80"><tspan fill="#fbbf24">3</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">0</tspan></text>
    <text x="245" y="126"><tspan fill="#fbbf24">20</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">15</tspan></text>
    <text x="390" y="126"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">5</tspan></text>
    <text x="530" y="126"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">0</tspan></text>
    <text x="245" y="172"><tspan fill="#fbbf24">13</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">115</tspan></text>
    <text x="390" y="172"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">5</tspan></text>
    <text x="530" y="172"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">6</tspan></text>
    <text x="245" y="218"><tspan fill="#fbbf24">14</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">25</tspan></text>
    <text x="390" y="218"><tspan fill="#fbbf24">1</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">136</tspan></text>
    <text x="530" y="218"><tspan fill="#fbbf24">0</tspan><tspan fill="#64748b"> · </tspan><tspan fill="#5eead4">18/19</tspan></text>
  </g>
  <g font-size="11" fill="#94a3b8">
    <text x="180" y="248"><tspan fill="#fbbf24">■</tspan> passes invalid work   <tspan fill="#5eead4">■</tspan> fails valid work</text>
  </g>
</svg>
<figcaption>Each cell: invalid runs the grader passes · valid runs it fails. In Lean the forbidden list (E1) is enough. The path (E3) buys very little on the left of each cell and costs a lot on the right. World C's E3 counts only the four problems with reference proofs.</figcaption>
</figure>

## What the path rejects

The path grader did catch something in A: 7 of the 21 runs the final state let through. It did that by failing whatever looked unusual, which also meant failing 25 of the 157 valid fixes. In Lean the trade is far worse. E3 failed 136 of the 400 valid proofs in B, a third, and 18 of the 19 valid proofs of the hard Mathlib problems. In exchange it caught two of the three invalid proofs in B, which E1 had caught as well.

The cause is the one in the opening example, at scale. Valid proofs of the same theorem take different routes, and not only in style. Take the coarsest possible classification, which looks only at what a proof inducts on, whether it generalises, and whether it leans on a helper lemma of its own. Even then, 11 of the 26 theorems in B were proved by two or more different routes, up to six on one theorem. And 113 of the 400 valid proofs inducted on something, or generalised in a way, that neither reference did. Two references, however carefully chosen, cannot cover that.

Lowering the threshold doesn't rescue it:

<figure class="path-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Share of valid work that the path grader fails, as the threshold tau goes from 0.5 to 1.0. In bugs it rises from 0 to 16 per cent; in Lean without Mathlib from 3 to 37 per cent; in hard Mathlib problems it stays between 74 and 95 per cent.">
  <g font-size="11" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace">
    <line x1="70" y1="220" x2="560" y2="220" stroke="#64748b"/>
    <line x1="70" y1="20" x2="70" y2="220" stroke="#64748b"/>
    <line x1="70" y1="120" x2="560" y2="120" stroke="rgba(255,255,255,0.08)"/>
    <line x1="70" y1="70" x2="560" y2="70" stroke="rgba(255,255,255,0.08)"/>
    <line x1="70" y1="170" x2="560" y2="170" stroke="rgba(255,255,255,0.08)"/>
    <line x1="70" y1="20" x2="560" y2="20" stroke="rgba(255,255,255,0.08)"/>
    <text x="62" y="224" text-anchor="end">0%</text><text x="62" y="174" text-anchor="end">25%</text><text x="62" y="124" text-anchor="end">50%</text><text x="62" y="74" text-anchor="end">75%</text><text x="62" y="24" text-anchor="end">100%</text>
    <text x="70" y="238" text-anchor="middle">0.5</text><text x="168" y="238" text-anchor="middle">0.6</text><text x="266" y="238" text-anchor="middle">0.7</text><text x="364" y="238" text-anchor="middle">0.8</text><text x="462" y="238" text-anchor="middle">0.9</text><text x="560" y="238" text-anchor="middle">1.0</text>
    <text x="315" y="260" text-anchor="middle">threshold τ</text>
  </g>
  <polyline fill="none" stroke="#f59e0b" stroke-width="2.5" points="70,73 168,41 266,30 364,30 462,30 560,30"/>
  <polyline fill="none" stroke="#2dd4bf" stroke-width="2.5" points="70,214 168,192 266,172 364,152 462,146 560,146"/>
  <polyline fill="none" stroke="#e2e8f0" stroke-width="2.5" points="70,220 168,215 266,211 364,188 462,188 560,188"/>
  <g font-size="12">
    <text x="470" y="48" fill="#fbbf24">C · hard Mathlib</text>
    <text x="470" y="140" fill="#5eead4">B · Lean</text>
    <text x="470" y="206" fill="#e2e8f0">A · bugs</text>
  </g>
</svg>
<figcaption>Valid work failed by the path grader, as a share of all valid work, for each threshold. At the loosest setting, τ = 0.5, it still fails 74% of the valid hard Mathlib proofs.</figcaption>
</figure>

In A, a loose threshold works: at $\tau = 0.5$ no valid fix is failed. A bug fix has a natural shape (look, edit the file, run the tests), and almost everyone follows it. A proof has no such shape. The harder the problem, the less any particular sequence of steps tells you about whether the result is right.

## An order rule that measures a working style

E2 doesn't compare paths. It adds one obligation that looks like plain good practice: run the test suite before you change anything, and again after the last change. In A, 115 of the 157 valid fixes failed E2. Almost all of them ran the tests at the end; what they skipped was the run before the first edit.

Who skipped it:

<figure class="path-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Share of each model's valid bug fixes that ran the tests before the first edit: gpt-6.1-sol 28 of 29, Qwen 19 of 22, Haiku 7 of 25, Luna 3 of 22, Opus 1 of 29, Sonnet 0 of 30.">
  <g font-size="12" fill="#e2e8f0" text-anchor="end">
    <text x="130" y="40">gpt-6.1-sol</text><text x="130" y="76">Qwen 3.5 9B</text><text x="130" y="112">Haiku</text>
    <text x="130" y="148">gpt-6-luna</text><text x="130" y="184">Opus</text><text x="130" y="220">Sonnet</text>
  </g>
  <g fill="#232333"><rect x="140" y="26" width="380" height="20" rx="4"/><rect x="140" y="62" width="380" height="20" rx="4"/><rect x="140" y="98" width="380" height="20" rx="4"/><rect x="140" y="134" width="380" height="20" rx="4"/><rect x="140" y="170" width="380" height="20" rx="4"/><rect x="140" y="206" width="380" height="20" rx="4"/></g>
  <g fill="#2dd4bf"><rect x="140" y="26" width="367" height="20" rx="4"/><rect x="140" y="62" width="328" height="20" rx="4"/><rect x="140" y="98" width="106" height="20" rx="4"/><rect x="140" y="134" width="52" height="20" rx="4"/><rect x="140" y="170" width="13" height="20" rx="4"/></g>
  <g font-size="12" fill="#5eead4" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="530" y="40">28 / 29</text><text x="530" y="76">19 / 22</text><text x="530" y="112">7 / 25</text>
    <text x="530" y="148">3 / 22</text><text x="530" y="184">1 / 29</text><text x="530" y="220">0 / 30</text>
  </g>
</svg>
<figcaption>Valid bug fixes that ran the test suite before the first edit, per model. Two working styles, not two levels of care: Sonnet and Opus, at the bottom, fixed as many bugs as the model at the top, or more.</figcaption>
</figure>

Sonnet fixed all 30 bugs and never once ran the suite before editing. Opus fixed 29 and ran it first once. Both read the failing test and the code, made the fix, then ran everything. `gpt-6.1-sol` fixed 29 and ran the suite first in 28 of them. Qwen, tied for the fewest fixes, ran it first in most runs, because it explores by running things. The obligation splits the models by habit, and the habit has nothing to do with who fixes more bugs.

Put the obligation together with the forbidden list and the ordering turns upside down. In about half its runs `gpt-6.1-sol` added a regression test next to its fix, which is good practice too, and E1 forbids editing the tests. So under E2 the model that passes most often is Qwen, with 18 of its 22 fixes, and the strongest models come last: Opus 1 of 29, Sonnet 0 of 30. Two rules that each sound reasonable add up to a grader that ranks the field in reverse.

## The case nobody's grader could see

Ten of the 21 runs the final state let through in A come from one bug. The report says that `naturaldate`, given a datetime with a timezone, compares it against the wrong "today". The cause is one level down: `naturaldate` hands over to `naturalday`, and `naturalday` uses the machine's local date. The hidden tests also check `naturalday`. To find out how many of those checks follow from the report, I gave a separate model the report, the failing test and the hidden cases, and nothing else: no agent, no fix, no model names. Three runs, majority vote. The one case all ten runs fail was voted two to one. So whether these ten count as false passes is a judgement call, and that is where the 11-to-21 range comes from.

What the runs did is more telling than the score. Every model that explained the cause found the same one. What split them was a decision:

- **Opus and Sonnet** fixed `naturalday`, which fixes `naturaldate` with it. Opus said in all three runs that this also changes `naturalday` when it is called directly.
- **Haiku** found the same cause and chose not to change `naturalday`'s public behaviour. It moved the comparison into a private helper that takes "today" as an argument, so that only `naturaldate` passes the timezone-aware date. It said so in plain words: `naturalday` behaves as before.
- **Luna** patched `naturaldate` from the inside and never mentioned `naturalday` in any of its three runs.

Haiku and Luna fail exactly the same hidden cases. One made a reasoned engineering decision and stated it; the other made a local patch with no diagnosis. The final state can't tell them apart, and neither can the path: five of their six runs scored a path correctness of 1.0, because all they did was edit one file and run the tests. Only the agent's own account of what it did separates them.

The same goes for the clearest false claim in the study. In one Mathlib run, Luna started `lean Main.lean`, moved on before the compiler had finished, and ended with:

> `aime_1987_p5` is proved in Main.lean. `lean Main.lean` completed successfully.

The file does not compile. The tool had reported that its wrapper script was done, while the command itself, with no exit code yet, was still running, and Luna read one as the other. The visible check catches this file, because it doesn't compile. But the sentence is false, and it is in a place none of the four graders read. It happened in three of Luna's seventeen Mathlib runs; in two of them the proof happened to be valid anyway.

## What I take from it

- **Where a mechanical checker is strong, check the final state and forbid the shortcuts.** In Lean that was enough to drive false passes to zero. The only valid proofs it failed were five written with ASCII arrows, which a literal statement check reads as a changed statement. Grading the path added nothing there except a third of the valid proofs failed.
- **Where it is weak, the path still doesn't fill the gap.** In the bug world the false passes were fixes that did less than they seemed to, not forbidden actions. The path caught some of them only by failing whatever looked unusual.
- **An obligation is an opinion about method.** "Tests before the first edit" sounds unobjectionable. Here it sorted the models by habit, and combined with a ban on touching the tests it ranked them in reverse order of how well they fixed bugs.
- **What separated the cases that mattered was what the agent said.** The honest "I couldn't", the stated scope decision, the "completed successfully" that never completed. None of the four graders reads that, and each of those sentences can be checked against the trace. An exit code either appears or it doesn't.

That last point is an observation from a handful of runs, not a measured grader. Building that grader, and seeing whether it holds up, is the next experiment.

## Limits

Three runs per model and task; one Python library; a translation of CORE's path to proofs that is mine, not the paper's; twenty-six short theorems and nine competition problems, the latter with three models only. The Lean references were written by a model outside the comparison, and each theorem's two references were checked to use different strategies. Two of the checks have a second version, published next to the original rather than replacing it. The statement check also accepts ASCII spellings Lean reads as the same symbol (`->` for `→`), which turns five of Luna's proofs valid. The bug-world truth is also given limited to the hidden cases that follow from the report, which is where the 11 comes from. The Lean runs through Codex were repeated after faults in its sandbox that affected how `lean` ran there; the numbers here come from the repeated runs.
