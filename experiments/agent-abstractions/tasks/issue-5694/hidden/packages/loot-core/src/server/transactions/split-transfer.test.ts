import { app as accountsApp } from '#server/accounts/app';
// @ts-strict-ignore
import { aqlQuery } from '#server/aql';
import { loadMappings } from '#server/db/mappings';
import { app as transactionsApp } from '#server/transactions/app';
import { q } from '#shared/query';
import {
  splitTransaction,
  ungroupTransactions,
  updateTransaction,
} from '#shared/transactions';

// Behaviour under test: a split transaction whose lines are transfers to the
// same account must show up in that account as ONE transaction for the total
// (a split mirroring the lines), with every line linked as a transfer, so the
// money is counted once and the counterpart can be matched like any transfer.

const createAccount = (fields: { name: string; offBudget?: boolean }) =>
  accountsApp.handlers['account-create'](fields);
const batchUpdate = diff =>
  transactionsApp.handlers['transactions-batch-update'](diff);

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
});

async function transferPayeeFor(accountId: string): Promise<string> {
  const { data } = await aqlQuery(
    q('payees').filter({ transfer_acct: accountId }).select('*'),
  );
  return data[0].id;
}

async function allTransactions() {
  const { data } = await aqlQuery(
    q('transactions').options({ splits: 'all' }).select('*'),
  );
  return data;
}

async function inAccount(accountId: string) {
  return (await allTransactions()).filter(t => t.account === accountId);
}

async function balance(accountId: string) {
  return (await inAccount(accountId))
    .filter(t => !t.is_parent)
    .reduce((sum, t) => sum + t.amount, 0);
}

async function ungrouped(id: string) {
  const { data } = await aqlQuery(
    q('transactions').filter({ id }).select('*').options({ splits: 'grouped' }),
  );
  return ungroupTransactions(data);
}

// Every non-parent transaction whose payee is a transfer payee must be linked
// to a live counterpart in the target account with the opposite amount, and
// the link must be reciprocal. Every live parent must equal the sum of its
// live children.
async function expectConsistentLedger() {
  const all = await allTransactions();
  const { data: payees } = await aqlQuery(q('payees').select('*'));
  const transferAcctOf = new Map(
    payees.filter(p => p.transfer_acct).map(p => [p.id, p.transfer_acct]),
  );
  const byId = new Map<string, (typeof all)[number]>(all.map(t => [t.id, t]));

  for (const t of all) {
    if (t.is_parent) {
      const children = all.filter(c => c.parent_id === t.id);
      expect(children.length).toBeGreaterThan(0);
      expect(children.reduce((s, c) => s + c.amount, 0)).toBe(t.amount);
      continue;
    }
    const target = transferAcctOf.get(t.payee);
    if (!target) continue;
    expect(t.transfer_id).toBeTruthy();
    const other = byId.get(t.transfer_id);
    expect(other).toBeDefined();
    expect(other.account).toBe(target);
    expect(other.transfer_id).toBe(t.id);
    expect(other.amount).toBe(-t.amount);
    expect(transferAcctOf.get(other.payee)).toBe(t.account);
  }
}

// The counterpart account must contain exactly one top-level transaction for
// the transfer, for the full amount, split into lines with the given amounts.
async function expectSingleMirroredSplit(
  accountId: string,
  total: number,
  lineAmounts: number[],
) {
  const rows = await inAccount(accountId);
  const topLevel = rows.filter(t => !t.is_child);
  expect(topLevel).toHaveLength(1);
  expect(topLevel[0].amount).toBe(total);
  expect(topLevel[0].is_parent).toBeTruthy();
  const lines = rows.filter(t => t.parent_id === topLevel[0].id);
  expect(lines.map(t => t.amount).sort((a, b) => a - b)).toEqual(
    [...lineAmounts].sort((a, b) => a - b),
  );
  expect(rows).toHaveLength(1 + lineAmounts.length);
}

async function setup({ offBudget = true } = {}) {
  const checking = await createAccount({ name: 'Checking' });
  const savings = await createAccount({ name: 'Savings', offBudget });
  const toSavings = await transferPayeeFor(savings);
  return { checking, savings, toSavings };
}

async function addTransfer(checking: string, toSavings: string) {
  await batchUpdate({
    added: [
      {
        id: 'trans1',
        account: checking,
        amount: -3000,
        payee: toSavings,
        date: '2025-09-01',
      },
    ],
  });
}

