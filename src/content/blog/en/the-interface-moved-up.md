---
title: "The Interface Moved Up"
description: "Coding agents went from the editor to the terminal, then to the cloud and native apps. Each move raised what the human looks at: from code, to diffs, to results. The next one takes the human out of the launch altogether."
pubDate: 2026-10-27
tags: ["AI Agents", "Developer Tools", "Claude Code", "Future of Work"]
lang: en
translationKey: the-interface-moved-up
heroImage: "/blog/the-interface-moved-up.png"
---

I started working with AI inside the editor, like almost everyone. Then I moved to the terminal, with a light editor open next to it. Today, on my own machine, I still spend most of my time in the terminal: habit, a lighter footprint, and being right next to the shell. But I use the app more every month: on the desktop, and on my phone when I'm away from it. It handles several projects and conversations better, and it lets me mix an ordinary chat, a coding session running in the cloud and a coding session running on my laptop in the same sidebar.

That drift isn't only mine. Cursor, OpenAI, Anthropic and GitHub have spent 2026 shipping the same kind of product: a window for managing agents rather than editing files. Laid side by side, the moves have a pattern. **Each jump raised what the human looks at.** First the code, then the diff, then the result. The next jump is already visible, and in it the human doesn't even start the work.

## Five years in one picture

<style>
.imu-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1rem;margin:2rem 0}
.imu-fig svg{display:block;width:100%;height:auto;font-family:Inter,-apple-system,system-ui,sans-serif}
.imu-fig figcaption{color:#94a3b8;font-size:.85rem;line-height:1.55;margin:1rem .25rem .25rem;text-align:center}
</style>

<figure class="imu-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 770" role="img" aria-label="Timeline from 2021 to September 2026 with five lanes: editor, terminal, cloud, app and unattended agents. The editor lane runs the whole period. Terminal agents appear in 2023 and become mainstream in 2025. Cloud agents arrive in May 2025, native apps from November 2025, and agents started by tickets and schedules from May 2025. No lane closes: surfaces accumulate.">
  <g font-size="13" font-weight="600" text-anchor="start">
    <text x="60" y="36" fill="#cbd5e1">Editor</text>
    <text x="169" y="36" fill="#5eead4">Terminal</text>
    <text x="278" y="36" fill="#7dd3fc">Cloud</text>
    <text x="387" y="36" fill="#fbbf24">App</text>
    <text x="496" y="36" fill="#f8fafc">Unattended</text>
  </g>
  <path d="M56 50H600" stroke="rgba(255,255,255,.1)"/>
  <g font-size="12" fill="#94a3b8">
    <text x="4" y="116">2022</text>
    <text x="4" y="164">2023</text>
    <text x="4" y="212">2024</text>
    <text x="4" y="284">2025</text>
    <text x="4" y="548">2026</text>
    <text x="4" y="745">Sep '26</text>
  </g>
  <g stroke="rgba(255,255,255,.06)">
    <path d="M40 112H600"/><path d="M40 160H600"/><path d="M40 208H600"/><path d="M40 280H600"/><path d="M40 544H600"/>
  </g>
  <path d="M40 262H600M40 268H600" stroke="#475569" stroke-dasharray="6 4"/>
  <path d="M58 741H600" stroke="#64748b" stroke-dasharray="4 4"/>
  <path d="M64 84V741" stroke="#94a3b8" stroke-width="3"/>
  <path d="M173 182V319" stroke="#2dd4bf" stroke-width="2" stroke-dasharray="3 5"/>
  <path d="M173 319V741" stroke="#2dd4bf" stroke-width="3"/>
  <path d="M282 218V380" stroke="#38bdf8" stroke-width="2" stroke-dasharray="3 5"/>
  <path d="M282 380V741" stroke="#38bdf8" stroke-width="3"/>
  <path d="M391 517V741" stroke="#f59e0b" stroke-width="3"/>
  <path d="M500 380V741" stroke="#f8fafc" stroke-width="3"/>
  <g fill="#1a1a24" stroke-width="2">
    <circle cx="64" cy="84" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="131" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="167" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="204" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="251" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="498" r="4.5" stroke="#94a3b8"/>
    <circle cx="173" cy="182" r="4.5" stroke="#2dd4bf"/><circle cx="173" cy="319" r="4.5" stroke="#2dd4bf"/><circle cx="173" cy="357" r="4.5" stroke="#2dd4bf"/><circle cx="173" cy="584" r="4.5" stroke="#2dd4bf"/>
    <circle cx="282" cy="218" r="4.5" stroke="#38bdf8"/><circle cx="282" cy="380" r="4.5" stroke="#38bdf8"/><circle cx="282" cy="492" r="4.5" stroke="#38bdf8"/>
    <circle cx="391" cy="517" r="4.5" stroke="#f59e0b"/><circle cx="391" cy="567" r="4.5" stroke="#f59e0b"/><circle cx="391" cy="614" r="4.5" stroke="#f59e0b"/><circle cx="391" cy="666" r="4.5" stroke="#f59e0b"/>
    <circle cx="500" cy="380" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="449" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="591" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="620" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="645" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="666" r="4.5" stroke="#f8fafc"/>
  </g>
  <g font-size="11" fill="#e2e8f0">
    <text x="73" y="88">Copilot preview</text>
    <text x="73" y="135">Copilot GA</text>
    <text x="73" y="171">Copilot X: chat</text>
    <text x="73" y="208">Copilot Chat GA</text>
    <text x="73" y="255">Cursor agent</text>
    <text x="73" y="502">Cursor 2.0:</text>
    <text x="73" y="515">8 agents at once</text>
    <text x="182" y="186">Aider,</text>
    <text x="182" y="199">gpt-engineer</text>
    <text x="182" y="323">Claude Code</text>
    <text x="182" y="361">Codex CLI</text>
    <text x="182" y="588">Copilot CLI GA</text>
    <text x="291" y="222">Devin announced</text>
    <text x="291" y="384">Cursor, Codex,</text>
    <text x="291" y="397">Copilot agents</text>
    <text x="291" y="496">Claude Code</text>
    <text x="291" y="509">on the web</text>
    <text x="400" y="521">Claude Code in</text>
    <text x="400" y="534">desktop app</text>
    <text x="400" y="571">Codex app</text>
    <text x="400" y="618">Cursor 3,</text>
    <text x="400" y="631">Claude redesign</text>
    <text x="400" y="670">Copilot app GA</text>
    <text x="509" y="384">Linear for</text>
    <text x="509" y="397">Agents</text>
    <text x="509" y="453">Linear triage</text>
    <text x="509" y="466">→ Cursor</text>
    <text x="509" y="595">Copilot in Jira</text>
    <text x="509" y="624">Claude Routines</text>
    <text x="509" y="649">Cursor in Jira</text>
    <text x="509" y="670">Copilot app</text>
    <text x="509" y="683">automations</text>
  </g>
</svg>
<figcaption>Launch dates of the surfaces agents have lived on, June 2021 to September 2026. From 2025 on (below the double line) each month takes five times more height, otherwise the last twenty months would not fit. Dashed stretches: the surface existed but was marginal. No lane closes.</figcaption>
</figure>

Two things jump out. The first is that **no surface disappeared**. The editor is still there, the terminal is still there, and the new surfaces were added on top. What changed is where you spend most of the day. The second is the density: almost everything that matters happened in the last twenty months.

## The editor: the human writes, the model suggests

GitHub Copilot opened its [technical preview in June 2021](https://github.blog/news-insights/product-news/introducing-github-copilot-ai-pair-programmer/) and reached [general availability a year later](https://github.blog/news-insights/product-news/github-copilot-is-generally-available-to-all-developers/). The unit of work was a line or a function: you were typing, and the model completed. In 2023 came chat inside the editor ([Copilot X in March](https://github.blog/news-insights/product-news/github-copilot-x-the-ai-powered-developer-experience/), [Copilot Chat GA in December](https://github.blog/news-insights/product-news/github-copilot-chat-now-generally-available-for-organizations-and-individuals/)), and at the end of 2024 Cursor added [an agent to its Composer](https://cursor.com/changelog/0-43-x) that picked its own context and used the terminal.

The agent was already doing multi-step work, but the frame was still the file. The human was looking at code, because the code was where the work happened.

## The terminal: the agent needs the whole machine

Agents in the terminal did not start in 2025. [Aider](https://github.com/Aider-AI/aider/releases) and gpt-engineer were already there in the middle of 2023. What changed in 2025 is that the terminal became the main road: [Claude Code launched in February](https://www.anthropic.com/news/claude-3-7-sonnet) as a research preview, [Codex CLI in April](https://community.openai.com/t/this-weeks-launches-o3-o4-mini-gpt-4-1-and-codex-cli/1230312), and Claude Code reached [general availability in May](https://www.anthropic.com/news/claude-4).

The terminal won because of what it gives the agent, not because of what it gives the person. The shell is a universal interface to tools: tests, git, package managers, every CLI you have, and any script. Handing the agent a terminal is the cheapest way to hand it everything. And that goes together with the models' growing autonomy: an agent that can run fifty commands on its own needs the whole machine, not a completion box.

It helps to split the terminal stage into two ways of working:

- **Terminal plus editor.** The terminal gives the orders, and the editor stays open to read the diff and handle git. You still look at code, but as a reviewer rather than an author.
- **Terminal alone.** More weight goes to managing agents, and terminal commands become the only manual touchpoint in development. You may still open an artefact, a browser to see the final result, or an extension, but the development itself happens in the conversation. It is less transparent: you see what the agent tells you, unless you ask for more.

In both, the human looks at the **diff**, and the unit of work is a task.

## The cloud: the laptop has a ceiling

The next step looks like it should have been the app, but the dates say otherwise. Cloud agents came first, three of them within five days of May 2025: [Cursor's Background Agents](https://cursor.com/changelog/0-50), [Codex inside ChatGPT](https://openai.com/index/introducing-codex/) and the [Copilot coding agent](https://github.blog/changelog/2025-05-19-github-copilot-coding-agent-in-public-preview/), which takes a GitHub issue and opens a pull request. [Claude Code on the web](https://www.anthropic.com/news/claude-code-on-the-web) followed in October.

Convenience is only part of the reason. The other part is capacity. Running several agents at once, each with its own branch and test suite, saturates a normal laptop long before it saturates your attention. [Parallel agents with worktrees](/en/blog/parallel-ai-agent-development) work, until the machine becomes the bottleneck.

The cloud has its own price: the environment has to be reproducible. If you want the remote agent to run exactly what runs locally, the repository needs to [own its bootstrap](/en/blog/bootstrap-the-environment-not-the-agent): system packages, test databases, secrets. It isn't always worth it. Sometimes the task doesn't need the full environment, and sometimes it is desirable to keep one phase local, such as the one that touches data you'd rather not move, or the final check on your own machine. Anthropic's [Remote Control](https://code.claude.com/docs/en/remote-control) takes that position explicitly: the session keeps running on your computer, and you drive it from your phone.

## The app: the same work, but you can see it

Here is where 2026 happened. Claude Code arrived in the Claude desktop app [with Opus 4.5 in November 2025](https://www.anthropic.com/news/claude-opus-4-5), already with parallel local and remote sessions. Then, in quick succession: the [Codex app in February](https://techcrunch.com/2026/02/02/openai-launches-new-macos-app-for-agentic-coding/), [Cursor 3 in April](https://cursor.com/blog/cursor-3) with a window for managing agents across local, worktrees, cloud and SSH, the [Claude Code desktop redesign](https://claude.com/blog/claude-code-desktop-redesign) that same month, and the [Copilot app in June](https://github.blog/changelog/2026-06-17-github-copilot-app-generally-available/).

The last one says the most. The company that invented the assistant inside the editor now ships a standalone app for running agents. And Cursor 3 did not delete the IDE: the agent window lives beside it, and you can switch. The editor wasn't replaced, it stopped being the centre.

Seen from inside, what the app offers is less dramatic than it sounds, and that's precisely its value:

- **A normal chat, but for code.** The conversation looks like ChatGPT or Claude, the interface everyone already knows, and underneath it runs an agent with access to your repository.
- **Everything around the conversation within reach.** Diff, git, pull requests, artefacts, a preview panel and an [embedded browser](https://code.claude.com/docs/en/whats-new/2026-w28) to see the result. No window switching.
- **The same things you do in the terminal, but clearer.** A lot of the improvement is simply that it is easier to read: sessions in a sidebar, diffs with a real viewer, panels you arrange.
- **Several devices.** You start something at the desk and follow it from your phone. With cloud sessions this isn't a trick; the work was never on your laptop.

And one change that's easy to miss: in the same sidebar live ordinary conversations, remote coding sessions and local ones. **The app stops being a place to program and becomes the place where you work.**

The cost is weight. It uses more resources than a terminal, which is part of why the terminal is still my default on my own machine.

## What moved up

Put the stages together and the thesis appears. It isn't that the interfaces got prettier. It's that what the human needs to see went up one level each time.

<figure class="imu-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 330" role="img" aria-label="Four rising steps. In the editor, the human looks at the code and the unit is a line or file. In the terminal, the diff and the unit is a task. In the app with the cloud, the result, and the unit is a session. With unattended agents, the metrics, and the unit is a flow of tickets.">
  <text x="20" y="30" fill="#94a3b8" font-size="15">WHAT THE HUMAN LOOKS AT</text>
  <rect x="20" y="220" width="135" height="90" rx="8" fill="#283240" stroke="#94a3b8"/>
  <text x="32" y="244" fill="#cbd5e1" font-size="15" font-weight="600">Editor</text>
  <text x="32" y="266" fill="#f8fafc" font-size="13">the code</text>
  <text x="32" y="286" fill="#94a3b8" font-size="12">a line, a file</text>
  <rect x="165" y="165" width="135" height="145" rx="8" fill="#203237" stroke="#2dd4bf"/>
  <text x="177" y="189" fill="#5eead4" font-size="15" font-weight="600">Terminal</text>
  <text x="177" y="211" fill="#f8fafc" font-size="13">the diff</text>
  <text x="177" y="231" fill="#94a3b8" font-size="12">a task</text>
  <rect x="310" y="110" width="135" height="200" rx="8" fill="#362e23" stroke="#f59e0b"/>
  <text x="322" y="134" fill="#fbbf24" font-size="15" font-weight="600">App + cloud</text>
  <text x="322" y="156" fill="#f8fafc" font-size="13">the result</text>
  <text x="322" y="176" fill="#94a3b8" font-size="12">a session</text>
  <text x="322" y="194" fill="#94a3b8" font-size="12">PR · preview</text>
  <text x="322" y="212" fill="#94a3b8" font-size="12">artefact</text>
  <rect x="455" y="55" width="135" height="255" rx="8" fill="#2a2a33" stroke="#f8fafc"/>
  <text x="467" y="79" fill="#f8fafc" font-size="15" font-weight="600">Unattended</text>
  <text x="467" y="101" fill="#f8fafc" font-size="13">the metrics</text>
  <text x="467" y="121" fill="#94a3b8" font-size="12">a flow of tickets</text>
  <text x="467" y="139" fill="#94a3b8" font-size="12">evals · feedback</text>
  <text x="467" y="157" fill="#94a3b8" font-size="12">tests</text>
</svg>
<figcaption>Each step raises the level at which the human intervenes. The earlier steps don't vanish, they become something you open when needed.</figcaption>
</figure>

## The surface separates from the harness

The most important consequence is not on screen. The same agent now runs in the terminal, in the IDE, in the desktop app, in the browser, from the phone, from a ticket in Linear or Jira, or on a schedule. What makes it *that* agent lives underneath and is shared by all those surfaces: the **harness**.

<figure class="imu-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 410" role="img" aria-label="Six surfaces (terminal, IDE, desktop app, web and mobile, tickets, schedules and events) sit on top of one shared harness: permissions, tools, inputs and outputs, context and memory, hooks and skills, sandbox, worktrees and escalation, running locally, in the cloud or over SSH. Below it sits a model that is increasingly swappable.">
  <defs><marker id="imu-arrow-en" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#94a3b8"/></marker></defs>
  <text x="20" y="26" fill="#94a3b8" font-size="14">SURFACES · a choice of view</text>
  <rect x="20" y="40" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="110" y="65" text-anchor="middle" fill="#e2e8f0" font-size="14">Terminal</text>
  <rect x="210" y="40" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="300" y="65" text-anchor="middle" fill="#e2e8f0" font-size="14">IDE</text>
  <rect x="400" y="40" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="490" y="65" text-anchor="middle" fill="#e2e8f0" font-size="14">Desktop app</text>
  <rect x="20" y="90" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="110" y="115" text-anchor="middle" fill="#e2e8f0" font-size="14">Web · mobile</text>
  <rect x="210" y="90" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="300" y="115" text-anchor="middle" fill="#e2e8f0" font-size="14">Tickets (Linear, Jira)</text>
  <rect x="400" y="90" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="490" y="115" text-anchor="middle" fill="#e2e8f0" font-size="14">Schedules · events</text>
  <path d="M110 138V172" stroke="#94a3b8" stroke-width="2" marker-end="url(#imu-arrow-en)"/>
  <path d="M300 138V172" stroke="#94a3b8" stroke-width="2" marker-end="url(#imu-arrow-en)"/>
  <path d="M490 138V172" stroke="#94a3b8" stroke-width="2" marker-end="url(#imu-arrow-en)"/>
  <rect x="20" y="180" width="560" height="150" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="300" y="212" text-anchor="middle" fill="#fbbf24" font-size="22" font-weight="600">Harness</text>
  <text x="300" y="242" text-anchor="middle" fill="#e2e8f0" font-size="15">permissions · tools · inputs and outputs</text>
  <text x="300" y="266" text-anchor="middle" fill="#e2e8f0" font-size="15">context and memory · hooks and skills</text>
  <text x="300" y="290" text-anchor="middle" fill="#e2e8f0" font-size="15">sandbox · worktrees · escalation to a human</text>
  <text x="300" y="316" text-anchor="middle" fill="#94a3b8" font-size="13">runs locally, in the cloud or over SSH</text>
  <path d="M300 332V346" stroke="#94a3b8" stroke-width="2" marker-end="url(#imu-arrow-en)"/>
  <rect x="20" y="352" width="560" height="46" rx="10" fill="#283240" stroke="#94a3b8"/>
  <text x="300" y="381" text-anchor="middle" fill="#f8fafc" font-size="15">Model: frontier or open source, increasingly swappable</text>
</svg>
<figcaption>The surface is a choice of view over the same agent. What the agent may do, what it remembers and when it asks for help is decided one layer down.</figcaption>
</figure>

Two trends push in the same direction. Open-source models are increasingly competent and frontier models increasingly cheap, so [choosing a model](/en/blog/routing-engineering) is becoming a routing decision rather than a platform decision. And the work is starting to happen at scale: many sessions, many repositories, long tasks. At that point what distinguishes one team's agents from another's is not the model and not the window, but the harness.

## Managing, not typing

When the human stops watching each step, the questions change. They are no longer "how do I write this" but "what may this agent do, what does it get, what does it give back, and when does it stop to ask me". They matter most in long-horizon work, where an agent runs for hours and a bad decision early on gets multiplied:

- **Permissions.** What it may touch without asking, what it may never touch, and in which environment. Deploying, writing to a shared database or sending anything outside is a different category from editing a file.
- **Inputs.** Which context it starts with: the ticket, the specification, the repository's instructions, the memory of previous sessions. An agent that starts without the facts that change its judgement makes decisions that someone who knows them wouldn't.
- **Outputs.** What counts as done and in what form it comes back: a pull request with evidence, a report with sources, tests that fail before and pass after. The output format is what lets you check without reopening everything.
- **Escalation.** When it stops and asks, and to whom. An agent that never escalates makes decisions it shouldn't; one that always escalates gives the work back to you.

For the surface, that translates into a short list. The screen for managing agents needs to show the state of each one, what it's waiting for from you, what's blocked and why, and the evidence of each result, one click away. Everything else is decoration. It's also the list that fixes how many agents one person can really supervise, which is [a human limit, not a technical one](/en/blog/human-limits-managing-ai-agents).

## Agents that run behind

The last step is the one where the human doesn't start the work. The chain looks like this: a customer leaves feedback, a ticket is created, an agent develops it, and the human supervises the *performance* of that process through evals (automated too), external feedback and final testing. Nobody opens a session.

It sounds like speculation, but the pieces already exist. [Linear turned agents into workspace members](https://linear.app/changelog/2025-05-20-linear-for-agents) in May 2025, and three months later its [Cursor integration](https://linear.app/changelog/2025-08-21-cursor-agent) allowed triage rules that assign issues to the agent automatically. Copilot [picks up Jira issues](https://github.blog/changelog/2026-03-05-github-copilot-coding-agent-for-jira-is-now-in-public-preview/) and Cursor [does too](https://cursor.com/changelog/page/6). Anthropic's [Routines](https://claude.com/blog/introducing-routines-in-claude-code) run a saved agent in the cloud on a schedule, when called through an API or on a GitHub event, without a laptop switched on. The Copilot app ships its own [scheduled automations](https://github.blog/changelog/2026-06-17-github-copilot-app-generally-available/). Most of it is still in preview, but it's already launched.

In that world, the interface for this kind of work is no longer a window where you type. It's a dashboard of metrics and a queue of what needs your judgement. The result arrives where you already are, which is the same movement I described in [Bring Your App to the Agent](/en/blog/bring-your-app-to-the-agent), seen from the developer's side.

## And reading the code?

There are cases where you want to be close to the code: a delicate change, a piece you don't trust, an exploration where you don't yet know what you're looking for. That doesn't go away, but it's becoming the edge case, as long as the evidence can be extracted. You can ask the agent for the exact fragment it changed, open it in the repository, request the test that proves it. What matters is [verifying the result, not re-reading the path](/en/blog/results-oriented-programming), and a good surface puts that evidence one click away.

## What comes next

The terminal isn't dying. It is becoming the substrate: the place where the agent executes, and a surface among others for whoever prefers it. The editor isn't dying either; it's what you open when you need to look closely. What's happening is that the interface is decoupling from the agent. You'll choose the surface by moment and by device, while the harness underneath stays the same.

What will set a team apart, then, is not which window it uses. It's how well it has defined what its agents may do, what they receive, what they return and when they call a human. That's a management problem, and it's where the interface is heading: fewer keyboards and more dashboards.

---

*Sources for the dates in the timeline: [Copilot preview](https://github.blog/news-insights/product-news/introducing-github-copilot-ai-pair-programmer/) · [Copilot GA](https://github.blog/news-insights/product-news/github-copilot-is-generally-available-to-all-developers/) · [Copilot X](https://github.blog/news-insights/product-news/github-copilot-x-the-ai-powered-developer-experience/) · [Copilot Chat GA](https://github.blog/news-insights/product-news/github-copilot-chat-now-generally-available-for-organizations-and-individuals/) · [Cursor 0.43](https://cursor.com/changelog/0-43-x) · [Cursor 2.0](https://cursor.com/changelog/2-0) · [Aider releases](https://github.com/Aider-AI/aider/releases) · [Claude Code preview](https://www.anthropic.com/news/claude-3-7-sonnet) · [Codex CLI](https://community.openai.com/t/this-weeks-launches-o3-o4-mini-gpt-4-1-and-codex-cli/1230312) · [Copilot CLI GA](https://github.blog/changelog/2026-02-25-github-copilot-cli-is-now-generally-available/) · [Devin](https://x.com/cognition/status/1767548763134964000) · [Cursor Background Agents](https://cursor.com/changelog/0-50) · [Codex cloud](https://openai.com/index/introducing-codex/) · [Copilot coding agent](https://github.blog/changelog/2025-05-19-github-copilot-coding-agent-in-public-preview/) · [Claude Code on the web](https://www.anthropic.com/news/claude-code-on-the-web) · [Claude Code in the desktop app](https://www.anthropic.com/news/claude-opus-4-5) · [Codex app](https://techcrunch.com/2026/02/02/openai-launches-new-macos-app-for-agentic-coding/) · [Cursor 3](https://cursor.com/blog/cursor-3) · [Claude Code desktop redesign](https://claude.com/blog/claude-code-desktop-redesign) · [Copilot app GA](https://github.blog/changelog/2026-06-17-github-copilot-app-generally-available/) · [Linear for Agents](https://linear.app/changelog/2025-05-20-linear-for-agents) · [Cursor in Linear](https://linear.app/changelog/2025-08-21-cursor-agent) · [Copilot for Jira](https://github.blog/changelog/2026-03-05-github-copilot-coding-agent-for-jira-is-now-in-public-preview/) · [Routines](https://claude.com/blog/introducing-routines-in-claude-code) · [Cursor in Jira](https://cursor.com/changelog/page/6).*
