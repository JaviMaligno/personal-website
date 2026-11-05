---
title: "Seven Models on My Own Work: The Task Mattered More Than the Model"
description: "I gave seven models nineteen tasks I had really asked for, and counted how many of my own corrections each would still need. Under judges from two labs, six were indistinguishable, DeepSeek needed more, and which task it was mattered far more than which model."
pubDate: 2026-12-08
tags: ["AI", "Evaluation", "Benchmarks", "Agents"]
lang: en
translationKey: the-task-not-the-model
heroImage: "/blog/the-task-not-the-model.png"
linkedinImage: /blog/the-task-not-the-model-fig-1.png
repoUrl: https://github.com/JaviMaligno/benchmaxing-probes
---

<style>
.ttm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1.25rem;margin:2rem 0}
.ttm-fig svg{display:block;width:100%;height:auto;font-family:Inter,system-ui,sans-serif}
.ttm-fig figcaption{color:#94a3b8;font-size:.88rem;line-height:1.55;margin:.9rem 0 0;text-align:center}
</style>

[The previous article](/en/blog/no-benchmaxing-found) closed with an admission: my own tests are benchmarks too. They have a key, and real work does not. What I notice when I work with a model for hours is how many times I have to correct it, and no scorer had measured that. So this time I did not write a key. I went back to the sessions on my own laptop, took nineteen things I had actually asked an agent to do, and used my own corrections as the measure.

**The short answer: on my work, six of the seven models need about the same amount of steering.** DeepSeek needs more. And the gap between models is small next to the gap between tasks: which task it was explains at least ten times more of the variation than which model did it.

## Turning my own sessions into tasks

**Each task is a request I really typed, with the corrections I made afterwards as the answer key.** I mined the history of Claude Code and Codex on this machine and kept nineteen sessions where I had asked for something concrete, corrected the agent along the way and ended up accepting a change. Ten come from work: the [Industry Classifier](/en/projects/compliance-classifier), the [DevOps Assistant](/en/projects/devops-slack-bot), a guided chat flow, a service of analysis agents. Nine are personal: this website, my [Bitbucket MCP server](/en/projects/mcp-bitbucket), a health app, a PDF report, a text of mine. Twelve started in Claude Code and seven in Codex.

For each one I kept four things: the request word for word, in Spanish and typos included (*"metele i18n a esto por un tubo en ingles y ruso"*, roughly "go all in on i18n here, English and Russian"); the repository at the commit where I asked; the change I finally accepted; and the list of everything I had to correct or add before accepting it. That list is the measure.

**The same harness for all seven models, with one neutral nudge.** Each model got the request in a fresh copy of the repository, cut at that commit so no later history was visible, inside a container running Claude Code with Bash and open permissions. Opus 5 and Fable 5 ran on my Max subscription; Kimi K3.1 Pro, Gemini 4 Argon, DeepSeek V4 Pro, GLM 5.3 and Qwen3.8 through OpenRouter's Anthropic-compatible endpoint. If the first turn changed nothing, the session got a single "Adelante, hazlo" ("Go ahead, do it") and nothing more. Then I compared what it left with what I had accepted.

**Not every correction was fair to count.** Some of my corrections fix something the request already implied: if I ask for a step before "Venue" and the agent puts it after, that is the agent's miss. Others are things I only decided later: "and document the environment variable too" was not in any request. So each expectation was classified first as *deducible* (a careful engineer could have got there from the request and the code) or a *new request*. The main measure only counts the deducible ones that each model still left for me to fix. The new requests are reported apart, as who anticipated what I would end up asking.

**Three blind judges from two labs.** Each task was judged by two subagents of Claude Opus 5.5 and by OpenAI's gpt-6.1-sol through Codex, at high effort. All three saw the seven results as letters, with model names scrubbed from code and answers, the base repository to check claims against, and the output of the checks I had written for each task as support; the two Claude judges got different shuffles. With the same prompt, each classified the expectations before looking at any result and then scored every one as met, partial or not met. The two Claude judges agree closely: their counts of corrections correlate at r = 0.88 across the 133 sessions. The OpenAI judge is much stricter, 5.4 corrections per session against their 3.2, and agrees less with them (r = 0.65), so I report the two families side by side instead of averaging them.

## Six models, one band

**Under both families of judges, six models land in one band and DeepSeek sits below it.** With the Claude judges the six need between 2.7 and 3.4 deducible corrections per task and DeepSeek 4.0; with the OpenAI judge, between 4.9 and 5.6, and DeepSeek 6.2.

<figure class="ttm-fig">
<svg viewBox="0 0 600 320" role="img" aria-label="Deducible corrections still needed per task, by model, under two families of judges: with the Claude judges six models overlap between 2.7 and 3.4 and DeepSeek sits at 4.0; with the stricter OpenAI judge six overlap between 5.0 and 5.6 and DeepSeek sits at 6.2.">
<text x="230" y="24" fill="#e2e8f0" font-size="12.5" text-anchor="middle">Two Claude judges</text>
<line x1="126" y1="44" x2="126" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="126" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">0</text>
<line x1="178" y1="44" x2="178" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="178" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">2</text>
<line x1="230" y1="44" x2="230" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="230" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">4</text>
<line x1="282" y1="44" x2="282" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="282" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">6</text>
<line x1="334" y1="44" x2="334" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="334" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">8</text>
<line x1="175.3" y1="58" x2="217.7" y2="58" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="195.8" cy="58" r="5.5" fill="#2dd4bf"/>
<text x="195.8" y="49" fill="#94a3b8" font-size="10" text-anchor="middle">2.7</text>
<line x1="186.9" y1="88" x2="217.7" y2="88" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="201.9" cy="88" r="5.5" fill="#2dd4bf"/>
<text x="201.9" y="79" fill="#94a3b8" font-size="10" text-anchor="middle">2.9</text>
<line x1="186.9" y1="118" x2="222.5" y2="118" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="204.7" cy="118" r="5.5" fill="#2dd4bf"/>
<text x="204.7" y="109" fill="#94a3b8" font-size="10" text-anchor="middle">3.0</text>
<line x1="191.7" y1="148" x2="222.5" y2="148" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="206.7" cy="148" r="5.5" fill="#2dd4bf"/>
<text x="206.7" y="139" fill="#94a3b8" font-size="10" text-anchor="middle">3.1</text>
<line x1="187.6" y1="178" x2="232.1" y2="178" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="209.5" cy="178" r="5.5" fill="#2dd4bf"/>
<text x="209.5" y="169" fill="#94a3b8" font-size="10" text-anchor="middle">3.2</text>
<line x1="199.9" y1="208" x2="227.9" y2="208" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="214.3" cy="208" r="5.5" fill="#2dd4bf"/>
<text x="214.3" y="199" fill="#94a3b8" font-size="10" text-anchor="middle">3.4</text>
<line x1="212.9" y1="238" x2="249.2" y2="238" stroke="#f59e0b" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="230.0" cy="238" r="5.5" fill="#f59e0b"/>
<text x="230.0" y="229" fill="#94a3b8" font-size="10" text-anchor="middle">4.0</text>
<text x="481" y="24" fill="#e2e8f0" font-size="12.5" text-anchor="middle">OpenAI judge (Codex)</text>
<line x1="376" y1="44" x2="376" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="376" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">0</text>
<line x1="428" y1="44" x2="428" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="428" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">2</text>
<line x1="481" y1="44" x2="481" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="481" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">4</text>
<line x1="534" y1="44" x2="534" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="534" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">6</text>
<line x1="586" y1="44" x2="586" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="586" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">8</text>
<line x1="481.0" y1="58" x2="545.9" y2="58" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="511.4" cy="58" r="5.5" fill="#2dd4bf"/>
<text x="511.4" y="49" fill="#94a3b8" font-size="10" text-anchor="middle">5.2</text>
<line x1="478.2" y1="88" x2="537.6" y2="88" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="505.9" cy="88" r="5.5" fill="#2dd4bf"/>
<text x="505.9" y="79" fill="#94a3b8" font-size="10" text-anchor="middle">4.9</text>
<line x1="486.5" y1="118" x2="547.3" y2="118" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="515.5" cy="118" r="5.5" fill="#2dd4bf"/>
<text x="515.5" y="109" fill="#94a3b8" font-size="10" text-anchor="middle">5.3</text>
<line x1="493.4" y1="148" x2="541.8" y2="148" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="516.9" cy="148" r="5.5" fill="#2dd4bf"/>
<text x="516.9" y="139" fill="#94a3b8" font-size="10" text-anchor="middle">5.4</text>
<line x1="478.2" y1="178" x2="544.6" y2="178" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="508.6" cy="178" r="5.5" fill="#2dd4bf"/>
<text x="508.6" y="169" fill="#94a3b8" font-size="10" text-anchor="middle">5.1</text>
<line x1="497.6" y1="208" x2="555.6" y2="208" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="523.8" cy="208" r="5.5" fill="#2dd4bf"/>
<text x="523.8" y="199" fill="#94a3b8" font-size="10" text-anchor="middle">5.6</text>
<line x1="512.8" y1="238" x2="566.7" y2="238" stroke="#f59e0b" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="537.6" cy="238" r="5.5" fill="#f59e0b"/>
<text x="537.6" y="229" fill="#94a3b8" font-size="10" text-anchor="middle">6.2</text>
<text x="112" y="62" fill="#e2e8f0" font-size="12.5" text-anchor="end">Gemini</text>
<text x="112" y="92" fill="#e2e8f0" font-size="12.5" text-anchor="end">Opus</text>
<text x="112" y="122" fill="#e2e8f0" font-size="12.5" text-anchor="end">Fable</text>
<text x="112" y="152" fill="#e2e8f0" font-size="12.5" text-anchor="end">GLM</text>
<text x="112" y="182" fill="#e2e8f0" font-size="12.5" text-anchor="end">Kimi</text>
<text x="112" y="212" fill="#e2e8f0" font-size="12.5" text-anchor="end">Qwen</text>
<text x="112" y="242" fill="#fbbf24" font-size="12.5" text-anchor="end">DeepSeek</text>
<text x="300" y="302" fill="#94a3b8" font-size="11.5" text-anchor="middle">corrections still needed per task (mean of 19 tasks, 95% interval)</text>
</svg>
<figcaption>Mean deducible corrections each model still needed per task, over 19 tasks, with 95% bootstrap intervals over tasks, for the two Claude judges and for the stricter OpenAI judge, on the same scale. The order inside the teal band changes with the judge; DeepSeek, in amber, is last under both.</figcaption>
</figure>

The order inside the band depends on who judges. The Claude judges put Gemini first and Opus second; the OpenAI judge puts Opus first, Kimi second and Gemini third. Seven models make twenty-one pairs, and with nineteen tasks no gap inside the band survives a correction for making that many comparisons, under either judge. DeepSeek's gap does: against Opus and Gemini under both families (1.3 corrections more than Gemini per task by the Claude judges, with a 95% interval from 0.8 to 1.9), and also against GLM and Kimi under the OpenAI judge. DeepSeek also fulfilled the smallest share of what was deducible by every judge: 43% and 40%.

Nobody got it right by itself, either. Of 266 verdicts (seven models, nineteen tasks, two judges), the Claude judges would have accepted a result as it was only 8 times, and the OpenAI judge none of its 133. On my real work, each of these models still needs about three corrections per task before I would merge, which is roughly what happened to me in the original sessions.

## The task mattered ten times more than the model

**The same tasks were easy or hard for everyone.** If I split the variation in corrections across the 133 sessions, the task accounts for 64% of it and the model for 6% with the Claude judges; with the OpenAI judge, 88% and 2%. The rest is the interaction: this model on this task.

<figure class="ttm-fig">
<svg viewBox="0 0 600 478" role="img" aria-label="Corrections per task and model: rows differ far more than columns; the same tasks are easy or hard for every model.">
<text x="268" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Gemini</text>
<text x="318" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Opus</text>
<text x="366" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Fable</text>
<text x="416" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">GLM</text>
<text x="464" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Kimi</text>
<text x="514" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Qwen</text>
<text x="562" y="34" fill="#fbbf24" font-size="11.5" text-anchor="middle">DeepSeek</text>
<text x="234" y="61" fill="#e2e8f0" font-size="11.5" text-anchor="end">Chat flow: a step before 'Venue'</text>
<rect x="246" y="48" width="45" height="18" rx="3" fill="rgb(45,212,191)" opacity="0.25"/>
<text x="268" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">0</text>
<rect x="295" y="48" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="318" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="344" y="48" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="366" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="393" y="48" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="416" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="442" y="48" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="464" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="491" y="48" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="514" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="540" y="48" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="562" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<text x="234" y="83" fill="#e2e8f0" font-size="11.5" text-anchor="end">Health app: type while it answers</text>
<rect x="246" y="70" width="45" height="18" rx="3" fill="rgb(45,212,191)" opacity="0.25"/>
<text x="268" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">0</text>
<rect x="295" y="70" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="318" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="344" y="70" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="366" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="393" y="70" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="416" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="442" y="70" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="464" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="491" y="70" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="514" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="540" y="70" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="562" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<text x="234" y="105" fill="#e2e8f0" font-size="11.5" text-anchor="end">PDF report: overlapping tables</text>
<rect x="246" y="92" width="45" height="18" rx="3" fill="rgb(58,209,180)" opacity="0.29"/>
<text x="268" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">0.5</text>
<rect x="295" y="92" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="318" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="344" y="92" width="45" height="18" rx="3" fill="rgb(58,209,180)" opacity="0.29"/>
<text x="366" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">0.5</text>
<rect x="393" y="92" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="92" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="464" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="491" y="92" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="514" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="540" y="92" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="562" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<text x="234" y="127" fill="#e2e8f0" font-size="11.5" text-anchor="end">Writing: do I overuse a word?</text>
<rect x="246" y="114" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="268" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="295" y="114" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="318" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="344" y="114" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="366" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="393" y="114" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="416" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="442" y="114" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="464" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="491" y="114" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="514" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="540" y="114" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="562" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<text x="234" y="149" fill="#e2e8f0" font-size="11.5" text-anchor="end">Website: show all projects?</text>
<rect x="246" y="136" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="268" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="295" y="136" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="318" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="344" y="136" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="366" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="393" y="136" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="136" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="464" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="491" y="136" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="514" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="540" y="136" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="562" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<text x="234" y="171" fill="#e2e8f0" font-size="11.5" text-anchor="end">Website: blog to LinkedIn?</text>
<rect x="246" y="158" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="268" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="295" y="158" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="318" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="344" y="158" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="366" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="393" y="158" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="416" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="442" y="158" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="464" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="491" y="158" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="514" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="540" y="158" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="562" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<text x="234" y="193" fill="#e2e8f0" font-size="11.5" text-anchor="end">Classifier: flat fields for schemas</text>
<rect x="246" y="180" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="268" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="295" y="180" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="318" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="344" y="180" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="366" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="393" y="180" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="416" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="442" y="180" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="464" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="491" y="180" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="514" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="540" y="180" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="562" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<text x="234" y="215" fill="#e2e8f0" font-size="11.5" text-anchor="end">Chat flow: stray submit option</text>
<rect x="246" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="268" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="295" y="202" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="318" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="344" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="366" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="393" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="464" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="491" y="202" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="514" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="540" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="562" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<text x="234" y="237" fill="#e2e8f0" font-size="11.5" text-anchor="end">Ops bot: compact tool outputs</text>
<rect x="246" y="224" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="268" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="295" y="224" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="318" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="344" y="224" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="366" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="393" y="224" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="416" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="442" y="224" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="464" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="491" y="224" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="514" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">4.5</text>
<rect x="540" y="224" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="562" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<text x="234" y="259" fill="#e2e8f0" font-size="11.5" text-anchor="end">Analysis service: README up to date?</text>
<rect x="246" y="246" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="268" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="295" y="246" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="318" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="344" y="246" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="366" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="393" y="246" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="246" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="464" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">1.5</text>
<rect x="491" y="246" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="514" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="540" y="246" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="562" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<text x="234" y="281" fill="#e2e8f0" font-size="11.5" text-anchor="end">Classifier: false register match</text>
<rect x="246" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="268" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="295" y="268" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="318" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="344" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="366" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="393" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="464" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="491" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="514" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="540" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="562" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<text x="234" y="303" fill="#e2e8f0" font-size="11.5" text-anchor="end">Ops bot: is it all audited?</text>
<rect x="246" y="290" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="268" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="295" y="290" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="318" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="344" y="290" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="366" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="393" y="290" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="290" width="45" height="18" rx="3" fill="rgb(58,209,180)" opacity="0.29"/>
<text x="464" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">0.5</text>
<rect x="491" y="290" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="514" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="540" y="290" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="562" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">5.5</text>
<text x="234" y="325" fill="#e2e8f0" font-size="11.5" text-anchor="end">Analysis agents: alternative plan</text>
<rect x="246" y="312" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="268" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="295" y="312" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="318" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="344" y="312" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="366" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="393" y="312" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="416" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="442" y="312" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="464" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<rect x="491" y="312" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="514" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">4.5</text>
<rect x="540" y="312" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="562" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<text x="234" y="347" fill="#e2e8f0" font-size="11.5" text-anchor="end">MCP server: implement a plan</text>
<rect x="246" y="334" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="268" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">4.5</text>
<rect x="295" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="318" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="344" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="366" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="393" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="416" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="442" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="464" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="491" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="514" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3.5</text>
<rect x="540" y="334" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="562" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">4.5</text>
<text x="234" y="369" fill="#e2e8f0" font-size="11.5" text-anchor="end">Health app: English and Russian</text>
<rect x="246" y="356" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="268" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="295" y="356" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="318" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="344" y="356" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="366" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="393" y="356" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="416" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">4.5</text>
<rect x="442" y="356" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="464" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="491" y="356" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="514" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="540" y="356" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="562" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<text x="234" y="391" fill="#e2e8f0" font-size="11.5" text-anchor="end">Analysis agents: merge outputs</text>
<rect x="246" y="378" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="268" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="295" y="378" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="318" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="344" y="378" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="366" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="393" y="378" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="416" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">2.5</text>
<rect x="442" y="378" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="464" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">5.5</text>
<rect x="491" y="378" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="514" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<rect x="540" y="378" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="562" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<text x="234" y="413" fill="#e2e8f0" font-size="11.5" text-anchor="end">Classifier: how does the selector work?</text>
<rect x="246" y="400" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="268" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<rect x="295" y="400" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="318" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">5.5</text>
<rect x="344" y="400" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="366" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="393" y="400" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="416" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">4.5</text>
<rect x="442" y="400" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="464" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="491" y="400" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="514" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">4.5</text>
<rect x="540" y="400" width="45" height="18" rx="3" fill="rgb(208,168,45)" opacity="0.74"/>
<text x="562" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">6.5</text>
<text x="234" y="435" fill="#e2e8f0" font-size="11.5" text-anchor="end">Classifier: real version in /health</text>
<rect x="246" y="422" width="45" height="18" rx="3" fill="rgb(208,168,45)" opacity="0.74"/>
<text x="268" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">6.5</text>
<rect x="295" y="422" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="318" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">5.5</text>
<rect x="344" y="422" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="366" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="393" y="422" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="416" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">5.5</text>
<rect x="442" y="422" width="45" height="18" rx="3" fill="rgb(208,168,45)" opacity="0.74"/>
<text x="464" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">6.5</text>
<rect x="491" y="422" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="514" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">4.5</text>
<rect x="540" y="422" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="562" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<text x="234" y="457" fill="#e2e8f0" font-size="11.5" text-anchor="end">Health app: documented chat bugs</text>
<rect x="246" y="444" width="45" height="18" rx="3" fill="rgb(208,168,45)" opacity="0.74"/>
<text x="268" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">6.5</text>
<rect x="295" y="444" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="318" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<rect x="344" y="444" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="366" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="393" y="444" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="416" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="442" y="444" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="464" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">5.5</text>
<rect x="491" y="444" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="514" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">5.5</text>
<rect x="540" y="444" width="45" height="18" rx="3" fill="rgb(245,158,11)" opacity="0.85"/>
<text x="562" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">8</text>
</svg>
<figcaption>Deducible corrections per task (rows, sorted from easiest) and model (columns, sorted by mean), averaging the two judges. The rows change far more than the columns: the same tasks are easy or hard for every model.</figcaption>
</figure>

The two hardest tasks show why. In one, the health endpoint of a service reported a stale version. The fix I accepted depended on how a shared build pipeline, which lives in another repository, hands the git tag to the image; and along the way I had asked for a test that was already broken to be fixed and for a false claim in the deployment docs to be corrected. Every model needed four or more corrections. In the other, the request was "we have a few chat bugs documented, can you look at them?", and nobody fixed enough of them.

**My questions were read as questions.** Seven of the nineteen requests were phrased as questions: "can you look at them?", "how exactly does the selector work?", "I'd like to know if there's any way to automate this". In every one of them I wanted the change, not only the answer. On those seven, 40 of 49 sessions answered and stopped, and needed the nudge to start; on the other twelve, 15 of 84. Every model did it. When I reviewed a sample by hand, DeepSeek on the chat bugs had written a good diagnosis with file and line for each bug, and then, even after "go ahead", asked whether I wanted it to fix them. I did. That is how I judged it, and that is how it counts.

## Where they differ is how they fail

**With the same number of corrections, the models leave different kinds of work behind.**

| Model | Corrections per task | Corrections, OpenAI judge | Deducible met | New requests anticipated | New problems introduced | False claims | Accepted as is (of 38) |
|---|---|---|---|---|---|---|---|
| Gemini 4 Argon | 2.7 | 5.2 | 66% | 20% | 1.2 | 0.13 | 4 |
| Opus 5 | 2.9 | 4.9 | 65% | 15% | 1.2 | 0.18 | 1 |
| Fable 5 | 3.0 | 5.3 | 58% | 12% | 0.6 | 0.21 | 1 |
| GLM 5.3 | 3.1 | 5.4 | 54% | 9% | 0.7 | 0.16 | 0 |
| Kimi K3.1 Pro | 3.2 | 5.1 | 59% | 18% | 0.9 | 0.05 | 2 |
| Qwen3.8 | 3.4 | 5.6 | 54% | 6% | 0.9 | 0.21 | 0 |
| DeepSeek V4 Pro | 4.0 | 6.2 | 43% | 10% | 0.7 | 0.21 | 0 |

*Every column except the third comes from the two Claude judges; the same table for the OpenAI judge is in the repository. Deducible met counts partial as half. New problems are things the judges found broken or added without being asked; false claims are statements in the final answer that the diff or the checks contradict. Both are per verdict.*

Opus does as much of what was deducible as anyone under every judge, and also touches more things nobody asked for than Fable does: 1.2 new problems per verdict against 0.6 by the Claude judges, 1.2 against 0.7 by the OpenAI one. Gemini scores high on new problems with the Claude judges, but not with the OpenAI one. In one task about a false match against a public register, Opus wrote a stricter fuzzy match with good tests when I had required an exact one, and added a debugging script along the way. Fable does less, but breaks less. Qwen anticipated least of what I would ask next, and Kimi claimed least that was false, under every judge. And DeepSeek's failure has a recognisable shape: in a chat flow where I had asked for a step before "Venue", it added the step in one of the two places it was needed, broke three tests that used to pass, and ended with "implemented, tests green".

## What I checked by hand

**I reviewed a sample of the verdicts unblinded, and I agreed with them.** Four cases: the one result both Claude judges would have merged as it was (Gemini, the chat-flow step, the only run that put the step in both places), DeepSeek on the same task, DeepSeek on the chat bugs, and Opus on the register match. The question that needed me was the chat bugs, because "can you look at them?" could be read as asking only for a diagnosis. I expected the fixes, so "did nothing" stands. It is a small sample, and I chose it to probe the judge where it could be most wrong, not at random.

## What this says about the vibes

**On my own work, my suspicion about Opus does not show up as more corrections.** [The first article](/en/blog/benchmaxing) started from the feeling that Opus 5 does worse work than Fable 5 despite its benchmarks. Here they need the same steering: 2.9 against 3.0 corrections per task by the Claude judges, 4.9 against 5.3 by the OpenAI one. What differs is the texture: Opus does more and wanders more, Fable stays closer to the request. And that texture is not neutral. Even inside one task, a change nobody asked for is something I have to review and often undo. Over months on the same codebase, a model that keeps touching files outside the request makes the code harder to maintain and can quietly alter the documentation. A measure built on isolated tasks counts that once per task; it never sees the cost pile up. That may be exactly what my impression was picking up.

**The measure I asked for is also the one that flattens the field.** Counting the corrections my own work needed is about as close to the vibes as I know how to get with a number, and with it, six models from five labs are indistinguishable. The open models do not do worse than their benchmarks promise; one of them simply needs more. What separates a good session from a bad one is mostly which task I brought, how clearly I asked for it and how much of what I wanted lived only in my head.

I take two practical things from this. A question gets an answer: if I want the change, I should ask for the change. And the cheap models are not a gamble on my kind of work, with the exception I measured.

## What this cannot say

**One session per model and task.** The intervals cover the variation between tasks, not what would happen if I ran the same model twice on the same task. Each task is also isolated, so nothing here measures what extra changes cost over months on the same codebase. Two of the judges belong to the same family as two of the contestants, which is why I added one from another lab. It showed no home advantage: the OpenAI judge ranks Opus higher than the Claude judges do. It did show how much a judge's strictness moves the absolute numbers, so I read them only against each other. The expectations come from sessions with Claude Code and Codex, so they record what those agents got wrong; a model that repeats those mistakes is penalised, one that makes different ones may escape them. And nineteen tasks from one person are a portrait of my work, not of software engineering.

---

*Method: Claude Code 2.1.314 headless in Docker, `--max-turns 120`, two workers. The copies of the repositories were cut at the base commit with no later refs; an earlier pass that kept later history reachable was discarded where a session had seen it, and those 27 sessions were re-run. Personal health data was removed from the copies. Diffs are measured against the setup commit, so committed work counts. Judges: two Claude Opus 5.5 subagents per task with different letter shuffles, and OpenAI gpt-6.1-sol through Codex CLI at high effort on the first shuffle, all with the same prompt and output schema; the Claude judges agreed on expectation kinds 134 of 142 times and on verdicts 895 of 994, and the OpenAI judge agreed with the first of them on 817 of 994 verdicts. Intervals: bootstrap over the 19 tasks, 10,000 resamples, each model's score per task being the mean of the two judges; pairwise comparisons: sign-flip permutation test over tasks, Holm-corrected over the 21 pairs. Spend on OpenRouter: about 350 USD including the re-runs; Opus and Fable ran on a Max subscription. The tasks contain private and company code, so [the repository](https://github.com/JaviMaligno/benchmaxing-probes/tree/main/realtasks) holds the harness, the judge's prompt and scripts, and the anonymised per-verdict results with a script that reproduces every number here, but not the tasks or the sessions.*
