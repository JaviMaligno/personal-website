import React from 'react';
import { interpolate } from 'remotion';
import { C, GRADIENT, alpha } from '../brand.ts';
import { tx } from '../types.ts';
import type { AnimProps } from './types.ts';
import { frameState, type BarCompareProps } from './BarCompare.state.ts';
import { Stage, stageOf } from './Stage.tsx';

export { frameState };
export type { BarCompareProps };

/** Horizontal bars that grow one per beat; the highlighted one carries the accent gradient. */
export const BarCompare: React.FC<AnimProps & BarCompareProps> = (p) => {
  const s = frameState(p, p.t, p.beats, p.dur);
  const box = stageOf(p.vertical);
  const n = Math.max(1, s.bars.length);
  const width = p.vertical ? box.w : Math.min(box.w, 1300);
  // Rows shrink a little when there are many bars, so five still fit the stage.
  const k = n <= 3 ? 1 : n === 4 ? 0.9 : 0.8;
  const track = Math.round((p.vertical ? 72 : 60) * k);
  const labelSize = Math.round((p.vertical ? 44 : 38) * k);
  const valueSize = Math.round((p.vertical ? 56 : 48) * k);
  return (
    <Stage vertical={p.vertical}>
      <div style={{ width, display: 'flex', flexDirection: 'column', gap: Math.round((p.vertical ? 56 : 40) * k) }}>
        {s.bars.map((b, i) => (
          <div key={i} style={{ opacity: b.opacity, transform: `translateX(${interpolate(b.opacity, [0, 1], [-24, 0])}px)` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 24, marginBottom: 14 }}>
              <div style={{ fontSize: labelSize, fontWeight: 600, color: b.highlight ? C.text : C.muted, lineHeight: 1.15 }}>
                {tx(b.label, p.lang)}
              </div>
              <div
                style={{
                  fontSize: valueSize,
                  fontWeight: 800,
                  color: b.highlight ? C.accentText : C.text,
                  fontVariantNumeric: 'tabular-nums',
                  whiteSpace: 'nowrap',
                  opacity: interpolate(b.grow, [0.5, 1], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
                }}
              >
                {b.text}
              </div>
            </div>
            <div
              style={{
                height: track,
                borderRadius: track / 3.5,
                background: C.card,
                border: `1px solid ${alpha('#ffffff', 0.07)}`,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${b.width * 100}%`,
                  height: '100%',
                  borderRadius: track / 3.5,
                  background: b.highlight ? GRADIENT : alpha(C.muted, 0.42),
                  boxShadow: b.highlight ? `0 0 40px ${alpha(C.accent, 0.45)}` : 'none',
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </Stage>
  );
};
