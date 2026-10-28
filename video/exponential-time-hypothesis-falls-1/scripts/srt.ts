// Caption file for upload next to the video (platform captions, accessibility):
// out/main-{voice}-vertical.srt with the same cues as the burned-in captions, in video time.
// Usage: npm run srt
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cueRows, heldCuesOf } from '../src/captions.ts';
import { handOverAt, linesInVideo } from '../src/timing.ts';
import type { Lang, Scene } from '../src/types.ts';

const ROW_CHARS = 32;

const stamp = (seconds: number): string => {
  const ms = Math.max(0, Math.round(seconds * 1000));
  const two = (n: number) => String(n).padStart(2, '0');
  return `${two(Math.floor(ms / 3_600_000))}:${two(Math.floor(ms / 60_000) % 60)}:${two(Math.floor(ms / 1000) % 60)},${String(ms % 1000).padStart(3, '0')}`;
};

/** SRT text for a cut. Every line is included, the intro hook too (on screen it is the title card). */
export function srtOf(scenes: Scene[], subs: Lang, maxChars = ROW_CHARS): string {
  const cues = linesInVideo(scenes).flatMap(({ scene, line, at }) => {
    const offset = at - line.start; // scene start in video seconds
    return heldCuesOf(scene.lines, scene.lines.indexOf(line), subs, maxChars, handOverAt(scene)).map((c) => ({ from: offset + c.start, to: offset + c.end, text: cueRows(c, maxChars).join('\n') }));
  });
  // Lines never overlap, but keep a hair of space between cues for players that merge them.
  cues.forEach((c, i) => {
    if (i + 1 < cues.length) c.to = Math.min(c.to, cues[i + 1].from - 0.04);
  });
  return cues.map((c, i) => `${i + 1}\n${stamp(c.from)} --> ${stamp(c.to)}\n${c.text}\n`).join('\n');
}

export function writeSrt(file: string, scenes: Scene[], subs: Lang): void {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, srtOf(scenes, subs));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const { VIDEOS } = await import('../src/timeline.ts');
  const { SETTINGS } = await import('../src/settings.ts');
  for (const voice of SETTINGS.voices) {
    const subs = SETTINGS.subtitles.includes(voice) ? voice : SETTINGS.subtitles[0] ?? voice;
    const file = `out/main-${voice}-vertical.srt`;
    writeSrt(file, VIDEOS[voice].main, subs);
    console.log(file);
  }
}
