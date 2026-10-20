# Codex RC: why missed copy drops 33% -> 12%

Source: `runs3/codex/{R,RC}/Z*/c/T*/result.json` (`missed_copy_preexisting` = registered), diffs and transcripts. Raw counts on rule steps T1+T3 (n=16 per zone and arm):

| zone | R missed | RC missed | R correct T1-T4 | RC correct T1-T4 | study-2 F missed |
|---|---|---|---|---|---|
| Z1 | 5 | 1 | 20/32 | 27/32 | 0 |
| Z2 | 12 | 5 | 12/32 | 18/32 | 8 |
| Z3 | 0 | 0 | 32/32 | 32/32 | 0 |
| Z4 | 4 | 2 | 12/32 | 12/32 | 6 |
| all | 21/64 (33%) | 8/64 (12.5%) | 76/128 (59%) | 89/128 (70%) | 14/64 (22%) |

**Z1 and Z2 carry the gain.** Of the 13 fewer misses, Z1 accounts for 4 and Z2 for 7. Z1 and Z2 also account for all 13 extra correct steps. Z4 does not count as a gain: every codex rule step in Z4 fails in every arm (0/64 correct), because codex never fixes the template's weekend loop (study 2, section 5.1). The test `schedule template for a daily schedule counts only its weekday…` fails in 32 of 32 codex T1 runs. Z4's "missed copy" therefore only records which partial failure happened to occur.

## Mechanism: (a) agent behaviour, mostly as in study-2 F

**Z2, T1.** In R, codex consolidates the rule during T1, but only over the copies it finds. The budget template's hand copy (`op === 'isbetween' ? Math.round(num1 + num2) / 2`) has a different shape. Whether the agent finds it predicts the result exactly. In R T1, codex opened `schedule-template.ts` in chains 1, 3 and 4, and those three passed. It never opened the file in chains 0, 2, 5, 6 and 7, and those five missed the template (`R/Z2/5/T1`: "I found three midpoint calculations…"). In RC, the T0 statement says the logic is "repeated rather than defined once", so codex searched for every copy. T0 routed the template through the helper in 6 of 8 chains. At T1, a single helper edit then reached it: chains 0 and 1 pass the template consumer without touching `schedule-template.ts`. The two RC T1 misses are both visible in the traces:
- **Chain 3: T0 never found the template.** `RC/Z2/3/T0`: "I found four copies of the midpoint calculation". At T1: "The shared helper feeds schedule previews, forecast projections, and posted schedule amounts, so one change there will apply consistently."
- **Chain 2: the study-2 F failure, reproduced by codex's own abstraction.** At T0 codex added a mode, `rounding: 'nearest' | 'sum-first'`, to preserve the template's quirk. At T1 it treated that mode as protected: "Schedule templates explicitly request a separate sum-first rounding mode; I'll preserve that behavior" (`RC/Z2/2/T1`). The diff keeps `rounding === 'sum-first' ? Math.round(num1 + num2) / 2`.

RC does better than F in Z2 (5 misses against 8) because codex's own T0 helper carried a named mode in only 3 of 8 chains. Study 2's F helper carried `rangeRounding: 'halfOfRoundedSum'` in every chain.

**Z2, T3 (approximate amounts) does not fit the one-place mechanism.** The helper receives only the amount value, so the operator has to be passed through every caller: "The shared helper currently sees only the amount value… I'm adding the operator as an optional input and threading it" (`RC/Z2/0/T3`). RC still misses at T3 in 6 of 8 chains. Three of those misses fall on the T2 consumer, `api-schedule-list`, which the registered metric excludes; the judge notes it: "scheduleModel.toExternal copies the null/number/range ternary… next to the shared helper" (`RC/Z2/2` chain packet).

**Z1.** The T0 instruction lists `copyPreviousMonth` among the sites. The R consolidations made during T1 often leave it, or one of the averages, outside the shared query. Examples: `R/Z1/5/T3`: "The shared month-action category query is used by zeroing, last-month spending, and the average actions"; `R/Z1/0/T3`: "for set-zero and spending-average". In RC, codex starts T3 from a predicate that every action shares: "All the month-wide actions already share `shouldWriteMonthBudget`, so the change can be centralized there" (`RC/Z1/5/T3`). The edit is not literally a single hunk; non-test hunk counts are similar in R and RC, because each query still has to select the new column. The shared predicate works as an index of consumers, so none is skipped. RC Z1 has one T1 miss (chain 3, the three averages, with a failing fixture left unresolved) and one empty T3 diff (chain 0: "`category_groups` table has no `notes` column", which gives 0/5 and so does not count as a missed copy).

## Verdict

The main finding is agent behaviour (a): once the consolidation exists, one edit reaches every consumer the consolidation covers. The T0 statement increases coverage because it makes codex search for every copy, which a rule-change task does not. The same mechanism produces both failure modes seen in study-2 F: coverage gaps (Z2 chain 3) and a named mode treated as protected (Z2 chain 2). RG and RL do not prompt that search, so codex's limited discovery stays the bottleneck (31%).

Measurement caveats (b): Z4 adds nothing interpretable. The registered metric hides the T2 consumer missed at T3 in Z2; counting all consumers, missed copy is 27/64 in R against 14/64 in RC. Chance (c): about 8 events per zone. The Z2 T1 result (6 misses to 2) and the Z1 result (5 to 1) each come from single cells of 8, so read them together with the traces rather than as separate effects. The pooled model gives a log-odds of -1.76 (sd 0.44).
