// @ts-strict-ignore
// Study 2, zone Z4, step T4 (hidden): `holidays` entries may be `MM-DD`, meaning that
// day in every year. Consumer: the days a schedule falls on within a period.
import { app as schedulesApp } from '#server/schedules/app';

function datesInRange(config, start, end) {
  return schedulesApp.handlers['schedule/get-dates-in-range']({
    config: { interval: 1, patterns: [], endMode: 'never', ...config },
    start,
    end,
  });
}

it('days in a period move off holidays given as a month and day, in every year', async () => {
  // Wednesdays: 2024-12-25 is listed, 2025-01-01 is not.
  expect(
    await datesInRange(
      {
        start: '2024-12-04',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'after',
        holidays: ['12-25'],
      },
      '2024-12-20',
      '2025-01-10',
    ),
  ).toEqual(['2024-12-26', '2025-01-01', '2025-01-08']);

  // Daily, a year later: Thu 2025-12-25 and Fri 2025-12-26 are skipped.
  expect(
    await datesInRange(
      {
        start: '2024-12-04',
        frequency: 'daily',
        skipWeekend: true,
        weekendSolveMode: 'after',
        holidays: ['12-25', '12-26'],
      },
      '2025-12-22',
      '2025-12-31',
    ),
  ).toEqual([
    '2025-12-22',
    '2025-12-23',
    '2025-12-24',
    '2025-12-29',
    '2025-12-30',
    '2025-12-31',
  ]);
});
