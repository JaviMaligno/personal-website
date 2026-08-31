---
title: "It blames the model for what it wouldn't blame itself for"
description: "Agents that build systems with an LLM inside keep reaching for the same explanation: the model is nondeterministic. Five times it wasn't, and the interesting part is where the suspicion went instead of where the cause was."
pubDate: 2026-08-31
tags: ["AI", "Agents", "Engineering", "Debugging"]
lang: en
translationKey: blaming-the-model
heroImage: "/blog/blaming-the-model.png"
---

<style>
.btm-fig { margin: 2rem 0; }
.btm-fig svg { width: 100%; height: auto; display: block; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; background: #1a1a24; }
.btm-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

I spend most of my time building systems that have a language model somewhere inside them, and most of that time I am not writing the code myself — an agent is. Which means I spend a lot of my day reading an agent's explanation of why something didn't work.

There is a pattern in those explanations that took me a while to name. When the system under discussion is ordinary software, the agent reasons about it well: it looks for the bug, it finds the bug. When the system under discussion has a model inside it, the reasoning changes. The suspicion drifts somewhere else, and it lands on the model.

What makes this odd, rather than merely wrong, is that the agent doing the reasoning is itself a model — frequently the same one that is running inside the thing it's diagnosing.

Five times this came up. None of them is a disaster story; they're all small, and that's rather the point.

## The trace nobody asked for

We had a classifier: it reads documents about something and assigns it a category, with a confidence and a justification. Results were uneven, and I asked the agents working on it to figure out why.

What came back were hypotheses. Good ones, in the sense that they were plausible and well written. The category boundaries might be ambiguous. The documents might be too short. The model might be over-indexing on certain words. Each of these could have been true. None of them could be checked with what we had, because what we had was the input and the final answer, and nothing in between.

Not once did anyone propose the obvious thing: *let's log what actually happened*.

So I decided it myself, and it took three passes to get right — first what was searched and what came back, then which documents actually reached the model rather than merely what the search returned, then every tool call rather than only the searches. Each pass I thought we had enough and each pass we didn't.

And then something I didn't expect. Once the trace was complete, the analysis got better on its own. I had also written a rule — look at the reasoning, look at the confidences, look at every intermediate step — and I'd assumed the rule was doing the work. It wasn't, or not most of it. **Handing over the information turned out to be more effective than handing over the instruction about how to analyse it.**

That's worth sitting with, because the current reflex for fixing an agent's behaviour is to write it a better rule: a skill, a section in `CLAUDE.md`, a checklist. Sometimes what it needs is not a better instruction but a wider window.

## "It's just stochastic"

The second one is the most common, and it's the one that named the whole thing.

Results vary between runs, and the explanation offered is the sampling of the model. Sometimes this is said outright; more often it arrives as a shrug — *these systems are nondeterministic, you can't expect stability*.

In my experience that has almost never been the actual cause. The inputs changed. The retrieval returned documents in a different order. A tool omitted an optional field. Two rules in the prompt both applied and nobody had declared which one wins. The context got truncated and the decisive document fell outside the window. These are design problems, and they have the useful property of being fixable.

<figure class="btm-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Diagram showing five layers of a system with a model inside — input data, prompt and rules, tools and retrieval, harness code, and model sampling. The causes of variability usually sit in the first four layers, while the suspicion lands on the fifth.">
  <rect x="30" y="40" width="300" height="34" rx="5" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.2"/>
  <text x="46" y="62" fill="#e2e8f0" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">input data</text>
  <rect x="30" y="86" width="300" height="34" rx="5" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.2"/>
  <text x="46" y="108" fill="#e2e8f0" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">prompt &amp; rules</text>
  <rect x="30" y="132" width="300" height="34" rx="5" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.2"/>
  <text x="46" y="154" fill="#e2e8f0" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">tools &amp; retrieval</text>
  <rect x="30" y="178" width="300" height="34" rx="5" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.2"/>
  <text x="46" y="200" fill="#e2e8f0" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">harness code</text>
  <rect x="30" y="230" width="300" height="34" rx="5" fill="#2a1f14" stroke="#f59e0b" stroke-width="1.6"/>
  <text x="46" y="252" fill="#fbbf24" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">model sampling</text>

  <path d="M338 57 L400 57 M338 103 L400 103 M338 149 L400 149 M338 195 L400 195" stroke="#2dd4bf" stroke-width="1.2" fill="none" opacity="0.7"/>
  <path d="M400 50 L400 202" stroke="#2dd4bf" stroke-width="1.5" fill="none"/>
  <text x="412" y="120" fill="#5eead4" font-size="13">where the cause</text>
  <text x="412" y="138" fill="#5eead4" font-size="13">usually is</text>

  <path d="M338 247 L400 247" stroke="#f59e0b" stroke-width="1.6" fill="none"/>
  <text x="412" y="243" fill="#fbbf24" font-size="13">where the</text>
  <text x="412" y="261" fill="#fbbf24" font-size="13">suspicion lands</text>
</svg>
<figcaption>The variability almost always comes from one of the top four layers, all of which are design decisions somebody made. The explanation reaches for the fifth, which is the only one nobody can be blamed for.</figcaption>
</figure>

Notice what the bottom layer has that the others don't: nobody wrote it. Attributing a problem to the sampling of the model is the one diagnosis that ends the investigation without implicating any decision anyone made. That is not a small part of its appeal.

## The switch

The second story has a reflex attached to it, and the reflex is its own small story.

Once "it's stochastic" is on the table, the remedy that follows is: lower the temperature. It is the first thing proposed, often before anything has been measured.

It fails on two levels at once. It isn't the cause, so it doesn't fix anything — at best it freezes the wrong answer instead of making it vary. And on a good number of current models it isn't even available: reasoning models reject the parameter. I checked this while building the experiment that follows this article, because I wanted to be precise rather than rhetorical: on the deployment I use, `gpt-5-mini` refuses any value of `temperature` at all, while `gpt-5.4` and `gpt-5.4-mini` accept it without complaint. So the reflex is always a diagnostic error, and on some models it's also an API error you discover by hitting it.

What I find telling is not the mistake. It's that reaching for a knob is easier than reaching for the design, and there is always a knob.

## Nobody audited the ground truth

We were moving from one model version to the next, and the feedback was that the new one was worse.

I didn't believe it, and not out of loyalty to the new model — I just knew how the comparison had been built. It turned out the prompt used for the new model wasn't equivalent to the one used for the old one. And underneath that, the gold set had errors of its own, and those errors happened to reward the answers the old model gave.

The measurement was wrong in the direction that made the conclusion look obvious. And it took someone asking *is this ground truth actually correct?* for anyone to look — which is a question about one's own method, not about the model.

That asymmetry is the clearest version of the whole pattern. Suspicion of the model came first. Suspicion of the setup that produced the number came only when prompted. I've [written before](/en/blog/how-much-should-you-still-know) about the part of the job that survives delegation being the ability to tell when an answer is wrong; auditing the thing you're measuring against is where that starts.

## A regex where judgement was needed

The fifth is what happens after the agent finally accepts that the problem is one of design.

The remedy it proposes is a regex. Or a list of keywords, or a hard threshold on a score. Something that works perfectly on the three examples in front of it and falls over on the fourth. In practice I have to stop almost every determinism proposal I'm offered, because I can usually see where it breaks before it's written.

And the motive behind it is the other half of the same problem. The agent reaches for brittle rules because it doesn't trust the model to discriminate — which is precisely the thing a model is for. When the task genuinely has no enumerable rule, when the set of cases isn't bounded and the phrasing is open-ended, the correct answer is to give the model better scaffolding and let it judge. Reaching for a keyword list there isn't caution; it's substituting the one component that could have handled the case.

So the two halves point in opposite directions and share a cause. It suspects the model where the fault is in the design, and it distrusts the model where the model is the design. Both are failures of calibration about what a system with a language model in it actually is — and I'd argue the second is the more expensive one, because the brittle rule tends to survive in the codebase long after the person who added it has moved on.

## The same model on both sides

None of these are exotic failures. They're the ordinary texture of building this kind of software with agents, and I want to be careful not to make them sound worse than they are: in most of these cases the agent's work was good and the fix, once pointed at, was competent.

But the pattern holds, and what makes it strange is the symmetry it breaks. An agent debugging a web server does not conclude that the CPU is unreliable. It looks for the mistake, and it looks for it in the code, because the code is where mistakes live. Put a language model in the system and the same agent starts treating one layer as weather — something that happens to you rather than something someone built.

The layer it excuses is running the agent that's doing the excusing. Which is a strange enough thing to notice that I stopped writing about it and went to measure it instead: whether the suspicion really does move depending on what you show the agent, and whether it moves for the reason it looks like. That's the next piece.

---

*Related: [coding agents and teamwork](/en/blog/coding-agents-structure), where a similar question — is this a capability problem or a structure problem? — turned out to have the same answer; and [what practices actually help an agent](/en/blog/practices-for-agents-substrate), measured over 750 runs.*
