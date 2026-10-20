# Show progress while importing a YNAB budget

Importing a YNAB4 or nYNAB (YNAB 5) budget can take minutes on a large budget, and
the import dialog only shows a spinner. The server imports in stages (accounts,
categories, payees, ..., budgets) but tells the client nothing about how far along
it is. Make the server report progress and let the import dialogs show it.

## Required behaviour

### 1. Progress events

During an import the server sends the client a server event named
`import-progress` (add it to the typed server events) whose payload is

```ts
{
  step: ImportStep;        // the stage being imported, see below
  current: number;         // items imported so far in this step
  total: number;           // items expected in this step (0 when it has no count)
  overallCurrent: number;  // items imported so far across every step
  overallTotal: number;    // sum of every step's total
  batch?: { amount: number; account: string }; // see "named batches"
}
```

with `ImportStep` one of `'accounts' | 'categories' | 'payees' | 'payee-locations' |
'tags' | 'transactions' | 'scheduled-transactions' | 'budgets' | 'finishing'`.

### 2. A shared step runner

Add a module `progress` next to the budget importers (in the same directory as the
YNAB4 and YNAB5 importers) exporting

```ts
type ImportTick = (count?: number, account?: string) => void;
runImportSteps(steps: { step: ImportStep; total: number;
                        run: (tick: ImportTick) => Promise<unknown> }[]): Promise<void>
```

It runs the steps in order. `overallTotal` is the sum of all step totals. For each
step:

- it first sends an event with `current: 0` for that step;
- `run` receives a `tick(count = 1, account?)` callback that adds `count` to both
  `current` and `overallCurrent`. A tick **with** an account name ("named batch")
  always sends an event immediately, with `batch: { amount: count, account }`. A
  tick without an account sends an event only if at least 100 ms have passed since
  the last event sent (by the system clock, `Date.now()`), so huge imports do not
  flood the client;
- when `run` resolves, the step is snapped to its total (totals are estimates):
  `overallCurrent` grows by `max(0, total - current)` (never decreases), `current`
  becomes `total`, and an event is sent.

After the last step it sends a final event
`{ step: 'finishing', current: 0, total: 0, overallCurrent: overallTotal, overallTotal }`.
Events without a batch have no `batch` value (undefined).

Example (clock not advancing): steps `accounts` (total 2, ticks twice) and
`transactions` (total 10, one `tick(10)`) send exactly: accounts 0/2 (overall
0/12), accounts 2/2 (2/12), transactions 0/10 (2/12), transactions 10/10 (12/12),
finishing 0/0 (12/12). A step with total 5 that only ticks once still ends at 5/5
(overall 5/5) just before `finishing`. A step with ticks `(10, 'Checking')` and
`(20, 'Savings')` sends batches `undefined, {10, Checking}, {20, Savings},
undefined, undefined`.

### 3. Both importers report through it

The YNAB4 and YNAB5 imports run their stages through `runImportSteps`, each stage
ticking once per item it creates (transactions tick once per account batch with
the number of transactions and the account's name). Step totals count the live
(not deleted) items of the export.

For YNAB5 scheduled transactions, the importer function
`importScheduledTransactions(data, entityIdMap, flagNameConflicts, tick)` must be
exported from the YNAB5 importer module and tick **once per scheduled
transaction, only once that schedule is fully imported**: for a schedule whose
category or splits are applied afterwards by updating its rule, the tick happens
only after that rule update has completed; if creating a schedule fails, the error
propagates and no tick happens for it.

### 4. Client

The YNAB4 and YNAB5 import dialogs subscribe to `import-progress` before starting
the import and show the current stage, a progress bar for the overall progress and,
for named batches, which account was just imported; the dialog cannot be dismissed
while an import is running.
