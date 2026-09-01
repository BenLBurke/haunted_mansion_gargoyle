# Loading/saving the gargoyle's config file (plain JSON -- MicroPython has no PyYAML).
#
# Named gargoyle_config.py rather than config.py to avoid shadowing anything
# a future library might expect to import as "config" on the device.

import json

CONFIG_PATH = "config.json"

DEFAULTS = {
    "park": "disneyland",
    "poll_interval_seconds": 60,
    # BCM-style GPIO numbers (see docs/HARDWARE.md for the full pin map and
    # why GP23/24/25/29 are off limits on the Pico W).
    "led_pin_candlestick_1": 2,
    "led_pin_candlestick_2": 3,
    # 2.8" 320x240 ILI9341 SPI TFT -- see docs/HARDWARE.md for the wiring
    # table and which header pin on the panel each of these maps to.
    "spi_id": 1,
    "spi_baudrate": 40_000_000,
    "spi_sck_pin": 10,
    "spi_mosi_pin": 11,
    "spi_miso_pin": 8,
    "spi_cs_pin": 9,
    "spi_dc_pin": 12,
    "spi_rst_pin": 13,
    # None because the panel's LED (backlight) pin is wired straight to 3V3
    # rather than a GPIO -- set this if yours is instead wired to a pin that
    # needs driving high to turn the backlight on.
    "spi_backlight_pin": None,
    "display_width": 320,
    "display_height": 240,
    "display_rotation": 90,  # 0/90/180/270 -- rotate if the image comes up sideways
    "i2s_id": 0,
    "i2s_sck_pin": 16,
    "i2s_ws_pin": 17,  # must always be i2s_sck_pin + 1, see docs/HARDWARE.md
    "i2s_sd_pin": 18,
    # Flip these off while bring-up testing on a breadboard without the TFT
    # or amp/speaker wired yet -- with the panel missing, an SPI write with
    # no device to receive it can hang/crash main.py at boot. See README.md
    # "Testing without the screen or speaker" for how to use these.
    "display_enabled": True,
    "audio_enabled": True,
    "sound_on_wait_increase": False,
    "sound_on_wait_decrease": True,
    "sound_on_park_open": True,
    "sound_on_park_close": True,
    "ap_ssid": "Gargoyle-Setup",
    "ap_password": "hauntedmansion",
    "connectivity_timeout_seconds": 30,
    # Hold this pin's button for reset_hold_seconds to forget WiFi and
    # reboot into setup mode (also re-prompts for which park to track).
    "reset_button_pin": 15,
    "reset_hold_seconds": 3,
    # OTA updates -- see docs/OTA.md.
    "ota_enabled": True,
    "ota_repo": "BenLBurke/haunted_mansion_gargoyle",
    "ota_check_interval_hours": 24,
}


def load(path=CONFIG_PATH):
    config = dict(DEFAULTS)
    try:
        with open(path) as fh:
            saved = json.load(fh)
    except OSError:
        return config
    for key, value in saved.items():
        if key in DEFAULTS:
            config[key] = value
    return config


def save(config, path=CONFIG_PATH):
    with open(path, "w") as fh:
        json.dump(config, fh)
