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
