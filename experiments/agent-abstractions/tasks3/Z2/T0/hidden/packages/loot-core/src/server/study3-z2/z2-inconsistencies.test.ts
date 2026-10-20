// @ts-strict-ignore
// Study 3, zone Z2, step T0 (hidden): the behaviour a consolidation of the ranged
// schedule amount must keep (spec section 3). Today a schedule budget template halves
// the rounded sum of the range (a half unit can survive a percent adjustment until the
// template's final rounding), while posting the schedule rounds the midpoint. Driven
// through the budget and schedule handlers on a real database; nothing mocked
// (MockDate only fixes today's date).
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
  schedulesApp.startServices();
  MockDate.set(new Date(2024, 1, 1, 12));
  await db.insertAccount({ id: 'acct', name: 'Checking' });
});

afterEach(async () => {
  MockDate.reset();
  await schedulesApp.stopServices();
});

// A monthly expense on the 10th between -101.01 and -200.00: the sum is odd, so the
// midpoint is -150.505.
async function addRangedBill() {
  return schedulesApp.handlers['schedule/create']({
    schedule: { name: 'Bill' },
    conditions: [
      { op: 'is', field: 'account', value: 'acct' },
      {
        op: 'is',
        field: 'date',
        value: { start: '2024-02-10', frequency: 'monthly', patterns: [] },
      },
      { op: 'isbetween', field: 'amount', value: { num1: -10101, num2: -20000 } },
    ],
  });
}

describe('Z2 T0 a ranged amount keeps its current rounding', () => {
  it('a template with a percent adjustment halves the rounded sum, posting rounds the midpoint', async () => {
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
    const id = await addRangedBill();

    // -15050.5 * 1.1 = -16555.55 -> 16556 (the rounded midpoint would give 16555)
    const result = await budgetApp.handlers['budget/dry-run-category-template']({
      month: '2024-02',
      categoryId: 'c-bills',
      templates: [
        {
          type: 'schedule',
          name: 'Bill',
          directive: 'template',
          priority: 0,
          adjustment: 10,
          adjustmentType: 'percent',
        },
      ],
    });
    expect(result.budgeted).toBe(16556);

    await schedulesApp.handlers['schedule/post-transaction']({ id });
    const posted = await db.all('SELECT amount, schedule FROM v_transactions_internal');
    expect(posted).toEqual([{ amount: -15050, schedule: id }]);
  });
});
