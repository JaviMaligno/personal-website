// @ts-strict-ignore
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

async function createMonthlyAutoPostSchedule(accountId: string, start: string) {
  return schedulesApp.handlers['schedule/create']({
    schedule: { posts_transaction: true },
    conditions: [
      { op: 'is', field: 'account', value: accountId },
      { op: 'is', field: 'amount', value: -12345 },
      {
        op: 'is',
        field: 'date',
        value: { start, frequency: 'monthly', interval: 1, patterns: [] },
      },
    ],
  });
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

async function runScheduleService() {
  await schedulesApp.handlers['schedule/force-run-service'](undefined);
}

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

describe('posting a scheduled transaction early and redating it', () => {
  it('does not post the same occurrence again when the posted transaction was moved earlier', async () => {
    let id: string;
    await onDay('2016-12-29', async () => {
      const accountId = await createAccount();
      id = await createMonthlyAutoPostSchedule(accountId, '2017-01-05');
      expect(await nextDate(id)).toBe('2017-01-05');

      // The user posts the upcoming occurrence early ...
      await schedulesApp.handlers['schedule/post-transaction']({ id });
      const posted = await scheduleTransactions(id);
      expect(posted).toEqual([
        { id: posted[0].id, date: '2017-01-05', amount: -12345 },
      ]);

      // ... and corrects its date to the day it was actually paid.
      await transactionsApp.handlers['transaction-update']({
        id: posted[0].id,
        date: '2016-12-29',
      } as TransactionEntity);
      await runScheduleService();
    });

    // The occurrence's due date arrives: nothing new must be posted.
    await onDay('2017-01-05', runScheduleService);
    expect(await scheduleTransactions(id)).toEqual([
      expect.objectContaining({ date: '2016-12-29', amount: -12345 }),
    ]);

    // Once that day is over the schedule moves on to the following
    // occurrence, still without a second transaction for January.
    await onDay('2017-01-06', runScheduleService);
    expect(await scheduleTransactions(id)).toEqual([
      expect.objectContaining({ date: '2016-12-29', amount: -12345 }),
    ]);
    expect(await nextDate(id)).toBe('2017-02-05');

    // The February occurrence is still posted normally when it is due.
    await onDay('2017-02-05', runScheduleService);
    expect(
      (await scheduleTransactions(id)).map(({ date, amount }) => ({
        date,
        amount,
      })),
    ).toEqual([
      { date: '2016-12-29', amount: -12345 },
      { date: '2017-02-05', amount: -12345 },
    ]);
  });

  it('does not post a duplicate when the early-posted transaction is redated to today', async () => {
    let id: string;
    await onDay('2017-01-01', async () => {
      const accountId = await createAccount();
      id = await createMonthlyAutoPostSchedule(accountId, '2017-01-03');

      await schedulesApp.handlers['schedule/post-transaction']({ id });
      const [posted] = await scheduleTransactions(id);
      await transactionsApp.handlers['transaction-update']({
        id: posted.id,
        date: '2017-01-01',
      } as TransactionEntity);
      await runScheduleService();
    });

    await onDay('2017-01-02', runScheduleService);
    await onDay('2017-01-03', runScheduleService);
    await onDay('2017-01-04', runScheduleService);

    expect(
      (await scheduleTransactions(id)).map(({ date, amount }) => ({
        date,
        amount,
      })),
    ).toEqual([{ date: '2017-01-01', amount: -12345 }]);
    expect(await nextDate(id)).toBe('2017-02-03');
  });

  it('still posts an occurrence whose only linked transaction belongs to the previous occurrence', async () => {
    let id: string;
    await onDay('2016-12-03', async () => {
      const accountId = await createAccount();
      id = await createMonthlyAutoPostSchedule(accountId, '2016-12-03');
      await runScheduleService();
    });
    expect(await scheduleTransactions(id)).toEqual([
      expect.objectContaining({ date: '2016-12-03', amount: -12345 }),
    ]);

    await onDay('2016-12-04', runScheduleService);
    expect(await nextDate(id)).toBe('2017-01-03');

    await onDay('2017-01-03', runScheduleService);
    expect(
      (await scheduleTransactions(id)).map(({ date, amount }) => ({
        date,
        amount,
      })),
    ).toEqual([
      { date: '2016-12-03', amount: -12345 },
      { date: '2017-01-03', amount: -12345 },
    ]);
  });
});
