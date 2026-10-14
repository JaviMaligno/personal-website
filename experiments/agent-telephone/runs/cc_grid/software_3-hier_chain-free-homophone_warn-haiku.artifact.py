PLAN_PURGE: SPEC, TEST CASES, AND OPEN QUESTIONS

SECTION 1: FINAL SPEC

1.1 Interface

plan_purge(accounts, today). accounts is a list of account records. today must be a datetime.date. Any other type, including datetime.datetime, raises TypeError.

Each account record has the keys id, email, status, last_seen_at, last_login, closed_at, closed_by, unpaid_invoices, and litigation_hold. The old tenant column is ignored.

The function returns a list of action records, at most one per account, sorted by account_id ascending. The function is pure: no I/O, no mutation of inputs. An empty input list returns an empty list.

Each action has exactly these four keys: account_id, action (one of "delete", "anonymise", "warn"), due (ISO "YYYY-MM-DD" string), and approved_by. Per the client spec, no action contains the email address or any other field. This conflicts with a team convention; see open question Q1.

1.2 Due date

inactivity_due = last_seen_at plus 730 calendar days (plain day arithmetic, not calendar years).

If closed_at is set: closed_due = closed_at plus 30 days, and due = the earlier of closed_due and inactivity_due.

If closed_at is None: due = inactivity_due.

last_login is never read.

1.3 Exclusions (applied first)

An account with litigation_hold truthy gets no action.

An account is staff if its email ends with "@tidewater-klatring.no", matched case-insensitively. Staff accounts get no action.

The status field is not read.

1.4 Classification (for non-excluded accounts)

If due is on or before today, the account is due for removal. If unpaid_invoices is truthy, the action is "anonymise". Otherwise the action is "delete". approved_by is the approver name.

If today is before due and due is on or before today plus 40 days, and closed_by is not "member", the action is "warn". approved_by is None.

Otherwise there is no action.

Only closed_by equal to "member" suppresses a warning. Warnings still apply to accounts with unpaid invoices, since the anonymise rule only covers the due-for-removal case.

1.5 Cap

At most 200 "delete" actions are returned per run. "anonymise" and "warn" actions are not counted.

If there are more than 200 delete candidates, they are ordered as follows: closed accounts (closed_at set) first, then accounts with closed_at None. Within each group, order by due ascending, then by account_id ascending (string comparison). The first 200 are returned. Candidates beyond the cap are not returned and remain due for a later run.

The ordering is deterministic for a given input, independent of input list order.

1.6 Output constants

approved_by for delete and anonymise actions is the string "Þórdís Sveinbjörnsdóttir", encoded as UTF-8. approved_by for warn actions is None.

1.7 Validation

today not a datetime.date (including datetime.datetime): TypeError.

last_seen_at is None: ValueError. Validation applies to all records, including excluded ones (recommended; see Q8).

last_seen_at or closed_at (when not None) is a non-date type, such as a string or datetime.datetime: TypeError.

Two records share the same id: ValueError (recommended; see Q9).

1.8 Edge case decisions (tentative, for client confirmation)

Case (a), closed_at in the future: apply the formula as written. The closed due date is in the future, so the account may get a warn or no action. Tentative; flagged.

Case (b), closed account with unpaid invoices that is due: anonymise. If closed_by is "member", there is still no warn. Tentative.

Case (c), litigation hold and staff: no action. Tentative.

Case (d), staff account with unpaid invoices that is due: no action. Tentative.

Case (e), account closed by staff in the warning window: warn. Tentative.

Case (f), closed_by is not "member" (including other values or None) while closed_at is set: treated as a non-member closure, so the account can be warned. Tentative; flagged.

Case (g), a required date is None: ValueError. Tentative; flagged.

Case (h), duplicate account ids: ValueError. Recommendation; flagged.

Case (m), unpaid_invoices is evaluated by Python truthiness: 0, False, and None are falsy; 1 and True are truthy. Non-count, non-bool values are open (Q5).

Cases (i) through (p) are covered by the tests in Section 2.

SECTION 2: NUMBERED TEST CASES

Conventions: today is 2026-10-13 unless stated. Unless a field is given, each record uses email "member@example.com" (not staff), closed_at None, closed_by None, unpaid_invoices 0, litigation_hold False, status "active", and last_login 2026-10-01. Expected output is written as (account_id, action, due, approved_by). NAME means "Þórdís Sveinbjörnsdóttir". Each expected action has exactly four keys, with no email.

