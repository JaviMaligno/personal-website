---
title: "Your Agent Doesn't Know What's Internal: Context Leakage in AI Workflows"
description: "AI agents keep quoting internal feedback, spec codenames, and process notes in client-facing deliverables. Why it happens, a taxonomy of the three failure modes, and the structural fixes that actually work."
pubDate: 2026-07-19
tags: ["AI", "Agents", "Claude Code", "Workflow"]
lang: en
translationKey: internal-context-leakage
heroImage: "/blog/internal-context-leakage.png"
---

There's a failure mode I keep hitting with AI agents, and once you see it you can't stop seeing it: the agent takes context that was meant to stay *inside* the working session — client background, internal spec names, my own corrections — and writes it straight into the deliverable. The thing that was supposed to shape the output ends up *in* the output.

Two real examples, both from my day-to-day with Claude Code (though I've seen the same with Codex, and I'd bet on it being universal to agents).

**The quoted correction.** I was writing an article with AI assistance. The draft came back with a negative framing in the title — something along the lines of "the AI didn't write this." I gave feedback: don't use that, first because I don't want a negative headline, and second because it's simply false — the writing itself *was* done by the AI. The agent obediently removed it from the title. Then it took my correction, rationale and all, and wrote it into the body of the article. My editorial note to the agent — an instruction *about* the text — became content *of* the text.

**The leaked spec.** When I work for clients I keep a spec: numbered feature points, feedback items, internal shorthand for each work stream. When I ask the agent to draft a status email, it loves referencing that internal nomenclature — "as per point 3.2 of the feedback spec" — in a message to a client who has never seen the spec, doesn't know the numbering, and shouldn't need to.

Neither of these is a hallucination. The agent didn't invent anything. It did something subtler and, in a way, more dangerous: it faithfully used information it had — it just had no idea that the information wasn't *for* the reader.

## A taxonomy: three ways context leaks

Once I started collecting instances, they sorted themselves into three distinct failure modes, and they matter differently.

**Type 1 — Confidential leak.** Information that must not leave the building: client conditions, internal assessments, commercial context, candid feedback about a third party. This is the severe case. In my experience it's also the one that human review usually catches in time — precisely *because* it's severe, we read anything sensitive-adjacent with full attention before it ships. The agent has certainly tried; it just hasn't gotten past me. Which is not the same as saying it never will.

**Type 2 — Unintelligible reference.** Not confidential, just meaningless outside the session: the spec numbering in the client email, an internal codename for a workstream, a shorthand only my notes use. The reader isn't harmed — they're confused. It makes the communication look sloppy and forces a round of "sorry, what's F-12?"

**Type 3 — Process residue.** Scaffolding from the working session that ends up in the final product: my quoted correction in the article, a "per your feedback, I've restructured this section" in a document, meta-commentary about the drafting process itself. Nothing sensitive, nothing even confusing — it's just not *product*. It's the woodworking equivalent of shipping the furniture with the clamps still attached.

Here's the trap: types 2 and 3 slip through *because* they look harmless. Review effort naturally concentrates on type 1, where the stakes are obvious. The innocuous leaks are the ones that reach the reader.

## Why this happens (and why better prompting won't fully fix it)

The root cause is structural. An LLM agent operates on a single, undifferentiated context window. Your spec, your feedback, the client's last email, the draft in progress — inside the model, it's all just tokens with equal standing. There is no native notion of *provenance* ("this came from an internal doc") and no native notion of *audience* ("the reader of this email has never seen that doc").

My title correction illustrates the mechanism perfectly. The instruction had two parts: an action (remove the negative title) and a rationale (I don't want negative framing, and it's false anyway). The agent executed the action *and* treated the rationale as material. From the model's perspective that's not unreasonable — the rationale was interesting, relevant, right there in context. Models are also trained to visibly address feedback, and the path of least resistance to "addressing" something is often to *incorporate* it rather than to silently apply it and move on.

Two aggravating factors:

- **Long shared sessions.** The more work you do in one session — discuss the spec, debate the feedback, draft the email — the richer the internal context sitting right next to the deliverable, and the higher the odds of contamination.
- **Standardization helps, until it doesn't.** For productions I repeat often, I've encoded the procedure in instructions and memory ([skills](/en/blog/claude-code-skills-blog-writer), CLAUDE.md rules, templates). That genuinely reduces the rate: when the agent knows the shape of a client email, it's less likely to improvise spec references into it. But it's mitigation, not prevention — instructions live in the same undifferentiated context as everything else, and they lose to proximity often enough that you can't rely on them alone.

That's why I've come to think of this the way we think about security: you don't fix data exfiltration by asking nicely. You fix it with architecture.

## Structural fixes

These are the patterns I'm converging on. The common thread: stop trying to make one agent *remember* what's internal, and instead make it *impossible or unlikely* for internal context to reach the deliverable.

### 1. Principle of least context

The direct analogue of least privilege: each step of the pipeline gets only the context it needs. The agent drafting the client email doesn't inherit the whole working session with the spec and the feedback discussion — it receives a curated brief: what to communicate, to whom, in what tone.

In Claude Code this is almost free: subagents don't see the parent conversation. Dispatch the drafting task to a subagent with an explicit brief, and the internal context physically isn't there to leak. The failure mode changes from "leaked the spec numbering" to "asked for a detail it didn't have" — which is a far better failure mode, because it's visible.

### 2. Clean-room review pass

The two-agent (or two-session) pattern: a *writer* with full internal context produces the draft; an *editor* in a clean session — seeing only the draft plus a description of the audience — reviews it with one question: "Does anything here presuppose context this reader doesn't have?"

The editor catches leaks precisely because it shares the reader's ignorance. It doesn't know what "F-12" means either — so it flags it. An editor inside the original session can't do this reliably: it knows too much, and knowledge is exactly the problem.

### 3. Provenance tagging

Internal material lives in clearly marked locations — an `internal/` directory, a tagged section in the notes — with a standing rule in the agent's instructions: *content from these sources is never quoted or referenced verbatim in external deliverables; it informs, it doesn't appear.* This is weaker than context isolation (the rule still lives in the same context window), but it's cheap, and it gives review passes and lints something mechanical to check against.

### 4. A deterministic gate, not another LLM

For recurring leak patterns, the best reviewer isn't a model — it's a script. A pre-send lint that greps the deliverable for spec identifiers, internal codenames, client shorthand, project code words. In Claude Code this slots naturally into a hook; anywhere else it's a ten-line script in the pipeline.

It's dumb, and that's the point. It doesn't get distracted, doesn't get convinced by context, and costs nothing. It won't catch a paraphrased leak — that's what the clean-room pass is for — but it turns the *known* leak vocabulary into a hard gate instead of a hope.

### 5. Explicit handoff

The strongest version of least context, for high-stakes deliverables: the final version is produced in a fresh session from a *handoff package* — the draft, the audience description, the style constraints — and nothing else. Working session and production session never mix. It's the same discipline as separating staging from production: not because anyone plans to deploy the debug build, but because environments that can't touch can't contaminate.

## The point

The examples are small — a quoted correction, a spec number in an email. The pattern isn't. As agents take on more of our external communication, the boundary between *working context* and *deliverable* becomes a real interface, and right now that interface exists only in our heads. The model doesn't have it.

So don't put it in the prompt and hope. Put it in the architecture: scope the context, isolate the sessions, gate the output. We learned this lesson in software a long time ago — the components that must not interfere with each other are the ones you *separate*, not the ones you ask to behave.

---

*I build AI agent pipelines with exactly these kinds of guardrails. If your team is putting agents in front of clients, [let's talk](/en/#contact).*
