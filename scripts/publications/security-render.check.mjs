import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import matter from 'gray-matter';

const content = path.resolve('src/content/blog');
const output = path.resolve('dist/client');
function entries(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const filename = path.join(directory, entry.name);
    return entry.isDirectory() ? entries(filename)
      : /^(?!_).*\.mdx?$/.test(entry.name) ? [filename] : [];
  });
}

test('every existing localized article keeps its URL and rendered body', () => {
  const files = entries(content);
  assert.ok(files.length > 20, 'Expected the existing bilingual article collection');
  for (const filename of files) {
    const { data, content: markdown } = matter(readFileSync(filename, 'utf8'));
    const relative = path.relative(content, filename).replaceAll(path.sep, '/');
    // Existing articles use canonical lowercase kebab-case filenames. The glob
    // loader preserves their legacy slug and any explicit frontmatter override.
    const id = data.slug ?? relative.replace(/\.mdx?$/, '');
    assert.match(id, /^[a-z0-9][a-z0-9/-]+$/);
    const slug = id.replace(`${data.lang}/`, '');
    const page = path.join(output, data.lang, 'blog', slug, 'index.html');
    assert.ok(existsSync(page), `Existing article URL is missing: ${data.lang}/blog/${slug}/`);
    const html = readFileSync(page, 'utf8');
    assert.match(html, /<article[\s>]/);
    assert.match(html, /<h1[\s>]/);
    assert.match(html, /rel="canonical"/);
  }
});

test('the migrated Markdown pipeline still renders math and scrollable tables', () => {
  let math = 0;
  let tables = 0;
  for (const filename of entries(content)) {
    const { data, content: markdown } = matter(readFileSync(filename, 'utf8'));
    const relative = path.relative(content, filename).replaceAll(path.sep, '/');
    const id = data.slug ?? relative.replace(/\.mdx?$/, '');
    const html = readFileSync(path.join(output, data.lang, 'blog', id.replace(`${data.lang}/`, ''), 'index.html'), 'utf8');
    if (html.includes('class="katex')) math++;
    // KaTeX also emits internal layout tables, which are not Markdown tables.
    if (/^\s*\|?[: -]+(?:\|[: -]+)+\|?\s*$/m.test(markdown)) {
      tables++;
      assert.ok(/class="table-wrap"[^>]*>\s*<table/.test(html), `Markdown table wrapper missing in ${relative}`);
    }
  }
  assert.ok(math > 0, 'KaTeX math output disappeared');
  assert.ok(tables > 0, 'Markdown table output disappeared');
});
