# Holidays, treated like weekend days

Users in countries with bank holidays want their schedules to avoid those days too.
A recurring date configuration gets an optional `holidays` field: an array of days
(`YYYY-MM-DD`).

When a schedule has weekend handling on, a day in its `holidays` list is treated
exactly like a Saturday or a Sunday:

- An occurrence that falls on a holiday is moved in the schedule's direction (earlier
  for "before", later for "after") to the nearest day that is neither a weekend day
  nor a holiday. The same goes for weekend occurrences: if the Monday after a weekend
  is a holiday, a Saturday occurrence moving "after" lands on the Tuesday.
- For daily schedules, an occurrence on a holiday is skipped, as weekend days are.

When weekend handling is off, `holidays` has no effect, and schedules without the
field behave as they do now.
