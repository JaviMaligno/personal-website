# A definition across an agent handoff

Protocol fixed before live calls, 2026-09-21. Exploratory third study; earlier
pilots remain separate. Do not presume that this study will justify an article.

## Question and scope

Does a named operational distinction survive a handoff, or do decisions converge
on a simpler interpretation that also fits the examples seen during development?
An observed loss is behavioural evidence about the transmitted instructions,
not a measurement of internal concepts, deception, or human trust.

Naming is requested deliberately. This is NOT a test of spontaneous jargon.
No definition is deliberately removed from the primary handoffs. The receiving
writer gets the previous complete guide and is asked to preserve the rules.
If it retains them and execution remains correct, that is a negative finding for
the proposed failure mechanism, not grounds for repeatedly changing the task.

## Four policies and a deliberately incomplete visible suite

Software workflows: recovery across database/external side effects; approval
bound to revision and scope; corroboration with shared sources and a blind
recheck; retry permission from either a matching receipt or safe idempotency.
These are simulated policies with stipulated rules, not recommended real-world
security/operations policy. Actions are labels, with no external side effects.

Each policy uses four Boolean fields plus a hard-block flag. The bank contains
all 16 combinations with the hard block false, and four with the block true:
20 inputs per policy. Independent truth sets check every gold label.

Six visible cases per task: two allow, two review where the full policy P agrees
with a prespecified simpler policy Q, plus two deny cases. The other 14 are
reserved, including every disagreement between P and Q. Selection is deterministic
and occurs before model calls. This is an intentionally weak visible suite, not
a random sample of deployment inputs. Success on it cannot identify P versus Q.
The schema and rules do not change between visible and reserved inputs; only
combinations change. Q is an analytical comparison, never a rule secretly given
to the receiver. P and Q are recorded before outputs, so observed failures can
also disagree with both and must not automatically be called reconstruction of Q.

## Stages

1. Two source writers each receive each full policy, schema and visible examples.
   They choose a concise local name and write a standalone guide (180 words
   requested). JSON contains `term` and `guide`. All eight artefacts are kept.
2. Both executors run each source guide on only the six visible cases, once each:
   16 calls. Exact results, including errors/invalid outputs, become the feedback.
3. A fresh call to the opposite model receives the source guide, its name, schema,
   visible examples and both executors' feedback. It prepares a shorter standalone
   guide (80 words requested), preserving the name and policy. It has no original
   policy or reserved inputs. Passing results do not select or filter the chains;
   failed visible results are retained and the receiving writer may address them.
4. Freeze all guides and final job prompts before evaluating reserved cases.
   Both executors receive each variant in fresh calls, twice, with all 20 inputs
   intermixed. Input order is paired across variants/models within a source-chain
   repetition and changed between repetitions. Executors see no test feedback,
   gold labels, alternative prompts, or history.

Four final variants per chain: canonical full policy; source guide; received
guide; received guide with every case-insensitive exact occurrence of its term
replaced by a fixed opaque name. No other text is changed in the rename. If the
term is absent, the rename contrast is marked unavailable, not counted as a
meaningful null. Renaming is not erasing all semantic clues, because definitions
and descriptive fields remain. It isolates the literal name's contribution in
the preserved guide, not every effect of naming.

Maximum 160 calls: 8 source + 16 visible execution + 8 handoff + 128 final.
Invalid generation can make dependent calls unavailable; keep those exclusions.
Word limits are requests, not truncation or a filter for favourable results.
Do not retry invalid JSON or incorrect decisions. Retry transport failures only
explicitly, preserving attempt histories. Stop before dependent stages if any
transport/interruption is unresolved.

## Report, including results that argue against the proposed story

- Every original and transmitted guide; names retained/changed and word counts.
- Canonical policy correctness, source-guide correctness and received-guide
  correctness, separately for visible, reserved, and P/Q-separating inputs.
- Chains passing visible tests under both executors but failing reserved tests.
- Stronger drift case: source and canonical variants agree with P in both
  repetitions; received variant repeatedly disagrees on the same input.
- On those changed inputs, does the received answer equal Q or neither P nor Q?
- Name-only effects compare received versus renamed on the same input and model,
  with separate reporting for repeated effects and within-condition variation.
- Distinguish original encoding errors from losses during handoff, unchanged
  errors, repaired errors, unsupported labels, and missing/incomplete calls.
- Inspect exact guide differences for every repeated drift case. Automated
  correctness is not enough to claim that a definition disappeared.

No model explanation is used as a proxy for behaviour. No significance claims or
population failure rates: there are four policy families and eight source chains,
not thousands of independent examples. Two repetitions only check repeatability
in this run. Canonical calls are paired controls and reuse four policies.
Observed Q agreement does not uniquely identify the executor's internal rule.
This design does not isolate compression from cross-model rewriting or feedback;
they jointly define the handoff condition. It does not measure long-term adoption.

## Execution and cost

Reuse the verified v2 private configuration and unmodified transport. GPT-5.6 Sol
through the existing gateway; Claude Opus 5 through Vertex global. 8192 output
tokens; GPT temperature 1; Claude adaptive thinking without temperature.
Concurrency at most two. Obtain existing credentials serially, keep them in
process memory only; do not persist tokens. Private config and provider envelopes
stay in ignored `runs/`; public export omits routing, credential paths and IDs.

Prior estimate: 20–35 minutes, gateway USD 3–7, Vertex USD 4–10, no external compute.
Reference costs use the previous pilot's recorded rates (4/20 and 5/25 USD per
million input/output tokens), not a claimed provider invoice or newly verified
price. Log realised tokens, wall time and all attempts. Freeze source hashes and
all stage prompts, and validate oracles/interventions/analysis with fixtures
before calling the models.
