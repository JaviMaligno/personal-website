#!/usr/bin/env node
/**
 * Does an article carry a hand-written `linkedinSummary` in its frontmatter?
 *
 * The LinkedIn post that goes out when an article is published is that text,
 * verbatim. There is no generated fallback any more (2026-11-14: the Gemini
 * summary of a-role-not-a-rule opened with a sentence nobody could parse, and
 * nothing checked it before it went out). So a scheduled article without one
 * must not be published: this check runs before the merge.
 *
 * Usage: git show origin/<branch>:<article> | node scripts/publish/linkedin-summary.mjs
 * Exit code 0 when present, 1 when missing or empty.
 */
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

/** The linkedinSummary text, or '' when absent. Handles `key: text` and `key: |` / `key: >` blocks. */
export function linkedinSummary(markdown) {
  const fm = markdown.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!fm) return '';
  const lines = fm[1].split(/\r?\n/);
  const i = lines.findIndex((l) => /^linkedinSummary:/.test(l));
  if (i < 0) return '';
  const inline = lines[i].replace(/^linkedinSummary:\s*/, '');
  if (!/^[|>][+-]?\s*$/.test(inline)) return inline.replace(/^["']|["']$/g, '').trim();
  const block = [];
  for (const l of lines.slice(i + 1)) {
    if (l.trim() === '' || /^\s+/.test(l)) block.push(l.trim());
    else break;
  }
  return block.join('\n').trim();
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const text = linkedinSummary(readFileSync(0, 'utf8'));
  if (!text) {
    console.error('Missing linkedinSummary: write the LinkedIn post in the article frontmatter before publishing.');
    process.exit(1);
  }
  console.log(`linkedinSummary present (${text.length} chars).`);
}
