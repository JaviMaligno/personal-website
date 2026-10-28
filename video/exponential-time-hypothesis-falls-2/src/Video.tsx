import React from 'react';
import { AbsoluteFill, Sequence, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { Audio } from '@remotion/media';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { AUDIO, WORDS } from './audio.generated.ts';
import { resolveMark } from './marks.ts';
import { VIDEOS } from './timeline.ts';
import { FPS, SCENE_TRANSITION, handOverAt, linesInVideo, sceneFrames } from './timing.ts';
import { SETTINGS } from './settings.ts';
import { musicVolume } from './music.ts';
import { C } from './brand.ts';
import { fontFamily, V } from './theme.ts';
import { ANIMS } from './anim/index.ts';
import { Background } from './components/Background.tsx';
import { Intro, Outro } from './components/Cards.tsx';
import { Captions } from './components/Captions.tsx';
import { Cameo, type CameoSpec } from './components/Cameo.tsx';
import { Badge } from './components/Brand.tsx';
import { dip } from './components/Dip.tsx';
import type { Lang, Scene } from './types.ts';

/** noSubs: no captions (poster frames and thumbnails). */
export type ArticleVideoProps = { voice: Lang; subs: Lang; vertical: boolean; noSubs?: boolean };

export const scenesFor = (voice: Lang): Scene[] => {
  const cuts = VIDEOS[voice];
  if (!cuts) throw new Error(`No timeline for voice "${voice}": add it to SETTINGS.voices.`);
  return cuts.main;
};

/** An anim scene: the registered component, given scene time and the narration beats. */
const AnimView: React.FC<{ scene: Scene; p: ArticleVideoProps }> = ({ scene, p }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const name = scene.anim?.name ?? '';
  const Comp = ANIMS[name];
  if (!Comp) {
    return (
      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', fontFamily, color: C.muted, fontSize: 44 }}>
        Missing animation: {name || '(none)'}
      </AbsoluteFill>
    );
  }
  return (
    <Comp
      {...(scene.anim?.props ?? {})}
      t={frame / fps}
      beats={scene.beats}
      dur={sceneFrames(scene) / FPS}
      lang={p.voice}
      vertical={p.vertical}
    />
  );
};

/** The avatar cameos of an anim scene (`cameos` in its props), each landing on its mark. */
const Cameos: React.FC<{ scene: Scene; vertical: boolean }> = ({ scene, vertical }) => {
  const cameos = (scene.anim?.props as { cameos?: CameoSpec[] } | undefined)?.cameos;
  if (!cameos?.length) return null;
  const lang = scene.lines[0]?.voice ?? 'en';
  return (
    <>
      {cameos.map((c, i) => (
        <Cameo
          key={i}
          pose={c.pose}
          at={typeof c.at === 'number' ? c.at : resolveMark(scene.lines, c.at, WORDS[lang], lang)}
          dur={c.dur}
          side={c.side}
          vertical={vertical}
        />
      ))}
    </>
  );
};

const SceneView: React.FC<{ scene: Scene; p: ArticleVideoProps }> = ({ scene, p }) => {
  // The intro shows its first line as the big hook, so the captions start from the second line.
  const captioned = scene.kind === 'intro' ? scene.lines.slice(1) : scene.lines;
  return (
    <AbsoluteFill>
      {scene.kind === 'intro' && <Intro hook={scene.lines[0]} lang={p.subs} vertical={p.vertical} />}
      {scene.kind === 'outro' && <Outro lang={p.subs} vertical={p.vertical} />}
      {scene.kind === 'anim' && (
        <>
          <AnimView scene={scene} p={p} />
          <div style={{ position: 'absolute', top: p.vertical ? V.badgeTop : 48, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
            <Badge size={p.vertical ? 1.1 : 0.9} />
          </div>
          {!p.noSubs && <Cameos scene={scene} vertical={p.vertical} />}
        </>
      )}
      {!p.noSubs && <Captions lines={captioned} lang={p.subs} vertical={p.vertical} until={handOverAt(scene)} />}
      {/* Before the TTS script has run there is no audio: the scene plays silent on estimated timing. */}
      {scene.lines
        .filter((l) => AUDIO[l.voice]?.[l.key] !== undefined)
        .map((l) => (
          <Sequence key={l.key} from={Math.round(l.start * FPS)} durationInFrames={Math.ceil((l.dur + 0.25) * FPS)}>
            <Audio src={staticFile(`audio/${l.voice}/${l.key}.wav`)} />
          </Sequence>
        ))}
    </AbsoluteFill>
  );
};

const Music: React.FC<{ scenes: Scene[] }> = ({ scenes }) => {
  const { durationInFrames } = useVideoConfig();
  const music = SETTINGS.music;
  const spans = React.useMemo(() => linesInVideo(scenes).map(({ line, at }) => ({ from: at, to: at + line.dur })), [scenes]);
  if (!music) return null;
  const total = durationInFrames / FPS;
  return (
    <Audio
      src={staticFile(music.src)}
      loop
      loopVolumeCurveBehavior="extend"
      volume={(f) => musicVolume(f / FPS, spans, total, music)}
    />
  );
};

export const ArticleVideo: React.FC<ArticleVideoProps> = (p) => {
  const scenes = scenesFor(p.voice);
  return (
    <AbsoluteFill style={{ background: C.bg0 }}>
      <Background />
      <Music scenes={scenes} />
      <TransitionSeries>
        {scenes.map((scene, i) => (
          <React.Fragment key={scene.id}>
            <TransitionSeries.Sequence durationInFrames={sceneFrames(scene)}>
              <SceneView scene={scene} p={p} />
            </TransitionSeries.Sequence>
            {i < scenes.length - 1 && (
              <TransitionSeries.Transition presentation={dip()} timing={linearTiming({ durationInFrames: SCENE_TRANSITION })} />
            )}
          </React.Fragment>
        ))}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
