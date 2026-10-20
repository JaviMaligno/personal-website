// @ts-strict-ignore
// Study 2, zone Z4, step T4 (hidden): `holidays` entries may be `MM-DD`, meaning that
// day in every year. Consumer: the amount a schedule budget template asks for in a
// month.
import { app as budgetApp } from '#server/budget/app';
import * as budget from '#server/budget/base';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { app as schedulesApp } from '#server/schedules/app';
import * as sheet from '#server/sheet';
import { loadRules } from '#server/transactions/transaction-rules';

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
  await db.insertCategoryGroup({ id: 'g-income', name: 'Income', is_income: 1 });
  await db.insertCategoryGroup({ id: 'g-bills', name: 'Bills', is_income: 0 });
  await db.insertCategory({
    id: 'c-bills',
    name: 'Bills',
    cat_group: 'g-bills',
    is_income: 0,
  });
  await sheet.loadSpreadsheet(db);
  await budget.createBudget(['2024-04', '2024-05', '2024-06']);
  await budget.createBudget(['2025-04', '2025-05', '2025-06']);
});

async function createSchedule(name, config, amount) {
  await schedulesApp.handlers['schedule/create']({
    schedule: { name },
    conditions: [
      {
        op: 'is',
        field: 'date',
        value: { interval: 1, patterns: [], endMode: 'never', ...config },
      },
      { op: 'is', field: 'amount', value: amount },
    ],
  });
}

async function templateAmount(scheduleName, month) {
  const result = await budgetApp.handlers['budget/dry-run-category-template']({
    month,
    categoryId: 'c-bills',
    templates: [
      { type: 'schedule', name: scheduleName, priority: 0, directive: 'template' },
    ],
  });
  return result.budgeted;
}

// Fridays in May 2024: 3, 10, 17, 24, 31; in May 2025: 2, 9, 16, 23, 30.
it('schedule template counts occurrences after moving them off month-and-day holidays', async () => {
  // The last Friday of May is listed in both years, so it moves into June.
  await createSchedule(
    'Weekly',
    {
      start: '2024-05-03',
      frequency: 'weekly',
      skipWeekend: true,
      weekendSolveMode: 'after',
      holidays: ['05-31', '05-30'],
    },
    -1000,
  );
  expect(await templateAmount('Weekly', '2024-05')).toBe(4 * 1000);
  expect(await templateAmount('Weekly', '2025-05')).toBe(4 * 1000);
});
