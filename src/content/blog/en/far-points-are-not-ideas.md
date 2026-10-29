---
title: "The Gaps in the Map Are Not Ideas"
description: "A tweet proposed getting brand-new ideas from the empty points of an embedding space. I tested it on Steam, arXiv and patents: no coherent text reaches the far points, and what comes out of them is an ordinary game."
pubDate: 2026-11-26
tags: ["AI", "Embeddings", "LLMs", "Research", "Creativity"]
lang: en
translationKey: far-points-are-not-ideas
heroImage: "/blog/far-points-are-not-ideas.png"
---
A few weeks ago I read a tweet by @syntheticbeef with a recipe for getting AI to invent genuinely new ideas: embed every game on Steam, pick a point in the space that is far from all of them, turn it back into a description, and rank the results by how unlike existing games they are. If the point is far from everything, the idea that comes out of it must be new.

My objection was immediate: in a space with a thousand dimensions almost everything is far from everything, and almost all of that space is noise. An empty point does not mean there is an idea there; there may be no meaningful text there at all. A friend replied that coherence is just another dimension, with its own local optima, and that image diffusion shows strange, meaningful corners exist: an astronaut riding a horse. I agreed that they exist, but diffusion reaches them by starting from a concept and moving by similarity; the tweet looks for dissimilarity with no starting point.

It was an argument that could be measured, so I measured it.

<style>
.lg-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.lg-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.lg-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## How I measured it

I took the Steam games released before 2024 (about 68,000 after removing adult content) as the map, and kept the 41,000 released later to check afterwards whether the world had filled any gap. Each listing becomes a vector with Qwen3-Embedding-0.6B, an open model. Then I repeated everything with arXiv abstracts and with patent applications, so as not to draw conclusions from a single domain.

To "decode" a point, an LLM writes a game listing in a loop. In each round it sees the 8 real games nearest to the point and, after writing, gets back only a score: how similar its listing is to the point (the cosine). Four rounds, three candidates per round, keep the best.

<figure class="lg-fig">
<svg viewBox="0 0 600 190" role="img" aria-label="The decoding loop: the target point gives its 8 nearest neighbours, the LLM writes a listing, it is embedded, its cosine with the point is measured and only that score goes back to the LLM, for 4 rounds of 3 candidates.">
<defs><marker id="lga1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
<g font-size="12" text-anchor="middle">
<rect x="15" y="40" width="100" height="56" rx="8" fill="#0f172a" stroke="#f59e0b"/><text x="65" y="64" fill="#fbbf24" font-weight="600">Point t</text><text x="65" y="81" fill="#94a3b8" font-size="10.5">in the space</text>
<rect x="135" y="40" width="100" height="56" rx="8" fill="#0f172a" stroke="rgba(255,255,255,0.18)"/><text x="185" y="64" fill="#e2e8f0">8 neighbours</text><text x="185" y="81" fill="#94a3b8" font-size="10.5">real + their cosine</text>
<rect x="255" y="40" width="100" height="56" rx="8" fill="#0f172a" stroke="#2dd4bf"/><text x="305" y="64" fill="#5eead4" font-weight="600">LLM</text><text x="305" y="81" fill="#94a3b8" font-size="10.5">writes a listing</text>
<rect x="375" y="40" width="100" height="56" rx="8" fill="#0f172a" stroke="rgba(255,255,255,0.18)"/><text x="425" y="64" fill="#e2e8f0">Embedding</text><text x="425" y="81" fill="#94a3b8" font-size="10.5">Qwen3-0.6B</text>
<rect x="495" y="40" width="90" height="56" rx="8" fill="#0f172a" stroke="rgba(255,255,255,0.18)"/><text x="540" y="64" fill="#e2e8f0">cos(listing, t)</text><text x="540" y="81" fill="#94a3b8" font-size="10.5">the score</text>
</g>
<g stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#lga1)">
<path d="M115,68 L133,68"/><path d="M235,68 L253,68"/><path d="M355,68 L373,68"/><path d="M475,68 L493,68"/>
<path d="M540,96 L540,135 L305,135 L305,99"/>
</g>
<text x="422" y="153" fill="#94a3b8" font-size="11" text-anchor="middle">only the score goes back · 4 rounds × 3 candidates · keep the best</text>
</svg>
<figcaption>The decoder. The LLM never sees the point, only the games around it and a score of how close it got.</figcaption>
</figure>

The points were not all of the same kind, and that is the key to the experiment:

