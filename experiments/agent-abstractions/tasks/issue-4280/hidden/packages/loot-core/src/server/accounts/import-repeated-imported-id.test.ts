import * as db from "#server/db";
import { loadMappings } from "#server/db/mappings";
import { loadRules } from "#server/transactions/transaction-rules";

import { app as accountsApp } from "./app";

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
});

const handlers = accountsApp.handlers;

async function createAccount(name = "Checking") {
  return handlers["account-create"]({ name, balance: 0 });
}

type Row = {
  date: string;
  amount: number;
  payee_name?: string;
  imported_id?: string;
  notes?: string;
  forceAddTransaction?: boolean;
};

function importRows(accountId: string, rows: Row[], isPreview = false) {
  return handlers["transactions-import"]({
    accountId,
    transactions: rows.map((r) => ({ account: accountId, ...r })),
    isPreview,
  });
}

function getTransactions(accountId: string) {
  return db.all<{
    id: string;
    date: number;
    amount: number;
    notes: string | null;
    imported_id: string | null;
  }>(
    `SELECT id, date, amount, notes, imported_id
       FROM v_transactions
       WHERE account = ? AND is_parent = 0
       ORDER BY date, amount, id`,
    [accountId]
  );
}

async function getBalance(accountId: string) {
  return handlers["account-balance"]({ id: accountId, cutoff: "2099-12-31" });
}

