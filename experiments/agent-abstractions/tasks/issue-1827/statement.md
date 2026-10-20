# Re-importing a transaction ignores a changed amount

I import transactions from my bank with the API's `importTransactions` call, giving each one the bank's id as `imported_id`. When I import again and a transaction with the same `imported_id` already exists in the account, no duplicate is created (good), but if the bank has since changed the amount (a pending charge that settled for a different value, a tip added, a payment that turns out to be a deposit), the import silently keeps the old amount. My account balance stays wrong and I have to fix every such transaction by hand.

Expected: when an import matches an existing transaction in the account by `imported_id` and the imported amount differs, the existing transaction takes the imported amount. It is the same transaction (same id, no new one added), the import result lists it among the updated transactions, and the account balance reflects the new amount. Transactions in the same import whose amount did not change stay as they are, and new rows are still added as usual. A preview import (`isPreview`) must report such a transaction as one that would be updated (not as ignored) and must not write anything.

What the user did to the transaction must survive the re-import:

- notes the user wrote are kept;
- the cleared status is never turned off by an import, and a re-imported row that does not say whether it is cleared leaves the existing cleared status as it is;
- a reconciled (locked) transaction is not touched at all, including its amount;
- a transaction the user has split into parts keeps its total and its parts unchanged (the import cannot know how to divide a new amount between the parts, so the parts must still add up to the total);
- if the user turned the transaction into a transfer to another account, the transfer stays consistent: the other account's side takes the opposite of the new amount and both balances reflect it.
