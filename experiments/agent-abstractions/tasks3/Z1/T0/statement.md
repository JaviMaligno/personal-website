# One definition of which categories a month-wide budget action fills

The budget has actions that fill a whole month at once. Which categories such an action
writes is currently worked out by the actions themselves: what happens to hidden
categories and to categories in hidden groups, income categories being written only in
tracking budgets, and, for averages, turning past spending into a positive amount to
budget.

Move this logic into one shared definition and have the code that needs it use that
definition, so that a future change to the logic is made once.

This is a refactor. Behaviour must not change: whatever the app does today it must
still do, with the same results, including any edge case where current results differ
from one another. Keep the public interface (requests, their parameters and their
results) as it is.
