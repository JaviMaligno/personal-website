// @ts-strict-ignore
// Study 2 equivalence probe (substrate/study2/probe), real database. Copied into
// packages/loot-core/src/server/ only for `aa probe2`, never part of a variant or an
// agent's tree. Drives the edge cases of the four zones (and the inconsistencies F
// must preserve) and writes what it observes to $AA_PROBE_OUT/db.json; the harness
// diffs that file across A, R and F. Every case records either its result or the
// error it threw, so a changed exception is a difference too.
import { writeFileSync } from 'fs';
import { join } from 'path';

import MockDate from 'mockdate';

import * as connection from '#platform/server/connection';
import { app as accountsApp } from '#server/accounts/app';
import * as bankSync from '#server/accounts/sync';
import { aqlQuery } from '#server/aql';
import * as actions from '#server/budget/actions';
import * as budget from '#server/budget/base';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { normalizeSchedule } from '#server/forecast/forecast-schedules';
import * as prefs from '#server/prefs';
import {
  createSchedule,
  app as schedulesApp,
  updateSchedule,
} from '#server/schedules/app';
import * as sheet from '#server/sheet';
import { loadRules, updateRule } from '#server/transactions/transaction-rules';
import { q } from '#shared/query';
import {
  computeSchedulePreviewTransactions,
  getNextDate,
} from '#shared/schedules';

vi.mock('#server/accounts/sync', async () => ({
  ...(await vi.importActual('#server/accounts/sync')),
  syncAccount: vi.fn(),
}));

const results: Record<string, unknown> = {};

async function record(name: string, fn: () => Promise<unknown> | unknown) {
  try {
    results[name] = { ok: await fn() };
  } catch (e) {
    results[name] = { error: String(e?.message ?? e) };
  }
}

afterAll(() => {
  writeFileSync(
    join(process.env.AA_PROBE_OUT, 'db.json'),
    JSON.stringify(results, null, 2),
  );
});

const settle = async () => {
  // set6/12MonthAvg fire their per-category writes without awaiting them.
  for (let i = 0; i < 5; i++) {
    await new Promise(r => setTimeout(r, 20));
    await sheet.waitOnSpreadsheet();
  }
};

// ---------------------------------------------------------------- Z1 bulk actions

async function setupBudget(tracking: boolean) {
  await global.emptyDatabase()();
  global.currentMonth = '2024-02';
  if (tracking) {
    await db.runQuery(
      `INSERT INTO preferences (id, value) VALUES ('budgetType', 'tracking')`,
    );
  }
  await db.insertAccount({ id: 'account1', name: 'Account 1' });
  await db.insertCategoryGroup({ id: 'g-inc', name: 'Income', is_income: 1 });
  await db.insertCategoryGroup({ id: 'g-vis', name: 'Visible', is_income: 0 });
  await db.insertCategoryGroup({
    id: 'g-hid',
    name: 'HiddenGroup',
    is_income: 0,
    hidden: 1,
  });
  const cats = [
    { id: 'c-inc', cat_group: 'g-inc', is_income: 1 },
    { id: 'c-vis', cat_group: 'g-vis', is_income: 0 },
    { id: 'c-hid', cat_group: 'g-vis', is_income: 0, hidden: 1 },
    { id: 'c-hgrp', cat_group: 'g-hid', is_income: 0 },
    { id: 'c-orphan', cat_group: 'no-such-group', is_income: 0 },
    { id: 'c-tomb', cat_group: 'g-vis', is_income: 0 },
  ];
  for (const c of cats) {
    await db.insertCategory({ name: c.id, ...c });
  }
  await sheet.loadSpreadsheet(db);
  if (tracking) {
    sheet.get().meta().budgetType = 'tracking';
  }
  await budget.createBudget([
    '2023-11',
    '2023-12',
    '2024-01',
    '2024-02',
    '2024-03',
    '2024-04',
  ]);
  let n = 1;
  for (const c of cats) {
    for (const date of ['2023-11-15', '2023-12-15', '2024-01-15']) {
      await db.insertTransaction({
        date,
        amount: (c.is_income ? 1 : -1) * 100 * n++ + 1,
        account: 'account1',
        category: c.id,
      });
    }
    await actions.setBudget({ category: c.id, month: '2024-03', amount: 1000 + n });
    await actions.setBudget({ category: c.id, month: '2024-04', amount: 7 });
  }
  await db.deleteCategory({ id: 'c-tomb' });
  await settle();
}

async function budgetRows(month: string) {
  const table = actions.isTrackingBudget() ? 'reflect_budgets' : 'zero_budgets';
  return db.all(
    `SELECT category, amount FROM ${table} WHERE month = ? ORDER BY category`,
    [parseInt(month.replace('-', ''))],
  );
}

