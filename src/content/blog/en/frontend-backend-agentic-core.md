---
title: "Frontend, Backend, and the Agentic Engine"
description: "When AI logic deserves its own architectural block alongside the frontend and application backend. Real projects, earlier patterns, and a simpler alternative."
pubDate: 2026-09-18
tags: ["AI Agents", "Architecture", "Development"]
lang: en
translationKey: frontend-backend-agentic-core
heroImage: "/blog/frontend-backend-agentic-core.png"
---

A separation keeps appearing in projects I work on. There is the frontend. There is the backend that keeps the application running. And there is the agentic engine: workflows, prompts, tools, context management, models, and the evaluations that tell us whether all of that does its job well.

I could call the last two pieces the backend and remain technically correct. But the distinction is increasingly useful when working on them. Changing how an agent investigates a data source is different work from changing how a user reviews and accepts its results. Both need server code; their responsibilities and reasons to change are different.

These are three blocks of responsibility. They can live in a monorepo, span repositories, or share a process. Giving the engine an identity of its own does not require making it a microservice.

## The application around the agent

One example is a [data source automation pipeline](/en/projects/data-source-automator). Its work includes investigating sources, proposing extraction methods, generating specifications, and producing services. There are several stages, tools, decisions, and review points. There is also an evaluation set that compares stage outputs against corrected references.

The application from which that work is managed has its own frontend and backend. The backend submits jobs to the engine, checks their status, and retrieves results. The logic that makes those results part of an application has enough substance to remain separate from the logic that produces them.

This is the distribution of responsibilities I am interested in:

