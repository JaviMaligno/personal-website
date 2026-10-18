# One definition of linking a bank-sync account

When a user links an account from a bank-sync provider, the app either upgrades the
chosen local account or creates a new account with its transfer payee, then runs the
account's first sync and tells the client that the sync finished. This linking logic is
currently repeated rather than defined once.

Move this logic into one shared definition and have the code that needs it use that
definition, so that a future change to the logic is made once.

This is a refactor. Behaviour must not change: whatever the app does today it must
still do, with the same results, including any edge case where current results differ
from one another. Keep the public interface (requests, their parameters and their
results) as it is.
