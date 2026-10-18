// @ts-strict-ignore
import { v4 as uuidv4 } from 'uuid';

import { app as accountsApp } from '#server/accounts/app';
import { app as budgetApp } from '#server/budget/app';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { app as payeesApp } from '#server/payees/app';
import { app as rulesApp } from '#server/rules/app';
import { app as transactionsApp } from '#server/transactions/app';
import { loadRules } from '#server/transactions/transaction-rules';

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
});

type Setup = {
  accountId: string;
  food: string;
  restaurants: string;
  storeA: string;
  storeB: string;
  bakery: string;
};

async function setup(): Promise<Setup> {
  const accountId = await accountsApp.handlers['account-create']({
    name: 'Checking',
  });
  const groupId = await budgetApp.handlers['category-group-create']({
    name: 'Everyday',
  });
  const food = await budgetApp.handlers['category-create']({
    name: 'Food',
    groupId,
  });
  const restaurants = await budgetApp.handlers['category-create']({
    name: 'Restaurants',
    groupId,
  });
  const storeA = await payeesApp.handlers['payee-create']({
    name: 'Grocery Store A',
  });
  const storeB = await payeesApp.handlers['payee-create']({
    name: 'Grocery Store B',
  });
  const bakery = await payeesApp.handlers['payee-create']({ name: 'Bakery' });
  return { accountId, food, restaurants, storeA, storeB, bakery };
}

// The user's own grouped rule: payee is one of [..] -> set category.
async function addOneOfRule(payees: string[], category: string) {
  const res = await rulesApp.handlers['rule-add']({
    stage: null,
    conditionsOp: 'and',
    conditions: [{ op: 'oneOf', field: 'payee', value: payees }],
    actions: [{ op: 'set', field: 'category', value: category }],
  });
  expect(res).not.toHaveProperty('error');
  return (res as { id: string }).id;
}

// Live rows of the rules table, decoded.
async function liveRules() {
  const rows = await db.all<{
    id: string;
    stage: string | null;
    conditions_op: string;
    conditions: string;
    actions: string;
  }>(
    'SELECT id, stage, conditions_op, conditions, actions FROM rules WHERE tombstone = 0 ORDER BY id',
  );
  return rows.map(r => ({
    id: r.id,
    stage: r.stage,
    conditionsOp: r.conditions_op,
    conditions: JSON.parse(r.conditions),
    actions: JSON.parse(r.actions),
  }));
}

function ruleHasPayeeCondition(rule, payeeId: string) {
  return rule.conditions.some(
    c =>
      c.field === 'payee' &&
      (c.value === payeeId ||
        (Array.isArray(c.value) && c.value.includes(payeeId))),
  );
}

// The user enters transactions from `payee` and categorises them, the way the
// transaction list saves them (category learning on).
async function enterCategorised(
  accountId: string,
  payee: string,
  category: string,
  dates: string[],
) {
  for (const date of dates) {
    await transactionsApp.handlers['transactions-batch-update']({
      added: [
        {
          id: uuidv4(),
          account: accountId,
          date,
          amount: -2500,
          payee,
          category,
        },
      ],
      learnCategories: true,
    });
  }
}

// Same, but the transactions arrive uncategorised (e.g. imported) and the user
// sets the category on each of them afterwards.
async function enterThenCategorise(
  accountId: string,
  payee: string,
  category: string,
  dates: string[],
) {
  const ids = dates.map(() => uuidv4());
  await transactionsApp.handlers['transactions-batch-update']({
    added: dates.map((date, i) => ({
      id: ids[i],
      account: accountId,
      date,
      amount: -1200,
      payee,
    })),
    learnCategories: true,
  });
  for (const id of ids) {
    await transactionsApp.handlers['transactions-batch-update']({
      updated: [{ id, category }],
      learnCategories: true,
    });
  }
}

async function categoryForNewTransaction(accountId: string, payee: string) {
  const result = await rulesApp.handlers['rules-run']({
    transaction: {
      id: uuidv4(),
      account: accountId,
      date: '2016-12-20',
      amount: -1000,
      payee,
      category: null,
    },
  });
  return result.category;
}