- **REAL**: the point of a real game that I hide. It is the control: if the method cannot recover a game that exists, nothing else means anything.
- **INTERP**: the midpoint between two very different games, the geometric version of "combine two distant ideas".
- **GAP**: inner gaps, points that fall inside the region where games are but where there is none.
- **FAR**: the tweet's literal recipe. Out of 20,000 random directions, the 50 furthest from any game.
- **PLAIN**: no map. I just ask the model to "invent a new game, unlike any that exists".

Five models scored the listings blind as judges (coherence, feasibility, appeal, and novelty against the 5 most similar games), and I scored a sample myself.

## Far points cannot be written

The control works: in REAL the decoder lands, at a cosine of around 0.7–0.75, in the hidden game's area, as close as the most similar existing game. The method can reach a place when there is text there.

In FAR, by contrast, the listing lands at a cosine of 0.03 from the point. Practically zero. And it is not that the LLM does badly: the existing game nearest to those points is at 0.046. What comes out is an ordinary game. For example, *Pounce & Pop: Kitten's Block Quest*, a block-pushing puzzle with a kitten finding her way home (cosine 0.069 with its point), or *The Museum of Unfinished Things*, a museum that rearranges itself at night (0.028). Reasonable games, even pleasant ones, that could already be on Steam.

The geometry explains why. Texts do not fill the whole space: they live in a narrow cap. Two random directions in 1,024 dimensions have a cosine of 0 ± 0.03; two Steam games, 0.41. A FAR point is outside that cap, and any listing the LLM writes, however odd, falls back inside it, at the same "latitude" as an ordinary game.

<figure class="lg-fig">
<svg viewBox="0 0 600 320" role="img" aria-label="Texts occupy a narrow cap of the sphere. A far point lies outside the cap and the decoded listing falls back inside, next to the neighbours it was shown; an inner gap does lie inside.">
<circle cx="250" cy="170" r="130" fill="none" stroke="rgba(255,255,255,0.18)" stroke-width="1.4"/>
<path d="M140.5,100 A130,130 0 0,1 359.5,100 Z" fill="rgba(45,212,191,0.12)" stroke="#2dd4bf" stroke-width="1.2"/>
<g fill="#94a3b8">
<circle cx="190" cy="88" r="3"/><circle cx="210" cy="72" r="3"/><circle cx="232" cy="90" r="3"/><circle cx="250" cy="60" r="3"/><circle cx="268" cy="84" r="3"/><circle cx="292" cy="68" r="3"/><circle cx="215" cy="95" r="3"/><circle cx="245" cy="78" r="3"/><circle cx="175" cy="96" r="3"/><circle cx="305" cy="92" r="3"/><circle cx="278" cy="56" r="3"/><circle cx="228" cy="62" r="3"/>
</g>
<g fill="#e2e8f0"><circle cx="330" cy="88" r="3.6"/><circle cx="342" cy="96" r="3.6"/><circle cx="322" cy="96" r="3.6"/></g>
<circle cx="262" cy="96" r="5" fill="none" stroke="#fbbf24" stroke-width="1.6"/>
<path d="M342,255 l4,9 10,1 -7.5,6.5 2.5,10 -9,-5.5 -9,5.5 2.5,-10 -7.5,-6.5 10,-1z" fill="#f59e0b"/>
<circle cx="334" cy="84" r="5" fill="#2dd4bf"/>
<path d="M340,252 C380,190 372,130 338,92" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5 4"/>
<g font-size="12">
<text x="250" y="30" fill="#5eead4" text-anchor="middle">the cap where texts live</text>
<text x="250" y="46" fill="#94a3b8" text-anchor="middle" font-size="10.5">two games: cos 0.41 · two random directions: 0 ± 0.03</text>
<text x="398" y="270" fill="#fbbf24">FAR point</text>
<text x="398" y="286" fill="#94a3b8" font-size="10.5">far from everything (max cos 0.046)</text>
<text x="398" y="160" fill="#5eead4">the decoded listing</text>
<text x="398" y="176" fill="#94a3b8" font-size="10.5">falls back into the cap, next to</text>
<text x="398" y="190" fill="#94a3b8" font-size="10.5">the neighbours it saw (white)</text>
<text x="160" y="140" fill="#fbbf24" font-size="11">GAP hole</text>
<path d="M210,135 L257,101" stroke="#fbbf24" stroke-width="1" fill="none"/>
</g>
</svg>
<figcaption>Schematic, not to scale. FAR points fall outside the region where text exists; GAP points fall inside it, in a hole between games.</figcaption>
</figure>

