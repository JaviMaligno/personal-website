import { installAPI } from '#server/api';
import * as db from '#server/db';
import * as prefs from '#server/prefs';
import type { ServerHandlers } from '#types/server-handlers';

import { app as budgetApp } from './app';

type CategoryRow = {
  id: string;
  name: string;
  cat_group: string | null;
  tombstone: number;
};

describe('a category always keeps a group', () => {
  const handlers = installAPI({} as unknown as ServerHandlers);

  let groupId: string;
  let otherGroupId: string;
  let catId: string;

  beforeEach(global.emptyDatabase());

  beforeEach(async () => {
    await prefs.loadPrefs();

    for (const name of [
      'get-categories',
      'get-category-groups',
      'category-create',
      'category-update',
      'category-delete',
      'category-group-create',
    ] as const) {
      // @ts-expect-error - wiring the budget app's handlers into the API
      handlers[name] = budgetApp.handlers[name];
    }

    groupId = await handlers['api/category-group-create']({
      group: { name: 'Income sources' },
    });
    otherGroupId = await handlers['api/category-group-create']({
      group: { name: 'Bonuses' },
    });
    catId = await handlers['api/category-create']({
      category: {
        name: 'Holiday Bonus',
        group_id: groupId,
        is_income: true,
      },
    });
  });

  async function categoryRows(): Promise<CategoryRow[]> {
    return db.all<CategoryRow>(
      'SELECT id, name, cat_group, tombstone FROM categories WHERE tombstone = 0',
    );
  }

  async function expectStillInGroup(id: string, expectedGroup: string) {
    const rows = (await categoryRows()).filter(r => r.id === id);
    expect(rows).toHaveLength(1);
    expect(rows[0].cat_group).toBe(expectedGroup);

    const listed = await handlers['api/categories-get']({});
    const matches = listed.filter(c => c.id === id);
    expect(matches).toHaveLength(1);
    expect(matches[0].group_id).toBe(expectedGroup);

    const groups = await handlers['api/category-groups-get']();
    const group = groups.find(g => g.id === expectedGroup);
    expect(group?.categories?.map(c => c.id)).toContain(id);
  }

  it.each([
    ['an empty string', ''],
    ['null', null],
  ])(
    'the API rejects moving a category to %s group and leaves it where it was',
    async (_label, emptyGroup) => {
      const before = await categoryRows();

      await expect(
        handlers['api/category-update']({
          id: catId,
          fields: { name: 'Holiday Bonus', group_id: emptyGroup },
        }),
      ).rejects.toThrow();

      await expectStillInGroup(catId, groupId);
      expect(await categoryRows()).toHaveLength(before.length);
    },
  );

  it.each([
    ['an empty string', ''],
    ['null', null],
  ])(
    'the app category-update handler rejects %s group and leaves the category where it was',
    async (_label, emptyGroup) => {
      await expect(
        handlers['category-update']({
          id: catId,
          name: 'Holiday Bonus',
          is_income: true,
          hidden: false,
          group: emptyGroup,
        }),
      ).rejects.toThrow();

      await expectStillInGroup(catId, groupId);
    },
  );

  it('the category stays fully manageable after a rejected attempt', async () => {
    await expect(
      handlers['api/category-update']({
        id: catId,
        fields: { name: 'Holiday Bonus', group_id: '' },
      }),
    ).rejects.toThrow();

    // its name is still taken by the (visible) category, so it cannot be
    // recreated in the same group
    await expect(
      handlers['api/category-create']({
        category: { name: 'Holiday Bonus', group_id: groupId, is_income: true },
      }),
    ).rejects.toThrow();

    await handlers['api/category-update']({
      id: catId,
      fields: { name: 'Year-end Bonus' },
    });
    const renamed = (await handlers['api/categories-get']({})).find(
      c => c.id === catId,
    );
    expect(renamed).toMatchObject({
      name: 'Year-end Bonus',
      group_id: groupId,
    });

    await handlers['api/category-delete']({ id: catId });
    expect(
      (await handlers['api/categories-get']({})).some(c => c.id === catId),
    ).toBe(false);
  });

  it('an update that does not mention the group keeps the current group', async () => {
    await handlers['api/category-update']({
      id: catId,
      fields: { name: 'Other', hidden: true },
    });

    const rows = (await categoryRows()).filter(r => r.id === catId);
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ name: 'Other', cat_group: groupId });

    const hidden = await handlers['api/categories-get']({ hidden: true });
    expect(hidden.find(c => c.id === catId)).toMatchObject({
      name: 'Other',
      group_id: groupId,
      hidden: true,
    });
  });

  it('moving a category to another existing group still works', async () => {
    await handlers['api/category-update']({
      id: catId,
      fields: { name: 'Holiday Bonus', group_id: otherGroupId },
    });

    await expectStillInGroup(catId, otherGroupId);
    const groups = await handlers['api/category-groups-get']();
    expect(
      groups.find(g => g.id === groupId)?.categories?.map(c => c.id) ?? [],
    ).not.toContain(catId);
  });
});
