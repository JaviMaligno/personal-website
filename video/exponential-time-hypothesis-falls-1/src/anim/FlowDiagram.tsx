import React, { useMemo } from 'react';
import { Easing, interpolate } from 'remotion';
import { C, alpha } from '../brand.ts';
import { tx } from '../types.ts';
import type { AnimProps } from './types.ts';
import { edgeSegments, flowGeometry, frameState, type FlowDiagramProps, type Point } from './FlowDiagram.state.ts';
import { Stage, stageOf } from './Stage.tsx';

export { frameState, flowGeometry };
export type { FlowDiagramProps };

const pts = (p: Point[]) => p.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');

/** Arrow head at the end of a polyline, pointing along its last segment. */
const Head: React.FC<{ line: Point[]; color: string; size: number }> = ({ line, color, size }) => {
  const [x0, y0] = line[line.length - 2];
  const [x1, y1] = line[line.length - 1];
  const a = Math.atan2(y1 - y0, x1 - x0);
  const p = (da: number, r: number): Point => [x1 + r * Math.cos(a + da), y1 + r * Math.sin(a + da)];
  return <polygon points={pts([[x1, y1], p(Math.PI - 0.45, size), p(Math.PI + 0.45, size)])} fill={color} />;
};

/** Boxes and arrows that appear in order; a broken edge is dashed and muted, with a gap. */
export const FlowDiagram: React.FC<AnimProps & FlowDiagramProps> = (p) => {
  const s = frameState(p, p.t, p.beats, p.dur);
  const box = stageOf(p.vertical);
  const geo = useMemo(() => flowGeometry(p, { w: box.w, h: box.h }), [p.nodes, p.edges, p.layout, box.w, box.h]);
  const nodeH = geo.nodes[0]?.h ?? 100;
  const nodeW = geo.nodes[0]?.w ?? 300;
  const fontSize = Math.round(Math.max(26, Math.min(46, nodeH * 0.32, nodeW * 0.12)));
  const labelSize = p.vertical ? 32 : 28;
  return (
    <Stage vertical={p.vertical} fill>
      <svg width={box.w} height={box.h} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
        {geo.edges.map((e, i) => {
          const st = s.edges[i];
          if (!e.valid || !st.valid) return null;
          const color = st.broken ? C.muted : C.accentText;
          const parts = edgeSegments(e.points, st.draw, st.broken);
          return (
            <g key={i}>
              {parts.map((seg, j) => (
                <polyline
                  key={j}
                  points={pts(seg)}
                  fill="none"
                  stroke={color}
                  strokeWidth={st.broken ? 5 : 6}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeDasharray={st.broken ? '14 14' : undefined}
                  opacity={st.broken ? 0.85 : 1}
                />
              ))}
              {st.draw >= 1 && !st.broken && <Head line={e.points} color={color} size={22} />}
            </g>
          );
        })}
      </svg>
      {geo.edges.map((e, i) => {
        const st = s.edges[i];
        const label = p.edges[i]?.label;
        if (!e.valid || !st.valid || label === undefined) return null;
        const [x, y] = e.label;
        return (
          <div
            key={`l${i}`}
            style={{
              position: 'absolute',
              left: e.labelAlign === 'left' ? x : x - 160,
              top: y,
              width: e.labelAlign === 'left' ? Math.max(120, box.w - x) : 320,
              transform: 'translateY(-50%)',
              textAlign: e.labelAlign,
              fontSize: labelSize,
              fontWeight: 600,
              lineHeight: 1.15,
              color: st.broken ? C.muted : C.accentText,
              fontStyle: st.broken ? 'italic' : 'normal',
              opacity: interpolate(st.draw, [0.4, 1], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
            }}
          >
            {tx(label, p.lang)}
          </div>
        );
      })}
      {geo.nodes.map((n, i) => {
        const appear = s.nodes[i]?.appear ?? 0;
        const scale = interpolate(appear, [0, 1], [0.86, 1], { easing: Easing.out(Easing.back(1.6)) });
        return (
          <div
            key={n.id}
            style={{
              position: 'absolute',
              left: n.x - n.w / 2,
              top: n.y - n.h / 2,
              width: n.w,
              height: n.h,
              boxSizing: 'border-box',
              opacity: appear,
              transform: `scale(${scale})`,
              borderRadius: 24,
              background: C.card,
              border: `2px solid ${alpha(C.accent, 0.45)}`,
              boxShadow: `0 0 36px ${alpha(C.accent, 0.18)}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '0 20px',
              fontSize,
              fontWeight: 700,
              lineHeight: 1.15,
              textAlign: 'center',
              color: C.text,
            }}
          >
            {tx(p.nodes[i].label, p.lang)}
          </div>
        );
      })}
    </Stage>
  );
};
