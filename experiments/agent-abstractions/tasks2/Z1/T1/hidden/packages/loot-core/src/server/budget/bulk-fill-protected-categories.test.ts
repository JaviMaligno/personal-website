// @ts-strict-ignore
// Study 2, zone Z1, step T1 (hidden). The month-wide budget actions must leave
// alone hidden categories, categories in hidden groups and categories that have
// saved budget templates. One test per action, through the budget handlers.
import { app as budgetApp } from '#server/budget/app';
import * as budget from '#server/budget/base';
import * as db from '#server/db';
import * as sheet from '#server/sheet';

const MONTH = '2024-04';
const PREV = '2024-03';
const UNTOUCHED = 777;
const MONTHLY_SPEND = { groceries: 3000, rent: 9000, gym: 2500, archived: 1100 };
const PREV_BUDGET = { groceries: 1500, rent: 9500, gym: 2600, archived: 1200 };

async function settle() {
  // Some actions write per category asynchronously; let them land.
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
  await db.insertCategory({ id: 'rent', name: 'Rent', cat_group: 'g-living', is_income: 0 });
  await db.insertCategory({
    id: 'gym',
    name: 'Gym',
    cat_group: 'g-living',
    is_income: 0,
    hidden: 1,
  });
  await db.insertCategory({ id: 'archived', name: 'Old car', cat_group: 'g-archive', is_income: 0 });

  await sheet.loadSpreadsheet(db);
  await budget.createBudget(['2023-12', '2024-01', '2024-02', PREV, MONTH, '2024-05']);

  for (const date of ['2024-01-10', '2024-02-10', '2024-03-10']) {
    await db.insertTransaction({ date, amount: 500000, account: 'acct', category: 'salary' });
    for (const [category, spend] of Object.entries(MONTHLY_SPEND)) {
      await db.insertTransaction({ date, amount: -spend, account: 'acct', category });
    }
  }
  for (const [category, amount] of Object.entries(PREV_BUDGET)) {
    await budgetApp.handlers['budget/budget-amount']({ category, month: PREV, amount });
  }
  for (const category of Object.keys(MONTHLY_SPEND)) {
    await budgetApp.handlers['budget/budget-amount']({ category, month: MONTH, amount: UNTOUCHED });
  }
  await budgetApp.handlers['budget/set-category-automations']({
    categoriesWithTemplates: [
      {
        id: 'rent',
        templates: [{ type: 'simple', monthly: 95, directive: 'template', priority: 0 }],
      },
    ],
    source: 'ui',
  });
  await settle();
});

async function run(handler: string) {
  await budgetApp.handlers[handler]({ month: MONTH });
  await settle();
}

async function expectProtectedUntouched() {
  expect(await budgeted('rent')).toBe(UNTOUCHED); // has a saved template
  expect(await budgeted('gym')).toBe(UNTOUCHED); // hidden category
  expect(await budgeted('archived')).toBe(UNTOUCHED); // in a hidden group
}

describe('month-wide budget actions leave protected categories alone', () => {
  it('copying last month', async () => {
    await run('budget/copy-previous-month');
    expect(await budgeted('groceries')).toBe(PREV_BUDGET.groceries);
    await expectProtectedUntouched();
  });

  it('setting budgets to zero', async () => {
    await run('budget/set-zero');
    expect(await budgeted('groceries')).toBe(0);
    await expectProtectedUntouched();
  });

  it('three-month average', async () => {
    await run('budget/set-3month-avg');
    expect(await budgeted('groceries')).toBe(MONTHLY_SPEND.groceries);
    await expectProtectedUntouched();
  });

  it('six-month average', async () => {
    await run('budget/set-6month-avg');
    expect(await budgeted('groceries')).toBe(MONTHLY_SPEND.groceries);
    await expectProtectedUntouched();
  });

  it('twelve-month average', async () => {
    await run('budget/set-12month-avg');
    expect(await budgeted('groceries')).toBe(MONTHLY_SPEND.groceries);
    await expectProtectedUntouched();
  });
});
