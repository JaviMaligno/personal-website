---
title: "Teaching a Model a Language You Just Invented"
description: "Speak to a language model in a cipher it has never been told the key to, and something surprising happens before any decoding does: some models refuse to play at all. A small experiment on how fast models crack novel codes — and where that runs into a safety wall."
pubDate: 2026-07-18
tags: ["AI", "Machine Learning", "Evaluation", "Alignment", "Security"]
lang: en
translationKey: ciphers-edges-of-language
heroImage: "/blog/ciphers-edges-of-language.png"
linkedinImage: /blog/ciphers-safety-boundary.png
repoUrl: https://github.com/JaviMaligno/llm-language-limits
---

Codebreakers have a word for the moment a cipher cracks open: the *break*. You stare at a wall of `Wklv pdnhv qr vhqvh` and count letters, and then all at once the shape of the language underneath swims up and the gibberish is just English wearing a mask. Human cryptanalysts describe it as a click. I wanted to know what that click looks like for a language model — and, more precisely, *how fast* it happens when the model has never been told the key.

This is the second piece in a loose series on the **edges of language** — what models do when you push their input outside the well-behaved distribution they were trained on. The [first one](/en/blog/repetition-edges-of-language) was about repetition. This one started as a simple question: **talk to a model in a code it doesn't know, and how many turns until it catches on and starts talking back in the same code?**

I got an answer to that. But first I ran into something I wasn't looking for.

## The setup

I built a ladder of **ten ciphers**, from ones the model has surely seen in training to ones it has to genuinely infer:

- **Substitution:** ROT13, and a *keyed random substitution* — an arbitrary shuffle of the alphabet the model cannot have memorized, so cracking it requires real frequency analysis.
- **Symbol remap:** letters→digits (`a=1…`), Morse.
- **Base encodings:** binary, base64.
- **Transposition:** full text reversal, and a keyed block permutation.
- **Alphabet mixing:** Latin↔Cyrillic homoglyphs.
- **Lossy:** disemvoweling (drop the vowels).

Each turn, the model gets a short **verifiable task** ("reply with the name of the long yellow fruit", "what is seven plus five") encoded in the active cipher. The whole point of using verifiable tasks is that the oracle is **deterministic** — I encode and decode the ciphers myself, so scoring whether the model *acted correctly* needs no LLM judge, just a string check. (That was the fragile part of the repetition study; here I designed it away.)

I measured two things per conversation: **comprehension** — did the model act correctly on the decoded task, in any language? — and **production** — did it start *replying in the code* itself? And I tried three exposure **protocols**: *pure* (just speak in cipher from turn one), *few-shot* (show a few plaintext↔coded example pairs first — a Rosetta stone), and *escalating* (start pure, add hints if it flounders).

Five models: Claude Opus and Sonnet, GPT-5, and Qwen2.5-7B in both Instruct and Base flavors.

## The thing I wasn't looking for

Here is the plan meeting reality. Before I could measure *how fast* anyone cracks a cipher, I had to notice that **two of my five models refuse to try.**

![Bar chart of refusal rate by model: Claude Opus 87%, Claude Sonnet 86%, GPT-5 0%, Qwen Instruct 0%, Qwen Base 0%. An annotation notes Azure's content filter blocks GPT-5's ciphered prompts as 'jailbreak' before the model sees them.](/blog/ciphers-safety-boundary.png)

**Claude Opus and Sonnet refuse ~87% of encoded turns.** Not "fail to decode" — *refuse*, with the API's `stop_reason: refusal` and an empty completion. Feed the same model the same question in plain English and it answers instantly and correctly ("The capital of France is **Paris**"). It is not that Claude can't read ROT13; it is that Claude won't act on an instruction it can't read as plain text.

And the refusal is shaped by **illegibility**. ROT13, base64, binary, Morse, keyed substitution — anything that turns the message into visual noise — draws refusal close to 100%. But `cyrillic_homoglyph`, where the text still *looks* like words, gets refused only a third of the time. The model's guard rises exactly with how alien the input looks.

