// Helpers shared by the scripts: secrets, ffmpeg, Cartesia endpoint.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

/** The template folder (scripts run from it through npm, but do not rely on the cwd). */
export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const at = (...p) => path.join(ROOT, ...p);

const fromEnvFile = (file, name) => {
  if (!fs.existsSync(file)) return undefined;
  const line = fs.readFileSync(file, 'utf8').split(/\r?\n/).find((l) => l.trim().startsWith(`${name}=`));
  const v = line?.slice(line.indexOf('=') + 1).trim().replace(/^["']|["']$/g, '');
  return v || undefined;
};

/**
 * A secret from, in order: the environment, template/.env, ~/Documents/repos/.env.
 * The value is never logged; errors only name where it was looked for.
 */
export const secret = (name, required = true) => {
  const v = process.env[name] || fromEnvFile(at('.env'), name) || fromEnvFile(path.join(os.homedir(), 'Documents', 'repos', '.env'), name);
  if (!v && required) throw new Error(`${name} not found (env, template/.env or ~/Documents/repos/.env)`);
  return v;
};

let ffmpegBin;
/** ffmpeg: $FFMPEG_PATH, else the one on PATH. */
export const findFfmpeg = () => {
  if (ffmpegBin) return ffmpegBin;
  const candidate = process.env.FFMPEG_PATH || 'ffmpeg';
  try {
    execFileSync(candidate, ['-version'], { stdio: 'ignore' });
  } catch {
    throw new Error('ffmpeg not found: install it (brew install ffmpeg) or set FFMPEG_PATH');
  }
  return (ffmpegBin = candidate);
};

/** Runs ffmpeg and returns its stderr, where analysis filters (loudnorm, astats…) report. */
export const ffmpegReport = (args) => {
  const r = spawnSync(findFfmpeg(), ['-hide_banner', '-nostats', ...args], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  if (r.status !== 0) throw new Error(`ffmpeg failed: ${r.stderr.slice(-800)}`);
  return r.stderr;
};

/** Duration, size and frame rate of a video, through the ffprobe next to ffmpeg. */
export const probe = (file) => {
  const bin = findFfmpeg().replace(/ffmpeg$/, 'ffprobe');
  const json = JSON.parse(
    execFileSync(bin, ['-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate', '-of', 'json', file], { encoding: 'utf8' }),
  );
  const video = json.streams.find((s) => s.codec_type === 'video');
  const [num, den] = (video?.r_frame_rate ?? '0/1').split('/').map(Number);
  return {
    seconds: +(+json.format.duration).toFixed(3),
    width: video?.width,
    height: video?.height,
    fps: den ? +(num / den).toFixed(3) : 0,
    audio: json.streams.some((s) => s.codec_type === 'audio'),
  };
};

/** Integrated loudness (LUFS) and true peak (dBTP) of a file's audio. */
export const loudness = (file) => {
  const out = ffmpegReport(['-i', file, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-']);
  const summary = out.slice(out.lastIndexOf('Summary:'));
  const I = +(summary.match(/I:\s+(-?[\d.]+) LUFS/)?.[1] ?? NaN);
  const peak = +(summary.match(/Peak:\s+(-?[\d.]+|-inf) dBFS/)?.[1] ?? NaN);
  return { I, peak };
};

/** Duration of a PCM WAV buffer, read from its chunks (any header layout ffmpeg writes). */
export const wavSeconds = (buf) => {
  let off = 12;
  let byteRate = 0;
  while (off + 8 <= buf.length) {
    const id = buf.toString('ascii', off, off + 4);
    const len = buf.readUInt32LE(off + 4);
    if (id === 'fmt ') byteRate = buf.readUInt32LE(off + 16);
    if (id === 'data') return byteRate ? Math.min(len, buf.length - off - 8) / byteRate : 0;
    off += 8 + len + (len % 2);
  }
  return 0;
};

/** Target loudness of every delivered mix, and the tolerance audio QA accepts. */
export const LOUDNESS = { I: -16, tolerance: 1, truePeak: -1.5 };

export const CARTESIA = {
  base: process.env.CARTESIA_BASE ?? 'https://api.cartesia.ai',
  version: '2026-08-14',
  sampleRate: 44100,
};
export const cartesiaHeaders = (key, json = true) => ({
  Authorization: `Bearer ${key}`,
  'Cartesia-Version': CARTESIA.version,
  ...(json ? { 'Content-Type': 'application/json' } : {}),
});