Priority order: basic and deletion rules first, then the cap, then exclusions, unpaid values, leap years, future closures, validation, and warnings last.

Basics and deletion rules

T01. Empty input. Inputs: accounts = []. today = 2026-10-13. Expected: [].

T02. today is a datetime. Inputs: one valid account, today = datetime(2026,10,13). Expected: TypeError. (A string today also raises TypeError.)

T03. Basic delete and output shape. Inputs: id "a1", last_seen_at 2024-10-13. Expected: [("a1", "delete", "2026-10-13", NAME)]. Keys are exactly account_id, action, due, approved_by.

T04. Input not mutated. Inputs: the T03 input. Deep-copy before the call. Expected: after the call, the input equals the copy, and list order is unchanged.

T05. last_login ignored. Inputs: id "a2", last_seen_at 2026-10-01, last_login 2024-01-01. Expected: []. The inactivity due is 2028-09-30, so no action.

T06. last_seen_at used, not last_login. Inputs: id "a3", last_seen_at 2024-10-13, last_login 2026-10-12. Expected: [("a3", "delete", "2026-10-13", NAME)].

T07. Due exactly today is a delete, not a warn. Inputs: id "a4", last_seen_at 2024-10-13, unpaid_invoices 0. Expected: [("a4", "delete", "2026-10-13", NAME)].

T08. Due yesterday. Inputs: id "a5", last_seen_at 2024-10-12. Expected: [("a5", "delete", "2026-10-12", NAME)].

T09. Due today with unpaid invoices. Inputs: id "a6", last_seen_at 2024-10-13, unpaid_invoices 1. Expected: [("a6", "anonymise", "2026-10-13", NAME)].

T10. Closure gives the earlier due date. Inputs: id "a7", last_seen_at 2026-10-01, closed_at 2026-09-13, closed_by "member". Closed due is 2026-10-13, inactivity due is 2028-09-30. Expected: [("a7", "delete", "2026-10-13", NAME)].

T11. Inactivity gives the earlier due date. Inputs: id "a8", last_seen_at 2024-10-13, closed_at 2026-10-30, closed_by "member". Closed due is 2026-11-29, inactivity due is 2026-10-13. Expected: [("a8", "delete", "2026-10-13", NAME)].

T12. Closed in the past, closed by staff. Inputs: id "a9", last_seen_at 2026-10-01, closed_at 2026-08-14, closed_by "staff". Closed due is 2026-09-13. Expected: [("a9", "delete", "2026-09-13", NAME)].

T13. Closed by member, due, with unpaid invoices. Inputs: id "a10", last_seen_at 2026-10-01, closed_at 2026-09-13, closed_by "member", unpaid_invoices 2. Expected: [("a10", "anonymise", "2026-10-13", NAME)].

Cap

T14. Exactly 200 deletes. Inputs: 200 inactive accounts, ids "acc-001" through "acc-200", each last_seen_at 2024-10-12 (due 2026-10-12). Expected: all 200 returned as delete actions, sorted by id.

T15. 201 deletes. Inputs: 201 inactive accounts, ids "acc-001" through "acc-201", each last_seen_at 2024-10-12. Expected: 200 returned, "acc-001" through "acc-200". "acc-201" is absent.

T16. Cap cuts through a mix of closed and inactive accounts. Inputs: 150 closed accounts, ids "c-001" through "c-150", each closed_at 2026-09-12 (due 2026-10-12), closed_by "staff", last_seen_at 2026-10-01. Also 100 inactive accounts, ids "i-001" through "i-100", each last_seen_at 2024-09-01 (due 2026-09-01). Expected: all 150 "c-" accounts plus "i-001" through "i-050". "i-051" through "i-100" are absent. Closed accounts come first even though their due dates are later.

T17. Closed group goes first even with a later due date. Inputs: 200 inactive accounts, ids "i-001" through "i-200", each last_seen_at 2024-10-01 (due 2026-10-01). One closed account, id "c-001", closed_at 2026-09-13, closed_by "member" (due 2026-10-13). Expected: "c-001" plus "i-001" through "i-199". "i-200" is absent.

T18. Anonymise is not counted against the cap. Inputs: 201 inactive accounts, ids "d-001" through "d-201", each last_seen_at 2024-10-13 with unpaid_invoices 0; plus 3 accounts, ids "n-001" through "n-003", each last_seen_at 2024-10-13 with unpaid_invoices 1. Expected: 200 deletes ("d-001" through "d-200") and 3 anonymise actions ("n-001" through "n-003"), 203 actions total.

