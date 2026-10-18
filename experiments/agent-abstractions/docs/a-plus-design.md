# A⁺ design: a domain layer over loot-core

**Substrate:** `actualbudget/actual`, `packages/loot-core`, base `9732a446`.
**Status:** draft for review. Once reviewed it is frozen together with
`substrate/patches/aplus.patch` and never adjusted to fit a task.

This document defines the A⁺ treatment: what the domain layer exports, what
moves behind the write boundary, and what is deliberately left alone. It is
derived only from the write sites present in base, never from tasks.

## 0. Inputs

Inventories taken on the base tree (from `packages/loot-core`, non-test files):

| File (in `work/`) | Content | Lines |
|---|---|---|
| `write-sites.txt` | generic write API calls `db.update/insert/insertWithUUID/delete_/insertWithSchema/updateWithSchema(` (66) + raw `runQuery('INSERT\|UPDATE\|DELETE…')` (9) | 75 |
| `write-sites-datafns.txt` | calls to the data-specific write functions of `db/index.ts` (`db.insertTransaction(`, `db.moveCategory(`, …) plus `db.run(`/`db.execQuery(` | 74 |
| `raw-sql-sites.txt` | every SQL string with `INSERT/UPDATE/DELETE/REPLACE` passed to `runQuery/run/execQuery/cache`, including multi-line literals the first grep misses | 40 |
| `money-sites.txt` | `amountToInteger(` / `integerToAmount(` calls | 34 |

`write-sites.txt` covers only the generic API; `write-sites-datafns.txt` and
`raw-sql-sites.txt` complement it because most transaction, payee and category
writes go through the data-specific functions, and two raw `UPDATE`s on synced
tables use `db.run` with a multi-line template.

Handler registrations (non-test code): 82 `app.method('<name>',
mutator(undoable(handler)))` registrations in 13 `app.ts` files (one of them,
`payees-merge`, passes a meta function as the second argument of `undoable`),
and 21 `mutator(handler)` registrations without `undoable` (including the
`undo`/`redo` handlers in `main.ts`). See §4.12.

Sites by table (generic API + data-specific functions, non-test code):

| Table group | Sites | Main files |
|---|---|---|
| `transactions` | 25 | `transactions/{index,transfer,merge,app}.ts`, `accounts/{app,sync}.ts`, `tags/app.ts` |
| `accounts`, `account_groups`, `banks` | 27 | `accounts/{app,sync,link}.ts`, `account-groups/app.ts`, `api.ts` |
| `payees`, `payee_locations` | 16 | `payees/app.ts`, `accounts/{app,sync,payees}.ts` |
| `categories`, `category_groups` | 12 (+3 raw) | `budget/{app,sort-categories,cleanup-template-notes,goal-template}.ts`, `budget/statements.ts` (raw), `api.ts` (raw) |
| `zero_budgets`/`reflect_budgets`, `zero_budget_months`, `cleanup_groups` | 10 (+1 raw) | `budget/{actions,cleanup-groups}.ts` |
| `schedules`, `schedules_next_date` | 7 | `schedules/app.ts` |
| `rules` | 5 | `transactions/transaction-rules.ts`, `schedules/app.ts` |
| `tags` | 8 | `tags/app.ts` |
| `notes` | 2 | `notes/app.ts`, `budget/actions.ts` |
| `preferences`, `dashboard`, `dashboard_pages`, `custom_reports`, `transaction_filters` | 21 | `preferences/app.ts`, `dashboard/app.ts`, `reports/app.ts`, `filters/app.ts` |

## 1. Principle

Every mutation of synced data in non-test code goes through a **domain
command** exported from `src/server/domain/`, and every undoable user-facing
handler is registered through the domain helper **`mutation()`** (§4.12).
A command:

- owns CRDT emission by calling the existing write functions (now in
  `db/write.ts`), so every row change produces messages with a `Timestamp`;
- owns validation: the `*Model.validate` calls that base already performs
  (in the data-specific functions and in `transaction-rules.ts`) run inside
  the command or the write function it calls;
- reproduces the base write sequence exactly, including a `batchMessages`
  wrapper when base wraps exactly those writes. A⁺ changes where writes are
  expressed, not what they do: the full suite must give identical results.

Money crosses the domain boundary only as `Cents`. Every amount-valued field
of a command argument is typed `Cents` (or `Cents | null`).

**Undo.** User-facing mutations are the `app.method(...)` handlers. Base
registers 82 of them as `mutator(undoable(handler))`; A⁺ replaces every one
of those with the domain helper `mutation(name, handler)` (§4.12), which is
exactly `mutator(undoable(handler))`, so a user-facing mutation is registered
with one named call instead of two composed wrappers. Undo stays at that
registration point: domain commands run inside those handlers and do not wrap
themselves again (a nested `undoable` would record a second undo entry and
break equivalence). The 21 base registrations that use `mutator(handler)`
without `undoable` keep that form, because adding undo to them would change
behaviour; see §5.

