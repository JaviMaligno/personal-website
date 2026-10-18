# G: claude chain maintainability gain, design or fewer copies?

Data: claude `chain` packets (T1-T4 diff), n=32 per arm, from `work/review3/scores` + `work/review3-mapping.json`. RL 3.69 is the non-blind Z1+Z3 subset. Over all zones RL is 3.19.

## Means by zone (maintainability)

| arm | all | Z1 | Z2 | Z3 | Z4 | dup_blocks |
|---|---|---|---|---|---|---|
| R | 2.59 | 2.50 | 2.88 | 2.62 | 2.38 | 2.62 |
| RG | 3.09 | 3.38 | 3.12 | 2.75 | 3.12 | 2.03 |
| RL | 3.19 | 3.25 | 3.38 | **4.12** | **2.00** | 1.59 |
| RC | 3.06 | 3.50 | 3.38 | 2.75 | 2.62 | 2.03 |

Each arm's gain comes from a different zone. No arm improves in all four.

## Reasons for low R scores, and whether they go away (keyword tally of `why`, 32 per arm)

| reason | R | RG | RL | RC |
|---|---|---|---|---|
| rule must be edited in N places / copies | 23 | 18 | 19 | 17 |
| overlapping entry points (Z2) | 7 | 5 | 6 | 1 |
| misnamed side-effecting `assert` (Z3) | 8 | 7 | 3 | 6 |
| magic look-ahead bounds (Z4) | 7 | 3 | 5 | 6 |
| praise for "one place / single function" | 8 | 17 | 17 | 12 |

The main complaint, that one rule lives in several places, mostly stays in every lever arm. What changes is the number of copies: "six places" becomes "two places". Typical R: "Every exclusion rule over the four steps had to be added in five or six places" (R/Z1/1, m=1). Typical lever: "Most actions share one selection function, but copyPreviousMonth keeps a parallel four-condition filter" (RL/Z1/3, m=3).

**A regression says the gain is mostly "fewer duplicated blocks".** Model: maint ~ arm + zone. Adding the judge's own `duplicated_blocks` shrinks the arm effects: RG +0.50 to +0.22, RL +0.59 to +0.11, RC +0.47 to +0.19. Across chains, r(maint, dup_blocks) = -0.67. Both measures come from the same judge, so this is collinearity, not proof of cause. Still, little of the gain is left after the duplicate count is accounted for.

## The genuine design case: RL in Z3, driven by the ratchet

Z3 is the only cell where reviewers describe a different structure, not fewer copies: "A single link pipeline with explicit per-provider variations ... is easy to own" (RL/Z3/1, m=4). "Adding a provider becomes a few lines" (RL/Z3/5, m=5). This was forced by the harness. The ratchet tripped in 15/32 Z3 and 16/32 Z1 steps but only 2/32 in Z4 and 0/32 in Z2. In RL/Z3/0/T2 the ratchet tripped 5 times, the 10 pre-existing provider clones it listed were cleaned up, and the transcript reads "Extract the payee-insert + sync-call tail into a shared helper." In Z4 the four weekend-rule variants are reimplementations that jscpd cannot see, so RL scores **below** R there (2.00 vs 2.38): "The weekend policy now has four independent implementations" (RL/Z4/0). The lever works only where duplication is lexical.

## RC: credit inherited from T0 (scope effect)

The RC chain diff applies to the T0 tree (`pre_image_empty: false`). T0 completeness was `full` on all sites in Z1 (7/8 chains) and Z3 (8/8). RC/Z1/4's chain diff only calls and extends `shouldFillCategory`, which T0 created (diff line 278 is context, not `+`). The judge credits it anyway: "A maintainer changes the skip rules in one function". The RC gain sits in Z1 (3.50 vs 2.50), where T0 built the predicate. In Z3, even with a fully consolidated guard, the chains re-copied provider bodies (2.75; "Works within the existing per-provider pattern", RC/Z3/3). Median RC chain diffs are only slightly smaller (208 vs 233 lines). Judging the larger T0..T4 `chain_full` diff raises the score (3.25; higher in 10 runs, lower in 3), so a "small diff looks clean" bias does not explain RC.

## Diff size or tree recognition?

Overall r(maint, log lines) = 0.02. RL/Z3 has the largest diffs (median 559 lines) and the best scores. Within RC, r(maint, lines) = -0.45, but the larger RC diffs are the ones that re-copy code (RC/Z1/2: 5 duplicated blocks, m=2). I found no `why` that rewards smallness as such. The tree effect is real for RC, as shown above: the rubric asks for the design of the resulting tree, so T0's predicate is counted as reuse.

## Verdict

- (a) Agent behaviour: real but narrow. In Z1 (RG/RC) and Z3 (RL) the agents built or reused one shared definition, and reviewers name it.
- (b) Harness: RL's gain is ratchet-forced clone removal. It disappears where clones are not lexical (Z4, Z2). RC's chain score inherits T0's consolidation.
- (c) Chance: per-zone n=8, and sign tests across zones are p ≥ 0.125. RL's 3.69 picks the two zones where the ratchet fires.

Mostly the gain is fewer duplicated blocks rather than a different design. The exception is RL in Z3.
