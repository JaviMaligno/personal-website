import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { chooseEngine, postChain, lineHash, colonsAsStops } from '../scripts/tts-engine.mjs';
import config, { JAVIER_POST } from '../video.config.mjs';

test('auto falls back per language', () => {
  const noKey = chooseEngine('auto', false);
  assert.equal(noKey.engine, 'kokoro');
  assert.match(noKey.warning ?? '', /CARTESIA_API_KEY/);

  const down = chooseEngine('auto', true, 'HTTP 402');
  assert.equal(down.engine, 'kokoro');
  assert.match(down.warning ?? '', /HTTP 402/);

  const ok = chooseEngine('auto', true);
  assert.equal(ok.engine, 'cartesia');
  assert.equal(ok.warning, undefined);

  assert.throws(() => chooseEngine('cartesia', false), /CARTESIA_API_KEY/);
});

test('explicit engines are honoured', () => {
  assert.deepEqual(chooseEngine('kokoro', true), { engine: 'kokoro' });
  assert.deepEqual(chooseEngine('cartesia', true), { engine: 'cartesia' });
  // Asked for Cartesia explicitly: an outage is an error, never a silent switch of voice.
  assert.throws(() => chooseEngine('cartesia', true, 'HTTP 500'), /HTTP 500/);
});

test('post chain: optional, trimmed, and never one that changes a line length', () => {
  assert.equal(postChain(undefined), '');
  assert.equal(postChain(null), '');
  assert.equal(postChain({}), '');
  assert.equal(postChain({ post: '' }), '');
  assert.equal(postChain({ post: '  highpass=f=85,afftdn=nr=10 ' }), 'highpass=f=85,afftdn=nr=10');
  assert.throws(() => postChain({ post: 42 }), /string/);
  assert.throws(() => postChain({ post: 'highpass=f=85,atempo=1.1' }), /atempo/);
  assert.throws(() => postChain({ post: 'silenceremove=1:0:-50dB' }), /silenceremove/);
});

test('line hash: unchanged without post, different with it', () => {
  const parts = ['cartesia', 'voice', 'model', 1];
  const legacy = createHash('sha1').update('cartesia|voice|model|1|Hello').digest('hex');
  assert.equal(lineHash(parts, 'Hello'), legacy); // existing caches stay valid
  assert.equal(lineHash(parts, 'Hello', ''), legacy);
  const a = lineHash(parts, 'Hello', 'highpass=f=85');
  const b = lineHash(parts, 'Hello', 'highpass=f=90');
  assert.notEqual(a, legacy);
  assert.notEqual(a, b);
});

test('video.config voices parse: the default EN voice carries a valid post chain', () => {
  const en = config.tts.voices.en;
  assert.equal(en.id, 'b7abe199-5f62-45fd-b77a-d12a1fe80a36');
  assert.equal(postChain(en), JAVIER_POST);
  for (const v of Object.values(config.tts.kokoro.voices)) postChain(v);
});

test('colons are voiced as full stops, captions untouched', () => {
  assert.equal(colonsAsStops('It said: one workflow per article.'), 'It said. One workflow per article.');
  assert.equal(colonsAsStops('The verdict: the checker is clumsy.'), 'The verdict. The checker is clumsy.');
  assert.equal(colonsAsStops('Locked out, it said so: "I could not confirm."'), 'Locked out, it said so. "I could not confirm."');
  assert.equal(colonsAsStops('Every move must match: 100%.'), 'Every move must match. 100%.');
  assert.equal(colonsAsStops('Iterating failed nearly all of those too:'), 'Iterating failed nearly all of those too.');
  // No space after the colon: clock times, ratios and URLs stay as they are.
  assert.equal(colonsAsStops('At 10:30, a 3:1 split on https://example.com.'), 'At 10:30, a 3:1 split on https://example.com.');
  assert.equal(colonsAsStops('No colon here.'), 'No colon here.');
  // The template turns it on by default.
  assert.equal(config.tts.colonsAsStops, true);
});
