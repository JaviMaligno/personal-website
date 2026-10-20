// @ts-strict-ignore
// Behaviour (issue #8464): a file import must honour the decisions the import
// preview showed. The preview and the real import both go through the
// "transactions-import" handler; the dialog drops the rows the user unchecked,
// so the import sees fewer rows than the preview did. A row the preview showed
// as new must be added as a new transaction, and a row the preview matched to a
// given existing transaction must be merged into THAT transaction, when the
// caller passes the preview's decision along (`matchedTransactionId`: the
// existing transaction's id, or null for "no match, add as new"). Callers that
// do not pass it keep the usual duplicate detection.
import { loadMappings } from '#server/db/mappings';
import { handlers } from '#server/main';
import * as prefs from '#server/prefs';
import { loadRules } from '#server/transactions/transaction-rules';

vi.mock('#server/post');

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
  await prefs.loadPrefs();
});

afterEach(() => {
  prefs.unloadPrefs();
});

async function newAccount(name = 'Checking') {
  return handlers['api/account-create']({ account: { name } });
}

async function existing(accountId: string, rows) {
  await handlers['api/transactions-add']({
    accountId,
    transactions: rows,
  });
  const all = await handlers['api/transactions-get']({ accountId });
  return all.filter(t => t.amount !== 0);
}

async function txns(accountId: string) {
  const all = await handlers['api/transactions-get']({ accountId });
  return all.filter(t => t.amount !== 0);
}

function preview(accountId: string, transactions) {
  return handlers['transactions-import']({
    accountId,
    transactions,
    isPreview: true,
  });
}

function runImport(accountId: string, transactions) {
  return handlers['transactions-import']({
    accountId,
    transactions,
    isPreview: false,
  });
}

function strip(row) {
  const { trx_id: _trx_id, ...rest } = row;
  return rest;
}

