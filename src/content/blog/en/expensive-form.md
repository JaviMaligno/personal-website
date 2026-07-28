---
title: "I Built an Expensive Form"
description: "I argued that a conversational journey added little over a well-designed form. The call went the other way, so I built it — and the client's feedback settled the argument better than I could have."
pubDate: 2026-07-28
tags: ["AI Agents", "Product", "LangGraph", "UX"]
lang: en
translationKey: expensive-form
heroImage: "/blog/expensive-form.png"
---

I lost this argument before I built anything.

We were replacing a legacy ticketing journey for filing regulatory reports — the kind of internal form that front-line staff dread and fill in badly. My position, stated more than once, was that turning the whole journey into a conversation added little over a well-designed form. What I'd have built instead was a form with genuinely good UX, plus an assistant beside it for the questions people actually have — *does this count as reportable?*, *which category is this?* — able to interact with the form rather than replace it.

The call went the other way, and it was a defensible call: a conversational journey is differentiating, it demos well, and clients ask for it by name. So I said *fine, I'll build it and we'll see what happens.*

We saw what happened. I had built an expensive form.

## Building well what you don't advocate for

I want to be precise about this, because "I disagreed and did it anyway" can read as either cynicism or spinelessness, and I don't think it was either.

An internal argument about whether users will like something is unresolvable by internal argument. Two people with plausible models of the user restate their priors at increasing volume, and the person with more authority wins. That isn't a bad process because the wrong person won — it's a bad process because *nobody learns anything*. The way out is to put the thing in front of a real user quickly, built well enough that their reaction is about the idea and not about your half-hearted execution.

So it had to be good. If I'd shipped a deliberately mediocre version, any bad feedback would have been about the mediocrity, and I'd have proven nothing.

I also didn't start from scratch: a colleague had built the initial LangGraph prototype, and I took it from there. Worth saying plainly, because the improvements I'm about to describe were made on top of someone else's foundation.

## What we shipped

The architecture wasn't sloppy. It was a pipeline engine configured in YAML: a DAG of phases, a handful of node types, conditional routers, global triggers that could redirect the flow, compliance scoring recalculated after each phase.

Each phase owned a slice of the form. It asked its question, validated the answer, confirmed it, advanced. For one report type that came out to roughly **seven interactive steps**: seven turns where the user waited for a model, read a question, answered one thing, confirmed.

And let me steelman that design, because its properties are real.

Phase-per-slice gives you **validation at the point of entry** — you catch a malformed date while the user is still thinking about dates. It gives you a **progress model**: because phases are explicit, you get a progress bar, per-phase analytics, and an admin panel showing exactly where a submission stalled. It makes the flow **legible** — a new engineer reads the YAML and knows what happens. And it makes the agent **safe by construction**: it cannot skip a required field, because the graph won't let it.

I didn't give those up. That matters for what comes later.

## The feedback that settled it

The client's compliance lead tried it and said it *felt too similar to the system it was replacing: time consuming and complex.*

That sentence did in one meeting what I hadn't managed in several. Nobody won the internal argument — the user ended it. And the useful part isn't that my prior was vindicated; it's that we now had a *specific* complaint instead of two competing opinions. "Time consuming and complex" is diagnosable. "I think users won't like it" isn't.

That feedback got me a blank cheque to rebuild it properly. Which is the actual reason I'm glad we shipped the version I argued against: my alternative would have been a guess too. What we got instead was evidence, and evidence buys you permission.

## Why a form wins that race

Here's the mechanism. If the interaction is a fixed sequence of questions, the form is simply the better interface:

- You see **all the fields at once**, so you know how long this will take. A chat hides the length of the queue, which is why "how many more questions?" is the most common thought in a scripted bot.
- You fill them in **any order**, skip around, come back. A sequential agent imposes an order that exists for the engine's convenience, not yours.
- You **tab between fields** in milliseconds. Every conversational turn costs a round trip to a model — sometimes one second, sometimes ten. Multiply by seven.
- It costs **nothing per submission**. Our version billed tokens for the privilege of being slower.

