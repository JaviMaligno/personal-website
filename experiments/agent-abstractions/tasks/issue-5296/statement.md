# Let a schedule carry its own note and category onto the transactions it posts

I pay several subscriptions to the same payee, on the same day of the month, for exactly the same amount (for example two -12.99 charges from the same app store: one is "PBS Kids", the other "Curiosity Stream"). I have one schedule for each, and I want each posted transaction to say which subscription it is and to land in the right category.

Today the only way to get a note or a category onto a scheduled transaction is to edit the schedule's rule and add actions to it. That is clumsy, and when I click "Create transaction now" on an upcoming schedule, or the schedule posts automatically, I have to retype the note by hand. A schedule should simply be able to hold a note and a category, the way it already holds a payee, an account, an amount and a date.

## What I'd like

- When a schedule is created or edited (the `schedule/create` and `schedule/update` handlers, which take `{ schedule, conditions }` / `{ schedule, conditions?, resetNextDate? }`), the `schedule` object may carry two optional fields:
  - `notes`: a string, the note to put on transactions the schedule posts;
  - `category`: the id of a category to put on those transactions.
- Every transaction the schedule posts gets that note and that category, together with the payee, account, amount and date it already gets. This applies to every way a schedule posts a transaction:
  - posting the schedule's transaction (`schedule/post-transaction` with the schedule id), on its due date;
  - "Create transaction now" (`schedule/post-transaction` with `today: true`), which posts it dated today;
  - automatic posting for schedules set to post transactions automatically, when the schedules service runs.
- Two schedules with identical payee, account, amount and date but different notes/categories must stay distinct: each posted transaction carries the note and category of the schedule that posted it, and both transactions exist with their full amounts.
- Editing a schedule's note or category changes what later postings get; transactions that were already posted keep the note and category they were posted with.
- Editing other fields of a schedule (for example renaming it) without mentioning `notes` or `category` keeps the note and category it has. Setting `notes` or `category` to `null` removes it, so later postings get no note / no category.
- A schedule with no note and no category behaves as it does today: its transactions are posted uncategorized and without a note.

The posted amount must still be exactly the schedule's amount, and none of this should change how the schedule's rule matches imported or manually entered transactions.