<style>
.fab-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1rem;margin:2rem 0}
.fab-fig svg{display:block;width:100%;height:auto;font-family:Inter,-apple-system,system-ui,sans-serif}
.fab-fig figcaption{color:#94a3b8;font-size:.85rem;line-height:1.55;margin:1rem .25rem .25rem;text-align:center}
</style>

<figure class="fab-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 620" role="img" aria-label="An application can separate frontend, application backend, and agentic engine. A direct-access interface can connect to the engine without a separate application backend.">
  <defs><marker id="fab-arrow-en" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#94a3b8"/></marker></defs>
  <text x="300" y="28" text-anchor="middle" fill="#94a3b8" font-size="17">WHEN THE APPLICATION HAS LOGIC OF ITS OWN</text>
  <rect x="35" y="49" width="530" height="76" rx="10" fill="#203237" stroke="#2dd4bf"/>
  <text x="300" y="80" text-anchor="middle" fill="#5eead4" font-size="23" font-weight="600">Frontend</text>
  <text x="300" y="107" text-anchor="middle" fill="#e2e8f0" font-size="17">Interaction · supervision · results</text>
  <path d="M300 135V181" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-arrow-en)" marker-end="url(#fab-arrow-en)"/>
  <text x="320" y="164" fill="#94a3b8" font-size="16">Product actions and state</text>
  <rect x="35" y="191" width="530" height="76" rx="10" fill="#283240" stroke="#94a3b8"/>
  <text x="300" y="222" text-anchor="middle" fill="#f8fafc" font-size="23" font-weight="600">Application backend</text>
  <text x="300" y="249" text-anchor="middle" fill="#e2e8f0" font-size="17">Permissions · rules · work lifecycle</text>
  <path d="M300 277V323" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-arrow-en)" marker-end="url(#fab-arrow-en)"/>
  <text x="320" y="306" fill="#94a3b8" font-size="16">Jobs, events, and results</text>
  <rect x="35" y="333" width="530" height="76" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="300" y="364" text-anchor="middle" fill="#fbbf24" font-size="23" font-weight="600">Agentic engine</text>
  <text x="300" y="391" text-anchor="middle" fill="#e2e8f0" font-size="17">Workflows · context · tools · evals</text>
  <path d="M35 442H565" stroke="#475569" stroke-dasharray="5 5"/>
  <text x="300" y="478" text-anchor="middle" fill="#94a3b8" font-size="17">WHEN THE INTERFACE IS A WAY INTO THE AGENT</text>
  <rect x="35" y="503" width="210" height="76" rx="10" fill="#203237" stroke="#2dd4bf"/>
  <text x="140" y="549" text-anchor="middle" fill="#5eead4" font-size="23">Frontend</text>
  <path d="M255 541H345" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-arrow-en)" marker-end="url(#fab-arrow-en)"/>
  <rect x="355" y="503" width="210" height="76" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="460" y="549" text-anchor="middle" fill="#fbbf24" font-size="23">Agentic engine</text>
  <text x="300" y="610" text-anchor="middle" fill="#94a3b8" font-size="16">Authentication is still needed in both cases.</text>
</svg>
<figcaption>Two possible arrangements. Boxes express responsibilities; arrows express exchanges. They specify neither the number of repositories or processes nor every communication path.</figcaption>
</figure>

The application backend can have plenty to do. In a document application, for example, it determines who can open a case, which review it needs, and when a result becomes accepted. The engine extracts information and supplies evidence. A completed run does not necessarily mean a resolved case.

In another document processing project I work on, extraction runs in a worker, and the application backend manages cases and their artefacts. For questions about previously processed documents, that same backend imports the AI service as a library. The separation of responsibilities accommodates both integration styles within one product.

## A chat can hide an entire system

In the [conversational AI projects I wrote about when discussing interfaces built inside a chat](/en/blog/ag-ui-third-protocol), the visible surface is a conversation. Behind it are document capture, tools, verification, persistent state, and processes that need human participation.

Some of those engines share a library with common capabilities: persistence during execution, activity events, context management, model connections, and protection against loops or repeated failures. Each engine keeps the tools, instructions, and structures specific to its domain.

That introduces another reason to give the agentic block an identity: several experiences can reuse the same execution capabilities. The shared core is a library; each consumer incorporates it into its service. A recognisable boundary in the code already provides value.

This also calls for more precision about what we mean by “a simple chatbot.” Chat describes how the user interacts. It says little about the system they are using. In [I Had Built an Expensive Form](/en/blog/expensive-form), I described how a conversation could rest on a graph of phases, validations, and decisions, yet still offer a worse experience than a form. Engine complexity and interface usefulness are separate questions.

## The agent can also operate on the application

An [assistant embedded in a case review platform](/en/projects/compliance-assistant) introduces another relationship. The analyst is already working on a case and opens the assistant within the application. They can ask it to look up information, update details, or propose a status change. The agent uses backend capabilities to work on that same case.

In the integrated implementation, tools are adapters over product operations. For example, the tool that updates a case validates the data and calls the existing update service. The tool that changes status checks that the transition is allowed from the current state. Writes go through a confirmation card and leave an audit record.

<figure class="fab-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 380" role="img" aria-label="The application's screens and the assistant's tools use capabilities of the same backend. The assistant proposes operations; writes require human confirmation.">
  <defs><marker id="fab-assistant-en" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#94a3b8"/></marker></defs>
  <rect x="25" y="35" width="235" height="100" rx="10" fill="#203237" stroke="#2dd4bf"/>
  <text x="142" y="74" text-anchor="middle" fill="#5eead4" font-size="23" font-weight="600">Frontend</text>
  <text x="142" y="105" text-anchor="middle" fill="#e2e8f0" font-size="17">Screens and chat panel</text>
  <rect x="340" y="35" width="235" height="100" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="458" y="74" text-anchor="middle" fill="#fbbf24" font-size="23" font-weight="600">AI assistant</text>
  <text x="458" y="105" text-anchor="middle" fill="#e2e8f0" font-size="17">Context and proposals</text>
  <path d="M270 85H330" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-assistant-en)" marker-end="url(#fab-assistant-en)"/>
  <text x="300" y="67" text-anchor="middle" fill="#94a3b8" font-size="16">chat</text>
  <path d="M142 145V245" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-assistant-en)" marker-end="url(#fab-assistant-en)"/>
  <path d="M458 145V245" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-assistant-en)" marker-end="url(#fab-assistant-en)"/>
  <text x="162" y="190" fill="#94a3b8" font-size="16">standard</text>
  <text x="162" y="212" fill="#94a3b8" font-size="16">actions</text>
  <text x="438" y="190" text-anchor="end" fill="#94a3b8" font-size="16">assistant</text>
  <text x="438" y="212" text-anchor="end" fill="#94a3b8" font-size="16">tools</text>
  <rect x="25" y="255" width="550" height="100" rx="10" fill="#283240" stroke="#94a3b8"/>
  <text x="300" y="295" text-anchor="middle" fill="#f8fafc" font-size="23" font-weight="600">Application backend capabilities</text>
  <text x="300" y="328" text-anchor="middle" fill="#e2e8f0" font-size="17">Cases · validation · transitions · audit trail</text>
</svg>
<figcaption>The assistant provides another way to operate on the product. This is a map of responsibilities: conversation and tools pass through server code, and writes require confirmation in the interface.</figcaption>
</figure>

Here the backend provides capabilities consumed by both the screens and the assistant's tools. The useful boundary separates interpreting the request from executing the business operation. In this case, the assistant module lives within the application's own backend: that distinction exists without a separate agent service.

This broadens the initial picture. An application can delegate work to the engine, and an agent can use application operations as tools. Both relationships can coexist. The three blocks help assign responsibilities, but they do not impose a single chain of calls.

## The case where two blocks were enough

The old frontend for a [business activity classifier](/en/projects/compliance-classifier) was a way into the agent: submit a query and see the classification. There was little intermediate logic beyond authenticating access.

That case worked well as frontend plus agent service. A separate application backend would have needed a concrete responsibility to justify maintaining it.

“Direct access” here means the frontend communicates with the service running the agent. Provider credentials and tool execution remain on the server. The interface client presents results and events; the engine prepares context and executes the work.

I find this example as useful as the others because it prevents a practical observation from becoming a universal recipe. Even a complex engine can have a very thin access interface.

## What is new about this

The separation between an application and a processing engine has clear precedents. The [Web–Queue–Worker pattern](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/web-queue-worker) already separates request handling from long or intensive work. Applications with inference services also know that boundary.

There are explicit references in the agent ecosystem. [LangGraph Cloud launched in June 2024](https://www.langchain.com/blog/langgraph-cloud) with persistence, background jobs, streaming, and human collaboration. [CopilotKit's architecture](https://docs.copilotkit.ai/concepts/architecture) describes a frontend, a runtime inside the application server, and an agent backend. That runtime covers integration with the interface; the business backend can have broader responsibilities.

What I see in my projects is AI logic acquiring enough substance to need an engineering cycle of its own. Changing a model or prompt calls for evaluating the quality of results as well as checking that requests work. A flow can finish without errors while choosing the wrong tool, omitting a fact, or consuming too much budget.

That cycle combines software tests, evaluations on representative cases, and inspection of runs. It is a reason to recognise the engine as a block, even when it shares infrastructure with the application. The separation still needs tracing across the whole system: a run must be traceable to the user's work that initiated it.

I have not found one established name for this exact arrangement. “Frontend, application backend, and agentic engine” describes what I want to point to. Also, part of that engine may be a workflow whose path is fixed by code. [Anthropic's distinction between workflows and agents](https://www.anthropic.com/engineering/building-effective-agents) is useful here: this boundary can make sense for both.

## Which boundary is worth drawing

How central AI is to the product and how complex it is both help with the decision, but neither is sufficient alone. An application can depend on a single, simple AI operation. Another can offer automated research as a secondary feature and need several complex workflows to deliver it.

I would look for concrete signals:

- The AI logic has tools, context, and evaluations that change independently of the rest of the product.
- Runs need to last, resume, or wait for human input beyond a web request.
- Several processes or experiences reuse the same engine or its common capabilities.
- The application has permissions, reviews, and business states that retain their meaning when the agent's approach changes.

The first three give the engine substance. The last gives the application backend substance. The classifier example illustrates why both questions matter.

Technology does not define the boundary either. The engine can have APIs, queues, and plenty of deterministic code. The backend can administer configurations and documents consumed by agents. A tool can invoke a business operation whose permissions and rules are enforced by the service responsible for that operation.

What needs to be clear is who decides what, which state each part maintains, and which contract lets them work together. That contract covers inputs and results, but also progress, errors, cancellation, and review when the product needs them.

Separating processes adds costs: communication failures, compatible versions, and synchronisation. If a retry creates two jobs, three well-drawn boxes will not solve the problem. I would therefore start with a boundary between modules and separate deployments when there is an operational reason.

For a small feature, an AI module inside the backend may be enough. For an interface whose only job is to provide access to the agent, its service may be enough. When both the product and the engine accumulate responsibilities of their own, recognising the three blocks helps us work on each without unnecessarily pulling the others along.

The question I find useful when reviewing these projects is: **if we change how the agent works tomorrow, what would need to change in the application, and why?** The answer says much more about the architecture than counting repositories.
