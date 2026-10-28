import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cuesOf, cueRows, GLUE } from '../src/captions.ts';
import { WORDS } from '../src/audio.generated.ts';
import type { Line, Word } from '../src/types.ts';

const line = (key: string, en: string, start = 1, dur = 3, es = ''): Line => ({ key, start, dur, text: { en, es }, voice: 'en' });
const near = (a: number, b: number, eps = 1e-6) => assert.ok(Math.abs(a - b) <= eps, `${a} is not ≈ ${b}`);
const bare = (w: string) => w.toLowerCase().replace(/[^\p{L}]/gu, '');

test('exact timing from TTS words when counts match', () => {
  const words: Word[] = [['Agents', 0.1, 0.5], ['forget', 0.55, 0.9], ['why.', 1.0, 1.4]];
  WORDS.en = { 'exact-01': words };
  try {
    const l = line('exact-01', 'Agents forget why.', 2, 1.8);
    const cues = cuesOf(l, 'en');
    assert.equal(cues.length, 1);
    assert.equal(cues[0].text, 'Agents forget why.');
    assert.deepEqual(
      cues[0].tokens.map((t) => [t.text, +t.start.toFixed(3), +t.end.toFixed(3)]),
      [['Agents', 2.1, 2.5], ['forget', 2.55, 2.9], ['why.', 3.0, 3.4]],
    );
    near(cues[0].start, 2);
    near(cues[0].end, 3.8);
  } finally {
    WORDS.en = {};
  }
});

test('falls back to proportional timing when word counts differ', () => {
  // The voice says "fourteen out of twenty" for the single written token "14/20".
  const words: Word[] = [
    ['It', 0, 0.2], ['solved', 0.2, 0.6], ['fourteen', 0.6, 1.0], ['out', 1.0, 1.1], ['of', 1.1, 1.2],
    ['twenty', 1.2, 1.6], ['tasks.', 1.6, 2.1],
  ];
  WORDS.en = { 'prop-01': words };
  try {
    const l = line('prop-01', 'It solved 14/20 tasks.', 0.5, 2.2);
    const cues = cuesOf(l, 'en');
    assert.equal(cues.map((c) => c.text).join(' '), 'It solved 14/20 tasks.');
    const toks = cues.flatMap((c) => c.tokens);
    assert.deepEqual(toks.map((t) => t.text), ['It', 'solved', '14/20', 'tasks.']);
    for (let i = 0; i < toks.length; i++) {
      assert.ok(toks[i].end > toks[i].start, 'token has positive length');
      if (i) assert.ok(toks[i].start >= toks[i - 1].start, 'starts are monotonic');
    }
    near(toks[0].start, 0.5);
    assert.ok(cues.at(-1)!.end <= l.start + l.dur + 1e-9);
    assert.ok(toks.at(-1)!.end <= l.start + l.dur + 1e-9);
  } finally {
    WORDS.en = {};
  }
});

test('TTS words that run past the line end are clamped to it', () => {
  WORDS.en = { 'clamp-01': [['Short', 0, 0.4], ['line.', 0.5, 2.5]] };
  try {
    const l = line('clamp-01', 'Short line.', 0, 1.5);
    const toks = cuesOf(l, 'en').flatMap((c) => c.tokens);
    assert.ok(toks.at(-1)!.end <= 1.5);
  } finally {
    WORDS.en = {};
  }
});

test('subtitles in another language than the voice use proportional timing', () => {
  WORDS.en = { 'trans-01': [['One', 0, 0.3], ['two.', 0.4, 0.8]] };
  try {
    const l = line('trans-01', 'One two.', 0, 1, 'Uno dos.');
    const cues = cuesOf(l, 'es');
    assert.equal(cues.map((c) => c.text).join(' '), 'Uno dos.');
    near(cues[0].tokens[0].start, 0);
    near(cues.at(-1)!.end, 1);
  } finally {
    WORDS.en = {};
  }
});

test('splits long lines into ≤ 2-line cues', () => {
  const texts = [
    'When the planner hands a task to the implementer it passes on the what but almost never the why, and the implementer has to guess the rest of the design from the code that is already in the repository.',
    'Con el contexto completo, el agente acertó en catorce de veinte casos; sin él, en cuatro de veinte, y la diferencia no se debe al modelo sino a la forma en que el sistema le entrega la información.',
    'The write-up with every number and the anonymised data is on javieraguilar.ai/blog/nobody-tells-the-implementer-why for anyone who wants to check.',
  ];
  for (const maxChars of [32, 42]) {
    for (const text of texts) {
      const l = line('long-01', text, 0, text.length / 14.5);
      const cues = cuesOf(l, 'en', maxChars);
      assert.ok(cues.length > 1, 'a long line is split');
      const squash = (s: string) => s.replace(/\s+/g, '');
      assert.equal(squash(cues.map((c) => c.text).join(' ')), squash(text), 'no characters lost or reordered');
      assert.equal(cues.flatMap((c) => c.tokens).filter((t) => !t.glued).length, text.split(' ').length);
      cues.forEach((c, i) => {
        assert.ok(c.text.length <= 2 * maxChars, `cue too long (${c.text.length}): ${c.text}`);
        const rows = cueRows(c, maxChars);
        assert.ok(rows.length >= 1 && rows.length <= 2, `cue renders in ${rows.length} rows`);
        rows.forEach((r) => assert.ok(r.length <= maxChars, `row too long: ${r}`));
        assert.equal(squash(rows.join('')), squash(c.text));
        if (i < cues.length - 1) {
          assert.ok(!GLUE.has(bare(c.tokens.at(-1)!.text)), `cue ends on a glue word: ${c.text}`);
          near(c.end, cues[i + 1].start);
        }
        assert.ok(c.end > c.start);
      });
      near(cues[0].start, l.start);
      near(cues.at(-1)!.end, l.start + l.dur);
    }
  }
});