// Recent dates (the test clock is fixed at 2017-01-01).
const DATES = ['2016-12-01', '2016-12-05', '2016-12-09', '2016-12-13'];

describe('category learning with an existing "payee is one of" rule', () => {
  test('does not add a rule for a payee already covered by a one-of rule with the same category', async () => {
    const s = await setup();
    const oneOfId = await addOneOfRule([s.storeA, s.storeB], s.food);
    const before = await liveRules();
    expect(before).toHaveLength(1);

    await enterCategorised(s.accountId, s.storeA, s.food, DATES);

    const after = await liveRules();
    // No extra "payee is Grocery Store A" rule appeared.
    expect(after).toHaveLength(1);
    expect(after).toEqual(before);
    expect(after[0].id).toBe(oneOfId);

    const ruleIds = (await rulesApp.handlers['rules-get']()).map(r => r.id);
    expect(ruleIds).toEqual([oneOfId]);

    // And the one-of rule still categorises both payees.
    expect(await categoryForNewTransaction(s.accountId, s.storeA)).toBe(s.food);
    expect(await categoryForNewTransaction(s.accountId, s.storeB)).toBe(s.food);
  });

  test('also when the category is set on existing transactions afterwards', async () => {
    const s = await setup();
    const oneOfId = await addOneOfRule([s.storeB, s.storeA], s.food);
    const before = await liveRules();

    await enterThenCategorise(s.accountId, s.storeA, s.food, DATES);

    const after = await liveRules();
    expect(after).toEqual(before);
    expect(after.map(r => r.id)).toEqual([oneOfId]);
  });

  test('payees covered by different one-of rules each stay without a redundant rule', async () => {
    const s = await setup();
    await addOneOfRule([s.storeA, s.storeB], s.food);
    await addOneOfRule([s.bakery], s.food);
    const before = await liveRules();
    expect(before).toHaveLength(2);

    await enterCategorised(s.accountId, s.storeB, s.food, DATES);
    await enterCategorised(s.accountId, s.bakery, s.food, DATES);

    expect(await liveRules()).toEqual(before);
  });

  test('a payee that is not in any one-of rule is still learned', async () => {
    const s = await setup();
    const oneOfId = await addOneOfRule([s.storeA, s.storeB], s.food);
    const oneOfBefore = (await liveRules()).find(r => r.id === oneOfId);

    await enterCategorised(s.accountId, s.bakery, s.food, DATES);

    const after = await liveRules();
    expect(after).toHaveLength(2);
    // The user's one-of rule is untouched.
    expect(after.find(r => r.id === oneOfId)).toEqual(oneOfBefore);
    // A rule for the bakery now sets Food.
    // Inspect the learned rule as the rules list shows it (public field names).
    const learned = (await rulesApp.handlers['rules-get']()).filter(
      r => r.id !== oneOfId,
    );
    expect(learned).toHaveLength(1);
    expect(ruleHasPayeeCondition(learned[0], s.bakery)).toBe(true);
    expect(learned[0].actions).toEqual([
      expect.objectContaining({ op: 'set', field: 'category', value: s.food }),
    ]);
    expect(await categoryForNewTransaction(s.accountId, s.bakery)).toBe(s.food);
  });

  test('when the user keeps choosing another category, it is learned and the one-of rule is left alone', async () => {
    const s = await setup();
    const oneOfId = await addOneOfRule([s.storeA, s.storeB], s.food);
    const oneOfBefore = (await liveRules()).find(r => r.id === oneOfId);

    await enterCategorised(s.accountId, s.storeA, s.restaurants, DATES);

    const after = await liveRules();
    // The user's grouped rule is exactly as they wrote it (Grocery Store A is
    // still in its list, it still sets Food).
    expect(after.find(r => r.id === oneOfId)).toEqual(oneOfBefore);
    // New transactions from Grocery Store A get the learned category, those
    // from Grocery Store B still get Food.
    expect(await categoryForNewTransaction(s.accountId, s.storeA)).toBe(
      s.restaurants,
    );
    expect(await categoryForNewTransaction(s.accountId, s.storeB)).toBe(s.food);
  });
});
