// substrate/checker/seed.setup.ts — extra vitest setupFile in EVERY harness vitest run
// (suite baselines, equivalence, `aa checker baseline` probe-on and probe-off, both
// evaluation passes, the task sanity check), identical on the four conditions. Copied
// into the tree as src/mocks/aa-seed.setup.ts at run time only; not part of any variant
// patch and not in the agents' start tree.
//
// Why (freeze gate, 2026-10-06): the fast-check property tests in
// src/server/aql/schema/executors.test.ts ("queries the correct transactions with a
// filter" / "without filters", numRuns 300) are unseeded, so every run draws new
// inputs; inside the full suite they failed intermittently (APL once, rerun passed).
// A fixed global seed makes every fc.assert / fc.check draw the same inputs on every
// run and condition. Per-call parameters still win (no test in loot-core sets `seed`).
// fast-check 4.9.0: configureGlobal replaces the global parameters, so the existing
// ones are spread in first.
import * as fc from 'fast-check';

export const AA_FAST_CHECK_SEED = 20261006;

fc.configureGlobal({ ...fc.readConfigureGlobal(), seed: AA_FAST_CHECK_SEED });
