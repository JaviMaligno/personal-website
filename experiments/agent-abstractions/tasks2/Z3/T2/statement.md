# Bank sync with Fintegra

The sync server now supports a new bank-sync provider, **Fintegra**. Actual needs to
be able to link Fintegra accounts and import their transactions, like it does for the
providers it already supports. The client UI is handled separately; this change is
the server side only.

## The sync server's Fintegra API

- Base path: the sync server URL followed by `/fintegra`, next to the other
  providers' base paths.
- Transactions: `POST <base>/transactions` with the JSON body
  `{ "accountId": <Fintegra account id>, "startDate": "YYYY-MM-DD" }` and the
  `X-ACTUAL-TOKEN` header carrying the signed-in user's token, exactly as for the
  other providers. The response has the same format as the other providers'
  transaction endpoints: `{ "transactions": { "all": [...], "booked": [...],
  "pending": [...] }, "balances": [...], "startingBalance": <integer amount> }`, or
  `{ "error_type": ..., "error_code": ... }` on failure.
- A Fintegra account, as returned to the client when it lists accounts, looks like
  `{ "account_id": "...", "name": "...", "institution": "...", "orgId": "...",
  "balance": <number> }`.

## Required behaviour

1. A new request, `fintegra-accounts-link`, takes
   `{ externalAccount, upgradingId?, offBudget?, startingDate?, startingBalance? }`
   (with `externalAccount` a Fintegra account as above) and resolves to `'ok'`. It
   links the Fintegra account with the same behaviour as linking an account from the
   other providers: a new local account (on or off budget) or, with `upgradingId`, an
   existing local account turned into a bank-synced one; the initial import with the
   chosen starting date and balance; the client notified that transactions and
   accounts changed; and the refusal to link a bank account that another local
   account already holds, with the same error.
2. Fintegra accounts are stored with the sync source `fintegra`. A new account's
   name and official name are both the Fintegra account name.
3. Accounts are grouped under one bank entry per Fintegra organisation (`orgId`)
   and institution name.
4. Later syncs of a linked Fintegra account download its transactions from the same
   endpoint.
