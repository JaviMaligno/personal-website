---
title: "What gives an accidental paste away"
description: "Contradicting the user doesn't raise suspicion — it removes it entirely. 1,920 conversations to find out what makes a model consider you pasted into the wrong window, and two failures of the automated judge that only surfaced from hand-labelling."
pubDate: 2026-10-12
tags: ["AI", "Agents", "Evaluation", "Claude"]
lang: en
translationKey: what-gives-a-paste-away
heroImage: "/blog/what-gives-a-paste-away.png"
repoUrl: "https://github.com/JaviMaligno/llm-wrong-paste"
---

<style>
.pg-fig { margin: 2rem 0; }
.pg-fig svg { width: 100%; height: auto; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; }
.pg-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

In [the previous article](/en/blog/that-was-for-another-chat) I reported that no
model ever considers you might have pasted into the wrong window. Zero out of
twenty-four. You paste a stack trace into a conversation about bread and the
model debugs the stack trace.

That result left an uncomfortable question: **what if we never gave them the
chance?** None of the sixty-four pastes in that run was impossible to read as a
legitimate change of subject. A recipe pasted into a conversation about the
electricity bill *could* be something the user wants to ask about.

So I ran three more rounds to separate "they never consider it" from "there was
nothing to consider". One thousand nine hundred and twenty conversations — too
many to read end to end, so two judge models do the classifying and I hand-label
a blind sample from each round to know which of them to trust. Here is what came
out.

## Three levels of paste

The idea was to give them progressively clearer openings.

- **N0, neutral.** The original bank: text independent of the topic by
  construction, written without knowing what the topics were.
- **N1, with a signal inside.** The paste gives itself away without depending on
  the conversation: it is addressed to someone by name, it is cut off mid-sentence,
  it answers a question nobody asked here, or it presupposes an earlier
  conversation that doesn't exist.
- **N2, contradiction.** The paste clashes with what the user just said: another
  city, another date, another figure. This was the **ceiling**: the most
  detectable, the closest to a real accident.

And a new category in the rubric, because the one from the previous article
couldn't register what we were about to look for: **"entertains the possibility
of a mistake"**. Naming the topic change isn't enough. It has to question the
**intent**.

## The ceiling turned out to be the floor

<figure class="pg-fig">
<svg viewBox="0 0 600 224" role="img" aria-label="With a neutral paste, 6.6 per cent of responses entertain the possibility of a mistake; with a signal inside the paste it rises to 20.4 per cent; with a paste that contradicts the user it drops to zero.">
<text x="14" y="30" fill="#94a3b8" font-size="11" font-family="ui-monospace,monospace">ENTERTAINS THE POSSIBILITY OF A MISTAKE</text>
<text x="14" y="66" fill="#e2e8f0" font-size="13">N0 · neutral paste</text>
<rect x="250" y="53" width="66" height="18" rx="3" fill="#64748b"/>
<text x="326" y="67" fill="#94a3b8" font-size="13" font-family="ui-monospace,monospace">6.6%</text>
<text x="14" y="108" fill="#e2e8f0" font-size="13">N1 · signal inside</text>
<rect x="250" y="95" width="204" height="18" rx="3" fill="#2dd4bf"/>
<text x="464" y="109" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">20.4%</text>
<text x="14" y="150" fill="#e2e8f0" font-size="13">N2 · contradicts the user</text>
<rect x="250" y="137" width="2" height="18" rx="1" fill="#f59e0b"/>
<text x="262" y="151" fill="#fbbf24" font-size="13" font-family="ui-monospace,monospace">0%</text>
<line x1="250" y1="172" x2="560" y2="172" stroke="rgba(255,255,255,0.12)"/>
<text x="14" y="194" fill="#94a3b8" font-size="11">The level designed as the ceiling — the most detectable paste — gave zero out of ninety-five.</text>
<text x="14" y="210" fill="#94a3b8" font-size="11">Something else spikes there: seventy-seven of ninety-five just do the work, silently.</text>
</svg>
<figcaption>A signal inside the paste triples the doubt. A contradiction with what you just said eliminates it.</figcaption>
</figure>

The signal works: from **6.6% to 20.4%**, and the difference holds (`p = 0.006`).
With the right paste, one in five stops to consider that you made a mistake.

But **N2, the ceiling, gave zero out of ninety-five**. Less than the neutral bank.
And looking at what they do instead explains it: in N2 *executes silently* spikes
to seventy-seven of ninety-five. The model accepts the new fact, redoes its
advice, and never registers the clash.

There is a reading of that which I think is the best sentence in the experiment:
**a contradiction doesn't read as an accident, it reads as you having changed
your mind.** And going along with the user changing their mind is precisely what
an assistant is trained to do.

That reorders the question. What triggers doubt isn't that the paste is
*incompatible* with the conversation. It's that it's **foreign** to it: that it
carries inside the marks of having been written for somewhere else.

## So does similarity matter?

