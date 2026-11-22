---
title: "The Riemann Hypothesis Has a Proof Nobody Has Read. Its Core Idea Fits in a Sentence"
description: "An Anthropic mathematician and Claude published a Lean proof of the Riemann hypothesis: 175,187 files, accepted by independent checkers within hours, with no human-readable version. What the headlines skip: what exactly was proved, what a machine check does and does not settle, why the central idea is one Chebyshev would recognise, and which theorems just changed status."
pubDate: 2026-11-24
tags: ["AI", "Mathematics", "Agents", "Research", "Anthropic"]
lang: en
translationKey: riemann-hypothesis-proof
heroImage: "/blog/riemann-hypothesis-proof.png"
linkedinImage: /blog/riemann-hypothesis-proof-prime-sum.png
linkedinSummary: |
  A proof of the Riemann hypothesis has been published that no human has read in full, and the person who published it says he has not yet mastered it.

  It is 175,187 files of Lean, the language in which a small program checks every step of a proof. Within hours, people with no connection to the author had compiled it, checked that the statement is the standard one, and run it through a second checker written independently. All of them accepted it. Nobody has refereed the mathematics, and no version for people exists yet.

  That is a new situation, and it is not only about mathematics. We are getting used to work whose correctness can be checked by machine long before anyone understands it. "Is it right?" and "do we understand why?" used to arrive together. Now they come apart, sometimes by years.

  What surprised me when I read the material is that the core idea is not exotic. A whole number that is divisible by many primes cannot be small. Chebyshev used that in 1850 with factorials to get the first real estimates of how many primes there are. The proof uses the same principle with a far more divisible number, and the square root in the hypothesis comes out of balancing two costs.

  The author, Levent Alpöge, says Claude suggested that balance, and that Claude "far outpaced" him near the end. He also says he will now do the slow part: understand it and write it properly.

  If you work with agents, the question to carry over is the one mathematicians are facing this week: for the output you accept, what plays the role of the checker, and who is doing the understanding?
linkedinLinks:
  - label: "Alpöge's announcement"
    url: "https://alpo.ge/remark.pdf"
  - label: "Sutherland's verification files (MIT)"
    url: "https://math.mit.edu/~drew/grh/"
  - label: "Tao's note"
    url: "https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/"
---

