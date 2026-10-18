// @ts-strict-ignore
// Study 2, zone Z2, step T3: hidden behavioural test for one consumer
// (rule-action-sync). Written from the step statement; real database, nothing mocked.

import MockDate from 'mockdate';

import { aqlQuery } from '#server/aql';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { app as rulesApp } from '#server/rules/app';
import { app as schedulesApp } from '#server/schedules/app';
import { loadRules } from '#server/transactions/transaction-rules';
import { q } from '#shared/query';

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

describe('Z2 T3 rule actions kept in sync with the schedule amount', () => {
  it('an approximate expense is expected at the end of its tolerance furthest from zero', async () => {
    const id = await addSchedule('Bill', { op: 'is', value: -1 });
    const { data: ruleId } = await aqlQuery(
      q('schedules').filter({ id }).calculate('rule'),
    );
    const rule = await rulesApp.handlers['rule-get']({ id: ruleId });
    await rulesApp.handlers['rule-update']({
      ...rule,
      actions: [...rule.actions, { op: 'set', field: 'amount', value: -1 }],
    });
    await schedulesApp.handlers['schedule/update']({
      schedule: { id },
      conditions: [{ op: 'isapprox', field: 'amount', value: -10000 }],
    });
    const after = await rulesApp.handlers['rule-get']({ id: ruleId });
    const setAmount = after.actions.filter(
      a => a.op === 'set' && a.field === 'amount',
    );
    expect(setAmount).toHaveLength(1);
    expect(setAmount[0].value).toBe(-10750);
  });

  it('an approximate income is expected at the end of its tolerance furthest from zero', async () => {
    const id = await addSchedule('Bill', { op: 'is', value: -1 });
    const { data: ruleId } = await aqlQuery(
      q('schedules').filter({ id }).calculate('rule'),
    );
    const rule = await rulesApp.handlers['rule-get']({ id: ruleId });
    await rulesApp.handlers['rule-update']({
      ...rule,
      actions: [...rule.actions, { op: 'set', field: 'amount', value: -1 }],
    });
    await schedulesApp.handlers['schedule/update']({
      schedule: { id },
      conditions: [{ op: 'isapprox', field: 'amount', value: 10000 }],
    });
    const after = await rulesApp.handlers['rule-get']({ id: ruleId });
    const setAmount = after.actions.filter(
      a => a.op === 'set' && a.field === 'amount',
    );
    expect(setAmount).toHaveLength(1);
    expect(setAmount[0].value).toBe(10750);
  });

  it('an approximate expense uses the tolerance rounded to the cent', async () => {
    const id = await addSchedule('Bill', { op: 'is', value: -1 });
    const { data: ruleId } = await aqlQuery(
      q('schedules').filter({ id }).calculate('rule'),
    );
    const rule = await rulesApp.handlers['rule-get']({ id: ruleId });
    await rulesApp.handlers['rule-update']({
      ...rule,
      actions: [...rule.actions, { op: 'set', field: 'amount', value: -1 }],
    });
    await schedulesApp.handlers['schedule/update']({
      schedule: { id },
      conditions: [{ op: 'isapprox', field: 'amount', value: -1234 }],
    });
    const after = await rulesApp.handlers['rule-get']({ id: ruleId });
    const setAmount = after.actions.filter(
      a => a.op === 'set' && a.field === 'amount',
    );
    expect(setAmount).toHaveLength(1);
    expect(setAmount[0].value).toBe(-1327);
  });
});
