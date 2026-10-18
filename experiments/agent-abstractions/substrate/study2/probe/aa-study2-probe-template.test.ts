// @ts-strict-ignore
// Study 2 equivalence probe (substrate/study2/probe), schedule budget templates.
// Copied into packages/loot-core/src/server/budget/ only for `aa probe2`. Same
// module mocks as the repo's schedule-template.test.ts. Covers the template's
// ranged-amount copy (Z2: half of the rounded sum, then adjustments) and its two
// weekend-rule copies (Z4), writing $AA_PROBE_OUT/template.json.
import { writeFileSync } from 'fs';
import { join } from 'path';

import * as db from '#server/db';
import { Rule } from '#server/rules';
import { getRuleForSchedule } from '#server/schedules/app';
import type { Currency } from '#shared/currencies';
import type { CategoryEntity } from '#types/models';

import { isTrackingBudget } from './actions';
import { runSchedule } from './schedule-template';

vi.mock('#server/db');
vi.mock('./actions');
vi.mock('#server/schedules/app', async () => ({
  ...(await vi.importActual('#server/schedules/app')),
  getRuleForSchedule: vi.fn(),
}));

const currency: Currency = {
  code: '',
  symbol: '',
  name: '',
  decimalPlaces: 2,
  numberFormat: 'comma-dot',
  symbolFirst: false,
};

const results: Record<string, unknown> = {};

afterAll(() => {
  writeFileSync(
    join(process.env.AA_PROBE_OUT, 'template.json'),
    JSON.stringify(results, null, 2),
  );
});

function rule(dateValue, amountCond) {
  return new Rule({
    id: 'r',
    stage: 'pre',
    conditionsOp: 'and',
    conditions: [
      { op: 'is', field: 'date', value: dateValue, type: 'date' },
      { ...amountCond, field: 'amount', type: 'number' },
    ],
    actions: [],
  });
}

async function run(name, dateValue, amountCond, month, line = {}, income = false) {
  vi.mocked(db.first).mockResolvedValue({ id: 1, completed: 0 });
  vi.mocked(db.getAccounts).mockResolvedValue([]);
  vi.mocked(isTrackingBudget).mockReturnValue(false);
  vi.mocked(getRuleForSchedule).mockResolvedValue(rule(dateValue, amountCond));
  try {
    const r = await runSchedule(
      [
        {
          type: 'schedule',
          name: 'S',
          priority: 0,
          directive: 'template',
          ...line,
        } as never,
      ],
      month,
      0,
      0,
      0,
      0,
      [],
      { id: 'c', name: 'C', is_income: income } as CategoryEntity,
      currency,
    );
    results[name] = { ok: r };
  } catch (e) {
    results[name] = { error: String(e?.message ?? e) };
  }
}

const recur = (start, frequency, skipWeekend, weekendSolveMode, interval = 1) => ({
  start,
  interval,
  frequency,
  patterns: [],
  skipWeekend,
  weekendSolveMode,
  endMode: 'never',
  endOccurrences: 1,
  endDate: '2099-01-01',
});

describe('template probe', () => {
  beforeEach(() => vi.clearAllMocks());

  it('Z2 ranged amounts and adjustments', async () => {
    const amounts = [
      ['ranged-odd', { op: 'isbetween', value: { num1: -101, num2: -200 } }],
      ['ranged-odd-pos', { op: 'isbetween', value: { num1: 101, num2: 200 } }],
      ['ranged-even', { op: 'isbetween', value: { num1: -100, num2: -200 } }],
      ['ranged-x3', { op: 'isbetween', value: { num1: -333, num2: -334 } }],
      ['number', { op: 'is', value: -1501 }],
      ['approx', { op: 'isapprox', value: -1501 }],
    ];
    const adjustments = [
      ['none', {}],
      ['pct10', { adjustment: 10, adjustmentType: 'percent' }],
      ['pct-33', { adjustment: -33, adjustmentType: 'percent' }],
      ['fixed1.5', { adjustment: 1.5, adjustmentType: 'fixed' }],
    ];
    for (const [a, cond] of amounts) {
      for (const [adj, line] of adjustments) {
        for (const income of [false, true]) {
          await run(
            `Z2/${a}/${adj}/income=${income}`,
            recur('2024-08-01', 'monthly', false, 'before'),
            cond,
            '2024-08-01',
            line,
            income,
          );
          await run(
            `Z2/once/${a}/${adj}/income=${income}`,
            '2024-09-15',
            cond,
            '2024-08-01',
            line,
            income,
          );
        }
      }
    }
  });

  it('Z4 weekend rule in repeating templates', async () => {
    // Starts on Saturdays/Sundays/weekdays near month ends, so the weekend shift
    // moves occurrences across the month boundary.
    const starts = ['2024-08-03', '2024-08-04', '2024-08-31', '2024-09-01', '2024-07-29'];
    for (const start of starts) {
      for (const frequency of ['weekly', 'monthly', 'daily']) {
        for (const skip of [true, false, undefined]) {
          for (const mode of ['before', 'after']) {
            for (const month of ['2024-08-01', '2024-09-01']) {
              await run(
                `Z4/${start}/${frequency}/${skip}/${mode}/${month}`,
                recur(start, frequency, skip, mode, frequency === 'daily' ? 6 : 1),
                { op: 'is', value: -1000 },
                month,
              );
            }
          }
        }
      }
    }
  });
});
