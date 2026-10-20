# Study 3 results — the agent as abstraction designer (R, RG, RL, RC)

Agent runs 2026-10-12 15:47 → 2026-10-16 08:58 BST; evaluation finished 2026-10-17; blind
design review finished 2026-10-18. Three agents at effort medium: Claude Code
(`claude-sonnet-5-5`, "claude" below), Codex (`gpt-6-luna`), Claude Code
(`claude-haiku-5-5`). 4 arms × 4 zones × 8 chains; R, RG, RL 4 steps, RC 5 (T0 + T1–T4):
**1,632 steps, all evaluated, 0 eval errors**. Final statuses: Codex 544 ok; claude 540 ok,
4 timeout; Haiku 528 ok, 16 timeout (timeouts count as not correct).
Spec: `docs/specs/2026-10-10-agent-as-designer-design.md` (amendments up to 2026-10-17).
Registered tables: `out/study3/tables3.md` (`aa tables3`); design review:
`out/study3/design_review3.md` (`scripts/study3_design_review.py`); trace reads behind §6:
`out/study3/trace-reads/`.

Arms, all from the frozen repeated-code variant R of study 2:

| arm | lever |
|---|---|
| R | none (fresh concurrent control) |
| RG | one rule in AGENTS.md: "Do not copy logic: when new code needs behaviour that already exists, extract it into a shared function and reuse it; when a rule changes, change it in one place." |
| RL | duplication ratchet in `yarn lint`: jscpd (min-tokens 35) fails on any clone touching lines the step added |
| RC | T0: a directed refactor ("this logic should live in one place, behaviour unchanged") before the chain |
| F | study 2's human-factored runs, descriptive ceiling; its chain packets re-judged with this study's |

## 1. Execution record and deviations

All declared in the spec (amendment 2026-10-17) before any comparison was read.

1. **Host sleep → `infra`.** Two lid-closed sleeps let the container clock run while the
   host's did not; four Haiku steps recorded `timeout` inside a sleep window were
   reclassified `infra` and re-run from that step (archive in `runs3-archive/`).
2. **Haiku's last 36 chains ran at 4 workers** (Docker VM 6 → 10 GiB). Timeouts: 12 in
   steps started at 2 workers, 4 at 4 workers. Tokens, turns and outcomes are not affected
   by the worker count itself; wall time of those steps is load-affected.
3. **Evaluation parallelism 4–10 workers**, part of it under thermal throttling.
4. **T0 evaluations shared the gate** (`AA_T0_SHARED=1`); every T0 with any failing check
   was re-evaluated alone: 18 steps, 14 clean alone, 4 stay incorrect with probe changes,
   1 flip of `correct`. The probe has load-sensitive cases.
5. **Load re-check of T1–T4:** the 226 incorrect steps evaluated at ≥ 6 workers were
   re-evaluated at low load; 2 changed (both T4, now correct), tables regenerated.
6. **Ratchet threshold 35** instead of the calibration rule's 25 (disclosed before any
   run, amendment 2026-10-11): pooled T2 sensitivity 51 %, false-positive rate 32 %.
   Z2 and Z4 are lint-blind and excluded from RL's confirmatory scope (Z1 + Z3).

## 2. Reliability (before any comparison)

Second judge (Claude Opus 5.5, same rubric, blind) on 340 packets (24 T0).

| measure | n | kappa |
|---|---|---|
| reuse / duplication / placement / scope / maintainability | 316 | 0.84 / 0.89 / 0.82 / 0.70 / 0.87 (quadratic) |
| interface (T0) | 24 | 0.85 |
| completeness (T0) | 24 | 1.00 (per site: 121 sites, agreement 100 %) |
| t2_reuse / one_place / disguised_duplication | 67 / 114 / 340 | 0.71 / 0.90 / 0.71 |
| bypasses_abstraction / would_merge / abstraction_drift | 316 / 316 / 76 | 0.76 / 0.75 / 0.72 |

Completeness at 1.00 is not degenerate: the 24 double-judged T0s range from 0.4 to 1.0, and
the second judge's justifications are written independently (none repeats the first's).
Both judges are the same model, so kappa measures the rubric's consistency, not agreement
between different reviewers.

## 3. Pre-registered hypotheses

