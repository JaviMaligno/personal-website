// AGILabs brand tokens, mirrored from the javieraguilar.ai dark theme.
// Kept free of Remotion imports so plain `node --test` can load it.

export const C = {
  bg0: '#0a0a0f',
  bg1: '#12121a',
  card: '#1a1a24',
  accent: '#6366f1',
  accent2: '#8b5cf6',
  accentText: '#818cf8',
  text: '#f8fafc',
  muted: '#94a3b8',
} as const;

export const GRADIENT = `linear-gradient(135deg, ${C.accent}, ${C.accent2})`;

export const BRAND = { name: 'AGILabs', site: 'javieraguilar.ai' } as const;

/** `#rgb` or `#rrggbb` plus an opacity (clamped to 0..1) as a CSS `rgba()` string. */
export function alpha(hex: string, a: number): string {
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) throw new Error(`alpha(): not a hex colour: ${hex}`);
  let h = m[1];
  if (h.length === 3) h = h.split('').map((ch) => ch + ch).join('');
  const n = parseInt(h, 16);
  const op = Math.min(1, Math.max(0, a));
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${op})`;
}