## The text lands where the neighbours are, not where the point is

Looking at where the FAR listings landed, I saw something else: they were much closer to the 8 neighbours shown to the LLM (cosine 0.63–0.72 with their centroid) than to the point itself. In patents it happened in 100% of cases. But that was a correlation, and it could have another explanation: maybe the neighbours are simply the closest thing to the point there is.

So I ran the causal test. Same point, same cosine score, and I change only one thing: the neighbours the LLM sees. They can be the true ones, those of a different point, or none. I repeated it on Steam and arXiv, with two generators (gpt-6-luna and Claude Sonnet) and on REAL, GAP and FAR, 20 points per condition, with the decision rules written down before launching anything.

<figure class="lg-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Mean cosine between listing and point depending on the neighbours shown. With the true neighbours, REAL reaches 0.73 on Steam and 0.78 on arXiv; with another point's neighbours or none it drops to 0.3-0.4. In FAR, with the true neighbours it only reaches 0.03-0.05, and without them it stays below zero.">
<g font-size="11" fill="#94a3b8">
<rect x="150" y="8" width="11" height="11" fill="#2dd4bf"/><text x="166" y="18">true neighbours</text>
<rect x="292" y="8" width="11" height="11" fill="#f59e0b"/><text x="308" y="18">another point's</text>
<rect x="406" y="8" width="11" height="11" fill="#64748b"/><text x="422" y="18">no neighbours</text>
</g>
<line x1="45" y1="230" x2="300" y2="230" stroke="rgba(255,255,255,0.25)"/><line x1="325" y1="230" x2="580" y2="230" stroke="rgba(255,255,255,0.25)"/>
<g stroke="rgba(255,255,255,0.07)"><line x1="45" y1="105" x2="300" y2="105"/><line x1="325" y1="105" x2="580" y2="105"/><line x1="45" y1="55" x2="300" y2="55"/><line x1="325" y1="55" x2="580" y2="55"/></g>
<g font-size="10" fill="#94a3b8" text-anchor="end"><text x="40" y="233">0</text><text x="40" y="108">0.5</text><text x="40" y="58">0.7</text></g>
<g fill="#2dd4bf"><rect x="60" y="48" width="18" height="182"/><rect x="145" y="105.5" width="18" height="124.5"/><rect x="230" y="223.25" width="18" height="6.75"/>
<rect x="340" y="34" width="18" height="196"/><rect x="425" y="114" width="18" height="116"/><rect x="510" y="217" width="18" height="13"/></g>
<g fill="#f59e0b"><rect x="82" y="120" width="18" height="110"/><rect x="167" y="139.75" width="18" height="90.25"/><rect x="252" y="230" width="18" height="5.25"/>
<rect x="362" y="143.75" width="18" height="86.25"/><rect x="447" y="153" width="18" height="77"/><rect x="532" y="230" width="18" height="4.25"/></g>
<g fill="#64748b"><rect x="104" y="124" width="18" height="106"/><rect x="189" y="142.25" width="18" height="87.75"/><rect x="274" y="230" width="18" height="3.25"/>
<rect x="384" y="137.5" width="18" height="92.5"/><rect x="469" y="156.25" width="18" height="73.75"/><rect x="554" y="230" width="18" height="3.5"/></g>
<g font-size="11.5" fill="#e2e8f0" text-anchor="middle"><text x="91" y="266">REAL</text><text x="176" y="266">GAP</text><text x="261" y="266">FAR</text><text x="371" y="266">REAL</text><text x="456" y="266">GAP</text><text x="541" y="266">FAR</text></g>
<g font-size="10" fill="#5eead4" text-anchor="middle"><text x="239" y="216">0.03</text><text x="519" y="210">0.05</text></g>
<g font-size="9.5" fill="#fbbf24" text-anchor="middle"><text x="268" y="247">−0.02</text><text x="548" y="247">−0.02</text></g>
<g font-size="12.5" fill="#f8fafc" text-anchor="middle" font-weight="600"><text x="172" y="290">Steam</text><text x="452" y="290">arXiv</text></g>
</svg>
<figcaption>Listing–point cosine, mean of the two generators. Remove or swap the neighbours and the little a listing got closer to a FAR point disappears: the cosine score on its own brings nothing closer.</figcaption>
</figure>