describe('Z1 bulk budget actions', () => {
  for (const tracking of [false, true]) {
    const kind = tracking ? 'tracking' : 'envelope';
    for (const [name, run] of [
      ['copyPreviousMonth', () => actions.copyPreviousMonth({ month: '2024-04' })],
      ['setZero', () => actions.setZero({ month: '2024-04' })],
      ['set3MonthAvg', () => actions.set3MonthAvg({ month: '2024-04' })],
      ['set6MonthAvg', () => actions.set6MonthAvg({ month: '2024-04' })],
      ['set12MonthAvg', () => actions.set12MonthAvg({ month: '2024-04' })],
      [
        'setNMonthAvg-hidden',
        () => actions.setNMonthAvg({ month: '2024-04', N: 3, category: 'c-hid' }),
      ],
      [
        'setNMonthAvg-income',
        () => actions.setNMonthAvg({ month: '2024-04', N: 3, category: 'c-inc' }),
      ],
    ] as const) {
      it(`${kind} ${name}`, async () => {
        await setupBudget(tracking);
        await record(`Z1/${kind}/${name}`, async () => {
          await run();
          await settle();
          return budgetRows('2024-04');
        });
      });
    }
  }
});

// ---------------------------------------------------------------- Z2 / Z4 schedules

const ranged = { num1: -101, num2: -200 }; // odd sum: midpoint -150.5

describe('Z2 scheduled amounts', () => {
  beforeEach(async () => {
    await global.emptyDatabase()();
    await loadMappings();
    await loadRules();
    MockDate.set(new Date(2024, 1, 1, 12));
    await db.insertAccount({ id: 'acct', name: 'Acct' });
  });
  afterEach(() => MockDate.reset());

  it('forecast normalisation', async () => {
    for (const [label, amount] of [
      ['ranged', ranged],
      ['ranged-even', { num1: -100, num2: -201 }],
      ['ranged-positive', { num1: 101, num2: 200 }],
      ['number', -123],
      ['zero', 0],
    ] as const) {
      await record(`Z2/normalize/${label}`, () =>
        normalizeSchedule({
          id: 's',
          name: 's',
          next_date: '2024-02-10',
          rule: 'r',
          _amount: amount,
          _date: '2024-02-10',
          _account: 'acct',
        } as never),
      );
    }
    await record('Z2/normalize/from-conditions', () =>
      normalizeSchedule({
        id: 's',
        name: 's',
        next_date: '2024-02-10',
        rule: 'r',
        _conditions: [
          { op: 'isbetween', field: 'amount', value: ranged },
          { op: 'is', field: 'date', value: '2024-02-10' },
        ],
      } as never),
    );
  });

  for (const [label, amountCond] of [
    ['ranged', { op: 'isbetween', field: 'amount', value: ranged }],
    ['ranged-positive', { op: 'isbetween', field: 'amount', value: { num1: 3, num2: 6 } }],
    ['number', { op: 'is', field: 'amount', value: -4321 }],
    ['none', null],
  ] as const) {
    it(`schedule lifecycle ${label}`, async () => {
      const conditions = [
        { op: 'is', field: 'account', value: 'acct' },
        {
          op: 'is',
          field: 'date',
          value: { start: '2024-02-10', frequency: 'monthly', patterns: [] },
        },
        ...(amountCond ? [amountCond] : []),
      ];
      let id;
      await record(`Z2/${label}/create`, async () => {
        id = await createSchedule({ schedule: { name: label }, conditions });
        return 'created';
      });
      if (!id) return;
      await record(`Z2/${label}/preview`, async () => {
        const { data } = await aqlQuery(q('schedules').select('*'));
        return computeSchedulePreviewTransactions(
          data,
          new Map(data.map(s => [s.id, 'upcoming'])),
          'oneMonth',
        ).map(t => ({ amount: t.amount, date: t.date }));
      });
      await record(`Z2/${label}/post`, async () => {
        await schedulesApp.handlers['schedule/post-transaction']({ id });
        return db.all('SELECT amount, date FROM v_transactions_internal');
      });
      await record(`Z2/${label}/update-actions`, async () => {
        const { data: ruleId } = await aqlQuery(
          q('schedules').filter({ id }).calculate('rule'),
        );
        await updateRule({
          id: ruleId,
          conditions,
          actions: [
            { op: 'set', field: 'amount', value: 1 },
            { op: 'link-schedule', value: id },
          ],
        });
        await updateSchedule({
          schedule: { id },
          conditions: [
            amountCond
              ? {
                  ...amountCond,
                  value:
                    amountCond.op === 'isbetween'
                      ? { num1: -301, num2: -400 }
                      : -999,
                }
              : { op: 'isbetween', field: 'amount', value: { num1: 5, num2: 8 } },
          ],
        });
        const rule = await db.first('SELECT actions FROM rules WHERE id = ?', [
          ruleId,
        ]);
        return JSON.parse(rule.actions);
      });
    });
  }
});

