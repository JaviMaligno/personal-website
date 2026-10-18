// @ts-strict-ignore
// Study 2, zone Z4, step T1 (hidden): a daily schedule with weekend handling skips
// weekend occurrences instead of moving them. Consumer: the schedule's next date.
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

// 2024-03-01 is a Friday, 2024-03-02 a Saturday, 2024-03-04 a Monday.
it('daily schedule starting on a weekend gets the first weekday as its next date', async () => {
  expect(
    await nextDateOf(
      'daily before',
      recurring({
        start: '2024-03-02',
        frequency: 'daily',
        skipWeekend: true,
        weekendSolveMode: 'before',
      }),
    ),
  ).toBe('2024-03-04');
  expect(
    await nextDateOf(
      'daily after',
      recurring({
        start: '2024-03-03',
        frequency: 'daily',
        skipWeekend: true,
        weekendSolveMode: 'after',
      }),
    ),
  ).toBe('2024-03-04');
  // Weekly schedules still move a weekend occurrence.
  expect(
    await nextDateOf(
      'weekly before',
      recurring({
        start: '2024-03-02',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'before',
      }),
    ),
  ).toBe('2024-03-01');
});
