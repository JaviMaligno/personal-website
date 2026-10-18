# Updating one part of a split transaction through the API wipes its amount and category

When a split transaction exists and an API client updates just one of its parts
(sub-transactions) with a partial set of fields, the fields that were not sent are
lost. For example, with a split of -100.00 made of a -60.00 "Groceries" part and a
-40.00 "Household" part, calling the API's transaction update (the `api/transaction-update` handler, which
takes an `id` and the `fields` to change) on the Groceries part with only
`{ notes: 'New notes' }` saves the new note but the part ends up with amount 0 and no
category. The same partial update on a transaction that is not split works correctly.

Expected behaviour when updating one part of a split through the API:

- Only the fields that were sent change; every other field of that part (amount,
  category, notes, ...) keeps its previous value. This holds for any partial update
  (notes only, category only, ...) and for several partial updates in a row.
- The rest of the split is untouched: the parent keeps its amount and notes, the other
  parts keep their values, no part is added or removed, and the parts still add up to
  the parent's amount.
- The change is saved by the time the update call resolves, so reading the
  transactions (through the API or from the budget file) right after the call returns
  sees it.
