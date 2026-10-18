# Split rule formulas cannot read the parent transaction's text fields

Rules can split a transaction, and a split's amount can be computed with a
spreadsheet-style formula (`set-split-amount` with `method: 'formula'`). Inside such
a formula the parent transaction's amount is available as the named value
`parent_amount` (in integer minor units, e.g. `=INTEGER_TO_AMOUNT(parent_amount) / 2`),
but nothing else about the parent is. A common need is to compute a split from the
bank's description, e.g. notes `Payment in USD: ITEM: 25.50USD FEE: 4.50USD` where the
first split should be the ITEM amount and the second the remainder. Using `notes`
inside the formula does not work reliably, because split actions also set the
child's own fields (a child can get its own notes).

## Required behaviour

1. In split-amount formulas, in addition to `parent_amount`, the following named
   values hold the **parent** transaction's fields, independent of anything the
   split actions set on the child:
   - `parent_notes` (the parent's notes),
   - `parent_imported_payee`,
   - `parent_payee` (the parent's payee id),
   - `parent_account` (the parent's account id).

   A missing value is the empty string (`parent_notes = ""` when the transaction
   has no notes).

2. These text values are always treated as **literal text** in the formula, even
   when they look like a formula, a number, a date or start with an apostrophe:
   with notes `=1+1`, `00123`, `2024-01-15` or `'quoted`,
   `=IF(parent_notes="<the notes>", -1, -2)` evaluates to -1.

3. Example: with the notes above,
   `=-VALUE(MID(parent_notes, SEARCH("ITEM: ", parent_notes)+6, SEARCH("USD", parent_notes, SEARCH("ITEM: ", parent_notes))-SEARCH("ITEM: ", parent_notes)-6))`
   on split 1 and `remainder` on split 2 of a -30.00 transaction give splits of
   -25.50 and -4.50.

4. These helper values (and `parent_amount`) never end up on the resulting
   transactions: once rules have been applied and the transaction is finalised
   for saving, neither the parent nor the children carry any `parent_*` field
   other than the children's normal `parent_id`.

5. End to end: importing a bank transaction into an account where such a rule
   applies (with other split actions setting payee, e.g. a transfer payee, and
   category on each split) produces exactly one parent that keeps its imported id,
   notes, imported payee, amount, cleared state and any matching schedule, two
   children whose amounts sum to the parent's, and a single transfer transaction
   for the transfer split. Importing the same bank transaction again changes
   nothing (same transactions, no second transfer).
