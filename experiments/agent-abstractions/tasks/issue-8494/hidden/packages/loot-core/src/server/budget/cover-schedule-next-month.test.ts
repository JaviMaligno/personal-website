// @ts-strict-ignore
// Behavioural tests for "Cover schedule" automations applied to the month
// after the current one (actualbudget/actual#8494). Everything goes through the
// server handlers; results are read back from the stored budget amounts.
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { handlers } from '#server/main';
import {
  disableGlobalMutations,
  enableGlobalMutations,
  runHandler,
} from '#server/mutators';
import * as sheet from '#server/sheet';
import { loadRules } from '#server/transactions/transaction-rules';

vi.mock('#server/post');

const CURRENT_MONTH = '2026-08';
const NEXT_MONTH = '2026-09';

type Setup = {
  accountId: string;
  categoryId: string;
  scheduleId: string;
};

async function setup({
  amount,
  start,
  month = CURRENT_MONTH,
}: {
  amount: number;
  start: string;
  month?: string;
}): Promise<Setup> {
  global.currentMonth = month;
  await sheet.loadSpreadsheet(db);

  const accountId = await runHandler(handlers['account-create'], {
    name: 'Checking',
  });

  const incomeGroup = await runHandler(handlers['category-group-create'], {
    name: 'Income',
    isIncome: true,
  });
  const incomeCategory = await runHandler(handlers['category-create'], {
    name: 'Salary',
    groupId: incomeGroup,
    isIncome: true,
  });
  const group = await runHandler(handlers['category-group-create'], {
    name: 'Bills',
  });
  const categoryId = await runHandler(handlers['category-create'], {
    name: 'Rent',
    groupId: group,
  });

  // Plenty of money to budget in the current month (and carried forward).
  await runHandler(handlers['transaction-add'], {
    id: 'income-1',
    account: accountId,
    date: `${month}-01`,
    amount: 1_000_000,
    category: incomeCategory,
  });

  const scheduleId = await runHandler(handlers['schedule/create'], {
    schedule: { name: 'Weekly rent' },
    conditions: [
      { op: 'is', field: 'account', value: accountId },
      { op: 'is', field: 'amount', value: amount },
      {
        op: 'is',
        field: 'date',
        value: {
          start,
          frequency: 'weekly',
          interval: 1,
          patterns: [],
          skipWeekend: false,
          weekendSolveMode: 'before',
          endMode: 'never',
          endOccurrences: 1,
          endDate: start,
        },
      },
    ],
  });

  // Make sure the budget months around "now" exist, as the app does on load.
  await runHandler(handlers['get-budget-bounds']);

  // "Cover schedule" automation, savings mode "save up for the next occurrence".
  await runHandler(handlers['budget/set-category-automations'], {
    categoriesWithTemplates: [
      {
        id: categoryId,
        templates: [
          {
            type: 'schedule',
            name: 'Weekly rent',
            scheduleId,
            full: false,
            priority: 0,
            directive: 'template',
          },
        ],
      },
    ],
    source: 'ui',
  });

  await sheet.waitOnSpreadsheet();
  return { accountId, categoryId, scheduleId };
}

async function budgetedAmount(month: string, categoryId: string) {
  await sheet.waitOnSpreadsheet();
  const row = await db.first<{ amount: number }>(
    'SELECT amount FROM zero_budgets WHERE month = ? AND category = ?',
    [Number(month.replace('-', '')), categoryId],
  );
  return row?.amount ?? 0;
}

async function applyToCurrentMonth(month = CURRENT_MONTH) {
  await runHandler(handlers['budget/apply-goal-template'], { month });
  await sheet.waitOnSpreadsheet();
}

async function overwriteNextMonth(month = NEXT_MONTH) {
  await runHandler(handlers['budget/overwrite-goal-template'], { month });
  await sheet.waitOnSpreadsheet();
}

async function spend(
  { accountId, categoryId }: Setup,
  amount: number,
  date: string,
  id: string,
  schedule?: string,
) {
  await runHandler(handlers['transaction-add'], {
    id,
    account: accountId,
    date,
    amount,
    category: categoryId,
    ...(schedule ? { schedule } : {}),
  });
  await sheet.waitOnSpreadsheet();
}

beforeEach(async () => {
  await global.emptyDatabase()();
  disableGlobalMutations();
  global.currentMonth = CURRENT_MONTH;
  await loadMappings();
  await loadRules();
});

afterEach(async () => {
  enableGlobalMutations();
  global.currentMonth = null;
});

describe('Cover schedule automation budgeting the next month', () => {
  // Weekly 100.00 starting Friday 2026-08-07: August has 4 Fridays
  // (7, 14, 21, 28) and September has 4 Fridays (4, 11, 18, 25).

  it('budgets the full weekly total for the current month', async () => {
    const s = await setup({ amount: -10000, start: '2026-08-07' });
    await applyToCurrentMonth();
    expect(await budgetedAmount(CURRENT_MONTH, s.categoryId)).toBe(40000);
  });

  it('budgets the full next-month total when nothing was spent this month', async () => {
    const s = await setup({ amount: -10000, start: '2026-08-07' });
    await applyToCurrentMonth();
    await overwriteNextMonth();
    expect(await budgetedAmount(CURRENT_MONTH, s.categoryId)).toBe(40000);
    expect(await budgetedAmount(NEXT_MONTH, s.categoryId)).toBe(40000);
  });

  it('budgets the full next-month total after spending in the current month (issue scenario)', async () => {
    const s = await setup({ amount: -10000, start: '2026-08-07' });
    await applyToCurrentMonth();
    expect(await budgetedAmount(CURRENT_MONTH, s.categoryId)).toBe(40000);

    await spend(s, -10000, '2026-08-07', 'rent-aug-07');
    await overwriteNextMonth();

    // The current month is untouched and the next month gets its own
    // 4 x 100.00, not a top-up of the current month's remaining balance.
    expect(await budgetedAmount(CURRENT_MONTH, s.categoryId)).toBe(40000);
    expect(await budgetedAmount(NEXT_MONTH, s.categoryId)).toBe(40000);
  });

  it('gives the next month the same amount whether or not the current month has spending', async () => {
    const s = await setup({ amount: -10000, start: '2026-08-07' });
    await applyToCurrentMonth();
    await overwriteNextMonth();
    const withoutSpending = await budgetedAmount(NEXT_MONTH, s.categoryId);

    await spend(s, -10000, '2026-08-07', 'rent-aug-07');
    await spend(s, -10000, '2026-08-14', 'rent-aug-14');
    await overwriteNextMonth();
    const withSpending = await budgetedAmount(NEXT_MONTH, s.categoryId);

    expect(withoutSpending).toBe(40000);
    expect(withSpending).toBe(withoutSpending);
  });

  it('is exact to the cent and counts five occurrences in a five-Friday month', async () => {
    // Weekly 123.45 starting Friday 2026-09-04: September has 4 Fridays
    // (4, 11, 18, 25) and October has 5 Fridays (2, 9, 16, 23, 30).
    const s = await setup({
      amount: -12345,
      start: '2026-09-04',
      month: '2026-09',
    });
    await applyToCurrentMonth('2026-09');
    expect(await budgetedAmount('2026-09', s.categoryId)).toBe(4 * 12345);

    // The first occurrence is paid, linked to the schedule.
    await spend(s, -12345, '2026-09-04', 'rent-sep-04', s.scheduleId);
    await overwriteNextMonth('2026-10');

    expect(await budgetedAmount('2026-09', s.categoryId)).toBe(4 * 12345);
    expect(await budgetedAmount('2026-10', s.categoryId)).toBe(5 * 12345);
  });
});
