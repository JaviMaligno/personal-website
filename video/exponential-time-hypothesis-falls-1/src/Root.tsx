import React from 'react';
import { Composition } from 'remotion';
import { ArticleVideo, scenesFor, type ArticleVideoProps } from './Video.tsx';
import { GALLERY, GALLERY_SECONDS, Gallery } from './Gallery.tsx';
import { SETTINGS } from './settings.ts';
import { FPS, sceneStarts } from './timing.ts';
import { LANDSCAPE, VERTICAL } from './theme.ts';

// One composition per narration voice and format: Main-EN-vertical, Main-EN-landscape, and the
// ES ones when SETTINGS.voices includes 'es'. Captions follow the voice unless overridden.
export const Root: React.FC = () => (
  <>
    {SETTINGS.voices.flatMap((voice) => {
      const frames = Math.max(1, sceneStarts(scenesFor(voice)).total);
      const subs = SETTINGS.subtitles.includes(voice) ? voice : SETTINGS.subtitles[0] ?? voice;
      return (['vertical', 'landscape'] as const).map((format) => {
        const size = format === 'vertical' ? VERTICAL : LANDSCAPE;
        const props: ArticleVideoProps = { voice, subs, vertical: format === 'vertical' };
        return (
          <Composition
            key={`${voice}-${format}`}
            id={`Main-${voice.toUpperCase()}-${format}`}
            component={ArticleVideo}
            durationInFrames={frames}
            fps={FPS}
            width={size.w}
            height={size.h}
            defaultProps={props}
          />
        );
      });
    })}
    {/* Every animation component in turn, to check the library by eye. */}
    {(['vertical', 'landscape'] as const).map((format) => {
      const size = format === 'vertical' ? VERTICAL : LANDSCAPE;
      return (
        <Composition
          key={`gallery-${format}`}
          id={`Gallery-${format}`}
          component={Gallery}
          durationInFrames={GALLERY.length * GALLERY_SECONDS * FPS}
          fps={FPS}
          width={size.w}
          height={size.h}
          defaultProps={{ vertical: format === 'vertical' }}
        />
      );
    })}
  </>
);
