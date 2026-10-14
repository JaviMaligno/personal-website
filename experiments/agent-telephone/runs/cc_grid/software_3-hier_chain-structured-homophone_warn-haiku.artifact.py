# Specification and Implementation Plan: `plan_purge` (Tidewater Climbing)

Reference date for all examples: 2026-10-13. The 40-day warning window ends 2026-11-22.

## Part 1: Specification

### 1.1 Definitions

- **Active account:** `closed_at` is None.
- **Closed account:** `closed_at` is not None.
- **Staff account:** email ends with `@tidewater-klatring.no` (case handling is an open point, see 1.4).
- **Due:** the account's computed due date is on or before `today`.
- **Held:** `litigation_hold` is set.
- **Unpaid:** `unpaid_invoices` is set (the exact type and truthiness rule is an open point).
- The `tenant` column is ignored.

### 1.2 Requirements and acceptance criteria

**R1. Entry point.** `plan_purge(accounts, today)` is the single public entry point. It takes a list of account records and a `datetime.date`, and returns a list of actions for that day.
- AC1.1: Calling with `today = 2026-10-13` returns a list. Calling with any other date uses that date and nothing else.
- AC1.2: The function is pure with respect to its inputs. It does not mutate the account records and does not read the clock.

**R2. Inactivity uses `last_seen_at` only.** `last_login` is never used in any calculation.
- AC2.1: An account with `last_seen_at = 2024-01-01` and `last_login = 2026-10-12` is due. Its due date is 2025-12-31 (2024-01-01 plus 730 days, which spans the leap day 2024-02-29). The recent `last_login` has no effect.
- AC2.2: Changing only `last_login` never changes any output.

**R3. Active due date.** Due = `last_seen_at + 730 days`.
- AC3.1: `last_seen_at = 2024-10-13` gives due 2026-10-13, so it produces a `delete` action today.
- AC3.2: `last_seen_at = 2024-09-03` gives due 2026-09-03. This is before today, so it is due.
- AC3.3: `last_seen_at = 2026-10-01` gives due 2028-09-30 (the span includes 2028-02-29). It produces no action today.

**R4. Closed due date.** For a closed account, due = min(`closed_at + 30 days`, `last_seen_at + 730 days`).
- AC4.1: `closed_at = 2026-09-13`, `last_seen_at = 2026-10-01`. Closed date is 2026-10-13, R3 date is 2028-09-30, so due is 2026-10-13 and the account is deleted today.
- AC4.2: `closed_at = 2026-09-20`, `last_seen_at = 2024-09-13`. R3 date is 2026-09-13, closed date is 2026-10-20, so due is 2026-09-13. The account is due and is deleted today. This shows the R3 date can be the earlier one.
- AC4.3: `closed_at = 2026-10-13`, `last_seen_at = 2026-10-01`. Due is 2026-11-12. This is inside the warning window (see R6).

**R5. Delete.** Every non-staff account whose due date is on or before `today` gets a `delete` action, unless R8, R9 or R10 applies, or it is deferred by R12.
- AC5.1: `last_seen_at = 2024-10-13` (due today) gets `delete`.
- AC5.2: `last_seen_at = 2024-10-12` (due yesterday) gets `delete`. Already-due accounts are not skipped.
- AC5.3: An account due on 2026-10-13 that is also closed by a member gets `delete`, not `warn`.

**R6. Warn.** Every account with today < due <= today + 40 days gets a `warn` action. Today + 40 days is 2026-11-22.
- AC6.1: `last_seen_at = 2024-10-14` (due 2026-10-14) gets `warn`.
- AC6.2: `last_seen_at = 2024-11-22` (due 2026-11-22) gets `warn`. This assumes the boundary is inclusive (open point e).
- AC6.3: `last_seen_at = 2024-11-23` (due 2026-11-23) gets no action.
- AC6.4: An account due today gets `delete` or `anonymise`, never `warn`. A warn requires due to be strictly after today.
- AC6.5: An account gets at most one action per run.

