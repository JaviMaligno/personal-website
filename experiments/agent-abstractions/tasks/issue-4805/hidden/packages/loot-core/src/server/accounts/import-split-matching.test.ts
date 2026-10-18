// @ts-strict-ignore
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { app as transactionsApp } from '#server/transactions/app';
import { loadRules } from '#server/transactions/transaction-rules';

import { app as accountsApp } from './app';

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
});

async function createAccount() {
  return accountsApp.handlers['account-create']({ name: 'Checking' });
}

function importTransactions(accountId, transactions) {
  return accountsApp.handlers['transactions-import']({
    accountId,
    transactions,
    isPreview: false,
  });
}

// Every live row of the account, parents, children and plain transactions.
function getRows(accountId) {
  return db.all<{
    id: string;
    amount: number;
    date: number;
    imported_id: string | null;
    notes: string | null;
    payee: string | null;
    is_parent: number;
    is_child: number;
    parent_id: string | null;
  }>(
    `SELECT id, amount, date, imported_id, notes, payee, is_parent, is_child, parent_id
       FROM v_transactions_internal
      WHERE account = ? AND tombstone = 0
      ORDER BY id`,
    [accountId],
  );
}

// Balance as the account shows it: children are already counted by their parent.
async function getBalance(accountId) {
  const rows = await getRows(accountId);
  return rows.filter(r => !r.is_child).reduce((s, r) => s + r.amount, 0);
}

// Imports a single transaction, then splits it into the given child amounts,
// the way the transaction editor does it (children carry no imported_id).
async function importAndSplit(accountId, transaction, childAmounts) {
  const res = await importTransactions(accountId, [transaction]);
  expect(res.errors).toEqual([]);
  expect(res.added).toHaveLength(1);
  const parentId = res.added[0];

  const children = childAmounts.map((amount, idx) => ({
    id: `${parentId}-child-${idx}`,
    account: accountId,
    date: transaction.date,
    amount,
    is_child: true,
    parent_id: parentId,
    sort_order: -idx,
  }));
  await transactionsApp.handlers['transactions-batch-update']({
    updated: [{ id: parentId, is_parent: true, category: null }],
    added: children,
  });

  const rows = await getRows(accountId);
  expect(rows.filter(r => r.parent_id === parentId)).toHaveLength(
    childAmounts.length,
  );
  return { parentId, childIds: children.map(c => c.id) };
}

describe('importing next to existing split transactions', () => {
  test('a new imported transaction is not merged into a child of an already-imported split', async () => {
    const accountId = await createAccount();
    const { parentId, childIds } = await importAndSplit(
      accountId,
      {
        date: '2024-03-01',
        amount: -1800,
        payee_name: 'Grocery Store',
        imported_id: 'bank-A',
        notes: 'weekly shop',
      },
      [-900, -900],
    );

    const childrenBefore = (await getRows(accountId)).filter(r =>
      childIds.includes(r.id),
    );
    expect(await getBalance(accountId)).toBe(-1800);

    const res = await importTransactions(accountId, [
      {
        date: '2024-03-04',
        amount: -900,
        payee_name: 'Coffee Shop',
        imported_id: 'bank-B',
        notes: 'beans',
      },
    ]);
    expect(res.errors).toEqual([]);
    expect(res.added).toHaveLength(1);
    expect(res.updated).toHaveLength(0);

    const rows = await getRows(accountId);
    // The new money is in the account.
    expect(await getBalance(accountId)).toBe(-2700);

    const added = rows.find(r => r.id === res.added[0]);
    expect(added).toBeDefined();
    expect(added.is_child).toBe(0);
    expect(added.parent_id).toBeNull();
    expect(added.amount).toBe(-900);
    expect(added.imported_id).toBe('bank-B');
    expect(added.notes).toBe('beans');

    // The split is untouched.
    const parent = rows.find(r => r.id === parentId);
    expect(parent.imported_id).toBe('bank-A');
    expect(parent.amount).toBe(-1800);
    const childrenAfter = rows.filter(r => childIds.includes(r.id));
    expect(childrenAfter).toEqual(childrenBefore);
    expect(rows.filter(r => r.imported_id === 'bank-B')).toHaveLength(1);
  });

  test('importing several transactions equal to the split children adds them all', async () => {
    const accountId = await createAccount();
    const { childIds } = await importAndSplit(
      accountId,
      {
        date: '2024-05-10',
        amount: -1000,
        payee_name: 'Hardware Store',
        imported_id: 'bank-P',
      },
      [-400, -600],
    );

    const res = await importTransactions(accountId, [
      {
        date: '2024-05-11',
        amount: -400,
        payee_name: 'Bakery',
        imported_id: 'bank-Q',
      },
      {
        date: '2024-05-12',
        amount: -600,
        payee_name: 'Pharmacy',
        imported_id: 'bank-R',
      },
    ]);
    expect(res.errors).toEqual([]);
    expect(res.added).toHaveLength(2);
    expect(res.updated).toHaveLength(0);

    const rows = await getRows(accountId);
    expect(await getBalance(accountId)).toBe(-2000);
    for (const child of rows.filter(r => childIds.includes(r.id))) {
      expect(child.imported_id).toBeNull();
    }
  });

  test('a transaction equal to the whole split still matches the split itself', async () => {
    const accountId = await createAccount();
    // A split entered by hand (no imported id), later confirmed by an import.
    const parentId = 'manual-split';
    await transactionsApp.handlers['transactions-batch-update']({
      added: [
        {
          id: parentId,
          account: accountId,
          date: '2024-07-02',
          amount: -2500,
          is_parent: true,
        },
        {
          id: 'manual-split-c0',
          account: accountId,
          date: '2024-07-02',
          amount: -1000,
          is_child: true,
          parent_id: parentId,
          sort_order: 0,
        },
        {
          id: 'manual-split-c1',
          account: accountId,
          date: '2024-07-02',
          amount: -1500,
          is_child: true,
          parent_id: parentId,
          sort_order: -1,
        },
      ],
    });
    expect(await getBalance(accountId)).toBe(-2500);

    const res = await importTransactions(accountId, [
      {
        date: '2024-07-03',
        amount: -2500,
        payee_name: 'Department Store',
        imported_id: 'bank-X',
      },
    ]);
    expect(res.errors).toEqual([]);
    expect(res.added).toHaveLength(0);
    expect(res.updated).toContain(parentId);

    const rows = await getRows(accountId);
    expect(await getBalance(accountId)).toBe(-2500);
    expect(rows.find(r => r.id === parentId).imported_id).toBe('bank-X');
    expect(rows.filter(r => r.is_child)).toHaveLength(2);
  });

  test('a plain transaction entered by hand is still matched by an import', async () => {
    const accountId = await createAccount();
    await transactionsApp.handlers['transactions-batch-update']({
      added: [
        {
          id: 'manual-plain',
          account: accountId,
          date: '2024-08-20',
          amount: -900,
          notes: 'typed in',
        },
      ],
    });

    const res = await importTransactions(accountId, [
      {
        date: '2024-08-21',
        amount: -900,
        payee_name: 'Coffee Shop',
        imported_id: 'bank-Y',
      },
    ]);
    expect(res.errors).toEqual([]);
    expect(res.added).toHaveLength(0);
    expect(res.updated).toContain('manual-plain');

    const rows = await getRows(accountId);
    expect(rows).toHaveLength(1);
    expect(rows[0].imported_id).toBe('bank-Y');
    expect(rows[0].notes).toBe('typed in');
    expect(await getBalance(accountId)).toBe(-900);
  });
});
