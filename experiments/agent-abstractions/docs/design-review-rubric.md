# Blind design review of agent diffs — pre-registered rubric (2026-10-08)

Written and committed BEFORE any score is seen. Motivation (Javier, 2026-10-08):
the phase-1 "bad decision" metric (invariant bypasses) is narrow and says nothing
about higher-level design quality; abstraction is supposed to help there.

## Sample
Passes 0–2 of every task × condition × agent in both arms (`runs/`, `runs-hard/`):
470 diffs (10 timeouts without a diff excluded). Packets in `work/review/packets/<id>/`
hold only `statement.md`, `diff.patch` and the path of the code tree the diff applies
to. Ids are neutral hashes; the four trees have shuffled neutral names (t1–t4). The
mapping (`work/review-mapping.json`) is never shown to judges.
**Limitation:** blindness is partial — A⁺ code is recognisable (domain commands,
`Cents`). Judges are not told conditions, agents, hypothesis or that conditions exist.

## Judge
A model not under test (Claude Opus 5.5 workflow agents; agents under test were
Sonnet 5.5 and gpt-6-luna). Reads the statement, the diff and the tree (read/grep only).
Judges DESIGN only; behavioural correctness is measured separately and ignored.

## Scores (1 = poor … 5 = excellent), each with a one-sentence justification
1. **reuse** — uses the helpers/abstractions that already exist in this tree instead of
   re-implementing them.
2. **duplication** — the diff does not duplicate logic (within itself or with existing code).
3. **placement** — logic lives in the module/layer where this tree puts that kind of logic;
   respects the existing layering.
4. **scope** — the change is focused; no unrelated edits.
5. **maintainability** — overall, a maintainer would be comfortable owning this design.
Plus: `bypasses_abstraction` (bool + where), `duplicated_blocks` (int),
`would_merge` (yes | with_changes | no).

