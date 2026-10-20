# Plan variable schedules for the worst case

Some schedules don't have a fixed amount: their amount "is between" two values, for
a bill that changes from one month to the next. Actual currently expects such a
schedule to post the middle of the range. For planning that is the wrong choice:
people budgeting for a variable bill want to be covered for the worst case.

Change the rule: the amount a ranged schedule is expected to post is **the end of the
range furthest from zero**, whichever order the two values were entered in.

- A bill between -101.00 and -200.00 is expected at -200.00 (also when it was entered
  as between -200.00 and -101.00).
- Income between 101.00 and 200.00 is expected at 200.00.

Schedules with a single amount, and schedules without an amount, behave as before.