On Friday 20 November, Levent Alpöge, a number theorist who works at Anthropic, posted a [four-page note](https://alpo.ge/remark.pdf) on his personal website. Its second paragraph begins: "I believe I have, working with Claude, discovered a proof of the Riemann Hypothesis." The proof itself is not in the note. It is in a footnote: fourteen links to an archive of Lean code, the language in which a program can check a mathematical proof step by step.

The Riemann hypothesis is the best-known open problem in mathematics. It is 167 years old, it is one of the seven Millennium Prize problems, and it says, in one line, that the prime numbers are spread as evenly as they possibly could be. By the end of that Friday, people who had nothing to do with the author had compiled the archive, and the checkers had accepted it.

The coverage has been about the machine beating the mathematicians, and about a second, all-human proof that appeared the same afternoon. Both are real stories. This is the third time since September that I write one of these, after [Navier–Stokes](/en/blog/navier-stokes-blows-up) in September and the [Exponential Time Hypothesis](/en/blog/exponential-time-hypothesis-falls) in October, and as with those, the parts I find most interesting do not fit in a headline: what exactly was proved, why this claim was not dismissed like all the earlier ones, what it means that nobody has read it, why the central idea is one you can explain at a blackboard, who did what, and which theorems changed status overnight.

<style>
.rh-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.rh-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.rh-fig img{display:block;width:100%;height:auto;margin:0;border:0;border-radius:.6rem}
.rh-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## What was proved, exactly

**The archive proves five statements, and the first one is the Riemann hypothesis word for word as the Lean community had already written it down.**

The primes thin out in a regular way: near a large number x, about one number in log x is prime. In 1859 Bernhard Riemann showed that the fine detail of that pattern is controlled by a single function, the zeta function ζ(s), and specifically by the complex numbers s where it equals zero. Some of those zeros are uninteresting (the negative even integers). All the others lie in a vertical strip of the complex plane, between real part 0 and real part 1. The hypothesis is that they all sit exactly in the middle of it, on the line of real part 1/2.

<figure class="rh-fig">
<svg viewBox="0 0 600 330" role="img" aria-label="The critical strip of the complex plane, between real part zero and real part one. The first ten nontrivial zeros of the Riemann zeta function, at heights from 14.13 to 49.77, all lie on the middle line of real part one half. A hypothetical zero off the line at real part 0.8 is drawn with its mirror image at real part 0.2: the Riemann hypothesis says no such pair exists">
  <rect x="230" y="24" width="140" height="276" fill="rgba(255,255,255,0.04)"/>
  <line x1="230" y1="24" x2="230" y2="300" stroke="rgba(255,255,255,0.22)" stroke-width="1"/>
  <line x1="370" y1="24" x2="370" y2="300" stroke="rgba(255,255,255,0.22)" stroke-width="1"/>
  <line x1="300" y1="18" x2="300" y2="300" stroke="#2dd4bf" stroke-width="2"/>
  <line x1="150" y1="300" x2="450" y2="300" stroke="#64748b" stroke-width="1.5"/>
  <g font-size="10.5" fill="#94a3b8" text-anchor="middle">
    <text x="230" y="316">0</text>
    <text x="300" y="316" fill="#5eead4" font-weight="700">1/2</text>
    <text x="370" y="316">1</text>
    <text x="430" y="316">real part of s</text>
  </g>
  <g fill="#2dd4bf">
    <circle cx="300" cy="226.5" r="4"/><circle cx="300" cy="190.7" r="4"/><circle cx="300" cy="169.9" r="4"/>
    <circle cx="300" cy="141.8" r="4"/><circle cx="300" cy="128.7" r="4"/><circle cx="300" cy="104.5" r="4"/>
    <circle cx="300" cy="87.2" r="4"/><circle cx="300" cy="74.7" r="4"/><circle cx="300" cy="50.4" r="4"/>
    <circle cx="300" cy="41.2" r="4"/>
  </g>
  <g font-size="9.5" fill="#94a3b8">
    <text x="310" y="230">14.13</text><text x="310" y="194">21.02</text><text x="310" y="173">25.01</text>
  </g>
  <g fill="none" stroke="#f59e0b" stroke-width="1.8" stroke-dasharray="3 2">
    <circle cx="342" cy="154" r="5"/><circle cx="258" cy="154" r="5"/>
  </g>
  <line x1="264" y1="154" x2="336" y2="154" stroke="#f59e0b" stroke-width="1" stroke-dasharray="2 3"/>
  <g font-size="10.5" fill="#e2e8f0">
    <text x="20" y="60" font-weight="700" fill="#5eead4">The critical line</text>
    <text x="20" y="76" fill="#94a3b8">The first ten zeros, computed.</text>
    <text x="20" y="90" fill="#94a3b8">Every zero ever computed</text>
    <text x="20" y="104" fill="#94a3b8">is on it.</text>
    <text x="392" y="140" font-weight="700" fill="#fbbf24">A zero off the line</text>
    <text x="392" y="156" fill="#94a3b8">would come with a mirror</text>
    <text x="392" y="170" fill="#94a3b8">image, and would make the</text>
    <text x="392" y="184" fill="#94a3b8">primes less regular.</text>
    <text x="392" y="204" fill="#94a3b8">The hypothesis: there is none.</text>
  </g>
  <text x="218" y="215" font-size="9.5" fill="#64748b" text-anchor="middle" transform="rotate(-90 218 215)">height (imaginary part of s)</text>
</svg>
<figcaption>Computing zeros, however many, can never prove the hypothesis: a proof has to exclude every zero off the line, at every height.</figcaption>
</figure>

Mathlib, the community library of mathematics formalized in Lean, already contained a definition called `RiemannHypothesis`. Nobody had proved it; the definition was there so that other results could say "assuming this". The archive's first theorem is a proof of exactly that definition, which matters more than it sounds: the statement was written by other people, before the proof existed, so the proof cannot have quietly proved something easier under the same name.

The other four statements go further. They say the same about a whole family of related functions, the Dirichlet L-functions, which control the primes inside arithmetic progressions (primes ending in 7, say). That is the Generalized Riemann Hypothesis for Dirichlet L-functions, for every modulus and every character.

The scope has an edge, and it is worth knowing where it is. "GRH" is used for several statements of increasing reach. What the checkers accepted concerns Dirichlet L-functions only. The versions for the zeta functions of number fields and for automorphic L-functions in general are not among the five theorems. Alpöge writes that he expects the method to reach further "with more time"; [Andrew Sutherland's verification page](https://math.mit.edu/~drew/grh/) at MIT says plainly that those were not checked, because they are not there.

## It has been "proved" many times before

**Announced proofs of the Riemann hypothesis are a genre, and almost none of them is taken seriously for more than a day.**

The oldest goes back to 1885, when Thomas Stieltjes published a note claiming a bound that would have implied the hypothesis. He never produced the proof, and the bound itself was shown to be false a century later. In 1945 Hans Rademacher, a respected number theorist, announced a *disproof*; Time magazine reported it, and then an error was found and it was withdrawn. Louis de Branges, who really did prove a famous conjecture in 1984 after years of not being believed, has announced proofs of this one several times since, and none has been accepted. And the preprint servers receive a steady supply of short papers titled some variant of "A proof of the Riemann hypothesis".

The one I remember personally is Michael Atiyah's. In September 2018 one of the most decorated mathematicians alive, a Fields medallist and Abel laureate, then 89, announced at a public lecture in Heidelberg that he had a simple proof, and posted five pages. I was studying mathematics at university at the time, and what I remember is that nobody around me took it seriously, not even for an afternoon. Nobody was unkind about it. Everyone simply knew that a claim of this size, resting on a few pages and a great name, was not something you had to stop and check.

That is the background against which to read last Friday. Every earlier claim asked the community to spend scarce expert time on the author's word, and the community had learned to say no. This one did not ask anyone to believe anything. It came with an object that anyone with a large enough computer could test, against a statement the author had not written. That changed the default response from "probably wrong, who has the time" to "run it", and the answer came back within hours. The reputation of the author mattered for how quickly people started, and not at all for what they found.

## A proof nobody has read

**The proof exists only as code, and that was a decision.** The numbers, from the notes of the people who checked it:

| | |
|---|---|
| Lean files | 175,187 |
| Lines | 17.4 million, with no comments |
| Theorems and lemmas | 818,755 |
| Source size | about 1 GB |
| The same argument written out for people | over 250,000 pages, by the author's count |
| Human-readable paper | none yet |

For scale, OpenAI's Navier–Stokes proof in September was 166 pages. Alpöge did generate the long document, and decided against posting it: in his words it would have been "some massive unreadable travesty of slop", so he chose "to only present Lean". He adds a detail that tells you what kind of text it is. Its Theorem 1 begins by noting that, because the real numbers are ordered, a number different from 1/2 is either larger or smaller than 1/2.

So the claim rests on the checker, and the first thing the community did was attack the checking from every side it could think of. Sutherland had the whole archive compiled by 16:43 UTC on the day of the announcement. Within a day and a half, his page and the [Lean community's own repository](https://github.com/leanprover-community/riemann-hypothesis) recorded the following.

<figure class="rh-fig">
<svg viewBox="0 0 600 372" role="img" aria-label="What has been checked about the Lean proof of the Riemann hypothesis and what has not. Checked: all 175,187 modules compile; the statement is Mathlib's own definition and matches a challenge file written independently; only Lean's three standard axioms are used; a second kernel written independently in Rust accepts the full proof; independent rebuilds by other people reproduce it. Not yet: a proof written for humans, and refereeing and understanding by mathematicians">
  <g>
    <rect x="20" y="14" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="62" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="110" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="158" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="206" width="560" height="42" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="20" y="268" width="560" height="42" rx="7" fill="rgba(245,158,11,0.07)" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="5 4"/>
    <rect x="20" y="316" width="560" height="42" rx="7" fill="rgba(245,158,11,0.07)" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="5 4"/>
  </g>
  <g font-size="12" font-weight="700" fill="#5eead4">
    <text x="36" y="32">Does it compile?</text>
    <text x="36" y="80">Does the statement say what we mean?</text>
    <text x="36" y="128">Is anything assumed?</text>
    <text x="36" y="176">Could the checker itself be wrong?</text>
    <text x="36" y="224">Does it depend on who ran it?</text>
  </g>
  <g font-size="12" font-weight="700" fill="#fbbf24">
    <text x="36" y="286">Is there a proof a person can read?</text>
    <text x="36" y="334">Do mathematicians understand why it is true?</text>
  </g>
  <g font-size="10.5" fill="#94a3b8">
    <text x="36" y="48">All 175,187 modules, zero errors, and every one replayed through Lean's kernel.</text>
    <text x="36" y="96">It is Mathlib's own definition, and all five match a challenge file written independently.</text>
    <text x="36" y="144">Only Lean's three standard axioms. No hidden hypothesis about primes or zeros.</text>
    <text x="36" y="192">A second kernel, written independently in Rust, accepts the full proof. So do two more.</text>
    <text x="36" y="240">Independent rebuilds by other people; a sandboxed one reproduces the export byte for byte.</text>
    <text x="36" y="302">Not yet. The author says he intends "to write it properly".</text>
    <text x="36" y="350">Not yet. No referee has read it, and the checkers do not explain anything.</text>
  </g>
  <g font-size="11" font-weight="700" text-anchor="end">
    <text x="566" y="32" fill="#5eead4">yes</text><text x="566" y="80" fill="#5eead4">yes</text><text x="566" y="128" fill="#5eead4">no</text>
    <text x="566" y="176" fill="#5eead4">covered</text><text x="566" y="224" fill="#5eead4">no</text>
    <text x="566" y="286" fill="#fbbf24">no</text><text x="566" y="334" fill="#fbbf24">no</text>
  </g>
</svg>
<figcaption>Everything a machine can settle was settled in about a day. The two rows at the bottom are the ones that take people, and time.</figcaption>
</figure>

Each row closes one way the result could be wrong. A proof can compile and prove the wrong statement, so the statements were compared with ones written by someone else. A checker can have a bug, so the proof was exported and run through kernels written independently, in a different language, by different people. An archive can smuggle in an assumption, so the axioms were listed: the same three every Lean proof uses. One of Sutherland's checks I find especially convincing because it leaves the zeta function out altogether. Combined with an independent formalization of a classical equivalence, the archive yields a statement about ordinary whole numbers: for every n above 5040, the sum of the divisors of n is less than e^γ · n · log log n. That is Robin's inequality, known since 1984 to be equivalent to the Riemann hypothesis. It can be tested on a pocket calculator, and it is now a theorem with no hypotheses.

There is a detail in those pages that says something about the moment. Sutherland notes that his checks were "run with Claude Code". The most detailed public [map of the proof's architecture](https://github.com/nasqret/riemann-rev) states that it was produced with an AI assistant. The proof was written with a model, and so were the tools used to audit it. What nobody delegated is the kernel: a small program, reviewed by people over years, that does nothing but check that each step follows from the previous ones.

What all of this leaves open is the bottom of the figure. A kernel certifies that the theorem follows from the axioms. It does not say why. I made the same distinction about Navier–Stokes, where the model's drafts had to be [turned into something a person can read](/en/blog/writing-a-research-paper-with-ai), but there a paper existed. Here the gap is total: the result is, as far as machines can tell, correct, and the understanding has not started. Terence Tao, in a [short note](https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/) the same day, ranked the day's announcements by how "digested" they were and put this one last: "I imagine the digestion process will take some time, though in this case at least we have a human author to communicate with to assist with this task."

## The idea, in one sentence

**A whole number that is divisible by many primes cannot be small.** That is the core of the argument, and the rest is the work of making it precise enough.

Start with why an *upper bound* is what you need. Riemann's formula says that each zero of ζ contributes a wave to the count of primes, and the real part of the zero sets how loud the wave is. If every zero has real part 1/2, every wave has an amplitude proportional to √y, where y is how far along the number line you are counting. A zero off the line, at real part 0.8 say, would be a wave growing like y to the power 0.8, and sooner or later it would drown the others.

You can watch this with nothing but a list of primes. Take a weighted count of the primes up to y, subtract the amount you expect, and divide by √y:

<figure class="rh-fig">
<img src="https://www.javieraguilar.ai/blog/riemann-hypothesis-proof-prime-sum.png" alt="The weighted prime count G(y), with its expected value subtracted and divided by the square root of y, computed for y from ten to ten million. The curve oscillates irregularly but never exceeds 0.023 in absolute value, well inside the band of plus or minus 0.0462 that the Riemann hypothesis predicts" aria-label="The weighted prime count G(y), with its expected value subtracted and divided by the square root of y, computed for y from ten to ten million. The curve oscillates irregularly but never exceeds 0.023 in absolute value, well inside the band of plus or minus 0.0462 that the Riemann hypothesis predicts" />
<figcaption>Computed from the primes up to ten million: the curve never exceeds 0.023, half the width of the band the hypothesis allows. A picture like this is evidence, not proof; the proof has to hold for every y. <a href="https://github.com/JaviMaligno/personal-website/blob/main/scripts/figures/riemann-centred-prime-sum.py">Script</a>.</figcaption>
</figure>

The hypothesis is the statement that this curve stays inside a band forever. And here is the first idea of the proof, a classical one sharpened: you do not need both sides of the band. A wave goes up as well as down. If you can show the count stays *below* the ceiling across long stretches, there is no room for a louder wave, because a louder wave would have poked through. The proof needs only this one-sided bound, and only on some long intervals, as long as the combinations involved have positive weights, so that waves from different functions cannot cancel each other out. That piece is a refinement of a theorem of Landau from 1905, and it has been machine-checked on its own, in isolation from the rest.

So the whole problem becomes: where can an upper bound on a count of primes come from?

From divisibility. Take a positive whole number N. Every prime power dividing N contributes to its size, so if you add up log p over all the prime powers that divide N, you cannot exceed log N. If you know N is divisible by a great many primes, and you can measure N's size some other way, you have an inequality with a sum over primes on one side and a known quantity on the other. That is an upper bound on a count of primes.

This is not a new trick. It is the oldest one. In 1850 Chebyshev applied it to the factorial: a! is divisible by each prime p about a/p + a/p² + … times, and its size is given by Stirling's formula. Out came the first proof that the number of primes up to x has the order of magnitude x/log x. The factorial is not divisible enough to give more than that. The announced proof runs the same principle with a much more divisible number. Alpöge's timeline records the starting point, dated 9 October: a quantity built from the derivatives of a theta function on an elliptic curve with extra symmetry, which is divisible by each suitable prime p about a/p + a/p³ + … times. It behaves like a factorial that only certain primes divide, and its size can be computed exactly.

That, alone, does not give the square root. The second idea does, and it is the one Alpöge chose as the single line that would make "fellow mathematicians fall out of their chairs".

## Where the square root comes from

**The proof is a descendant of a 1969 argument for a different world, and the square root appears when you balance two costs.**

The Riemann hypothesis has a twin for curves over finite fields, where the analogue of counting primes is counting the points of a curve. That twin was proved by André Weil in the 1940s with heavy machinery, and then again, starting in 1969, by Sergei Stepanov with almost none. Stepanov's idea: build an auxiliary polynomial that vanishes at every point of the curve, and not just vanishes but vanishes *to high order*, a zero of multiplicity m at each point. A polynomial cannot have more zeros, counted with multiplicity, than its degree. So the number of points times m is at most the degree, and that is an upper bound on the number of points. As in the previous section, upper bounds turn out to be enough.

The obstacle to copying this for the ordinary primes is the word "multiplicity". To make a polynomial vanish to order m you differentiate it. There is nothing to differentiate in the whole numbers. Alpöge puts it this way: multiplicity "is hard to find over the integers, corresponding to something like differentiating whole numbers".

The substitute is divisibility, obtained by iteration. The construction that produces the highly divisible number can be chained: apply it once and you gain a certain amount of divisibility, apply it m times in a row and you gain it m times over. The technical name of each link is a theta lift, a classical way of moving a symmetric function from one group to a larger one; I will not pretend the details are intuitive. The accounting is.

<figure class="rh-fig">
<svg viewBox="0 0 600 262" role="img" aria-label="A dictionary between Stepanov's 1969 proof of the Riemann hypothesis for curves over finite fields and the announced proof over the integers. Vanishing to order m becomes divisibility of an m-fold chain of theta lifts. Counting zeros against the degree becomes weighing divisibility against size. The finite extensions of the field become the layers of a tower of number fields. In both, an upper bound is enough">
  <g font-size="11.5" font-weight="700" text-anchor="middle">
    <text x="150" y="24" fill="#94a3b8">Stepanov, 1969</text>
    <text x="150" y="40" font-size="10" font-weight="400" fill="#64748b">points of a curve over a finite field</text>
    <text x="450" y="24" fill="#5eead4">The announced proof, 2026</text>
    <text x="450" y="40" font-size="10" font-weight="400" fill="#64748b">prime numbers</text>
  </g>
  <defs>
    <marker id="rh-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <g>
    <rect x="20" y="54" width="260" height="40" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)"/>
    <rect x="20" y="104" width="260" height="40" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)"/>
    <rect x="20" y="154" width="260" height="40" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)"/>
    <rect x="20" y="204" width="260" height="40" rx="7" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.16)"/>
    <rect x="320" y="54" width="260" height="40" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="320" y="104" width="260" height="40" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="320" y="154" width="260" height="40" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="320" y="204" width="260" height="40" rx="7" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
  </g>
  <g stroke="#64748b" stroke-width="1.5" marker-end="url(#rh-ar)">
    <line x1="284" y1="74" x2="316" y2="74"/><line x1="284" y1="124" x2="316" y2="124"/>
    <line x1="284" y1="174" x2="316" y2="174"/><line x1="284" y1="224" x2="316" y2="224"/>
  </g>
  <g font-size="11" fill="#e2e8f0" text-anchor="middle">
    <text x="150" y="78">a polynomial vanishing to order m</text>
    <text x="150" y="128">zeros counted against the degree</text>
    <text x="150" y="178">the finite extensions of the field</text>
    <text x="150" y="228">an upper bound is enough</text>
    <text x="450" y="78">a number made divisible by m chained lifts</text>
    <text x="450" y="128">divisibility weighed against size</text>
    <text x="450" y="178">the layers of a tower of number fields</text>
    <text x="450" y="228">an upper bound, on long windows, is enough</text>
  </g>
