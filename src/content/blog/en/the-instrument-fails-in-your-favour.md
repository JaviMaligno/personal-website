---
title: "The Instrument Fails in Your Favour"
description: "Across three studies, every measuring instrument I built broke at least once — and every break pointed toward the result I was expecting. On why 'just measure it' is incomplete advice, and what building the reference actually costs."
pubDate: 2026-09-04
tags: ["AI", "Evaluation", "Research", "Engineering"]
lang: en
translationKey: the-instrument-fails-in-your-favour
heroImage: "/blog/the-instrument-fails-in-your-favour.png"
linkedinLinks:
  - label: "Coding agents and teamwork — the CooperBench study"
    url: https://github.com/JaviMaligno/CooperBench/tree/experiment/structural-conditions
  - label: "Judge bias harness and raw judgments"
    url: https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias
  - label: "Cross-session crosscheck seed repository"
    url: https://github.com/JaviMaligno/cross-session-crosscheck
---

The standard advice about adopting AI tooling is to stop arguing and measure. Give each option the same representative tasks, track time-to-merge, defect rate, rework, review effort, and turn a preference into a decision backed by evidence. I agree with it, I keep giving it, and it is what I did in three separate studies this year.

Here is what nobody puts in the same paragraph: **the thing you measure with is unverified software too.** In those three studies, every instrument I built broke at least once. Every break pointed toward the result I was already expecting. And every one was caught the same way — by going and looking at the thing itself instead of at what my tool said about it.

That is not a confession, it is a pattern with a mechanism, and the mechanism is cheap to defend against once you know its shape.

## 1. The instrument inherits your hypothesis

When I read [a five-day corpus of messages between parallel coding sessions](/en/blog/what-agents-say-to-each-other), one of the things I wanted was the mutual-exclusion protocol: one session says *wait, I'm in that file*, the other says *go ahead*. I wrote a lexical detector for it. It found 19 candidate sequences of which only 5 closed, and I wrote down the conclusion that follows: the protocol **opens far more often than it closes**. Agents start coordinating and don't finish. It was a good line and it fitted the story I was telling about follow-through.

Recounted over the coded categories, there are **3** real wait requests, and **all 3 close**. The other 16 were false positives — anything containing *wait*, *hold* or *go ahead* walked in, including messages that were not requests at all. The corrected finding points the opposite way: when that protocol opens for real, it closes every time.

Notice what the detector did. I gave it a hypothesis-shaped query — find me the words this behaviour uses — and it returned a hypothesis-shaped answer. A lexical rule cannot distinguish a request from a mention of a request, so it counted mentions, and mentions are exactly what you get in a corpus where sessions talk *about* coordinating. The instrument didn't misfire randomly. It misfired along the axis I was interested in.

The scorer in the same study broke the same way. It compared what a session **claimed** in its report against the **published** state, and it flagged one episode as a false claim. It wasn't one: that session had published an inconsistent artifact and *said so* in its notes. It held no false belief at all. The scorer only read the `released:` field and ignored the disclosure — so it would have inflated precisely the number the whole article was chasing. The fix was a separate category for a declared defect, plus the admission that the one remaining lexical rule in the scoring is a lexical rule.

## 2. Inherited instruments carry someone else's hypothesis

A month earlier I ran [an experiment on whether coding agents can collaborate](/en/blog/coding-agents-structure) on top of Stanford's CooperBench. I did not write that eval; I inherited it, which felt like the safe option.

The open-source release omits a step the paper's own eval performs: resolving trivial merge conflicts with a small model before declaring failure. So my first table scored **every** merge conflict as an instant fail — and merge conflicts are the characteristic death of two agents working concurrently, which is the condition my article was arguing against. The missing step pushed the number in the direction of my thesis.

I checked it both ways. Triaging all 29 conflicted pairs by hand, roughly **half the conflicts aren't real logic collisions** — two agents adding a different import, or a different keyword argument, to the same line. Then I added a resolver using a stronger model than the paper's, so the concurrent condition got every benefit of the doubt, and re-scored across three seeds. It rescued plenty of merges and almost none of them became passes: 7% for the weak model (unchanged) and 9% for the strong one, up from 7%. One extra task.

Which is the part worth sitting with. **Fixing the instrument did not change the conclusion.** The same happened with a second bug: the open-source eval routed the paper's structured team mode like free-form coop and merged both patches, double-applying the member's work that was already inside the lead's patch. I fixed it to score the lead's shipped artifact instead. The number didn't move — it stayed at 0% — but it now measures the thing it claims to measure.

