---
title: "The caveat that became the pitch"
description: "A caveat about one bad evaluation set ended up as the headline of the demos, briefs and decks an agent wrote about the product. Nobody decided it: each piece was built from the previous one, and the emphasis grew with every copy."
pubDate: 2026-11-20
tags: ["AI", "Agents", "Claude Code", "Memory"]
lang: en
translationKey: the-caveat-that-became-the-pitch
heroImage: "/blog/the-caveat-that-became-the-pitch.png"
---

<style>
.cap-fig { margin: 2rem 0; padding: 1rem; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.cap-fig svg { width: 100%; height: auto; display: block; }
.cap-fig figcaption { margin-top: 0.75rem; font-size: 0.9rem; color: #94a3b8; line-height: 1.5; }
</style>

A few weeks ago I was reviewing a deck about [an industry classification service I work on](/en/projects/compliance-classifier), to be presented to the company's CEO. Slide three, the one about why the problem is hard, had a card that said: *506 classes. The right one is rarely in the company name.*

I cut it, and then realised I had cut the same idea before: from promo videos, from drafts, from a demo guide. Whenever an agent wrote something about this product for people to read, sooner or later it said, in one form or another, that the service doesn't classify companies by their name.

That is selling a car because it has wheels. Nobody evaluating a classifier assumes it reads the sign over the door and stops there, so nobody sees that as a risk the product protects them from. As a selling point it says nothing. I wanted to know how it got there, and whether I could stop it.

## Where the sentence came from

A couple of months earlier a client had sent us an evaluation set of about 500 companies, along with a report that scored the service at 54%. [I wrote about that set at the time](/en/blog/the-grader-knew-less): its labels had been derived from the company names, a name-only predictor matched them better than the classifier did, and finding a company's real website made the score go *down*.

That finding was correct, and it was useful for evaluation. It meant: don't score against that set, and if people are going to build a reference set by hand, tell them not to guess from names, because that is exactly what went wrong last time. It says nothing a buyer cares about. It is a caveat about one measuring instrument, not a property of the product.

## The chain

The agent I work with keeps full transcripts of its sessions, so I could check how the sentence travelled instead of guessing. The logs I still have go back to mid-September; anything older is gone, so the first two pieces below are documents I can date but whose origin I can't trace.

<figure class="cap-fig">
<svg viewBox="0 0 600 470" role="img" aria-label="One evaluation finding fed two branches. On the reviewer branch the rule stayed with its audience. On the product branch a single presenter line in a demo runbook became the central message of a demo guide, verified by a read 82 minutes before the write, and then appeared in a CEO deck with no source found.">
<defs>
<marker id="cap-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
</defs>
<g font-family="ui-sans-serif,system-ui,sans-serif">
<text x="150" y="16" text-anchor="middle" font-size="11" fill="#5eead4" font-weight="600">RULE FOR REVIEWERS</text>
<text x="450" y="16" text-anchor="middle" font-size="11" fill="#fbbf24" font-weight="600">PRODUCT MESSAGING</text>
<rect x="170" y="30" width="260" height="56" rx="6" fill="#232332" stroke="#94a3b8"/>
<text x="300" y="52" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">Day 0 · a client's evaluation set</text>
<text x="300" y="72" text-anchor="middle" font-size="11" fill="#e2e8f0">labels derived from company names</text>
<rect x="20" y="130" width="260" height="74" rx="6" fill="#232332" stroke="#2dd4bf"/>
<text x="150" y="152" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+11 d · manual for human reviewers</text>
<text x="150" y="173" text-anchor="middle" font-size="11" fill="#5eead4">“Never decide what a company</text>
<text x="150" y="190" text-anchor="middle" font-size="11" fill="#5eead4">does from its name”</text>
<rect x="320" y="130" width="260" height="74" rx="6" fill="#232332" stroke="#f59e0b"/>
<text x="450" y="152" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+18 d · demo runbook for a prospect</text>
<text x="450" y="173" text-anchor="middle" font-size="11" fill="#fbbf24">one presenter line, one case:</text>
<text x="450" y="190" text-anchor="middle" font-size="11" fill="#fbbf24">“It didn't guess from the name”</text>
<rect x="20" y="270" width="260" height="74" rx="6" fill="#232332" stroke="#2dd4bf"/>
<text x="150" y="292" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+41 d · reviewer guide, client benchmark</text>
<text x="150" y="313" text-anchor="middle" font-size="11" fill="#5eead4">“The one rule. Never classify</text>
<text x="150" y="330" text-anchor="middle" font-size="11" fill="#5eead4">from the name”</text>
<rect x="320" y="270" width="260" height="74" rx="6" fill="#232332" stroke="#f59e0b"/>
<text x="450" y="292" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+57 d · internal demo guide</text>
<text x="450" y="313" text-anchor="middle" font-size="11" fill="#fbbf24">“The idea to get across:</text>
<text x="450" y="330" text-anchor="middle" font-size="11" fill="#fbbf24">it doesn't classify by name”</text>
<rect x="320" y="390" width="260" height="66" rx="6" fill="#232332" stroke="#f59e0b"/>
<text x="450" y="413" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+67 d · CEO deck</text>
<text x="450" y="434" text-anchor="middle" font-size="11" fill="#fbbf24">“The right one is rarely in the name”</text>
<path d="M235,86 L170,128" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5 4" fill="none" marker-end="url(#cap-arr)"/>
<path d="M365,86 L430,128" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5 4" fill="none" marker-end="url(#cap-arr)"/>
<path d="M150,204 L150,268" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#cap-arr)"/>
<path d="M450,204 L450,268" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#cap-arr)"/>
<path d="M450,344 L450,388" stroke="#64748b" stroke-width="1.5" stroke-dasharray="2 4" fill="none" marker-end="url(#cap-arr)"/>
<rect x="156" y="226" width="118" height="20" fill="#1a1a24"/>
<text x="160" y="240" font-size="10.5" fill="#e2e8f0">read → wrote 13 min later</text>
<rect x="456" y="226" width="122" height="20" fill="#1a1a24"/>
<text x="460" y="240" font-size="10.5" fill="#e2e8f0">read → wrote 82 min later</text>
<text x="460" y="371" font-size="10.5" fill="#94a3b8">no source found</text>
<text x="20" y="400" font-size="10.5" fill="#94a3b8">— verified in the transcripts</text>
<text x="20" y="418" font-size="10.5" fill="#94a3b8">- - older than the logs I keep</text>
<text x="20" y="436" font-size="10.5" fill="#94a3b8">··· not found</text>
</g>
</svg>
<figcaption>Two branches from one finding. On the left the rule stays with the people it was written for. On the right one line of a presenter's script becomes the thesis of a guide and then a slide. Solid arrows are a read followed by a write in the same session.</figcaption>
</figure>

On the reviewer side, eleven days after the finding there was a manual for the people who would adjudicate companies by hand: *The one rule: never decide what a company does from its name.* For that audience the rule is right. A month later a reviewer guide for a client benchmark was written in a session that had opened that manual twice. Thirteen minutes after the second read, the new guide said *The one rule. Never classify from the name*, almost word for word. Still the right audience.

On the product side, eighteen days after the finding, a demo runbook for a prospect had one line in the presenter's script, for one case: *It didn't guess from the name — it read the company's own filings.* About five weeks later I asked for a guide for an internal demo, with representative cases. The session read that runbook and, 82 minutes later, wrote a guide whose central callout said: *The idea to get across: it doesn't classify by name.* One line of a script had become the thesis.

Ten days after that came the CEO deck. There I couldn't find a source: nothing that entered that session before the card was written said it. The closest thing was a subagent that had read "its gold is name-derived" in a results document. It may be that by then the idea also sat in the general repertoire of "why this is hard" openers. The logs don't say.

I didn't ask for it anywhere. The requests were "adjust the manual", "a guide with representative cases", "a deck for the CEO".

## Why copying forward amplifies

Three things happen along the chain, and none of them is a bug on its own.

**The nearest document becomes the template.** To write a guide, the agent looks for the guide that already exists and starts from it. That is what I would want: it reuses structure, cases and tone that someone already approved. It also reuses claims without deciding them again.

**Each rewrite compresses, and compression promotes what is quotable.** A presenter line about one case is easy to lift; a careful paragraph about taxonomies is not. When a long runbook becomes a one-page guide, the memorable sentence survives and moves up.

**The audience doesn't travel with the sentence.** A rule written for people building a reference set reached a prospect, an internal demo and a CEO without anyone asking whether that reader cares.

Underneath there is something I recognised from [auditing my agent's memories](/en/blog/the-memory-that-was-true): what gets written down is what was hard to find out. The name-derived labels were the best-evidenced, most hard-won fact about evaluating this product, so they were all over the notes and documents. Being well documented made the idea look important. Whether it mattered to a buyer was never checked.

## Fixing it

My first correction, the day of the deck, went into the memory of the project where the deck was made. That is the natural place, and it isn't enough: sessions in the service's own repository never load it, and the documents that start the chain were still there to be read and copied.

The agent's proposal for the next step was the simple one: a prohibition everywhere a session can load it. *Don't sell the product on not classifying by name*, in the global instructions, in the service's memory and next to the runbook. I let it go ahead and tested it, and it worked. It was still the wrong fix. A prohibition covers only the sentence it names, so the next well-documented caveat starts the cycle again, and it is the kind of fix I have argued against before: in [an earlier experiment](/en/blog/what-has-already-happened) a plain-language prohibition left a failure at 96%, and [a role works better than a rule](/en/blog/a-role-not-a-rule) when the purpose is what tells the cases apart.

So I tested three fixes against doing nothing:

1. **Prohibition.** The rule above, wherever a session can load it.
2. **Role and product story.** No prohibitions. A short product story: what the reader decides with the service, why it is hard (506 ANZSIC classes, 923 NAICS Canada industries, 731 UK SIC codes; scattered and outdated evidence; each client's own risk policy) and the proof points with their sources. Wherever sessions load instructions, one line: write as someone explaining to this reader what they decide with the product, starting from the product story; older documents supply facts and cases. The reviewer guides now open with their purpose and audience.
3. **Role, product story and a corrected source.** The same, plus a revised runbook where the one presenter line is rewritten from the product story. The original stays in an archive folder.

Four tasks, none of them mentioning names: the "why this is hard" section of a brochure, a presenter guide built from the old runbook, the "problem" slide of a deck for the CEO, and a LinkedIn announcement. Five fresh sessions per task and condition, each one restored to its exact state before the next.

<figure class="cap-fig">
<svg viewBox="0 0 600 290" role="img" aria-label="Presenter guides written from the old runbook that still sold the product on not classifying by name, out of five per condition: five with no fix, zero with a prohibition, three with a role and a product story, zero once the runbook line was also corrected.">
<g font-family="ui-sans-serif,system-ui,sans-serif">
<line x1="70" y1="220" x2="580" y2="220" stroke="rgba(255,255,255,0.25)"/>
<line x1="70" y1="40" x2="580" y2="40" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3 4"/>
<text x="62" y="224" text-anchor="end" font-size="11" fill="#94a3b8">0</text>
<text x="62" y="44" text-anchor="end" font-size="11" fill="#94a3b8">5</text>
<text x="22" y="130" font-size="11" fill="#94a3b8" transform="rotate(-90 22 130)" text-anchor="middle">guides out of 5</text>
<rect x="100" y="40" width="70" height="180" fill="#f59e0b"/>
<text x="135" y="33" text-anchor="middle" font-size="12" fill="#fbbf24" font-weight="600">5/5</text>
<rect x="220" y="218" width="70" height="2" fill="#94a3b8"/>
<text x="255" y="211" text-anchor="middle" font-size="12" fill="#e2e8f0" font-weight="600">0/5</text>
<rect x="340" y="112" width="70" height="108" fill="#5eead4" fill-opacity="0.55"/>
<text x="375" y="105" text-anchor="middle" font-size="12" fill="#5eead4" font-weight="600">3/5</text>
<rect x="460" y="218" width="70" height="2" fill="#2dd4bf"/>
<text x="495" y="211" text-anchor="middle" font-size="12" fill="#5eead4" font-weight="600">0/5</text>
<text x="135" y="242" text-anchor="middle" font-size="12" fill="#e2e8f0">No fix</text>
<text x="255" y="242" text-anchor="middle" font-size="12" fill="#e2e8f0">Prohibition</text>
<text x="255" y="258" text-anchor="middle" font-size="10.5" fill="#94a3b8">names the sentence</text>
<text x="375" y="242" text-anchor="middle" font-size="12" fill="#e2e8f0">Role + story</text>
<text x="375" y="258" text-anchor="middle" font-size="10.5" fill="#94a3b8">from the reader</text>
<text x="495" y="242" text-anchor="middle" font-size="12" fill="#e2e8f0">+ corrected source</text>
<text x="495" y="258" text-anchor="middle" font-size="10.5" fill="#94a3b8">line rewritten</text>
</g>
</svg>
<figcaption>Presenter guides written from the old runbook that still sold the product on the name. The role moved the key message but not the copied line; correcting the runbook removed it without naming it anywhere.</figcaption>
</figure>

| Task | No fix | Prohibition | Role + story | + corrected source |
|---|---|---|---|---|
| Presenter guide from the old runbook | 5/5 | 0/5 | 3/5 | 0/5 |
| Brochure, "why this is hard" | 3/5 | 0/5 | 0/5 | — |
| CEO slide, "the problem" | 0/5 | 0/5 | 0/5 | — |
| LinkedIn announcement | 0/5 | 0/5 | 0/5 | — |

The corrected source only matters to tasks that read the runbook, so I ran it on that one.

The prohibition worked: none of the 20. It worked on the sentence it named, though, and in one demo guide it leaked into the deliverable as a note to the presenter: *don't say it doesn't classify by name*. A rule about what not to say can end up in what gets said.

The role and the product story worked on the message. All 20 sessions opened the product story, the brochures led with what the reader decides, and the five demo guides took their key message from it: *the AI proposes, controls decide, your analysts stay in charge*. What it didn't stop was copying. Three of the five demo guides still carried the runbook's line into the script for the first case, word for word, after reading the product story. A role decides where the message comes from; it doesn't stop an agent lifting a sentence from the template in front of it.

Correcting the source did. With that line rewritten in the runbook, none of the five guides used it, including two sessions that also opened the archived original.

Two tasks didn't discriminate: the CEO slide and the LinkedIn announcement came out clean in every condition, doing nothing included. The deck that failed was written from a different project, and the LinkedIn task was meant to show whether a role covers caveats a prohibition wouldn't name; with nothing leaking even without a fix, it can't. The limits are the usual ones: one repository, one model, five runs per cell, scored by me and not blind.

## Fix the source, give the message a home

Nothing in this chain was false. The finding was right, the reviewer rule was right, and every copy was a reasonable thing for an agent to do. What went wrong is that a finding has an audience, and when it is copied the audience isn't copied with it.

The prohibition was the easy fix, and it passed the test. The fix I kept has two parts, and neither is an instruction about what not to say. The message has a source of its own, written for the reader, so the agent no longer fills that slot with whatever is best documented. And the document being copied is corrected, because an agent that starts from a template carries its sentences forward whatever the instructions say. A prohibition answers the symptom you have already seen; the other two don't depend on having seen it first.
