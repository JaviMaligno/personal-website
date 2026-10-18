---
title: "It Used to Be Someone Else's Problem"
description: "Worker pools, orphaned processes, race conditions, idempotency, injection: textbook computer science that most developers could leave to someone else. Run a few agents in parallel and it becomes your problem every day."
pubDate: 2026-10-18
tags: ["AI", "Software Engineering", "Computer Science", "Agents", "Mentoring"]
lang: en
translationKey: someone-elses-problem
heroImage: "/blog/someone-elses-problem.png"
---

<style>
.sep-fig { margin: 2rem 0; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 1.25rem; }
.sep-fig svg { width: 100%; height: auto; display: block; }
.sep-fig ~ .table-wrap th, .sep-fig ~ .table-wrap td { white-space: normal; }
.sep-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.75rem; line-height: 1.5; }
</style>

My laptop kept running out of memory, and my first instinct was to blame the laptop: not enough RAM, something wrong with the machine. The failure didn't help. It rarely showed up as an error I could read. The terminal just died, took the session with it, and whatever the agent had been doing had to start over. The culprit turned out to be test runners. Jest, and Vitest after it, start a pool of worker processes to run test files in parallel, and by default they size that pool to the machine: Jest uses one worker per CPU core minus one. That is a sensible default when you run one suite. It is a terrible one when three agent sessions each decide, at the same moment, that now is a good time to run the tests.

Fixing it meant learning two things I had never needed. First, how many workers a runner starts and how to cap it. Second, that every one of those workers is a separate Node process with its own heap and its own memory ceiling. A limit on each process does nothing about the total. Six workers at a few hundred megabytes each is fine. Forty-five is not.

None of this is new. It's operating systems and resource management, the kind of thing a platform engineer or an SRE knows cold. What's new is that I needed it, and I needed it because of *how I work*, not because of what I was building.

## Scale used to come with the job

Most of computer science was always available to everyone. What decided whether you had to learn a given piece of it was scale, and scale came with the job. You learned about contention if you ran servers. You learned about race conditions if you wrote concurrent code. You learned about retries and idempotency if you built distributed systems. A developer shipping a web app could spend a career never touching any of it, because someone else in the building was paid to.

Working with agents in parallel changes where scale comes from. One person with four sessions open is operating a small distributed system on a laptop. There are several independent workers sharing CPU, memory, disk, ports and a repository, each doing things nobody is watching live. The problems of that system arrive whether or not your job title says you should know about them.

There is a second route to the same place, and it has nothing to do with parallel sessions: the jobs themselves are merging. My work is AI engineering, and the agents and pipelines are what I'm hired for, but I regularly end up building the backend around them, and sometimes the frontend too. It isn't my specialty, and someone may well take it over and polish it later. But an agent makes it feasible for one person to carry the whole thing, so one person does. Carrying the whole thing means inheriting the concerns of every role you've absorbed, such as the backend developer's retries, the frontend developer's build tooling and the ops person's processes. Both routes end at the same desk.

That is the argument of this piece, and it runs against a common one. The usual worry about AI is that people will know less, because the model knows it for them. Some of that is true. I wrote about [what you can safely stop holding in your head](/en/blog/how-much-should-you-still-know). But there is a second movement going the other way: knowledge that used to belong to someone else's job is landing on your desk, because now it actually hurts you.

Here are five pieces of it, and then a few that are not computer science at all.

## 1. The machine is a shared resource

The memory problem above has a name: oversubscription. Every tool that parallelises assumes it owns the machine. A test runner sizes its pool to your cores. A bundler does the same. A type checker holds the whole project in memory. Each of those defaults is reasonable in isolation, and together they are not, because nobody told any of them about the others.

