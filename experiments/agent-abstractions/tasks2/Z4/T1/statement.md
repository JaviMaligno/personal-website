# Daily schedules: skip weekend days instead of moving them

A recurring schedule can be set to avoid weekends: an occurrence that falls on a
Saturday or a Sunday is moved to the Friday before or to the Monday after, depending
on the schedule's setting.

For schedules that repeat daily this does not work well. Saturday's and Sunday's
occurrences both land on the same Friday or Monday, so the schedule ends up falling
on that day two or three times, and a daily schedule that starts on a weekend can
even report a date before its own start.

Change the rule for daily schedules (every day or every few days): when weekend
handling is on, an occurrence that falls on a Saturday or a Sunday is skipped
altogether. It is not moved, whichever direction the schedule is set to. Weekday
occurrences of daily schedules are unchanged. Schedules that repeat weekly, monthly
or yearly keep moving weekend occurrences exactly as they do now, and nothing changes
for schedules with weekend handling off.
