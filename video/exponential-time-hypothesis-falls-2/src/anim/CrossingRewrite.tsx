import React from 'react';
import { C, alpha } from '../brand.ts';
import type { AnimProps } from './types.ts';
import { frameState, type CrossingRewriteProps } from './CrossingRewrite.state.ts';
import { Stage, stageOf } from './Stage.tsx';

export { frameState };
export type { CrossingRewriteProps };

type Kind = 'cross' | 'row' | 'col';

/** One rectangle: corners x, y (top) and u, v (bottom), drawn with the links of its kind. */
const Rect: React.FC<{ cx: number; cy: number; size: number; kind: Kind; draw?: number; opacity: number }> = ({ cx, cy, size, kind, draw = 1, opacity }) => {
  const h = size / 2;
  const r = size * 0.13;
  const P = { x: [cx - h, cy - h], y: [cx + h, cy - h], u: [cx - h, cy + h], v: [cx + h, cy + h] } as const;
  const seg = (a: readonly number[], b: readonly number[], color: string, w: number, dash?: string) => (
    <line
      x1={a[0]}
      y1={a[1]}
      x2={a[0] + (b[0] - a[0]) * draw}
      y2={a[1] + (b[1] - a[1]) * draw}
      stroke={color}
      strokeWidth={w}
      strokeDasharray={dash}
      strokeLinecap="round"
    />
  );
  const thin = alpha(C.muted, 0.55);
  return (
    <g opacity={opacity}>
      {kind === 'cross' && (
        <>
          {seg(P.x, P.v, C.text, size * 0.035)}
          {seg(P.y, P.u, C.text, size * 0.035)}
        </>
      )}
      {kind !== 'cross' && (
        <>
          {seg(P.x, P.v, thin, size * 0.012, '8 8')}
          {seg(P.y, P.u, thin, size * 0.012, '8 8')}
          <circle cx={cx} cy={cy} r={size * 0.025} fill={C.muted} />
        </>
      )}
      {kind === 'row' && (
        <>
          {seg(P.x, P.y, C.accentText, size * 0.05)}
          {seg(P.u, P.v, C.accentText, size * 0.05)}
        </>
      )}
      {kind === 'col' && (
        <>
          {seg(P.x, P.u, C.accent2, size * 0.05)}
          {seg(P.y, P.v, C.accent2, size * 0.05)}
        </>
      )}
      {(Object.keys(P) as (keyof typeof P)[]).map((k) => (
        <g key={k}>
          <circle cx={P[k][0]} cy={P[k][1]} r={r} fill={C.card} stroke={C.text} strokeWidth={size * 0.02} />
          <text x={P[k][0]} y={P[k][1] + r * 0.36} textAnchor="middle" fontSize={r * 1.05} fontWeight={700} fill={C.text}>
            {k}
          </text>
        </g>
      ))}
    </g>
  );
};

/** The eight-square identity on one rectangle: two crossing checks become two cheap pieces. */
export const CrossingRewrite: React.FC<AnimProps & CrossingRewriteProps> = (p) => {
  const s = frameState(p, p.t, p.beats, p.dur);
  const box = stageOf(p.vertical);
  const W = box.w;
  const H = box.h;
  const es = p.lang === 'es';
  // The crossing: big and centred, then small at the top.
  const cSize = 460 - 200 * s.split;
  const cy = H * 0.42 - (H * 0.42 - 210) * s.split;
  const pieceY = H * 0.66;
  const pSize = 250;
  const lx = W * 0.25;
  const rx = W * 0.75;
  const font = p.vertical ? 46 : 40;
  const label = (x: number, y: number, top: string, bottom: string, color: string, o: number) => (
    <div style={{ position: 'absolute', left: x - 230, width: 460, top: y, textAlign: 'center', opacity: o }}>
      <div style={{ fontSize: font, fontWeight: 800, color }}>{top}</div>
      <div style={{ fontSize: font * 0.78, fontWeight: 600, color: C.muted, marginTop: 6 }}>{bottom}</div>
    </div>
  );
  return (
    <Stage vertical={p.vertical} fill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: 'absolute', inset: 0 }}>
        <Rect cx={W / 2} cy={cy} size={cSize} kind="cross" draw={s.crossing.draw} opacity={s.crossing.appear} />
        <g opacity={s.split}>
          <text x={W / 2} y={cy + cSize / 2 + 95} textAnchor="middle" fontSize={64} fill={C.muted} fontWeight={700}>
            =
          </text>
        </g>
        <Rect cx={lx} cy={pieceY} size={pSize} kind="row" opacity={s.row.appear} />
        <Rect cx={rx} cy={pieceY} size={pSize} kind="col" opacity={s.col.appear} />
        <text x={W / 2} y={pieceY + 22} textAnchor="middle" fontSize={72} fill={C.muted} fontWeight={700} opacity={s.plus.opacity}>
          ±
        </text>
      </svg>
      {label(W / 2, cy + cSize / 2 + 30, es ? '2 × cruce' : '2 × crossing', es ? '6 bits' : '6 bits', C.text, s.crossing.appear * (1 - s.split))}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: cy - cSize / 2 - 110,
          textAlign: 'center',
          fontSize: font * 0.85,
          fontWeight: 700,
          color: C.accentText,
          opacity: s.tag.opacity,
          letterSpacing: '0.04em',
        }}
      >
        {es ? '1818 · octoniones' : '1818 · octonions'}
      </div>
      {label(lx, pieceY + pSize / 2 + 40, es ? 'por filas' : 'row choice', es ? '3 bits' : '3 bits', C.accentText, s.row.appear)}
      {label(rx, pieceY + pSize / 2 + 40, es ? 'por columnas' : 'column choice', es ? '3 bits, en columnas' : '3 bits, by columns', C.accent2, s.col.appear)}
    </Stage>
  );
};
