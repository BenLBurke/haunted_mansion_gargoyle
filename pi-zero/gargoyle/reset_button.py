"""Hold a physical button to forget WiFi and reboot into setup mode.

Re-provisioning already asks for both WiFi credentials and which park to
track via the existing captive portal form, so this alone covers
"reconnect to WiFi and re-select park." gpiozero's Button already does
hold-duration detection and debouncing well, so there's no need to
reimplement that logic the way the Pico build has to.
"""

from __future__ import annotations

import logging

from gargoyle import network

log = logging.getLogger(__name__)


class MockButton:
    """Stands in for gpiozero.Button when not running on real hardware."""

    def __init__(self, pin: int, hold_time: float):
        self.pin = pin
        self.hold_time = hold_time
        self.when_held = None

    def close(self) -> None:
        pass


def make_reset_button(pin: int, hold_seconds: float, on_triggered, simulate: bool):
    if simulate:
        return MockButton(pin, hold_seconds)
    try:
        from gpiozero import Button

        button = Button(pin, pull_up=True, hold_time=hold_seconds)
        button.when_held = on_triggered
        return button
    except Exception:
        log.warning("gpiozero unavailable, falling back to mock reset button on pin %s", pin, exc_info=True)
        return MockButton(pin, hold_seconds)


def factory_reset() -> None:
    """Forgets saved WiFi credentials and reboots into setup mode."""
    log.info("reset button held -- forgetting WiFi and rebooting into setup mode")
    network.forget_all_wifi_connections()
    network.reboot()
