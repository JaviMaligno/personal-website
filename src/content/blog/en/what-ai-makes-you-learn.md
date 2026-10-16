---
title: "What AI makes you learn"
description: "Using AI well depends more and more on knowing things that aren't technical: how a model is trained and why it pulls towards the most probable, what evidence counts for each kind of knowledge, what each kind of study answers, how to pin down a definition. And why getting answers right isn't the same as having a relation to truth."
pubDate: 2026-11-11
tags: ["AI", "Critical Thinking", "Philosophy", "Epistemology"]
lang: en
translationKey: what-ai-makes-you-learn
heroImage: "/blog/what-ai-makes-you-learn.png"
---

Ask a language model to pick a random number between 1 and 10. Very often it will say 7. Ask for one between 1 and 100 and each model has its favourite: in [some tests across several models](https://www.s-anand.net/blog/llms-random-number-bias/), ChatGPT settled on 47, Claude 3 Haiku on 42 and Gemini on 72. [A 2025 study](https://arxiv.org/abs/2502.19965) puts it down to biases in the data they were trained on.

It isn't a curious glitch. It's the simplest way to see how the thing works inside, and it explains almost everything I described in [Oracle or tool](/en/blog/oracle-or-tool): why the first answer is the conventional one, why definitions drift towards popular usage. There I argued that using AI doesn't require knowing everything, only having a method. This article is about what makes that method possible: a handful of skills, some technical and most of them philosophical, that AI makes more useful than ever.

## Why it pulls towards the most probable

A language model is trained to predict the next word of a text. It's shown enormous amounts of text written by people and, through a procedure called gradient descent, its parameters are adjusted little by little so it gets that prediction wrong less and less. The result is a model that has learned what tends to follow what: the distribution of what people write.

When you ask it something, the model generates the answer by choosing, word by word, among the most probable continuations. And people, when asked for a random number, also pick 7 far more often than they should. The model has learned that human bias and, by settling on the most probable, concentrates it further.

Then comes a second phase of training, in which the model is adjusted according to the answers people rate best. That makes it more useful and more polite, but it [reduces the variety of what it answers](https://arxiv.org/abs/2310.06452): it pushes towards the answer most people would approve.

This explains three things users notice without knowing why:

- **The conventional answer.** Far more has been written about nutrition's mainstream recommendation than about any alternative, so that's what comes out first.
- **The popular definition.** If a word is used loosely a thousand times for every time it's used rigorously, the model tends to the loose use, even if you pinned it down three messages ago.
- **The agreeable tone.** Agreeing with you tends to be rated better than contradicting you.

None of this makes it useless. It means the default answer is the most probable one, not the best justified, and getting the second one is up to you.

## Each kind of knowledge has its evidence

In the previous article I separated five kinds of knowledge: formal, experimental, observational, historical and personal. Each rests on a different kind of evidence, and this is where AI stumbles most. Two mistakes come up again and again:

- **Demanding a formal proof before accepting a historical fact.** No historical fact is proved like a theorem. It's established through remains, documents, testimony and the convergence of several independent traces, and that can give very strong support.
- **Presenting empirical evidence as if it were a logical necessity.** That something has always been observed doesn't make it impossible otherwise.

Logic is involved in both. What changes is how the premises are justified and how strongly the conclusion follows.

I've seen it in my own work. For months I've been building an ontology with AI, a philosophical investigation into what exists and how one thing depends on another ([it's in a public repository](https://github.com/JaviMaligno/god-ontology)). The model kept answering "this doesn't prove X" to well-supported historical conclusions. True, it didn't prove them: they aren't that kind of claim. But the phrase took the place of what needed doing, which was assessing how much support they had and whether any alternative had comparable support. An alternative that is merely conceivable doesn't weigh the same as one with evidence behind it.

We corrected it, and it went into the project's methodology as a written rule. Even so, the same failure came back later in another form: moving on to a new question, the model treated a foundation that had already been justified as if it were a mere interpretation still to be proved from scratch. Having the rule in writing helps a lot, but it doesn't guarantee it gets applied. You still need someone who can recognise the mistake.

## Each study answers a question

Within empirical knowledge there are also different kinds of study, and AI tends to cite them without telling you which is which. They're usually presented as a ladder, with the randomised trial at the top and the survey at the bottom. It's more useful to see them as tools for different questions. None is "the one that tells the truth": each gives a different degree of knowledge, under different conditions.

<style>
.wml-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.wml-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.wml-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

<figure class="wml-fig">
<svg viewBox="0 0 600 326" role="img" aria-label="Six kinds of study, each with the question it answers well and its limit: lab, survey, cohort, case-control, randomised trial and meta-analysis. None is better at everything; each answers a different question.">
<text x="14" y="26" fill="#94a3b8" font-size="12" font-weight="700" letter-spacing="0.04em">KIND OF STUDY</text>
<text x="200" y="26" fill="#94a3b8" font-size="12" font-weight="700" letter-spacing="0.04em">ANSWERS WELL</text>
<text x="410" y="26" fill="#94a3b8" font-size="12" font-weight="700" letter-spacing="0.04em">ITS LIMIT</text>
<rect x="0" y="44" width="600" height="46" rx="6" fill="rgba(255,255,255,0.04)"/>
<text x="14" y="64" fill="#e2e8f0" font-size="13" font-weight="600">Lab and</text><text x="14" y="80" fill="#e2e8f0" font-size="13" font-weight="600">mechanisms</text>
<text x="200" y="64" fill="#5eead4" font-size="13" font-weight="400">How one piece</text><text x="200" y="80" fill="#5eead4" font-size="13" font-weight="400">works</text>
<text x="410" y="64" fill="#fbbf24" font-size="13" font-weight="400">How much it weighs</text><text x="410" y="80" fill="#fbbf24" font-size="13" font-weight="400">in a real person</text>
<text x="14" y="118" fill="#e2e8f0" font-size="13" font-weight="600">Survey</text>
<text x="200" y="110" fill="#5eead4" font-size="13" font-weight="400">What goes together,</text><text x="200" y="126" fill="#5eead4" font-size="13" font-weight="400">at one moment</text>
<text x="410" y="118" fill="#fbbf24" font-size="13" font-weight="400">What causes what</text>
<rect x="0" y="136" width="600" height="46" rx="6" fill="rgba(255,255,255,0.04)"/>
<text x="14" y="164" fill="#e2e8f0" font-size="13" font-weight="600">Cohort</text>
<text x="200" y="156" fill="#5eead4" font-size="13" font-weight="400">What happens</text><text x="200" y="172" fill="#5eead4" font-size="13" font-weight="400">over years</text>
<text x="410" y="164" fill="#fbbf24" font-size="13" font-weight="400">What wasn’t measured</text>
<text x="14" y="210" fill="#e2e8f0" font-size="13" font-weight="600">Case-control</text>
<text x="200" y="202" fill="#5eead4" font-size="13" font-weight="400">Causes of something</text><text x="200" y="218" fill="#5eead4" font-size="13" font-weight="400">uncommon</text>
<text x="410" y="202" fill="#fbbf24" font-size="13" font-weight="400">How the cases</text><text x="410" y="218" fill="#fbbf24" font-size="13" font-weight="400">were chosen</text>
<rect x="0" y="228" width="600" height="46" rx="6" fill="rgba(255,255,255,0.04)"/>
<text x="14" y="248" fill="#e2e8f0" font-size="13" font-weight="600">Randomised</text><text x="14" y="264" fill="#e2e8f0" font-size="13" font-weight="600">trial</text>
<text x="200" y="248" fill="#5eead4" font-size="13" font-weight="400">Whether the intervention</text><text x="200" y="264" fill="#5eead4" font-size="13" font-weight="400">causes the effect</text>
<text x="410" y="248" fill="#fbbf24" font-size="13" font-weight="400">Its duration, dose</text><text x="410" y="264" fill="#fbbf24" font-size="13" font-weight="400">and population</text>
<text x="14" y="302" fill="#e2e8f0" font-size="13" font-weight="600">Meta-analysis</text>
<text x="200" y="294" fill="#5eead4" font-size="13" font-weight="400">What many studies</text><text x="200" y="310" fill="#5eead4" font-size="13" font-weight="400">say together</text>
<text x="410" y="294" fill="#fbbf24" font-size="13" font-weight="400">Inherits the biases</text><text x="410" y="310" fill="#fbbf24" font-size="13" font-weight="400">of what it pools</text>
</svg>
<figcaption>None is "the one that tells the truth". Each design answers one question well and another badly, and what matters is which one is yours.</figcaption>
</figure>

A randomised trial is the best way to know whether an intervention causes an effect, but it usually lasts weeks or months, with a specific dose and a specific population. A cohort study can follow tens of thousands of people for decades, but it doesn't control everything that affects them. For the question "what happens to someone who follows this diet for twenty years?" there is no randomised trial, and there probably never will be.

Underneath there's also a statistical part worth knowing, even intuitively:

- **Every result depends on the assumptions of the statistical model** it was analysed with: what was assumed, which variables were adjusted for and which weren't.
- **A statistically significant effect isn't necessarily a large one.** With huge samples, tiny effects come out significant.
- **A relative risk isn't an absolute risk.** "Doubles the risk" can mean going from 1 in 10,000 to 2 in 10,000.

With this you can ask AI for what matters: what kind of study backs each claim, what question that kind of study answers, and what assumptions sit behind it. On how to evaluate knowledge when these studies aren't enough, or arrive late, I wrote a whole book, [Science Catch-Up](/en/publications).

## Definitions drift

The same mechanism that produces the 7 makes concepts converge on what a word most popularly means, not on its proper definition. In a long conversation you notice it: you pin down a term, the model uses it well for a while and, a few messages later, it's back to the everyday sense.

To handle it, it helps to separate three things that tend to get mixed up:

- **A stipulation**: "in this text, X means this". It's decided, not argued.
- **A description of usage**: how the word is actually used. It's checked.
- **A proposal about the nature of something**: what X really is. It needs arguments.

No definition proves by itself that what it defines exists. Nor does a term's prestige replace a definition you can reason with: in the ontology, the model proposed a classical concept, "ontological perfection", that turned out too broad for the distinction we needed. It had to be broken down into three more precise concepts.

The practical tool is the same as in the previous article: write the definitions that matter into a glossary, or into the project's instructions, so you don't have to repeat them.

## Getting it right isn't knowing the truth

All of the above turns around the same thing. What's hardest for an artificial intelligence is whatever has to do with truth, and I think that's precisely what sets it apart from ours.

A model follows patterns. It accumulates what the data point to and hands it back, without an internal notion of what is true. As it's trained better, it gets better at telling kinds of knowledge apart, because it learns better how we tell them apart. That makes it more useful. But producing correct answers isn't the same as having a relation of its own to truth.

My reason for saying so is theistic, and it's the conclusion of the ontology work, not an add-on:

1. Human beings are created in the image of God, and receive from him their condition as rational subjects.
2. Conferring that condition belongs to God alone. Having it doesn't give us the power to confer it by building something.
3. An AI is an artefact built by human beings.
4. Therefore, building an AI doesn't by itself give it what only God can give.

That's why our reason is oriented towards an objective truth that exists and that we try to reach, and the machine's isn't. The full development, with its objections, is in the [ontology repository](https://github.com/JaviMaligno/god-ontology).

You don't need to share that foundation to draw the practical conclusion. As long as the model has no relation of its own to truth, someone has to have it for it. That someone is you.

## Why philosophy matters again

Put it all together and the list of what's worth knowing to use AI well looks little like a programming course:

- **How a model is trained**, just enough to understand why it pulls towards the most probable.
- **Epistemology**: what kinds of knowledge there are and what evidence counts for each.
- **Scientific method and basic statistics**: what question each kind of study answers and what its assumptions are.
- **Definitions**: when you stipulate, when you describe and when you have to argue.
- **A notion of truth** that doesn't reduce to what most people say.

The more capable models become, the more valuable what they don't ship with: the ability to judge what they produce. That's a philosophical skill, and you don't need to be a philosopher to have it. You only need to learn it well enough to ask the right questions, and to teach it to the people around you.
