// @ts-strict-ignore
// Study 2, zone Z2, step T3: hidden behavioural test for one consumer
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

describe('Z2 T3 balance forecast', () => {
  it('an approximate expense is expected at the end of its tolerance furthest from zero', async () => {
    await addSchedule('Bill', { op: 'isapprox', value: -10000 });
    const { dataPoints } = await forecastApp.handlers['forecast/generate']({
      accountIds: ['acct'],
      startDate: '2024-02-01',
      endDate: '2024-02-29',
    });
    const byDate = Object.fromEntries(
      dataPoints.map(({ date, balance }) => [date, balance]),
    );
    expect(byDate['2024-02-09']).toBe(0);
    expect(byDate['2024-02-10']).toBe(-10750);
    expect(byDate['2024-02-29']).toBe(-10750);
  });

  it('an approximate income is expected at the end of its tolerance furthest from zero', async () => {
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
    expect(byDate['2024-02-10']).toBe(10750);
    expect(byDate['2024-02-29']).toBe(10750);
  });

  it('an approximate expense uses the tolerance rounded to the cent', async () => {
    await addSchedule('Bill', { op: 'isapprox', value: -1234 });
    const { dataPoints } = await forecastApp.handlers['forecast/generate']({
      accountIds: ['acct'],
      startDate: '2024-02-01',
      endDate: '2024-02-29',
    });
    const byDate = Object.fromEntries(
      dataPoints.map(({ date, balance }) => [date, balance]),
    );
    expect(byDate['2024-02-09']).toBe(0);
    expect(byDate['2024-02-10']).toBe(-1327);
    expect(byDate['2024-02-29']).toBe(-1327);
  });
});
