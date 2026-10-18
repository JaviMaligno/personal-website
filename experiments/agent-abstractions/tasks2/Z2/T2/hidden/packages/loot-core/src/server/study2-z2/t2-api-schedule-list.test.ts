// @ts-strict-ignore
// Study 2, zone Z2, step T2: hidden behavioural test for one consumer
// (api-schedule-list). Written from the step statement; real database, nothing mocked.

import MockDate from 'mockdate';

import { installAPI } from '#server/api';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import * as prefs from '#server/prefs';
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

describe('Z2 T2 API schedule list', () => {
  it('a ranged expense reports the amount it is expected to post', async () => {
    await prefs.loadPrefs();
    const api = installAPI({} as never);
    const id = await addSchedule('Bill', {
      op: 'isbetween',
      value: { num1: -20000, num2: -10100 },
    });
    const [schedule] = await api['api/schedules-get']();
    expect(schedule).toMatchObject({
      id,
      name: 'Bill',
      amount: { num1: -20000, num2: -10100 },
      amountOp: 'isbetween',
      expectedAmount: -20000,
    });
  });

  it('a ranged income reports the amount it is expected to post', async () => {
    await prefs.loadPrefs();
    const api = installAPI({} as never);
    const id = await addSchedule('Salary', {
      op: 'isbetween',
      value: { num1: 10100, num2: 20000 },
    });
    const [schedule] = await api['api/schedules-get']();
    expect(schedule).toMatchObject({
      id,
      name: 'Salary',
      amount: { num1: 10100, num2: 20000 },
      amountOp: 'isbetween',
      expectedAmount: 20000,
    });
  });

  it('a schedule with a single amount reports that amount', async () => {
    await prefs.loadPrefs();
    const api = installAPI({} as never);
    const id = await addSchedule('Rent', { op: 'is', value: -4321 });
    const [schedule] = await api['api/schedules-get']();
    expect(schedule).toMatchObject({
      id,
      amount: -4321,
      amountOp: 'is',
      expectedAmount: -4321,
    });
  });

  it('a schedule without an amount reports 0', async () => {
    await prefs.loadPrefs();
    const api = installAPI({} as never);
    const id = await addSchedule('Unknown', null);
    const [schedule] = await api['api/schedules-get']();
    expect(schedule.id).toBe(id);
    expect(schedule.expectedAmount).toBe(0);
  });
});
