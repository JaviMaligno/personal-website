# Study 2 results — repetition (R) vs abstraction (F) over task chains

Run 2026-10-09 21:26 → 2026-10-10 18:30. Three agents at effort medium: Claude Code
(`claude-sonnet-5-5`), Codex (`gpt-6-luna`), Claude Code (`claude-haiku-5-5`).
4 zones × 2 conditions × 8 chains × 4 steps = 256 steps per agent, **768 steps, all
evaluated, 0 eval errors**; 2 agent timeouts per agent (counted as not correct).
Spec: `docs/specs/2026-10-08-repetition-vs-abstraction-design.md`. Registered tables:
`out/study2/tables2.md` (`aa tables2`). Exploratory measures: `out/study2/secondary.txt`
(`scripts/study2_secondary.py`). Run incidents: `docs/study2-run-log.md`.

Every anomaly below was explained by reading the agents' transcripts and diffs before
being interpreted (five independent trace readers; evidence quoted in §5).

**Correction (2026-10-18, from study 3).** The T2 label of this study could not say
`helper` in R (`chain_eval.T2_LABELS = {"F": "helper", "R": "copy"}`: a call to a helper
the agent made at T1 was never checked), so "the T2 consumer is a copy in R" was built
in. Study 3's trace read (`out/study3/trace-reads/D-r-base-reuse.md`) found the same
behaviour in study 2's R runs that study 3 labels `helper`: e.g. all 8 Haiku Z1 chains
call the helper Haiku created at T1, and Z2 T2 calls the existing `getScheduledAmount` in
most chains. "Agents in R extend the repeated pattern" holds for the judged diffs
(§7) but overstates copying in Z1, Z2 and Z4; Z3 is copy for every agent in both studies.
The registered H1–H4 results above are unaffected.

## 1. Measurement fix before analysis

jscpd 5.4 reports bare basenames (`actions.ts`), and the parser compared them with full
paths, so every clone was dropped and duplication read 0 everywhere, including the R
starting trees that are duplicated by construction. Fixed in `f65078b` (basename resolved
against the scanned file list; 0 ambiguous names in runs2) and re-read from the reports
already on disk (`rescan_duplication`); no agent or evaluation re-run.

**Usage re-parsed (2026-10-12, after this report was first written).** The study-3 pilot
found that the transcript parser kept only the last `result` event of a Claude Code
stream, so a step in which background tasks woke the agent again recorded only its last
segment's tokens and turns; and a Codex step killed before `turn.completed` recorded 0
tokens instead of missing (study-3 spec, amendment 2026-10-12, items 2-3). `aa chain
reparse --runs runs2` re-derived 16 of 512 Claude-engine steps (summed over every
`result`) and 3 Codex steps (now missing), with a record per step in result.json
(`rederived`) and `runs2/rederive-log.jsonl`; no agent or evaluation re-run. The tables
were regenerated (`d13930c`), and the H2 token row, the H2 bullet and §6 point 5 below
now give the re-parsed values. Before the re-parse they read: Sonnet 324k vs 299k
(p=0.57), Codex 578k vs 569k (p=0.53), Haiku 1.18M vs 1.04M (p=0.028), and Haiku turns
25.5 vs 22 (p=0.043). After it: Sonnet 336k vs 331k (p=0.85), Codex 578k vs 578k (F n=125,
3 missing; p=0.76), Haiku 1.18M vs 1.07M (p=0.126), Haiku turns 26 vs 23 (p=0.171). Cost
growth (T4 / T1 tokens per chain) moved for Sonnet (R 0.738 → 0.875, F 0.761 → 0.698) and
Haiku F (0.64 → 0.536). "H2 not supported" is unchanged, and stronger: no token difference
is near threshold any more.

## 2. Pre-registered hypotheses

| | Claude Sonnet | Codex | Claude Haiku |
|---|---|---|---|
| **H1** missed copy T1+T3, R vs F | 6% vs 2% | 28% vs 22% | 5% vs 0% |
| mixed logistic, F (log-odds, sd) | −1.59 (0.82) | −0.65 (0.38) | −2.39 (1.12) |
| **H2** lines added / step (median) | 43 vs 41.5, p=0.27 | 56.5 vs 58, p=0.65 | 104 vs 106.5, p=0.19 |
| **H2** tokens / step (median) † | 336k vs 331k, p=0.85 | 578k vs 578k, p=0.76 (F: 3 missing) | 1.18M vs 1.07M, p=0.13 |
| **H3** dup. lines T0 → T4 (mean) | R 138→163, F 88→93 | R 138→156, F 88→94 | R 138→154, F 88→93 |
| **H3** F × step, duplication | −6.3 (1.3), p<0.001 | −4.1 (1.1), p<0.001 | −4.0 (1.3), p=0.001 |
| **H4** maintainability, step diffs R vs F | 3.69 vs 4.07, p<0.001 | 3.26 vs 3.61, p<0.001 | 4.24 vs 4.38, p=0.07 |
| **H4** maintainability, chain diffs R vs F | 2.94 vs 3.56, p<0.001 | 2.59 vs 2.97, p=0.10 | 3.72 vs 4.09, p=0.007 |

