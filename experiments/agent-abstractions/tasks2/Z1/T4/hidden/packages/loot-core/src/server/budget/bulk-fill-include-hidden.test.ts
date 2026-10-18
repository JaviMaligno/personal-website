// @ts-strict-ignore
// Study 2, zone Z1, step T4 (hidden). Each month-wide budget action accepts an
// opt-in to include hidden categories and categories in hidden groups; the other
// exclusions (saved templates, #fixed groups) still apply. One test per action,
// through the budget handlers.
import { app as budgetApp } from '#server/budget/app';
import * as budget from '#server/budget/base';
import * as db from '#server/db';
import { app as notesApp } from '#server/notes/app';
import * as sheet from '#server/sheet';

const MONTH = '2024-04';
const PREV = '2024-03';
const UNTOUCHED = 777;
const MONTHLY_SPEND = {
  groceries: 3000,
  rent: 9000,
  gym: 2500,
  archived: 1100,
  mortgage: 15000,
};
const PREV_BUDGET = {
  groceries: 1500,
  rent: 9500,
  gym: 2600,
  archived: 1200,
  mortgage: 15500,
};

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
  await db.insertCategoryGroup({ id: 'g-loans', name: 'Loans', is_income: 0 });
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
  await db.insertCategory({ id: 'mortgage', name: 'Mortgage', cat_group: 'g-loans', is_income: 0 });

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
  await notesApp.handlers['notes-save']({ id: 'g-living', note: 'Day to day costs' });
  await notesApp.handlers['notes-save']({ id: 'g-loans', note: 'Loan repayments #fixed' });
  await settle();
});

async function run(handler: string) {
  await budgetApp.handlers[handler]({ month: MONTH, includeHiddenCategories: true });
  await settle();
}

describe('month-wide budget actions can include hidden categories', () => {
  for (const [label, handler, expected] of [
    ['copying last month', 'budget/copy-previous-month', PREV_BUDGET],
    [
      'setting budgets to zero',
      'budget/set-zero',
      { groceries: 0, gym: 0, archived: 0 },
    ],
    ['three-month average', 'budget/set-3month-avg', MONTHLY_SPEND],
    ['six-month average', 'budget/set-6month-avg', MONTHLY_SPEND],
    ['twelve-month average', 'budget/set-12month-avg', MONTHLY_SPEND],
    ['last month spending', 'budget/set-last-month-spending', MONTHLY_SPEND],
  ] as const) {
    it(label, async () => {
      await run(handler);
      expect(await budgeted('groceries')).toBe(expected.groceries);
      expect(await budgeted('gym')).toBe(expected.gym); // hidden category
      expect(await budgeted('archived')).toBe(expected.archived); // hidden group
      expect(await budgeted('rent')).toBe(UNTOUCHED); // has a saved template
      expect(await budgeted('mortgage')).toBe(UNTOUCHED); // group tagged #fixed
    });
  }
});
