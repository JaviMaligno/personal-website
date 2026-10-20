// RuleTester tests for the agent lint rules (plan Task 4, Step 1).
//
// Kept in the harness, not in the variant tree: loot-core's vitest collects any
// `*.test.mjs` under packages/loot-core, which would change the test set of AL/APL
// and break the A vs AL / AP vs APL equivalence.
//
// Run against a built variant (eslint is resolved from it); rules the variant does
// not ship are skipped (AL: raw-write, float-money; APL: withAllowList wrapper):
//   LOOT_CORE=work/variants/AL/packages/loot-core node --test substrate/lint/rules.test.mjs
//   LOOT_CORE=work/variants/APL/packages/loot-core node --test substrate/lint/rules.test.mjs
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { describe, it } from 'node:test';
import { pathToFileURL } from 'node:url';

const loot = path.resolve(process.env.LOOT_CORE ?? '');
const req = createRequire(path.join(loot, 'package.json'));
const { RuleTester } = req('eslint');
const tsParser = req('@typescript-eslint/parser');
const ruleFile = name => path.join(loot, 'eslint-rules', `${name}.mjs`);
const has = name => existsSync(ruleFile(name));
const load = async name => import(pathToFileURL(ruleFile(name)).href);
const rule = async name => (await load(name)).default;

RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

const t = new RuleTester({ languageOptions: { parser: tsParser } });
const X = 'src/server/x.ts';

if (has('no-raw-synced-write')) t.run('no-raw-synced-write', await rule('no-raw-synced-write'), {
  valid: [
    { code: "runQuery('SELECT * FROM transactions')", filename: X },
    { code: "db.runQuery('DELETE FROM kvcache_key')", filename: X },
    { code: "runQuery('UPDATE transactions SET x=1')", filename: 'src/server/db/index.ts' },
    { code: 'db.run(`UPDATE categories SET a = 1`)', filename: 'src/server/sync/reset.ts' },
    { code: 'db.runQuery(sql, [1])', filename: X },
    {
      code: "db.runQuery('DELETE FROM categories WHERE is_income = 0')",
      filename: 'src/server/api.ts',
      options: [{ allow: [{ file: 'src/server/api.ts', sql: 'DELETE FROM categories WHERE is_income = 0' }] }],
    },
    {
      code: 'db.run(`\n  UPDATE   cleanup_groups\n  SET tombstone = 1`)',
      filename: 'src/server/budget/cleanup-groups.ts',
      options: [{ allow: [{ file: 'src/server/budget/cleanup-groups.ts', sql: 'UPDATE cleanup_groups SET tombstone = 1' }] }],
    },
  ],
  invalid: [
    { code: "db.runQuery('UPDATE transactions SET amount = ?', [1])", filename: X, errors: 1 },
    { code: 'db.runQuery(`DELETE FROM categories WHERE id = ?`, [id])', filename: X, errors: 1 },
    { code: "db.execQuery('INSERT OR REPLACE INTO payees (id) VALUES (1)')", filename: X, errors: 1 },
    { code: 'db.run(`\n UPDATE zero_budgets SET amount = ${a}`)', filename: X, errors: 1 },
    // the allow-list is per file
    {
      code: "db.runQuery('DELETE FROM categories WHERE is_income = 0')",
      filename: X,
      options: [{ allow: [{ file: 'src/server/api.ts', sql: 'DELETE FROM categories WHERE is_income = 0' }] }],
      errors: 1,
    },
  ],
});

if (has('no-float-money')) t.run('no-float-money', await rule('no-float-money'), {
  valid: [
    { code: 'const x = amountToInteger(amount)', filename: X },
    { code: 'const x = count * 100', filename: X },
    { code: 'const x = amount * 100', filename: 'src/shared/util.ts' },
    {
      code: 'const x = t.amount * 100;',
      filename: X,
      options: [{ allow: [{ file: X, line: 'const x = t.amount * 100;' }] }],
    },
  ],
  invalid: [
    { code: 'const x = amount * 100', filename: X, errors: 1 },
    { code: 'const y = t.balance / 100', filename: X, errors: 1 },
    { code: 'const y = 100 * row.budgeted', filename: X, errors: 1 },
    { code: 'const y = spent / 10 ** 2', filename: X, errors: 1 },
    { code: 'const y = carryover * Math.pow(10, d)', filename: X, errors: 1 },
    { code: 'const y = t?.amount * 100', filename: X, errors: 1 },
  ],
});

