# Rules that turn an API-added transaction into a transfer leave the other account untouched

I have a rule that says "when the account is Checking, set the payee to the transfer payee for Savings" (i.e. the payee "Transfer: Savings"). When I add a transaction to Checking through the API's `addTransactions` method with its default options (for example `{ date: '2026-01-21', amount: -12300, notes: 'Some notes' }`), the rule runs: the new transaction in Checking shows the Savings transfer payee. But nothing appears in Savings and its balance does not change. The transaction looks like a transfer in Checking but there is no other side.

Expected: when a rule assigns a transfer payee to a transaction added through the API, the result is a real transfer, just as if the transfer had been entered in the app:

- the destination account gets exactly one counterpart transaction with the opposite amount and the same date;
- the two transactions are linked to each other as a transfer (each one refers to the other);
- both account balances reflect the movement.

This must also hold when several transactions are added in one call (one counterpart each), and when the caller explicitly asks the API to process transfers (there must still be exactly one counterpart, never two). Transactions that the rule does not match must not create anything in other accounts.
