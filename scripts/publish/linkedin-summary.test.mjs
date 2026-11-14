import { test } from 'node:test';
import assert from 'node:assert/strict';
import { linkedinSummary } from './linkedin-summary.mjs';

const doc = (fm) => `---\n${fm}\n---\n\nBody text.\n`;

test('block scalar is read until the next key', () => {
  const md = doc('title: "X"\nlinkedinSummary: |\n  First paragraph.\n\n  Second one.\nheroImage: "/a.png"');
  assert.equal(linkedinSummary(md), 'First paragraph.\n\nSecond one.');
});

test('inline value, quoted or not', () => {
  assert.equal(linkedinSummary(doc('linkedinSummary: "Short post."')), 'Short post.');
  assert.equal(linkedinSummary(doc('linkedinSummary: Short post.')), 'Short post.');
});

test('missing or empty counts as absent', () => {
  assert.equal(linkedinSummary(doc('title: "X"')), '');
  assert.equal(linkedinSummary(doc('linkedinSummary: |\nheroImage: "/a.png"')), '');
  assert.equal(linkedinSummary(doc('linkedinSummary: ""')), '');
});

test('a body line that looks like the key is not frontmatter', () => {
  assert.equal(linkedinSummary('---\ntitle: "X"\n---\nlinkedinSummary: nope\n'), '');
});

test('CRLF files', () => {
  const md = '---\r\nlinkedinSummary: |\r\n  Line one.\r\ntags: []\r\n---\r\n';
  assert.equal(linkedinSummary(md), 'Line one.');
});
