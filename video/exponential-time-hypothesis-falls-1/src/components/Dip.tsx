import React from 'react';
import { AbsoluteFill, interpolate } from 'remotion';
import type { TransitionPresentation, TransitionPresentationComponentProps } from '@remotion/transitions';

type DipProps = Record<string, never>;

// The outgoing scene fades out over the first half, the incoming one fades in over the second,
// so the background shows through for a moment between them.
const DipView: React.FC<TransitionPresentationComponentProps<DipProps>> = ({ children, presentationDirection, presentationProgress }) => {
  const p = presentationProgress;
  const opacity =
    presentationDirection === 'exiting'
      ? interpolate(p, [0, 0.5], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
      : interpolate(p, [0.5, 1], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};

export const dip = (): TransitionPresentation<DipProps> => ({ component: DipView, props: {} });
