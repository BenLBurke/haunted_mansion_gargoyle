"""Picks a real gpiozero PWMLED on a Pi, or a no-op mock everywhere else."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class MockPWMLED:
    """Stands in for gpiozero.PWMLED when not running on real hardware."""

    def __init__(self, pin: int):
        self.pin = pin
        self._value = 0.0

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float) -> None:
        self._value = v

    def close(self) -> None:
        pass


def make_pwm_led(pin: int, simulate: bool):
    if simulate:
        return MockPWMLED(pin)
    try:
        from gpiozero import PWMLED

        return PWMLED(pin)
    except Exception:
        log.warning("gpiozero unavailable, falling back to mock LED on pin %s", pin, exc_info=True)
        return MockPWMLED(pin)
