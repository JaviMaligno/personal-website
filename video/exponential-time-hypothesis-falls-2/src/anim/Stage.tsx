import React from 'react';
import { C } from '../brand.ts';
import { fontFamily } from '../theme.ts';
import { STAGE } from '../layout.ts';

/**
 * Where animations may draw: below the AGILabs badge and above the caption box (layout.ts).
 * Vertical keeps clear of the platform UI (SAFE) and of two caption rows; landscape leaves room
 * for the same.
 */
export { STAGE };

export const stageOf = (vertical: boolean) => (vertical ? STAGE.vertical : STAGE.landscape);

/** Absolutely positioned content box; children are centred unless `fill` asks for the raw box. */
export const Stage: React.FC<{ vertical: boolean; children: React.ReactNode; fill?: boolean; style?: React.CSSProperties }> = ({
  vertical,
  children,
  fill,
  style,
}) => {
  const s = stageOf(vertical);
  return (
    <div
      style={{
        position: 'absolute',
        top: s.top,
        left: s.side,
        width: s.w,
        height: s.h,
        fontFamily,
        color: C.text,
        ...(fill ? {} : { display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }),
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** Gradient-filled text, the website's accent treatment for big figures. */
export const gradientText: React.CSSProperties = {
  backgroundImage: `linear-gradient(135deg, ${C.accentText}, ${C.accent2})`,
  backgroundClip: 'text',
  WebkitBackgroundClip: 'text',
  color: 'transparent',
  WebkitTextFillColor: 'transparent',
};
