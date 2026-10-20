# A closed account cannot be linked to a bank account

A user can pick a closed account as the account to link a bank account into. The
link goes through: the account stays closed but starts receiving bank transactions,
which then do not show up anywhere the user looks, and its balance silently drifts.

## Required behaviour

1. Linking a bank account into an existing local account that is closed must be
   refused with the error
   `Closed accounts cannot be linked to a bank account. Reopen the account first.`
   Nothing changes: the account is left exactly as it was, nothing is created, the
   sync server is not contacted and the client is not told that a sync happened.
2. This also applies when the closed account is the one that already holds the link
   to that bank account (re-linking it).
3. Once the account is reopened it can be linked as usual. Linking a bank account as
   a new account is not affected.

The rule that a bank account can only be linked to one local account is unchanged.
