"""Soft ambient pad generated in code: the default music bed under the narration.

No samples, no licence, no network. The bed is exactly periodic (every partial completes a whole
number of cycles over its length), so it loops without a click and can sit under any video length.

Usage: python3 scripts/music_local.py [seconds=80] [out=public/music/bed.wav]
Needs numpy (the npm script falls back to `uv run --with numpy` when python3 lacks it).
"""
import sys
import wave
from pathlib import Path

import numpy as np

RATE = 48000
CHORD_SECONDS = 5.0
# A calm minor progression voiced in the middle register (MIDI notes): Am9 - Fmaj7 - Cmaj7 - G6.
CHORDS = [
    [45, 57, 60, 64, 71],
    [41, 57, 60, 64, 65],
    [48, 55, 59, 60, 64],
    [43, 55, 59, 62, 64],
]


def midi_hz(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def periodic(freq: float, length: float) -> float:
    """Nearest frequency that fits a whole number of cycles in `length` seconds."""
    return max(1, round(freq * length)) / length


def pad(seconds: float) -> np.ndarray:
    # Whole progression cycles only, so the chord change at the loop point is a normal one.
    cycle = CHORD_SECONDS * len(CHORDS)
    length = cycle * max(1, int(np.ceil(seconds / cycle)))
    n = int(length * RATE)
    t = np.arange(n) / RATE
    out = np.zeros((n, 2))
    slots = int(length / CHORD_SECONDS)
    for slot in range(slots):
        chord = CHORDS[slot % len(CHORDS)]
        # Raised-cosine window 1.6x the chord slot: neighbours crossfade; wraps around the loop.
        centre = (slot + 0.5) * CHORD_SECONDS
        dist = (t - centre + length / 2) % length - length / 2
        half = CHORD_SECONDS * 0.8
        env = np.where(np.abs(dist) < half, 0.5 * (1 + np.cos(np.pi * dist / half)), 0.0)
        active = env > 0
        for i, note in enumerate(chord):
            base = midi_hz(note)
            gain = 0.55 if i == 0 else 0.32
            for side, cents in ((0, -4), (1, 4)):  # slight detune per channel for width
                f = periodic(base * 2 ** (cents / 1200), length)
                tone = np.zeros(n)
                # Mellow timbre: fundamental plus two soft overtones.
                for k, amp in ((1, 1.0), (2, 0.18), (3, 0.06)):
                    fk = periodic(f * k, length)
                    tone[active] += amp * np.sin(2 * np.pi * fk * t[active] + 0.7 * i)
                out[:, side] += gain * env * tone
    # Slow breathing in level, whole cycles over the loop.
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * periodic(0.07, length) * t)
    out *= lfo[:, None]
    out /= np.abs(out).max()
    return out * 10 ** (-6 / 20)  # peak at -6 dBFS; the video sets the final level


def main() -> None:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 80.0
    root = Path(__file__).resolve().parent.parent
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "public" / "music" / "bed.wav"
    audio = pad(max(70.0, seconds))
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((audio * 32767).astype("<i2").tobytes())
    print(f"{target} ({len(audio) / RATE:.0f} s, loopable)")


if __name__ == "__main__":
    main()
