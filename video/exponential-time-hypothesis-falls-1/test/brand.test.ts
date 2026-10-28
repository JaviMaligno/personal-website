import { test } from 'node:test';
import assert from 'node:assert/strict';
import { C, GRADIENT, alpha, BRAND } from '../src/brand.ts';

test('brand tokens match the website', () => {
  assert.equal(C.bg0, '#0a0a0f');
  assert.equal(C.bg1, '#12121a');
  assert.equal(C.card, '#1a1a24');
  assert.equal(C.accent, '#6366f1');
  assert.equal(C.accent2, '#8b5cf6');
  assert.equal(C.accentText, '#818cf8');
  assert.equal(C.text, '#f8fafc');
  assert.equal(C.muted, '#94a3b8');
  assert.equal(GRADIENT, 'linear-gradient(135deg, #6366f1, #8b5cf6)');
  assert.equal(BRAND.name, 'AGILabs');
  assert.equal(BRAND.site, 'javieraguilar.ai');
  assert.equal(alpha('#6366f1', 0.5), 'rgba(99,102,241,0.5)');
});

test('alpha accepts short hex and clamps opacity', () => {
  assert.equal(alpha('#fff', 1), 'rgba(255,255,255,1)');
  assert.equal(alpha('#000000', 2), 'rgba(0,0,0,1)');
  assert.equal(alpha('#000000', -1), 'rgba(0,0,0,0)');
  assert.throws(() => alpha('nope', 0.5));
});