## 2. `Cents` (`src/server/domain/money.ts`)

```ts
declare const brand: unique symbol;
export type Cents = number & { readonly [brand]: 'Cents' };

export const cents: {
  fromInteger(n: number): Cents;                    // throws 'Cents must be an integer' if !Number.isInteger(n)
  fromAmount(a: Amount, decimals?: number): Cents;  // = fromInteger(amountToInteger(a, decimals)); decimals defaults to 2
  toAmount(c: Cents, decimals?: number): Amount;    // = integerToAmount(c, decimals)
  add(a: Cents, b: Cents): Cents;
  sub(a: Cents, b: Cents): Cents;
  neg(a: Cents): Cents;
  sum(xs: readonly Cents[]): Cents;
  zero: Cents;
};
```

- `Amount` and `IntegerAmount` are the existing aliases from `#shared/util`
  (both plain `number`). The spec's working names map as: spec
  `IntegerAmount` (branded) → `Cents`; spec `AmountFloat` → existing `Amount`.
- The only ways to obtain a `Cents` are the constructors above. A `Cents`
  is still assignable to `number`, so reads, formatting and comparisons keep
  working; `a * 100` or `a + 0.5` yields a plain `number` that no command
  accepts.
- "Cents" means integer minor units of the budget currency (`decimals`
  defaults to 2, as `amountToInteger` does), not literally hundredths.
- `cents.fromInteger` throws on a non-integer (including `NaN`). Where base
  wrote an amount without any integer check, A⁺ now throws instead of storing
  the value; the call sites where this can differ at runtime are listed in
  §8, item 6.

## 3. Boundary (structural, not lint)

- The write API moves, unchanged, from `db/index.ts` to `db/write.ts`:
  `update`, `insert`, `insertWithUUID`, `delete_`, `deleteAll`,
  `insertWithSchema`, `updateWithSchema`, and the data-specific write
  functions `insertCategoryGroup`, `updateCategoryGroup`, `moveCategoryGroup`,
  `deleteCategoryGroup`, `insertCategory`, `updateCategory`, `moveCategory`,
  `deleteCategory`, `insertPayee`, `deletePayee`, `deleteTransferPayee`,
  `updatePayee`, `mergePayees`, `insertAccount`, `updateAccount`,
  `deleteAccount`, `moveAccount`, `insertAccountGroup`, `updateAccountGroup`,
  `moveAccountGroup`, `deleteAccountGroup`, `insertTransaction`,
  `updateTransaction`, `deleteTransaction`, `moveTransaction`,
  `moveSchedule`, `insertTag`, `deleteTag`, `updateTag`.
- `#server/db` keeps reads and the generic SQL entry points (`runQuery`,
  `run`, `execQuery`, `cache`, `all`, `first`, `firstSync`, `select*`,
  `transaction`, `asyncTransaction`) because reads need them (see §5).
- `package.json` `imports` gains `"#server/db/write": "./src/server/db/write.ts"`.
- `db/write` is imported only by `src/server/domain/`, `src/server/db/` and
  test files. `domain/internal.ts` is imported only from inside `domain/`
  and is not re-exported by `domain/index.ts`.
- Nothing enforces this in A⁺ except that no non-domain module imports
  `db/write`. Enforcement is what "+L" adds, so lint stays the only difference
  between AP and APL.

## 4. Domain modules and commands

`domain/index.ts` re-exports every module below and `cents`/`Cents`.
Shared helper types (in `domain/internal.ts`, type-only exports allowed):

```ts
type Id = string;
type Patch<T extends { id: Id }> = Pick<T, 'id'> & Partial<Omit<T, 'id'>>;
type WithCents<T, K extends keyof T> = Omit<T, K> & { [P in K]: Cents };
type WithCentsOpt<T, K extends keyof T> = Omit<T, K> & { [P in K]?: Cents | null };
```

Each command lists the base site it replaces in brackets. "generic" marks a
command implemented with `update/insert/insertWithUUID/delete_/…Schema` from
`db/write` because base has no data-specific function for that table.

### 4.1 `domain/transactions.ts` — `transactions`

```ts
export type NewTransaction =
  WithCents<Omit<Partial<TransactionEntity>, 'id' | 'subtransactions'>, 'amount'>
  & { id?: Id; account: AccountEntity['id'] };
export type TransactionPatch =
  WithCentsOpt<Patch<Omit<TransactionEntity, 'subtransactions'>>, 'amount'>;

export function createTransaction(t: NewTransaction): Promise<TransactionEntity['id']>;   // [insertTransaction: transactions/index, transfer, accounts/app, accounts/sync]
export function updateTransaction(t: TransactionPatch): Promise<void>;                     // [updateTransaction: transactions/index, transfer, merge, accounts/app, tags/app]
export function deleteTransaction(t: { id: Id }): Promise<void>;                           // [deleteTransaction]
export function moveTransaction(id: Id, accountId: Id, targetId: Id | null): Promise<void>; // [moveTransaction: transactions/app]
```

