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
    "i2c_id": 0,
    "i2c_scl_pin": 5,
    "i2c_sda_pin": 4,
    "display_width": 128,
    "display_height": 64,
    "display_i2c_address": 0x3C,
    # "ssd1306" (default, 128x64 I2C OLED) or "ili9341" (2.8"/320x240 SPI
    # TFT) -- see docs/HARDWARE.md. Switching to ili9341 also needs
    # display_width/display_height set to 320/240.
    "display_driver": "ssd1306",
    "tft_spi_id": 1,
    "tft_sck_pin": 10,
    "tft_mosi_pin": 11,
    "tft_miso_pin": 8,
    "tft_cs_pin": 9,
    "tft_dc_pin": 12,
    "tft_rst_pin": 13,
    "tft_rotation": 90,  # 0/90/180/270 -- rotate if the image comes up sideways
    "tft_fg_color": 0xFD20,  # RGB565, warm amber (candlelight) by default
    "tft_bg_color": 0x0000,  # RGB565, black
    "i2s_id": 0,
    "i2s_sck_pin": 16,
    "i2s_ws_pin": 17,  # must always be i2s_sck_pin + 1, see docs/HARDWARE.md
    "i2s_sd_pin": 18,
    # Flip these off while bring-up testing on a breadboard without the OLED
    # or amp/speaker wired yet -- with the OLED missing, an I2C write with no
    # device to ACK it raises OSError and crashes main.py at boot. See
    # README.md "Testing without the screen or speaker" for how to use these.
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
