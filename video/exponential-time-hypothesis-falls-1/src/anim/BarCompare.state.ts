import type { Label } from '../types.ts';
import { easeOutCubic, progress, stepTimes, sceneTime } from './steps.ts';

export type Bar = {
  label: Label;
  value: number;
  /** Text shown instead of the number, to match the article exactly (e.g. "14/20"). */
  display?: string;
  highlight?: boolean;
  /** Scene second the bar grows at; default: its own narration beat. */
  at?: number;
};

export type BarCompareProps = { bars: Bar[]; max?: number; unit?: string };

/** Time a bar takes to grow to full length, in seconds. */
export const GROW_SECONDS = 0.9;

/** What the chart draws at scene second `t`: bars grow one per beat. */
export function frameState(p: BarCompareProps, time: number, beats: number[], dur: number) {
  const t = sceneTime(time, dur);
  const values = p.bars.map((b) => (Number.isFinite(b.value) ? Math.max(0, b.value) : 0));
  const top = p.max !== undefined && Number.isFinite(p.max) && p.max > 0 ? p.max : Math.max(0, ...values);
  const max = top > 0 ? top : 1;
  const starts = stepTimes(p.bars.length, beats, p.bars.map((b) => b.at), GROW_SECONDS, dur);
  return {
    max,
    bars: p.bars.map((b, i) => {
      const grow = progress(t, starts[i], GROW_SECONDS);
      const share = Math.min(1, values[i] / max);
      return {
        label: b.label,
        text: b.display ?? `${b.value}${p.unit ?? ''}`,
        highlight: !!b.highlight,
        start: starts[i],
        grow,
        /** Share of the full track, at full growth. */
        fill: share,
        /** Share of the full track drawn now. */
        width: share * easeOutCubic(grow),
        opacity: progress(t, starts[i], 0.3),
      };
    }),
  };
}
