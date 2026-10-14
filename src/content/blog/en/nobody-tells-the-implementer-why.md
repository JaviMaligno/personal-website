---
title: "Nobody tells the implementer why"
description: "I measured how a client's request degrades as it passes through a team of agents, from lead to implementer. Names, numbers and prohibitions survive. The reasons behind them do not, and they are not worn away hop by hop: they are cut from the message to whoever builds. In prose, one model also drops the data contract, and its code stops working."
pubDate: 2026-11-05
tags: ["Agents", "Multi-Agent", "Claude", "Communication"]
lang: en
translationKey: nobody-tells-the-implementer-why
repoUrl: "https://github.com/JaviMaligno/personal-website/tree/main/experiments/agent-telephone"
heroImage: "/blog/nobody-tells-the-implementer-why.png"
---

<style>
.tel-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.tel-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.tel-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

I dictate a lot of what I ask my agents, and the transcriber has a weakness for names. "Siobhán" comes out as something else, and nothing in the rest of the message lets anyone recover it. When that request then goes to a lead agent, which passes it to a product manager, which passes it to an architect, which passes it to whoever writes the code, I wanted to know two things: what reaches the end of the chain, and whether the agents add noise of their own along the way.

It is the children's game of telephone, played with agents. But I did not want the artificial version, with ten agents in a row whispering to each other. In real setups a message rarely crosses more than three or four agents, and when it does it is because there is a hierarchy: a lead and roles under it. So that is what I measured.

## The setup

Six client requests, three for software and three for an event agency. The software ones ask for a small Python module (appointment reminders for an optician, seat proration for a SaaS bill, a GDPR purge job). The event ones ask for a plan: a company away-day, a Spanish–Finnish wedding, a scientific conference. Each request is written the way a client talks, and each contains facts of several kinds, tagged in advance: names, numbers, prohibitions, conditions, priorities, details easy to overlook, and **reasons** ("because the old field went stale after the March CRM migration").

Two team shapes, both realistic:

<figure class="tel-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Two team topologies. In the chain, the client's request goes to the lead, then the product manager, the architect and the implementer, four hops. In the relay, the lead sends the request to the product manager, gets the answer back, and then writes the fourth hop to the implementer itself, with the client's original request still in hand.">
  <defs><marker id="tel-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#64748b"/></marker><marker id="tel-ah-amber" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#f59e0b"/></marker></defs>
  <text x="20" y="24" fill="#94a3b8" font-size="12" font-weight="600">Chain</text>
  <rect x="20" y="35" width="80" height="34" rx="7" fill="#232334" stroke="#64748b"/><text x="60" y="56" text-anchor="middle" fill="#e2e8f0" font-size="12">client</text>
  <rect x="130" y="35" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="170" y="56" text-anchor="middle" fill="#e2e8f0" font-size="12">lead</text>
  <rect x="240" y="35" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="280" y="56" text-anchor="middle" fill="#e2e8f0" font-size="12">PM</text>
  <rect x="350" y="35" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="390" y="56" text-anchor="middle" fill="#e2e8f0" font-size="12">architect</text>
  <rect x="460" y="35" width="110" height="34" rx="7" fill="#232334" stroke="#f59e0b"/><text x="515" y="56" text-anchor="middle" fill="#fbbf24" font-size="12">implementer</text>
  <path d="M100 52 L128 52" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/><path d="M210 52 L238 52" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/>
  <path d="M320 52 L348 52" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/><path d="M430 52 L458 52" stroke="#f59e0b" stroke-width="1.5" marker-end="url(#tel-ah-amber)"/>
  <text x="114" y="86" text-anchor="middle" fill="#94a3b8" font-size="10">1</text><text x="224" y="86" text-anchor="middle" fill="#94a3b8" font-size="10">2</text>
  <text x="334" y="86" text-anchor="middle" fill="#94a3b8" font-size="10">3</text><text x="444" y="86" text-anchor="middle" fill="#fbbf24" font-size="10">4</text>
  <text x="20" y="128" fill="#94a3b8" font-size="12" font-weight="600">Relay</text>
  <rect x="20" y="175" width="80" height="34" rx="7" fill="#232334" stroke="#64748b"/><text x="60" y="196" text-anchor="middle" fill="#e2e8f0" font-size="12">client</text>
  <rect x="130" y="175" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="170" y="196" text-anchor="middle" fill="#e2e8f0" font-size="12">lead</text>
  <rect x="270" y="135" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="310" y="156" text-anchor="middle" fill="#e2e8f0" font-size="12">PM</text>
  <rect x="270" y="218" width="110" height="34" rx="7" fill="#232334" stroke="#f59e0b"/><text x="325" y="239" text-anchor="middle" fill="#fbbf24" font-size="12">implementer</text>
  <path d="M100 192 L128 192" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/>
  <path d="M210 182 L268 150" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/>
  <path d="M270 163 L212 192" stroke="#64748b" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#tel-ah)"/>
  <path d="M210 202 L268 232" stroke="#f59e0b" stroke-width="1.5" marker-end="url(#tel-ah-amber)"/>
  <text x="114" y="226" text-anchor="middle" fill="#94a3b8" font-size="10">1</text>
  <text x="232" y="152" text-anchor="middle" fill="#94a3b8" font-size="10">2</text>
  <text x="254" y="190" text-anchor="middle" fill="#94a3b8" font-size="10">3</text>
  <text x="228" y="232" text-anchor="middle" fill="#fbbf24" font-size="10">4</text>
  <text x="395" y="232" fill="#94a3b8" font-size="11">the lead writes hop 4</text>
  <text x="395" y="247" fill="#94a3b8" font-size="11">with the client's request in hand</text>
