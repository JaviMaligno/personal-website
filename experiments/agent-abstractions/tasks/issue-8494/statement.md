# Weekly "Cover schedule" automation under-budgets the next month when the current month has spending

I budget one month ahead for a weekly recurring cost (for example rent of $100 every Friday) with a **"Cover schedule"** budget automation on its category, linked to a weekly schedule, savings mode "Save up for the next occurrence". This is in the envelope budget.

What works today:

1. Applying the budget templates to the current month budgets the full total for that month's occurrences (e.g. $400 for a month with 4 Fridays).
2. If nothing has been spent from the category yet this month, overwriting the templates on the **next** month also budgets that month's full total (e.g. $400).

What goes wrong: as soon as an expense has been recorded against the category in the current month, overwriting the templates on the next month only budgets enough to top up the shortfall against the current month's remaining balance (e.g. +$100 after a $100 expense, +$200 after two), instead of the full total for the next month's own occurrences. The amount budgeted for the next month silently depends on unrelated spending in the current month. For comparison, a plain "Fixed amount" automation of $100/week budgets 4 x $100 for each month regardless of spending.

Expected behaviour:

- Applying a "Cover schedule" automation to the month after the current one budgets the full total of that month's scheduled occurrences (number of occurrences falling in that month x the schedule amount, exact to the cent), whether or not money was already spent from the category in the current month, and whether or not that spending is linked to the schedule.
- The result for the next month is the same with or without spending in the current month.
- Applying the automation to the current month keeps working as it does today, and the current month's budgeted amount is not changed by budgeting the next month.
