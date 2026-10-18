# Daily schedules never show missed or due occurrences

I have a schedule that repeats every day, with an approximate date ("is approx"),
and that I post by hand (it does not add transactions automatically). When I skip
it for a couple of days I expect the unpaid occurrence to show up as due on its
day and as missed afterwards. That never happens: the day after I post an
occurrence, the next one already counts as paid, and the schedule quietly moves on
to the following days without ever showing anything as due or missed. If I switch
the date to an exact date ("is") the due occurrence appears as expected.

Steps to reproduce:

1. Create a daily schedule with an approximate date, not set to add
   transactions automatically.
2. Post today's occurrence.
3. Do not post the following days' occurrences, but keep using the app.
4. The next day's occurrence never shows as due, and once it is past it never
   shows as missed: the schedule's next date keeps moving forward each day as if
   it had been paid.

The same happens with schedules that repeat every other day.

## Required behaviour

- The transaction posted for one occurrence of a schedule must never count as the
  payment of a later occurrence of that schedule. This applies to every schedule
  with an approximate date whose occurrences are close together (every day, every
  other day, ...).
- A manually posted daily (or every-other-day) schedule therefore stays on its
  first unpaid occurrence: that occurrence is due on its day, is missed once the
  day has passed, and the schedule's next date does not move past it until it is
  paid. Posting it from the schedule then records a transaction on that
  occurrence's date.
- When every occurrence is paid on its day, the schedule keeps moving on to the
  next day as it does today.
- Unchanged: schedules with an approximate date whose occurrences are further
  apart (weekly, monthly, ...) still count a payment made up to two days before
  the due date as paying that occurrence; schedules with an exact date behave as
  today; and schedules that add their transactions automatically still post
  exactly one transaction per occurrence, including when catching up on several
  days the app was not opened, never a duplicate.
