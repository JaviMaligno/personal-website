// Pure state of the DinnerParty scene: the article's dinner example of 3-SAT.
// mode 'intro': four friends appear, then three conditions one per beat 0..2 (cards), a yes/no
//   chip under each friend on beat 3, and a "3-SAT" stamp on beat 4.
// mode 'check': everything already on screen; one guest list fills in (Ana yes, Bea no, Carlos
//   yes, Diego no) and each condition gets its tick, one after another: checking is one pass.
// No Remotion or React here.
import { beatAt, clamp01, easeOutCubic, progress, sceneTime } from './steps.ts';

export type DinnerMode = 'intro' | 'check';
export type DinnerPartyProps = { mode?: DinnerMode };

export const FRIENDS = ['Ana', 'Bea', 'Carlos', 'Diego'] as const;
/** The guest list that is checked: Ana yes, Bea no, Carlos yes, Diego no (meets all three). */
export const LIST = [true, false, true, false] as const;
export const CONDITIONS = [
  { en: "Ana comes, or Bea doesn't", es: 'Viene Ana, o no viene Bea' },
  { en: 'Carlos or Diego, at least one', es: 'Carlos o Diego, al menos uno' },
  { en: 'Not Ana, Bea and Carlos together', es: 'Ana, Bea y Carlos juntos no' },
] as const;

const fin = (x: number, d = 0) => (Number.isFinite(x) ? x : d);
const beatOr = (beats: number[], i: number, d: number): number => {
  const b = beats[i];
  return b !== undefined && Number.isFinite(b) ? b : d;
};

export type DinnerPartyState = {
  friends: { appear: number }[];
  cards: { appear: number; tick: number }[];
  /** Yes/no chips under the friends: 0 hidden, 1 shown. */
  chips: { appear: number; fill: number }[];
  /** Shown chips flicker between yes and no until the list is filled ('intro'). */
  flicker: number;
  stamp: { appear: number };
};

export function frameState(props: DinnerPartyProps, t: number, beats: number[], dur: number): DinnerPartyState {
  const st = sceneTime(fin(t), dur);
  const d = Number.isFinite(dur) && dur > 0 ? dur : 8;
  const b0 = beatAt(beats, 0);
  if (props.mode === 'check') {
    const fillStart = b0 + 0.2;
    return {
      friends: FRIENDS.map(() => ({ appear: 1 })),
      cards: CONDITIONS.map((_, i) => ({ appear: 1, tick: easeOutCubic(progress(st, fillStart + 1.0 + i * 0.45, 0.3)) })),
      chips: FRIENDS.map((_, i) => ({ appear: 1, fill: easeOutCubic(progress(st, fillStart + i * 0.2, 0.3)) })),
      flicker: 0,
      stamp: { appear: 0 },
    };
  }
  const b1 = beatOr(beats, 1, b0 + d * 0.2);
  const b2 = beatOr(beats, 2, b1 + d * 0.2);
  const b3 = beatOr(beats, 3, b2 + d * 0.2);
  const b4 = beatOr(beats, 4, b3 + d * 0.2);
  const cardAt = [b0 + 0.2, b1, b2];
  return {
    friends: FRIENDS.map((_, i) => ({ appear: easeOutCubic(progress(st, b0 + i * 0.12 - 0.3, 0.4)) })),
    cards: CONDITIONS.map((_, i) => ({ appear: easeOutCubic(progress(st, cardAt[i], 0.45)), tick: 0 })),
    chips: FRIENDS.map((_, i) => ({ appear: easeOutCubic(progress(st, b3 + i * 0.1, 0.35)), fill: 0 })),
    flicker: clamp01(progress(st, b3, 0.4)),
    stamp: { appear: easeOutCubic(progress(st, b4, 0.5)) },
  };
}
