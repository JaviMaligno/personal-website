# Payees page counts rules of completed schedules

The Payees page shows, for each payee, how many rules refer to it (the server's
`payees-get-rule-counts` handler returns a map from payee id to that number). Every
schedule is backed by a rule whose conditions include the schedule's payee, so
schedules contribute to these counts. Once a schedule is marked **completed** it no
longer does anything, yet its rule is still counted: a payee whose only rule
belongs to a completed schedule shows "1 rule".

## Required behaviour

- `payees-get-rule-counts` must not count rules that belong to a completed
  schedule. A payee whose only references are such rules gets no entry in the
  result (its id is absent from the map, as for a payee with no rules at all).
- Rules not linked to a schedule, and rules of schedules that are not completed,
  are counted exactly as before.
- On the Payees page, the rule counts must be refreshed when schedules change
  (for example when a schedule is completed), not only when rules change.
