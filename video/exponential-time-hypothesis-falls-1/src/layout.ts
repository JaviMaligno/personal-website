// Where things sit on the frame. Pure numbers (no Remotion), so tests can check them.

export const VERTICAL = { w: 1080, h: 1920 } as const;
export const LANDSCAPE = { w: 1920, h: 1080 } as const;

/**
 * Vertical (1080x1920) zones the platform UI draws over, from published overlays (Oct 2026):
 * - top: TikTok's tab bar ends at ~131 px; the Reels header and camera button reach ~220 px.
 *   Text that must be read starts at 220; the decorative badge may sit from 140.
 * - bottom: organic UI (username, one or two caption lines, audio row) measured at 367 px on
 *   TikTok and 420-480 px in the more conservative overlays; Meta's 35 % (672 px) is the ads spec,
 *   with a CTA button that organic posts do not have. 420 keeps captions clear of the organic UI.
 * - right: the action rail (like, comment, share) is 120-150 px wide from ~840 px down.
 * Sources: aicarousels.com TikTok overlay, moda.app and revid.ai checkers, socialync.io (Meta spec).
 */
export const SAFE = { top: 220, bottom: 420, side: 60, rail: 140, railFrom: 840 } as const;

/** Captions: font, rows and the box they sit in. */
export const CAPTION = {
  vertical: { fontSize: 48, lineHeight: 1.22, padY: 16, padX: 28, rows: 2 },
  landscape: { fontSize: 46, lineHeight: 1.22, padY: 18, padX: 30, rows: 2 },
} as const;

/** Height of a two-row caption box. */
export const captionHeight = (vertical: boolean): number => {
  const c = vertical ? CAPTION.vertical : CAPTION.landscape;
  return Math.ceil(c.fontSize * c.lineHeight * c.rows + 2 * c.padY);
};

/**
 * Vertical layout, top to bottom: badge, stage (the animation), captions, platform UI.
 * - Captions sit on the bottom safe line, the lowest place every platform leaves readable, and
 *   are no wider than the frame minus the action rail on both sides (centred, clear of the rail).
 * - The stage takes everything between the badge and the captions.
 */
export const V = (() => {
  const captionBottom = VERTICAL.h - SAFE.bottom;
  const captionTop = captionBottom - captionHeight(true);
  const stageTop = 236;
  const stageBottom = captionTop - 24;
  return {
    badgeTop: 140,
    stageTop,
    stageBottom,
    captionTop,
    captionBottom,
    captionWidth: VERTICAL.w - 2 * SAFE.rail,
  } as const;
})();

/** Where animations may draw. */
export const STAGE = {
  vertical: { top: V.stageTop, bottom: VERTICAL.h - V.stageBottom, side: SAFE.side, w: VERTICAL.w - 2 * SAFE.side, h: V.stageBottom - V.stageTop },
  landscape: { top: 140, bottom: 250, side: 160, w: LANDSCAPE.w - 2 * 160, h: LANDSCAPE.h - 140 - 250 },
} as const;

/** Captions (landscape): distance from the bottom edge. */
export const LANDSCAPE_CAPTION_BOTTOM = 70;
