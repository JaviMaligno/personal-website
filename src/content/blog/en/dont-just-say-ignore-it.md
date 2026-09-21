---
title: "Don't just say \"ignore it\""
description: "Two months ago I guessed that telling a model to ignore an accidental paste might leave more residue than saying nothing. 480 paired conversations later: it does, it roughly sextuples it, and the fix is not asking harder."
pubDate: 2026-10-15
tags: ["AI", "Agents", "Evaluation", "Claude"]
lang: en
translationKey: dont-just-say-ignore-it
heroImage: "/blog/dont-just-say-ignore-it.png"
repoUrl: "https://github.com/JaviMaligno/llm-wrong-paste"
---

<style>
  .ign-fig { margin: 2.5rem 0; }
  .ign-fig svg { width: 100%; height: auto; display: block; }
  .ign-fig figcaption {
    color: #94a3b8; font-size: 0.9rem; line-height: 1.5;
    margin-top: 0.75rem; text-align: left;
  }
</style>

At the end of [the first article in this series](/en/blog/that-was-for-another-chat) I wrote down a guess I could not test:

> My suspicion, which the data has not tested yet, is that saying it may leave more residue than saying nothing at all.

It is the kind of sentence that is cheap to write and expensive to check. This article is the check. It is also the last of the three I promised, and it turns out the guess was right — with one correction that I did not see coming and that I think is the more useful half.

## The shape of the experiment

The awkward part of measuring a repair is that you need two conversations that are identical up to the moment of repair, and differ only in what the user types next. Otherwise you are comparing repairs *and* the accidents that preceded them.

So I did not run new conversations. I reused the 1,339 reactions from [the previous run](/en/blog/what-gives-a-paste-away) — prefix, pasted block and the model's response to it, already paid for and already judged — and hung four different continuations off each one. Same prefix, same artefact, same paste, same reaction. The only thing that varies is the sentence the user types after:

- **(a)** nothing. The user carries on with the original topic as if the paste had not happened.
- **(b)** *"Ignore it."*
- **(c)** *"Ignore it, that was for another chat. Let's carry on with the electricity bill."*
- **(d)** *"Yes, let's talk about that."*

That last one is the control, and it is the reason the design is worth anything. (b) and (d) are **opposite instructions about the same block of text**: one says *this doesn't belong here*, the other says *it does*. If a model answered both the same way, it would not be reading the user's intent at all — it would be reacting to the presence of the text. I put it in expecting to catch exactly that.

What I measure is **leakage**: whether any of the pasted artefact's distinctive entities — the names, the products, the places that belong to the other conversation and to nothing here — reappear in the model's later replies. The entities are known because the paste bank is mine.

120 bases, four arms each: 480 conversations, all on Claude Opus 5.

## The result

