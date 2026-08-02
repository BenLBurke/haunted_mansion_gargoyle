"""Loading/saving the gargoyle's YAML config file."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import yaml

from gargoyle.parks import DEFAULT_PARK_KEY, get_park

DEFAULT_CONFIG_PATH = Path("/etc/gargoyle/config.yaml")


@dataclasses.dataclass
class Config:
    # Which resort/attraction to track. See gargoyle/parks.py for valid keys.
    park: str = DEFAULT_PARK_KEY

    # How often to poll the themeparks.wiki API, in seconds. The API is a free
    # community project fed by park data partners -- be polite, don't go below 30s.
    poll_interval_seconds: int = 60

    # GPIO (BCM numbering) driving each candlestick's flame LED.
    led_pin_candlestick_1: int = 17
    led_pin_candlestick_2: int = 27

    # I2C bus/address for the SSD1306 OLED screen.
    display_i2c_port: int = 1
    display_i2c_address: int = 0x3C
    display_width: int = 128
    display_height: int = 64

    # ALSA device used for sound playback (the MAX98357A I2S amp shows up as
    # the default `hw:0,0`-style card unless you've added other audio devices).
    audio_device: str | None = None
    sound_on_wait_increase: bool = False
    sound_on_wait_decrease: bool = True
    sound_on_park_open: bool = True
    sound_on_park_close: bool = True
    volume: float = 0.8

    # Force software fallbacks (mock GPIO/display/audio) for developing off-Pi.
    simulate: bool = False

    # WiFi provisioning
    ap_ssid: str = "Gargoyle-Setup"
    ap_password: str = "hauntedmansion"
    portal_port: int = 80
    connectivity_timeout_seconds: int = 30

    # Hold this pin's button for reset_hold_seconds to forget WiFi and
    # reboot into setup mode (also re-prompts for which park to track).
    reset_button_pin: int = 22
    reset_hold_seconds: float = 3.0

    # OTA updates -- see docs/OTA.md.
    ota_enabled: bool = True
    ota_repo: str = "BenLBurke/haunted_mansion_gargoyle"
    ota_check_interval_hours: float = 24.0

    def park_info(self):
        return get_park(self.park)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_CONFIG_PATH) -> "Config":
        path = Path(path)
        if not path.exists():
            return cls()
        with path.open() as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}
        known_fields = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in raw.items() if k in known_fields}
        return cls(**filtered)

    def save(self, path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as fh:
            yaml.safe_dump(dataclasses.asdict(self), fh, sort_keys=False)
