# Adjudication — issue-1062

- **Round:** 1 of at most 2 (spec 4.2); converged.
- **Adjudicated by:** adjudicator-agent:batch5 (orchestration workflow `agent-abstractions-batch5`,
  phase Validate, model claude-opus-5-5), committed in `cd3af7c` (2026-10-06).
- **Classification:** type-only.
- **Failing check:** typecheck failed in the hidden test: `schedule/force-run-service` is typed with one parameter (`syncSuccess`) and was called with none.
- **What changed in the hidden test:** `handlers['schedule/force-run-service']()` -> `(undefined)` (2 calls).
- **References:** unchanged (A and AP). After the edit `aa issues check --force` gave sanity ok
  on A, AL, AP and APL, including the hidden tests still failing on every untouched variant.

## Pre-adjudication version

**Partially reconstructable.** The pre-adjudication file was never committed: the task directory was first committed in cd3af7c, after the edit, so `git show cd3af7c^` has no version of it. The adjudicator's session transcript (batch5, session `a71b0502622ee3ad1`) records the exact string replacements, which are reversed below. After those replacements it also ran `oxfmt` over the file, and for this file `oxfmt` changed the formatting too (quotes / line wrapping); the formatting before that pass is **not recoverable**. The diff below therefore shows the semantic edits only, rendered in the post-format layout. No assertion is touched.

```diff
--- a/packages/loot-core/src/server/schedules/month-end-days.test.ts (before adjudication)
+++ b/packages/loot-core/src/server/schedules/month-end-days.test.ts (cd3af7c)
@@ -226,5 +226,5 @@
         setToday(2017, 1, 1);
-        await schedulesApp.handlers['schedule/force-run-service']();
+        await schedulesApp.handlers['schedule/force-run-service'](undefined);
         // Running the service again must not post anything twice.
-        await schedulesApp.handlers['schedule/force-run-service']();
+        await schedulesApp.handlers['schedule/force-run-service'](undefined);
 
```