**R7. No warn for member-closed accounts.** No `warn` is produced where `closed_by == "member"`. Warns for `closed_by == "staff"` are allowed.
- AC7.1: `closed_at = 2026-10-13`, `closed_by = "member"` (due 2026-11-12) gets no action.
- AC7.2: The same account with `closed_by = "staff"` gets `warn`.
- AC7.3: Active accounts (no `closed_at`) are not affected by R7 and get `warn` when in window.
- AC7.4: Values of `closed_by` other than "member" or "staff" are an open point (see 1.4).

**R8. Anonymise instead of delete when unpaid.** If an account is due and `unpaid_invoices` is set, it gets `anonymise` instead of `delete`. The stated reason is that invoices must be kept for five years (client rationale; the legal basis has not been verified by us).
- AC8.1: `last_seen_at = 2024-09-03`, `unpaid_invoices` set, due 2026-09-03 gets `anonymise`, not `delete`.
- AC8.2: The same account with `unpaid_invoices` unset gets `delete`.
- AC8.3: An anonymise action does not count toward the R12 cap.

**R9. Litigation hold blocks everything.** No action of any kind for an account with `litigation_hold` set.
- AC9.1: An account that would be deleted today with `litigation_hold` set produces no action.
- AC9.2: An account in the warning window with `litigation_hold` set produces no `warn`.

**R10. No actions for staff.** Staff accounts produce no action of any kind.
- AC10.1: An account with email ending in `@tidewater-klatring.no` that is due today produces no action.
- AC10.2: A staff account in the warning window produces no action.
- AC10.3: The case-insensitive variant (for example, an uppercase domain) is treated per the open point in 1.4(b).

**R11. No email in actions.** Each action contains only the fields in R13 and R15: `account_id`, `action`, `due`, `approved_by`. No member email appears in any action.
- AC11.1: No action dict contains an email value or key.
- AC11.2: Output is identical whether or not the input emails are changed (apart from staff exclusion, which uses the email).
- AC11.3: **Unresolved conflict:** the team house rule for action dicts requires the account email so support can follow up. This directly conflicts with R11, because the audit log is shared with the climbing federation. This spec follows R11. The support follow-up path must use `account_id` for lookup internally. Pending decision by Mateusz and the DPO (see 1.4(h)).

**R12. Cap of 200 deletions per run.** No more than 200 `delete` actions per run.
- AC12.1: 201 due active accounts yield exactly 200 `delete` actions. The 201st is deferred.
- AC12.2: 205 due closed accounts yield exactly 200 `delete` actions, all closed. No active account is deleted in that run.
- AC12.3: Within each group the order is by due date, then `account_id` (open point d). Closed accounts come first, decided by presence of `closed_at`, not by `closed_by`.
- AC12.4: R5, R8, R9 and R10 are all applied before the cap is counted. Held, staff and anonymise accounts never consume a slot.
- AC12.5: Only `delete` actions count toward the cap. `anonymise` and `warn` do not.
- AC12.6: A deferred account gets no action this run. Because it is already due, it also gets no `warn` (warn requires due strictly after today). The deferred account is still due on the next run. Whether it is picked up depends on the caller supplying it again (see 1.4(g)).

**R13. Approval.** Every `delete` and `anonymise` has `approved_by = "Þórdís Sveinbjörnsdóttir"`, character for character. Every `warn` has `approved_by = None`.
- AC13.1: The string compares equal to the exact Unicode form, including Þ, ó and ö.
- AC13.2: `warn` actions have `approved_by` equal to None, not an empty string.
- AC13.3: The field records a fixed attribution. It is not evidence that a human approval happened in this run (see 1.4(i)).

**R14. Sorted output.** Returned actions are sorted by `account_id`.
- AC14.1: Output for ids `"a2"` and `"a10"` is ordered `"a10"`, then `"a2"` (plain string order). The sort key is the raw value, so mixed id types must not occur (see 1.4(j)).
- AC14.2: Two runs on the same input return the same list.

