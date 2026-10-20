// @ts-strict-ignore
// Hidden test, study 2 zone Z3 step T1: a bank account can be linked to only one
// local account. One test per link handler, through the public handlers; only the
// sync-server boundary (`post`) is mocked.
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

const DUPLICATE = 'This bank account is already linked to another account.';

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

async function expectRefusedWithoutChanges(attempt: () => Promise<unknown>) {
  const before = await snapshot();
  resetBoundary();
  await expect(attempt()).rejects.toThrow(DUPLICATE);
  expect(await snapshot()).toEqual(before);
  expect(vi.mocked(post)).not.toHaveBeenCalled();
  expect(syncEvents()).toEqual([]);
}

async function checkProvider(provider: Provider) {
  // The bank account is linked a first time, as a new local account.
  expect(await link(provider, 'ext-1')).toBe('ok');
  const holder = await accountLinkedTo(provider, 'ext-1');
  expect(holder).toBeTruthy();

  // Linking it again as a new account is refused.
  await expectRefusedWithoutChanges(() => link(provider, 'ext-1'));

  // Linking it into another existing local account is refused too, and that
  // account is left as it was.
  await db.insertAccount({ id: 'local-other', name: 'Other' });
  await expectRefusedWithoutChanges(() =>
    link(provider, 'ext-1', { upgradingId: 'local-other' }),
  );

  // A closed account still holds its link.
  await db.updateAccount({ id: holder.id, closed: 1 });
  await expectRefusedWithoutChanges(() => link(provider, 'ext-1'));
  await db.updateAccount({ id: holder.id, closed: 0 });

  // Re-linking the account that holds the link keeps working.
  resetBoundary();
  expect(await link(provider, 'ext-1', { upgradingId: holder.id })).toBe('ok');
  expect(vi.mocked(post)).toHaveBeenCalled();
  expect(syncEvents()).toHaveLength(1);
  expect(
    (await db.all('SELECT id FROM accounts WHERE account_id = ? AND tombstone = 0', [
      'ext-1',
    ])).map(a => a.id),
  ).toEqual([holder.id]);

  // The same provider account id under another provider is not a conflict.
  const otherProvider = (Object.keys(providers) as Provider[]).find(
    p => p !== provider,
  );
  await db.insertAccount({
    id: 'local-elsewhere',
    name: 'Elsewhere',
    account_id: 'ext-2',
    account_sync_source: otherProvider,
  });
  expect(await link(provider, 'ext-2')).toBe('ok');
  expect(await accountLinkedTo(provider, 'ext-2')).toBeTruthy();

  // A deleted account does not hold its link.
  await db.deleteAccount({ id: holder.id });
  resetBoundary();
  expect(await link(provider, 'ext-1')).toBe('ok');
  const relinked = await accountLinkedTo(provider, 'ext-1');
  expect(relinked).toBeTruthy();
  expect(relinked.id).not.toBe(holder.id);
}

describe('a bank account is linked to at most one local account', () => {
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
});
