# Monthly schedules on the 29th, 30th or 31st skip the months that are too short

A monthly schedule set to a day that some months do not have (the 29th, 30th or
31st) silently skips those months. For example, a monthly schedule starting on
31 May produces nothing in June: the next occurrence after 31 May is 31 July.
The same happens to a schedule on the 30th in February, and to one on the 29th
in a February that is not in a leap year. Users only notice when a payment is
missing from their budget, and schedules that post transactions automatically
never post the skipped month at all.

"Last day of the month" is not a workaround: a bill that is due on the 30th
should still fall on the 30th in 31-day months.

## Required behaviour

When a monthly schedule falls on a day of the month that a given month does not
have, that month's occurrence falls on the **last day of that month** instead of
being skipped.

- 31st: 30 June, 30 September, 28 February (29 February in leap years), and so on.
- 30th: 28 February, or 29 February in leap years.
- 29th: 28 February in common years; in leap years it stays on 29 February.
- The adjustment only applies to the short month itself: the following months
  go back to the chosen day (31 May -> 30 June -> 31 July -> 31 August ...), the
  date never drifts.
- This applies both to a schedule that just repeats monthly from its start date
  and to one with one or several explicit days of the month. With several days,
  only the ones that do not exist in that month move (15th and 31st in February
  -> 15 and 28 February).
- A given date is never produced twice. When two of the chosen days end up on
  the same last day, that date occurs once (30th and 31st: 28 February once;
  30 April once).
- "Last day of the month" schedules behave exactly as before.

This must hold everywhere the schedule's dates are used:

- the list of upcoming dates shown when editing a schedule
  (`schedule/get-upcoming-dates`);
- the schedule's next date when it is computed or recomputed
  (`schedule/create`, `schedule/update` with `resetNextDate`), and when the next
  occurrence is skipped (`schedule/skip-next-date`);
- schedules that post transactions automatically: when the app catches up on
  missed occurrences (`schedule/force-run-service`), the short-month occurrence is
  posted on the last day of that month, with the schedule's amount and account,
  exactly once, and the schedule then moves on to the following occurrence.

Weekend handling, end dates/occurrence counts and the other frequencies (daily,
weekly, yearly) are otherwise unchanged.
