# Adjudication — issue-1957

- **Round:** 1 of at most 2 (spec 4.2); converged.
- **Adjudicated by:** adjudicator-agent:batch5 (orchestration workflow `agent-abstractions-batch5`,
  phase Validate, model claude-opus-5-5), committed in `cd3af7c` (2026-10-06).
- **Classification:** type-only.
- **Failing check:** typecheck failed: force-run-service called without its argument; partial transaction literals passed where a `TransactionEntity` is expected.
- **What changed in the hidden test:** `(undefined)` for force-run-service; `} as TransactionEntity);` on two partial transaction literals (dates 2016-12-29, 2017-01-01); added the type import.
- **References:** unchanged (A and AP). After the edit `aa issues check --force` gave sanity ok
  on A, AL, AP and APL, including the hidden tests still failing on every untouched variant.

## Pre-adjudication version

**Reconstructed exactly.** The pre-adjudication file was never committed (the task directory was first committed in cd3af7c, after the edit; `git show cd3af7c^` has no version of it). The adjudicator's transcript (batch5, session `a71b0502622ee3ad1`) records the exact string replacements, and its `oxfmt` pass left this file unchanged (only 1062, 1827 and 5694 were reformatted), so reversing the replacements gives the pre-adjudication bytes. Diff from that reconstruction to the committed file:

```diff
--- a/packages/loot-core/src/server/schedules/early-posted-redated.test.ts (before adjudication)
+++ b/packages/loot-core/src/server/schedules/early-posted-redated.test.ts (cd3af7c)
@@ -10,2 +10,3 @@
 import { q } from '#shared/query';
+import type { TransactionEntity } from '#types/models';
 
@@ -62,3 +63,3 @@
 async function runScheduleService() {
-  await schedulesApp.handlers['schedule/force-run-service']();
+  await schedulesApp.handlers['schedule/force-run-service'](undefined);
 }
@@ -96,3 +97,3 @@
         date: '2016-12-29',
-      });
+      } as TransactionEntity);
       await runScheduleService();
@@ -138,3 +139,3 @@
         date: '2017-01-01',
-      });
+      } as TransactionEntity);
       await runScheduleService();
```