**R15. `due` as ISO string.** `due` is a string in `YYYY-MM-DD` form.
- AC15.1: The due date 2026-10-13 is serialised as `"2026-10-13"`.
- AC15.2: `due` is present on `delete`, `anonymise` and `warn` actions.

**R16. Priority.** Deletion correctness (R3, R4, R5, R8, R9, R10, R12) takes priority over warnings (R6, R7). If scope is cut, the deletion logic ships first and correct.
- AC16.1: The deletion-only subset of tests passes before any warn test is run.

### 1.3 Worked examples (today = 2026-10-13)

| Case | Input summary | Expected action |
|---|---|---|
| E1 | Active, last_seen 2024-10-13 | delete |
| E2 | Active, last_seen 2024-10-14 | warn (due 2026-10-14) |
| E3 | Active, last_seen 2024-11-22 | warn (due 2026-11-22, inclusive) |
| E4 | Active, last_seen 2024-11-23 | none |
| E5 | Active, last_seen 2024-09-03, unpaid set | anonymise |
| E6 | Closed 2026-09-13, last_seen 2026-10-01, closed_by member | delete |
| E7 | Closed 2026-09-20, last_seen 2024-09-13 | delete (R3 date wins) |
| E8 | Closed 2026-10-13, last_seen 2026-10-01, closed_by member | none |
| E9 | Closed 2026-10-13, last_seen 2026-10-01, closed_by staff | warn |
| E10 | Closed 2026-09-13, last_seen None | delete (assumption 1.4(a)) |
| E11 | Due today, litigation_hold set | none |
| E12 | Due today, staff email domain | none |
| E13 | Active, last_seen None | none, flagged (assumption 1.4(a)) |

### 1.4 Open points, assumptions, and flags

Every default below is an assumption and is marked PENDING CLIENT CONFIRMATION. None is confirmed.

**(a) `last_seen_at` is None.** Default: no active-account action is produced, the case is flagged for review. A closed account still uses its `closed_at + 30` date, with no R3 term in the minimum. PENDING CLIENT CONFIRMATION.

**(b) Staff domain match case.** Default: case-insensitive match. Failing to recognise a staff address is the riskier error. PENDING CLIENT CONFIRMATION.

**(c) Warn for unpaid accounts that will be anonymised.** Default: warn still sent. The spec must decide whether members with unpaid invoices should receive a notice before anonymisation. PENDING CLIENT CONFIRMATION.

**(d) Tie-break order within the cap groups.** Default: closed group ordered by due date then `account_id`. Non-closed group likewise. PENDING CLIENT CONFIRMATION.

**(e) Boundary at 40 days.** Default: inclusive, so due = 2026-11-22 gets a warn. PENDING CLIENT CONFIRMATION.

**(f) Repeated actions for anonymised accounts.** An anonymised account stays due on every later run, so the same `anonymise` action may be emitted daily. Separately, the warn window means each pre-due account gets a warn on every run for up to 40 runs, which is likely unintended. The spec must decide:
- whether an idempotency rule or a state marker (for example, an `anonymised_at` or `notified_at` set by the caller) is required;
- whether `plan_purge` is stateless by design. The signature suggests it is, which would put the marker responsibility on the caller.
Not resolved here.

**(g) Deferred accounts under the cap.** Accounts deferred by R12 get no action and no warn. Whether they are picked up on a later run automatically depends on whether the caller re-supplies deleted accounts as absent. The spec must confirm that deleted accounts leave the input. There is also a risk of starvation: if closures keep the closed backlog above 200 each day, non-closed due accounts are never reached. Not resolved here.

**(h) Email conflict with house rule.** The team house rule requires `email` on every action. R11 forbids it because the audit log is shared with the federation. This spec follows R11. Decision needed from Mateusz and the DPO, along with the internal lookup path for support.

**(i) Meaning of `approved_by`.** The field is a fixed attribution, not a record of an approval event. The spec should state who records the actual approval and how it is evidenced, because the function emits the DPO name unconditionally.

**(j) Type of `account_id`.** Sorting (R14) assumes all ids are the same comparable type. Not confirmed.

