# Adjudication — issue-5694

- **Round:** 1 of at most 2 (spec 4.2); converged.
- **Adjudicated by:** adjudicator-agent:batch5 (orchestration workflow `agent-abstractions-batch5`,
  phase Validate, model claude-opus-5-5), committed in `cd3af7c` (2026-10-06).
- **Classification:** type-only.
- **Failing check:** typecheck failed: `new Map(all.map(t => [t.id, t]))` inferred an untyped Map, so `byId.get(...)` fields were errors.
- **What changed in the hidden test:** `new Map(...)` -> `new Map<string, (typeof all)[number]>(...)`.
- **References:** unchanged (A and AP). After the edit `aa issues check --force` gave sanity ok
  on A, AL, AP and APL, including the hidden tests still failing on every untouched variant.

## Pre-adjudication version

**Partially reconstructable.** The pre-adjudication file was never committed: the task directory was first committed in cd3af7c, after the edit, so `git show cd3af7c^` has no version of it. The adjudicator's session transcript (batch5, session `a71b0502622ee3ad1`) records the exact string replacements, which are reversed below. After those replacements it also ran `oxfmt` over the file, and for this file `oxfmt` changed the formatting too (quotes / line wrapping); the formatting before that pass is **not recoverable**. The diff below therefore shows the semantic edits only, rendered in the post-format layout. No assertion is touched.

```diff
--- a/packages/loot-core/src/server/transactions/split-transfer.test.ts (before adjudication)
+++ b/packages/loot-core/src/server/transactions/split-transfer.test.ts (cd3af7c)
@@ -68,3 +68,3 @@
   );
-  const byId = new Map(all.map(t => [t.id, t]));
+  const byId = new Map<string, (typeof all)[number]>(all.map(t => [t.id, t]));
 
```
