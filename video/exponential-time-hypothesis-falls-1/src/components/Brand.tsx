import React from 'react';
import { BRAND, C } from '../brand.ts';
import { fontFamily } from '../theme.ts';

/**
 * The AGILabs text badge, styled like the website header (uppercase, letter-spaced, thin border).
 * The site draws its text muted; here it is full white so it stays legible at video size.
 */
export const Badge: React.FC<{ size?: number; style?: React.CSSProperties }> = ({ size = 1, style }) => (
  <div
    style={{
      fontFamily,
      fontSize: 26 * size,
      fontWeight: 600,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color: C.text,
      padding: `${10 * size}px ${20 * size}px`,
      border: `${Math.max(1, 2 * size)}px solid rgba(255,255,255,0.16)`,
      borderRadius: 10 * size,
      background: 'rgba(255,255,255,0.03)',
      lineHeight: 1,
      whiteSpace: 'nowrap',
      ...style,
    }}
  >
    {BRAND.name}
  </div>
);

/** The site address, in the accent text colour. */
export const Site: React.FC<{ size?: number; style?: React.CSSProperties }> = ({ size = 1, style }) => (
  <div style={{ fontFamily, fontSize: 40 * size, fontWeight: 600, color: C.accentText, letterSpacing: '0.01em', ...style }}>
    {BRAND.site}
  </div>
);