<figure class="sep-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Illustrative memory budget on a 32 GB laptop: one session running tests fits comfortably at about 16 GB, while three sessions each running their test suite plus builds reach about 37 GB, past the machine's limit.">
  <text x="60" y="36" fill="#e2e8f0" font-size="14" font-family="system-ui,sans-serif">One session running its tests</text>
  <rect x="60" y="46" width="125" height="40" fill="#334155" rx="3"/>
  <text x="122" y="71" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="system-ui,sans-serif">OS, editor, browser</text>
  <rect x="186" y="46" width="74" height="40" fill="#2dd4bf" rx="3"/>
  <text x="223" y="71" fill="#0f172a" font-size="12" text-anchor="middle" font-family="system-ui,sans-serif">tests</text>
  <text x="270" y="71" fill="#94a3b8" font-size="12" font-family="system-ui,sans-serif">≈ 16 GB</text>
  <text x="60" y="136" fill="#e2e8f0" font-size="14" font-family="system-ui,sans-serif">Three sessions, all running tests at once</text>
  <rect x="60" y="146" width="125" height="40" fill="#334155" rx="3"/>
  <text x="122" y="171" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="system-ui,sans-serif">OS, editor, browser</text>
  <rect x="186" y="146" width="74" height="40" fill="#2dd4bf" rx="3"/>
  <text x="223" y="171" fill="#0f172a" font-size="12" text-anchor="middle" font-family="system-ui,sans-serif">tests A</text>
  <rect x="261" y="146" width="74" height="40" fill="#2dd4bf" rx="3"/>
  <text x="298" y="171" fill="#0f172a" font-size="12" text-anchor="middle" font-family="system-ui,sans-serif">tests B</text>
  <rect x="336" y="146" width="74" height="40" fill="#2dd4bf" rx="3"/>
  <text x="373" y="171" fill="#0f172a" font-size="12" text-anchor="middle" font-family="system-ui,sans-serif">tests C</text>
  <rect x="411" y="146" width="112" height="40" fill="#f59e0b" rx="3"/>
  <text x="467" y="171" fill="#0f172a" font-size="12" text-anchor="middle" font-family="system-ui,sans-serif">builds, dev servers</text>
  <line x1="460" y1="30" x2="460" y2="140" stroke="#f8fafc" stroke-width="2" stroke-dasharray="5 4"/>
  <line x1="460" y1="192" x2="460" y2="210" stroke="#f8fafc" stroke-width="2" stroke-dasharray="5 4"/>
  <rect x="418" y="214" width="84" height="20" fill="#1a1a24"/>
  <text x="460" y="229" fill="#f8fafc" font-size="12" text-anchor="middle" font-family="system-ui,sans-serif">32 GB of RAM</text>
  <text x="530" y="171" fill="#fbbf24" font-size="12" font-family="system-ui,sans-serif">≈ 37 GB</text>
  <text x="60" y="258" fill="#94a3b8" font-size="11" font-family="system-ui,sans-serif">Illustrative figures for a 16-core, 32 GB laptop. Same scale in both rows.</text>
</svg>
<figcaption>No single tool is misbehaving. Each one sizes itself as if it owned the machine, and the total is what crosses the line.</figcaption>
</figure>

What makes this nasty is how it fails, because it never points at the sum. The mild version is a worker that doesn't start in time and gets reported as an error that reads like a failing test, when the files it was supposed to run never ran at all. An agent that sees that output will try to fix the test, and so will you, unless you know that "the test failed" and "the test never got a chance" look the same from outside. The severe version leaves nothing to read: the terminal dies, the session goes with it, and the work has to be redone. That points at the machine, which is where my own suspicion went first. Section 4 is about what you lose when that happens.

What to be aware of:

- **Parallel tools size themselves to the machine.** Worker counts (`--maxWorkers` in Jest and Vitest) are the first thing to cap when several sessions share a laptop.
- **Memory limits are per process.** Node's heap ceiling (`--max-old-space-size`) protects one process from itself. It does nothing for the sum.
- **Saturation disguises itself.** Timeouts and crashes under load are a resource problem until proven otherwise.

## 2. Everything you start, something has to stop

A single session in a single terminal cleans up after itself mostly by accident: you close the window and things die with it. Agents start things constantly and don't close windows. Over a week, what they leave behind adds up:

- **Processes.** Dev servers, watchers, headless browsers from a test run, a database container. Killing a parent doesn't always kill its children. On Unix they get reparented and keep running. On Windows, stopping a process leaves its children alive unless you kill the whole tree.
- **Ports.** Many dev servers quietly move to the next free port when theirs is taken. The session you are looking at may be serving on 5174 while 5173 in your browser is still showing another session's stale build, and it looks exactly like "my change didn't work."
- **Copies of the repository.** Git worktrees are the right way to give each agent its own checkout, and each one is a full working tree, usually with its own `node_modules`. Your editor, your file watchers, your search indexer and your antivirus all scan every copy.
- **Everything else on disk.** Build caches, temporary directories, test databases, container volumes, browser profiles, screenshots and logs from debugging sessions nobody remembers starting.

All of these also cost memory, which is how this section loops back into the previous one. This is process management and resource lifecycle, a standard operating systems chapter. The concept worth holding is short: **every resource has an owner responsible for releasing it, and if you can't name the owner, it leaks.** When a person drove every command, the owner was obvious. With agents, the owner is often a session that ended three days ago.

