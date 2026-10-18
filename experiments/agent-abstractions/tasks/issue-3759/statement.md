# Category learning creates redundant rules for payees already in a "one of" rule

I keep finding auto-generated rules in my rules list that duplicate rules I wrote myself.

I have a rule: if payee **is one of** [Grocery Store A, Grocery Store B, ...], set the category to Food. After entering and categorising a few transactions from Grocery Store A as Food (in the transaction list, with category learning on, i.e. saving through `transactions-batch-update` with `learnCategories: true`), a new automatic rule appears: if payee **is** Grocery Store A, set the category to Food. It does nothing my rule doesn't already do; it just clutters the rules list.

Expected behaviour:

- When category learning would learn category C for a payee, and the user already has a rule whose only condition is "payee is one of [...]" with that payee in the list and whose only action sets the category to that same C, no new rule should be created. The rules list should stay exactly as it was, whether the transactions were entered already categorised or categorised afterwards. This applies to every payee in such a rule.
- The user's "one of" rule must never be edited by category learning: its payee list and its category stay as the user wrote them.
- Learning must otherwise keep working as it does today:
  - A payee that is not covered by such a rule still gets a learned rule, so new transactions from it receive the learned category.
  - If the user keeps choosing a *different* category for a payee than the one their "one of" rule sets, that choice is still learned: new transactions from that payee get the newly chosen category, while the other payees of the "one of" rule keep getting the rule's category.
