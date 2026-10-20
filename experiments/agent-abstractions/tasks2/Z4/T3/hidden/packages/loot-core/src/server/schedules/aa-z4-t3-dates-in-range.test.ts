// @ts-strict-ignore
// Study 2, zone Z4, step T3 (hidden): with weekend handling on, days listed in the
// recurring configuration's `holidays` are treated like weekend days. Consumer: the
// days a schedule falls on within a period.
import { app as schedulesApp } from '#server/schedules/app';

function datesInRange(config, start, end) {
  return schedulesApp.handlers['schedule/get-dates-in-range']({
    config: { interval: 1, patterns: [], endMode: 'never', ...config },
    start,
    end,
  });
}

// 2024-03-28 Thu, 2024-03-29 Fri (listed), 2024-03-30/31 weekend,
// 2024-04-01 Mon (listed), 2024-04-02 Tue.
const easter = ['2024-03-29', '2024-04-01'];

it('days in a period move off listed holidays like off a weekend', async () => {
  expect(
    await datesInRange(
      {
        start: '2024-03-01',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'after',
        holidays: easter,
      },
      '2024-03-01',
      '2024-04-05',
    ),
  ).toEqual([
    '2024-03-01',
    '2024-03-08',
    '2024-03-15',
    '2024-03-22',
    '2024-04-02',
    '2024-04-05',
  ]);

  expect(
    await datesInRange(
      {
        start: '2024-03-04',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'before',
        holidays: easter,
      },
      '2024-03-25',
      '2024-04-08',
    ),
  ).toEqual(['2024-03-25', '2024-03-28', '2024-04-08']);

  expect(
    await datesInRange(
      {
        start: '2024-03-27',
        frequency: 'daily',
        skipWeekend: true,
        weekendSolveMode: 'after',
        holidays: easter,
      },
      '2024-03-27',
      '2024-04-03',
    ),
  ).toEqual(['2024-03-27', '2024-03-28', '2024-04-02', '2024-04-03']);

  // Without weekend handling the list has no effect.
  expect(
    await datesInRange(
      {
        start: '2024-03-22',
        frequency: 'weekly',
        skipWeekend: false,
        weekendSolveMode: 'after',
        holidays: easter,
      },
      '2024-03-22',
      '2024-03-29',
    ),
  ).toEqual(['2024-03-22', '2024-03-29']);
});
