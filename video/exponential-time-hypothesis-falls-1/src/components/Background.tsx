import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, alpha } from '../brand.ts';

/** Dark site background with a soft accent glow that drifts slowly. */
export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const s = frame / fps;
  const x = 50 + 8 * Math.sin(s / 6);
  const y = 30 + 6 * Math.cos(s / 7);
  const r = Math.max(width, height) * 0.6;
  return (
    <AbsoluteFill style={{ background: C.bg0 }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(${r}px circle at ${x}% ${y}%, ${alpha(C.accent, 0.16)}, ${alpha(C.accent2, 0.06)} 45%, transparent 70%)`,
        }}
      />
      <AbsoluteFill style={{ background: `linear-gradient(180deg, transparent 55%, ${alpha(C.bg1, 0.85)})` }} />
    </AbsoluteFill>
  );
};
