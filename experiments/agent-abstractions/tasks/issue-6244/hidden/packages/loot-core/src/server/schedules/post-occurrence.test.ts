// @ts-strict-ignore
import MockDate from "mockdate";

import { app as accountsApp } from "#server/accounts/app";
import { aqlQuery } from "#server/aql";
import { loadMappings } from "#server/db/mappings";
import { runHandler } from "#server/mutators";
import { app as payeesApp } from "#server/payees/app";
import { app as schedulesApp } from "#server/schedules/app";
import { loadRules } from "#server/transactions/transaction-rules";
import { q } from "#shared/query";

// In tests "today" is 2017-01-01. A weekly schedule starting on Monday
// 2017-01-02 has upcoming occurrences 2017-01-02, -09, -16, -23, ...
const AMOUNT = -12345;

beforeEach(async () => {
  await global.emptyDatabase()();
  await loadMappings();
  await loadRules();
  MockDate.set(new Date(2017, 0, 1, 12));
  schedulesApp.startServices();
});

afterEach(async () => {
  MockDate.reset();
  await schedulesApp.stopServices();
});

async function setupWeeklySchedule() {
  const accountId = await runHandler(accountsApp.handlers["account-create"], {
    name: "Checking",
  });
  const payeeId = await runHandler(payeesApp.handlers["payee-create"], {
    name: "Home Depot",
  });
  const scheduleId = await runHandler(
    schedulesApp.handlers["schedule/create"],
    {
      schedule: { name: "Weekly payment" },
      conditions: [
        { op: "is", field: "payee", value: payeeId },
        { op: "is", field: "account", value: accountId },
        { op: "is", field: "amount", value: AMOUNT },
        {
          op: "isapprox",
          field: "date",
          value: {
            start: "2017-01-02",
            frequency: "weekly",
            interval: 1,
            patterns: [],
            skipWeekend: false,
            weekendSolveMode: "after",
          },
        },
      ],
    }
  );
  return { accountId, payeeId, scheduleId };
}

async function post(args) {
  await runHandler(schedulesApp.handlers["schedule/post-transaction"], args);
}

async function scheduledTransactions(scheduleId: string) {
  const { data } = await aqlQuery(
    q("transactions")
      .filter({ schedule: scheduleId })
      .select(["date", "amount", "account", "payee", "schedule"])
      .options({ splits: "none" })
  );
  return [...data].sort((a, b) =>
    a.date < b.date ? -1 : a.date > b.date ? 1 : 0
  );
}

async function nextDate(scheduleId: string) {
  const { data } = await aqlQuery(
    q("schedules").filter({ id: scheduleId }).select(["next_date"])
  );
  return data[0].next_date;
}

describe("posting a chosen upcoming occurrence of a schedule", () => {
  it("starts with the first upcoming occurrence as the next date", async () => {
    const { scheduleId } = await setupWeeklySchedule();
    expect(await nextDate(scheduleId)).toBe("2017-01-02");
  });

  it("posts a later occurrence on the requested date, not on the next date", async () => {
    const { scheduleId, accountId, payeeId } = await setupWeeklySchedule();

    await post({ id: scheduleId, date: "2017-01-16" });

    const txns = await scheduledTransactions(scheduleId);
    expect(txns).toEqual([
      expect.objectContaining({
        date: "2017-01-16",
        amount: AMOUNT,
        account: accountId,
        payee: payeeId,
        schedule: scheduleId,
      }),
    ]);
  });

  it("posting the next occurrence and then later ones creates one transaction per chosen date", async () => {
    const { scheduleId } = await setupWeeklySchedule();

    // The first upcoming occurrence, posted the usual way.
    await post({ id: scheduleId });
    // The following upcoming occurrences, chosen explicitly.
    await post({ id: scheduleId, date: "2017-01-09" });
    await post({ id: scheduleId, date: "2017-01-16" });

    const txns = await scheduledTransactions(scheduleId);
    expect(txns.map((t) => [t.date, t.amount])).toEqual([
      ["2017-01-02", AMOUNT],
      ["2017-01-09", AMOUNT],
      ["2017-01-16", AMOUNT],
    ]);
  });

  it("moves the next date past a posted later occurrence", async () => {
    const { scheduleId } = await setupWeeklySchedule();

    await post({ id: scheduleId });
    await post({ id: scheduleId, date: "2017-01-09" });
    expect(await nextDate(scheduleId)).toBe("2017-01-16");

    await post({ id: scheduleId, date: "2017-01-16" });
    expect(await nextDate(scheduleId)).toBe("2017-01-23");

    // Posting "the next occurrence" now posts the one after the last posted,
    // instead of duplicating an already posted date.
    await post({ id: scheduleId });
    const dates = (await scheduledTransactions(scheduleId)).map((t) => t.date);
    expect(dates).toEqual([
      "2017-01-02",
      "2017-01-09",
      "2017-01-16",
      "2017-01-23",
    ]);
  });

  it("still posts on the next date when no date is given", async () => {
    const { scheduleId } = await setupWeeklySchedule();

    await post({ id: scheduleId });

    const txns = await scheduledTransactions(scheduleId);
    expect(txns.map((t) => [t.date, t.amount])).toEqual([
      ["2017-01-02", AMOUNT],
    ]);
  });

  it("still posts on today when asked to post today", async () => {
    const { scheduleId } = await setupWeeklySchedule();

    await post({ id: scheduleId, today: true });

    const txns = await scheduledTransactions(scheduleId);
    expect(txns.map((t) => [t.date, t.amount])).toEqual([
      ["2017-01-01", AMOUNT],
    ]);
  });
});
