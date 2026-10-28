import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CAPTION, SAFE, STAGE, V, VERTICAL, captionHeight } from '../src/layout.ts';

test('vertical captions sit on the bottom safe line and clear the action rail', () => {
  assert.equal(V.captionBottom, VERTICAL.h - SAFE.bottom);
  assert.equal(V.captionBottom - V.captionTop, captionHeight(true));
  // Centred and no wider than the frame minus the rail on both sides.
  assert.ok((VERTICAL.w + V.captionWidth) / 2 <= VERTICAL.w - SAFE.rail);
  // Two rows of 32 characters (~0.46 em each in Inter Bold) fit inside the box.
  const c = CAPTION.vertical;
  assert.ok(32 * 0.46 * c.fontSize + 2 * c.padX <= V.captionWidth);
});

test('vertical stage runs from under the badge to just above the captions, inside the safe band', () => {
  const s = STAGE.vertical;
  assert.ok(V.badgeTop >= 131, 'badge below the TikTok tab bar');
  assert.ok(s.top >= SAFE.top);
  assert.equal(s.top + s.h, V.stageBottom);
  assert.ok(V.stageBottom < V.captionTop);
  assert.equal(s.top + s.h + s.bottom, VERTICAL.h);
  assert.ok(s.h >= 1080, `stage is ${s.h} px tall`);
});
