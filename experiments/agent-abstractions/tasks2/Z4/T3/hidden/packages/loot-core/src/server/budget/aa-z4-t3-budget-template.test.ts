// @ts-strict-ignore
// Study 2, zone Z4, step T3 (hidden): with weekend handling on, days listed in the
// recurring configuration's `holidays` are treated like weekend days. Consumer: the
// amount a schedule budget template asks for in a month.
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
  await budget.createBudget(['2024-02', '2024-03', '2024-04', '2024-05']);
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

// March 2024 has five Fridays (1, 8, 15, 22, 29); 2024-04-01 is a Monday.
// April 2024 has 22 weekdays.
it('schedule template counts occurrences after moving them off listed holidays', async () => {
  // 29 March moves past the weekend and the listed 1 April, out of March.
  await createSchedule(
    'Weekly',
    {
      start: '2024-03-01',
      frequency: 'weekly',
      skipWeekend: true,
      weekendSolveMode: 'after',
      holidays: ['2024-03-29', '2024-04-01'],
    },
    -1000,
  );
  expect(await templateAmount('Weekly', '2024-03')).toBe(4 * 1000);

  // A daily schedule skips the listed 1 April, the first day of the month.
  await createSchedule(
    'Daily',
    {
      start: '2024-02-01',
      frequency: 'daily',
      skipWeekend: true,
      weekendSolveMode: 'after',
      holidays: ['2024-04-01'],
    },
    -100,
  );
  expect(await templateAmount('Daily', '2024-04')).toBe(21 * 100);
});
