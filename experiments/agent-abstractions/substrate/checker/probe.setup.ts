// substrate/checker/probe.setup.ts — extra vitest setupFile at evaluation only
// (copied into the tree as src/mocks/aa-probe.setup.ts and added through
// vitest.aa.config.ts, because vitest 5 has no --setupFiles flag). Hidden from the agent.
//
// Emits one JSON line per event to $AA_PROBE_OUT:
//   {"kind": "raw_write", "table", "sql", "caller"}
//   {"kind": "non_integer_money", "table", "column", "value", "caller"}
// "caller" is the first stack frame outside src/server/db, src/server/sync and
// src/platform (see aa.static_check.probe_violations, which only counts a
// raw_write whose caller is a line the agent added).
//
// Validated on base 9732a446 with Node 24.18.1 / vitest 5.0.0 by the canary
// (substrate/checker/canary.test.ts, aa.checker.run_canary):
// * vi.spyOn on the namespace works for *cross-module* calls (db/index.ts ->
//   sqlite.runQuery, anything -> sync.sendMessages). It does not intercept calls
//   inside the same module, so spying sync.applyMessages saw nothing: sendMessages
//   and batchMessages reach it internally. Money values are therefore inspected in
//   the sendMessages spy (batchMessages collects through sendMessages too).
// * The CRDT engine applies messages with runQuery from src/server/sync/; those
//   writes are not raw writes, and are recognised by their issuing frame (nearest
//   frame outside db/, platform/, libraries and the probe) being in sync/ (a flag set
//   around applyMessages never engaged, see above).
import { appendFileSync } from 'fs';

import { vi } from 'vitest';

import * as sqlite from '#platform/server/sqlite';
import * as sync from '#server/sync';

const OUT = process.env.AA_PROBE_OUT!;
const SYNCED = new Set(['transactions', 'accounts', 'categories', 'category_groups', 'payees',
  'payee_mapping', 'schedules', 'rules', 'notes', 'tags', 'zero_budgets', 'reflect_budgets',
  'custom_reports', 'dashboard', 'preferences', 'transaction_filters', 'category_mapping']);
