# Study 2 full run — execution log

- 2026-10-09 08:18: full run launched with the three agents concurrently (codex 2 + claude 3 +
  haiku 2 containers; commit e8d1816).
- 2026-10-09 14:45: stopped Claude and Haiku. With 7 study containers plus other host workloads
  (load ≈ 20), 20/56 Claude and 17/30 Haiku steps hit the 25-min wall: both agents end every step
  with monorepo-wide `yarn lint` / `yarn typecheck` and wait on them; under that load they no
  longer finish (pilot at lower load: 2/96 timeouts). Codex (2/53 timeouts) does not run those
  commands and was left running. Claude/Haiku steps of this attempt are archived in
  `work/superseded/runs2-overload/` and not used.
- Rerun: after Codex finishes, Claude alone (3 workers), then Haiku alone (3 workers) — the load
  of the pilot. Conditions R/F stay interleaved by the scheduler within each agent.
- 2026-10-09 ~15:00 and ~21:24: Docker Desktop was quit manually on the host (Javier, to stop
  unrelated containers; he did not know the study used it). The first time, 2 Codex steps went
  `infra` and were retried by the runner. The second time, 38 Claude and all 64 Haiku steps failed
  instantly with `setup_error` ("failed to connect to the docker API"), and part of the evaluation
  ran without Docker (`eval_error=container`). Those 102 step dirs (only those with that exact
  error) were deleted so the runner re-runs them from that step; the evaluation is redone with
  `--force` for every step. Codex completed all 256 steps (254 ok, 2 timeouts).
