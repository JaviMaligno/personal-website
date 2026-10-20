# The days a schedule falls on within a period

We want to show recurring schedules on a calendar. Add a server handler
`schedule/get-dates-in-range` that takes `{ config, start, end }` and returns the
days on which the schedule falls between `start` and `end`.

- `config` is a recurring date configuration, the same object a schedule stores as
  its recurring date (start, frequency, interval, patterns, end settings and weekend
  settings).
- `start` and `end` are days (`YYYY-MM-DD`); both are included in the period.
- The result is an array of days (`YYYY-MM-DD`) in ascending order, each day at most
  once.

The days must be the ones the schedule really falls on, including weekend handling:
when it is on, an occurrence on a Saturday or a Sunday is moved to the Friday before
or the Monday after, as the schedule is set, except for daily schedules, whose
weekend occurrences are skipped. Whether a day belongs to the period is decided
by that final day, not by the date the occurrence had before any adjustment: an
occurrence moved into the period is listed, one moved out of it is not.