If what gives the paste away is coming from outside, the obvious hypothesis is
that the more it resembles the current topic, the less it shows. That's the
question the next run went to measure, sweeping the entire similarity axis.

The short answer is **no**.

<figure class="pg-fig">
<svg viewBox="0 0 600 214" role="img" aria-label="Between the less-similar half of the axis and the more-similar half, the doubt rate goes from 64.4 to 62.4 per cent; the 95 per cent confidence interval runs from minus 7.1 to plus 3.2 points and crosses zero.">
<text x="14" y="28" fill="#94a3b8" font-size="11" font-family="ui-monospace,monospace">DOUBT BY SIMILARITY TO THE CONVERSATION · n = 1,339</text>
<text x="14" y="62" fill="#e2e8f0" font-size="13">Less similar half</text>
<rect x="266" y="49" width="193" height="18" rx="3" fill="#2dd4bf"/>
<text x="469" y="63" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">64.4%</text>
<text x="14" y="98" fill="#e2e8f0" font-size="13">More similar half</text>
<rect x="266" y="85" width="187" height="18" rx="3" fill="#2dd4bf"/>
<text x="463" y="99" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">62.4%</text>
<line x1="14" y1="124" x2="586" y2="124" stroke="rgba(255,255,255,0.12)"/>
<text x="14" y="148" fill="#94a3b8" font-size="11" font-family="ui-monospace,monospace">DIFFERENCE AND 95% INTERVAL</text>
<line x1="180" y1="176" x2="420" y2="176" stroke="#64748b" stroke-width="1"/>
<line x1="300" y1="166" x2="300" y2="186" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3 3"/>
<text x="296" y="200" fill="#94a3b8" font-size="10" font-family="ui-monospace,monospace">0</text>
<line x1="207" y1="176" x2="358" y2="176" stroke="#f59e0b" stroke-width="3"/>
<circle cx="268" cy="176" r="4" fill="#fbbf24"/>
<text x="150" y="180" fill="#94a3b8" font-size="10" font-family="ui-monospace,monospace">−7.1</text>
<text x="364" y="180" fill="#94a3b8" font-size="10" font-family="ui-monospace,monospace">+3.2</text>
</svg>
<figcaption>The interval crosses zero. With 88% power to detect a nine-point drop, this isn't "we didn't see it": it's that there is no effect larger than about seven points.</figcaption>
</figure>

That last sentence is the part that cost something. The first version of this run
**also** came out flat, and I was about to call the axis closed. It wasn't:
computing the power *afterwards* — which is exactly when you discover it should
have come first — showed that design had an **11%** chance of detecting the
effect I had myself declared relevant. A flat result at that power doesn't say
"there is no effect". It says "we wouldn't have seen one".

Redoing the design so that a null would mean something forced three changes, and
none of them was the one I expected:

- **Run a single model.** The behaviour only exists in one: across the earlier
  runs `claude-opus-5` gives 55% doubt on the signal arm, `gpt-5.6-sol` gives 9%,
  and **`gpt-5.6-luna` gives zero out of ninety-six**. Spending a third of the
  budget on a model that never doubts doesn't buy information: it buys zeros.
- **More distinct stimuli, not more conversations.** With eight topics and two
  lengths there are sixteen starting conversations, and every point on the axis
  was seeing the same sixteen. Repeating them adds nothing; forty more artefacts
  had to be written.
- **Drop the follow-up turns.** The category is decided in the first response to
  the paste, and the two turns after it accounted for 72% of the bill. They'll be
  generated separately when they're needed.

With that: 1,344 conversations and 88% power. And the answer is still no —
similarity doesn't predict whether the model will doubt you.

## The finding that wasn't in the script

At this scale you can't read every conversation, so two judge models do the
classifying. But for each round I sit down and label a handful myself, blind,
without seeing what they said. It's the dullest part of the experiment and it's
the part that produced the two findings below.

The first: **the judge was wrong in one specific direction.** In the first round
it handed out the doubt category far too freely — thirty times where I counted
thirteen — and always in the same direction, never the other way. A systematic
error like that doesn't show up in the final percentage: it shows up when you put
its labels next to yours.

The second surfaced while labelling the last round, and it runs deeper. **The
categories aren't mutually exclusive.** A response can flag the topic jump **and**
adopt the role the paste describes — it routinely does — and the rubric makes you
pick one of two true things. That's a defect in the instrument, not in the model,
and it had been sitting inside three rounds without anyone noticing.

Measuring it produced something bigger than I expected. Re-judging one hundred
and fifty conversations with a two-axis rubric — does it acknowledge the
discontinuity? and what does it do with the paste? — **one hundred and
twenty-four land in a combination the old rubric can't express**.

But the flaw wasn't where I was looking. "Flags the jump and also adopts the
role", the case that made me suspicious in the first place, appears **exactly
once** in a hundred and fifty. What was missing was an entire box nobody had
named.

