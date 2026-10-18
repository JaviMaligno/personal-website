# Merge two transactions through the API, and refuse to merge a transaction with itself

The app can merge two duplicate transactions (for example a manually entered one and
the same transaction imported from the bank) into one: the kept transaction takes
the useful fields of the other, which is deleted. This is only available from the
UI. Integrations built on the public API (`@actual-app/api`) cannot do it.

## Required behaviour

1. **API method.** Add `mergeTransactions(ids)` to the public API, where `ids` is a
   pair of transaction ids `[id1, id2]`. It merges the two transactions with exactly
   the same rules, validation and result as the UI merge action, and resolves to the
   id of the transaction that is kept. Like the other mutating API methods it
   requires an open budget. Document it in the API reference next to the other
   transaction methods.

2. **Same transaction twice.** Merging currently accepts the same transaction id
   given twice: it passes the "exactly two transactions" check and ends up
   deleting that transaction. Merging must instead be rejected when the two ids are
   not distinct. The error is the existing "wrong number of transactions" error,
   whose message must now read
   `Merging is only possible with 2 distinct transactions, but found ...`
   (followed, as today, by the JSON of the transactions that were passed). It is
   used for both cases (not exactly two ids, or two equal ids). The transaction
   must be left untouched.

All other merge behaviour (amount checks, unknown ids, which fields are kept) is
unchanged.