The batch engine `batchUpdateTransactions` (`transactions/index.ts`) stays
where it is and calls these commands; callers holding a `TransactionEntity`
pass `amount: cents.fromInteger(t.amount)`.

### 4.2 `domain/accounts.ts` — `accounts`, `account_groups`, `banks`

```ts
type MoneyFields = 'balance_current' | 'balance_available' | 'balance_limit';
export type NewAccount = WithRequired<Partial<Omit<DbAccount, 'id' | MoneyFields>>, 'name'>
  & { id?: Id } & { [K in MoneyFields]?: Cents | null };
export type AccountPatch = WithCentsOpt<Patch<DbAccount>, MoneyFields>;

export function createAccount(a: NewAccount): Promise<AccountEntity['id']>;               // [insertAccount (sort order + validate)]
export function createLinkedAccount(a: NewAccount & { id: Id }): Promise<AccountEntity['id']>; // generic insertWithUUID [accounts/app: 5 link flows]
export function updateAccount(a: AccountPatch): Promise<void>;                              // [updateAccount (validate): api, accounts/app]
export function setAccountFields(a: AccountPatch): Promise<void>;                           // generic update, no validate [accounts/app: rename, link, close/reopen, sync status; accounts/sync balance]
export function deleteAccount(a: { id: Id }): Promise<void>;                                // [deleteAccount]
export function moveAccount(id: Id, targetId: Id | null, accountGroupId?: Id | null): Promise<void>; // [moveAccount]
export function createAccountGroup(g: WithRequired<Partial<DbAccountGroup>, 'name'>): Promise<AccountGroupEntity['id']>; // [insertAccountGroup]
export function updateAccountGroup(g: WithRequired<Partial<DbAccountGroup>, 'id' | 'name'>): Promise<void>;           // [updateAccountGroup]
export function moveAccountGroup(id: Id, targetId?: Id | null): Promise<void>;              // [moveAccountGroup]
export function deleteAccountGroup(g: { id: Id }): Promise<void>;                           // [deleteAccountGroup]
export function createBank(b: Omit<DbBank, 'tombstone'>): Promise<BankEntity['id']>;        // generic insertWithUUID [accounts/link]
```

`updateAccount` and `setAccountFields` both exist because base uses both
paths (validated and raw `update`) for `accounts`; collapsing them would
change behaviour. The account-delete flow (`accounts/app.ts`, forced
delete) keeps its `batchMessages` and calls `updateTransaction`,
`deleteTransaction`, `deleteAccount` and `payees.deleteTransferPayee`.

### 4.3 `domain/payees.ts` — `payees`, `payee_locations`

```ts
export type NewPayee = WithRequired<Partial<DbPayee>, 'name'>;

export function createPayee(p: NewPayee): Promise<PayeeEntity['id']>;                  // [insertPayee: payees/app, accounts/{app,sync,payees}, transaction-rules]
export function updatePayee(p: WithRequired<Partial<DbPayee>, 'id'>): Promise<void>;   // [updatePayee]
export function deletePayee(p: { id: Id }): Promise<void>;                             // [deletePayee]
export function deleteTransferPayee(p: { id: Id }): Promise<void>;                     // [deleteTransferPayee]
export function mergePayees(target: Id, ids: Id[]): Promise<void>;                     // [mergePayees]
export function createPayeeLocation(l: Omit<PayeeLocationEntity, 'id'>): Promise<PayeeLocationEntity['id']>; // generic insertWithUUID [payees/app]
export function deletePayeeLocation(id: PayeeLocationEntity['id']): Promise<void>;     // generic delete_ [payees/app]
```

Coordinate validation for locations stays in `payees/app.ts` (it is input
validation of the handler, not a write invariant).

### 4.4 `domain/categories.ts` — `categories`, `category_groups`

```ts
export function createCategory(c: WithRequired<Partial<DbCategory>, 'name' | 'cat_group'>,
  opts?: { atEnd?: boolean }): Promise<CategoryEntity['id']>;                                        // [insertCategory]
export function updateCategory(c: WithRequired<Partial<DbCategory>, 'name' | 'is_income' | 'cat_group'>): Promise<void>; // [updateCategory]
export function setCategoryTemplateFields(p: Pick<DbCategory, 'id'>
  & { goal_def?: string | null; cleanup_def?: string | null; template_settings?: unknown }): Promise<void>;   // generic updateWithSchema [cleanup-template-notes, goal-template]
export function moveCategory(id: Id, groupId: Id, targetId?: Id | null): Promise<void>;             // [moveCategory: budget/app, sort-categories]
export function deleteCategory(c: { id: Id }, transferId?: Id | null): Promise<void>;               // [deleteCategory]
export function createCategoryGroup(g: WithRequired<Partial<DbCategoryGroup>, 'name'>): Promise<CategoryGroupEntity['id']>; // [insertCategoryGroup]
export function updateCategoryGroup(g: WithRequired<Partial<DbCategoryGroup>, 'id' | 'name' | 'is_income'>): Promise<void>; // [updateCategoryGroup]
export function moveCategoryGroup(id: Id, targetId?: Id | null): Promise<void>;                     // [moveCategoryGroup]
export function deleteCategoryGroup(g: { id: Id }, transferId?: Id | null): Promise<void>;          // [deleteCategoryGroup]

// Pre-existing raw SQL writes, preserved verbatim (no CRDT messages, as in base):
export function resetGoalDefsWithoutTemplates(categoryIds?: Id[]): Promise<void>;   // raw db.run UPDATE categories [budget/statements]
export function clearDefaultExpenseCategories(): void;                               // raw runQuery DELETE categories + category_groups WHERE is_income = 0 [api.ts start-import]
```

