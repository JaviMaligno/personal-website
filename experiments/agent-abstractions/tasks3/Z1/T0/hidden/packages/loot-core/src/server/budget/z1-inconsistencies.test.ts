// @ts-strict-ignore
// Study 3, zone Z1, step T0 (hidden): the behaviour a consolidation of the
// month-wide budget actions must keep (spec section 3). Today, setting a month's
// budgets to zero also writes hidden categories and categories in hidden groups,
// while copying last month leaves them alone. Driven through the budget handlers on
// a real database; nothing mocked. No category belongs to a missing group.
import { app as budgetApp } from '#server/budget/app';
import * as budget from '#server/budget/base';
import * as db from '#server/db';
import * as sheet from '#server/sheet';

const MONTH = '2024-04';
const PREV = '2024-03';
const UNTOUCHED = 777;
const PREV_BUDGET = { groceries: 1500, gym: 2600, archived: 1200 };

async function settle() {
  for (let i = 0; i < 5; i++) {
    await new Promise(r => setTimeout(r, 20));
    await sheet.waitOnSpreadsheet();
  }
}

async function budgeted(category: string) {
  const row = await db.first<{ amount: number }>(
    'SELECT amount FROM zero_budgets WHERE month = ? AND category = ?',
    [parseInt(MONTH.replace('-', '')), category],
  );
  return row ? row.amount : null;
}

async function setMonth(amount: number) {
  for (const category of Object.keys(PREV_BUDGET)) {
    await budgetApp.handlers['budget/budget-amount']({ category, month: MONTH, amount });
  }
  await settle();
}

beforeEach(async () => {
  await global.emptyDatabase()();
  global.currentMonth = '2024-05';
  await db.insertAccount({ id: 'acct', name: 'Checking' });
  await db.insertCategoryGroup({ id: 'g-income', name: 'Income', is_income: 1 });
  await db.insertCategoryGroup({ id: 'g-living', name: 'Living', is_income: 0 });
  await db.insertCategoryGroup({
    id: 'g-archive',
    name: 'Archive',
    is_income: 0,
    hidden: 1,
  });
  await db.insertCategory({
    id: 'salary',
    name: 'Salary',
    cat_group: 'g-income',
    is_income: 1,
  });
  await db.insertCategory({ id: 'groceries', name: 'Groceries', cat_group: 'g-living', is_income: 0 });
  await db.insertCategory({
    id: 'gym',
    name: 'Gym',
    cat_group: 'g-living',
    is_income: 0,
    hidden: 1,
  });
  await db.insertCategory({ id: 'archived', name: 'Old car', cat_group: 'g-archive', is_income: 0 });

  await sheet.loadSpreadsheet(db);
  await budget.createBudget(['2024-01', '2024-02', PREV, MONTH, '2024-05']);
  for (const [category, amount] of Object.entries(PREV_BUDGET)) {
    await budgetApp.handlers['budget/budget-amount']({ category, month: PREV, amount });
  }
  await setMonth(UNTOUCHED);
});

describe('Z1 T0 month-wide budget actions keep their current category selection', () => {
  it('setting budgets to zero writes hidden categories and hidden groups, copying last month does not', async () => {
    await budgetApp.handlers['budget/set-zero']({ month: MONTH });
    await settle();
    expect(await budgeted('groceries')).toBe(0);
    expect(await budgeted('gym')).toBe(0); // hidden category
    expect(await budgeted('archived')).toBe(0); // in a hidden group

    await setMonth(UNTOUCHED);
    await budgetApp.handlers['budget/copy-previous-month']({ month: MONTH });
    await settle();
    expect(await budgeted('groceries')).toBe(PREV_BUDGET.groceries);
    expect(await budgeted('gym')).toBe(UNTOUCHED);
    expect(await budgeted('archived')).toBe(UNTOUCHED);
  });
});
