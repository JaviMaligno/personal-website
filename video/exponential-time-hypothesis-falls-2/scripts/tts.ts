// Voices every narration line: public/audio/{lang}/{key}.wav (+ {key}.words.json with Cartesia's
// word timestamps), then rewrites src/audio.generated.ts from what is on disk.
// Lines are cached by a hash of engine + voice + model + speed (+ emotion) + text (+ the voice's `post` chain):
// only new or edited lines are voiced again. A voice's optional `post` (an ffmpeg -af chain) is
// applied to each line right after synthesis; it must keep the line's length (word timestamps). One engine per language (see tts-engine.mjs): if Cartesia drops out half way,
// the whole language is redone with Kokoro, and the next run with Cartesia back redoes it again.
// Usage: npm run tts [-- en|es]
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { VIDEOS } from '../src/timeline.ts';
import { SETTINGS } from '../src/settings.ts';
import { spokenText, type Lang, type Tone, type Word } from '../src/types.ts';
import config from '../video.config.mjs';
import { at, secret, findFfmpeg, wavSeconds, CARTESIA, cartesiaHeaders } from './lib.mjs';
import { chooseEngine, cartesiaUnavailable, postChain, lineHash, colonsAsStops } from './tts-engine.mjs';

type CartesiaVoice = { id: string; language?: string; post?: string };
type KokoroVoice = { voice: string; lang: string; post?: string };

const TTS = config.tts;
const ENGINE = TTS.engine as 'cartesia' | 'kokoro' | 'auto';
const RATE = CARTESIA.sampleRate;
const requested = process.argv.slice(2).filter((a): a is Lang => a === 'en' || a === 'es');
const langs = SETTINGS.voices.filter((l) => !requested.length || requested.includes(l));
const key = ENGINE === 'kokoro' ? undefined : secret('CARTESIA_API_KEY', false);

/** Cartesia said "not now" (outage, credits, rate limit) or the network failed: try Kokoro. */
class Unavailable extends Error {}

// ── WAV helpers: Cartesia streams raw 16-bit PCM; we add the header ourselves.
const wavFile = (pcm: Buffer): Buffer => {
  const h = Buffer.alloc(44);
  h.write('RIFF', 0);
  h.writeUInt32LE(36 + pcm.length, 4);
  h.write('WAVEfmt ', 8);
  h.writeUInt32LE(16, 16);
  h.writeUInt16LE(1, 20); // PCM
  h.writeUInt16LE(1, 22); // mono
  h.writeUInt32LE(RATE, 24);
  h.writeUInt32LE(RATE * 2, 28);
  h.writeUInt16LE(2, 32);
  h.writeUInt16LE(16, 34);
  h.write('data', 36);
  h.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([h, pcm]);
};

// ── Cartesia: one line through the SSE endpoint, which streams audio chunks and word timestamps.
// A line's tone overrides the config's default emotion and speed. Cartesia emotions are English only.
const toneOf = (tone: Tone | undefined, lang: Lang) => ({
  speed: tone?.speed ?? TTS.speed ?? 1,
  emotion: lang === 'en' ? (tone?.emotion ?? TTS.emotion) : undefined,
});