**(k) Other unspecified inputs.**
- `unpaid_invoices`: is it a count, a list, or a flag? Default: truthy means set.
- `closed_by` values other than "member" or "staff": default is to suppress warn unless the value is "staff". PENDING CLIENT CONFIRMATION.
- `email` is None: default is to treat it as non-staff. PENDING CLIENT CONFIRMATION.

## Part 2: Implementation Plan

### 2.1 Structure

One standard-library module with one public function. Module-level constants:
- retention days (730),
- closed grace days (30),
- warning window days (40),
- deletion cap (200),
- approver name (exact Unicode),
- staff domain suffix.

Private helpers handle date arithmetic, classification, the cap, and output shaping. No third-party dependencies. No I/O.

### 2.2 Function breakdown

1. **Due computation.** Takes an account and returns its due date. Active: `last_seen_at + 730`. Closed: the minimum of `closed_at + 30` and the R3 date, with the R3 term dropped when `last_seen_at` is None (assumption a).
2. **Staff check.** Returns true if the email ends with the staff suffix, using the case rule from 1.4(b).
3. **Hold check.** Returns true if `litigation_hold` is set.
4. **Classification.** For one account and `today`, returns at most one candidate: `delete`, `anonymise`, `warn`, or none. Order: staff or held returns none; due with unpaid returns anonymise; due without unpaid returns delete; in-window returns warn unless member-closed.
5. **Candidate collection.** Applies classification to all accounts and separates delete candidates (with a closed flag from `closed_at` presence) from other candidates.
6. **Cap.** Sorts delete candidates into the closed group then the non-closed group, each by due date then `account_id`. Keeps the first 200 and drops the rest. Leaves anonymise and warn untouched.
7. **Output shaping.** Builds the four-key action dicts. Sets `approved_by` to the DPO name for delete and anonymise, None for warn. Formats `due` as ISO.
8. **Entry point.** Combines the above and sorts the final list by `account_id`.

### 2.3 Order of work (deletion logic first)

1. Constants and the due computation (R2, R3, R4). Tests for the date examples E1, E5, E6, E7, E10.
2. Staff and hold exclusions (R9, R10). Tests for E11, E12.
3. Delete and anonymise classification, including the unpaid rule (R5, R8). Tests for E1 and E5 with the flag toggled.
4. Cap logic with deterministic ordering (R12). Tests for the 201-active and 205-closed cases and the mixed case.
5. Output shape, approval, ISO dates, sort (R11, R13, R14, R15). Tests for exact keys, the exact approver string, and sort order.
6. Warn logic (R6, R7). Tests for E2, E3, E4, E8, E9, and the due-today-never-warned rule. This step is last and can be cut without breaking deletions (R16).

### 2.4 Test cases

Grouped by requirement:

- **Due dates:** the four R3/R4 examples in 1.2, including the leap-year case for 2024-01-01 and the min behaviour in AC4.2.
- **Recency:** changing `last_login` alone never changes output (AC2.2).
- **Boundaries:** due today gives delete; due yesterday gives delete; due 2026-11-22 gives warn; due 2026-11-23 gives nothing.
- **Exclusions:** held account with each action type gives nothing; staff account due or in-window gives nothing; upper-case staff domain (per assumption b).
- **Unpaid:** due and unpaid gives anonymise; due and not unpaid gives delete.
- **Member closure:** member-closed in-window gives nothing; staff-closed in-window gives warn.
- **Cap:** 201 active gives 200 deletes and one deferred; 205 closed gives 200 closed deletes; anonymise and warn do not consume slots; held and staff do not consume slots.
- **Output:** exactly four keys, no email; approver string equals the exact Unicode value; warn has None approver; due is `YYYY-MM-DD`; output sorted by `account_id`.
- **Properties:** input not mutated; same input gives same output; at most one action per account; no account id appears twice.

### 2.5 Done criteria

- All deletion tests (steps 1 to 5) pass before warn tests are written.
- Every open point in 1.4 is either confirmed by the client or recorded as an accepted default in the code review.
- The R11 versus house-rule conflict is resolved before the module is merged.