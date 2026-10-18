# Batch 2 statement review (mined tasks incl. [AI]) — Codex reviewer

Reviewer: `codex exec --model gpt-6-luna`, all tools and web search disabled (same flags as the memo probe), prompt = tasks/_reviews/reviewer-prompt.txt header + statement + commit diff (source and hidden tests). Claude was not used (quota rule, before 22:00).

## Round 1 verdicts

TASK 041f9f3b6e  
SOLVABLE: yes — The statement specifies the public method, argument shape, return value, open-budget requirement, documentation, distinct-ID validation, error message, and unchanged merge behavior.  
LEAK: no.  
FIX: none.

TASK 068185751c  
SOLVABLE: yes — The statement covers both transaction export paths and CLI output, the trigger characters, text versus numeric handling, unchanged headers and columns, and carriage-return quoting.  
LEAK: no.  
FIX: none.

TASK 208283a517  
SOLVABLE: yes — It specifies which schedule-linked rules to exclude, the absent-map-entry behavior, unchanged counting for other rules, and refreshing counts when schedules change.  
LEAK: no.  
FIX: none.

TASK 23da0016d2  
SOLVABLE: no — The hidden tests require every entry in `currencies` to expose a numeric, non-negative `decimalPlaces` field. The statement asks for `getDecimalPlaces` and says the list records decimal places, but doesn’t explicitly require that field on each currency entry.  
LEAK: no.  
FIX: Add that every currency object in the exported `currencies` list must include a numeric, non-negative `decimalPlaces` field, with 2 for the empty-code entry and the appropriate value for each currency.

TASK 4350045c3b  
SOLVABLE: yes — The statement specifies the importer’s export and signature, the missing-payee property behavior, transfer-child behavior, and parent payee fields.  
LEAK: no.  
FIX: none.

TASK df4dc0d6cc  
SOLVABLE: yes — The statement covers creation and update, stored settings when the update omits the field, and leaving the marker unchanged when auto-posting is disabled.  
LEAK: no.  
FIX: none.

TASK 53dae19f70  
SOLVABLE: yes — The statement specifies accepted institution inputs, name normalization, the two-field match rule including null names, creation behavior, and the returned record fields.  
LEAK: no.  
FIX: none.

TASK 35e04473aa  
SOLVABLE: yes — The statement specifies the new function’s signature and behavior, covers the weekend and end-of-schedule cases exercised by the tests, and explains how both callers should use it. No hidden-test expectation is left underivable.

LEAK: no — “the one that exports `getNextDate`” identifies the module by its public interface. The remaining details describe required behavior, not a specific implementation.

FIX: none.

TASK 93508bc6a3  
SOLVABLE: yes — The statement specifies the parent fields and their values, literal-text handling, cleanup before saving, and the import, split, transfer, and duplicate-import outcomes checked by the tests.

LEAK: no — The named formula variables and reconciliation outcomes are public behavior. No implementation-specific code structure or internal API is prescribed.

FIX: none.

TASK f78a6fa041  
SOLVABLE: yes — The statement covers the option’s type and accepted values, trimming and title-case defaults, invalid-value rejection before import, the reconciliation options object and defaults, and the affected import paths.

LEAK: no — The function names and option shapes define the requested interface; they do not prescribe how to implement it.

FIX: none.

TASK 9788bb123a  
SOLVABLE: yes — the statement specifies the event payload, step order behavior, tick semantics, totals, throttling, final event, importer requirements, and client behavior closely enough to implement against the hidden tests.

No hidden-test expectations in the provided tests are left derivable only from the diff: the progress tests assert the stated examples, and the scheduled-transaction tests assert the explicitly stated tick timing and error propagation.

LEAK: yes — it exposes implementation structure beyond the required behavior:

- “Add a module `progress` next to the budget importers (in the same directory as the YNAB4 and YNAB5 importers)”
- “exporting `type ImportTick`” and the exact `runImportSteps(steps: ...)` signature
- “by the system clock, `Date.now()`”
- “the importer function `importScheduledTransactions(data, entityIdMap, flagNameConflicts, tick)` must be exported from the YNAB5 importer module”

FIX: Keep the event behavior and importer-visible outcomes. Remove the prescribed module location and shared-runner API unless those are intentionally part of the benchmark’s public interface. Describe the 100 ms throttle behavior without requiring `Date.now()`. Specify the scheduled importer’s observable tick timing and failure behavior without prescribing its export name, module, or argument list.
## Adjudication

- 23da0016d2: fixed. The statement now says every `currencies` entry has a numeric, non-negative `decimalPlaces` (already true at base; the hidden test checks it).
- 9788bb123a: LEAK kept as justified interface. The hidden tests import `runImportSteps` from `./progress` and `importScheduledTransactions` from the YNAB5 importer, and they pin `Date.now` to make the 100 ms throttle deterministic. The module location, the export names and the clock source are therefore part of the tested interface (same precedent as 81ea158cf6 in batch 1).
- All others: SOLVABLE yes, LEAK no, no changes.
