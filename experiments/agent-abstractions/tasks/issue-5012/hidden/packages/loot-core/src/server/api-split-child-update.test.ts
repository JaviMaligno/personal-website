// @ts-strict-ignore
import * as db from '#server/db';

import { handlers } from './main';
import { runHandler } from './mutators';
import * as prefs from './prefs';
import * as sheet from './sheet';

vi.mock('./post');

type Setup = {
  accountId: string;
  groceries: string;
  household: string;
  fuel: string;
};

async function setup(): Promise<Setup> {
  await sheet.loadSpreadsheet(db);
  await prefs.loadPrefs();

  const accountId = await runHandler(handlers['api/account-create'], {
    account: { name: 'Checking' },
  });
  const groupId = await runHandler(handlers['api/category-group-create'], {
    group: { name: 'Spending' },
  });
  const groceries = await runHandler(handlers['api/category-create'], {
    category: { name: 'Groceries', group_id: groupId },
  });
  const household = await runHandler(handlers['api/category-create'], {
    category: { name: 'Household', group_id: groupId },
  });
  const fuel = await runHandler(handlers['api/category-create'], {
    category: { name: 'Fuel', group_id: groupId },
  });
  return { accountId, groceries, household, fuel };
}

async function addSplit(s: Setup) {
  await runHandler(handlers['api/transactions-add'], {
    accountId: s.accountId,
    transactions: [
      {
        date: '2025-05-10',
        amount: -10000,
        notes: 'Weekly shop',
        subtransactions: [
          { amount: -6000, category: s.groceries, notes: 'food' },
          { amount: -4000, category: s.household, notes: 'cleaning' },
        ],
      },
    ],
  });
  const txns = await runHandler(handlers['api/transactions-get'], {
    accountId: s.accountId,
  });
  expect(txns).toHaveLength(1);
  const parent = txns[0];
  expect(parent.subtransactions).toHaveLength(2);
  const food = parent.subtransactions.find(t => t.amount === -6000);
  const cleaning = parent.subtransactions.find(t => t.amount === -4000);
  return { parentId: parent.id, foodId: food.id, cleaningId: cleaning.id };
}

async function stored(id: string) {
  return db.first<{
    amount: number;
    category: string | null;
    notes: string | null;
    isParent: number;
    isChild: number;
    parent_id: string | null;
    tombstone: number;
  }>(
    'SELECT amount, category, notes, isParent, isChild, parent_id, tombstone FROM transactions WHERE id = ?',
    [id],
  );
}

async function liveChildren(parentId: string) {
  return db.all<{ id: string; amount: number }>(
    'SELECT id, amount FROM transactions WHERE parent_id = ? AND isChild = 1 AND tombstone = 0',
    [parentId],
  );
}

async function getSplit(accountId: string, parentId: string) {
  const txns = await runHandler(handlers['api/transactions-get'], {
    accountId,
  });
  return txns.find(t => t.id === parentId);
}

describe('API: updating one part of a split transaction', () => {
  beforeEach(global.emptyDatabase());

  afterEach(() => {
    prefs.unloadPrefs();
  });

  it('changing only the notes of a split part keeps its amount and category', async () => {
    const s = await setup();
    const { parentId, foodId, cleaningId } = await addSplit(s);

    await runHandler(handlers['api/transaction-update'], {
      id: foodId,
      fields: { notes: 'New notes' },
    });

    const food = await stored(foodId);
    expect(food).toMatchObject({
      amount: -6000,
      category: s.groceries,
      notes: 'New notes',
      isChild: 1,
      parent_id: parentId,
      tombstone: 0,
    });

    // The other part and the parent are left alone.
    expect(await stored(cleaningId)).toMatchObject({
      amount: -4000,
      category: s.household,
      notes: 'cleaning',
      tombstone: 0,
    });
    expect(await stored(parentId)).toMatchObject({
      amount: -10000,
      isParent: 1,
      notes: 'Weekly shop',
      tombstone: 0,
    });

    // The split still adds up and still has exactly its two parts.
    const children = await liveChildren(parentId);
    expect(children.map(c => c.id).sort()).toEqual([foodId, cleaningId].sort());
    expect(children.reduce((sum, c) => sum + c.amount, 0)).toBe(-10000);

    // And the API reads it back the same way.
    const split = await getSplit(s.accountId, parentId);
    expect(split.amount).toBe(-10000);
    const apiFood = split.subtransactions.find(t => t.id === foodId);
    expect(apiFood).toMatchObject({
      amount: -6000,
      category: s.groceries,
      notes: 'New notes',
    });
  });

  it('changing only the category of a split part keeps its amount and notes', async () => {
    const s = await setup();
    const { parentId, foodId, cleaningId } = await addSplit(s);

    await runHandler(handlers['api/transaction-update'], {
      id: cleaningId,
      fields: { category: s.fuel },
    });

    expect(await stored(cleaningId)).toMatchObject({
      amount: -4000,
      category: s.fuel,
      notes: 'cleaning',
      parent_id: parentId,
      tombstone: 0,
    });
    expect(await stored(foodId)).toMatchObject({
      amount: -6000,
      category: s.groceries,
      notes: 'food',
      tombstone: 0,
    });
    expect((await stored(parentId)).amount).toBe(-10000);

    const children = await liveChildren(parentId);
    expect(children).toHaveLength(2);
    expect(children.reduce((sum, c) => sum + c.amount, 0)).toBe(-10000);
  });

  it('successive partial updates of a split part accumulate', async () => {
    const s = await setup();
    const { parentId, foodId } = await addSplit(s);

    await runHandler(handlers['api/transaction-update'], {
      id: foodId,
      fields: { notes: 'first' },
    });
    await runHandler(handlers['api/transaction-update'], {
      id: foodId,
      fields: { category: s.fuel },
    });

    expect(await stored(foodId)).toMatchObject({
      amount: -6000,
      category: s.fuel,
      notes: 'first',
      tombstone: 0,
    });
    const children = await liveChildren(parentId);
    expect(children).toHaveLength(2);
    expect(children.reduce((sum, c) => sum + c.amount, 0)).toBe(-10000);
  });
});
