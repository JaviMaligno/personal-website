// @ts-strict-ignore
// Study 2, zone Z2, step T4: hidden behavioural test for one consumer
// (budget-template). Written from the step statement; real database, nothing mocked.

import MockDate from 'mockdate';

import { app as budgetApp } from '#server/budget/app';
import { createAllBudgets } from '#server/budget/base';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import * as prefs from '#server/prefs';
import { app as schedulesApp } from '#server/schedules/app';
import * as sheet from '#server/sheet';
import { loadRules } from '#server/transactions/transaction-rules';

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
  // keeps the schedules view's amount/account/date columns in sync with rules
  schedulesApp.startServices();
  MockDate.set(new Date(2024, 1, 1, 12));
  await db.insertAccount({ id: 'acct', name: 'Checking' });
});

afterEach(async () => {
  MockDate.reset();
  await schedulesApp.stopServices();
});

// A monthly schedule on the 10th, first occurrence 2024-02-10.
async function addSchedule(name: string, amountCondition) {
  return schedulesApp.handlers['schedule/create']({
    schedule: { name },
    conditions: [
      { op: 'is', field: 'account', value: 'acct' },
      {
        op: 'is',
        field: 'date',
        value: { start: '2024-02-10', frequency: 'monthly', patterns: [] },
      },
      ...(amountCondition ? [{ field: 'amount', ...amountCondition }] : []),
    ],
  });
}

describe('Z2 T4 schedule budget templates', () => {
  it('a ranged income is expected at its lowest value', async () => {
    await prefs.loadPrefs();
    await sheet.loadSpreadsheet(db);
    await db.insertCategoryGroup({ id: 'g-bills', name: 'Bills' });
    await db.insertCategory({ id: 'c-bills', name: 'Utilities', cat_group: 'g-bills' });
    await db.insertCategoryGroup({ id: 'g-income', name: 'Income', is_income: 1 });
    await db.insertCategory({
      id: 'c-income',
      name: 'Salary',
      cat_group: 'g-income',
      is_income: 1,
    });
    await createAllBudgets();
    await addSchedule('Bill', { op: 'isbetween', value: {num1: 10100, num2: 20000} });
    const expected = 10100;
    // money in is budgeted in an income category, money out in an expense one
    const categoryId = expected > 0 ? 'c-income' : 'c-bills';
    const result = await budgetApp.handlers['budget/dry-run-category-template']({
      month: '2024-02',
      categoryId,
      templates: [
        { type: 'schedule', name: 'Bill', directive: 'template', priority: 0 },
      ],
    });
    expect(result.budgeted).toBe(Math.abs(expected));
  });

  it('an approximate income is expected at the low end of its tolerance', async () => {
    await prefs.loadPrefs();
    await sheet.loadSpreadsheet(db);
    await db.insertCategoryGroup({ id: 'g-bills', name: 'Bills' });
    await db.insertCategory({ id: 'c-bills', name: 'Utilities', cat_group: 'g-bills' });
    await db.insertCategoryGroup({ id: 'g-income', name: 'Income', is_income: 1 });
    await db.insertCategory({
      id: 'c-income',
      name: 'Salary',
      cat_group: 'g-income',
      is_income: 1,
    });
    await createAllBudgets();
    await addSchedule('Bill', { op: 'isapprox', value: 10000 });
    const expected = 9250;
    // money in is budgeted in an income category, money out in an expense one
    const categoryId = expected > 0 ? 'c-income' : 'c-bills';
    const result = await budgetApp.handlers['budget/dry-run-category-template']({
      month: '2024-02',
      categoryId,
      templates: [
        { type: 'schedule', name: 'Bill', directive: 'template', priority: 0 },
      ],
    });
    expect(result.budgeted).toBe(Math.abs(expected));
  });

  it('a range spanning zero is expected at its negative end', async () => {
    await prefs.loadPrefs();
    await sheet.loadSpreadsheet(db);
    await db.insertCategoryGroup({ id: 'g-bills', name: 'Bills' });
    await db.insertCategory({ id: 'c-bills', name: 'Utilities', cat_group: 'g-bills' });
    await db.insertCategoryGroup({ id: 'g-income', name: 'Income', is_income: 1 });
    await db.insertCategory({
      id: 'c-income',
      name: 'Salary',
      cat_group: 'g-income',
      is_income: 1,
    });
    await createAllBudgets();
    await addSchedule('Bill', { op: 'isbetween', value: {num1: 5000, num2: -3000} });
    const expected = -3000;
    // money in is budgeted in an income category, money out in an expense one
    const categoryId = expected > 0 ? 'c-income' : 'c-bills';
    const result = await budgetApp.handlers['budget/dry-run-category-template']({
      month: '2024-02',
      categoryId,
      templates: [
        { type: 'schedule', name: 'Bill', directive: 'template', priority: 0 },
      ],
    });
    expect(result.budgeted).toBe(Math.abs(expected));
  });

  it('a ranged expense is still expected at the end furthest from zero', async () => {
    await prefs.loadPrefs();
    await sheet.loadSpreadsheet(db);
    await db.insertCategoryGroup({ id: 'g-bills', name: 'Bills' });
    await db.insertCategory({ id: 'c-bills', name: 'Utilities', cat_group: 'g-bills' });
    await db.insertCategoryGroup({ id: 'g-income', name: 'Income', is_income: 1 });
    await db.insertCategory({
      id: 'c-income',
      name: 'Salary',
      cat_group: 'g-income',
      is_income: 1,
    });
    await createAllBudgets();
    await addSchedule('Bill', { op: 'isbetween', value: {num1: -20000, num2: -10100} });
    const expected = -20000;
    // money in is budgeted in an income category, money out in an expense one
    const categoryId = expected > 0 ? 'c-income' : 'c-bills';
    const result = await budgetApp.handlers['budget/dry-run-category-template']({
      month: '2024-02',
      categoryId,
      templates: [
        { type: 'schedule', name: 'Bill', directive: 'template', priority: 0 },
      ],
    });
    expect(result.budgeted).toBe(Math.abs(expected));
  });
});
