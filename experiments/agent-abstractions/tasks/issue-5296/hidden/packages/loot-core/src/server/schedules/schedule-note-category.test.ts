// @ts-strict-ignore
import MockDate from 'mockdate';

import { app as accountsApp } from '#server/accounts/app';
import { app as budgetApp } from '#server/budget/app';
import * as db from '#server/db';
import { loadMappings } from '#server/db/mappings';
import { app as payeesApp } from '#server/payees/app';
import { loadRules } from '#server/transactions/transaction-rules';

import { app as schedulesApp } from './app';

// The server's notion of "today" is fixed to this day under test.
const TODAY = '2017-01-01';

beforeEach(async () => {
  MockDate.set(new Date(2017, 0, 1, 12));
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
  // The schedules app keeps its derived data (account, payee, amount and date
  // of each schedule) up to date while its services run, as in the app.
  schedulesApp.startServices();
});

afterEach(async () => {
  await schedulesApp.stopServices();
  MockDate.reset();
});

type Row = {
  id: string;
  account: string;
  payee: string | null;
  category: string | null;
  notes: string | null;
  amount: number;
  date: number;
  schedule: string | null;
};

async function setup() {
  const accountId = await accountsApp.handlers['account-create']({
    name: 'Checking',
  });
  const payeeId = await payeesApp.handlers['payee-create']({
    name: 'Apple',
  });
  const groupId = await budgetApp.handlers['category-group-create']({
    name: 'Subscriptions',
  });
  const kids = await budgetApp.handlers['category-create']({
    name: 'Kids',
    groupId,
  });
  const streaming = await budgetApp.handlers['category-create']({
    name: 'Streaming',
    groupId,
  });
  return { accountId, payeeId, kids, streaming };
}

function scheduleConditions({ accountId, payeeId, date = TODAY }) {
  return [
    { op: 'is', field: 'payee', value: payeeId },
    { op: 'is', field: 'account', value: accountId },
    { op: 'is', field: 'amount', value: -1299 },
    { op: 'is', field: 'date', value: date },
  ];
}

// The schedule fields are passed through a variable so the call does not
// depend on how the schedule entity type is declared.
function createSchedule(schedule, conditions) {
  return schedulesApp.handlers['schedule/create']({ schedule, conditions });
}

function updateSchedule(schedule, conditions?) {
  return schedulesApp.handlers['schedule/update'](
    conditions ? { schedule, conditions } : { schedule },
  );
}

function postTransaction(id: string, today = false) {
  return schedulesApp.handlers['schedule/post-transaction'](
    today ? { id, today: true } : { id },
  );
}

function transactionsFor(scheduleId: string) {
  return db.all<Row>(
    `SELECT id, account, payee, category, notes, amount, date, schedule
       FROM v_transactions_internal
      WHERE schedule = ? AND tombstone = 0
      ORDER BY date, id`,
    [scheduleId],
  );
}

function allTransactions(accountId: string) {
  return db.all<Row>(
    `SELECT id, account, payee, category, notes, amount, date, schedule
       FROM v_transactions_internal
      WHERE account = ? AND tombstone = 0
      ORDER BY id`,
    [accountId],
  );
}