So the scripted chat loses on speed, on predictability, and on cost, and its only compensation is that it feels modern. A conversational wrapper around a fixed sequence is a form with worse ergonomics and a variable bill.

## The diagnosis: sequentiality, not widgets

My first instinct was presentation — the inputs looked clunky, the confirmations were verbose, maybe better in-chat widgets would fix it. That instinct was wrong, and it's the interesting part.

The cost wasn't in any single step. It was in **there being steps at all**. Seven turns is seven turns whether each one is beautiful or ugly.

Then the genuinely humbling detail. The machinery for *"only ask for what's missing"* already existed. Each phase could compute its own missing fields and ask only about those. It just operated **within phase scope** — so when a user opened by typing a rich paragraph describing everything that happened, phase one extracted its two fields and the rest of that paragraph was discarded. The user had already given us most of the answers. We threw them away and then asked for them one at a time.

The system wasn't failing to understand the user. It was understanding and then forgetting, because the unit of extraction was the phase rather than the conversation.

## First pass: fix it inside the graph

Diagnosing it didn't earn me a rewrite, and it shouldn't have.

This is the part people skip when they tell these stories, so let me be explicit about it. There was a *product*. It was built, deployed, in front of clients, and it worked — badly, but it worked. Nobody throws that away on the strength of one piece of feedback and an engineer's conviction. The reasonable next step, and the one the business wanted, was to see how good the existing thing could get.

That instinct is correct more often than engineers like to admit. Incremental fixes are cheap, they ship this week instead of next quarter, and if they'd been enough we'd have saved an entire rewrite. The only way to know whether a rewrite is necessary is to first exhaust what isn't one.

So: two additions to the existing graph, both behind an opt-in flag so other flows kept their old behaviour and I had zero regression risk on clients who weren't asking for this.

**A global intake node.** Before the first phase, the agent asks for the story in the user's own words. Then it makes a *single* structured-extraction call against the union of every field the whole flow could extract, and writes everything it confidently found.

```python
# Sequential: the graph decides the order, one question at a time
START → phase_1 → phase_2 → ... → phase_7 → END

# Conversational: extract everything from the narrative, then
# only visit phases that still have gaps
START → intake → first_unsatisfied_phase → ... → END
```

Three details mattered more than the idea:

- **The extractable set is computed, not hand-written.** It's the union of fields written by phases that can be satisfied from prose. Document extraction, file uploads and signatures are *explicitly excluded* — no narrative produces a scanned ID.
- **It reuses the real field definitions**, so the same validators run in intake as in the phases. Passing an empty schema and "just extracting text" hands you unvalidated data with extra steps.
- **It never guesses.** If the narrative doesn't clearly give a field, intake leaves it empty. For an option list, a wrong selection in a regulatory form is worse than one more question — a blank gets asked about, a wrong value gets submitted.

**Skipping satisfied phases.** Phases needing genuine interaction (upload, signature) always run. Data phases branch: all fields present and nothing critical → advance silently; all present but something critical → one minimal confirmation; gaps → ask only about the gaps.

Result: **roughly seven interactions down to three or four.** Narrate, confirm the high-risk items, upload, sign.

Notice what survived. The phases still exist, so the progress bar, the analytics, the admin panel and the validators all still work. I didn't tear down the DAG to get conversational — I put a node in front of it and let phases opt out of asking. The alternative I rejected in writing was collapsing everything into one adaptive node, which buys elegance and costs every structural property listed earlier.

## Second pass: what the rewrite actually required

The first pass bought real improvement, and it wasn't enough. Three or four turns is better than seven, but the shape of the thing was still a graph marching through phases with a smarter front door bolted on.

Going properly agentic meant **a completely new backend**. Not a refactor: a different shape of system, where instead of a graph deciding the order of questions, an agent holds tools over a server-authoritative state and decides what to do next.

A rewrite of that size is never won on technical argument alone. It took two things: the client feedback, which made the problem concrete, and then a change of direction at the company that made a new bet acceptable in the first place. Evidence made the case; an appetite for risk gave it somewhere to land. Both had to be true at once.

