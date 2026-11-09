# Technical Spec: `plan_purge` GDPR Clean-up Module (Tidewater Climbing)

**Status:** Draft for client review
**Reference run date:** 2026-10-13
**Requirement IDs:** R1 to R15 are the tech lead's IDs and are unchanged. D1 to D13 are derived. OPEN-n items need client confirmation.

---

## 1. Scope

**In scope:** One pure function, `plan_purge(accounts, today)`, that returns the actions due on `today` (R1, R3).

**Out of scope:** Executing deletions or anonymisation, writing the audit log, database locking, sending member notices, scheduling, and any I/O. The `tenant` column is ignored (R2). `last_login` is not used (R4, D9).

**Priority if scope must be cut:** Deletion correctness (R5, R6, R8, R9, R10, R11, R12, R13) takes precedence over warnings (R7) (R15).

---

## 2. Data Shapes

### 2.1 Input account

| Field | Type | Required | Use |
|---|---|---|---|
| `id` | non-empty str or int, unique within the run | yes | Sort key and output key (R14, D6). OPEN-10 |
| `email` | str | yes | Staff check only (R10, D7). Never output (R11) |
| `status` | str | yes (key only) | Not used in any decision. OPEN-1 |
| `last_seen_at` | `datetime.date` | yes | Inactivity clock (R4) |
| `last_login` | any | not required | Ignored entirely, not validated (D9, R4) |
| `closed_at` | `datetime.date` or None | yes | Closure date (R5) |
| `closed_by` | "member" or "staff" | only when `closed_at` is set | Warn exclusion and cap ordering (R7, D5, D8) |
| `unpaid_invoices` | int (bool allowed) or None | yes | Unpaid if truthy (R8). OPEN-3 |
| `litigation_hold` | bool | yes | Hard exclusion (R9) |
| `tenant` | any | not required | Ignored (R2) |

Dates must be `datetime.date` instances. `datetime.datetime` is a subclass of `date`, so it must be rejected explicitly (D6).

### 2.2 Output action

Each action is a dict with exactly four keys (R3, D10):

- `account_id`: the input `id`.
- `action`: "delete", "anonymise", or "warn".
- `due`: ISO date string "YYYY-MM-DD". This is the computed deletion due date, which may be before `today` (see 3.3).
- `approved_by`: the approver constant for delete and anonymise (R13, D13). None for warn.

No email, no other fields (R11, D10).

### 2.3 Constant

`APPROVER = "Þórdís Sveinbjörnsdóttir"` (R13, D13). Use these exact Unicode characters with no transliteration.

---

## 3. Function Contract

### 3.1 Signature

`plan_purge(accounts, today) -> list[dict]`

- `accounts`: a list of account dicts. An empty list returns an empty list.
- `today`: a `datetime.date`, not a `datetime.datetime`. This is the only clock source (D11). The module must not call `datetime.now` or `date.today`.

### 3.2 Guarantees

- **Pure:** no I/O, no printing, no logging of email addresses or other personal data, and no mutation of input dicts (D11).
- **Fail closed:** if any validation fails, raise `ValueError` before producing any action. Never return a partial result (D6).
- **Sorted:** the result is sorted by `account_id` ascending, using the natural ordering of the id type. The sort is stable. Ids are unique, so the order is total (R14, D10).
- **At most one action per account**, except that no account ever gets both a warn and a delete or anonymise (D1).

### 3.3 Past-due handling

An account whose computed due date is before `today` still gets a delete or anonymise action. Its `due` field holds the computed due date, not `today`. The module is stateless, so a past-due account that is not yet processed is emitted again on every run (OPEN-2).

---

## 4. Rules in Evaluation Order

### Step 0: Compute the due date (R5, D12)

- `base = last_seen_at + 730 days`
- If `closed_at` is None: `due = base`. `closed_by` is ignored (D8).
- If `closed_at` is set: `due = earlier of base and (closed_at + 30 days)`.

Use `date + timedelta(days=N)` exactly as stated (D12).

### Step 1: Precedence (D1)

