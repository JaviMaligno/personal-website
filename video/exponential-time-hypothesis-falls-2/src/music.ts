// Music bed level over time. No Remotion imports, so Node tests can load it.

/** Seconds the music takes to dip under a line and to come back up. */
export const DUCK_RAMP = 0.35;
const MUSIC_FADE_IN = 1;
const MUSIC_FADE_OUT = 1.5;

/**
 * Music bed volume at a video second: `volume`, ducked to `volume * duck` while a line plays
 * (ramping over DUCK_RAMP either side), faded in at the start and out at the end.
 */
export const musicVolume = (
  seconds: number,
  spans: { from: number; to: number }[],
  total: number,
  music: { volume: number; duck: number },
): number => {
  // 1 inside a line, 0 more than DUCK_RAMP away from every line, linear in between.
  const depth = spans.reduce((d, s) => {
    const away = seconds < s.from ? s.from - seconds : seconds > s.to ? seconds - s.to : 0;
    return Math.max(d, 1 - Math.min(1, away / DUCK_RAMP));
  }, 0);
  const edge = Math.max(0, Math.min(1, seconds / MUSIC_FADE_IN, (total - seconds) / MUSIC_FADE_OUT));
  return music.volume * (1 - (1 - music.duck) * depth) * edge;
};
