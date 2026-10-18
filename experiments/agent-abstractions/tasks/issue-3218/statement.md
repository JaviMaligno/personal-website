# Starting Balance is not created when an account already holds only transfers from other accounts

When an account is synced with its bank (SimpleFIN) for the first time, or synced again after all of its transactions were deleted, Actual creates a "Starting Balance" transaction so that the account's running balance matches what the bank reports. That works for an empty account, but not when other accounts have already put transfers into it.

To reproduce:

1. Have two accounts, "Account 1" and "Account 2", both linked to SimpleFIN.
2. Create a rule (pre stage) that turns a transaction imported into Account 1 into a transfer to Account 2 (condition on the account and the imported payee, action: set payee to Account 2).
3. Delete all transactions in both accounts.
4. Sync Account 1, then sync Account 2 once Account 1 has finished.

Account 1 gets its Starting Balance, and the rule creates the transfer leg in the otherwise empty Account 2. When Account 2 syncs, no Starting Balance is created because the account "already contains transactions" (only that transfer), so Account 2's balance no longer matches the bank. The same happens when an account that so far only holds transfers made from other accounts is linked to SimpleFIN.

Expected behaviour:

- When an account is synced and everything it holds is transfer legs coming from other accounts (or it holds nothing at all), it is treated like a brand-new account: a single Starting Balance transaction is created, computed exactly as for an empty account (the bank's current balance minus the downloaded transactions), dated no later than the account's other transactions. After the sync, the account's total equals the balance reported by the bank (the downloaded transaction that corresponds to an existing transfer leg is matched with it, as today).
- This applies to linking an existing account to SimpleFIN, to syncing a single account, and to the SimpleFIN "sync all accounts" batch sync.
- Syncing again must never add a second Starting Balance, including for an account whose only bank activity is the transfer itself.
- An account that already holds transactions of its own (anything other than transfer legs from other accounts) keeps today's behaviour: no Starting Balance is added on sync.
