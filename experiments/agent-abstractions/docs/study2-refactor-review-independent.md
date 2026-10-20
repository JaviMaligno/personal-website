# Study 2 R/F refactor: independent review

Reviewer: a separate agent that did not write or implement the refactor. Read only
`substrate/patches/study2/r.patch`, `substrate/patches/study2/f.patch`,
`docs/study2-variants.md`, and the base code they touch in `work/actual-base`
(Actual `9732a446`, `packages/loot-core/src`; paths below are relative to it). Did not
read `tasks2/`, the author's review, or the spec/plan. The patches are unchanged since
the `rf-frozen` tag (`git diff rf-frozen HEAD -- substrate/patches/study2` is empty);
nothing was modified.

Questions, per zone: (a) is F what a competent maintainer would extract; (b) is R a fair
representation of the repeated form, not a straw man in either direction; and overall,
(c) do F's doc comments give F an unfair advantage.

## Summary

| Zone | Verdict | Main caveat |
|---|---|---|
| Z1 bulk budget categories | **pass-with-caveat** | `skipMissingGroup` and its comment state a NULL-semantics inconsistency that R leaves implicit in SQL |
| Z2 scheduled amount | **pass-with-caveat** | R is artificial (declared) and still has the helper; F's `rangeRounding` keeps a probable paren bug in a public API |
| Z3 bank-sync account linking | **pass** | helper doc lists two caller quirks; both are already visible at the F call sites |
| Z4 weekend adjustment | **pass-with-caveat** | thin extraction; `WeekendRule` comment names the `weekendSolve` / `weekendSolveMode` trap that R does not |
| Doc-comment fairness (cross-zone) | **caveat, not fail** | F's comments state some *inconsistencies*, not only the rule; stronger than the variants doc's honesty item 8 suggests |

No zone fails. R is upstream code in Z1, Z3, Z4 and a plain, uniform inlining in Z2, so
it is not a straw man. F is a reasonable extraction under the hard constraint of
identical behaviour; where F looks unlike what a maintainer would write, it is because
the constraint forces it to encode an upstream quirk as a named parameter, and that
naming is itself the main fairness risk.

## Z1: which categories a bulk budget action writes

**R (base, untouched).** Fair by construction: it is upstream code. The five actions
really do select categories three different ways (budget rows joined to categories in
`copyPreviousMonth`, `v_categories` in `setZero`, a `LEFT JOIN` SQL filter in the three
average actions). Not a straw man.

**F.** `getBulkBudgetCategories({ includeHidden, skipMissingGroup })` plus
`averageToBudget`. Checked against base:

- The tombstone filter matches (`getBudgetData` also filters `c.tombstone = 0`).
- `hidden` is `BOOLEAN NOT NULL DEFAULT 0` on both tables (migration
  `1685007876842_add_category_hidden.sql`), so moving `c.hidden = 0` from SQL to
  `cat.hidden === 1` in JS has no NULL edge for the category itself; the only NULL is
  `group_hidden` from a missing group row, which is exactly what `skipMissingGroup`
  covers. Correct.
- `averageToBudget` is a sensible, natural extraction (the sign inversion was copied
  twice).

Would a competent maintainer write this? Mostly yes; one category-selection helper for
"bulk actions" is the obvious extraction. Two points where a maintainer might differ:

1. `copyPreviousMonth` now runs a second query and filters its budget rows by a `Set`
   of ids. A maintainer would more likely extract a row predicate
   (`isBulkTarget(row, opts)`) and apply it to whatever rows each action already has.
   F's choice is defensible (one query owns the rule) and keeps row order, but it is
   one plausible shape, not the only one.
2. `skipMissingGroup` is a parameter that exists only to preserve an accident (SQL
   `g.hidden = 0` is not true for NULL; JS `=== 1` is false for NULL). No maintainer
   would introduce it deliberately; they would either not notice the difference or
   fix it. It is forced by the equivalence requirement, so it is acceptable, but see
   the caveat.

**Caveat (fairness).** This is the largest information asymmetry in the treatment. In
R the missing-group difference is invisible unless the reader reasons about NULL
semantics across a SQL `LEFT JOIN` and a JS strict comparison. In F it is a named
boolean at every call site plus a comment: "`skipMissingGroup` also skips a category
whose group row does not exist: the average actions have always done so, copy last
month has not." Any task whose correctness hinges on missing-group categories is
handed to F and hidden from R. `includeHidden: true` for `setZero` is much less of an
asymmetry (in R, `setZero` visibly lacks the hidden check).

