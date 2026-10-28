import type { Lang } from '../types.ts';

/** What every animation receives, besides its own props from the timeline. */
export type AnimProps = {
  /** Seconds since the scene started. */
  t: number;
  /** Scene seconds at which each narration line starts. */
  beats: number[];
  /** Scene length in seconds. */
  dur: number;
  lang: Lang;
  vertical: boolean;
};
