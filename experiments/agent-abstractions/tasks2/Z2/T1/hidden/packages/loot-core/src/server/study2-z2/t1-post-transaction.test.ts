// @ts-strict-ignore
// Study 2, zone Z2, step T1: hidden behavioural test for one consumer
// (post-transaction). Written from the step statement; real database, nothing mocked.

import MockDate from 'mockdate';

import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { app as schedulesApp } from '#server/schedules/app';
import { loadRules } from '#server/transactions/transaction-rules';

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
  // keeps the schedules view's amount/account/date columns in sync with rules
  schedulesApp.startServices();
  MockDate.set(new Date(2024, 1, 1, 12));
  await db.insertAccount({ id: 'acct', name: 'Checking' });
});

afterEach(async () => {
  MockDate.reset();
  await schedulesApp.stopServices();
});

// A monthly schedule on the 10th, first occurrence 2024-02-10.
async function addSchedule(name: string, amountCondition) {
  return schedulesApp.handlers['schedule/create']({
    schedule: { name },
    conditions: [
      { op: 'is', field: 'account', value: 'acct' },
      {
        op: 'is',
        field: 'date',
        value: { start: '2024-02-10', frequency: 'monthly', patterns: [] },
      },
      ...(amountCondition ? [{ field: 'amount', ...amountCondition }] : []),
    ],
  });
}

describe('Z2 T1 posting a scheduled transaction', () => {
  it('a ranged expense is expected at the end furthest from zero', async () => {
    const id = await addSchedule('Bill', { op: 'isbetween', value: {num1: -10100, num2: -20000} });
    await schedulesApp.handlers['schedule/post-transaction']({ id });
    const posted = await db.all(
      'SELECT amount, date, schedule FROM v_transactions_internal',
    );
    expect(posted).toEqual([
      { amount: -20000, date: 20240210, schedule: id },
    ]);
  });

  it('a ranged expense entered high-to-low is expected at the end furthest from zero', async () => {
    const id = await addSchedule('Bill', { op: 'isbetween', value: {num1: -20000, num2: -10100} });
    await schedulesApp.handlers['schedule/post-transaction']({ id });
    const posted = await db.all(
      'SELECT amount, date, schedule FROM v_transactions_internal',
    );
    expect(posted).toEqual([
      { amount: -20000, date: 20240210, schedule: id },
    ]);
  });

  it('a ranged income is expected at the end furthest from zero', async () => {
    const id = await addSchedule('Bill', { op: 'isbetween', value: {num1: 10100, num2: 20000} });
    await schedulesApp.handlers['schedule/post-transaction']({ id });
    const posted = await db.all(
      'SELECT amount, date, schedule FROM v_transactions_internal',
    );
    expect(posted).toEqual([
      { amount: 20000, date: 20240210, schedule: id },
    ]);
  });
});