describe('Z4 weekend rule', () => {
  beforeEach(async () => {
    await global.emptyDatabase()();
    await loadMappings();
    await loadRules();
  });
  afterEach(() => MockDate.reset());

  // 2024-03-02 is a Saturday, 2024-03-03 a Sunday.
  const configs = [];
  for (const start of ['2024-03-02', '2024-03-03', '2024-03-04', '2024-03-31']) {
    for (const skipWeekend of [true, false, undefined]) {
      for (const mode of ['before', 'after', undefined]) {
        for (const frequency of ['weekly', 'monthly']) {
          configs.push({ start, skipWeekend, mode, frequency });
        }
      }
    }
  }

  it('getNextDate', () => {
    for (const c of configs) {
      for (const noSkip of [false, true]) {
        const key = `Z4/next/${JSON.stringify(c)}/noSkip=${noSkip}`;
        void record(key, () =>
          getNextDate(
            {
              op: 'is',
              field: 'date',
              value: {
                start: c.start,
                frequency: c.frequency,
                skipWeekend: c.skipWeekend,
                weekendSolveMode: c.mode,
                patterns: [],
              },
            },
            new Date(2024, 2, 1),
            noSkip,
          ),
        );
      }
    }
  });

  it('upcoming dates handler', async () => {
    MockDate.set(new Date(2024, 2, 1, 12));
    for (const c of configs) {
      await record(`Z4/upcoming/${JSON.stringify(c)}`, () =>
        schedulesApp.handlers['schedule/get-upcoming-dates']({
          config: {
            start: c.start,
            frequency: c.frequency,
            interval: 1,
            skipWeekend: c.skipWeekend,
            weekendSolveMode: c.mode,
            patterns: [],
            endMode: 'never',
          },
          count: 6,
        }),
      );
    }
  });
});

// ---------------------------------------------------------------- Z3 linking

describe('Z3 bank-sync account linking', () => {
  beforeEach(async () => {
    vi.mocked(bankSync.syncAccount).mockReset();
    vi.mocked(bankSync.syncAccount).mockResolvedValue({
      added: [],
      updated: [],
    } as never);
    vi.mocked(connection.send).mockReset();
    await global.emptyDatabase()();
    await loadMappings();
    vi.spyOn(prefs, 'getPrefs').mockReturnValue({ cloudFileId: 'file-1' } as never);
  });

  const ext = {
    account_id: 'ext-1',
    name: 'Checking',
    official_name: 'Official Checking',
    mask: '1234',
    institution: 'Bank A',
    orgDomain: 'bank-a.example',
    orgId: 'org-a',
    balance: 0,
  };
  const providers = [
    ['gocardless-accounts-link', { requisitionId: 'req-1', account: ext }],
    ['simplefin-accounts-link', { externalAccount: ext }],
    ['pluggyai-accounts-link', { externalAccount: ext }],
    ['akahu-accounts-link', { externalAccount: ext }],
    ['enablebanking-accounts-link', { externalAccount: ext }],
  ] as const;

  async function snapshot() {
    return {
      accounts: await db.all(
        'SELECT id, account_id, mask, name, official_name, bank, offbudget, account_sync_source FROM accounts ORDER BY id',
      ),
      payees: await db.all('SELECT id, name, transfer_acct FROM payees ORDER BY id'),
      banks: await db.all('SELECT id, bank_id, name FROM banks ORDER BY id'),
      // Trailing undefined arguments are trimmed: an explicit undefined for an
      // optional parameter is the same call to a function that reads neither
      // `arguments` nor a rest parameter (syncAccount reads neither). Everything
      // else about the call is compared as made.
      syncAccount: vi.mocked(bankSync.syncAccount).mock.calls.map(args => {
        const a = [...args];
        while (a.length && a[a.length - 1] === undefined) a.pop();
        return a;
      }),
      sent: vi.mocked(connection.send).mock.calls,
      messages: await db.all(
        'SELECT dataset, column, value FROM messages_crdt ORDER BY timestamp',
      ),
    };
  }

  for (const [handler, params] of providers) {
    for (const mode of ['new', 'new-offbudget', 'upgrade', 'upgrade-missing']) {
      it(`${handler} ${mode}`, async () => {
        if (mode.startsWith('upgrade')) {
          await db.insertAccount({ id: 'local-1', name: 'Local' });
        }
        await record(`Z3/${handler}/${mode}`, async () => {
          const res = await accountsApp.handlers[handler]({
            ...params,
            ...(mode === 'new-offbudget' ? { offBudget: true } : {}),
            ...(mode === 'upgrade' ? { upgradingId: 'local-1' } : {}),
            ...(mode === 'upgrade-missing' ? { upgradingId: 'nope' } : {}),
            startingDate: '2024-01-01',
            startingBalance: 500,
          } as never);
          return { res, ...(await snapshot()) };
        });
        if (results[`Z3/${handler}/${mode}`]['error']) {
          results[`Z3/${handler}/${mode}/after-error`] = await snapshot();
        }
      });
    }
  }
});
