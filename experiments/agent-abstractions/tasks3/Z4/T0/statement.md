# One definition of the weekend rule for schedule dates

A schedule can be set to move an occurrence that falls on a weekend to the nearest
weekday before or after it. Deciding whether this applies to an occurrence, and in which
direction, is currently repeated rather than defined once.

Move this logic into one shared definition and have the code that needs it use that
definition, so that a future change to the logic is made once.

This is a refactor. Behaviour must not change: whatever the app does today it must
still do, with the same results, including any edge case where current results differ
from one another. Keep the public interface (requests, their parameters and their
results) as it is.