</svg>
<figcaption>The note calls the argument "a descendant of Stepanov's". Each row replaces something that needs derivatives with something the whole numbers do have.</figcaption>
</figure>

Each link in the chain costs something. To bound a prime count of length x with a chain of m links, the error has two parts. One shrinks as the chain gets longer, like x/m: more multiplicity, sharper bound. The other grows with the chain, like m: every link adds its own loss. The best you can do is make them equal.

<figure class="rh-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="The error of the bound as a function of the number m of chained lifts, for a prime count of length x equal to ten thousand. One cost, x over m, falls as the chain gets longer; the other, m, rises. Their sum is smallest when m equals the square root of x, here one hundred, and the minimum is of the order of the square root of x">
  <line x1="70" y1="200" x2="566" y2="200" stroke="#64748b" stroke-width="1.5"/>
  <line x1="70" y1="200" x2="70" y2="24" stroke="#64748b" stroke-width="1.5"/>
  <path d="M90.8,33.3 L92.0,42.6 L93.3,50.9 L94.5,58.3 L97.0,71.2 L99.4,81.9 L101.8,91.0 L104.3,98.8 L108.0,108.6 L111.7,116.7 L116.5,125.4 L121.4,132.5 L127.6,139.7 L134.9,146.5 L143.5,152.8 L155.8,159.5 L168.0,164.6 L180.2,168.5 L192.5,171.7 L210.9,175.4 L229.2,178.2 L253.8,181.1 L284.4,183.8 L315.0,185.8 L351.8,187.7 L388.5,189.1 L437.5,190.6 L486.5,191.7 L523.2,192.3 L560.0,192.9" fill="none" stroke="#2dd4bf" stroke-width="1.6" stroke-dasharray="5 4"/>
  <path d="M82.3,197.2 L560,86.7" fill="none" stroke="#f59e0b" stroke-width="1.6" stroke-dasharray="5 4"/>
  <path d="M92.0,37.5 L93.3,45.5 L94.5,52.7 L97.0,65.0 L99.4,75.1 L101.8,83.7 L104.3,90.9 L108.0,99.8 L111.7,107.0 L116.5,114.7 L121.4,120.6 L127.6,126.4 L134.9,131.5 L143.5,135.8 L155.8,139.7 L168.0,141.9 L180.2,143.0 L192.5,143.3 L210.9,142.8 L229.2,141.4 L253.8,138.6 L284.4,134.2 L315.0,129.2 L351.8,122.5 L388.5,115.4 L437.5,105.6 L486.5,95.3 L523.2,87.5 L560.0,79.6" fill="none" stroke="#f8fafc" stroke-width="2.4"/>
  <line x1="192.5" y1="143.3" x2="192.5" y2="200" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3 3"/>
  <circle cx="192.5" cy="143.3" r="4.5" fill="#f8fafc"/>
  <g font-size="10.5" fill="#94a3b8">
    <text x="192.5" y="216" text-anchor="middle" fill="#e2e8f0" font-weight="700">m = √x</text>
    <text x="560" y="216" text-anchor="end">number of chained lifts, m</text>
    <text x="64" y="30" text-anchor="end">error</text>
    <text x="112" y="50" fill="#5eead4">x/m: what a short chain loses</text>
    <text x="556" y="132" text-anchor="end" fill="#fbbf24">m: what every link costs</text>
    <text x="204" y="98" fill="#f8fafc" font-weight="700">total error ≈ 2√x at the minimum</text>
    <text x="300" y="240" text-anchor="middle">drawn for x = 10,000: the two costs meet at m = 100</text>
  </g>