</svg>
<figcaption>In the chain, the implementer's message has been rewritten three times. In the relay it is also hop 4, but its author has the original request in front of it. That difference is what separates distance from audience.</figcaption>
</figure>

The event teams have three roles (account manager, logistics, vendor liaison) instead of four, so their chain is one hop shorter.

Each message between agents went out in one of three formats: free prose, a numbered requirement list, or a short note with the client's original request attached verbatim. The original request came in four versions: clean, or with one transcription error of a different type (a mangled name, a homophone, or punctuation that changes the meaning: "No, do it this way" against "No do it this way").

The models were Claude Haiku 5.5 and Sonnet 5.5, running as real nested subagents in Claude Code, and GPT-6 Luna in my own harness, which passes the same messages from role to role. Three repetitions per cell: 853 valid Claude runs and 432 Luna runs. Every message was scored fact by fact as preserved, lost, distorted or inverted: names and numbers by deterministic checks, the rest by a judge from a different family from the agents: GPT-6.1 Sol (through Codex) for the Claude runs, and Claude Opus 5.5 for the Luna runs. The final artifact, the code or the plan, went through hidden tests that check each requirement.

## Almost everything arrives

Most of the request survives the trip. At hop 4, in the Claude runs, prohibitions arrive intact 98% of the time, details that are easy to miss 96%, numbers 92%, names and conditions 90%, priorities 85%. Luna lands in the same range: 91–99% for everything except one type.

That type is the reasons.

## The why is not worn away. It is cut

In the Claude chain, the reason behind a decision travels well for two hops: 88–99% in the lead's message to the PM, 83–97% from the PM to the architect. Then the architect writes to the implementer, and it falls to 8–31%.

The obvious reading would be distance: four hops, four chances to lose something. The relay rules that out. There, the lead writes hop 4 itself, with the client's request in front of it, and only keeps the reason in **24%** of its messages to the implementer, with Haiku and with Sonnet alike. It has the information; it chooses not to pass it on.

