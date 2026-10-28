import { test } from 'node:test';
import assert from 'node:assert/strict';
import { musicVolume, DUCK_RAMP } from '../src/music.ts';

const music = { volume: 0.2, duck: 0.3 };
const spans = [{ from: 3, to: 5 }];
const near = (a: number, b: number) => assert.ok(Math.abs(a - b) < 1e-9, `${a} is not ≈ ${b}`);

test('music ducks under a line and comes back between lines', () => {
  near(musicVolume(4, spans, 20, music), 0.2 * 0.3);
  near(musicVolume(10, spans, 20, music), 0.2);
  // Half way through the ramp: half way between full and ducked.
  near(musicVolume(5 + DUCK_RAMP / 2, spans, 20, music), 0.2 * (1 - 0.7 * 0.5));
});

test('music fades in at the start and out at the end', () => {
  near(musicVolume(0, [], 20, music), 0);
  near(musicVolume(20, [], 20, music), 0);
  assert.ok(musicVolume(0.5, [], 20, music) < 0.2);
  for (let s = 0; s <= 20; s += 0.1) {
    const v = musicVolume(s, spans, 20, music);
    assert.ok(Number.isFinite(v) && v >= 0 && v <= 0.2);
  }
});
