// Every local image a blog article points at must exist in public/.
//
// Astro does not check this: a heroImage pointing at a file that is not there
// builds fine and renders a broken image in the preview. That happened on the
// first push of most articles, because the draft set heroImage before Codex had
// generated the PNG.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const BLOG = 'src/content/blog';
const IMAGE = /\.(png|jpe?g|webp|gif|svg|avif)$/i;

export function localImageRefs(markdown) {
  const refs = new Set();
  const fm = markdown.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (fm) {
    for (const m of fm[1].matchAll(/^(heroImage|linkedinImage):\s*["']?([^"'\s]+)/gm)) refs.add(m[2]);
  }
  for (const m of markdown.matchAll(/!\[[^\]]*\]\(\s*([^)\s]+)/g)) refs.add(m[1]);
  for (const m of markdown.matchAll(/\bsrc=["']([^"']+)["']/g)) refs.add(m[1]);
  return [...refs].filter((r) => r.startsWith('/') && !r.startsWith('//') && IMAGE.test(r.split(/[?#]/)[0]));
}

function articles() {
  return readdirSync(BLOG, { recursive: true })
    .filter((f) => /\.mdx?$/.test(f))
    .map((f) => join(BLOG, f));
}

test('localImageRefs finds frontmatter, markdown and html image paths', () => {
  const md = [
    '---',
    'heroImage: "/blog/a.png"',
    'linkedinImage: /blog/b.jpg',
    '---',
    '![x](/blog/c.webp)',
    '<img src="/blog/d.png" alt="">',
    '![remote](https://example.com/e.png)',
    '<a href="/blog/f.png">not an image tag</a>',
  ].join('\n');
  assert.deepEqual(localImageRefs(md).sort(), ['/blog/a.png', '/blog/b.jpg', '/blog/c.webp', '/blog/d.png']);
});

test('every local image referenced by a blog article exists in public/', () => {
  const missing = [];
  for (const file of articles()) {
    for (const ref of localImageRefs(readFileSync(file, 'utf8'))) {
      if (!existsSync(join('public', ref.split(/[?#]/)[0]))) missing.push(`${file} -> ${ref}`);
    }
  }
  assert.deepEqual(missing, [], `images referenced but not in public/:\n${missing.join('\n')}`);
});
