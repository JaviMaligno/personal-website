# Adjudication — issue-6244

- **Round:** 1 of at most 2 (spec 4.2); converged.
- **Adjudicated by:** adjudicator-agent:batch5 (orchestration workflow `agent-abstractions-batch5`,
  phase Validate, model claude-opus-5-5), committed in `cd3af7c` (2026-10-06).
- **Classification:** over-specified test.
- **Failing check:** hidden test failed with the reference on all four conditions: it compared the stored row with `toEqual` on a literal of five fields, and the query also returns `id`. The statement does not constrain extra columns, so the assertion over-specified the row shape (classified *over-specified test*, spec 4.2).
- **What changed in the hidden test:** the one row literal in 'posts a later occurrence on the requested date' is wrapped in `expect.objectContaining({...})` with the same five fields; no other change.
- **References:** unchanged (A and AP). After the edit `aa issues check --force` gave sanity ok
  on A, AL, AP and APL, including the hidden tests still failing on every untouched variant.

## Pre-adjudication version

**Reconstructed exactly.** The pre-adjudication file was never committed (the task directory was first committed in cd3af7c, after the edit; `git show cd3af7c^` has no version of it). The adjudicator's transcript (batch5, session `a71b0502622ee3ad1`) records the exact string replacements, and its `oxfmt` pass left this file unchanged (only 1062, 1827 and 5694 were reformatted), so reversing the replacements gives the pre-adjudication bytes. Diff from that reconstruction to the committed file:

```diff
--- a/packages/loot-core/src/server/schedules/post-occurrence.test.ts (before adjudication)
+++ b/packages/loot-core/src/server/schedules/post-occurrence.test.ts (cd3af7c)
@@ -98,3 +98,3 @@
     expect(txns).toEqual([
-      {
+      expect.objectContaining({
         date: "2017-01-16",
@@ -104,3 +104,3 @@
         schedule: scheduleId,
-      },
+      }),
     ]);
```

## Exposure found after adjudication (orchestrator audit, 2026-10-06)

The implementer of this task copied the hidden test out of the `aa issues check` sanity
output and ran it, so the references committed in cd3af7c are not independent of the
hidden test. They are being regenerated blind (`implementer-agent-blind:issue-6244`,
batch6, statement and code only); `task.json` carries
`reference_status: pending_blind_regeneration` until then, and the eligibility
(`aa issues eligibility --task issue-6244`) must be recomputed on the new
`reference.A.patch`. The test edit above is independent of this: it was made by the
adjudicator from the reference's failure output.

## Blind reference check (2026-10-06): dropped, `blind_reference_failed`

- **Reference:** regenerated blind (`implementer-agent-blind:issue-6244`, statement and code only).
- **Check:** `aa issues check --task issue-6244 --force` → `reference_fails` on A, AL, AP and APL.
  The untouched variants still fail 3 of 6 hidden tests (discriminating); the reference passes 5 of 6.
- **Failing assertion:** `moves the next date past a posted later occurrence`, line 134:
  `expected '2017-01-16' to be '2017-01-23'`. After `post({id})` and `post({id, date: '2017-01-09'})`
  the next date is 2017-01-16 (passes); posting `date: '2017-01-16'` must then move it to 2017-01-23.
- **Cause:** the reference calls `setNextDate({advance: true, after: date})` only when
  `date > schedule.next_date` (strict), so posting the occurrence equal to the current next date leaves
  that already-posted occurrence as the next date.
- **Classification:** reference wrong, not an over-specified test. Statement point 2 says the schedule
  "must not keep offering, as its next date, an occurrence that is on or before one that was just
  posted", which covers the equal case the test exercises.
- **Decision:** dropped (`blind_reference_failed`) without another reference iteration, because a further
  attempt would be made with knowledge of the hidden-test failure (exposure). The hidden test is unchanged.
