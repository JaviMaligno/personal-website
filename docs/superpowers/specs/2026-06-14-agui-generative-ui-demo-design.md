# AG-UI Generative UI Demo — Design

**Date:** 2026-06-14
**Purpose:** A small, public, reproducible demo that shows the AG-UI protocol rendering interactive widgets inside a chat (generative UI). It accompanies the blog article *"When the Chat Builds Its Own Interface"* — providing a real, running example (GIF + linkable repo) instead of only retelling Sofía Sánchez-Zárate's calculator demo.

## Narrative fit

The article's thesis: the generative-UI pattern is already built **by hand** in the conversational-KYC project (typed `interrupt` + React widget registry on LangGraph). This demo shows the **standardised** version of the same idea using the official AG-UI SDK in ~100 lines — closing the loop "hand-built pattern → emerging standard".

## Scope

- **In:** a chat where the agent, asked a parametric question, renders an interactive widget instead of static text.
  - Widget 1 — **Loan calculator**: ask "help me work out a loan repayment" → agent renders an editable calculator (amount / rate / term → monthly payment, live).
  - Widget 2 — **Loan application form**: a short structured form (applicant name, monthly income, desired amount, term) the agent renders when the user wants to "apply"; on submit it feeds the calculator. Shows variety and nods to the forms/KYC use case.
- **Out:** auth, persistence, deployment, multi-turn memory, anything beyond demonstrating generative UI. YAGNI.

## Stack

- **Backend:** Python 3.12 + FastAPI + AG-UI Python SDK. One endpoint emitting AG-UI protocol events. Adapted to **Azure OpenAI** (not vanilla OpenAI as in the official quickstart) — reusing existing Azure credentials (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, a deployment name).
- **Frontend:** CopilotKit React (understands AG-UI natively). Two components registered as generative UI (`LoanCalculator`, `<Form>`), triggered by agent actions/tool calls.
- **LLM:** Azure OpenAI GPT-4o-class deployment.

## Data flow

1. User types a message in the CopilotKit chat.
2. Frontend → AG-UI events → FastAPI backend.
3. Agent (Azure OpenAI) decides to call an action (`show_loan_calculator` / `show_form`).
4. Backend streams AG-UI tool-call events back.
5. CopilotKit renders the mapped React component inline; user interacts; result flows back into the conversation.

## Repo & secrets

- New **public** GitHub repo: `JaviMaligno/agui-generative-ui-demo`.
- Secrets via `.env` (gitignored) + a committed `.env.example`. Azure creds used **only locally** for capturing the GIF; never committed.
- README: what it is, how to run, link back to the article; a short "this is the SDK version of the hand-built pattern" note.

## Deliverables

1. Working repo (backend + frontend + README), public.
2. A GIF (or screenshots) of the calculator + form rendering live in the chat, saved to `personal-website/public/blog/` and embedded in the article.
3. A new closing section in the article — *"Trying it: from hand-built pattern to SDK"* — with the GIF and the repo link.

## Risks / open points

- AG-UI quickstart uses vanilla OpenAI; adapting to Azure OpenAI may need a custom client config. Low risk, well-trodden.
- Capturing the GIF needs the browser automation reconnected (currently disconnected) or the user records it.
- Keep it tiny: if Azure adaptation or CopilotKit setup balloons, fall back to a single widget (calculator) first, add the form second.

## Verification

- Backend runs and streams AG-UI events locally.
- Frontend renders both widgets from agent actions.
- End-to-end: a real prompt produces a rendered, interactive widget — captured as the GIF.