test('a word longer than a row (a URL) is split at its slashes and dashes', () => {
  const url = 'javieraguilar.ai/blog/nobody-tells-the-implementer-why';
  const l = line('url-01', `Read it at ${url}`, 0, 4);
  const cues = cuesOf(l, 'en', 32);
  const pieces = cues.flatMap((c) => c.tokens).filter((t, i, all) => t.glued || all[i + 1]?.glued);
  assert.ok(pieces.length >= 2);
  assert.equal(pieces.map((t) => t.text).join(''), url);
  for (const p of pieces) assert.ok(p.text.length <= 32 && p.end >= p.start);
  assert.ok(pieces.slice(0, -1).every((p) => /[/.\-_]$/.test(p.text)), 'cuts after a separator');
});

test('glue words include the usual EN and ES function words', () => {
  for (const w of ['the', 'of', 'a', 'de', 'la', 'el', 'and', 'y']) assert.ok(GLUE.has(w), w);
});

test('a spoken form keeps the written caption, timed proportionally', () => {
  // Same word count by coincidence: the TTS timestamps belong to other words, so they are ignored.
  WORDS.en = { 'spk-01': [['About', 0, 0.1], ['eighty-three', 0.1, 0.2], ['percent.', 0.2, 0.3]] };
  try {
    const l: Line = { ...line('spk-01', 'About 83 %.', 0, 3), spoken: { en: 'About eighty-three percent.' } };
    const toks = cuesOf(l, 'en').flatMap((c) => c.tokens);
    assert.deepEqual(toks.map((t) => t.text), ['About', '83', '%.']);
    assert.ok(toks.at(-1)!.end > 2.5, 'proportional over the whole line, not the 0.3 s of the timestamps');
  } finally {
    WORDS.en = {};
  }
});

test('the last cue of a line is held into the silence, never past the next line', async () => {
  const { heldCuesOf, CUE_HOLD } = await import('../src/captions.ts');
  const mk = (key: string, start: number, dur: number, text: string) => ({ key, start, dur, text: { en: text, es: text }, voice: 'en' as const });
  const lines = [mk('x-01', 0, 1, 'Short one.'), mk('x-02', 1.3, 1, 'Next.'), mk('x-03', 3, 1, 'Last.')];
  assert.equal(heldCuesOf(lines, 0, 'en').at(-1)!.end, 1.3);
  assert.equal(heldCuesOf(lines, 2, 'en').at(-1)!.end, 4 + CUE_HOLD);
});

test('alignWords gives a number read out as several words the span of those words', async () => {
  const { alignWords } = await import('../src/captions.ts');
  const written = 'only 8–31% of those'.split(' ');
  const spoken: [string, number, number][] = [['only', 0, 0.3], ['eight', 0.4, 0.6], ['to', 0.6, 0.7], ['thirty-one', 0.7, 1.2], ['percent', 1.2, 1.6], ['of', 1.6, 1.7], ['those', 1.8, 2]];
  const a = alignWords(written, spoken)!;
  assert.deepEqual(a[1], [0.4, 1.6]);
  assert.deepEqual(a[2], [1.6, 1.7]);
});

test('a cue closes at a sentence end once half full, and never ends on "into"', () => {
  // 26 characters: past half of a 32-character row, so the sentence gets its own cue.
  const l = line('half-01', 'The agent went home early. It then looked into the old repo for the missing file.', 0, 6);
  assert.equal(cuesOf(l, 'en', 32)[0].text, 'The agent went home early.');
  assert.ok(GLUE.has('into'));
  const long = line('into-01', 'Every message it wrote went straight into the queue and then into a log nobody read into the night.', 0, 8);
  for (let max = 8; max <= 40; max++) {
    const cues = cuesOf(long, 'en', max);
    for (const c of cues.slice(0, -1)) assert.notEqual(bare(c.tokens.at(-1)!.text), 'into', `maxChars ${max}: "${c.text}"`);
  }
});
