Answering in English, as the task header requests.

TASK 4556e9e244
SOLVABLE: yes. The hidden test runs SimpleFIN batch sync twice for the same transaction. The first run has no category; the second carries `category: 'provider-category'`. Each expectation is covered by the statement or by current behaviour:
- First sync returns 2 `newTransactions` (starting balance plus the transaction). That is unchanged import behaviour, which the statement says to preserve.
- Second sync returns 0 `newTransactions`, 0 `matchedTransactions` and no errors. This follows from "must not modify the stored transaction".
- Exactly 3 new CRDT messages, all with dataset `accounts`, on columns `balance_current`, `bank_sync_status` and `last_sync`. None has dataset `transactions`. The statement states this explicitly ("current balance, sync status, last sync time").
- The stored transaction's `category` is `null`. The statement says "stays empty", which in practice means null.

Two small points remain implicit:
- `matchedTransactions` must be empty rather than containing a no-op match. A competent engineer would infer this from "must not modify", because the existing code only reports matches it updates.
- "Empty" means `null`, not `''`.

LEAK: no. "a provider category is kept only if it is the id of an existing category in the budget" describes behaviour; it doesn't name `db.getCategories`, `normalizeBankSyncTransactions` or a file. Saying that SimpleFIN batch sync is covered is scope, not implementation.
FIX: Optional: change "the transaction's category stays empty" to "the transaction's category stays `null`", and add "no transaction is reported as matched/updated".

TASK 81ea158cf6
SOLVABLE: yes. Each hidden-test expectation is covered:
- Exports in the actions module are `setNMonthAvg({month, N, category})` and `set3MonthAvg({month})`, both existing. The new export `getCategoryAverage({month, maxMonths, categoryId})` is given with its exact signature and key names.
- With `global.currentMonth = '2024-02'` and target 2024-04, the expected values are 600, 600 (with a 1000 budget in 2023-12) and 633 (with an extra -100 in 2023-12). The statement's example gives all three numbers, and its rule "current month = the shared month utilities, not system clock" makes the mocked current month take effect.
- Rounding: Math.round(-1900/3) = -633, which negates to 633. "rounded to an integer" is enough here.
- The template tests mock `./actions` with only `getCategoryAverage`, `getSheetValue`, `getSheetBoolean` and `isTrackingBudget`. The statement says the template "imports `getCategoryAverage` directly from that budget actions module and needs no other new export". That covers it.
- `toHaveBeenCalledWith({month: '2024-01' | '2024-03', maxMonths: 3, categoryId: 'test'})`, with exactly these keys and the unadjusted template month. The statement says to pass "the template's own month (unchanged…)", and the key names come from the signature.
- Converting the helper result: the mock returns -200 and the template returns 200; the mock returns -(200/3) and the template returns 67, through existing rounding. "turn it into a positive amount … existing … rounding then apply" covers this.

One thing is not fully pinned down. "turn it into a positive amount" is ambiguous when the helper returns a positive number (absolute value vs. negation), but no test exercises that case. The first-activity rule is specified but never actually decides a test outcome: in every test the earliest activity is 2023-11 anyway.
LEAK: minor, and justified by the tests:
- "the module that already exports `setNMonthAvg` and `set3MonthAvg`" and "imports `getCategoryAverage` directly from that budget actions module" fix a module location and an import structure. Both are needed, because the hidden test mocks `./actions` and asserts calls on it.
- "the same per-month 'spent' value the budget sheet already exposes" hints at the `sum-amount-<cat>` sheet cell. This is a mild hint about the data source.
- "has a budgeted amount recorded, or has a (non-deleted) transaction in an on-budget account" is close to the SQL in `getFirstActivityMonth`, but it reads as a behavioural definition.

None of this names `getAverageMonths`, `getFirstActivityMonth`, the SQL or the views.
FIX: Mostly none. Optionally:
- Say "if the average is positive it is used as is", which removes the abs-vs-negate ambiguity.
- Drop "the budget sheet already exposes" and keep only "the category's spent amount for that month (negative for spending)".
