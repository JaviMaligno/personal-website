# Bank sync shows the wrong bank for a second connection to the same bank

When accounts are linked through a bank-sync provider, each connection gets a bank
record (a row of the `banks` table, with the provider's identifier in `bank_id` and
the institution's display name in `name`); `findOrCreateBank(institution, bankId)`
in the server's account-linking code finds the record for a connection or creates
it.

The record is currently looked up by the provider identifier alone. SimpleFIN
reports the institution's domain as that identifier, so two separate logins at the
same bank (e.g. one per family member, reported as "Robinhood (Person A)" and
"Robinhood (Person B)", both with identifier `robinhood.com`) collapse into a single
bank record, and accounts linked through the second connection are listed under the
first connection's name on the Bank Sync page.

In addition, some providers report the institution as a plain string rather than an
object with a `name`; the lookup then fails with an error.

## Required behaviour

`findOrCreateBank(institution, bankId)`:

- `institution` may be an object with a `name` (which may be `null`), a plain
  string (which is the name), or `null`/`undefined` (no name). The institution
  name is therefore that string, that `name`, or `null`.
- An existing bank record is reused only if **both** its `bank_id` equals `bankId`
  and its `name` equals the institution name, where a `null` name matches a
  record whose name is `null`. Otherwise a new record is created with that
  `bank_id` and name.
- It returns the bank record (at least its `id` and `bank_id`), as today.

Examples, with identifier `robinhood.com`:
- linking `{ name: 'Robinhood' }` twice → one record, the same `id` both times;
- `{ name: 'Robinhood (Person A)' }` then `{ name: 'Robinhood (Person B)' }` → two
  records with different ids and their own names;
- `null` then `{ name: null }` → one record, with a `null` name;
- `'Robinhood'` (a string) then `{ name: 'Robinhood' }` → one record.