<figure class="tel-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Share of messages that keep the reason behind a decision, in the software teams, by message and model. Lead to PM: Haiku 88%, Sonnet 99%, Luna 30%. PM to architect: 83%, 97%, 28%. Architect to implementer: 31%, 8%, 13%. Lead to implementer in the relay, with the original request at hand: 24%, 24%, 22%.">
  <rect x="380" y="10" width="10" height="10" fill="#2dd4bf"/><text x="395" y="19" fill="#e2e8f0" font-size="11">Haiku</text>
  <rect x="445" y="10" width="10" height="10" fill="#f59e0b"/><text x="460" y="19" fill="#e2e8f0" font-size="11">Sonnet</text>
  <rect x="515" y="10" width="10" height="10" fill="#94a3b8"/><text x="530" y="19" fill="#e2e8f0" font-size="11">Luna</text>
  <path d="M70 50 L585 50" stroke="rgba(255,255,255,0.08)"/><path d="M70 145 L585 145" stroke="rgba(255,255,255,0.08)"/><path d="M70 240 L585 240" stroke="#64748b"/>
  <text x="62" y="54" text-anchor="end" fill="#94a3b8" font-size="10">100%</text><text x="62" y="149" text-anchor="end" fill="#94a3b8" font-size="10">50%</text><text x="62" y="244" text-anchor="end" fill="#94a3b8" font-size="10">0</text>
  <rect x="462" y="34" width="116" height="210" rx="6" fill="none" stroke="#f59e0b" stroke-dasharray="4 3" opacity="0.6"/>
  <rect x="80" y="73" width="30" height="167" fill="#2dd4bf"/><rect x="114" y="52" width="30" height="188" fill="#f59e0b"/><rect x="148" y="183" width="30" height="57" fill="#94a3b8"/>
  <rect x="210" y="82" width="30" height="158" fill="#2dd4bf"/><rect x="244" y="56" width="30" height="184" fill="#f59e0b"/><rect x="278" y="187" width="30" height="53" fill="#94a3b8"/>
  <rect x="340" y="181" width="30" height="59" fill="#2dd4bf"/><rect x="374" y="225" width="30" height="15" fill="#f59e0b"/><rect x="408" y="215" width="30" height="25" fill="#94a3b8"/>
  <rect x="470" y="194" width="30" height="46" fill="#2dd4bf"/><rect x="504" y="194" width="30" height="46" fill="#f59e0b"/><rect x="538" y="198" width="30" height="42" fill="#94a3b8"/>
  <text x="129" y="260" text-anchor="middle" fill="#e2e8f0" font-size="11">lead → PM</text><text x="129" y="275" text-anchor="middle" fill="#94a3b8" font-size="10">hop 2</text>
  <text x="259" y="260" text-anchor="middle" fill="#e2e8f0" font-size="11">PM → architect</text><text x="259" y="275" text-anchor="middle" fill="#94a3b8" font-size="10">hop 3</text>
  <text x="389" y="260" text-anchor="middle" fill="#e2e8f0" font-size="11">architect → impl.</text><text x="389" y="275" text-anchor="middle" fill="#94a3b8" font-size="10">hop 4, chain</text>
  <text x="519" y="260" text-anchor="middle" fill="#fbbf24" font-size="11">lead → impl.</text><text x="519" y="275" text-anchor="middle" fill="#94a3b8" font-size="10">hop 4, relay</text>
</svg>
<figcaption>Share of messages that keep the reason behind a decision (software teams, prose and list formats). The drop is in the message to the implementer, and it happens just the same when the writer has the full request at hand.</figcaption>
</figure>

So it is not a telephone effect in the sense of something wearing away from mouth to mouth. It is a decision about the audience: whoever writes to the person who builds writes instructions, and instructions do not carry reasons. Luna does the same, only earlier: it drops the reason from the very first message (it keeps it in 30% of its messages to the PM) and stays low all the way down.

In the event teams the cut is milder. The vendor, who books the caterer and writes the plan, still gets the reason 75–84% of the time in the Claude chain, and 40–64% when the lead writes to it directly in the relay. The executor writing code is the one who hears it least.

### Does losing it matter?

