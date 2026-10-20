# Let a link take over a bank account from another local account

Linking a bank account that another local account already holds is refused. Users who
want to move a bank feed to a different account (for example after starting a fresh
account for the same bank account) currently have to unlink the old account first and
then link the new one.

## Required behaviour

1. A request to link a bank account accepts a new optional flag,
   `replaceExistingLink: true`. Without it (or with `false`), linking behaves exactly
   as today, including the refusal when another local account already holds the bank
   account.
2. With the flag, when another local account holds the bank account, the link goes
   ahead (as a new account or into the chosen existing account) and the account that
   held it is unlinked: it is left as the "unlink account" action leaves an account
   (no bank, no provider account id, no sync source). It is not deleted, keeps its
   transactions and stays open or closed as it was. Nothing about that account is sent
   to the bank provider, since the bank connection is still in use by the new link.
3. With the flag and no other account holding the bank account, the link is an
   ordinary link.
4. The flag does not lift any other rule: in particular, linking into a closed
   account is still refused, and nothing changes in that case.
