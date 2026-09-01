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
import ota
from audio import NullSoundPlayer, SoundPlayer
from candle import make_candle
from display import ConsoleScreen, Screen, make_display
from parks import get_park
from provision import needs_provisioning, run_provisioning
from reset_button import ResetButton, factory_reset
from state import StateTracker
from themeparks_api import ThemeParksApiError, fetch_snapshot

POLL_TICK_MS = 60  # candle flicker update granularity


def run():
    config = gargoyle_config.load()

    # If we got this far, every module main.py imports (including this one)
    # compiled and ran its top-level code successfully -- reasonable proof
    # an OTA update, if one is pending confirmation, is basically sound. See
    # ota.py and boot.py for the other half of this (rollback if it's NOT
    # confirmed within a couple of boots).
    ota.confirm_boot()

    # Created before the connectivity check (not after) so the candles keep
    # flickering through the entire boot -- including a stuck-for-30-seconds
    # WiFi join attempt or a stretch in the captive portal -- rather than
    # going dark for however long WiFi takes to sort itself out.
    candles = [
        make_candle(config["led_pin_candlestick_1"]),
        make_candle(config["led_pin_candlestick_2"]),
    ]
    button = ResetButton(config["reset_button_pin"], hold_ms=config["reset_hold_seconds"] * 1000)

    if needs_provisioning(config, candles, button):
        run_provisioning(config, candles, button)  # blocks; the device resets itself on success
        return

    park = get_park(config["park"])
    park_label = park.short_label

    if config["display_enabled"]:
        device = make_display(config)
        screen = Screen(device, config["display_width"], config["display_height"], park_label=park_label)
    else:
        print("display_enabled is false -- printing screen contents to the console instead")
        screen = ConsoleScreen()

    if config["audio_enabled"]:
        sound = SoundPlayer(config["i2s_id"], config["i2s_sck_pin"], config["i2s_ws_pin"], config["i2s_sd_pin"])
    else:
        print("audio_enabled is false -- printing sound cues to the console instead")
        sound = NullSoundPlayer()

    tracker = StateTracker()
    screen.begin()  # paint the static gothic scene once
    screen.show_message("Waking up...")
    sound.play("startup")

    poll_interval_ms = config["poll_interval_seconds"] * 1000
    last_poll = time.ticks_add(time.ticks_ms(), -poll_interval_ms)  # poll immediately on the first loop

    ota_interval_ms = config["ota_check_interval_hours"] * 3600 * 1000
    last_ota_check = time.ticks_ms()  # don't check immediately -- let the device settle in first

    while True:
        now = time.ticks_ms()

        for candle in candles:
            candle.step()

        # Advances the on-screen candle flame (4-step, 1.6s) and the ghost's
        # occasional drift pass. Cheap and non-blocking: ~448 bytes of SPI
        # every 400ms. Distinct from the physical candle LEDs above.
        screen.tick()

        if button.check():
            factory_reset()  # never returns -- forgets WiFi and resets

        if time.ticks_diff(now, last_poll) >= poll_interval_ms:
            last_poll = now
            _poll_and_react(park, park_label, screen, sound, tracker, config)

        if config["ota_enabled"] and time.ticks_diff(now, last_ota_check) >= ota_interval_ms:
            last_ota_check = now
            ota.check_and_apply(config)  # resets the device if an update was applied

        time.sleep_ms(POLL_TICK_MS)


def _poll_and_react(park, park_label, screen, sound, tracker, config):
    try:
        snapshot = fetch_snapshot(park)
    except ThemeParksApiError as exc:
        print("themeparks.wiki request failed:", exc)
        # Keep the last known number on screen. A stale wait time is more
        # useful on an always-on ambient display than an error message, and
        # the panel should never look broken. show_stale() draws only a
        # small dim corner mark and leaves the numeral untouched.
        if tracker.current is not None:
            screen.show_stale()
        else:
            # Nothing has ever been fetched, so there is no number to keep.
            screen.show_message("Lost the signal...", "retrying")
        return

    reactions = tracker.update(snapshot)
    connected = network_setup.is_connected()
    screen.clear_stale()

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
