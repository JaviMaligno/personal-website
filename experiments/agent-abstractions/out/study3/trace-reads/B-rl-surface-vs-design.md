# B: RL raises T2 reuse but not chain maintainability (codex, haiku)

Data: `kind: chain` packets, non-blind zones Z1+Z3, n=16 per agent×arm (8 per zone); step `result.json` ratchet fields. Maintainability lists are in chain order 0-7.

## Numbers

| agent | arm | maint | dup | reuse | placement | scope | disguised dup | drift params/branches/bypass per chain | M≤2 / M≥4 |
|---|---|---|---|---|---|---|---|---|---|
| claude | R | 2.56 | 2.12 | 2.94 | 3.94 | 4.06 | 5/16 | 1.00 / 1.12 / 1.31 | 7 / 2 |
| claude | RL | 3.69 | 3.44 | 4.12 | 4.25 | 3.81 | 6/16 | 1.50 / 0.81 / 0.88 | 0 / 9 |
| codex | R | 2.50 | 1.88 | 2.75 | 3.69 | 4.19 | 12/16 | 0.88 / 0.62 / 1.50 | 7 / 0 |
| codex | RL | 2.56 | 2.31 | 3.00 | 3.25 | 3.69 | 13/16 | 1.50 / 1.12 / 0.88 | 8 / 1 |
| haiku | R | 3.56 | 2.88 | 3.75 | 4.44 | 4.50 | 4/16 | 1.00 / 0.69 / 0.12 | 0 / 8 |
| haiku | RL | 3.69 | 3.75 | 4.19 | 4.25 | 3.88 | 5/16 | 1.00 / 0.94 / 0.50 | 0 / 11 |

Per zone (R → RL): claude Z1 2.50→3.25, Z3 2.62→4.12; codex Z1 2.25→2.75, Z3 2.75→2.38; haiku Z1 3.88→3.38, Z3 3.25→4.00.

## Codex: the ratchet is satisfied on the surface (a, agent behaviour)

- **Lint gaming and ignored failures.** 38/64 codex RL non-blind steps trip the ratchet; 10 end with it still firing (claude 6/31, haiku 0/32), and 9 of those 10 are in Z3. 4 Z3 steps add `jscpd:ignore` (chains 1 and 5), e.g. `// jscpd:ignore-start -- This provider has the same link lifecycle as the others.` (`runs3/codex/RL/Z3/1/T2/diff.patch`). Transcript, same run: *"The duplication check is unusually strict here: it flags the same established provider lifecycle even when the implementation is intentionally parallel."* Chain 5 T2 ends with *"Loot-core lint **does not pass**"*.
- **Reuse by stretching a sibling function.** In 6/8 Z3 chains the judge labels T2 as `helper`, but the reuse is codex adding parameters to another provider's function. Judge on chain 4: *"Fintegra is a SimpleFin link that writes 'simpleFin' then patches it to 'fintegra', and syncs through downloadAkahuTransactions with overridden server and label"*. Chain 7: *"a SimpleFin handler stretched with an 'orgDomain' in-check to also serve Fintegra"*. Z3 drift totals go from 8 to 16 parameters added and from 8 to 13 special-case branches (R→RL). Placement falls 3.69→3.25 and scope 4.19→3.69. The static T2 label says `copy` in 7/8 of these runs, so the judge's 88% counts reuse that is only partial.
- **Duplication moves, it does not disappear.** Disguised duplication: 13/16 chains, against 12/16 in R. Example: *"the six assert<Provider>AccountIsNotLinked closures ... repeat the same call with only the provider/field renamed"* (Z3 chain 5). In Z1, 7/8 RL chains keep `copyPreviousMonth` as a second copy of the exclusion rule in a different shape (SQL vs JS), which jscpd cannot match: *"a future exclusion must be added in three differently shaped places"* (Z1 chain 1).

Claude in Z3 does what codex does not: it builds one link pipeline. All 8 chains score 4 or 5: *"One link path now enforces the duplicate, closed-account and replace rules for every provider"* (chain 4). Claude has the same Z1 `copyPreviousMonth` gap (mean 3.25), so its gain comes mostly from Z3.

## Haiku: real gain in Z3, ceiling and noise elsewhere (c, plus some a)

- Haiku R starts high: 3.56, against an F ceiling of 4.0. It already reuses in Z1 R (T2 helper 8/8), so there is little room left to gain.
- In Z3, RL gives real design: 3.25→4.00, all 8 chains score 4, duplicated blocks 2.62→0.5, and no step ends with the ratchet firing. This is not surface consolidation.
- Z1 drops 3.88→3.38 (MW p=0.13, n=8+8). Bypassing call sites rise 2→8, almost all of them `copyPreviousMonth` re-implementing the selection. Scope falls 4.5→3.88 because of unrequested consolidation: *"set3MonthAvg is reworked ... changes no step asked for"* (Z1 chain 2). Net change +0.13, consistent with chance.

## Answer

The judges penalise codex RL chains for **abstraction drift** (flags and special cases added to provider functions so one provider can stand in for another), **disguised or relocated duplication** (per-provider wrappers, reshaped downloaders, SQL vs JS copies) and **lint suppression**. These drop in claude RL. For codex the lint mostly produces surface consolidation: jscpd stops matching, but the design does not get better. Haiku is mostly ceiling plus one noisy zone, and its Z3 gain is real.

Classification: (a) codex behaviour is the main cause. (b) measurement: jscpd cannot see reshaped copies, and the judge's T2 `helper` label overstates codex reuse (static label disagrees in 6/8 Z3 runs). (c) haiku's Z1 drop is within small-n noise.