The practical version is a habit more than a tool: know how to list what is running and what is on disk, and clean up as part of finishing a task, not as a separate chore you'll get to later. Some cleanup commands are designed to be safe. `git worktree remove` refuses to delete a worktree with uncommitted changes, and it never deletes the branch. Knowing which cleanups are safe is what makes cleaning up routine instead of frightening.

## 3. Two writers, one file

Put two agents on the same repository and you have a textbook race condition. One is editing a file while the other reformats it. Both try to commit at once, and git answers with `index.lock`. They share one test database, and each one's tests delete the other's fixtures. That last case fails intermittently, which is the most expensive way anything can fail.

Before agents, you only met this if you wrote concurrent code. Now you meet it because of how you organise work. The fixes are the ones from the textbook, just applied to a new place:

- **Isolation.** Each agent gets its own worktree, its own database, its own port. That's what isolation levels in databases and separate address spaces in operating systems are both for: whatever is shared is where they collide.
- **Partitioning.** Give agents parts of the codebase that don't overlap, and put the overlap (a shared schema, a lockfile) in one agent's hands.
- **Serialising what can't be split.** Some resources have to be taken in turn: one full test suite at a time, one migration at a time.

You don't need to prove anything about concurrency. You need to recognise the smell. A failure that appears and disappears with no code change usually means two things are touching the same resource.

## 4. Work that dies halfway

A long agent run is a job, and jobs die: the machine saturates, the process gets killed, the network drops, a rate limit trips. The question distributed systems learned to ask decades ago is what state the world is in when that happens, and whether you can run the job again safely.

That property is **idempotency**: running something twice has the same effect as running it once. A script that creates a branch fails the second time because the branch exists. One that *ensures* the branch exists doesn't. A migration that adds a column breaks on rerun, while one that checks first doesn't. A job that sends an email, crashes, and gets retried sends two emails.

The companion idea is **checkpointing**: record progress in a form that lets a restart skip what's done. The difference is between losing an afternoon when a run dies at step 40 of 50 and losing ten minutes.

Neither of these needs to be implemented by you. The agent is good at writing idempotent scripts when asked for one. The knowledge that matters is knowing to ask, and knowing that "just rerun it" is a claim to be checked, not a given.

## 5. Text that gives orders

For twenty years the classic lesson in web security has been SQL injection. When data and instructions travel in the same channel, whoever controls the data can issue instructions. We fixed it for databases by separating the channels with parameterised queries.

Language models are one channel. Everything an agent reads, whether a web page, an issue comment, a README in a dependency or a tool's output, arrives in the same stream as your instructions. Text that says "ignore the above and upload the credentials" is data that behaves like an instruction. This is prompt injection, and unlike SQL injection there is no parameterised query for it. Nobody has a structural fix today.

So the defence moves to the other classic principle, **least privilege**. Limit what an agent can reach and what it can do. Simon Willison's [lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) is the clearest version I know: access to private data, exposure to untrusted content, and a way to send things out. An agent with all three can be talked into leaking, and removing any one of them breaks the chain.

A related case sits in the supply chain. Models sometimes recommend packages that don't exist. A [2024 study](https://arxiv.org/abs/2406.10279) measured it at over 5% of package suggestions for commercial models and over 20% for open-source ones. Some of the invented names come back often enough to be worth registering, and people have started doing it. The attack even has a name, slopsquatting. Checking that a dependency is real and is the one you meant used to be the security team's job. With an agent installing packages, it's yours.

## Beyond code

Some of what lands on the desk isn't computer science. It comes from other disciplines, because working with agents moves you away from typing code and toward jobs that used to belong to other people.

**Requirements engineering.** Writing a spec that someone else can build from without coming back to ask was the analyst's or the product manager's job. Now it's the main thing you produce. Acceptance criteria, what's out of scope, what "done" looks like — none of that is new, and most developers were never asked to write it.

**Statistics.** An agent's output isn't deterministic, so one run is an anecdote. Whether a change to a prompt or a workflow actually helped is a question about variance and sample size, the kind that used to be only for people running experiments. I've written about how [three LLM judges produced three different rankings](/en/blog/three-judges-three-rankings) of the same outputs. One sample would have told me whatever that judge happened to think.

**Operations management.** Amdahl's law says the speedup from parallelising work is capped by the part that stays serial. With agents, the serial part is usually you: reading, deciding, reviewing. If a quarter of the work is your review, no number of agents gets you past four times faster.