<figure class="ign-fig">
  <svg viewBox="0 0 600 224" role="img" aria-label="Saying &quot;ignore it&quot; produces entity leakage in 19.2 per cent of conversations, against 3.3 per cent when the user says nothing at all. Explaining where to go next brings it back down to 8.3 per cent, and saying &quot;yes, let's talk about that&quot; gives the lowest rate of the four at 2.5 per cent.">
    <rect x="0" y="0" width="600" height="224" fill="#1a1a24"/>
    <rect x="12" y="10" width="576" height="204" rx="8" fill="none" stroke="rgba(255,255,255,0.1)"/>
    <text x="32" y="38" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" letter-spacing="1.2">THE PASTE LEAKS INTO WHAT COMES NEXT</text>

    <text x="32" y="72" fill="#e2e8f0" font-size="13">(a) say nothing</text>
    <rect x="232" y="61" width="50" height="14" rx="2" fill="#64748b"/>
    <text x="292" y="73" fill="#94a3b8" font-family="ui-monospace,monospace" font-size="12">3.3%</text>

    <text x="32" y="106" fill="#f8fafc" font-size="13" font-weight="600">(b) "ignore it"</text>
    <rect x="232" y="95" width="292" height="14" rx="2" fill="#f59e0b"/>
    <text x="534" y="107" fill="#fbbf24" font-family="ui-monospace,monospace" font-size="12" font-weight="600">19.2%</text>

    <text x="32" y="140" fill="#e2e8f0" font-size="13">(c) + where to go</text>
    <rect x="232" y="129" width="126" height="14" rx="2" fill="#2dd4bf"/>
    <text x="368" y="141" fill="#5eead4" font-family="ui-monospace,monospace" font-size="12">8.3%</text>

    <text x="32" y="174" fill="#e2e8f0" font-size="13">(d) "yes, let's talk"</text>
    <rect x="232" y="163" width="38" height="14" rx="2" fill="#2dd4bf"/>
    <text x="280" y="175" fill="#5eead4" font-family="ui-monospace,monospace" font-size="12">2.5%</text>

    <line x1="32" y1="192" x2="568" y2="192" stroke="rgba(255,255,255,0.08)"/>
    <text x="32" y="207" fill="#94a3b8" font-size="11.5">The instruction to discard the text produces six times the residue of not mentioning it.</text>
  </svg>
  <figcaption>120 conversations per arm, all four hanging off the same paste and the same reaction to it. Only the user's next sentence differs.</figcaption>
</figure>

Because the arms are paired, the right test is on the conversations where two arms disagree. All three declared comparisons survive Holm correction:

<figure class="ign-fig">
  <svg viewBox="0 0 600 214" role="img" aria-label="All three paired comparisons are statistically significant after Holm correction: saying ignore it adds 15.8 points of leakage over saying nothing, explaining where to go next removes 10.8 points, and saying ignore it adds 16.7 points over saying yes let's talk about that.">
    <rect x="0" y="0" width="600" height="214" fill="#1a1a24"/>
    <rect x="12" y="10" width="576" height="194" rx="8" fill="none" stroke="rgba(255,255,255,0.1)"/>
    <text x="32" y="36" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" letter-spacing="1.2">PAIRED DIFFERENCE, 95% INTERVAL</text>

    <line x1="348" y1="50" x2="348" y2="166" stroke="#64748b" stroke-dasharray="3 3"/>
    <text x="348" y="182" fill="#94a3b8" font-size="10.5" text-anchor="middle">0</text>

    <text x="32" y="76" fill="#e2e8f0" font-family="ui-monospace,monospace" font-size="12">(b) vs (a)</text>
    <line x1="399" y1="72" x2="505" y2="72" stroke="#f59e0b" stroke-width="3"/>
    <circle cx="452" cy="72" r="4.5" fill="#fbbf24"/>
    <text x="515" y="76" fill="#fbbf24" font-family="ui-monospace,monospace" font-size="11">+15.8</text>

    <text x="32" y="114" fill="#e2e8f0" font-family="ui-monospace,monospace" font-size="12">(c) vs (b)</text>
    <line x1="233" y1="110" x2="318" y2="110" stroke="#2dd4bf" stroke-width="3"/>
    <circle cx="276" cy="110" r="4.5" fill="#5eead4"/>
    <text x="225" y="114" fill="#5eead4" font-family="ui-monospace,monospace" font-size="11" text-anchor="end">&#8722;10.8</text>

    <text x="32" y="152" fill="#e2e8f0" font-family="ui-monospace,monospace" font-size="12">(b) vs (d)</text>
    <line x1="409" y1="148" x2="507" y2="148" stroke="#f59e0b" stroke-width="3"/>
    <circle cx="458" cy="148" r="4.5" fill="#fbbf24"/>
    <text x="517" y="152" fill="#fbbf24" font-family="ui-monospace,monospace" font-size="11">+16.7</text>

    <text x="32" y="198" fill="#94a3b8" font-size="11">No interval touches zero. Holm-corrected p: 0.0011, 0.0036, 0.0003.</text>
  </svg>
  <figcaption>Percentage points of leakage, measured within conversation. The arms are the ones in the first figure. The middle row is the one worth keeping: adding a destination to the same instruction removes about eleven points.</figcaption>
