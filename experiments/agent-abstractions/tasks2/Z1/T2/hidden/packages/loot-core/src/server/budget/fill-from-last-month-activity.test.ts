// @ts-strict-ignore
// Study 2, zone Z1, step T2 (hidden). New month-wide action: budget each category
// at what it spent (or, for income, received) in the previous month, over the same
// categories the other month-wide actions fill. Through the budget handlers.
import { app as budgetApp } from '#server/budget/app';
import * as budget from '#server/budget/base';
import * as db from '#server/db';
import * as sheet from '#server/sheet';

const HANDLER = 'budget/set-last-month-spending';
const MONTH = '2024-04';
const UNTOUCHED = 777;
// Spending per month (Jan, Feb, Mar): last month differs from any average.
const SPEND = {
  groceries: [1000, 2000, 3000],
  books: [400, 600, 0],
  rent: [9000, 9000, 9000],
  gym: [2500, 2500, 2500],
  archived: [1100, 1100, 1100],
};
const SALARY = [480000, 490000, 510000];

async function settle() {
  for (let i = 0; i < 5; i++) {
    await new Promise(r => setTimeout(r, 20));
    await sheet.waitOnSpreadsheet();
  }
}

let tracking = false;

async function budgeted(category: string) {
  const table = tracking ? 'reflect_budgets' : 'zero_budgets';
  const row = await db.first<{ amount: number }>(
    `SELECT amount FROM ${table} WHERE month = ? AND category = ?`,
    [parseInt(MONTH.replace('-', '')), category],
  );
  return row ? row.amount : null;
}

async function setup(budgetType: 'envelope' | 'tracking') {
  tracking = budgetType === 'tracking';
  await global.emptyDatabase()();
  global.currentMonth = '2024-05';
  if (tracking) {
    await db.runQuery(
      `INSERT INTO preferences (id, value) VALUES ('budgetType', 'tracking')`,
    );
  }
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
  await db.insertCategory({ id: 'books', name: 'Books', cat_group: 'g-living', is_income: 0 });
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
  if (tracking) {
    sheet.get().meta().budgetType = 'tracking';
  }
  await budget.createBudget(['2023-12', '2024-01', '2024-02', '2024-03', MONTH, '2024-05']);

  const dates = ['2024-01-10', '2024-02-10', '2024-03-10'];
  for (let m = 0; m < dates.length; m++) {
    await db.insertTransaction({ date: dates[m], amount: SALARY[m], account: 'acct', category: 'salary' });
    for (const [category, spend] of Object.entries(SPEND)) {
      if (spend[m] !== 0) {
        await db.insertTransaction({ date: dates[m], amount: -spend[m], account: 'acct', category });
      }
    }
  }
  for (const category of ['salary', ...Object.keys(SPEND)]) {
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
}

async function run() {
  await budgetApp.handlers[HANDLER]({ month: MONTH });
  await settle();
}

describe('budget at last month spending', () => {
  it('budgets what each category spent in the previous month', async () => {
    await setup('envelope');
    await run();
    expect(await budgeted('groceries')).toBe(3000);
    expect(await budgeted('books')).toBe(0);
  });

  it('fills the same categories as the other month-wide actions', async () => {
    await setup('envelope');
    await run();
    expect(await budgeted('groceries')).toBe(3000);
    expect(await budgeted('rent')).toBe(UNTOUCHED); // has a saved template
    expect(await budgeted('gym')).toBe(UNTOUCHED); // hidden category
    expect(await budgeted('archived')).toBe(UNTOUCHED); // in a hidden group
    expect(await budgeted('salary')).toBe(UNTOUCHED); // income, envelope budget
  });

  it('budgets last month income in a tracking budget', async () => {
    await setup('tracking');
    await run();
    expect(await budgeted('salary')).toBe(SALARY[2]);
    expect(await budgeted('groceries')).toBe(3000);
    expect(await budgeted('rent')).toBe(UNTOUCHED);
  });
});