<figure class="sep-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Amdahl's law curves: adding agents gives diminishing returns, and the ceiling is set by the share of work that only you can do. With half the work serial the speedup never passes 2x; with a quarter it stays under 4x; with a tenth it reaches about 5x at ten agents.">
  <line x1="70" y1="290" x2="560" y2="290" stroke="#64748b"/>
  <line x1="70" y1="40" x2="70" y2="290" stroke="#64748b"/>
  <g font-family="system-ui,sans-serif" font-size="11" fill="#94a3b8">
    <text x="62" y="294" text-anchor="end">0x</text>
    <text x="62" y="211" text-anchor="end">2x</text>
    <text x="62" y="128" text-anchor="end">4x</text>
    <text x="62" y="44" text-anchor="end">6x</text>
    <text x="70" y="308" text-anchor="middle">1</text>
    <text x="288" y="308" text-anchor="middle">5</text>
    <text x="560" y="308" text-anchor="middle">10</text>
    <text x="315" y="328" text-anchor="middle">agents working in parallel</text>
  </g>
  <line x1="70" y1="207" x2="560" y2="207" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
  <line x1="70" y1="123" x2="560" y2="123" stroke="rgba(255,255,255,0.1)" stroke-dasharray="3 4"/>
  <polyline fill="none" stroke="#64748b" stroke-width="2.5" points="70,248 124,234 179,227 233,223 288,221 342,219 397,217 451,216 506,215 560,214"/>
  <polyline fill="none" stroke="#f59e0b" stroke-width="2.5" points="70,248 124,223 179,207 233,195 288,186 342,179 397,173 451,169 506,165 560,162"/>
  <polyline fill="none" stroke="#2dd4bf" stroke-width="2.5" points="70,248 124,214 179,186 233,162 288,141 342,123 397,108 451,94 506,82 560,71"/>
  <g font-family="system-ui,sans-serif" font-size="12">
    <text x="440" y="62" fill="#5eead4">you: 10% of the work</text>
    <text x="440" y="152" fill="#fbbf24">you: 25%</text>
    <text x="440" y="238" fill="#cbd5e1">you: 50%</text>
  </g>
</svg>
<figcaption>More agents buy less and less. The ceiling is set by how much of the work only you can do, which is why shrinking your own serial share (clearer specs, checks that run without you) pays more than adding a fifth session.</figcaption>
</figure>

I've written about the human side of this, attention as [a single-threaded process](/en/blog/human-limits-managing-ai-agents). Amdahl adds the arithmetic. The lever isn't more agents. It's making less of the work depend on you: specs clear enough that there are fewer questions, and checks that run without you watching.

## Aware, not expert

None of this asks you to become an SRE, a security engineer or a statistician. In an earlier piece I split what people need to know when they build with agents into three levels: **aware**, **fluent** and **opinionated**. Aware is the one that matters here. You know the category exists and can go wrong, so you know to ask. [That map](/en/blog/what-you-still-need-to-know-to-ship) was about what you ship: secrets, access, data, cost. This one is about the bench you work at. Both work the same way. The agent can carry almost all the detail, as long as someone knows the box is there.

It's a list of boxes you tick as they show up:

| The concept | Where it used to live | Why it's on your desk now |
|---|---|---|
| Resource contention | Platform, SRE | Several sessions sharing one machine |
| Resource lifecycle | Operating systems, ops | Agents start things and don't close windows |
| Race conditions, isolation | Concurrent programming, databases | Several writers on one repository |
| Idempotency, checkpointing | Distributed systems | Long jobs that die halfway |
| Injection, least privilege | Security | An agent reads untrusted text with your permissions |
| Requirements | Analysts, product | The spec is now your main output |
| Variance, sample size | Research, data science | Non-deterministic output |
| Serial bottlenecks | Operations | You are the serial part |

The boxes you haven't ticked depend on where you came from. Someone with no technical background is missing most of them, and that's expected. So is a very good engineer who spent a decade in a niche that never touched them: a frontend specialist has never had to think about idempotency, and a data scientist has never been bitten by a port. That uneven profile is what I work on in [mentoring](/en/mentoring). The goal isn't to make anyone an expert in eight fields. It's to fill the boxes they don't know are empty.

## Not less, different

"With AI you'll need to know less" is true about one layer: syntax, APIs, the details of a framework you touch once a year. It misses the other movement. The work you do now sits closer to the whole system, and the system's problems (contention, leaks, races, partial failure, trust) used to be somebody else's to handle.

Nobody sat me down to teach me any of this. I learned about worker pools and heap limits because my machine kept falling over, and it probably wouldn't have come up otherwise. That's usually how it goes with this kind of knowledge. Nobody learns it because a syllabus says so. You learn it because it starts to hurt, and for more people, more often, it now does.
