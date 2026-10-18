# Splitting a transfer: the other account should get one matching split, not loose pieces

Reported by users:

> I split a transaction that is a transfer to an off budget account. In the off
> budget account, it does not allow you to link to the transfer, but ends up adding
> 2 transactions. [...] I would expect that the split would exist on both accounts
> and not show up as 2 new transactions.

Another user sees the same with two on-budget accounts.

## Current behaviour

Take a transfer of 30.00 from *Checking* to *Savings* (off budget or on budget).
Savings shows one +30.00 transaction, linked as the other side of the transfer.

Now split the Checking transaction into lines that all keep the transfer to Savings
as their payee, e.g. 20.00 + 10.00. Afterwards Savings no longer has a single +30.00
transaction: it has two separate, unrelated-looking transactions (+20.00 and +10.00).
A +30.00 transaction that the bank reports for Savings can no longer be matched to
the transfer, so in practice users end up with the money counted twice. The only
workaround today is to rebuild the split by hand on the Savings side.

## Wanted behaviour

When the lines of a split transaction transfer to the same account, the other
account must show the transfer as **one transaction for the full amount, split into
lines that mirror the lines on the first side**:

- Savings has exactly one top-level transaction for the transfer (+30.00), and it is
  a split whose lines are +20.00 and +10.00.
- Every line on each side that has a transfer payee is linked to its counterpart
  line on the other side (and the link goes both ways), with the opposite amount.
- On both sides a split's total always equals the sum of its lines, and each
  account's balance counts the transfer exactly once.

This must hold however the split is produced:

- splitting an existing transfer by giving the lines explicitly (the parent keeps
  the transfer payee), or splitting it from the transaction list (the parent's
  payee is cleared and the lines carry the transfer payee);
- entering a brand-new split transaction whose lines all transfer to that account;
- editing the line amounts afterwards (both sides stay in step);
- deleting the split: its counterpart in the other account disappears completely,
  with nothing left behind.

Splits whose lines transfer to *different* accounts keep working as today: each
target account gets one ordinary transfer per line.

All of this goes through the normal server handlers the app uses
(`transactions-batch-update` for transaction changes, `account-create` for
accounts), and the result must be what is stored in the budget file.
