# C: why RG helps claude and not codex

Read-only trace read, 2026-10-18. Sources: `out/study3/design-labels.json` (unblinded judge labels), `runs3/*/{R,RG}/*/*/T*/{result.json,diff.patch,transcript.jsonl}`, `work/variants/RG/AGENTS.md`, `src/aa/prompt.md`, `src/aa/chain_eval3.py`.

## Counts (32 chains per cell)

| agent | judge T2 helper R → RG | static `t2_reuses_logic` helper R → RG | judge one_place T1+T3 R → RG | chain maint R → RG (MWU p) | T2 diffs that remove ≥3 non-test lines (extraction at T2) R → RG |
|---|---|---|---|---|---|
| claude | 14 → 20 (Fisher p 0.21) | 13 → 20 | 41/64 → 48/64 | 2.59 → 3.09 (0.005) | 0 → 3 |
| codex | 13 → 11 (p 0.80) | 10 → 6 | 21/64 → 22/64 | 2.19 → 2.16 (0.88) | 2 → 1 |
| haiku | 22 → 28 (p 0.13) | 20 → 25 | 58/64 → 61/64 | 3.56 → 3.78 (0.12) | 1 → 10 |

## (a) Agent behaviour

- **Claude's T2 reuse is mostly reuse of a helper it made itself at T1.** Of claude's judge-`helper` T2s, the static `shared_functions` were defined in that chain's T1 diff in 11/14 (R) and 15/20 (RG). In R, 2 T2s copied even though a T1 helper existed; in RG, 0. Where T1 was *not* judged one-place, claude still reused at T2 in 6/10 RG chains vs 3/15 R. The gain sits in Z1 (4 → 7) and Z4 (1 → 4). Example: `runs3/claude/RG/Z1/2/T2/diff.patch` calls `getFillableCategories()` (added at T1), while `runs3/claude/R/Z1/0/T2/diff.patch` pastes the `SELECT c.* FROM categories c ...` query and the `hasSavedTemplates` skip inline. Judge on the R chain: "has to be made in six places by hand". On the RG chain: "must be added in two places". Claude also extracted at T2 itself 3 times in RG and never in R (`runs3/claude/RG/Z1/3/T2`: a new `getMonthWideCategories()` replaces 36 lines at existing sites).
- **Codex does not change at the moment of the new consumer.** Its one-place rate (≈33%) and T2 reuse are flat. When a T1 helper exists, it reuses it only 4/10 in RG. Its T2 messages describe copying the pattern, not reusing it: "applies the same visible, non-template category rules as the existing bulk actions" (`runs3/codex/RG/Z1/2/T2`). Its chain maintainability is low whatever the T2 label (helper 2.36, copy 2.07), so even extra T2 reuse would hardly move H1 for codex.
- **Haiku does respond at T2**: 10 vs 1 T2 extractions, mostly in Z3/Z4. Its maintainability ceiling is already high (one-place 58/64 in R), which leaves little room.

## (b) Measurement and harness

- **AGENTS.md reaches codex.** Codex's JSONL has no instruction items, so this cannot be seen directly. Indirect evidence: the prompt says to run lint "in packages/loot-core", but AGENTS.md says "ALWAYS run yarn commands from the root directory". Codex ran without `cd` in 541/544 steps and says so in 159 of them ("I'll run ... lint from the repository root as requested", `runs3/codex/RG/Z1/0/T2`). The file is 20,019 B, under Codex's 32 KiB limit. Codex follows AGENTS.md selectively: 0/544 diffs add `upcoming-release-notes/`, against 318/544 for claude.
- **The finding that the rule is "never quoted" is partly an artifact.** `_RULE_PHRASES` matches only "do not copy logic". Haiku wrote: "Pluggy and Akahu's link handlers are near-identical, so a third copy would violate the \"don't copy logic\" rule" (`runs3/haiku/RG/Z3/6/T2`), and then extracted `linkBankSyncAccount` (91 removed lines). This is the only paraphrase in the R/RG transcripts. Claude cites AGENTS.md only for build steps (2 transcripts).
- The static and judge labels disagree on codex's RG drop (static 10 → 6, judge 13 → 11). The judge also has 6 `reimplements` in codex RG vs 3 in R.

## (c) Chance

None of the per-agent T2 reuse differences is significant: claude p 0.21, codex 0.80, haiku 0.13. The claude/codex contrast is driven by zones: codex's drop is all in Z2 (6 → 3), and claude's gain is in Z1 and Z4. Only claude's maintainability gain is significant (p 0.005). It comes mainly through T1 one-place helpers and their reuse, not through a T2 change alone.

**Verdict:** the effect is mixed. It is real agent behaviour for claude: more T1 helpers, which it then reliably reuses, plus occasional T2 extraction. Codex has the rule in context but does not act on it. The rule-quote measure misses paraphrases. The per-agent T2 differences are within chance.
