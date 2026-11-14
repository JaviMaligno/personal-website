---
title: "A Role, Not a Rule"
description: "Skills work better written as a role than as a list of rules: a rule gets applied to every case, a role carries the purpose that tells the cases apart. My video skill is one example. A rule written against strings of figures made Opus take numbers out of the voice everywhere, including the finding that needed its size; \"say it like a colleague\" kept it. I measured it across four skill versions and four models, and the more obedient the model, the worse the rule."
pubDate: 2026-11-14
tags: ["AI", "Skills", "Prompting", "Evaluation", "Research"]
lang: en
translationKey: a-role-not-a-rule
heroImage: "/blog/a-role-not-a-rule.png"
repoUrl: https://github.com/JaviMaligno/skill-framing-experiments
---
<style>
.rtn-fig{margin:2rem 0;padding:1.25rem;background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:12px}
.rtn-fig svg{width:100%;height:auto;display:block}
.rtn-fig figcaption{margin-top:.75rem;color:#94a3b8;font-size:.9rem;line-height:1.5}
.article-content table.rtn-ba{table-layout:fixed}.article-content table.rtn-ba td,.article-content table.rtn-ba th{width:50%}
</style>

At [Claude Code Curious](https://luma.com/ccc-mk) in Milton Keynes, one of the organizers made a point I had just run into myself: skills work better written as a role or a metaphor than as detailed instructions. The example was documentation. Instead of listing what good docs contain, ask the model to act as a librarian.

The idea is easy to agree with and hard to believe until a rule fails on you. A rule spells out what to do in each case, and a model that follows instructions well applies it to every case that fits, including the ones its author didn't have in mind. A role carries the purpose behind the rule, and the purpose is what tells the cases apart. A librarian knows which documents someone will come looking for.

The role depends on the skill. Librarian for documentation; in my case, a colleague. This is how I found mine, and what happened when I measured it.

## The rule that ate the number

I make short narrated videos of my articles ([they're on Instagram](https://www.instagram.com/agilabs_ai)) with a [Claude Code plugin](/en/skills) that writes the script: scenes, what the voice says, what appears on screen. In some of them the voice read out strings of figures, one after another, the way nobody talks. So I added a line to the skill:

> Spoken numbers sparingly. Never chain several figures in a row, and avoid repetitive or unround values in the voice: say the one number that carries the point […] and leave the rest on screen or out.

Then I asked Opus to revise two existing scripts with the updated skill. The line was written against strings of figures, and Opus applied it to every number in the voice, strung together or not:

<div class="table-wrap"><table class="rtn-ba">
<thead><tr><th>before</th><th>after</th></tr></thead>
<tbody>
<tr><td>"Its own subagent's report? Answered straight away 25% of the time."</td><td>"Its own subagent's report? Answered straight away a quarter of the time."</td></tr>
<tr><td>"Aligned models: ~0.10 repetition. The base: 0.51, multi-turn 0.78."</td><td>"Aligned models barely repeat. The base does, and more over many turns."</td></tr>
</tbody>
</table></div>

The first line had one figure and nothing to fix. The swap does no harm, but the rule fired where it had no business. The second line was a real pile-up, and the fix took the finding with it: the base model repeats about five times as much as the aligned ones, and "more" doesn't say that. That is a rule overfitted to the case that prompted it: written for one symptom, applied to everything that looks like it.

So I corrected the correction, three times in a row. Each version of the line is a real commit:

| version | what the numbers line says |
|---|---|
| **rule** | say the one number that carries the point and leave the rest on screen or out |
| **pile-ups** | the problem is the pile-up, not the number; keep the figure that carries the point and move the rest to the screen |
| **if, by ear** | case by case: say a number when it's easy to hear; when it's awkward, say what it means in words ("almost never") and keep the figure on screen |
| **colleague** | say them the way you would explaining the result to a colleague: naturally, as part of the sentence; the only thing to avoid is reading a table aloud |

Each patch got more precise and none of them fixed it. The last one isn't a rule; it describes who is talking and to whom. That's the one that stuck.

A story about my own videos isn't evidence, so I measured it.

## Reproducing it

First, the same situation: the same two scripts, revised by Opus under each of the four versions, three times each.

The rule took the size out of the repetition line all three times ("The aligned models barely repeat. The base is on another planet."). In the subagent script, where the real revision had said "almost half", it turned "47% with long context" into "more often" all three times, which says less than the screen behind it. The patched `if` said "almost half" there, and lost the repetition gap just like the rule. Under the colleague, Opus kept the 47% all three times ("With long context, that rose to 47%"). On the repetition line it kept the three figures as they were, which isn't the fix either; I come back to that below.

## On scripts it had never seen

Those two scripts are the ones that broke the skill, and every version after them was written with them in mind. So the real test uses material the skill had never seen: six of my articles with experimental results that never had a video.

For each article, Opus wrote a first script with the skill as it was before any numbers line. Those six drafts are fixed. Then four models revised each draft under each of the four versions, three times: Claude Opus 5.5 and gpt-6-astra (large), Claude Haiku 5.5 and gpt-6-luna (small). That makes 288 revisions.

Two LLM judges, Opus and gpt-6.1-sol, read each revision, together with the article it narrates, without knowing which version produced it. A revision passes if every finding the draft said with a number is still carried by the voice. When the article states a finding qualitatively, words that say the same thing pass: "almost never" for 4 times in 791 is fine when the point is that it almost never happens. When the finding is a size or a gap, the voice has to keep the size, with the number or with a fraction or ratio like "almost half" or "five times as much". "More often", "far more" or "on another planet" don't count, and neither does moving the number to the screen. Before trusting the judges, I checked them against the reproduction above, where I had read every line myself; they agreed. On the 288 they agree with each other on 86% of the verdicts.

<figure class="rtn-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Revisions whose voice still carries the finding, of 18, per model and skill version, judge Opus and judge Sol. Rule: Opus 7 and 0, Astra 5 and 3, Haiku 7 and 2. If by ear: Opus 6 and 2, Astra 18 and 18, Haiku 15 and 13. Colleague: 18 for every model except Astra under Sol, 17. Luna barely revises and keeps the numbers under every version.">
<text x="590" y="18" fill="#94a3b8" font-size="11" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">keeps the finding, of 18 (judge Opus · judge Sol)</text>
<text x="186" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">rule</text>
<text x="298" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">pile-ups</text>
<text x="410" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">if, by ear</text>
<text x="522" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">colleague</text>
<text x="118" y="77" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Opus</text>
<rect x="133" y="53" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.66"/>
<text x="186" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">7 · 0</text>
<rect x="245" y="53" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.50"/>
<text x="298" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">15 · 5</text>
<rect x="357" y="53" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.65"/>
<text x="410" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">6 · 2</text>
<rect x="469" y="53" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="118" y="123" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Astra</text>
<rect x="133" y="99" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.65"/>
<text x="186" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">5 · 3</text>
<rect x="245" y="99" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.53"/>
<text x="298" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">9 · 9</text>
<rect x="357" y="99" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="410" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<rect x="469" y="99" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.74"/>
<text x="522" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 17</text>
<text x="118" y="169" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Haiku</text>
<rect x="133" y="145" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.64"/>
<text x="186" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">7 · 2</text>
<rect x="245" y="145" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.54"/>
<text x="298" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">13 · 4</text>
<rect x="357" y="145" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.68"/>
<text x="410" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">15 · 13</text>
<rect x="469" y="145" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="118" y="215" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Luna</text>
<rect x="133" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="186" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<rect x="245" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="298" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<rect x="357" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.74"/>
<text x="410" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 17</text>
<rect x="469" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="134" y="252" fill="#94a3b8" font-size="11" font-family="ui-sans-serif,system-ui,sans-serif">Luna: barely revises</text>
</svg>
<figcaption>Six fresh articles, three revisions each per model and version, judged blind by two judges. The rule loses the finding on every model that actually revises; the patched "if" loses it on Opus; "say it like a colleague" keeps it everywhere.</figcaption>
</figure>

Here's what that looks like on one article. The draft's finding was "iterating solved 86%. Clean restarts: 69%. The button: 91%." Opus revised it like this:

- **rule**: "Clean restarts did clearly worse. The button did slightly better, but not significantly."
- **if, by ear**: "Clean restarts did worse. The button did slightly better, but not significantly."
- **colleague**: "Starting clean every round solved only 69%. The scoped button reached 91%, but its edge over iterating isn't significant."

The first two read well, and that's the problem. Nothing in them is wrong; the result is just gone.

## The more obedient the model, the worse the rule

The rule loses the finding on every model that actually revises: depending on the judge, Opus keeps it in 0 to 7 revisions out of 18, Astra in 3 to 5, Haiku in 2 to 7. The patched `if` splits them. Astra and Haiku mostly keep the finding with it (Astra 18 out of 18 with both judges, Haiku 13 to 15), and Opus drops it most of the time (6 and 2). The model that follows instructions best is the one that takes "say what it means in words" and applies it to every number it finds.

That matches my episode, which was with Opus: every escape route in the instruction gets taken. It's also the general argument from the top. The better the model follows a rule, the more it matters that the rule is wrong in some case, and a rule always is.

Luna is the exception in the other direction. It hardly revises at all: it returns the draft nearly as it was, numbers included, under every version. Keeping every number isn't a virtue there, because Luna ignores the correction.

The colleague isn't spotless either. The judges also marked runs of figures, and the colleague leaves more of them than the rule, which strips everything: "from 0.958 with state alone to 0.999", or a row of decimals read one after another. Part of that comes from somewhere else in the skill. All four versions carried an older line, written the same way: give the finding "with its exact number", as the article writes it, "same rounding, same units". Under the rule, the rule won. Under the colleague, that old patch was in charge again. Swapping the rule for a role brought out the other patches written like it, and those needed their own fixes. In the video I made with the colleague version, I don't hear any pile-up.

## When a plain rule is enough

The same question on simpler material bounds the effect: a 40-60 second briefing for an internal podcast, audio only, written from scratch rather than revised.

- A rule with a cap, "say at most the one figure that carries the point", dropped the essential figure there too: Opus kept it in 6 briefings out of 18 and Astra in 4. When the news is "from 9 to 12 euros", a single figure can't carry it.
- A rule without a cap, "don't string unround numbers together; round when the source allows", kept the essential figure in every model, 17 or 18 out of 18. It also cleaned up the recitation better than "like a colleague" did.

So a rule isn't wrong by being a rule. The briefing had no screen to move numbers to, and the model wrote it from scratch instead of revising something that already had them. My video skill had both: "leave the rest on screen", and a script full of numbers to apply it to. I haven't isolated which of the two matters; that would take the same skill with and without the screen.

## What I take from it

A rule is fitted to the case that prompted it, and a capable model applies it to everything that resembles that case. It fails worst when it gives the model somewhere else to put the thing ("on screen", "in words") or a cap ("the one number"): a capable model uses it on every instance, including the one that mattered. Patching it with conditions adds more instructions to follow to the letter, and a rule is rarely alone: swapping one for a role shows the others written the same way. A role gives the model the purpose, and the purpose knows which number is the finding.

So before writing the next rule into a skill, I ask who would do this task well without being told the rules, and write that person in. For documentation it's a librarian; for narration, someone explaining a result to a colleague. Where there's no escape route and no cap, a plain rule did as well, and sometimes better.

The limits: one skill, one kind of correction, six articles, three runs per cell, and all of it single-turn with no tools, while my real episode happened inside an agent session. The pattern holds across two judges and three models that revise, and it's the same one I hit by hand. The librarian I only know from the talk; I haven't measured it.

---

*Code, the four skill versions, every script and both judges' verdicts with their reasons: [skill-framing-experiments](https://github.com/JaviMaligno/skill-framing-experiments). The video plugin and the rest of my skills are [here](/en/skills).*
