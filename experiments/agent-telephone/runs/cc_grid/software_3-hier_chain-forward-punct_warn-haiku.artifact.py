# Technical spec: `plan_purge(accounts, today)`

## 0. Blocking conflict: member email in output

The house rule says every action dict must carry the account's `email` so support can follow up. The client brief says the member's email must not appear in any action, because the audit log is shared with the climbing federation. These cannot both be met. This spec follows the client brief, since it is a stated legal and privacy constraint and the house rule is generic. The architect or client must confirm this before build. Support can look up the email internally by `account_id`. If the architect insists on the email field, the client must sign off first.

## 1. Constants

- `INACTIVITY_DAYS = 730`
- `CLOSED_GRACE_DAYS = 30`
- `WARN_DAYS = 14`
- `DELETE_CAP = 200`
- `DPO_NAME = "Þórdís Sveinbjörnsdóttir"`, stored as a Unicode NFC string and covered by a byte-exact test.
- `STAFF_DOMAIN_SUFFIX = "@tidewater-klatring.no"`

## 2. Input contract

Each account is a dict with `id`, `email`, `status`, `last_seen_at`, `last_login`, `closed_at`, `closed_by`, `unpaid_invoices`, `litigation_hold`. `last_seen_at` and `closed_at` are `datetime.date` or None. `today` is a `datetime.date`.

Validation:
- `today` must be a `date`. A `datetime` must be rejected, because `datetime` is a subclass of `date`.
- Duplicate `id` values raise `ValueError`.
- Error messages must never include the email value. Log account ids only.
- `tenant`, `last_login`, and `status` are never read.

## 3. Output contract

A list of dicts, each with exactly these keys:
- `account_id`: the input `id`
- `action`: `"delete"`, `"anonymise"`, or `"warn"`
- `due`: ISO 8601 date string, `YYYY-MM-DD`
- `approved_by`: `DPO_NAME` for delete and anonymise, `None` for warn

The list is sorted ascending by `account_id`. An empty input returns `[]`.

## 4. Due date

For each account:
- `inactive_due = last_seen_at + 730 days`, if `last_seen_at` is set.
- `closed_due = closed_at + 30 days`, if `closed_at` is set.
- `due = min` of the applicable dates. If neither applies, the account has no due date and gets no action. It is logged as a data exception.

## 5. Classification precedence

For each account, in order:
1. If `litigation_hold` is truthy, emit nothing.
2. If the email is staff (see section 8), emit nothing.
3. If there is no due date, emit nothing and log an exception.
4. If `due <= today`:
   - If `unpaid_invoices > 0`, emit `anonymise`. This is not capped.
   - Otherwise emit a deletion candidate. It is subject to the cap.
5. Else, if `today < due <= today + 14 days` and `closed_by != "member"`, emit `warn`.
6. Otherwise, emit nothing.

## 6. Cap and ordering

- Deletion candidates are ordered by key `(0 if closed_at is not None else 1, due, account_id)`.
- The first 200 are emitted. The rest are deferred: not emitted, and counted in a log line with no emails.
- Anonymise and warn actions are not counted toward the cap.
- The final list is sorted by `account_id` after selection.

## 7. Warn rules

- A warn is emitted when the days until due are 1 through 14 inclusive.
- Warns are not capped.
- A warn is suppressed when `closed_by == "member"`.
- Warns are stateless and repeat on each run while the window holds.

## 8. Staff exclusion and email handling

- Staff match: `email.strip().lower().endswith("@tidewater-klatring.no")`. An email of None is treated as non-staff and logged.
- The email field is read only for this check and is never copied to output.

## 9. Ambiguities and recommended defaults

**(a) Cap interaction.** The brief caps only deletions. Recommended: deletions over the cap are deferred (not dropped), so they stay due and are picked up next run. They are reported as a count in logs only. Anonymise is not counted toward the cap and is not capped. Warns are not capped.

**(b) Due date when both apply.** Recommended: `due = min(inactive_due, closed_due)`. The brief's "if that comes sooner" supports this. For a closed account the closed date almost always wins, but if `last_seen_at` is later than `closed_at`, the min still applies.

**(c) Unpaid invoices.**
- Anonymise once is intended, but the planner is stateless and the input has no "already anonymised" marker. On the next run the account is still due and would be anonymised again. Recommended: the executor must be idempotent, and the architect should add an `anonymised_at` input field so the planner can skip anonymised accounts.
- Warn first? The brief does not say. Recommended: no separate pre-anonymise warn beyond the normal 14-day warn, which applies to anonymise-bound accounts too.
- Open risk: if `unpaid_invoices` later drops to 0, the account is still due and the next run emits a delete. This could remove the account record that the five-year invoice retention depends on. The client must confirm invoices are retained independently before this is built.

