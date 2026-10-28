import { tx, type Label, type Lang } from '../types.ts';
import { beatAt, fit, progress, sceneTime } from './steps.ts';

export type KeyQuoteProps = {
  text: Label;
  /** Words or phrases to colour in the accent, matched ignoring case and punctuation. */
  emphasis?: string[];
  /** Index of the narration beat the quote appears on (default 0). */
  beat?: number;
};

/** Fade of a single word, in seconds. */
const WORD_SECONDS = 0.35;
/** The whole sentence is in within this many seconds, however long it is. */
const SPREAD_SECONDS = 0.8;
/** Accent underline under the emphasised words, after the sentence is in. */
const EMPHASIS_SECONDS = 0.4;

const norm = (w: string) => w.toLowerCase().replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');

/** For each word, whether it belongs to one of the emphasised words or phrases. */
export const emphasisMask = (words: string[], emphasis: string[] = []): boolean[] => {
  const mask = words.map(() => false);
  const keys = words.map(norm);
  for (const phrase of emphasis) {
    const parts = phrase.split(/\s+/).map(norm).filter(Boolean);
    if (!parts.length) continue;
    for (let i = 0; i + parts.length <= keys.length; i++) {
      if (parts.every((p, j) => keys[i + j] === p)) for (let j = 0; j < parts.length; j++) mask[i + j] = true;
    }
  }
  return mask;
};

/** What the quote draws at scene second `t`: words fade in one after another, then the emphasis. */
export function frameState(p: KeyQuoteProps, time: number, beats: number[], dur: number, lang: Lang = 'en') {
  const t = sceneTime(time, dur);
  const words = tx(p.text, lang).split(/\s+/).filter(Boolean);
  const stagger = words.length > 1 ? Math.min(0.05, SPREAD_SECONDS / (words.length - 1)) : 0;
  const sentence = Math.max(0, words.length - 1) * stagger + WORD_SECONDS;
  const start = fit(beatAt(beats, p.beat ?? 0), sentence + EMPHASIS_SECONDS, dur);
  const mask = emphasisMask(words, p.emphasis);
  return {
    start,
    chars: words.join(' ').length,
    words: words.map((text, i) => ({ text, emphasis: mask[i], opacity: progress(t, start + i * stagger, WORD_SECONDS) })),
    emphasis: progress(t, start + sentence, EMPHASIS_SECONDS),
  };
}
