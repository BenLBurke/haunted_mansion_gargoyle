"""Synthesizes the gargoyle's sound cues as WAV files using only the stdlib.

Run as `python -m gargoyle.audio.generate_tones` (also done automatically by
scripts/install.sh). These are placeholder "spooky enough" tones -- swap any
file in gargoyle/audio/sounds/ with your own recording/download and it'll be
used instead, as long as the filename matches.
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path
from typing import Callable

SAMPLE_RATE = 22050
SOUNDS_DIR = Path(__file__).parent / "sounds"

Samples = list[float]


def _envelope(n: int, i: int, attack: float = 0.05, release: float = 0.25) -> float:
    attack_n = int(n * attack)
    release_n = int(n * release)
    if attack_n and i < attack_n:
        return i / attack_n
    if release_n and i > n - release_n:
        return max(0.0, (n - i) / release_n)
    return 1.0


def tone(
    freq_fn: Callable[[float], float],
    duration: float,
    amplitude: float = 0.5,
    noise: float = 0.0,
    rng: random.Random | None = None,
) -> Samples:
    rng = rng or random.Random(0)
    n = int(duration * SAMPLE_RATE)
    samples = []
    phase = 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = freq_fn(t)
        phase += 2 * math.pi * freq / SAMPLE_RATE
        val = math.sin(phase)
        if noise:
            val += noise * (rng.random() * 2 - 1)
        val *= amplitude * _envelope(n, i)
        samples.append(val)
    return samples


def concat(*parts: Samples) -> Samples:
    out: Samples = []
    for part in parts:
        out.extend(part)
    return out


def write_wav(path: Path, samples: Samples) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SAMPLE_RATE)
        frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(s * 32767)))) for s in samples)
        fh.writeframes(frames)


def _startup() -> Samples:
    return tone(lambda t: 220 + 440 * t, duration=0.6, amplitude=0.4)


def _wait_decreased() -> Samples:
    # A pleasant-but-eerie two-note bell -- good news, wait went down.
    return concat(
        tone(lambda t: 880, duration=0.15, amplitude=0.45),
        tone(lambda t: 659, duration=0.3, amplitude=0.4),
    )


def _wait_increased() -> Samples:
    rng = random.Random(1)
    return tone(lambda t: 500 - 150 * t, duration=0.4, amplitude=0.35, noise=0.02, rng=rng)


def _park_open() -> Samples:
    return concat(
        tone(lambda t: 440, duration=0.12, amplitude=0.4),
        tone(lambda t: 554, duration=0.12, amplitude=0.4),
        tone(lambda t: 659, duration=0.25, amplitude=0.4),
    )


def _park_close() -> Samples:
    # A slow descending, vibrato-laden "howl".
    rng = random.Random(2)

    def freq_fn(t: float) -> float:
        base = 500 - 340 * (t / 2.2)
        vibrato = 18 * math.sin(2 * math.pi * 5 * t)
        return max(80.0, base + vibrato)

    return tone(freq_fn, duration=2.2, amplitude=0.5, noise=0.015, rng=rng)


def _error() -> Samples:
    return tone(lambda t: 220, duration=0.15, amplitude=0.3)


CUES: dict[str, Callable[[], Samples]] = {
    "startup.wav": _startup,
    "wait_decreased.wav": _wait_decreased,
    "wait_increased.wav": _wait_increased,
    "park_open.wav": _park_open,
    "park_close.wav": _park_close,
    "error.wav": _error,
}


def generate_all(output_dir: Path = SOUNDS_DIR, overwrite: bool = False) -> None:
    for filename, generator in CUES.items():
        path = output_dir / filename
        if path.exists() and not overwrite:
            continue
        write_wav(path, generator())
        print(f"wrote {path}")


if __name__ == "__main__":
    generate_all(overwrite=True)