<figure class="pg-fig">
<svg viewBox="0 0 600 240" role="img" aria-label="Denying a premise of the paste appears in sixty of one hundred and fifty responses, and the old rubric scattered it across all seven of its categories: sixteen to executes silently, thirteen to adopts the role, ten to asks what to do, nine to confabulated bridge, nine to flags the jump, eight to weighs and dismisses.">
<text x="14" y="28" fill="#94a3b8" font-size="11" font-family="ui-monospace,monospace">"WHAT YOU'RE TAKING FOR GRANTED DOESN'T EXIST" · 60 OF 150</text>
<rect x="14" y="44" width="150" height="34" rx="4" fill="#232941" stroke="#93a4e8"/>
<text x="30" y="65" fill="#93a4e8" font-size="12.5">denies a premise</text>
<text x="180" y="59" fill="#94a3b8" font-size="11">the old rubric had no box</text>
<text x="180" y="74" fill="#94a3b8" font-size="11">for this, so it scattered it</text>
<text x="180" y="89" fill="#94a3b8" font-size="11">across all seven:</text>
<text x="30" y="122" fill="#e2e8f0" font-size="12">Executes silently</text>
<rect x="250" y="111" width="80" height="14" rx="2" fill="#f59e0b"/><text x="340" y="122" fill="#fbbf24" font-size="12" font-family="ui-monospace,monospace">16</text>
<text x="30" y="144" fill="#e2e8f0" font-size="12">Adopts the role</text>
<rect x="250" y="133" width="65" height="14" rx="2" fill="#f59e0b" opacity="0.85"/><text x="340" y="144" fill="#fbbf24" font-size="12" font-family="ui-monospace,monospace">13</text>
<text x="30" y="166" fill="#e2e8f0" font-size="12">Asks what to do</text>
<rect x="250" y="155" width="50" height="14" rx="2" fill="#f59e0b" opacity="0.7"/><text x="340" y="166" fill="#fbbf24" font-size="12" font-family="ui-monospace,monospace">10</text>
<text x="30" y="188" fill="#e2e8f0" font-size="12">Confabulated bridge</text>
<rect x="250" y="177" width="45" height="14" rx="2" fill="#64748b"/><text x="340" y="188" fill="#94a3b8" font-size="12" font-family="ui-monospace,monospace">9</text>
<text x="30" y="210" fill="#e2e8f0" font-size="12">Flags the jump</text>
<rect x="250" y="199" width="45" height="14" rx="2" fill="#2dd4bf"/><text x="340" y="210" fill="#5eead4" font-size="12" font-family="ui-monospace,monospace">9</text>
<text x="30" y="232" fill="#e2e8f0" font-size="12">Weighs and dismisses</text>
<rect x="250" y="221" width="40" height="14" rx="2" fill="#2dd4bf" opacity="0.8"/><text x="340" y="232" fill="#5eead4" font-size="12" font-family="ui-monospace,monospace">8</text>
</svg>
<figcaption>One behaviour, scattered across all seven categories of the taxonomy. It's the most frequent reaction of all, and the rubric had no name for it.</figcaption>
</figure>

The missing behaviour is **denying a premise of the paste**: "I have no record of
that conversation", "I'm not Tomás", "we haven't agreed on that format in this
thread". It isn't flagging that the topic changed. It isn't doubting that you
meant to send it. It's a third thing: **the model doesn't correct you, it
corrects the world the paste takes for granted**.

And it's the most frequent reaction in the run: forty out of every hundred. The
taxonomy in the previous article missed it because it came from twenty-four
conversations, and in twenty-four it barely shows up four times.

## What I take from this

**About the models.** What makes them consider your mistake isn't that the text
clashes with the conversation, but that it carries signals of having been written
for somewhere else. Contradicting you doesn't give you away: it obeys you. And
there's a way of reacting — denying what the paste assumes — that is the most
common of all and wasn't even on the map.

**About measuring with automated judges.** Delegating the classification to a
model is the only thing that makes a thousand-conversation run feasible, and it's
also what leaves you not knowing what you're counting. The two errors I found — a
judge inflating one category in a single direction, and a rubric that forces a
choice between two things that are both true — show up in no aggregate metric.
They show up from sitting down and labelling sixty conversations by hand, then
comparing.

**And about not concluding more than you've earned.** The first sweep of the axis
came out flat and meant nothing: it had an 11% chance of detecting the effect I
had myself declared relevant. A flat result like that doesn't say "no effect", it
says "we wouldn't have seen one". And a hypothesis the small run hinted at — that
longer conversations produce more doubt — **reversed** when measured with fourteen
times the data.

Neither of those is visible by looking at the data. They're visible by working
out beforehand how much you'd need to see in order to believe what you're about
to say.

What's left is the part that gives the series its name: what happens **after**,
when the user types *"sorry, that was meant for another chat"*. That's Phase 2,
and that's the next article.

---

*Code, data and rubrics: [llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste).
All 1,920 conversations, both judges' verdicts and the human labels are in the
repository, failures included.*