**Minor doc inaccuracy.** "set to zero writes every category" is not quite true: it
still skips income categories outside tracking budgets (the preceding sentence says
so, so it is imprecise rather than wrong).

Verdict: **pass-with-caveat**.

## Z2: scheduled amount of a ranged schedule

**R (artificial, declared).** The four loot-core calls to `getScheduledAmount` are
inlined as the same ternary; no base call passed `inverse`, so nothing is lost; the
`normalizeSchedule` copy drops the null branch, which is correct because `amountValue`
is checked non-null three lines earlier. The template's own copy is untouched. As a
"repeated" form this is fair: the copies are textually uniform, readable, and not
obfuscated. If anything R is generous: each inlined site carries a new one-line
comment ("a ranged ... amount is scheduled at its rounded midpoint"), which upstream
would not necessarily have. Two things weaken the R treatment rather than strengthen
it, both already disclosed (honesty item 3): the helper is still exported and used by
five desktop-client files, so an R agent that greps the name finds it; and R is the
only zone where the repetition is not upstream's.

**F.** All five sites call the helper, which gains
`rangeRounding: 'roundedMidpoint' | 'halfOfRoundedSum'`. The template's base expression
`Math.round(num1 + num2) / 2` looks like a misplaced parenthesis (`Math.round((a+b)/2)`
elsewhere); the comment in F correctly notes the half unit is rounded later
(`scheduleAmount = Math.round(scheduleAmount)` after the adjustment), so the effect is
on the adjustment input only. A competent maintainer unifying these would most likely
fix the template to use the default rounding and accept the tiny behaviour change, or
leave the template's copy alone; adding a named mode for the quirk to an exported,
widely used API is not a natural move. Under the equivalence constraint it is the
least bad option and is honestly named. The call `getScheduledAmount(value, false,
'halfOfRoundedSum')` with a positional boolean is slightly awkward but idiomatic for
this codebase.

**Equivalence nit (not covered by the variants doc).** When a schedule's rule has no
amount condition (`extractScheduleConds` returns `amount: null`; the helper's own
comment says the condition can be deleted), the template throws in both variants but
with different messages: base reads `amountCondition.op` ("reading 'op'"), F reads
`amountCondition.value` ("reading 'value'"). For a null `.value` (condition present,
value missing) base yields `null` and F `0`, which round to the same final amount
through both adjustment paths. The variants doc says the probe records thrown errors
as results; it does not list a missing-amount-condition template case, so this
difference is probably unprobed. Low impact (an error string), but it contradicts "R
and F behave identically" in a narrow sense.

**Caveat (fairness).** F's helper comment states both rounding modes and which caller
uses which; F's template comment explains the half unit. In R the template's divergent
rounding is visible in code but uncommented, and R's added comments describe only the
default rule. A task about ranged amounts in templates is easier to reason about in F
partly because of prose, not only shape.

Verdict: **pass-with-caveat**.

## Z3: linking a bank-sync provider account

**R (base, untouched).** Five near-identical upgrade-or-insert / sync / notify blocks
in one file, as upstream wrote them. Fair; this is the most convincing natural
repetition of the four zones.

**F.** `linkBankSyncAccount` is exactly what a competent maintainer would extract:
provider functions keep their provider-specific bank lookup (and PluggyAI its file id),
and the shared tail moves into one function. Checked against base:

- `offBudget` defaults to `false` in every provider (base lines 176-474), so making it
  required in the helper is safe.
- Insert key order is preserved by the spread (`id`, then `account_id`, `mask` (GoCardless
  only), `name`, `official_name`, then `bank`, `offbudget`, `account_sync_source`), and
  the update keys are unchanged.
- `syncAccount`'s 8th parameter is an optional `fileId?: string` with no `arguments` /
  rest use, so passing `undefined` explicitly equals omitting it.
- Dropping Enable Banking's `id == null` check is correct (unreachable).
- `bank` typed as `Awaited<ReturnType<typeof link.findOrCreateBank>>` is honest.

