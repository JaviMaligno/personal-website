# Architect plan: `plan_purge(accounts, today)`

This is a pure function with no I/O. It takes a list of account dicts and a `date` and returns a sorted list of action dicts. The design below is sound on the main paths. The items that need client decisions are the 200-cap conflict, daily warn repetition, and the statelessness of anonymise.

## Blocking contradiction

- **Every due account vs. the 200 cap.** The brief says to return a delete for every account due on or before today, and also says at most 200 deletions per run. Both cannot hold when more than 200 are due. Default assumed: cap at 200. Excess candidates get no action this run and stay due, so the next run picks them up. This needs written client confirmation before build.

## Architecture

**Validation (step 0).** Ids must be unique and mutually comparable, so mixed types are an error. `last_seen_at` must be a `date`, not `None`. Reject `datetime.datetime` wherever a `date` is expected, since `datetime` is a subclass of `date` and an `isinstance` check alone will pass it. Error messages may name the account id but never the email. Default: raise `ValueError` rather than skip, because skipping silently hides deletions.

**Exclusions (step 1).** Applied first, to every rule:
- Staff: `email.lower()` ends with `"@tidewater-klatring.no"`. Use the `@` prefix. Without it, a domain like `x-tidewater-klatring.no` would match.
- `litigation_hold` truthy. Default: require a strict bool and treat `None` as an error.
- Excluded accounts produce no action and do not consume cap slots. `status`, `last_login`, and `tenant` are ignored.

**Due date (step 2).** `inactive_due = last_seen_at + timedelta(days=730)`. If `closed_at` is set, `closed_due = closed_at + timedelta(days=30)` and `due = min(inactive_due, closed_due)`. Otherwise `due = inactive_due`. The closure rule applies regardless of `closed_by`. The reported `due` is the same for every action type for a given account.

**Classification (step 3).**
- `due <= today`: `anonymise` if `unpaid_invoices > 0`, otherwise a delete candidate. Overdue accounts are emitted every run until processed.
- `today < due <= today + 14 days`: `warn`, unless `closed_by == "member"`. This applies to delete-bound and anonymise-bound accounts alike. A due account never gets a warn, so no account gets both a warn and a delete.
- Otherwise: no action. Each account yields at most one action.

**Cap (step 4).** Only delete candidates are capped. Anonymise and warn are neither capped nor counted. Unpaid-invoice accounts become anonymise before the cap is applied. Sort candidates by `(0 if closed_at is not None else 1, due, id)` and keep the first 200 as deletes.

**Output (step 5).** One dict per action with exactly four keys: `account_id`, `action`, `due` (ISO `YYYY-MM-DD`), and `approved_by` (the DPO for delete and anonymise, `None` for warn). No email or other personal fields. Sort by `account_id`. Empty input returns `[]`. Do not mutate the input.

## Rule confirmations

1. **Closed-30 rule.** Confirmed. It uses the same on-or-before semantics as the 730 rule. `closed_at` of `None` means only the 730-day rule applies.

2. **Warn window.** Partly open. The window applies to both delete-due and anonymise-due accounts and never duplicates a due account, which is confirmed by the design logic. Inclusion of day 14 is an assumption: `today + 14` gets a warn, `today + 15` does not. Client to confirm.

3. **Cap and ordering.** Anonymise does not count toward the 200 cap, and unpaid-invoice accounts convert to anonymise before the cap is applied. Both are confirmed by the brief. Closed-first precedes due-date ordering, and the tie-break is due then id. The closed-first key ("any `closed_at`" vs. "`closed_by == member` only") and the tie-break are still open (questions a and k below).

4. **Exclusions.** Staff and litigation-hold accounts are excluded before any other rule, and they do not consume cap slots. Staff-closed accounts (`closed_by == "staff"`) are not exempt from warnings. This is the literal reading of the brief, which exempts only member closures. Still open (question b).

5. **Reported due.** Confirmed. For closed accounts, the reported due is the earlier of the two deadlines.

## Gaps and risks

- **Warn repetition.** As designed, an account in the window gets a warn on each run, up to 14 notices. That conflicts with the "warn before delete" intent, which suggests a single notice. Client to confirm daily repetition or request one warn per account.
- **Anonymise is stateless.** An anonymised account that still has its old `last_seen_at` and unpaid invoices will be re-emitted as anonymise every run. The same applies to deletes deferred by the cap, which is intended. The caller must remove processed accounts from the input, or `plan_purge` must be given a processed-state input. The brief does not say how this is tracked. Needs an answer before build.
- **Anonymise and DB locking.** The brief attributes the lock risk to deletions only. If anonymise also causes locks, the cap has to cover it as well (question e).
- **Silent deferral.** Excess deletions are deferred with no report, so ops has no signal that the backlog exists (question d).
- **Ambiguous "closed" priority.** Prioritising every `closed_at` puts staff-closed accounts ahead of inactive ones. The brief's rationale ("people who asked to leave") points to `closed_by == "member"` (question a).
- **Data consistency.** `closed_by` can be set with `closed_at` as `None`, or the reverse. The design does not yet decide whether that is an error.
- **Retention.** Anonymise keeps invoices for the Skatteetaten five-year period, which the brief covers. Out of scope for this module.

## Test list

- `closed_at` of `None` uses only the 730-day rule.
- Boundaries: `due == today` gives delete or anonymise. `due == today + 14` gives warn. `due == today + 15` gives nothing.
- Inactivity of 729 days gives nothing, 730 gives delete, and 729 or 730 days inactive with a closed date at 29 or 30 days.
- A `closed_at` later than `last_seen_at` makes the 30-day rule the earlier deadline, so `min` applies.
- Staff or litigation-hold accounts that are due produce nothing and use no cap slots.
- A member closure in the warn window gets no warn. A staff closure in the window gets a warn.
- Exactly 200 deletes is allowed. 201 candidates gives 200 deletes and the rest omitted, with closed-first ordering verified.
- Anonymise does not count toward the cap, even with more than 200 due.
- The email string appears in no output and no error message.
- Output is sorted by account id, and `due` strings are ISO.
- Duplicate ids, `None` `last_seen_at`, `datetime` values, `None` `unpaid_invoices`, and mixed id types all raise.
- Input is not mutated.

## Open questions for the client

Default assumed for each, pending confirmation:

a. Closed-first key: any `closed_at` (default), or only `closed_by == "member"`?
b. Staff-closed accounts: warned (default), or exempt?
c. Warns repeat daily while the account is in the window, up to 14 per account (default). Is that intended?
d. Excess deletions beyond the cap are silently deferred (default). Is any signal needed?
e. Anonymise is uncapped (default). Does the database lock issue also apply to anonymise?
f. Warn for anonymise-bound accounts (default: yes)?
g. Invalid or missing data: raise (default), or skip?
h. What does `status` mean? Are any statuses, such as already deleted, excluded?
i. Email domain matching is case-insensitive (default)?
j. `unpaid_invoices`: integer count with `> 0` meaning unpaid (default), or boolean? `None` is an error.
k. Tie-break within closed accounts: due then id (default), or id only?
l. Account id type: must be mutually comparable. Mixed types are an error.
m. How are processed accounts removed from subsequent runs, given that `plan_purge` is stateless?
n. Is the 14-day window inclusive of day 14 (default: yes)?
o. Is 730 days a day count (default, via `timedelta`) rather than two calendar years?