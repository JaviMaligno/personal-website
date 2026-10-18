# Posting a later upcoming occurrence of a schedule posts it on the first upcoming date

When the "upcoming" period is long enough, a recurring schedule shows several
upcoming occurrences at once (for a weekly payment: the next one, the one a week
later, the one two weeks later, ...). The user can pick any of them and post it.

Today, whichever occurrence is picked, the transaction is always created on the
schedule's **next date** (the first upcoming occurrence). Example with a weekly
schedule whose upcoming occurrences are Jan 2, Jan 9 and Jan 16:

1. Post the Jan 2 occurrence: a transaction dated Jan 2 is created. Correct.
2. Post the Jan 9 occurrence: a *second* transaction dated Jan 2 is created, and
   the Jan 9 occurrence is still shown as upcoming.

## Required behaviour

The server handler that posts a schedule's transaction, `schedule/post-transaction`,
currently takes the schedule `id` and an optional `today` flag. It must also accept
an optional `date` (a `YYYY-MM-DD` string) naming the occurrence to post:

1. **Posting a chosen occurrence.** With `{ id, date }`, exactly one transaction is
   created for the schedule, dated `date`, with the schedule's account, payee and
   amount, and linked to the schedule, just like posting the next occurrence. No
   transaction is created on the schedule's next date.

2. **Keeping the schedule's next date consistent.** After posting an occurrence
   that is later than the schedule's current next date, the schedule's next date
   must move to the occurrence that follows the posted one (for the example above:
   posting Jan 9 while the next date is still Jan 2 leaves the next date at Jan 16).
   The schedule must not keep offering, as its next date, an occurrence that is
   on or before one that was just posted; posting "the next occurrence" afterwards
   must therefore not create a duplicate of an already posted date.

3. **Unchanged behaviour.** Without `date`, posting works as today: `{ id }` posts
   on the schedule's next date, and `{ id, today: true }` posts on the current day.

The UI should send the date of the occurrence the user picked, so that posting a
later upcoming occurrence from the account view creates it on its own date.
