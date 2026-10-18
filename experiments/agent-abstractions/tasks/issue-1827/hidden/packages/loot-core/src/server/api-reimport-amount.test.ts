// @ts-strict-ignore
// Behaviour: re-importing a transaction through the API import call, when a
// transaction with the same imported_id already exists in the account, must
// bring the stored amount in line with the imported amount (no duplicate), while
// keeping what the user did to the transaction: notes, cleared status,
// reconciled lock, splits, and the other side of a transfer.
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { handlers } from '#server/main';
import * as prefs from '#server/prefs';
import { loadRules } from '#server/transactions/transaction-rules';
import type { ImportTransactionEntity } from '#types/models';

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

async function createAccount(name: string) {
  return handlers['api/account-create']({ account: { name } });
}

function importRows(
  accountId: string,
  rows: Omit<ImportTransactionEntity, 'account'>[],
  isPreview = false,
) {
  return handlers['api/transactions-import']({
    accountId,
    transactions: rows as ImportTransactionEntity[],
    isPreview,
  });
}

async function getTransactions(accountId: string) {
  return handlers['api/transactions-get']({ accountId });
}

// The user edits a transaction (as the app does when a field is changed).
async function editTransaction(id: string, fields: object) {
  await handlers['transactions-batch-update']({
    updated: [{ id, ...fields }],
  });
}

function balance(accountId: string) {
  return handlers['api/account-balance']({ id: accountId });
}

// Stored, non-deleted leaf rows (children of splits included, parents excluded).
async function liveLeafRows(accountId: string) {
  return db.all<{
    id: string;
    amount: number;
    transfer_id: string | null;
    parent_id: string | null;
  }>(
    `SELECT id, amount, transferred_id AS transfer_id, parent_id
       FROM transactions
      WHERE acct = ? AND tombstone = 0 AND isParent = 0
      ORDER BY amount, id`,
    [accountId],
  );
}

async function liveParentRows(accountId: string) {
  return db.all<{ id: string; amount: number }>(
    `SELECT id, amount FROM transactions
      WHERE acct = ? AND tombstone = 0 AND isParent = 1`,
    [accountId],
  );
}

