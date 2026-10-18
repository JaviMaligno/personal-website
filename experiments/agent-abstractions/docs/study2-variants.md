# Study 2 variants: R (repeated) and F (factored)

Spec: `docs/specs/2026-10-08-repetition-vs-abstraction-design.md` §2. Plan: Task 1.
Base: Actual `9732a446`, `packages/loot-core` (paths below are relative to
`packages/loot-core/src`).

Both conditions start from base + `lint-script.patch` (`lint` = `tsgo -b`, as in study
1's A). Then:

- **R** = `substrate/patches/study2/r.patch`: base as it is, except Z2, where the
  shared amount helper is inlined at its four loot-core call sites (the only
  artificial repetition; declared below).
- **F** = `substrate/patches/study2/f.patch`: each zone's copies routed through one
  helper (Z1, Z3, Z4 new; Z2 the existing helper, extended so the hand copy can use it).

The treatment changes only the *shape* of the code. Every inconsistency between the
copies is kept in F through an explicit helper parameter, so R and F (and base) behave
identically; the Equivalence section lists how that was checked.

## Z1: which categories a bulk budget action writes

Copies (5): `server/budget/actions.ts` `copyPreviousMonth`, `setZero`, `set3MonthAvg`,
`set6MonthAvg`, `set12MonthAvg` (plus the sign inversion in `setNMonthAvg`, which the
6/12-month actions call per category).

**R form (base).** Each action selects its categories itself:
- `copyPreviousMonth` iterates last month's budget rows (joined to categories), skips
  income categories outside tracking budgets, skips `hidden === 1 || group_hidden === 1`.
- `setZero` reads `v_categories` (every non-deleted category) and skips only income
  categories outside tracking budgets.
- `set3/6/12MonthAvg` each run the same SQL (`c.hidden = 0 AND g.hidden = 0` through a
  `LEFT JOIN` on the group) and skip income categories outside tracking budgets.
- `set3MonthAvg` and `setNMonthAvg` each invert the sign of the average for expense
  categories (`is_income === 0`).

**F helpers** (same file, module-private):

```ts
async function getBulkBudgetCategories({ includeHidden, skipMissingGroup }: {
  includeHidden: boolean; skipMissingGroup: boolean;
}): Promise<BulkBudgetCategory[]>      // { id, is_income, hidden, group_hidden }
function averageToBudget(category: Pick<DbCategory, 'is_income'>, average: number): number
```

One query (`categories LEFT JOIN category_groups`, non-deleted), then the rule in JS:
income only in tracking budgets; hidden category / hidden group skipped unless
`includeHidden`. The five actions call it; `copyPreviousMonth` keeps iterating its own
budget rows (same order as base) and writes those whose category the helper returns.
`set3MonthAvg` and `setNMonthAvg` use `averageToBudget`.

**Preserved inconsistencies:**

| Inconsistency (base) | Preserved by |
|---|---|
| `setZero` does not skip hidden categories or categories in hidden groups | `includeHidden: true` at its call |
| A category whose group row does not exist (`group_hidden` NULL; the `category-create` handler does not check the group exists) is skipped by the average actions (SQL `g.hidden = 0` is not true for NULL) but copied by `copyPreviousMonth` (`=== 1` is false for NULL) | `skipMissingGroup: true` for the three average actions, `false` for copy |
| `set3MonthAvg` awaits each average inside one batch; `set6/12MonthAvg` fire `setNMonthAvg` per category without awaiting it (each with its own batch and its own `is_income` query) | call structure unchanged; only the category selection and the sign moved |

## Z2: scheduled amount of a ranged (`isbetween`) schedule

Copies: 4 loot-core call sites of `shared/schedules.ts` `getScheduledAmount` +
1 hand copy in `server/budget/schedule-template.ts`.

**Base** has the helper `getScheduledAmount(amount, inverse = false)` (null → 0; number
→ itself; `{num1, num2}` → `Math.round((num1 + num2) / 2)`), called from
`server/forecast/forecast-schedules.ts` `normalizeSchedule`, `server/schedules/app.ts`
`updateActions` and `postTransactionForSchedule`, and `shared/schedules.ts`
`computeSchedulePreviewTransactions`; the budget template has its own copy
(`op === 'isbetween' ? Math.round(num1 + num2) / 2 : value`).

**R form (artificial).** The helper is inlined at the four call sites as the same
ternary (`== null ? 0 : typeof === 'number' ? value : Math.round(...)`), with a short
comment at each; in `normalizeSchedule` the null branch is dropped because the value
was checked non-null two lines earlier. The hand copy is untouched. The helper stays
exported from `shared/schedules.ts` because desktop-client imports it, but nothing in
loot-core calls it in R. **This is the one repetition we created**; the other three
zones are repeated in base itself.

**F form.** All five sites call the helper; it gains one parameter for the template's
rounding:

```ts
export function getScheduledAmount(
  amount: number | { num1: number; num2: number },
  inverse: boolean = false,
  rangeRounding: 'roundedMidpoint' | 'halfOfRoundedSum' = 'roundedMidpoint',
): number
```

| Inconsistency (base) | Preserved by |
|---|---|
| The template rounds the *sum* and then halves (can leave a half unit, which survives a percent adjustment until the template's later `Math.round`); every other site rounds the midpoint | `rangeRounding: 'halfOfRoundedSum'` at the template call |
| The template dispatches on `op === 'isbetween'`, the helper on the value's type, and only the helper maps a null value to 0 | none needed: rules reaching the template are validated by `Condition` (`server/rules/condition.ts`: amount is non-nullable, `isbetween` requires a `{num1, num2}` value and every other op a number), so the two dispatches agree and null never arrives |

## Z3: linking a bank-sync provider account

Copies (5): `server/accounts/app.ts` `linkGoCardlessAccount`, `linkSimpleFinAccount`,
`linkPluggyAiAccount`, `linkAkahuAccount`, `linkEnableBankingAccount` (handlers
`*-accounts-link`).

**R form (base).** Each function finds or creates its bank row (provider-specific key),
then repeats: upgrade the local account `upgradingId` (throw if missing) or insert a new
account and its transfer payee; run the initial `bankSync.syncAccount`; handle the
response; send a `sync-event`.

**F helper** (same file, module-private):

```ts
async function linkBankSyncAccount({
  bank, syncSource, newAccount, upgradingId, offBudget, startingDate, startingBalance,
  fileId, changedTables = ['transactions', 'accounts'],
}): Promise<string>   // 'ok'
```

Each provider function keeps its own bank lookup (and PluggyAI its file id) and calls
the helper.

| Inconsistency (base) | Preserved by |
|---|---|
| Only PluggyAI passes the budget file id to the initial sync (the `X-Actual-File-Id` it sends to the sync server) | `fileId` passed only by PluggyAI (an explicit `undefined` 8th argument equals the omitted optional one) |
| GoCardless stores `mask` and the provider's `official_name`; the others store `official_name = name` and no `mask` key | `newAccount` carries exactly each provider's columns, in base order (the insert emits one sync message per key, so the key set matters) |
| Akahu's `sync-event` reports only `transactions` as changed; the others `transactions` and `accounts` | `changedTables: ['transactions']` for Akahu |
| Each provider's bank key differs (requisition id; org domain / org id; account id for Enable Banking) | bank lookup stays in each provider function |
| Enable Banking alone checks `id == null` after the upgrade/insert branch | dropped: unreachable (both branches assign `id`), so no behaviour to preserve |

## Z4: weekend adjustment of schedule dates

Copies (4): `shared/schedules.ts` `getNextDate`, `server/schedules/app.ts`
`getUpcomingDates` (handler `schedule/get-upcoming-dates`),
`server/budget/schedule-template.ts` (×2, the repeating-schedule loop).

**R form (base).** Each site decides itself whether the rule applies and with which
mode, then calls the date arithmetic `getDateWithSkippedWeekend(date, mode)`, which base
already shares. The template converts day strings to dates and back around it.

**F helpers** (`shared/schedules.ts`, exported):

```ts
export type WeekendRule = { skipWeekend?: boolean; solveMode?: 'after' | 'before' };
export function applyWeekendRule(date: Date, rule: WeekendRule): Date
export function applyWeekendRuleToDay(day: string | null, rule: WeekendRule): string | null
```

`applyWeekendRuleToDay` is the template's day-string form; it delegates to
`applyWeekendRule` and returns the day unchanged (it may be null) when the rule is off,
as base does.

| Inconsistency (base) | Preserved by |
|---|---|
| The parsed schedule names the mode `weekendSolve`; the recurrence config (and the template's date condition) `weekendSolveMode` | each caller maps its own field onto `solveMode` |
| `getNextDate` can be told to ignore the rule (`noSkipWeekend`); no other site can | `skipWeekend: data.skipWeekend && !noSkipWeekend` at that call |

## Honesty list

1. **Only Z2's repetition is artificial.** Z1, Z3 and Z4 are repeated in base exactly
   as upstream wrote them; R leaves them alone.
2. **In R, Z4's date arithmetic is already shared** (`getDateWithSkippedWeekend`, base).
   What is repeated is the decision (whether the rule applies, which field holds the
   mode, the string/date conversion in the template). A change to the arithmetic alone
   reaches every R copy through that function; a change to the decision does not.
3. **In R, Z2's helper still exists** (exported for desktop-client), so an agent in R
   can find and reuse it; nothing in loot-core calls it.
4. **F's helpers are module-private where the copies were in one file** (Z1 in
   `actions.ts`, Z3 in `accounts/app.ts`), exported where the copies span files (Z2,
   Z4 in `shared/schedules.ts`). No new files.
5. **Ordering:** `copyPreviousMonth` keeps base's row order; `setZero` and the average
   actions now iterate the helper's query order instead of their own queries' order.
   Only the order of the per-category writes inside one batch can change; final state
   is the same (checked by the probe; see Equivalence).
6. **`getBudgetData`** still selects `is_income`, `hidden`, `group_hidden` though
   `copyPreviousMonth` in F no longer reads them (left as is to keep its rows and
   their order identical).
7. **Size of the treatment:** F changes 5 files (+241/−303 lines); R changes 3 files
   (+36/−7) (`packages/loot-core/src` only; both also carry `lint-script.patch`).
8. **Residual bias (from the review):** F's helpers carry short doc comments stating the
   rule, as extracted helpers do; R's upstream copies have none. So F differs from R in
   one more thing than shape: the rule is written down once in prose. Keep this in mind
   when reading any F advantage.

## Equivalence (how "behaviour identical" was checked)

All on trees rebuilt from the committed patches (`aa variant build R|F`, `aa variant
install R|F`), Node 24.18.1, before tagging `rf-frozen`:

| Check | A (base) | R | F |
|---|---|---|---|
| `tsgo -b` errors (the `lint` script) | 0 | 0 | 0 |
| `yarn typecheck` (`tsgo -b && tsc-strict`) | pass | pass | pass |
| Full loot-core suite, fast-check seed (passed / failed / skipped) | 1227 / 0 / 2 | 1227 / 0 / 2 | 1227 / 0 / 2 |
| `aa equivalence` (pass/fail sets) | — | A vs R: 0 differences | A vs F: 0; R vs F: 0 |
| `aa probe2` (553 behavioural cases) | reference | identical to A | identical to A |

The seeded A reference was rerun for study 2 (`aa suite baseline --cond A --study2` →
`work/study2/baseline-A.json`); study 1's `work/baseline-A.json` predates the seed and is
left untouched. For R/F comparisons `aa equivalence` allows no new test on either side
(study 1's A⁺ domain-test allowance does not apply).

**Why a probe as well as the suite.** The suite leaves much of the zones untested: no
loot-core test calls any `*-accounts-link` handler or `link*Account` function, none
runs a budget template on a ranged (`isbetween`) amount, and none calls
`copyPreviousMonth`, `setZero`, `set6MonthAvg` or `set12MonthAvg` (grep of the base
tests). Suite equivalence alone would therefore say little about Z1 and Z3. `substrate/study2/probe/`
holds two vitest files, copied into a tree only for `aa probe2` (like the seed), that
drive every zone through its edge cases and every preserved inconsistency, and dump
what they observe (budget rows per category for each bulk action in envelope and
tracking budgets; forecast / preview / posted / synced-action amounts for ranged,
numeric and missing amounts; template results for ranged amounts × percent / fixed
adjustments × income/expense and for weekly/monthly/daily schedules with every weekend
setting across month ends; next and upcoming dates for every weekend setting; for each
provider × new / off-budget / upgrade / missing-upgrade: account, payee and bank rows,
the initial-sync call, the client events, the thrown error). Cases record a thrown
error as their result, so a changed exception is a difference.

One normalisation, stated here because it was decided after seeing a difference: the
recorded `syncAccount` call drops trailing `undefined` arguments. F passes `fileId`
explicitly (undefined except for PluggyAI) where base omits the argument; `syncAccount`
reads neither `arguments` nor a rest parameter, so the two calls are the same call.

**Probe power.** Each preserved inconsistency was removed from F in turn (one edit,
probe rerun against A's output, edit reverted); every one was caught:

| Edit to F | Cases that differ |
|---|---|
| Z1 `setZero` skips hidden (`includeHidden: false`) | 2 |
| Z1 averages keep categories with a missing group (`skipMissingGroup: false`) | 6 |
| Z2 template uses the default rounding | 11 |
| Z3 PluggyAI does not send the file id | 3 |
| Z3 GoCardless without `mask` | 2 |
| Z3 Akahu reports `accounts` too | 3 |
| Z4 `getNextDate` ignores `noSkipWeekend` | 28 |
| Z4 template reads `weekendSolve` instead of `weekendSolveMode` | 46 |

Not observable by the probe: the insert key set for new accounts (sync messages are
not stored with syncing disabled in tests); it is preserved by construction (each
provider passes exactly its base columns, in base order).

## Images

`aa image build R|F` → `aa-actual:R` (`sha256:a2f09e994682…`), `aa-actual:F`
(`sha256:6e6e6135fcc9…`), built from the frozen variant trees. They are the study-1
`actual` stage plus a final `study2` stage that installs **jscpd 5.4.0** (pinned,
global) for the per-chain duplication measure. Smoke test in both: the image's
`/work/actual` HEAD is the variant commit, no agent-config dirs, and
`jscpd --min-tokens 50 --reporters json --silent` (the chain evaluator's arguments)
runs (on `actions.ts` + `accounts/app.ts`: R 33 clones / 510 duplicated lines, F 24 / 312).

**Study-1 images unchanged.** The Dockerfile change only appends the `study2` stage;
`build_image` now names the stage (`--target actual` for A/AL/AP/APL, `--target study2`
for R/F), because an untargeted build would pick the new last stage. Check: one
identical A context built twice, with the old Dockerfile and no target (study 1's
command) and with the new Dockerfile and `--target actual`: identical layers, config,
labels and creation time; only the top-level image digest differs, from per-build
BuildKit metadata (`Ref`, `CreatedAt`). The existing `aa-actual:A/AL/AP/APL` images were
not rebuilt or retagged.

## Review

`docs/study2-refactor-review.md`: review request and a separated second-pass review
(no independent agent was available in the session); round 1 found three comments that
narrated the refactor and one dishonest type, all fixed; round 2 passes all four zones.