</svg>
<figcaption>The exponent 1/2 of the Riemann hypothesis, as the bottom of a trade-off. In the note, the suggestion to take a chain of length √X is credited to Claude.</figcaption>
</figure>

x/m equals m when m is √x, and the error is then of size √x. That is the square root of the Riemann hypothesis: the amplitude every wave is allowed to have. Alpöge's line, in full: "for the von Mangoldt sum of length X, Claude's suggested length of chain of theta lifts, in view of each mimicking multiplicity, was √X. (And yet, what else could it be?)"

I should be clear about what I am doing here. This is the architecture as the note and the public reading guides describe it, and I have read those; I have not verified seventeen million lines, and neither has anyone else by eye. The picture can be right and the understanding of it still be shallow. That is the state of everyone this week, the author included.

## What it took underneath

**The simple idea sits on top of most of modern number theory, and the archive rebuilds that too.**

The route from the idea to the theorem, as the reading guides lay it out:

<figure class="rh-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="The route of the proof in seven steps. Arithmetic supply: Galois representations attached to automorphic forms, from the Langlands programme, and Iwasawa theory bounding the loss of divisibility. The estimate: a chain of about square root of x theta lifts, where divisibility is weighed against size, and an averaging over characters with positive weights. The analytic engine: an upper bound on long windows excludes zeros to the right of the critical line. The destination: reflection by the functional equation gives the Riemann hypothesis and its generalization for Dirichlet L-functions">
  <defs>
    <marker id="rh-a2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <g font-size="9.5" fill="#64748b" font-weight="700">
    <text x="20" y="20">ARITHMETIC SUPPLY</text>
    <text x="216" y="20">THE ESTIMATE</text>
    <text x="412" y="20">ANALYSIS AND DESTINATION</text>
  </g>
  <g>
    <rect x="20" y="32" width="170" height="74" rx="8" fill="rgba(245,158,11,0.07)" stroke="#f59e0b" stroke-width="1.5"/>
    <rect x="20" y="166" width="170" height="74" rx="8" fill="rgba(245,158,11,0.07)" stroke="#f59e0b" stroke-width="1.5"/>
    <rect x="216" y="32" width="170" height="74" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.25)" stroke-width="1.5"/>
    <rect x="216" y="166" width="170" height="74" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.25)" stroke-width="1.5"/>
    <rect x="412" y="32" width="168" height="74" rx="8" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.5"/>
    <rect x="412" y="166" width="168" height="74" rx="8" fill="rgba(45,212,191,0.16)" stroke="#2dd4bf" stroke-width="2.2"/>
  </g>
  <g font-size="11" font-weight="700" fill="#e2e8f0" text-anchor="middle">
    <text x="105" y="54" fill="#fbbf24">Galois representations</text>
    <text x="105" y="188" fill="#fbbf24">Iwasawa theory</text>
    <text x="301" y="54">Chain of ~√x theta lifts</text>
    <text x="301" y="188">Averaging over characters</text>
    <text x="496" y="54" fill="#5eead4">Localized Landau theorem</text>
    <text x="496" y="188" fill="#5eead4">RH and Dirichlet GRH</text>
  </g>
  <g font-size="9.5" fill="#94a3b8" text-anchor="middle">
    <text x="105" y="72">attached to automorphic</text>
    <text x="105" y="85">forms: the Langlands</text>
    <text x="105" y="98">programme</text>
    <text x="105" y="206">the divisibility fails a little;</text>
    <text x="105" y="219">this bounds by how much,</text>
    <text x="105" y="232">on a whole window</text>
    <text x="301" y="72">divisible numbers cannot</text>
    <text x="301" y="85">be small: divisibility</text>
    <text x="301" y="98">weighed against size</text>
    <text x="301" y="206">positive weights isolate</text>
    <text x="301" y="219">the wanted function; the</text>
    <text x="301" y="232">others are discarded</text>
    <text x="496" y="72">an upper bound on long</text>
    <text x="496" y="85">windows leaves no room</text>
    <text x="496" y="98">for a zero right of the line</text>
    <text x="496" y="206">the functional equation</text>
    <text x="496" y="219">mirrors left onto right:</text>
    <text x="496" y="232">all zeros on the line</text>
  </g>
  <g stroke="#64748b" stroke-width="1.5" fill="none" marker-end="url(#rh-a2)">
    <line x1="192" y1="69" x2="213" y2="69"/>
    <line x1="105" y1="108" x2="105" y2="163"/>
    <path d="M192,190 L203,190 L203,90 L213,90"/>
    <line x1="301" y1="108" x2="301" y2="163"/>
    <path d="M388,203 L399,203 L399,69 L409,69"/>
    <line x1="496" y1="108" x2="496" y2="163"/>
  </g>
  <text x="300" y="272" text-anchor="middle" font-size="10" fill="#94a3b8">Everything from "averaging" onwards has also been machine-checked in isolation, as an implication from stated premises.</text>
  <text x="300" y="288" text-anchor="middle" font-size="10" fill="#64748b">Reconstructed from the public reading guide; the amber boxes are where the heavy machinery lives.</text>
