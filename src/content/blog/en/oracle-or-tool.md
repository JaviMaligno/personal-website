---
title: "Oracle or tool"
description: "Plenty of people who use AI every day run into walls that aren't the AI's. What they lack is a criterion of their own, and they treat the model as an oracle. What changes when you use it as a tool, and how to write your criterion down so you only argue with it once."
pubDate: 2026-11-08
tags: ["AI", "Critical Thinking", "ChatGPT", "Productivity"]
lang: en
translationKey: oracle-or-tool
heroImage: "/blog/oracle-or-tool.png"
---

A friend asked me for advice recently. She loves AI and uses it a lot, mostly for drawing and writing. This time she wanted ChatGPT to put together a diet plan. She already had an intuitive idea of what she was after and was torn between two options: paleo or keto.

ChatGPT gave her the usual answer: if you go to the gym, you need carbohydrates. With an explanation, mechanisms and even some nods to the evidence. It may well be right. But an answer that comes well argued isn't thereby correct, or the only option.

Talking it through with her, I saw something more useful than the diet. The walls she runs into aren't the AI's limits. They're hers, and running into them is good for exactly that: seeing where they are. What happens to her happens to most people who use AI casually. In a company, those users are almost everyone.

## The first answer is the conventional one

A language model tends to give you whatever is repeated most. It learned from what has been written, and what has been written most about nutrition is the mainstream recommendation. When a question has a broad, solid consensus, that's fine. But for a personal decision with several defensible options, the default answer is a starting point, not a verdict.

There's a detail almost nobody outside the field knows, and it explains much of the problem. The model answers first with what it has closest to hand: what it learned in training, or the document you gave it. It can search the web, read studies and compare sources, but often it only does so if you ask. The first answer is usually the most repeated one, not the best supported.

And it shows more in the free versions. The paid tool is better than the free one, and this is where you see it: generic answers that don't fit what you asked are far more common in the free version, for me and for my friend. In the paid one it happens much less.

## You don't lack knowledge, you lack a criterion

The first thing my friend told me was that she doesn't know about nutrition. Or biochemistry, or how muscle responds to training. My answer was that she doesn't need to. If you already had to know the answer to use AI, it would be no use to you.

What you do need is a method. By what criterion do you decide whether to accept something? What's enough for you to take it as true? That question comes before any fact.

