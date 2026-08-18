import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

// The Vercel adapter writes the static output to dist/client/; a plain static
// build writes to dist/. Look for both so the assertions work either way.
const ROOTS = ['dist/client', 'dist'];

function page(lang) {
  for (const root of ROOTS) {
    const candidate = `${root}/${lang}/publications/index.html`;
    if (existsSync(candidate)) return candidate;
  }
  return `dist/client/${lang}/publications/index.html`;
}

const EN = page('en');
const ES = page('es');

function read(path) {
  assert.ok(existsSync(path), `${path} is missing — run "npm run build" first`);
  return readFileSync(path, 'utf8');
}

test('the English page links Payhip for every edition', () => {
  const html = read(EN);
  assert.ok(html.includes('https://payhip.com/b/sVI15'), 'The Logic of Sacrifice (en)');
  assert.ok(html.includes('https://payhip.com/b/KHMxr'), 'Science Catch-Up (en)');
});

test('the Spanish page links the Spanish editions, not the English ones', () => {
  const html = read(ES);
  assert.ok(html.includes('https://payhip.com/b/ux0mB'), 'La lógica del sacrificio');
  assert.ok(html.includes('https://payhip.com/b/M4bjR'), 'Science Catch-Up (es)');
  assert.ok(!html.includes('https://payhip.com/b/sVI15'), 'no English edition leaks in');
});

test('Amazon links use the reader marketplace', () => {
  assert.ok(read(EN).includes('https://www.amazon.com/dp/B0HBLBGHPF'), 'en → amazon.com');
  assert.ok(read(ES).includes('https://www.amazon.es/dp/B0H8M1W9SR'), 'es → amazon.es');
});

test('no print ASIN is ever composed into a URL', () => {
  for (const path of [EN, ES]) {
    const html = read(path);
    for (const asin of ['B0HBLPHZD9', 'B0HBNJ4MRD', 'B0H958KHNW', 'B0H961RXY2', 'B0GSS3224N', 'B0GT3TS16R']) {
      assert.ok(!html.includes(`/dp/${asin}`), `${asin} must not be linked in ${path}`);
    }
  }
});

test('the English Science Catch-Up shows no Amazon link', () => {
  const html = read(EN);
  const amazonLinks = html.match(/https:\/\/www\.amazon\.com\/dp\/\w+/g) ?? [];
  assert.deepEqual([...new Set(amazonLinks)], ['https://www.amazon.com/dp/B0HBLBGHPF']);
});

test('both pages carry the papers, the thesis and the teaching entries', () => {
  for (const path of [EN, ES]) {
    const html = read(path);
    assert.ok(html.includes('https://arxiv.org/abs/2607.14169'), `verified world model preprint in ${path}`);
    assert.ok(html.includes('https://arxiv.org/abs/2307.11414'), `derived Deligne preprint in ${path}`);
    assert.ok(html.includes('https://kar.kent.ac.uk/105426/'), `thesis in ${path}`);
    assert.ok(html.includes('KeepCoding'), `teaching list in ${path}`);
  }
});

test('both pages emit Book and ScholarlyArticle structured data', () => {
  for (const path of [EN, ES]) {
    const html = read(path);
    assert.ok(html.includes('"@type":"Book"'), `Book schema in ${path}`);
    assert.ok(html.includes('"@type":"ScholarlyArticle"'), `ScholarlyArticle schema in ${path}`);
    assert.ok(html.includes('"@type":"Thesis"'), `Thesis schema in ${path}`);
  }
});
