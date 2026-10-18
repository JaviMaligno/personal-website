# Applying rule actions to existing transactions double-counts transfers

When money moves between two of my accounts, I often end up with two ordinary
transactions: one in each account, on the same date, with opposite amounts and
some regular payee. I then use rules to turn those payees into transfers and
apply them to the existing transactions with the rule editor's "Apply actions"
button (the `rule-apply-actions` handler).

Steps to reproduce:

1. Create account A and account B.
2. In account A, add a transaction with payee "b" for 25.00 (inflow).
3. In account B, add a transaction with payee "a" for -25.00 (outflow), same date.
4. Create a rule that sets the payee to the transfer payee of account A, and
   apply its actions to the existing transaction in account B.
5. Create a rule that sets the payee to the transfer payee of account B, and
   apply its actions to the existing transaction in account A.

What happens: each application creates a brand new transfer leg in the other
account instead of recognising the transaction that is already there. The
result is four transactions, and the balances are doubled: A ends up at +50.00
and B at -50.00.

What I expect: the two existing transactions get linked to each other as the
two sides of one transfer, whichever of the two I apply the rule to first.
Afterwards there are exactly two transactions, one in each account, each one
showing the other account's transfer payee and linked to the other, and the
balances are A = +25.00 and B = -25.00.

A transaction in the other account that is not the counterpart (for example a
different amount) must not be swallowed: in that case turning a transaction
into a transfer should keep working as it does today and create the other leg.
