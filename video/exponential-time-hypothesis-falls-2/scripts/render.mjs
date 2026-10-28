// Renders the main cut and normalises its loudness: out/main-{en|es}-{vertical|landscape}.mp4
// (+ the matching .srt). Two-pass loudnorm to -16 LUFS integrated, true peak -1.5 dBTP.
// Usage: npm run render [-- --es] [-- --landscape]
// Env: CONCURRENCY=n render threads (default: half the CPU threads).
import fs from 'node:fs';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { at, ffmpegReport, loudness, probe, LOUDNESS } from './lib.mjs';
import { makeMusicBed } from './music.mjs';

const args = process.argv.slice(2);
const voice = args.includes('--es') ? 'es' : 'en';
const format = args.includes('--landscape') ? 'landscape' : 'vertical';
const { SETTINGS } = await import('../src/settings.ts');
const { VIDEOS } = await import('../src/timeline.ts');
const { writeSrt } = await import('./srt.ts');

if (!SETTINGS.voices.includes(voice)) throw new Error(`"${voice}" is not in SETTINGS.voices`);
if (SETTINGS.music && !fs.existsSync(at('public', SETTINGS.music.src))) makeMusicBed();

const id = `Main-${voice.toUpperCase()}-${format}`;
const name = `main-${voice}-${format}`;
const raw = at('out', `_raw-${name}.mp4`);
const final = at('out', `${name}.mp4`);
fs.mkdirSync(at('out'), { recursive: true });

const concurrency = process.env.CONCURRENCY ?? String(Math.max(2, Math.floor(os.cpus().length / 2)));
execFileSync('npx', ['remotion', 'render', 'src/index.ts', id, raw, '--crf=18', `--concurrency=${concurrency}`], { stdio: 'inherit', cwd: at() });

// Measure, then apply as one linear gain so the voice does not "pump".
const target = `I=${LOUDNESS.I}:TP=${LOUDNESS.truePeak}:LRA=11`;
const m = JSON.parse(ffmpegReport(['-i', raw, '-vn', '-af', `loudnorm=${target}:print_format=json`, '-f', 'null', '-']).match(/\{[^{}]*"input_i"[^{}]*\}/)[0]);
const second = `loudnorm=${target}:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true`;
ffmpegReport(['-y', '-i', raw, '-c:v', 'copy', '-af', second, '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', final]);
fs.rmSync(raw);

const subs = SETTINGS.subtitles.includes(voice) ? voice : SETTINGS.subtitles[0] ?? voice;
writeSrt(at('out', `${name}.srt`), VIDEOS[voice].main, subs);

const info = probe(final);
const { I, peak } = loudness(final);
console.log(
  `${final}: ${info.width}x${info.height} @ ${info.fps} fps, ${info.seconds.toFixed(1)} s, ` +
    `${(fs.statSync(final).size / 1e6).toFixed(1)} MB, ${I.toFixed(1)} LUFS, true peak ${peak.toFixed(1)} dBTP`,
);
