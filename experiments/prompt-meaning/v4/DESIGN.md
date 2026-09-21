# Project handoffs and maintenance reviews

Frozen before model calls, 2026-09-21. Exploratory fourth study, following three
preserved pilots. This protocol was designed after their results were known.

## What changed

The substrate is an existing research implementation, not a newly invented
Boolean policy. Eight unmodified source snapshots include a 59 kB implementation
plan, a 12 kB design, implementation modules and regression tests. Two work areas
are sampled: evidence-dose refinement and endpoint-space geometry metrics.
The source revision and byte hashes are in `sources/manifest.json`.

These are project-local concepts already used in implementation instructions.
We have NOT established that an agent coined them, or that they are unknown in
the literature. This experiment cannot establish spontaneous jargon formation.
The earlier peer-message corpus motivated looking at real work but is NOT the
sample in this study; its private transcripts are not sent to providers.

## Procedure

Each work area starts twice, once with each model as the first writer (four
chains, no outcome-based case selection). The writer receives the complete
existing design, plan, implementation and tests for that work area. The task is
to prepare a maintenance handoff, with a 650-word target. No invented names are
requested. A second, isolated model receives that handoff and prepares a
450-word reviewer brief; a third isolated model receives that brief and prepares
a 350-word session note. Models alternate within each chain. These word counts
are targets, not enforced truncations; deviations are reported.

This simulates successive session handoffs with explicit compression. It is not
a live multi-agent coding session, a natural longitudinal corpus, or an induced
context-window overflow. It tests retention in agent-written instructions for
real maintenance work. Agents have no file retrieval; this models an isolated
recipient and limits generalization to agents that can retrieve the originals.

## Evaluation

Each of the two executor models reviews the same 16 proposed maintenance changes
per work area, in two fresh repetitions, under four contexts: original dossier,
first handoff, third handoff, and third handoff with project labels consistently
replaced by opaque labels. The replacement also applies to the proposal text,
so an API-name mismatch is not introduced. Rename contrasts are omitted when no
target label occurs in the third handoff. All chains remain in the record.

Four proposals per task are designated routine and twelve boundary-sensitive
before calls. These are constructed review probes derived from the existing
code/tests, not actual historical PRs. Their expected decisions and source
anchors are frozen in `bank.py`. They are not shown to any handoff writer.
Order is shuffled deterministically by chain and repetition and paired across
variants and executors. Reviewers may explicitly request context; this counts
as abstention, not as a wrong decision. Malformed output is separate.

Primary descriptive quantities: incorrect decisions and abstentions by context;
stable new errors after handoff where full context and first handoff were
correct twice; stable lexical changes where renaming changes a decision twice;
and cases where all routine proposals are correct but a reserved boundary is
consistently wrong. Report proposed source-to-final losses separately from
errors already introduced by the first summary. Quote actual reasons to assess
whether a terminology effect is supported. No significance tests or claims
that repeated decisions are independent conceptual discoveries.

Correct source-context reviews are a competence check, not a claim that every
source statement is correct. Probe answers are pinned to current documented
behavior, including explicit exceptions, not to an idealized redesign. Conflicts
between old plan and current implementation/tests resolve to the latter, and
this precedence is stated to the writers and reviewers.

## Controls and stopping

The full dossier controls task competence; first versus third handoff separates
initial summarization from later transmission; opaque renaming changes surface
labels while holding the substantive instructions fixed. Compression and lack
of retrieval remain explicit causes of possible information loss. A handoff
error alone does not establish a jargon effect or shared private language.

Maximum 76 calls: 12 handoffs + 64 reviews. No retries for malformed output, no
resampling a failed chain, no changing probes after seeing results. Transport
errors are recorded without automatic retries. Plans, prompts, source hashes
and every attempt persist. Invalid handoffs block their dependent chain.

Models and transports: existing GPT-5.6 Sol gateway and Claude Opus 5 through
Vertex with existing gcloud login. Same settings as pilot 3, max 8192 output
tokens, two concurrent requests. Credentials remain in RAM/private config.
Before live execution report estimated wall time and provider costs.

All conclusions remain conditional on two work areas from one project and four
generated chains. The study does not measure human comprehension, reliability
of arbitrary production agents, or the prevalence of invented jargon.