† Re-parsed usage (§1, 2026-10-12); the first version of this row was computed with the
under-counted usage.

- **H1: direction supported in all three agents, no single agent conclusive.** Each
  agent's F coefficient is 1.7–2.1 sd below 0. Pooled over agents (exploratory, not
  registered: agent and zone fixed, chain random) F = −1.06 (sd 0.33). The registered
  null reading does not apply (R is not ~0), but the rival ("agents grep every copy")
  holds for Sonnet and Haiku most of the time: their absolute rates are ≤6 % in R.
- **H2: not supported.** No difference in lines or tokens. Haiku's F median is lower in
  4/4 zones (sign test p=0.125), but with the re-parsed usage (§1) its token difference is
  p=0.126 (first version, under-counted: p=0.028, then the only one near threshold) and
  its turns p=0.171 (was 0.043). Where the direction comes from (§5.5): R needs one edit
  per inlined copy and more reads before writing a new consumer.
- **H3: duplication supported; carried defects not as registered.** R accumulates
  duplicated lines along the chain, F barely does, in all three agents. The registered
  carried-defects measure turned out to count the *same* unfixed failure again at every
  later step (§4.2); true regressions are almost absent in both conditions.

## 3. Correctness (registered measure, read across agents)

| | R | F | Fisher |
|---|---|---|---|
| Sonnet | 111/128 (87%) | 126/128 (98%) | p < 0.001 |
| Codex | 83/128 (65%) | 84/128 (66%) | p = 1.00 |
| Haiku | 122/128 (95%) | 126/128 (98%) | p = 0.28 |

Timeouts count as not correct (§4.6; the first version counted timed-out steps whose
hidden tests passed: Sonnet R 113, Codex F 85, Haiku R 123 and F 127, Fisher p = 0.002,
0.90, 0.21).

Pooled (exploratory) F = +0.75 (sd 0.19); without Codex +2.20 (sd 0.51) (refitted on the
registered counts, §4.6). The Sonnet gap
is concentrated in Z2 (R 66 % vs F 94 %) and has a mechanism not captured by the
registered missed-copy measure (§5.4): in R, the consumer added at T2 gets attached to the
wrong copy (the display helper) or becomes a new copy, and the T3 rule change routes
around it.

## 4. Measures that need a caveat