**Caveat (minor).** The helper's doc comment names caller-specific quirks ("`fileId`
is passed ... only by PluggyAI; Akahu reports only `transactions` as changed"). A
helper's doc describing its callers is mild narration, and it is information R does
not have in prose. The advantage is small: in F both quirks are explicit arguments at
the one call site that uses them, and in R the Akahu `tables` and PluggyAI `fileId`
lines are visibly different in otherwise identical blocks.

Verdict: **pass**.

## Z4: weekend adjustment of schedule dates

**R (base, untouched).** Fair, and if anything it understates repetition: base already
shares the arithmetic (`getDateWithSkippedWeekend`), so only the 3-line decision
(`skip ? adjust(date, mode) : date`) and, in the template, the string/date round trip
are repeated (honesty item 2). Not a straw man; the template's two 8-line copies inside
one loop are real duplication.

**F.** `WeekendRule`, `applyWeekendRule(date, rule)`, `applyWeekendRuleToDay(day, rule)`.
Checked: `skipWeekend: data.skipWeekend && !noSkipWeekend` reproduces `getNextDate`;
`applyWeekendRuleToDay` returns the day unchanged (including `null`) when the rule is
off and calls `_parse` on the day otherwise, exactly as base does; types line up.

Would a competent maintainer extract this? For the template's two identical blocks,
yes. For `getNextDate` and `getUpcomingDates`, wrapping a one-line ternary in a call
that builds an object literal is break-even at best, and it introduces a third name
for the mode (`solveMode`, alongside `weekendSolve` and `weekendSolveMode`). A
maintainer could equally have pushed the "skip or not" flag into
`getDateWithSkippedWeekend` itself. So F is a plausible but thin abstraction; the
contrast between R and F in this zone is small by construction, which should temper
any Z4 effect size.

**Caveat (fairness).** The `WeekendRule` comment states the zone's main trap outright:
"the recurrence config calls the mode `weekendSolveMode`, the parsed schedule
`weekendSolve`". The variants doc's own probe-power table shows that confusing these
two fields is the single most consequential edit in the study (46 differing cases). In
R that fact must be discovered by reading two types or two call sites. This is a rule
stated in F and absent in R.

**Minor doc imprecision.** `applyWeekendRule`'s comment does not mention that
`getDateWithSkippedWeekend` throws when the date is a weekend and `solveMode` is
missing, which the optional `solveMode?` type now permits.

Verdict: **pass-with-caveat**.

## Do F's doc comments give F an unfair advantage?

Partly, yes. The variants doc's honesty item 8 frames this as "F's helpers carry
short doc comments stating the rule". That is accurate for `averageToBudget`, the main
sentence of `getBulkBudgetCategories`, `applyWeekendRule` and `linkBankSyncAccount`'s
first paragraph, which describe what the shared code does (normal for an extracted
helper, and arguably part of what "factoring" means). But three comments go further
and state an **inconsistency between copies**, which is the kind of fact study tasks
are likely to turn on:

| Zone | F states explicitly | Where R has it |
|---|---|---|
| Z1 | averages skip categories with a missing group; copy does not | only implicit in SQL NULL vs JS `=== 1` |
| Z2 | templates use a different rounding, and why it is harmless after adjustment | visible but uncommented code in the template |
| Z4 | the two field names for the mode | two types / call sites, no prose |
| Z3 | PluggyAI-only `fileId`, Akahu-only `tables` | visibly different lines in identical blocks (small asymmetry) |

R does get some compensating prose in Z2 (the comments added at the inlined sites),
but those state only the default rule.

Since R and F are frozen, this is a confound to carry into the analysis, not something
to fix now. Suggested handling (the reviewer has not seen the tasks, so these are
conditional):

1. For each study task, record whether its hidden tests depend on any fact in the
   table above. Report F-vs-R effects separately for tasks that do and tasks that do
   not; an F advantage confined to the first group is at least partly a documentation
   effect, not a shape effect.
2. In the write-up, describe the treatment as "factored + documented helpers" unless
   the split in (1) shows no difference.
3. If a later replication is possible, a cheap ablation is F with the inconsistency
   sentences removed (keeping the rule sentences), or R with the same sentences added
   as comments at the copies.

## Other notes

- The variants doc says the earlier review was a "separated second pass" because no
  independent agent was available; this document is the independent pass and agrees
  with that review's conclusion that all four zones are usable, with the fairness
  caveats above made more specific.
- The Z2 thrown-message difference is the only behavioural divergence found; it is
  outside what the stated equivalence checks list as covered.