`setCategoryTemplateFields` accepts the exact field shapes base passes
(`goal_def`/`cleanup_def` as JSON strings or null, `template_settings` as an
object converted by the schema).

### 4.5 `domain/budget.ts` — `zero_budgets`/`reflect_budgets`, `zero_budget_months`, `cleanup_groups`

```ts
type BudgetCell = { category: CategoryEntity['id']; month: string };

export function setBudgetAmount(c: BudgetCell & { amount: Cents }): Promise<void>;                 // [actions.setBudget: update | insert on the active budget table]
export function setBudgetGoal(c: BudgetCell & { goal: Cents | null; long_goal: 0 | 1 | null }): Promise<void>; // [actions.setGoal]
export function setBuffered(month: string, amount: Cents): Promise<void>;                          // [actions.setBuffer: zero_budget_months]
export function setCarryover(c: BudgetCell & { flag: boolean }): Promise<void>;                     // [actions.setCarryover: update | insert on the active budget table]
export function restoreCleanupGroup(id: Id): Promise<void>;                                         // generic update tombstone = 0 [cleanup-groups]
export function createCleanupGroup(g: { id: Id; name: string }): Promise<Id>;                       // generic insertWithSchema [cleanup-groups]

// Pre-existing raw SQL write, preserved verbatim:
export function tombstoneOrphanCleanupGroups(): Promise<void>;                                      // raw db.run UPDATE cleanup_groups [cleanup-groups]
```

The read-then-insert-or-update logic of `setBudget`, `setGoal`, `setBuffer`
and `setCarryover` moves into these commands unchanged; the exported
functions in `budget/actions.ts` keep their names and signatures and become
thin callers (`safeNumber` already rejects non-integers, so
`cents.fromInteger(safeNumber(amount))` preserves behaviour). The goal
amount `goal` is money; `long_goal` and `carryover` are flags.

`setBudgetAmount`, `setBudgetGoal` and `setCarryover` all choose the active
budget table internally (`reflect_budgets` for tracking budgets,
`zero_budgets` otherwise, as base `getBudgetTable()` does); no command takes
the table as an argument. In base, `setCarryover` received the table from its
two callers (`setCategoryCarryover`, `resetIncomeCarryover`), and both pass
`getBudgetTable()`, so choosing it inside the command is equivalent. All
three take `month` as `YYYY-MM`; `setCarryover` converts it with `dbMonth`
and writes the row id and `month` value exactly as base did (the `dbMonth`
string).

These four commands are deliberately not `async`: base ran the existence
check synchronously (`firstSync`) and returned the write promise, and callers
rely on that inside `batchMessages` (`void setBudget(...)` in loops).

### 4.6 `domain/schedules.ts` — `schedules`, `schedules_next_date`

```ts
export function createScheduleRows(s: {
  schedule: Omit<Partial<DbSchedule>, 'id' | 'rule'>; id: Id; ruleId: Id;
  nextDate: string | null; now: number;
}): Promise<void>;                                                                     // generic insertWithUUID schedules_next_date + insertWithSchema schedules [schedules/app create]
export function updateScheduleRow(s: Patch<ScheduleEntity>): Promise<void>;            // generic updateWithSchema [schedules/app update]
export function setScheduleNextDate(n: Patch<DbScheduleNextDate>): Promise<void>;      // generic update [schedules/app setNextDate]
export function replaceScheduleRule(id: Id, oldRuleId: Id | null, newRuleId: Id): Promise<void>; // generic delete_ old rule (if any) + updateWithSchema schedules.rule [fixRuleForSchedule]
export function deleteScheduleWithRule(id: Id, ruleId: Id): Promise<void>;             // generic delete_ rules + schedules in batchMessages [deleteSchedule]
export function moveSchedule(id: Id, targetId: Id | null): Promise<void>;              // [moveSchedule]
```

`createScheduleRows` takes `nextDate` as `YYYY-MM-DD` (or `null`) and stores
it as its date repr (`toDateRepr`), as base did. `replaceScheduleRule` is
called by `fixRuleForSchedule` after the new rule is created
(`insertRule`), so the old rule is now deleted after the insert instead of
before it (§8, item 3).

Schedule amounts live inside rule conditions (`_amount` JSON); they are not
typed as `Cents` (see §5).

