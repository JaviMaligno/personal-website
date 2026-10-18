# Importing a transaction silently merges it into one part of an existing split

When I import transactions into an account (through the API's transaction import, or the `transactions-import` handler the import dialog uses), some of them are never added. They are merged into one part of a split transaction that is already in the account.

How to reproduce:

1. Import a transaction of -18.00 with an imported ID of `A`.
2. Split it into two parts of -9.00 each (the parts have no imported ID of their own).
3. A few days later, import a new, unrelated transaction of -9.00 with an imported ID of `B` and a different payee.

What happens: nothing is added. The new transaction is taken to be one of the two -9.00 parts of the split, so that part's imported ID, imported payee and notes are overwritten with the new transaction's data, and the -9.00 never shows up in the account. The account balance is now wrong by -9.00, and the split, which already corresponds to its own imported transaction `A`, is quietly altered.

The same thing happens on bank syncs: a bank transaction is split across categories, and a later, separate bank transaction whose amount equals one of the parts is swallowed by that part instead of being added.

Expected: a part of a split that already corresponds to an imported transaction must not be taken as the match for a different incoming transaction. The incoming transaction should be added as a new transaction (with its own amount, imported ID, payee and notes), the account balance should include it, and the existing split (parent and parts) should stay exactly as it was. This also applies when several incoming transactions each equal one of the parts.

Matching that is legitimate today must keep working:

- An import whose amount equals the whole split still matches the split itself (for example, a split entered by hand that the bank later confirms), instead of adding a duplicate.
- A plain transaction entered by hand is still matched by the corresponding import.
- Existing behaviour around splits that have no imported counterpart yet (for example, bank sync matching one of the parts of a hand-entered split) should not regress.
