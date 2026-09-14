---
title: "Sorry, That Was For Another Chat"
description: "I pasted the wrong thing into 24 conversations on purpose and read every reply by hand. Not one model considered that it might have been a mistake. What varies is not whether they notice — it's how much work they do on something you never asked for."
pubDate: 2026-09-21
tags: ["AI", "Agents", "Evaluation", "Claude"]
lang: en
translationKey: that-was-for-another-chat
heroImage: "/blog/that-was-for-another-chat.png"
repoUrl: "https://github.com/JaviMaligno/llm-wrong-paste"
---

<style>
.wp-fig { margin: 2rem 0; }
.wp-fig svg { width: 100%; height: auto; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.wp-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

You have done this. There is something in your clipboard that belonged to a different conversation — you copied it for another reason, or you forgot it was there at all — and it ends up pasted into a chat where it makes no sense. Most of the time you catch it before sending. Sometimes you don't.

There is a newer version of the same mistake, and if you work with agents you have lived it this week: twenty sessions open in parallel, each one waiting on something, and you answer the wrong one. The reply was true — just not there.

I was setting up an experiment about exactly this when it happened to me. An agent had just put an API key on my clipboard, and in the same breath suggested a shell command to save it. I copied the command to run it. The command overwrote the key. The file ended up containing the text of the command instead of the secret.

That is the whole phenomenon in one move, and it is worth being precise about why it is interesting.

## This is not prompt injection, and it is not a topic change

Four research lines sit next to this and none of them cover it.

**Irrelevant context injected into a task prompt** is very well studied — [GSM-IC](https://arxiv.org/pdf/2302.00093) and its successor [GSM-DC](https://arxiv.org/abs/2505.18761) — but single-turn, on arithmetic, where the noise is part of the problem statement rather than an accident.

**Deliberate topic switches** are covered by [Beyond Continuity](https://arxiv.org/pdf/2605.09268), which measures whether a model notices the user has *pivoted*. Its conclusion travels well: models drag stale context along even with explicit cues. But there the user meant to change the subject.

**Getting lost in multi-turn** is [Laban et al.](https://arxiv.org/abs/2505.06120): a 39% average drop, and the memorable finding that once a model takes a wrong turn it does not recover. There the failure is under-specification, not a stray paste.

**Instructions to ignore previous content** are almost always framed adversarially — [Nevermind](https://arxiv.org/pdf/2402.03303), instructional distraction, context-ignoring attacks.

The accidental paste is none of these. Its defining property is that **it is ambiguous**. That block of text could be three different things, and the model has no way to tell them apart:

<figure class="wp-fig">
<svg viewBox="0 0 600 236" role="img" aria-label="Three possible readings of a pasted block — clipboard junk, a deliberate topic change, or relevant context the user forgot to explain. In all 24 conversations read, every model chose the deliberate topic change.">
<rect x="200" y="10" width="200" height="36" rx="6" fill="#1a1a24" stroke="#2dd4bf" stroke-width="1.5"/>
<text x="300" y="33" text-anchor="middle" fill="#5eead4" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">a pasted block</text>
<path d="M265 46 L110 88" stroke="#64748b" stroke-width="1.5" fill="none"/>
<path d="M300 46 L300 88" stroke="#f59e0b" stroke-width="2.5" fill="none"/>
<path d="M335 46 L490 88" stroke="#64748b" stroke-width="1.5" fill="none"/>
<rect x="20" y="88" width="180" height="56" rx="6" fill="#1a1a24" stroke="rgba(255,255,255,0.18)" stroke-width="1"/>
<text x="110" y="111" text-anchor="middle" fill="#e2e8f0" font-size="13">clipboard junk</text>
<text x="110" y="131" text-anchor="middle" fill="#94a3b8" font-size="11.5">"ignore it"</text>
<rect x="210" y="88" width="180" height="56" rx="6" fill="#1a1a24" stroke="#f59e0b" stroke-width="2"/>
<text x="300" y="111" text-anchor="middle" fill="#fbbf24" font-size="13">a deliberate pivot</text>
<text x="300" y="131" text-anchor="middle" fill="#94a3b8" font-size="11.5">"let's talk about this"</text>
<rect x="400" y="88" width="180" height="56" rx="6" fill="#1a1a24" stroke="rgba(255,255,255,0.18)" stroke-width="1"/>
<text x="490" y="111" text-anchor="middle" fill="#e2e8f0" font-size="13">context I forgot</text>
<text x="490" y="131" text-anchor="middle" fill="#94a3b8" font-size="11.5">"you need this to answer"</text>
<text x="110" y="188" text-anchor="middle" fill="#64748b" font-size="30" font-family="ui-monospace,'JetBrains Mono',monospace">0</text>
<text x="300" y="188" text-anchor="middle" fill="#fbbf24" font-size="30" font-family="ui-monospace,'JetBrains Mono',monospace">24</text>
<text x="490" y="188" text-anchor="middle" fill="#64748b" font-size="30" font-family="ui-monospace,'JetBrains Mono',monospace">0</text>
<text x="300" y="218" text-anchor="middle" fill="#94a3b8" font-size="12">of the 24 conversations I read</text>
</svg>
<figcaption>The reading is a choice the model cannot avoid making. In the twenty-four conversations I read, it was never once resolved towards "you probably made a mistake".</figcaption>
</figure>

## The setup, briefly

Eight deliberately unrelated topics — a house move, training for a 10K, choosing a school, baking bread, a trip to Japan, a balcony vegetable garden, an electricity bill, buying a camera. A simulated user drives the conversation for either 2 or 10 turns. Then a block of text is pasted in raw, with no preamble, exactly as a real misfire arrives.

The pasted blocks come from a bank of 64 clipboard artefacts — a recipe, an SSH config, a stack trace, meeting minutes, a shopping list, a SQL migration, a job ad, a prompt from another chat. **They were written without any knowledge of the conversation topics.** That constraint matters more than it looks: if you generate a paste that is "moderately related to a conversation about bread", you have built a designed distractor, which is what GSM-DC already studies. Here similarity is an emergent property of crossing topic × artefact, measured afterwards with embeddings, not a dial I set.

Three models: two sizes of the same GPT-5.6 family — sol, the larger, and luna, the smaller — and Claude Opus 5. Twenty-four conversations with a paste, three controls without one. I read all of them, in full, by hand.

## Nobody thinks you made a mistake

Zero out of twenty-four.

Not one reply contains anything like *"was this meant for this conversation?"*. The two behaviours I would have bet on before running it — flagging it as a probable error, and silently ignoring it to carry on with the topic — **did not appear a single time**.

What I got instead was six behaviours, and the axis of variation is not detection. It is how much unrequested work the model does.

<figure class="wp-fig">
<svg viewBox="0 0 600 252" role="img" aria-label="Six observed behaviours across 24 conversations: performs the implied task silently 14, asks what to do without questioning the fit 5, flags the topic jump 2, reasons about the relation and dismisses it 1, invents a bridge 1, adopts the pasted prompt's role 1.">
<text x="8" y="35" fill="#e2e8f0" font-size="12.5">Performs the implied task, silently</text>
<rect x="320" y="22" width="200" height="17" rx="3" fill="#f59e0b" opacity="1.0"/>
<text x="560" y="35" fill="#fbbf24" font-size="13" font-family="ui-monospace,monospace">14</text>
<text x="8" y="69" fill="#e2e8f0" font-size="12.5">Asks what to do — never if it fits</text>
<rect x="320" y="56" width="71" height="17" rx="3" fill="#f59e0b" opacity="0.75"/>
<text x="560" y="69" fill="#fbbf24" font-size="13" font-family="ui-monospace,monospace">5</text>
<text x="8" y="103" fill="#e2e8f0" font-size="12.5">Flags the jump, then complies</text>
<rect x="320" y="90" width="29" height="17" rx="3" fill="#2dd4bf" opacity="1.0"/>
<text x="560" y="103" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">2</text>
<text x="8" y="137" fill="#e2e8f0" font-size="12.5">Weighs the relation, dismisses it</text>
<rect x="320" y="124" width="14" height="17" rx="3" fill="#2dd4bf" opacity="1.0"/>
<text x="560" y="137" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">1</text>
<text x="8" y="171" fill="#e2e8f0" font-size="12.5">Invents a bridge to the old topic</text>
<rect x="320" y="158" width="14" height="17" rx="3" fill="#64748b" opacity="1.0"/>
<text x="560" y="171" fill="#94a3b8" font-size="13" font-family="ui-monospace,monospace">1</text>
<text x="8" y="205" fill="#e2e8f0" font-size="12.5">Adopts the pasted prompt's role</text>
<rect x="320" y="192" width="14" height="17" rx="3" fill="#64748b" opacity="1.0"/>
<text x="560" y="205" fill="#94a3b8" font-size="13" font-family="ui-monospace,monospace">1</text>
<line x1="320" y1="232" x2="545" y2="232" stroke="rgba(255,255,255,0.12)"/>
<text x="8" y="246" fill="#94a3b8" font-size="11">Amber: never mentions the jump · Teal: mentions it · Grey: one-offs</text>
</svg>
<figcaption>Nineteen of twenty-four replies never acknowledge that anything changed. The interesting minority is small, and it is where the good behaviour lives.</figcaption>
</figure>

### It just does the work

Fourteen of twenty-four take the paste as the new request and deliver. A conversation about a balcony vegetable garden receives a Rust panic, and the reply opens:

> The problem is the `unwrap()` on the key lookup. Replace it with a contextual error that says which field is missing.

A conversation about an electricity bill receives a pumpkin curry recipe, and gets a genuinely good answer about frying the curry paste in the thick cream from the top of the coconut tin instead of in oil. Not one word about the bill.

### It asks what to do — but never whether it belongs

Five replies ask for clarification, which sounds like the good outcome until you read what they ask:

> Would you like me to turn it into more polished release notes, translate it into English, or draft a launch message?

The question is about the **output format**. Nothing in it questions whether a changelog for a parsing library belongs in a conversation about buying a camera. All five came from the gateway models; Opus never did this once.

### It notices, and complies anyway

Two replies name the jump. One of them is the best behaviour in the whole run:

> I see you've changed the subject and pasted a Prometheus alert rule. Here's a quick review in case you want to check it, **and at the end I'll come back to the garden, which I owe you.**

It notices, it helps, and it commits to returning. It still never entertains that the paste was an accident — but it is the only reply that treats the previous conversation as something it has a debt to.

### The invented bridge

One reply builds a plausible link and runs with it. The topic was training for a 10K; the paste was a job ad for a night-shift baker:

> A quick note in case it's the first option, **which is the one that connects to what we were talking about**: a 2am-to-10am shift doesn't stop you preparing a 10K in April, but it does force you to reorganise the plan.

The advice is good. The connection is invented. Both things are true at once, and that is exactly what makes this failure mode expensive: nothing in the reply looks wrong.

### The pasted prompt that ate the conversation

One artefact type deserves its own paragraph. Five of the sixty-four artefacts are prompts from another chat — the thing you copy when you are reusing an instruction. One of them landed in a conversation about moving house:

> *You are a style editor. Follow the Vilaseca Style Manual and nothing else. Flag sentences over thirty words…*

Opus took the role. It correctly noted that the text to edit was missing and that it did not know the cited manual. And then, for lack of anything else to work on, **it applied the four style criteria to its own previous answers in the conversation**, in a table, quoting itself and proposing corrections.

This is the point where the accidental paste brushes against prompt injection, and the difference is worth stating plainly: there is no adversary here. There is a clipboard.

## The one that got it right

One reply, out of twenty-four, did the thing I would want. The topic was an electricity bill; the paste was a notice from a residents' association about lift repairs:

> This text is a notice from the residents' association, **not from your electricity bill**. […] If you received it along with the building's monthly charge, those €87 could explain why that charge is higher, **but they don't affect your electricity bill** unless they've been included by mistake.

It spots the mismatch, explicitly considers whether there could be a real relation, and dismisses it with a reason. That is the opposite of the invented bridge: a link considered and rejected. It matters because it proves the ceiling exists — this is not a capability problem.

## The split by family, on eight conversations each

The six behaviours are not spread evenly across the three models, and the
contrast is sharp enough to be worth writing down even though the numbers are
tiny:

| | Does the work | Asks about format | Mentions the jump | Other |
|---|---|---|---|---|
| GPT-5.6 sol | 5 | **3** | 0 | — |
| GPT-5.6 luna | 5 | **2** | 0 | 1 (the good one) |
| Claude Opus 5 | 4 | **0** | **2** | 1 bridge, 1 role |

Every single "what would you like me to do with this?" came from the two GPT
models, and neither of them ever mentioned that the subject had changed. Opus
never asked about format once, and it is the only model that ever named the jump
— as well as the only one that invented a bridge, and the only one that took on
the pasted prompt's role.

Two different default postures, in other words: one asks you to pick an output
format, the other comments on what just happened and then gets on with it. Which
is more useful probably depends on what you were actually doing.

**Eight conversations per model.** That is not a finding, it is a pattern worth
testing properly, and it is now the first thing I want out of the next round.

## What I am not claiming

Twenty-four conversations, one paste each, no preregistration, and the design deliberately rotates topics and lengths so that nothing is measured with any statistical power. **This is an observation, not a measurement.** I cannot tell you a detection rate, and I cannot tell you whether similarity between the paste and the conversation changes anything — across these 24 the acknowledgements land at 0.23, 0.26, 0.26 and 0.37 cosine, and the silent ones spread across the entire range.

The next article runs a proper grid, with enough conversations per cell to talk about rates. If it contradicts this one, I will say so there.

## What to do the next time it happens to you

From reading all of it, the practical advice is less about the models and more about what you can expect from them:

- **Assume it will be taken seriously.** The default reading is "you meant this". If you paste a stack trace into a conversation about bread, you will get debugging.
- **A clarifying question is not a detection.** "What would you like me to do with this?" means it has already accepted the topic change and is asking about formatting.
- **Watch for the bridge.** The expensive failure is not the model doing the wrong task — you notice that immediately. It is the model weaving the stray content into the thing you actually care about, plausibly, in a reply where nothing looks out of place.
- **If the paste is an instruction, expect it to be followed.** A prompt from another chat is not read as data. It is read as a role.

The second half of this — what happens *after* you say "ignore that, wrong window" — is the next experiment. My suspicion, which the data has not tested yet, is that saying it may leave more residue than saying nothing at all.

---

*This is the first of three articles. The next one measures the curve; the third one is about the repair. Related: [Your Agent Doesn't Know What's Internal](/en/blog/internal-context-leakage), on context going the other way — internal material leaking into things it shouldn't.*