describe('file import honours the preview decisions', () => {
  it('adds a row the preview showed as new even when the true duplicate is left out', async () => {
    const acct = await newAccount();
    const [netflix] = await existing(acct, [
      { date: '2026-03-10', amount: -899, payee_name: 'Netflix' },
    ]);

    const file = [
      {
        trx_id: '0',
        date: '2026-03-10',
        amount: -899,
        payee_name: 'Netflix',
        notes: 'Subscription',
      },
      {
        trx_id: '1',
        date: '2026-03-08',
        amount: -899,
        payee_name: 'Corner Coffee',
        notes: 'Latte and croissant',
      },
    ];

    const { updatedPreview } = await preview(acct, file);
    const byRow = new Map(
      updatedPreview.map(e => [(e.transaction as any).trx_id, e]),
    );
    // Precondition (what the dialog shows): Netflix row matched to the
    // existing Netflix transaction, Corner Coffee row is a plain new row.
    expect(byRow.get('0')?.existing?.id).toBe(netflix.id);
    expect(byRow.has('1')).toBe(false);

    // The user unchecks the duplicate Netflix row; only Corner Coffee is
    // imported, carrying the preview's decision ("no match").
    const result = await runImport(acct, [
      { ...strip(file[1]), matchedTransactionId: null },
    ]);
    expect(result.errors).toEqual([]);

    const after = await txns(acct);
    expect(after).toHaveLength(2);
    expect(after.reduce((s, t) => s + t.amount, 0)).toBe(-1798);

    const coffee = after.find(t => t.id !== netflix.id);
    expect(coffee).toBeDefined();
    expect(coffee.amount).toBe(-899);
    expect(coffee.date).toBe('2026-03-08');
    expect(coffee.notes).toBe('Latte and croissant');
    expect(coffee.imported_payee).toBe('Corner Coffee');

    const netflixAfter = after.find(t => t.id === netflix.id);
    expect(netflixAfter.payee).toBe(netflix.payee);
    expect(netflixAfter.imported_payee ?? null).toBe(
      netflix.imported_payee ?? null,
    );
    expect(netflixAfter.notes ?? null).toBe(netflix.notes ?? null);
    expect(netflixAfter.date).toBe('2026-03-10');
  });

  it('merges a row into the existing transaction the preview matched it to', async () => {
    const acct = await newAccount();
    await existing(acct, [
      { date: '2026-05-01', amount: -5000, payee_name: 'Gym' },
      { date: '2026-05-06', amount: -5000, payee_name: 'Electricity' },
    ]);
    const before = await txns(acct);
    const early = before.find(t => t.date === '2026-05-01');
    const late = before.find(t => t.date === '2026-05-06');

    const file = [
      {
        trx_id: '0',
        date: '2026-05-02',
        amount: -5000,
        payee_name: 'Bookshop',
        notes: 'first row',
      },
      {
        trx_id: '1',
        date: '2026-05-03',
        amount: -5000,
        payee_name: 'Hardware Store',
        notes: 'second row',
      },
    ];

    const { updatedPreview } = await preview(acct, file);
    const byRow = new Map(
      updatedPreview.map(e => [(e.transaction as any).trx_id, e]),
    );
    const target0 = byRow.get('0')?.existing?.id;
    const target1 = byRow.get('1')?.existing?.id;
    expect(target0).toBeDefined();
    expect(target1).toBeDefined();
    expect(new Set([target0, target1])).toEqual(new Set([early.id, late.id]));

    // The user unchecks the first row and keeps the second one in its
    // default "merge with existing" state.
    const result = await runImport(acct, [
      { ...strip(file[1]), matchedTransactionId: target1 },
    ]);
    expect(result.errors).toEqual([]);

    const after = await txns(acct);
    expect(after).toHaveLength(2);
    expect(after.reduce((s, t) => s + t.amount, 0)).toBe(-10000);

    const merged = after.find(t => t.id === target1);
    expect(merged.imported_payee).toBe('Hardware Store');
    expect(merged.notes).toBe('second row');

    const untouched = after.find(t => t.id === target0);
    const untouchedBefore = before.find(t => t.id === target0);
    expect(untouched.imported_payee ?? null).toBe(
      untouchedBefore.imported_payee ?? null,
    );
    expect(untouched.notes ?? null).toBe(untouchedBefore.notes ?? null);
  });

  it('honours preview decisions for a mixed batch in one import', async () => {
    const acct = await newAccount();
    const [rent] = await existing(acct, [
      { date: '2026-07-01', amount: -120000, payee_name: 'Landlord' },
    ]);

    const file = [
      {
        trx_id: '0',
        date: '2026-07-01',
        amount: -120000,
        payee_name: 'Landlord',
        notes: 'July rent',
      },
      {
        trx_id: '1',
        date: '2026-07-03',
        amount: -120000,
        payee_name: 'Laptop Store',
        notes: 'new laptop',
      },
    ];

    const { updatedPreview } = await preview(acct, file);
    const byRow = new Map(
      updatedPreview.map(e => [(e.transaction as any).trx_id, e]),
    );
    expect(byRow.get('0')?.existing?.id).toBe(rent.id);
    expect(byRow.has('1')).toBe(false);

    // Both rows kept, but passed in reverse order: the decisions shown in the
    // preview still hold.
    const result = await runImport(acct, [
      { ...strip(file[1]), matchedTransactionId: null },
      { ...strip(file[0]), matchedTransactionId: rent.id },
    ]);
    expect(result.errors).toEqual([]);

    const after = await txns(acct);
    expect(after).toHaveLength(2);
    expect(after.reduce((s, t) => s + t.amount, 0)).toBe(-240000);
    const rentAfter = after.find(t => t.id === rent.id);
    expect(rentAfter.notes).toBe('July rent');
    const laptop = after.find(t => t.id !== rent.id);
    expect(laptop.notes).toBe('new laptop');
    expect(laptop.date).toBe('2026-07-03');
  });

  it('still de-duplicates a re-imported row when no preview decision is given', async () => {
    const acct = await newAccount();
    const [netflix] = await existing(acct, [
      { date: '2026-03-10', amount: -899, payee_name: 'Netflix' },
    ]);

    const result = await runImport(acct, [
      { date: '2026-03-10', amount: -899, payee_name: 'Netflix' },
    ]);
    expect(result.errors).toEqual([]);

    const after = await txns(acct);
    expect(after).toHaveLength(1);
    expect(after[0].id).toBe(netflix.id);
    expect(after[0].amount).toBe(-899);
  });
});
