// @ts-strict-ignore
// Study 2, zone Z4, step T2 (hidden): a new handler lists the days a recurring
// schedule falls on within a period, following the schedule date rules (weekend
// handling included). Consumer: the new handler.
import { app as schedulesApp } from '#server/schedules/app';

function datesInRange(config, start, end) {
  return schedulesApp.handlers['schedule/get-dates-in-range']({
    config: { interval: 1, patterns: [], endMode: 'never', ...config },
    start,
    end,
  });
}

// March 2024: Saturdays 2, 9, 16, 23, 30; Fridays 1, 8, 15, 22, 29;
// 2024-04-01 is a Monday.
it('days in a period follow weekend handling, judged by the day the schedule falls on', async () => {
  const saturdays = { start: '2024-03-02', frequency: 'weekly' };

  // Moved to Monday: 2 March lands inside the period, 30 March outside it.
  expect(
    await datesInRange(
      { ...saturdays, skipWeekend: true, weekendSolveMode: 'after' },
      '2024-03-04',
      '2024-03-31',
    ),
  ).toEqual(['2024-03-04', '2024-03-11', '2024-03-18', '2024-03-25']);

  // Moved to Friday: 2 March lands before the period, 30 March inside it.
  expect(
    await datesInRange(
      { ...saturdays, skipWeekend: true, weekendSolveMode: 'before' },
      '2024-03-04',
      '2024-03-29',
    ),
  ).toEqual(['2024-03-08', '2024-03-15', '2024-03-22', '2024-03-29']);

  // Without weekend handling the occurrences stay where they are, and nothing
  // before the schedule's start is listed.
  expect(
    await datesInRange(
      { ...saturdays, skipWeekend: false, weekendSolveMode: 'after' },
      '2024-02-01',
      '2024-03-10',
    ),
  ).toEqual(['2024-03-02', '2024-03-09']);

  // Monthly on the 15th (a Friday in March 2024, a Monday in April).
  expect(
    await datesInRange(
      {
        start: '2024-01-15',
        frequency: 'monthly',
        skipWeekend: true,
        weekendSolveMode: 'after',
      },
      '2024-03-01',
      '2024-04-30',
    ),
  ).toEqual(['2024-03-15', '2024-04-15']);
});

it('days in a period of a daily schedule with weekend handling are weekdays only', async () => {
  const daily = { start: '2024-03-01', frequency: 'daily' };
  for (const weekendSolveMode of ['after', 'before']) {
    expect(
      await datesInRange(
        { ...daily, skipWeekend: true, weekendSolveMode },
        '2024-03-01',
        '2024-03-10',
      ),
    ).toEqual([
      '2024-03-01',
      '2024-03-04',
      '2024-03-05',
      '2024-03-06',
      '2024-03-07',
      '2024-03-08',
    ]);
  }
  expect(
    await datesInRange(
      { ...daily, skipWeekend: false, weekendSolveMode: 'after' },
      '2024-03-01',
      '2024-03-04',
    ),
  ).toEqual(['2024-03-01', '2024-03-02', '2024-03-03', '2024-03-04']);
});
