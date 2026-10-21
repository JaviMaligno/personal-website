---
title: "The Rule Was on the Other Branch"
description: "A team's practices live in a repo checklist, an org wiki, a project convention and people's heads. delivery-loop writes each one once, at the level where it is true, so the organisation's part is shared, yours is written once, and each repo's travels with the repo."
pubDate: 2026-11-17
tags: ["AI Agents", "Claude Code", "Codex", "Software Delivery", "Developer Experience"]
lang: en
translationKey: the-rule-was-on-the-other-branch
heroImage: "/blog/the-rule-was-on-the-other-branch.png"
repoUrl: "https://github.com/JaviMaligno/delivery-loop"
---

<style>
.dl-fig { margin: 2rem 0; }
.dl-fig svg { width: 100%; height: auto; display: block; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; }
.dl-fig figcaption { font-size: 0.9rem; color: #94a3b8; margin-top: 0.6rem; }
</style>

Every team I have worked with keeps its practices in a dozen places. The PR checklist lives in one repository. Who promotes to production is on a wiki page for the whole organisation. The branch a project integrates into is a convention of that project. The test command is in a README, unless it moved to a Makefile. And a good part of it lives only in the heads of the people who have been there longest.

People absorb this over months. An agent starts every session without any of it, or with a copy someone pasted into a prompt that went stale the week after.

[delivery-loop](https://github.com/JaviMaligno/delivery-loop) is a plugin for Claude Code and Codex that takes a task from its ticket to a change verified in a test environment and handed over. Taking a task to the end is not new by itself. What makes it work in more than one place is where the agent gets the practices of the place it runs in, how they are shared between the people who use it, and how they stay current without anyone maintaining them.

## The loop, phase by phase

First, what the loop does. A task goes through ten phases; a small one skips the spec, the open questions and the plan.

<figure class="dl-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="The ten phases of the loop in four groups: understand (start, spec, gaps, plan), build (implement, review), prove (integrate until the test environment serves the exact commit, live verification with evidence per requirement) and hand over (promote or hand off, close the ticket).">
  <g font-family="ui-sans-serif,system-ui,sans-serif" text-anchor="middle">
    <g fill="#22222e" stroke-width="1.5">
      <rect x="20" y="30" width="100" height="62" rx="8" stroke="#94a3b8"/>
      <rect x="134" y="30" width="100" height="62" rx="8" stroke="#94a3b8"/>
      <rect x="248" y="30" width="100" height="62" rx="8" stroke="#94a3b8"/>
      <rect x="362" y="30" width="100" height="62" rx="8" stroke="#94a3b8"/>
      <rect x="476" y="30" width="100" height="62" rx="8" stroke="#2dd4bf"/>
      <rect x="20" y="146" width="100" height="62" rx="8" stroke="#2dd4bf"/>
      <rect x="134" y="146" width="100" height="62" rx="8" stroke="#f59e0b"/>
      <rect x="248" y="146" width="100" height="62" rx="8" stroke="#f59e0b"/>
      <rect x="362" y="146" width="100" height="62" rx="8" stroke="#e2e8f0"/>
      <rect x="476" y="146" width="100" height="62" rx="8" stroke="#e2e8f0"/>
    </g>
    <g fill="#e2e8f0" font-size="14" font-weight="600">
      <text x="70" y="56">0 start</text>
      <text x="184" y="56">1 spec</text>
      <text x="298" y="56">2 gaps</text>
      <text x="412" y="56">3 plan</text>
      <text x="526" y="56">4 implement</text>
      <text x="70" y="172">5 review</text>
      <text x="184" y="172">6 integrate</text>
      <text x="298" y="172">7 live</text>
      <text x="412" y="172">8 promote</text>
      <text x="526" y="172">9 close</text>
    </g>
    <g fill="#94a3b8" font-size="11">
      <text x="70" y="76">done yet? size</text>
      <text x="184" y="76">points with IDs</text>
      <text x="298" y="76">open questions</text>
      <text x="412" y="76">reviewed plan</text>
      <text x="526" y="76">tests first</text>
      <text x="70" y="192">second opinion</text>
      <text x="184" y="192">serves exact SHA</text>
      <text x="298" y="192">evidence per ID</text>
      <text x="412" y="192">or hand-off</text>
      <text x="526" y="192">ticket, cleanup</text>
    </g>
    <g stroke="#64748b" stroke-width="1.5" fill="none">
      <path d="M120 61 L132 61"/><path d="M234 61 L246 61"/><path d="M348 61 L360 61"/><path d="M462 61 L474 61"/>
      <path d="M120 177 L132 177"/><path d="M234 177 L246 177"/><path d="M348 177 L360 177"/><path d="M462 177 L474 177"/>
      <path d="M526 92 L526 119 L70 119 L70 144"/>
    </g>
    <g font-size="12">
      <rect x="60" y="234" width="10" height="10" rx="2" fill="none" stroke="#94a3b8"/><text x="112" y="243" fill="#94a3b8">understand</text>
      <rect x="190" y="234" width="10" height="10" rx="2" fill="none" stroke="#2dd4bf"/><text x="226" y="243" fill="#5eead4">build</text>
      <rect x="290" y="234" width="10" height="10" rx="2" fill="none" stroke="#f59e0b"/><text x="328" y="243" fill="#fbbf24">prove</text>
      <rect x="390" y="234" width="10" height="10" rx="2" fill="none" stroke="#e2e8f0"/><text x="446" y="243" fill="#e2e8f0">hand over</text>
    </g>
  </g>
</svg>
<figcaption>Ten phases in four groups. A small task goes from start straight to implement.</figcaption>
</figure>

- **Understand.** It checks whether the work is already done (a ticket marked as pending can be in production through a PR that never cited it), creates an isolated workspace and sizes the task. It turns the ticket or document into points with stable IDs, separates what only a person can decide, and writes a plan that another agent reviews before any code.
- **Build.** Tests first, then the change, in commits tied to the IDs; then an independent review by whichever reviewers the profile names.
- **Prove.** After merging, it waits until the test environment serves that exact commit, not until the deploy says success. Then it checks every ID against the deployed environment. Wherever there is something to see, the evidence is visual: screenshots or a recording, uploaded to the ticket. An API or a queue gets a real response instead.
- **Hand over.** Promotion to production, or, when that belongs to someone else, an explicit hand-off with the prepared material. Then the ticket moves to done with its evidence, and branches, workspaces and test data are cleaned up.

Almost every one of those steps leans on a practice of the place: which ticket state means "in review", who reviews, which branch to integrate into, how a change reaches the test environment, who promotes. That is what the profiles are for.

## Each practice is written once, at its level

The plugin's core names no tool. Everything specific to a place goes in a profile, and profiles come in levels that mirror where practices already live. "Promotion to production belongs to the platform team" is true for the whole organisation, so it goes in the organisation profile. "This repo integrates into `develop`" is true for one repository, so it goes there. Nothing is copied into every repo, and nothing is in the plugin.

<figure class="dl-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Five profile levels from far to near: plugin defaults, updated with the plugin; user, written once by each person; organisation, shared and maintained in one place; project, shared and installed only by those who work on it; repository, committed to the repo and updated with it. The nearest level wins, except for invariants.">
  <g font-family="ui-sans-serif,system-ui,sans-serif">
    <text x="40" y="22" fill="#94a3b8" font-size="12">level</text>
    <text x="330" y="22" fill="#94a3b8" font-size="12">written by · updated when</text>
    <rect x="30" y="32" width="540" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="48" y="55" fill="#e2e8f0" font-size="15" font-weight="600">Defaults</text>
    <text x="48" y="72" fill="#94a3b8" font-size="12">invariants, authority, method</text>
    <text x="330" y="62" fill="#e2e8f0" font-size="13">the plugin · each release</text>
    <rect x="30" y="92" width="540" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="48" y="115" fill="#e2e8f0" font-size="15" font-weight="600">User</text>
    <text x="48" y="132" fill="#94a3b8" font-size="12">accounts, machine, tools, autonomy</text>
    <text x="330" y="122" fill="#e2e8f0" font-size="13">you · once</text>
    <rect x="30" y="152" width="540" height="50" rx="8" fill="#2a2418" stroke="#f59e0b"/>
    <text x="48" y="175" fill="#fbbf24" font-size="15" font-weight="600">Organisation</text>
    <text x="48" y="192" fill="#94a3b8" font-size="12">tracker, reviewers, CI policy, who promotes</text>
    <text x="330" y="182" fill="#e2e8f0" font-size="13">shared repo · a PR, for everyone</text>
    <rect x="30" y="212" width="540" height="50" rx="8" fill="#2a2418" stroke="#f59e0b"/>
    <text x="48" y="235" fill="#fbbf24" font-size="15" font-weight="600">Project</text>
    <text x="48" y="252" fill="#94a3b8" font-size="12">environments, releases, test identity</text>
    <text x="330" y="242" fill="#e2e8f0" font-size="13">shared repo · if you work on it</text>
    <rect x="30" y="272" width="540" height="50" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="48" y="295" fill="#5eead4" font-size="15" font-weight="600">Repository</text>
    <text x="48" y="312" fill="#94a3b8" font-size="12">branches, test commands, deploy, URLs</text>
    <text x="330" y="302" fill="#e2e8f0" font-size="13">the repo itself · with every pull</text>
  </g>
</svg>
<figcaption>Levels merge from far to near and the nearest wins, except invariants such as "production is never tested against", which no lower level can relax. The amber levels are the shared ones: written once, by whoever knows, for everyone.</figcaption>
</figure>

## Built to be shared

This is what makes it worth setting up. An organisation keeps its profiles in one private repository: the organisation level and one profile per project. A new person installs the plugin, runs one script, and gets the organisation profile plus the profiles of the projects whose repos they actually have. Nothing else.

What is left for them is small and mostly written once:

- **Their user profile.** Their accounts, their machine's limits, the browser tool they use. Written once, kept forever, and never part of a shared file: the shared repo's CI checks that no shared profile holds personal data.
- **Each new repo.** The first run in a repo without a profile detects what it can (remote, branch protection, CI jobs, test runners, deploy configuration) and asks only what detection cannot settle, once, with a recommended answer. The result is committed in the repo, so the next colleague who pulls it gets it without running anything. For a client's repository, the same profile stays local, inside `.git`, so it is never pushed to the client.

Nobody re-learns the organisation. When a rule changes for everyone, it changes in one place with a PR, and everyone gets it on the next install. When a repo changes its integration branch, the profile in that repo changes with it.

## Same plugin, two organisations

I run it in two organisations that work very differently. In one, the integration branch is `develop`, a change reaches the test environment by bumping a version in a separate config repository, and promotion beyond that belongs to another team. In the other, several client projects each have their own environments and release process, reviews include the company's own review agents, and client repositories must never receive our files.

The core is the same in both, unchanged, in Claude Code and in Codex. Every one of those differences is a line in a profile at its level. The public repo carries only fictitious example profiles; the real ones live in each organisation's private repo.

## Keeping them current

A profile that was right when written goes stale on its own, the same way [the memories my agent keeps](/en/blog/the-memory-that-was-true) did: never wrong when written, describing a state that expired. So the profile is treated as something to re-check, not to trust:

- At the start of every task, a cheap recheck compares the profile with what the repo shows. A mismatch updates that datum at its level and gets one line in the report.
- Any datum older than 30 days is verified again before the loop relies on it.
- When the profile and another source disagree, the newer dated source wins, and the stale one is fixed where it lives, so the fix reaches everyone who shares that level.
- The profiles are merged again mid-task, because rules can change while the work is in progress.

## The rule was on the other branch

Keeping the practices current is only half of it. The agent also has to read the current ones, and that is where a real run surprised me.

A repository I work in had added a rule to its PR checklist: a person must attest that they have reviewed any AI-generated code before it ships. One run stopped before merging and asked me for that review. Two earlier runs in the same repository had merged without it. The rule was current and in the right place, the integration branch. But all three sessions had been launched from a checkout sitting on an older branch, whose instruction files predate the rule. The work then happened in a fresh worktree on the integration branch. The run that stopped happened to re-read the instructions there; the others worked from the copy they started with.

<figure class="dl-fig">
<svg viewBox="0 0 600 200" role="img" aria-label="Sessions start from a checkout on an old branch whose instruction files have no review rule. The work happens in a worktree on the integration branch, where the rule exists. A run that re-reads the worktree's instructions stops before merging; one that keeps the launch copy merges without the rule.">
  <g font-family="ui-sans-serif,system-ui,sans-serif">
    <rect x="30" y="24" width="250" height="62" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.15)"/>
    <text x="155" y="48" fill="#e2e8f0" font-size="14" font-weight="600" text-anchor="middle">Launch checkout</text>
    <text x="155" y="68" fill="#94a3b8" font-size="12" text-anchor="middle">old branch · no review rule</text>
    <rect x="320" y="24" width="250" height="62" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="445" y="48" fill="#5eead4" font-size="14" font-weight="600" text-anchor="middle">Task worktree</text>
    <text x="445" y="68" fill="#94a3b8" font-size="12" text-anchor="middle">integration branch · rule present</text>
    <path d="M282 55 L316 55" stroke="#64748b" stroke-width="2"/>
    <path d="M308 49 L318 55 L308 61 Z" fill="#64748b"/>
    <path d="M155 88 L155 124" stroke="#64748b" stroke-width="2" stroke-dasharray="5 4"/>
    <path d="M445 88 L445 124" stroke="#2dd4bf" stroke-width="2"/>
    <rect x="30" y="126" width="250" height="50" rx="8" fill="#2a2418" stroke="#f59e0b"/>
    <text x="155" y="148" fill="#fbbf24" font-size="13" text-anchor="middle">keeps the launch copy</text>
    <text x="155" y="166" fill="#94a3b8" font-size="12" text-anchor="middle">merges without the rule</text>
    <rect x="320" y="126" width="250" height="50" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="445" y="148" fill="#5eead4" font-size="13" text-anchor="middle">re-reads in the worktree</text>
    <text x="445" y="166" fill="#94a3b8" font-size="12" text-anchor="middle">stops, asks for human review</text>
  </g>
</svg>
<figcaption>The rule existed and was current. Whether it applied depended on which copy of the practices the agent was reading.</figcaption>
</figure>

So now it is not left to chance: when a session was launched from a branch other than the integration or production branch, the plugin reads the repository's instruction files from the workspace where the work happens and logs which branch they came from.

## Fewer questions on the way

Shared, current profiles are also what let the loop run without stopping to ask. Before starting, it probes every capability the task will use with a real call, because configured is not authenticated and authenticated is not working: a tool listed as connected can fail on its first call, and `gh auth status` can report one account while commands run as another. Whatever fails is raised in a single round, and the answer is saved at its level so no one asks again. What remains for a person are the decisions that are genuinely theirs: a business call, a client-facing text, the attestation that rule exists to protect.

---

*[delivery-loop on GitHub](https://github.com/JaviMaligno/delivery-loop) (MIT). Install in Claude Code with `claude plugin marketplace add JaviMaligno/delivery-loop`, or in Codex with `codex plugin marketplace add JaviMaligno/delivery-loop`. More of what I package for agents in [Plugins & Skills](/en/skills).*