That was my next question, and the answer is less tidy than I expected. Within each rule, format and model, I compared runs where the reason reached the implementer with runs where it did not, and looked at whether the final artifact obeyed the rule. With Claude, keeping the reason did not help: rules were obeyed slightly *less* often when their reason arrived (10 points less, 95% interval −15 to −5). With Luna the difference goes the other way, +9 points, but the interval crosses zero.

The negative effect in Claude is concentrated in Haiku and in rules whose reason names the old thing. "Inactivity is measured on `last_seen_at`, not `last_login`, because the mobile app stopped updating `last_login`": with that reason in the message, Haiku used the right field 59% of the time; without it, 97%. My hypothesis is that the reason puts the wrong name back into the message and acts as a distractor. This analysis was not planned before the runs, so I take it as a hypothesis, not a conclusion. But it is enough to stop me from claiming that the why is always worth carrying.

What does matter, clearly, is losing the requirement itself. In the Claude runs, a fact that arrived intact at the implementer was satisfied in the final artifact 95% of the time; one that was lost on the way, 40%. Losses are rare, but each one shows up in the result.

## Names freeze; punctuation gets repaired

The transcription errors behave very differently depending on the type.

A mangled name cannot be repaired from the text: nothing in the request says how "Siobhán" should be spelled. But it can be questioned, the way a person would ask "is that name right?". Almost nobody did. In the Claude hand-offs, under 2% of the messages that carried a mangled name marked it as doubtful; Luna, never. The name froze and reached the artifact as transcribed: every final plan or module that used it used the wrong version.

Punctuation errors that change the meaning, on the other hand, were repaired about two thirds of the time in the hand-offs (Claude 66%, Luna 73%), probably because the rest of the request makes the intended reading obvious. Claude repeated the wrong reading as given in about one message in seven; Luna, in one in twenty.

## The format matters, depending on the model

For Claude, the hand-off format barely changes anything: a numbered list keeps a little more at hop 4 than prose (88% against 85% of facts), and the final code scores about the same in all three formats.

For Luna it changes everything.

<figure class="tel-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Mean share of hidden tests passed by the final software module, by hand-off format and model. Free prose: Haiku 72%, Sonnet 89%, Luna 23%. Numbered list: Haiku 72%, Sonnet 89%, Luna 76%. Note with the original attached: Haiku 71%, Sonnet 91%, Luna 86%.">
  <rect x="380" y="10" width="10" height="10" fill="#2dd4bf"/><text x="395" y="19" fill="#e2e8f0" font-size="11">Haiku</text>
  <rect x="445" y="10" width="10" height="10" fill="#f59e0b"/><text x="460" y="19" fill="#e2e8f0" font-size="11">Sonnet</text>
  <rect x="515" y="10" width="10" height="10" fill="#94a3b8"/><text x="530" y="19" fill="#e2e8f0" font-size="11">Luna</text>
  <path d="M70 50 L585 50" stroke="rgba(255,255,255,0.08)"/><path d="M70 135 L585 135" stroke="rgba(255,255,255,0.08)"/><path d="M70 220 L585 220" stroke="#64748b"/>
  <text x="62" y="54" text-anchor="end" fill="#94a3b8" font-size="10">100%</text><text x="62" y="139" text-anchor="end" fill="#94a3b8" font-size="10">50%</text><text x="62" y="224" text-anchor="end" fill="#94a3b8" font-size="10">0</text>
  <rect x="110" y="98" width="34" height="122" fill="#2dd4bf"/><rect x="150" y="69" width="34" height="151" fill="#f59e0b"/><rect x="190" y="181" width="34" height="39" fill="#94a3b8"/>
  <rect x="270" y="98" width="34" height="122" fill="#2dd4bf"/><rect x="310" y="69" width="34" height="151" fill="#f59e0b"/><rect x="350" y="91" width="34" height="129" fill="#94a3b8"/>
  <rect x="430" y="99" width="34" height="121" fill="#2dd4bf"/><rect x="470" y="65" width="34" height="155" fill="#f59e0b"/><rect x="510" y="74" width="34" height="146" fill="#94a3b8"/>
  <text x="207" y="175" text-anchor="middle" fill="#e2e8f0" font-size="10">23%</text>
  <text x="167" y="240" text-anchor="middle" fill="#e2e8f0" font-size="11">prose</text>
  <text x="327" y="240" text-anchor="middle" fill="#e2e8f0" font-size="11">numbered list</text>
  <text x="487" y="240" text-anchor="middle" fill="#e2e8f0" font-size="11">note + original attached</text>