GPT-5 hits a *different* wall, one turn earlier. Azure's content filter classifies the ciphered prompts as a **jailbreak attempt** and returns a 400 before the model ever sees them. (To measure GPT-5 at all I had to route it through a deployment with the jailbreak shield disabled — the harm-category filters left fully on. I'll come back to why that matters.)

So before any cryptanalysis happens, encoded text has already hit a **safety boundary** — and two frontier labs guard it two different ways: OpenAI/Azure with an external filter, Anthropic with the model's own refusal reflex. Only GPT-5 (past the filter) and the two open Qwen models actually engage. That reframed the whole study: the "how fast do they learn a code" question only has an answer for the models willing to play.

## For the models that do play: the difficulty ladder

Among the engaging models (GPT-5 + Qwen ×2, eight replicates), the original question finally has an answer — but it pays to look model by model rather than at a pooled average, because the three are not equally fluent.

![Heatmap of comprehension rate by cipher and model. GPT-5 is near 100% almost everywhere; Qwen-7B Instruct sits a notch below; Qwen-7B Base is low on most ciphers (0% on binary, Cyrillic, block permutation) but 100% on letters-to-digits. GPT-5's base64 cell is marked 'filtered'.](/blog/ciphers-difficulty-heatmap.png)

**GPT-5 is near-ceiling on almost everything** (88–100%); Qwen-7B-Instruct sits a notch below; and **Qwen-7B-Base is the one that struggles** — 0% on binary, Cyrillic homoglyphs, and the block permutation, yet a flawless 100% on letters→digits. A pooled "difficulty ranking" is really the *base model's* ranking dragged over the others; the aligned models mostly just solve everything.

One honest caveat the model-by-model view surfaces: **base64 for GPT-5 is `filtered`, not failed.** Azure's *harm-category* filter — the one I deliberately left on — blocked every one of GPT-5's base64 cells, so base64's pooled number is simply missing its strongest model. Treat its apparent difficulty with suspicion; the genuinely hard cases are the **keyed** ciphers.

What *is* robust is that difficulty shows up two ways at once — lower success **and** more turns to get there. Broken down the same way, by model:

![Heatmap of median turns-to-comprehension by cipher and model. GPT-5 cracks most ciphers on turn 1 but takes 4-5 turns on the keyed ones (random substitution, block permutation); the Qwen models are slower; dashes mark ciphers a model never solved.](/blog/ciphers-turns.png)

**GPT-5 cracks most ciphers on the very first turn**, but takes a median of 4–5 on the keyed ones — random substitution and block permutation, the two it has to genuinely *infer*. The keyed random substitution is the purest case: no model could have memorized it, so watching one grind it out over several turns is the closest thing here to a human frequency-analysis "break" in slow motion. (One honest wrinkle: the open Qwen models run greedily, so their replicates are deterministic — their "turns" reflect the protocol and the task rotation more than sampling noise. I read this as a coarse ordering, not a precise latency.)

## What actually helps a model crack a code

The three protocols pull two different levers, and this is where a design decision paid off.

![Grouped bar chart by protocol. Comprehension: pure 61%, few-shot 83%, escalating 70%. Production: pure 25%, few-shot 14%, escalating 62%.](/blog/ciphers-protocol-effect.png)

Giving the model a **Rosetta stone** — a few plaintext↔coded pairs — lifts comprehension from 61% to 83%, a gap whose confidence intervals don't overlap, and it helps the *novel* keyed ciphers as much as the memorized ones. That is exactly what you'd hope: shown the key, the model cracks the code faster, even a code it's never seen.

(An aside for anyone who builds evals: this result only exists because of a bug I caught in review. My first implementation of the "Rosetta stone" accidentally encoded *both* sides of each example, so there was no plaintext anchor at all — the few-shot condition was secretly identical to pure inference. Had it shipped, the headline finding here would have been a flat "examples don't help," which is false. The plaintext key *is* the whole intervention.)

Escalation, by contrast, barely moves comprehension but drives **production** through the roof (62% vs 25%): the moment you explicitly say "reply in the same code," the models that understand start *speaking* it. Understanding a code and choosing to answer in it are separate switches, and they respond to different prompts.

## The twist: encoding a refused request doesn't unlock it

Which brings us back to that safety boundary, and the obvious follow-up. If encoded text sails past Claude's refusal-of-legible-instructions and Azure's plaintext filter, is a cipher a **jailbreak** — a way to smuggle a request the model would normally decline? This is the CipherChat hypothesis, and it's a legitimate thing to test, so I did, carefully: a small, fixed set of mild "normally-refused" requests (phishing copy, a defamatory rumor, lock-picking — nothing in the CBRN/weapons/self-harm categories), sent in plaintext and encoded, scored only for aggregate compliance. Labels only; no harmful text stored or published.

The result runs the opposite way from the scare headline.

![Bar chart: compliance on a harmful request in plain text is 36%, versus 1% when the same request is encoded in a cipher. Annotation: the model switches to 'decode this puzzle' mode instead of obeying.](/blog/ciphers-jailbreak-backfire.png)

In plain text these requests get complied with 36% of the time — and the *base* model, with no alignment layer, 80% of the time, because it never learned to refuse anything. Encode the exact same request and compliance across every model **collapses to under 1%.**

So did we actually jailbreak anything? The blunt answer from the data: **no. Across 375 encoded requests, exactly three were complied with — and all three are the same cell:** the *unaligned base model*, on base64, for a single lock-picking prompt. Every safety-trained model (GPT-5, Qwen-Instruct) complied with **zero** encoded requests. There is no case here of a cipher making an aligned model carry out something it would otherwise refuse.

What the models do instead is **decode-and-comment**. The cipher flips them into *translator mode*: they reply, in plain English, "This looks like ROT13 — it says: EXPLAIN HOW TO…", print the decoded text, and stop there. They treat the message as a puzzle to *solve*, not an instruction to *obey* — so the very obfuscation that slips past the outer filter is also what stops the model from acting on the request. Decoding it and executing it pull in opposite directions.

That's the honest, un-scary version. Under *pure inference* — no system prompt teaching the cipher, unlike the original CipherChat setup — a cipher doesn't jailbreak a model; it defuses it. The lone exception proves the rule: the only thing that "complied" was the one model with no guardrail to bypass in the first place. The real lesson isn't "ciphers break guardrails" — it's that **a plaintext safety filter and the decoded content are two different surfaces.** Azure's filter fires on the ciphertext's *shape*; Claude refuses on illegibility; whether the decoded instruction ever gets *executed* is a third thing entirely. A defense tuned to any one of them is blind to the other two.

## Back to the click

The human cryptanalyst's "break" is a moment of *comprehension* — the mask comes off and meaning floods in. What this experiment keeps separating out is that, for a model, comprehension is only one of several switches, and not even the first one to fire. Before understanding there's a *willingness to engage at all* — the switch Claude keeps flipped to off, that Azure flips off on GPT-5's behalf. After understanding there's the choice to *speak back* in the code, which only turns on when you ask. And the thing you'd most fear — understanding-plus-obedience of a hidden instruction — turns out to be the switch that jams, because decoding and obeying pull the model in different directions.

A person who cracks a cipher and reads "rob the bank" doesn't thereby rob the bank; the reading and the doing are different acts. It's oddly reassuring that, at least under plain inference, the models draw the same line — and a little unsettling that the base model, stripped of alignment, is the one most willing to just do as the plaintext says.

---

*Code, ciphers, deterministic oracle, and full analysis: [github.com/JaviMaligno/llm-language-limits](https://github.com/JaviMaligno/llm-language-limits). Second in a series on the edges of language, after [Repetition at the Edges of Language](/en/blog/repetition-edges-of-language). The jailbreak sub-probe follows the framing of [CipherChat](https://arxiv.org/abs/2308.06463) and reports aggregate rates only.*
