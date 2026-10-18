# Study 3 pilot report

Date: 2026-10-12. Spec: `docs/specs/2026-10-10-agent-as-designer-design.md` (§9 and
amendments 2026-10-10 to 2026-10-11f). Plan: `docs/plans/2026-10-10-agent-as-designer-plan.md`,
Task 8. Data: `runs3-pilot/<agent>/<arm>/<zone>/0/T<k>/`, tables `out/study3/pilot/tables3.md`
and `summary3.json`, run log `out/study3/pilot-run.log`.

This is a pilot with **one chain per cell** (n = 1 per agent × arm × zone). Its questions are
whether the design runs and whether it measures what it is meant to. Nothing in this report
is an effect estimate. Where a number is given per arm, it is a count over 4 chains (16
steps), and differences between arms at that size are not evidence of anything.

Agents: `codex` (gpt-6-luna), `claude` (Sonnet 5.5), `haiku` (Haiku 5.5). Arms: R, RG
(written rule), RL (duplication ratchet), RC (T0 refactor step, then T1–T4).

> **Re-derivation note (2026-10-12, after this report).** The blocking fixes of §6
> (spec amendments 2026-10-12, 2026-10-12b and 2026-10-12c) were applied to `runs3-pilot/`
> through harness commands, each with a record in `runs3-pilot/rederive-log.jsonl`; no
> agent was re-run and no transcript or diff was edited. Statements below that they
> supersede are marked **[superseded, see note]**; the current values are:
>
> 1. **Status (§1, §4.1).** `codex/R/Z3/0/T1` and `codex/RC/Z3/0/T2` are now `infra`
>    (`aa chain reclassify`, transport stall; agent.json keeps the old value in
>    `status_reclassified.from`), their usage is missing (None), not 0, and `aa tables3`
>    excludes them and the steps built on their trees (`after_infra`: R/Z3 T2–T4, RC/Z3
>    T3–T4) until the two chains are re-run. Final status 202 `ok`, 2 `infra`. Codex
>    correct T1–T4 is therefore R 4/12 and RC 7/13 (RG 10/16, RL 11/16 unchanged); the
>    report's 7/16 and 9/16 counted the two killed steps as incorrect and kept their
>    chains.
> 2. **Usage (§6 item 2).** `aa chain reparse` re-derived the 5 multi-result
>    Claude-engine steps and the 2 Codex steps (missing). Checked against the report: §5's
>    chain-token medians (claude RC 1,763,936 vs R 1,315,089) involve none of the re-parsed
>    steps and are unchanged; §7's projected quota already uses the re-parsed values
>    (claude 197M input, 178M before the re-parse; haiku 638M, 628M before).
> 3. **Trip kinds (§3.2, measurement defect).** Fixed (`aa chain rederive-trips`, trips
>    matched against the start tree as at the trip, `ratchet_trip_basis` per trip;
>    approximate where the clone is gone from the post tree, amendment 2026-10-12).
>    `ratchet_split` at T1 is now Z1: R `PPP`, RG `PPP`, RL `NPP` (claude RL Z1 T1 never
>    saw a trip, so its split is its final tree's kind); Z3: R `PPP`, RG `PPP`, RL `PPP`
>    (claude, codex, haiku; P = `touches_preexisting_only`, N = `adds_new_clone_side`).
> 4. **H4 decomposition (§3.2, "what agents did after a trip").** Now derived
>    (`ratchet_trip_clones`, amendment 2026-10-12c) and reported by `aa tables3`; it
>    reproduces the trace reading of the 12 fired non-blind steps: (a) consolidation 6,
>    (b) edit moved outside the clone 2 (codex Z3 T1: 7 of 7 listed clones remain; haiku
>    Z3 T1: 1 of 1), (c) seen, not fixed 2, (d) never seen 2 (claude Z1 T1 d0, codex Z1
>    T4 d1), (g) 0, (u) 0.
> 5. **Behaviour outside T0 (§3.2, §6 item 9).** The behaviour check (`aa chain
>    behaviour-check`, Z3's three T0 inconsistency tests on every T1–T4 post tree) finds
>    more than the trace reading: **haiku RL Z3 T2–T4** unify `akahu-changed-tables` *and*
>    `gocardless-mask-official-name` (the report noted only the Akahu change, from the
>    agent's own message), and **haiku RG Z3 T2–T4** unify `akahu-changed-tables`
>    (an RG consolidation, not ratchet-driven). Claude and Codex unify none in any arm (the
>    Codex chains R/Z3 and RC/Z3 only up to their infra step). The statement that only
>    haiku RL Z3 T2 unified an inconsistency is superseded. Of the RL H4 successes, 1
>    (haiku Z3 T2) unified inconsistencies.

## 1. What ran

- **48 chains, 204 steps**: 3 agents × 4 arms × 4 zones × 4 steps (T1–T4) = 192, plus 12
  RC T0 steps. Every step has `agent.json` and `result.json`; every chain has
  `chain_result.json`.
- Final agent status: 202 `ok`, 2 `timeout` (both are really infrastructure, see below).
  **[superseded, see note: now 202 `ok`, 2 `infra`]**
  No `harness_error`, `setup_error`, `eval_error` (0/204) or ratchet error. `docker_rc` = 0
  in 204/204 steps; no OOM, `Killed`, exit 137, ENOMEM or disk messages anywhere under
  `runs3-pilot/`.
- Order: codex, then claude (04:03:48 → 06:42:49 BST, 2 h 39 m), then haiku (06:42:49 →
  10:02:23 BST, 3 h 20 m), `--workers 2`. Evaluation 10:02:23 → 11:33:58 BST (178 steps),
  then a second pass 12:02:41 → 12:13:44 BST for the 26 rerun steps.

### Incidents

1. **Power loss** (log line 2: `RESUME after power loss … 21:36:40 BST`). Two Codex steps
   in flight were rerun as infra and left no record; steps finished before the loss were
   kept.
2. **Network/DNS outage, about 21:00–21:22 UTC (22:00–22:22 BST) on 2026-10-11.** Not in
   the known history. Two Codex steps that started after the power-loss resume,
   `codex/R/Z3/0/T1` (20:59:04 UTC) and `codex/RC/Z3/0/T2` (20:58:54 UTC), lost the network:
   `stderr.log` shows `failed to lookup address information: Name does not resolve`, and the
   transcripts end in 25 and 23 `Reconnecting... waiting for network` events. Both were
   killed at the 1,500 s wall limit (1,513.4 s and 1,511.6 s, exit 124) with 0 tokens
   recorded **[superseded, see note: reclassified `infra`, usage missing]**. Their parsed outcome was `infra`, but `runner.classify_status`
   (`src/aa/runner.py:276`) gives exit 124 priority, so they were stored as `timeout`. The
   chain runner carries `timeout` forward (`CARRIED = ("ok", "timeout")`,
   `src/aa/chain_runner.py:95`), so both chains continued from those trees. Both agents had
   essentially finished (R/Z3/T1 had passed lint and typecheck about 96 s in), and the
   evaluator scored both `correct = True`; `aa tables3` counts `timeout` as not correct.
3. **Codex login expiry (evening of 2026-10-11).** 7 Codex chains (R/Z3@T2, R/Z4@T1, RG/Z3@T1, RG/Z4@T1,
   RL/Z4@T1, RC/Z3@T3, RC/Z4@T0) failed 8 attempts each with 401s (49 re-queues + 7
   `infra_exhausted`). Cause (plan note 2026-10-12): the host `~/.codex/auth.json` is copied
   into each container, refreshes are not written back, and when the 10-day token expired
   the parallel containers raced on the single-use refresh token. The backoff
   (60 + 120 + 240 + 480 + 960 + 1,800 + 1,800 s = 91 min per chain) idled the Codex block
   until 04:03:48 BST. After a re-login the 7 chains were resumed from the failed step
   (11:34:53 → 12:02:41 BST, 28 min) and all ended `ok`. **Guard** (commit `01189b3`):
   `aa chain run --agent codex` refuses to start with < 24 h of login left
   (`--min-codex-auth-hours`), and the scheduler stops dispatching (status `auth_expired`,
   no infra attempts spent) when < 2 h remain. The 401s themselves can no longer be
   inspected: rerunning deleted the failed attempts' directories and the log has no
   per-event timestamps. Timing (verifier): no Codex step started between the two
   network-killed steps' kill (~21:24 UTC) and the 10-12 rerun, so the first 401 came right
   after the network outage ended (last DNS error 21:22:05 UTC). The expiry/refresh-race
   cause comes from the plan note and cannot be checked against the deleted attempts; a
   refresh lost during the outage is an alternative that the same guard would not cover.

## 2. Spec §9 checks

| §9 check | Result | Evidence |
|---|---|---|
| T0 sanity: probe and inconsistency tests pass on R and F, fail on seeded breakages | **Pass** (pre-pilot) | `tasks3/Z{1..4}/T0/sanity.json`: `untouched` R and F `all_pass = true`, every seed `ok`, `all_ok = true` in 4/4 zones (Z4 has a behaviour seed only: 46 template cases flagged). `reference_check.json` `ok = true` in 4/4 on image `f9bfc01`. In the pilot itself the probe flagged the one real behaviour change (Codex Z4, §3.1). |
| Ratchet fires where calibration says it should | **Pass at T1 and in the counterfactual arms; not testable for RL T2–T4** | See §3.2. Z1 T1 fired 3/3 in RL, R and RG (calibration 100 %); Z3 T1 3/3 (100 %); Z2 T1 0/3 (8 %); Z4 T1 RL 0/3, R 1/3, RG 2/3 (29 %). R/RG counterfactuals match calibration at T2–T4 too, except R Z4 T2 (2/3 vs 12 %). RL T2–T4 firing depends on what the agent did at T1, so calibration (on R trees) is not its benchmark. |
| T0 fits its limits (Z3 especially) | **Pass** | Max 519 s of 2,400 s (22 %, haiku Z4) and 25 of 90 turns (28 %, haiku Z2). Z3: claude 209 s / 9 turns, codex 104 s / 20 turns, haiku 372 s / 24 turns. No T0 timed out. T1–T4 (not a §9 check, 25 min / 60 turns): two RL steps came close, haiku RL Z3 T2 at 59/60 turns (`classify_status` would have made 60 a `timeout`) and claude RL Z4 T1 at 1,365/1,500 s. |
| Chains run end to end | **Pass, with two defects** (both fixed since, see note) | 48/48 chains complete, every T1 starts from the expected tree (RC: T1 `start_tree` = T0 `post_tree`, `carry.exact = true`, `tree_fallback = false` in 12/12). Defects: network stalls recorded as agent timeouts (§1, item 2) and Claude multi-result token under-count (§6). |
| Traces of every 0 % / 100 % cell read | **Done** | §4.3. All extreme cells are real except: the registered missed copy is 0 % partly by definition, and `rule_quoted` is 0 % because the measure cannot see the rule (§3.3). |
| Estimate repeated | **Done** | §7. |

## 3. Does the lever reach the agents?

### 3.1 RC: the T0 step

All 12 T0 steps ended `ok` with related tests passing, typecheck passing (`tsgo -b` and
full), and no gaming flags or test-infrastructure edits. All 12 transcripts frame the step
as a behaviour-preserving refactor; none adds features or changes semantics on purpose.

| agent | zone | turns | wall s | diff (files, +/−) | probe changed (minus excl.) | root lint | `correct` | sites through one definition (my reading) |
|---|---|---|---|---|---|---|---|---|
| claude | Z1 | 12 | 264 | 4, +105/−56 | 0 | ok | T | ~6/6 |
| claude | Z2 | 7 | 264 | 3, +13/−6 | 0 | ok | T | 4/5 (template left out on purpose) |
| claude | Z3 | 9 | 209 | 2, +95/−216 | 0 | ok | T | 5/5 |
| claude | Z4 | 8 | 158 | 4, +35/−11 | 0 | ok | T | partial (template keeps its outer `skipWeekend ?`) |
| codex | Z1 | 14 | 64 | 1, +42/−30 | 0 | ok | T | partial (SQL hidden filter kept in the averages) |
| codex | Z2 | 21 | 123 | 4, +15/−28 | 0 | ok | T | 5/5 (F's design, `roundRange: 'sum-first'`) |
| codex | Z3 | 20 | 104 | 2, +103/−93 | 0 | **fail** (format check; later stages not run) | T | **2/5** (stopped and said so) |
| codex | Z4 | 18 | 85 | 3, +26/−26 | **26** | ok | **F** | partial, plus a behaviour change |
| haiku | Z1 | 15 | 356 | 1, +62/−56 | 0 | ok | T | 6/6 |
| haiku | Z2 | 25 | 340 | 3, +19/−13 | 0 | ok | T | 4/5 (template left out on purpose) |
| haiku | Z3 | 24 | 372 | 1, +103/−297 | 0 | ok | T | 5/5 |
| haiku | Z4 | 21 | 519 | 3, +36/−43 | 0 | ok | T | 4/4 (F's shape) |

The site counts are an analyst reading of diff + transcript against `tasks3/Z<k>/T0/sites.json`,
not the registered blind completeness judgement.

- **The probe works.** Codex Z4 added `skipWeekend = true` as a default parameter, so a
  schedule without `skipWeekend` now skips weekends. All 26 changed cases (21 `db:Z4/upcoming`
  configs without the key, 5 `template:…/undefined/…`) are real. Codex hit this in
  `getNextDate`, fixed only that site, and then wrote "The `skipWeekend`-absent case remains
  disabled, preserving existing behavior", which is false for `getUpcomingDates` and the
  template. Related tests did not catch it.
- **The inconsistency tests work.** 0 unified in 9/9 Z1–Z3 steps; the agents that touched an
  inconsistent site kept it deliberately.
- **`correct` does not mean complete.** Codex Z3 converted 2 of 5 providers, stopped at
  104 s ("the refactor is incomplete … I can't claim the requested task is complete") and
  is `correct = true`. The probe criterion of H3 can be met by doing less; only the
  completeness judge separates these cases.
- **Z2's statement invites leaving the hard site out.** Claude and Haiku both excluded
  `schedule-template.ts` because unifying it "would change results", citing the statement's
  edge-case clause. That caps Z2 completeness at 0.8, which still clears H3's 0.75 bar.
- **Partial consolidations are common** (Codex Z1, Z3, Z4; Claude Z4; the Z2 exclusions), and
  the rubric does not say how to score a site whose decision goes through the shared
  definition but is still partly re-decided locally (§6, blocking).
- **T1 carry is exact** in 12/12 RC chains, and T2–T4 chain the same way.
- Minor: `probe_passed = 43` in every T0 `result.json` is the probe's vitest test count, not
  the 553 cases.

### 3.2 RL: the ratchet

**Firing at T1** (the only RL step that shares R's start tree):

| zone | calibration (R, n = 24) | pilot R | pilot RG | pilot RL |
|---|---|---|---|---|
| Z1 | 100 % | 3/3 | 3/3 | 3/3 (codex and haiku saw it; claude never ran lint, final tree fires) |
| Z2 | 8 % | 0/3 | 0/3 | 0/3 |
| Z3 | 100 % | 3/3 | 3/3 | 3/3 (all three saw it) |
| Z4 | 29 % | 1/3 | 2/3 | 0/3 |

The R and RG counterfactual fields match calibration at later steps too (Z1 T2 3/3 vs 79 %,
T3 1/3 vs 42 %, T4 3/3 vs 100 %; Z4 T3 3/3 vs 92 %), with one exception: R Z4 T2 fires 2/3
(codex, haiku; both `adds_new_clone_side`) against a calibration of 12 % (3/24). The in-container dup-check
(`eval/lint.log`) and the harness `ratchet_final` agree on firing and clone count in 48/48 RL
steps. After T1, RL trees no longer match R's (e.g. Z3 T4: RL 0/3 fire, R 3/3); in the traces
RL agents had consolidated at T1 (claude merged the five link functions into
`linkBankAccount`; haiku and codex added wrappers), so later steps edit shared code. At
n = 1 per cell this is a description of these chains, not an RL vs R difference.

**What agents did after a trip** (12 fired steps in non-blind Z1+Z3; trips = dup-check
failures the agent saw):

- **Seen, ended passing, by consolidation (6):** claude Z1 T4, claude Z3 T1 ("because the
  lint duplicate-code check failed"), codex Z1 T1, haiku Z1 T1, haiku Z1 T2, haiku Z3 T2.
- **Seen, ended passing, by moving the edit out of the clone (2):** codex Z3 T1 and haiku Z3
  T1 ("Rather than edit inside those duplicated bodies, I'll move the check into one
  wrapper"). The rule allows this; H4 counts it as success.
- **Seen, not fixed (2):** claude Z1 T2 extracted a helper (`getFillableCategories`), after which
  dup-check still listed 4 clones; it told the user "`yarn lint` passes" and that the check
  "still lists some other duplicated lines … but reports a pass", which its own tool output
  contradicts; codex Z3 T2 tried to
  consolidate Akahu and Fintegra, gave up and reported honestly that lint fails (and is
  `correct = false`, where codex R and RG Z3 T2 pass).
- **Fired on the final tree, never seen (2):** claude Z1 T1 ran `npx oxlint` and `npx tsgo`
  instead of `yarn lint`; codex Z1 T4 created a 35-token clone after its last lint run.

Registered H4 per agent (non-blind Z1+Z3): claude 2/4, codex 2/4, haiku 4/4 (8/12 overall).
Half of the failures (2/4) are "lever never reached the agent", not "lever ignored".

**Gaming:** none. No RL diff touches dup-check, jscpd, package.json scripts or
`jscpd:ignore`; `start_commit_rewritten` is false throughout. Codex read `bin/dup-check.mjs`
(Z3 T1, T2) and haiku read it too (Z3 T2, `sed -n 1,80p bin/dup-check.mjs`; it did not open
`dup-check.config.json`), but none modified them. The script's header states the rule (a
clone side on a changed line), which is what the two relocations exploit.

**A ratchet-driven consolidation changed behaviour, unmeasured [superseded, see note item 5: the behaviour check now measures it and finds more].** haiku RL Z3 T2, after its
dup-check trip, merged the link functions of all bank-sync providers into one helper and
wrote in its final message: "Akahu's sync event now also reports `accounts`, which is a small
behaviour change" (the diff drops Akahu's `tables: ['transactions']`). That is one of Z3's
registered T0 inconsistencies (§3), unified; the step is `correct = True` and counts as an H4
success. The probe and inconsistency tests run only on RC's T0, so a behaviour change made by
a lever-driven consolidation at T1–T4 (RL, and RG if it works) is invisible to every measure,
while RC's T0 is checked for it (§6, blocking).

**Lint not run at all** (`lint_runs` = 0): Claude in 3/16 steps in R, RL and RC and 4/16 in RG
(RL: Z1 T1, Z2 T2, Z2 T4); Codex in 1/16 in R and RC (RC's is the network-killed Z3 T2), 0 in
RG and RL; Haiku never. Root `yarn lint` takes about 1 m 50 s, close to Claude Code's 120 s
Bash limit; chained with tests and typecheck it exceeds it (claude RL Z1 T2's
`vitest …; yarn lint; yarn typecheck` command was moved to the background at 120 s).

**At min-tokens 35 the ratchet catches parameter boilerplate**: codex RL Z1 T4's final clone
is the `setZero` / `setLastMonthSpending` destructured signature, 8 lines, exactly 35 tokens;
claude RL Z1 T4 created a `MonthWideArgs` type to satisfy it. Relevant to the rival
hypothesis (surface changes).

**Measurement defect [superseded, see note item 3: fixed and re-derived]:** `trip_kind` (`src/aa/chain_eval3.py:324`, used at line 677) maps a
trip's line numbers with the step's **final** diff. When the agent consolidates after a
trip, a pre-existing clone reads as `adds_new_clone_side`. In the pilot `ratchet_split` at
Z1 T1 is R `PPP`, RG `PPP`, RL `NNN`; at Z3 T1 RL is `N P P` with claude (the one that
consolidated) as N. Rebuilding the tree at the trip flips claude RL Z3 T1 (trips 0–1) and
haiku RL Z1 T1 (trip 0) to `touches_preexisting_only`. This biases the registered split
exactly in the steps where the lever worked (§6, blocking).

### 3.3 RG: the written rule

- **Delivered:** the rule is at `work/variants/RG/AGENTS.md:294`. Claude Code loads it
  through the variant's `CLAUDE.md` (`@AGENTS.md`), Codex loads AGENTS.md itself (19.9 KB,
  under its 32 KiB limit). Agents quote other AGENTS.md rules without opening the file (e.g.
  haiku RG Z1 T3: "AGENTS.md says yarn commands run from the root").
- **Never cited:** "Do not copy logic" appears in 0/204 transcripts; `rule_quoted` /
  `rule_cited` = 0/48 RG T1–T4 steps (0/204 in all arms). No RG agent attributes a decision to the rule. Claude RG Z3
  T2 copied knowingly: "the new download function is largely a copy of the Akahu one … I
  didn't extract a shared helper".
- **The manipulation check cannot see the rule.** `agents_md_read` is false in 204/204 by
  construction (the file is already in context, so nobody opens it). Claude/Haiku thinking
  blocks are empty (1 of 249 non-empty for Sonnet, 0 of 946 for Haiku) and Codex emits no
  reasoning items, so a citation can only appear in visible messages, which Codex keeps to
  2–5 short lines per step. Spec §6 promises "whether the agent quotes or follows the rule";
  as built, only "follows" (behaviour: T2 label, judge) is measurable (§6, blocking).

## 4. Correctness and extreme cells

### 4.1 Correct, T1–T4, per agent × arm (status `ok` and `correct`)

| agent | R | RG | RL | RC |
|---|---|---|---|---|
| claude | 16/16 | 14/16 | 16/16 | 14/16 |
| codex | 7/16 ‡ | 10/16 | 11/16 | 9/16 ‡ |
| haiku | 16/16 | 16/16 | 16/16 | 16/16 |

Codex R and RC each include one network-killed step that `result.json` scores correct; with
those counted they would be 8/16 and 10/16. ‡ **[superseded, see note item 1]:** with the
killed steps `infra` and their later steps excluded, R 4/12 and RC 7/13. Haiku is also 4/4 at T0; Codex is 3/4 at T0.

Per zone × step over the 12 runs (all agents and arms, status `ok` and `correct`): Z1
12/12/11/10, Z2 9/11/8/8, Z3 10/10/12/11 (11/11/12/11 counting the two network-killed
steps), Z4 8/12/8/9 (T1/T2/T3/T4). Every zone × step was solved at least 8 times
out of 12. For Codex, Z4 T1 and Z4 T3 fail in every arm here (0/1 per arm, 0/4 in all) and were 0/8
in both study-2 arms (R and F): a
floor for that agent, with no arm information.

### 4.2 Every incorrect step, with the trace explanation

**Claude**
- RG Z3 T1 (3/5 consumers): its grep (`linkAccount\|link-account\|linkGoCardless\|linkSimpleFin\|linkPluggyAi`)
  never matched Akahu or Enable Banking; it reported success.
- RG Z3 T4 (4/6): the T4 hidden test re-asserts T1's refusal for those two providers; the
  agent wrote that they "never had that check … I left them alone". T1's defect re-tested,
  not a new error.
- RC Z2 T3 (5/6) and T4 (5/6 + 2 carried): T2 had wired the new API consumer through
  `getScheduledAmount`; T3 added `getExpectedAmount(amount, op)` and moved the five original
  sites to it but not `getScheduledAmount`, although `api-models.ts:256` was in its grep
  output. Same failure as study-2 Claude R (`api-schedule-list` missed at T3 in 4/8 R chains).
  Not attributable to T0 at n = 1.

**Codex**
- R Z1 T3 (0/6, empty diff, 36.8 s): quit with "category_groups has no notes column … I
  haven't changed any files", though its own `rg` output showed `INSERT INTO notes (id, note)`.
- R Z1 T4 (0/6): missed `copyPreviousMonth`, and the T4 tests also assert T3's `#fixed`
  exclusion (coupling).
- R Z2 T1 (1/5), T3 (2/6), T4 (2/6): only `shared/schedules.ts` changed at T1 (study 2:
  Codex R Z2 T1 2/8); later steps inherit.
- RG Z2 T1 (4/5), T3, T4 (5/6): template missed; its greps (`rounded midpoint|midpoint|is between`)
  cannot match the template's form.
- RG Z2 T2 (0/1): inlined a copy of the range rule without the null branch (`TypeError:
  Cannot read properties of null (reading 'num1')`), while `getScheduledAmount` already
  handled null.
- RL Z1 T4 (5/6): threaded the flag through `getBulkActionCategories` but missed
  `copyPreviousMonth`, which does not use it.
- RL Z3 T2 (0/1): generalised the Akahu path for Fintegra and so inherited Akahu's
  `tables: ['transactions']`; statement and test expect `['transactions','accounts']`. It had
  4 ratchet trips and abandoned a consolidation. T3, T4 carry it.
- RC Z2 T1 (4/5), T3, T4 (5/6): **caused by its own T0.** T0 had made the template's rounding
  an explicit `'sum-first'` mode; at T1 Codex said "budget template calculations explicitly
  request a separate `sum-first` rounding mode … leave that explicit template behavior
  intact". This is study-2 §5.2's F failure ("a named exception read as protected
  behaviour"), now created by the agent's own abstraction. An inconsistency made explicit,
  which the interface score rewards, can produce later missed copies. Codex RC Z2 T3 also
  fails typecheck (TS2551, `_amountOp` on `RawScheduleData`).
- RC Z1 T4: correct, but the only **regression** in the pilot: removing `c.hidden = 0 AND
  g.hidden = 0` from the averages' SQL broke 3 of T1's 5 average tests and T2's
  same-categories test.
- Z4 T1 / T3 in R, RG, RL and RC, and T4 in R, RL and RC (RG Z4 T4 is correct): the study-2 §5.1 pattern; Codex changes
  `getNextDate`/`shared/schedules.ts` and never the template loop. Not attributable to T0
  (same in every arm); the T0 behaviour change travels into later RC trees but no hidden
  T1–T4 test exercises it.
- R Z3 T1 and RC Z3 T2: network-killed (§1), not agent failures.

**Haiku:** 64/64 T1–T4 and 4/4 T0 correct, with hidden tests actually run (`passed` > 0,
`start_fresh` true). Study 2: Haiku R 123/128, F 127/128.

### 4.3 Extreme cells (0 % / 100 %)

- 100 % correct for Sonnet R, Sonnet RL and all Haiku arms: real.
- Codex T2 static reuse 0 % in R (4/4 copy): real; four inline copies or private
  reimplementations.
- Sonnet RC T2 static reuse 100 % (4/4): real; all four call T0 helpers.
- Haiku RG/RL/RC T2 static reuse 100 %: mostly real; Z1 keeps only the sign flip inline.
- Missed copy 0 % for Sonnet R/RL/RC: partly an artefact. The registered definition counts
  only consumers listed at T1, so claude RC Z2 T3's miss of the T2-added consumer is not
  counted. Likewise Codex Z4 T3's total miss (0 of 2) is not counted. Codex RL Z2 found the
  template through a `num1.*num2` grep with 0 trips: search luck, not the lever.
- `rule_quoted` 0 % in every arm: the measure cannot detect the rule (§3.3).

**Static `t2_reuses_logic` label.** A spot-check of 17 of the 48 T2 diffs agreed in 11. In 5,
labelled `helper`, the new consumer calls an agent-made helper but pastes part of the zone
decision inline (claude RG Z1, codex RG Z1, haiku R Z1: the income gate; codex RC Z1: the SQL
hidden filter; haiku R Z4: the `skipWeekend ?` branch); in total 10 of 28 `helper` labels
have zone markers in their new code. In 1, generalising a copy site in place reads `copy`
when the function keeps its name (codex RL Z3 `linkAkahuAccount(…, 'fintegra')`) but
`helper` when it is renamed (haiku RG Z3 `linkSyncServerAccount`). The judge label stays
primary.

## 5. Descriptive pilot numbers (n = 1 chain per cell; not effects)

Counts, not rates; 4 chains per agent × arm. These describe what happened in the pilot and
must not be read as differences between arms.

- **T2 static label, helper / copy** (of 4 T2 steps): claude R 1/3, RG 2/2, RL 3/1, RC 4/0;
  codex R 0/4, RG 1/3, RL 1/3, RC 1/3; haiku R 3/1, RG 4/0, RL 4/0, RC 4/0. The judge labels
  are pending (plan Task 7).
- **Correct T1–T4:** table in §4.1.
- **RL ratchet (H4), non-blind Z1+Z3:** claude 2/4, codex 2/4, haiku 4/4.
- **T0 probe unchanged:** 11/12 (Codex Z4 changed 26 cases).
- **Chain tokens** (claude RC with T0 vs R, medians of 4): 1,763,936 vs 1,315,089. T0 adds
  roughly one step's cost.
- The mixed-effects logistic coefficients printed in `tables3.md` are fitted on 4–16
  observations and are reported there only because the script prints them; they carry no
  information at this size.

## 6. Problems and changes before the full run

### Blocking

1. **Network stalls recorded as agent timeouts.** `classify_status` lets exit 124 override a
   parsed `infra` outcome, and `CARRIED` carries `timeout`, so a host network outage is
   neither re-run nor excluded, the chain continues from a partial tree, and the step counts
   as not correct with 0 tokens. Fix: classify as infra when the transcript ends in
   transport errors (Codex `waiting for network` / `Name does not resolve`; check the Claude
   Code equivalent) or usage is 0 at the wall limit, and re-queue from that step. For pilot
   use, treat `codex/R/Z3/0/T1`, `codex/RC/Z3/0/T2` and their later steps as
   infra-contaminated.
2. **Claude multi-result token under-count.** `parse_claude_stream` (`src/aa/agents.py`)
   keeps only the last `result` event; when background tasks finish, Claude Code wakes the
   agent and writes a new `result` with per-segment usage. Pilot: 5/136 Claude-engine steps
   (claude RG/Z1/T4, RG/Z2/T3, RG/Z3/T4, RL/Z4/T1, haiku R/Z3/T3). Worst:
   `claude/RL/Z4/0/T1` recorded 2 turns / 102,715 input / 361 output; summed over its 3
   results it is 28 / 1,114,530 / 10,688. Study 2: 16/512 steps. The numbers flow into
   `result.json` and the efficiency and H5 tables; 4 of the 5 pilot cases are RG/RL steps
   (too few to say whether arms differ), so the bias can differ by arm. Fix: sum usage
   and turns over all `result` events; re-parse the pilot and `runs2`.
3. **Timeout usage recorded as 0.** A killed `codex exec` never emits `turn.completed`, so
   timeouts record 0 tokens (both pilot timeouts and both study-2 Codex timeouts; study 2
   also has one `ok` step with exit 1 and 0 usage, `runs2/codex/F/Z2/0/T1`). Record
   missing, not zero, so H5 does not count them as free.
4. **RL trip classification uses the final diff.** Snapshot `git diff -U0 <start>` at each
   dup-check invocation into a harness-owned location outside `/work` and classify each trip
   against its own snapshot; add a fixture test for "trip then consolidate"; re-evaluate the
   pilot RL steps.
5. **Register how RL firing is benchmarked.** Calibration (`out/study3/ratchet-firing-by-step.json`)
   applies to RL only at T1 and to the R/RG/RC counterfactual fields; RL T2–T4 firing is
   downstream of the treatment and must not be reported as "fires where calibration says".
6. **Register a decomposition of H4's fired steps:** (a) seen, passing by consolidation;
   (b) seen, passing by relocating the edit outside the clone; (c) seen, not fixed
   (including a false "lint passes" report); (d) fired on the final tree but never seen (no
   lint run, or an edit after the last lint). In the pilot 2 of 4 H4 failures are (d).
7. **RG manipulation check.** `rule_quoted` and `agents_md_read` cannot observe the rule
   (§3.3). Register an amendment: report RG compliance through behaviour only (T2 label,
   judge) and drop or rename `agents_md_read`, or add a measure that can observe it.
8. **Completeness rubric for partial sites.** `docs/design-review-rubric.md` (T0
   `completeness`) must say, before any T0 packet is judged, how to score a site whose
   decision goes through the shared definition but is still partly decided locally (Codex Z1
   SQL filter, Claude Z4 outer `skipWeekend ?`, Z2 null/number dispatch left at each site,
   Codex Z4 per-caller boolean). These occur in about half the T0 cells and will drive kappa
   and H3.
9. **Behaviour check for consolidations outside T0.** Run the zone's T0 inconsistency tests
   (those no T1–T4 statement supersedes) on every step's post tree in all arms, at least
   descriptively, and report unified inconsistencies beside H4 and the T2 label. Without it
   RC is the only arm checked for behaviour change, and an RL consolidation that unifies an
   inconsistency (haiku RL Z3 T2, §3.2) scores as a ratchet success. **[Done, see note
   item 5: haiku RL Z3 T2–T4 and haiku RG Z3 T2–T4.]**

### Nice to have

- Report steps near the T1–T4 caps (≥ 50 turns or ≥ 80 % of wall) by arm, and register how
  a cap hit is counted: the pilot's closest steps are all RL (haiku RL Z3 T2 59/60 turns, a
  post-trip consolidation; haiku RL Z2 T2 50/60, no trip; claude RL Z4 T1 1,365 s), and a cap
  hit is a `timeout`, i.e. not correct. n = 3, so no arm reading.
- Report the all-consumer missed copy beside the registered one (captures T3 misses of the
  T2 consumer and total misses); `result.json` already has it as `missed_copy` (e.g. claude
  RC Z2 T3 `missed_copy = true`, `missed_copy_preexisting = false`), only `aa tables3` omits it.
- Split later-step failures into "new at this step" vs "inherited through test coupling"
  (Z1 T4 asserts T3's `#fixed`, Z3 T4 asserts T1's refusal, Z4 T3 needs T1's daily skip).
- A `mixed` class for `t2_reuses_logic` (helper call plus zone markers), and name-independent
  handling of a generalised copy site.
- Narrow `added_code_outside_scope`: it flagged claude RL Z2 T3, haiku RL Z2 T3 and haiku RC
  Z2 T3 for updating desktop-client callers of a changed shared function (good design). None
  of these fired, so H4 is unaffected here.
- Do not use RL `lint_ok` as a ratchet proxy (false on carried type errors with `dup-check: ok`:
  claude RL Z1 T3/T4, haiku RL Z4 T2–T4).
- `lint_runs` counts lint commands that never ran after an earlier `&&` failure.
- Rename or document `probe_passed` (43 = vitest test count).
- Use tool calls, not `turns`, for efficiency (haiku R Z3 T3: 1 turn in 375 s; partly the
  multi-result bug).
- Timestamp every run-log line; keep infra attempts' `agent.json`/`stderr.log` instead of
  deleting them on rerun.
- A Claude rate-limit guard like Codex's: a weekly-cap `rejected` would be retried as infra
  8 times (91 min of backoff) and then mass-exhaust chains.
- Report results with and without Z4 as registered; for Codex, Z4 T1/T3 are a floor.

## 7. Full-run estimate

Per agent: 544 steps (32 T0 + 512 T1–T4), 8.0× the pilot's 68. Agents run one after
another, 2 chains in parallel; measured elapsed time is 1.02 × (sum of step times ÷ 2).

| agent | pilot mean wall (T1–T4 / T0) | agent time from pilot means | with study-2 R mean for T1–T4 (heavy tail) |
|---|---|---|---|
| codex | ~118 s (network kills excluded) / 94 s | 9.0 h | 19.6 h |
| claude | 277 s / 224 s | 21.1 h | 26.7 h |
| haiku | 344 s / 397 s | 26.7 h | 32.0 h |
| **total** | | **≈ 57 h** | **≈ 78 h** |

Pilot medians match study 2 (codex 102 vs 100 s, claude 212 vs 272 s, haiku 300 vs 351 s),
but study 2's means and p90 are higher (codex R mean 265 s, p90 822 s), so the pilot-based
figure is optimistic.

**Evaluation:** T1–T4 about 21 s per step with 2 workers (1,536 × 21 s ≈ 9.0 h); T0 evaluations
run alone, 176–200 s each (96 steps ≈ 4.7–5.3 h). Total ≈ 14 h. Evaluation cannot overlap agent
runs (the 6 GB Docker VM holds two loot-core containers).

**Total machine time: about 71 h (pilot means) to 92 h (study-2 tail), i.e. 3–4 days**, with
no margin for infrastructure incidents.

**Quota.** 8× the pilot per agent. Against study 2's full run (256 steps per agent, the 16
multi-result steps corrected):

| agent | projected input / uncached / output | study 2 input / uncached / output | ratio |
|---|---|---|---|
| codex | 355M / 23.0M / 1.87M | 171M / 11.3M / 0.90M | ≈ 2.1× |
| claude | 197M / 13.3M / 2.06M | 89.0M / 6.07M / 0.87M | ≈ 2.2–2.4× |
| haiku | 638M / 25.2M / 8.01M | 316M / 11.7M / 3.50M | ≈ 2.0–2.3× |

The ratios are close to the step ratio 544 / 256 = 2.125×; Codex adds about 3 % for steps
with no recorded usage. All on subscriptions, no money cost.

- **Claude weekly window:** it stood at 0.78 before the pilot (other use) and 0.79 after all
  136 Sonnet and Haiku steps; the 5-hour window peaked at 0.05. Scaling ×8 gives roughly
  8–16 points of the weekly window (resolution 0.01, so rough). It resets 2026-10-12 21:00 UTC;
  start the Claude blocks after the reset.
- **Codex login:** the current token expires 2026-10-22 06:57 UTC; the guard refuses to
  start Codex after 2026-10-21 06:57 UTC. Run Codex first, or log in again immediately
  before the Codex block. With the order claude → haiku → codex the full run must start by
  about 2026-10-18/19.