### 4.7 `domain/rules.ts` — `rules`

```ts
export function createRule(r: Omit<RuleEntity, 'id'> & { id?: Id }): Promise<RuleEntity['id']>; // [transaction-rules.insertRule: validate + fromJS + insertWithUUID]
export function updateRule(r: Patch<RuleEntity>): Promise<void>;                                  // [transaction-rules.updateRule: validate + fromJS + update]
export function deleteRule(id: Id): Promise<boolean>;                                             // [transaction-rules.deleteRule: refuses if a schedule links it]
```

`insertRule/updateRule/deleteRule` in `transaction-rules.ts` keep their
exports (many callers and tests use them) and delegate to these commands.

### 4.8 `domain/notes.ts` — `notes`

```ts
export function saveNote(n: NoteEntity): Promise<void>;                        // generic update [notes/app updateNotes]
export function appendToNote(id: Id, existing: string, line: string): Promise<void>; // generic update [budget/actions addMovementNotes]
```

### 4.9 `domain/tags.ts` — `tags`

```ts
export function createTag(t: Omit<DbTag, 'id' | 'tombstone'>): Promise<TagEntity['id']>; // [insertTag]
export function updateTag(t: Patch<DbTag>): Promise<void>;                                // [updateTag: 5 sites]
export function deleteTag(t: { id: Id }): Promise<void>;                                  // [deleteTag: 2 sites]
```

Renaming a tag also rewrites transaction notes; that path calls
`transactions.updateTransaction`.

### 4.10 `domain/workspace.ts` — `preferences`, `dashboard`, `dashboard_pages`, `custom_reports`, `transaction_filters`

These tables are synced but hold user workspace configuration, not ledger
data. They get commands so that the boundary has no hole; none carry money.

```ts
export function saveSyncedPref(id: keyof SyncedPrefs, value: string | undefined): Promise<void>; // generic update [preferences/app]
export function createDashboardPage(p: { id: Id; name: string }): Promise<Id>;     // generic insertWithSchema
export function renameDashboardPage(p: { id: Id; name: string }): Promise<void>;   // generic updateWithSchema
export function deleteDashboardPage(id: Id): Promise<void>;                        // generic delete_
export function createWidget(w: WithOptional<NewDashboardWidgetEntity, 'x' | 'y'>
  & { id?: Id; dashboard_page_id: Id }): Promise<Id>;                             // generic insertWithSchema (x/y filled only when both missing, as base)
export function updateWidget(w: Patch<DashboardWidgetEntity>
  | EverythingButIdOptional<Omit<DashboardWidgetEntity, 'tombstone'>>,
  opts?: { schema?: boolean }): Promise<void>;                                     // generic update / updateWithSchema (base uses both)
export function deleteWidget(id: Id): Promise<void>;                               // generic delete_
export function createReport(r: CustomReportEntity): Promise<Id>;                  // generic insertWithSchema(reportModel.fromJS) [reports/app, dashboard import]
export function updateReport(r: Patch<CustomReportEntity>): Promise<void>;         // generic updateWithSchema(reportModel.fromJS) [reports/app]
export function restoreReport(r: CustomReportEntity): Promise<void>;               // generic updateWithSchema(reportModel.fromJS, undefined->null) + tombstone false [dashboard/app import of an existing report]
export function deleteReport(id: Id): Promise<void>;                               // generic delete_
// FilterInput = Omit<TransactionFilterEntity, 'tombstone'> & Partial<Pick<TransactionFilterEntity, 'tombstone'>>
export function createFilter(f: FilterInput): Promise<Id>;                         // generic insertWithSchema(filterModel.fromJS)
export function updateFilter(f: FilterInput): Promise<void>;                       // generic updateWithSchema
export function deleteFilter(id: Id): Promise<void>;                               // generic delete_
```

Name-uniqueness checks and import parsing stay in the `app.ts` handlers.

### 4.11 `domain/internal.ts`

Imports `#server/db/write` and exposes it only to sibling domain modules. It
also documents, as a comment block, the raw SQL writes of base and where
each one lives (§4.4, §4.5 and the list below).

Raw `INSERT/UPDATE/DELETE` sites from the inventory that are **not** moved,
because they target local, non-synced tables or are the db/sync engine or
test infrastructure itself:

| Site | Table | Reason left in place |
|---|---|---|
| `db/index.ts` (`loadClock`), `sync/index.ts`, `sync/repair.ts`, `budgetfiles/app.ts` | `messages_clock`, `messages_crdt`, `messages_pending` | sync engine |
| `sync/replay.ts`, `sync/reset.ts` | CRDT apply, `messages_pending`, `kvcache_key` | sync engine |
| `sheet.ts`, `cloud-storage.ts`, `importers/actual.ts` | `kvcache`, `kvcache_key` | local spreadsheet cache |
| `update.ts` | `__meta__` | migration metadata |
| `schedules/app.ts` | `schedules_json_paths` | local derived index |
| `mocks/setup.ts`, `mocks/budget.ts` | `db_version`, `categories`, `category_groups` | test fixtures |

