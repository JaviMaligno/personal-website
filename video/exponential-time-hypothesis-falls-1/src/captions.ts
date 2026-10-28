// Caption cues for the burned-in captions (and, later, the SRT export).
// A cue is what is on screen at once: at most two rows of `maxChars` characters.
// No Remotion imports, so plain `node --test` can load it.
import { WORDS } from './audio.generated.ts';
import { spokenText, type Lang, type Line } from './types.ts';

/**
 * One written word with its time on screen, in scene seconds. `glued` marks a piece of a word too
 * long for a row (a URL, say) that continues the previous piece with no space in between.
 */
export type Token = { text: string; start: number; end: number; glued?: boolean };
export type Cue = { start: number; end: number; text: string; tokens: Token[] };

/** Short function words a cue should not end on: they read as part of what follows. */
export const GLUE = new Set(
  (
    'a an the of to into in on at by for from with as and or but nor so if than that this these those ' +
    'is are was were be its our your their my his her we i you it not no ' +
    'el la los las lo un una unos unas de del al a y e o u ni en con por para sin sobre que su sus ' +
    'se le les es son era fue como mi tu nos no'
  ).split(' '),
);

const bare = (w: string) => w.toLowerCase().replace(/[^\p{L}]/gu, '');
const isGlue = (t: Token) => GLUE.has(bare(t.text));
/** A sentence ends here: a good place to start a new cue. */
const SENTENCE_END = /[.!?…:;]["')\]]*$/;

const textLen = (ts: Token[]) => ts.reduce((n, t, i) => n + t.text.length + (i > 0 && !t.glued ? 1 : 0), 0);

/** Tokens back to text: a space between words, none before a glued piece. */
export const joinTokens = (ts: Token[]) => ts.map((t, i) => (i > 0 && !t.glued ? ' ' : '') + t.text).join('');

/**
 * Breaks a word longer than `maxChars` into pieces that fit a row, cutting after `/`, `-`, `.`
 * or `_` when it can and anywhere when it cannot. The word's time is shared by length.
 */
const splitLong = (tok: Token, maxChars: number): Token[] => {
  if (tok.text.length <= maxChars) return [tok];
  const pieces: string[] = [];
  let rest = tok.text;
  while (rest.length > maxChars) {
    const head = rest.slice(0, maxChars);
    const cut = Math.max(head.lastIndexOf('/'), head.lastIndexOf('-'), head.lastIndexOf('.'), head.lastIndexOf('_'));
    const at = cut >= maxChars / 3 ? cut + 1 : maxChars;
    pieces.push(rest.slice(0, at));
    rest = rest.slice(at);
  }
  if (rest) pieces.push(rest);
  const span = tok.end - tok.start;
  let acc = 0;
  return pieces.map((text, i) => {
    const start = tok.start + (acc / tok.text.length) * span;
    acc += text.length;
    return { text, start, end: tok.start + (acc / tok.text.length) * span, ...(i > 0 ? { glued: true } : {}) };
  });
};

/**
 * The written words of a line, timed in scene seconds. When the line is subtitled in its own
 * voice, the TTS read the written text, and it returned one timestamp per written word, those
 * times are used as they are. Otherwise (numbers or symbols read out as several words, a spoken
 * form that differs from the caption, or a translation under another voice) the line's duration
 * is spread over the written words in proportion to their length.
 */
export const tokensOf = (line: Line, subs: Lang): Token[] => {
  const words = line.text[subs].split(/\s+/).filter(Boolean);
  const end = line.start + line.dur;
  // TTS timestamps belong to the spoken words: only usable when the caption is that same text.
  const ownText = subs === line.voice && spokenText(line, subs) === line.text[subs];
  const spoken = ownText ? WORDS[line.voice]?.[line.key] : undefined;
  if (spoken && spoken.length === words.length) {
    let prev = line.start;
    return words.map((text, i) => {
      const start = Math.min(end, Math.max(prev, line.start + spoken[i][1]));
      const stop = Math.min(end, Math.max(start, line.start + spoken[i][2]));
      prev = start;
      return { text, start, end: stop };
    });
  }
  // Spoken form differs (a number or address read out as several words): align the written words
  // to the spoken ones, so only the rewritten words take the span of what was said for them.
  const said = subs === line.voice ? WORDS[line.voice]?.[line.key] : undefined;
  if (said && said.length) {
    const aligned = alignWords(words, said);
    if (aligned) {
      let prev = line.start;
      return words.map((text, i) => {
        const start = Math.min(end, Math.max(prev, line.start + aligned[i][0]));
        const stop = Math.min(end, Math.max(start, line.start + aligned[i][1]));
        prev = start;
        return { text, start, end: stop };
      });
    }
  }
  // Weight = characters plus one for the space, so short words still get some time.
  const weights = words.map((w) => w.length + 1);
  const total = weights.reduce((a, b) => a + b, 0) || 1;
  let acc = 0;
  return words.map((text, i) => {
    const start = line.start + (acc / total) * line.dur;
    acc += weights[i];
    return { text, start, end: line.start + (acc / total) * line.dur };
  });
};

const norm = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');

/**
 * Times for written words from spoken word timestamps, matching identical words in order and
 * giving each run of unmatched written words the span of the unmatched spoken words between the
 * same anchors ("8–31%" ← "eight to thirty-one percent"). Null when too few words match.
 */
export const alignWords = (written: string[], spoken: [string, number, number][]): [number, number][] | null => {
  const w = written.map(norm);
  const s = spoken.map(([x]) => norm(x));
  const out: [number, number][] = [];
  let i = 0;
  let j = 0;
  let matched = 0;
  while (i < w.length) {
    if (j < s.length && w[i] && w[i] === s[j]) {
      out.push([spoken[j][1], spoken[j][2]]);
      matched++;
      i++;
      j++;
      continue;
    }
    // Next anchor: the nearest pair (i2, j2) of equal words ahead.
    let best: [number, number] | null = null;
    for (let i2 = i; i2 < Math.min(w.length, i + 6) && !best; i2++) {
      if (!w[i2]) continue;
      for (let j2 = j; j2 < Math.min(s.length, j + 10); j2++) {
        if (w[i2] === s[j2] && !(i2 === i && j2 === j)) {
          best = [i2, j2];
          break;
        }
      }
    }
    const [i2, j2] = best ?? [w.length, s.length];
    if (i2 === i) {
      // Extra spoken words before this written word: skip them.
      j = j2;
      continue;
    }
    const a = j < s.length ? spoken[j][1] : (spoken.at(-1)?.[2] ?? 0);
    const b = j2 > j ? spoken[Math.min(j2, s.length) - 1][2] : a;
    const n = i2 - i;
    for (let k = 0; k < n; k++) out.push([a + ((b - a) * k) / n, a + ((b - a) * (k + 1)) / n]);
    i = i2;
    j = j2;
  }
  return matched >= Math.ceil(written.length / 2) ? out : null;
};

/** Greedy row filling (words longer than `maxChars` have already been split). */
const fillRows = (toks: Token[], maxChars: number): Token[][] => {
  const rows: Token[][] = [];
  let row: Token[] = [];
  for (const t of toks) {
    if (row.length && textLen([...row, t]) > maxChars) {
      rows.push(row);
      row = [];
    }
    row.push(t);
  }
  if (row.length) rows.push(row);
  return rows;
};

/**
 * Splits a line into cues of at most two rows of `maxChars` characters. A cue closes early at the
 * end of a sentence once it is half full, and never ends on a glue word (those move on to the
 * next cue). Cues tile the line: each ends where the next begins, the last at the line's end.
 */
export const cuesOf = (line: Line, subs: Lang, maxChars = 32): Cue[] => {
  const toks = tokensOf(line, subs).flatMap((t) => splitLong(t, maxChars));
  const groups: Token[][] = [];
  let cur: Token[] = [];
  const close = () => {
    const carry: Token[] = [];
    while (cur.length > 1 && isGlue(cur.at(-1)!)) carry.unshift(cur.pop()!);
    groups.push(cur);
    cur = carry;
  };
  toks.forEach((t, i) => {
    if (cur.length && fillRows([...cur, t], maxChars).length > 2) close();
    cur.push(t);
    const rest = toks.length - 1 - i;
    if (rest > 0 && SENTENCE_END.test(t.text) && textLen(cur) >= maxChars / 2) close();
  });
  if (cur.length) groups.push(cur);
  // Carrying glue words forward can, rarely, make the next cue three rows; split it again.
  const fitted = groups.flatMap((g) => {
    const rows = fillRows(g, maxChars);
    if (rows.length <= 2) return [g];
    const out: Token[][] = [];
    for (let k = 0; k < rows.length; k += 2) out.push(rows.slice(k, k + 2).flat());
    return out;
  });
  const lineEnd = line.start + line.dur;
  return fitted.map((g, i) => ({
    start: i === 0 ? line.start : g[0].start,
    end: i + 1 < fitted.length ? fitted[i + 1][0].start : lineEnd,
    text: joinTokens(g),
    tokens: g,
  }));
};

/**
 * How long the last cue of a line stays up after the voice stops, in seconds: a short closing
 * phrase ("Can you tell where it is?") would otherwise flash by faster than it can be read.
 * Never past the start of the next line, nor past `until` (where the scene starts handing over
 * to the next one, so two scenes' captions never show at once).
 */
export const CUE_HOLD = 0.8;

/** The cues of line `i` of a scene, its last cue held up to CUE_HOLD into the silence after it. */
export const heldCuesOf = (lines: Line[], i: number, subs: Lang, maxChars = 32, until = Infinity): Cue[] => {
  const cues = cuesOf(lines[i], subs, maxChars);
  const last = cues.at(-1);
  if (last) {
    const next = lines[i + 1]?.start ?? until;
    last.end = Math.max(last.end, Math.min(last.end + CUE_HOLD, next));
  }
  return cues;
};

/** All cues of a scene's lines, in scene seconds, with the hold after each line. */
export const cuesOfLines = (lines: Line[], subs: Lang, maxChars = 32, until = Infinity): Cue[] =>
  lines.flatMap((_, i) => heldCuesOf(lines, i, subs, maxChars, until));

/**
 * Splits a cue into one or two rows for display: the most balanced break that keeps both rows
 * within `maxChars`, avoiding a first row that ends on a glue word.
 */
export const cueRows = (cue: Cue, maxChars = 32): string[] => cueRowTokens(cue, maxChars).map(joinTokens);

export const cueRowTokens = (cue: Cue, maxChars = 32): Token[][] => {
  const toks = cue.tokens;
  if (toks.length < 2 || textLen(toks) <= maxChars) return [toks];
  let best = 1;
  let bestScore = Infinity;
  for (let i = 1; i < toks.length; i++) {
    const a = textLen(toks.slice(0, i));
    const b = textLen(toks.slice(i));
    const over = Math.max(0, a - maxChars) + Math.max(0, b - maxChars);
    // Never break a row inside a split word if it can be helped; avoid ending row 1 on "the", "de"…
    const score = over * 100 + Math.abs(a - b) + (isGlue(toks[i - 1]) ? 8 : 0) + (toks[i].glued ? 20 : 0);
    if (score < bestScore) {
      bestScore = score;
      best = i;
    }
  }
  return [toks.slice(0, best), toks.slice(best)];
};