1. If `litigation_hold` is True: no action (R9). Stop.
2. If the normalised email is a staff address: no action (R10, D7). Stop.
   - Normalise by stripping surrounding whitespace and comparing case-insensitively.
   - Match if the normalised email ends with "@tidewater-klatring.no". The "@" prefix prevents lookalike domains from matching.
3. Classify by `due` against `today`:
   - **Due on or before today** (`due <= today`):
     - If unpaid: `anonymise` (R8).
     - Otherwise: `delete` candidate, subject to the cap (Section 5).
   - **Due within the warn window** (`today < due <= today + 14 days`):
     - If `closed_at` is set and `closed_by == "member"`: no action (R7).
     - Otherwise: `warn`, including unpaid accounts (D3, OPEN-5).
   - **Otherwise:** no action.

### Unpaid rule (R8, OPEN-3)

`unpaid_invoices` is unpaid if it is truthy. None, 0, and False mean not unpaid.

### Window boundaries (D2)

- Delete set: `due <= today`.
- Warn set: `today < due <= today + 14 days`.
- The two sets are disjoint by construction, so no account can receive both.
- `today` itself is never a warn date. Day 14 is included.
- For `today = 2026-10-13`, the warn window is 2026-10-14 through 2026-10-27 inclusive.

### Retention timing (R8, D4)

Unpaid status does not change the 730-day clock or the 30-day closure rule. Anonymise runs on the same date a delete would have run (OPEN-6).

---

## 5. Cap and Ordering (R12, D5)

1. **Candidates:** all accounts classified as `delete` in Step 1.3. Anonymise actions are not counted (OPEN-7).
2. **Ordering of candidates:**
   1. Closed accounts first, meaning `closed_at` is set. This includes both `closed_by` values (OPEN-8).
   2. Ascending by `due`.
   3. Ascending by `account_id` as the tie-break.
3. **Cap:** emit the first 200 candidates as `delete` actions. The cap is "at most 200".
4. **Deferred accounts:** candidates beyond 200 are not emitted this run. They get no warn. This is guaranteed, because a deferred account has `due <= today` and warns require `due > today`.
5. **Uncapped actions:** anonymise and warn actions are not capped by default (OPEN-7, OPEN-12).

---

## 6. Validation (D6)

Raise `ValueError` for any of the following. Validate the entire input before producing output.

- `accounts` is not a list, or `today` is not a `datetime.date` (including `datetime.datetime`).
- An account is not a mapping, or is missing any required key from Section 2.1.
- `last_seen_at` is not a date, or `closed_at` is neither None nor a date.
- `closed_at` is set and `closed_by` is not "member" or "staff".
- `closed_at` is set and `closed_at < last_seen_at`.
- `email` is not a str.
- `litigation_hold` is not a bool.
- `unpaid_invoices` is not an int, bool, or None.
- `id` is not a non-empty str or int, or ids mix types.
- Two accounts share the same `id`.

**Error messages** may name the field and the `account_id`. They must not include the email address or any other personal data.

**Not validated:** `status` content, `last_login`, and `tenant` (D9, OPEN-1).

---

## 7. Edge Cases

`today = 2026-10-13`. The warn window is 2026-10-14 to 2026-10-27. Unless noted, the account is open, has `unpaid_invoices = 0`, `litigation_hold = False`, and a member email.

