---
title: "The Gaps in the Map Are Not Ideas"
description: "A tweet proposed mining new ideas from the empty points of an embedding space. I tested it on Steam games, arXiv papers and patents: no coherent text reaches those points, and what comes out of them is an ordinary game."
pubDate: 2026-11-02
tags: ["AI", "Embeddings", "LLMs", "Research", "Creativity"]
lang: en
translationKey: far-points-are-not-ideas
heroImage: "/blog/far-points-are-not-ideas.png"
---
Recently [@syntheticbeef posted a recipe on X](https://x.com/syntheticbeef/status/2112904858718367750) for getting AI to invent genuinely new ideas. You embed the games on Steam, pick points in the space that are far from all of them, turn each point back into a game description, and rank the results by how different they are from what already exists. If a point is far from everything, the idea that comes out of it should be new.

My objection was immediate. In a space with a thousand dimensions almost everything is far from everything, and almost all of that space is noise. An empty point is not necessarily a place where an idea fits. It may be a place where no meaningful text fits at all.

A friend replied that coherence is just one more dimension, with its own local optima, and that image diffusion proves it: ask for an astronaut riding a horse and you get one, even though the model has never seen such a thing. I agreed that those strange, meaningful corners exist. But diffusion reaches them by starting from concepts it knows ("astronaut", "horse") and combining them by similarity. The tweet does the opposite: it looks for dissimilarity, with no concept to start from.

It was an argument that could be measured, so I measured it.

<style>
.lg-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.lg-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.lg-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Three maps

The main map is the tweet's: the 71,939 Steam games released before 2024, with their descriptions, genres and tags. I set aside the 41,000 released afterwards, to check at the end whether any idea got ahead of what came out later.

A video game catalogue is a very particular space, and I did not want the conclusion to depend on it. So I repeated everything on two other catalogues that look nothing like Steam:

- **arXiv**: 72,000 computer science papers from before 2023, each with its title and abstract.
- **Patents**: 71,521 US patent applications filed between 2012 and 2015.

Each text becomes a vector with Qwen3-Embedding-0.6B, an open embedding model. To measure how close two texts are I use the cosine between their vectors: 1 if they point the same way, 0 if they have nothing to do with each other.

A note on the Steam map. I left out the 3,717 games that Steam tags as sexual content or nudity, because Azure's content filter rejected requests that showed them as examples. I checked afterwards that adding them back does not change the geometry: the nearest game to the far points stays at the same distance, and the centre of the map barely moves (cosine 0.9999 between the two centres). Explicit games without the tag did stay in, though, and one of them appears below.

## Turning a point into a game

A point in the space cannot be read directly. To "decode" it, an LLM writes a game listing in a loop. In each round it sees the 8 real games nearest to the point and, after writing, it only gets back a score: the cosine between its listing and the point. Four rounds of three candidates, and I keep the best. On arXiv the LLM writes a paper abstract, and on patents, an application.

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

I tried five kinds of point. Each kind is what an experiment calls an arm:

- **REAL**: the point of a real game that I hide from the map. This is the control. If the method cannot recover a game that exists, nothing else means anything.
- **INTERP**: the midpoint between two very different games, the geometric version of "combine two distant ideas".
- **GAP**: interior holes, points that fall in the region where games are but where there is none.
- **FAR**: the tweet's recipe. Out of 20,000 random directions, the 50 furthest from any game.
- **PLAIN**: no map. I just ask the model to "invent a new game, different from any that exists".

On Steam I used six generators, the models that write the listings: Claude Opus, Sonnet and Haiku, gpt-6.1-sol, and gpt-6-luna through the API and through Codex. On arXiv and patents I used two, luna through Codex and Sonnet. Before scoring, another model rewrote every listing into the same 120-word format, so that style would not give away where it came from. Then four different models scored them blind on coherence, feasibility, appeal, and novelty against the five most similar existing texts. Real games released after 2024 were mixed in as a reference. I also scored 80 by hand.

## What comes out of each kind of point

**REAL works.** When the point is a hidden game, the decoder goes back to its neighbourhood, at a cosine of around 0.7. It gets as close as the most similar existing game, and sometimes closer. With *Star Farmer: Warlock of the Universe* hidden, it wrote *Voidbloom Run*, a space-farming game about growing seeds on hostile planets, at 0.87.

And it rebuilds whatever is on the map, including what nobody would want. One of the hidden games was *SEX with HITLER: WW2*, and the neighbours the model saw included its two sequels. It wrote *Hitler: No Future in Berlin*, a visual novel with shooting in which the defeated Führer tries to survive in the ruins of Berlin and meets "five adult heroines" (cosine 0.69). The method has no judgement. It goes wherever there is text.

**INTERP produces literal combinations.** Between a virtual reality meditation game and a strategy game with demons came *Ashen Breath: Legions of the Void*, a dark-fantasy tactical RPG "with an optional VR meditation mode" (0.84). It is what was asked for, and you can see the seam.

**FAR goes nowhere.** The listing lands at a cosine of 0.03 to 0.05 from the point, depending on the generator, which is practically zero. And it is not that the LLM is doing badly: the nearest existing game to those points is at 0.046. What comes out is an ordinary game. The neighbours of one point were *Challenge from the Black Cat*, a Japanese hamster puzzle game and *My Furry Stepmom*, and out came *Pounce & Pop: Kitten's Block Quest*, a kitten pushing blocks to get home (0.069). Another gave *The Museum of Unfinished Things*, a museum that rearranges itself at night (0.028). Reasonable games, pleasant even, that could already be on Steam.

The geometry explains why. Texts do not spread across the whole space. They all share a common direction, so they occupy a narrow cap of the sphere: any two Steam games have a cosine of 0.41, while two random directions have 0 ± 0.03. FAR points are random directions picked for being far from everything, so they fall outside the cap. Any listing the LLM writes, however odd, falls inside it.

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

The same happens on arXiv and patents. Before building any arXiv point, I computed from the corpus statistics alone how far the nearest paper would be from a far point. I predicted 0.062 and got 0.058. On patents it came out at 0.062. In all three catalogues, what gets written for a FAR point lands below 0.08.

## The text goes where the neighbours are

Looking at where the FAR listings landed, I noticed something else. They were much closer to the 8 neighbours the LLM had been shown than to the point itself: on Steam, at a cosine of 0.63–0.72 from their centroid, against 0.03 from the point. That held for 100% of FAR listings in all three catalogues. But it was a correlation, and it could have another explanation: maybe the neighbours are simply the closest thing to the point that exists.

So I ran the causal test. Same point, same cosine score, and only one change: the neighbours the LLM sees. They can be the true ones, another point's, or none at all. I ran it on Steam and arXiv, with two generators (luna and Sonnet), on REAL, GAP and FAR, with 20 points per combination and the decision rules written down before running anything. Patents were not part of this test.

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

The result was the same in all 12 combinations: changing the neighbours drags the listing towards whatever neighbours it sees. On FAR, the little the listing got closer to the point (0.02–0.07 with the true neighbours) disappears as soon as you remove or swap them, and it sits at −0.02/−0.01. **The cosine score on its own does not bring the text any closer to a far point. What the LLM can do is write something that resembles what you show it.**

## What does work: asking without a map

Interior holes can be reached. A GAP listing gets to 0.48–0.55 from its point on Steam, as close as the best existing game. But they are not newer. On Steam the judges gave them a novelty of 4.9 out of 10, below INTERP (5.5), with all six generators. On arXiv they tied with INTERP, and on patents it depends on the generator. A hole between games gets filled with something that looks like the games around it.

For the judges, the most novel output was the one that did not use the map: PLAIN, simply asking for "a new game". With every generator, PLAIN beat the best guided arm by 1.1 to 2.6 points of novelty.

Until I read the listings one after another. Sonnet called 45 of its 50 games "Tidewright" something, and luna through Codex wrote 46 museums out of 50. I saw it straight away ("otro museo… cansino", another museum, tiresome). The judges did not, because they scored each listing on its own and never saw two together. Each idea was new against the catalogue, but the generator kept repeating the same idea. The same happened on arXiv: Sonnet titled 43 of its 50 papers "Tidal" something.

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

My novelty and the judges' turned out less alike than I expected. On patents I gave every arm 1.2 to 3 points less than the judges did. For three of the four FAR patents I read I answered "yes, I know something that does this", and of one GAP patent I wrote that it was "un recommendation system de toda la vida", a plain old recommendation system. I think we measure different things. The judges reward what is specific and unfamiliar compared with the five texts they are shown, and I ask whether the concept already exists.

## What if we really search for a coherent text far away?

All of the above left the tweet one way out: maybe the LLM does not reach far points because it searches badly, not because there is nothing there. So I searched harder. A GPU search optimises the cosine directly, without showing any neighbours, and produces texts that get very close to the point but are word soup. Claude or Codex then rewrite them so they can be read, with the cosine as their only clue. Two models had to accept the text as coherent. Before looking at far points I checked that the method worked: it recovered all 10 hidden games and all 10 hidden papers of REAL.

On arXiv my objection holds: for 90% of FAR points, the best coherent text does not beat the nearest existing paper. On Steam, not entirely. For 25% of the points the coherent text does land more than 0.05 above the nearest game, and for 15% if I also require approval from a third model that had not written or filtered anything it was judging. Getting a little beyond what exists is possible.

<figure class="lg-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Cosine scale from 0 to 1. The best existing game is at 0.042 from a FAR point and the best coherent text at 0.07, 0.14 at most; a hidden real game is recovered at 0.84 and the point is at 1.">
<line x1="40" y1="60" x2="560" y2="60" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>
<g font-size="10" fill="#94a3b8" text-anchor="middle"><text x="40" y="78">0</text><text x="300" y="78">0.5</text><text x="560" y="78">1</text></g>
<rect x="40" y="52" width="104" height="16" fill="none" stroke="#64748b" stroke-dasharray="3 3"/>
<circle cx="477.8" cy="60" r="5" fill="#2dd4bf"/><text x="477.8" y="96" fill="#5eead4" font-size="11" text-anchor="middle">REAL: 0.84</text>
<path d="M560,48 l3,7 8,1 -6,5 2,8 -7,-4 -7,4 2,-8 -6,-5 8,-1z" fill="#f59e0b"/><text x="548" y="35" fill="#fbbf24" font-size="11" text-anchor="end">the point: 1</text>
<path d="M40,68 L40,138 M144,68 L560,138" stroke="#64748b" stroke-dasharray="3 3" fill="none"/>
<line x1="40" y1="150" x2="560" y2="150" stroke="rgba(255,255,255,0.35)" stroke-width="1.5"/>
<g font-size="10" fill="#94a3b8" text-anchor="middle"><text x="40" y="168">0</text><text x="300" y="168">0.1</text><text x="560" y="168">0.2</text></g>
<line x1="149" y1="140" x2="149" y2="160" stroke="#94a3b8" stroke-width="2"/>
<text x="149" y="128" fill="#e2e8f0" font-size="11" text-anchor="middle">nearest game 0.042 (median)</text>
<circle cx="219" cy="150" r="5" fill="#2dd4bf"/>
<text x="219" y="190" fill="#5eead4" font-size="11" text-anchor="middle">coherent median 0.07</text>
<rect x="274" y="144" width="130" height="12" rx="3" fill="rgba(45,212,191,0.35)" stroke="#2dd4bf"/>
<text x="339" y="128" fill="#5eead4" font-size="11" text-anchor="middle">the escapes: 0.09–0.14</text>
<text x="300" y="218" fill="#94a3b8" font-size="10.5" text-anchor="middle">zoom from 0 to 0.2 · Steam, FAR points, GPU search + rewrite</text>
</svg>
<figcaption>Beyond any existing game is not the same as at the point. Even the coherent texts that escape stay at 0.09–0.14 from a point that sits at 1.</figcaption>
</figure>

But look at the scale. Those escaping texts stay at a cosine of 0.09–0.14 from their point. The nearest game was at 0.04 (median of those 20 points), and the point itself is at 1. "Further out than any game" is not "at the point". This qualifies my objection, and I think it improves it. Leaving the map is not impossible. It is that what you reach stays very far from what you asked for, and what you read is still an ordinary game.

## Can it be proved?

I wanted to go beyond the data, and with help from gpt-6-astra I tried to prove a bound: how close a coherent text can get to a far point. No bound held, because each proposal fell to data we already had. Coherence is not smooth: the judges give opposite verdicts to listings that differ by a single word. And no probability threshold from a language model separates what the judges accept from what they reject.

So I turned it around: can we prove there is no bound? Strictly speaking, no, because texts of bounded length are a finite set and always have a maximum. What was proved, and checked in Lean, is something else. Without a rule that says what counts as coherent, nobody can certify a ceiling better than the trivial one, however many tests they run. And in general the problem is computationally hard.

## Did any idea get ahead of the future?

That left the check against later games and papers. On Steam it does not work: once every listing is rewritten into the same format, real games from before and after 2024 are barely distinguishable. On arXiv it does work, and FAR ideas get no closer to what was published after 2023 than any old paper does. PLAIND ideas do get closer. But the generators were trained after 2023, so that shows they know what came next, not that they anticipate it. The one generator that could not know those papers, gpt-4o, anticipates nothing once style is removed.

## In short

- **Interior holes can be reached, but they are not new.** They get filled with something that resembles what surrounds them.
- **Far points cannot be reached.** The text goes back to the cap where texts live, next to the neighbours it is shown, and the causal test shows that the neighbours are what pull it there.
- **Novelty came from asking for it**, not from empty geometry, as long as the model sees what it has already proposed.

The tweet gets something right: there are unexplored corners of the map that can be reached. But a point far from everything is not an idea waiting for someone to write it down. Almost always, it is a place where no text fits.

The other half of the question remains, the one the arXiv result leaves open: can a model reach an idea that genuinely did not exist when it was trained? This is the Einstein test Demis Hassabis proposed: train a model only on what was known before 1911 and see whether it arrives at general relativity. That will be part two, with a generator whose training cutoff I control.
