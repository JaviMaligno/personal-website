// Helpers for timeline.ts. A scene is a card or an animation with narration lines on top;
// lines play one after another, and their start times ("beats") drive the animation.
import { AUDIO } from './audio.generated.ts';
import { SETTINGS } from './settings.ts';
import { spokenText, type Cuts, type Label, type Lang, type Line, type Scene, type Text, type Tone } from './types.ts';

/** Silence between two lines, in seconds. */
export const GAP = 0.35;
/** Silence after the last line of a scene, in seconds. */
export const TAIL = 0.8;
/**
 * The outro card: shown OUTRO_SECONDS when silent; when it speaks, held only OUTRO_TAIL after its
 * last line (the card carries the address, so a long silent hold just loses viewers at the end).
 */
export const OUTRO_SECONDS = 3;
export const OUTRO_TAIL = 0.5;

// The timeline is built once per narration language; helpers read the current one.
let current: Lang = 'en';
export const voice = (): Lang => current;

export const videos = (build: () => Cuts): Record<Lang, Cuts> => {
  const out = {} as Record<Lang, Cuts>;
  for (const lang of SETTINGS.voices) {
    current = lang;
    try {
      out[lang] = build();
    } finally {
      current = 'en';
    }
  }
  return out;
};

/** Bilingual on-screen label. */
export const L = (en: string, es: string): Label => ({ en, es });

/**
 * One narration line: `at` is the earliest scene second it may start. `spoken` optionally gives
 * what the TTS should read per language when it differs from the caption text (numbers, symbols,
 * version strings): `say(0, 'It solved 14/20.', '…', { en: 'It solved fourteen out of twenty.' })`.
 */
export type Spec = { at: number; en: string; es: string; spoken?: Partial<Text>; tone?: Tone };
export const say = (at: number, en: string, es: string, spoken?: Partial<Text>, tone?: Tone): Spec => ({
  at,
  en,
  es,
  ...(spoken ? { spoken } : {}),
  ...(tone ? { tone } : {}),
});

const CHARS_PER_SECOND: Record<Lang, number> = { en: 14.5, es: 15.5 };

/** Expected spoken length of a text, from its length: used before TTS and by audio QA. */
export const estimateSeconds = (text: string, lang: Lang): number => text.length / CHARS_PER_SECOND[lang];

/** Spoken length of a line: the real audio once TTS has run, an estimate before that. */
export const lineSeconds = (key: string, text: string, lang: Lang = current): number =>
  AUDIO[lang]?.[key] ?? estimateSeconds(text, lang);

const round = (n: number) => +n.toFixed(3);

const place = (id: string, specs: Spec[]): Line[] => {
  const lines: Line[] = [];
  let prevEnd: number | null = null;
  specs.forEach((spec, i) => {
    const key = `${id}-${String(i + 1).padStart(2, '0')}`;
    const text = { en: spec.en, es: spec.es };
    const dur = lineSeconds(key, spokenText({ text, spoken: spec.spoken }, current), current);
    const start = prevEnd === null ? Math.max(0, spec.at) : Math.max(spec.at, prevEnd + GAP);
    lines.push({ key, start: round(start), dur, text, voice: current, ...(spec.spoken ? { spoken: spec.spoken } : {}), ...(spec.tone ? { tone: spec.tone } : {}) });
    prevEnd = start + dur;
  });
  return lines;
};

const scene = (id: string, kind: Scene['kind'], specs: Spec[], min: number, extra: Partial<Scene> = {}, tail = TAIL): Scene => {
  const lines = place(id, specs);
  const last = lines.at(-1);
  const minSeconds = round(Math.max(min, last ? last.start + last.dur + tail : 0));
  return { id, kind, ...extra, lines, beats: lines.map((l) => l.start), minSeconds };
};

export const intro = (id: string, specs: Spec[], min = 3): Scene => scene(id, 'intro', specs, min);

export const anim = (
  id: string,
  name: string,
  props: Record<string, unknown>,
  specs: Spec[],
  opts: { chapter?: Label; min?: number } = {},
): Scene =>
  scene(id, 'anim', specs, opts.min ?? 0, {
    anim: { name, props },
    ...(opts.chapter !== undefined ? { chapter: opts.chapter } : {}),
  });

export const outro = (id: string, specs: Spec[], min = OUTRO_SECONDS): Scene => scene(id, 'outro', specs, min, {}, OUTRO_TAIL);
