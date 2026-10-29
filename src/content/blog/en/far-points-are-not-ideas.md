---
title: "The Gaps in the Map Are Not Ideas"
description: "A tweet proposed mining new ideas from the empty points of an embedding space. I tested it on Steam games, arXiv papers and patents: no coherent text reaches those points, and what comes out of them is an ordinary game."
pubDate: 2026-11-02
tags: ["AI", "Embeddings", "LLMs", "Research", "Creativity"]
lang: en
translationKey: far-points-are-not-ideas
heroImage: "/blog/far-points-are-not-ideas.png"
linkedinImage: "/blog/far-points-are-not-ideas-linkedin.png"
---
Recently [@syntheticbeef posted a recipe on X](https://x.com/syntheticbeef/status/2112904858718367750) for getting AI to invent genuinely new ideas. You embed the games on Steam, pick points in the space that are far from all of them, turn each point back into a game description, and rank the results by how different they are from what already exists. If a point is far from everything, the idea that comes out of it should be new.

My objection was immediate: in a space with a thousand dimensions almost everything is far from everything, and almost all of that space is noise. An empty point does not mean there is an idea there; there may be no meaningful text there at all. A friend replied that coherence is just another dimension, with its own local optima, and that image diffusion shows strange, meaningful corners exist: an astronaut riding a horse. I agreed that they exist, but diffusion reaches them by starting from a concept and moving by similarity; the tweet looks for dissimilarity with no starting point.

It was an argument that could be measured, so I measured it.

<style>
.lg-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.lg-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.lg-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Three maps

The main map is the tweet's: the Steam games released before 2024, about 68,000, with their descriptions, genres and tags. I set aside the 41,000 released afterwards, to check at the end whether any idea got ahead of what came out later.

A video game catalogue is a very particular space, and I did not want the conclusion to depend on it. So I repeated everything on two other catalogues that look nothing like Steam:

- **arXiv**: 72,000 computer science papers from before 2023, each with its title and abstract.
- **Patents**: 71,521 US patent applications filed between 2012 and 2015.

Each text becomes a vector with Qwen3-Embedding-0.6B, an open embedding model. To measure how close two texts are I use the cosine between their vectors: 1 if they point the same way, 0 if they have nothing to do with each other.

## Two ways to turn a point into text

A point in the space is a list of 1,024 numbers. No language model can read it, so the tweet takes for granted a step that is not trivial: turning the point back into text. There are two ways to do it.

The first is the one anyone would think of. You show the LLM the 8 real games nearest to the point, ask it for a game listing, and tell it how close it got: the cosine between its listing and the point. With that score it tries again, like a game of hot and cold. Four rounds of three candidates, and I keep the best. On arXiv the LLM writes a paper abstract, and on patents, an application.

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

This approach has an obvious problem. Give it 8 games and it will most likely write something that resembles those 8, and then the point is irrelevant: it is the same as asking "make me a game based on these". The only thing that could make the point matter is the cosine score. If hot and cold worked, the LLM would move towards the point beyond what the neighbours give it. That can be measured, and I measured it.

The second way shows nothing. A GPU search generates texts that directly maximise the cosine with the point. Those texts get very close, but they are word soup, so Claude or Codex then rewrite them to be readable, with the cosine as their only clue. Two models have to accept the result as coherent. This is the real test of the tweet's idea: if there is a coherent text near the point, this is the method most likely to find it.

## Five kinds of point

I tried five kinds of point. Each kind is what an experiment calls an arm:

- **REAL**: the point of a real game that I hide from the map. This is the control. If the method cannot recover a game that exists, nothing else means anything.
- **INTERP**: the midpoint between two very different games, the geometric version of "combine two distant ideas".
- **GAP**: interior holes, points that fall in the region where games are but where there is none.
- **FAR**: the tweet's recipe. Out of 20,000 random directions, the 50 furthest from any game.
- **PLAIN**: no map. I just ask the model to "invent a new game, different from any that exists".

On Steam I used six generators, the models that write the listings: Claude Opus, Sonnet and Haiku, gpt-6.1-sol, and gpt-6-luna through the API and through Codex. On arXiv and patents I used two, luna through Codex and Sonnet. Before scoring, another model rewrote every listing into the same 120-word format, so that style would not give away where it came from. Then four different models scored them blind on coherence, feasibility, appeal, and novelty against the five most similar existing texts. Real games released after 2024 were mixed in as a reference. I also scored 64 of the same items by hand.

## What comes out when you show the neighbours

**REAL works.** When the point is a hidden game, the decoder goes back to its neighbourhood, at a cosine of around 0.7. With *Star Farmer: Warlock of the Universe* hidden, it wrote *Voidbloom Run*, a space-farming game about growing seeds on hostile planets, at 0.87.

And it rebuilds whatever is on the map, including what nobody would want. One of the hidden games was *SEX with HITLER: WW2*, and the neighbours the model saw included its two sequels. It wrote *Hitler: No Future in Berlin*, a visual novel with shooting in which the defeated Führer tries to survive in the ruins of Berlin and meets "five adult heroines" (cosine 0.69).

**INTERP produces literal combinations.** Between a virtual reality meditation game and a strategy game with demons came *Ashen Breath: Legions of the Void*, a dark-fantasy tactical RPG "with an optional VR meditation mode" (0.84). It is what was asked for, and you can see the seam.

**FAR goes nowhere.** The listing lands at a cosine of 0.03 to 0.05 from the point, depending on the generator, which is practically zero. The nearest existing game to those points is at 0.046, so there is nothing better either. What comes out is an ordinary game that resembles the neighbours it was shown. One point's neighbours were *Challenge from the Black Cat*, a Japanese hamster puzzle game and *My Furry Stepmom*, and out came *Pounce & Pop: Kitten's Block Quest*, a kitten pushing blocks to get home (0.069). Another gave *The Museum of Unfinished Things*, a museum that rearranges itself at night (0.028). Reasonable games, pleasant even, that could already be on Steam.

The same happens on arXiv and patents: what gets written for a FAR point lands below 0.08.

## Is it just copying the neighbours?

FAR listings were much closer to their 8 neighbours than to the point itself: on Steam, at a cosine of 0.63–0.72 from their centroid, against 0.03 from the point. That held for 100% of FAR listings in all three catalogues. The question from before was still open: does the cosine score add anything, or is it all the neighbours?

To separate the two I ran a causal test. Same point, same cosine score, and only one change: the neighbours the LLM sees. They can be the true ones, another point's, or none at all. I ran it on Steam and arXiv, with two generators (luna and Sonnet), on REAL, GAP and FAR, with 20 points per combination and the decision rules written down before running anything.

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
<figcaption>Listing–point cosine, mean of the two generators. Without the true neighbours, even a hidden game or paper stays at 0.3–0.4, barely closer than to any other point. The cosine score on its own brings almost nothing closer.</figcaption>
</figure>

It is the neighbours, in all 12 combinations. With another point's neighbours, the listing heads towards that other point. With no neighbours, playing hot and cold alone, the listing ends up only 0.04 to 0.07 closer to its own point than to any other point of the same kind. Even for a hidden game, without neighbours it stays at 0.36–0.47, when with them it reaches 0.7–0.8.

In hindsight this looks obvious, and partly it is: give an LLM 8 games and it writes something that depends on those 8, not on a point it knows nothing about. But that is what any decoder built on an LLM this way does, so any "idea" that comes out of a point along this route is a blend of its neighbours. To find out whether there is anything at the point, you have to search without neighbours.

## Searching without neighbours

Before looking at far points I checked that the search worked. With the hidden games and papers of REAL, the best coherent text ended up closer to the point than any existing text in all 10 cases in each catalogue. In most GAP holes it reached the level of what exists, or a little beyond.

<figure class="lg-fig">
<svg viewBox="0 0 600 328" role="img" aria-label="Each dot is a point in the space. Horizontally, the cosine of the nearest existing text; vertically, that of the best coherent text found by the search without neighbours. On REAL and GAP the search gets as close as what exists, or closer. On FAR everything stays in the bottom corner: on Steam 5 of 20 points beat what exists by more than 0.05, but none passes 0.14.">
<text x="160" y="22" fill="#e2e8f0" font-size="12" text-anchor="middle" font-weight="600">all points (Steam)</text>
<rect x="60" y="50" width="200" height="200" fill="none" stroke="rgba(255,255,255,0.12)"/>
<line x1="60" y1="250" x2="260" y2="50" stroke="#64748b" stroke-dasharray="4 4"/>
<text x="60" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0</text>
<text x="54" y="253.5" fill="#94a3b8" font-size="10" text-anchor="end">0</text>
<text x="160.0" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0.5</text>
<text x="54" y="153.5" fill="#94a3b8" font-size="10" text-anchor="end">0.5</text>
<text x="260" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">1</text>
<text x="54" y="53.5" fill="#94a3b8" font-size="10" text-anchor="end">1</text>
<circle cx="71.4" cy="240.8" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="66.6" cy="238.8" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="69.4" cy="251.6" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="67.5" cy="236.7" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="67.7" cy="234.8" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="67.3" cy="243.4" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.2" cy="240.0" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.0" cy="225.7" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.1" cy="248.4" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="73.8" cy="240.7" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.4" cy="235.6" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.5" cy="222.4" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.5" cy="231.4" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.5" cy="234.7" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="69.2" cy="233.2" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="68.8" cy="238.8" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="70.7" cy="234.9" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="69.9" cy="228.2" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="70.3" cy="229.0" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="71.1" cy="241.1" r="3.2" fill="#f8fafc" fill-opacity="0.85"/>
<circle cx="164.0" cy="154.4" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="165.1" cy="145.0" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="164.4" cy="120.7" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="164.0" cy="144.2" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="169.0" cy="131.5" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="167.7" cy="132.0" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="169.2" cy="138.3" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="169.7" cy="142.0" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="166.3" cy="141.2" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="166.9" cy="128.5" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="166.7" cy="144.3" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="174.5" cy="154.7" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="171.2" cy="158.6" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="167.1" cy="145.1" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="170.7" cy="132.1" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="168.0" cy="134.8" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="171.0" cy="134.3" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="168.3" cy="121.6" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="167.7" cy="130.3" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="171.2" cy="133.9" r="3.2" fill="#f59e0b" fill-opacity="0.85"/>
<circle cx="202.0" cy="96.9" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="206.0" cy="78.9" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="226.2" cy="72.8" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="208.6" cy="72.4" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="200.2" cy="84.2" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="215.7" cy="79.1" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="206.1" cy="95.7" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="204.9" cy="88.2" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="213.7" cy="78.8" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<circle cx="204.6" cy="86.5" r="3.2" fill="#2dd4bf" fill-opacity="0.85"/>
<text x="202.0" y="60.0" fill="#5eead4" font-size="11" text-anchor="end">REAL</text>
<text x="166.0" y="110.0" fill="#fbbf24" font-size="11" text-anchor="middle">GAP</text>
<text x="78.0" y="216.0" fill="#f8fafc" font-size="11">FAR</text>
<rect x="58.0" y="220.0" width="34.0" height="32.0" fill="none" stroke="#94a3b8" stroke-dasharray="2 2"/>
<text x="98.0" y="246.0" fill="#94a3b8" font-size="10">zoom →</text>
<text x="440" y="22" fill="#e2e8f0" font-size="12" text-anchor="middle" font-weight="600">zoom: FAR points</text>
<rect x="340" y="50" width="200" height="200" fill="none" stroke="rgba(255,255,255,0.12)"/>
<polygon points="340.0,191.1764705882353 481.1764705882353,50.0 340.0,50.0" fill="rgba(45,212,191,0.10)"/>
<line x1="340.0" y1="191.1764705882353" x2="481.1764705882353" y2="50.0" stroke="#2dd4bf" stroke-width="0.8" stroke-dasharray="3 3"/>
<line x1="340.0" y1="250.0" x2="540.0" y2="50.0" stroke="#64748b" stroke-dasharray="4 4"/>
<text x="363.52941176470586" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0</text>
<text x="546" y="229.97058823529412" fill="#94a3b8" font-size="10">0</text>
<text x="422.3529411764706" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0.05</text>
<text x="546" y="171.1470588235294" fill="#94a3b8" font-size="10">0.05</text>
<text x="481.1764705882353" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0.1</text>
<text x="546" y="112.3235294117647" fill="#94a3b8" font-size="10">0.1</text>
<text x="540.0" y="265" fill="#94a3b8" font-size="10" text-anchor="middle">0.15</text>
<text x="546" y="53.5" fill="#94a3b8" font-size="10">0.15</text>
<circle cx="430.9" cy="172.4" r="3.4" fill="#f8fafc"/>
<circle cx="402.6" cy="160.4" r="3.4" fill="#f8fafc"/>
<circle cx="418.9" cy="235.8" r="3.4" fill="#f8fafc"/>
<circle cx="407.9" cy="148.1" r="3.4" fill="#f8fafc"/>
<circle cx="409.1" cy="137.3" r="3.4" fill="#f8fafc"/>
<circle cx="406.6" cy="187.9" r="3.4" fill="#f8fafc"/>
<circle cx="411.8" cy="167.8" r="3.4" fill="#f8fafc"/>
<circle cx="410.4" cy="83.7" r="3.4" fill="#f8fafc"/>
<circle cx="411.1" cy="217.1" r="3.4" fill="#f8fafc"/>
<circle cx="444.7" cy="171.9" r="3.4" fill="#f8fafc"/>
<circle cx="413.2" cy="141.9" r="3.4" fill="#f8fafc"/>
<circle cx="413.4" cy="64.4" r="3.4" fill="#f8fafc"/>
<circle cx="413.6" cy="116.8" r="3.4" fill="#f8fafc"/>
<circle cx="413.8" cy="136.4" r="3.4" fill="#f8fafc"/>
<circle cx="417.5" cy="127.8" r="3.4" fill="#f8fafc"/>
<circle cx="415.6" cy="160.7" r="3.4" fill="#f8fafc"/>
<circle cx="426.4" cy="137.6" r="3.4" fill="#f8fafc"/>
<circle cx="421.5" cy="98.1" r="3.4" fill="#f8fafc"/>
<circle cx="424.1" cy="103.2" r="3.4" fill="#f8fafc"/>
<circle cx="428.8" cy="174.2" r="3.4" fill="#f8fafc"/>
<circle cx="432.1" cy="153.9" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="439.1" cy="165.4" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="421.0" cy="241.5" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="423.6" cy="147.8" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="441.0" cy="167.0" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="430.5" cy="190.4" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="444.5" cy="168.0" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="428.2" cy="167.1" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="454.0" cy="153.6" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="441.5" cy="186.5" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="440.0" cy="197.3" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="428.7" cy="138.9" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="453.7" cy="135.4" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="462.0" cy="98.6" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="453.3" cy="149.3" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="434.7" cy="110.2" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="429.9" cy="189.9" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="436.4" cy="233.0" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="436.0" cy="136.4" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<circle cx="453.0" cy="100.9" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/>
<text x="160" y="282" fill="#94a3b8" font-size="10.5" text-anchor="middle">nearest existing text →</text>
<text x="440" y="282" fill="#94a3b8" font-size="10.5" text-anchor="middle">nearest existing text →</text>
<text x="22" y="150" fill="#94a3b8" font-size="10.5" text-anchor="middle" transform="rotate(-90 22 150)">best coherent text found →</text>
<circle cx="150" cy="310" r="3.4" fill="#f8fafc"/><text x="158" y="313.5" fill="#e2e8f0" font-size="10.5">FAR Steam</text>
<circle cx="240" cy="310" r="3.4" fill="none" stroke="#fbbf24" stroke-width="1.3"/><text x="248" y="313.5" fill="#e2e8f0" font-size="10.5">FAR arXiv</text>
<line x1="325" y1="310" x2="345" y2="310" stroke="#64748b" stroke-dasharray="4 4"/><text x="351" y="313.5" fill="#e2e8f0" font-size="10.5">same as what exists</text>
<rect x="478" y="304" width="14" height="12" fill="rgba(45,212,191,0.25)" stroke="#2dd4bf" stroke-width="0.8" stroke-dasharray="3 3"/><text x="498" y="313.5" fill="#e2e8f0" font-size="10.5">+0.05: escapes</text>
</svg>
<figcaption>The search without neighbours gets where text already exists, and a little beyond. On FAR points it stays stuck near zero: on Steam, 5 of 20 beat what exists by more than 0.05, and the best reaches 0.14.</figcaption>
</figure>

On FAR points things change. On arXiv my objection holds: for 90% of the points, the best coherent text does not beat the nearest existing paper. On Steam, not entirely. For 25% of the points the coherent text does land more than 0.05 above the nearest game, and for 15% if I also require approval from a third model that had not written or filtered anything it was judging. Getting a little beyond what exists is possible.

But look at the scale. Those escaping texts stay at a cosine of 0.09–0.14 from their point, when the point itself is at 1. "Further out than any game" is not "at the point". This qualifies my objection, and I think it improves it. Leaving the map is not impossible. It is that what you reach stays very far from what you asked for, and what you read is still an ordinary game.

## Why: the cap

The geometry explains why far points are out of reach. Texts do not spread across the whole space. They all share a common direction, so they occupy a narrow cap of the sphere: any two Steam games have a cosine of 0.41, while two random directions have 0 ± 0.03. FAR points are random directions picked for being far from everything, so they fall outside the cap. Any text, however odd, falls inside it.

<figure class="lg-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Texts occupy a narrow cap of the sphere. An interior GAP hole sits inside the cap, between games. A FAR point sits outside it, on the rest of the sphere, and the description written for it lands back in the cap, next to the neighbours it was shown.">
<circle cx="210" cy="190" r="135" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1.4"/>
<path d="M97.8,115 A135,135 0 0,1 322.2,115 Z" fill="rgba(45,212,191,0.12)" stroke="#2dd4bf" stroke-width="1.2"/>
<g fill="#94a3b8"><circle cx="130" cy="108" r="3"/><circle cx="152" cy="100" r="3"/><circle cx="172" cy="90" r="3"/><circle cx="190" cy="104" r="3"/><circle cx="196" cy="74" r="3"/><circle cx="240" cy="72" r="3"/><circle cx="258" cy="92" r="3"/><circle cx="242" cy="106" r="3"/><circle cx="222" cy="64" r="3"/><circle cx="268" cy="108" r="3"/><circle cx="160" cy="80" r="3"/></g>
<g fill="#f8fafc"><circle cx="286" cy="100" r="3.6"/><circle cx="300" cy="108" r="3.6"/><circle cx="302" cy="96" r="3.6"/></g>
<circle cx="292" cy="90" r="5" fill="#2dd4bf"/>
<circle cx="216" cy="88" r="6" fill="none" stroke="#fbbf24" stroke-width="1.6"/>
<defs><marker id="lga2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
<path d="M302,282 C405,245 400,140 310,108" fill="none" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#lga2)"/>
<path d="M297,286 l4,9 10,1 -7.5,6.5 2.5,10 -9,-5.5 -9,5.5 2.5,-10 -7.5,-6.5 10,-1z" fill="#f59e0b"/>
<line x1="216" y1="96" x2="216" y2="140" stroke="#fbbf24" stroke-width="1"/>
<line x1="392" y1="66" x2="298" y2="88" stroke="#5eead4" stroke-width="1"/>
<g font-size="12">
<text x="210" y="22" fill="#5eead4" text-anchor="middle" font-weight="600">the cap where texts live</text>
<text x="210" y="40" fill="#94a3b8" text-anchor="middle" font-size="10.5">any two games: cos 0.41 · two random directions: 0 ± 0.03</text>
<text x="216" y="156" fill="#fbbf24" text-anchor="middle">GAP hole</text>
<text x="216" y="171" fill="#94a3b8" text-anchor="middle" font-size="10.5">inside, between games</text>
<text x="210" y="240" fill="#64748b" text-anchor="middle" font-size="10.5">the rest of the sphere:</text>
<text x="210" y="254" fill="#64748b" text-anchor="middle" font-size="10.5">directions with no text at all</text>
<text x="398" y="62" fill="#5eead4">the description written</text>
<text x="398" y="78" fill="#94a3b8" font-size="10.5">lands back in the cap, next to</text>
<text x="398" y="92" fill="#94a3b8" font-size="10.5">the neighbours it saw (white)</text>
<text x="398" y="292" fill="#fbbf24">FAR point</text>
<text x="398" y="308" fill="#94a3b8" font-size="10.5">the nearest game is</text>
<text x="398" y="322" fill="#94a3b8" font-size="10.5">at cos 0.046</text>
</g>
</svg>
<figcaption>Schematic, not to scale. GAP holes lie inside the region where text exists; FAR points lie outside it. Whatever is written for a FAR point lands back inside.</figcaption>
</figure>

With this geometry the distance can be predicted before looking. Before building any arXiv point, I computed from the corpus statistics alone how far the nearest paper would be from a far point. I predicted 0.062 and got 0.058. On patents it came out at 0.062.

## What does work: asking without a map

Interior holes can be reached, but they are not newer. On Steam the judges gave them a novelty of 4.9 out of 10, below INTERP (5.5), with all six generators. On arXiv they tied with INTERP, and on patents it depends on the generator. A hole between games gets filled with something that looks like the games around it.

For the judges, the most novel output was the one that did not use the map: PLAIN, simply asking for "a new game". With every generator, PLAIN beat the best guided arm by 1.1 to 2.6 points of novelty.

Until I read the listings one after another. Sonnet called 45 of its 50 games "Tidewright" something, and luna through Codex wrote 46 museums out of 50. I saw it straight away: another museum, and by then a tiresome one. The judges did not, because they scored each listing on its own and never saw two together. Each idea was new against the catalogue, but the generator kept repeating the same idea. The same happened on arXiv: Sonnet titled 43 of its 50 papers "Tidal" something.

<figure class="lg-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Median similarity between each generator's 50 ideas. PLAIN with Sonnet reaches 0.86 and with luna via Codex 0.81, far above 50 random real games (0.40) and the guided arms (0.35-0.49).">
<g font-size="11.5" fill="#e2e8f0" text-anchor="end">
<text x="200" y="45">PLAIN · Sonnet</text><text x="200" y="75">PLAIN · luna via Codex</text><text x="200" y="105">PLAIN · gpt-6.1-sol</text><text x="200" y="135">PLAIN · luna (API)</text><text x="200" y="165">PLAIN · Haiku</text><text x="200" y="195">PLAIN · Opus</text><text x="200" y="225">50 random real games</text><text x="200" y="255">guided arms</text>
</g>
<g fill="#f59e0b"><rect x="210" y="34" width="241.9" height="15"/><rect x="210" y="64" width="227.1" height="15"/></g>
<g fill="#b45309"><rect x="210" y="94" width="176.9" height="15"/><rect x="210" y="124" width="160.7" height="15"/><rect x="210" y="154" width="159.3" height="15"/><rect x="210" y="184" width="145.6" height="15"/></g>
<rect x="210" y="214" width="113.1" height="15" fill="#64748b"/>
<rect x="210" y="244" width="137.2" height="15" fill="rgba(45,212,191,0.3)"/><rect x="210" y="244" width="98" height="15" fill="#2dd4bf"/>
<g font-size="10.5" fill="#94a3b8"><text x="457" y="46">0.86 · 45/50 "Tidewright"</text><text x="443" y="76">0.81 · 46/50 museums</text><text x="393" y="106">0.63</text><text x="377" y="136">0.57</text><text x="375" y="166">0.57</text><text x="362" y="196">0.52</text><text x="329" y="226">0.40</text><text x="353" y="256">0.35–0.49</text></g>
<line x1="210" y1="25" x2="210" y2="265" stroke="rgba(255,255,255,0.25)"/>
<text x="300" y="288" fill="#94a3b8" font-size="10.5" text-anchor="middle">median cosine between pairs of ideas from the same generator (higher = more repeated)</text>
</svg>
<figcaption>Asking without the map gives the newest ideas one at a time, but two generators almost always repeat the same one. Showing the model its earlier ideas (PLAIND) brings repetition down almost to the guided arms.</figcaption>
</figure>

I fixed it with a variant, PLAIND, in which the model sees the titles it has already proposed. Repetition drops almost to the level of the guided arms, and novelty stays the highest in all three catalogues, 1 to 5 points above INTERP depending on the generator.

My novelty and the judges' turned out less alike than I expected.

<figure class="lg-fig">
<svg viewBox="0 0 600 420" role="img" aria-label="Mean novelty I gave against the judges, by catalogue and arm. On Steam we agree except on PLAIN, where the judges give 7.6 and I give 5.2. On arXiv we mostly agree. On patents I give 1.2 to 3 points less on every arm.">
<rect x="230" y="8" width="10" height="10" rx="5" fill="#f59e0b"/><text x="246" y="17" fill="#e2e8f0" font-size="11">me</text>
<rect x="300" y="8" width="10" height="10" rx="5" fill="#2dd4bf"/><text x="316" y="17" fill="#e2e8f0" font-size="11">judges</text>
<text x="20" y="48" fill="#f8fafc" font-size="12" font-weight="600">Steam</text>
<text x="218" y="48" fill="#e2e8f0" font-size="11" text-anchor="end">INTERP <tspan fill="#64748b" font-size="9.5">n=13</tspan></text>
<line x1="230" y1="44" x2="554" y2="44" stroke="rgba(255,255,255,0.06)"/>
<line x1="418.3" y1="44" x2="410.0" y2="44" stroke="#64748b" stroke-width="2"/>
<circle cx="418.3" cy="44" r="5" fill="#f59e0b"/><circle cx="410.0" cy="44" r="5" fill="#2dd4bf"/>
<text x="218" y="75" fill="#e2e8f0" font-size="11" text-anchor="end">GAP <tspan fill="#64748b" font-size="9.5">n=6</tspan></text>
<line x1="230" y1="71" x2="554" y2="71" stroke="rgba(255,255,255,0.06)"/>
<line x1="416.1" y1="71" x2="402.4" y2="71" stroke="#64748b" stroke-width="2"/>
<circle cx="416.1" cy="71" r="5" fill="#f59e0b"/><circle cx="402.4" cy="71" r="5" fill="#2dd4bf"/>
<text x="218" y="102" fill="#e2e8f0" font-size="11" text-anchor="end">PLAIN <tspan fill="#64748b" font-size="9.5">n=5</tspan></text>
<line x1="230" y1="98" x2="554" y2="98" stroke="rgba(255,255,255,0.06)"/>
<line x1="381.2" y1="98" x2="467.6" y2="98" stroke="#64748b" stroke-width="2"/>
<circle cx="381.2" cy="98" r="5" fill="#f59e0b"/><circle cx="467.6" cy="98" r="5" fill="#2dd4bf"/>
<text x="218" y="129" fill="#e2e8f0" font-size="11" text-anchor="end">PLAIND <tspan fill="#64748b" font-size="9.5">n=8</tspan></text>
<line x1="230" y1="125" x2="554" y2="125" stroke="rgba(255,255,255,0.06)"/>
<line x1="446.0" y1="125" x2="455.0" y2="125" stroke="#64748b" stroke-width="2"/>
<circle cx="446.0" cy="125" r="5" fill="#f59e0b"/><circle cx="455.0" cy="125" r="5" fill="#2dd4bf"/>
<text x="20" y="166" fill="#f8fafc" font-size="12" font-weight="600">arXiv</text>
<text x="218" y="166" fill="#e2e8f0" font-size="11" text-anchor="end">GAP <tspan fill="#64748b" font-size="9.5">n=3</tspan></text>
<line x1="230" y1="162" x2="554" y2="162" stroke="rgba(255,255,255,0.06)"/>
<line x1="398.1" y1="162" x2="403.9" y2="162" stroke="#64748b" stroke-width="2"/>
<circle cx="398.1" cy="162" r="5" fill="#f59e0b"/><circle cx="403.9" cy="162" r="5" fill="#2dd4bf"/>
<text x="218" y="193" fill="#e2e8f0" font-size="11" text-anchor="end">FAR <tspan fill="#64748b" font-size="9.5">n=4</tspan></text>
<line x1="230" y1="189" x2="554" y2="189" stroke="rgba(255,255,255,0.06)"/>
<line x1="410.0" y1="189" x2="412.2" y2="189" stroke="#64748b" stroke-width="2"/>
<circle cx="410.0" cy="189" r="5" fill="#f59e0b"/><circle cx="412.2" cy="189" r="5" fill="#2dd4bf"/>
<text x="218" y="220" fill="#e2e8f0" font-size="11" text-anchor="end">PLAIND <tspan fill="#64748b" font-size="9.5">n=5</tspan></text>
<line x1="230" y1="216" x2="554" y2="216" stroke="rgba(255,255,255,0.06)"/>
<line x1="431.6" y1="216" x2="465.8" y2="216" stroke="#64748b" stroke-width="2"/>
<circle cx="431.6" cy="216" r="5" fill="#f59e0b"/><circle cx="465.8" cy="216" r="5" fill="#2dd4bf"/>
<text x="218" y="247" fill="#e2e8f0" font-size="11" text-anchor="end">later real ones <tspan fill="#64748b" font-size="9.5">n=4</tspan></text>
<line x1="230" y1="243" x2="554" y2="243" stroke="rgba(255,255,255,0.06)"/>
<line x1="437.0" y1="243" x2="376.2" y2="243" stroke="#64748b" stroke-width="2"/>
<circle cx="437.0" cy="243" r="5" fill="#f59e0b"/><circle cx="376.2" cy="243" r="5" fill="#2dd4bf"/>
<text x="20" y="284" fill="#f8fafc" font-size="12" font-weight="600">Patents</text>
<text x="218" y="284" fill="#e2e8f0" font-size="11" text-anchor="end">GAP <tspan fill="#64748b" font-size="9.5">n=3</tspan></text>
<line x1="230" y1="280" x2="554" y2="280" stroke="rgba(255,255,255,0.06)"/>
<line x1="349.9" y1="280" x2="419.0" y2="280" stroke="#64748b" stroke-width="2"/>
<circle cx="349.9" cy="280" r="5" fill="#f59e0b"/><circle cx="419.0" cy="280" r="5" fill="#2dd4bf"/>
<text x="218" y="311" fill="#e2e8f0" font-size="11" text-anchor="end">FAR <tspan fill="#64748b" font-size="9.5">n=4</tspan></text>
<line x1="230" y1="307" x2="554" y2="307" stroke="rgba(255,255,255,0.06)"/>
<line x1="338.0" y1="307" x2="446.0" y2="307" stroke="#64748b" stroke-width="2"/>
<circle cx="338.0" cy="307" r="5" fill="#f59e0b"/><circle cx="446.0" cy="307" r="5" fill="#2dd4bf"/>
<text x="218" y="338" fill="#e2e8f0" font-size="11" text-anchor="end">PLAIND <tspan fill="#64748b" font-size="9.5">n=5</tspan></text>
<line x1="230" y1="334" x2="554" y2="334" stroke="rgba(255,255,255,0.06)"/>
<line x1="402.8" y1="334" x2="480.2" y2="334" stroke="#64748b" stroke-width="2"/>
<circle cx="402.8" cy="334" r="5" fill="#f59e0b"/><circle cx="480.2" cy="334" r="5" fill="#2dd4bf"/>
<text x="218" y="365" fill="#e2e8f0" font-size="11" text-anchor="end">later real ones <tspan fill="#64748b" font-size="9.5">n=4</tspan></text>
<line x1="230" y1="361" x2="554" y2="361" stroke="rgba(255,255,255,0.06)"/>
<line x1="356.0" y1="361" x2="398.8" y2="361" stroke="#64748b" stroke-width="2"/>
<circle cx="356.0" cy="361" r="5" fill="#f59e0b"/><circle cx="398.8" cy="361" r="5" fill="#2dd4bf"/>
<text x="230" y="394" fill="#94a3b8" font-size="10" text-anchor="middle">1</text>
<text x="338" y="394" fill="#94a3b8" font-size="10" text-anchor="middle">4</text>
<text x="446" y="394" fill="#94a3b8" font-size="10" text-anchor="middle">7</text>
<text x="554" y="394" fill="#94a3b8" font-size="10" text-anchor="middle">10</text>
<text x="392.0" y="410" fill="#94a3b8" font-size="10.5" text-anchor="middle">mean novelty (1–10)</text>
</svg>
<figcaption>My novelty against the judges' (64 items scored by both). On patents, where I recognised almost everything, I am much harsher; on Steam I only part ways on PLAIN, the one with the repeated museums.</figcaption>
</figure>

On Steam we agree except on PLAIN, because of the repeated museums. On patents I am much harsher on every arm. For three of the four FAR patents I read I answered "yes, I know something that does this", and one GAP patent I described as a plain old recommendation system. I think we measure different things. The judges reward what is specific and unfamiliar compared with the five texts they are shown, and I ask whether the concept already exists.

## Can it be proved?

I wanted to go beyond the data, and with help from gpt-6-astra I tried to prove a bound: how close a coherent text can get to a far point. No bound held, because each proposal fell to data we already had. Coherence is not smooth: the judges give opposite verdicts to listings that differ by a single word. And no probability threshold from a language model separates what the judges accept from what they reject.

So I turned it around: can we prove there is no bound? Strictly speaking, no, because texts of bounded length are a finite set and always have a maximum. What was proved, and checked in Lean, is something else. Without a rule that says what counts as coherent, nobody can certify a ceiling better than the trivial one, however many tests they run. And in general the problem is computationally hard.

## Did any idea get ahead of the future?

That left the check against later games and papers. On Steam it does not work: once every listing is rewritten into the same format, real games from before and after 2024 are barely distinguishable. On arXiv it does work, and FAR ideas get no closer to what was published after 2023 than any old paper does. PLAIND ideas do get closer. But the generators were trained after 2023, so that shows they know what came next, not that they anticipate it. The one generator that could not know those papers, gpt-4o, anticipates nothing once style is removed.

## In short

- **Decoding a point with an LLM blends its neighbours.** The cosine score adds almost nothing; what comes out depends on what you show it.
- **Searching without neighbours, far points are still out of reach.** The best I found stays at 0.14 from a point that sits at 1, because texts live in a cap and those points are outside it.
- **Interior holes can be reached, but they are not new.** They get filled with something that resembles what surrounds them.
- **Novelty came from asking for it**, not from empty geometry, as long as the model sees what it has already proposed.

The tweet gets something right: there are unexplored corners of the map that can be reached. But a point far from everything is not an idea waiting for someone to write it down. Almost always, it is a place where no text fits.

The other half of the question remains, the one the arXiv result leaves open: can a model reach an idea that genuinely did not exist when it was trained? This is the Einstein test Demis Hassabis proposed: train a model only on what was known before 1911 and see whether it arrives at general relativity. That will be part two, with a generator whose training cutoff I control.
