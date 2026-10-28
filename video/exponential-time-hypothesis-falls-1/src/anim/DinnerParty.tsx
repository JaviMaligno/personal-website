import React from 'react';
import { Img, staticFile } from 'remotion';
import { C, alpha } from '../brand.ts';
import type { AnimProps } from './types.ts';
import { CONDITIONS, FRIENDS, LIST, frameState, type DinnerPartyProps } from './DinnerParty.state.ts';
import { Stage, gradientText, stageOf } from './Stage.tsx';

export { frameState };
export type { DinnerPartyProps };

const GREEN = '#34d399';
const RED = '#f87171';

/** The dinner-party version of 3-SAT: friends as yes/no choices, conditions as cards. */
export const DinnerParty: React.FC<AnimProps & DinnerPartyProps> = (p) => {
  const s = frameState(p, p.t, p.beats, p.dur);
  const box = stageOf(p.vertical);
  const W = box.w;
  const es = p.lang === 'es';
  const col = W / FRIENDS.length;
  return (
    <Stage vertical={p.vertical} fill>
      <div style={{ position: 'absolute', top: 40, left: 0, width: W, display: 'flex' }}>
        {FRIENDS.map((name, i) => {
          const f = s.friends[i];
          const c = s.chips[i];
          const yes = LIST[i];
          // In 'intro' the chip flickers between yes and no: the choice is open.
          const flickYes = Math.floor(p.t * 3 + i) % 2 === 0;
          const shownYes = c.fill > 0.5 ? yes : flickYes;
          const chipColor = c.fill > 0.5 ? (yes ? GREEN : RED) : C.muted;
          return (
            <div key={name} style={{ width: col, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, opacity: f.appear, transform: `translateY(${(1 - f.appear) * 30}px)` }}>
              {/* Each friend is a caricature (public/friends/friend-<name>.png), not a letter. */}
              <div style={{ width: 150, height: 150, borderRadius: 75, background: C.card, border: `6px solid ${C.accentText}`, overflow: 'hidden', display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
                <Img src={staticFile(`friends/friend-${name.toLowerCase()}.png`)} style={{ width: '112%', height: '112%', objectFit: 'cover', objectPosition: 'center 20%' }} />
              </div>
              <div style={{ fontSize: 44, fontWeight: 700, color: C.text }}>{name}</div>
              <div
                style={{
                  opacity: c.appear,
                  minWidth: 120,
                  padding: '8px 22px',
                  borderRadius: 40,
                  border: `4px solid ${chipColor}`,
                  color: chipColor,
                  fontSize: 38,
                  fontWeight: 800,
                  textAlign: 'center',
                }}
              >
                {shownYes ? (es ? 'sí' : 'yes') : 'no'}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: 'absolute', top: 430, left: 0, width: W, display: 'flex', flexDirection: 'column', gap: 34 }}>
        {CONDITIONS.map((c, i) => {
          const k = s.cards[i];
          return (
            <div
              key={i}
              style={{
                opacity: k.appear,
                transform: `translateX(${(1 - k.appear) * 60}px)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '30px 40px',
                borderRadius: 26,
                background: alpha(C.card, 0.95),
                border: `3px solid ${k.tick > 0.5 ? GREEN : alpha(C.muted, 0.35)}`,
                fontSize: 48,
                fontWeight: 600,
                color: C.text,
              }}
            >
              <span>“{es ? c.es : c.en}”</span>
              <span style={{ color: GREEN, fontSize: 64, fontWeight: 800, opacity: k.tick, transform: `scale(${0.6 + 0.4 * k.tick})` }}>✓</span>
            </div>
          );
        })}
      </div>
      <div
        style={{
          position: 'absolute',
          top: 980,
          left: 0,
          width: W,
          textAlign: 'center',
          fontSize: 96,
          fontWeight: 900,
          letterSpacing: '0.02em',
          opacity: s.stamp.appear,
          transform: `scale(${1.3 - 0.3 * s.stamp.appear})`,
          ...gradientText,
        }}
      >
        3-SAT
      </div>
    </Stage>
  );
};