</svg>
<figcaption>One hard estimate in the middle, classical analysis to its right, and to its left the part that makes the experts' eyes widen.</figcaption>
</figure>

Two pieces of that picture deserve a sentence each. First, the divisibility is not perfect: at each link it fails by a little, and the size of the failure is measured by objects from Galois cohomology of the kind that appear in a famous unproved conjecture of Vandiver. The proof does not need that conjecture. It needs a bound on the total failure across a whole window, which it gets from Iwasawa theory; Alpöge calls it "a significant weakening of Vandiver" and adds, in a footnote, "this is still pretty strong!!"

Second, both the sizes and that cohomology are controlled by Galois representations attached to automorphic forms, the central objects of the Langlands programme and the subject of some of the deepest papers of the last thirty years. A written proof would cite those papers. A Lean proof cannot cite anything Mathlib does not contain, so the archive carries its own formal construction of them. Chris Birkbeck, a number theorist at the University of East Anglia, described what he was seeing in the community's chat, quoted by [TechCrunch](https://techcrunch.com/2026/11/20/ai-claimed-a-solution-to-the-167-year-old-riemann-hypothesis-and-a-human-did-too/): the argument "genuinely uses the existence of Galois representations attached to regular algebraic, polarized cuspidal automorphic representations of GL_n over CM fields", along with a list of named theorems. Tao's first impression was that it "appears to use the full power of modern developments on the Langlands program and arithmetic geometry".

