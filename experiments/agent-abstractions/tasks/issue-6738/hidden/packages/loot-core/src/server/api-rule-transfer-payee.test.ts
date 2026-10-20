// @ts-strict-ignore
// Behaviour: when a transaction is added through the API's "add transactions"
// call and a rule assigns it a transfer payee (i.e. "transfer to account B"),
// the transfer must be complete: account B gets exactly one linked counterpart
// with the opposite amount, and account B's balance moves accordingly.
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { handlers } from '#server/main';
import * as prefs from '#server/prefs';
import { loadRules } from '#server/transactions/transaction-rules';

vi.mock('#server/post');

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
  await prefs.loadPrefs();
});

afterEach(() => {
  prefs.unloadPrefs();
});

async function setup() {
  const checking = await handlers['api/account-create']({
    account: { name: 'Checking' },
  });
  const savings = await handlers['api/account-create']({
    account: { name: 'Savings' },
  });
  const other = await handlers['api/account-create']({
    account: { name: 'Other' },
  });

  const payees = await handlers['api/payees-get']();
  const toSavings = payees.find(p => p.transfer_acct === savings);
  expect(toSavings).toBeDefined();

  // "When the account is Checking, set the payee to the Savings transfer payee"
  await handlers['api/rule-create']({
    rule: {
      stage: null,
      conditionsOp: 'and',
      conditions: [{ field: 'account', op: 'is', value: checking }],
      actions: [{ op: 'set', field: 'payee', value: toSavings.id }],
    },
  });

  return { checking, savings, other, toSavings };
}

async function liveRows(accountId: string) {
  return db.all<{
    id: string;
    acct: string;
    amount: number;
    transfer_id: string | null;
    description: string | null;
    date: number;
  }>(
    `SELECT id, acct, amount, transferred_id AS transfer_id, description, date
       FROM transactions
      WHERE acct = ? AND tombstone = 0 AND isParent = 0`,
    [accountId],
  );
}

describe('API add transactions with a rule that sets a transfer payee', () => {
  it('creates the counterpart transaction in the destination account', async () => {
    const { checking, savings, toSavings } = await setup();

    await handlers['api/transactions-add']({
      accountId: checking,
      transactions: [
        { date: '2026-01-21', amount: -12300, notes: 'Some notes' },
      ],
    });

    const source = await handlers['api/transactions-get']({
      accountId: checking,
    });
    expect(source).toHaveLength(1);
    expect(source[0].amount).toBe(-12300);
    expect(source[0].payee).toBe(toSavings.id);

    const dest = await handlers['api/transactions-get']({
      accountId: savings,
    });
    expect(dest).toHaveLength(1);
    expect(dest[0].amount).toBe(12300);
    expect(dest[0].date).toBe('2026-01-21');

    // Both legs point at each other.
    expect(source[0].transfer_id).toBe(dest[0].id);
    expect(dest[0].transfer_id).toBe(source[0].id);
  });

  it('updates the destination account balance', async () => {
    const { checking, savings } = await setup();

    await handlers['api/transactions-add']({
      accountId: checking,
      transactions: [{ date: '2026-01-21', amount: -12300 }],
    });

    expect(await handlers['api/account-balance']({ id: checking })).toBe(
      -12300,
    );
    expect(await handlers['api/account-balance']({ id: savings })).toBe(
      12300,
    );
  });

  it('creates exactly one linked leg per added transaction (stored state)', async () => {
    const { checking, savings } = await setup();

    await handlers['api/transactions-add']({
      accountId: checking,
      transactions: [
        { date: '2026-01-20', amount: -1000 },
        { date: '2026-01-21', amount: -2550 },
      ],
    });

    const src = await liveRows(checking);
    const dst = await liveRows(savings);
    expect(src).toHaveLength(2);
    expect(dst).toHaveLength(2);

    for (const s of src) {
      const legs = dst.filter(d => d.transfer_id === s.id);
      expect(legs).toHaveLength(1);
      expect(s.transfer_id).toBe(legs[0].id);
      expect(legs[0].amount).toBe(-s.amount);
      expect(legs[0].date).toBe(s.date);
    }
    expect(dst.map(d => d.amount).sort((a, b) => a - b)).toEqual([1000, 2550]);
  });

  it('does not duplicate the leg when transfers are explicitly requested', async () => {
    const { checking, savings } = await setup();

    await handlers['api/transactions-add']({
      accountId: checking,
      transactions: [{ date: '2026-01-21', amount: -12300 }],
      runTransfers: true,
    });

    const src = await liveRows(checking);
    const dst = await liveRows(savings);
    expect(src).toHaveLength(1);
    expect(dst).toHaveLength(1);
    expect(src[0].transfer_id).toBe(dst[0].id);
    expect(dst[0].transfer_id).toBe(src[0].id);
    expect(dst[0].amount).toBe(12300);
  });

  it('leaves other accounts alone when the rule does not match', async () => {
    const { savings, other } = await setup();

    await handlers['api/transactions-add']({
      accountId: other,
      transactions: [{ date: '2026-01-21', amount: -500 }],
    });

    const otherRows = await liveRows(other);
    expect(otherRows).toHaveLength(1);
    expect(otherRows[0].transfer_id).toBeNull();
    expect(await liveRows(savings)).toHaveLength(0);
    expect(await handlers['api/account-balance']({ id: savings })).toBe(0);
  });
});
