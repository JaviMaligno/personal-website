// Pure state of the CrossingRewrite scene (the eight-square identity, one rectangle), two beats:
//  0. a rectangle x, y / u, v whose two diagonals test x = v and y = u: "6 bits", tagged
//     "1818 · octonions";
//  1. the crossing moves up and splits into a row choice (horizontal links, 3 bits with rows
//     merged) and a column choice (vertical links, 3 bits with columns merged), joined by "+".
// Illustrative layout. No Remotion or React here.
import { beatAt, clamp01, easeOutCubic, progress, sceneTime } from './steps.ts';

export type CrossingRewriteProps = Record<string, never>;

const fin = (x: number, d = 0) => (Number.isFinite(x) ? x : d);
const inOut = (p: number) => {
  const q = clamp01(p);
  return q < 0.5 ? 4 * q * q * q : 1 - (-2 * q + 2) ** 3 / 2;
};
const beatOr = (beats: number[], i: number, d: number): number => {
  const b = beats[i];
  return b !== undefined && Number.isFinite(b) ? b : d;
};

export type CrossingRewriteState = {
  crossing: { appear: number; draw: number };
  tag: { opacity: number };
  /** 0 = crossing alone, centred; 1 = crossing small at the top, the two pieces below. */
  split: number;
  row: { appear: number };
  col: { appear: number };
  plus: { opacity: number };
};

export function frameState(_props: CrossingRewriteProps, t: number, beats: number[], dur: number): CrossingRewriteState {
  const st = sceneTime(fin(t), dur);
  const d = Number.isFinite(dur) && dur > 0 ? dur : 8;
  const b0 = beatAt(beats, 0);
  const b1 = beatOr(beats, 1, b0 + d * 0.5);
  return {
    crossing: { appear: easeOutCubic(progress(st, b0, 0.6)), draw: easeOutCubic(progress(st, b0 + 0.3, 0.8)) },
    tag: { opacity: progress(st, b0 + 1.0, 0.5) },
    split: inOut(progress(st, b1, 0.9)),
    row: { appear: easeOutCubic(progress(st, b1 + 0.6, 0.6)) },
    col: { appear: easeOutCubic(progress(st, b1 + 1.2, 0.6)) },
    plus: { opacity: progress(st, b1 + 1.0, 0.4) },
  };
}
