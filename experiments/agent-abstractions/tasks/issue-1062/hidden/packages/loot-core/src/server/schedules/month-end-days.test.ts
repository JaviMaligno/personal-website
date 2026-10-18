// @ts-strict-ignore
import MockDate from 'mockdate';

import { app as accountsApp } from '#server/accounts/app';
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

afterEach(() => {
  MockDate.reset();
});

function setToday(year: number, month: number, day: number, hour = 12) {
  // month is 1-based here; mid-day local time avoids any day-boundary effects
  MockDate.set(new Date(year, month - 1, day, hour));
}

function monthly(
  start: string,
  patterns: { type: string; value: number }[] = [],
) {
  return { start, frequency: 'monthly', patterns };
}

async function upcomingDates(config, count: number): Promise<string[]> {
  return schedulesApp.handlers['schedule/get-upcoming-dates']({
    config,
    count,
  });
}

async function createSchedule(
  dateValue,
  extra: { schedule?; conditions? } = {},
) {
  return schedulesApp.handlers['schedule/create']({
    schedule: extra.schedule ?? null,
    conditions: [
      ...(extra.conditions ?? []),
      { op: 'is', field: 'date', value: dateValue },
    ],
  });
}

async function nextDateOf(id: string): Promise<string> {
  const { data } = await aqlQuery(
    q('schedules').filter({ id }).select(['next_date']),
  );
  return data[0].next_date;
}

describe('monthly schedules on days that some months do not have', () => {
  describe('upcoming dates', () => {
    it('a schedule starting on the 31st falls on the last day of shorter months', async () => {
      setToday(2023, 5, 1);
      expect(await upcomingDates(monthly('2023-05-31'), 6)).toEqual([
        '2023-05-31',
        '2023-06-30',
        '2023-07-31',
        '2023-08-31',
        '2023-09-30',
        '2023-10-31',
      ]);
    });

    it('the 31st falls on February 28th in a common year and returns to the 31st in March', async () => {
      setToday(2023, 1, 1);
      expect(
        await upcomingDates(
          monthly('2023-01-31', [{ type: 'day', value: 31 }]),
          4,
        ),
      ).toEqual(['2023-01-31', '2023-02-28', '2023-03-31', '2023-04-30']);
    });

    it('the 30th falls on February 29th in a leap year and on the 28th otherwise', async () => {
      setToday(2024, 1, 1);
      expect(
        await upcomingDates(
          monthly('2024-01-30', [{ type: 'day', value: 30 }]),
          3,
        ),
      ).toEqual(['2024-01-30', '2024-02-29', '2024-03-30']);

      setToday(2025, 1, 1);
      expect(
        await upcomingDates(
          monthly('2025-01-30', [{ type: 'day', value: 30 }]),
          3,
        ),
      ).toEqual(['2025-01-30', '2025-02-28', '2025-03-30']);
    });

    it('the 29th stays on the 29th in a leap February and moves to the 28th otherwise', async () => {
      setToday(2024, 1, 1);
      expect(await upcomingDates(monthly('2024-01-29'), 3)).toEqual([
        '2024-01-29',
        '2024-02-29',
        '2024-03-29',
      ]);

      setToday(2023, 1, 1);
      expect(await upcomingDates(monthly('2023-01-29'), 3)).toEqual([
        '2023-01-29',
        '2023-02-28',
        '2023-03-29',
      ]);
    });

    it('several days in the month: the late one moves to month end while the early one is untouched', async () => {
      setToday(2023, 2, 1);
      expect(
        await upcomingDates(
          monthly('2023-02-01', [
            { type: 'day', value: 15 },
            { type: 'day', value: 31 },
          ]),
          6,
        ),
      ).toEqual([
        '2023-02-15',
        '2023-02-28',
        '2023-03-15',
        '2023-03-31',
        '2023-04-15',
        '2023-04-30',
      ]);
    });

    it('never lists the same date twice when two chosen days collapse onto the month end', async () => {
      setToday(2023, 2, 1);
      expect(
        await upcomingDates(
          monthly('2023-02-01', [
            { type: 'day', value: 30 },
            { type: 'day', value: 31 },
          ]),
          5,
        ),
      ).toEqual([
        '2023-02-28',
        '2023-03-30',
        '2023-03-31',
        '2023-04-30',
        '2023-05-30',
      ]);
    });

    it('"last day of the month" keeps working', async () => {
      setToday(2023, 1, 1);
      expect(
        await upcomingDates(
          monthly('2023-01-01', [{ type: 'day', value: -1 }]),
          4,
        ),
      ).toEqual(['2023-01-31', '2023-02-28', '2023-03-31', '2023-04-30']);
    });
  });

  describe("a schedule's next date", () => {
    it("recalculating it during a short month gives that month's last day", async () => {
      setToday(2023, 1, 15);
      const id = await createSchedule(monthly('2023-01-31'));

      // Ask for the next date to be recomputed on February 5th.
      setToday(2023, 2, 5);
      await schedulesApp.handlers['schedule/update']({
        schedule: { id },
        resetNextDate: true,
      });
      expect(await nextDateOf(id)).toBe('2023-02-28');
    });

    it('skipping an occurrence lands on the end of the following short month', async () => {
      const id = await createSchedule(monthly('2017-01-31'));
      expect(await nextDateOf(id)).toBe('2017-01-31');

      await schedulesApp.handlers['schedule/skip-next-date']({ id });
      expect(await nextDateOf(id)).toBe('2017-02-28');

      await schedulesApp.handlers['schedule/skip-next-date']({ id });
      expect(await nextDateOf(id)).toBe('2017-03-31');

      await schedulesApp.handlers['schedule/skip-next-date']({ id });
      expect(await nextDateOf(id)).toBe('2017-04-30');
    });
  });

  describe('automatically posted transactions', () => {
    it('posts the short-month occurrence while catching up, exactly once', async () => {
      // The clock only moves forward: everything is set up in October 2016,
      // and the service runs on 2017-01-01 (the test environment's "today").
      setToday(2016, 10, 20);
      schedulesApp.startServices();

      try {
        const accountId = await accountsApp.handlers['account-create']({
          name: 'Checking',
        });

        const id = await createSchedule(monthly('2016-10-31'), {
          schedule: { posts_transaction: true },
          conditions: [
            { op: 'is', field: 'account', value: accountId },
            { op: 'is', field: 'amount', value: -12345 },
          ],
        });

        // Later that day the schedule's next date is recomputed, and the app
        // is not opened again until January.
        setToday(2016, 10, 20, 14);
        await schedulesApp.handlers['schedule/update']({
          schedule: { id },
          resetNextDate: true,
        });
        expect(await nextDateOf(id)).toBe('2016-10-31');

        setToday(2017, 1, 1);
        await schedulesApp.handlers['schedule/force-run-service'](undefined);
        // Running the service again must not post anything twice.
        await schedulesApp.handlers['schedule/force-run-service'](undefined);

        const { data: transactions } = await aqlQuery(
          q('transactions')
            .filter({ schedule: id })
            .select(['date', 'amount', 'account'])
            .orderBy({ date: 'asc' }),
        );

        expect(
          transactions.map(({ date, amount, account }) => ({
            date,
            amount,
            account,
          })),
        ).toEqual([
          { date: '2016-10-31', amount: -12345, account: accountId },
          { date: '2016-11-30', amount: -12345, account: accountId },
          { date: '2016-12-31', amount: -12345, account: accountId },
        ]);

        expect(await nextDateOf(id)).toBe('2017-01-31');
      } finally {
        await schedulesApp.stopServices();
      }
    });
  });
});
