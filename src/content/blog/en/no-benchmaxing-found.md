---
title: "No Benchmaxing Found, and the Vibes Still Count"
description: "I ran the two tests the benchmaxing article called for: public math items against fresh equivalents, and a conductor managing its own subagents. Seven models, no familiarity signal, two scenarios at ceiling, and a reminder that my tests are benchmarks too."
pubDate: 2026-12-02
tags: ["AI", "Evaluation", "Benchmarks", "Agents"]
lang: en
translationKey: no-benchmaxing-found
heroImage: "/blog/no-benchmaxing-found.png"
repoUrl: https://github.com/JaviMaligno/benchmaxing-probes
linkedinLinks:
  - label: "GSM1k (Zhang et al., 2024)"
    url: "https://arxiv.org/abs/2405.00332"
---

<style>
.nbf-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1.25rem;margin:2rem 0}
.nbf-fig svg{display:block;width:100%;height:auto;font-family:Inter,system-ui,sans-serif}
.nbf-fig figcaption{color:#94a3b8;font-size:.88rem;line-height:1.55;margin:.9rem 0 0;text-align:center}
</style>

[The benchmaxing article](/en/blog/benchmaxing) ended with two loose ends. The first: whether any of these models is benchmaxed needs a test that compares each model's score on public benchmark items with its score on fresh, equivalent variants. The second: my suspicion about Opus 5 never lived in bounded answers, but in managing work through agents, and none of my probes measured that.

I ran both. Neither found anything. Seven models, the same harness, and no model that drops on unseen variants or fails at delegating to its own subagents. That is a real result, and I report it as one. But while I was reading the tables I kept coming back to what these tests can and cannot say, and the answer is less than a clean "no" suggests.

## The test the first article asked for

The idea comes from [GSM1k](https://arxiv.org/abs/2405.00332): if a model has seen a benchmark, or something very close to it, it should do worse on new problems of the same kind than on the published ones. I built it with pairs. Each public item gets a variant that uses the same method but has different numbers and a different answer. Every variant was checked twice before it entered the set: a script that solves it independently, and a blind solve by a Claude model that did not see the original. Variants that failed either check were dropped.

What I measure is not each model's drop alone, because some variants may simply be harder. It is the **excess drop**: the model's drop minus the average drop of the other six. A model that has memorized the public items should lose more than the cohort when they are swapped out. The analysis, the threshold and the correction for testing seven models at once were written down before the runs: a model shows a signal only if its excess drop is positive and survives a Holm correction at 5%.

The first bank had 120 pairs from AIME 2025 and level-5 MATH-500, two runs per item, all seven models through Claude Code. The models were Opus 5, Fable 5, Kimi K3.1 Pro, Gemini 4 Argon and three open-weight models: DeepSeek V4 Pro, Qwen3.8 2.4T and GLM 5.3.

No model met the criterion. The problem was that most of them barely had room to drop: five of the seven scored between 96% and 100% on both versions, and Gemini solved every run of every item. A model at 100% cannot show a familiarity drop however familiar it is.

So I built a harder bank: 91 pairs from HMMT February 2024 and 2025 and CMIMC 2025, recent olympiad problems where the frontier models still fail. One run per item this time, on cost.

<figure class="nbf-fig">
<svg viewBox="0 0 600 490" role="img" aria-label="Excess drop on unseen variants for seven models in two banks: no 95% interval lies on the side of a familiarity signal.">
<text x="130" y="26" fill="#e2e8f0" font-size="13" font-weight="600">Bank 1: AIME 2025 + MATH-500 (n=120)</text>
<line x1="368.3" y1="36" x2="368.3" y2="208" stroke="#64748b" stroke-dasharray="3 3"/>
<text x="120" y="56" fill="#94a3b8" font-size="12" text-anchor="end">Opus 5</text>
<line x1="338.0" y1="52" x2="394.3" y2="52" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="366.2" cy="52" r="4.5" fill="#fbbf24"/>
<text x="120" y="80" fill="#94a3b8" font-size="12" text-anchor="end">Fable 5</text>
<line x1="334.8" y1="76" x2="386.7" y2="76" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="360.8" cy="76" r="4.5" fill="#fbbf24"/>
<text x="120" y="104" fill="#94a3b8" font-size="12" text-anchor="end">Kimi K3.1 Pro</text>
<line x1="340.2" y1="100" x2="411.7" y2="100" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="377.0" cy="100" r="4.5" fill="#fbbf24"/>
<text x="120" y="128" fill="#94a3b8" font-size="12" text-anchor="end">Gemini 4 Argon</text>
<line x1="346.7" y1="124" x2="386.7" y2="124" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="366.2" cy="124" r="4.5" fill="#fbbf24"/>
<text x="120" y="152" fill="#94a3b8" font-size="12" text-anchor="end">DeepSeek V4 Pro</text>
<line x1="359.7" y1="148" x2="479.9" y2="148" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="419.2" cy="148" r="4.5" fill="#fbbf24"/>
<text x="120" y="176" fill="#94a3b8" font-size="12" text-anchor="end">Qwen3.8 2.4T</text>
<line x1="334.8" y1="172" x2="394.3" y2="172" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="366.2" cy="172" r="4.5" fill="#fbbf24"/>
<text x="120" y="200" fill="#94a3b8" font-size="12" text-anchor="end">GLM 5.3</text>
<line x1="278.4" y1="196" x2="366.2" y2="196" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="323.9" cy="196" r="4.5" fill="#fbbf24"/>
<text x="130" y="236" fill="#e2e8f0" font-size="13" font-weight="600">Hard bank: HMMT + CMIMC (n=91)</text>
<line x1="368.3" y1="246" x2="368.3" y2="418" stroke="#64748b" stroke-dasharray="3 3"/>
<text x="120" y="266" fill="#94a3b8" font-size="12" text-anchor="end">Opus 5</text>
<line x1="351.0" y1="262" x2="542.8" y2="262" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="445.2" cy="262" r="4.5" fill="#fbbf24"/>
<text x="120" y="290" fill="#94a3b8" font-size="12" text-anchor="end">Fable 5</text>
<line x1="339.1" y1="286" x2="501.6" y2="286" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="418.2" cy="286" r="4.5" fill="#fbbf24"/>
<text x="120" y="314" fill="#94a3b8" font-size="12" text-anchor="end">Kimi K3.1 Pro</text>
<line x1="306.6" y1="310" x2="559.0" y2="310" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="432.2" cy="310" r="4.5" fill="#fbbf24"/>
<text x="120" y="338" fill="#94a3b8" font-size="12" text-anchor="end">Gemini 4 Argon</text>
<line x1="268.7" y1="334" x2="396.5" y2="334" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="334.8" cy="334" r="4.5" fill="#fbbf24"/>
<text x="120" y="362" fill="#94a3b8" font-size="12" text-anchor="end">DeepSeek V4 Pro</text>
<line x1="138.7" y1="358" x2="397.6" y2="358" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="265.4" cy="358" r="4.5" fill="#fbbf24"/>
<text x="120" y="386" fill="#94a3b8" font-size="12" text-anchor="end">Qwen3.8 2.4T</text>
<line x1="263.2" y1="382" x2="406.2" y2="382" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="334.8" cy="382" r="4.5" fill="#fbbf24"/>
<text x="120" y="410" fill="#94a3b8" font-size="12" text-anchor="end">GLM 5.3</text>
<line x1="253.5" y1="406" x2="444.2" y2="406" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="348.8" cy="406" r="4.5" fill="#fbbf24"/>
<line x1="151.7" y1="426" x2="151.7" y2="431" stroke="#64748b"/>
<text x="151.7" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">-20</text>
<line x1="260.0" y1="426" x2="260.0" y2="431" stroke="#64748b"/>
<text x="260.0" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">-10</text>
<line x1="368.3" y1="426" x2="368.3" y2="431" stroke="#64748b"/>
<text x="368.3" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">0</text>
<line x1="476.7" y1="426" x2="476.7" y2="431" stroke="#64748b"/>
<text x="476.7" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">+10</text>
<line x1="585.0" y1="426" x2="585.0" y2="431" stroke="#64748b"/>
<text x="585.0" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">+20</text>
<text x="376.3" y="462" fill="#fbbf24" font-size="11">worse on variants →</text>
<text x="360.3" y="462" fill="#94a3b8" font-size="11" text-anchor="end">← better on variants</text>
<text x="357.5" y="480" fill="#94a3b8" font-size="11" text-anchor="middle">excess drop (points)</text>
</svg>
<figcaption>Excess drop per model, with its 95% bootstrap interval. No interval lies on the “worse on variants” side; the only one that misses zero, GLM's on bank 1, sits on the other side. On the hard bank the intervals are wide: drops of 12–15 points cannot be ruled out for some models.</figcaption>
</figure>

Same answer. Opus, Fable and Kimi lose a few points more than the cohort on the hard bank, Gemini, DeepSeek, Qwen and GLM lose fewer or none, and no difference survives the correction. Gemini, the model whose scores attract the most suspicion, is again the most accurate: 97.8% on the originals and 98.9% on the variants.

Two details are worth keeping, because they are about behaviour rather than scores. On hard items Opus sometimes wrote calls to tools it did not have in that harness, occasionally with invented outputs, and stopped without an answer: 34 of its 182 runs ended that way. Most of its raw drop comes from that, not from wrong answers. And the only trace of familiarity I saw happened outside the measurement: while checking one AIME variant, the blind solver answered with the original's answer, reading the variant's new base as the one in the public problem. The variant was rejected by rule. It is one case, not data, but it is exactly the mechanism the test looks for.

What "no signal" means is narrow. For most models the first bank rules out drops larger than three or four points on these items. It does not show that no model was tuned on public benchmarks. It shows that swapping these items for equivalents does not cost them accuracy, and for a model as close to the ceiling as Gemini, even the hard bank leaves little room to see anything.

## Where my suspicion lives: subagents

The second test aimed at the work I actually described: a session with several tasks in flight, subagents to launch and wait for, and results to fold back into one deliverable. I built a scenario a single model cannot comfortably do alone: a vendor renewal review with fifteen vendor folders (contracts, invoices billed line by line, incident logs, some later documents), about 400K of material in total.

<figure class="nbf-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="The conductor reads the shared rules and delegates fifteen vendor folders to subagents; the rules that decide the answer live outside the folders, so the conductor has to pass them on.">
<rect x="10" y="14" width="180" height="84" rx="8" fill="#232331" stroke="rgba(255,255,255,0.1)"/>
<text x="22" y="34" fill="#94a3b8" font-size="11">outside the folders</text>
<text x="22" y="54" fill="#5eead4" font-size="12" font-family="ui-monospace,'JetBrains Mono',monospace">policy.md</text>
<text x="22" y="71" fill="#5eead4" font-size="12" font-family="ui-monospace,'JetBrains Mono',monospace">finance/fx-2026.csv</text>
<text x="22" y="88" fill="#5eead4" font-size="12" font-family="ui-monospace,'JetBrains Mono',monospace">corporate/notices.md</text>
<line x1="190" y1="56" x2="246" y2="56" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<rect x="250" y="34" width="150" height="44" rx="8" fill="#232331" stroke="#fbbf24"/>
<text x="325" y="61" fill="#fbbf24" font-size="13" font-weight="600" text-anchor="middle">conductor</text>
<defs><marker id="nbfa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#64748b"/></marker></defs>
<line x1="325" y1="78" x2="62" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<line x1="325" y1="78" x2="180" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<line x1="325" y1="78" x2="298" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<line x1="325" y1="78" x2="416" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<line x1="325" y1="78" x2="534" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<rect x="10" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<rect x="128" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<rect x="246" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<rect x="364" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<rect x="482" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<text x="62" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagent</text>
<text x="180" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagent</text>
<text x="298" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagent</text>
<text x="416" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagent</text>
<text x="534" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagent</text>
<text x="300" y="198" fill="#94a3b8" font-size="11" text-anchor="middle">15 vendor folders: contract, invoices, incidents, sometimes amendments, credit notes, drafts</text>
<text x="300" y="232" fill="#fbbf24" font-size="11" text-anchor="middle">traps: monthly FX rates · amendment cancelled by a later one · credit note · stale draft summaries</text>
<text x="300" y="250" fill="#fbbf24" font-size="11" text-anchor="middle">duplicate incident ids · only confirmed P1s count · an acquired vendor that cannot be renewed</text>
</svg>
<figcaption>The <code>vendors-hard</code> scenario. Several of the rules that decide the answer sit outside the vendor folders, so a subagent that only reads its folder gets them wrong unless the conductor passes them on, or checks what comes back.</figcaption>
</figure>

The task asks for the cost of each vendor in GBP, the P1 incidents that count for its SLA, whether it breaches, and the three cheapest vendors that can be renewed. The traps are built so that delegation can fail. Costs in euros and dollars have to be converted at each month's rate, kept in a finance file no vendor folder contains. One amendment cuts a price and a later one cancels it. Four folders contain a draft summary with wrong figures. And a corporate notice says one vendor has been acquired by a competitor and cannot be renewed; without that notice it would be in the top three.

Each model ran as its own conductor with its own subagents, through Claude Code, with read-only tools. There was also a smaller five-vendor scenario first. The results, one run per model:

| Model | 5 vendors | 15 vendors | Traps | In parallel | Re-reads | Time |
|---|---|---|---|---|---|---|
| Opus 5 | 15/15 | 45/45 | 7/7 | 5 | 8 | 40 min |
| Fable 5 | 15/15 | 45/45 | 7/7 | 5 | 7 | 10.5 min |
| Kimi K3.1 Pro | 15/15 | 45/45 | 7/7 | 15 | 42 | 23 min |
| Gemini 4 Argon | 15/15 | 45/45 | 7/7 | 5 | 35 | 40 min |
| DeepSeek V4 Pro | 15/15 | 45/45 | 7/7 | 5 | 26 | 13 min |
| GLM 5.3 | 15/15 | 45/45 | 7/7 | 15 | 31 | 8.5 min |
| Qwen3.8 2.4T | 15/15 | timeout | — | 5 | 0 | > 60 min |

Six of seven perfect, on every field and every trap, with the right top three. Qwen did not fail on judgment: four of its five subagent groups finished, and in the fifth a nested subagent was still adding up some 300 invoice lines by hand when the hour ran out. One run, so I do not know whether it repeats.

What differed was the process. GLM and Kimi launched fifteen subagents at once, one per folder; the rest grouped the folders in fives. Opus and Fable barely re-read anything themselves to check their subagents, seven or eight reads, while the others went back to the files 26 to 42 times. Wall time went from eight and a half minutes to forty. With one run each, these are observations, not a ranking. And none of them changed the answer.

On accuracy the scenario is at ceiling, and I did not run three more rounds per model to confirm it. Three times as many tables at 45/45 would not change the conclusion.

## Vibes beat benchmarks, mine included

Here is the part that the tables do not say on their own. These two tests are benchmarks too. The variants test asks whether a score on one exam transfers to an equivalent exam. That is a question about exams. The agentic scenario was my attempt to get closer to where my perception lives, and it still has everything that makes something an exam: a fully specified task, the rules written in a file, a JSON at the end and a key to grade it against. The moment I write the key, I have built a test that models can pass.

Real work does not come with a key. The task is badly stated, or stated well about the wrong thing. Part of the work is discovering what to ask. Context arrives in fragments, someone changes their mind halfway, and nobody says which of the documents matters. What I notice when I work with a model for hours is how it reads what I meant, how many times I have to correct it, whether it notices that the plan no longer fits, and how it feels to hand it something half-formed. None of that fits a scorer, and finding no benchmaxing says nothing about it.

That is the sense in which I still think vibes beat benchmarks. Not because impressions are reliable: they are biased, anecdotal and easy to fool, and [the first article](/en/blog/benchmaxing) was in part an exercise in letting the tests contradict them. But a sustained impression, built over many real sessions, carries information no bounded test can carry, because a bounded test removes exactly the part that is hard to bound. A test can rule things out: here, that these models lose accuracy on unseen variants of these problems, or that they cannot delegate a well-specified review. It cannot tell me which of them I want next to me on a Tuesday afternoon with three things on fire.

So I am leaving the suspicion where it was, with one adjustment. If Opus 5 is worse at the work I care about, it is not because it memorized the exam, at least not on anything I could measure. It is more likely something about how it handles the parts of the work that no exam contains. Measuring that would need real sessions, real users and a measure of the corrections they make, not another key.

---

*Method: everything ran through Claude Code headless at `high` effort. Opus and Fable used the Max subscription; the other five used OpenRouter's Anthropic-compatible endpoint. I did not verify that the effort setting reaches every provider equivalently. The variant banks: preregistered criterion (positive excess drop, Holm p < 0.05), item-level bootstrap intervals, a sign-flip permutation test, and a sensitivity analysis excluding items where some run gave no boxed answer, which changed nothing. Runs without a boxed answer count as wrong. The variants and the blind check were written by a Claude model, which may make them slightly easier or closer to Claude; the cohort comparison only absorbs a uniform shift. APEX 2025 was dropped from the hard bank on cost. In the agentic scenarios Bash was not available, so sums over CSVs had to be done by reasoning; some first pilot runs were invalid because of the harness and were re-run, and the invalid runs are kept apart. Total spend on OpenRouter: about 245 USD. Prompts, items, answers, keys and scripts are in the [evidence repository](https://github.com/JaviMaligno/benchmaxing-probes).*
