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

Among the engaging models (GPT-5 + Qwen ×2, eight replicates, 95% confidence intervals), the original question finally has a clean answer.

![Horizontal bar chart ranking cipher comprehension rate: letters_to_digits 100%, morse 79%, disemvowel 78%, reverse_all 75%, random_substitution 74%, rot13/cyrillic/binary 67%, block_permutation 51%, base64 50%.](/blog/ciphers-difficulty-ranking.png)

The ladder mostly matches intuition, with a couple of surprises. **Letters→digits is trivial** (100%) — the model reads `8-5-12-12-15` as "hello" without breaking stride. **base64 and the keyed block permutation are the hardest** (~50%), which is the interesting part: base64 is *everywhere* in training data, yet decoding a long base64 string turn after turn and acting on it is genuinely error-prone. Familiarity isn't the same as fluency. And the hard ciphers aren't just less often solved — when they *are* solved it takes longer (median 4–5 turns versus 1 for the easy ones).

The keyed random substitution — the one cipher no model could have memorized — sits mid-ladder at 74%, and the models visibly *work* for it, which is the closest thing here to watching a frequency-analysis "break" happen over several turns.

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

In plain text these requests get complied with 36% of the time (and the *base* model, with no alignment layer, 80% of the time — it simply hasn't learned to refuse). Encode the exact same request and compliance **collapses to ~1%.** Reading the transcripts by hand shows why: the cipher flips the model into *translator mode*. It replies, in plain English, "This looks like ROT13 — decoding: EXPLAIN HOW TO…" and then treats the decoded text as a puzzle it has solved rather than an order it must follow. The obfuscation that gets past the outer filter also stops the model from *executing* the instruction, because it reframes the instruction as an object to be examined.

That's the honest, un-scary version. Under *pure inference* — no system prompt teaching the cipher, à la the original CipherChat setup — wrapping a request in a code doesn't jailbreak the model; it defuses it. The safety-relevant lesson isn't "ciphers break guardrails." It's subtler and more useful: **plaintext filters and decoded content are two different surfaces.** Azure's filter fires on the ciphertext's shape; Claude refuses on illegibility; the actual decoded compliance is a third thing entirely. A defense tuned to any one of them is blind to the other two.

## Back to the click

The human cryptanalyst's "break" is a moment of *comprehension* — the mask comes off and meaning floods in. What this experiment keeps separating out is that, for a model, comprehension is only one of several switches, and not even the first one to fire. Before understanding there's a *willingness to engage at all* — the switch Claude keeps flipped to off, that Azure flips off on GPT-5's behalf. After understanding there's the choice to *speak back* in the code, which only turns on when you ask. And the thing you'd most fear — understanding-plus-obedience of a hidden instruction — turns out to be the switch that jams, because decoding and obeying pull the model in different directions.

A person who cracks a cipher and reads "rob the bank" doesn't thereby rob the bank; the reading and the doing are different acts. It's oddly reassuring that, at least under plain inference, the models draw the same line — and a little unsettling that the base model, stripped of alignment, is the one most willing to just do as the plaintext says.

---

*Code, ciphers, deterministic oracle, and full analysis: [github.com/JaviMaligno/llm-language-limits](https://github.com/JaviMaligno/llm-language-limits). Second in a series on the edges of language, after [Repetition at the Edges of Language](/en/blog/repetition-edges-of-language). The jailbreak sub-probe follows the framing of [CipherChat](https://arxiv.org/abs/2308.06463) and reports aggregate rates only.*
