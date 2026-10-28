import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lintTimeline } from '../scripts/lint.ts';
import { anim, intro, outro, say } from '../src/narrate.ts';
import type { Scene } from '../src/types.ts';

const words = (n: number) => Array.from({ length: n }, (_, i) => `word${i}`).join(' ');

test('flags unknown anim and length out of range', () => {
  const scenes: Scene[] = [
    intro('hook', [say(0.3, 'A short hook line.', 'Una frase corta.')]),
    anim('chart', 'NoSuchAnimation', {}, [say(0.3, 'The bars grow one by one.', 'Las barras crecen.')]),
    outro('end', [say(0.3, 'Read it on javieraguilar.ai.', 'Léelo en javieraguilar.ai.')]),
  ];
  const issues = lintTimeline(scenes, 45);
  assert.ok(issues.some((m) => /NoSuchAnimation/.test(m)), issues.join('\n'));
  assert.ok(issues.some((m) => /target 45/.test(m)), issues.join('\n'));
});

test('a timeline on target with known anims and readable cues is clean', () => {
  // Lines long enough that every cue reads below 17 chars/s and lasts at least 0.8 s.
  const long = (id: string) => [0, 1, 2, 3].map(() => say(0, `${words(5)}.`, `${words(5)}.`));
  const scenes: Scene[] = [
    intro('hook', long('hook'), 12),
    anim('chart', 'Known', {}, long('chart'), { min: 18 }),
    outro('end', long('end'), 14),
  ];
  const issues = lintTimeline(scenes, 45, { known: ['Known'] });
  assert.deepEqual(issues, []);
});

test('flags caption cues that are too fast or too short', () => {
  // One long line squeezed into a very short scene: the estimate is replaced by a 0.5 s duration
  // (short enough that even with the closing hold the first cue stays under 0.8 s).
  const s = anim('fast', 'Known', {}, [say(0, words(12), words(12))]);
  s.lines[0].dur = 0.5;
  const issues = lintTimeline([s], 1, { known: ['Known'] });
  assert.ok(issues.some((m) => /chars\/s/.test(m)), issues.join('\n'));
  assert.ok(issues.some((m) => /0\.8 s/.test(m)), issues.join('\n'));
});
