// Pure state of the ExpanderCut scene ("the wall"): a ring of clause nodes wired like an expander,
// and a dashed cut through its centre that sweeps half a turn. At every angle the links that cross
// the cut light up, and there are always many of them. Illustrative graph, not a real formula.
// No Remotion or React here.
import { beatAt, clamp01, easeOutCubic, progress, sceneTime } from './steps.ts';

export type ExpanderCutProps = Record<string, never>;

export const N = 14;
/** Each node links to the ones 1, 5 and 7 steps round the ring (7 = opposite), so every half is tangled. */
export const STEPS = [1, 5, 7] as const;

export const NODES: { x: number; y: number }[] = Array.from({ length: N }, (_, i) => {
  const a = (2 * Math.PI * i) / N - Math.PI / 2;
  return { x: Math.cos(a), y: Math.sin(a) };
});

export const EDGES: [number, number][] = (() => {
  const seen = new Set<string>();
  const out: [number, number][] = [];
  for (let i = 0; i < N; i++) {
    for (const d of STEPS) {
      const j = (i + d) % N;
      const k = i < j ? `${i}-${j}` : `${j}-${i}`;
      if (!seen.has(k)) {
        seen.add(k);
        out.push([Math.min(i, j), Math.max(i, j)]);
      }
    }
  }
  return out;
})();

const fin = (x: number, d = 0) => (Number.isFinite(x) ? x : d);

/** Which side of the cut (a line through the centre at `angle`) a node is on: -1 or 1. */
export const side = (i: number, angle: number): number => {
  const n = NODES[i];
  // Offset the line a hair so no node ever sits exactly on it.
  const v = Math.cos(angle) * n.y - Math.sin(angle) * n.x + 1e-3;
  return v >= 0 ? 1 : -1;
};

export type ExpanderCutState = {
  appear: number;
  /** Cut line: opacity and its angle in radians. */
  cut: { opacity: number; angle: number };
  /** Per edge: 1 when it crosses the cut (and the cut is shown), else 0. */
  crossing: number[];
  /** How many links cross the cut right now. */
  crossCount: number;
  label: { opacity: number };
};

export function frameState(_props: ExpanderCutProps, t: number, beats: number[], dur: number): ExpanderCutState {
  const st = sceneTime(fin(t), dur);
  const b0 = beatAt(beats, 0);
  const d = Number.isFinite(dur) && dur > 0 ? dur : 6;
  const appear = easeOutCubic(progress(st, b0, 0.6));
  // The cut comes in on the second beat when there is one ("The wall: ..."), else soon after the first.
  const b1 = beats[1] !== undefined && Number.isFinite(beats[1]) ? beats[1] : b0 + 0.7;
  const cutOn = progress(st, b1, 0.4);
  const sweepLen = Math.max(0.5, d - (b1 + 0.4) - 0.5);
  const sweep = clamp01(progress(st, b1 + 0.4, sweepLen));
  const angle = Math.PI / 2 + 0.2 + sweep * Math.PI;
  const crossing: number[] = EDGES.map(([i, j]) => (cutOn > 0 && side(i, angle) !== side(j, angle) ? 1 : 0));
  return {
    appear,
    cut: { opacity: cutOn, angle },
    crossing,
    crossCount: crossing.reduce((a, b) => a + b, 0),
    label: { opacity: progress(st, b1 + 0.6, 0.5) },
  };
}
