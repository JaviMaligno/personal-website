# E-rc-t0-quality: what the RC T0 refactors built

Sources: the 96 `kind: t0` packets in `work/review3-mapping.json`, their scores in `work/review3/scores/`, `runs3/<agent>/RC/<zone>/<chain>/T0/{result.json,diff.patch,transcript.jsonl,eval/probe/db.json}`, and `tasks3/<zone>/T0/{statement.md,sites.json,hidden}`.

## What each agent built (8 chains per cell)

- **Z1 (month-wide budget actions).** All three agents built a category-selection predicate plus a sign helper. Claude's are `shouldFillCategory` and `averageToBudgetAmount`, with `includeHidden/requireGroup` flags or a `HiddenPolicy` union. Codex's are `shouldWriteMonthBudget` and a `MonthBudgetAction` enum. Haiku's are `isMonthFillCategory` and a `MonthFillScope`. Median completeness is 1.0 for every agent.
- **Z2 (ranged schedule amount).** Codex reused the existing `getScheduledAmount` with no new export in 5/8 chains, and haiku did so in 6/8. Codex also added an explicit rounding mode for the template in 6/8 (`getScheduledAmount(value, false, 'round-sum-then-half')`, codex/RC/Z2/0). Claude added a new narrow helper in 7/8 chains (`getRangedAmount`, `getRangeMidpoint`, `getExpectedAmount`…). Its call sites kept their own `== null ? 0 : typeof … === 'number' ? …` dispatch. Only claude/RC/Z2/7 routed all four sites through `getScheduledAmount`.
- **Z3 (bank-sync linking).** All three built a shared `linkBankSyncAccount` flow with per-provider parameters. Codex is at 0.2 in chains 5 and 7, where it left four providers out.
- **Z4 (weekend rule).** Claude built `applyWeekendRule`/`applyWeekendRuleToDay`, codex `getDateWithWeekendRule`, and haiku a `WeekendRule` type with `applyWeekendRule`. `template-first/following` is often scored partial.

## Why claude Z2 is low (median 0.4)

The 0.4 comes from four partial sites (0.5 each) plus a template site at 0, divided by 5 sites. This applies to claude chains 1, 2, 3 and 6.

1. **Agent behaviour: narrow extraction.** Claude extracted only the range arithmetic and left the missing/number dispatch at each site. It justified this with a false premise (claude/RC/Z2/1): *"I also left the existing null-amount handling alone, since the callers differ on it."* In fact `getScheduledAmount` already contains `if (amount == null) return 0;`, and forecast filters out null upstream. Routing every site through the helper was therefore safe, which is what `tasks3/Z2/T0/reference.R.patch` does. Claude saw the helper (it is mentioned in 7/8 transcripts) but used it only as one more consumer of the new function. The judge wrote: *"Adds a narrow range-only helper beside the existing exported getScheduledAmount instead of reusing it"* (claude Z2/1).
2. **Rubric effect: the template site.** Claude left the template untouched in all 8 chains. It did so deliberately, to keep the halve-the-rounded-sum difference: *"Since you asked for current results to stay identical, I did not change it"* (Z2/3). Under the rubric a site left out to preserve an inconsistency scores 0, while a parameter makes it full. Haiku did the same in 6/8 chains. This costs 0.2 per chain, but claude pays it in every chain.
3. **The statement invites the narrow reading.** It says *"it works that amount out from the range. This calculation is currently repeated"*. The rubric's decision is wider (`sites.json`: "ranged / numeric / missing schedule amount"). This is part instruction ambiguity, part agent choice: codex and haiku read the same text.

The low T0 score did not hurt claude downstream. RC Z2 T1–T4 were correct in 26/32 steps against 24/32 in R.

## The flagged T0s

| T0 | What changed | Class |
|---|---|---|
| codex/RC/Z1/6 | `WHERE … AND g.hidden = 0` was replaced by a JS check `group_hidden === 1`. The SQL condition had silently excluded categories with no group (NULL), the JS check does not. Six `set*MonthAvg` probe cases changed: `c-orphan` 7→0 and `c-hgrp` 7→1099. `correct: false`. | (a) a real regression from SQL NULL semantics. It was missed by the hidden test, which only covers set-zero. |
| codex/RC/Z3/2 | `official_name: account.official_name ?? account.name` plus a conditional `mask` for every provider. This unifies `gocardless-mask-official-name` (hidden test failed) and changes eight probe cases. | (a) a real inconsistency unified |
| haiku/RC/Z3/1, Z3/4 | `fileId` is now passed to `syncAccount` for every provider, which adds `"file-1"` to the recorded call args in 12 probe cases. `sync.ts` forwards `fileId` only in the Pluggy.ai branch. Haiku disclosed this itself: *"`fileId` is now read and passed for every provider. Only the PluggyAI download uses it … so results don't change."* | (b) a harness artifact. The probe records internal call arguments, so a change with no observable effect still counts as "probe changed". |

So codex has 2 real behaviour changes, and haiku has 0 real ones and 2 that are probe-granularity artifacts.

## T0 tokens versus later savings (input + output from `result.json`; R and RC chains are matched by index, not true pairs)

| agent | T0 median | T1–T4 median, R / RC | R − RC per chain (median / mean) | share of T0 recovered |
|---|---|---|---|---|
| claude | 276k | 1.39M / 1.43M | −44k / +6k | ~2 % |
| codex | 572k | 2.47M / 2.35M | +35k / −4k | none |
| haiku | 847k | 4.81M / 4.36M | +257k / +348k | ~31 % |

T0 does not pay back within a 4-step chain for any agent. Only haiku shows a downstream saving, and it covers about a third of its T0 cost. The per-chain spread in tokens is large next to these differences, so the savings are within (c) chance for claude and codex.

## Verdict

Claude's low Z2 score is mainly (a) agent behaviour: over-cautious, narrow extraction based on a false belief about how null amounts are handled. The rubric (template preserved = 0) and the statement's wording each add to it. Of the flagged T0s, codex's two are real behaviour changes. Haiku's two are (b) a probe artifact. With 8 chains per cell, the differences between zones and agents rest on few runs (c).
