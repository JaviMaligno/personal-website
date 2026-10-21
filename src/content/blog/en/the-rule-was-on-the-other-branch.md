---
title: "The Rule Was on the Other Branch"
description: "A team's practices live in a repo checklist, an org wiki, a project convention and people's heads. I built delivery-loop to write them down where they apply and keep them current. A real run showed why the second part matters: the rule that should have stopped a merge was current on one branch and missing from the copy the agents started with."
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

Every team I have worked with has its practices spread across a dozen places. The PR checklist lives in one repository. The rule about who promotes to production lives on a wiki page for the whole organisation. The branch a project integrates into is a convention of that project, sometimes written down, sometimes not. The test command is in a README, unless it moved to a Makefile. And a good part of it lives only in the heads of the people who have been there longest.

People cope with this because they absorb it over months. An agent starts every session without any of it, or with a copy someone pasted into a prompt that went stale the week after. I kept running into the same failures: work redone because an earlier branch was forgotten, "deployed" taken to mean "serving", a ticket closed without proof, and the same five questions about my environment at the start of every session.

So I built [delivery-loop](https://github.com/JaviMaligno/delivery-loop), a plugin that takes a task from its source (a ticket, a requirements document, a plain request) to a change that is merged, verified live in a test environment, handed over for promotion and closed. The loop itself is the easy part. The part I care about is how it learns the practices of the place it runs in, and how it keeps them current when they change.

## Practices have a level

The core of the plugin names no tool. It says what each phase takes in, what it produces and what evidence proves it is done. Everything specific to an environment goes in a profile, and profiles come in layers:

<figure class="dl-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Four profile levels stacked from far to near: plugin defaults, user, organisation or project, and repository. Each level holds different practices, the nearest level wins, and items marked invariant cannot be relaxed further down.">
  <g font-family="ui-sans-serif,system-ui,sans-serif">
    <rect x="40" y="24" width="370" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="58" y="47" fill="#e2e8f0" font-size="15" font-weight="600">Defaults</text>
    <text x="58" y="65" fill="#94a3b8" font-size="12">authority classes, invariants, methodology</text>
    <rect x="40" y="88" width="370" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="58" y="111" fill="#e2e8f0" font-size="15" font-weight="600">User</text>
    <text x="58" y="129" fill="#94a3b8" font-size="12">your machine, your access, your autonomy</text>
    <rect x="40" y="152" width="370" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="58" y="175" fill="#e2e8f0" font-size="15" font-weight="600">Organisation / project</text>
    <text x="58" y="193" fill="#94a3b8" font-size="12">tracker, CI conventions, reviewers, who promotes</text>
    <rect x="40" y="216" width="370" height="50" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="58" y="239" fill="#5eead4" font-size="15" font-weight="600">Repository</text>
    <text x="58" y="257" fill="#94a3b8" font-size="12">branches, test commands, environment URLs</text>
    <line x1="440" y1="40" x2="440" y2="250" stroke="#64748b" stroke-width="2"/>
    <path d="M432 240 L440 254 L448 240 Z" fill="#64748b"/>
    <text x="456" y="120" fill="#e2e8f0" font-size="13">far → near</text>
    <text x="456" y="140" fill="#94a3b8" font-size="12">nearest wins</text>
    <text x="456" y="176" fill="#fbbf24" font-size="12">[invariant]</text>
    <text x="456" y="194" fill="#94a3b8" font-size="12">can't be relaxed</text>
    <text x="456" y="210" fill="#94a3b8" font-size="12">further down</text>
  </g>
</svg>
<figcaption>Each practice is written once, at the level where it is true. The nearest level wins, except for invariants such as "production is never touched", which no lower level can relax.</figcaption>
</figure>

This mirrors where practices already live. "Promotion to production belongs to team X" is true for the whole organisation, so it goes in the organisation profile. "This repo integrates into `develop`, not `main`" is true for one repository, so it goes there. None of it is copied into every repo, and none of it is in the plugin.

That last point is what lets the same loop run anywhere. The public repo only carries fictitious example profiles; the real ones for my company live in a private repo of that company. The same plugin runs, without changes, in Claude Code and in Codex.

## Writing them down without a questionnaire

Nobody fills in a forty-field profile, so a skill called `census` does most of it. It detects first: git remote and branch protection, CI configuration and which jobs run on which event, test runners, deploy configuration, the tools and MCP servers the session has. It only asks what detection cannot settle, once, with a recommended answer. Each datum is written at its level, with where it came from and when it was checked.

One rule there earned its place quickly: a procedure copied from a document is not a verified procedure. Before `census` writes "promote by merging branch A into B", it checks that the remote and the branch exist and that the push would fast-forward. If the documented procedure does not work, it writes the one that does, with the evidence.

## Keeping them current

A profile that was right when written goes stale on its own. I found the same thing when I [audited the memories my agent keeps](/en/blog/the-memory-that-was-true): the stale ones were never wrong when written, they described a state that expired. So the profile is treated as something to re-check, not something to trust:

- At the start of every task, a cheap recheck compares the profile with what the repo shows: remote, default branch, protection, deploy configuration, required checks. A mismatch updates that datum at its level and gets one line in the report.
- Any datum older than 30 days is verified again before the loop relies on it.
- When the profile and another source disagree, the newer dated source wins, the stale one is fixed where it lives, and the change is logged. Undated or same date: it asks. An old note pointing the tests at a shared account loses to a newer rule that requires a named one.
- Layout facts get no grace period. A repository moved to another folder kept a link in its profile that was dated, marked as verified, and already false, so paths and links are re-checked every time.
- The profiles are merged again on entering integration and live verification, because rules can change in the middle of a task.

That is the whole idea: write each practice where it applies, and assume it will change.

## A real run, in the other harness

I had been using the plugin with Claude Code for a couple of days. Then I installed it in Codex CLI (0.163, on gpt-6.1-sol at medium effort) and gave it a real ticket from work with a single instruction: implement it. The ticket asked to make the published API contract of a [classification service I maintain](/en/projects/compliance-classifier) match what the service actually emits, in five points.

In thirteen minutes it went from phase 0 to phase 6, with every step in its task log:

- **Start.** It sized the task as a feature, created an isolated worktree, and chose `develop` over a stale `main` because that is where the repo actually integrates, recording the decision.
- **Spec and gaps.** It turned the ticket into five requirements with stable IDs and recorded seven decisions. One of them declined a field on purpose: the schema promised a value that the formatter never emits, so instead of documenting it, the change removes the dead declaration and says why.
- **Plan.** A second agent reviewed the plan before any code.
- **Implement.** It wrote the failing contract tests first (14 red, 4 green), then the implementation, in commits tied to the requirement IDs.
- **Review and integrate.** An independent review, the PR opened, 199 tests green.

And then it stopped.

## The stop

The repository has a PR checklist, and one of its rules asks a person to attest that they have reviewed and validated any AI-generated code before it ships. Codex recorded it as decision D0.7, left that box unticked, and asked me for review instead of merging. Its own words in the decision: an automated review cannot satisfy a human attestation.

That rule was not new: it had been on the integration branch for two and a half weeks. The two previous tickets in the same repository had gone through the same plugin with Claude Code over the preceding day, and both were merged without it. It looks like a difference between agents. It isn't, and the real cause is more useful.

All three runs were launched from the same directory, my main checkout of the repository, which happened to sit on a branch from the start of the month. Its instruction files predate the rule: neither mentions the PR checklist. The loop then does its work in a fresh worktree on the integration branch, where the instructions are current and the rule is there. So every run started with the same out-of-date copy of the repository's practices, and the current ones were one directory away.

What differed is whether the agent went and read them. During phase 0, Codex opened the worktree's instruction file looking for its rules on development, testing and workflow, found the review rule, and later read the checklist itself before writing D0.7. Nothing in the plugin asked it to. The Claude runs worked on the same branch without re-reading those files; in one of them, the worktree's instructions first entered the context 94 minutes after the merge.

<figure class="dl-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="All runs started from a checkout on an old branch whose instruction files had no review rule. The work happened in a worktree on the integration branch, where the rule existed. Codex re-read the worktree's instructions in phase 0 and stopped before merging; the Claude runs did not re-read them and merged.">
  <g font-family="ui-sans-serif,system-ui,sans-serif">
    <rect x="30" y="24" width="250" height="62" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.15)"/>
    <text x="155" y="48" fill="#e2e8f0" font-size="14" font-weight="600" text-anchor="middle">Launch checkout</text>
    <text x="155" y="68" fill="#94a3b8" font-size="12" text-anchor="middle">old branch · no review rule</text>
    <rect x="320" y="24" width="250" height="62" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="445" y="48" fill="#5eead4" font-size="14" font-weight="600" text-anchor="middle">Task worktree</text>
    <text x="445" y="68" fill="#94a3b8" font-size="12" text-anchor="middle">integration branch · rule present</text>
    <path d="M282 55 L316 55" stroke="#64748b" stroke-width="2"/>
    <path d="M308 49 L318 55 L308 61 Z" fill="#64748b"/>
    <rect x="30" y="130" width="250" height="44" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="155" y="157" fill="#e2e8f0" font-size="13" text-anchor="middle">Codex: re-reads in phase 0</text>
    <rect x="320" y="130" width="250" height="44" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="445" y="157" fill="#e2e8f0" font-size="13" text-anchor="middle">Claude Code (2): doesn&#8217;t</text>
    <path d="M155 174 L155 204" stroke="#2dd4bf" stroke-width="2"/>
    <path d="M445 174 L445 204" stroke="#64748b" stroke-width="2" stroke-dasharray="5 4"/>
    <rect x="30" y="206" width="250" height="44" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="155" y="233" fill="#5eead4" font-size="13" text-anchor="middle">stops, asks for human review</text>
    <rect x="320" y="206" width="250" height="44" rx="8" fill="#2a2418" stroke="#f59e0b"/>
    <text x="445" y="233" fill="#fbbf24" font-size="13" text-anchor="middle">merges without the rule</text>
  </g>
