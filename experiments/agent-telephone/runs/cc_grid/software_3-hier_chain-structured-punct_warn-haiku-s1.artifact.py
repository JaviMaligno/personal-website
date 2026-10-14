Scope: the module is a pure planner. It returns actions and performs no deletes, anonymisation, notices, de-duplication, logging, or data dropping. Those belong to the executor and the caller.

**Requirements (R-IDs)**

R1 confirmed. Single entry point `plan_purge(accounts, today)`. The 14, 730, 30 and 200 values are fixed constants, not parameters.

R2 corrected. `last_login` may be None and must not be validated (see R25). `closed_by` allows only "member", "staff" or None; anything else is a validation error. `unpaid_invoices` must be a bool or a non-negative int.

R3 confirmed. Warn actions carry `approved_by` as None (see C1).

R4 confirmed.

R5 confirmed. Date arithmetic near 9999-12-31 can raise OverflowError; treat that as a validation error for the run (see R25).

R6 confirmed, with the reading that R8 and R9 also apply (see C3).

R7 corrected. Warn suppression follows the single rule in R22 below, which also covers closed_by None with closed_at set.

R8 confirmed for classification. The module cannot "drop personal data"; the executor must, and the action does not say which fields. The five-year retention basis is a legal claim for the DPO to confirm.

R9 confirmed. Any truthy `litigation_hold` suppresses all actions, which is the safe direction.

R10 confirmed; see R24 for the matching rule.

R11 confirmed; ordering is in R20.

R12 confirmed, with a governance flag (C12). Store the approver name in NFC form.

R13 confirmed. Error text must name only the account id and field, never an email.

R14 confirmed. Ids must be a single comparable type (see R25).

R15 confirmed. Unknown keys such as `tenant` are ignored, not rejected.

R16 confirmed. Deletion logic has priority over warnings.

R17 confirmed. Validation runs before any filtering.

R18 confirmed.

R19 confirmed, with a flag. Accounts with both dates None produce no action, but the module has no channel for the flag (see C8).

R20 confirmed. Over-cap accounts are due on or before today, so they could never be warned anyway; "no warn" is a no-op.

R21 corrected. Closed_by None with closed_at set stays in tier 1, but the warn is suppressed (see R22). Flag as a data error.

R22 corrected (in place of the split R21/R22 rules). Warn is allowed only when closed_by is "staff", or when closed_at is None and closed_by is not "member". In all other cases, including closed_by "member" with closed_at None, no warn is emitted. For due dates, closed_by "member" with closed_at None uses last_seen_at only. Flag the data inconsistency.

R23 confirmed. Action keys are exactly account_id, action, due (ISO string), approved_by. No email or other personal field.

R24 corrected in part. Strip whitespace and a trailing dot, then compare the domain case-insensitively. Missing or non-string email is not staff; flag the account as a data error. Subdomains are a decision for Mateusz (see C13). The literal R10 reading treats them as non-staff, but the recommended default is to treat them as staff.

R25 corrected. Validate `today` and the dates `last_seen_at` and `closed_at` (datetime.date, not datetime.datetime). Validate `unpaid_invoices` and `closed_by` as above, and require unique ids of one comparable type. Do not validate `last_login` or unknown keys. Wrap OverflowError as a validation error. Error text names only the account id and field.

R26 confirmed. Flagging has no output channel (see C8).

R27 confirmed. Repeated warns are a caller concern (see C5).

R28 confirmed.

R29 added. The function is stateless, so an anonymised account with unpaid invoices re-qualifies on every run. The caller must exclude processed accounts, or a status value must suppress them (see O5). This is blocking.

**Open points (O-IDs)**

O1 confirmed, extended by R20. The PM ordering covers inactive accounts only. Closed accounts come first in tiers 0 and 1, then inactive accounts in tier 2, each sorted by due date then account_id.

O2 confirmed as uncapped per the requirements. Flag for Mateusz before go-live: R11 cites database locks, and anonymise also writes rows (C2).

O3 confirmed, subject to R22. Flag that the warn text cannot distinguish delete from anonymise (C9).

O4 confirmed. Anonymise uses the R5 due date.

O5 flag, blocking. Mateusz must list the status values and say which suppress actions. Without that, the caller must filter processed accounts (R29).

**Conflicts**

C1 resolved as proposed. The approved_by key is present with value None on warns.

C2 flag. Mateusz decides whether anonymise is capped. Default is uncapped per PM.

C3 confirmed. R9 and R10 remove accounts first, then R8 reclassifies to anonymise before the cap. R6 is read as subject to R8 and R9 as well.

C4 confirmed. No action and a flag when both dates are None.

C5 flag. A daily run re-emits the same warn for up to 14 days, so a member could receive up to 14 notices. The caller should de-duplicate on (account_id, action, due). Mateusz to confirm.

C6 confirmed compatible.

C7 flag for product confirmation. Member-closed accounts get no warning and are deleted 30 days after closure.

C8 new flag. R19, R21, R22 and R26 require flagging, but R3 fixes the output shape and R26 forbids logging, so there is no channel. Mateusz and the architect decide; the default is that the caller checks for missing dates itself.

C9 new flag. A warn cannot say whether deletion or anonymisation is coming. The notice text must come from the caller and match the outcome (O3).

C10 new, resolved by R2 and R25. Strict date validation would reject a None `last_login` that the module does not use.

C11 new flag. An account warned for a date can be deferred past that date by the cap, so deletion happens later than the notice promised. Mateusz either accepts this or changes the cap.

C12 new flag for the DPO. R12 hardcodes the DPO's name as approver on every action, so the audit trail records an approval that no one gave for each run. The DPO should sign off the run policy, and the approver should be confirmed as intended.

C13 new flag. Subdomain staff emails fail open under the literal R10 rule. The recommended default is to treat subdomains as staff. Mateusz decides.

C14 new flag. The module plans anonymisation but cannot perform the data drop (R8). The executor needs the field list from the DPO.

C15 new flag for product confirmation. A member who closes an account and then logs in is still due at closed_at + 30 days under R5.

C16 resolved. The R21/R22 asymmetry is replaced by the single warn rule in R22.

C17 new flag for operations. R25 halts the whole run on any violation, so one bad row stops all deletions until fixed. Alerting is needed.