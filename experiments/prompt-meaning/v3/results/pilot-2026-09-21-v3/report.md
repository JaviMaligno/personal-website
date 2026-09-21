# Third study: a definition across an agent handoff

Descriptive exploratory results. Four policies, eight source chains; repeated
inputs and calls are not independent conceptual discoveries. Names were requested
deliberately. The study does not measure spontaneous jargon or long-term adoption.

Completed call records: 133; attempts: 133; invalid execution outputs: 0; invalid generations: 1.

## Correctness

Expected denominators cover planned calls. A missing dependent variant following
invalid generation is listed under chains rather than counted as a correct call.

| Executor | Guide | Inputs | Correct / valid / expected |
|---|---|---|---|
| gpt-sol | visible | visible | 42 / 42 / 42 |
| claude-opus | visible | visible | 42 / 42 / 42 |
| gpt-sol | canonical | visible | 96 / 96 / 96 |
| gpt-sol | canonical | reserved | 224 / 224 / 224 |
| gpt-sol | canonical | separating | 80 / 80 / 80 |
| gpt-sol | source | visible | 84 / 84 / 84 |
| gpt-sol | source | reserved | 196 / 196 / 196 |
| gpt-sol | source | separating | 70 / 70 / 70 |
| claude-opus | source | visible | 84 / 84 / 84 |
| claude-opus | source | reserved | 196 / 196 / 196 |
| claude-opus | source | separating | 70 / 70 / 70 |
| claude-opus | renamed | visible | 48 / 48 / 48 |
| claude-opus | renamed | reserved | 112 / 112 / 112 |
| claude-opus | renamed | separating | 40 / 40 / 40 |
| gpt-sol | renamed | visible | 48 / 48 / 48 |
| gpt-sol | renamed | reserved | 112 / 112 / 112 |
| gpt-sol | renamed | separating | 40 / 40 / 40 |
| claude-opus | received | visible | 84 / 84 / 84 |
| claude-opus | received | reserved | 196 / 196 / 196 |
| claude-opus | received | separating | 70 / 70 / 70 |
| claude-opus | canonical | visible | 96 / 96 / 96 |
| claude-opus | canonical | reserved | 224 / 224 / 224 |
| claude-opus | canonical | separating | 80 / 80 / 80 |
| gpt-sol | received | visible | 84 / 84 / 84 |
| gpt-sol | received | reserved | 196 / 196 / 196 |
| gpt-sol | received | separating | 70 / 70 / 70 |

## Each chain

### recovery--gpt-sol

Both initial executors passed visible cases: **True**.

**source** — Recovery Gate (102 words)

Use “Recovery Gate” as the local name for this decision rule; it is defined here, not asserted as industry terminology. Evaluate only the fields for the change in question and apply rules in this order:

1. If `active_data_loss` is true, return `deny`, regardless of all other fields.
2. Otherwise, return `allow` only when both `db_snapshot` and `db_restore_tested` are true, and either:
   - `external_writes` is false, or
   - `external_writes` is true and `compensation_tested` is true.
3. In every other case, return `review`.

A database restore alone does not establish recovery of external effects. When `external_writes` is true, tested compensation is required for `allow`.

**received** — Recovery Gate (71 words)

"Recovery Gate" is the local name for this rule, defined here, not industry terminology. Apply in order: (1) If active_data_loss is true, return deny, regardless of other fields. (2) Else return allow only if db_snapshot and db_restore_tested are both true and either external_writes is false, or external_writes is true and compensation_tested is true. (3) Otherwise return review. A database restore alone doesn't cover external effects; any examples are illustrative, not exhaustive.

Occurrences of the local name inside the received executable guide: 1. Metadata name retained: True.

| Executor | Guide | Valid repetitions | Visible pass in both | Reserved inputs with errors |
|---|---|---|---|---|
| gpt-sol | canonical | 2 | True | — |
| gpt-sol | source | 2 | True | — |
| gpt-sol | received | 2 | True | — |
| gpt-sol | renamed | 2 | True | — |
| claude-opus | canonical | 2 | True | — |
| claude-opus | source | 2 | True | — |
| claude-opus | received | 2 | True | — |
| claude-opus | renamed | 2 | True | — |

### recovery--claude-opus

Both initial executors passed visible cases: **True**.

**source** — rollback assurance (163 words)

