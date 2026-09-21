# Targeted label × explicit-reference follow-up

Exploratory follow-up designed AFTER reading the main results. Do not pool it
with the original pre-call test or call it independent discovery.

Observed candidate: GPT, globally opaque geometry context, repetition 1,
accepted p07 and rejected p08. Its reasons interpreted `on failure` as failure
of IoU evaluation rather than failure of the preceding invariance check.
The other opaque repetition and both original-label repetitions were correct.
These two wrong proposal decisions are ONE underlying interpretation, not two
independent findings.

The final handoff's actual sentence is:

> iou_vs_truth returns non_positional with iou=None on failure; otherwise it uses the first velocity sample.

The preceding sentence describes `preimage_invariant`. The current source code
explicitly branches on `not preimage_invariant(...)`. The final handoff was
generated in the main run without being shown these proposals.

## Bounded factorial check

Only GPT, the executor that made the observed error. Four conditions, five fresh
calls each, the same 16 geometry proposals and same third handoff:

1. Original category name and original sentence.
2. Replace only `non_positional` with `class_q8`, in context AND proposals.
3. Original name; replace `on failure` with `when preimage_invariant returns False`.
4. The same explicit-reference edit AND the single category rename.

All other terminology, source sentences, proposals and instructions stay fixed.
Proposal order is paired across conditions, deterministically shuffled per
repetition. Only the one preselected sentence may be edited. Freeze all 20
prompts before calls. No retries or expansion if the result is null.

The original globally renamed condition is NOT repeated here. This check asks
whether the candidate explanation can be localized to this category name and
the unclear reference. A negative result does not retroactively erase the
original error, and it does not prove that every possible rename is inert.

Primary report: p07/p08 response pairs per repetition in all four cells; all
other decisions remain diagnostic controls. Separate wrong decisions,
abstentions, malformed calls and output reasons. If the proposed interaction
does not recur, report it as not reproduced, without adding new arms.

20 calls; estimate 3–6 minutes, $0.5–1.5 on the existing GPT gateway. No Claude
calls are needed for this within-model mechanistic follow-up. Across main,
boundary supplement and this check, the planned total is 76 calls.
