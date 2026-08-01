"""Plays the gargoyle's sound cues over ALSA (the MAX98357A I2S amp shows up as a normal ALSA device)."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from gargoyle.audio.generate_tones import CUES, SOUNDS_DIR, generate_all

log = logging.getLogger(__name__)

CueName = str  # one of the keys in CUES, without the .wav extension


class SoundPlayer:
    def __init__(self, device: str | None = None, volume: float = 0.8, sounds_dir: Path = SOUNDS_DIR):
        self.device = device
        self.volume = volume
        self.sounds_dir = sounds_dir
        self._aplay = shutil.which("aplay")
        generate_all(sounds_dir)  # fills in any cue that hasn't been manually replaced
        if self._aplay is None:
            log.warning("aplay not found on PATH; sound cues will be logged but not played")
        self._apply_volume()

    def play(self, cue: CueName) -> None:
        filename = f"{cue}.wav"
        if filename not in CUES:
            raise ValueError(f"Unknown sound cue '{cue}'. Valid cues: {sorted(n[:-4] for n in CUES)}")

        path = self.sounds_dir / filename
        if self._aplay is None or not path.exists():
            log.info("(sound cue '%s' not played: %s)", cue, path)
            return

        cmd = [self._aplay, "-q"]
        if self.device:
            cmd += ["-D", self.device]
        cmd.append(str(path))
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, OSError):
            log.warning("failed to play sound cue '%s'", cue, exc_info=True)

    def _apply_volume(self) -> None:
        amixer = shutil.which("amixer")
        if amixer is None:
            return
        percent = max(0, min(100, round(self.volume * 100)))
        try:
            subprocess.run(
                [amixer, "-q", "sset", "PCM", f"{percent}%"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            log.debug("amixer volume set failed", exc_info=True)
