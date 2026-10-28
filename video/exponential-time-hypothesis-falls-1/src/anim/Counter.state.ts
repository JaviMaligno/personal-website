import type { Label } from '../types.ts';
import { beatAt, easeOutCubic, fit, progress, sceneTime } from './steps.ts';

export type CounterProps = {
  value: number;
  prefix?: string;
  suffix?: string;
  label: Label;
  decimals?: number;
  /** Index of the narration beat the count starts on (default 0). */
  beat?: number;
};

/** Length of the count-up, in seconds. */
export const COUNT_SECONDS = 1.2;
/** Fade-in of the number and its label, in seconds. */
const APPEAR_SECONDS = 0.4;

const format = (n: number, p: CounterProps, decimals: number) => `${p.prefix ?? ''}${n.toFixed(decimals)}${p.suffix ?? ''}`;

/** What the counter draws at scene second `t`: the number counts up with ease-out from its beat. */
export function frameState(p: CounterProps, time: number, beats: number[], dur: number) {
  const t = sceneTime(time, dur);
  const target = Number.isFinite(p.value) ? p.value : 0;
  const decimals = Math.min(8, Math.max(0, Math.round(p.decimals ?? 0)));
  const start = fit(beatAt(beats, p.beat ?? 0), COUNT_SECONDS, dur);
  const prog = progress(t, start, COUNT_SECONDS);
  // Exactly the target once finished, so the last frame shows the article's number.
  const value = prog >= 1 ? target : target * easeOutCubic(prog);
  return {
    start,
    progress: prog,
    appear: progress(t, start, APPEAR_SECONDS),
    value,
    text: format(value, p, decimals),
    /** The finished text, to size the number so it never reflows while counting. */
    finalText: format(target, p, decimals),
  };
}