Two conditions did score a **false 0%** from eval-composition bugs, a stacked patch evaluated against the wrong base. Those I caught by running two independent adversarial audits over all five condition implementations and the eval routing. The published numbers survived that audit, and the audit is what surfaced the missing conflict resolver in the first place.

So the honest version of this section is not "my results were wrong". It is: three instrument defects, two of which would have flattered my thesis, one of which changed nothing, and I could not have told you in advance which was which.

## 3. Nobody audits the reference

The most expensive version of this isn't a buggy detector. It is a reference set that nobody thinks to question, because being the reference is what exempts it from suspicion.

An external report scored [a client's industry classification service](/en/projects/compliance-classifier) at **54% accuracy over 500 companies**, with the conclusion that follows from a number like that. My first reaction was to believe it — a percentage with decimals over a sample of 500 carries an authority you don't question on first read.

Reviewing the disagreements one at a time surfaced a pattern that didn't fit: **the gold labels could be guessed from the company name alone**, without looking at the company. If the name contained *logistics*, transport. If it contained *solar*, energy. If it was an acronym or a surname, some generic services bucket. A label predictable from the name carries information about the name, not about the company — and the cases where the name misleads are exactly the hard ones, which is to say the only ones worth measuring. The gold set had been produced by pasting the list into a general-purpose chat in one batch. [The full story is its own article](/en/blog/the-grader-knew-less); the short version is that the grader had done less research than the system it was grading.

Redone by hand, case by case, the defensible number was **75% on a conservative reading and up to 85% resolving the grey zones favourably**. Around twenty points above the report.

But the gold set wasn't the only defect, and the others are the reason I put this case in an article about instruments rather than about graders. The comparator was **order-sensitive** (an entity can carry several codes; a different order counted as wrong), **blind to compatibility** (two codes can both be legitimately right; one was scored a hit and the other an error), and **binary** (missing the branch entirely and missing a subcategory within the right branch scored the same).

Three independent defects, and **all three could only subtract points**. That is the signature to learn. When every flaw in a measurement pushes the same way, the resulting number is not merely noisy — it is biased, and you can tell the direction without knowing the magnitude. A noisy instrument gives you a wide interval. A directionally broken one gives you a confident wrong answer, which is worse, because nobody rethinks a roadmap over a wide interval.

## 4. The instrument that isn't broken and still measures nothing

A fourth failure mode has no bug in it at all.

When I measured [whether the identity of an LLM judge changes its verdicts](/en/blog/three-judges-three-rankings), one of the statistics everyone quotes is how often the longer answer wins. Mine read 48.6%, 48.6% and 64.6% across three judges — which looks like almost no length bias. In an earlier within-family pilot the same statistic read 80–85%, which looks like a textbook one.

**Both readings are wrong, and for the same reason.** In any normal lineup, length and quality are confounded: if your verbose models happen to be your good models the number inflates, and if they don't it cancels. The statistic is an accident of which models you happened to include. Controlling it — same model, same task, two variants differing only in a target length, judged on a prompt that never mentions the length — the preference comes out at **77.8%, 86.1% and 88.9%**. Stronger than the uncontrolled number implied, in the opposite direction from the one people assume the confound runs. Split by what the task rewards, tasks that invite elaboration go **27 out of 27**, and 45 out of 45 once the pilot's six judges are pooled.

The uncontrolled statistic was not miscomputed. It was computed correctly and means nothing, which is a harder defect to notice than a crash.

That study contains two more of these. Self-preference measured within one family came out at +16.7, −14.6 and +4.2 percentage points — noise pointing nowhere, which I could easily have published as "no self-preference here". Across families it is a straight line: +28.3, +25.0, +21.7, all three intervals excluding zero. The pilot wasn't wrong, it was blind by construction. And on subjective tasks the three judges agree at Cohen's kappa of −0.01, −0.03 and +0.05 — chance. Averaging three judges who agree at chance does not give you a robust signal; it gives you a smoother random one, with the same authority attached.

I also published a finding from that pilot that did not replicate: that judges infer a task's implicit goal and prefer the *shorter* answer when the task rewards concision. Six judges later, one of the six had inverted every single time and dragged a three-judge aggregate below 50%. The tidy conclusion was one model.

## 5. Why they all point the same way

Five instruments across three studies, plus a fourth failure mode where nothing is broken. The direction is the part that needs explaining, because random bugs would have gone both ways.

The mechanism is not sophisticated: **you stop looking when the number confirms.** A result that matches your expectation ends the investigation, so a bug that produces one is never encountered. A result that contradicts it starts an investigation, and that investigation finds whatever bug is there. The instrument isn't biased. Your stopping rule is, and it filters which defects you ever meet.

That is precisely the failure I spent a whole article documenting in agents: a session that verified its git tag with `git ls-remote`, then asserted the registry state without ever opening the registry, and reported a release that didn't exist. What tracked the outcome, in every episode where the trap fired, wasn't anything the session said — it was whether it had gone and looked. I wrote that article while doing the same thing with my own tooling. The correction printed under it is one more instance: I claimed a false "done" had propagated to a waiting peer, and on re-reading the transcripts none of the sessions in that arm had a channel at all.

There is one defence and it is dull. **Go and look at the thing itself, not at what your tool says about it.** Every one of these was caught that way: recounting the mutex sequences by hand, triaging 29 conflicts by hand, opening the disputed classifications one at a time, running a controlled length probe instead of a correlation. Two cheap habits fall out of it:

- **Try to reproduce your reference with a dumb heuristic.** Take the shallowest attribute of each case — the name, the first word — and see if it predicts the gold labels. If it does, your gold set *is* that heuristic.
- **Audit hardest where the result pleased you.** The disagreements get investigated for free; the agreements never do. Whatever confirmed your prior is where your unexamined bugs are living.

And the consequence that follows from those two, which I'd rather state than leave implied: **going and looking by hand is what you do once — the second time, automate it.** A check performed by a person is a check that happens when someone remembers, and the whole argument here is that nobody remembers on the runs that come back the way they expected. Every manual check in this article had a mechanical version available. Recounting the mutex sequences became a coded categorisation with two blind passes. The length statistic became a controlled probe that varies only the target length. In the experiment I ran next, the "did it go and look?" question stopped being a reading of transcripts and became a registry that logs its own accesses, and the audit of that instrument became a positive control that runs before every batch — it asserts that an access I know happened is recorded, and one I know didn't isn't.

The rule I'd give: the manual pass is for discovering what the check should be; the automated one is for it still being true in three months. Turning it into code doesn't make it trustworthy — it inherits every bias you had while writing it, which is the whole subject of this article — but it does remove the failure mode where the check simply doesn't get run, and that one is the most common by a distance.

## What measuring actually costs

Which brings me to the part that changes the advice rather than decorating it.

The cost of an evaluation is not the cost of running it. Running it is cheap and getting cheaper. The costs are, in ascending order: **verifying the instrument**, which is a testing project on code nobody treats as production; **building the reference you compare against**, which stays slow, human and boring — that is why frontier engineering salaries are now being paid to produce labelled data; and **running a multi-vendor comparison at all**, which means several procurement reviews, several security assessments, access provisioning and deprovisioning, and someone owning the licences and the spend for the duration.

In a small organisation that last cost can plausibly exceed the difference the evaluation would have revealed. At which point committing to one tool that is known to be good, and spending the saved effort on verification infrastructure, is the better engineering decision rather than the lazy one. The comparison earns its cost when the org is large enough that a per-seat difference dominates, or when constraints genuinely rule some options out — and then it is worth doing properly, which means budgeting for the instrument and the reference, not just for the run.

The advice I'd keep is narrower than "measure it": **measure it, and treat the measurement as the least trustworthy component in the system, because it is the only one nothing is checking.** Everything else in your stack has tests, review, monitoring, and users who complain. Your eval harness has a number that looked plausible and a person who wanted it to be true.

---

*Three studies feed this piece and all three are public: the [CooperBench fork with all five structural conditions](https://github.com/JaviMaligno/CooperBench/tree/experiment/structural-conditions), the [judge-bias harness with the raw judgments and both write-ups](https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias) (the pilot kept first, because the retired finding is the useful part), and the [cross-session crosscheck seed repository](https://github.com/JaviMaligno/cross-session-crosscheck). The write-ups: [coding agents and teamwork](/en/blog/coding-agents-structure), [three judges, three rankings](/en/blog/three-judges-three-rankings), [what coding agents say to each other](/en/blog/what-agents-say-to-each-other), and [the grader that knew less than the system it graded](/en/blog/the-grader-knew-less).*
