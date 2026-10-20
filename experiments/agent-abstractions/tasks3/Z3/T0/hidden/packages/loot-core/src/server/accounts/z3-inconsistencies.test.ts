// @ts-strict-ignore
// Study 3, zone Z3, step T0 (hidden): the behaviour a consolidation of bank-sync
// account linking must keep (spec section 3). Today only Pluggy.ai sends the budget
// file id to the sync server; only GoCardless stores the account mask and the
// provider's official name; only Akahu reports just `transactions` as changed after
// the first sync. One test per difference, through the public link handlers; only
// the sync-server boundary (`post`) is mocked.
import * as asyncStorage from '#platform/server/asyncStorage';
import * as connection from '#platform/server/connection';
import { app } from '#server/accounts/app';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { post } from '#server/post';
import * as prefs from '#server/prefs';

vi.mock('#server/post', async () => ({
  ...(await vi.importActual('#server/post')),
  post: vi.fn(),
}));

const FILE_ID = 'budget-file-1';

beforeEach(async () => {
  vi.mocked(post).mockReset();
  vi.mocked(post).mockImplementation(async () => ({
    transactions: { all: [], booked: [], pending: [] },
    balances: [],
    startingBalance: 0,
  }));
  vi.mocked(connection.send).mockReset();
  vi.mocked(asyncStorage.getItem).mockImplementation(async key =>
    key === 'user-token' ? 'token-1' : null,
  );
  await global.emptyDatabase()();
  await loadMappings();
  await prefs.loadPrefs();
  await prefs.savePrefs({ cloudFileId: FILE_ID }, { avoidSync: true });
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
    params: (accountId: string) => ({ externalAccount: externalAccount(accountId) }),
  },
  pluggyai: {
    handler: 'pluggyai-accounts-link',
    params: (accountId: string) => ({ externalAccount: externalAccount(accountId) }),
  },
  akahu: {
    handler: 'akahu-accounts-link',
    params: (accountId: string) => ({ externalAccount: externalAccount(accountId) }),
  },
  enableBanking: {
    handler: 'enablebanking-accounts-link',
    params: (accountId: string) => ({ externalAccount: externalAccount(accountId) }),
  },
};

type Provider = keyof typeof providers;

async function link(provider: Provider, accountId: string) {
  const p = providers[provider];
  return app.handlers[p.handler]({
    ...p.params(accountId),
    startingDate: '2024-01-01',
    startingBalance: 500,
  } as never);
}

async function linkedRow(provider: Provider, accountId: string) {
  return db.first<{ mask: string | null; name: string; official_name: string | null }>(
    'SELECT mask, name, official_name FROM accounts WHERE account_id = ? AND account_sync_source = ? AND tombstone = 0',
    [accountId, provider],
  );
}

// Headers of every request made to the sync server since the last reset.
function sentHeaders() {
  return vi.mocked(post).mock.calls.map(call => (call[2] ?? {}) as Record<string, string>);
}

// Tables named by the notification that tells the client the first sync finished.
function syncSuccessTables() {
  return vi
    .mocked(connection.send)
    .mock.calls.filter(
      ([name, args]) =>
        name === 'sync-event' && (args as { type?: string })?.type === 'success',
    )
    .map(([, args]) => (args as { tables: string[] }).tables);
}

describe('Z3 T0 bank-sync account linking keeps its provider differences', () => {
  it('Pluggy.ai sends the budget file id to the sync server when linking', async () => {
    expect(await link('pluggyai', 'ext-p')).toBe('ok');
    const headers = sentHeaders();
    expect(headers.length).toBeGreaterThan(0);
    expect(headers.some(h => h['X-Actual-File-Id'] === FILE_ID)).toBe(true);
  });

  it('GoCardless stores the mask and official name, the other providers the name and no mask', async () => {
    expect(await link('goCardless', 'ext-g')).toBe('ok');
    expect(await linkedRow('goCardless', 'ext-g')).toEqual({
      mask: '1234',
      name: 'Checking ext-g',
      official_name: 'Official Checking ext-g',
    });
    for (const provider of ['simpleFin', 'pluggyai', 'akahu', 'enableBanking'] as const) {
      const accountId = 'ext-' + provider;
      expect(await link(provider, accountId)).toBe('ok');
      expect(await linkedRow(provider, accountId)).toEqual({
        mask: null,
        name: 'Checking ' + accountId,
        official_name: 'Checking ' + accountId,
      });
    }
  });

  it('Akahu reports only transactions as changed, the other providers transactions and accounts', async () => {
    for (const provider of Object.keys(providers) as Provider[]) {
      vi.mocked(connection.send).mockClear();
      expect(await link(provider, 'ext-s-' + provider)).toBe('ok');
      expect(syncSuccessTables()).toEqual([
        provider === 'akahu' ? ['transactions'] : ['transactions', 'accounts'],
      ]);
    }
  });
});
