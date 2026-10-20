# YNAB4 import: split children lose the parent's payee

A YNAB4 export stores the payee of a split transaction on the parent only; its sub
transactions carry no payee of their own. After importing such a budget, the
non-transfer children of a split show up with **no payee**, instead of inheriting
the parent's payee as split children normally do.

The cause is in how the YNAB4 importer builds the children it sends when adding the
imported transactions: every non-transfer child is given an explicit `payee` field
even when no payee was resolved for it (the field is present with an `undefined`
value). A child that carries a `payee` key is treated as having an explicit payee,
so it never falls back to the parent's.

## Required behaviour

- When the YNAB4 importer adds a split transaction, a non-transfer child for which
  no payee was resolved must **not have a `payee` property at all** in the
  transaction data it submits, so that building the child from its parent gives it
  the parent's payee.
- Transfer children are unchanged: they keep the transfer payee of the other
  account and their `transfer_id` linking them to the counterpart transaction.
  Non-transfer children keep `transfer_id: null`.
- The parent keeps its payee and its `imported_payee` (the YNAB4 payee name).
- The function of the YNAB4 importer module that imports the transactions,
  `importTransactions(data, entityIdMap, tick)`, must be exported from that module
  (it is currently module-private) so it can be exercised on its own.
