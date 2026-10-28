import type { Label } from '../types.ts';
import { progress, stepTimes, sceneTime } from './steps.ts';

export type Stat = {
  /** Shown as written, so it matches the article exactly. */
  value: string;
  label: Label;
  /** Scene second the tile pops in at; default: its own narration beat. */
  at?: number;
};

export type StatGridProps = { stats: Stat[] };

/** Pop-in of a tile, in seconds. */
export const POP_SECONDS = 0.5;

/** Rows and columns for `n` tiles: a column on vertical (2×2 for four), a row on landscape. */
export const gridShape = (n: number, vertical: boolean): { cols: number; rows: number } => {
  const count = Math.max(1, n);
  if (!vertical) return { cols: count, rows: 1 };
  const cols = count === 4 ? 2 : 1;
  return { cols, rows: Math.ceil(count / cols) };
};

/** What the grid draws at scene second `t`: one tile pops in per beat. */
export function frameState(p: StatGridProps, time: number, beats: number[], dur: number) {
  const t = sceneTime(time, dur);
  const starts = stepTimes(p.stats.length, beats, p.stats.map((s) => s.at), POP_SECONDS, dur);
  return {
    tiles: p.stats.map((s, i) => ({
      value: s.value,
      label: s.label,
      start: starts[i],
      pop: progress(t, starts[i], POP_SECONDS),
      opacity: progress(t, starts[i], POP_SECONDS * 0.6),
    })),
  };
}