</figure>

## The control answered a question I hadn't asked

I expected (d) to be the embarrassing one. If *"ignore it"* and *"yes, let's talk about that"* produced the same behaviour, the honest conclusion would have been that the model is not processing the instruction, just reacting to the text being there.

It came out the other way, and hard. The instruction to **keep** the pasted text gives the lowest leakage of all four arms — 2.5%. The instruction to **discard** it gives the highest — 19.2%. The gap is 16.7 points and it is the most significant of the three.

So the model reads intent perfectly well. That was never the problem. The problem is the one the white-bear experiments have been making about people since the eighties: **to ignore something you have to hold it.** Asking for the deletion is what puts it back in play.

And (c) closes the argument from the other side. Same instruction to ignore, but with somewhere to go — *"let's carry on with the electricity bill"* — and the rate falls from 19.2% to 8.3%. What repairs the conversation is not requesting the forgetting. It is supplying the replacement.

## Where the residue actually lives, and why I'm hedging

This is the part where I have to take something back off the table.

<figure class="ign-fig">
  <svg viewBox="0 0 600 240" role="img" aria-label="All of the leakage happens in the model's reply to the repair itself. In the two later turns every arm sits at or near zero, including the arm that leaks 19.2 per cent in the first reply.">
    <rect x="0" y="0" width="600" height="240" fill="#1a1a24"/>
    <rect x="12" y="10" width="576" height="220" rx="8" fill="none" stroke="rgba(255,255,255,0.1)"/>
    <text x="32" y="36" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" letter-spacing="1.2">LEAKAGE BY TURN</text>

    <text x="196" y="58" fill="#94a3b8" font-size="10.5" text-anchor="middle">reply to repair</text>
    <text x="352" y="58" fill="#94a3b8" font-size="10.5" text-anchor="middle">next turn</text>
    <text x="474" y="58" fill="#94a3b8" font-size="10.5" text-anchor="middle">turn after</text>

    <text x="32" y="88" fill="#e2e8f0" font-size="12.5">(a) nothing</text>
    <rect x="160" y="78" width="12" height="12" rx="2" fill="#64748b"/>
    <text x="180" y="88" fill="#94a3b8" font-family="ui-monospace,monospace" font-size="11">3.3%</text>
    <text x="330" y="88" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0.0%</text>
    <text x="452" y="88" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0.8%</text>

    <text x="32" y="122" fill="#f8fafc" font-size="12.5" font-weight="600">(b) "ignore it"</text>
    <rect x="160" y="112" width="66" height="12" rx="2" fill="#f59e0b"/>
    <text x="234" y="122" fill="#fbbf24" font-family="ui-monospace,monospace" font-size="11" font-weight="600">19.2%</text>
    <text x="330" y="122" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0.0%</text>
    <text x="452" y="122" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0.0%</text>

    <text x="32" y="156" fill="#e2e8f0" font-size="12.5">(c) + destination</text>
    <rect x="160" y="146" width="26" height="12" rx="2" fill="#2dd4bf"/>
    <text x="194" y="156" fill="#5eead4" font-family="ui-monospace,monospace" font-size="11">7.5%</text>
    <text x="330" y="156" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0.0%</text>
    <text x="452" y="156" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0.8%</text>

    <text x="32" y="190" fill="#e2e8f0" font-size="12.5">(d) "yes, let's talk"</text>
    <rect x="160" y="180" width="9" height="12" rx="2" fill="#2dd4bf"/>
    <text x="177" y="190" fill="#5eead4" font-family="ui-monospace,monospace" font-size="11">2.5%</text>
    <text x="330" y="190" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0.8%</text>
    <text x="452" y="190" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0.8%</text>

    <line x1="32" y1="206" x2="568" y2="206" stroke="rgba(255,255,255,0.08)"/>
    <text x="32" y="222" fill="#94a3b8" font-size="11.5">The residue is an immediate echo, not a drift. But see the caveat: the next turn is a hard question.</text>
  </svg>
  <figcaption>The effect is concentrated entirely in the model's reply to the repair. What the design cannot separate is how much of the two zeros belongs to the residue fading and how much to the question that follows being very specific.</figcaption>
