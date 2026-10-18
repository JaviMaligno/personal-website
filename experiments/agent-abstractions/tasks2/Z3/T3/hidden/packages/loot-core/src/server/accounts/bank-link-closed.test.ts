// @ts-strict-ignore
// Hidden test, study 2 zone Z3 step T3: a closed account cannot be linked to a
// bank account. One test per link handler (including the provider added in T2),
// through the public handlers; only the sync-server boundary (`post`) is mocked.
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

async function checkProvider(provider: Provider) {
  await db.insertAccount({ id: 'local-closed', name: 'Closed', closed: 1 });
  const before = await snapshot();
  resetBoundary();
  await expect(
    link(provider, 'ext-1', { upgradingId: 'local-closed' }),
  ).rejects.toThrow(CLOSED);
  expect(await snapshot()).toEqual(before);
  expect(vi.mocked(post)).not.toHaveBeenCalled();
  expect(syncEvents()).toEqual([]);

  // Once reopened, the same account can be linked.
  await db.updateAccount({ id: 'local-closed', closed: 0 });
  resetBoundary();
  expect(await link(provider, 'ext-1', { upgradingId: 'local-closed' })).toBe(
    'ok',
  );
  expect(await accountLinkedTo(provider, 'ext-1')).toMatchObject({
    id: 'local-closed',
  });
  expect(syncEvents()).toHaveLength(1);

  // Closing the linked account and re-linking it is refused the same way.
  await db.updateAccount({ id: 'local-closed', closed: 1 });
  const closedBefore = await snapshot();
  resetBoundary();
  await expect(
    link(provider, 'ext-1', { upgradingId: 'local-closed' }),
  ).rejects.toThrow(CLOSED);
  expect(await snapshot()).toEqual(closedBefore);
  expect(vi.mocked(post)).not.toHaveBeenCalled();
  expect(syncEvents()).toEqual([]);

  // Linking a bank account as a new account is not affected.
  resetBoundary();
  expect(await link(provider, 'ext-2')).toBe('ok');
  expect(await accountLinkedTo(provider, 'ext-2')).toMatchObject({ closed: 0 });
}

describe('a closed account cannot be linked', () => {
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
