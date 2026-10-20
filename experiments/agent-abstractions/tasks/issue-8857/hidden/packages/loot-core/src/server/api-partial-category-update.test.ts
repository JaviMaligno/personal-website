// @ts-strict-ignore
import * as db from '#server/db';
import * as sheet from '#server/sheet';
import { setSyncingMode } from '#server/sync';
import type { ServerHandlers } from '#types/server-handlers';

import { installAPI } from './api';
import { app as budgetApp } from './budget/app';
import * as prefs from './prefs';

// Partial updates of categories and category groups through the public API:
// only the fields that are passed may change, everything else (and in
// particular the name) must be left exactly as it was, both in the stored row
// and in the changes recorded for sync.

type Row = {
  id: string;
  name: string;
  is_income: number;
  hidden: number;
  cat_group?: string;
  tombstone: number;
};

async function categoryRow(id: string): Promise<Row> {
  return db.first<Row>(
    'SELECT id, name, is_income, hidden, cat_group, tombstone FROM categories WHERE id = ?',
    [id],
  );
}

async function groupRow(id: string): Promise<Row> {
  return db.first<Row>(
    'SELECT id, name, is_income, hidden, tombstone FROM category_groups WHERE id = ?',
    [id],
  );
}

async function syncedColumns(dataset: string, row: string, after: string) {
  const rows = await db.all<{ column: string }>(
    'SELECT column FROM messages_crdt WHERE dataset = ? AND row = ? AND timestamp > ?',
    [dataset, row, after],
  );
  return [...new Set(rows.map(r => r.column))].sort();
}

async function lastTimestamp(): Promise<string> {
  const row = await db.first<{ ts: string | null }>(
    'SELECT MAX(timestamp) AS ts FROM messages_crdt',
  );
  return row?.ts ?? '';
}

describe('API partial category updates', () => {
  const handlers = installAPI({} as unknown as ServerHandlers);

  let expenseGroup: string;
  let otherGroup: string;
  let incomeGroup: string;
  let groceries: string;
  let salary: string;

  beforeEach(global.emptyDatabase());

  beforeEach(async () => {
    await sheet.loadSpreadsheet(db);
    await prefs.loadPrefs();

    for (const name of [
      'category-create',
      'category-update',
      'get-categories',
      'category-group-create',
      'category-group-update',
      'get-category-groups',
    ]) {
      handlers[name] = budgetApp.handlers[name];
    }

    // Record changes for sync locally (no sync server involved).
    setSyncingMode('offline');

    expenseGroup = await handlers['category-group-create']({
      name: 'Bills',
    });
    otherGroup = await handlers['category-group-create']({
      name: 'Everyday',
      hidden: true,
    });
    incomeGroup = await handlers['category-group-create']({
      name: 'Earnings',
      isIncome: true,
    });
    groceries = await handlers['category-create']({
      name: 'Groceries',
      groupId: expenseGroup,
      hidden: true,
    });
    salary = await handlers['category-create']({
      name: 'Salary',
      groupId: incomeGroup,
      isIncome: true,
    });
  });

  afterEach(() => {
    setSyncingMode('disabled');
  });

  it('moves a category to another group without passing its name', async () => {
    const before = await lastTimestamp();
    global.stepForwardInTime();

    await handlers['api/category-update']({
      id: groceries,
      fields: { group_id: otherGroup },
    });

    expect(await categoryRow(groceries)).toEqual({
      id: groceries,
      name: 'Groceries',
      is_income: 0,
      hidden: 1,
      cat_group: otherGroup,
      tombstone: 0,
    });

    const categories = await handlers['api/categories-get']({});
    expect(categories.find(c => c.id === groceries)).toMatchObject({
      name: 'Groceries',
      group_id: otherGroup,
      hidden: true,
      is_income: false,
    });

    expect(await syncedColumns('categories', groceries, before)).toEqual([
      'cat_group',
    ]);
  });

  it('changes only the hidden flag of a category', async () => {
    // A stored setting the request does not mention must survive the update.
    db.runQuery('UPDATE categories SET template_settings = ? WHERE id = ?', [
      '{"source":"ui"}',
      groceries,
    ]);
    const before = await lastTimestamp();
    global.stepForwardInTime();

    await handlers['api/category-update']({
      id: groceries,
      fields: { hidden: false },
    });

    expect(await categoryRow(groceries)).toEqual({
      id: groceries,
      name: 'Groceries',
      is_income: 0,
      hidden: 0,
      cat_group: expenseGroup,
      tombstone: 0,
    });
    const settings = await db.first<{ template_settings: string }>(
      'SELECT template_settings FROM categories WHERE id = ?',
      [groceries],
    );
    expect(JSON.parse(settings.template_settings)).toEqual({ source: 'ui' });
    expect(await syncedColumns('categories', groceries, before)).toEqual([
      'hidden',
    ]);
  });

  it('keeps an income category an income category when hiding it', async () => {
    const before = await lastTimestamp();
    global.stepForwardInTime();

    await handlers['api/category-update']({
      id: salary,
      fields: { hidden: true },
    });

    expect(await categoryRow(salary)).toEqual({
      id: salary,
      name: 'Salary',
      is_income: 1,
      hidden: 1,
      cat_group: incomeGroup,
      tombstone: 0,
    });
    expect(await syncedColumns('categories', salary, before)).toEqual([
      'hidden',
    ]);
  });

  it('still renames a category, trimming the new name', async () => {
    await handlers['api/category-update']({
      id: groceries,
      fields: { name: '  Food  ' },
    });

    expect(await categoryRow(groceries)).toEqual({
      id: groceries,
      name: 'Food',
      is_income: 0,
      hidden: 1,
      cat_group: expenseGroup,
      tombstone: 0,
    });
  });

  it('changes only the hidden flag of a category group', async () => {
    const before = await lastTimestamp();
    global.stepForwardInTime();

    await handlers['api/category-group-update']({
      id: incomeGroup,
      fields: { hidden: true },
    });

    expect(await groupRow(incomeGroup)).toEqual({
      id: incomeGroup,
      name: 'Earnings',
      is_income: 1,
      hidden: 1,
      tombstone: 0,
    });

    const groups = await handlers['api/category-groups-get']({});
    expect(groups.find(g => g.id === incomeGroup)).toMatchObject({
      name: 'Earnings',
      is_income: true,
      hidden: true,
    });

    expect(await syncedColumns('category_groups', incomeGroup, before)).toEqual(
      ['hidden'],
    );
  });

  it('still rejects renaming a category group to an existing group name', async () => {
    await expect(
      handlers['api/category-group-update']({
        id: expenseGroup,
        fields: { name: 'everyday' },
      }),
    ).rejects.toThrow();

    expect(await groupRow(expenseGroup)).toMatchObject({ name: 'Bills' });
  });
});
