import React from 'react';
import { C, alpha } from '../brand.ts';
import type { AnimProps } from './types.ts';
import { EDGES, NODES, frameState, type ExpanderCutProps } from './ExpanderCut.state.ts';
import { Stage, stageOf } from './Stage.tsx';

export { frameState };
export type { ExpanderCutProps };

/** "The wall": a tangled ring of clauses; a cut sweeps round and always severs many links. */
export const ExpanderCut: React.FC<AnimProps & ExpanderCutProps> = (p) => {
  const s = frameState(p, p.t, p.beats, p.dur);
  const box = stageOf(p.vertical);
  const W = box.w;
  const H = box.h;
  const R = Math.min(W, H) * 0.4;
  const cx = W / 2;
  const cy = H * 0.44;
  const pt = (i: number) => ({ x: cx + R * NODES[i].x, y: cy + R * NODES[i].y });
  const L = R * 1.25;
  const dx = Math.cos(s.cut.angle) * L;
  const dy = Math.sin(s.cut.angle) * L;
  return (
    <Stage vertical={p.vertical} fill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ opacity: s.appear }}>
        {EDGES.map(([i, j], k) => {
          const a = pt(i);
          const b = pt(j);
          const on = s.crossing[k];
          return (
            <line
              key={k}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={on ? C.accent2 : alpha(C.muted, 0.35)}
              strokeWidth={on ? 6 : 3}
            />
          );
        })}
        <line
          x1={cx - dx}
          y1={cy - dy}
          x2={cx + dx}
          y2={cy + dy}
          stroke={C.text}
          strokeWidth={5}
          strokeDasharray="22 16"
          opacity={s.cut.opacity}
        />
        {NODES.map((_, i) => {
          const a = pt(i);
          return <circle key={i} cx={a.x} cy={a.y} r={22} fill={C.card} stroke={C.accentText} strokeWidth={6} />;
        })}
      </svg>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: cy + R + 90,
          textAlign: 'center',
          opacity: s.label.opacity,
          fontSize: p.vertical ? 56 : 48,
          fontWeight: 700,
          color: C.text,
        }}
      >
        <span style={{ color: C.accent2, fontVariantNumeric: 'tabular-nums' }}>{s.crossCount}</span>
        {p.lang === 'es' ? ' enlaces cortados' : ' links cut'}
        <div style={{ fontSize: p.vertical ? 40 : 36, fontWeight: 600, color: C.muted, marginTop: 14 }}>
          {p.lang === 'es' ? 'cortes donde cortes' : 'wherever you cut'}
        </div>
      </div>
    </Stage>
  );
};
