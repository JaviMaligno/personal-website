# Let importers keep payee names as given (no forced title case)

When transactions are imported through the `transactions-import` handler (used by
the API's `importTransactions`), each `payee_name` is trimmed and then title-cased.
Title casing lowercases the whole string before capitalising each word, so acronyms
do not survive it: `Nintendo Store New York NY` becomes `Nintendo Store New York Ny`
(both as the created payee's name and as the transaction's `imported_payee`).
Custom importers that already supply final payee names have no way to opt out.

## Required behaviour

1. **New import option.** The `opts` of `transactions-import` (the
   `ImportTransactionsOpts` type, alongside `defaultCleared`, `dryRun`,
   `reimportDeleted`) accept `payeeNameNormalization?: 'original' | 'title-case'`.
   - Omitted (or `'title-case'`): behaviour unchanged, names are trimmed and
     title-cased.
   - `'original'`: names are only trimmed (`'  Nintendo Store New York NY  '` →
     `Nintendo Store New York NY`, for both the new payee and `imported_payee`).
   - Any other value is rejected: the handler throws an API error whose message
     mentions `payeeNameNormalization` and lists the allowed values, before
     anything is imported (no payee is created).
   - Document the option in the API reference of `importTransactions`.

2. **Reconcile options object.** The server-side bank/import reconciliation
   function `reconcileTransactions(acctId, transactions, ...)` (in the accounts
   sync module) and its matching step `matchTransactions` currently take a long
   list of trailing positional flags. Replace those trailing flags with a single
   optional options object, so callers write e.g.
   `reconcileTransactions(id, transactions, { reimportDeleted: false })` or
   `reconcileTransactions(id, transactions, { strictIdChecking: false })`:

   - `reconcileTransactions(acctId, transactions, options = {})` with
     `{ isBankSyncAccount?, strictIdChecking?, isPreview?, defaultCleared?,
     updateDates?, reimportDeleted?, payeeNameNormalization? }`, defaults as today
     (`isBankSyncAccount` false, `strictIdChecking` true, `isPreview` false,
     `defaultCleared` true, `updateDates` false, `reimportDeleted` unset,
     `payeeNameNormalization` title-case);
   - `matchTransactions(acctId, transactions, options = {})` with
     `{ isBankSyncAccount?, strictIdChecking?, reimportDeleted?,
     payeeNameNormalization? }`.

   Update every caller. `reconcileTransactions(id, transactions)` with no options
   still title-cases payee names. Bank sync and the manual "add transactions" path
   behave exactly as before.