T19. Ordering is stable for the same input. Inputs: the T15 accounts in reversed or shuffled list order. Expected: exactly the same output as T15.

Exclusions

T20. Litigation hold, due today. Inputs: id "h1", last_seen_at 2024-10-13, litigation_hold True. Expected: [].

T21. Litigation hold with unpaid invoices. Inputs: id "h2", last_seen_at 2024-10-13, unpaid_invoices 1, litigation_hold True. Expected: [].

T22. Staff email, due today, case-insensitive match. Inputs: id "s1", email "Ada.Lovelace@TIDEWATER-KLATRING.NO", last_seen_at 2024-10-13. Expected: [].

T23. Look-alike domains are not staff. Inputs: id "s2", email "x@nottidewater-klatring.no", last_seen_at 2024-10-13; id "s3", email "x@tidewater-klatring.no.example.com", last_seen_at 2024-10-13. Expected: ("s2", "delete", "2026-10-13", NAME) and ("s3", "delete", "2026-10-13", NAME).

T24. Staff account with unpaid invoices, due (case d). Inputs: id "s4", email "ops@tidewater-klatring.no", last_seen_at 2024-10-13, unpaid_invoices 3. Expected: [].

T25. Staff account with litigation hold (case c). Inputs: id "s5", email "ops@tidewater-klatring.no", last_seen_at 2024-10-13, litigation_hold True. Expected: [].

T26. Litigation hold on a closed account closed by staff. Inputs: id "h3", last_seen_at 2026-10-01, closed_at 2026-09-13, closed_by "staff", litigation_hold True. Expected: [].

Unpaid invoices values (all due today; "due" means last_seen_at 2024-10-13)

T27. unpaid_invoices 0: delete. Expected: ("u0", "delete", "2026-10-13", NAME).

T28. unpaid_invoices False: delete. Expected: ("uF", "delete", "2026-10-13", NAME).

T29. unpaid_invoices None: delete. Expected: ("uN", "delete", "2026-10-13", NAME).

T30. unpaid_invoices 1: anonymise. Expected: ("u1", "anonymise", "2026-10-13", NAME).

T31. unpaid_invoices True: anonymise. Expected: ("uT", "anonymise", "2026-10-13", NAME).

T32. unpaid_invoices 2, due yesterday (last_seen_at 2024-10-12): anonymise with due "2026-10-12". Expected: ("u2", "anonymise", "2026-10-12", NAME).

Leap years (730-day offset)

T33. Due on the day of today, crossing a leap day. Inputs: id "l1", last_seen_at 2024-02-28, today 2026-02-27. Due is 2026-02-27. Expected: [("l1", "delete", "2026-02-27", NAME)].

T34. Last seen on 29 February, due the day after today. Inputs: id "l2", last_seen_at 2024-02-29, today 2026-02-27. Due is 2026-02-28, which is today plus 1. Expected: [("l2", "warn", "2026-02-28", None)]. The due date is not 2026-02-29, which does not exist.

T35. Last seen on 29 February, due on the day of today. Inputs: id "l3", last_seen_at 2024-02-29, today 2026-02-28. Expected: [("l3", "delete", "2026-02-28", NAME)].

T36. Last seen on 1 March after a leap year. Inputs: id "l4", last_seen_at 2024-03-01, today 2026-03-01. Expected: [("l4", "delete", "2026-03-01", NAME)].

Future closed_at (case a)

T37. Future closure, member, inactivity far off. Inputs: id "f1", last_seen_at 2026-10-01, closed_at 2026-10-20, closed_by "member". Closed due is 2026-11-19, which is today plus 37. Expected: [] (member closure, no warn).

T38. Future closure, closed by staff. Inputs: id "f2", last_seen_at 2026-10-01, closed_at 2026-10-20, closed_by "staff". Expected: [("f2", "warn", "2026-11-19", None)].

Validation

T39. last_seen_at is None (case g). Inputs: id "v1", last_seen_at None. Expected: ValueError.

T40. last_seen_at is a string. Inputs: id "v2", last_seen_at "2024-10-13". Expected: TypeError.

T41. last_seen_at is a datetime. Inputs: id "v3", last_seen_at datetime(2024,10,13,0,0). Expected: TypeError.

T42. closed_at is a string. Inputs: id "v4", last_seen_at 2026-10-01, closed_at "2026-09-13". Expected: TypeError.