### 4.12 `domain/mutation.ts` — registering user-facing mutations

```ts
import type { HandlerFunctions } from '#types/handlers'; // the type base `mutator`/`undoable` already use

export function mutation<K extends string, H extends HandlerFunctions>(
  name: K,
  handler: H,
  meta?: (...args: Parameters<H>) => unknown,
): readonly [K, ReturnType<typeof undoable<H>>];
// = [name, mutator(undoable(handler, meta))]
```

Call site: `app.method(...mutation('budget/budget-amount', actions.setBudget))`
replaces `app.method('budget/budget-amount', mutator(undoable(actions.setBudget)))`.
The method name and the undo + mutator wrapping are written in one call; the
wrapped handler is the same function object base registers (`mutator` marks it
in `mutatingMethods`, `undoable` records the undo marker with the same `meta`),
so behaviour is identical. `meta` exists only because one base registration
(`payees-merge`) passes a meta function to `undoable`. `domain/index.ts`
re-exports `mutation`. `mutation.ts` imports `mutator` from `#server/mutators`
and `undoable` from `#server/undo`, both unchanged.

Registrations migrated (every `mutator(undoable(...))` in non-test code, all of
the form `app.method('<literal name>', mutator(undoable(handler[, meta])))`):

| File | Registrations |
|---|---|
| `budget/app.ts` | 34 |
| `dashboard/app.ts` | 10 |
| `tags/app.ts` | 7 |
| `schedules/app.ts` | 6 |
| `accounts/app.ts` | 5 |
| `rules/app.ts` | 4 |
| `account-groups/app.ts` | 4 |
| `payees/app.ts` | 3 (one with `meta`) |
| `transactions/app.ts` | 3 |
| `reports/app.ts` | 3 |
| `filters/app.ts`, `preferences/app.ts`, `notes/app.ts` | 1 each |
| **Total** | **82** |

Not migrated: the 21 `mutator(handler)` registrations without `undoable`
(e.g. `transaction-add/update/delete`, `filter-create/update`,
`payee-location-create/delete`, `account-close`, `rule-add`, `undo`/`redo`).
They are mutating but not undoable in base, and `mutation()` would add undo.
After migration, no `mutator(undoable(` remains outside `domain/mutation.ts`.

## 5. What is NOT abstracted (honesty list)

1. **Raw SQL stays expressible.** `runQuery`, `run`, `execQuery` and `cache`
   remain in `#server/db` because reads use them. A⁺ removes the CRDT write
   API from non-domain code; it does not make `db.runQuery('UPDATE …')`
   impossible. Only the lint (`no-raw-synced-write`) and the hidden checker
   see that.
2. **Pre-existing raw writes on synced tables** (no CRDT messages) are kept
   verbatim behind named commands, not fixed: `UPDATE categories SET goal_def`
   (`resetGoalDefsWithoutTemplates`), `UPDATE cleanup_groups SET tombstone`
   (`tombstoneOrphanCleanupGroups`), and the two `DELETE`s in API import
   (`clearDefaultExpenseCategories`). Fixing them would change behaviour.
3. **`sendMessages`** remains importable from `#server/sync`; `prefs.ts` and
   `undo.ts` call it directly in base and keep doing so.
4. **`batchMessages`** is not wrapped; callers that batch several commands
   keep calling it.
5. **Undo:** `undoable`, `mutator`, `runMutator` and `withUndo` internals are
   untouched, and undo stays at handler registration (§1). `mutation()` makes
   the undoable registration one named call (§4.12) but does not force it:
   `mutator`, `undoable` and `app.method` stay importable, so a new handler
   registered as `app.method('x', handler)` or `mutator(handler)` compiles in
   A⁺, and the 21 base `mutator`-only registrations keep that form.
6. **Reads/queries** (AQL `q(...)`, `aqlQuery`, `db.all/first/select*`) are
   not abstracted; they return plain `number` amounts.
7. **Sync engine** (`src/server/sync/`), migrations and the spreadsheet
   (`sheet.ts`, budget cell formulas) are untouched.
8. **Money inside JSON** is not typed: rule condition/action values
   (including schedule `_amount`), goal templates (`goal_def`), cleanup
   templates and custom report settings carry numbers as plain JSON.
9. **`Cents` is a type-level guarantee only.** `as Cents` casts compile in A⁺
   (forbidding them is part of A⁺+L), and `cents.fromAmount` accepts any
   `number`, so a float can still be converted explicitly.
