# Importing transactions does not detect duplicates within the same import

When transactions are imported into an account (the `transactions-import` handler, which backs the API's `importTransactions`), a row whose `imported_id` already exists in that account is recognised as the same transaction and is not added again. That only works across separate imports, though. If a single import contains two or more rows with the same `imported_id`, every one of them is inserted as a new transaction, so the account ends up with duplicates and its balance counts the same money more than once. Importing the same rows in separate, consecutive calls behaves correctly.

Example: importing `[{date: '2024-03-05', amount: -2599, payee_name: 'Coffee Shop', imported_id: 'csv-hash-1'}, <the same row again>]` in one call creates two transactions and a balance of -51.98 instead of one transaction and -25.99.

Expected behaviour: a repeated `imported_id` within one import into an account is handled exactly as if the rows had been imported one after another in separate calls. In particular:

- only one transaction is created per `imported_id` (the first occurrence), and later occurrences are reconciled against it with the usual import rules — e.g. the first row's amount is kept, and a later row can still fill in details the first one lacked, such as empty notes;
- a row explicitly flagged with `forceAddTransaction` is still added, as it would be in a separate import;
- rows with different `imported_id`s, and rows without an `imported_id`, are not affected, even when they are otherwise identical;
- a preview of the import (`isPreview`) reports the same additions the real import would make and writes nothing;
- the result of the import (`added`) lists only the transactions actually created.
