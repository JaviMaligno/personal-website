# One definition of a ranged schedule's expected amount

A schedule's amount can be a range (between two values). When the app needs the single
amount such a schedule is expected to come to, it works that amount out from the range.
This calculation is currently repeated rather than defined once.

Move this logic into one shared definition and have the code that needs it use that
definition, so that a future change to the logic is made once.

This is a refactor. Behaviour must not change: whatever the app does today it must
still do, with the same results, including any edge case where current results differ
from one another. Keep the public interface (requests, their parameters and their
results) as it is.
