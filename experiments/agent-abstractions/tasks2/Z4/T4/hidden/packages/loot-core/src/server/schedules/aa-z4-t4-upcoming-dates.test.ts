// @ts-strict-ignore
// Study 2, zone Z4, step T4 (hidden): `holidays` entries may be `MM-DD`, meaning that
// day in every year. Consumer: the upcoming dates shown for a recurring date
// configuration.
import MockDate from 'mockdate';

import { app as schedulesApp } from '#server/schedules/app';

afterEach(() => MockDate.reset());

function upcoming(config, count) {
  return schedulesApp.handlers['schedule/get-upcoming-dates']({
    config: { interval: 1, patterns: [], endMode: 'never', ...config },
    count,
  });
}

// Wednesdays: 2024-12-25 (then Thu 26 is listed too, Fri 27 is free) and
// 2025-01-01 (then Thu 2025-01-02 is free).
it('upcoming dates move off holidays given as a month and day, in every year', async () => {
  MockDate.set(new Date(2024, 11, 1, 12));

  expect(
    await upcoming(
      {
        start: '2024-12-04',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'after',
        holidays: ['12-25', '12-26', '01-01'],
      },
      6,
    ),
  ).toEqual([
    '2024-12-04',
    '2024-12-11',
    '2024-12-18',
    '2024-12-27',
    '2025-01-02',
    '2025-01-08',
  ]);

  // Full dates keep working next to month-and-day entries.
  expect(
    await upcoming(
      {
        start: '2024-12-18',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'before',
        holidays: ['12-25', '2024-12-24'],
      },
      2,
    ),
  ).toEqual(['2024-12-18', '2024-12-23']);
});
