import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tx } from '../src/types.ts';

test('tx picks the language and falls back to EN when ES is empty', () => {
  assert.equal(tx('same', 'es'), 'same');
  assert.equal(tx({ en: 'hello', es: 'hola' }, 'es'), 'hola');
  assert.equal(tx({ en: 'hello', es: '' }, 'es'), 'hello');
});