**(d) Warn window.**
- Accounts already due but deferred by the cap: recommended no warn, because the notice would be late. They are deleted on the next run. The DPO should confirm this is acceptable.
- Inclusivity: recommended inclusive of day 14 (`due <= today + 14`). Day 0 is not a warn; it is a due action.
- Warns for anonymise-bound accounts: recommended yes, because the brief says "every account that will become due within the next 14 days".

**(e) Unknown `closed_by` values and `closed_at` with `closed_by = None`.**
- Recommended: `closed_at` is authoritative for the 30-day rule and for the closed ordering group regardless of `closed_by`.
- Only the exact value `"member"` suppresses a warn. Any other value, including None, allows the warn. Unknown values are logged as data exceptions.
- Staff matching is case-insensitive (recommended, since email domains are case-insensitive in practice).
- The brief's sentence "If the member closed the account themselves, don't. Warn them, they asked to leave." reads as self-contradictory. The recommended reading is: do not warn member-closed accounts. This needs confirmation.

**(f) `status` field.** The brief does not say. Recommended: ignored. Client should confirm whether statuses such as "deleted" or "pending" exist and should exclude accounts.

**Other ambiguities:**
- `last_login`: ignored, as the brief states.
- `last_seen_at = None`: no inactivity due date. If `closed_at` is set, the closed rule still applies. Otherwise no action and a data exception is logged. Falling back to `last_login` is rejected, per the brief.
- Inclusivity of the 730-day boundary: `last_seen_at + 730 == today` is due today and therefore a delete. The boundary is inclusive on `today`.
- Deleting today versus the 30-day rule: `closed_at + 30 == today` is due and deleted today.
- `closed_at` before `last_seen_at`: the min rule applies, which usually means the 30-day closed rule wins.
- Duplicate ids: raise `ValueError`.
- `unpaid_invoices` of None: treat as an exception and emit nothing for that account.
- Mixed `account_id` types: the sort may fail. Recommended: require all ids to be the same type.
- Staff accounts with unpaid invoices: no action, per the brief.
- Warn repetition: the warn repeats daily during the window. Client should confirm this is acceptable or request state tracking.
- Time zone: none. `today` is taken as given.

## 10. Edge cases

| Case | Expected result |
|---|---|
| Empty input | `[]` |
| Litigation hold, past due | nothing |
| Litigation hold, due in 5 days | nothing |
| Staff email, any case, past due | nothing |
| Both dates None | nothing, logged |
| `closed_by = "member"`, due in 3 days | nothing |
| `closed_by = "staff"`, due in 3 days | warn |
| Unpaid, past due, closed | anonymise, not counted to cap |
| 201 deletion candidates | 200 emitted, 1 deferred |
| 300 unpaid due accounts | 300 anonymise, 0 delete |

## 11. Module structure

- `_due_date(acc) -> date | None`
- `_is_staff(email) -> bool`
- `_classify(acc, today) -> (kind, due) | None`
- `_select_deletions(candidates) -> (selected, deferred_count)`
- `plan_purge(accounts, today) -> list[dict]`

Stdlib only. No I/O inside `plan_purge`. Logging uses account ids only.

## 12. Acceptance criteria

1. `last_seen_at = today - 730` produces a delete with `due = today`.
2. `last_seen_at = today - 729` produces a warn with `due = today + 1` (unless member-closed).
3. `closed_at = today - 30` produces a delete with `due = today`, regardless of recent `last_seen_at`.
4. `closed_at = today - 29` produces a warn (unless member-closed).
5. `closed_at` and `last_seen_at` both set: `due` is the earlier of the two.
6. With 201 deletion candidates, 200 deletes are emitted and the 201st is absent.
7. Closed accounts are selected before open accounts when the cap bites.
8. Within the same group, selection follows earlier `due`, then smaller `account_id`.
9. Litigation hold produces no action of any kind, including warn and anonymise.
10. Staff email (any case) produces no action of any kind.
11. Serialised JSON output contains no member email substring.
12. Output is sorted by `account_id` for shuffled input.
13. Every `due` is a string that round-trips through `date.fromisoformat`.
14. `approved_by` equals `DPO_NAME` for delete and anonymise, and `None` for warn.
15. The output key set is exactly `{account_id, action, due, approved_by}`.
16. Changing `tenant`, `last_login`, or `status` does not change output.
17. Unpaid past-due accounts produce anonymise and are not counted toward the cap.
18. Warn is emitted for days 1 through 14 inclusive, and not for day 15 or day 0.
19. `last_seen_at = None` with `closed_at = None` produces no action.
20. Duplicate ids raise `ValueError`.
21. `today` given as a `datetime` raises an error.
22. The DPO name constant is byte-equal to `"Þórdís Sveinbjörnsdóttir"` in NFC form.