Use this to decide recovery readiness for one change. All five fields describe that same change.

Rollback assurance means the change's effects can be undone in full: the database can be returned to its prior state AND any effects written to external systems can be reversed. A database restore alone does not establish recovery of external effects; external effects require tested compensation.

Evaluate in this order:

1. If active_data_loss is true, output deny. This overrides everything else, regardless of any other field.
2. Otherwise, output allow only if db_snapshot is true AND db_restore_tested is true AND (external_writes is false OR compensation_tested is true).
3. Otherwise, output review.

Output exactly one of: deny, allow, review.

Notes: with external_writes false, compensation_tested is irrelevant. With external_writes true, compensation_tested true is required but never substitutes for db_snapshot and db_restore_tested. Missing or unknown fields cannot be treated as satisfying an allow condition. Add no further requirements beyond those listed; illustrative cases you may have seen are not exhaustive.

**received** — rollback assurance (72 words)

Use rollback assurance for one change; all fields concern that change. Output exactly deny, allow, or review. First, if active_data_loss is true, deny regardless of everything else. Otherwise, allow only if db_snapshot and db_restore_tested are true and either external_writes is false or compensation_tested is true. Otherwise, review. Missing or unknown fields cannot satisfy allow. Compensation is irrelevant without external writes and never replaces database requirements. Add no requirements; examples are not exhaustive.

Occurrences of the local name inside the received executable guide: 1. Metadata name retained: True.

| Executor | Guide | Valid repetitions | Visible pass in both | Reserved inputs with errors |
|---|---|---|---|---|
| gpt-sol | canonical | 2 | True | — |
| gpt-sol | source | 2 | True | — |
| gpt-sol | received | 2 | True | — |
| gpt-sol | renamed | 2 | True | — |
| claude-opus | canonical | 2 | True | — |
| claude-opus | source | 2 | True | — |
| claude-opus | received | 2 | True | — |
| claude-opus | renamed | 2 | True | — |

### approval--gpt-sol

Both initial executors passed visible cases: **True**.

**source** — Scoped Signoff Check (106 words)

Use the Scoped Signoff Check to decide whether approval attached to the specific change and scope permits that change. All fields refer to this change.

1. If prohibited_change is true, output "deny". This takes precedence over every other field.
2. Otherwise, output "allow" only when:
   - owner_signoff is true;
   - scope_matches is true; and
   - either revision_matches is true or nonsemantic_change is true.
3. In every other case, output "review".

A nonsemantic revision may reuse the owner sign-off when nonsemantic_change is true, even if revision_matches is false. It never extends the approved scope, so scope_matches must still be true. Owner sign-off is always required for allowance.

**received** — Scoped Signoff Check (77 words)

Decide whether approval attached to this specific change and scope permits it; all fields describe the same change. 1) If prohibited_change is true, output "deny" — this overrides every other field. 2) Otherwise output "allow" only if owner_signoff is true, scope_matches is true, and either revision_matches or nonsemantic_change is true. 3) Otherwise output "review". A nonsemantic change may reuse the sign-off in place of revision_matches, but never replaces scope_matches or owner_signoff. Apply these rules to every record.

Occurrences of the local name inside the received executable guide: 0. Metadata name retained: True.

| Executor | Guide | Valid repetitions | Visible pass in both | Reserved inputs with errors |
|---|---|---|---|---|
| gpt-sol | canonical | 2 | True | — |
| gpt-sol | source | 2 | True | — |
| gpt-sol | received | 2 | True | — |
| gpt-sol | renamed | 0 | False | — |
| claude-opus | canonical | 2 | True | — |
| claude-opus | source | 2 | True | — |
| claude-opus | received | 2 | True | — |
| claude-opus | renamed | 0 | False | — |

### approval--claude-opus

Both initial executors passed visible cases: **True**.

**source** — bound sign-off (160 words)

Use this guide to decide allow / review / deny for one proposed change. A **bound sign-off** is an owner's approval that is tied to both a specific revision of the change and a specific scope; it authorizes only what it was attached to. A nonsemantic revision (no change in meaning or effect) may reuse an existing bound sign-off, but reuse never extends the sign-off's scope.

All five fields describe this change: owner_signoff, revision_matches, nonsemantic_change, scope_matches, prohibited_change.

