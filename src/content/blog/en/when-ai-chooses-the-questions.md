---
title: "When AI chooses the questions"
description: "Solving open problems can open new questions. What happens if AI also learns to choose them, why understanding still matters, and what academia should reward."
pubDate: 2026-09-23
tags: ["AI", "Mathematics", "Research", "Academia"]
lang: en
translationKey: when-ai-chooses-the-questions
heroImage: "/blog/when-ai-chooses-the-questions.png"
linkedinImage: "/blog/when-ai-chooses-the-questions.png"
linkedinLinks:
  - label: "OpenAI announcement"
    url: "https://openai.com/index/advisory-group-on-mathematics-and-ai/"
  - label: "On Proof and Progress in Mathematics"
    url: "https://arxiv.org/abs/math/9404236"
  - label: "arXiv monthly submission statistics"
    url: "https://arxiv.org/stats/monthly_submissions"
---

On September 21, OpenAI [announced that an internal model had solved more than a hundred open mathematical problems](https://openai.com/index/advisory-group-on-mathematics-and-ai/). Two weeks earlier, it had [published a proof of the Navier–Stokes problem](https://openai.com/index/navier-stokes-solution/), accompanied by a Lean formalization. The announcements offer different kinds of evidence: the latter gives us an argument to study; the statement about a hundred problems includes neither a list nor their proofs. The Clay Mathematics Institute, meanwhile, is [continuing its evaluation process](https://www.claymath.org/news/navier-stokes-announcement/) for the Navier–Stokes result.

I have already written about [what the Navier–Stokes result means](/en/blog/navier-stokes-blows-up). What interests me now is what comes next. If AI can answer questions we have spent decades trying to solve, what new questions will we be able to ask? And if it also learns to choose them better than we do, what will participating in mathematics mean?

To get there, it helps to start with something the headlines tend to take for granted: why open problems exist, and why some of them matter to us.

## Where the questions come from

A problem is open when we do not know a solution that answers its formulation with the required guarantees. That may be because we lack the techniques, because we have not found the right way to frame it, or because hardly anyone has worked on it. The age of a question tells us how long it has been around; on its own, it does not measure how much intelligence answering it requires. And a pattern observed across millions of examples may still fall short of a proof that it always holds.

There is no final inventory of everything left to discover. Every definition makes questions possible; every theorem invites us to examine its assumptions; every connection between two fields gives us things we previously did not even know how to ask. Solving problems changes the conditions under which the next ones arise.

We can see this without reaching for a famous conjecture. If a proof uses a symmetry assumption, we can investigate which parts of the result survive when we remove it. If a counterexample appears, we can try to identify what makes it fail and which cases remain valid. If the argument works on seemingly different objects, we can look for the structure they share. A specific answer can grow into a theory.

Counting open questions and solved questions would therefore be a rather poor measure of progress. Variations on a statement are easy to manufacture. The difficult part is finding a question whose answer changes what we are able to understand.

## Who decides what is worth studying

No central authority makes that judgment. Researchers propose problems; others decide to spend time on them; seminars, journals, PhD supervisors and funding amplify some directions more than others. Famous lists make a selection visible. Clay itself [explains that it chose its problems](https://www.claymath.org/news/navier-stokes-announcement/) for their depth and their potential to drive new structures and methods, with consequences extending beyond the original question.

There are criteria we can discuss: how much a problem unifies, which obstacles it helps us understand, what techniques it might unlock, what applications it suggests. Beauty, surprise and the appeal of exploring something with no recognizable use also play a part. These criteria can conflict. A problem may be fruitful for one field and peripheral to another. And the prestige of the person proposing it may attract attention that an equally good question elsewhere never receives.

Mathematical judgment develops through work: seeing which attempts fail, which assumptions do the real work, and which ideas survive a change of example. Recognizing famous names is only a small part of it.

AI can participate throughout this process. It can search for counterexamples, compare cases, suggest a generalization and help us notice that two results express something similar. There are precedents that predate today's models: [a 2021 study by Davies and colleagues in Nature](https://www.nature.com/articles/s41586-021-04086-x) used machine learning to detect relationships that guided new conjectures and results in knot theory and representation theory. Mathematicians interpreted and developed those clues. The collaboration helped formulate new mathematics.

My expectation is that more capable tools will expand the questions we can tackle. A direction that once seemed impractical can become a viable research project if exploring examples or proving preliminary lemmas costs much less. But there is no guarantee that this capability will be spent on the most fruitful questions. A system rewarded for accumulating solutions has an incentive to select problems it can close. A system rewarded for making an impression has an incentive to select recognizable names. Neither objective necessarily coincides with producing understanding.

## What if AI develops its own judgment?

Here comes the reassuring answer: we will supply the judgment, and the machine will do the work.

I do not think we can assume that division will last.

Part of judgment is anticipating consequences: which idea will connect results, which experiment will distinguish two explanations, which question will open a line of research. I see no sufficient reason to declare that AI can never learn to do this. Nor is a model proposing ten sophisticated-sounding questions enough to establish that it already can. The evidence would come from following its proposals: checking whether they produce reusable methods, unexpected connections and worthwhile subsequent work.

Two transitions are worth distinguishing. One is learning to choose well by the criteria we already use. Another is proposing a direction those criteria initially reject, then giving us reason to revise our judgment. The second looks more like developing its own mathematical taste. Recognizing it would require time and results; asking the model whether it feels curious would not settle anything.

The fact that a criterion was learned does not automatically disqualify it, either. Our own taste develops through reading, teachers, examples and institutional rewards. The practical question is whether the system can revise what it has learned in light of its discoveries, and whether its choices remain valuable beyond the evaluation it was trained for.

Even then, identifying a mathematically promising direction would differ from deciding how much we want to invest in it, who should have access to its results, or which human needs to prioritize. The technical ability to recommend a course does not, by itself, confer authority to set the goals. Who controls the system also matters: an agenda chosen by AI may be responding to the incentives of the company training it.

## Consumers of truths

Would that turn us into consumers of truths?

We already consume many truths we did not discover. Almost everything a mathematician learns was first thought through by someone else. Yet studying a proof can profoundly change what that person is able to do. Authorship has never been a necessary condition for acquiring intuition. A machine author does not, by itself, make a result impossible to understand.

What matters is how the result reaches us. A certificate of correctness, an explanation and a technique I can reuse offer different things. Formal verification checks that a conclusion follows from definitions and assumptions within a system. Interpreting what has been formalized and why it matters requires further work. Learning to recognize when the idea is useful requires more still.

![Correctness, understanding and judgment require different evidence: a proof, a reusable idea and a justified research priority.](/blog/when-ai-chooses-the-questions-criteria-en.png)

*A correct proof does not, by itself, establish that someone understands the idea or that choosing the problem was a good decision.*

In his 1994 essay [On Proof and Progress in Mathematics](https://arxiv.org/abs/math/9404236), Thurston argued that mathematical progress should be examined through what it enables people to understand. His essay describes the distance between a written proof and the different ways of understanding it, as well as the effort involved in communicating those ideas. This concern predates generative models.

AI could also help with that communication: finding a simple case, explaining where an intuition fails, constructing a counterexample or searching for another proof. Human understanding could grow through results nobody would have obtained unaided. To know whether that is happening, we would need to look at what the reader can do afterwards: recognize a new situation, adapt the argument, identify a limit. Feeling that an explanation is clear is not enough.

A harder scenario is possible too: correct results whose methods we can barely absorb, or production advancing much faster than our ability to study it. We might use some consequences without mastering the entire mechanism. If AI also became better at finding applications, human understanding could cease to be necessary for certain parts of technical progress.

That would not make understanding worthless. It enables participation in decisions, teaching, debate and intellectual independence. Understanding something can be valuable to the person who understands it even if another intelligence could do it better. We do not have to prove that learning makes us economically irreplaceable in order to want to keep learning. But we should not promise that preserving this value will, by itself, solve the problem of academic employment.

## What academia would have to reward

This is where universities enter the picture. Part of research training involves learning through work that leads to an original result. If that result can be obtained with much less human involvement, we will need to assess more directly what the researcher has learned and contributed. Increasing publication requirements would preserve the metric while its meaning deteriorates.

The scale already deserves attention. arXiv went from [185,692 new submissions in 2022](https://info.arxiv.org/about/reports/2022_arXiv_annual_report.pdf) to [284,486 in 2025](https://info.arxiv.org/about/reports/2025_arXiv_annual_report.pdf): an increase of approximately 53%. The trend continues in 2026: adding up [arXiv's monthly statistics](https://arxiv.org/stats/monthly_submissions) gives 230,322 submissions from January through August, compared with 181,595 in the same eight months of 2025, a 26.8% increase. September is still incomplete as of the access date, September 21, 2026.

These are submissions to the repository across its disciplines, not peer-reviewed mathematics articles. The series does not isolate AI's effect; the [2025 report identifies the rise in AI-generated manuscripts](https://info.arxiv.org/about/reports/2025_arXiv_annual_report.pdf) as a challenge for the platform.

![New arXiv submissions from January through August: 120,343 in 2022, 133,741 in 2023, 158,079 in 2024, 181,595 in 2025 and 230,322 in 2026. All disciplines and the same period each year.](/blog/when-ai-chooses-the-questions-arxiv-en.png)

*Author’s visualization using [arXiv's monthly CSV](https://arxiv.org/stats/get_monthly_submissions), accessed September 21, 2026. January–August is compared across all years: new submissions, not revisions or peer-reviewed publications.*

In my own case, I have one paper from before I used AI and four since. That is a sample of one, with different projects and time periods. What I can describe more precisely is in [my experience doing research with AI](/en/blog/writing-a-research-paper-with-ai): models participate in planning, execution and scientific review. The number of completed documents does not, on its own, tell us which questions I chose well, which errors I learned to detect, or how valuable the results are.

That is why I think the academic model that uses paper volume as a substitute for intellectual contribution is rapidly losing its justification. Reform would need to give more weight to contributions that can be examined: a well-motivated question, a reusable tool, an independent check or an explanation that enables others to work with an idea. It would also need to recognize the time spent reviewing, organizing and teaching what is discovered.

Training would need real opportunities to practise reasoning, alongside opportunities to use these tools with judgment. Asking someone to adapt a proof when an assumption changes tells us something different from asking them to hand in a correct text. When AI participates, it matters how the question was chosen, how the answer was verified and what the researcher can explain about its limits.

The [mathematicians' letter published on September 11](https://mathandai.org/) raises a related concern: using open problems as a benchmark may favour answer production while weakening the understanding and training those problems helped develop. I think that warning deserves serious attention. An abundance of results should come with resources to study and communicate them, and access to the tools used to produce them.

What interests me about AI in mathematics is how far it can extend our ability to ask questions. First, by helping us explore what we currently cannot. Later, perhaps, by proposing directions we would not have known how to value in advance.

If that second moment arrives, our role will not be guaranteed by some permanent inability of the machine. It will also depend on what we choose to build around it: institutions that make learning possible, ways to turn results into shared ideas, and the ability to influence the goals of research. Having more truths available will be an achievement. Making them our own will remain a task.
