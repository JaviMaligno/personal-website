import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildPostText } from './utils.js';

const base = {
  summary: 'A short summary of the article.',
  postUrl: 'https://www.javieraguilar.ai/en/blog/my-post',
  hashtags: '#AI #MachineLearning',
};

test('includes a "Read more" link and hashtags', () => {
  const text = buildPostText(base);
  assert.ok(text.includes(`📖 Read more: ${base.postUrl}`));
  assert.ok(text.endsWith(base.hashtags));
  assert.ok(text.startsWith(base.summary));
});

test('adds a "Code" line when repoUrl is present, above "Read more"', () => {
  const repoUrl = 'https://github.com/JaviMaligno/language-world-model-forgetting';
  const text = buildPostText({ ...base, repoUrl });
  assert.ok(text.includes(`💻 Code: ${repoUrl}`), 'repo line present');
  assert.ok(text.indexOf('💻 Code:') < text.indexOf('📖 Read more:'), 'code line before read-more');
});

test('omits the "Code" line when repoUrl is absent', () => {
  assert.ok(!buildPostText(base).includes('💻 Code:'));
  assert.ok(!buildPostText({ ...base, repoUrl: '' }).includes('💻 Code:'));
});

test('truncates to stay under the character cap, keeping repo + read-more + hashtags', () => {
  const repoUrl = 'https://github.com/JaviMaligno/language-world-model-forgetting';
  const summary = 'x'.repeat(5000); // far over the limit
  const text = buildPostText({ ...base, summary, repoUrl, maxLength: 3000 });
  assert.ok(text.length <= 3000, `length ${text.length} should be <= 3000`);
  assert.ok(text.includes('...'), 'truncation marker present');
  assert.ok(text.includes(`💻 Code: ${repoUrl}`), 'repo line survives truncation');
  assert.ok(text.includes(`📖 Read more: ${base.postUrl}`), 'read-more survives truncation');
  assert.ok(text.endsWith(base.hashtags), 'hashtags survive truncation');
});

test('short posts are not truncated', () => {
  const text = buildPostText(base);
  assert.ok(!text.includes('...'));
});

test('renders extra links with 🔗 and label, above code and read-more', () => {
  const links = [{ label: 'Connect your AI', url: 'https://getvitamind.app/connect' }];
  const repoUrl = 'https://github.com/JaviMaligno/vitamind';
  const text = buildPostText({ ...base, links, repoUrl });
  assert.ok(text.includes('🔗 Connect your AI: https://getvitamind.app/connect'), 'link line present');
  assert.ok(text.indexOf('🔗 Connect your AI:') < text.indexOf('💻 Code:'), 'links before code');
  assert.ok(text.indexOf('🔗 Connect your AI:') < text.indexOf('📖 Read more:'), 'links before read-more');
});

test('supports multiple links and omits a missing label', () => {
  const links = [
    { url: 'https://getvitamind.app/connect' },              // no label
    { label: 'Preprint', url: 'https://arxiv.org/abs/2607.14169' },
  ];
  const text = buildPostText({ ...base, links });
  assert.ok(text.includes('🔗 https://getvitamind.app/connect'), 'label-less link renders bare');
  assert.ok(text.includes('🔗 Preprint: https://arxiv.org/abs/2607.14169'), 'labelled link renders');
});

test('omits links block when none provided or entries lack a url', () => {
  assert.ok(!buildPostText(base).includes('🔗'), 'no links → no 🔗');
  assert.ok(!buildPostText({ ...base, links: [] }).includes('🔗'), 'empty array → no 🔗');
  assert.ok(!buildPostText({ ...base, links: [{ label: 'x' }] }).includes('🔗'), 'urlless entry skipped');
});

test('extra links survive truncation', () => {
  const links = [{ label: 'Preprint', url: 'https://arxiv.org/abs/2607.14169' }];
  const summary = 'x'.repeat(5000);
  const text = buildPostText({ ...base, summary, links, maxLength: 3000 });
  assert.ok(text.length <= 3000, `length ${text.length} should be <= 3000`);
  assert.ok(text.includes('🔗 Preprint: https://arxiv.org/abs/2607.14169'), 'link survives truncation');
  assert.ok(text.includes(`📖 Read more: ${base.postUrl}`), 'read-more survives truncation');
});
