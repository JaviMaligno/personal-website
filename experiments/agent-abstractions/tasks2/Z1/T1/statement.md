# Month-wide budget actions overwrite hidden and template-managed categories

The budget month menu has actions that fill in the budget of every category for that month in one go.

Users who budget some categories with templates report that running a month-wide action overwrites those categories, undoing what their templates set. Hidden categories, and categories inside hidden groups, are meant to be out of the way, and month-wide actions should not write to them either.

Expected behaviour of month-wide budget actions:

- A category is left untouched (its budget for that month keeps the value it had) when any of these holds:
  - the category is hidden;
  - the category's group is hidden;
  - the category has at least one budget template saved (as the template editor saves them). Templates that exist only as text in a category's notes and have never been saved need no special handling.
- Other categories are filled exactly as today: same amounts, and income categories still take part only in tracking budgets.
- Actions that work on a single category the user picked are not affected.