That's the part I'd generalise. The window where an organisation will accept a rewrite opens and closes for reasons that have nothing to do with your architecture diagram, and it is usually short. What you control is being ready when it opens — which, in my case, meant that the design I'd been arguing for was already specified, because I'd spent the incremental pass learning exactly which constraints mattered.

Two things came out of that rebuild that I'd defend anywhere.

**Generative UI in the chat, which was my idea and the part I'm most attached to.** If the agent has to render options as text, you've reinvented the dropdown with extra latency. Instead the chat renders actual interactive widgets — chips, pickers, panels — so the agent can propose a structured value and the user adjusts it directly. I've written separately about [why that pattern matters and the protocol standardising it](/en/blog/ag-ui-third-protocol).

This produced my favourite rule in the whole system. When the agent asks about remaining gaps, it splits them in two: free-text and date fields get asked directly, consolidated into one natural question, but fields with a fixed option list get a different instruction — **infer your best option from what the user already told you and let them adjust it in the panel; do not read the options out.** The interception lives in the tool that computes missing fields, not in the prompt, because that's the exact point where the model decides what to ask.

If you're building on a messaging channel, this is load-bearing. Nobody wants to read eight numbered choices in WhatsApp.

**Freedom to understand, ceremony to act.** Intake can be as open as you like; the write cannot. When the agent is about to submit something with real-world consequences, I want a narrow, explicit, boring step. In the new backend that gate is checked in code: a submission is refused unless it was offered in an *earlier* turn, and any later correction voids the pending approval — because if the content changed, what the person approved is no longer what would be sent. Same principle as the [guardrails I keep writing about](/en/blog/typescript-ai-agent-guardrails): the constraint has to live somewhere the model can't reach.

## The abstraction I waited to build

Here's where it went beyond one client. A new backend per use case doesn't scale, and the obvious move was a **generator**: a backend that takes configuration for a use case — prompts, the form models, the knowledge base — and produces the agentic flow from it.

The discipline was in the timing. I deliberately waited until I had **two genuinely different flows** working before generalising: business-banking onboarding and regulatory incident reporting. Different domains, different form shapes, different failure modes.

Two reasons, and both are the same reason:

- **Two dissimilar examples tell you which parts are actually variable.** Abstract from one and you build a configuration layer shaped exactly like your first client, then bend it painfully for the second. Every knob I exposed had to be a knob both flows genuinely turned differently.
- **Two examples also prove the abstraction is worth it at all.** With one flow, "just deploy another backend" is the cheaper answer and the honest one. The generator only earns its complexity once you can show the alternative is N backends.

That's the current work, and it exists because the rewrite happened twice in different shapes — not because someone drew a platform diagram at the start.

## Not chat everything

I'd rather not overcorrect this into conversational-everything, because my original position still stands and the boundary is the useful part.

Keep the form when the fields are **few and known**, when the user has the data **in front of them**, when input is inherently **non-narrative** (upload a file, sign, pick from a calendar), or when the flow is **used daily by trained staff** who memorised the tab order long ago. Power users beat conversational interfaces at speed, every time.

Reach for the agent when input arrives as **a story rather than a record** — an incident, a complaint, a symptom, a request — when the field set is **large but sparsely relevant** to any one case, or when the person filing is **occasional and untrained** and the form's vocabulary isn't theirs.

And note the middle option I originally argued for hasn't gone anywhere: a good form plus an assistant that can see it and act on it. That's often the right answer, and it's the one nobody demos.

## The question I ask first now

Before building a conversational anything: *what does this let the user do that the form doesn't?*

If the answer is "it's friendlier", build the form. If the answer is "the user can describe their situation however it comes out, and the system works out which fields that maps to", there's something real — and the design job is extracting once, asking only for what's genuinely missing, and never reading the options out loud.

The rest of the time you're building an expensive form. Sometimes you have to build it anyway to prove it, and if you do, build it well enough that the feedback is about the idea.
