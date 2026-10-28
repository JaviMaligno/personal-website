import React, { useMemo } from 'react';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, alpha } from '../brand.ts';
import { fontFamily } from '../theme.ts';
import { CAPTION, LANDSCAPE_CAPTION_BOTTOM, V, VERTICAL } from '../layout.ts';
import { cuesOfLines, cueRowTokens, type Token } from '../captions.ts';
import type { Lang, Line } from '../types.ts';

/** Characters per caption row: narrow on vertical so a row stays within the rail-free width. */
export const ROW_CHARS = { vertical: 32, landscape: 42 } as const;

// Vertical: the box's bottom edge on the bottom safe line, no wider than the rail-free width.
const VERTICAL_STYLE = { ...CAPTION.vertical, width: V.captionWidth, bottom: VERTICAL.h - V.captionBottom };
const LANDSCAPE_STYLE = { ...CAPTION.landscape, width: 1500, bottom: LANDSCAPE_CAPTION_BOTTOM };

/**
 * Karaoke captions: the current cue in one or two rows, the word being spoken in the accent text
 * colour. Times are scene seconds, so this must sit inside the scene's Sequence.
 */
/** `until`: scene second where the hand-over to the next scene starts; held cues stop there. */
export const Captions: React.FC<{ lines: Line[]; lang: Lang; vertical: boolean; until?: number }> = ({ lines, lang, vertical, until }) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const t = frame / fps;
  const maxChars = vertical ? ROW_CHARS.vertical : ROW_CHARS.landscape;
  const cues = useMemo(() => cuesOfLines(lines, lang, maxChars, until), [lines, lang, maxChars, until]);
  const cue = cues.find((c) => t >= c.start && t < c.end);
  if (!cue) return null;
  const st = vertical ? VERTICAL_STYLE : LANDSCAPE_STYLE;
  const fadeIn = interpolate(t - cue.start, [0, 0.12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const rows = cueRowTokens(cue, maxChars);
  const word = (tok: Token, i: number) => {
    const active = t >= tok.start && t < tok.end;
    return (
      <span key={i} style={{ color: active ? C.accentText : C.text, transition: 'none' }}>
        {tok.text}
      </span>
    );
  };
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: st.bottom,
        display: 'flex',
        justifyContent: 'center',
        opacity: fadeIn,
        // Keep clear of the top half on short landscape frames.
        maxHeight: height / 2,
      }}
    >
      <div
        style={{
          maxWidth: st.width,
          padding: `${st.padY}px ${st.padX}px`,
          borderRadius: 22,
          background: alpha(C.bg0, 0.72),
          border: `1px solid ${alpha('#ffffff', 0.08)}`,
          fontFamily,
          fontSize: st.fontSize,
          fontWeight: 700,
          lineHeight: st.lineHeight,
          textAlign: 'center',
          letterSpacing: '-0.005em',
        }}
      >
        {rows.map((row, r) => (
          <div key={r} style={{ whiteSpace: 'nowrap' }}>
            {row.map((tok, i) => (
              <React.Fragment key={i}>
                {i > 0 && !tok.glued ? ' ' : null}
                {word(tok, i)}
              </React.Fragment>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};
