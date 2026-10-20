import { loadMappings } from '#server/db/mappings';
import * as dbWrite from '#server/db/write';
import { app } from '#server/payees/app';
import { createSchedule, updateSchedule } from '#server/schedules/app';
import {
  insertRule,
  loadRules,
  resetState,
} from '#server/transactions/transaction-rules';

beforeEach(async () => {
  await global.emptyDatabase()();
  resetState();
  await loadMappings();
  await loadRules();
});

describe('payees app', () => {
  describe('payees-get-rule-counts', () => {
    it('counts payee rules but excludes rules linked to completed schedules', async () => {
      const activePayeeId = await dbWrite.insertPayee({ name: 'Active Payee' });
      const completedPayeeId = await dbWrite.insertPayee({
        name: 'Completed Payee',
      });

      await insertRule({
        stage: 'pre',
        conditionsOp: 'and',
        conditions: [{ op: 'is', field: 'payee', value: activePayeeId }],
        actions: [{ op: 'set', field: 'category', value: null }],
      });

      const scheduleId = await createSchedule({
        conditions: [
          { op: 'is', field: 'payee', value: completedPayeeId },
          { op: 'is', field: 'date', value: '2020-12-20' },
        ],
      });
      await updateSchedule({
        schedule: { id: scheduleId, completed: true },
      });

      const counts = await app.handlers['payees-get-rule-counts']();

      expect(counts[activePayeeId]).toBe(1);
      expect(counts[completedPayeeId]).toBeUndefined();
    });
  });
});
