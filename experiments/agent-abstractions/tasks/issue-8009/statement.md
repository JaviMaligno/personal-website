# Category learning never fires for payees whose learning flag is unset

Users report that category learning is turned on, yet after dozens of transactions to the same merchant with the same category no rule is ever created and new transactions for that merchant stay uncategorised.

Category learning is what happens when transactions are saved with learning enabled (the `learnCategories` option of the `transactions-batch-update` handler, which the transaction register uses): once at least three of a payee's most recent transactions share a category, a rule "payee is X → set category Y" is created for that payee, or the payee's existing learned rule is switched to the new category. Each payee also has its own opt-out, the `learn_categories` flag (turned off per payee from the payee manager, e.g. through `payees-batch-change`).

The problem: in real budget files the per-payee flag is not always 1 or 0. Payees can have no value at all for it (NULL) — in rows that already exist in the budget file, and when a change that arrives through sync from another device carries an empty value for that field. Such payees never learn anything, as if the user had opted them out, even though the user never turned learning off for them.

Expected behaviour:

- A payee whose learning flag is unset is treated like the default, i.e. learning is **on** for it. Saving transactions with learning enabled creates (and later updates) its category rule exactly as for a payee with learning explicitly on — whether the transactions are added in one batch, one at a time, or existing uncategorised transactions are given a category, and whether the flag was already empty in the stored row or became empty through a synced change.
- Only an explicit "off" (0 / `false`) opts a payee out. Turning learning off for a payee whose flag was unset must still stop learning for it.
- Everything else about learning is unchanged: payees with learning explicitly on keep learning, saves made without the learning option never create rules, fewer than three matching transactions are not enough, and each payee ends up with a single learned rule (visible through `rules-get`).
