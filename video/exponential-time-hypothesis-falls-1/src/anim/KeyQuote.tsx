import React from 'react';
import { interpolate } from 'remotion';
import { C, GRADIENT } from '../brand.ts';
import type { AnimProps } from './types.ts';
import { frameState, type KeyQuoteProps } from './KeyQuote.state.ts';
import { Stage, gradientText, stageOf } from './Stage.tsx';

export { frameState };
export type { KeyQuoteProps };

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** The key sentence of the article, word by word, with its emphasised words in the accent. */
export const KeyQuote: React.FC<AnimProps & KeyQuoteProps> = (p) => {
  const s = frameState(p, p.t, p.beats, p.dur, p.lang);
  const box = stageOf(p.vertical);
  // Big for a short sentence, smaller as it grows, so it stays well inside the stage.
  const size = Math.round(interpolate(s.chars, p.vertical ? [40, 170] : [50, 220], p.vertical ? [88, 56] : [76, 50], clamp));
  return (
    <Stage vertical={p.vertical}>
      <div style={{ width: p.vertical ? box.w : Math.min(box.w, 1400), display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 28 }}>
        <div
          style={{
            fontSize: size * 2.2,
            fontWeight: 800,
            lineHeight: 0.6,
            height: size * 0.95,
            opacity: s.words[0]?.opacity ?? 0,
            ...gradientText,
          }}
        >
          &ldquo;
        </div>
        <div style={{ fontSize: size, fontWeight: 700, lineHeight: 1.22, letterSpacing: '-0.015em' }}>
          {s.words.map((w, i) => (
            <React.Fragment key={i}>
              {i > 0 ? ' ' : null}
              <span
                style={{
                  display: 'inline-block',
                  position: 'relative',
                  opacity: w.opacity,
                  transform: `translateY(${interpolate(w.opacity, [0, 1], [18, 0])}px)`,
                  color: w.emphasis ? C.accentText : C.text,
                }}
              >
                {w.text}
                {w.emphasis && (
                  <span
                    style={{
                      position: 'absolute',
                      left: 0,
                      bottom: -size * 0.06,
                      height: Math.max(4, size * 0.07),
                      width: `${s.emphasis * 100}%`,
                      borderRadius: 4,
                      background: GRADIENT,
                    }}
                  />
                )}
              </span>
            </React.Fragment>
          ))}
        </div>
      </div>
    </Stage>
  );
};
