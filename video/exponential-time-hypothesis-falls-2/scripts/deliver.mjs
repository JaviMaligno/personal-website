// Everything to post besides the video itself, for every rendered main cut in out/:
// poster PNG (SETTINGS.poster, else the first anim scene at 1.5 s, else the intro once its hook
// has played),
// SRT captions, and out/manifest.json with durations, sizes and loudness.
// Run after `npm run render`. Lint issues are printed as a reminder; they do not stop delivery.
// Usage: npm run deliver
import fs from 'node:fs';
import { execFileSync, spawnSync } from 'node:child_process';
import { at, loudness, probe } from './lib.mjs';

const { SETTINGS } = await import('../src/settings.ts');
const { VIDEOS } = await import('../src/timeline.ts');
const { FPS, sceneStarts, sceneFrames } = await import('../src/timing.ts');
const { tx } = await import('../src/types.ts');
const { writeSrt } = await import('./srt.ts');

spawnSync('node', [at('scripts', 'lint.ts')], { stdio: 'inherit', cwd: at() });
fs.mkdirSync(at('out'), { recursive: true });

/** Poster frame: the scene and second chosen in settings, else a frame with the visual idea on it. */
const posterFrame = (scenes) => {
  const { starts } = sceneStarts(scenes);
  const firstAnim = scenes.findIndex((s) => s.kind === 'anim');
  // No anim scene: the intro once its hook line has fully played (every word lit).
  const hook = scenes[0]?.lines[0];
  const pick = SETTINGS.poster
    ? { index: scenes.findIndex((s) => s.id === SETTINGS.poster.scene), second: SETTINGS.poster.second }
    : firstAnim >= 0
      ? { index: firstAnim, second: 1.5 }
      : { index: 0, second: hook ? +(hook.start + hook.dur + 0.2).toFixed(2) : 1.5 };
  if (pick.index < 0) throw new Error(`SETTINGS.poster.scene "${SETTINGS.poster.scene}" is not in the timeline`);
  const frame = Math.min(starts[pick.index] + Math.round(pick.second * FPS), starts[pick.index] + sceneFrames(scenes[pick.index]) - 1);
  return { scene: scenes[pick.index].id, second: pick.second, frame };
};

const manifest = {
  generated: new Date().toISOString(),
  article: SETTINGS.articleTitle,
  targetSeconds: SETTINGS.targetSeconds,
  videos: [],
  posters: [],
  captions: [],
};

for (const voice of SETTINGS.voices) {
  const scenes = VIDEOS[voice].main;
  const subs = SETTINGS.subtitles.includes(voice) ? voice : SETTINGS.subtitles[0] ?? voice;

  const poster = posterFrame(scenes);
  const posterFile = `poster-${voice}.png`;
  const props = JSON.stringify({ voice, subs, vertical: true, noSubs: true });
  execFileSync('npx', ['remotion', 'still', 'src/index.ts', `Main-${voice.toUpperCase()}-vertical`, `out/${posterFile}`, `--frame=${poster.frame}`, `--props=${props}`], { stdio: 'inherit', cwd: at() });
  manifest.posters.push({ file: posterFile, voice, ...poster });

  for (const format of ['vertical', 'landscape']) {
    const name = `main-${voice}-${format}`;
    const video = at('out', `${name}.mp4`);
    if (!fs.existsSync(video)) continue;
    writeSrt(at('out', `${name}.srt`), scenes, subs);
    manifest.captions.push({ file: `${name}.srt`, lang: subs });
    const info = probe(video);
    const { I, peak } = loudness(video);
    manifest.videos.push({
      file: `${name}.mp4`,
      voice,
      format,
      seconds: info.seconds,
      width: info.width,
      height: info.height,
      fps: info.fps,
      megabytes: +(fs.statSync(video).size / 1e6).toFixed(2),
      lufs: +I.toFixed(1),
      truePeak: +peak.toFixed(1),
      scenes: scenes.map((s) => ({ id: s.id, kind: s.kind, seconds: +(sceneFrames(s) / FPS).toFixed(2), ...(s.chapter ? { chapter: tx(s.chapter, voice) } : {}) })),
    });
  }
}

if (!manifest.videos.length) console.warn('No render in out/ yet: run `npm run render` first for the video entries.');
fs.writeFileSync(at('out', 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(`out/manifest.json: ${manifest.videos.length} video(s), ${manifest.posters.length} poster(s), ${manifest.captions.length} caption file(s)`);
