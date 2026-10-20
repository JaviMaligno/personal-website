# D-r-base-reuse: why R's T2 reuse is 41-69 % in study 3, not ~0-6 %

**Short answer: it is the label (measurement), not new behaviour.** Study 2's "copy in 32/32 / 30/32 / 31/32" was not a measured behaviour rate. The study-2 static label had no `helper` outcome for R, so ~0 % was built in. The R base, the models and the T1 outcomes are close to study 2's. The agents did the same thing in both studies: they made a helper at T1 and called it at T2.

## 1. The study-2 label could not say "helper" in R (b: measurement)

`src/aa/chain_eval.py:127,734-737`: `T2_LABELS = {"F": "helper", "R": "copy"}`. In R, a call to the R helper list returns `copy`, and so does a marker hit. A call to a function the agent made at T1 is never checked (`helpers_checked` holds only pre-existing names such as `setNMonthAvg` or `getScheduledAmount`).

- runs2 R T2 `t2_reuses_logic`: claude 32 copy; codex 30 copy and 2 None; haiku 31 copy and 1 None. These are the cited figures.
- The study-2 label re-run on the **study-3** diffs (`t2_reuse_detail.study2_label`) gives claude 31 copy and 1 None, codex 29 copy and 3 None, haiku 32 copy. The old rule reproduces "~all copy" on the new runs, so the new runs did not change the number. The new label did.
- The study-3 static label (`t2_static3`, amendment 2026-10-11b) counts a zone function that both the new consumer and a pre-existing site reach. Agent-made helpers count. Results: R helper claude 13/32, codex 10/32, haiku 20/32. The judge gives claude 14/32 (44 %), codex 13/32 (41 %), haiku 22/32 (69 %).

## 2. Same behaviour in study 2, labelled copy (a: agent behaviour, constant across studies)

- **runs2/haiku/R/Z1/\*/T2**: all 8 chains call the helper that haiku created at T1 (`getMonthWideCategories` and similar names). All 8 were labelled `copy` because the income guard matched a marker. From runs2/haiku/R/Z1/1/T2/diff.patch: `+  const categories = await getMonthWideCategories();`. In study 3 the same pattern is judged `helper`. Judge on runs3/haiku/R/Z1/0/T2: "Uses the shared getMonthWideCategories selection … no helper existed for the income guard or sign flip."
- **Z2**: in both studies the T1 change goes through a new `getRangedAmount`, and T2 calls `getScheduledAmount`, an exported function that already exists in the R tree (`shared/schedules.ts:356`). Compare runs2/claude/R/Z2/0 with runs3/claude/R/Z2/0: the T1 diffs are near-identical, and both T2 diffs add `expectedAmount: getScheduledAmount(schedule._amount)`. Study 2 labelled it `copy` (`calls: ["getScheduledAmount"]`). Study 3 labels it `helper`. The judge wrote: "Computes the field with the existing exported getScheduledAmount". T2 calls `getScheduledAmount` in claude 7/8, codex 3/8 and haiku 8/8 chains in study 2, against 7/8, 4/8 and 8/8 in study 3.
- T1 helper creation (new non-test functions in the T1 diff) is similar in both studies. Z1: claude 8 vs 6, codex 3 vs 4, haiku 8 vs 7. Z4: claude 7 vs 6, codex 1 vs 0, haiku 8 vs 7. One difference: study-2 claude Z1 T1 often extracted only `hasSavedTemplates`. The T2 that followed called it but still pasted the query and income check (runs2/claude/R/Z1/0/T2), which is a real copy.

## 3. Which zones carry R reuse

Judge counts of `helper`, out of 8 per cell:

| agent | Z1 | Z2 | Z3 | Z4 |
|---|---|---|---|---|
| claude | 4 | 7 | 2 | 1 |
| codex | 4 | 6 | 1 | 2 |
| haiku | 8 | 8 | 0 | 6 |

The static3 label gives the same picture: Z3 is 0 for every agent. Z1 and Z2 carry the reuse for all three agents, and Z4 adds it for haiku. Z2's R base already contains a callable `getScheduledAmount`, so a high R base there is structural.

## 4. Is the R base comparable? Yes, at the code level

- R zone sources are identical. Across all R T1 diffs, I compared the pre-image lines at matching file:line positions in runs2 and runs3: 100,194 agree and 0 differ. The task statements are shared (`tasks2/`), and the spec (§2) says the chains, hidden tests and evaluator are unchanged.
- The tree ids differ: start_tree is `1bc8223…` in runs2 and `0cc93d2…` in runs3, from a rebuilt image (`a2f09e9` vs `f9bfc01`, variants rebuilt 2026-10-11). The difference lies outside the zone sources and was not located. Claude's model id (`claude-sonnet-5-5`) and CLI (2.1.289) are the same.

## 5. Chance

Small n (8 per cell) explains cell-to-cell noise, not the jump from ~0 % to 41-69 %. Re-labelling the same kind of behaviour accounts for that jump.

**Implication:** the spec's "R base ~0-6 %" (H2) was an artifact of the study-2 label and should not be cited as a behavioural baseline. Study 3's R (13-22/32 helper) is the right comparator. It also implies that study 2's "agents extend the repeated pattern" claim overstated copying in Z1, Z2 and Z4, where T1-made or pre-existing helpers were often reused.
