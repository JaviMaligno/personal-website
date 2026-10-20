# Let month-wide budget actions include hidden categories on request

Users who park categories by hiding them sometimes still want a month-wide budget action (one that fills in the budget of every category for a month in one go) to fill those categories as well.

Month-wide budget actions now accept an optional `includeHiddenCategories` flag next to `month` in their arguments:

- When `includeHiddenCategories` is `true`, hidden categories and categories in hidden groups are filled like any other category.
- The other exclusions still apply: categories with saved budget templates, categories in groups tagged `#fixed`, and income categories outside tracking budgets are still left untouched.
- When the flag is absent or `false`, behaviour is exactly as before.
