---
title: "Building a Production DevOps Agent: From Slack to Kubernetes"
description: "How I built an AI agent that investigates infrastructure issues autonomously — with read-only guardrails, output compaction, and infrastructure knowledge baked into the system prompt."
pubDate: 2026-04-29
tags: ["AI Agents", "DevOps", "Slack", "Kubernetes", "Azure"]
lang: en
translationKey: building-a-production-devops-agent
heroImage: "/blog/building-a-production-devops-agent.png"
---

At [SimpleKYC](https://simplekyc.com), the `#devops_requests` Slack channel is where every team goes when something breaks — or when they think something might be about to break. Pod stuck in CrashLoopBackOff? Pipeline failed? 502 from a service that was fine yesterday? It all lands there.

A colleague analyzed the channel and found that **70% of requests could be self-resolved** by querying the same tools the DevOps team uses: kubectl, Azure CLI, Bitbucket pipelines, health checks. The knowledge wasn't secret — it was just scattered across terminals, runbooks, and people's heads.

We were already using Claude Code to investigate issues ourselves. The next step was obvious: put an agent in the channel that could do the same thing, for everyone, automatically.

## The Agent Architecture

The bot is a generic LLM agent — not a collection of pre-built workflows. When someone mentions `@DevOpsBot` in a thread, [GPT-5.4](https://platform.openai.com/docs/models) (via Azure OpenAI) decides which tools to call, in what order, with what arguments. It can chain up to 20 tool calls per request, building up context as it goes.

This matters. A pod crash investigation might require:

1. `kubectl get pods` to find the failing pod
2. `kubectl describe pod` to check events
3. `kubectl logs` to read the error
4. A Bitbucket API call to check the last deployment pipeline
5. A health check on the service endpoint

No pre-built workflow can anticipate every combination. The LLM constructs the investigation path dynamically, adapting based on what each tool returns.

### Six Tools, All Read-Only

The bot has access to six tools:

| Tool | What it does | Examples |
|------|-------------|----------|
| **kubectl** | Kubernetes diagnostics across 9 AKS clusters | `get pods`, `describe`, `logs`, `top` |
| **az cli** | Azure resource queries across 5 subscriptions | VM status, Postgres info, storage, APIM |
| **Bitbucket** | CI/CD pipeline status, repo content, config files | Pipeline logs, `values.yaml`, branch diffs |
| **Health check** | HTTP endpoint testing | Status codes, response times, body preview |
| **Jira** | Issue search and context | JQL queries, ticket details, comments |
| **Confluence** | Documentation search | Runbooks, architecture docs, onboarding guides |

Every tool is **strictly read-only**. kubectl blocks `delete`, `apply`, `patch`, `scale`, `exec`, and `edit`. Azure CLI only allows `show` and `list`. There's no way for the agent to modify infrastructure — by design.

## Read-Only First: A Deliberate Choice

This wasn't a technical limitation — it was a trust-building strategy. The agent's first job is to prove it can *understand* the infrastructure correctly before anyone considers letting it *change* anything.

The roadmap is progressive:
- **Phase 1** (current): Read-only diagnostics — investigate and report
- **Phase 2**: Safe actions in dev/test — restart pods, rerun pipelines
- **Phase 3**: Approval workflows for staging/production — the agent proposes, a human approves via Slack reaction
- **Phase 4**: Full traced autonomy — the agent acts independently with complete audit trails

Escalation to humans isn't a phase — it's always present. The agent knows when it's out of its depth and routes to the right person. That's not a feature you add later; it's part of the human-in-the-loop design from day one.

This mirrors how you'd onboard a new team member. You don't give someone production access on day one. You let them observe, ask questions, and demonstrate understanding first.

## Infrastructure as Knowledge

The agent's system prompt encodes the team's accumulated infrastructure knowledge: cluster naming conventions, namespace patterns, GitOps workflows, config repo structures, and common troubleshooting paths.

For example, the agent knows that:
- Deployments follow a GitOps pattern — editing config files in environment branches triggers ArgoCD reconciliation
- Kubernetes labels follow consistent naming patterns that map services to environments
- The promotion chain goes through multiple stages from development to production
- Some services run on VMs with different config structures than the K8s-based ones

This knowledge didn't come from a single source. I had context from working with the infrastructure, the LLM explored the actual clusters and repos to fill gaps, and then a DevOps engineer shared the documentation he personally uses with Claude — that was the biggest single jump in accuracy. After that, I refined edge cases through testing.

The result is that when someone asks "why is service X failing in UAT?", the agent already knows which cluster to check, which namespace, what label selector to use, and where the config repo lives. It doesn't need to be told.

## Output Compaction: Saving 79% on Tokens

kubectl and Azure CLI return verbose JSON. A `kubectl get pods` across a namespace can easily be 8,000+ characters. Feed that raw into the LLM context and you burn tokens fast.

The bot compacts tool outputs on the fly — parsing JSON, extracting relevant fields, and discarding noise. A raw kubectl response of 8,000 characters becomes ~1,600 characters after compaction, with no loss of diagnostic value. That's a **79% token reduction** that directly translates to lower costs and faster responses.

The compaction is tool-aware: it knows which fields matter for kubectl (status, restart count, images, events) vs. Azure CLI (provisioning state, FQDN, SKU) vs. Bitbucket (pipeline state, step results, error messages). If JSON parsing fails, it falls back gracefully to truncation.

## Security Guardrails

Building an agent that runs shell commands against production infrastructure requires paranoia-level security:

**Command validation**: Every tool call goes through `shlex.split` with an array-based subprocess call — never `shell=True`. This prevents injection by construction.

**Blocklists**: Shell metacharacters (`;`, `|`, `&`, backticks, `$()`) are blocked at the input level, before any command reaches the shell.

**Allowlists**: Each tool defines exactly which subcommands are permitted. For kubectl, that's `get`, `describe`, `logs`, `top`, `config`, `version`. Everything else is rejected.

**Output limits**: Tool results are capped at 8,000 characters (before compaction) to prevent context window flooding.

**Private IP blocking**: The health check tool blocks requests to localhost, 10.x, 192.168.x, and 172.16-31.x to prevent [SSRF](https://en.wikipedia.org/wiki/Server-side_request_forgery).

## The Moment It Clicked

Before any DevOps engineer had responded to a request, the bot investigated a service that appeared healthy on the surface — pods running, endpoints responding. But it dug deeper, found a new pod that was failing to start, pulled the container logs, and identified the exact error: a misconfigured environment variable in the latest deployment.

That's the kind of investigation that takes a human 10-15 minutes of context-switching between terminals. The bot did it in seconds, in the Slack thread where the question was asked, visible to everyone.

## The First Test Went Wrong

The first live demo with the DevOps team exposed two UX problems I hadn't anticipated.

The first: someone tagged `@DevOpsBot` in an existing thread — just the mention, no additional text. They expected the bot to read the thread context and help. Instead, it silently dropped the message. I'd built a guard against empty inputs as a safety measure, but "empty mention" and "useless input" aren't the same thing. In a thread with 15 messages of context, a bare `@DevOpsBot` is a perfectly valid request for help. This guard made the bot useless in one of the most common Slack patterns: jumping into an ongoing conversation.

The second: requiring an `@mention` at all is friction. In a fast-moving incident, typing `@DevOpsBot` before every question feels like ceremony. But it's an acceptable tradeoff as part of the trust-building process — no accidental triggers, no noise, clear audit trail of who asked what. The alternative, auto-responding to everything in the channel, risks unintended tool calls and noise that erodes trust faster than the friction does.

Both were quick fixes in code, but they taught me something about building agents for real teams: defensive defaults that make sense in isolation can break the most natural interaction patterns. Test with the actual users early — your assumptions about how people will talk to the bot are probably wrong.

## What I Learned

**Tools first was the right call.** Getting kubectl and Azure CLI working reliably was the quick win that let me start experimenting immediately. The system prompt refinements came naturally from watching the agent struggle with real questions — you need the tools running to know what knowledge is missing.

**Compaction should be built in from day one.** I added it after noticing token costs climbing. In hindsight, every agent that calls tools returning structured data should compact by default.

**Design for thread context early, even if you implement it later.** The bot reads up to 20 previous messages in a thread to maintain conversation continuity. Without this, every follow-up question ("what about the UAT environment?") would lack context. You don't need it for initial testing, but keep it in mind from the start — retrofitting conversational state is harder than designing for it.

## The Stack

- **LLM**: GPT-5.4 via Azure OpenAI (function calling)
- **Slack**: Slack Bolt + Socket Mode (async Python)
- **Runtime**: Python 3.11, asyncio throughout
- **Deployment**: Docker → AKS via ArgoCD (GitOps)
- **Observability**: Prometheus metrics, Application Insights, structured logging
- **Testing**: pytest (unit + integration + e2e against real Slack)

## Is It Worth Building?

If your DevOps team spends significant time on questions that amount to "look at this thing and tell me what's wrong" — yes. The investment is primarily in encoding your team's infrastructure knowledge, not in the LLM plumbing.

The read-only constraint makes the risk profile low. The agent can't break anything. The worst case is a wrong answer, which is the same worst case as a human answering from memory without checking.

The best case is that 70% of your `#devops_requests` channel gets answered in seconds, and your DevOps engineers focus on the 30% that actually needs human judgment.

---

*Built with Python, Azure OpenAI, Slack Bolt, and a lot of infrastructure knowledge. Deployed on AKS via ArgoCD.*