describe('schedules carry a note and a category onto posted transactions', () => {
  it('posts the transaction with the note and category of the schedule', async () => {
    const { accountId, payeeId, kids } = await setup();
    const schedule = {
      name: 'PBS Kids',
      notes: 'PBS Kids',
      category: kids,
    };
    const id = await createSchedule(
      schedule,
      scheduleConditions({ accountId, payeeId }),
    );

    await postTransaction(id);

    const rows = await transactionsFor(id);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      account: accountId,
      payee: payeeId,
      amount: -1299,
      date: 20170101,
      notes: 'PBS Kids',
      category: kids,
      schedule: id,
    });
  });

  it('keeps two identical schedules apart: each posted transaction gets its own note and category', async () => {
    const { accountId, payeeId, kids, streaming } = await setup();
    const conditions = scheduleConditions({ accountId, payeeId });
    const pbs = { name: 'PBS Kids', notes: 'PBS Kids', category: kids };
    const curiosity = {
      name: 'Curiosity Stream',
      notes: 'Curiosity Stream',
      category: streaming,
    };
    const pbsId = await createSchedule(pbs, conditions);
    const curiosityId = await createSchedule(curiosity, conditions);

    await postTransaction(pbsId);
    await postTransaction(curiosityId);

    const pbsRows = await transactionsFor(pbsId);
    const curiosityRows = await transactionsFor(curiosityId);
    expect(pbsRows).toHaveLength(1);
    expect(curiosityRows).toHaveLength(1);
    expect(pbsRows[0]).toMatchObject({
      notes: 'PBS Kids',
      category: kids,
      amount: -1299,
    });
    expect(curiosityRows[0]).toMatchObject({
      notes: 'Curiosity Stream',
      category: streaming,
      amount: -1299,
    });

    // Two distinct transactions, nothing merged or lost.
    const all = await allTransactions(accountId);
    expect(all).toHaveLength(2);
    expect(all.reduce((s, r) => s + r.amount, 0)).toBe(-2598);
  });

  it('applies the note and category when the transaction is created now, ahead of the due date', async () => {
    const { accountId, payeeId, streaming } = await setup();
    const id = await createSchedule(
      { name: 'Curiosity Stream', notes: 'Annual plan', category: streaming },
      scheduleConditions({ accountId, payeeId, date: '2017-01-06' }),
    );

    await postTransaction(id, true);

    const rows = await transactionsFor(id);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      date: 20170101,
      amount: -1299,
      notes: 'Annual plan',
      category: streaming,
    });
  });

  it('applies the note and category to transactions the schedule posts automatically', async () => {
    const { accountId, payeeId, kids } = await setup();
    const id = await createSchedule(
      {
        name: 'PBS Kids',
        posts_transaction: true,
        notes: 'PBS Kids',
        category: kids,
      },
      scheduleConditions({ accountId, payeeId }),
    );

    await schedulesApp.handlers['schedule/force-run-service'](undefined);

    const rows = await transactionsFor(id);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      account: accountId,
      payee: payeeId,
      date: 20170101,
      amount: -1299,
      notes: 'PBS Kids',
      category: kids,
    });
  });

  it('uses the edited note and category for later postings and leaves earlier ones alone', async () => {
    const { accountId, payeeId, kids, streaming } = await setup();
    const conditions = scheduleConditions({ accountId, payeeId });
    const id = await createSchedule(
      { name: 'Apple', notes: 'Old note', category: kids },
      conditions,
    );
    await postTransaction(id);
    const [first] = await transactionsFor(id);

    // The schedule editor sends the schedule fields together with the conditions.
    const edited = {
      id,
      name: 'Apple',
      notes: 'New note',
      category: streaming,
    };
    await updateSchedule(edited, conditions);
    await postTransaction(id, true);

    const rows = await transactionsFor(id);
    expect(rows).toHaveLength(2);
    const earlier = rows.find(r => r.id === first.id);
    const later = rows.find(r => r.id !== first.id);
    expect(earlier).toMatchObject({ notes: 'Old note', category: kids });
    expect(later).toMatchObject({
      notes: 'New note',
      category: streaming,
      amount: -1299,
    });
  });

  it('keeps the note and category when other schedule fields are edited, and clears them when set to null', async () => {
    const { accountId, payeeId, kids } = await setup();
    const id = await createSchedule(
      { name: 'Apple', notes: 'Family plan', category: kids },
      scheduleConditions({ accountId, payeeId }),
    );

    const renamed = { id, name: 'Apple One' };
    await updateSchedule(renamed);
    await postTransaction(id);
    const before = await transactionsFor(id);
    expect(before).toHaveLength(1);
    expect(before[0]).toMatchObject({ notes: 'Family plan', category: kids });

    const cleared = { id, notes: null, category: null };
    await updateSchedule(cleared);
    await postTransaction(id, true);
    const rows = await transactionsFor(id);
    expect(rows).toHaveLength(2);
    const earlier = rows.find(r => r.id === before[0].id);
    const later = rows.find(r => r.id !== before[0].id);
    expect(earlier).toMatchObject({ notes: 'Family plan', category: kids });
    expect(later.notes || null).toBeNull();
    expect(later.category).toBeNull();
    expect(later.amount).toBe(-1299);
  });

  it('a schedule without a note or category still posts an uncategorized transaction without a note', async () => {
    const { accountId, payeeId } = await setup();
    const id = await createSchedule(
      { name: 'Apple' },
      scheduleConditions({ accountId, payeeId }),
    );

    await postTransaction(id);

    const rows = await transactionsFor(id);
    expect(rows).toHaveLength(1);
    expect(rows[0].notes || null).toBeNull();
    expect(rows[0].category).toBeNull();
    expect(rows[0].amount).toBe(-1299);
  });
});