10. **Test files** keep direct access to `db/write`; mocks under `src/mocks/`
    are treated as test code. Test files that imported a moved write function
    from `#server/db` were repointed mechanically to `#server/db/write` (import
    line and `db.<write>` → `dbWrite.<write>`, including `vi.mock`/`vi.mocked`);
    no assertion changed. Because the vitest setup file already loads the
    domain layer (through `#server/sync` → `budget/actions` and
    `transactions/transaction-rules`, as base already loaded those modules), a
    test-file `vi.mock('#server/db/write')` does not reach domain commands by
    itself: the two tests that assert on mocked writes
    (`budget/template-notes.test.ts`, `budget/cleanup-template-notes.test.ts`)
    add `vi.hoisted(() => vi.resetModules())` so the code under test and the
    domain load fresh with their mocks. A hidden test that mocks the db write
    API needs the same two edits on A⁺.
11. **Leaf module for template prefixes.** `TEMPLATE_PREFIX`/`GOAL_PREFIX`
    move to `budget/template-prefixes.ts` (re-exported by `template-notes.ts`)
    so `domain/categories.ts` does not load the template engine.
12. **Lint allow-list size** (frozen with the rule sets, `eslint-rules/base-allow-list.mjs`
    in each lint variant). Base sites that trip a rule are allow-listed individually
    (file + SQL prefix, trimmed source line or method name; an entry covers at most
    `count` identical sites, default 1), never by weakening a rule or turning it off
    for a file.
    - **A+L: 115 sites, 115 entries.** `no-raw-synced-write` 4: `api.ts`
      `DELETE FROM categories|category_groups WHERE is_income = 0`,
      `budget/statements.ts` `UPDATE categories SET goal_def = NULL`,
      `budget/cleanup-groups.ts` `UPDATE cleanup_groups SET tombstone = 1`.
      `no-send-messages` 4 (`prefs.ts`, `undo.ts`: import + call each).
      `no-float-money` 1 (`accounts/sync.ts`, pluggyai starting balance).
      `mutator-required` 106: registrations whose name does not start with
      `get`/`query`/`list` and are not wrapped in `mutator(`; mostly reads named
      `*-get` and handlers outside the CRDT (budget files, auth, sync, bank links).
    - **A⁺+L: 140 sites, 135 entries.** `no-send-messages` 4 (same sites).
      `mutator-required` (form `mutation()`) 125: the same 106 plus the 19
      `app.method` registrations that keep `mutator(handler)` (§4.12).
      `no-explicit-any` 3 (`aql/exec.ts`, `db/index.ts` x2). `ban-ts-comment`
      (every `@ts-expect-error`/`@ts-ignore`/`@ts-nocheck`, with or without a
      description) 8 sites in 3 entries (`api.ts` x5, `encryption-internals.electron.ts`
      x2, `spreadsheet/spreadsheet.ts`). `#server/db/write` imports and `as Cents`
      casts: 0 base sites. A⁺+L has no raw-write rule (its rules forbid bypassing
      the abstraction); the four raw writes listed for A+L sit behind the domain
      commands of §4.4/§4.5 in A⁺.

## 6. Why this is "more than usual"

| Concern | A (habitual) | A⁺ |
|---|---|---|
| Writing synced data | `db.update('accounts', …)` is one import away from every server module | the write API is not exported by `#server/db`; non-domain code calls a named command (`accounts.setAccountFields`) |
| Bypassing the abstraction | nothing to bypass: the helpers are the low-level API | requires importing `#server/db/write`, which no non-domain module imports |
| Float money | `amount: 12.5` is a valid `number` in any write | every command amount field is `Cents`; a float is a type error unless converted through `cents.*` |
| Where invariants live | spread across `db/index.ts`, handlers and helpers | one module per table group; CRDT emission and validation inside the command |
| Registering a user-facing mutation | `mutator(undoable(handler))` composed by hand at each of 82 sites | one helper, `mutation(name, handler)` (§4.12) |
| Raw SQL, `sendMessages`, missing undo | unconstrained | still unconstrained (§5): `mutation()` is offered, not enforced; lint and checker treat A and A⁺ identically here |

## 7. Acceptance criteria for the implementation

- `grep` for imports of `db/write` outside `src/server/domain/`, `src/server/db/`
  and test files returns nothing.
- Every line of the three write inventories is either migrated to a command
  listed in §4 or appears in the not-moved table of §4.11.
- `grep` for `mutator(undoable(` in non-test code returns only
  `domain/mutation.ts`, and the 82 registrations of §4.12 use `mutation()`.
- `yarn tsgo -b` is as clean as on base; the full loot-core suite gives the
  same pass/fail sets as A (new passing tests allowed only under
  `src/server/domain/`).
- No command signature differs from §4 without updating this document
  before the freeze.

## 8. Implementation adjustments (before freeze)

Adjustments found while implementing `aplus.patch` against this document.
None came from a task (no task existed when they were made); each is derived
from base code or from Actual's own test suite. §2–§5 above already reflect
them; this section records what changed relative to the approved draft
(commit `faa3731`) and why.

1. **`mutation()` returns a tuple.** `mutation(name, handler, meta?)` returns
   `readonly [name, mutator(undoable(handler, meta))]` and is spread into the
   registration: `app.method(...mutation('x', h))`. The return type was in
   the approved draft; the implementation fixes the call-site form, which is
   what the APL `mutator-required` rule and the hidden checker recognise as a
   wrapped user-facing mutation (§4.12).
