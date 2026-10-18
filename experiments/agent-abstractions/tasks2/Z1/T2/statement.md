# New month-wide budget action: budget last month's spending

Add a month-wide budget action (one that fills in the budget of every category for a month in one go) that sets each category's budget for a month to what the category spent in the previous calendar month.

- Expose it as the budget method `budget/set-last-month-spending`, next to the other budget methods. It takes `{ month }` (`YYYY-MM`), the month being budgeted.
- Amount: for an expense category, its net spending in the month before `month`, as a positive budget (spent 30.00, budget 30.00). A category that spent nothing in that month is budgeted 0. For an income category, when income categories are filled, the amount received in that month.
- Which categories: the same ones the existing month-wide actions fill. Categories those actions leave untouched are left untouched by this one too (their budget keeps the value it had).
- Otherwise it behaves like the existing month-wide actions (for example, it can be undone).
