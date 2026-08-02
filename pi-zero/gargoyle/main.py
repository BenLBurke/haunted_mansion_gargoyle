"""Entry point: wires config, WiFi provisioning, hardware, and the polling loop together."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading

from gargoyle import network
from gargoyle.audio.player import SoundPlayer
from gargoyle.config import Config, DEFAULT_CONFIG_PATH
from gargoyle.display.backend import make_screen
from gargoyle.display.screen import Screen
from gargoyle.leds.candle import CandleLED
from gargoyle.leds.gpio_backend import make_pwm_led
from gargoyle.reset_button import factory_reset, make_reset_button
from gargoyle.state import Snapshot, StateTracker
from gargoyle.themeparks_api import ThemeParksApiError, ThemeParksClient
from gargoyle.wifi_setup.provision import needs_provisioning, run_provisioning

log = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Haunted Mansion wait-time gargoyle")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--simulate", action="store_true", help="force mock hardware backends")
    return parser


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


class Gargoyle:
    def __init__(self, config: Config):
        self.config = config
        self._stop_event = threading.Event()

        self.candles = [
            CandleLED(make_pwm_led(config.led_pin_candlestick_1, config.simulate), name="left"),
            CandleLED(make_pwm_led(config.led_pin_candlestick_2, config.simulate), name="right"),
        ]

        device = make_screen(
            config.display_width,
            config.display_height,
            config.display_i2c_port,
            config.display_i2c_address,
            config.simulate,
        )
        self.screen = Screen(device, config.display_width, config.display_height)

        self.sound = SoundPlayer(device=config.audio_device, volume=config.volume)

        # gpiozero's Button runs hold-detection on its own background thread,
        # so unlike the Pico build there's no polling loop needed here.
        self.reset_button = make_reset_button(
            config.reset_button_pin, config.reset_hold_seconds, factory_reset, config.simulate
        )

        self.api = ThemeParksClient(config.park_info())
        self.tracker = StateTracker()

    def start(self) -> None:
        for candle in self.candles:
            candle.start()
        self.sound.play("startup")
        self.screen.show_message("Waking up...")

    def stop(self) -> None:
        for candle in self.candles:
            candle.stop()
        self.reset_button.close()

    def request_stop(self) -> None:
        self._stop_event.set()

    def poll_once(self) -> None:
        park_label = self.config.park_info().short_label
        try:
            attraction = self.api.get_attraction_status()
            hours = self.api.get_todays_park_hours()
        except ThemeParksApiError:
            log.warning("themeparks.wiki request failed", exc_info=True)
            self.screen.show_message("Lost the signal...", "retrying")
            return

        snapshot = Snapshot(attraction=attraction, hours=hours)
        reactions = self.tracker.update(snapshot)
        connected = network.is_connected()

        if reactions.wait_time_changed:
            self.screen.play_wait_time_change_animation()
            if reactions.wait_time_increased and self.config.sound_on_wait_increase:
                self.sound.play("wait_increased")
            if reactions.wait_time_decreased and self.config.sound_on_wait_decrease:
                self.sound.play("wait_decreased")

        if reactions.park_just_opened and self.config.sound_on_park_open:
            self.sound.play("park_open")
        if reactions.park_just_closed and self.config.sound_on_park_close:
            self.sound.play("park_close")

        self.screen.show_snapshot(snapshot, park_label, connected)

    def run_forever(self) -> None:
        self.start()
        while not self._stop_event.is_set():
            self.poll_once()
            self._stop_event.wait(self.config.poll_interval_seconds)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = build_arg_parser().parse_args(argv)

    config = Config.load(args.config)
    if args.simulate:
        config.simulate = True

    if not config.simulate and needs_provisioning(config):
        run_provisioning(config)
        return 0  # the device reboots itself once provisioning succeeds

    gargoyle = Gargoyle(config)

    def handle_sigterm(signum, frame):
        gargoyle.request_stop()

    # SIGTERM has no default Python exception, so we intercept it to shut down
    # cleanly. SIGINT (Ctrl+C) is deliberately left alone: Python's default
    # handler raises KeyboardInterrupt, which is what lets it break out of a
    # blocked wait() immediately. A handler that just sets a flag and returns
    # normally doesn't -- the blocking call has no reason to wake up early, so
    # Ctrl+C would silently do nothing until the current poll wait times out.
    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        gargoyle.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        gargoyle.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
