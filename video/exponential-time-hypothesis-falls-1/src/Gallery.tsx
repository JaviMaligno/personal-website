// A reel of every animation component, 4 s each, with a sample caption: for checking the
// library by eye (stills) after changing a component. Not part of any video.
import React from 'react';
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from 'remotion';
import { C } from './brand.ts';
import { V } from './theme.ts';
import { ANIMS } from './anim/index.ts';
import { Background } from './components/Background.tsx';
import { Badge } from './components/Brand.tsx';
import { Captions } from './components/Captions.tsx';
import type { Line } from './types.ts';

export const GALLERY_SECONDS = 4;

type Sample = { name: string; props: Record<string, unknown>; beats: number[]; caption: string };

export const GALLERY: Sample[] = [
  {
    name: 'Counter',
    props: { value: 83, suffix: '%', label: 'of the runs followed through' },
    beats: [0.3],
    caption: 'Most of the runs followed through on the plan.',
  },
  {
    name: 'BarCompare',
    props: {
      bars: [
        { label: 'With the reason', value: 14, display: '14/20', highlight: true },
        { label: 'Without it', value: 4, display: '4/20' },
      ],
      max: 20,
    },
    beats: [0.3, 1.2],
    caption: 'Giving the reason changed the outcome more than anything else.',
  },
  {
    name: 'FlowDiagram',
    props: {
      layout: 'vertical',
      nodes: [
        { id: 'plan', label: 'Planner' },
        { id: 'lead', label: 'Team lead' },
        { id: 'impl', label: 'Implementer' },
      ],
      edges: [
        { from: 'plan', to: 'lead', label: 'plan + why' },
        { from: 'lead', to: 'impl', label: 'only the what', broken: true },
      ],
    },
    beats: [0.2, 0.9, 1.7],
    caption: 'Each hand-off keeps the task and drops the reason.',
  },
  {
    name: 'KeyQuote',
    props: { text: 'The reason is the first thing to get lost on the way down.', emphasis: ['reason', 'lost'] },
    beats: [0.3],
    caption: 'That was the pattern in every run.',
  },
  {
    name: 'StatGrid',
    props: {
      stats: [
        { value: '14/20', label: 'with the reason' },
        { value: '4/20', label: 'without it' },
        { value: '0.0018', label: 'p-value' },
      ],
    },
    beats: [0.3, 0.9, 1.5],
    caption: 'Three numbers sum it up.',
  },
];

const sampleLine = (s: Sample, i: number): Line => ({
  key: `gallery-${i}`,
  start: 0.2,
  dur: GALLERY_SECONDS - 0.6,
  text: { en: s.caption, es: s.caption },
  voice: 'en',
});

const Segment: React.FC<{ sample: Sample; index: number; vertical: boolean }> = ({ sample, index, vertical }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const Comp = ANIMS[sample.name];
  return (
    <AbsoluteFill>
      <Comp {...sample.props} t={frame / fps} beats={sample.beats} dur={GALLERY_SECONDS} lang="en" vertical={vertical} />
      <div style={{ position: 'absolute', top: vertical ? V.badgeTop : 48, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
        <Badge size={vertical ? 1.1 : 0.9} />
      </div>
      <Captions lines={[sampleLine(sample, index)]} lang="en" vertical={vertical} />
    </AbsoluteFill>
  );
};

export const Gallery: React.FC<{ vertical: boolean }> = ({ vertical }) => {
  const { fps } = useVideoConfig();
  const len = GALLERY_SECONDS * fps;
  return (
    <AbsoluteFill style={{ background: C.bg0 }}>
      <Background />
      {GALLERY.map((s, i) => (
        <Sequence key={s.name} from={i * len} durationInFrames={len}>
          <Segment sample={s} index={i} vertical={vertical} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
