# Keep fixed-cost groups out of month-wide budget actions

Some users keep fixed costs (rent, loan repayments, subscriptions) in category groups that they mark by writing the tag `#fixed` in the group's notes. Those budgets are set once and should not change when the user runs a month-wide budget action.

Expected behaviour:

- Month-wide budget actions (the actions that fill in the budget of every category for a month in one go) leave untouched the categories in a group whose notes contain the tag `#fixed`, in addition to the categories they already leave alone. Untouched means the category's budget for that month keeps the value it had.
- Groups without the tag, or without notes, behave as today.
- Only the group's notes count; the tag in a category's own notes has no effect.
