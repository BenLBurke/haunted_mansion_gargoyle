# Entry point -- MicroPython auto-runs this after boot.py once it's copied
# to the Pico's flash root. Wires config, WiFi provisioning, hardware, and
# the polling loop together.
#
# This is a single cooperative loop rather than threads/asyncio for the main
# app (unlike wifi_portal.py, which needs asyncio for its DNS+HTTP servers):
# playing a sound or the change animation blocks candle flicker updates for
# a second or two, which is an acceptable trade rather than the complexity
# of coordinating RP2040's second core for something this small.

import time

import gargoyle_config
import network_setup
from audio import SoundPlayer
from candle import make_candle
from display import Screen, make_display
from parks import get_park
from provision import needs_provisioning, run_provisioning
from state import StateTracker
from themeparks_api import ThemeParksApiError, fetch_snapshot

POLL_TICK_MS = 60  # candle flicker update granularity


def run():
    config = gargoyle_config.load()

    if needs_provisioning(config):
        run_provisioning(config)  # blocks; the device resets itself on success
        return

    park = get_park(config["park"])
    park_label = park.short_label

    candles = [
        make_candle(config["led_pin_candlestick_1"]),
        make_candle(config["led_pin_candlestick_2"]),
    ]

    device = make_display(
        config["i2c_id"],
        config["i2c_scl_pin"],
        config["i2c_sda_pin"],
        config["display_width"],
        config["display_height"],
        config["display_i2c_address"],
    )
    screen = Screen(device, config["display_width"], config["display_height"])

    sound = SoundPlayer(config["i2s_id"], config["i2s_sck_pin"], config["i2s_ws_pin"], config["i2s_sd_pin"])

    tracker = StateTracker()
    screen.show_message("Waking up...")
    sound.play("startup")

    poll_interval_ms = config["poll_interval_seconds"] * 1000
    last_poll = time.ticks_add(time.ticks_ms(), -poll_interval_ms)  # poll immediately on the first loop

    while True:
        now = time.ticks_ms()

        for candle in candles:
            candle.step()

        if time.ticks_diff(now, last_poll) >= poll_interval_ms:
            last_poll = now
            _poll_and_react(park, park_label, screen, sound, tracker, config)

        time.sleep_ms(POLL_TICK_MS)


def _poll_and_react(park, park_label, screen, sound, tracker, config):
    try:
        snapshot = fetch_snapshot(park)
    except ThemeParksApiError as exc:
        print("themeparks.wiki request failed:", exc)
        screen.show_message("Lost the signal...", "retrying")
        return

    reactions = tracker.update(snapshot)
    connected = network_setup.is_connected()

    if reactions.wait_time_changed:
        screen.play_wait_time_change_animation()
        if reactions.wait_time_increased and config["sound_on_wait_increase"]:
            sound.play("wait_increased")
        if reactions.wait_time_decreased and config["sound_on_wait_decrease"]:
            sound.play("wait_decreased")

    if reactions.park_just_opened and config["sound_on_park_open"]:
        sound.play("park_open")
    if reactions.park_just_closed and config["sound_on_park_close"]:
        sound.play("park_close")

    screen.show_snapshot(snapshot, park_label, connected)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        # Sealed inside the print with no keyboard/screen for a REPL, so
        # crash-and-reset beats crash-and-hang. See docs/HARDWARE.md for why
        # this isn't backed by the RP2040's hardware watchdog too.
        import sys

        sys.print_exception(exc)
        time.sleep(5)
        import machine

        machine.reset()
