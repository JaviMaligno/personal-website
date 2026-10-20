# Schedules moved "before" the weekend occasionally get stuck

A recurring schedule can avoid weekends: with "skip weekend" on and the solve mode
`before`, an occurrence that falls on a Saturday or Sunday is moved to the preceding
Friday (with `after`, to the following Monday). The *resolved* date of an occurrence
is its date after this adjustment.

Advancing such a schedule to its next date is broken in some cases. Advancing
works by looking for the next occurrence starting from the day after the current
next date, and then applying the weekend adjustment; with `before`, the adjustment
can move the found occurrence back onto (or before) the current next date, so the
next date does not move and the schedule gets stuck. Two features advance a
schedule this way:

- **Skip next date** on a schedule.
- The **auto-posting service**, which, for a schedule that posts transactions,
  posts every missed occurrence and advances the schedule's next date past each
  one while catching up.

The existing special-case workaround for skipping (`before` mode, when the next
date is a Friday or on a weekend) does not cover all cases and should be replaced
by one shared rule.

## Required behaviour

1. Add to the shared schedules module (the one that exports `getNextDate`) an
   exported function

   ```ts
   getNextDateAfter(dateCond, afterDate: string): string | null
   ```

   where `dateCond` is a schedule's date condition (as accepted by `getNextDate`)
   and `afterDate` a `YYYY-MM-DD` date. It returns the **first resolved occurrence
   date strictly later than `afterDate`**, honouring the weekend settings, or
   `null` when the schedule has no further occurrence (e.g. it ends after N
   occurrences). It must walk past every occurrence whose resolved date is on or
   before `afterDate`, including several in a row (e.g. a daily schedule with
   `before` mode, where Friday, Saturday and Sunday all resolve to the Friday),
   but it does not need to search indefinitely: a handful of occurrences (up to a
   week's worth) is enough.

   Examples (December 2020: the 4th, 11th and 18th are Fridays; the 5th is a
   Saturday; the 7th and 14th are Mondays):
   - weekly from Sat 2020-12-05, no weekend skipping: after `2020-12-05` →
     `2020-12-12`;
   - same, skip weekend `after`: after `2020-12-07` → `2020-12-14`; after
     `2020-12-13` → `2020-12-14`;
   - weekly from Sun 2020-12-06, skip weekend `after`: after `2020-12-07` →
     `2020-12-14`;
   - weekly from Sat 2020-12-05, skip weekend `before`: after `2020-12-04` →
     `2020-12-11`;
   - daily from Fri 2020-12-04, skip weekend `before`: after `2020-12-04` →
     `2020-12-07`;
   - daily from Mon 2026-08-24, skip weekend `before`: after `2026-08-28` (a
     Friday) → `2026-08-31`;
   - weekly from Sat 2020-12-05 ending after 2 occurrences: after `2020-12-05` →
     `2020-12-12`; after `2020-12-12` → `null`.

2. **Skip next date** sets the schedule's next date to `getNextDateAfter` of its
   current next date (e.g. the daily `before` schedule above, next date
   2020-12-04, becomes 2020-12-07).

3. The **auto-posting service**, when it advances a schedule past an occurrence it
   handled, uses the same rule, so it never gets stuck. Example: a weekly schedule
   from Sat 2016-12-24 with skip weekend `before` that posts transactions, whose
   occurrence of 2016-12-23 already has its transaction; when the service runs on
   2016-12-31 it posts the missed 2016-12-30 occurrence (once) and the schedule's
   next date becomes 2017-01-06.

Recomputing a schedule's next date from today (when it is created or its rule
changes) is unchanged.
