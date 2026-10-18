import { Timestamp } from '@actual-app/crdt';
import { beforeEach, describe, expect, test } from 'vitest';

import { app as accountsApp } from '#server/accounts/app';
import { app as budgetApp } from '#server/budget/app';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { app as payeesApp } from '#server/payees/app';
import { app as rulesApp } from '#server/rules/app';
import { sendMessages } from '#server/sync';
import { app as transactionsApp } from '#server/transactions/app';
import { loadRules } from '#server/transactions/transaction-rules';

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
});

type Setup = {
  accountId: string;
  groceries: string;
  dining: string;
};

async function setup(): Promise<Setup> {
  const accountId = await accountsApp.handlers['account-create']({
    name: 'Checking',
    balance: 0,
  });
  const groupId = await budgetApp.handlers['category-group-create']({
    name: 'Everyday',
  });
  const groceries = await budgetApp.handlers['category-create']({
    name: 'Groceries',
    groupId,
  });
  const dining = await budgetApp.handlers['category-create']({
    name: 'Dining out',
    groupId,
  });
  return { accountId, groceries, dining };
}

async function createPayee(name: string): Promise<string> {
  return payeesApp.handlers['payee-create']({ name });
}

// A payee row whose per-payee learning flag holds no value, as found in
// existing budget files.
async function clearFlagInStoredRow(payeeId: string) {
  db.runQuery('UPDATE payees SET learn_categories = NULL WHERE id = ?', [
    payeeId,
  ]);
  const row = await db.first<{ learn_categories: number | null }>(
    'SELECT learn_categories FROM payees WHERE id = ?',
    [payeeId],
  );
  expect(row?.learn_categories).toBeNull();
}

// The flag is cleared by a change that arrives through sync (e.g. written by
// another device / client that sends an empty value for it).
async function clearFlagThroughSync(payeeId: string) {
  await sendMessages([
    {
      dataset: 'payees',
      row: payeeId,
      column: 'learn_categories',
      value: null,
      timestamp: Timestamp.send()!,
    },
  ]);
  const row = await db.first<{ learn_categories: number | null }>(
    'SELECT learn_categories FROM payees WHERE id = ?',
    [payeeId],
  );
  expect(row?.learn_categories).toBeNull();
}

async function setFlag(payeeId: string, value: boolean) {
  await payeesApp.handlers['payees-batch-change']({
    updated: [{ id: payeeId, learn_categories: value }],
  });
}

let nextId = 0;
function tx(
  accountId: string,
  payee: string,
  date: string,
  category: string | null,
) {
  nextId += 1;
  return {
    id: `learn-tx-${nextId}`,
    account: accountId,
    payee,
    date,
    amount: -1500,
    category,
  };
}

// Add transactions the way the transaction register does, with category
// learning turned on.
async function addWithLearning(
  transactions: ReturnType<typeof tx>[],
  learnCategories = true,
) {
  await transactionsApp.handlers['transactions-batch-update']({
    added: transactions,
    learnCategories,
  });
}

async function categoryRulesFor(payeeId: string) {
  const rules = await rulesApp.handlers['rules-get']();
  return rules.filter(
    rule =>
      rule.conditions.some(
        c =>
          c.field === 'payee' &&
          (c.value === payeeId ||
            (Array.isArray(c.value) && c.value.includes(payeeId))),
      ) &&
      rule.actions.some(
        a => a.op === 'set' && 'field' in a && a.field === 'category',
      ),
  );
}

function categoryOf(rule: Awaited<ReturnType<typeof categoryRulesFor>>[0]) {
  const action = rule.actions.find(
    a => a.op === 'set' && 'field' in a && a.field === 'category',
  );
  return action && 'value' in action ? action.value : undefined;
}