Apply in order:
1. If prohibited_change is true → deny. This overrides everything else, regardless of any sign-off.
2. Otherwise, allow only if ALL of these hold: owner_signoff is true, scope_matches is true, and at least one of revision_matches or nonsemantic_change is true.
3. Otherwise → review.

Notes: Missing owner_signoff or missing scope_matches can never be cured by nonsemantic_change — such cases go to review. Examples given to you are illustrative only, not an exhaustive list; decide any combination by the rules above.

**received** — bound sign-off (74 words)

A **bound sign-off** is owner approval tied to a specific revision and scope, authorizing only that attachment. Decide in order: (1) If prohibited_change is true, deny regardless of sign-off. (2) Otherwise, allow only if owner_signoff and scope_matches are true and either revision_matches or nonsemantic_change is true. A nonsemantic revision may reuse approval but never broaden scope. (3) Otherwise, review. Nonsemantic_change cannot cure absent owner_signoff or scope mismatch. Apply to every combination; examples are nonexhaustive.

Occurrences of the local name inside the received executable guide: 1. Metadata name retained: True.

| Executor | Guide | Valid repetitions | Visible pass in both | Reserved inputs with errors |
|---|---|---|---|---|
| gpt-sol | canonical | 2 | True | — |
| gpt-sol | source | 2 | True | — |
| gpt-sol | received | 2 | True | — |
| gpt-sol | renamed | 2 | True | — |
| claude-opus | canonical | 2 | True | — |
| claude-opus | source | 2 | True | — |
| claude-opus | received | 2 | True | — |
| claude-opus | renamed | 2 | True | — |

### evidence--gpt-sol

Both initial executors passed visible cases: **True**.

**source** — Corroboration Gate (104 words)

Use the Corroboration Gate to decide whether a validation claim is deny, allow, or review from five boolean inputs: first_pass, second_pass, shared_source, blind_recheck, and known_contradiction. blind_recheck means a successful independent blind remeasurement.

Apply in this precedence:
1. If known_contradiction is true, deny. This overrides every other input.
2. Otherwise, allow if either:
   - first_pass and second_pass are both true and shared_source is false; or
   - blind_recheck is true and at least one of first_pass or second_pass is true.
3. Otherwise, review.

Shared-source reports alone are insufficient. The blind_recheck condition is a separate route to allowance, so it may allow even when shared_source is true.

**received** — Corroboration Gate (75 words)

Decide deny, allow, or review from first_pass, second_pass, shared_source, blind_recheck (a successful independent blind remeasurement), known_contradiction. Precedence: 1) If known_contradiction is true, deny; this overrides everything. 2) Otherwise allow if first_pass and second_pass are both true and shared_source is false, or if blind_recheck is true and at least one of first_pass or second_pass is true. 3) Otherwise review. Shared-source reports alone are insufficient; blind_recheck is a separate allowance route, valid even when shared_source is true.

Occurrences of the local name inside the received executable guide: 0. Metadata name retained: True.

| Executor | Guide | Valid repetitions | Visible pass in both | Reserved inputs with errors |
|---|---|---|---|---|
| gpt-sol | canonical | 2 | True | — |
| gpt-sol | source | 2 | True | — |
| gpt-sol | received | 2 | True | — |
| gpt-sol | renamed | 0 | False | — |
| claude-opus | canonical | 2 | True | — |
| claude-opus | source | 2 | True | — |
| claude-opus | received | 2 | True | — |
| claude-opus | renamed | 0 | False | — |

### evidence--claude-opus

Both initial executors passed visible cases: **True**.

**source** — Corroboration Gate (158 words)

You judge a single validation claim from five booleans: first_pass, second_pass, shared_source, blind_recheck, known_contradiction. Output exactly one of: deny, allow, review.

The Corroboration Gate is the test below; it has two independent satisfying routes.

Step 1 (highest precedence): if known_contradiction is true, output deny, whatever the other fields say.

Step 2: otherwise the Corroboration Gate is met, and you output allow, if either route holds:
(a) Agreement route: first_pass is true AND second_pass is true AND shared_source is false.
(b) Recheck route: blind_recheck is true AND at least one of first_pass or second_pass is true.
blind_recheck means a successful independent blind remeasurement was performed.

Step 3: otherwise, output review.