describe("importing a batch that repeats an imported_id", () => {
  test("two identical rows with the same imported_id create one transaction", async () => {
    const acct = await createAccount();
    const row = {
      date: "2024-03-05",
      amount: -2599,
      payee_name: "Coffee Shop",
      imported_id: "csv-hash-1",
    };

    const result = await importRows(acct, [row, { ...row }]);

    expect(result.errors).toEqual([]);
    expect(result.added).toHaveLength(1);

    const txns = await getTransactions(acct);
    expect(txns).toHaveLength(1);
    expect(txns[0].imported_id).toBe("csv-hash-1");
    expect(txns[0].amount).toBe(-2599);
    expect(await getBalance(acct)).toBe(-2599);
  });

  test("a batch with repeats ends in the same state as importing the rows one call at a time", async () => {
    const rows: Row[] = [
      {
        date: "2024-03-01",
        amount: -1000,
        payee_name: "Grocer",
        imported_id: "a",
      },
      {
        date: "2024-03-02",
        amount: 250000,
        payee_name: "Employer",
        imported_id: "b",
      },
      {
        date: "2024-03-01",
        amount: -1000,
        payee_name: "Grocer",
        imported_id: "a",
      },
      {
        date: "2024-03-03",
        amount: -4550,
        payee_name: "Fuel",
        imported_id: "c",
      },
      {
        date: "2024-03-02",
        amount: 250000,
        payee_name: "Employer",
        imported_id: "b",
      },
      {
        date: "2024-03-01",
        amount: -1000,
        payee_name: "Grocer",
        imported_id: "a",
      },
    ];

    const batched = await createAccount("Batched");
    const result = await importRows(batched, rows);
    expect(result.added).toHaveLength(3);

    const oneByOne = await createAccount("One by one");
    for (const row of rows) {
      await importRows(oneByOne, [row]);
    }

    const strip = (ts: Awaited<ReturnType<typeof getTransactions>>) =>
      ts.map(({ date, amount, notes, imported_id }) => ({
        date,
        amount,
        notes,
        imported_id,
      }));
    const batchedTxns = await getTransactions(batched);
    expect(batchedTxns).toHaveLength(3);
    expect(strip(batchedTxns)).toEqual(strip(await getTransactions(oneByOne)));
    expect(await getBalance(batched)).toBe(-1000 + 250000 - 4550);
    expect(await getBalance(batched)).toBe(await getBalance(oneByOne));
  });

  test("re-importing the same batch does not add anything", async () => {
    const acct = await createAccount();
    const rows: Row[] = [
      {
        date: "2024-04-10",
        amount: -799,
        payee_name: "Stream",
        imported_id: "x1",
      },
      {
        date: "2024-04-10",
        amount: -799,
        payee_name: "Stream",
        imported_id: "x1",
      },
      {
        date: "2024-04-11",
        amount: -1200,
        payee_name: "Lunch",
        imported_id: "x2",
      },
    ];

    await importRows(acct, rows);
    const second = await importRows(acct, rows);

    expect(second.added).toHaveLength(0);
    expect(await getTransactions(acct)).toHaveLength(2);
    expect(await getBalance(acct)).toBe(-799 - 1200);
  });

  test("the first occurrence wins for the amount and a later one can fill in missing notes", async () => {
    const acct = await createAccount();

    await importRows(acct, [
      {
        date: "2024-05-01",
        amount: -500,
        payee_name: "Bakery",
        imported_id: "dup",
      },
      {
        date: "2024-05-01",
        amount: -700,
        payee_name: "Bakery",
        imported_id: "dup",
        notes: "croissants",
      },
    ]);

    const txns = await getTransactions(acct);
    expect(txns).toHaveLength(1);
    expect(txns[0].amount).toBe(-500);
    expect(txns[0].notes).toBe("croissants");
    expect(await getBalance(acct)).toBe(-500);
  });

  test("a repeated row explicitly marked to be force-added is still added", async () => {
    const acct = await createAccount();
    const row = {
      date: "2024-06-01",
      amount: -3000,
      payee_name: "Gym",
      imported_id: "gym-1",
    };

    const result = await importRows(acct, [
      row,
      { ...row, forceAddTransaction: true },
    ]);

    expect(result.added).toHaveLength(2);
    expect(await getTransactions(acct)).toHaveLength(2);
    expect(await getBalance(acct)).toBe(-6000);
  });

  test("rows with different imported_ids are all kept, even if otherwise identical", async () => {
    const acct = await createAccount();
    const base = { date: "2024-07-01", amount: -150, payee_name: "Vending" };

    const result = await importRows(acct, [
      { ...base, imported_id: "v1" },
      { ...base, imported_id: "v2" },
      { ...base, imported_id: "v3" },
    ]);

    expect(result.added).toHaveLength(3);
    const txns = await getTransactions(acct);
    expect(txns.map((t) => t.imported_id).sort()).toEqual(["v1", "v2", "v3"]);
    expect(await getBalance(acct)).toBe(-450);
  });

  test("identical rows without an imported_id are all kept", async () => {
    const acct = await createAccount();
    const row = { date: "2024-07-02", amount: -200, payee_name: "Parking" };

    const result = await importRows(acct, [row, { ...row }]);

    expect(result.added).toHaveLength(2);
    expect(await getTransactions(acct)).toHaveLength(2);
    expect(await getBalance(acct)).toBe(-400);
  });

  test("the same imported_id in two different accounts is kept in each", async () => {
    const one = await createAccount("One");
    const two = await createAccount("Two");
    const row = {
      date: "2024-08-01",
      amount: -999,
      payee_name: "Shop",
      imported_id: "shared",
    };

    await importRows(one, [row, { ...row }]);
    await importRows(two, [row, { ...row }]);

    expect(await getTransactions(one)).toHaveLength(1);
    expect(await getTransactions(two)).toHaveLength(1);
    expect(await getBalance(one)).toBe(-999);
    expect(await getBalance(two)).toBe(-999);
  });

  test("a preview of a batch with repeats reports what the real import does and writes nothing", async () => {
    const acct = await createAccount();
    const rows: Row[] = [
      {
        date: "2024-09-01",
        amount: -4200,
        payee_name: "Books",
        imported_id: "p1",
      },
      {
        date: "2024-09-01",
        amount: -4200,
        payee_name: "Books",
        imported_id: "p1",
      },
      {
        date: "2024-09-02",
        amount: -100,
        payee_name: "Snack",
        imported_id: "p2",
      },
    ];

    const preview = await importRows(acct, rows, true);
    expect(preview.errors).toEqual([]);
    expect(preview.added).toHaveLength(2);
    expect(await getTransactions(acct)).toHaveLength(0);
    expect(await getBalance(acct)).toBe(0);

    const real = await importRows(acct, rows);
    expect(real.added).toHaveLength(preview.added.length);
    expect(await getTransactions(acct)).toHaveLength(2);
  });
});
