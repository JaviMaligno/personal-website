// @ts-strict-ignore
// Study 2, zone Z4, step T4 (hidden): `holidays` entries may be `MM-DD`, meaning that
// day in every year. Consumer: the schedule's next date.
import { aqlQuery } from '#server/aql';
import { loadMappings } from '#server/db/mappings';
import { app as schedulesApp } from '#server/schedules/app';
import { loadRules } from '#server/transactions/transaction-rules';
import { q } from '#shared/query';

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
});

function recurring(fields) {
  return { interval: 1, patterns: [], endMode: 'never', ...fields };
}

async function nextDateOf(name, config) {
  const id = await schedulesApp.handlers['schedule/create']({
    schedule: { name },
    conditions: [
      { op: 'is', field: 'date', value: config },
      { op: 'is', field: 'amount', value: -1000 },
    ],
  });
  const { data } = await aqlQuery(
    q('schedules').filter({ id }).select(['next_date']),
  );
  return data[0].next_date;
}

// 2025-12-25 Thu, 2025-12-26 Fri, 2025-12-29 Mon, 2025-12-30 Tue,
// 2025-12-31 Wed, 2026-01-01 Thu.
it('next date moves off holidays given as a month and day', async () => {
  expect(
    await nextDateOf(
      'yearly only',
      recurring({
        start: '2025-12-25',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'after',
        holidays: ['12-25', '12-26'],
      }),
    ),
  ).toBe('2025-12-29');
  expect(
    await nextDateOf(
      'mixed',
      recurring({
        start: '2025-12-25',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'after',
        holidays: ['12-25', '12-26', '2025-12-29'],
      }),
    ),
  ).toBe('2025-12-30');
  expect(
    await nextDateOf(
      'before',
      recurring({
        start: '2026-01-01',
        frequency: 'monthly',
        skipWeekend: true,
        weekendSolveMode: 'before',
        holidays: ['01-01'],
      }),
    ),
  ).toBe('2025-12-31');
});