describe('splitting a transfer whose lines all go to the same account', () => {
  test.each([
    ['off-budget', true],
    ['on-budget', false],
  ])(
    'the %s counterpart becomes one matching split (lines given explicitly)',
    async (_label, offBudget) => {
      const { checking, savings, toSavings } = await setup({ offBudget });
      await addTransfer(checking, toSavings);
      expect(await balance(savings)).toBe(3000);

      const { diff } = updateTransaction(await ungrouped('trans1'), {
        id: 'trans1',
        subtransactions: [{ amount: -2000 }, { amount: -1000 }],
      } as never);
      await batchUpdate(diff);

      expect(await balance(checking)).toBe(-3000);
      expect(await balance(savings)).toBe(3000);
      await expectSingleMirroredSplit(savings, 3000, [2000, 1000]);
      await expectConsistentLedger();
    },
  );

  test('splitting from the transaction list (parent payee cleared) mirrors the split', async () => {
    const { checking, savings, toSavings } = await setup();
    await addTransfer(checking, toSavings);

    const { diff } = splitTransaction(
      await ungrouped('trans1'),
      'trans1',
      parent => [
        {
          id: 'line1',
          account: parent.account,
          date: parent.date,
          amount: -2000,
          payee: toSavings,
          is_child: true,
          parent_id: parent.id,
          sort_order: -1,
        } as never,
        {
          id: 'line2',
          account: parent.account,
          date: parent.date,
          amount: -1000,
          payee: toSavings,
          is_child: true,
          parent_id: parent.id,
          sort_order: -2,
        } as never,
      ],
    );
    await batchUpdate(diff);

    expect(await balance(checking)).toBe(-3000);
    expect(await balance(savings)).toBe(3000);
    await expectSingleMirroredSplit(savings, 3000, [2000, 1000]);
    await expectConsistentLedger();
  });

  test('a new split entered with all lines transferring to the account is mirrored once', async () => {
    const { checking, savings, toSavings } = await setup();

    await batchUpdate({
      added: [
        {
          id: 'parent1',
          account: checking,
          amount: -3000,
          payee: toSavings,
          date: '2025-09-01',
          is_parent: true,
        },
        {
          id: 'child1',
          account: checking,
          amount: -1200,
          payee: toSavings,
          date: '2025-09-01',
          is_child: true,
          parent_id: 'parent1',
        },
        {
          id: 'child2',
          account: checking,
          amount: -1800,
          payee: toSavings,
          date: '2025-09-01',
          is_child: true,
          parent_id: 'parent1',
        },
      ],
    });

    expect(await balance(checking)).toBe(-3000);
    expect(await balance(savings)).toBe(3000);
    await expectSingleMirroredSplit(savings, 3000, [1200, 1800]);
    await expectConsistentLedger();
  });

  test('editing the line amounts keeps both sides in step', async () => {
    const { checking, savings, toSavings } = await setup();
    await addTransfer(checking, toSavings);
    await batchUpdate(
      updateTransaction(await ungrouped('trans1'), {
        id: 'trans1',
        subtransactions: [
          { id: 'line1', amount: -2000 },
          { id: 'line2', amount: -1000 },
        ],
      } as never).diff,
    );

    await batchUpdate({
      updated: [
        { id: 'line1', amount: -2500 },
        { id: 'line2', amount: -500 },
      ],
    });

    expect(await balance(checking)).toBe(-3000);
    expect(await balance(savings)).toBe(3000);
    await expectSingleMirroredSplit(savings, 3000, [2500, 500]);
    await expectConsistentLedger();
  });

  test('deleting the split removes its counterpart completely', async () => {
    const { checking, savings, toSavings } = await setup();
    await addTransfer(checking, toSavings);
    await batchUpdate(
      updateTransaction(await ungrouped('trans1'), {
        id: 'trans1',
        subtransactions: [{ amount: -2000 }, { amount: -1000 }],
      } as never).diff,
    );

    await batchUpdate({ deleted: [{ id: 'trans1' }] });

    expect(await inAccount(checking)).toHaveLength(0);
    expect(await inAccount(savings)).toHaveLength(0);
    expect(await balance(savings)).toBe(0);
  });

  test('lines transferring to different accounts still get one plain transfer each', async () => {
    const { checking, savings, toSavings } = await setup();
    const broker = await createAccount({ name: 'Broker', offBudget: true });
    const toBroker = await transferPayeeFor(broker);
    await addTransfer(checking, toSavings);

    await batchUpdate(
      updateTransaction(await ungrouped('trans1'), {
        id: 'trans1',
        subtransactions: [
          { amount: -2000, payee: toSavings },
          { amount: -1000, payee: toBroker },
        ],
      } as never).diff,
    );

    expect(await balance(checking)).toBe(-3000);
    expect(await balance(savings)).toBe(2000);
    expect(await balance(broker)).toBe(1000);
    expect((await inAccount(savings)).filter(t => !t.is_child)).toHaveLength(1);
    expect((await inAccount(broker)).filter(t => !t.is_child)).toHaveLength(1);
    await expectConsistentLedger();
  });
});
