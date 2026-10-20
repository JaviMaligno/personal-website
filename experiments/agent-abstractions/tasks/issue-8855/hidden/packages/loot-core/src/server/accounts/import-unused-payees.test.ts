// @ts-strict-ignore
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { setSyncingMode } from '#server/sync';
import { loadRules } from '#server/transactions/transaction-rules';

import { app as payeesApp } from '../payees/app';
import { app as rulesApp } from '../rules/app';

import { app as accountsApp } from './app';

// Importing transactions must not leave behind payees that no transaction ends
// up using: not when a row matches an existing transaction by imported_id (the
// existing transaction keeps its payee), and not during a preview import. A
// payee that does end up used is created exactly once and linked.

type PayeeRow = { id: string; name: string; tombstone: number };

async function payeeRows(): Promise<PayeeRow[]> {
  // Every non-transfer payee row, deleted (tombstoned) ones included.
  return db.all<PayeeRow>(
    'SELECT id, name, tombstone FROM payees WHERE transfer_acct IS NULL ORDER BY name, id',
  );
}

async function transactionRows() {
  return db.all<{ id: string; imported_id: string | null; payee: string | null }>(
    'SELECT id, imported_id, payee FROM v_transactions ORDER BY imported_id, id',
  );
}

async function lastTimestamp(): Promise<string> {
  const row = await db.first<{ ts: string | null }>(
    'SELECT MAX(timestamp) AS ts FROM messages_crdt',
  );
  return row?.ts ?? '';
}

async function payeeMessagesSince(after: string) {
  return db.all<{ row: string; column: string }>(
    "SELECT row, column FROM messages_crdt WHERE dataset = 'payees' AND timestamp > ?",
    [after],
  );
}

async function importRows(accountId: string, transactions, isPreview = false) {
  const result = await accountsApp.handlers['transactions-import']({
    accountId,
    transactions,
    isPreview,
  });
  expect(result.errors).toEqual([]);
  return result;
}

async function addRenameRule(importedPayee: string, newName: string) {
  const rule = await rulesApp.handlers['rule-add']({
    stage: null,
    conditionsOp: 'and',
    conditions: [{ op: 'is', field: 'imported_payee', value: importedPayee }],
    actions: [{ op: 'set', field: 'payee_name', value: newName }],
  });
  expect(rule).not.toHaveProperty('error');
}

function bankRow(importedId: string, extra = {}) {
  return {
    date: '2024-01-02',
    amount: -1000,
    imported_id: importedId,
    payee_name: 'FOOBAR',
    imported_payee: 'FOOBAR',
    ...extra,
  };
}

