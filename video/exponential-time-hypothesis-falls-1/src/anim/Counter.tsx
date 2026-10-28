import React from 'react';
import { interpolate } from 'remotion';
import { C, GRADIENT } from '../brand.ts';
import { tx } from '../types.ts';
import type { AnimProps } from './types.ts';
import { frameState, type CounterProps } from './Counter.state.ts';
import { Stage, gradientText, stageOf } from './Stage.tsx';

export { frameState };
export type { CounterProps };

/** One big number counting up to the article's figure, with its label underneath. */
export const Counter: React.FC<AnimProps & CounterProps> = (p) => {
  const s = frameState(p, p.t, p.beats, p.dur);
  const box = stageOf(p.vertical);
  // Sized on the finished text so the number never grows past the box while counting.
  const size = Math.min(p.vertical ? 260 : 240, (box.w * 0.92) / (0.62 * Math.max(1, s.finalText.length)));
  const lift = interpolate(s.appear, [0, 1], [30, 0]);
  return (
    <Stage vertical={p.vertical}>
      <div style={{ opacity: s.appear, transform: `translateY(${lift}px)`, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 36 }}>
        <div
          style={{
            fontSize: size,
            fontWeight: 800,
            lineHeight: 1,
            letterSpacing: '-0.03em',
            fontVariantNumeric: 'tabular-nums',
            whiteSpace: 'nowrap',
            ...gradientText,
          }}
        >
          {s.text}
        </div>
        <div style={{ width: interpolate(s.progress, [0, 1], [0, 200]), height: 8, borderRadius: 4, background: GRADIENT }} />
        <div
          style={{
            maxWidth: box.w * 0.9,
            fontSize: p.vertical ? 50 : 44,
            fontWeight: 600,
            lineHeight: 1.25,
            textAlign: 'center',
            color: C.muted,
          }}
        >
          {tx(p.label, p.lang)}
        </div>
      </div>
    </Stage>
  );
};
