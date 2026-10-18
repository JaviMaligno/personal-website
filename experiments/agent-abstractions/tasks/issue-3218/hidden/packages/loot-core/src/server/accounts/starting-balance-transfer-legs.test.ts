// @ts-strict-ignore
// Issue #3218: bank sync must create the "Starting Balance" of an account that
// holds nothing but transfer legs created from other accounts, exactly once.
import * as asyncStorage from '#platform/server/asyncStorage';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { handlers as mockServer } from '#server/tests/mockSyncServer';
import { loadRules } from '#server/transactions/transaction-rules';
import * as monthUtils from '#shared/months';

import { app as accountsApp } from './app';
import { app as rulesApp } from '../rules/app';
import { app as transactionsApp } from '../transactions/app';

// Pin "today" shortly after the bank data below.
vi.mock('#shared/months', async () => ({
  ...(await vi.importActual('#shared/months')),
  currentDay: vi.fn(),
  currentMonth: vi.fn(),
}));

type BankTx = {
  date: string;
  payeeName: string;
  amount: string;
  transactionId: string;
};

// What the (mocked) SimpleFIN bridge reports, keyed by the bank's account id.
let bank: Record<string, { balance: number; transactions: BankTx[] }> = {};

function bankPayload(externalId: string) {
  const acct = bank[externalId];
  return {
    transactions: {
      all: acct.transactions.map(t => ({
        booked: true,
        date: t.date,
        payeeName: t.payeeName,
        transactionAmount: { amount: t.amount, currency: 'USD' },
        transactionId: t.transactionId,
      })),
      booked: [],
      pending: [],
    },
    balances: [],
    startingBalance: acct.balance,
  };
}

function installBank() {
  mockServer['/simplefin/transactions'] = ({ accountId }) => {
    if (Array.isArray(accountId)) {
      const out: Record<string, unknown> = { errors: {} };
      for (const id of accountId) out[id] = bankPayload(id);
      return out;
    }
    return bankPayload(accountId);
  };
}

const CHECKING_EXT = 'sf-checking';
const SAVINGS_EXT = 'sf-savings';

function resetBank() {
  bank = {
    [CHECKING_EXT]: {
      // 1500.00 now; downloads total -350.00 -> starting balance 1850.00
      balance: 150000,
      transactions: [
        {
          date: '2024-08-05',
          payeeName: 'Grocer',
          amount: '-50.00',
          transactionId: 'chk-2',
        },
        {
          date: '2024-08-03',
          payeeName: 'Transfer to Savings',
          amount: '-300.00',
          transactionId: 'chk-1',
        },
      ],
    },
    [SAVINGS_EXT]: {
      // 800.00 now; downloads total +302.50 -> starting balance 497.50
      balance: 80000,
      transactions: [
        {
          date: '2024-08-06',
          payeeName: 'Interest',
          amount: '2.50',
          transactionId: 'sav-2',
        },
        {
          date: '2024-08-03',
          payeeName: 'Transfer from Checking',
          amount: '300.00',
          transactionId: 'sav-1',
        },
      ],
    },
  };
}

const EXPECTED_SAVINGS_START = 80000 - (30000 + 250);
const EXPECTED_CHECKING_START = 150000 - (-5000 - 30000);

async function transferPayeeOf(accountId: string): Promise<string> {
  const row = await db.first<{ id: string }>(
    'SELECT id FROM payees WHERE transfer_acct = ? AND tombstone = 0',
    [accountId],
  );
  return row.id;
}

async function liveTransactions(accountId: string) {
  return db.all<{
    id: string;
    amount: number;
    date: number;
    starting_balance_flag: number;
    transferred_id: string | null;
  }>(
    `SELECT id, amount, date, starting_balance_flag, transferred_id
       FROM transactions
      WHERE acct = ? AND tombstone = 0 AND isParent = 0`,
    [accountId],
  );
}

async function startingBalances(accountId: string) {
  return (await liveTransactions(accountId)).filter(
    t => t.starting_balance_flag === 1,
  );
}

async function balanceOf(accountId: string) {
  return (await liveTransactions(accountId)).reduce((s, t) => s + t.amount, 0);
}

async function expectSingleStartingBalance(
  accountId: string,
  expectedAmount: number,
) {
  const starts = await startingBalances(accountId);
  expect(starts).toHaveLength(1);
  expect(starts[0].amount).toBe(expectedAmount);
  // It is the opening entry: not dated after anything else in the account.
  const all = await liveTransactions(accountId);
  const earliest = Math.min(
    ...all.filter(t => t.starting_balance_flag !== 1).map(t => t.date),
  );
  expect(starts[0].date).toBeLessThanOrEqual(earliest);
}

async function createLocalAccounts() {
  const checking = await accountsApp.handlers['account-create']({
    name: 'Account 1',
  });
  const savings = await accountsApp.handlers['account-create']({
    name: 'Account 2',
  });
  return { checking, savings };
}

// "Account 1" transactions whose bank payee says it goes to savings become a
// transfer to "Account 2" (pre-stage rule, as in the issue).
async function addTransferRule(checking: string, savings: string) {
  await rulesApp.handlers['rule-add']({
    stage: 'pre',
    conditionsOp: 'and',
    conditions: [
      { op: 'is', field: 'account', value: checking },
      { op: 'is', field: 'imported_payee', value: 'Transfer to Savings' },
    ],
    actions: [
      { op: 'set', field: 'payee', value: await transferPayeeOf(savings) },
    ],
  });
}

async function link(accountId: string, externalId: string, name: string) {
  await accountsApp.handlers['simplefin-accounts-link']({
    externalAccount: {
      account_id: externalId,
      name,
      institution: 'Test Bank',
      orgDomain: 'testbank.example',
      orgId: 'testbank',
      balance: bank[externalId].balance / 100,
    },
    upgradingId: accountId,
  });
}

