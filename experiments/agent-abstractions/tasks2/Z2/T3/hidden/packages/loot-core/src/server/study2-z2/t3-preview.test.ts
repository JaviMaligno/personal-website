// @ts-strict-ignore
// Study 2, zone Z2, step T3: hidden behavioural test for one consumer
// (preview). Written from the step statement; real database, nothing mocked.

import MockDate from 'mockdate';

import { aqlQuery } from '#server/aql';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { app as schedulesApp } from '#server/schedules/app';
import { loadRules } from '#server/transactions/transaction-rules';
import { q } from '#shared/query';
import { computeSchedulePreviewTransactions } from '#shared/schedules';

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

describe('Z2 T3 upcoming (preview) transactions', () => {
  it('an approximate expense is expected at the end of its tolerance furthest from zero', async () => {
    const id = await addSchedule('Bill', { op: 'isapprox', value: -10000 });
    const { data } = await aqlQuery(q('schedules').select('*'));
    const preview = computeSchedulePreviewTransactions(
      data,
      new Map(data.map(s => [s.id, 'upcoming'])),
      'oneMonth',
    );
    expect(preview.length).toBeGreaterThan(0);
    for (const t of preview) {
      expect(t.schedule).toBe(id);
      expect(t.amount).toBe(-10750);
    }
  });

  it('an approximate income is expected at the end of its tolerance furthest from zero', async () => {
    const id = await addSchedule('Bill', { op: 'isapprox', value: 10000 });
    const { data } = await aqlQuery(q('schedules').select('*'));
    const preview = computeSchedulePreviewTransactions(
      data,
      new Map(data.map(s => [s.id, 'upcoming'])),
      'oneMonth',
    );
    expect(preview.length).toBeGreaterThan(0);
    for (const t of preview) {
      expect(t.schedule).toBe(id);
      expect(t.amount).toBe(10750);
    }
  });

  it('an approximate expense uses the tolerance rounded to the cent', async () => {
    const id = await addSchedule('Bill', { op: 'isapprox', value: -1234 });
    const { data } = await aqlQuery(q('schedules').select('*'));
    const preview = computeSchedulePreviewTransactions(
      data,
      new Map(data.map(s => [s.id, 'upcoming'])),
      'oneMonth',
    );
    expect(preview.length).toBeGreaterThan(0);
    for (const t of preview) {
      expect(t.schedule).toBe(id);
      expect(t.amount).toBe(-1327);
    }
  });
});
