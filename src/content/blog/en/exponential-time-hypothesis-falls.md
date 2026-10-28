---
title: "The Exponential Time Hypothesis Fell Twice. The Way Through Was a Minus Sign"
description: "OpenAI and Anthropic each published a Lean-checked algorithm that solves 3-SAT in subexponential time, refuting a 27-year-old hypothesis that hundreds of papers rested on. I read both papers. They hit the same wall, they went through it the same way, and one of them borrowed a 200-year-old identity from the octonions to do it."
pubDate: 2026-10-28
tags: ["AI", "Mathematics", "Complexity Theory", "Research", "Anthropic", "OpenAI"]
lang: en
translationKey: exponential-time-hypothesis-falls
heroImage: "/blog/exponential-time-hypothesis-falls.png"
linkedinImage: /blog/exponential-time-hypothesis-falls-fig-4.png
linkedinLinks:
  - label: "Anthropic's paper and Lean proof"
    url: "https://github.com/anthropics/formal-math/tree/main/eth"
  - label: "OpenAI's paper and Lean proof"
    url: "https://github.com/openai/math/blob/main/lean/docs/378.md"
---

On 26 October two papers appeared within hours of each other. One, from OpenAI, is titled [*The Exponential Time Hypothesis is False*](https://github.com/openai/math/blob/main/lean/docs/378.md). The other, from Anthropic, is credited to "Claude" and titled [*A 2^o(n) Time Algorithm for 3-SAT*](https://github.com/anthropics/formal-math/tree/main/eth). Both say the same thing: the reference hard problem of computer science, which I explain below with a dinner party, can be solved faster than anyone believed possible, and a conjecture that hundreds of results were built on is false. Both come with a proof checked line by line by Lean, a program that verifies mathematics mechanically. Both were found by an AI model the labs have not released. Anthropic's paper dates its discovery to 16 October, "with 14M output tokens and no human input"; OpenAI's manuscript is dated 17 October.

The headlines went for the AI-cracks-a-decades-old-puzzle angle and stopped there. That leaves out the part I find most interesting, which is *how*. I read both papers, and the answer is not two unrelated tricks. Both algorithms run into the same wall that every SAT algorithm since the 1980s has run into, and both get through it the same way: by solving a harder problem than the one asked, and letting negative numbers cancel. One of them does it with an identity a Danish mathematician wrote down in 1818.

None of this makes any real software faster, and none of it settles P vs NP, the famous million-dollar question. I'll get to why. First, the problem, in plain words, because without it nothing else in this story makes sense.

<style>
.eth-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.eth-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.eth-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## The problem: a dinner party with conditions

Say you are organising a dinner and your friends have sent conditions. "I'll come if Ana comes or Bea doesn't." "At least one of Carlos and Diego." "Not Ana, Bea and Carlos all together, please." Each friend is a yes/no decision, and each condition mentions at most three friends. The question: **is there any guest list that meets every condition at once?**

That is **3-SAT**. "SAT" stands for *satisfiability*: can all the conditions be satisfied together? The "3" is because each condition, called a *clause*, involves at most three yes/no variables. Written the way computer scientists write it, a clause looks like $(x_1 \lor \lnot x_2 \lor x_5)$: "friend 1 comes, or friend 2 doesn't, or friend 5 comes".

It looks like a parlour puzzle, and it is the puzzle. In 1971 Stephen Cook showed that a huge family of problems (timetables, delivery routes, verifying that a chip has no bugs, Sudoku, and thousands more) can be translated into it. Solve 3-SAT fast and you solve all of them fast. That is why it is the reference hard problem of computer science.

What makes it hard is an asymmetry. If someone hands you a guest list, **checking** it is trivial: go through the conditions one by one. **Finding** one is another matter. With $n$ friends there are $2^n$ possible lists: with 30 friends, about a billion; with 100, so many that a million computers each checking a billion lists per second would need some 40 million years to go through them. The question since the 1970s has been how much better than "try them all" you can do.

<figure class="eth-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="The asymmetry behind 3-SAT. On the left, checking one proposed guest list against three conditions takes one pass and three ticks. On the right, finding a valid list by trying them all means 2 to the n lists: 1,024 for 10 friends, about a billion for 30, and a 31-digit number for 100.">
  <text x="150" y="26" text-anchor="middle" font-size="13" fill="#5eead4" font-weight="700">Checking a list: easy</text>
  <text x="450" y="26" text-anchor="middle" font-size="13" fill="#fbbf24" font-weight="700">Finding one: 2ⁿ lists to try</text>
  <rect x="30" y="44" width="240" height="56" rx="8" fill="#0f1117" stroke="rgba(255,255,255,0.12)"/>
  <text x="44" y="66" font-size="11" fill="#94a3b8">guest list</text>
  <g font-size="12.5" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="44" y="88" fill="#e2e8f0">Ana ✔  Bea ✘  Carlos ✔  Diego ✘</text>
  </g>
  <g font-size="12" fill="#e2e8f0">
    <text x="44" y="132">Ana comes, or Bea doesn't</text>
    <text x="44" y="162">Carlos or Diego, at least one</text>
    <text x="44" y="192">Not Ana, Bea and Carlos together</text>
  </g>
  <g font-size="15" fill="#2dd4bf" font-weight="700"><text x="256" y="133" text-anchor="end">✔</text><text x="256" y="163" text-anchor="end">✔</text><text x="256" y="193" text-anchor="end">✔</text></g>
  <text x="150" y="228" text-anchor="middle" font-size="11.5" fill="#94a3b8">one pass over the conditions</text>
  <line x1="300" y1="44" x2="300" y2="220" stroke="rgba(255,255,255,0.1)"/>
  <g font-size="12" fill="#e2e8f0">
    <text x="330" y="78">10 friends</text><text x="330" y="132">30 friends</text><text x="330" y="186">100 friends</text>
  </g>
  <rect x="420" y="66" width="19" height="16" rx="2" fill="#f59e0b"/>
  <rect x="420" y="120" width="48" height="16" rx="2" fill="#f59e0b"/>
  <rect x="420" y="174" width="150" height="16" rx="2" fill="#f59e0b"/>
  <g font-size="12" font-family="ui-monospace,'JetBrains Mono',monospace" fill="#fbbf24">
    <text x="447" y="78">1,024</text><text x="476" y="132">≈ 1 billion</text><text x="420" y="210">a 31-digit number</text>
  </g>
  <text x="450" y="236" text-anchor="middle" font-size="11.5" fill="#94a3b8">(bar length: number of digits)</text>
</svg>
<figcaption>The asymmetry behind 3-SAT. Checking a proposed answer is quick; finding one by trying them all doubles in cost with every friend you add.</figcaption>
</figure>

## What the hypothesis said

The best algorithms don't try everything; they prune, guess cleverly, and backtrack. But their running time still grows *exponentially*: each extra variable multiplies the work by a fixed factor, the *base*. For trying everything the base is 2 (one more friend, twice the lists). Schöning's random walk brought it to $1.334$ in 1999, PPSZ with Hertli's analysis to $1.308$, Liu's deterministic algorithm to $1.328$. That sounds like a small gain and it is an enormous one: $2^{100}$ is a 31-digit number, $1.308^{100}$ a 12-digit one. But forty years of very clever work never brought the base close to 1.

In 1999 Russell Impagliazzo and Ramamohan Paturi turned that experience into a conjecture, the **Exponential Time Hypothesis** (ETH): the base can be lowered but never to 1. Put precisely: there is some number $c$ greater than 1 such that no algorithm solves every 3-SAT instance faster than $c^n$. However clever the algorithm, each extra variable will always cost at least that fixed multiplier. Its stronger sibling, SETH, says that when conditions can mention many variables, you cannot even lower the base much.

Papers usually write the same thing with the base fixed at 2 and the change moved into the exponent. Any base $c$ is a power of 2, $c = 2^{\delta}$, so $c^n = 2^{\delta n}$: trying everything is $\delta = 1$, and $1.308^n$ is about $2^{0.39n}$. Lowering the base towards 1 and lowering $\delta$ towards 0 are the same thing. In that language ETH says $\delta$ can never go below some fixed positive number.

An algorithm that breaks this is called *subexponential*, written $2^{o(n)}$: its exponent grows more slowly than $\delta n$ for every $\delta > 0$. In the language of bases, the multiplier you pay per extra variable keeps shrinking towards 1 as the problem grows. It is still not fast in any everyday sense, but it is a different kind of growth, and ETH said it was impossible.

<figure class="eth-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Bar chart of the best known running time for 3-SAT written as base to the n: brute force 2, Schöning 1999 1.334, Liu 2018 deterministic 1.328, PPSZ with Hertli 2014 randomized 1.308. The 2026 algorithms have an effective base that tends to 1 as n grows, which is what refutes the Exponential Time Hypothesis.">
  <g font-size="11" fill="#94a3b8">
    <text x="170" y="250" text-anchor="middle">1.0</text>
    <text x="300" y="250" text-anchor="middle">1.25</text>
    <text x="430" y="250" text-anchor="middle">1.5</text>
    <text x="560" y="250" text-anchor="middle">2.0</text>
  </g>
  <g stroke="rgba(255,255,255,0.08)">
    <line x1="170" y1="20" x2="170" y2="236"/><line x1="300" y1="20" x2="300" y2="236"/><line x1="430" y1="20" x2="430" y2="236"/><line x1="560" y1="20" x2="560" y2="236"/>
  </g>
  <g font-size="12" fill="#e2e8f0">
    <text x="160" y="44" text-anchor="end">Brute force</text>
    <text x="160" y="88" text-anchor="end">Schöning (1999)</text>
    <text x="160" y="132" text-anchor="end">Liu (2018, determ.)</text>
    <text x="160" y="176" text-anchor="end">PPSZ + Hertli (2014)</text>
    <text x="160" y="220" text-anchor="end" fill="#fbbf24" font-weight="700">2026, both labs</text>
  </g>
  <!-- scale: base 1 -> x=170, base 2 -> x=560 is not linear for 1.5; use piecewise: 1..1.5 -> 170..430 (520 px per unit), 1.5..2 -> 430..560 -->
  <rect x="170" y="30" width="390" height="22" rx="4" fill="#64748b"/>
  <rect x="170" y="74" width="174" height="22" rx="4" fill="#2dd4bf" opacity=".75"/>
  <rect x="170" y="118" width="171" height="22" rx="4" fill="#2dd4bf" opacity=".75"/>
  <rect x="170" y="162" width="160" height="22" rx="4" fill="#2dd4bf"/>
  <rect x="170" y="206" width="6" height="22" rx="2" fill="#f59e0b"/>
  <g font-size="12" font-family="ui-monospace,'JetBrains Mono',monospace" fill="#f8fafc">
    <text x="548" y="46" text-anchor="end">2ⁿ</text>
    <text x="352" y="90">1.334ⁿ</text>
    <text x="349" y="134">1.328ⁿ</text>
    <text x="338" y="178">1.308ⁿ</text>
    <text x="186" y="222" fill="#fbbf24">2^o(n): the base tends to 1</text>
  </g>
</svg>
<figcaption>Forty years of progress on 3-SAT lowered the base of the exponent. ETH bet that it could never reach 1. The new algorithms take time 2^o(n): their effective base slides to 1 as n grows. (The axis is compressed between 1.5 and 2.)</figcaption>
</figure>

That bet was not idle. Anthropic's paper reports a literature search, carried out by Claude, that found more than 800 papers proving at least one result only under ETH or something that implies it. ETH is the reason we "know" that k-Clique has no $n^{o(k)}$ algorithm, that many parameterized algorithms are optimal, that dynamic programming over tree decompositions cannot be improved. In 2019 Ryan Williams put his own odds at 70% that ETH was true and 25% for SETH. Most of the field would have put them higher.

Both papers now give a deterministic algorithm that runs in $2^{o(n)}$: for every $\delta > 0$ it is eventually faster than $2^{\delta n}$, which is to say it eventually beats every base above 1. That refutes ETH, SETH, Gap-ETH and the counting version #ETH in one go.

## The wall

Here is the intuition for why the base never reached 1, and it is the same picture in both papers.

Go back to the dinner. Draw each condition as a dot, and join two dots with a line when they mention the same friend. Anthropic's paper says each line "carries bits", one per shared yes/no decision. The natural shortcut is divide and conquer: split the drawing in two halves, try every possible answer for just the friends whose lines cross the split, and for each of those, solve each half on its own. If your friends form two groups that barely know each other, only a few decisions cross the split, and this is enormously faster than trying every list.

The problem is that you don't get to choose the friends. Random sets of conditions, and the hard instances generally, look like **expander graphs**, where every way of splitting the nodes into two halves of comparable size is crossed by a constant fraction of all the edges. In the paper's words, "any algorithm that fixes one tree of cuts in advance and enumerates the crossing bits of each cut takes time $2^{\Omega(n)}$. Thus earlier divide and conquer ideas only improved the constant in the exponent."

<figure class="eth-fig">
<svg viewBox="0 0 600 262" role="img" aria-label="Two graphs side by side. On the left, a formula whose clause graph has two loosely connected clusters: a cut between them is crossed by only two edges, so divide and conquer is cheap. On the right, an expander-like graph where every balanced cut is crossed by many edges, so enumerating the crossing bits costs exponential time whatever cut is chosen.">
  <text x="150" y="22" text-anchor="middle" font-size="13" fill="#e2e8f0" font-weight="700">Clustered formula</text>
  <text x="450" y="22" text-anchor="middle" font-size="13" fill="#e2e8f0" font-weight="700">Expander-like formula</text>
  <g stroke="#64748b" stroke-width="1.6">
    <line x1="60" y1="70" x2="100" y2="110"/><line x1="60" y1="70" x2="50" y2="140"/><line x1="100" y1="110" x2="50" y2="140"/><line x1="100" y1="110" x2="80" y2="185"/><line x1="50" y1="140" x2="80" y2="185"/><line x1="60" y1="70" x2="110" y2="60"/><line x1="110" y1="60" x2="100" y2="110"/>
    <line x1="200" y1="70" x2="240" y2="110"/><line x1="200" y1="70" x2="250" y2="150"/><line x1="240" y1="110" x2="250" y2="150"/><line x1="250" y1="150" x2="215" y2="190"/><line x1="240" y1="110" x2="215" y2="190"/><line x1="200" y1="70" x2="190" y2="130"/><line x1="190" y1="130" x2="215" y2="190"/>
  </g>
  <g stroke="#f59e0b" stroke-width="2.2">
    <line x1="110" y1="60" x2="200" y2="70"/><line x1="80" y1="185" x2="190" y2="130"/>
  </g>
  <line x1="150" y1="40" x2="150" y2="210" stroke="#fbbf24" stroke-width="1.5" stroke-dasharray="5 4"/>
  <g fill="#1a1a24" stroke="#2dd4bf" stroke-width="2">
    <circle cx="60" cy="70" r="7"/><circle cx="100" cy="110" r="7"/><circle cx="50" cy="140" r="7"/><circle cx="80" cy="185" r="7"/><circle cx="110" cy="60" r="7"/>
    <circle cx="200" cy="70" r="7"/><circle cx="240" cy="110" r="7"/><circle cx="250" cy="150" r="7"/><circle cx="215" cy="190" r="7"/><circle cx="190" cy="130" r="7"/>
  </g>
  <text x="150" y="250" text-anchor="middle" font-size="12" fill="#fbbf24">2 edges cross: enumerate 2 bits</text>
  <g transform="translate(450,132)">
    <g stroke="#64748b" stroke-width="1.4">
      <line x1="0" y1="-85" x2="74" y2="42"/><line x1="0" y1="-85" x2="-74" y2="42"/><line x1="0" y1="-85" x2="42" y2="74"/>
      <line x1="42" y1="-74" x2="-42" y2="74"/><line x1="42" y1="-74" x2="-85" y2="0"/><line x1="42" y1="-74" x2="0" y2="85"/>
      <line x1="74" y1="-42" x2="-74" y2="-42"/><line x1="74" y1="-42" x2="-42" y2="74"/><line x1="74" y1="-42" x2="-42" y2="-74"/>
      <line x1="85" y1="0" x2="-85" y2="0"/><line x1="85" y1="0" x2="-42" y2="-74"/><line x1="85" y1="0" x2="0" y2="85"/>
      <line x1="74" y1="42" x2="-74" y2="-42"/><line x1="42" y1="74" x2="-74" y2="42"/><line x1="0" y1="85" x2="-74" y2="-42"/><line x1="-42" y1="74" x2="-85" y2="0"/>
      <line x1="0" y1="-85" x2="42" y2="-74"/><line x1="74" y1="42" x2="85" y2="0"/><line x1="-74" y1="42" x2="-42" y2="74"/><line x1="-42" y1="-74" x2="-74" y2="-42"/>
    </g>
    <line x1="-15" y1="-100" x2="15" y2="100" stroke="#fbbf24" stroke-width="1.5" stroke-dasharray="5 4"/>
    <g fill="#1a1a24" stroke="#2dd4bf" stroke-width="2">
      <circle cx="0" cy="-85" r="7"/><circle cx="42" cy="-74" r="7"/><circle cx="74" cy="-42" r="7"/><circle cx="85" cy="0" r="7"/><circle cx="74" cy="42" r="7"/><circle cx="42" cy="74" r="7"/><circle cx="0" cy="85" r="7"/><circle cx="-42" cy="74" r="7"/><circle cx="-74" cy="42" r="7"/><circle cx="-85" cy="0" r="7"/><circle cx="-74" cy="-42" r="7"/><circle cx="-42" cy="-74" r="7"/>
    </g>
  </g>
  <text x="450" y="250" text-anchor="middle" font-size="12" fill="#fbbf24">any balanced cut: a constant fraction of all bits</text>
</svg>
<figcaption>Divide and conquer pays for the bits that cross the cut. On hard formulas every balanced cut is crossed by a constant fraction of the bits, so any fixed plan of cuts costs 2^Ω(n). This is the wall.</figcaption>
</figure>

To go through the wall you have to stop paying for every crossing bit. And there is no way to do that if every quantity you handle means "number of solutions of something", because counts of solutions are non-negative and cannot cancel.

## Count, don't decide

So both papers do something that sounds backwards. They don't ask "is there a valid guest list?". They ask "**how many** valid guest lists are there?" and compute the exact number, which is the #3-SAT problem and is in principle much harder (the previous best for counting was around $1.64^n$, worse than for deciding). Testing whether the count is zero then decides satisfiability for free.

Why make your life harder? Because a count is a sum, and a sum is algebra. The number of satisfying assignments is

$$\#F = \sum_{x \in \{0,1\}^n} \prod_{\text{clauses } e} \Phi_e(x)$$

where each $\Phi_e$ is 1 if clause $e$ is satisfied and 0 otherwise. A sum of products can be rearranged, rewritten, expanded and regrouped, and nothing forces the intermediate terms to be 0 or 1 or even positive. Once negative numbers are allowed in the middle of the computation, two expensive pieces can cancel into a cheap one. Branching algorithms, which ask "what if $x_1$ is true?", can't do this: every branch is a real sub-question with a real non-negative answer.

That is the common move. The two papers then implement it in completely different ways.

*If you only want the idea, you have it: the wall is that hard problems can't be split cleanly, and the way through is to count with numbers that can be negative, so the expensive parts cancel. The next two sections show how each lab did it, with a bit more mathematics; you can skip to [What changes, and what doesn't](#what-changes-and-what-doesnt) without losing the thread.*

## Claude's route: an identity from 1818

Anthropic's algorithm stays with the graph picture and attacks the bits that cross.

Take the clause graph and merge clauses into a modest number $K$ of big nodes, so that every pair of big nodes is joined by an edge carrying the same number $\lambda$ of bits. The quantity to beat is the total number of crossing bits, $S$. Now place the nodes on a $g \times g$ grid. Most edges are *diagonals*: they join two nodes in different rows and different columns. Every diagonal belongs to exactly one rectangle, and each rectangle has two diagonals: the top-left corner holds a string $x$ that must equal the bottom-right's $v$, and the top-right holds $y$, which must equal the bottom-left's $u$. That pair of equality checks, $[x = v]\,[y = u]$, the paper calls a crossing.

If you merge each row into one node, a crossing costs 6 bits per block of 3: the top row has to tell the bottom row both $x$ and $y$. Here comes the identity. For blocks of 3 bits there is a sign function $\sigma$ such that

$$2\,[x = v]\,[y = u] = [x \oplus y \oplus u \oplus v = 0]\,\big(\sigma(x,y)\,\sigma(v,u) + \sigma(x,u)\,\sigma(v,y)\big)$$

and it can be checked by brute force on all 4,096 settings of the 12 bits. Read the right-hand side as two terms. In the first, the **row choice**, each $\sigma$ depends only on one row, and the two rows only need to agree on the single 3-bit string $x \oplus y = u \oplus v$. That costs 3 bits, half of the 6. The second term, the **column choice**, is still expensive if you merged rows, but it costs only 3 bits if you merge columns instead. Neither term means anything combinatorially, they take negative values, and only their sum is a count. But each term is cheap in one direction.

<figure class="eth-fig">
<svg viewBox="0 0 640 280" role="img" aria-label="A rectangle of the grid with corners holding strings x, y on top and u, v below. Its two diagonals test x equals v and y equals u, which costs six bits per block when rows are merged. The eight-square identity rewrites twice this crossing as a four-corner parity check times the sum of a row choice, whose sign functions each live in one row and cost three bits, and a column choice, which costs six bits with rows merged but three with columns merged.">
  <defs>
    <marker id="eth-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <g font-size="12.5" text-anchor="middle" fill="#e2e8f0" font-weight="700">
    <text x="100" y="24">2 × crossing</text>
    <text x="300" y="24" fill="#5eead4">row choice</text>
    <text x="520" y="24" fill="#fbbf24">column choice</text>
  </g>
  <text x="200" y="118" font-size="22" fill="#94a3b8" text-anchor="middle">=</text>
  <text x="400" y="118" font-size="22" fill="#94a3b8" text-anchor="middle">+</text>
  <!-- panel 1 -->
  <g stroke="#e2e8f0" stroke-width="2">
    <line x1="50" y1="60" x2="150" y2="170"/><line x1="150" y1="60" x2="50" y2="170"/>
  </g>
  <!-- panel 2: hyperedge + row edges -->
  <g stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="3 3">
    <line x1="250" y1="60" x2="300" y2="115"/><line x1="350" y1="60" x2="300" y2="115"/><line x1="250" y1="170" x2="300" y2="115"/><line x1="350" y1="170" x2="300" y2="115"/>
    <line x1="470" y1="60" x2="520" y2="115"/><line x1="570" y1="60" x2="520" y2="115"/><line x1="470" y1="170" x2="520" y2="115"/><line x1="570" y1="170" x2="520" y2="115"/>
  </g>
  <circle cx="300" cy="115" r="4" fill="#94a3b8"/><circle cx="520" cy="115" r="4" fill="#94a3b8"/>
  <g stroke="#2dd4bf" stroke-width="3"><line x1="250" y1="60" x2="350" y2="60"/><line x1="250" y1="170" x2="350" y2="170"/></g>
  <g stroke="#f59e0b" stroke-width="3"><line x1="470" y1="60" x2="470" y2="170"/><line x1="570" y1="60" x2="570" y2="170"/></g>
  <g fill="#1a1a24" stroke="#2dd4bf" stroke-width="2">
    <circle cx="50" cy="60" r="15"/><circle cx="150" cy="60" r="15"/><circle cx="50" cy="170" r="15"/><circle cx="150" cy="170" r="15"/>
    <circle cx="250" cy="60" r="15"/><circle cx="350" cy="60" r="15"/><circle cx="250" cy="170" r="15"/><circle cx="350" cy="170" r="15"/>
    <circle cx="470" cy="60" r="15"/><circle cx="570" cy="60" r="15"/><circle cx="470" cy="170" r="15"/><circle cx="570" cy="170" r="15"/>
  </g>
  <g font-size="13" text-anchor="middle" fill="#f8fafc" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="50" y="65">x</text><text x="150" y="65">y</text><text x="50" y="175">u</text><text x="150" y="175">v</text>
    <text x="250" y="65">x</text><text x="350" y="65">y</text><text x="250" y="175">u</text><text x="350" y="175">v</text>
    <text x="470" y="65">x</text><text x="570" y="65">y</text><text x="470" y="175">u</text><text x="570" y="175">v</text>
  </g>
  <g font-size="10.5" text-anchor="middle" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="100" y="204">x=v · y=u</text>
    <text x="300" y="50">σ(x,y)</text><text x="300" y="192">σ(v,u)</text>
    <rect x="264" y="131" width="72" height="13" fill="#1a1a24"/><text x="300" y="141">x⊕y⊕u⊕v=0</text>
    <text x="460" y="119" text-anchor="end">σ(x,u)</text><text x="580" y="119" text-anchor="start">σ(v,y)</text>
    <rect x="484" y="131" width="72" height="13" fill="#1a1a24"/><text x="520" y="141">x⊕y⊕u⊕v=0</text>
  </g>
  <line x1="20" y1="218" x2="620" y2="218" stroke="rgba(255,255,255,0.1)"/>
  <text x="20" y="236" font-size="11.5" fill="#94a3b8">with rows merged, bits per 3-bit block:</text>
  <g font-size="14" text-anchor="middle" font-weight="700">
    <text x="100" y="264" fill="#e2e8f0">6 bits</text>
    <text x="300" y="264" fill="#5eead4">3 bits</text>
    <text x="520" y="264" fill="#fbbf24">6 bits (3 if columns merged)</text>
  </g>
</svg>
<figcaption>The eight-square identity for one rectangle. Two diagonal checks become a four-corner parity check times a signed sum of two terms. Each term is cheap along one direction of the grid, so whichever direction you merge, a share of the bits disappears.</figcaption>
</figure>

The rest is bookkeeping, done carefully. Strings are split into blocks of 3, and the expansion is grouped by how many blocks took the column choice, which keeps the number of terms polynomial. For each term the algorithm merges rows or columns, whichever is cheaper. Per block, the two directions together cost $3 + 6 + 1 + 1 = 11$ bits against the $12$ of two crossings, so the cheaper direction pays at most $11/12$ of what was there before. Then it groups the merged rows into $K$ balanced super-nodes and recurses.

The paper writes the running time as $2^{e S}$, where $S$ is the number of bits on the edges, proportional to the size of the formula. So $e$ plays the role of $\delta$ above, and $2^e$ is the base, paid per bit instead of per variable. One level shrinks $e$ by a factor of $11/12$. Repeat it and $e$ goes to zero, which is the base going to 1: the paper's bound is $e_\ell \le 1.12\,(11/12)^\ell$. The price is that each level needs vastly more nodes, $K_\ell = 9K_{\ell-1}^{16}$ starting from 64, which is why all of this only matters for astronomically large formulas.

<figure class="eth-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Chart of the running-time exponent at each level of the recursion in Anthropic's algorithm. Level 0 is brute force with exponent 1. Level 1 is slightly worse, about 1.03, because the first grid is small. From level 2 on, the exponent falls by a factor of eleven twelfths per level, bounded by 1.12 times eleven twelfths to the level, reaching under 0.47 by level 10 and tending to zero.">
  <g stroke="rgba(255,255,255,0.08)"><line x1="60" y1="30" x2="580" y2="30"/><line x1="60" y1="105" x2="580" y2="105"/><line x1="60" y1="180" x2="580" y2="180"/></g>
  <g font-size="11" fill="#94a3b8" text-anchor="end"><text x="52" y="34">1.0</text><text x="52" y="109">0.5</text><text x="52" y="184">0</text></g>
  <g fill="#2dd4bf">
    <rect x="72" y="30" width="30" height="150" fill="#64748b"/>
    <rect x="119" y="25.5" width="30" height="154.5" fill="#64748b"/>
    <rect x="166" y="38.8" width="30" height="141.2"/>
    <rect x="213" y="50.6" width="30" height="129.4"/>
    <rect x="260" y="61.4" width="30" height="118.6"/>
    <rect x="307" y="71.3" width="30" height="108.7"/>
    <rect x="354" y="80.3" width="30" height="99.7"/>
    <rect x="401" y="88.6" width="30" height="91.4"/>
    <rect x="448" y="96.2" width="30" height="83.8"/>
    <rect x="495" y="103.2" width="30" height="76.8"/>
    <rect x="542" y="109.6" width="30" height="70.4"/>
  </g>
  <g font-size="11" fill="#e2e8f0" text-anchor="middle">
    <text x="87" y="198">0</text><text x="134" y="198">1</text><text x="181" y="198">2</text><text x="228" y="198">3</text><text x="275" y="198">4</text><text x="322" y="198">5</text><text x="369" y="198">6</text><text x="416" y="198">7</text><text x="463" y="198">8</text><text x="510" y="198">9</text><text x="557" y="198">10</text>
  </g>
  <text x="320" y="222" font-size="11.5" fill="#94a3b8" text-anchor="middle">recursion level ℓ (bound e_ℓ ≤ 1.12 · (11/12)^ℓ from level 2)</text>
  <text x="87" y="22" font-size="10.5" fill="#94a3b8" text-anchor="middle">brute</text>
</svg>
<figcaption>Each level of the recursion multiplies the exponent (the δ of 2^δn, so the base is 2^δ) by about 11/12. It never reaches zero at any fixed level, but it gets below any δ you name, which is exactly what refuting ETH requires.</figcaption>
</figure>

The identity is the beautiful part. Its classical form says that the product of two sums of eight squares is again a sum of eight squares. Ferdinand Degen found it in 1818, and John Graves found it again in 1843 while showing that the norm of the octonions, the eight-dimensional cousin of the complex numbers, is multiplicative. The sign function $\sigma$ in the algorithm is, in the paper's words, "the table of signs of the multiplication of the octonions, with the basis elements renamed". Hurwitz proved in 1898 that such identities exist only for 1, 2, 4 and 8 squares. The paper has an appendix explaining why the search for a cheaper decomposition of a crossing leads straight to Hurwitz's problem, and why, under the simple bit count it uses, only eight leaves a gain: two squares break even, four break even, eight give 11 out of 12.

So the thing that broke ETH is the multiplication table of the octonions, used to cut bits on a grid.

## OpenAI's route: deform the problem, then interpolate back

OpenAI's algorithm uses the same "count, and let terms cancel" idea through a different door: interpolation.

Start from the same formula for $\#F$. Now introduce a parameter $T$ and replace each variable occurrence inside each clause by a linear combination of variables whose coefficients are polynomials in $T$. At $T = 0$ every replacement is the original variable, so the deformed sum $H(T)$ satisfies $H(0) = \#F$. At the points $T = 1, \dots, Q$, the replacements are designed so that the variables split into small groups that interact only through a few shared "measurements", small integer linear combinations of each group's bits. Fix the values of those measurements and the sum factorizes group by group, exactly the way the clustered formula of the earlier figure would. At those points the expensive problem becomes cheap.

<figure class="eth-fig">
<svg viewBox="0 0 600 240" role="img" aria-label="Sketch of OpenAI's interpolation strategy. A polynomial H of T is drawn as a curve. At T equals zero, its value is the exact number of satisfying assignments, which is hard to compute directly. At the points T equals one to Q, the problem splits into groups and is cheap, so the algorithm computes the value and a few Taylor coefficients there, drawn as short tangent marks. Because the degree of H is known, these determine H, and therefore H of zero.">
  <line x1="50" y1="200" x2="580" y2="200" stroke="#64748b" stroke-width="1.5"/>
  <line x1="80" y1="30" x2="80" y2="210" stroke="#64748b" stroke-width="1.5"/>
  <path d="M80,70 C140,170 190,40 250,110 S350,180 410,95 S520,60 570,140" fill="none" stroke="#e2e8f0" stroke-width="2"/>
  <circle cx="80" cy="70" r="8" fill="#1a1a24" stroke="#f59e0b" stroke-width="3"/>
  <text x="98" y="48" font-size="12" fill="#fbbf24" font-weight="700">H(0) = #F</text>
  <text x="98" y="63" font-size="11" fill="#94a3b8">the count we want: hard here</text>
  <g stroke="#2dd4bf" stroke-width="3">
    <line x1="182" y1="85" x2="214" y2="61"/>
    <line x1="272" y1="124" x2="308" y2="148"/>
    <line x1="342" y1="166" x2="378" y2="146"/>
    <line x1="432" y1="80" x2="468" y2="72"/>
    <line x1="508" y1="74" x2="540" y2="96"/>
  </g>
  <g fill="#2dd4bf"><circle cx="198" cy="73" r="5"/><circle cx="290" cy="136" r="5"/><circle cx="360" cy="156" r="5"/><circle cx="450" cy="76" r="5"/><circle cx="524" cy="85" r="5"/></g>
  <g font-size="11" fill="#e2e8f0" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="80" y="218">0</text><text x="198" y="218">1</text><text x="290" y="218">2</text><text x="360" y="218">3</text><text x="450" y="218">…</text><text x="524" y="218">Q</text>
  </g>
  <text x="360" y="236" font-size="11.5" fill="#5eead4" text-anchor="middle">easy points: groups separate, compute value + a few Taylor coefficients</text>
  <path d="M175,95 C140,110 115,95 92,78" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#eth-ar2)"/>
  <defs><marker id="eth-ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
  <text x="128" y="128" font-size="10.5" fill="#94a3b8" text-anchor="middle">interpolate</text>
  <text x="128" y="141" font-size="10.5" fill="#94a3b8" text-anchor="middle">back (exact)</text>
</svg>
<figcaption>OpenAI's strategy: deform the counting problem into a polynomial H(T) of known degree. At T = 0 it is the count; at T = 1…Q it splits into independent groups. A few Taylor coefficients at each easy point pin down the polynomial, and with it the count.</figcaption>
</figure>

Because $H$ is a polynomial of known degree, its values and a few derivatives at the easy points determine it completely, and you read off $H(0)$. Interpolation here is not an approximation: it is exact rational arithmetic. The whole difficulty is in a tension between two costs. The replacements must have low degree in $T$, or you need too many Taylor coefficients per point. And they must respect a *different* grouping at each of the $Q$ points, which naively costs degree $Q$.

The construction that resolves it is where the minus sign comes back. It is built out of **swaps**: permutation matrices $\Pi_s$ that exchange two group labels at position $s$, each with eigenvalues $+1$ and $-1$. A basis vector with $j$ of its positions in the $-1$ eigenspace gets multiplied by $(-1)^j$ under the full swap. OpenAI chooses a polynomial $f$ that interpolates $(-1)^j$ only on a short window of $j$ values, centred where a binomial distribution puts almost all of its mass. Inside the window the construction is exact; the few directions outside it are paid for with explicit measurements. The window only needs to be about as wide as the binomial's standard deviation, $\sqrt{Q}$, and with $Q \approx \log n$ that is where the $\sqrt{\log n}$ in the final bound comes from.

Multiply out the three costs (Taylor data, measurements, one group at a time) and each one is $2^{o(n)}$. The algorithm also runs in polynomial space, which Anthropic's does not claim.

## Same wall, same minus sign

Side by side:

| | OpenAI | Anthropic (Claude) |
|---|---|---|
| Date on the paper | 17 October, revised 25 October | 26 October; core found 16 October |
| Length | 67 pages | 49 pages |
| What it computes | exact #k-SAT, deterministic | exact #k-SAT, deterministic |
| Bound, sparse formulas | $2^{O(n/\sqrt{\log n})}$ | $2^{O(m/\sqrt{\log m})}$ in the clause count |
| Bound, any formula | $2^{O(n \log\log n/\sqrt{\log n})}$ | $2^{O(k^2 n \log\log n/\sqrt{\log n})}$ |
| Bound proved in Lean | weaker: $(\log\log n)^2$ in place of $\log\log n$ | the main theorem as stated |
| Key device | deformation + Hermite interpolation; swap matrices, $f(j) = (-1)^j$ | grid + eight-square identity; recursion with factor 11/12 |
| Space | polynomial | not claimed |

The bounds land in the same place, which is either a coincidence or a hint about where the natural barrier for this family of techniques sits. Neither paper knows how to remove the $\log\log n$ for general formulas.

And the mechanisms rhyme more than they look. OpenAI's construction is literally built from swap operators with eigenvalues $\pm 1$. Anthropic's README compresses its own key idea into a paragraph that includes "Per bit, SWAP = I − 2·singlet", the physicist's way of writing a swap as the identity minus a signed correction. Both papers solve a harder problem so they can work with signed quantities, and both get their saving from writing an exchange of two things as a combination of cheaper things with signs. The non-negative world, where every intermediate number counts solutions of something, is exactly where ETH was true.

## What changes, and what doesn't

**Nothing changes in practice.** Anthropic's paper is unusually blunt about it. For a 3-CNF with $m = 5n$ clauses its bound beats the $2^n$ of brute force only once $n > 10^{10\,000}$, and the bound in $n$ alone only once $n > 10^{10^8}$. The authors add that their general approach "seems unlikely to yield any general improvement unless $n > 10^7$, however it is instantiated", while brute force is already impossible at $n = 100$. Your SAT solver, your scheduler, your verification tool are exactly as fast as last week.

**P vs NP is untouched.** P vs NP asks whether problems like 3-SAT can be solved in *polynomial* time, with work growing like $n^2$ or $n^3$, which is far faster than anything in these papers. ETH was a stronger bet than P ≠ NP, so losing it says nothing about the weaker one. And a $2^{o(n)}$ bound for 3-SAT does not transfer to every NP problem, because polynomial-time reductions can blow up the number of variables polynomially, and $2^{o(n)}$ composed with a polynomial is no longer subexponential. For problems with reductions that keep the size linear, it does transfer: OpenAI derives subexponential counting of independent sets, proper colourings and perfect matchings; Anthropic lists Independent Set, Clique, Vertex Cover and Dominating Set in $O(2^{\delta n})$ for every $\delta > 0$.

**A shelf of theorems changed status.** Everything proved "under ETH" or "under SETH" has lost its hypothesis. Some of it survives on weaker foundations: the quadratic lower bounds for edit distance and longest common subsequence also follow from the Orthogonal Vectors conjecture, which neither paper refutes. Much of it, the 800-odd papers' worth, now needs a new reason to be true or turns out to be false.

**And there is one genuinely unconditional gain.** Through Ryan Williams's programme, which turns slightly-faster-than-brute-force SAT algorithms into circuit lower bounds, both papers get that the class $E^{NP}$ has no Boolean circuits of linear size. OpenAI's version gives a lower bound of order $n\sqrt{\log n}$. The best known before, over the full binary basis, was $3.1n$. Circuit lower bounds are one of the most stuck areas of complexity theory, and this one came out as a side effect.

## What Lean checks, and what it doesn't

Both results are formalized, and both teams are careful about what that means. Anthropic's README says it in one line I wish every formalization carried: "Lean checks the proofs, but no machine checks that this file says what the paper says; the file is kept short so that a reader can check this." OpenAI's Lean scope note is similarly precise: the machine-checked bound is the weaker one with $(\log\log n)^2$; the sharper bound in the paper is not.

That is the gap I wrote about in [Proved, Certified, Swept, Sampled](/en/blog/proved-certified-swept-sampled): a green check is a statement about a specific claim, and the work is knowing which claim. Here it is handled well. The statements are short, they are printed in the papers, and the differences from the prose are listed. As I write this, human review is still under way: according to the coverage, OpenAI handed its result to outside reviewers that include Impagliazzo and Paturi themselves. A Lean proof of a correctly stated theorem leaves them very little to find, but "correctly stated" is the part they are there for.

## The proof that fits in a prompt

One more detail, and for someone who builds with these models it is the one that stays with me. At the end of Anthropic's README there is a section titled "The key idea, in condensed form interpretable by AI models". It is a single paragraph. It starts "The exponential time hypothesis is false!", states a recursion for the cost of contracting tensor networks on a complete graph, mentions the grid, the swap, the grouping by number of singlets, and ends "Prove it." The README says that Claude Opus 5.5 at high effort can rederive the refutation, in its weaker $O(2^{\delta n})$ form, from that paragraph alone.

That is a new kind of mathematical object. For centuries a proof has been written for a human reader, at whatever level of detail that reader needs. Here there are three layers: a 49-page paper for people, a Lean development for the kernel, and a one-paragraph hint for a model, which is enough because the model can fill in the rest. When I wrote about [the Navier–Stokes blow-up](/en/blog/navier-stokes-blows-up), the bottleneck was the opposite one: the machine's drafts were close to unreadable, and turning them into a paper a person could follow was weeks of work. Seven weeks later, the most compressed description of a major result is the one written for a machine.

## What to take from it

- **ETH is false, twice, independently, with formal proofs**, pending the human review that is now under way. SETH, Gap-ETH and #ETH go with it.
- **The wall was the expander, and the way through was a minus sign.** Both algorithms count instead of decide, so that terms can be negative and cancel. That is the one-sentence intuition, and it is the same for both.
- **Claude's version runs on the octonions.** A 1818 identity for sums of eight squares turns two crossing equality checks into terms that are each cheap in one direction, and a recursion multiplies the exponent by 11/12 per level until it is as small as you like.
- **OpenAI's version deforms and interpolates.** A polynomial that equals the count at 0 and splits into independent groups at $1, \dots, Q$, held together by swap matrices and a polynomial that imitates $(-1)^j$ on a window under a bell curve.
- **No practical consequence.** The crossover is beyond $10^{10\,000}$ variables. The consequences are for theory: hundreds of conditional lower bounds lose their hypothesis, and a circuit lower bound moved for free.
- **Two labs, the same week, the same bound.** Whatever this says about the problem, it says something about the models: the frontier of what they can find now includes a result that one of the field's leading experts, in 2019, put at 70-to-30 against.

---

*Sources: Anthropic's [paper and Lean formalization](https://github.com/anthropics/formal-math/tree/main/eth) (A 2^o(n) Time Algorithm for 3-SAT, by Claude), OpenAI's [Lean scope note](https://github.com/openai/math/blob/main/lean/docs/378.md) and [paper](https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/paper.pdf) (The Exponential Time Hypothesis is False).*
