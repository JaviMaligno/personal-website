import React, { useMemo } from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, GRADIENT } from '../brand.ts';
import { fontFamily, SAFE, V } from '../theme.ts';
import { SETTINGS } from '../settings.ts';
import { tokensOf } from '../captions.ts';
import { tx, type Lang, type Line } from '../types.ts';
import { Badge, Site } from './Brand.tsx';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** Hook size: big for a short hook, smaller as it grows, so it stays a few lines tall. */
const hookSize = (chars: number, vertical: boolean) => {
  const [big, small] = vertical ? [96, 64] : [84, 56];
  return Math.round(interpolate(chars, [30, 110], [big, small], clamp));
};

/**
 * Opening card: the AGILabs badge at the top and the first narration line as a big hook, its
 * words lighting up as they are spoken (so the hook doubles as its own caption).
 */
export const Intro: React.FC<{ hook?: Line; lang: Lang; vertical: boolean }> = ({ hook, lang, vertical }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const tokens = useMemo(() => (hook ? tokensOf(hook, lang) : []), [hook, lang]);
  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 20 });
  const text = hook?.text[lang] ?? '';
  const size = hookSize(text.length, vertical);
  return (
    <div style={{ position: 'absolute', inset: 0, fontFamily }}>
      <div style={{ position: 'absolute', top: vertical ? V.badgeTop : 80, left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: enter }}>
        <Badge size={vertical ? 1.5 : 1.2} />
      </div>
      <div
        style={{
          position: 'absolute',
          left: vertical ? SAFE.side : 200,
          right: vertical ? SAFE.side : 200,
          top: 0,
          bottom: 0,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 48,
          transform: `translateY(${(1 - enter) * 40}px)`,
          opacity: enter,
        }}
      >
        <div style={{ fontSize: size, fontWeight: 800, lineHeight: 1.12, letterSpacing: '-0.02em', textAlign: 'center', color: C.text }}>
          {tokens.map((tok, i) => {
            const said = t >= tok.start;
            const active = said && t < tok.end;
            return (
              <React.Fragment key={i}>
                {i > 0 ? ' ' : null}
                <span style={{ color: active ? C.accentText : C.text, opacity: said ? 1 : 0.28 }}>{tok.text}</span>
              </React.Fragment>
            );
          })}
        </div>
        <div style={{ width: interpolate(frame, [8, 30], [0, 160], clamp), height: 8, borderRadius: 4, background: GRADIENT }} />
      </div>
    </div>
  );
};

/** Closing card: AGILabs badge, the site address and the article's title. */
export const Outro: React.FC<{ lang: Lang; vertical: boolean }> = ({ lang, vertical }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = (delay: number) => spring({ frame: frame - delay, fps, config: { damping: 200 }, durationInFrames: 22 });
  const item = (delay: number): React.CSSProperties => ({ opacity: pop(delay), transform: `translateY(${(1 - pop(delay)) * 30}px)` });
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        // Vertical: centred between the badge line and the caption box.
        paddingTop: vertical ? V.badgeTop : 0,
        paddingBottom: vertical ? 1920 - V.stageBottom : 140,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        gap: vertical ? 44 : 32,
        fontFamily,
      }}
    >
      <div style={item(0)}>
        <Badge size={vertical ? 2.4 : 2} />
      </div>
      <div style={item(6)}>
        <Site size={vertical ? 1.5 : 1.3} />
      </div>
      <div style={{ ...item(12), width: 120, height: 6, borderRadius: 3, background: GRADIENT }} />
      <div
        style={{
          ...item(16),
          maxWidth: vertical ? 860 : 1300,
          fontSize: vertical ? 40 : 38,
          fontWeight: 500,
          lineHeight: 1.3,
          color: C.muted,
          textAlign: 'center',
        }}
      >
        {tx(SETTINGS.articleTitle, lang)}
      </div>
    </div>
  );
};