2. **`workspace.restoreReport` and a wider `createWidget`.** Dashboard import
   of a report that already exists used a raw `updateWithSchema` in base with
   its own transformation, so it gets its own command (exported from
   `domain/workspace.ts`):

   ```ts
   export function restoreReport(r: CustomReportEntity): Promise<void>;
   // = updateWithSchema('custom_reports', { ...reportModel.fromJS(r) with every
   //   undefined value replaced by null, tombstone: false })
   export function createWidget(
     widget: WithOptional<NewDashboardWidgetEntity, 'x' | 'y'> & { id?: Id; dashboard_page_id: Id },
   ): Promise<Id>;
   ```

   The approved draft had no `restoreReport` and typed `createWidget` as
   `NewDashboardWidgetEntity & { id?: Id; dashboard_page_id: Id }`.
   `createWidget` now takes `x`/`y` as optional because
   `addDashboardWidget` passes a widget typed
   `WithOptional<…, 'x' | 'y'>`: base `addDashboardWidget` computes the position only when both
   are missing and writes the widget as given otherwise.
3. **`fixRuleForSchedule` order.** Base deleted the schedule's old rule,
   inserted the new rule and then linked it. A⁺ inserts the new rule first
   (`insertRule`) and then calls `schedules.replaceScheduleRule(id, oldRuleId,
   newRuleId)`, which deletes the old rule (if any) and links the new one.
   The CRDT messages are emitted in a different order; the end state (rows and
   message set) is the same and the suite results are identical.
4. **Leaf module `budget/template-prefixes.ts`.** `TEMPLATE_PREFIX` and
   `GOAL_PREFIX` moved there (re-exported by `template-notes.ts`) so that
   `domain/categories.ts` (`resetGoalDefsWithoutTemplates`) does not import
   the template engine and create an import cycle (§5, item 11).
5. **Two Actual tests need `vi.hoisted(() => vi.resetModules())` on A⁺.**
   `budget/template-notes.test.ts` and `budget/cleanup-template-notes.test.ts`
   mock db writes that the code under test now reaches through the domain
   layer, which the vitest setup file has already loaded; without a module
   reset the domain keeps the unmocked `db/write`. The edit is mechanical and
   changes no assertion (§5, item 10). The same rule applies to hidden tests
   (spec §6, plan Task 9).
6. **`cents.fromInteger` throws where base accepted non-integers.** Call sites
   in the A⁺ tree (`grep -rnE "cents\.from(Integer|Amount)"`, non-domain):

   | Site | Value | Base behaviour on a non-integer | A⁺ |
   |---|---|---|---|
   | `budget/actions.ts` `setBudget` | `safeNumber(amount)` | `safeNumber` already throws | same |
   | `budget/actions.ts` `setGoal` | `goal` from goal/cleanup templates | stored (plain `update`/`insert`, no schema check) | **throws**; integer in practice (`amountToInteger`, sheet values) |
   | `budget/actions.ts` `setBuffer` | `holdForNextMonth` amount (handler/API `budget-hold-for-next-month` argument, clamped against sheet values) | stored | **throws** if a client passes a float |
   | `api.ts` `api/account-update` | `balance_current` from the API caller | stored (`updateAccount` validates required fields only) | **throws** on a float |
   | `accounts/sync.ts` `updateAccountBalance` | bank current balance from the sync server | stored (plain `update`) | **throws** if a provider returns a non-integer |
   | `accounts/sync.ts` initial sync starting balance | `balanceToUse` (custom or computed) | insert schema throws (`Can't convert to integer`) | throws earlier, different message |
   | `transactions/index.ts` `withCents`, `transactions/transfer.ts` (2) | transaction `amount` (`null` passed through) | insert/update schema throws | same point, different message |
   | `accounts/app.ts` create account, `accounts/sync.ts` import | `cents.fromAmount(...)` (rounds) | `NaN` reaches the schema check and throws | `NaN` throws earlier, different message |

   The four **throws** rows are the only places where A⁺ can reject a value
   that base stored; none is exercised by the base suite (equivalence holds).
   A hidden test that writes a float there would fail on A⁺ but not on A; the
   control of spec §6 (the original solution must pass the hidden tests in
   all four conditions) drops such a task for all conditions.
7. **§4 signatures checked against the code.** Every signature of §4 was
   diffed against the exports of `src/server/domain/*.ts` in the AP tree. The
   parameter and return types match; the corrections were to the comments:
   `createPayee` also replaces `insertPayee` in `transaction-rules`;
   `updateReport` and `restoreReport` go through `reportModel.fromJS`;
   `replaceScheduleRule` deletes only when there is an old rule; the four
   budget-cell commands are not `async` (§4.5); `createScheduleRows` stores
   `nextDate` as its date repr (§4.6). `cents` is declared as an object
   literal whose inferred type is the one in §2.