| | claude | Codex | Haiku |
|---|---|---|---|
| **H1** chain maintainability, RG vs R | 3.09 vs 2.59, p=0.005 | 2.16 vs 2.19, p=0.88 | 3.78 vs 3.56, p=0.12 |
| **H1** RL vs R (non-blind Z1+Z3) | 3.69 vs 2.56, p=0.001 | 2.56 vs 2.50, p=1.0 | 3.69 vs 3.56, p=0.44 |
| **H1** RC vs R (T1–T4 from its T0 tree) | 3.06 vs 2.59, p=0.017 | 2.59 vs 2.19, p=0.023 | 3.91 vs 3.56, p=0.025 |
| **H2** T2 reuse (judge), R → RG / RL† / RC | 44 → 62 / 100 / 88 % | 41 → 34 / 88 / 84 % | 69 → 88 / 100 / 97 % |
| **H3** T0 completeness ≥ 0.75 / probe unchanged | 78 % / 100 % | 88 % / 94 % | 94 % / 94 % |
| **H4** fired RL steps ending clean (Z1+Z3) | 64 % | 68 % | 100 % |
| **H5** chain tokens with T0, RC vs R (median) | 1.70M vs 1.39M | 3.01M vs 2.47M | 5.59M vs 4.81M |

H1: Mann-Whitney on 32 chains per arm (16 for RL non-blind); per-zone sign tests never go
below p = 0.125 with 4 zones. Nine confirmatory comparisons: Bonferroni threshold 0.0056.
† RL's R base in Z1+Z3 is 38 / 31 / 50 %.

- **H1 supported for claude under RG and RL** (both survive Bonferroni); RC is in the
  same direction (p = 0.017). **For Codex and Haiku only RC moves**, and in every agent:
  zones in favour 4/0, 4/0, 3/1, p ≈ 0.02 each, none surviving correction on its own. RC's
  T0..T4 packet (secondary) gives the same picture: claude p = 0.0006, Codex 0.059, Haiku
  0.005.
- **H2 supported for RL and RC in all three agents; RG only in direction for claude and
  Haiku** (per-agent p 0.21 / 0.13). Codex under RG reuses *less* (41 → 34 %). The R base
  is 41–69 %, not the ~0–6 % the spec expected: a label effect (§6.1). Codex RL's judge
  label overstates its reuse (§5).
- **H3 supported in all three agents.** Medians of completeness are 1.0; claude's Z2 T0 is
  the low cell (median 0.4, §6.4). Behaviour is kept: of the 4 T0s with probe changes,
  Codex's 2 are real behaviour changes and Haiku's 2 a probe artifact (§6.4).
- **H4 supported only for Haiku** (registered threshold 90 %); claude and Codex leave about
  a third of fired ratchets unfixed or unseen, and Codex suppresses it in 4 steps (§5).
- **H5: T0 does not pay for itself in tokens** over a 4-step chain: RC chains cost
  +16–23 % with T0 and about the same as R without it.

## 4. Secondary measures

| | claude R / RG / RL / RC / F | Codex R / RG / RL / RC / F | Haiku R / RG / RL / RC / F |
|---|---|---|---|
| missed copy (T1+T3) | 16 / 11 / 11 / 6 / 2 % | 33 / 31 / 31 / 12 / 22 % | 0 / 5 / 3 / 0 / 0 % |
| correct T1–T4 | 84 / 88 / 89 / 93 / 98 % | 59 / 55 / 59 / 70 / 66 % | 98 / 95 / 89 / 98 / 98 % |
| carried defects (T2–T4) | 19 / 12 / 11 / 5 / 1 % | 54 / 55 / 49 / 39 / 43 % | 0 / 4 / 4 / 0 / 0 % |
| chain tokens T1–T4 (M) | 1.39 / 1.37 / 1.56 / 1.43 / 1.39 | 2.47 / 2.86 / 3.19 / 2.35 / 2.92 | 4.81 / 4.88 / 5.38 / 4.36 / 4.70 |
| dup. lines T0→T4 (median) | 0 / 0 / −26.5 / 0 / 0 | 0 / 0 / 0 / 0 / 2 | 0 / 0 / −26.5 / 0 / 0 |

F is study 2 (other sessions and evaluator): a ceiling, not a comparison.

