---
title: "The definition looked complete"
description: "An agent summarised real code for another agent. Its note supported 16 correct change reviews, yet had turned a condition in the program into a broader rule."
pubDate: 2026-12-14
tags: ["AI", "Agents", "Evaluation"]
lang: en
translationKey: now-it-seems-to-mean-something
heroImage: "/blog/now-it-seems-to-mean-something-v4.png"
linkedinImage: "/blog/now-it-seems-to-mean-something-fig-2.png"
repoUrl: "https://github.com/JaviMaligno/code-world-models"
linkedinLinks:
  - label: "Mathias Strasser's post"
    url: "https://www.linkedin.com/posts/mathias-strasser-6990594_today-i-have-something-interesting-to-share-share-7505892928104570880-nI6R/"
---
<style>
.meaning-fig { margin: 2rem 0; }
.meaning-fig img, .meaning-fig svg { display: block; width: 100%; height: auto; border-radius: 6px; margin: 0; }
.meaning-fig figcaption { color: #94a3b8; font-size: .9rem; line-height: 1.55; margin-top: .7rem; }
</style>

An agent received code, documentation and tests from one of my projects. Its task was to prepare a note for another agent that would review maintenance changes. In that note, it explained the meaning of one of the flags the program returns.

The definition was clear. It passed through two further handoffs and remained clear. With the final note, two models correctly reviewed all 16 proposed changes in the initial test, in both repetitions.

Yet the definition had lost a condition. When a case was constructed to separate what the note said from what the code did, GPT accepted incorrect behaviour and justified it by referring to that same definition.

That is what interests me about this case: **an agent can work well from an explanation that has already changed the operational meaning of what it explains.**

## A word with a reasonable definition

The question came from [a post by Mathias Strasser](https://www.linkedin.com/posts/mathias-strasser-6990594_today-i-have-something-interesting-to-share-share-7505892928104570880-nI6R/) about terminology invented by LLMs. His concern was what happens when those expressions enter prompts written by one agent for another. The next model may appear to understand them while the person maintaining the system loses the ability to follow the conversation.

I wanted to examine what an agent actually preserves when it passes on a technical explanation. I used code, plans and tests from [my Code World Models project](https://github.com/JaviMaligno/code-world-models). One task was to prepare instructions for reviewing performance changes to a code generation and repair process.

That process shows the model a sample of observations and evaluates its generated code against a larger set. During repair, it can only show the model errors belonging to the permitted sample. This makes it possible to study what the model can correct with a bounded amount of evidence.

There is a flag called `evidence_capped_failure`. The first agent explained it like this:

> An `evidence_capped_failure` occurs when gate accuracy is below 1.0 but no remaining attributable failure belongs to the allowed set. It stops refinement immediately.

In other words: errors remain, but none belongs to the set the model is allowed to see; repair therefore stops and the failure is marked as limited by the available evidence.

It is a useful explanation. It distinguishes that situation from a syntax or execution error, which is handled separately. It preserves the distinction between what is evaluated and what can be shown. It also fits the name of the flag.

The missing detail is where in the program this check happens.

## The condition was outside the definition

The [original function](https://github.com/JaviMaligno/code-world-models/blob/e2e061a8112d1576728e00912b92df455049b4d5/src/cwm/continuous/evidence_dose.py) initialises the flag to `False` and changes it inside the repair loop. This excerpt omits the separate handling of infrastructure errors and the body of the model call:

```python
evidence_capped_failure = False

while acc < 1.0 and iterations < max_iters:
    # ... infrastructure error handling ...
    feed = [f for f in failures
            if f["source_index"] in allowed_source_indices]
    if not feed:
        evidence_capped_failure = True
        break
    # ... repair and increment iterations ...
```

With zero iterations allowed, the loop never runs. The flag remains `False`, even when the known errors fall outside the permitted sample.

The note had turned a description of what happens **inside a procedure** into a definition that could be applied directly to the data. The code requires entering the loop; the shortened definition only requires remaining errors outside the permitted set.

That difference can slip out of view if the question is what the name means. The words *evidence-capped failure* fit imperfect code that will not be shown further examples fairly well. But the result field has the particular behaviour implemented by the function, including when it can be set.

One could decide that the program should compute the flag before the loop. That would change its behaviour. In this test the task was to preserve behaviour during a performance refactor, so that decision was outside the assignment.

## The handoff preserved the phrase

GPT-5.6 Sol wrote the first summary. A fresh Claude Opus 5 session turned it into a reviewer brief, and another fresh GPT session prepared the next agent's session note. Each recipient saw only the text it received and could not retrieve the original files. Length targets became progressively shorter, without mechanically truncating any response.

<figure class="meaning-fig">
<picture>
<source srcset="/blog/now-it-seems-to-mean-something-fig-1.png" type="image/png">
<img src="https://www.javieraguilar.ai/blog/now-it-seems-to-mean-something-fig-1.png" alt="The loop-entry condition was already missing from the first note. Subsequent handoffs preserved the shortened definition." aria-label="The loop-entry condition was already missing from the first note. Subsequent handoffs preserved the shortened definition." loading="lazy">
</picture>
<figcaption>The loop-entry condition was already missing from the first note. Subsequent handoffs preserved the shortened definition.</figcaption>
</figure>

The final note said:

> Gate accuracy below 1.0 with no attributable allowed failure is `evidence_capped_failure` and stops refinement.

The loop-entry condition was already missing from the first note. Subsequent handoffs preserved that shortened definition. This matters for locating the failure: this case did not show a correct rule gradually deteriorating at each handoff. The first explanation already covered more cases than the procedure it came from.

Even so, the final note supported correct reviews of all 16 initial proposals in the evidence task, with both models and two repetitions. These concerned changes such as preserving original indices, evaluating against the full set, preventing positive examples from leaking into the background, and distinguishing an infrastructure failure. The note retained enough information to resolve them.

## The case that separates the two meanings

The additional check fixed a concrete situation: two errors remained, both outside the permitted set, there was no infrastructure problem, and the maximum number of iterations was zero. The proposal was to return `evidence_capped_failure=True` without making repair calls.

Under the current code, that proposal must be rejected. The expected result was checked by executing the original function with a simulated evaluation. It did not depend on another LLM's judgement.

Four contexts were compared: the full dossier, the first note, the final note, and a copy of the final note with opaque labels. Among the replacements, `evidence_capped_failure` became `flag_q7` in both the instructions and the proposal.

<figure class="meaning-fig">
<picture>
<source srcset="/blog/now-it-seems-to-mean-something-fig-2.png" type="image/png">
<img src="https://www.javieraguilar.ai/blog/now-it-seems-to-mean-something-fig-2.png" alt="The proposal returns True where the code returns False. Opaque labels do not fix the incorrect acceptance. These are two repetitions of the same case per condition and model." aria-label="The proposal returns True where the code returns False. Opaque labels do not fix the incorrect acceptance. These are two repetitions of the same case per condition and model." loading="lazy">
</picture>
<figcaption>The proposal returns True where the code returns False. Opaque labels do not fix the incorrect acceptance. These are two repetitions of the same case per condition and model.</figcaption>
</figure>

With the summaries, GPT accepted the change in both repetitions of all three conditions. One of its reasons was:

> With accuracy below 1.0, no failure attributable to an allowed source, and zero permitted iterations, returning evidence_capped_failure with zero repair iterations preserves the specified behavior.

With the full dossier, its only valid response rejected the change; the other had incomplete JSON and was excluded in full. Claude rejected the change in both dossier responses. With the first note it requested context twice; with the final note it requested context once and accepted once; with opaque labels it accepted twice.

These are repetitions of **one case**, not independent discoveries or an estimate of how often handoffs fail this way. The check was designed after examining the summaries: it is an exploratory probe of an observed omission. Its expected answers were fixed before its calls.

## What success had left unchecked

The agents could use the term, explain the condition and agree on many decisions. None of those things forced a distinction between two readings: “the data satisfy this condition” and “the procedure has reached the point at which it checks this condition”.

With zero iterations, that distinction determines the result. A definition that appeared to describe the program had become a small alternative specification. The next agent could follow it quite faithfully and propose a change that broke the behaviour it was supposed to preserve.

The name survived. What stopped travelling with it was a condition of use expressed in the structure of the code.

This also bounds what I can say about the concern that motivated the test. I have not established who coined these terms or measured how people understand them. Changing the names did not fix this case's error. Elsewhere in the test, a possible confusion appeared after a category was renamed; its proposed lexical explanation did not reproduce in the follow-up's 19 valid responses. I have no basis for attributing this result to two models sharing private jargon.

I do have an example of a sufficiently useful explanation coming to stand in for the specification. Explaining the word again can leave that difference intact. Here, it became visible in a situation where the two readings stopped agreeing.

For a flag like this, I would ask what allows the program to set it and what it returns when that step never happens. That information belongs to its operational meaning. If the next agent receives only the definition, it has grounds to treat it as a general rule.

The missing sentence was short: “This flag can only be set inside the repair loop.” Everything else could be well written, understandable and useful for the task. That sentence was still needed.

---

*Test using two maintenance areas of one project and simulated handoffs without file access. Two of the four planned starts completed the chain; the other two returned empty responses marked as refusals by the provider. The main test and two follow-ups totalled 76 calls, with two malformed reviews excluded in full. Reference cost: USD 4.97. The [code and data archive (ZIP)](/downloads/prompt-meaning-pilots.zip) contains sources, prompts, responses, exclusions and earlier pilots. This study's report is at `v4/results/findings.md` inside the archive; the follow-ups are documented separately.*
