# Worst case for approximate amounts too

Besides ranges, a schedule's amount can be "approximately" a value. When matching
transactions to such a schedule, Actual accepts anything within 7.5% of the value
(the tolerance is rounded to the cent). For planning, though, these schedules are still
expected at the exact value, so a bill that is "approximately 100.00" can cost more
than was planned.

Extend the worst-case rule to approximate amounts: an approximate amount is expected
at **the end of its tolerance furthest from zero**.

- Approximately -100.00 is expected at -107.50; approximately 100.00 at 107.50.
- Approximately -12.34 is expected at -13.27 (the tolerance, 7.5% of 12.34, rounded
  to the cent, is 0.93).

Ranged amounts keep the rule they have now; single ("is") amounts and missing amounts
are unchanged.
