import React from 'react';
import { Easing, interpolate } from 'remotion';
import { C, alpha } from '../brand.ts';
import { tx } from '../types.ts';
import type { AnimProps } from './types.ts';
import { frameState, gridShape, type StatGridProps } from './StatGrid.state.ts';
import { Stage, gradientText, stageOf } from './Stage.tsx';

export { frameState, gridShape };
export type { StatGridProps };

const GAP = 32;

/** Two to four figure tiles that pop in one per beat. */
export const StatGrid: React.FC<AnimProps & StatGridProps> = (p) => {
  const s = frameState(p, p.t, p.beats, p.dur);
  const box = stageOf(p.vertical);
  const { cols, rows } = gridShape(s.tiles.length, p.vertical);
  const tileW = (Math.min(box.w, p.vertical ? box.w : 1500) - GAP * (cols - 1)) / cols;
  const tileH = Math.min(p.vertical ? 300 : 360, (box.h - GAP * (rows - 1)) / rows);
  const longest = Math.max(1, ...s.tiles.map((x) => x.value.length));
  // One size for every value, set by the longest, so the tiles read as a set.
  const valueSize = Math.min(tileH * 0.45, (tileW * 0.84) / (0.6 * longest), 150);
  return (
    <Stage vertical={p.vertical}>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, ${tileW}px)`, gap: GAP }}>
        {s.tiles.map((tile, i) => {
          const scale = interpolate(tile.pop, [0, 1], [0.82, 1], { easing: Easing.out(Easing.back(1.8)) });
          return (
            <div
              key={i}
              style={{
                height: tileH,
                opacity: tile.opacity,
                transform: `scale(${scale})`,
                borderRadius: 28,
                background: C.card,
                border: `1px solid ${alpha(C.accent, 0.28)}`,
                boxShadow: `0 20px 60px ${alpha('#000000', 0.35)}`,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                gap: 14,
                padding: '0 28px',
                boxSizing: 'border-box',
              }}
            >
              <div style={{ fontSize: valueSize, fontWeight: 800, lineHeight: 1, letterSpacing: '-0.02em', whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums', ...gradientText }}>
                {tile.value}
              </div>
              <div style={{ fontSize: Math.max(30, Math.min(42, valueSize * 0.34)), fontWeight: 600, color: C.muted, textAlign: 'center', lineHeight: 1.2 }}>
                {tx(tile.label, p.lang)}
              </div>
            </div>
          );
        })}
      </div>
    </Stage>
  );
};