const MONEY: Record<string, string[]> = {
  transactions: ['amount'], zero_budgets: ['amount', 'carryover', 'goal', 'long_goal'],
  reflect_budgets: ['amount', 'carryover', 'goal', 'long_goal'],
};
const IGNORED_FRAMES = /src\/(server\/db|server\/sync|platform)\/|node_modules|probe\.setup/;
const SYNC_FRAME = /src\/server\/sync\//;
const CALLER_FRAME = /(src\/[^\s):]+):(\d+)/;
const STACK_LIMIT = 30;
const SHALLOW_LIMIT = 8;
// Write statements start with one of these letters (after leading whitespace); every
// other SQL (SELECT, PRAGMA, CREATE, ...) returns before the regex runs.
const WRITE_FIRST = new Set(['I', 'i', 'U', 'u', 'D', 'd', 'R', 'r']);
const WRITE = /^\s*(INSERT(\s+OR\s+\w+)?\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+["`]?(\w+)/i;

// Performance (freeze gate, 2026-10-05): fast-check property tests apply thousands of
// CRDT messages, each a runQuery write on a synced table. Formatting a source-mapped
// `new Error().stack` for every one of them made src/server/aql/schema/executors.test.ts
// 3-4x slower and pushed it past vitest timeouts. Hence:
// * fromSync() inspects raw V8 CallSites (file names only: no string formatting, no
//   source maps), shallow first, with a bounded stackTraceLimit;
// * the formatted stack is built only in caller(), i.e. only when an event is emitted
//   (a non-sync write on a synced table, or a non-integer money value).
function withStackLimit<T>(limit: number, fn: () => T): T {
  const prev = Error.stackTraceLimit;
  Error.stackTraceLimit = limit;
  try {
    return fn();
  } finally {
    Error.stackTraceLimit = prev;
  }
}
const asSites = (_e: Error, sites: NodeJS.CallSite[]) => sites;
// Frames that never issue a write themselves: the db layer, platform, libraries
// (vitest/tinyspy), node internals and the probe.
const PASS_THROUGH = /src\/(server\/db|platform)\/|node_modules|probe\.setup|^node:/;
// Some frame within `limit` decides; null = all frames within `limit` are pass-through.
function issuedBySyncWithin(limit: number): boolean | null {
  return withStackLimit(limit, () => {
    const prevPrepare = Error.prepareStackTrace;
    Error.prepareStackTrace = asSites;
    const holder: { stack?: NodeJS.CallSite[] } = {};
    try {
      Error.captureStackTrace(holder);
      const sites = holder.stack;
      if (!Array.isArray(sites)) return null;
      for (const s of sites) {
        const f = s.getFileName();
        if (!f || PASS_THROUGH.test(f)) continue;
        return SYNC_FRAME.test(f);
      }
      return null;
    } finally {
      Error.prepareStackTrace = prevPrepare;
    }
  });
}
// A write comes from the CRDT engine when the nearest frame that is not pass-through
// (the code that issued it, as in caller()) is in src/server/sync/. Not "any sync/
// frame on the stack": batchMessages() (sync/index.ts) runs the caller's callback, so
// a raw write inside batchMessages(async () => ...) has a sync/ frame further up and
// must still count (canary case 3). The issuing frame is ~4 frames above the spy, so
// the shallow look settles almost every write; the deep look runs only if it did not.
const fromSync = () => issuedBySyncWithin(SHALLOW_LIMIT) ?? issuedBySyncWithin(STACK_LIMIT) ?? false;
function caller(): string {
  // Source-mapped frames, as the agent's diff sees the file; first one outside
  // db/sync/platform. slice(2): "Error" line and caller() itself.
  const fs = withStackLimit(STACK_LIMIT, () => new Error().stack ?? '').split('\n').slice(2);
  for (const f of fs) {
    const m = CALLER_FRAME.exec(f);
    if (m && !IGNORED_FRAMES.test(f)) return `${m[1]}:${m[2]}`;
  }
  return 'unknown';
}
// vi.spyOn records every call's arguments and result; the probe never reads them, and
// over a property test they pile up (thousands of runQuery calls). Drop them now and then.
let calls = 0;
function forgetCalls(): void {
  if (++calls % 1000 === 0) {
    runSpy.mockClear();
    sendSpy.mockClear();
  }
}
const emit = (e: object) => {
  if (OUT) appendFileSync(OUT, JSON.stringify(e) + '\n');
};
function writeTable(text: string): string | null {
  let i = 0;
  while (i < text.length && text.charCodeAt(i) <= 32) i++;
  if (!WRITE_FIRST.has(text[i])) return null;
  const m = WRITE.exec(text);
  if (!m) return null;
  const table = m[3].toLowerCase();
  return SYNCED.has(table) ? table : null;
}

const origSend = sync.sendMessages;
const sendSpy = vi.spyOn(sync, 'sendMessages').mockImplementation((async (msgs: sync.Message[]) => {
  for (const m of msgs ?? []) {
    const cols = MONEY[m.dataset];
    if (cols?.includes(m.column) && typeof m.value === 'number' && !Number.isInteger(m.value)) {
      emit({ kind: 'non_integer_money', table: m.dataset, column: m.column, value: m.value, caller: caller() });
    }
  }
  return origSend(msgs);
}) as typeof sync.sendMessages);

const origRun = sqlite.runQuery;
const runSpy = vi.spyOn(sqlite, 'runQuery').mockImplementation(((db, sql, params, fetchAll) => {
  const text = typeof sql === 'string' ? sql : (sql as { source?: string }).source ?? '';
  forgetCalls();
  const table = writeTable(text);
  if (table !== null && !fromSync()) {
    emit({ kind: 'raw_write', table, sql: text.slice(0, 200), caller: caller() });
  }
  return origRun(db, sql, params, fetchAll);
}) as typeof sqlite.runQuery);
