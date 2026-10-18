// @ts-strict-ignore
// Behaviour (issue #8558): for a schedule with an approximate date whose
// occurrences are close together (every day, every other day), the payment of
// one occurrence must not be taken as the payment of the following one. The
// schedule must then stay on the first unpaid occurrence (due today, missed
// afterwards) instead of silently moving past it. Schedules whose occurrences
// are further apart keep the usual early-payment tolerance, and schedules that
// post automatically still post exactly one transaction per occurrence.
import MockDate from 'mockdate';

import { app as accountsApp } from '#server/accounts/app';
import { aqlQuery } from '#server/aql';
import { loadMappings } from '#server/db/mappings';
import { app as schedulesApp } from '#server/schedules/app';
import { app as transactionsApp } from '#server/transactions/app';
import { loadRules } from '#server/transactions/transaction-rules';
import { q } from '#shared/query';
import type { TransactionEntity } from '#types/models';

// Runs `fn` with "today" being `day` (yyyy-MM-dd) for the whole server.
async function onDay<T>(day: string, fn: () => Promise<T>): Promise<T> {
  const wasTesting = global.IS_TESTING;
  const [y, m, d] = day.split('-').map(Number);
  global.IS_TESTING = false;
  MockDate.set(new Date(y, m - 1, d, 12));
  try {
    return await fn();
  } finally {
    MockDate.reset();
    global.IS_TESTING = wasTesting;
  }
}

async function createAccount() {
  return accountsApp.handlers['account-create']({ name: 'Checking' });
}

async function createSchedule(
  accountId: string,
  dateValue,
  {
    auto = false,
    dateOp = 'isapprox' as 'is' | 'isapprox',
  }: { auto?: boolean; dateOp?: 'is' | 'isapprox' } = {},
) {
  return schedulesApp.handlers['schedule/create']({
    schedule: { posts_transaction: auto },
    conditions: [
      { op: 'is', field: 'account', value: accountId },
      { op: 'isapprox', field: 'amount', value: -500 },
      { op: dateOp, field: 'date', value: dateValue },
    ],
  });
}

function recur(start: string, frequency: string, interval = 1) {
  return { start, frequency, interval, patterns: [], endMode: 'never' };
}

async function scheduleTransactions(scheduleId: string) {
  const { data } = await aqlQuery(
    q('transactions')
      .filter({ schedule: scheduleId })
      .select(['id', 'date', 'amount'])
      .orderBy({ date: 'asc' }),
  );
  return data.map(({ id, date, amount }) => ({ id, date, amount }));
}

async function nextDate(scheduleId: string) {
  const { data } = await aqlQuery(
    q('schedules').filter({ id: scheduleId }).select(['next_date']),
  );
  return data[0].next_date;
}

const runScheduleService = () =>
  schedulesApp.handlers['schedule/force-run-service'](undefined);

const postOccurrence = (id: string) =>
  schedulesApp.handlers['schedule/post-transaction']({ id });

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
  schedulesApp.startServices();
});

afterEach(async () => {
  MockDate.reset();
  await schedulesApp.stopServices();
});

