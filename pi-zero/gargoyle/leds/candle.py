"""Drives a single LED with a random-walk brightness pattern that reads as a flickering candle flame."""

from __future__ import annotations

import logging
import random
import threading
import time

log = logging.getLogger(__name__)

MIN_BRIGHTNESS = 0.15
MAX_BRIGHTNESS = 1.0
STEP_INTERVAL = 0.06  # seconds between brightness updates -- fast enough to look organic, not strobing
MAX_STEP = 0.22  # largest jump in brightness per tick
GUTTER_CHANCE = 0.04  # odds per tick of a brief near-extinguish "gutter" dip


class CandleLED:
    """Owns one PWM-capable LED output and flickers it in a background thread."""

    def __init__(self, pwm_led, name: str = "candle"):
        self._pwm_led = pwm_led
        self.name = name
        self._brightness = 0.7
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=f"candle-{self.name}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        self._pwm_led.value = 0

    def _run(self) -> None:
        rng = random.Random()
        while not self._stop_event.is_set():
            self._brightness = next_flicker_value(self._brightness, rng)
            self._pwm_led.value = self._brightness
            time.sleep(STEP_INTERVAL)


def next_flicker_value(current: float, rng: random.Random | None = None) -> float:
    """Pure function computing the next brightness value from the current one.

    Kept separate from CandleLED so the flicker algorithm is unit-testable
    without any GPIO hardware involved.
    """
    rng = rng or random
    if rng.random() < GUTTER_CHANCE:
        return MIN_BRIGHTNESS

    delta = rng.uniform(-MAX_STEP, MAX_STEP)
    value = current + delta
    return max(MIN_BRIGHTNESS, min(MAX_BRIGHTNESS, value))