| # | Input | Computed due | Expected output | Rule |
|---|---|---|---|---|
| E1 | last_seen 2024-10-13, open | 2026-10-13 | delete, due "2026-10-13" | R5, R6, D2 |
| E2 | last_seen 2024-10-12, open | 2026-10-12 | delete, due "2026-10-12" (past due keeps computed date) | R6, Section 3.3 |
| E3 | last_seen 2024-10-14, open | 2026-10-14 | warn, due "2026-10-14" | R7, D2 |
| E4 | last_seen 2024-10-27, open | 2026-10-27 | warn, due "2026-10-27" (day 14 included) | R7, D2 |
| E5 | last_seen 2024-10-28, open | 2026-10-28 | no action (day 15) | R7, D2 |
| E6 | closed_by member, closed_at 2026-09-13, last_seen 2025-06-01 | min(2027-06-01, 2026-10-13) = 2026-10-13 | delete, due "2026-10-13" | R5 |
| E7 | closed_by member, closed_at 2026-09-20, last_seen 2025-06-01 | 2026-10-20 | no action (member closure, no notice) | R7 |
| E8 | closed_by staff, closed_at 2026-09-20, last_seen 2025-06-01 | 2026-10-20 | warn, due "2026-10-20" | R7 |
| E9 | unpaid 2, last_seen 2024-10-01 | 2026-10-01 | anonymise, due "2026-10-01" | R8 |
| E10 | unpaid 1, last_seen 2024-10-20 | 2026-10-20 | warn, due "2026-10-20" (D3 default) | R7, R8, D3 |
| E11 | litigation_hold True, last_seen 2024-10-01 | 2026-10-01 | no action | R9 |
| E12 | email "  Kari@TIDEWATER-KLATRING.no ", last_seen 2024-10-01 | 2026-10-01 | no action (staff) | R10, D7 |
| E13 | closed_at 2025-01-01 earlier than last_seen 2025-06-01 | n/a | ValueError, no actions for any account | D6 |
| E14 | 201 open accounts, all due on or before today | varies | first 200 by due then id emitted as delete; the 201st is not emitted and gets no warn | R12, D5 |
| E15 | closed_by member, closed_at None, last_seen 2024-10-20 | 2026-10-20 | warn (open account; closed_by ignored) | D8, OPEN-9 |
| E16 | unpaid_invoices None, last_seen 2024-10-01 | 2026-10-01 | delete, due "2026-10-01" | R8, OPEN-3 |
| E17 | status "deleted", last_seen 2024-10-01 | 2026-10-01 | delete (status not used) | OPEN-1 |
| E18 | last_seen_at is a datetime.datetime | n/a | ValueError | D6 |
| E19 | last_login missing, otherwise valid | as computed | processed normally | D9 |

---

## 8. Open Points for Client

Each open point gives the default the spec uses until the client confirms.

| ID | Question | Default in this spec |
|---|---|---|
| OPEN-1 | How is `status` used? | No effect on any decision. Client to confirm, in particular whether a status such as "deleted" should exclude an account. |
| OPEN-2 | Are past-due accounts re-emitted every run until processed? | Yes. The caller must deduplicate or track execution. |
| OPEN-3 | Is `unpaid_invoices` a count or a boolean? Are negative values valid? | Truthy means unpaid. Any non-zero value counts, including negatives. |
| OPEN-5 | (D3) Should unpaid accounts in the warn window get a warn? | Yes, because personal data will still be dropped. DPO to confirm. |
| OPEN-6 | (D4) Does Skatteetaten's five-year invoice retention change timing? Does the invoice itself contain personal data (name, address) that anonymise must strip? | No timing change. Anonymise keeps invoices. DPO to confirm against Skatteetaten rules and define exactly which invoice fields are kept. |
| OPEN-7 | Do anonymise actions count toward the 200 cap? | No. Only delete counts. Confirm. |
| OPEN-8 | (D5) Should "closed" for cap priority include `closed_by == "staff"`? R12 says "people who asked to leave" suggests member only. | Yes, `closed_at` set includes both values. Confirm. |
| OPEN-9 | (D8) What if `closed_by` is "member" but `closed_at` is None? | `closed_by` is ignored and the account is treated as open, so a warn can apply. Alternative: reject as inconsistent data. |
| OPEN-10 | (D6) What type is `account_id`? | str or int, unique, one type per run. |
| OPEN-12 | Should warn actions be capped? | No cap. R12 applies to deletions only. |

### Resolved within this spec

- **Warn and delete in the same run:** not possible. The windows are disjoint (D1, D2).
- **Inactivity clock:** `last_seen_at` only (R4). `last_login` is never read (D9).
- **Closure rule:** the earlier of the two dates applies (R5).
- **Precedence:** litigation hold, then staff email, then due date (D1).
- **Approver:** the exact DPO string for delete and anonymise, None for warn (R13, D13).
- **Email exposure:** no action carries an email or any personal field (R11, D10).