describe('transactions-import does not create unused payees', () => {
  let acct: string;

  beforeEach(async () => {
    await global.emptyDatabase()();
    await loadMappings();
    await loadRules();
    // Record changes for sync locally (no sync server involved).
    setSyncingMode('offline');
    acct = await accountsApp.handlers['account-create']({ name: 'Bank' });
  });

  afterEach(() => {
    setSyncingMode('disabled');
  });

  it('re-importing a matched row with a rule pointing at an existing payee creates nothing', async () => {
    const target = await payeesApp.handlers['payee-create']({
      name: 'FooBar, Inc',
    });
    const rule = await rulesApp.handlers['rule-add']({
      stage: null,
      conditionsOp: 'and',
      conditions: [{ op: 'is', field: 'imported_payee', value: 'FOOBAR' }],
      actions: [{ op: 'set', field: 'payee', value: target }],
    });
    expect(rule).not.toHaveProperty('error');

    await importRows(acct, [bankRow('bank-1')]);
    const before = await payeeRows();
    expect(before.map(p => [p.name, p.tombstone])).toEqual([
      ['FooBar, Inc', 0],
    ]);

    const ts = await lastTimestamp();
    await importRows(acct, [bankRow('bank-1')], true);
    await importRows(acct, [bankRow('bank-1')]);

    expect(await payeeRows()).toEqual(before);
    expect(await payeeMessagesSince(ts)).toEqual([]);
    const txs = await transactionRows();
    expect(txs).toHaveLength(1);
    expect(txs[0].payee).toBe(target);
  });

  it('re-importing a row matched by imported_id does not create the payee a rule names', async () => {
    // First import, before any rule exists: the transaction gets its own payee.
    await importRows(acct, [bankRow('bank-1')]);
    const before = await payeeRows();
    expect(before).toHaveLength(1);
    const original = before[0].id;
    expect((await transactionRows())[0].payee).toBe(original);

    // A rule that renames the payee to a name that does not exist yet.
    await addRenameRule('FOOBAR', 'FooBar, Inc');

    const ts = await lastTimestamp();
    const result = await importRows(acct, [bankRow('bank-1')]);
    expect(result.added).toEqual([]);

    // The existing transaction keeps its payee, so no payee may be created
    // (not even one that is deleted again afterwards).
    const txs = await transactionRows();
    expect(txs).toHaveLength(1);
    expect(txs[0].payee).toBe(original);
    expect(await payeeRows()).toEqual(before);
    expect(await payeeMessagesSince(ts)).toEqual([]);
  });

  it('a preview import of a matched row creates no payee', async () => {
    await importRows(acct, [bankRow('bank-1')]);
    const before = await payeeRows();
    await addRenameRule('FOOBAR', 'FooBar, Inc');

    const ts = await lastTimestamp();
    const preview = await importRows(acct, [bankRow('bank-1')], true);
    expect(preview.added).toEqual([]);

    expect(await payeeRows()).toEqual(before);
    expect(await payeeMessagesSince(ts)).toEqual([]);
  });

  it('a preview import of a new row creates no payee', async () => {
    await addRenameRule('FOOBAR', 'FooBar, Inc');

    const ts = await lastTimestamp();
    await importRows(acct, [bankRow('bank-1')], true);

    expect(await payeeRows()).toEqual([]);
    expect(await payeeMessagesSince(ts)).toEqual([]);
    expect(await transactionRows()).toEqual([]);
  });

  it('a new row renamed by a rule gets the renamed payee, created once', async () => {
    await addRenameRule('FOOBAR', 'FooBar, Inc');

    await importRows(acct, [bankRow('bank-1')]);

    const payees = await payeeRows();
    expect(payees.map(p => [p.name, p.tombstone])).toEqual([
      ['FooBar, Inc', 0],
    ]);
    const txs = await transactionRows();
    expect(txs).toHaveLength(1);
    expect(txs[0].payee).toBe(payees[0].id);
  });

  it('several new rows renamed to the same new name share one payee', async () => {
    await addRenameRule('FOOBAR', 'FooBar, Inc');

    await importRows(acct, [
      bankRow('bank-1'),
      bankRow('bank-2', { date: '2024-01-03', amount: -2500 }),
      bankRow('bank-3', { date: '2024-01-04', amount: -700 }),
    ]);

    const payees = await payeeRows();
    expect(payees.map(p => [p.name, p.tombstone])).toEqual([
      ['FooBar, Inc', 0],
    ]);
    const txs = await transactionRows();
    expect(txs).toHaveLength(3);
    expect(txs.every(t => t.payee === payees[0].id)).toBe(true);
  });

  it('a batch mixing a matched row and a new row creates the renamed payee once, for the new row', async () => {
    await importRows(acct, [bankRow('bank-1')]);
    const [original] = await payeeRows();
    await addRenameRule('FOOBAR', 'FooBar, Inc');

    await importRows(acct, [
      bankRow('bank-1'),
      bankRow('bank-2', { date: '2024-01-10', amount: -4200 }),
    ]);

    const payees = await payeeRows();
    expect(payees).toHaveLength(2);
    expect(payees.every(p => p.tombstone === 0)).toBe(true);
    expect(payees.map(p => p.name).sort()).toEqual(
      ['FooBar, Inc', original.name].sort(),
    );
    const renamed = payees.find(p => p.name === 'FooBar, Inc');
    const txs = await transactionRows();
    expect(txs.map(t => [t.imported_id, t.payee])).toEqual([
      ['bank-1', original.id],
      ['bank-2', renamed.id],
    ]);
  });

  it('a matched row without a payee takes the renamed payee, which is created', async () => {
    // First import carries no payee at all.
    await importRows(acct, [
      { date: '2024-01-02', amount: -1000, imported_id: 'bank-1', imported_payee: 'FOOBAR' },
    ]);
    expect(await payeeRows()).toEqual([]);
    expect((await transactionRows())[0].payee).toBeNull();

    await addRenameRule('FOOBAR', 'FooBar, Inc');
    await importRows(acct, [bankRow('bank-1')]);

    const payees = await payeeRows();
    expect(payees.map(p => [p.name, p.tombstone])).toEqual([
      ['FooBar, Inc', 0],
    ]);
    const txs = await transactionRows();
    expect(txs).toHaveLength(1);
    expect(txs[0].payee).toBe(payees[0].id);
  });
});