The result was the same in all 12 combinations. Changing the neighbours drags the listing toward the neighbours it sees. And in FAR, the little the listing got closer to the point (0.02–0.07 with the true neighbours) vanishes as soon as you remove or swap them: it stays at −0.02/−0.01. **The cosine score alone does not move the text toward a far point. What the LLM can do is write something similar to what you show it.** The simple formula I had been using to describe it (landing proportional to the neighbours' centroid) holds precisely only in REAL; in FAR and most of GAP it is approximate. The effect is causal; the law, only approximate.

## What does work: asking without the map

The inner gaps (GAP) can be reached: the listing gets to 0.48–0.55 of the point, the same as the best existing game. But they are not newer. The judges gave them a novelty of 4.9, below INTERP (5.5) for all six generators. A hole between games gets filled with something that looks like the games around it.

What the judges found most novel was what did not use the map: PLAIN, simply asking for "a new game", with a novelty of 7.8. For every generator PLAIN beat the best guided arm by between 1.1 and 2.6 points.

Until I read the listings one after another. Claude Sonnet named 45 of its 50 games "Tidewright" something. Luna, through Codex, wrote 46 museums out of 50. I saw it straight away ("another museum… tiresome"); the judges did not, because they scored each listing on its own and never saw two together. Each idea was new against the catalogue, but the generator kept repeating the same idea.

<figure class="lg-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Median similarity between each generator's 50 ideas. PLAIN with Sonnet reaches 0.86 and with luna via Codex 0.81, far above 50 random real games (0.40) and the guided arms (0.35-0.49).">
<g font-size="11.5" fill="#e2e8f0" text-anchor="end">
<text x="200" y="45">PLAIN · Sonnet</text><text x="200" y="75">PLAIN · luna via Codex</text><text x="200" y="105">PLAIN · gpt-6.1-sol</text><text x="200" y="135">PLAIN · luna (API)</text><text x="200" y="165">PLAIN · Haiku</text><text x="200" y="195">PLAIN · Opus</text><text x="200" y="225">50 random real games</text><text x="200" y="255">guided arms</text>
</g>
<g fill="#f59e0b"><rect x="210" y="34" width="241.9" height="15"/><rect x="210" y="64" width="227.1" height="15"/></g>
<g fill="#b45309"><rect x="210" y="94" width="176.9" height="15"/><rect x="210" y="124" width="160.7" height="15"/><rect x="210" y="154" width="159.3" height="15"/><rect x="210" y="184" width="145.6" height="15"/></g>
<rect x="210" y="214" width="113.1" height="15" fill="#64748b"/>
<rect x="308" y="244" width="39.2" height="15" fill="#2dd4bf"/>
<g font-size="10.5" fill="#94a3b8"><text x="457" y="46">0.86 · 45/50 "Tidewright"</text><text x="443" y="76">0.81 · 46/50 museums</text><text x="393" y="106">0.63</text><text x="377" y="136">0.57</text><text x="375" y="166">0.57</text><text x="362" y="196">0.52</text><text x="329" y="226">0.40</text><text x="353" y="256">0.35–0.49</text></g>
<line x1="210" y1="25" x2="210" y2="265" stroke="rgba(255,255,255,0.25)"/>
<text x="300" y="288" fill="#94a3b8" font-size="10.5" text-anchor="middle">median cosine between pairs of ideas from the same generator (higher = more repeated)</text>
</svg>
<figcaption>Asking without the map gives the newest ideas one at a time, but two generators almost always repeat the same one. Showing the model its earlier ideas (PLAIND) removes the repetition.</figcaption>
</figure>

I fixed it with a variant, PLAIND, in which the model sees the titles it has already proposed. Diversity gets close to that of the guided arms and novelty stays the highest: in patents, PLAIND beats INTERP by between 2 and almost 5 points.

I also scored a sample myself, and my novelty and the judges' are less alike than I expected. In patents I give every arm between 1.2 and 3 points less than the judges, and FAR 3 less. For 3 of the 4 FAR patents I scored, my answer was "yes, I know something that does this"; of a GAP one I wrote that it was "a good old recommendation system". I think we are measuring different things: the judges reward what is specific and unfamiliar against the five neighbours they see, and I ask whether the concept already exists.

## What if we really search for a coherent text far away?

All of the above had a way out: maybe the LLM does not reach the far points because it does not search well, not because there is nothing there. So I searched harder: a GPU search that optimises the cosine directly, without neighbours, whose texts Claude or Codex then rewrote to make them readable, with only the cosine as a hint. Two judges had to accept the text as coherent. Before looking at the far points I checked that the method worked: it recovered all 10 hidden REAL games (and all 10 papers) into the top 1% most similar of the corpus.

On arXiv my objection holds: for 90% of the FAR points the best coherent text does not go beyond the nearest existing paper. On Steam not entirely: for 25% of the points the coherent text does beat the nearest game by more than 0.05 (15% if I also require the approval of a third judge that neither wrote nor filtered anything it judged). So getting a little beyond what exists is possible.

<figure class="lg-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Cosine scale from 0 to 1. The best existing game is at 0.042 from a FAR point and the best coherent text at 0.07, 0.14 at most; a hidden real game is recovered at 0.84 and the point is at 1.">
<line x1="40" y1="60" x2="560" y2="60" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>
<g font-size="10" fill="#94a3b8" text-anchor="middle"><text x="40" y="78">0</text><text x="300" y="78">0.5</text><text x="560" y="78">1</text></g>
<rect x="40" y="52" width="104" height="16" fill="none" stroke="#64748b" stroke-dasharray="3 3"/>
<circle cx="477.8" cy="60" r="5" fill="#2dd4bf"/><text x="477.8" y="96" fill="#5eead4" font-size="11" text-anchor="middle">REAL: 0.84</text>
<path d="M560,48 l3,7 8,1 -6,5 2,8 -7,-4 -7,4 2,-8 -6,-5 8,-1z" fill="#f59e0b"/><text x="548" y="35" fill="#fbbf24" font-size="11" text-anchor="end">the point: 1</text>
<path d="M92,68 L40,132 M144,68 L560,132" stroke="#64748b" stroke-dasharray="3 3" fill="none"/>
<line x1="40" y1="150" x2="560" y2="150" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>
<g font-size="10" fill="#94a3b8" text-anchor="middle"><text x="40" y="168">0</text><text x="300" y="168">0.1</text><text x="560" y="168">0.2</text></g>
<line x1="149" y1="140" x2="149" y2="160" stroke="#94a3b8" stroke-width="2"/>
<text x="149" y="128" fill="#e2e8f0" font-size="11" text-anchor="middle">best existing game 0.042</text>
<circle cx="219" cy="150" r="5" fill="#2dd4bf"/>
<text x="219" y="190" fill="#5eead4" font-size="11" text-anchor="middle">coherent median 0.07</text>
<rect x="274" y="144" width="130" height="12" rx="3" fill="rgba(45,212,191,0.35)" stroke="#2dd4bf"/>
<text x="339" y="128" fill="#5eead4" font-size="11" text-anchor="middle">the escapes: 0.09–0.14</text>
<text x="300" y="218" fill="#94a3b8" font-size="10.5" text-anchor="middle">zoom from 0 to 0.2 · Steam, FAR points, GPU search + rewrite</text>
</svg>
<figcaption>Beyond any existing game is not the same as at the point. Even the coherent texts that escape stay at 0.09–0.14 from a point that sits at 1.</figcaption>
</figure>

But look at the scale. Those escaping texts stay at a cosine of 0.09–0.14 from their point, when the nearest game was at 0.04 and the point itself is at 1. "Further out than any game" is not "at the point". This qualifies my objection, and I think it improves it: it is not that leaving the map is impossible, it is that what you can reach is very far from what you asked for, and what you read is still an ordinary game.

## Can it be proved?

I wanted to go beyond the data and, with the help of gpt-6-astra, I tried to prove a bound: how close a coherent text can get to a far point. No bound held. Each proposal fell against the data we already had: coherence is not smooth (the judges give opposite verdicts to listings that differ by one word), and no probability threshold of a language model separates what the judges accept from what they reject.

So I turned it around: can we prove there is no bound? Strictly speaking, no, because with texts of bounded length the set is finite and there is always a maximum. What was proved, and checked in Lean, is that without a rule saying what counts as coherent nobody can certify a ceiling tighter than the trivial one, however many queries they make, and that in general the problem is computationally hard. Every candidate rule we tried fell against the data.

## In short

- **Inner gaps can be reached, but they are not new**: they get filled with something like what surrounds them.
- **Far points cannot be reached**: the text falls back into the cap where texts are, next to the neighbours it is shown. And that is causal.
- **Novelty came from asking for it**, not from empty geometry, as long as the model sees what it has already proposed.

The tweet gets something right: there are unexplored corners of the map that can be reached. But a point far from everything is not an idea waiting to be written; almost always it is a place where no text fits.

The other half of the question remains, the one a catalogue cannot measure: can a model reach an idea that really did not exist? It is the Einstein test Demis Hassabis proposed: train a model only on what was known before 1911 and see whether it reaches general relativity. That will be part two, with a generator whose training cutoff is controlled.
