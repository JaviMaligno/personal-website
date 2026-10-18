// @ts-strict-ignore
// Study 2, zone Z4, step T1 (hidden): a daily schedule with weekend handling skips
// weekend occurrences instead of moving them. Consumer: the upcoming dates shown for a
// recurring date configuration.
import MockDate from 'mockdate';

import { app as schedulesApp } from '#server/schedules/app';

afterEach(() => MockDate.reset());

function upcoming(config, count) {
  return schedulesApp.handlers['schedule/get-upcoming-dates']({
    config: { interval: 1, patterns: [], endMode: 'never', ...config },
    count,
  });
}

const isWeekend = (day: string) => {
  const dow = new Date(day + 'T12:00:00Z').getUTCDay();
  return dow === 0 || dow === 6;
};

// 2024-03-01 is a Friday, 2024-03-02 a Saturday, 2024-03-04 a Monday.
it('upcoming dates of a daily schedule skip weekend days without repeating a day', async () => {
  MockDate.set(new Date(2024, 2, 1, 12));

  const after = await upcoming(
    {
      start: '2024-03-01',
      frequency: 'daily',
      skipWeekend: true,
      weekendSolveMode: 'after',
    },
    5,
  );
  expect(after.length).toBeGreaterThanOrEqual(3);
  expect(after.slice(0, 3)).toEqual(['2024-03-01', '2024-03-04', '2024-03-05']);
  expect(new Set(after).size).toBe(after.length);
  expect(after.filter(isWeekend)).toEqual([]);

  const before = await upcoming(
    {
      start: '2024-03-02',
      frequency: 'daily',
      skipWeekend: true,
      weekendSolveMode: 'before',
    },
    4,
  );
  expect(before.length).toBeGreaterThanOrEqual(2);
  expect(before.slice(0, 2)).toEqual(['2024-03-04', '2024-03-05']);
  expect(new Set(before).size).toBe(before.length);
  expect(before.filter(isWeekend)).toEqual([]);

  // Weekly schedules still move a weekend occurrence.
  expect(
    await upcoming(
      {
        start: '2024-03-02',
        frequency: 'weekly',
        skipWeekend: true,
        weekendSolveMode: 'after',
      },
      2,
    ),
  ).toEqual(['2024-03-04', '2024-03-11']);
});