T43. Duplicate ids (case h). Inputs: two records, both id "dup", both last_seen_at 2024-10-13. Expected: ValueError.

T44. Bad date on an excluded account. Inputs: id "v5", email "ops@tidewater-klatring.no", last_seen_at None. Expected: ValueError (recommended behaviour; see Q8).

Warnings (lowest priority)

T45. Due tomorrow, no closure. Inputs: id "w1", last_seen_at 2024-10-14. Expected: [("w1", "warn", "2026-10-14", None)].

T46. Due exactly today plus 40. Inputs: id "w2", last_seen_at 2024-11-22. Due is 2026-11-22. Expected: [("w2", "warn", "2026-11-22", None)].

T47. Due today plus 41. Inputs: id "w3", last_seen_at 2024-11-23. Expected: [].

T48. Member closure in the window. Inputs: id "w4", last_seen_at 2026-10-01, closed_at 2026-09-14, closed_by "member". Closed due is 2026-10-14. Expected: [].

T49. Staff closure in the window (case e). Inputs: id "w5", last_seen_at 2026-10-01, closed_at 2026-09-14, closed_by "staff". Expected: [("w5", "warn", "2026-10-14", None)].

T50. Closed_by is "other" or None with closed_at set (case f). Inputs: id "w6", closed_at 2026-09-14, closed_by "other", last_seen_at 2026-10-01; id "w7", closed_at 2026-09-14, closed_by None, last_seen_at 2026-10-01. Expected: ("w6", "warn", "2026-10-14", None) and ("w7", "warn", "2026-10-14", None).

T51. Warn for an account with unpaid invoices. Inputs: id "w8", last_seen_at 2024-10-18, unpaid_invoices 1. Due is 2026-10-18, which is today plus 5. Expected: [("w8", "warn", "2026-10-18", None)]. No anonymise, since the account is not yet due for removal.

SECTION 3: OPEN QUESTIONS FOR THE CLIENT

Q1 (blocking). Email on action records. Our team convention requires the account email on every action record so support can follow up with members. The client spec forbids any field other than the four listed, and forbids the email. The tests in Section 2 assume no email. The client must decide before implementation. Email is personal data, so the client should weigh that in the decision. If the answer is to include the email, the output-key tests (T03, T27 to T32, and the warn tests) need updating.

Q2. Status field. The spec ignores status. Please confirm. If any status value means the account is already deleted or anonymised, tell us which values, because the function would otherwise plan actions for them again.

Q3. Repeat emission. The function is stateless. After an anonymise or delete, last_seen_at is unchanged, so the account is emitted again on every run until the upstream system changes it. Options: the upstream system updates the record, the caller passes a list of already-processed ids, or the function remains stateless and the caller filters results. The client needs to choose.

Q4. Cap and anonymise. The cap counts only deletes, but anonymise still writes to the database. Should anonymise also count against a cap? If yes, the cap ordering rule needs a second pass for anonymise.

Q5. Non-count, non-bool unpaid_invoices values. Under truthiness, the string "0" is truthy and triggers anonymise, and a negative number is truthy. Should these raise ValueError, or should truthiness apply?

Q6. Future closed_at (case a). The formula is applied as written. An account with a future closed_at and an inactivity due date in the past is deleted now, because due is the earlier of the two dates. Confirm this is intended, or say whether a future closed_at should be rejected as bad data.

Q7. Future closed_at and anonymise. Accounts with no unpaid invoices and a future closed_at whose inactivity due date is past get "delete", not "anonymise". Confirm this is the intended status.

Q8. Validation scope. Should a bad date on a staff or litigation-hold account raise, or be ignored because the account is excluded? The recommendation is to raise, so bad data is caught early.

Q9. Duplicate ids. The recommendation is to raise ValueError before any classification, because duplicate ids make the cap ordering and the output sort ambiguous and could cause the same account to be acted on twice. Confirm.

Q10. Type of error for bad values. The spec says None raises ValueError and wrong types (string, datetime) raise TypeError. Confirm this split.

Q11. Email values. What if email is None or not a string? The proposal is to raise ValueError. Should whitespace around the email be trimmed before the staff check?

Q12. Approver name. approved_by is a fixed name in the code. Should the approver come from the caller for each run, or is a fixed name the intended sign-off?

Q13. Cap fairness. Closed accounts always go first in the cap. If closures keep arriving, inactive accounts could wait indefinitely. Confirm this is the intended priority.