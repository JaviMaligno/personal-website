import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import matter from 'gray-matter';
import katex from 'katex';
import { convertMathForDevto, protectForDevto } from './math.mjs';

// What Dev.to does to a {% katex %} body before KaTeX sees it (measured on a
// draft): backslash-escaped punctuation loses its backslash.
const STRIPPED = new Set('!#&()*+-./:<=>?@[]^_`{|}~\\');
function devtoUnescape(body) {
  return body.replace(/\\(.)/g, (m, ch) => (STRIPPED.has(ch) ? ch : m));
}

function katexBodies(markdown) {
  return [...markdown.matchAll(/\{% katex( inline)? %\}([\s\S]*?)\{% endkatex %\}/g)]
    .map(([, inline, body]) => ({ inline: !!inline, tex: devtoUnescape(body).trim() }));
}

test('protectForDevto survives Dev.to unescaping', () => {
  for (const tex of ['\\#F', '\\{0,1\\}^n', 'a \\\\ b', '\\text{a\\_b}', 'x\\,y', '\\alpha']) {
    assert.equal(devtoUnescape(protectForDevto(tex)), tex);
  }
});

test('inline and display math become katex tags; code and prices do not', () => {
  const md = [
    'Cost $2^{0.39n}$ beats `$x$` in code.',
    '',
    '$$\\#F = \\sum_x 1$$',
    '',
    '$$',
    'a = b',
    '$$',
  ].join('\n');
  const out = convertMathForDevto(md);
  assert.match(out, /Cost \{% katex inline %\}2\^\{0\.39n\}\{% endkatex %\} beats `\$x\$` in code\./);
  assert.match(out, /\{% katex %\}\n\\\\#F = \\sum_x 1\n\{% endkatex %\}/);
  assert.match(out, /\{% katex %\}\na = b\n\{% endkatex %\}/);
  assert.equal(out.replace('`$x$`', '').includes('$'), false);
});

// Two prices on one line ("$109 → $64") parse as one formula on the site too;
// write them as \$109.
for (const lang of ['en', 'es']) {
  const langDir = `src/content/blog/${lang}`;
  test(`no prices parsed as math (${lang})`, () => {
    for (const file of readdirSync(langDir).filter((f) => f.endsWith('.md'))) {
      const { content } = matter(readFileSync(`${langDir}/${file}`, 'utf-8'));
      for (const { tex } of katexBodies(convertMathForDevto(content))) {
        assert.doesNotMatch(tex, /^\d[\d.,]*\s+(→|\p{L}+\s)/u, `${lang}/${file}: "$${tex}$" looks like a price — escape it as \\$`);
      }
    }
  });
}

// Every EN article — published or scheduled — must render on Dev.to without a
// KaTeX ParseError.
const dir = 'src/content/blog/en';
for (const file of readdirSync(dir).filter((f) => f.endsWith('.md'))) {
  const { content } = matter(readFileSync(`${dir}/${file}`, 'utf-8'));
  const bodies = katexBodies(convertMathForDevto(content));
  if (!bodies.length) continue;
  test(`Dev.to KaTeX parses: ${file}`, () => {
    for (const { inline, tex } of bodies) {
      assert.doesNotThrow(() => katex.renderToString(tex, { displayMode: !inline, throwOnError: true }), tex);
    }
  });
}