</svg>
<figcaption>The rule existed and was current. Whether it applied depended on whether the agent re-read the practices of the branch it was actually working on.</figcaption>
</figure>

I want to be careful with what this shows. It is one run against two, not a comparison of models, and I would not read it as "Codex is more careful": it read the right file once, on its own initiative, and the loop gave it no reason to. That was a gap in my loop, and it is exactly the problem this article is about. The plugin rechecks its own profile at the start of every task, but it does not re-read the repository's instruction files from the branch where the work happens. The practice was written in the right place and kept current; the agents simply started from an older copy of it. So the fix went into phase 0, next to the profile recheck, not into a rule about checklists. Since version 0.7.1, when a session was launched from a checkout on a branch other than the integration or production branch, phase 0 reads the agent instruction files, and what they import, from the fresh workspace, follows those, and logs which file and branch they came from. I have not re-run a ticket since, so that behaviour is shipped, not yet proven live.

When I approved the merge, the loop recorded the approval with a distinction: permission to merge, not a line-by-line review attestation. That is exactly the difference the rule exists to protect, and now it is written down with my name and the date.

## Pushing back with evidence

After the stop, an external review raised three findings, and they went back to the same Codex session. It reproduced two of them as failing tests before changing anything. One of the handed-over instructions asked for the published enum of reasons to be literally equal to a constant in the code. Codex checked the source first and found that the service emits one more value, `content_filtered`, from a second code path. It wrote in the log that literal equality "would exclude a real value", published the full set instead, and re-ran the whole suite (6,609 tests), fixing one stale known-debt entry the run exposed.