</svg>
<figcaption>Final software module, mean share of hidden tests passed. Luna's code is not worse in itself: with a list or with the original attached it lands next to Claude. In prose, its summary drops the input fields, and the implementer invents them.</figcaption>
</figure>

When I first saw Luna's numbers I assumed its code was simply worse. It is not. The client lists the fields of the input data ("each appointment has `id`, `customer_name`, `email`…"), and Luna, summarising in prose, dropped that list from the message to the implementer in **54 of 72** runs. The implementer then invented the names (`appointment["appointment_id"]` instead of `appointment["id"]`), and the module crashed on the first test. With a numbered list the contract arrived 89% of the time; with the original attached, always. Its code then scored 0.76 and 0.86, next to Sonnet.

Claude kept that contract in practically every run, in all three formats. Its failures came from somewhere else: in 29 of its 216 software runs, Haiku's implementer did not deliver code at all, but a specification, because that was the shape of the message the architect had sent it. The type of deliverable had drifted down the chain too.

## What I am taking from this

- **If the reason matters to the person executing, it has to be in their message, and nobody will put it there for you.** The intermediate roles carry it; the one writing to the executor removes it. If you want the implementer to know *why*, say so in the delegation or attach the original.
- **Attach the original request to the last hop.** It was the most robust format across the three models and the only one where Luna did not lose the data contract. It costs tokens, but the alternative is the implementer guessing field names.
- **Contracts travel verbatim, not summarised.** Field names, signatures and output shapes are exactly the kind of thing a summary in prose drops because it looks like detail.
- **Ask your agents to flag names they cannot verify.** A mangled name cannot be fixed downstream, but it can be questioned, and in these runs nobody did.

This fits with what I found when [comparing ways of making coding agents collaborate](/en/blog/coding-agents-structure): what helped was the shape of the team and its hand-offs, not a better conversation protocol. Here too, the biggest effect was not in the models' intelligence but in what each message is asked to carry.

## Limits

- Six hand-written requests, three per domain. The transcription errors are synthetic: written to look like what a transcriber does, not produced by running one.
- Claude ran in Claude Code with real subagents; Luna ran in my own harness. Comparisons between them mix model and harness.
- The judge was validated on a pilot sample of 150 labels against a second model as annotator (Claude Opus 5.5) and a third as adjudicator (Claude Fable 5.1), not against human labels. Both are from the same family as the Claude agents. On the pilot, its agreement was good on losses and weaker on distortions (κ 0.79 overall), so distortion rates are probably underestimated. Its agreement with itself on a second pass was 0.93 (GPT) and 0.97 (Claude).
- Two checks on the event plans were corrected after seeing the data: they counted "not Coachline" as a booking of Coachline. With the correction, only 3 plans across both grids book the vendor the client excluded.
- Sonnet delegated twice in the same step in 7% of its first attempts, mostly in event runs (25 of 30). Those runs were repeated; excluding them moves no figure by more than about two points.
- The analysis of whether the reason helps obey the rule was not planned in advance.
- Claude Code adds the account's name and email to the main session's context even when the system prompt is replaced. In 17 of the 853 Claude runs the lead used them, treating my email as the client's or naming me as the go-between. No scored fact depends on it; the published data has them replaced.

---

*The code, the six requests, every message between agents, the final artifacts and the scores are in [`experiments/agent-telephone`](https://github.com/JaviMaligno/personal-website/tree/main/experiments/agent-telephone). The design, with its hypotheses fixed before the runs and every later change dated, is in `DESIGN.md`; `scripts/article_numbers.py` recomputes every figure in this article from the published data.*
