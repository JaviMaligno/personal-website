import { loadFont } from '@remotion/google-fonts/Inter';

export const { fontFamily } = loadFont('normal', {
  weights: ['400', '500', '600', '700', '800'],
  subsets: ['latin'],
});

// Frame sizes, platform safe zones and the vertical layout live in layout.ts (pure, tested).
export { VERTICAL, LANDSCAPE, SAFE, V } from './layout.ts';
