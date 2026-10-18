# Auto-posting schedules created or edited later in the day are not posted until tomorrow

Schedules can be set to post their transactions automatically ("automatically add
transaction"). The background service that posts due schedule transactions runs at
most once per calendar day: after it runs, it records the date in the budget's
`lastScheduleRun` preference and skips any further run on the same date.

So if, after that day's run, the user creates a schedule that posts transactions, or
edits a schedule so that it posts transactions, an occurrence that is already due
today is not posted until the next day.

## Required behaviour

- After a schedule is **created** with "posts transactions" enabled, the
  `lastScheduleRun` marker is cleared (the preference becomes `undefined`), so the
  auto-posting service may run again today.
- After a schedule is **updated** and the resulting schedule posts transactions, the
  marker is cleared as well. This includes updates that do not mention the
  "posts transactions" field at all (for example a rename) of a schedule whose
  stored setting already posts transactions: the stored value decides.
- Creating or updating a schedule that does **not** post transactions leaves the
  marker untouched.
- Clearing the marker is harmless: the service only posts occurrences that do not
  have a transaction yet. Nothing else about creating or updating schedules
  changes.
