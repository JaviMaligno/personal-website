# Bank sync keeps rewriting transactions whose provider category is not a budget category

Some bank-sync providers attach their own category label to each transaction they
return (for example `"Same person transfer"` or `"Groceries"`). That label is a
free-text name chosen by the provider, not the id of a category in the user's
budget.

Today the importer passes that value through as the transaction's category. When an
already-imported transaction is matched again on a later sync, the provider label is
seen as a change, so the existing transaction is rewritten on every sync even though
nothing changed at the bank. The bogus value never sticks (it is not a valid
category), so the next sync sees the same difference again and the rewrite repeats
forever, flooding the budget's sync history with no-op changes. Transfers, which can
never carry a category, are always affected.

## Required behaviour

- When bank sync imports the transactions returned by a provider, a provider
  category is kept only if it is the id of an existing category in the budget.
  Any other value (a provider label, an unknown id) is treated as "no category".
- Consequently, re-syncing a transaction that has not changed at the bank must not
  modify the stored transaction, even if the provider now reports a category label
  for it that it did not report before. In that case the only changes a sync makes
  are to the account's own sync bookkeeping (current balance, sync status, last sync
  time): no transaction is reported as matched or changed, and the transaction's
  category stays `null`.
- Imports of new transactions, matching, and categories that *are* valid budget
  category ids behave exactly as before.

This applies to every bank-sync provider (SimpleFIN batch sync included), not only
to the one where the problem was first reported.