That is a large part of why the archive is the size it is. It is a proof of the Riemann hypothesis, and it is also a formalization of a good share of a research area that had never been formalized. Alpöge's own intuition "insists it will be massively simplified, likely immediately".

## Who did what

**A mathematician who had planned his whole career around this problem set the direction, and by his own account the model outran him at the end.**

The note is unusually candid about the division of labour. Alpöge writes that the problem was his secret plan since his student days, and that he spent years learning every tool he might one day recognise in it. In this attempt he "had us on the line of combining two quite different ideas present in a toy setting" and "guided us to the right situation analogous to that toy setting, and then Claude began to leave me in awe". The decisive stretch involves automorphic forms on large groups, where he says he is "out of my element". For those parts, he warns, his own summary paraphrases a machine summary that "might make zero sense", and "the Lean should suffice to clarify everything".

The timeline in the note, which he says Claude compiled, has twenty entries:

<figure class="rh-fig">
<svg viewBox="0 0 600 196" role="img" aria-label="Timeline of the proof according to the author's note and the verification records. 6 October 2026: first entry, a Stepanov-type determinant. 9 October: the highly divisible quantity on a curve with complex multiplication. 15 November: eight entries in one day, including the chain of theta lifts of length about square root of X. 16 November: the generalized Riemann hypothesis. 19 November: Anthropic's stock market debut. 20 November: the announcement, and the first independent build finishes at 16:43 UTC. 21 November: independent kernels and rebuilds accept the proof">
  <defs>
    <marker id="rh-a3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <line x1="24" y1="100" x2="578" y2="100" stroke="#64748b" stroke-width="2" marker-end="url(#rh-a3)"/>
  <g fill="#1a1a24" stroke="#94a3b8" stroke-width="2">
    <circle cx="56" cy="100" r="6"/><circle cx="140" cy="100" r="6"/>
    <circle cx="268" cy="100" r="6" stroke="#2dd4bf"/><circle cx="346" cy="100" r="6" stroke="#2dd4bf"/>
    <circle cx="420" cy="100" r="6"/><circle cx="486" cy="100" r="6" stroke="#f59e0b"/><circle cx="552" cy="100" r="6"/>
  </g>
  <circle cx="268" cy="100" r="3" fill="#2dd4bf"/><circle cx="346" cy="100" r="3" fill="#2dd4bf"/><circle cx="486" cy="100" r="3" fill="#f59e0b"/>
  <g text-anchor="middle" font-size="10.5" fill="#e2e8f0">
    <text x="56" y="62" font-weight="700">Oct 6</text>
    <text x="56" y="76" fill="#94a3b8">first entry:</text>
    <text x="56" y="88" fill="#94a3b8">a Stepanov idea</text>
    <text x="140" y="128" font-weight="700">Oct 9</text>
    <text x="140" y="142" fill="#94a3b8">the very divisible</text>
    <text x="140" y="154" fill="#94a3b8">number</text>
    <text x="268" y="62" font-weight="700" fill="#5eead4">Nov 15</text>
    <text x="268" y="76" fill="#94a3b8">eight entries in a day:</text>
    <text x="268" y="88" fill="#94a3b8">the chain, m ≈ √X</text>
    <text x="346" y="128" font-weight="700" fill="#5eead4">Nov 16</text>
    <text x="346" y="142" fill="#94a3b8">"GRH."</text>
    <text x="420" y="62" font-weight="700">Nov 19</text>
    <text x="420" y="76" fill="#94a3b8">Anthropic's</text>
    <text x="420" y="88" fill="#94a3b8">market debut</text>
    <text x="486" y="128" font-weight="700" fill="#fbbf24">Nov 20</text>
    <text x="486" y="142" fill="#94a3b8">announced; first</text>
    <text x="486" y="154" fill="#94a3b8">outside build 16:43 UTC</text>
    <text x="552" y="62" font-weight="700">Nov 21</text>
    <text x="552" y="76" fill="#94a3b8">other kernels,</text>
    <text x="552" y="88" fill="#94a3b8">other builders</text>
  </g>
  <text x="300" y="184" text-anchor="middle" font-size="10" fill="#64748b">Dates up to 16 November are from the note's own timeline; the rest from the verification records and press.</text>
