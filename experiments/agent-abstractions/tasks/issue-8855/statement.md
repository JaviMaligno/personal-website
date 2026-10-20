# Importing transactions creates payees that no transaction ends up using

I import transactions from my bank with a script that calls `transactions-import` (also reached through the API's import) every day, always sending the full recent history. Each row carries the bank label as its payee name and imported payee (e.g. `FOOBAR`) and the bank's `imported_id`. I have a rule "if imported payee is `FOOBAR`, set the payee name to `FooBar, Inc`".

Most rows I send already exist in Actual: they match an existing transaction by `imported_id`, and that transaction keeps the payee it already has. Even so, the import creates the payee named by the rule, although no transaction is linked to it. The same happens when the import is only a preview (`isPreview: true`): nothing is imported, yet a payee is created. These payees are synced changes, and my payees table keeps growing with entries I never use (deleting them only adds deleted rows).

Expected behaviour:

- An import never creates a payee that no transaction ends up using. In particular, when a row matches an existing transaction by `imported_id` and that transaction keeps its payee, the import creates no payee at all, not even one that is deleted again afterwards (no new payee rows, deleted ones included, and no payee changes recorded for sync).
- A preview import (`isPreview: true`) creates no payee and changes nothing.
- When a payee does end up used (a new transaction, or an existing transaction that had no payee yet, gets the payee name set by a rule), it is created exactly once and linked, as today. Several rows in one import that resolve to the same new payee name share a single payee.
- Rules that set the payee to an existing payee keep working as they do today.