async function cartesiaLine(text: string, voice: CartesiaVoice, tone: { speed: number; emotion?: string }): Promise<{ audio: Buffer; words: Word[] }> {
  const config = { ...(tone.speed !== 1 ? { speed: tone.speed } : {}), ...(tone.emotion ? { emotion: tone.emotion } : {}) };
  const body = {
    model_id: TTS.model,
    transcript: text,
    voice: { mode: 'id', id: voice.id },
    language: voice.language ?? 'en',
    output_format: { container: 'raw', encoding: 'pcm_s16le', sample_rate: RATE },
    add_timestamps: true,
    ...(Object.keys(config).length ? { generation_config: config } : {}),
  };
  let res: Response;
  try {
    res = await fetch(`${CARTESIA.base}/tts/sse`, {
      method: 'POST',
      headers: { ...cartesiaHeaders(key), Accept: 'text/event-stream' },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new Unavailable(`network: ${(e as Error).message}`);
  }
  if (!res.ok || !res.body) {
    const msg = `HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`;
    throw cartesiaUnavailable(res.status) ? new Unavailable(msg) : new Error(`Cartesia ${msg}`);
  }
  const pcm: Buffer[] = [];
  const words: Word[] = [];
  const onEvent = (block: string) => {
    const data = block
      .split(/\r?\n/)
      .filter((l) => l.startsWith('data:'))
      .map((l) => l.slice(5).trim())
      .join('\n');
    if (!data) return;
    const ev = JSON.parse(data);
    if (ev.type === 'chunk' && ev.data) pcm.push(Buffer.from(ev.data, 'base64'));
    if (ev.type === 'timestamps' && ev.word_timestamps) {
      const w = ev.word_timestamps;
      w.words.forEach((word: string, i: number) => words.push([word, +(+w.start[i]).toFixed(3), +(+w.end[i]).toFixed(3)]));
    }
    if (ev.type === 'error') {
      const msg = `error ${ev.status_code ?? ''}: ${ev.message ?? ev.error ?? 'unknown'}`;
      throw cartesiaUnavailable(+ev.status_code) ? new Unavailable(msg) : new Error(`Cartesia ${msg}`);
    }
  };
  const decoder = new TextDecoder();
  let pending = '';
  for await (const part of res.body as unknown as AsyncIterable<Uint8Array>) {
    pending += decoder.decode(part, { stream: true });
    const blocks = pending.split(/\r?\n\r?\n/);
    pending = blocks.pop() ?? '';
    blocks.forEach(onEvent);
  }
  if (pending.trim()) onEvent(pending);
  if (!pcm.length) throw new Error('Cartesia returned no audio');
  return { audio: wavFile(Buffer.concat(pcm)), words };
}

// ── Post-processing: run the voice's ffmpeg chain over a line's WAV in place, same format, and
// check the length did not move (the word timestamps belong to the unfiltered audio).
function applyPost(file: string, chain: string) {
  if (!chain) return;
  const tmp = file.replace(/\.wav$/, '.post.wav');
  const r = spawnSync(findFfmpeg(), ['-y', '-loglevel', 'error', '-i', file, '-af', chain, '-ar', String(RATE), '-ac', '1', '-c:a', 'pcm_s16le', tmp], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`ffmpeg post chain failed on ${file}: ${r.stderr.slice(-400)}`);
  const before = wavSeconds(fs.readFileSync(file));
  const after = wavSeconds(fs.readFileSync(tmp));
  if (Math.abs(after - before) > 0.02) {
    fs.rmSync(tmp);
    throw new Error(`post chain changed the length of ${file} (${before.toFixed(3)} s -> ${after.toFixed(3)} s): word timestamps would drift`);
  }
  fs.renameSync(tmp, file);
}

// ── Kokoro: a batch per language through scripts/kokoro.py, resampled to Cartesia's format.
function kokoroBatch(jobs: { text: string; out: string }[], voice: KokoroVoice) {
  if (!jobs.length) return;
  const raw = jobs.map((j) => ({ text: j.text, voice: voice.voice, lang: voice.lang, speed: TTS.kokoro?.speed ?? 1, out: j.out.replace(/\.wav$/, '.24k.wav') }));
  const r = spawnSync('uv', ['run', '--quiet', '--with', 'kokoro-onnx', '--with', 'soundfile', 'python', at('scripts', 'kokoro.py')], {
    input: JSON.stringify({ items: raw }),
    encoding: 'utf8',
    stdio: ['pipe', 'inherit', 'inherit'],
  });
  if (r.status !== 0) throw new Error(`Kokoro failed (it runs through uv: brew install uv). ${r.error?.message ?? ''}`);
  for (const item of raw) {
    const c = spawnSync(findFfmpeg(), ['-y', '-loglevel', 'error', '-i', item.out, '-ar', String(RATE), '-ac', '1', '-c:a', 'pcm_s16le', item.out.replace(/\.24k\.wav$/, '.wav')]);
    if (c.status !== 0) throw new Error(`ffmpeg could not resample ${item.out}`);
    fs.rmSync(item.out);
  }
}

// What the TTS reads for each line. Colons are voiced as full stops unless the config opts out
// (see colonsAsStops in tts-engine.mjs): only the audio changes, never the caption.
const voiced = (text: string): string => (TTS.colonsAsStops === false ? text : colonsAsStops(text));

const linesOf = (lang: Lang): Map<string, { text: string; tone?: Tone }> => {
  const lines = new Map<string, { text: string; tone?: Tone }>();
  for (const cut of Object.values(VIDEOS[lang] ?? {})) for (const scene of cut) for (const l of scene.lines) lines.set(l.key, { text: voiced(spokenText(l, lang)), tone: l.tone });
  return lines;
};

for (const lang of langs) {
  const dir = at('public', 'audio', lang);
  fs.mkdirSync(dir, { recursive: true });
  const cacheFile = path.join(dir, 'cache.json');
  const cache: Record<string, string> = fs.existsSync(cacheFile) ? JSON.parse(fs.readFileSync(cacheFile, 'utf8')) : {};
  const saveCache = () => fs.writeFileSync(cacheFile, JSON.stringify(cache, null, 1));
  const lines = linesOf(lang);
  const cvoice: CartesiaVoice | null = TTS.voices?.[lang] ?? null;
  const kvoice: KokoroVoice | undefined = TTS.kokoro?.voices?.[lang];
  const cpost = postChain(cvoice);
  const kpost = postChain(kvoice);
  let made = 0;

  // A missing Cartesia voice for this language counts as Cartesia being unavailable for it.
  let choice = chooseEngine(ENGINE, !!key, cvoice?.id ? undefined : `no Cartesia voice set for "${lang}" in video.config.mjs`);

  if (choice.engine === 'cartesia') {
    try {
      for (const [k, { text, tone }] of lines) {
        const file = path.join(dir, `${k}.wav`);
        const t = toneOf(tone, lang);
        // The emotion joins the hash only when set, so lines voiced before emotions keep their hash.
        const hash = lineHash(['cartesia', cvoice!.id, TTS.model, t.speed, ...(t.emotion ? [t.emotion] : [])], text, cpost);
        if (cache[k] === hash && fs.existsSync(file)) continue;
        const { audio, words } = await cartesiaLine(text, cvoice!, t);
        fs.writeFileSync(file, audio);
        applyPost(file, cpost);
        fs.writeFileSync(path.join(dir, `${k}.words.json`), JSON.stringify(words));
        cache[k] = hash;
        saveCache();
        made++;
        console.log(`${lang}/${k}: ${wavSeconds(audio).toFixed(2)} s, ${words.length} words (Cartesia${cpost ? ' + post' : ''})`);
      }
    } catch (e) {
      if (!(e instanceof Unavailable)) throw e;
      choice = chooseEngine(ENGINE, true, e.message);
    }
  }

  if (choice.engine === 'kokoro') {
    if (choice.warning) console.warn(`\nWARNING ${lang.toUpperCase()}: ${choice.warning}.\n  The whole language uses this voice; captions fall back to proportional timing.\n`);
    if (!kvoice) throw new Error(`no Kokoro voice for "${lang}": set tts.kokoro.voices.${lang} in video.config.mjs`);
    const jobs: { key: string; hash: string; text: string; out: string }[] = [];
    for (const [k, { text }] of lines) {
      const out = path.join(dir, `${k}.wav`);
      const hash = lineHash(['kokoro', kvoice.voice, kvoice.lang, TTS.kokoro?.speed ?? 1], text, kpost);
      if (cache[k] === hash && fs.existsSync(out)) continue;
      jobs.push({ key: k, hash, text, out });
    }
    kokoroBatch(jobs, kvoice);
    for (const j of jobs) {
      applyPost(j.out, kpost);
      fs.rmSync(path.join(dir, `${j.key}.words.json`), { force: true });
      cache[j.key] = j.hash;
      made++;
      console.log(`${lang}/${j.key}: ${wavSeconds(fs.readFileSync(j.out)).toFixed(2)} s (Kokoro)`);
    }
    saveCache();
  }
  console.log(`${lang}: ${lines.size} lines, ${made} voiced (${choice.engine})`);
}

// ── src/audio.generated.ts from the files on disk, for every narration language.
const AUDIO: Partial<Record<Lang, Record<string, number>>> = {};
const WORDS: Partial<Record<Lang, Record<string, Word[]>>> = {};
for (const lang of SETTINGS.voices) {
  for (const k of linesOf(lang).keys()) {
    const file = at('public', 'audio', lang, `${k}.wav`);
    if (!fs.existsSync(file)) continue;
    (AUDIO[lang] ??= {})[k] = +wavSeconds(fs.readFileSync(file)).toFixed(3);
    const wordsFile = file.replace(/\.wav$/, '.words.json');
    if (fs.existsSync(wordsFile)) (WORDS[lang] ??= {})[k] = JSON.parse(fs.readFileSync(wordsFile, 'utf8'));
  }
}
fs.writeFileSync(
  at('src', 'audio.generated.ts'),
  `// Written by the TTS script; regenerated on every run. Durations in seconds, keyed by line key.
import type { Lang, Word } from './types.ts';

export const AUDIO: Partial<Record<Lang, Record<string, number>>> = ${JSON.stringify(AUDIO, null, 2)};
export const WORDS: Partial<Record<Lang, Record<string, Word[]>>> = ${JSON.stringify(WORDS)};
`,
);
console.log('src/audio.generated.ts updated. Next: npm run audio-qa');