I have one for essays ([I wrote about it here](/en/blog/writing-an-essay-with-ai-codex-vs-claude-code)) and another for researching the Bible and ontology ([it's in a public repository](https://github.com/JaviMaligno/god-ontology)). In both I hit the same thing: the AI mixes kinds of knowledge. It doesn't cleanly separate a historical fact from a theological interpretation, or know which evidence counts for each. I have to tell it that, or argue it out the first time.

That method has a name: epistemology, the branch of philosophy that studies how we know what we know. You don't need to study it. A few notions are enough, even intuitive ones, and the main one is that not all knowledge rests on the same kind of evidence:

- **Formal.** Logic and mathematics. It rests on proof. A valid argument doesn't hand you the truth by itself: it guarantees that if the premises are true, so is the conclusion.
- **Experimental.** What can be reproduced under controlled, bounded conditions. It rests on experiments others can repeat.
- **Observational.** Open systems that can't be isolated or repeated: a society, an economy, a population's health over decades. You observe them, compare groups and measure correlations, but you don't control everything that matters.
- **Historical.** What already happened and can't be repeated. It rests on forensic-style evidence: remains, documents, testimony and the convergence of several independent traces.
- **Personal.** What depends on you: your goals, your values and your own experience, meaning whether it works for you and whether you can keep it up. General evidence informs it, but yours counts too.

AI tends to mix these categories up. It presents an observed correlation as if it were an experimental result, or dismisses a well-documented historical fact because it can't be reproduced in a lab. With that clear, four questions cover almost everything:

1. **What kind of claim is this?**
2. **What evidence counts for that kind, and which is it giving me?**
3. **What is this particular answer based on?** Not in general: this one.
4. **What serious alternatives are there, and how do they differ?**

Nutrition shows well why it matters. It is mostly observational knowledge: what happens on a diet over years comes from following populations, not from a lab. Mechanisms, on the other hand, are studied with experiments: what a hormone does, how a nutrient is used. And each needs the other. A demonstrated mechanism doesn't tell you how much it weighs in real life until observation corroborates it, because other mechanisms can cancel it out. And an observed correlation without a mechanism to explain it may be tangled up with other causes.

There is also historical evidence that tends to be dismissed: how humans have fed themselves throughout history and how they evolved with that food. It settles nothing on its own, but I use it as a tiebreaker when there's no consensus: when in doubt, what would you eat in your natural state? I wrote a book on how to evaluate knowledge without waiting for consensus, [Science Catch-Up](/en/publications).

Choosing between paleo and keto is, in the end, a personal decision. No oracle can answer it for you. What AI can do is gather the evidence on each option, tell you what kind it is and where there's no agreement. You make the decision, with your goals in front of you, and your own experience puts it to the test: whether it agrees with you and whether you can keep it up.

## Oracle or tool

The second limitation I saw is the one this article is named after. My friend uses AI as an oracle: she asks, gets an answer, and accepts or rejects it whole. Using it as a tool is something else: asking it to justify what it says, to give you the source, to look for alternatives and compare them.

<style>
.oot-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.oot-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.oot-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

<figure class="oot-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="As an oracle, the question goes to the model and a single answer comes out to accept or reject. As a tool, the model searches sources, compares alternatives and explains the evidence, and your criterion makes the decision.">
  <defs>
    <marker id="oot-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <text x="145" y="24" text-anchor="middle" fill="#fbbf24" font-size="15" font-weight="700">Oracle</text>
  <text x="445" y="24" text-anchor="middle" fill="#5eead4" font-size="15" font-weight="700">Tool</text>
  <line x1="300" y1="12" x2="300" y2="290" stroke="rgba(255,255,255,0.1)" stroke-width="1"/>
  <g fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#oot-a)">
    <path d="M145,74 V100"/>
    <path d="M145,148 V174"/>
    <path d="M145,222 V246"/>
    <path d="M445,74 V100"/>
    <path d="M390,148 V172"/>
    <path d="M500,148 V172"/>
    <path d="M390,214 C390,232 430,236 438,244"/>
    <path d="M500,214 C500,232 460,236 452,244"/>
  </g>
  <rect x="70" y="40" width="150" height="34" rx="6" fill="none" stroke="rgba(255,255,255,0.25)"/>
  <text x="145" y="62" text-anchor="middle" fill="#e2e8f0" font-size="13">Your question</text>
  <rect x="70" y="104" width="150" height="44" rx="6" fill="none" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="145" y="124" text-anchor="middle" fill="#e2e8f0" font-size="13">The model</text>
  <text x="145" y="140" text-anchor="middle" fill="#94a3b8" font-size="11">what it already knows</text>
  <rect x="70" y="178" width="150" height="44" rx="6" fill="none" stroke="rgba(255,255,255,0.25)"/>
  <text x="145" y="198" text-anchor="middle" fill="#e2e8f0" font-size="13">One answer</text>
  <text x="145" y="214" text-anchor="middle" fill="#94a3b8" font-size="11">the most repeated one</text>
  <text x="145" y="270" text-anchor="middle" fill="#fbbf24" font-size="13">Take it or leave it?</text>
  <rect x="345" y="40" width="200" height="34" rx="6" fill="none" stroke="rgba(255,255,255,0.25)"/>
  <text x="445" y="62" text-anchor="middle" fill="#e2e8f0" font-size="13">Your question + your criterion</text>
  <rect x="330" y="104" width="230" height="44" rx="6" fill="none" stroke="#2dd4bf" stroke-width="1.5"/>
  <text x="445" y="124" text-anchor="middle" fill="#e2e8f0" font-size="13">The model researches</text>
  <text x="445" y="140" text-anchor="middle" fill="#94a3b8" font-size="11">searches, cites, explains its basis</text>
  <rect x="340" y="176" width="100" height="38" rx="6" fill="none" stroke="rgba(255,255,255,0.25)"/>
  <text x="390" y="192" text-anchor="middle" fill="#e2e8f0" font-size="13">Option A</text>
  <text x="390" y="207" text-anchor="middle" fill="#94a3b8" font-size="11">with its sources</text>
  <rect x="450" y="176" width="100" height="38" rx="6" fill="none" stroke="rgba(255,255,255,0.25)"/>
  <text x="500" y="192" text-anchor="middle" fill="#e2e8f0" font-size="13">Option B</text>
  <text x="500" y="207" text-anchor="middle" fill="#94a3b8" font-size="11">with its sources</text>
  <text x="445" y="270" text-anchor="middle" fill="#5eead4" font-size="13">You decide, comparing</text>
</svg>
<figcaption>As an oracle, all you can do is accept or reject what comes out. As a tool, what comes out is material for your criterion to decide on.</figcaption>
</figure>

The difference is clearest with the same request made both ways. As an oracle:

> Make me a diet for going to the gym.

As a tool:

> I'm torn between a keto diet and a paleo one. I do strength training three days a week and want to lose fat without losing muscle. Look for recent reviews and studies on each for this goal. For each claim, tell me what kind of evidence is behind it (clinical trial, observational study or expert opinion) and point out where there's no agreement. Then compare them and, with whichever fits best, make me a two-week plan.

The second one doesn't require knowing nutrition. It requires knowing what you want and what you'll accept as proof.

If you know or suspect something, tell it: "I've read that keto hurts performance in long sets — is that true? Look it up." It has often happened to me that I knew something the AI hadn't mentioned; as soon as I ask it to look, it finds it. But even if you know nothing, you can always ask it to justify what it says. That alone changes the conversation.

Don't expect the ideal answer on the first try, either. Using it as a tool means iterating: you often need to research further, fill in some part, or even rethink your own criterion or goals to get clear. The method doesn't hand you the answer in one go. It tells you how to continue on each round.

## Argue once

The problem with all of the above is that it's tiring. If every conversation starts with arguing with the model about what evidence you accept, you end up back at the oracle.

You don't have to. The platforms themselves let you fix your instructions so you don't have to repeat them: memory in ChatGPT, Claude or Gemini, projects with their own instructions, or a custom assistant (a GPT, a Gem). It takes no engineering at all; it's in the settings of the app you already use. You argue once, write down what you learned, and that's it.

Instructions like these are enough to start:

> When I ask about health, nutrition or any topic where there's debate, don't just give me the mainstream recommendation. Tell me what kind of evidence is behind each claim, separate consensus from opinion, lay out the serious alternatives, and search for sources before answering if the topic warrants it. If there's no agreement, say so.

My impression, and not only mine, is that Gemini and Claude adapt a bit better to what you ask of them, and ChatGPT is a bit more obtuse. But they all need it. With Gemini, until I turned on memory, it didn't remember certain things and tended to use popular definitions instead of rigorous ones. Once it was written down, that was the end of it.

## What the wall teaches

If running into these walls has an upside, it's that they show you where your own limit is. The conversation with my friend showed me where hers was, and it wasn't where she thought. She didn't lack knowledge of nutrition. She lacked a decision about what she'd accept as an answer, and the habit of asking the tool for it.

That can be learned, and quickly. And if you work with AI every day, you have the chance, and I'd say some responsibility, to teach it to the people around you, at home or at work. The hard question was never how much you delegate to the model. It's whether [you can still tell when the answer is wrong](/en/blog/how-much-should-you-still-know). That doesn't take knowing everything. It takes a criterion, written down somewhere.
