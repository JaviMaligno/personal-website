---
title: "The Rule Ate the Number"
description: "I told my video skill not to pile up numbers, and Opus removed every number from the voice. I reproduced it on fresh scripts across four skill versions and four models: the rule and the patched rule drop the finding's number, \"say it like a colleague\" never does, and the more obedient the model, the worse the rule."
pubDate: 2026-10-24
tags: ["AI", "Skills", "Prompting", "Evaluation", "Research"]
lang: en
translationKey: the-rule-ate-the-number
heroImage: "/blog/the-rule-ate-the-number.png"
repoUrl: https://github.com/JaviMaligno/skill-framing-experiments
---
<style>
.rtn-fig{margin:2rem 0;padding:1.25rem;background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:12px}
.rtn-fig svg{width:100%;height:auto;display:block}
.rtn-fig figcaption{margin-top:.75rem;color:#94a3b8;font-size:.9rem;line-height:1.5}
</style>

I make short narrated videos of my articles with a skill that writes the script: scenes, what the voice says, what appears on screen. In some of them the voice read out strings of figures, one after another, the way nobody talks. So I added a line to the skill:

> Spoken numbers sparingly. Never chain several figures in a row, and avoid repetitive or unround values in the voice: say the one number that carries the point […] and leave the rest on screen or out.

Then I asked Opus to revise two existing scripts with the updated skill. It removed every number from the voice:

| before | after |
|---|---|
| "With the fact in plain sight, Opus adopted the wrong conclusion 4 times in 791." | "With the fact in plain sight, Opus almost never adopted the wrong conclusion." |
| "Gemini 3 Flash: 88%, against 3% and 0%." | "Gemini 3 Flash: almost always, against almost never." |

The first line was the finding of the whole article. "Almost never" sounds the same as "rarely", and the point was precisely how rare.

So I corrected the correction, three times in a row. Each version of the line is a real commit:

| version | what the numbers line says |
|---|---|
| **rule** | say the one number that carries the point and leave the rest on screen or out |
| **pile-ups** | the problem is the pile-up, not the number; keep the figure that carries the point and move the rest to the screen |
| **if, by ear** | case by case: say a number when it's easy to hear; when it's awkward, say what it means in words ("almost never") and keep the figure on screen |
| **colleague** | say them the way you would explaining the result to a colleague: naturally, as part of the sentence; the only thing to avoid is reading a table aloud |

Each patch got more precise and none of them fixed it. The last one isn't a rule; it describes a way of speaking. That's the one that stuck. Around the same time I heard the same idea at a Claude Code event: skills work better written as a role or a metaphor than as detailed instructions.

A story about my own videos isn't evidence, so I measured it.

## Reproducing it

First, the same situation: the same two scripts, revised by Opus under each of the four versions, three times each.

The headline of the first script, "4 times in 791", came through like this:

| version | what Opus says in the three runs |
|---|---|
| rule | "almost never" twice, "only 4 times" once (without the 791) |
| pile-ups | "4 times in 791" all three times |
| if, by ear | "almost never" all three times |
| colleague | "4 times in 791" all three times |

The rule also turned "47% with long context" into "more often" all three times, which says less than the screen behind it. The episode reproduces, and the patched `if` is no better than the rule it replaced.

## On scripts it had never seen

Those two scripts are the ones that broke the skill, and every version after them was written with them in mind. So the real test uses material the skill had never seen: six of my articles with experimental results that never had a video.

For each article, Opus wrote a first script with the skill as it was before any numbers line. Those six drafts are fixed. Then four models revised each draft under each of the four versions, three times: Claude Opus 5.5 and gpt-6-astra (large), Claude Haiku 5.5 and gpt-6-luna (small). That makes 288 revisions.

Two LLM judges, Opus and gpt-6.1-sol, read each revision without knowing which version produced it. A revision passes if every finding the draft said with a number is still said with a number, or with an exact fraction like "a quarter" or "nine in ten". "Almost never", "more often" or "far more" don't count, and neither does moving the number to the screen. Before trusting the judges, I checked them against the reproduction above, where I had read every line myself; they agreed. On the 288 they agree with each other on 92% of the verdicts.

<figure class="rtn-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Revisions that still say the finding's number, of 18, per model and skill version. Rule: Opus 1, Astra 3, Haiku 5. If by ear: Opus 4, Astra 18, Haiku 14. Colleague: 18 for every model. Luna barely revises and keeps the numbers under every version.">
<text x="590" y="18" fill="#94a3b8" font-size="11" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">keeps the finding's number, of 18 (judge Opus · judge Sol)</text>
<text x="186" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">rule</text>
<text x="298" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">pile-ups</text>
<text x="410" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">if, by ear</text>
<text x="522" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">colleague</text>
<text x="118" y="77" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Opus</text>
<rect x="133" y="53" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.73"/>
<text x="186" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">1 · 0</text>
<rect x="245" y="53" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.47"/>
<text x="298" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">9 · 6</text>
<rect x="357" y="53" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.68"/>
<text x="410" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">4 · 0</text>
<rect x="469" y="53" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="118" y="123" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Astra</text>
<rect x="133" y="99" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.70"/>
<text x="186" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">3 · 0</text>
<rect x="245" y="99" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.55"/>
<text x="298" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">9 · 3</text>
<rect x="357" y="99" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.68"/>
<text x="410" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 14</text>
<rect x="469" y="99" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="118" y="169" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Haiku</text>
<rect x="133" y="145" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.60"/>
<text x="186" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">5 · 4</text>
<rect x="245" y="145" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.48"/>
<text x="298" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">9 · 7</text>
<rect x="357" y="145" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.62"/>
<text x="410" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">14 · 14</text>
<rect x="469" y="145" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="118" y="215" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Luna</text>
<rect x="133" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="186" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<rect x="245" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="298" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<rect x="357" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="410" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<rect x="469" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="134" y="252" fill="#94a3b8" font-size="11" font-family="ui-sans-serif,system-ui,sans-serif">Luna: barely revises</text>
</svg>
<figcaption>Six fresh articles, three revisions each per model and version, judged blind by two judges. The rule drops the finding's number on every model that actually revises; the patched "if" drops it on Opus; "say it like a colleague" keeps it everywhere.</figcaption>
</figure>

Here's what that looks like on one article. The draft's finding was "iterating solved 86%. Clean restarts: 69%. The button: 91%." Opus revised it like this:

- **rule**: "Clean restarts did clearly worse. The button did slightly better, but not significantly."
- **if, by ear**: "Clean restarts did worse. The button did slightly better, but not significantly."
- **colleague**: "Starting clean every round solved only 69%. The scoped button reached 91%, but its edge over iterating isn't significant."

The first two read well, and that's the problem. Nothing in them is wrong; the result is just gone.

## The more obedient the model, the worse the rule

The rule loses the number on every model that actually revises: Opus keeps it in 1 revision out of 18, Astra in 3, Haiku in 5. The patched `if` splits them. Astra and Haiku mostly keep the number with it (Astra 14 to 18 out of 18 depending on the judge, Haiku 14), and Opus drops it almost every time (4 and 0). The model that follows instructions best is the one that takes "say what it means in words" and applies it to every number it finds.

That matches my episode, which was with Opus: every escape route in the instruction gets taken.

Luna is the exception in the other direction. It hardly revises at all: it returns the draft nearly as it was, numbers included, under every version. Keeping every number isn't a virtue there, because Luna ignores the correction.

## What "colleague" doesn't fix

The colleague version never lost a finding, in any model. But it doesn't remove the pile-ups either. In the one scene of the original scripts that really was a pile-up, Opus with the colleague version kept all three figures in a row every time:

> The aligned models sit at ~0.10 repetition. The base hits 0.51 in one turn, and 0.78 over many.

The judges rated how much table-reading was left, from 0 to 3. The colleague version sits around 1.4 for Opus, where the rule sits at 0, and its overall quality scores are not the highest. It fixes the worse failure, losing the result, and leaves the milder one. For my videos that's the right trade: I can trim a pile-up in review, but I don't notice a missing number when the sentence sounds fine.

## When a plain rule is enough

The same question on simpler material bounds the effect: a 40-60 second briefing for an internal podcast, audio only, written from scratch rather than revised.

- A rule with a cap, "say at most the one figure that carries the point", dropped the essential figure there too: Opus kept it in 6 briefings out of 18 and Astra in 4. When the news is "from 9 to 12 euros" or "4 out of 791", a single figure can't carry it.
- A rule without a cap, "don't string unround numbers together; round when the source allows", kept the essential figure in every model, 17 or 18 out of 18. It also cleaned up the recitation better than "like a colleague" did.

So the rule isn't the problem in itself. The briefing had no screen to move numbers to, and the model wrote it from scratch instead of revising something that already had them. My video skill had both: "leave the rest on screen", and a script full of numbers to apply it to. I haven't isolated which of the two matters; that would take the same skill with and without the screen.

## What I take from it

If a correction gives the model somewhere else to put the thing ("on screen", "in words") or a cap ("the one number"), a capable model will use it on every instance, including the one that mattered. Patching it with conditions adds more instructions to follow to the letter. Describing how it should sound gives the model the purpose, and the purpose knows which number is the finding.

Where there's no escape route and no cap, a plain rule did as well, and sometimes better.

The limits: one skill, one kind of correction, six articles, three runs per cell, and all of it single-turn with no tools, while my real episode happened inside an agent session. The pattern holds across two judges and three models that revise, and it's the same one I hit by hand.

---

*Code, the four skill versions, every script and both judges' verdicts with their reasons: [skill-framing-experiments](https://github.com/JaviMaligno/skill-framing-experiments). The skills I use are [here](/en/skills).*