## Reliability
A second, independent judge scores a random 15 % of packets; report weighted agreement
(quadratic-weighted Cohen's kappa) per dimension before any condition comparison.

## Analysis (pre-registered)
Primary: **maintainability**, A vs AP per agent and arm; ordinal mixed model with task
random effect (or Mann-Whitney + per-task sign test if the model fails). Secondary:
the other four scores, `duplicated_blocks`, `would_merge`. Lint factor (AL, APL)
reported descriptively. Multiple comparisons stated; no single p near 0.05 is read as
an effect.

## Study 2 addendum (2026-10-10, before any study-2 score is seen)
Same rubric, judge model and instructions, applied to `work/review2/packets/` (960 packets:
768 step diffs + 192 cumulative chain diffs, R and F, three agents; exported by
`aa chain packets`, every diff verified with `git apply --check` on its base tree plus
pre-image, and the evaluator's measured change verified identical to the agent's diff).
Base trees are two fresh single-commit repos with neutral names (`work/review2/trees/`);
for a step packet the judge applies `pre-image.patch` in a temporary worktree.
Blindness is partial: F's helpers are recognisable. Judges are not told conditions,
agents, hypotheses or that conditions exist. Batches of 12, seeded shuffle; a second judge
scores a seeded 15 % (144 packets); kappa reported before any comparison.
Analysis (H4): maintainability F vs R per agent, step packets and chain packets separately;
Mann-Whitney + per-zone sign test, ordinal mixed model with chain random effect if it fits.
Secondary as in study 1. Nothing near p = 0.05 read as an effect on its own.

## Study 3 addendum (2026-10-11, before any study-3 run and before any study-3 score)
Plan Task 7; spec `docs/specs/2026-10-10-agent-as-designer-design.md` sections 3, 6, 7.
Committed before any study-3 packet is judged. Tooling: `aa.review3`,
`scripts/study3_review_packets.py` or `aa chain packets --study 3` (packets, batches,
the judges' trees),
`scripts/study3_design_review.py` (kappa, labels, H1 tables).

**Sample.** From `runs3/` (arms R, RG, RL, RC) plus the study-2 F chains (`runs2/`):
- *step* packets: every evaluated T1–T4 step that changed something (as study 2);
- *t0* packets (RC): the T0 statement, the T0 diff and the zone's copy sites
  (`sites.json`, judge-facing copy of `tasks3/<zone>/T0/sites.json`: logic, decision,
  sites, existing-helper / not-a-copy notes, inconsistencies to preserve; without the
  zone id, the source note, F's reference or any mention of variants, tasks or spec);
- *chain* packets (H1 primary): the T1–T4 diff of every complete chain. R, RG, RL:
  untouched start → T4. RC: the agent's T0 tree → T4, read on T0's tree (the analogue
  of F's diff from F);
- *chain_full* packets (RC, secondary): T0..T4 from the untouched start;
- the study-2 F *chain* packets, re-exported with the same scheme, so that F and the
  four arms are judged by the same judges in the same batches (study-2 scores of F are
  not compared with study-3 scores). F step packets are not re-exported, so F's T2
  judge label in `aa tables3`'s descriptive F column stays pending.
Ids: `sha256(salt, kind, agent, arm, zone, chain[, step])[:10]`, salt `study3` (the
study-2 scheme). Mapping in `work/review3-mapping.json`, never shown to judges.

**Blinding to arm.** Every R-based arm (R, RG, RL, RC) is judged on ONE neutral base
tree, the untouched R variant, never the arm image (F on its own, as in study 2). From
every pre-image and diff, in every arm: file sections of any `AGENTS.md`,
`packages/loot-core/bin/dup-check.mjs` and `dup-check.config.json`, `.jscpd*` and
dup-check files, and any file holding dup-check output are removed; lines mentioning
jscpd, dup-check, AGENTS.md, a duplication lint/check/ratchet, dup-check output, the RG
rule's phrases or common paraphrases of it ("don't duplicate logic", "extracted the logic
into a shared helper", "change it in a single place") are dropped (hunk headers
recounted). The root and loot-core `package.json` (which RL's patch touches) are kept,
since dependency changes are the agent's design, with their dup-check lines dropped;
only when the result cannot apply to the neutral base (a hunk next to RL's lint scripts)
is the section removed, recorded as `package_json_stripped` (amendment of 2026-10-11,
review of Task 7; before, `package.json` was removed in every arm). What was removed is
recorded in the mapping. Every packet file is
then scanned for arm, run-path, agent and study words, dup-check/jscpd and the rule's
phrases; a packet that still leaks is not exported (listed in `apply-check.json`).
Diffs are checked with `git apply --check` on the base tree + pre-image after
sanitising.
**The judge's tree (amended 2026-10-11, review of Task 7, before any score).** No packet
ships a pre-image. Each packet's sanitised pre-image is applied to its base tree in ONE
neutral bare repository (`work/review3/trees/<neutral name>.git`), one parentless commit
per packet with a fixed date and the packet id as message; `tree.txt` names the
repository and the packet's commit, in the same form for every packet (the judge's
workflow checks that commit out with `git worktree add --detach`). Before this, RC's
chain and T1 packets carried T0's tree as a non-empty pre-image, and a `tree.txt` saying
to apply it, where every R/RG/RL chain and T1 packet had none: the packet's form told
the judge that a T0 refactor had happened (in a dry run on study-2 data: 96/96 R/RG/RL
chain and T1 pre-images empty, 4/4 RC non-empty). A dry run on study-2 data (`scripts/study3_review_dry_run.py`) checks that
the same agent work linked under R, RG and RL gives identical packets.
**Limitations (partial blindness, inherent):** the content of RC's chain and T1 trees is
the agent's T0 refactor (a judge reading that tree closely may see code more factored
than other packets'); *t0* and *chain_full* packets exist only in RC; F's helpers are
recognisable (as in study 2).
Removing gaming artefacts (markers, configs) hides them from the judge; gaming is
measured by `aa.static3`'s flags, not by the judge.

**Judge.** As study 2 (Claude Opus 5.5 workflow agents, not under test; read/grep only
on the packet's tree; design only, behaviour ignored; not told arms, agents,
hypotheses or that arms exist). Each packet's `questions.json` lists the questions it
asks; they depend on the packet kind and the step kind only, never on the arm:

| packet | questions |
|---|---|
| step T1, T3 (rule) | five scores, `bypasses_abstraction`, `duplicated_blocks`, `would_merge`, `disguised_duplication`, `one_place` |
| step T2 (consumer) | the same with `t2_reuse` instead of `one_place` |
| step T4 (build) | the same without either |
| chain, chain_full | five scores, flags as above, `disguised_duplication`, `abstraction_drift` |
| t0 | `completeness`, `interface`, `disguised_duplication` |

New questions (the study-1 ones are unchanged):
- `t2_reuse` (T2 reuse label, primary H2 measure): `"helper"` when the new consumer
  calls a shared function that also serves the pre-existing consumers (including one an
  earlier change in this tree created); `"copy"` when it copies existing logic;
  `"reimplements"` when it writes its own version of that logic without copying it.
- `one_place` (T1/T3): `{"value": bool, "where": str}`: does the rule change land in one
  shared definition that every code path applying the rule uses?
- `abstraction_drift` (chain packets): `{"value": bool, "parameters_added": int,
  "special_case_branches": int, "bypassing_call_sites": int, "where": str}`: over the
  chain, flags/parameters added to a shared helper, special-case branches added inside
  it, call sites that bypass or re-implement it.
- `disguised_duplication` (every packet, so that it does not mark RL): `{"value": bool,
  "where": str}`: is logic this diff duplicates (within itself or with the tree)
  disguised (renamed, reordered, split or reshaped) rather than removed or shared?
- `completeness` (t0): for each site in `sites.json`, does its *decision* now go
  through one shared definition? `{"per_site": {site id: bool}, "sites_shared": int,
  "sites_total": int, "value": sites_shared / sites_total, "why": str}`. Z4 is scored on
  the decision (whether/how to adjust), not the date arithmetic the base already
  shares; Z2: re-using the existing exported helper counts. **Scoring of partial and
  left-out sites amended 2026-10-12 (below, "T0 completeness levels"); the per-site
  booleans are replaced by three levels.**
- `interface` (t0): `{"score": 1–5, "why": str}`: parameters for the real variation, no
  speculative options, the preserved inconsistencies made explicit.
Output: one JSON per packet, `work/review3/scores/<id>.json` (second judge `scores2/`),
with the keys its `questions.json` lists; scores `{"score", "why"}`, flags
`{"value", "where"}`. Study 2's abbreviated shape (`[score, why]`, `bp`/`db`/`wm`) is
tolerated; out-of-range values are errors.

**Batches.** ONE seeded shuffle (seed 20261011) of every packet id, all four arms and
F together, cut in batches of at most 12 (`work/review3/batches.json`: `pool`, `main`,
`second`); no per-arm or per-session batch. At most ONE packet per chain in a batch
(amended 2026-10-11, review of Task 7): first fit in shuffled order, each packet into
the first open batch holding no packet of its chain, so an RC chain's *t0* and
*chain_full* packets, or a chain's chain and step packets, are never side by side. Second judge: a seeded 25 % of t0 packets
and 15 % of the rest (seed + 1), shuffled and batched the same way.

**Reliability, before any comparison.** Quadratic-weighted kappa (own implementation, as
study 2) for the 1–5 scores, `interface` and `completeness` (in quarters); Cohen's kappa
for `t2_reuse`, `one_place`, `disguised_duplication`, `bypasses_abstraction`,
`would_merge`, `abstraction_drift.value`. The analysis script prints and writes kappa
first (`out/study3/design-kappa.json`, the flat `{measure: kappa}` JSON that
`aa tables3 --kappa` reads; `aa tables3` also accepts the script's full result JSON and
rejects a file with no judged measure) and refuses the labels and comparisons until the
second judge has scored every packet of the planned second sample (`batches.json`
`second`; amended 2026-10-11, before: refused only when no packet had a second
judgement, and the labels were written before the check).

**Labels for the tables.** First judge only, `out/study3/design-labels.json`, the
`aa tables3 --labels` input keyed `<agent>/<arm>/<zone>/<chain>/T<k>` (`T0` for RC's
T0) with `t2_reuse`, `one_place`, `completeness`, `interface`, plus the design scores
and flags; chain packets under `.../chain` and `.../chain_full`.

**Analysis (H1).** Per agent, each lever arm (RG, RL, RC) vs R (confirmatory) and vs F
(descriptive closeness), on chain packets; primary **maintainability** of the T1–T4
chain diff (RC from its T0 tree), secondary the other scores, `duplicated_blocks` and
the drift / disguised-duplication flags; RC's T0..T4 packet vs R secondary. All zones and
without Z4 (pre-declared weak); RL's confirmatory scope the non-blind zones Z1 + Z3
(amendment 2026-10-11). Mann-Whitney + per-zone sign test; ordinal mixed model with zone
and chain random effects if it fits (not in the script yet; if added, added before any
score is read).
Step packets by step and arm, descriptive. Nothing near p = 0.05 is read as an effect
on its own.

### T0 completeness levels (amended 2026-10-12, after the study-3 pilot, before any T0 packet is judged)

Spec amendment 2026-10-12b, item 8. No study-3 packet had been exported or judged when
this was written; the examples below were taken from the pilot's T0 diffs (analyst
reading, no judge score) and are described by what the code does, not by who wrote it.
The judge is still not told arms, agents, hypotheses, probe results or that arms exist.

**What a site's decision is.** The zone's `decision` and each site's `decides` text in
`sites.json`. A site's own data handling is *not* part of the decision: reading its own
fields (the same setting may be named differently at different sites), converting its own
formats (a day string to a date and back), awaiting or not, logging. A variation that
exists only at that one site in the original code (an option no other site has) may stay
at the site.

**Levels, per site** (`per_site`: `{site id: "full" | "partial" | "none"}`):
- **full (1)** — every element of the site's decision is taken by the shared definition;
  the site only passes its own data, plus at most an explicit argument that selects a
  variation the definition names (a preserved inconsistency made explicit).
  Examples: every month-wide budget action takes its category set from one selection
  function, with a parameter for the hidden-category rule, and the sign of an average
  from one function. Each ranged-amount site calls the existing exported amount helper
  with the raw value (missing, number or range), and the one site that rounds
  differently calls it with an explicit rounding-mode argument. Each date site passes its
  own schedule's enable flag and mode, under its own field names, to one function that
  decides whether and how to move the date.
- **partial (0.5)** — the site calls the shared definition, but still decides part of the
  decision itself: a filter, condition, branch, dispatch or flag computation that the
  shared definition takes, or should take, for the other sites. Anchors:
  - the shared category selection is called with "exclude hidden", but the query that
    feeds the site still filters hidden categories and hidden groups in its own SQL, so
    the hidden rule is still decided there (twice);
  - the date site calls the shared weekend function, which now takes the enable flag,
    but keeps its own outer `enabled ? adjust(…) : date` ternary around the call;
  - the shared function covers only the range arithmetic; each site keeps its own
    `missing ? 0 : number ? value : shared(range)` dispatch, while the decision includes
    the missing and numeric cases (and an existing helper decides all three);
  - one caller computes the flag the shared function decides on with its own expression
    (its own strict comparison combined with another option), where the other callers
    pass their raw field, so "whether the rule applies" is still settled differently at
    that site.
- **none (0)** — the site still decides locally (does not call the shared definition for
  the decision, or calls it only for something that was already shared), or it was not
  touched. Anchors: a refactor that converts two of five provider functions and leaves
  three as they were (the three are none); a site deliberately left out to keep a
  registered inconsistency ("unifying it would change results") is **none**, with the
  reason recorded (`left_out`); the same inconsistency carried as an explicit parameter
  of the shared definition is **full**.

When a site is between two levels, choose the lower one and say why in `why`.

**Value.** `completeness = (n_full + 0.5 × n_partial) / sites_total`. Output:
`{"per_site": {id: level}, "left_out": {id: "preserve_inconsistency" | "missed" |
"other"}, "sites_full": int, "sites_partial": int, "sites_total": int, "value": float,
"why": str}` (`left_out` lists only sites scored none that the diff did not route through
the definition). Legacy booleans (`true` = full, `false` = none) are still read. Reported
beside the primary (0.5): partial counted as 1 (lenient) and as 0 (strict), descriptive.

**Behaviour changes.** A T0 that changes behaviour (probe minus exclusions changed, or a
preserved inconsistency unified) is scored on its design like any other T0; the judge is
not told the probe result and does not mark completeness down for behaviour (measured by
the probe and inconsistency tests). It is **flagged** in the tables (`t0_probe_changed`,
`t0_inconsistency_unified`, from the step's `result.json`), and an exploratory completeness
over unflagged T0s is shown beside the primary. Example of a flagged T0: the shared
weekend function gained a default that turns the rule on when a caller's flag is absent,
so schedules without the flag started skipping weekends.

**Reliability.** As registered: quadratic-weighted kappa on `completeness` in quarters,
before any comparison; plus, descriptive, Cohen's kappa on the three levels over the sites
of the double-judged T0 packets.

### Judge copy of the rubric (2026-10-18, before any study-3 packet is judged)

The study-3 judges read `docs/design-review-rubric-judge-copy.md` (copied to
`work/review3/judge-rubric.md`), not this file: this file names the arms, the hypotheses
and the measures they feed, which the judges must not see. The copy holds the five
scores, the flags, the new questions and the T0 completeness levels word for word, with
the arm-revealing asides removed ("primary H2 measure", "so that it does not mark RL",
"registered" inconsistency → "listed as one to preserve", "zone's decision" →
"`decision` in `sites.json`") and the packet kinds named by what they contain (rule
change, several changes, refactor). Batches, second judge, output paths and analysis are
as above.