</figure>

All of the leakage is in the reply to the repair itself. The model names the other conversation's entities **in the act of promising to forget them** — *"understood, I'll set aside the thing about Marta's invoice"* — and then, two turns later, nothing.

That makes the finding smaller in scope and sharper in mechanism. It is not drift. It is an echo.

But I am not going to claim the residue simply decays, because my own design gets in the way. The turn immediately after the repair is a literal arithmetic question with one correct answer, identical across all arms. That is a turn which dominates what the model can say. A zero there is partly a property of the instrument, not of the phenomenon. The defensible sentence is *"the residue does not survive a specific question"* — which is still useful advice, just not the same claim.

## The thing that didn't work

I wanted a second dependent variable: does the contaminated conversation get the *task* wrong? Every topic in the bank got a verifiable question with exactly one right answer, written before anything ran.

Opus got 120/120, 120/120, 120/120 and 119/120.

So I made them harder — multi-step chains, each with a classic trap of its domain: applying the electricity levy and VAT in sequence rather than adding them into one 26%, charging the bank's commission on the euros rather than the yen, forgetting the water already in the preferment. I re-ran the clean, no-paste control to calibrate.

24 out of 24. All eight topics, every repetition.

That is a null result and I am reporting it as one: in this model, accidental-paste contamination does not reach a verifiable arithmetic task. What it leaves open is whether it would reach a task that depends on the *context* rather than the calculation — and that is a redesign, not an adjustment, because it breaks the rule I set that the question must carry all its own data.

## What I'd actually do

- **Don't send "ignore it" on its own.** It is the worst of the four things I tested, by a factor of six over saying nothing.
- **Say where to go instead.** *"Ignore that, wrong window — back to the invoice"* costs you one clause and removes about eleven points of echo. This is the one recommendation here with a corrected p-value behind it.
- **Saying nothing is fine.** If you can just carry on with your question, do. It sits at 3.3%, statistically indistinguishable from the best arm.
- **Don't read this as lasting contamination.** The echo showed up in the immediate reply and was gone by the next specific question. If your next message is concrete, you are probably fine either way.

One more thing, which is the most concrete lead this leaves and which I am not claiming, only reporting: the leakage after *"ignore it"* was almost double when the model had **not** already flagged the paste as odd — 25.0% against 13.3%. The one that noticed nothing is the one that handles being told to forget worst.

## Two ways I nearly fooled myself

Both are the same shape, and it is the shape this whole series keeps running into: **a well-formed number that reads like a finding when it is an artefact.**

The first was a gate I had written to stop the experiment sizing itself on a dead variable — *if arm (a) barely leaks, there's no range for a repair to move.* It was written assuming repairs **reduce** leakage. This effect goes the other way, so a floor in (a) is the best case, not the worst: it is the clean background the effect stands against. The gate was measuring correctly and concluding backwards, and it declared the finding unmeasurable at precisely the moment the pilot found it.

The second: the power formula refuses to run when the base rate is exactly zero, and it is right to refuse — a normal approximation over a rate pinned to the floor describes nothing. But my report was recording that refusal as *"no sample size achieves the declared power"*, which is a statement about the experiment rather than about the formula. Published as written, it would have closed the phase on a conclusion the data does not support.

Neither was caught by a test. Both were caught by going back and asking what each number was actually a number *of*.

---

*This closes the three-article series that started with [an accidental paste nobody questioned](/en/blog/that-was-for-another-chat) and continued with [what gives one away](/en/blog/what-gives-a-paste-away). All 480 conversations, the four repair arms, both judges' verdicts and the failures are in [llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste).*