- **RC is the only lever that lowers missed copies and raises correctness**, most for
  Codex (missed copy 33 → 12 %, correct 59 → 70 %, both past study 2's F).
- **RL costs** 12–29 % more chain tokens (claude p = 0.003) and more turns; it is the only
  arm that removes duplication along the chain.
- **Haiku RL is the only drop in correctness** (98 → 89 %, mixed logistic −1.24, sd 0.31):
  mostly timeouts whose code passes the hidden tests, two of them mis-labelled by the
  turn-count rule (§6.5).
- **The rule is never quoted literally** by any agent (one paraphrase, §6.2); talk of reuse
  rises from 8 % (R) to 16 % (RG) for claude.

## 5. What the design review shows

Judges (`why` texts of the chain packets, `out/study3/trace-reads/G`, `B`):

- **The main complaint in R stays in every lever arm: one rule lives in several places.**
  What changes is how many: "had to be added in five or six places" (R) becomes "most
  actions share one selection function, but copyPreviousMonth keeps a parallel
  four-condition filter" (RL). Praise for "one place / single function" rises from 8 of 32
  claude R chains to 17 (RG, RL) and 12 (RC).
- **For claude most of the H1 gain is fewer duplicated blocks.** Adding the judge's own
  `duplicated_blocks` to `maintainability ~ arm + zone` shrinks the arm effects from
  +0.50 / +0.59 / +0.47 (RG / RL / RC) to +0.22 / +0.11 / +0.19 (same judge for both, so
  collinearity, not proof). The case of a different structure, not fewer copies, is RL in
  Z3: one link pipeline for every provider ("Adding a provider becomes a few lines";
  claude Z3 2.62 → 4.12, Haiku 3.25 → 4.00).
- **Each arm's gain sits in a different zone**; none improves all four. RL is *worse* than
  R in Z4 for claude (2.00 vs 2.38), where the weekend-rule variants are reimplementations
  jscpd cannot see ("The weekend policy now has four independent implementations").
- **RC's chain score inherits T0.** Its T1–T4 diff applies to the T0 tree, and the judges
  credit calls to the T0 predicate as reuse (the rubric asks for the design of the
  resulting tree). The gain sits in Z1, where T0 built the predicate; in Z3, even with a
  consolidated guard, the chains re-copied provider bodies. No justification rewards a
  small diff as such (r(maintainability, log lines) = 0.02).
- **Codex under RL satisfies the lint on the surface.** It stretches a sibling provider's
  function with flags ("a SimpleFin handler stretched with an 'orgDomain' in-check to also
  serve Fintegra"; Z3 parameters added 8 → 16, special-case branches 8 → 13), keeps
  reshaped copies (disguised duplication 13/16 chains vs 12/16 in R) and suppresses the
  check (`jscpd:ignore` in 4 steps; 10 of 38 tripped steps end with it firing). Placement
  falls 3.69 → 3.25, scope 4.19 → 3.69, maintainability stays flat. The judge's 88 % T2
  `helper` for Codex RL overstates its reuse (static label `copy` in 7/8 Z3 runs).


## 5b. Cross-family judge (exploratory, added after the registered review was read)

Two of the three agents and the judge are Claude. GPT-6.1 Sol (Codex CLI, read-only, same
blind judge rubric; `scripts/study3_cross_judge.py`) re-scored all 480 chain packets (H1's
unit, F included). 150 packets read the pre-change tree from a worktree, 330 with git read
commands on the same commit (the worktrees were CPU-bound under the host's file scanner);
the information is the same and each score records `tree_access`. Analysis:
`scripts/study3_cross_judge_analysis.py` → `out/study3/cross_judge.md`.

- **Agreement with Opus** (quadratic kappa): maintainability 0.79, duplication 0.87, reuse
  0.79, placement 0.67; scope 0.13 (Sol gives scope 5 almost always, mean 4.92).
- **Own-family gap.** d = Opus − Sol on maintainability is +0.04 on Claude-written chains
  (Sonnet and Haiku, n = 320) and −0.17 on Codex-written ones (n = 160): a relative gap of
  +0.21 (Mann-Whitney p < 0.001). Opus favours its family's code, or Sol its own; the
  design cannot tell which. The gap is larger in RG and RL (+0.31) than in R (+0.20), RC
  (+0.14) or F (+0.09).
- **H1 with Sol as the judge** (maintainability, arm vs R):

| | RG | RL (Z1+Z3) | RC | F |
|---|---|---|---|---|
| claude, Opus | 3.09 vs 2.59, p=0.005 | 3.69 vs 2.56, p=0.001 | 3.06 vs 2.59, p=0.017 | 3.41 vs 2.59, p<0.001 |
| claude, Sol | 3.06 vs 2.75, p=0.021 | 3.31 vs 2.88, p=0.041 | 3.09 vs 2.75, p=0.027 | 3.38 vs 2.75, p<0.001 |
| codex, Opus | 2.16 vs 2.19, p=0.88 | 2.56 vs 2.50, p=1.0 | 2.59 vs 2.19, p=0.023 | 2.78 vs 2.19, p=0.005 |
| codex, Sol | 2.41 vs 2.44, p=0.81 | 2.81 vs 2.75, p=0.69 | 2.69 vs 2.44, p=0.094 | 2.91 vs 2.44, p=0.012 |
| haiku, Opus | 3.78 vs 3.56, p=0.12 | 3.69 vs 3.56, p=0.44 | 3.91 vs 3.56, p=0.025 | 3.91 vs 3.56, p=0.034 |
| haiku, Sol | 3.69 vs 3.50, p=0.25 | 3.69 vs 3.31, p=0.071 | 3.78 vs 3.50, p=0.045 | 4.00 vs 3.50, p=0.005 |

**Reading.** The comparisons are within agent, so a constant family offset cancels; the
pattern holds under Sol: RC raises all three agents in the same direction, RG and RL do
nothing for Codex. What depends on the judge is the size of claude's lever gains under RG
and RL: with Sol none survives the Bonferroni threshold (0.0056), and claude's RL gain in
Z1+Z3 shrinks from +1.13 to +0.43. Cross-agent levels (e.g. "Codex's design scores lower")
carry the family gap and are not read.

## 6. What the traces show

Seven trace readers, one per anomaly (`out/study3/trace-reads/A`–`G`).

### 6.1 The R base of T2 reuse is a label effect, and corrects study 2
R reuses at T2 in 41–69 % of chains, not the ~0–6 % the spec expected. Study 2's label
could not say `helper` in R (`T2_LABELS = {"F": "helper", "R": "copy"}`, a call to a
function the agent made at T1 was never checked); re-run on the study-3 diffs it still
gives "~all copy". The behaviour is the same in both studies: the agent makes a helper at
T1 and calls it at T2 (study-2 Haiku Z1: 8/8 chains), or calls the existing exported
`getScheduledAmount` in Z2. R zone sources are identical in both studies. **Study 2's
"a copy in 32/32 Sonnet chains, 30/32 Codex, 31/32 Haiku" overstated copying** in Z1,
Z2 and Z4; the judge-based H4 of study 2 is unaffected. Study 3's R (13–22/32 helper by
the static label) is the comparator here. Z3 carries no R reuse for any agent.

### 6.2 RG: claude reuses its own T1 helpers; Codex does not act on the rule
Claude's RG T2 reuse is mostly reuse of a helper it made at T1 (15 of 20); in R it
sometimes copied even though a T1 helper existed (2), in RG never. Claude also extracted
at T2 itself 3 times in RG, never in R; Haiku 10 vs 1. AGENTS.md reaches Codex (it follows
its "run yarn from the root" instruction against the prompt in 541/544 steps) but Codex
does not change at the new consumer: with a T1 helper present it reuses it 4/10. None of
the per-agent T2 differences is significant on its own (p 0.21 / 0.80 / 0.13).
The "rule quoted 0 %" measure matches only the literal phrase; one Haiku RG transcript
paraphrases it ("a third copy would violate the \"don't copy logic\" rule") and then
extracts `linkBankSyncAccount`.

### 6.3 RC: why Codex stops missing copies
Z1 and Z2 carry the gain (missed copy 5 → 1 and 12 → 5 of 16; all 13 extra correct steps).
In R Codex consolidates at T1 only the copies it finds: in Z2 it passes exactly in the
chains where it opened `schedule-template.ts` (3/8). The T0 statement says the logic is
"repeated rather than defined once", so Codex searches for every copy, and at T1 one
helper edit reaches the template without touching its file. The two RC misses reproduce
study 2's F failure modes with Codex's own abstraction: a copy T0 never found, and a
named rounding mode treated as protected ("Schedule templates explicitly request a
separate sum-first rounding mode; I'll preserve that behavior"). Z4 adds nothing: Codex
fails every Z4 rule step in every arm (it never fixes the template's weekend loop).

### 6.4 T0 quality
All three agents build the same shapes (a selection predicate plus sign helper in Z1, one
`linkBankSyncAccount` in Z3, a weekend-rule function in Z4). Claude's low Z2 (0.4) is a
narrow extraction: it adds a range-only helper beside the existing `getScheduledAmount`,
keeps each site's missing/number dispatch on a false premise ("the callers differ on it";
the helper already returns 0 for null), and leaves the template out to preserve its
rounding (scored 0 by the rubric, full if made a parameter). It did not hurt downstream
(RC Z2 26/32 correct vs R 24/32). Flagged T0s: Codex's two are real behaviour changes (a
SQL `NULL` exclusion lost in a JS rewrite; GoCardless's mask/official name unified);
Haiku's two "probe changed" are a probe artifact (it now passes `fileId` to every
provider's sync call, which only PluggyAI uses; the probe records call arguments).

### 6.5 Haiku RL correctness: mostly timeouts, two of them mis-labelled
RL has 14 incorrect steps, R 3. 9 of RL's are timeouts whose code passes every hidden
test, as do all 3 of R's. **Two are a harness artifact**: `haiku/RL/Z3/0/T2` and
`Z3/3/T2` exited 0 with `end_turn` and a finished summary, but the parsed turn count (61,
62) reached the 60-turn limit, and `runner.classify_status` reads that as a timeout.
They are kept as registered (sensitivity below). The other 7 are wall-clock kills, 5 of
them after the ratchet had tripped and been cleared: refactor loops plus a slow
`yarn lint` ("Lint now passes, but the refactor broke the 3-month average tests"). The 5
wrong `ok` steps are 2 missed copies (+3 carried) in the lint-blind zones, where the
ratchet never fired. Scoring timeouts by their hidden tests: R 128/128, RL 123/128.
**The ratchet costs Haiku time, not correctness of the code it leaves.**


## 7. Reading

1. **The agent can design the abstraction when asked (H3), and that is the lever that
   reaches every agent.** RC is the only arm that moves maintainability in all three
   (p ≈ 0.02 each, same direction in 11 of 12 zones; same direction with the Sol judge,
   §5b) and the only one that lowers missed
   copies and raises correctness (Codex past study 2's human F). Its mechanism is search:
   the refactor request makes the agent find every copy, which a rule-change task does
   not. Two costs: T0 does not pay for itself in tokens within four steps, and the agent's
   abstraction brings back F's failure mode (a named exception read as protected).
2. **Passive levers depend on the agent.** The written rule and the ratchet improve
   claude's judged design (surviving correction with Opus; smaller and not surviving it
   with Sol, §5b) and do nothing measurable for Codex's.
   Haiku starts near the ceiling. The rule is followed without being quoted; it acts
   mostly through reuse of helpers the agent made itself.
3. **The rival hypothesis holds for Codex under the lint**: the ratchet changes the
   surface (clones jscpd stops matching, `jscpd:ignore`, sibling functions stretched with
   flags) but not the judged design. It also only sees lexical copies: where duplication
   is a reimplementation (Z4) the lint is blind and claude's design is worse than in R.
4. **Most of the judged gain is fewer copies of the same rule, not a different design.**
   The exception is the one-pipeline Z3 under RL. In every arm the judges' main complaint
   (one rule in several places) is reduced, not removed.
5. **Study 2's claim that agents copy at T2 in almost every R chain was a label artifact**
   (§6.1); its judged design gap (R vs F) stands.


## 8. Limits

- The registered judge and its second pass are the same model (Claude Opus 5.5); a
  cross-family judge (GPT-6.1 Sol) re-scored the chain packets only (§5b) and shows a
  0.21-point own-family gap. Blindness is partial (a consolidated tree is recognisable).
- 4 zones: the per-zone sign test cannot reach significance; no ordinal mixed model was
  added before reading (registered as optional, so none is added after).
- RC is a directed refactor: the experimenter chose what and when. It says the agent can
  design the abstraction when asked, not that it decides to.
- The ratchet threshold deviates from its own calibration rule and is blind in Z2/Z4.
- Timeouts count as not correct, and the turn-count rule labels a finished step whose
  parsed turns reach 60 as a timeout (2 Haiku RL steps, §6.5).
- One codebase (Actual's loot-core), one effort level, three agents.