describe('category learning for payees whose learning flag is unset', () => {
  test('a payee with an unset flag in its stored row learns its category', async () => {
    const { accountId, dining } = await setup();
    const payee = await createPayee('Soccer Taco');
    await clearFlagInStoredRow(payee);

    await addWithLearning([
      tx(accountId, payee, '2016-01-03', dining),
      tx(accountId, payee, '2016-01-17', dining),
      tx(accountId, payee, '2016-02-02', dining),
    ]);

    const rules = await categoryRulesFor(payee);
    expect(rules).toHaveLength(1);
    expect(categoryOf(rules[0])).toBe(dining);
  });

  test('learning also fires when the user categorises transactions one at a time', async () => {
    const { accountId, dining } = await setup();
    const payee = await createPayee('Soccer Taco');
    await clearFlagInStoredRow(payee);

    for (const date of ['2016-03-01', '2016-03-15', '2016-03-29']) {
      await addWithLearning([tx(accountId, payee, date, dining)]);
    }

    const rules = await categoryRulesFor(payee);
    expect(rules).toHaveLength(1);
    expect(categoryOf(rules[0])).toBe(dining);
  });

  test('categorising existing uncategorised transactions of such a payee learns too', async () => {
    const { accountId, groceries } = await setup();
    const payee = await createPayee('Corner Market');

    const existing = [
      tx(accountId, payee, '2016-04-02', null),
      tx(accountId, payee, '2016-04-09', null),
      tx(accountId, payee, '2016-04-16', null),
    ];
    await addWithLearning(existing);
    await clearFlagThroughSync(payee);

    await transactionsApp.handlers['transactions-batch-update']({
      updated: existing.map(t => ({ id: t.id, category: groceries })),
      learnCategories: true,
    });

    const rules = await categoryRulesFor(payee);
    expect(rules).toHaveLength(1);
    expect(categoryOf(rules[0])).toBe(groceries);
  });

  test('a flag cleared through sync behaves like the default (learning on)', async () => {
    const { accountId, groceries } = await setup();
    const payee = await createPayee('Corner Market');
    await clearFlagThroughSync(payee);

    await addWithLearning([
      tx(accountId, payee, '2016-05-01', groceries),
      tx(accountId, payee, '2016-05-08', groceries),
      tx(accountId, payee, '2016-05-15', groceries),
    ]);

    const rules = await categoryRulesFor(payee);
    expect(rules).toHaveLength(1);
    expect(categoryOf(rules[0])).toBe(groceries);
  });

  test('a learned rule of such a payee follows a change of habit', async () => {
    const { accountId, groceries, dining } = await setup();
    const payee = await createPayee('Food Hall');
    await clearFlagInStoredRow(payee);

    await addWithLearning([
      tx(accountId, payee, '2016-06-01', groceries),
      tx(accountId, payee, '2016-06-02', groceries),
      tx(accountId, payee, '2016-06-03', groceries),
    ]);
    let rules = await categoryRulesFor(payee);
    expect(rules).toHaveLength(1);
    expect(categoryOf(rules[0])).toBe(groceries);

    await addWithLearning([
      tx(accountId, payee, '2016-06-10', dining),
      tx(accountId, payee, '2016-06-11', dining),
      tx(accountId, payee, '2016-06-12', dining),
    ]);
    rules = await categoryRulesFor(payee);
    expect(rules).toHaveLength(1);
    expect(categoryOf(rules[0])).toBe(dining);
  });

  test('only payees that need it get a rule, one each', async () => {
    const { accountId, groceries, dining } = await setup();
    const unset = await createPayee('Unset Payee');
    const enabled = await createPayee('Enabled Payee');
    await clearFlagInStoredRow(unset);

    await addWithLearning([
      tx(accountId, unset, '2016-07-01', dining),
      tx(accountId, enabled, '2016-07-01', groceries),
      tx(accountId, unset, '2016-07-02', dining),
      tx(accountId, enabled, '2016-07-02', groceries),
      tx(accountId, unset, '2016-07-03', dining),
      tx(accountId, enabled, '2016-07-03', groceries),
    ]);

    const unsetRules = await categoryRulesFor(unset);
    expect(unsetRules).toHaveLength(1);
    expect(categoryOf(unsetRules[0])).toBe(dining);
    const enabledRules = await categoryRulesFor(enabled);
    expect(enabledRules).toHaveLength(1);
    expect(categoryOf(enabledRules[0])).toBe(groceries);
  });
});

describe('explicit per-payee choices and the learning switch are respected', () => {
  test('a payee with learning explicitly turned off never gets a rule', async () => {
    const { accountId, dining } = await setup();
    const payee = await createPayee('Do Not Learn');
    await setFlag(payee, false);

    await addWithLearning([
      tx(accountId, payee, '2016-08-01', dining),
      tx(accountId, payee, '2016-08-02', dining),
      tx(accountId, payee, '2016-08-03', dining),
    ]);

    expect(await categoryRulesFor(payee)).toHaveLength(0);
  });

  test('turning learning off for a payee whose flag was unset stops learning', async () => {
    const { accountId, dining } = await setup();
    const payee = await createPayee('Changed My Mind');
    await clearFlagInStoredRow(payee);
    await setFlag(payee, false);

    await addWithLearning([
      tx(accountId, payee, '2016-08-11', dining),
      tx(accountId, payee, '2016-08-12', dining),
      tx(accountId, payee, '2016-08-13', dining),
    ]);

    expect(await categoryRulesFor(payee)).toHaveLength(0);
  });

  test('a payee with learning explicitly turned on still learns', async () => {
    const { accountId, groceries } = await setup();
    const payee = await createPayee('Always Learn');
    await setFlag(payee, true);

    await addWithLearning([
      tx(accountId, payee, '2016-09-01', groceries),
      tx(accountId, payee, '2016-09-02', groceries),
      tx(accountId, payee, '2016-09-03', groceries),
    ]);

    const rules = await categoryRulesFor(payee);
    expect(rules).toHaveLength(1);
    expect(categoryOf(rules[0])).toBe(groceries);
  });

  test('nothing is learned when the change is saved without category learning', async () => {
    const { accountId, dining } = await setup();
    const payee = await createPayee('Soccer Taco');
    await clearFlagInStoredRow(payee);

    await addWithLearning(
      [
        tx(accountId, payee, '2016-09-10', dining),
        tx(accountId, payee, '2016-09-11', dining),
        tx(accountId, payee, '2016-09-12', dining),
      ],
      false,
    );

    expect(await categoryRulesFor(payee)).toHaveLength(0);
  });

  test('fewer than three matching transactions are not enough', async () => {
    const { accountId, dining } = await setup();
    const payee = await createPayee('Soccer Taco');
    await clearFlagInStoredRow(payee);

    await addWithLearning([
      tx(accountId, payee, '2016-09-20', dining),
      tx(accountId, payee, '2016-09-21', dining),
    ]);

    expect(await categoryRulesFor(payee)).toHaveLength(0);
  });
});
