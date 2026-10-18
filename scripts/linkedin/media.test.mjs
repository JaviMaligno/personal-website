import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';
import { tmpdir } from 'os';
import { findMedia } from './media.js';

function setup(files) {
  const root = mkdtempSync(join(tmpdir(), 'li-media-'));
  mkdirSync(join(root, 'posts', 'my-post'), { recursive: true });
  for (const f of files) writeFileSync(join(root, f), 'x');
  return { root, post: join(root, 'posts', 'my-post.txt') };
}

test('video in the post folder wins over root video and images', () => {
  const { root, post } = setup(['posts/my-post/clip.mp4', 'posts/my-post/a.png', 'video-linkedin.mp4']);
  const m = findMedia(root, post);
  assert.equal(m.type, 'video');
  assert.equal(m.paths[0], join(root, 'posts', 'my-post', 'clip.mp4'));
});

test('root video-linkedin still works when the post folder has no video', () => {
  const { root, post } = setup(['posts/my-post/a.png', 'video-linkedin.mp4']);
  const m = findMedia(root, post);
  assert.equal(m.type, 'video');
  assert.equal(m.paths[0], join(root, 'video-linkedin.mp4'));
});

test('images in the post folder when there is no video', () => {
  const { root, post } = setup(['posts/my-post/2.png', 'posts/my-post/10.png']);
  const m = findMedia(root, post);
  assert.equal(m.type, 'image');
  assert.deepEqual(m.paths.map(p => p.split('/').pop()), ['2.png', '10.png']);
});

test('no media → null', () => {
  const { root, post } = setup([]);
  assert.equal(findMedia(root, post), null);
});