describe('re-importing a transaction whose amount changed', () => {
  it('updates the amount of the existing transaction instead of keeping the old one', async () => {
    const acct = await createAccount('Checking');
    await importRows(acct, [
      {
        date: '2024-02-10',
        amount: -4500,
        payee_name: 'Hardware Store',
        imported_id: 'bank-1',
      },
    ]);
    const [original] = await getTransactions(acct);

    const result = await importRows(acct, [
      {
        date: '2024-02-10',
        amount: -5250,
        payee_name: 'Hardware Store',
        imported_id: 'bank-1',
      },
    ]);

    expect(result.errors).toEqual([]);
    expect(result.added).toHaveLength(0);
    expect(result.updated).toContain(original.id);

    const after = await getTransactions(acct);
    expect(after).toHaveLength(1);
    expect(after[0].id).toBe(original.id);
    expect(after[0].amount).toBe(-5250);
    expect(after[0].imported_id).toBe('bank-1');
    expect(await balance(acct)).toBe(-5250);
  });

  it('handles a sign flip (a payment re-imported as a deposit)', async () => {
    const acct = await createAccount('Checking');
    await importRows(acct, [
      {
        date: '2024-02-11',
        amount: 3000,
        payee_name: 'Shop',
        imported_id: 'f1',
      },
    ]);
    await importRows(acct, [
      {
        date: '2024-02-11',
        amount: -3000,
        payee_name: 'Shop',
        imported_id: 'f1',
      },
    ]);

    const after = await getTransactions(acct);
    expect(after).toHaveLength(1);
    expect(after[0].amount).toBe(-3000);
    expect(await balance(acct)).toBe(-3000);
  });

  it('keeps the notes and the uncleared status the user set', async () => {
    const acct = await createAccount('Checking');
    await importRows(acct, [
      {
        date: '2024-02-12',
        amount: -1000,
        payee_name: 'Cafe',
        imported_id: 'c1',
      },
    ]);
    const [original] = await getTransactions(acct);
    await editTransaction(original.id, { notes: 'team lunch', cleared: false });

    // The re-imported row does not say anything about cleared or notes.
    await importRows(acct, [
      {
        date: '2024-02-12',
        amount: -1250,
        payee_name: 'Cafe',
        imported_id: 'c1',
      },
    ]);

    const after = await getTransactions(acct);
    expect(after).toHaveLength(1);
    expect(after[0].amount).toBe(-1250);
    expect(after[0].notes).toBe('team lunch');
    expect(after[0].cleared).toBe(false);
  });

  it('never un-clears a transaction that is already cleared', async () => {
    const acct = await createAccount('Checking');
    await importRows(acct, [
      {
        date: '2024-02-13',
        amount: -800,
        payee_name: 'Bakery',
        imported_id: 'k1',
        cleared: true,
      },
    ]);

    await importRows(acct, [
      {
        date: '2024-02-13',
        amount: -900,
        payee_name: 'Bakery',
        imported_id: 'k1',
        cleared: false,
      },
    ]);

    const after = await getTransactions(acct);
    expect(after).toHaveLength(1);
    expect(after[0].amount).toBe(-900);
    expect(after[0].cleared).toBe(true);
  });

  it('only changes the transactions whose amount differs in a mixed batch', async () => {
    const acct = await createAccount('Checking');
    await importRows(acct, [
      { date: '2024-03-01', amount: -100, payee_name: 'A', imported_id: 'm1' },
      { date: '2024-03-02', amount: -200, payee_name: 'B', imported_id: 'm2' },
      { date: '2024-03-03', amount: -300, payee_name: 'C', imported_id: 'm3' },
    ]);

    const result = await importRows(acct, [
      { date: '2024-03-01', amount: -100, payee_name: 'A', imported_id: 'm1' },
      { date: '2024-03-02', amount: -275, payee_name: 'B', imported_id: 'm2' },
      { date: '2024-03-03', amount: -300, payee_name: 'C', imported_id: 'm3' },
      { date: '2024-03-04', amount: -400, payee_name: 'D', imported_id: 'm4' },
    ]);
    expect(result.added).toHaveLength(1);

    const after = await getTransactions(acct);
    const byImportedId = Object.fromEntries(
      after.map(t => [t.imported_id, t.amount]),
    );
    expect(byImportedId).toEqual({ m1: -100, m2: -275, m3: -300, m4: -400 });
    expect(await balance(acct)).toBe(-100 - 275 - 300 - 400);
  });

  it('does not touch a reconciled (locked) transaction', async () => {
    const acct = await createAccount('Checking');
    await importRows(acct, [
      {
        date: '2024-02-14',
        amount: -6000,
        payee_name: 'Rent',
        imported_id: 'r1',
      },
    ]);
    const [original] = await getTransactions(acct);
    await editTransaction(original.id, { reconciled: true });

    const result = await importRows(acct, [
      {
        date: '2024-02-14',
        amount: -6500,
        payee_name: 'Rent',
        imported_id: 'r1',
      },
    ]);

    expect(result.added).toHaveLength(0);
    expect(result.updated).not.toContain(original.id);
    const after = await getTransactions(acct);
    expect(after).toHaveLength(1);
    expect(after[0].amount).toBe(-6000);
    expect(after[0].reconciled).toBe(true);
    expect(await balance(acct)).toBe(-6000);
  });

  it('leaves a split transaction and its parts unchanged, so the parts still add up', async () => {
    const acct = await createAccount('Checking');
    await importRows(acct, [
      {
        date: '2024-02-15',
        amount: -10000,
        payee_name: 'Supermarket',
        imported_id: 's1',
        subtransactions: [{ amount: -7000 }, { amount: -3000 }],
      },
    ]);
    expect(await liveParentRows(acct)).toHaveLength(1);

    await importRows(acct, [
      {
        date: '2024-02-15',
        amount: -12000,
        payee_name: 'Supermarket',
        imported_id: 's1',
      },
    ]);

    const parents = await liveParentRows(acct);
    expect(parents).toHaveLength(1);
    expect(parents[0].amount).toBe(-10000);
    const children = await liveLeafRows(acct);
    expect(children.map(c => c.amount)).toEqual([-7000, -3000]);
    expect(children.every(c => c.parent_id === parents[0].id)).toBe(true);
    expect(await balance(acct)).toBe(-10000);
  });

  it('keeps a transfer consistent: the other side follows the new amount', async () => {
    const checking = await createAccount('Checking');
    const savings = await createAccount('Savings');
    const payees = await handlers['api/payees-get']();
    const toSavings = payees.find(p => p.transfer_acct === savings);

    await importRows(checking, [
      {
        date: '2024-02-16',
        amount: -20000,
        payee_name: 'Xfer',
        imported_id: 't1',
      },
    ]);
    const [original] = await getTransactions(checking);
    // The user turns the imported transaction into a transfer to Savings.
    await editTransaction(original.id, { payee: toSavings.id });
    expect(await balance(savings)).toBe(20000);

    await importRows(checking, [
      {
        date: '2024-02-16',
        amount: -25000,
        payee_name: 'Xfer',
        imported_id: 't1',
      },
    ]);

    const src = await liveLeafRows(checking);
    const dst = await liveLeafRows(savings);
    expect(src).toHaveLength(1);
    expect(dst).toHaveLength(1);
    expect(src[0].amount).toBe(-25000);
    expect(dst[0].amount).toBe(25000);
    expect(src[0].transfer_id).toBe(dst[0].id);
    expect(dst[0].transfer_id).toBe(src[0].id);
    expect(await balance(checking)).toBe(-25000);
    expect(await balance(savings)).toBe(25000);
  });

  it('a preview reports the amount change as an update and writes nothing', async () => {
    const acct = await createAccount('Checking');
    await importRows(acct, [
      {
        date: '2024-02-17',
        amount: -700,
        payee_name: 'Books',
        imported_id: 'p1',
      },
    ]);

    const preview = await importRows(
      acct,
      [
        {
          date: '2024-02-17',
          amount: -750,
          payee_name: 'Books',
          imported_id: 'p1',
        },
      ],
      true,
    );

    expect(preview.errors).toEqual([]);
    expect(preview.added).toHaveLength(0);
    expect(preview.updatedPreview).toHaveLength(1);
    expect(preview.updatedPreview[0].ignored).toBeFalsy();
    expect(preview.updatedPreview[0].existing).toBeTruthy();

    const after = await getTransactions(acct);
    expect(after).toHaveLength(1);
    expect(after[0].amount).toBe(-700);
    expect(await balance(acct)).toBe(-700);
  });
});