describe('manual daily schedule with an approximate date', () => {
  it('stays on the first unpaid occurrence instead of skipping it', async () => {
    let id: string;
    await onDay('2017-01-02', async () => {
      const accountId = await createAccount();
      id = await createSchedule(accountId, recur('2017-01-02', 'daily'));
      expect(await nextDate(id)).toBe('2017-01-02');

      // The user posts today's occurrence by hand.
      await postOccurrence(id);
      await runScheduleService();
    });

    // Next day: today's occurrence is the one now due.
    await onDay('2017-01-03', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-03');

    // The user does not post it. The following days the schedule must keep
    // pointing at the unpaid 2017-01-03 occurrence (shown as missed), not move
    // on as if yesterday's payment had covered it.
    await onDay('2017-01-04', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-03');

    await onDay('2017-01-05', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-03');

    await onDay('2017-01-06', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-03');

    // Nothing was posted on the user's behalf.
    expect((await scheduleTransactions(id)).map(t => t.date)).toEqual([
      '2017-01-02',
    ]);
  });

  it('posting the missed occurrence records it on its own date', async () => {
    let id: string;
    await onDay('2017-03-10', async () => {
      const accountId = await createAccount();
      id = await createSchedule(accountId, recur('2017-03-10', 'daily'));
      await postOccurrence(id);
      await runScheduleService();
    });
    await onDay('2017-03-11', runScheduleService);
    await onDay('2017-03-12', runScheduleService);

    // The occurrence offered to the user is the missed one of 2017-03-11.
    await onDay('2017-03-12', async () => {
      expect(await nextDate(id)).toBe('2017-03-11');
      await postOccurrence(id);
    });
    expect((await scheduleTransactions(id)).map(t => t.date)).toEqual([
      '2017-03-10',
      '2017-03-11',
    ]);
  });

  it('keeps following the occurrences when every day is paid', async () => {
    let id: string;
    await onDay('2017-02-06', async () => {
      const accountId = await createAccount();
      id = await createSchedule(accountId, recur('2017-02-06', 'daily'));
      await postOccurrence(id);
      await runScheduleService();
    });
    for (const day of ['2017-02-07', '2017-02-08', '2017-02-09']) {
      await onDay(day, async () => {
        await runScheduleService();
        expect(await nextDate(id)).toBe(day);
        await postOccurrence(id);
        await runScheduleService();
      });
    }
    await onDay('2017-02-10', runScheduleService);
    expect(await nextDate(id)).toBe('2017-02-10');
    expect((await scheduleTransactions(id)).map(t => t.date)).toEqual([
      '2017-02-06',
      '2017-02-07',
      '2017-02-08',
      '2017-02-09',
    ]);
  });
});

describe('manual every-other-day schedule with an approximate date', () => {
  it('does not take the previous occurrence payment for the next one', async () => {
    let id: string;
    await onDay('2017-01-02', async () => {
      const accountId = await createAccount();
      id = await createSchedule(accountId, recur('2017-01-02', 'daily', 2));
      expect(await nextDate(id)).toBe('2017-01-02');
      await postOccurrence(id);
      await runScheduleService();
    });

    await onDay('2017-01-03', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-04');

    await onDay('2017-01-04', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-04');

    // 2017-01-04 was never paid: it is missed, not skipped.
    await onDay('2017-01-05', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-04');

    await onDay('2017-01-06', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-04');
    expect((await scheduleTransactions(id)).map(t => t.date)).toEqual([
      '2017-01-02',
    ]);
  });
});

describe('schedules that must keep their current behaviour', () => {
  it('a weekly approximate schedule paid two days early counts as paid', async () => {
    let id: string;
    await onDay('2017-01-05', async () => {
      const accountId = await createAccount();
      id = await createSchedule(accountId, recur('2017-01-09', 'weekly'));
      expect(await nextDate(id)).toBe('2017-01-09');
    });

    await onDay('2017-01-07', async () => {
      // The user posts the upcoming occurrence and dates it the day they
      // actually paid, two days before the due date.
      await postOccurrence(id);
      const [posted] = await scheduleTransactions(id);
      await transactionsApp.handlers['transaction-update']({
        id: posted.id,
        date: '2017-01-07',
      } as TransactionEntity);
      await runScheduleService();
    });
    await onDay('2017-01-08', runScheduleService);
    await onDay('2017-01-09', runScheduleService);
    await onDay('2017-01-10', runScheduleService);

    expect(await nextDate(id)).toBe('2017-01-16');
    expect((await scheduleTransactions(id)).map(t => t.date)).toEqual([
      '2017-01-07',
    ]);
  });

  it('a daily schedule that posts automatically posts each day exactly once', async () => {
    let id: string;
    await onDay('2017-01-02', async () => {
      const accountId = await createAccount();
      id = await createSchedule(accountId, recur('2017-01-02', 'daily'), {
        auto: true,
      });
      await runScheduleService();
    });
    await onDay('2017-01-03', runScheduleService);
    await onDay('2017-01-03', runScheduleService);
    // The app is not opened for a few days, then catches up.
    await onDay('2017-01-06', runScheduleService);
    await onDay('2017-01-06', runScheduleService);
    await onDay('2017-01-07', runScheduleService);

    expect(
      (await scheduleTransactions(id)).map(({ date, amount }) => ({
        date,
        amount,
      })),
    ).toEqual([
      { date: '2017-01-02', amount: -500 },
      { date: '2017-01-03', amount: -500 },
      { date: '2017-01-04', amount: -500 },
      { date: '2017-01-05', amount: -500 },
      { date: '2017-01-06', amount: -500 },
      { date: '2017-01-07', amount: -500 },
    ]);
    expect(await nextDate(id)).toBe('2017-01-07');
  });

  it('a daily schedule with an exact date is not affected', async () => {
    let id: string;
    await onDay('2017-01-02', async () => {
      const accountId = await createAccount();
      id = await createSchedule(accountId, recur('2017-01-02', 'daily'), {
        dateOp: 'is',
      });
      await postOccurrence(id);
      await runScheduleService();
    });
    await onDay('2017-01-03', runScheduleService);
    await onDay('2017-01-04', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-03');
  });
});
