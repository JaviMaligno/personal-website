// @ts-strict-ignore
// Hidden test, study 2 zone Z3 step T2: linking accounts from a new bank-sync
// provider (Fintegra). Through the public handler; only the sync-server boundary
// (`post`) is mocked.
import * as asyncStorage from '#platform/server/asyncStorage';
import * as connection from '#platform/server/connection';
import { app } from '#server/accounts/app';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { post } from '#server/post';

vi.mock('#server/post', async () => ({
  ...(await vi.importActual('#server/post')),
  post: vi.fn(),
}));

const HANDLER = 'fintegra-accounts-link';
const DUPLICATE = 'This bank account is already linked to another account.';
const TRANSACTIONS_URL = 'https://test.env/fintegra/transactions';

beforeEach(async () => {
  vi.mocked(post).mockReset();
  vi.mocked(post).mockImplementation(async () => ({
    transactions: { all: [], booked: [], pending: [] },
    balances: [],
    startingBalance: 0,
  }));
  vi.mocked(connection.send).mockReset();
  // Global storage is mocked by the test setup; the bank-sync downloads need a
  // signed-in user.
  vi.mocked(asyncStorage.getItem).mockImplementation(async key =>
    key === 'user-token' ? 'token-1' : null,
  );
  await global.emptyDatabase()();
  await loadMappings();
});

function externalAccount(accountId: string) {
  return {
    account_id: accountId,
    name: 'Fintegra ' + accountId,
    institution: 'Bank F',
    orgId: 'org-f',
    balance: 0,
  };
}

function link(accountId: string, extra = {}) {
  return app.handlers[HANDLER]({
    externalAccount: externalAccount(accountId),
    startingDate: '2024-01-01',
    startingBalance: 500,
    ...extra,
  } as never);
}

function syncEvents() {
  return vi
    .mocked(connection.send)
    .mock.calls.filter(
      ([name, args]) =>
        name === 'sync-event' && (args as { type?: string })?.type === 'success',
    )
    .map(([, args]) => args);
}

function transactionRequests() {
  return vi.mocked(post).mock.calls.filter(([url]) => url === TRANSACTIONS_URL);
}

async function linkedAccount(accountId: string) {
  return db.first<db.DbAccount>(
    "SELECT * FROM accounts WHERE account_id = ? AND account_sync_source = 'fintegra' AND tombstone = 0",
    [accountId],
  );
}

async function snapshot() {
  return {
    accounts: await db.all('SELECT * FROM accounts ORDER BY id'),
    payees: await db.all('SELECT * FROM payees ORDER BY id'),
    transactions: await db.all('SELECT * FROM transactions ORDER BY id'),
  };
}

describe('linking Fintegra accounts', () => {
  it('Fintegra', async () => {
    // A new on-budget account.
    expect(await link('ext-1')).toBe('ok');
    const account = await linkedAccount('ext-1');
    expect(account).toMatchObject({
      name: 'Fintegra ext-1',
      official_name: 'Fintegra ext-1',
      offbudget: 0,
      closed: 0,
    });
    const bank = await db.first<db.DbBank>('SELECT * FROM banks WHERE id = ?', [
      account.bank,
    ]);
    expect(bank).toMatchObject({ bank_id: 'org-f', name: 'Bank F' });
    expect(
      await db.all('SELECT * FROM payees WHERE transfer_acct = ? AND tombstone = 0', [
        account.id,
      ]),
    ).toHaveLength(1);

    // The initial sync goes to the sync server's Fintegra endpoint.
    const requests = transactionRequests();
    expect(requests).toHaveLength(1);
    const [, body, headers] = requests[0];
    expect(body).toMatchObject({ accountId: 'ext-1', startDate: '2024-01-01' });
    expect(headers).toMatchObject({ 'X-ACTUAL-TOKEN': 'token-1' });

    // ...and records the chosen starting balance on the chosen date.
    const starting = await db.all<db.DbTransaction>(
      'SELECT * FROM transactions WHERE acct = ? AND tombstone = 0',
      [account.id],
    );
    expect(starting).toHaveLength(1);
    expect(starting[0]).toMatchObject({
      amount: 500,
      date: 20240101,
      starting_balance_flag: 1,
    });
    expect(syncEvents()).toEqual([
      { type: 'success', tables: ['transactions', 'accounts'] },
    ]);

    // A second bank account of the same connection, off budget, shares the bank.
    expect(await link('ext-2', { offBudget: true })).toBe('ok');
    const offBudget = await linkedAccount('ext-2');
    expect(offBudget).toMatchObject({ offbudget: 1, bank: account.bank });

    // Linking into an existing local account turns it into a Fintegra account.
    await db.insertAccount({ id: 'local-1', name: 'Local' });
    const payeesBefore = await db.all('SELECT * FROM payees');
    expect(await link('ext-3', { upgradingId: 'local-1' })).toBe('ok');
    expect(await linkedAccount('ext-3')).toMatchObject({
      id: 'local-1',
      name: 'Local',
      bank: account.bank,
    });
    // No transfer payee is created for an account that already exists.
    expect(await db.all('SELECT * FROM payees')).toHaveLength(
      payeesBefore.length,
    );

    // A missing local account is reported as for the other providers.
    await expect(link('ext-4', { upgradingId: 'nope' })).rejects.toThrow(
      'Account with ID nope not found.',
    );

    // The bank account is linked to at most one local account.
    const before = await snapshot();
    vi.mocked(post).mockClear();
    vi.mocked(connection.send).mockClear();
    await expect(link('ext-1')).rejects.toThrow(DUPLICATE);
    await expect(link('ext-1', { upgradingId: 'local-1' })).rejects.toThrow(
      DUPLICATE,
    );
    expect(await snapshot()).toEqual(before);
    expect(vi.mocked(post)).not.toHaveBeenCalled();
    expect(syncEvents()).toEqual([]);
  });
});