Notes: the routes are alternatives; either alone suffices. shared_source being true blocks route (a) only; it never blocks route (b). Reports sharing one source are alone insufficient corroboration; the blind recheck is a separate route. Impose no requirements beyond these. Any examples you have seen are illustrative, not exhaustive.

**received** — Corroboration Gate (70 words)

Judge each claim from the five booleans and output exactly deny, allow, or review. Highest precedence: if known_contradiction is true, deny regardless of all else. Otherwise allow if either: (1) first_pass and second_pass are true and shared_source is false; or (2) blind_recheck is true and at least one of first_pass or second_pass is true. shared_source blocks only route (1). Otherwise review. The routes are independent alternatives; impose no additional requirements.

Occurrences of the local name inside the received executable guide: 0. Metadata name retained: True.

| Executor | Guide | Valid repetitions | Visible pass in both | Reserved inputs with errors |
|---|---|---|---|---|
| gpt-sol | canonical | 2 | True | — |
| gpt-sol | source | 2 | True | — |
| gpt-sol | received | 2 | True | — |
| gpt-sol | renamed | 0 | False | — |
| claude-opus | canonical | 2 | True | — |
| claude-opus | source | 2 | True | — |
| claude-opus | received | 2 | True | — |
| claude-opus | renamed | 0 | False | — |

### retry--gpt-sol

Both initial executors passed visible cases: **True**.

**source** — Retry Clearance (107 words)

Retry Clearance is the decision—allow, deny, or review—on whether a failed operation may be retried. Apply these rules in order:

1. If nonretryable_failure is true, deny. This takes precedence over all other fields.
2. Otherwise, allow if either:
   - receipt_present and receipt_matches are both true; or
   - key_valid and operation_idempotent are both true.
3. Otherwise, review.

A present, matching receipt confirms that this exact operation was never applied, so it permits retry even when operation_idempotent is false. receipt_matches without receipt_present is insufficient. An unmatched receipt is insufficient. key_valid without operation_idempotent is insufficient.

Inputs are booleans: receipt_present, receipt_matches, key_valid, operation_idempotent, and nonretryable_failure. Return exactly allow, deny, or review.

**received** — Retry Clearance (71 words)

Retry Clearance: decide allow, deny, or review on retrying a failed operation. In order: (1) If nonretryable_failure is true, deny; this overrides all other fields. (2) Otherwise allow if receipt_present and receipt_matches are both true (valid even if operation_idempotent is false), or if key_valid and operation_idempotent are both true. (3) Otherwise review. receipt_matches without receipt_present, an unmatched receipt, or key_valid without operation_idempotent are each insufficient. Return exactly allow, deny, or review.

Occurrences of the local name inside the received executable guide: 1. Metadata name retained: True.

| Executor | Guide | Valid repetitions | Visible pass in both | Reserved inputs with errors |
|---|---|---|---|---|
| gpt-sol | canonical | 2 | True | — |
| gpt-sol | source | 2 | True | — |
| gpt-sol | received | 2 | True | — |
| gpt-sol | renamed | 2 | True | — |
| claude-opus | canonical | 2 | True | — |
| claude-opus | source | 2 | True | — |
| claude-opus | received | 2 | True | — |
| claude-opus | renamed | 2 | True | — |

### retry--claude-opus

Both initial executors passed visible cases: **False**.

**source: unavailable**

**received: unavailable**

| Executor | Guide | Valid repetitions | Visible pass in both | Reserved inputs with errors |
|---|---|---|---|---|
| gpt-sol | canonical | 2 | True | — |
| gpt-sol | source | 0 | False | — |
| gpt-sol | received | 0 | False | — |
| gpt-sol | renamed | 0 | False | — |
| claude-opus | canonical | 2 | True | — |
| claude-opus | source | 0 | False | — |
| claude-opus | received | 0 | False | — |
| claude-opus | renamed | 0 | False | — |

## Repeated handoff losses with correct source and canonical policy

Input–executor–chain combinations: **0**.

## Repeated effects of renaming alone

Input–executor–chain combinations: **0**.


## Usage and reference cost

First-to-last call: 382.4 seconds.

Costs use the previous pilot's reference rates, not a provider invoice; exclude
implementation, Codex assistance and previous studies.

- claude-opus: 96921 input / 21357 output tokens; USD 1.0185.
- gpt-sol: 65856 input / 12971 output tokens; USD 0.5228.
