---
title: "Scaling Development with Parallel AI Agents"
description: "A workflow for running multiple Claude Code agents simultaneously on different features, using git worktree to manage branches and automating PR reviews."
pubDate: 2025-12-17
tags: ["AI", "Claude Code", "Automation", "Git", "Developer Productivity"]
lang: en
translationKey: parallel-ai-agent-development
heroImage: "/blog/parallel-ai-agents.png"
---

I've been experimenting with a workflow that has multiplied my productivity as a developer: running multiple AI agents in parallel, each working on its own feature branch.

The result? Several features being developed simultaneously while I supervise.

## The Workflow

The process has three main steps:

### 1. Extract TODOs into Structured Prompts

Start by scanning your codebase for TODOs, planned features, or backlog items. Transform each into a well-structured prompt that gives the agent enough context to work autonomously:

```markdown
## Task: Implement user authentication
- Add login/logout endpoints to /api/auth
- Use JWT tokens with 24h expiration
- Follow existing patterns in /api/users
- Write tests in /tests/auth/
```

The key is providing clear scope and pointing to existing patterns. Agents work best when they can follow established conventions.

### 2. Launch Parallel Agents with Git Worktree

Here's where it gets interesting. Instead of switching branches constantly, use `git worktree` to create separate working directories for each feature:

```bash
# Create worktrees for each feature
git worktree add ../feature-auth feature/auth
git worktree add ../feature-dashboard feature/dashboard
git worktree add ../feature-export feature/export
```

Now you have three separate directories, each on its own branch. Launch a Claude Code agent in each:

```bash
# Terminal 1
cd ../feature-auth && claude

# Terminal 2
cd ../feature-dashboard && claude

# Terminal 3
cd ../feature-export && claude
```

Each agent works independently without conflicts. No branch switching, no stashing, no merge conflicts while working.

### 3. Supervise and Guide

While the agents work, I monitor their progress and provide guidance when they hit decision points. Most of the time, they work autonomously. Occasionally, they need clarification on business logic or architectural choices.

The key mindset shift: you're not writing code—you're reviewing proposals and steering direction.

## The New Bottleneck: PR Review

Here's what I didn't anticipate: when you have 5-10 PRs generated in an hour, manual review becomes the chokepoint.

Suddenly, the limiting factor isn't code generation—it's code review.

### Solutions I'm Exploring

**Automated Code Review**

Claude Code can perform reviews on its own output. I run a review pass before creating the PR:

```
"Review this branch for bugs, security issues, and adherence to project conventions. Be critical."
```

This catches obvious issues before they reach human review.

**Atlassian's Rovo Dev Agent**

For teams on Bitbucket, Rovo can automate parts of the review process. It's still early, but the direction is promising.

**MCP Integration**

For Bitbucket users, I've built an [MCP Server for Bitbucket](/en/blog/mcp-server-bitbucket/) that enables Claude to interact directly with PRs—viewing diffs, adding comments, and managing the review workflow through natural language.

## Practical Tips

**Start Small**

Don't launch 10 agents on day one. Start with 2-3 parallel features and build your supervision skills.

**Define Clear Boundaries**

Each agent should work on isolated features. Overlapping scope leads to merge conflicts and wasted effort.

**Use Consistent Prompts**

Create a template for your task prompts. Consistency helps agents produce predictable output.

**Review Before Merge, Not After**

Catch issues in the PR stage. Once it's merged, fixing problems is more expensive.

## The Future of Development

The future isn't writing more code—it's orchestrating agents that do it well.

This workflow has fundamentally changed how I think about development capacity. A single developer can now realistically manage multiple feature streams simultaneously.

The skills that matter are shifting:
- **Prompt engineering** for clear task specification
- **Architecture** for defining clean boundaries
- **Review efficiency** for maintaining quality at scale
- **Orchestration** for managing parallel workstreams

## See It in Action

I recorded a full walkthrough of this workflow:

[Watch the full walkthrough on Loom](https://www.loom.com/share/07e76de238e94aa4b101ee08a019d9df)

---

*Experimenting with similar workflows? I'd love to hear what's working for you. [Get in touch](/en/#contact).*