This is the behaviour I want from the loop more than any single phase. The decision is not the agent's taste against mine; it is a recorded reason, with the evidence next to it, that I can read and overturn.

## Live, and handed over

<!-- TODO: fill in when the run finishes phases 7–9: live verification evidence, the hand-off for promotion, the close-out. -->

After the merge the loop confirmed the build published the image under the exact name it expected, merged the bump in the test environment's config repository, and waited until both pods were serving that exact commit before calling the integration done. Promotion beyond the test environment belongs to another team in my organisation, so phase 8 is built to end in an explicit hand-off, with the reason, the owner and the prepared material, instead of a skipped step.

Phase 7 also has to say what it could not measure. A criterion that only real traffic will show, or that an outage left unchecked, is marked 🔄 with its cause and a dated wait, and the ticket stays open until it is measured. It is never marked as passed with a note: a criterion left unmeasured that way reads as a pass to anyone skimming the report.

## Checking the environment before trusting it

The practices are half of what the loop has to know about a place. The other half is the environment: the accounts, tools and connections the task will use. These fail in a way a profile cannot catch, because they look fine when you ask about them.

Configured is not authenticated, authenticated is not exposed to the session, and exposed is not working. A tool listed as connected returned `invalid_grant` on its first real call. `gh auth status` reported one GitHub account while commands ran as another that could not see the repository; the account actually in use is the one `gh api user` returns. A browser tab kept showing the test environment after the VPN had dropped, because a page that is already loaded proves nothing about access. A local linter one major version behind CI passed a check that CI then failed.

So phase 0 starts with a preflight. Every capability the task will use is probed with a real call, and local check tools run at the version the repository or CI pins. Whatever fails is raised in a single round, offering the substitute accepted last time, and the answer is saved so the next run does not ask again. Without it, setup problems surface one at a time in the middle of the task.

The same rule applies at the other end. A deployment marked "SUCCESS" does not say which commit is being served; what counts is the SHA the platform reports, or content that only the change produces. That is why the run above waited for both pods to serve the exact commit.

In Codex, the environment needed two things, neither of them changes to the plugin: a sandbox with network access for merge, deploy and live checks, and an MCP server for the tracker and the code host. It found those tools on its own.

What it does not do is invent practices. It reads them, writes them at the right level, re-checks them, and stops when one says it should. If a practice only exists in someone's head, the loop will ask once. If it exists on a branch the agent has not re-read, this run is what happens, which is why re-reading is the part I care about most.

---

*[delivery-loop on GitHub](https://github.com/JaviMaligno/delivery-loop) (MIT). Install in Claude Code with `claude plugin marketplace add JaviMaligno/delivery-loop`, or in Codex with `codex plugin marketplace add JaviMaligno/delivery-loop`. More of what I package for agents in [Plugins & Skills](/en/skills).*
