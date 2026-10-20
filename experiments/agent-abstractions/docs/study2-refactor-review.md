# Study 2: independent refactor review (R vs F)

Spec §2 "Integrity" item 3 and plan Task 1: before freezing `rf-frozen`, someone other
than the author reads the R→F diff and the variants doc and answers *"is this a
reasonable refactor, or a straw man in either direction?"*.

## How the review was done

No separate agent could be spawned in the session that built the variants (no Agent
tool; running the experiment CLIs as reviewers is not allowed), so, as the plan's
fallback, the author did the review in a **second, separated pass** that read only:

- `substrate/patches/study2/r.patch` and `substrate/patches/study2/f.patch`,
- the R→F diff of the six touched files (regenerated from the two patches),
- `docs/study2-variants.md`,

and not the author's notes, the probe, or the reasoning that produced the patches.
This is weaker than an independent reviewer: the reviewer knows the author's intent.
Javier may want a second reviewer before the chain tasks are written; the request
below is self-contained for that.

## Request (self-contained, for any reviewer)

You are reviewing a treatment for an experiment on coding agents. Two versions of
Actual Budget's `packages/loot-core` (base `9732a446`) are given to agents, who then do
chains of feature tasks in them:

- **R (repeated):** some domain logic exists as N near-identical copies, as it does
  upstream (one zone, Z2, had its shared helper inlined at its callers on purpose).
- **F (factored):** each zone's copies replaced by one helper. Behaviour must be
  identical, so inconsistencies between the copies are kept via explicit parameters.

Read `substrate/patches/study2/r.patch`, `substrate/patches/study2/f.patch` (both
apply to base + `lint-script.patch`) and `docs/study2-variants.md`. Answer, per zone
(Z1 bulk budget categories, Z2 ranged scheduled amount, Z3 bank-sync account
linking, Z4 schedule weekend rule):

1. Is F's helper what a competent maintainer of this codebase would extract (name,
   placement, signature, size), or is it over-engineered, under-factored, or shaped to
   make the experiment's later tasks easy?
2. Is R a fair "repeated" codebase, or a straw man (copies made worse, harder to find,
   or more numerous than natural)? For Z2, is the inlining what a developer copying
   the helper would plausibly have written?
3. Do the inconsistency-preserving parameters look like plausible code, or do they
   telegraph the experiment? Would a maintainer keep them, or would they fix the
   inconsistency (and does keeping them bias either condition)?
4. Do any comments or names leak the study (copy counts, "zone", "factored", hints
   about future tasks)?
5. Any behaviour difference between R and F you can see from the diff?

Verdict per zone: **pass** / **fix needed** (with what to change).

## Review (second pass, 2026-10-08)

Read: `r.patch`, `f.patch`, the R→F diff (`work/study2/review/r-to-f.diff`, 939 lines)
and `docs/study2-variants.md`. Nothing else.

### Round 1

**Z1 (bulk budget categories).** F: one query plus the rule in a filter, two flags.
`includeHidden` reads naturally (set to zero is the odd one out, visible at its call).
`skipMissingGroup` is obscure but documented as historical behaviour of the average
actions; a maintainer preserving behaviour in a pure refactor would keep exactly this,
and fixing it would be a behaviour change, out of scope for the treatment.
`averageToBudget` is a two-line helper used by `set3MonthAvg` and `setNMonthAvg`;
fine. `copyPreviousMonth` now runs `getBudgetData` (which still joins categories) and
the helper, a redundant read a maintainer might later trim; harmless. R = upstream
code, not a straw man. *Comment issue:* "writes, in one place" describes the refactor,
not the domain. **Fix needed (comment).**

**Z2 (ranged scheduled amount).** R: the inlined ternary is what a developer copying
the helper writes; the null branch dropped in `normalizeSchedule` because the value is
checked two lines above is a realistic local simplification. The R copies carry a
short comment each ("rounded midpoint"), which also makes them greppable by the same
phrase; that slightly favours R on discoverability, a conservative direction for H1.
The helper staying exported for desktop-client is declared. F: extending the existing
helper with a third parameter keeps desktop-client's calls intact; the positional
`false` before the string is a little awkward but is the minimal compatible change.
The doc's argument that the template's `op` dispatch and the helper's type dispatch
agree on validated rules is sound (`Condition` asserts both). **Pass.**

**Z3 (account linking).** F: a textbook extract; provider functions keep only what
differs (bank key, PluggyAI file id, GoCardless columns, Akahu's tables). The
`newAccount` spread keeps each provider's key set. Dropping Enable Banking's
unreachable `id == null` check is what a maintainer would do. *Comment issue:* "the
same way for every provider" again narrates the refactor. **Fix needed (comment).**

**Z4 (weekend rule).** F: `applyWeekendRule` plus a day-string adapter; callers map
`weekendSolve` / `weekendSolveMode` and `noSkipWeekend` explicitly. Reasonable and
small. *Issues:* the type comment says "in one place for every caller" (narration); and
`applyWeekendRuleToDay` is typed `string` while its comment says the day may be null
(it can be: `getNextDate` returns null when there is no occurrence). R = upstream, with
the arithmetic already shared (declared in the honesty list). **Fix needed (comment,
type).**

**Leaks.** No mention of zones, copies, the study or future tasks in either patch.

**Behaviour.** No difference visible in the diff; the doc's Equivalence checks (suite + probe)
cover what reading cannot.

**Residual bias (not fixed, recorded).** F's helpers have explanatory doc comments
(that is what extraction produces), while R's upstream copies have none. An agent in F
reads the rule stated once in prose; in R it must infer it from code. This is part of
what "factored" means in practice, but it is a second difference besides shape; it
should be mentioned when the results are interpreted.

### Round 2 (after fixes)

Changed hunks only (round-1 vs round-2 diff): the three comments no longer narrate the
refactor ("in one place", "the same way for every provider", "for every caller"), and
`applyWeekendRuleToDay` is typed `string | null` with the null case explained.
Typecheck and the repo formatter (oxfmt) pass on F. Leak scan of both patches for
`zone|study|factor|in one place|copies|experiment`: no hits.

**Verdict: pass on all four zones** — reasonable refactor in F, R not a straw man; one
artificial repetition (Z2) and one residual bias (helper doc comments) declared.
