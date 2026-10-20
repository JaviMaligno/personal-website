# A bank account can only be linked to one local account

Nothing stops the same bank account from being linked twice. If a user links a bank
account that is already linked, either as a new account or into another existing
account, Actual ends up with two local accounts fed by the same bank feed, and every
transaction is imported into both. Users then delete one of them by hand, usually
after the duplicates have already been categorised.

## Required behaviour

1. **Refuse a second link.** Linking a bank account must be refused when that bank
   account is already linked, through the same bank-sync provider, to another local
   account. The request fails with the error
   `This bank account is already linked to another account.`
   and changes nothing: no account or payee is created, an existing account that was
   chosen to receive the link is left exactly as it was, the sync server is not
   contacted and the client is not told that a sync happened.
2. **What counts as linked.** A local account holds the link to a bank account when it
   is not deleted (closed accounts still hold their link) and its provider and the
   provider's account id are the ones being linked. A deleted account does not hold
   a link. The same provider account id under a different provider is a different
   bank account.
3. **Re-linking is unchanged.** Linking a bank account into the very account that
   already holds it (for example to refresh an expired connection) keeps working as
   today.

Everything else about linking (which bank entry is used, the initial import, the
starting balance, off-budget accounts) is unchanged.
