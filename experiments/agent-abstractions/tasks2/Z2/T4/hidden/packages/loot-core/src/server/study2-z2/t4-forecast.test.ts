// @ts-strict-ignore
// Study 2, zone Z2, step T4: hidden behavioural test for one consumer
// (forecast). Written from the step statement; real database, nothing mocked.

import MockDate from 'mockdate';

import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { app as forecastApp } from '#server/forecast/app';
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

describe('Z2 T4 balance forecast', () => {
  it('a ranged income is expected at its lowest value', async () => {
    await addSchedule('Bill', { op: 'isbetween', value: {num1: 10100, num2: 20000} });
    const { dataPoints } = await forecastApp.handlers['forecast/generate']({
      accountIds: ['acct'],
      startDate: '2024-02-01',
      endDate: '2024-02-29',
    });
    const byDate = Object.fromEntries(
      dataPoints.map(({ date, balance }) => [date, balance]),
    );
    expect(byDate['2024-02-09']).toBe(0);
    expect(byDate['2024-02-10']).toBe(10100);
    expect(byDate['2024-02-29']).toBe(10100);
  });

  it('an approximate income is expected at the low end of its tolerance', async () => {
    await addSchedule('Bill', { op: 'isapprox', value: 10000 });
    const { dataPoints } = await forecastApp.handlers['forecast/generate']({
      accountIds: ['acct'],
      startDate: '2024-02-01',
      endDate: '2024-02-29',
    });
    const byDate = Object.fromEntries(
      dataPoints.map(({ date, balance }) => [date, balance]),
    );
    expect(byDate['2024-02-09']).toBe(0);
    expect(byDate['2024-02-10']).toBe(9250);
    expect(byDate['2024-02-29']).toBe(9250);
  });

  it('a range spanning zero is expected at its negative end', async () => {
    await addSchedule('Bill', { op: 'isbetween', value: {num1: 5000, num2: -3000} });
    const { dataPoints } = await forecastApp.handlers['forecast/generate']({
      accountIds: ['acct'],
      startDate: '2024-02-01',
      endDate: '2024-02-29',
    });
    const byDate = Object.fromEntries(
      dataPoints.map(({ date, balance }) => [date, balance]),
    );
    expect(byDate['2024-02-09']).toBe(0);
    expect(byDate['2024-02-10']).toBe(-3000);
    expect(byDate['2024-02-29']).toBe(-3000);
  });

  it('a ranged expense is still expected at the end furthest from zero', async () => {
    await addSchedule('Bill', { op: 'isbetween', value: {num1: -20000, num2: -10100} });
    const { dataPoints } = await forecastApp.handlers['forecast/generate']({
      accountIds: ['acct'],
      startDate: '2024-02-01',
      endDate: '2024-02-29',
    });
    const byDate = Object.fromEntries(
      dataPoints.map(({ date, balance }) => [date, balance]),
    );
    expect(byDate['2024-02-09']).toBe(0);
    expect(byDate['2024-02-10']).toBe(-20000);
    expect(byDate['2024-02-29']).toBe(-20000);
  });
});
