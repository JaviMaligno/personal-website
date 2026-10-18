// @ts-strict-ignore
// Study 2, zone Z4, step T3 (hidden): with weekend handling on, days listed in the
// recurring configuration's `holidays` are treated like weekend days. Consumer: the
// upcoming dates shown for a recurring date configuration.
import MockDate from 'mockdate';

import { app as schedulesApp } from '#server/schedules/app';

afterEach(() => MockDate.reset());

function upcoming(config, count) {
  return schedulesApp.handlers['schedule/get-upcoming-dates']({
    config: { interval: 1, patterns: [], endMode: 'never', ...config },
    count,
  });
}

// 2024-03-28 Thu, 2024-03-29 Fri (listed), 2024-03-30/31 weekend,
// 2024-04-01 Mon (listed), 2024-04-02 Tue.
const easter = ['2024-03-29', '2024-04-01'];

it('upcoming dates move off listed holidays like off a weekend', async () => {
  MockDate.set(new Date(2024, 2, 20, 12));

  expect(
    await upcoming(
      {
        start: '2024-03-22',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'after',
        holidays: easter,
      },
      3,
    ),
  ).toEqual(['2024-03-22', '2024-04-02', '2024-04-05']);

  expect(
    await upcoming(
      {
        start: '2024-03-25',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'before',
        holidays: easter,
      },
      3,
    ),
  ).toEqual(['2024-03-25', '2024-03-28', '2024-04-08']);

  const daily = await upcoming(
    {
      start: '2024-03-28',
      frequency: 'daily',
      skipWeekend: true,
      weekendSolveMode: 'after',
      holidays: easter,
    },
    6,
  );
  expect(daily.length).toBeGreaterThanOrEqual(2);
  expect(daily.slice(0, 2)).toEqual(['2024-03-28', '2024-04-02']);
  expect(new Set(daily).size).toBe(daily.length);
  expect(daily.filter(d => easter.includes(d))).toEqual([]);

  // Without weekend handling the list has no effect.
  expect(
    await upcoming(
      {
        start: '2024-03-22',
        frequency: 'weekly',
        skipWeekend: false,
        weekendSolveMode: 'after',
        holidays: easter,
      },
      2,
    ),
  ).toEqual(['2024-03-22', '2024-03-29']);
});