1. **Registered missed copy excludes total misses** ("zero consumers updated is simply
   incorrect", §5.2). Kept as registered. The exploratory "any pre-existing consumer fails"
   gives: Sonnet R 6 % vs F 2 %, Codex 48 % vs 45 %, Haiku 5 % vs 0 %. The Codex gap
   between registered (28/22 %) and this (48/45 %) is Z4 and part of Z2: total misses.
2. **Carried defects ≠ regressions.** Codex T4: R 103 of 107 failing earlier tests never
   passed at their own step; F 100 of 116 (the other 16: one T3 schema crash taking down
   T1/T2 tests). Chains with any true regression: Sonnet 0/32 vs 0/32, Codex 1/32 vs 2/32,
   Haiku 0/32 vs 0/32. The registered F × step coefficient for carried defects (Sonnet
   −0.77, Codex +0.91, Haiku −2.18) mostly measures persistence of an early failure.
3. **Z4 consumer labelling.** `tasks2/Z4/T1/consumers.json` maps the budget-template test
   to consumer `next-date`, but it checks the separate `schedule-template.ts` copy. It
   changes attribution (Codex Z4 failures show as total misses, not missed copies), not
   correctness. Z4 was already marked weak contrast.
4. **`turns` was unreliable for Claude Code runs that use background tasks** (e.g. Haiku
   F/Z1/0/T1: turns=2, 27 tool calls): the parser read only the last `result` event.
   Fixed by the re-parse of §1 (that step now has 29 turns); tool calls remain the safer
   count.
5. **One Codex step would be `infra` under study 3's run-status rule.** `runs2/codex/F/Z2/0/T1`
   ended `ok` with exit 1, `correct = true` and no recorded usage, its transcript ending in
   `workspace routing discovery timed out` reconnects and `turn.failed`. The study-3 rule
   (spec of study 3, amendment 2026-10-12) classifies a transcript that ends in transport
   errors as `infra` and re-runs it; study 2 keeps its registered classification, so the
   two studies treat this situation differently (pending confirmation). Sensitivity with
   that chain's four steps excluded (as study 3 would until the re-run): Codex F correct
   82/124 instead of 84/128, registered missed copy 13/62 instead of 14/64.
6. **Correctness counts and timeouts.** The table of §3 counted the `correct` field of
   every step, so 4 timed-out steps whose hidden tests passed (Sonnet R 2, Codex F 1, Haiku
   R 1 and F 1; one Codex F timeout was incorrect) counted as correct, against this
   report's own rule (timeouts are not correct, as in `out/study2/tables2.md`). §3 now
   gives the registered count; the first version's counts are kept beside it. The pooled
   coefficients below the table were refitted on 2026-10-12 with the same model
   (`scripts/study2_secondary.py`, which now uses `tables2.is_correct`; same
   `BinomialBayesMixedGLM`, agent and zone fixed, chain random): 3 agents F = +0.80
   (sd 0.20) → +0.75 (sd 0.19); without Codex +2.52 (sd 0.59) → +2.20 (sd 0.51). Same sign,
   both still ~4 sd above 0; no conclusion changes.

## 5. What the traces show

### 5.1 Codex Z4 (T1 and T3 fail 8/8 in both R and F) — agent behaviour, not an artifact
Codex changes only `getNextDate` in `shared/schedules.ts` ("The logic is centralized in
`getNextDate`"), runs `schedules.test.ts` (65 passing) and stops. It never touches the
budget template's own weekend loop (`schedule-template.ts`, 0/16) and leaves
`getUpcomingDates` in 12/16. Failing assertion every time:
`expected 30000 to be 22000` (template still counts moved-to-Monday occurrences).
Sonnet and Haiku pass the same hidden tests in the same harness. The statement describes
a product-wide rule and the symptom ("falls on that day two or three times"); a
"next date only" reading is weakly defensible at most. The F helper returns a `Date` and
cannot express "drop this occurrence", so every caller must change in both variants: the
abstraction offers no help here, consistent with R ≈ F.

### 5.2 Codex Z2 — same missed consumer, different mechanism by condition
The missed consumer is almost always the budget template (`createScheduleList`).
- **R: never located.** Codex greps the shape of the copies it knows
  (`"rounded midpoint|num1 \+ .*num2|normalizeSchedule"`); the template's copy is written
  differently and never appears.
- **F: located and deliberately excluded.** The helper's named mode
  `rangeRounding: 'halfOfRoundedSum'` (the preserved inconsistency) reads as protected
  behaviour: "…while preserving the separate midpoint estimate used by budget templates";
  chain 2 even added a test asserting the old value. The abstraction made the copy
  visible, and its named exception made it look intentional.
- T3 adds a second failure: the operator must be threaded to every call site and Codex
  often reads "for planning" as excluding posting ("Posting and preview transactions use
  the nominal amount, so I'll keep those unchanged"). T3-posting is ambiguous in the
  statement and is flagged as such.

### 5.3 Codex Z1 F (T3 fails 4/8 vs R 1/8) — unrelated to the helper
Three chains invent a `category_groups.notes` column (migration + AQL field) instead of
the existing `notes` table (`SqliteError: no such column: _.notes`); one joins the right
table but never selects the note. All F chains put the rule in the right layer (the shared
filter). R's single failure is the same invented column. n=8: read as chance.

### 5.4 Sonnet
- Missed copies in R are search failures: `grep -rn "isbetween"` misses copies without
  that word; a `| head -30` cut the template out; in Z1 a scripted replacement
  (`assert s.count(sel_old)==3`) skipped the one copy with its own query, while the summary
  claimed it had been fixed. The single F miss: a grep excluding the caller's own file.
- R Z2 T3 failures (5/8): the T2 API consumer was wired to `getScheduledAmount`, the
  leftover display helper nothing else in loot-core calls (4 chains), or to a private
  fifth copy (1 chain); T3 then moved the real copies to a new planning helper and left
  the API on the old one ("Callers that don't pass `op` behave as before").
- R Z3 T2 (2/8): the new provider was cloned from Akahu, the one provider that differs,
  inheriting its notification `tables: ['transactions']` instead of
  `['transactions','accounts']`.

### 5.5 Haiku
- R misses: the template was listed by a broad grep and then dropped from a hand-picked
  list ("The midpoint is computed in four places"); at T3 its search terms could not match
  the template; Z4 T3 fixed the daily branch of `getUpcomingDates` but not the weekly one.
- F/Z2/0/T3: its own T2 had written a private copy in `api-models.ts`
  (`t2_reuses_logic: reimplements`), which T3's grep could not find.
- Token gap: Z2 T1 edits 12.5 vs 5.2 per step (one Edit per inlined copy plus imports);
  Z2 T2 reads 11.4 vs 7.0 (reading the scattered copies to infer the rule).

## 6. Reading

1. **Repetition hurts mainly through search, not through judgement.** In R, misses come
   from greps that cannot match every textual variant of a copy; the agent then reports
   success. F removes that failure mode where the helper carries the rule.
2. **Abstraction has its own failure mode:** a named exception in a helper can be read as
   a protected requirement (Codex F Z2). Mild in count, but a qualitatively different
   error from R's.
3. **The cost of R appears downstream:** the new consumer added at T2 attaches to the
   wrong copy or becomes a new copy, and the next rule change misses it (Sonnet Z2, Haiku
   F/Z2/0 after it reimplemented). This is the "maintainability over time" effect, and
   the registered measures under-count it.
4. **Agent capability dominates condition.** Codex's failures (Z4, Z2) come from deciding
   the change is local after one search; they happen in both conditions at similar rates.
   Sonnet and Haiku find most copies in R; F still lowers their residual misses and
   (Sonnet) raises correctness.
5. **No efficiency effect** in lines or tokens (re-parsed usage, §1; the first version
   had Haiku's tokens near threshold, p=0.028, now p=0.126).
6. Duplication grows in R and not in F for all three agents. Agents seldom consolidate R
   on their own: chains ending with less duplication than they started with are Sonnet
   4/32, Codex 4/32, Haiku 8/32, all small (10–29 lines).

## 7. H4 — blind design review

Rubric and analysis pre-registered (`docs/design-review-rubric.md`, study 2 addendum,
`3700fef`, committed before any score). 960 packets (768 step diffs + 192 cumulative chain
diffs), Claude Opus 5.5 judges, batches of 12; second judge on a seeded 15 % (144).
Script `scripts/study2_design_review.py` → `out/study2/design_review.txt`.

Before export the packet check had to be fixed: runner and evaluator tree ids never
match by construction (the image repo excludes ~30 docs/e2e files that a fresh `git init`
includes); the check is now that the change the evaluator measured equals the agent's own
diff, true for all 768 steps (so the evaluation itself is unaffected). 30 of 1104 judge
files used an abbreviated JSON shape with the same content; normalised on load.

**Reliability** (quadratic-weighted kappa): maintainability 0.77, duplication 0.87, reuse
0.82, placement 0.73, scope 0.63; `would_merge` exact agreement 90 %.

**Maintainability (1–5), R vs F, Mann-Whitney; zones with F higher out of 4:**

| | step diffs | chain diffs |
|---|---|---|
| Sonnet | 3.69 vs 4.07, p=0.0001, 4/4 | 2.94 vs 3.56, p=0.0006, 4/4 |
| Codex | 3.26 vs 3.61, p=0.001, 3/4 | 2.59 vs 2.97, p=0.10, 3/4 |
| Haiku | 4.24 vs 4.38, p=0.07, 2/4 | 3.72 vs 4.09, p=0.007, 4/4 |

Duplication and reuse move the same way (Sonnet and Codex p<0.001 on step diffs);
duplicated blocks per step diff: Sonnet 0.75 vs 0.35, Codex 1.16 vs 0.50, Haiku 0.27 vs
0.25. `would_merge = yes` on step diffs: Sonnet 53 → 71 %, Codex 35 → 48 %, Haiku
82 → 85 %; on chain diffs Sonnet 3 → 28 %, Codex 0 → 16 %, Haiku 44 → 59 %. Placement
does not differ except Sonnet chains. Scope is slightly *lower* in F for Haiku (4.84 vs
4.66): judges cite the same unrelated import reorder in `schedules/app.ts` in most of those
packets, a variant/tooling artifact rather than a design choice.

**What the judges penalise in R** (sampled justifications of R step diffs with
duplication ≤ 3, 142 packets): agents adding one more copy, not merely touching existing
ones: "linkFintegraAccount is a ~70-line copy of linkAkahuAccount", "the hidden-category
query is pasted into setZero, making four identical copies", "getExpectedAmount is a
line-for-line copy of getScheduledAmount". Agents in R extend the repeated pattern they
find instead of introducing a helper.

**Caveats.** Blindness is partial (F's helpers are recognisable, and the R tree is visibly
duplicated); a judge may partly score the starting code rather than the change. The
per-zone sign tests never reach significance with 4 zones (best p = 0.125).

**Reading.** H4 is supported for Sonnet and Codex on step diffs and for Sonnet and Haiku
on chain diffs; Codex chains are in the same direction (p=0.10). The gap widens over the
chain for Sonnet (step 3.69 vs 4.07 → chain 2.94 vs 3.56): repeated code invites more
copies, and the accumulated change is judged worse than any single step. This is the
clearest effect in the study, larger than the effect on missed copies.
