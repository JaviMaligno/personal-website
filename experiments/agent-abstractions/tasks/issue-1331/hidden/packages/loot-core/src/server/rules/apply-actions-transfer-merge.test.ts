// @ts-strict-ignore
import { app as accountsApp } from "#server/accounts/app";
import { aqlQuery } from "#server/aql";
import * as db from "#server/db";
import { loadMappings } from "#server/db/mappings";
import { app as payeesApp } from "#server/payees/app";
import { app as rulesApp } from "#server/rules/app";
import { app as transactionsApp } from "#server/transactions/app";
import { loadRules, resetState } from "#server/transactions/transaction-rules";
import { q } from "#shared/query";

beforeEach(async () => {
  await global.emptyDatabase()();
  resetState();
  await loadMappings();
  await loadRules();
});

const DATE = "2023-07-10";

async function transferPayeeOf(accountId: string): Promise<string> {
  const row = await db.first<{ id: string }>(
    "SELECT id FROM payees WHERE transfer_acct = ? AND tombstone = 0",
    [accountId]
  );
  return row.id;
}

async function liveTransactions(accountId?: string) {
  let query = q("transactions").select("*");
  if (accountId) {
    query = query.filter({ account: accountId });
  }
  const { data } = await aqlQuery(query);
  return data;
}

async function balanceOf(accountId: string): Promise<number> {
  const props = await accountsApp.handlers["account-properties"]({
    id: accountId,
  });
  return props.balance;
}

async function setUp(amountInB = -2500) {
  const accountA = await accountsApp.handlers["account-create"]({
    name: "Account A",
  });
  const accountB = await accountsApp.handlers["account-create"]({
    name: "Account B",
  });
  const payeeA = await payeesApp.handlers["payee-create"]({ name: "a" });
  const payeeB = await payeesApp.handlers["payee-create"]({ name: "b" });

  // Money moved from B into A, imported/entered as two ordinary transactions.
  await transactionsApp.handlers["transaction-add"]({
    id: "trans-in-a",
    account: accountA,
    payee: payeeB,
    amount: 2500,
    date: DATE,
  });
  await transactionsApp.handlers["transaction-add"]({
    id: "trans-in-b",
    account: accountB,
    payee: payeeA,
    amount: amountInB,
    date: DATE,
  });

  return { accountA, accountB };
}

// The rule editor's "Apply actions": the user selects the existing
// transaction in the given account and applies a "set payee" action to it.
async function applySetPayee(
  accountId: string,
  originalId: string,
  payeeId: string
) {
  const inAccount = await liveTransactions(accountId);
  let selected = inAccount.filter((t) => t.id === originalId);
  if (selected.length === 0) {
    // The original row may have been replaced by an equivalent one.
    selected = inAccount;
  }
  expect(selected).toHaveLength(1);
  const result = await rulesApp.handlers["rule-apply-actions"]({
    transactions: selected,
    actions: [{ op: "set", field: "payee", value: payeeId, type: "id" }],
  });
  expect(result).not.toBeNull();
}

async function expectLinkedPair(accountA: string, accountB: string) {
  const all = await liveTransactions();
  expect(all).toHaveLength(2);

  const inA = await liveTransactions(accountA);
  const inB = await liveTransactions(accountB);
  expect(inA).toHaveLength(1);
  expect(inB).toHaveLength(1);

  expect(inA[0].amount).toBe(2500);
  expect(inB[0].amount).toBe(-2500);

  // The two legs point at each other.
  expect(inA[0].transfer_id).toBe(inB[0].id);
  expect(inB[0].transfer_id).toBe(inA[0].id);

  // Each leg's payee is the transfer payee of the other account.
  expect(inA[0].payee).toBe(await transferPayeeOf(accountB));
  expect(inB[0].payee).toBe(await transferPayeeOf(accountA));

  expect(await balanceOf(accountA)).toBe(2500);
  expect(await balanceOf(accountB)).toBe(-2500);
}

describe("applying rule actions that turn two existing opposite transactions into a transfer", () => {
  test("links the existing transactions instead of double counting (B side first)", async () => {
    const { accountA, accountB } = await setUp();

    // Rule: payee "a" -> transfer to account A, applied to the transaction in B.
    await applySetPayee(
      accountB,
      "trans-in-b",
      await transferPayeeOf(accountA)
    );
    // Rule: payee "b" -> transfer to account B, applied to the transaction in A.
    await applySetPayee(
      accountA,
      "trans-in-a",
      await transferPayeeOf(accountB)
    );

    await expectLinkedPair(accountA, accountB);
  });

  test("links the existing transactions instead of double counting (A side first)", async () => {
    const { accountA, accountB } = await setUp();

    await applySetPayee(
      accountA,
      "trans-in-a",
      await transferPayeeOf(accountB)
    );
    await applySetPayee(
      accountB,
      "trans-in-b",
      await transferPayeeOf(accountA)
    );

    await expectLinkedPair(accountA, accountB);
  });

  test("a transaction with a different amount in the other account is left alone", async () => {
    const { accountA, accountB } = await setUp(-3000);

    await applySetPayee(
      accountA,
      "trans-in-a",
      await transferPayeeOf(accountB)
    );

    const inA = await liveTransactions(accountA);
    const inB = await liveTransactions(accountB);
    expect(inA).toHaveLength(1);
    expect(inB).toHaveLength(2);

    const untouched = inB.find((t) => t.id === "trans-in-b");
    expect(untouched.amount).toBe(-3000);
    expect(untouched.transfer_id).toBeNull();

    const counterpart = inB.find((t) => t.id !== "trans-in-b");
    expect(counterpart.amount).toBe(-2500);
    expect(counterpart.transfer_id).toBe(inA[0].id);
    expect(inA[0].transfer_id).toBe(counterpart.id);

    expect(await balanceOf(accountA)).toBe(2500);
    expect(await balanceOf(accountB)).toBe(-5500);
  });
});