t.run('no-send-messages', await rule('no-send-messages'), {
  valid: [
    { code: 'await sendMessages(msgs)', filename: 'src/server/db/index.ts' },
    { code: 'await sendMessages(msgs)', filename: 'src/server/sync/index.ts' },
    {
      code: "import { sendMessages } from './sync';",
      filename: 'src/server/prefs.ts',
      options: [{ allow: [{ file: 'src/server/prefs.ts', line: "import { sendMessages } from './sync';" }] }],
    },
    {
      code: 'await sendMessages(m);\nawait sendMessages(m);',
      filename: 'src/server/prefs.ts',
      options: [{ allow: [{ file: 'src/server/prefs.ts', line: 'await sendMessages(m);', count: 2 }] }],
    },
  ],
  invalid: [
    { code: "import { sendMessages } from '#server/sync';", filename: X, errors: 1 },
    { code: 'await sync.sendMessages(msgs)', filename: X, errors: 1 },
    { code: "import { sendMessages as s } from '#server/sync';", filename: X, errors: 1 },
    // an entry covers `count` (default 1) identical sites: a second identical line is reported
    {
      code: 'await sendMessages(m);\nawait sendMessages(m);',
      filename: 'src/server/prefs.ts',
      options: [{ allow: [{ file: 'src/server/prefs.ts', line: 'await sendMessages(m);' }] }],
      errors: 1,
    },
  ],
});

const mutatorRequired = await rule('mutator-required');
t.run('mutator-required (form mutator, A+L)', mutatorRequired, {
  valid: [
    { code: "app.method('category-create', mutator(undoable(createCategory)))", filename: X },
    { code: "app.method('transaction-add', mutator(addTransaction))", filename: X },
    { code: "app.method('get-categories', getCategories)", filename: X },
    { code: "app.method('query', runQuery)", filename: X },
    { code: "other.method('category-create', createCategory)", filename: X },
    {
      code: "app.method('sync', fullSync)",
      filename: 'src/server/sync/app.ts',
      options: [{ form: 'mutator', allow: [{ file: 'src/server/sync/app.ts', name: 'sync' }] }],
    },
  ],
  invalid: [
    { code: "app.method('category-create', createCategory)", filename: X, errors: 1 },
    { code: "app.method('category-create', undoable(createCategory))", filename: X, errors: 1 },
    {
      code: "app.method('sync', fullSync)",
      filename: X,
      options: [{ form: 'mutator', allow: [{ file: 'src/server/sync/app.ts', name: 'sync' }] }],
      errors: 1,
    },
  ],
});

t.run('mutator-required (form mutation, A+ +L)', mutatorRequired, {
  valid: [
    { code: "app.method(...mutation('category-create', createCategory))", filename: X, options: [{ form: 'mutation' }] },
    { code: "app.method(...mutation('payees-merge', merge, meta))", filename: X, options: [{ form: 'mutation' }] },
    { code: "app.method('get-categories', getCategories)", filename: X, options: [{ form: 'mutation' }] },
    {
      code: "app.method('transaction-add', mutator(addTransaction))",
      filename: X,
      options: [{ form: 'mutation', allow: [{ file: X, name: 'transaction-add' }] }],
    },
  ],
  invalid: [
    { code: "app.method('category-create', createCategory)", filename: X, options: [{ form: 'mutation' }], errors: 1 },
    { code: "app.method('category-create', mutator(undoable(createCategory)))", filename: X, options: [{ form: 'mutation' }], errors: 1 },
    { code: "app.method('transaction-add', mutator(addTransaction))", filename: X, options: [{ form: 'mutation' }], errors: 1 },
    { code: "app.method(...other('category-create', createCategory))", filename: X, options: [{ form: 'mutation' }], errors: 1 },
  ],
});

if (has('with-allow-list')) {
  const { withAllowList } = await load('with-allow-list');
  const ts = req('typescript-eslint').plugin.rules;
  const anyRule = withAllowList(ts['no-explicit-any']);
  const tsComment = withAllowList(ts['ban-ts-comment'], [
    { 'ts-expect-error': true, 'ts-ignore': true, 'ts-nocheck': true, 'ts-check': false },
  ]);
  t.run('withAllowList(no-explicit-any)', anyRule, {
    valid: [
      { code: 'const a: unknown = 1;', filename: X },
      {
        code: 'return rows[0] as any;',
        filename: 'src/server/db/index.ts',
        languageOptions: { parserOptions: { ecmaFeatures: { globalReturn: true } } },
        options: [{ allow: [{ file: 'src/server/db/index.ts', line: 'return rows[0] as any;' }] }],
      },
    ],
    invalid: [
      { code: 'const a: any = 1;', filename: X, errors: 1 },
      {
        code: 'const a: any = 1;',
        filename: X,
        options: [{ allow: [{ file: 'src/server/other.ts', line: 'const a: any = 1;' }] }],
        errors: 1,
      },
    ],
  });
  t.run('withAllowList(ban-ts-comment, strict)', tsComment, {
    valid: [
      {
        code: '// @ts-expect-error fix me\nconst a = 1;',
        filename: X,
        options: [{ allow: [{ file: X, line: '// @ts-expect-error fix me' }] }],
      },
    ],
    invalid: [
      { code: '// @ts-expect-error with a long description\nconst a = 1;', filename: X, errors: 1 },
      { code: '// @ts-ignore\nconst a = 1;', filename: X, errors: 1 },
      {
        code: '// @ts-expect-error fix me\nconst a = 1;\n// @ts-expect-error fix me\nconst b = 1;',
        filename: X,
        options: [{ allow: [{ file: X, line: '// @ts-expect-error fix me' }] }],
        errors: 1,
      },
    ],
  });
}
