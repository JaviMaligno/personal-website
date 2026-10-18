// substrate/checker/canary.test.ts — probe canary (review finding 5).
// Copied into the tree as src/server/aa-canary.test.ts by aa.checker.run_canary
// and run together with probe.setup.ts. It drives two raw SQL writes to synced
// tables (one inside batchMessages) and one non-integer amount through the normal db code paths; the probe
// must report both, otherwise it is silently recording nothing (e.g. vi.spyOn
// could not replace the ESM namespace exports) and every run would look clean.
// Never shown to agents; never part of baseline-writers.json. Runs on all four
// conditions (see the db/write note below).
import * as dbIndex from './db';
import { batchMessages } from './sync';

// In A+ (AP/APL) the CRDT write API lives in ./db/write (the A+ write boundary);
// in A/AL it is exported by ./db. import.meta.glob yields {} when the file does
// not exist, so the same canary runs unchanged in all four conditions.
const writeModules = import.meta.glob('./db/write.ts', { eager: true });
const db = { ...dbIndex, ...Object.values(writeModules)[0] } as typeof dbIndex;

beforeEach(global.emptyDatabase());

test('aa probe canary: raw UPDATE categories', async () => {
  await db.insertCategoryGroup({ id: 'aa-canary-group', name: 'aa-canary-group' });
  const id = await db.insertCategory({ name: 'aa-canary', cat_group: 'aa-canary-group' });
  await db.runQuery('UPDATE categories SET hidden = 1 WHERE id = ?', [id]); // AA_CANARY_RAW_WRITE
  const row = await db.first<{ hidden: number }>('SELECT hidden FROM categories WHERE id = ?', [id]);
  expect(row?.hidden).toBe(1);
});

test('aa probe canary: non-integer amount through sendMessages', async () => {
  await db.insertAccount({ id: 'aa-canary-account', name: 'aa-canary-account' });
  const id = await db.insertTransaction({ account: 'aa-canary-account', amount: 1250, date: '2026-01-01' });
  // db.update goes straight to sendMessages (no schema conversion), so the
  // non-integer value reaches applyMessages, where the probe inspects it.
  await db.update('transactions', { id, amount: 12.5 }); // AA_CANARY_NON_INTEGER_MONEY
  expect((await db.getTransactions('aa-canary-account')).length).toBe(1);
});

test('aa probe canary: raw UPDATE category_groups inside batchMessages', async () => {
  // batchMessages lives in src/server/sync/, so a sync/ frame is on the stack here;
  // the probe must still attribute this write to the canary, not to the CRDT engine.
  await db.insertCategoryGroup({ id: 'aa-canary-group-2', name: 'aa-canary-group-2' });
  await batchMessages(async () => {
    db.runQuery('UPDATE category_groups SET hidden = 1 WHERE id = ?', ['aa-canary-group-2']); // AA_CANARY_RAW_IN_BATCH
  });
  const row = await db.first<{ hidden: number }>('SELECT hidden FROM category_groups WHERE id = ?', ['aa-canary-group-2']);
  expect(row?.hidden).toBe(1);
});
