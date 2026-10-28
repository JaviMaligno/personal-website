// Marks: scene seconds of spoken words, so a picture lands on the word that names it.
// A mark is written in timeline.ts as [line index, word]; it resolves to line start + the word's
// start in the TTS word timestamps, or, before TTS has run, to an estimate from where the word
// sits in the line's text. Pure (no Remotion).
import { spokenText, type Lang, type Line, type Word } from './types.ts';

export type MarkSpec = [line: number, word: string];

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9-]/g, '');

/** Scene seconds of the first word of line `li` that starts with `word`. */
export function resolveMark(lines: Line[], [li, word]: MarkSpec, words: Record<string, Word[]> | undefined, lang: Lang): number {
  const line = lines[li];
  if (!line) return Number.NaN;
  const target = norm(word);
  const ws = words?.[line.key];
  if (ws?.length) {
    const hit = ws.find((w) => norm(w[0]).startsWith(target));
    if (hit) return +(line.start + hit[1]).toFixed(3);
  }
  const text = spokenText(line, lang);
  const at = text.toLowerCase().indexOf(word.toLowerCase());
  const frac = at < 0 ? 0.5 : at / Math.max(1, text.length);
  return +(line.start + frac * line.dur).toFixed(3);
}
