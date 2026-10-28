// Timing helpers shared by the animation components' pure `frameState` functions.
// No Remotion or React here, so the states can be tested with plain `node --test`.

/** Clamp to [0, 1]; anything that is not a finite number counts as 0. */
export const clamp01 = (x: number): number => (Number.isFinite(x) ? Math.min(1, Math.max(0, x)) : 0);

export const easeOutCubic = (p: number): number => 1 - (1 - clamp01(p)) ** 3;

/** Linear progress of an animation of `len` seconds that starts at `start`, clamped to [0, 1]. */
export const progress = (t: number, start: number, len: number): number =>
  len <= 0 ? (t >= start ? 1 : 0) : clamp01((t - start) / len);

/** Spacing for steps that have no narration beat of their own, in seconds. */
export const STEP_SPACING = 0.6;

/**
 * Start of an animation of `len` seconds: never before the scene starts, and early enough to
 * finish by the scene end, so the last frame always shows the finished state.
 */
export const fit = (start: number, len: number, dur: number): number => {
  const s = Number.isFinite(start) ? Math.max(0, start) : 0;
  return Number.isFinite(dur) ? Math.min(s, Math.max(0, dur - len)) : s;
};

/**
 * Start times of `n` steps: step i at its explicit `at`, else at beats[i], else STEP_SPACING after
 * the previous step. Each start is then fitted into the scene.
 */
export const stepTimes = (n: number, beats: number[], ats: (number | undefined)[], len: number, dur: number): number[] => {
  const out: number[] = [];
  let prev: number | null = null;
  for (let i = 0; i < n; i++) {
    const at = ats[i];
    const beat = beats[i];
    const raw: number =
      at !== undefined && Number.isFinite(at)
        ? at
        : beat !== undefined && Number.isFinite(beat)
          ? beat
          : prev === null
            ? 0
            : prev + STEP_SPACING;
    prev = raw;
    out.push(fit(raw, len, dur));
  }
  return out;
};

/**
 * Scene time as the states read it: from the scene end on, every animation counts as finished,
 * even in a scene too short to play it out.
 */
export const sceneTime = (t: number, dur: number): number => (Number.isFinite(dur) && t >= dur ? Number.MAX_SAFE_INTEGER : t);

/** The beat with index `i`, or the scene start when there is no such beat. */
export const beatAt = (beats: number[], i = 0): number => {
  const b = beats[i];
  return b !== undefined && Number.isFinite(b) ? b : 0;
};
