export type Lang = 'en' | 'es';

/** Text in both languages; ES may be left empty while a video is EN-only. */
export type Text = Record<Lang, string>;

/** Either one string for every language or a per-language pair. */
export type Label = string | Text;

export function tx(label: Label, lang: Lang): string {
  if (typeof label === 'string') return label;
  return label[lang] || label.en;
}

/**
 * One narration line. `start` and `dur` are seconds from the start of its scene. `text` is the
 * written form (captions); `spoken`, when set for a language, is what the TTS reads instead
 * ("fourteen out of twenty" for "14/20"), and the captions keep the written form.
 */
export type Line = { key: string; start: number; dur: number; text: Text; voice: Lang; spoken?: Partial<Text> };

/** What the TTS reads for a line: its spoken form when one is given, else the written text. */
export const spokenText = (line: Pick<Line, 'text' | 'spoken'>, lang: Lang): string => line.spoken?.[lang] || line.text[lang];

/** A spoken word from TTS: [word, start, end] in seconds from the start of its line. */
export type Word = [string, number, number];

export type SceneKind = 'intro' | 'anim' | 'outro';

export type Scene = {
  id: string;
  kind: SceneKind;
  chapter?: Label;
  anim?: { name: string; props: Record<string, unknown> };
  lines: Line[];
  /** Scene seconds at which each line starts; animations key off these. */
  beats: number[];
  minSeconds?: number;
};

export type Cuts = { main: Scene[] };
