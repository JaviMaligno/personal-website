# File import silently merges a genuinely new transaction that shares an amount with an existing one

When importing a file (CSV/OFX/QIF) into an account, the import dialog first asks the server for a preview, and then sends the rows the user kept to the real import. Both go through the `transactions-import` handler (`isPreview: true` for the preview, `isPreview: false` for the import). The duplicate detection runs from scratch each time, and its result depends on which other rows are in the batch. Because the user can uncheck rows between the two calls, the real import can make different decisions from the ones the preview showed. As a result, transactions can be lost.

## Reproduction

1. An account has one transaction: Netflix, -8.99, dated 2026-03-10.
2. Import a file with two rows:
   - 2026-03-10, Netflix, "Subscription", -8.99 (a true duplicate)
   - 2026-03-08, Corner Coffee, "Latte and croissant", -8.99 (a genuinely new purchase)
3. The preview matches the Netflix row to the existing Netflix transaction. Corner Coffee shows as a plain new transaction with no match.
4. The user unchecks the duplicate Netflix row and imports only Corner Coffee.

**Actual:** Corner Coffee is never created. It is silently merged into the existing Netflix transaction (the Netflix transaction's imported payee becomes "Corner Coffee"), and the account balance stays at -8.99. There is no error or warning.

**Expected:** Corner Coffee is added as a new transaction, the existing Netflix transaction is left as it was, and the balance becomes -17.98.

The same divergence affects merges. Suppose the preview matched a row to one existing same-amount transaction, and the user unchecked another row. The import can then merge the remaining row into a *different* existing transaction from the one the preview displayed.

## What we want

The import must honour the decisions shown in the preview. The dialog should be able to pass the preview's decision for each row to the import. Each transaction given to `transactions-import` may carry an optional `matchedTransactionId` field:

- a string id: the preview matched this row to that existing transaction. The import merges the row into exactly that transaction (the same merge as today), regardless of which other rows are in the batch.
- `null`: the preview found no match for this row. The import adds it as a new transaction, even if an existing transaction has the same amount on a nearby date.
- absent: no preview decision is available (e.g. API callers or bank sync). The import behaves as it does today, so re-importing an already imported row is still detected as a duplicate and does not create a second transaction.

`matchedTransactionId` is an instruction for the import only. It must never be stored on the transaction. Results must not depend on the order of the rows in the batch. The preview's own output stays as it is today: matched rows report the existing transaction they matched.

Update the import dialog so that it passes these decisions along for the rows it imports.
