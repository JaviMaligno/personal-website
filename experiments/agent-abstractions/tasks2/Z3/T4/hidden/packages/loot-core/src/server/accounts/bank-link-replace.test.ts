// @ts-strict-ignore
// Hidden test, study 2 zone Z3 step T4: linking can take over a bank account that
// another local account holds, on request. One test per link handler (including
// the provider added in T2), through the public handlers; only the sync-server
// boundary (`post`) is mocked.
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

function bankResponse() {
  return {
    transactions: { all: [], booked: [], pending: [] },
    balances: [],
    startingBalance: 0,
  };
}

beforeEach(async () => {
  vi.mocked(post).mockReset();
  vi.mocked(post).mockImplementation(async () => bankResponse());
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
    name: 'Checking ' + accountId,
    official_name: 'Official Checking ' + accountId,
    mask: '1234',
    institution: 'Bank A',
    orgDomain: 'bank-a.example',
    orgId: 'org-a',
    balance: 0,
  };
}

const providers = {
  goCardless: {
    handler: 'gocardless-accounts-link',
    params: (accountId: string) => ({
      requisitionId: 'req-1',
      account: externalAccount(accountId),
    }),
  },
  simpleFin: {
    handler: 'simplefin-accounts-link',
    params: (accountId: string) => ({
      externalAccount: externalAccount(accountId),
    }),
  },
  pluggyai: {
    handler: 'pluggyai-accounts-link',
    params: (accountId: string) => ({
      externalAccount: externalAccount(accountId),
    }),
  },
  akahu: {
    handler: 'akahu-accounts-link',
    params: (accountId: string) => ({
      externalAccount: externalAccount(accountId),
    }),
  },
  enableBanking: {
    handler: 'enablebanking-accounts-link',
    params: (accountId: string) => ({
      externalAccount: externalAccount(accountId),
    }),
  },
  fintegra: {
    handler: 'fintegra-accounts-link',
    params: (accountId: string) => ({
      externalAccount: externalAccount(accountId),
    }),
  },
};

type Provider = keyof typeof providers;

function link(provider: Provider, accountId: string, extra = {}) {
  const p = providers[provider];
  return app.handlers[p.handler]({
    ...p.params(accountId),
    startingDate: '2024-01-01',
    startingBalance: 500,
    ...extra,
  } as never);
}

async function accountLinkedTo(provider: Provider, accountId: string) {
  return db.first<db.DbAccount>(
    'SELECT * FROM accounts WHERE account_id = ? AND account_sync_source = ? AND tombstone = 0',
    [accountId, provider],
  );
}

async function snapshot() {
  return {
    accounts: await db.all('SELECT * FROM accounts ORDER BY id'),
    payees: await db.all('SELECT * FROM payees ORDER BY id'),
    transactions: await db.all('SELECT * FROM transactions ORDER BY id'),
  };
}

function resetBoundary() {
  vi.mocked(post).mockClear();
  vi.mocked(connection.send).mockClear();
}

// The notifications that tell the client a bank sync finished.
function syncEvents() {
  return vi
    .mocked(connection.send)
    .mock.calls.filter(
      ([name, args]) =>
        name === 'sync-event' && (args as { type?: string })?.type === 'success',
    );
}

const CLOSED =
  'Closed accounts cannot be linked to a bank account. Reopen the account first.';
const TAKE_OVER = { replaceExistingLink: true };

async function transactionsOf(id: string) {
  return db.all(
    'SELECT id, amount, date FROM transactions WHERE acct = ? AND tombstone = 0 ORDER BY id',
    [id],
  );
}

async function expectUnlinked(id: string, closed: 0 | 1) {
  expect(
    await db.first(
      'SELECT account_id, bank, account_sync_source, tombstone, closed FROM accounts WHERE id = ?',
      [id],
    ),
  ).toEqual({
    account_id: null,
    bank: null,
    account_sync_source: null,
    tombstone: 0,
    closed,
  });
}

// Every request the link made went to the provider's transactions endpoint (the
// initial sync of the new link): nothing about the account losing the link.
function expectOnlyInitialSync() {
  const urls = vi.mocked(post).mock.calls.map(([url]) => String(url));
  expect(urls).toHaveLength(1);
  expect(urls[0]).toMatch(/\/transactions$/);
  expect(syncEvents()).toHaveLength(1);
}

async function checkProvider(provider: Provider) {
  expect(await link(provider, 'ext-1')).toBe('ok');
  const first = await accountLinkedTo(provider, 'ext-1');
  const firstTransactions = await transactionsOf(first.id);
  expect(firstTransactions).toHaveLength(1);

  // Without the option, the link is still refused.
  await expect(link(provider, 'ext-1')).rejects.toThrow(
    'This bank account is already linked to another account.',
  );

  // With it, a new account takes the link; the previous holder is unlinked and
  // keeps its transactions.
  resetBoundary();
  expect(await link(provider, 'ext-1', TAKE_OVER)).toBe('ok');
  const second = await accountLinkedTo(provider, 'ext-1');
  expect(second.id).not.toBe(first.id);
  await expectUnlinked(first.id, 0);
  expect(await transactionsOf(first.id)).toEqual(firstTransactions);
  expectOnlyInitialSync();

  // An existing local account can take the link too.
  await db.insertAccount({ id: 'local-2', name: 'Local 2' });
  resetBoundary();
  expect(
    await link(provider, 'ext-1', { ...TAKE_OVER, upgradingId: 'local-2' }),
  ).toBe('ok');
  expect(await accountLinkedTo(provider, 'ext-1')).toMatchObject({
    id: 'local-2',
  });
  await expectUnlinked(second.id, 0);
  expectOnlyInitialSync();

  // The option does not allow linking into a closed account; nothing changes.
  await db.insertAccount({ id: 'local-3', name: 'Local 3', closed: 1 });
  const before = await snapshot();
  resetBoundary();
  await expect(
    link(provider, 'ext-1', { ...TAKE_OVER, upgradingId: 'local-3' }),
  ).rejects.toThrow(CLOSED);
  expect(await snapshot()).toEqual(before);
  expect(vi.mocked(post)).not.toHaveBeenCalled();

  // A closed holder gives up its link and stays closed.
  await db.updateAccount({ id: 'local-2', closed: 1 });
  resetBoundary();
  expect(await link(provider, 'ext-1', TAKE_OVER)).toBe('ok');
  const third = await accountLinkedTo(provider, 'ext-1');
  expect(third.id).not.toBe('local-2');
  await expectUnlinked('local-2', 1);
  expectOnlyInitialSync();

  // Taking over when nothing holds the link is an ordinary link.
  resetBoundary();
  expect(await link(provider, 'ext-9', TAKE_OVER)).toBe('ok');
  expect(await accountLinkedTo(provider, 'ext-9')).toBeTruthy();
  expectOnlyInitialSync();
}

describe('linking can take over an existing link on request', () => {
  it('GoCardless', async () => {
    await checkProvider('goCardless');
  });

  it('SimpleFIN', async () => {
    await checkProvider('simpleFin');
  });

  it('Pluggy.ai', async () => {
    await checkProvider('pluggyai');
  });

  it('Akahu', async () => {
    await checkProvider('akahu');
  });

  it('Enable Banking', async () => {
    await checkProvider('enableBanking');
  });

  it('Fintegra', async () => {
    await checkProvider('fintegra');
  });
});
