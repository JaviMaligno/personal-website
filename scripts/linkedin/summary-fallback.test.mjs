import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generateWithFallback, isRetryable } from './summary-fallback.js';

const SUMMARY = 'A summary that is comfortably longer than fifty characters in total.';
const unavailable = () => new Error('[503 Service Unavailable] This model is currently experiencing high demand.');

function recorder() {
  const waits = [];
  return { waits, sleep: async (ms) => { waits.push(ms); } };
}

test('503 and 429 are retryable; a bad request is not', () => {
  assert.equal(isRetryable(unavailable()), true);
  assert.equal(isRetryable(new Error('[429 Too Many Requests] RESOURCE_EXHAUSTED')), true);
  assert.equal(isRetryable(new Error('fetch failed')), true);
  assert.equal(isRetryable(new Error('[400 Bad Request] invalid argument')), false);
});

test('a transient 503 is retried on the same model before moving on', async () => {
  const { waits, sleep } = recorder();
  const calls = [];
  let n = 0;
  const summary = await generateWithFallback({
    models: ['a', 'b'],
    callModel: async (m) => { calls.push(m); if (n++ < 2) throw unavailable(); return SUMMARY; },
    delaysMs: [10, 20],
    sleep,
  });
  assert.equal(summary, SUMMARY);
  assert.deepEqual(calls, ['a', 'a', 'a']);
  assert.deepEqual(waits, [10, 20]);
});

test('a non-retryable error skips straight to the next model', async () => {
  const { waits, sleep } = recorder();
  const calls = [];
  const summary = await generateWithFallback({
    models: ['a', 'b'],
    callModel: async (m) => { calls.push(m); if (m === 'a') throw new Error('[400 Bad Request]'); return SUMMARY; },
    delaysMs: [10, 20],
    sleep,
  });
  assert.equal(summary, SUMMARY);
  assert.deepEqual(calls, ['a', 'b']);
  assert.deepEqual(waits, []);
});

test('when every Gemini model stays unavailable, the last-resort provider answers', async () => {
  const { sleep } = recorder();
  const calls = [];
  const summary = await generateWithFallback({
    models: ['a', 'b'],
    callModel: async (m) => { calls.push(m); throw unavailable(); },
    lastResort: { name: 'openrouter', call: async () => SUMMARY },
    delaysMs: [1],
    sleep,
  });
  assert.equal(summary, SUMMARY);
  assert.deepEqual(calls, ['a', 'a', 'b', 'b']);
});

test('without a last resort, the error names every failure', async () => {
  const { sleep } = recorder();
  await assert.rejects(
    generateWithFallback({
      models: ['a'],
      callModel: async () => { throw unavailable(); },
      delaysMs: [],
      sleep,
    }),
    /All summary providers failed.*503/,
  );
});

test('a summary that is too short counts as a failure', async () => {
  const { sleep } = recorder();
  const summary = await generateWithFallback({
    models: ['a', 'b'],
    callModel: async (m) => (m === 'a' ? 'short' : SUMMARY),
    delaysMs: [1],
    sleep,
  });
  assert.equal(summary, SUMMARY);
});
