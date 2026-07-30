---
title: "Confident About Text It Cannot Read"
description: "A safety filter gave a base64 string a medium self-harm severity. Two judges scoring the same ciphered replies agreed worse than chance. A base model wrote fluent cipher it had never understood. Three systems producing confident verdicts about text they cannot read — and one conclusion of mine that didn't survive the full run."
pubDate: 2026-08-01
tags: ["AI", "Machine Learning", "Evaluation", "Alignment", "Security"]
lang: en
translationKey: confident-about-unreadable-text
heroImage: "/blog/confident-about-unreadable-text.png"
linkedinImage: /blog/ciphers-chatgpt-banana.png
repoUrl: https://github.com/JaviMaligno/llm-language-limits
linkedinLinks:
  - label: "CipherChat, the framing this sub-probe follows"
    url: "https://arxiv.org/abs/2308.06463"
---

Take the string `cmVwbHkgd2l0aCB0aGUgc2luZ2xlIHdvcmQgYmFuYW5h`. It is base64, and it decodes to *reply with the single word banana*. Send it to GPT-5 through the Azure gateway and you do not get back `banana`. You get an HTTP 400, and a filter verdict that names its reason:

```
jailbreak:                 { detected: true,  filtered: false }
self_harm:                 { filtered: true,  severity: "medium" }
hate / sexual / violence:  safe
```

A self-harm classifier looked at a string it could not parse and assigned it a **medium severity**. Not "unknown", not an abstention, not a low-confidence flag — a specific, confident, wrong verdict about a request for the word *banana*.

The string is not some exotic edge case, either. Paste it into ChatGPT and the answer comes straight back:

![Screenshot of a ChatGPT conversation. The user message is the base64 string cmVwbHkgd2l0aCB0aGUgc2luZ2xlIHdvcmQgYmFuYW5h and the assistant's entire reply is the single word: banana.](/blog/ciphers-chatgpt-banana.png)

Different stack, different filters, no drama — it decodes the request and answers it. That contrast is the point. The severity verdict is not a fact about the request; it is a property of the ensemble sitting in front of one particular deployment, an ensemble that had to say *something* about a string it could not read, and said `medium`.

That is the shape of everything worth reporting from this experiment. I have now finished the full version of the cipher sweep I [wrote about in the previous post](/en/blog/ciphers-edges-of-language) — 696 conversations, 6,960 model turns, ten ciphers the models were never taught. Three separate systems in it turned out to do the same thing: produce a confident, structured judgement about text they cannot read. One is that safety filter. One is a base model writing fluent cipher it does not understand. And one is an LLM judge — the one my own earlier conclusion was resting on.

So this post starts with the correction.

## What didn't survive

The [cipher post](/en/blog/ciphers-edges-of-language) ended on a reassuring note. Its sub-probe on robustness reported that encoding a normally-refused request made compliance *collapse* — 36% in plain text against about 1% under ciphers — and I drew the obvious conclusion: a cipher doesn't unlock a refused request, it defuses it. The models flip into translator mode, decode the message, and comment on it instead of obeying.

That post hedged the claim in several directions, and I still think the hedges were right. But the direction of the headline was wrong, for a reason that is worth more than the conclusion it replaced.

**The measurement was broken in a specific way.** That first sub-probe judged the *decoded* view of every reply unconditionally. So when a model decoded a harmful request and then refused in plain English — the single most common thing that happens — the judge took that plain-English refusal and ran it back through the cipher before scoring it. It saw noise and filed it as "garbled". Every letter-level cipher condition returned garbled by construction, which pushes both compliance and refusal toward zero and leaves an encouraging-looking near-1%.

The corrected probe judges whichever view actually reads as English, records which channel the model answered in, and stores the judge's identity for every cell. Then it does the thing the first run didn't: it has a **second, independent judge** re-label a sample, so I can ask whether the labels mean anything before reading a rate off them.

They mostly don't. And where they do, the answer runs the other way.

![Bar chart of inter-judge agreement (Cohen's kappa) for three models, split by plain-text and ciphered replies. GPT-5: 1.00 plain text, 0.35 ciphered. Qwen-7B Instruct: 0.66 plain text, minus 0.17 ciphered. Qwen-7B Base: 0.74 plain text, minus 0.05 ciphered. The negative region is shaded and labelled 'worse than chance'.](/blog/ciphers-full-judge-agreement.png)

On plain text, two independent judges agree about what happened, for every model. On ciphered replies they agree on GPT-5 — and on the two 7B models they agree **worse than chance**: kappa of −0.17 and −0.05. Per cipher the same split shows up, from 0.71 on full reversal down to 0.002 on the keyed substitution.

That is not a small caveat about noisy data. It means that for those models, in that condition, the standard CipherChat-style instrument does not measure anything. Their "uplift" comes out strongly negative — the base model falls from 80% compliance in plain text to somewhere between 0% and 20% under every cipher — and **that negative number is not evidence that ciphers protect them.** A 7B model answering an encoded harmful request usually emits something that is neither a refusal nor a fulfilment, and "refused / complied / garbled" are plain-text categories that don't carve up that output space. A compliance the judge fails to recognise in half-decoded text gets filed as garbled, which lowers the rate mechanically. Whichever judge you happened to run is doing the work.

**On GPT-5, where the judges do agree, a bypass appears.** In plain text it refused all 30 harmful cells — a clean 100%, with both judges in perfect agreement. Under ciphers, two distinct prompts were complied with under two distinct ciphers (letters→digits and full reversal) after being refused in plain text. Each reproduced across replicates, and both judges independently labelled all four cells as compliances — including the judge that isn't GPT-5, which matters, because a judge scoring its own outputs would be biased toward reading them as refusals.

I want to be exact about how much that is and isn't. It is an **existence result, never a rate**. Ten prompts cannot estimate a frequency; every confidence interval here includes zero; 0.067 is literally two prompts. What it establishes is that refusal is not a property of the request's meaning alone — the same meaning, wrapped in a cipher, crossed a boundary it did not cross in plain text. Note also which ciphers did *not* do it: ROT13 and base64, the two GPT-5 decodes most fluently, and the keyed cipher it has to work out. Whatever is going on, it isn't "harder to read means easier to bypass".

The whole sub-probe used a deliberately mild subset of **AdvBench**, with CBRN, weapons, CSAM and self-harm categories excluded, and it stores labels only — no harmful prompt or model completion is published, here or in the repo.

## The part the judges never touched

Everything above is the appendix. The main experiment is the reason I trust it at all, because **its core metrics use no LLM judge**.

Each turn, the model gets a short verifiable instruction — *reply with the single word banana*, *what is seven plus five* — encoded in the active cipher, and I check two things programmatically. **Comprehension**: did it *act* correctly on the decoded instruction, in whatever language it answered? A task oracle decides that, deterministically. **Production**: did it write its reply in the code? The inverse cipher decides that, by decoding the reply and checking the result reads as English while the raw reply doesn't.

Ten ciphers, three exposure protocols, eight replicates, three models: 696 conversations. Two of the ciphers — a random alphabet substitution and a block permutation — are **keyed per run**, so their mapping cannot have been memorised in training. Those are the only ones that speak to inference rather than recognition.

Most of what that machinery found, [the earlier post](/en/blog/ciphers-edges-of-language) already reported from the pilot, and the full sweep confirms it rather than revising it: the keyed ciphers are the genuinely hard ones, three plain-text↔coded example pairs lift comprehension sharply, and models only start *replying* in code when you ask them to. Two details are worth adding. Pooled across models, Morse, disemvoweling and ROT13 have a **median of one turn whenever they get solved at all** — recognition is instant or it never comes, with almost nothing in between, which is the opposite of the several-turn grind the keyed ciphers produce. And base64's row rests on two models rather than three, because Azure rejected GPT-5's entire base64 block: the rejection from the top of this post is also a hole in the results table.

The genuinely new thing needs every model's *production* rate side by side.

### The two abilities dissociate in opposite directions

![Grouped bar chart comparing comprehension and production rates per model, with confidence intervals. GPT-5: 97% comprehension, 24% production. Qwen-7B Instruct: 83% and 20%. Qwen-7B Base: 36% comprehension, 56% production — the only model that produces more than it understands.](/blog/ciphers-full-dissociation.png)

That the two are separable was already the earlier post's finding — escalation drives production up without moving comprehension. What the full sweep shows is sharper: they don't just separate, they **invert**. GPT-5 understands 97% of cells and answers in plain English anyway, writing back in code in only 24% of them. Qwen-7B Base does the reverse: it understands 36% and writes in code 56% of the time. It is the only model here that produces more than it understands.

The base model's half of that needs a caveat, and it is the third system on my list. In three cipher cells — binary, Cyrillic homoglyphs, block permutation — it produced in-code output while **never once** acting correctly on the decoded task. That is not adopting the code. It is continuing the surface pattern of the prompt, which is exactly what a completion model without instruction tuning should do. Fluent cipher, zero comprehension. Reported as mimicry, not as speaking the language.

## The thing they have in common

A filter that cannot parse base64 assigns it a medium self-harm severity. A judge that cannot read a half-decoded reply files it as garbled and quietly deflates a rate. A base model that has understood nothing produces flawless cipher. In all three cases the system's output has the *form* of a judgement — a severity, a label, a fluent answer — and none of the content one would need behind it.

That is a specific, unglamorous failure mode, and it is a different story from the one I told in the previous post. The reassuring reading I published wasn't wrong because the models turned out to be more fragile than I thought. It was wrong because I read a number off an instrument that was, in that condition, measuring nothing — and the artefact happened to point somewhere comfortable.

So the practical lesson isn't about ciphers. If you are replicating CipherChat-style work, or any evaluation where an LLM judge scores text the model may have mangled, **compute inter-judge agreement per subject and per condition before you report a single rate**. On this material that one extra judging pass is the entire difference between a measurement and a confident artefact. It cost me one run to find out, and I'd already published the artefact.

The defensive version of the same lesson: a plain-text safety filter and the decoded instruction are two different surfaces. The same ensemble over-blocks an innocuous encoded request about a banana *and* let two harmful ones through on a frontier model. Tuning for one of those surfaces tells you very little about the other.

---

*Code, ciphers, the deterministic oracle, and the full method: [github.com/JaviMaligno/llm-language-limits](https://github.com/JaviMaligno/llm-language-limits) — with a provenance record in `docs/PUBLICATION_FREEZE.md` (model ids, served versions, sampling settings, cipher seed, and a sha256 for every data file, stamped with the generating commit) and 172 tests. This finishes the cipher study that began in [Teaching a Model a Language You Just Invented](/en/blog/ciphers-edges-of-language), itself the second piece in a series on the edges of language after [Repetition at the Edges of Language](/en/blog/repetition-edges-of-language). The robustness sub-probe follows the framing of [CipherChat](https://arxiv.org/abs/2308.06463) and reports aggregate labels only.*
