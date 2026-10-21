---
title: "A Role, Not a Rule"
description: "Skills work better written as a role than as a list of rules: a rule gets applied to every case, a role carries the purpose that tells the cases apart. My video skill is one example. A numbers rule made Opus strip the finding's number from the voice; \"say it like a colleague\" kept it. I measured it across four skill versions and four models, and the more obedient the model, the worse the rule."
pubDate: 2026-10-24
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
.article-content .table-wrap table td,.article-content .table-wrap table th{white-space:normal}
.article-content table.rtn-ba{table-layout:fixed}.article-content table.rtn-ba td,.article-content table.rtn-ba th{width:50%}
</style>

At [Claude Code Curious](https://luma.com/ccc-mk) in Milton Keynes, one of the organizers made a point I had just run into myself: skills work better written as a role or a metaphor than as detailed instructions. The example was documentation. Instead of listing what good docs contain, ask the model to act as a librarian.

The idea is easy to agree with and hard to believe until a rule fails on you. A rule names what to avoid, and a model that follows instructions well applies it to every case it finds, including the one where it was wrong. A role carries the purpose behind the rule, and the purpose is what tells the cases apart. A librarian knows which documents someone will come looking for.

The role depends on the skill. Librarian for documentation; in my case, a colleague. This is how I found mine, and what happened when I measured it.

## The rule that ate the number

I make short narrated videos of my articles ([they're on Instagram](https://www.instagram.com/agilabs_ai)) with a [Claude Code plugin](/en/skills) that writes the script: scenes, what the voice says, what appears on screen. In some of them the voice read out strings of figures, one after another, the way nobody talks. So I added a line to the skill:

> Spoken numbers sparingly. Never chain several figures in a row, and avoid repetitive or unround values in the voice: say the one number that carries the point […] and leave the rest on screen or out.

Then I asked Opus to revise two existing scripts with the updated skill. It removed every number from the voice:

<div class="table-wrap"><table class="rtn-ba">
<thead><tr><th>before</th><th>after</th></tr></thead>
<tbody>
<tr><td>"With the fact in plain sight, Opus adopted the wrong conclusion 4 times in 791."</td><td>"With the fact in plain sight, Opus almost never adopted the wrong conclusion."</td></tr>
<tr><td>"Gemini 3 Flash: 88%, against 3% and 0%."</td><td>"Gemini 3 Flash: almost always, against almost never."</td></tr>
</tbody>
</table></div>

The first line was the finding of the whole article. "Almost never" sounds the same as "rarely", and the point was precisely how rare.

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

That matches my episode, which was with Opus: every escape route in the instruction gets taken. It's also the general argument from the top. The better the model follows a rule, the more it matters that the rule is wrong in some case, and a rule always is.

Luna is the exception in the other direction. It hardly revises at all: it returns the draft nearly as it was, numbers included, under every version. Keeping every number isn't a virtue there, because Luna ignores the correction.

What I can't settle from this is whether the colleague brings back the pile-ups that started it all. The judges scored a bit more leftover figure-reading for it than for the rule, which strips everything, but I didn't check that score against my own ear the way I checked the main verdict. In the video I made with the colleague version, I don't hear any pile-up.

## When a plain rule is enough

The same question on simpler material bounds the effect: a 40-60 second briefing for an internal podcast, audio only, written from scratch rather than revised.

- A rule with a cap, "say at most the one figure that carries the point", dropped the essential figure there too: Opus kept it in 6 briefings out of 18 and Astra in 4. When the news is "from 9 to 12 euros" or "4 out of 791", a single figure can't carry it.
- A rule without a cap, "don't string unround numbers together; round when the source allows", kept the essential figure in every model, 17 or 18 out of 18. It also cleaned up the recitation better than "like a colleague" did.

So a rule isn't wrong by being a rule. The briefing had no screen to move numbers to, and the model wrote it from scratch instead of revising something that already had them. My video skill had both: "leave the rest on screen", and a script full of numbers to apply it to. I haven't isolated which of the two matters; that would take the same skill with and without the screen.

## What I take from it

A rule fails when it gives the model somewhere else to put the thing ("on screen", "in words") or a cap ("the one number"): a capable model uses it on every instance, including the one that mattered. Patching it with conditions adds more instructions to follow to the letter. A role gives the model the purpose, and the purpose knows which number is the finding.

So before writing the next rule into a skill, I ask who would do this task well without being told the rules, and write that person in. For documentation it's a librarian; for narration, someone explaining a result to a colleague. Where there's no escape route and no cap, a plain rule did as well, and sometimes better.

The limits: one skill, one kind of correction, six articles, three runs per cell, and all of it single-turn with no tools, while my real episode happened inside an agent session. The pattern holds across two judges and three models that revise, and it's the same one I hit by hand. The librarian I only know from the talk; I haven't measured it.

---

*Code, the four skill versions, every script and both judges' verdicts with their reasons: [skill-framing-experiments](https://github.com/JaviMaligno/skill-framing-experiments). The video plugin and the rest of my skills are [here](/en/skills).*
