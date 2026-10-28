// Audio QA without listening to everything: `npm run audio-qa [-- en|es]`.
//  1. Normalises every narration line to the same loudness (in place, once per file version).
//  2. Flags lines that were clipped as delivered by the TTS, and lines more than 1.6x longer than
//     their text suggests (a sign of garbled or repeated speech): listen to those.
//  3. Measures each rendered mix in out/ (main-*.mp4) against -16 LUFS ±1.
// Writes out/audio-qa.md. Exit code 1 when a mix is off target.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { VIDEOS } from '../src/timeline.ts';
import { SETTINGS } from '../src/settings.ts';
import { estimateSeconds } from '../src/narrate.ts';
import { spokenText, type Lang } from '../src/types.ts';
import { at, ffmpegReport, findFfmpeg, loudness, wavSeconds, LOUDNESS, CARTESIA } from './lib.mjs';

/** A line this much longer than its estimate is worth a listen. */
const TOO_LONG = 1.6;
/** Sample peak at which a source line counts as clipped, in dBFS. */
const CLIP_DB = -0.1;
/** Loudness each line is brought to before mixing; the final mix is normalised again on render. */
const LINE_TARGET = `I=${LOUDNESS.I}:TP=${LOUDNESS.truePeak}:LRA=11`;

const requested = process.argv.slice(2).filter((a): a is Lang => a === 'en' || a === 'es');
const langs = SETTINGS.voices.filter((l) => !requested.length || requested.includes(l));
const sha1 = (b: Buffer) => crypto.createHash('sha1').update(b).digest('hex');

const peakDb = (file: string): number => {
  const out = ffmpegReport(['-i', file, '-af', 'astats=measure_perchannel=none:measure_overall=Peak_level', '-f', 'null', '-']);
  const m = [...out.matchAll(/Peak level dB:\s*(-?[\d.]+|-inf)/g)].at(-1);
  return m ? +m[1] : -Infinity;
};

/** Two-pass, linear loudnorm of one WAV (keeps its 44.1 kHz mono s16 format). */
const normaliseLine = (file: string) => {
  const first = ffmpegReport(['-i', file, '-af', `loudnorm=${LINE_TARGET}:print_format=json`, '-f', 'null', '-']);
  const m = JSON.parse(first.match(/\{[^{}]*"input_i"[^{}]*\}/)![0]);
  const tmp = file.replace(/\.wav$/, '.norm.wav');
  const second =
    `loudnorm=${LINE_TARGET}:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}` +
    `:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true`;
  const r = spawnSync(findFfmpeg(), ['-y', '-loglevel', 'error', '-i', file, '-af', second, '-ar', String(CARTESIA.sampleRate), '-ac', '1', '-c:a', 'pcm_s16le', tmp]);
  if (r.status !== 0) throw new Error(`ffmpeg could not normalise ${file}`);
  fs.renameSync(tmp, file);
};

const report: string[] = ['# Audio QA', '', `Generated ${new Date().toISOString().slice(0, 16)}`, ''];
let flagged = 0;
let failed = 0;

for (const lang of langs) {
  const dir = at('public', 'audio', lang);
  const doneFile = path.join(dir, 'normalised.json');
  const done: Record<string, string> = fs.existsSync(doneFile) ? JSON.parse(fs.readFileSync(doneFile, 'utf8')) : {};
  report.push(`## Narration ${lang.toUpperCase()}`, '', '| Line | Seconds | Issues |', '|---|---|---|');
  for (const scene of VIDEOS[lang]?.main ?? []) {
    for (const line of scene.lines) {
      const file = path.join(dir, `${line.key}.wav`);
      const issues: string[] = [];
      if (!fs.existsSync(file)) {
        issues.push('no audio yet (npm run tts)');
      } else {
        const buf = fs.readFileSync(file);
        // Clipping is judged on the TTS output, before our own normalisation touches it.
        if (done[line.key] !== sha1(buf)) {
          const peak = peakDb(file);
          if (peak >= CLIP_DB) issues.push(`clipped (peak ${peak.toFixed(2)} dBFS)`);
          normaliseLine(file);
          done[line.key] = sha1(fs.readFileSync(file));
          fs.writeFileSync(doneFile, JSON.stringify(done, null, 1));
        }
        const seconds = wavSeconds(fs.readFileSync(file));
        const expected = estimateSeconds(spokenText(line, lang), lang);
        if (seconds > expected * TOO_LONG) issues.push(`${seconds.toFixed(1)} s for an expected ${expected.toFixed(1)} s: listen for garbled or repeated words`);
        report.push(`| ${line.key} | ${seconds.toFixed(2)} | ${issues.join('; ') || 'ok'} |`);
      }
      if (issues.length) {
        flagged++;
        console.log(`FLAG ${lang}/${line.key}: ${issues.join('; ')}`);
      }
    }
  }
  report.push('');
}

// Rendered mixes: voice + music, after render.mjs normalised them.
const outDir = at('out');
const mixes = fs.existsSync(outDir) ? fs.readdirSync(outDir).filter((f) => /^main-.*\.mp4$/.test(f)).sort() : [];
report.push('## Mixes', '');
if (!mixes.length) report.push('No render in out/ yet: run `npm run render`, then this again to check the mix.');
for (const f of mixes) {
  const { I, peak } = loudness(path.join(outDir, f));
  const ok = Math.abs(I - LOUDNESS.I) <= LOUDNESS.tolerance;
  if (!ok) failed++;
  const msg = `${f}: ${I.toFixed(1)} LUFS integrated (target ${LOUDNESS.I} ±${LOUDNESS.tolerance}), true peak ${peak.toFixed(1)} dBTP: ${ok ? 'ok' : 'OFF TARGET'}`;
  report.push(`- ${msg}`);
  console.log(msg);
}

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'audio-qa.md'), report.join('\n') + '\n');
console.log(`${flagged} line(s) flagged, ${mixes.length - failed}/${mixes.length} mix(es) on target -> out/audio-qa.md`);
process.exitCode = failed ? 1 : 0;