</svg>
<figcaption>Six weeks from the first entry to the last, with eight of the twenty entries dated to a single Sunday.</figcaption>
</figure>

Three things the note does not say, and that I would want to know. It does not name the model; Tao describes it as "an internal AI model", so, as with OpenAI in September, this is not something you can run. It gives no figures for compute, tokens or agents, where OpenAI published all of them for Navier–Stokes. And it is not an Anthropic announcement: it is a note on a personal website, and I have not found a company statement.

It does address the timing. Anthropic went public on Thursday 19 November; the note appeared the next morning. Alpöge writes that "the precise timing is horrible", that the proof came together "late Sunday night", that he messaged Dario Amodei, Anthropic's chief executive, to ask about announcing, that "there was a constraint to respect", and that he is "clearly unilaterally responsible for feeling I just could not live if I waited even longer". Of the cynical reading he says only that it is false. I have no way to check any of that, and I report it as his account.

Two pieces of context make the speed easier to place. In August, Anthropic [reported](https://www.anthropic.com/research/riemann-zeta) that an unreleased version of Claude, asked by a non-mathematician on staff to "take a real stab" at the hypothesis, had raised the proven share of zeros on the critical line from 41.6% to 67.2%, and added: "We don't expect that the techniques Claude used will lead to proving the Riemann hypothesis." And in October, OpenAI's release of several hundred machine-written manuscripts included a proof of a [much weaker form of the hypothesis](/en/blog/when-ai-chooses-the-questions): no zeros with real part above 7/8. Alpöge's note thanks "the people at OpenAI involved with various mathematical results" for their taste in choosing problems, and says that one argument they published he "immediately recognized" as "Stepanov without multiplicity". A competing lab's publication was one of his clues.

## The other proof, the same afternoon

**Hours later, the president of the American Mathematical Society posted a human proof of the same theorem, and it is in a very different state.**

Ravi Vakil, of Stanford, published a draft by Alessandro Masullo claiming the Generalized Riemann Hypothesis. "It is all human, with no AI," he wrote; the hope had been to bring Masullo to Stanford for a year to polish the writing, and "now it seems best to put out the current draft". Brian Conrad, a Stanford number theorist, had been giving Masullo feedback for months. Masullo's own introduction, as [TechCrunch quotes it](https://techcrunch.com/2026/11/20/ai-claimed-a-solution-to-the-167-year-old-riemann-hypothesis-and-a-human-did-too/), says the work took twelve years and carries a message for mathematicians discouraged by the current climate: "we are still here. We are very much alive. We are not going anywhere."

The status is not comparable, and the people closest to it say so. Conrad told [Scientific American](https://www.scientificamerican.com/article/dueling-claims-of-riemann-hypothesis-proofs-emerge/) that the paper is "undergoing major revision" and that judging the method requires a more final version. Within about eight hours, [according to The Decoder](https://the-decoder.com/hours-after-anthropic-claims-a-claude-proof-of-the-riemann-hypothesis-stanford-releases-an-all-human-competing-draft/), Vakil updated his post: several people had reported problems in the draft, found with the help of AI models, and he made "no claim as to the correctness of the proof strategy".

Put the two side by side and you get the oddest fact of the week. One proof has been checked completely and understood by nobody. The other was written to be understood and has been checked by nobody. Until this year those two properties came together, because the only way to check a proof was to understand it.

## Theorems that changed status overnight

**A century of results begin with the words "assuming the Riemann hypothesis". For the ones that need only what was proved, that clause can now be deleted.**

As with [Navier–Stokes](/en/blog/navier-stokes-blows-up), a conditional theorem does not change when its hypothesis is settled, but its meaning does. Some examples, sorted by which side of the scope they fall on.

- **Now unconditional, if the proof stands.** The sharpest form of the prime number theorem: for x ≥ 2657, the count of primes up to x differs from Gauss's estimate li(x) by less than √x · log x / 8π (Schoenfeld, 1976). Robin's inequality about sums of divisors, mentioned above. The primes in each arithmetic progression are as evenly distributed as the primes overall. Miller's primality test from 1976, which is fast and deterministic *provided* GRH for Dirichlet L-functions holds, is now simply correct; in practice nothing changes, because an unconditional fast test has existed since 2002.
- **Theorems that had been proved twice.** Gauss conjectured that a certain count attached to quadratic number fields, the class number, grows without bound. Hecke proved it assuming GRH. In 1934 Heilbronn proved it assuming GRH is *false*. Between them the conjecture became a theorem with nobody knowing which proof was the valid one. We now know: Hecke's.
- **Not covered.** Anything that needs the hypothesis for the zeta functions of number fields beyond the simplest kind, or for L-functions of elliptic curves and automorphic forms. Artin's conjecture on primitive roots, which Hooley proved in 1967 under such a hypothesis, stays conditional. So do many effective results in algebraic number theory.
- **Not affected at all.** Cryptography. No deployed system rests on the Riemann hypothesis being false, and knowing it is true does not factor any number faster.

What mathematicians expect to matter is the method more than the list. Carlo Pagano, of Concordia University, told [Scientific American](https://www.scientificamerican.com/article/anthropic-mathematician-claims-to-prove-riemann-hypothesis-most-famous-problem-in-all-of-math/) it is "very plausible" that the new ideas "will open up brand new avenues of thinking in number theory". That depends on the ideas being extracted, which brings it back to the two amber rows.

On the million dollars, the same answer as in September. The Clay Mathematics Institute requires publication in a qualifying outlet, a wait of two years, and general acceptance by the mathematical community. An archive that no one has read is, for now, none of those.

## The same day, the other Millennium problem

In September I ended the Navier–Stokes article with a ladder whose top rung was empty: the unforced equations, the question most people actually mean. Tao's note of 20 November lists, above the Riemann item and as better digested, two more announcements involving Alpöge and Tristan Buckmaster of NYU: a human-readable proof, with Matei Coiculescu, of finite-time blow-up for the *unforced* three-dimensional Euler equations, and a proof of finite-time blow-up for the *unforced* three-dimensional Navier–Stokes equations, both with Lean formalizations. Of the second, Tao says the strategy is "broadly clear" and follows an expected path, but that "more work needs to be done to create a proper, professionally written proof". I have not read either, and they deserve their own piece. I note it here because that top rung now has a claimant, and it is the pair whose route OpenAI finished first in September.

## "Math is dead"

**I have read that sentence a lot this week, and I think it is the opposite of what happened. My view is that mathematics is more alive than it has ever been.** Three reasons, in increasing order of importance.

The first is simply how many people are looking. A problem about the zeros of a function was front-page news, and people who had not thought about prime numbers since school spent a weekend asking what a critical line is. Even if that were the only effect, a subject that the whole world stops to watch is not a dead one.

The second is that the capacity to solve problems went up, and so did the capacity to *understand* them. Much of this week's commentary takes for granted that we now have answers without understanding, and that the understanding is lost. Look at what actually happened. Within a day of the announcement there was a public map of the proof's architecture, a guide to its seven steps and a list of which parts had been checked in isolation, all produced with AI assistance. The problems in the human draft were found by people working with AI models. The author's plan for understanding his own proof is to work through it with the same tool that helped find it. Understanding is the part that is behind, and AI is the main reason it will not stay behind for long. I do not see how anyone digests seventeen million lines without it.

The third is what it opens. This proof connects a 1969 argument about curves over finite fields, a classical construction with theta functions, Iwasawa theory and the Langlands programme, in a combination nobody had tried, partly because trying it by hand would have cost a career. When exploring a route costs weeks, far more routes, tools and connections get explored. The questions do not run out: the wider forms of the hypothesis are still open, the proof is waiting to be simplified, and every theorem that used to say "assuming RH" is now a starting point. Alpöge, who by his own account has just lost the problem that guided his life, calls it a dawn. Sutherland calls it "a human triumph, and a day for celebration". Masullo, with twelve years of work overtaken in an afternoon, writes "we are still here".

What has ended is something narrower: the idea that being the first to find a proof is the main thing a mathematician is for. Choosing what is worth proving, recognising that a toy case hides the real one, and explaining why something is true were always most of the job. They are now the scarce part.

## What to take from it

- **What was proved is the Riemann hypothesis and its generalization to Dirichlet L-functions**, in Mathlib's own wording. The wider versions of GRH are not in the archive.
- **Correct and understood have come apart.** Everything a machine can check was checked within about a day, by independent people with independent tools. Nothing a referee does has been done, and no human-readable proof exists. Neither fact cancels the other.
- **The central idea is old and simple.** A number divisible by many primes cannot be small; Chebyshev used it in 1850. The square root comes from balancing the length of a chain against the cost of each link.
- **The idea is simple; what holds it up is not.** It rests on a formal reconstruction of a large part of the Langlands programme, which is where most of the seventeen million lines go.
- **A human chose the route and the model finished it.** That is the author's own description. He also says he cannot yet explain the last stretch, and that understanding it is the work that starts now.
- **The model is not one you can use, and the numbers behind the run are not public.**
- **Mathematics is not dead.** More people are watching it than ever, the tools that found the proof are the ones that will explain it, and far more routes can now be explored.

For anyone building with agents, the part of this that transfers is not the mathematics. It is that the result was accepted in a day because a small, independent, well-understood checker existed, and because the statement to be checked had been written down by someone else beforehand. Where your work has both of those, you can let a model run a long way ahead of you. Where it has neither, the 250,000 pages are all you get.

---

*Sources: [Alpöge's announcement](https://alpo.ge/remark.pdf); [Andrew Sutherland's verification files](https://math.mit.edu/~drew/grh/) at MIT; the Lean community's [verification repository](https://github.com/leanprover-community/riemann-hypothesis); the independent [map and guide to the proof](https://github.com/nasqret/riemann-rev); [Terence Tao's note](https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/); Scientific American on [the announcement](https://www.scientificamerican.com/article/anthropic-mathematician-claims-to-prove-riemann-hypothesis-most-famous-problem-in-all-of-math/) and on [the two claims](https://www.scientificamerican.com/article/dueling-claims-of-riemann-hypothesis-proofs-emerge/); [TechCrunch's report](https://techcrunch.com/2026/11/20/ai-claimed-a-solution-to-the-167-year-old-riemann-hypothesis-and-a-human-did-too/); and Anthropic's August post on [Claude and the zeros of the zeta function](https://www.anthropic.com/research/riemann-zeta).*
