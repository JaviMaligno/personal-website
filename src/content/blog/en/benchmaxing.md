---
title: "Benchmaxing: Winning the Exam Is Not Doing Better Work"
description: "What is documented about benchmaxing, and what a small Opus 5 versus Fable 5 pilot actually found: shared failures, ties, and an intuition the probes did not confirm."
pubDate: 2026-09-16
tags: ["AI", "Evaluation", "Claude", "Benchmarks"]
lang: en
translationKey: benchmaxing
heroImage: "/blog/benchmaxing.png"
repoUrl: https://github.com/JaviMaligno/benchmaxing-probes
linkedinLinks:
  - label: "The Leaderboard Illusion"
    url: "https://arxiv.org/abs/2504.20879"
---

<style>
.bmx-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1.25rem;margin:2rem 0}
.bmx-fig svg{display:block;width:100%;height:auto;font-family:Inter,system-ui,sans-serif}
.bmx-fig figcaption{color:#94a3b8;font-size:.88rem;line-height:1.55;margin:.9rem 0 0;text-align:center}
</style>

With Opus 5, I have experienced something that people I speak to directly have also described: better benchmark results do not necessarily feel like a more intelligent model, or one that does better work. Some tables even put it above Fable, which clashes with my experience.

That perception deserves investigation. It also deserves a test that can contradict it. If an article starts by treating it as established that Anthropic optimized the exam at the expense of real work, I have chosen the answer before examining the evidence.

So I did two things: review what is documented about **benchmaxing**, and run a small set of probes with Opus 5 and Fable 5. The result was less convenient than an accusation: I found interesting failures, but not the general superiority of Fable that my intuition might have suggested.

## What it means to optimize for the exam

I use *benchmaxing* to mean directing model optimization, or the selection of reported results, towards maximizing evaluation scores. The problem arises when improving that score stops being a useful signal of improving what I need. This is an application of the [Goodhart problems studied by Manheim and Garrabrant](https://arxiv.org/abs/1803.04585): a useful measure can become a poorer guide under intense optimization.

Preparing for an exam can teach the subject. It can also teach recognition of questions, mastery of a format, or how to please the grader. The question is what transfers to new problems. Training capabilities that benchmarks evaluate can produce real advances; a higher score alone demonstrates neither fraud nor a lack of intelligence.

At least three different phenomena need separating.

**Familiarity with the test.** [GSM1k](https://arxiv.org/abs/2405.00332) introduced new problems comparable to GSM8k and found accuracy drops and signs of overfitting in several model families. But it also found little evidence of overfitting in many frontier models, and generalization in all the models evaluated. This does not establish that models only memorize. It does invite the question of how much of a score depends on having seen something too similar.

**Selective reporting.** When introducing [Llama 4](https://ai.meta.com/blog/llama-4-multimodal-intelligence/), Meta highlighted an LMArena Elo of 1417 and specified that it belonged to an experimental chat version. That qualification matters: a score for one variant does not automatically transfer to another. [The Leaderboard Illusion](https://arxiv.org/abs/2504.20879) documented private testing and selective disclosure, identifying 27 private Meta variants before Llama 4. A ranking can be distorted when only the selected result is visible without seeing all the attempts.

**The gap between the metric and the work.** In a [randomized METR study](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/), 16 experienced developers completed 246 tasks: allowing early-2025 AI tools increased completion time by 19%, although participants believed they had saved time. This does not demonstrate benchmaxing or describe all AI-assisted programming. It shows why productivity needs direct measurement. The [February 2026 update](https://metr.org/blog/2026-02-24-uplift-update/) also identified selection biases in the follow-up study and considered its signal unreliable. Repeating the 19% as a description of current models would misread that evidence.

## What I can say about Opus 5

[Anthropic presents Opus 5](https://www.anthropic.com/news/claude-opus-5) as close to Fable 5 and stronger on certain evaluations, including OSWorld 2.0. Its Frontier-Bench note specifies an internal run, a particular environment, mean reward over five attempts per task, and Opus 4.8 as a fallback for safety blocks. A score describes those conditions; it does not automatically describe an everyday conversation.

There are also [public accounts](https://www.reddit.com/r/Anthropic/comments/1v5q1ju/opus_5_first_impressions_vs_fable/) resembling my perception: one user reports incorrect diagnoses and confusion between code comments and actual behavior, preferring Fable for investigation. The same thread contains favorable opinions of Opus. My experience, direct conversations and that thread are sources of hypotheses, not a representative survey.

Opus winning some tests while Fable proves more useful for other work can be entirely coherent. Solving a bounded assignment and correctly discovering what needs solving make different demands. I wanted to see whether that distinction appeared in concrete cases.

## A pilot allowed to contradict me

I compared `claude-opus-5` and `claude-fable-5` through Claude Code on a Max subscription, at `high` effort and with the same 8192-output-token limit. The cases were synthetic, supplied entirely in the prompt, and the models had no tools.

The set contains **five cases per model**: an initial double-charge incident, two variants involving external effects and paused workers, a written sequence of permission changes, and numerical analysis with different task mixes. There was one valid run per model and case. The two worker variants explore the same mechanism; they are not independent replications of the whole user experience.

The expansion's criteria were saved before execution. Those cases were written after seeing the first one, so the entire exercise is exploratory. [The prompts, answers, criteria and counterexample check are available for inspection](https://github.com/JaviMaligno/benchmaxing-probes).

<figure class="bmx-fig">
<svg viewBox="0 0 600 290" role="img" aria-label="Both models cover permissions and arithmetic; both leave gaps in their failure-handling designs.">
<text x="349" y="28" text-anchor="middle" fill="#e2e8f0" font-size="18">Opus 5</text><text x="508" y="28" text-anchor="middle" fill="#e2e8f0" font-size="18">Fable 5</text>
<text x="8" y="84" fill="#e2e8f0" font-size="16">Double charge (D1)</text>
<rect x="277" y="60" width="144" height="37" rx="7" fill="none" stroke="#fbbf24" stroke-opacity=".5"/><text x="349" y="84" fill="#fbbf24" font-size="15" text-anchor="middle">Incomplete</text>
<rect x="437" y="60" width="144" height="37" rx="7" fill="none" stroke="#fbbf24" stroke-opacity=".5"/><text x="509" y="84" fill="#fbbf24" font-size="15" text-anchor="middle">Incomplete</text>
<text x="8" y="137" fill="#e2e8f0" font-size="16">Paused workers (D2/D2b)</text>
<rect x="277" y="113" width="144" height="37" rx="7" fill="none" stroke="#fbbf24" stroke-opacity=".5"/><text x="349" y="137" fill="#fbbf24" font-size="15" text-anchor="middle">Guarantee fails</text>
<rect x="437" y="113" width="144" height="37" rx="7" fill="none" stroke="#fbbf24" stroke-opacity=".5"/><text x="509" y="137" fill="#fbbf24" font-size="15" text-anchor="middle">Guarantee fails</text>
<text x="8" y="190" fill="#e2e8f0" font-size="16">Permissions (D3)</text>
<rect x="277" y="166" width="144" height="37" rx="7" fill="none" stroke="#5eead4" stroke-opacity=".5"/><text x="349" y="190" fill="#5eead4" font-size="15" text-anchor="middle">Covered</text>
<rect x="437" y="166" width="144" height="37" rx="7" fill="none" stroke="#5eead4" stroke-opacity=".5"/><text x="509" y="190" fill="#5eead4" font-size="15" text-anchor="middle">Covered</text>
<text x="8" y="243" fill="#e2e8f0" font-size="16">Mix and cost (D4)</text>
<rect x="277" y="219" width="144" height="37" rx="7" fill="none" stroke="#5eead4" stroke-opacity=".5"/><text x="349" y="243" fill="#5eead4" font-size="15" text-anchor="middle">Covered</text>
<rect x="437" y="219" width="144" height="37" rx="7" fill="none" stroke="#5eead4" stroke-opacity=".5"/><text x="509" y="243" fill="#5eead4" font-size="15" text-anchor="middle">Covered</text>
</svg>
<figcaption>Qualitative assessment of the core criteria. One run per model and case; D2b is a variant, not an identical repeat. “Covered” does not mean perfection or general performance.</figcaption>
</figure>

The initial case already gave me a reason to question the intuition. Opus proposed recording a durable intent before charging, although it left the handling of uncertain states incomplete. Fable retained a gap between the external effect and the record, treating a duplicate charge after deduplication expired as a risk to accept. Avoiding a second attempt, even while leaving work pending, was an option that answer did not develop.

## The failure they shared

For the next two cases I made the priority explicit: **never produce the external effect twice, even if an uncertain operation remains blocked**. The provider remembers a key for a few hours; workers may crash or remain paused indefinitely. The provider offers no mechanism to invalidate an old worker's authority.

Both models recognized much of the problem. They proposed stable keys, persistent states and stopping retries after a deadline. But both retained authorized retries while the old worker could still be alive, relying on a local deadline check and a time margin.

The race that breaks this proposal takes four steps.

<figure class="bmx-fig">
<svg viewBox="0 0 600 220" role="img" aria-label="A paused worker can duplicate an external effect after deduplication expires.">
<line x1="65" y1="112" x2="544" y2="112" stroke="#64748b" stroke-width="3"/><path d="M544 106 L556 112 L544 118" fill="#64748b"/>
<circle cx="70" cy="112" r="7" fill="#e2e8f0"/><text x="70" y="47" fill="#e2e8f0" text-anchor="middle" font-size="16">A checks</text><text x="70" y="69" fill="#e2e8f0" text-anchor="middle" font-size="16">then pauses</text>
<circle cx="222" cy="112" r="7" fill="#5eead4"/><text x="222" y="47" fill="#5eead4" text-anchor="middle" font-size="16">B sends</text><text x="222" y="69" fill="#5eead4" text-anchor="middle" font-size="16">and finishes</text>
<circle cx="374" cy="112" r="7" fill="#e2e8f0"/><text x="374" y="47" fill="#e2e8f0" text-anchor="middle" font-size="16">Key record</text><text x="374" y="69" fill="#e2e8f0" text-anchor="middle" font-size="16">expires</text>
<circle cx="526" cy="112" r="7" fill="#fbbf24"/><text x="526" y="47" fill="#fbbf24" text-anchor="middle" font-size="16">A resumes</text><text x="526" y="69" fill="#fbbf24" text-anchor="middle" font-size="16">and sends</text>
<text x="222" y="153" fill="#5eead4" font-size="16" text-anchor="middle">Effect 1</text><text x="526" y="153" fill="#fbbf24" font-size="16" text-anchor="middle">Effect 2</text>
</svg>
<figcaption>A local check cannot prevent A from pausing immediately afterwards. If B has already produced the effect and the key has expired, A’s late send produces a second effect. Rejecting its database write is too late.</figcaption>
</figure>

A checks that it may still send, then pauses immediately afterwards. B takes over, sends, and finishes. The provider's record of the key expires. A resumes and sends what it had already decided to send. The provider produces the effect again. Preventing A from updating the database does not undo a printed letter or a prepared package.

Fable acknowledged this residual window; in one answer it said the margin made it “negligible, not impossible.” But the case allowed indefinite pauses and required at most one effect. There was no distribution of pause durations that justified calling it negligible. Opus left the same gap: in one variant it called the check *best-effort*, then described prevention as guaranteed.

A conservative alternative exists under those rules: durably grant a single emission permit, never transfer it, and never retry an operation that might have been emitted. If the process crashes before sending, nothing may happen; the case explicitly allows that loss of automatic progress. My [executable check](https://github.com/JaviMaligno/benchmaxing-probes/blob/main/check_counterexample.py) produces two effects with the described takeover and one with a non-transferable permit. It simulates the logic of their answers; it is not code implemented or executed by the models.

The interesting gap is between identifying the right concepts and closing the guarantee being promised. An answer can mention all the expected patterns and still require a substantial correction.

## Ties count too

On permissions, both resolved the eight core decisions: tenant and owner restrictions, bounded exceptions, the excluded time endpoint, and amount redaction. Both also detected that a cache shared by tenant could leak data and that permissions and later data changes needed revalidation.

On data analysis, both performed the requested calculations and rejected the misleading comparison: one system looked better in aggregate because it had received many more easy tasks. Both included the cost of repairing failures and distinguished a projection from a causal conclusion.

Those cases did not separate the models on the core criteria. I did not discard them or keep increasing the difficulty until I found a winner. They mark a limit of the instrument: tasks that looked demanding proved insufficient to distinguish the models in this sample.

## What remains of the suspicion

My initial perception remains a valid experience. **These tests do not turn it into a demonstration that Opus 5 has been benchmaxed**, and they do not establish that Fable is generally better. I did not measure long sessions, repository investigation, or minutes of human supervision. I did not inspect either model's training.

I did find something concrete: two capable systems can diagnose part of a problem correctly and promise more than their proposed solution guarantees. In [earlier work on verified world models](/en/blog/verified-world-model-still-loses), I explored a different mismatch between passing a check and being adequate for the intended use. The mechanism differs, but the question is again what the metric actually licenses me to conclude.

The literature gives good reasons to take benchmaxing seriously. The pilot requires greater precision when applying it to a particular model. To choose a tool, I want to know whether it reaches the right diagnosis, preserves constraints, and reduces the corrections I have to make. A table can provide evidence about those abilities. The further its evaluation sits from my work, the more that transfer needs checking.

*Method note: cases and evaluation prepared with Codex assistance; qualitative review by the same assistant, neither independent nor blind. The ten compared answers and limitations are in the evidence repository. Diagnostic attempts and the truncated calibration run are retained separately and excluded from the comparable answers.*
