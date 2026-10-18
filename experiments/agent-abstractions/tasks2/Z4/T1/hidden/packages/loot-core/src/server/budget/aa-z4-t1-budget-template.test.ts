// @ts-strict-ignore
// Study 2, zone Z4, step T1 (hidden): a daily schedule with weekend handling skips
// weekend occurrences instead of moving them. Consumer: the amount a schedule budget
// template asks for in a month.
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
  await budget.createBudget(['2024-05', '2024-06', '2024-07', '2024-08', '2024-09']);
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

// August 2024 starts on a Thursday and has 22 weekdays; June 2024 starts on a
// Saturday and has 20 weekdays.
it('schedule template for a daily schedule counts only its weekday occurrences', async () => {
  await createSchedule(
    'Daily lunch',
    {
      start: '2024-05-01',
      frequency: 'daily',
      skipWeekend: true,
      weekendSolveMode: 'after',
    },
    -1000,
  );
  expect(await templateAmount('Daily lunch', '2024-08')).toBe(22 * 1000);
  expect(await templateAmount('Daily lunch', '2024-06')).toBe(20 * 1000);
});
