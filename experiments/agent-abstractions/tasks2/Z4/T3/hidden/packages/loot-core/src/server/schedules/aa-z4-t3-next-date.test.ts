// @ts-strict-ignore
// Study 2, zone Z4, step T3 (hidden): with weekend handling on, days listed in the
// recurring configuration's `holidays` are treated like weekend days. Consumer: the
// schedule's next date.
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

// 2024-03-28 Thu, 2024-03-29 Fri (listed), 2024-03-30/31 weekend,
// 2024-04-01 Mon (listed), 2024-04-02 Tue.
const easter = ['2024-03-29', '2024-04-01'];

it('next date moves off listed holidays like off a weekend', async () => {
  expect(
    await nextDateOf(
      'weekly after',
      recurring({
        start: '2024-03-29',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'after',
        holidays: easter,
      }),
    ),
  ).toBe('2024-04-02');
  expect(
    await nextDateOf(
      'weekly before',
      recurring({
        start: '2024-04-01',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'before',
        holidays: easter,
      }),
    ),
  ).toBe('2024-03-28');
  expect(
    await nextDateOf(
      'daily',
      recurring({
        start: '2024-03-29',
        frequency: 'daily',
        skipWeekend: true,
        weekendSolveMode: 'before',
        holidays: easter,
      }),
    ),
  ).toBe('2024-04-02');
  // Without weekend handling the list has no effect.
  expect(
    await nextDateOf(
      'weekly off',
      recurring({
        start: '2024-03-29',
        frequency: 'weekly',
        skipWeekend: false,
        weekendSolveMode: 'after',
        holidays: easter,
      }),
    ),
  ).toBe('2024-03-29');
});