async function deleteEverything(accountIds: string[]) {
  const rows = await db.all<{ id: string }>(
    `SELECT id FROM transactions
      WHERE tombstone = 0 AND isChild = 0
        AND acct IN (${accountIds.map(() => '?').join(', ')})`,
    accountIds,
  );
  await transactionsApp.handlers['transactions-batch-update']({
    deleted: rows.map(r => ({ id: r.id })),
  });
}

beforeEach(async () => {
  vi.resetAllMocks();
  vi.mocked(monthUtils.currentDay).mockReturnValue('2024-08-15');
  vi.mocked(monthUtils.currentMonth).mockReturnValue('2024-08');
  vi.mocked(asyncStorage.getItem).mockResolvedValue('test-token');
  vi.mocked(asyncStorage.multiGet).mockResolvedValue({
    'user-id': 'user-1',
    'user-key': 'key-1',
  });
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
  resetBank();
  installBank();
});

afterEach(() => {
  delete mockServer['/simplefin/transactions'];
});

describe('starting balance of an account holding only incoming transfer legs', () => {
  test('linking the account creates its starting balance', async () => {
    const { checking, savings } = await createLocalAccounts();
    await addTransferRule(checking, savings);

    await link(checking, CHECKING_EXT, 'Checking');

    // Precondition: the rule put a transfer leg (and nothing else) in Account 2.
    const legs = await liveTransactions(savings);
    expect(legs).toHaveLength(1);
    expect(legs[0].transferred_id).not.toBeNull();
    expect(legs[0].amount).toBe(30000);

    await link(savings, SAVINGS_EXT, 'Savings');

    await expectSingleStartingBalance(checking, EXPECTED_CHECKING_START);
    await expectSingleStartingBalance(savings, EXPECTED_SAVINGS_START);
    expect(await balanceOf(savings)).toBe(80000);
    expect(await balanceOf(checking)).toBe(150000);
  });

  test.each([
    ['simplefin-batch-sync'],
    ['accounts-bank-sync'],
  ])(
    're-syncing emptied accounts one after the other via %s',
    async handler => {
      const { checking, savings } = await createLocalAccounts();
      await addTransferRule(checking, savings);
      await link(checking, CHECKING_EXT, 'Checking');
      await link(savings, SAVINGS_EXT, 'Savings');

      // As in the issue: wipe both accounts, then sync Account 1 and, once it
      // has finished, Account 2.
      await deleteEverything([checking, savings]);
      expect(await liveTransactions(checking)).toHaveLength(0);
      expect(await liveTransactions(savings)).toHaveLength(0);

      const sync = (id: string) => accountsApp.handlers[handler]({ ids: [id] });

      await sync(checking);
      const legs = await liveTransactions(savings);
      expect(legs).toHaveLength(1);
      expect(legs[0].transferred_id).not.toBeNull();

      await sync(savings);

      await expectSingleStartingBalance(checking, EXPECTED_CHECKING_START);
      await expectSingleStartingBalance(savings, EXPECTED_SAVINGS_START);
      expect(await balanceOf(savings)).toBe(80000);

      // Syncing again (nothing new at the bank) must not add a second one.
      await sync(checking);
      await sync(savings);
      await sync(savings);

      await expectSingleStartingBalance(checking, EXPECTED_CHECKING_START);
      await expectSingleStartingBalance(savings, EXPECTED_SAVINGS_START);
      expect(await balanceOf(savings)).toBe(80000);
      expect(await balanceOf(checking)).toBe(150000);
    },
  );

  test.each([
    ['simplefin-batch-sync'],
    ['accounts-bank-sync'],
  ])(
    'an account whose only bank activity is the incoming transfer keeps a single starting balance across syncs (%s)',
    async handler => {
      // The savings bank only reports the transfer: 800.00 now -> 500.00 before.
      bank[SAVINGS_EXT] = {
        balance: 80000,
        transactions: [
          {
            date: '2024-08-03',
            payeeName: 'Transfer from Checking',
            amount: '300.00',
            transactionId: 'sav-1',
          },
        ],
      };
      const { checking, savings } = await createLocalAccounts();
      await addTransferRule(checking, savings);
      await link(checking, CHECKING_EXT, 'Checking');
      await link(savings, SAVINGS_EXT, 'Savings');

      await expectSingleStartingBalance(savings, 50000);
      expect(await balanceOf(savings)).toBe(80000);

      const sync = (id: string) => accountsApp.handlers[handler]({ ids: [id] });
      await sync(checking);
      await sync(savings);
      await sync(savings);

      await expectSingleStartingBalance(savings, 50000);
      await expectSingleStartingBalance(checking, EXPECTED_CHECKING_START);
      expect(await balanceOf(savings)).toBe(80000);
      expect(await balanceOf(checking)).toBe(150000);
    },
  );

  test('an account that already holds its own (non-transfer) transactions gets no starting balance', async () => {
    const { checking, savings } = await createLocalAccounts();
    await transactionsApp.handlers['transactions-batch-update']({
      added: [
        {
          id: 'manual-1',
          account: savings,
          amount: 1234,
          date: '2024-08-01',
          notes: 'entered by hand',
        },
      ],
    });
    // A transfer from Account 1 lands in Account 2 as well.
    await transactionsApp.handlers['transactions-batch-update']({
      added: [
        {
          id: 'manual-2',
          account: checking,
          amount: -30000,
          date: '2024-08-03',
          payee: await transferPayeeOf(savings),
        },
      ],
    });

    await link(savings, SAVINGS_EXT, 'Savings');

    expect(await startingBalances(savings)).toHaveLength(0);
  });
});
