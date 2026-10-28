import React from 'react';
import { Img, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { V } from '../theme.ts';
import type { MarkSpec } from '../marks.ts';

/** Avatar cut-outs, transparent PNGs at public/avatar/avatar-<pose>.png. */
export type CameoPose = 'amazed' | 'sceptical' | 'thinking' | 'laughing' | 'laptop' | 'pointing' | 'neutral';

/**
 * A cameo as written in an anim scene's props (`cameos: [...]`): `at` is a mark
 * ([line index, word], so it lands on the spoken word) or scene seconds.
 */
export type CameoSpec = { pose: CameoPose; at: MarkSpec | number; dur?: number; side?: 'left' | 'right' };

const SIZE = 300;

/**
 * The author's avatar popping up from a bottom corner for a couple of seconds: a reaction at the
 * moment of a reveal, or the author's own role in the work ("I trained…"). `at` is resolved to
 * scene seconds by the caller.
 */
export const Cameo: React.FC<{ pose: CameoPose; at: number; dur?: number; side?: 'left' | 'right'; vertical: boolean }> = ({
  pose,
  at,
  dur = 2.4,
  side = 'left',
  vertical,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const start = Math.round(at * fps);
  const end = start + Math.round(dur * fps);
  if (frame < start - 2 || frame > end + 14) return null;
  const inP = spring({ frame: frame - start, fps, config: { damping: 14, stiffness: 180 }, durationInFrames: 14 });
  const outP = spring({ frame: frame - end, fps, config: { damping: 200 }, durationInFrames: 12 });
  const p = inP * (1 - outP);
  const size = vertical ? SIZE : 300;
  // Vertical: standing on the bottom safe line, peeking out behind the caption box (captions are
  // drawn after it, so they stay on top) and below the stage, which fills the frame down to them.
  const bottom = vertical ? 1920 - V.captionBottom : 150;
  return (
    <div
      style={{
        position: 'absolute',
        [side]: vertical ? -6 : 60,
        bottom,
        width: size,
        height: size,
        transform: `translateY(${(1 - p) * 60}px) scale(${0.7 + 0.3 * p}) rotate(${(side === 'left' ? -1 : 1) * (1 - p) * 8}deg)`,
        transformOrigin: side === 'left' ? 'bottom left' : 'bottom right',
        opacity: p,
        filter: 'drop-shadow(0 10px 24px rgba(0,0,0,0.55))',
      }}
    >
      <Img src={staticFile(`avatar/avatar-${pose}.png`)} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
    </div>
  );
};
